// LightDX - AS7341 dosimeter test firmware for M5Capsule 1.1 (Stamp-S3A / ESP32-S3)
//
// Reads the Adafruit AS7341 over I2C with auto-gain, serves a live spectrum page over a WiFi access point,
// and records sessions to the SD card ONLY when the user presses Start on the page.
//
//   Live mode   : WiFi AP + web page, ~2.3 samples/s. Nothing is logged unless a session is recording.
//   Recording   : Start/Stop on the page. A session logs one row per minute and accumulates J_ppix (session dose).
//                 It stops by itself after REC_MAX_S (12 h) or when the battery is low.
//   Sleep cycle : while recording, if nobody uses the page for LIVE_IDLE_TIMEOUT_MS the board sleeps between rows
//                 (M5 timerSleep: fully powered off on battery, deep sleep on USB), wakes on the RTC, takes one
//                 reading, appends a row and sleeps again. A button press or USB plug-in starts live mode.
//
// Uses the local AS7341 driver (copied from Pocket-Spectrometer-V2, m5-atom-lite-arduino).
// Gain/AGC approach follows Non-Invasive-Bioelectronics-Lab/Wearable_Light_Sensor_Public (MIT).
// Ambient-light measurement: the AS7341 onboard LED is never switched on.

#include <Wire.h>
#include <Preferences.h>
#include <M5Capsule.h> // official M5Stack library: power hold (G46), BM8563 RTC (M5Capsule.Rtc), BMI270 (M5.Imu)
#include "AS7341.h"

// ---- Pins (Capsule v1.1 pinmap sticker: PORT.A = G13 yellow/SDA, G15 white/SCL; buzzer = G2, RGB LED = G21) ----
// setup() retries with SDA/SCL swapped if 0x39 isn't found.
#define I2C_SDA 13
#define I2C_SCL 15
#define BUZZER_PIN 2
#define LED_PIN 21

// ---- Sensor configuration ----
// Long fixed integration time, so gain is the only range knob.
// tint = (ATIME+1)*(ASTEP+1)*2.78 us = ~50 ms per pass (was 65466 -> ~182 ms).
#define SENSOR_ATIME 0
#define SENSOR_ASTEP 17999

#define GAIN_MAX_CODE 10      // 0..10 = 0.5x..512x
#define GAIN_START_CODE 5     // 16x
#define AGC_MAX_ITERATIONS 8
#define LOW_FRACTION 0.15f    // a channel below this fraction of full scale -> try more gain
#define FLICKER_EVERY_N 30    // run flicker detection every N samples in live mode (0 = never)
#define SAMPLE_PERIOD_MS 0     // back-to-back: rate = sensor read time (~0.4 s)

// ---- Recording / power configuration ----
#define LOG_PERIOD_S 60                      // one row per minute while recording
#define REC_MAX_S (12UL * 3600UL)            // a session stops by itself after 12 h
#define BATT_LOW_MV 3300                     // a session stops by itself below this (battery readings are only valid on battery, not USB)
#ifndef LIVE_IDLE_TIMEOUT_MS
#define LIVE_IDLE_TIMEOUT_MS (10UL * 60UL * 1000UL) // while recording: no web page/serial activity for this long -> sleep cycle
#endif

// Gain code -> factor, and the per-gain correction table from the Bioelectronics Lab wearable.
// NOTE: correctionGain is that lab's calibration of their own sensor; unverified for this one.
static const float GAIN_FACTOR[11] = {0.5f, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512};
static const float CORRECTION_GAIN[11] = {1.06f, 1.05f, 1.05f, 1.05f, 1.02f, 1.02f, 1.01f, 1.00f, 1.00f, 0.99f, 0.96f};

// Channel order in all arrays below.
enum { CH_F1, CH_F2, CH_F3, CH_F4, CH_F5, CH_F6, CH_F7, CH_F8, CH_CLEAR, CH_NIR, CH_COUNT };
static const char *CH_NAME[CH_COUNT] = {"F1_415", "F2_445", "F3_480", "F4_515", "F5_555",
                                        "F6_590", "F7_630", "F8_680", "Clear", "NIR"};

// One calibrated sample (declared early so the Arduino auto-generated prototypes can see it).
struct Sample
{
    uint16_t raw[CH_COUNT];
    float cnt[CH_COUNT];
    float ePpix, lux, tintMs;
    int nSat;
};

// PpIX index: E_ppix = K_SCALE * sum(W_PPIX[i] * cnt_Fi). Weights come from analysis/ppix_weights.py
// (placeholder responsivity/PpIX spectra for now). K_SCALE = 1 means ARBITRARY units, uncalibrated.
#include "ppix_weights.h"
#define K_SCALE 1.0f

// Illuminance: lux = LUX_K * sum(W_LUX[i] * cnt_Fi) (weights from analysis/lux_weights.py, photopic V(l)).
// LUX_K = 1 means the "lux" column is ARBITRARY until calibrated: LUX_K = meter_lux / printed_lux (at LUX_K = 1).
#include "lux_weights.h"
#define LUX_K 1.0f

// ---- WiFi access point + live web page (join the AP, open http://192.168.4.1/) ----
#include <WiFi.h>
#include <WebServer.h>
#include "html_content.h"
#define AP_SSID "LightDX"
#define AP_PASS "lightdx123" // >= 8 chars, or "" for an open network

WebServer server(80);
static char lastJson[640] = "{}"; // latest sample, served at /data (guarded by jsonMutex)
static SemaphoreHandle_t jsonMutex;
static volatile bool pendingClockSet = false;
static int pendingClock[6]; // y, mo, d, h, mi, s
static volatile int pendingCmd = 0; // set by the web task, handled in loop(): 1 = start session, 2 = stop session
static volatile uint32_t lastActivityMs = 0; // last web request or serial host activity (live-mode idle timer)

// Serves web clients on their own task: sensor reads block for ~1 s and would starve handleClient().
static void webTask(void *)
{
    for (;;)
    {
        server.handleClient();
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}

// ---- SD logging (Capsule v1.1 SD: CS G11, MOSI G12, MISO G39, SCK G14) ----
// Serial command 'd' dumps the log, 'e' erases it; the web page also serves it at /log.
#include <SPI.h>
#include <SD.h>
#define SD_CS 11
#define SD_MOSI 12
#define SD_MISO 39
#define SD_SCK 14
#define LOG_FILE "/lightdx_log.csv"
SPIClass sdSPI(FSPI);
static bool sdOk = false;
static SemaphoreHandle_t sdMutex;

AS7341 sensor(Wire);
float jPpix = 0;            // session dose: accumulated index x seconds (arbitrary units until K_SCALE is calibrated)
uint32_t lastSampleMs = 0;
uint8_t gainCode = GAIN_START_CODE;
uint32_t sampleCount = 0;
uint16_t flickerHz = 0;
static bool liveMode = true;

// ---- Session state, kept in flash (NVS) so a reset, brownout or sleep cycle resumes the session ----
static Preferences prefs;
static bool recActive = false;
static uint32_t sessionId = 0;
static uint32_t sessionStartEpoch = 0; // RTC (local time) seconds
static uint32_t lastEpoch = 0;         // RTC time of the previous sample
static uint32_t lastRowEpoch = 0;      // RTC time of the previous logged row
static const char *pendingEvent = nullptr; // event name for the next logged row ("start", "resume")
static bool stopRequested = false;

static bool i2cPresent(uint8_t addr)
{
    Wire.beginTransmission(addr);
    return Wire.endTransmission() == 0;
}

static void i2cScan()
{
    Serial.print("I2C scan:");
    bool any = false;
    for (uint8_t a = 1; a < 127; a++)
    {
        if (i2cPresent(a))
        {
            Serial.printf(" 0x%02X", a);
            any = true;
        }
    }
    Serial.println(any ? "" : " (nothing found)");
}

// One full read: pass 1 = F1-F4, Clear, NIR; pass 2 = F5-F8 (Clear/NIR of pass 2 are ignored).
static void readChannels(uint16_t raw[CH_COUNT])
{
    sensor.startMeasure("F1F4CN");
    for (int i = 0; i < 4; i++)
        raw[CH_F1 + i] = sensor.getChannelData(i);
    raw[CH_CLEAR] = sensor.getChannelData(4);
    raw[CH_NIR] = sensor.getChannelData(5);

    sensor.startMeasure("F5F8CN");
    for (int i = 0; i < 4; i++)
        raw[CH_F5 + i] = sensor.getChannelData(i);
}

// Reads with auto-gain. Leaves gainCode at the final gain; raw[] holds the reading taken at that gain.
static void readWithAgc(uint16_t raw[CH_COUNT])
{
    // ADC full scale is min(65535, (ATIME+1)*(ASTEP+1)); a reading at full scale is saturated.
    const uint32_t fullScale = min<uint32_t>(65535, (uint32_t)(SENSOR_ATIME + 1) * (SENSOR_ASTEP + 1));

    uint8_t saturationGain = GAIN_MAX_CODE + 1; // lowest gain code known to saturate
    for (int iter = 0; iter < AGC_MAX_ITERATIONS; iter++)
    {
        readChannels(raw);

        bool saturated = false, low = false;
        for (int i = 0; i < CH_COUNT; i++)
        {
            if (raw[i] >= fullScale)
                saturated = true;
            if (raw[i] <= LOW_FRACTION * fullScale)
                low = true;
        }

        uint8_t next = gainCode;
        if (saturated)
        {
            if (gainCode == 0)
                return; // cannot go lower
            if (gainCode < saturationGain)
                saturationGain = gainCode;
            next = gainCode - 1;
        }
        else if (low)
        {
            if (gainCode >= GAIN_MAX_CODE)
                return;
            next = (GAIN_MAX_CODE + gainCode + 1) / 2; // halfway up, rounded up
            if (next <= gainCode)
                next = gainCode + 1;
            if (next >= saturationGain)
                return; // would reach a gain that already saturated; stay
        }
        else
        {
            return; // all channels in range
        }

        gainCode = next;
        sensor.setGain(gainCode);
    }
}

static void takeSample(Sample &s, bool withFlicker)
{
    readWithAgc(s.raw);
    if (withFlicker && FLICKER_EVERY_N > 0 && sampleCount % FLICKER_EVERY_N == 0)
        flickerHz = sensor.getFlickerFrequency(); // 0 = none/unknown, 100 or 120 Hz

    s.tintMs = sensor.getIntegrationTime();
    const uint32_t fullScale = min<uint32_t>(65535, (uint32_t)(SENSOR_ATIME + 1) * (SENSOR_ASTEP + 1));
    s.nSat = 0;
    for (int i = 0; i < CH_COUNT; i++)
        if (s.raw[i] >= fullScale)
            s.nSat++;
    for (int i = 0; i < CH_COUNT; i++)
        s.cnt[i] = s.raw[i] / (s.tintMs * GAIN_FACTOR[gainCode]) * CORRECTION_GAIN[gainCode];

    // PpIX-weighted index: weighted sum of F1-F8 (weights from analysis/ppix_weights.py).
    s.ePpix = 0;
    for (int i = 0; i < 8; i++)
        s.ePpix += W_PPIX[i] * s.cnt[CH_F1 + i];
    s.ePpix *= K_SCALE;
    s.lux = 0;
    for (int i = 0; i < 8; i++)
        s.lux += W_LUX[i] * s.cnt[CH_F1 + i];
    s.lux *= LUX_K;
}

// ---- RTC (BM8563) and IMU (BMI270) come from the official M5Capsule / M5Unified libraries ----
// Set the clock with the serial command "t YYYY-MM-DD HH:MM:SS" (local time), or from the web page.
// "NOTSET" is logged if the RTC is missing or reports low voltage (time lost).
static bool imuOk = false;

// "YYYY-MM-DD HH:MM:SS" or "NOTSET" into buf (>= 20 bytes).
static void rtcString(char *buf, size_t n)
{
    if (M5Capsule.Rtc.isEnabled() && !M5Capsule.Rtc.getVoltLow())
    {
        auto dt = M5Capsule.Rtc.getDateTime();
        snprintf(buf, n, "%04d-%02d-%02d %02d:%02d:%02d", dt.date.year, dt.date.month, dt.date.date,
                 dt.time.hours, dt.time.minutes, dt.time.seconds);
    }
    else
        snprintf(buf, n, "NOTSET");
}

// Seconds since 1970-01-01 of the RTC's local time (no time zone handling; only differences are used). 0 = RTC invalid.
static uint32_t rtcEpoch()
{
    if (!M5Capsule.Rtc.isEnabled() || M5Capsule.Rtc.getVoltLow())
        return 0;
    auto dt = M5Capsule.Rtc.getDateTime();
    int y = dt.date.year, m = dt.date.month, d = dt.date.date;
    y -= m <= 2;
    const int era = y / 400;
    const unsigned yoe = y - era * 400;
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    const long days = era * 146097L + (long)doe - 719468L;
    return (uint32_t)(days * 86400L + dt.time.hours * 3600L + dt.time.minutes * 60L + dt.time.seconds);
}

static void setRtc(int y, int mo, int d, int h, int mi, int s)
{
    m5::rtc_datetime_t t;
    t.date.year = y; t.date.month = mo; t.date.date = d;
    t.time.hours = h; t.time.minutes = mi; t.time.seconds = s;
    M5Capsule.Rtc.setDateTime(t);
}

static uint32_t sdTotalMB = 0, sdFreeMB = 0;
static void sdUpdateSpace()
{
    if (!sdOk)
        return;
    uint64_t total = SD.totalBytes(), used = SD.usedBytes();
    sdTotalMB = total / 1048576ULL;
    sdFreeMB = total > used ? (total - used) / 1048576ULL : 0;
}

static String logHeader()
{
    String h = "datetime,session,event,elapsed_s,ms,gain_x,tint_ms,flicker_hz,n_sat";
    for (int i = 0; i < CH_COUNT; i++)
        h += String(",cnt_") + CH_NAME[i];
    h += ",E_ppix,J_ppix,lux,acc_x_g,acc_y_g,acc_z_g,tilt_deg,batt_mv";
    return h;
}

// A log with a different header (older firmware) is kept as /lightdx_log_prevN.csv instead of being mixed in or deleted.
static void sdArchiveOldFormat()
{
    if (!sdOk || !SD.exists(LOG_FILE))
        return;
    File old = SD.open(LOG_FILE, FILE_READ);
    String first = old.readStringUntil('\n');
    old.close();
    first.trim();
    if (first == logHeader())
        return;
    for (int n = 1; n < 100; n++)
    {
        String name = "/lightdx_log_prev" + String(n) + ".csv";
        if (!SD.exists(name))
        {
            SD.rename(LOG_FILE, name);
            Serial.println("SD: old-format log kept as " + name);
            return;
        }
    }
}

static void logRow(const char *row)
{
    if (!sdOk)
        return;
    xSemaphoreTake(sdMutex, portMAX_DELAY);
    bool isNew = !SD.exists(LOG_FILE);
    File f = SD.open(LOG_FILE, FILE_APPEND);
    if (f)
    {
        if (isNew)
            f.println(logHeader());
        f.println(row);
        size_t sz = f.size();
        f.close();
        Serial.printf("SD: logged row, file size now %u bytes\n", (unsigned)sz);
        sdUpdateSpace();
    }
    else
        Serial.println("SD: open for append FAILED");
    xSemaphoreGive(sdMutex);
}

static void dumpLog()
{
    xSemaphoreTake(sdMutex, portMAX_DELAY);
    File f = SD.open(LOG_FILE, FILE_READ);
    if (!f)
        Serial.println("SD: no log file");
    else
    {
        Serial.printf("----- %s (%u bytes) -----\n", LOG_FILE, (unsigned)f.size());
        while (f.available())
            Serial.write(f.read());
        Serial.println("----- end -----");
        f.close();
    }
    xSemaphoreGive(sdMutex);
}

static void printHeader()
{
    Serial.print("ms,gain_x,tint_ms,flicker_hz,n_sat");
    for (int i = 0; i < CH_COUNT; i++)
        Serial.printf(",raw_%s", CH_NAME[i]);
    for (int i = 0; i < CH_COUNT; i++)
        Serial.printf(",cnt_%s", CH_NAME[i]);
    Serial.println(",E_ppix,J_ppix,lux");
}

// ---- Session handling ----
static void saveState()
{
    prefs.putBool("rec", recActive);
    prefs.putUInt("sid", sessionId);
    prefs.putUInt("start", sessionStartEpoch);
    prefs.putUInt("lastep", lastEpoch);
    prefs.putUInt("lastrow", lastRowEpoch);
    prefs.putFloat("j", jPpix);
    prefs.putUChar("gain", gainCode);
}

static void loadState()
{
    recActive = prefs.getBool("rec", false);
    sessionId = prefs.getUInt("sid", 0);
    sessionStartEpoch = prefs.getUInt("start", 0);
    lastEpoch = prefs.getUInt("lastep", 0);
    lastRowEpoch = prefs.getUInt("lastrow", 0);
    jPpix = prefs.getFloat("j", 0);
    gainCode = min<uint8_t>(prefs.getUChar("gain", GAIN_START_CODE), GAIN_MAX_CODE);
}

static void startSession()
{
    uint32_t now = rtcEpoch();
    if (now == 0)
    {
        Serial.println("Session NOT started: RTC not set");
        return;
    }
    sessionId++;
    recActive = true;
    sessionStartEpoch = now;
    lastEpoch = now;
    lastRowEpoch = 0;
    jPpix = 0;
    lastSampleMs = 0;
    stopRequested = false;
    pendingEvent = "start";
    saveState();
    Serial.printf("Session %u started\n", (unsigned)sessionId);
}

// One CSV row for the current sample, with the event name and session columns.
static void logSessionRow(const char *event, const Sample &s, uint32_t now)
{
    char row[420];
    char dt[24];
    rtcString(dt, sizeof(dt));
    const uint32_t elapsed = (now >= sessionStartEpoch) ? now - sessionStartEpoch : 0;
    int m = snprintf(row, sizeof(row), "%s,%u,%s,%u,%lu,%g,%.1f,%u,%d", dt, (unsigned)sessionId, event, (unsigned)elapsed,
                     (unsigned long)millis(), GAIN_FACTOR[gainCode], s.tintMs, flickerHz, s.nSat);
    for (int i = 0; i < CH_COUNT; i++)
        m += snprintf(row + m, sizeof(row) - m, ",%.5f", s.cnt[i]);
    m += snprintf(row + m, sizeof(row) - m, ",%.5f,%.5f,%.5f", s.ePpix, jPpix, s.lux);
    // Accelerometer snapshot (g); tilt = angle between sensor Z axis and gravity (0 = flat, face up).
    float ax, ay, az;
    const int battMv = M5.Power.getBatteryVoltage();
    if (imuOk && M5.Imu.getAccel(&ax, &ay, &az))
    {
        float mag = sqrtf(ax * ax + ay * ay + az * az);
        float tilt = mag > 0.1f ? acosf(constrain(az / mag, -1.0f, 1.0f)) * 57.29578f : NAN;
        snprintf(row + m, sizeof(row) - m, ",%.4f,%.4f,%.4f,%.1f,%d", ax, ay, az, tilt, battMv);
    }
    else
        snprintf(row + m, sizeof(row) - m, ",,,,,%d", battMv);
    logRow(row);
}

// Called for every sample. Integrates the session dose, logs rows and ends the session when needed.
// forceRow = log a row now (sleep-cycle wake-ups); otherwise rows are logged once per LOG_PERIOD_S.
static void processSample(const Sample &s, bool forceRow)
{
    const uint32_t now = rtcEpoch();
    float dt;
    if (lastSampleMs != 0)
        dt = (millis() - lastSampleMs) / 1000.0f; // continuous sampling (live mode)
    else // first sample after a wake-up/boot: time since the previous sample, capped (a gap is not integrated in full)
        dt = (now > lastEpoch && lastEpoch != 0) ? (float)min<uint32_t>(now - lastEpoch, 2 * LOG_PERIOD_S) : 0.0f;
    lastSampleMs = millis();
    lastEpoch = now;
    if (!recActive)
        return;
    if (s.nSat == 0)
        jPpix += s.ePpix * dt; // saturated samples are invalid

    const int battMv = M5.Power.getBatteryVoltage();
    const char *ev = nullptr;
    if (pendingEvent)
        ev = pendingEvent;
    else if (stopRequested)
        ev = "stop";
    else if (now >= sessionStartEpoch && now - sessionStartEpoch >= REC_MAX_S)
        ev = "auto_12h";
    else if (battMv > 2500 && battMv < BATT_LOW_MV)
        ev = "batt_low";
    else if (forceRow || now == 0 || now - lastRowEpoch >= LOG_PERIOD_S)
        ev = "sample";
    if (!ev)
        return;

    logSessionRow(ev, s, now);
    lastRowEpoch = now;
    pendingEvent = nullptr;
    if (!strcmp(ev, "stop") || !strcmp(ev, "auto_12h") || !strcmp(ev, "batt_low"))
    {
        recActive = false;
        stopRequested = false;
        Serial.printf("Session %u ended (%s), J_ppix = %.3f\n", (unsigned)sessionId, ev, jPpix);
    }
    saveState();
}

// Powers the board down until the next whole-minute row. M5's timerSleep(seconds) arms the RTC countdown timer
// (powers the board back on, on battery) and the ESP32 timer (wakes the deep sleep, on USB). It does not return.
static void sleepUntilNextRow()
{
    saveState();
    auto t = M5Capsule.Rtc.getDateTime();
    int wait = LOG_PERIOD_S - t.time.seconds; // 1..60 s to the next minute boundary
    if (wait < 8)
        wait += LOG_PERIOD_S;                 // leave time for the timer to be armed
    Serial.printf("Sleeping %d s until the next row\n", wait);
    Serial.flush();
    sensor.disable();
    neopixelWrite(LED_PIN, 0, 0, 0);
    M5.Power.timerSleep(wait);
    Serial.println("timerSleep returned (sleep failed); continuing awake");
}

static void startLive()
{
    liveMode = true;
    lastActivityMs = millis();
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    auto touch = []() { lastActivityMs = millis(); };
    server.on("/", [touch]() {
        touch();
        server.sendHeader("Cache-Control", "no-store"); // phones kept showing an old copy of the page after a firmware update
        server.send_P(200, "text/html", INDEX_HTML);
    });
    server.on("/data", [touch]() {
        touch();
        char copy[sizeof(lastJson)];
        xSemaphoreTake(jsonMutex, portMAX_DELAY);
        memcpy(copy, lastJson, sizeof(copy));
        xSemaphoreGive(jsonMutex);
        server.sendHeader("Cache-Control", "no-store");
        server.send(200, "application/json", copy);
    });
    server.on("/log", [touch]() {
        touch();
        xSemaphoreTake(sdMutex, portMAX_DELAY);
        File f = sdOk ? SD.open(LOG_FILE, FILE_READ) : File();
        if (!f)
            server.send(404, "text/plain", "no log");
        else
        {
            server.sendHeader("Content-Disposition", "attachment; filename=lightdx_log.csv");
            server.streamFile(f, "text/csv");
            f.close();
        }
        xSemaphoreGive(sdMutex);
    });
    // "t" = phone time "YYYY-MM-DD HH:MM:SS"; returns true and fills pendingClock if valid.
    auto parseTime = []() -> bool {
        int v[6];
        if (server.hasArg("t") && sscanf(server.arg("t").c_str(), "%d-%d-%d %d:%d:%d", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]) == 6 &&
            v[0] >= 2020 && v[0] < 2100 && v[1] >= 1 && v[1] <= 12 && v[2] >= 1 && v[2] <= 31 && v[3] < 24 && v[4] < 60 && v[5] < 60)
        {
            memcpy(pendingClock, v, sizeof(v));
            return true;
        }
        return false;
    };
    server.on("/settime", [touch, parseTime]() {
        touch();
        if (parseTime())
        {
            pendingClockSet = true;
            server.send(200, "text/plain", "ok");
        }
        else
            server.send(400, "text/plain", "bad time");
    });
    // /rec?cmd=start&t=<phone time>  or  /rec?cmd=stop ; applied in loop() (the RTC and sensor are only touched there)
    server.on("/rec", [touch, parseTime]() {
        touch();
        const String cmd = server.arg("cmd");
        if (cmd == "start")
        {
            if (!parseTime())
            {
                server.send(400, "text/plain", "bad time");
                return;
            }
            pendingClockSet = true; // the start sets the RTC from the phone first
            pendingCmd = 1;
            server.send(200, "text/plain", "ok");
        }
        else if (cmd == "stop")
        {
            pendingCmd = 2;
            server.send(200, "text/plain", "ok");
        }
        else
            server.send(400, "text/plain", "bad cmd");
    });
    server.begin();
    xTaskCreatePinnedToCore(webTask, "web", 8192, nullptr, 1, nullptr, 0);
    Serial.printf("WiFi AP \"%s\" up, open http://%s/\n", AP_SSID, WiFi.softAPIP().toString().c_str());
}

void setup()
{
    auto m5cfg = M5.config();
    m5cfg.internal_spk = false; // we do not use the buzzer or mic; leave G2 and the mic pins alone
    m5cfg.internal_mic = false;
    m5cfg.disable_rtc_irq = false; // keep the RTC wake flag so we can tell a timer wake-up from a button/USB start
    M5Capsule.begin(m5cfg); // also drives the power-hold pin (G46) so the Capsule stays on with USB unplugged
    const bool timerWake = M5Capsule.Rtc.isEnabled() && M5Capsule.Rtc.getIRQstatus();
    if (M5Capsule.Rtc.isEnabled())
        M5Capsule.Rtc.disableIRQ(); // clear the flag (releases the INT line) and cancel any pending timer

    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW); // keep the buzzer silent
    Serial.begin(115200);
    Serial.setTxTimeoutMs(0); // drop output instead of blocking when no USB host is reading

    prefs.begin("lightdx", false);
    loadState();
    liveMode = !(timerWake && recActive); // a timer wake while recording = quiet logging cycle; anything else = live mode

    if (liveMode)
    {
        uint32_t t0 = millis();
        while (!Serial && millis() - t0 < 3000)
            delay(10);
        Serial.println();
        Serial.println("LightDX AS7341 dosimeter (M5Capsule 1.1)");
        Serial.printf("M5Capsule: board=%d, power-hold G46 level=%d, timerWake=%d\n", (int)M5.getBoard(), gpio_get_level(GPIO_NUM_46), timerWake);
        if (M5Capsule.Rtc.isEnabled())
        {
            char dt[24];
            rtcString(dt, sizeof(dt));
            Serial.printf("RTC OK (M5Capsule.Rtc), time now %s\n", dt);
        }
        else
            Serial.println("RTC NOT enabled; log datetime will be NOTSET");
    }
    imuOk = M5.Imu.isEnabled();
    if (liveMode)
        Serial.printf("IMU %s (M5.Imu type %d)\n", imuOk ? "OK" : "NOT enabled (acc columns will be empty)", (int)M5.Imu.getType());
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);
    if (liveMode)
        i2cScan();
    if (!i2cPresent(AS7341_I2C_ADDRESS))
    {
        Serial.println("0x39 not found on SDA=" + String(I2C_SDA) + "/SCL=" + String(I2C_SCL) + ", trying swapped pins");
        Wire.end();
        Wire.begin(I2C_SCL, I2C_SDA);
        Wire.setClock(100000);
        i2cScan();
    }
    if (!i2cPresent(AS7341_I2C_ADDRESS))
    {
        Serial.println("AS7341 not found. Check Grove cable, power and pin defines.");
        if (!liveMode)
            sleepUntilNextRow(); // keep the cycle alive; the missing sensor shows up as no new rows
        while (true)
            delay(1000);
    }

    if (!sensor.begin())
    {
        Serial.println("AS7341 init failed (ID check).");
        if (!liveMode)
            sleepUntilNextRow();
        while (true)
            delay(1000);
    }
    sensor.setMeasureMode(AS7341_MODE_SPM);
    sensor.setATime(SENSOR_ATIME);
    sensor.setAStep(SENSOR_ASTEP);
    sensor.setGain(gainCode);
    if (liveMode)
    {
        Serial.printf("AS7341 initialized. tint=%.1f ms, start gain=%gx\n", sensor.getIntegrationTime(), GAIN_FACTOR[gainCode]);
        Serial.println("cnt_* = raw / (tint_ms * gain) * correctionGain  [counts per ms per unit gain]");
        printHeader();
    }

    jsonMutex = xSemaphoreCreateMutex();
    sdMutex = xSemaphoreCreateMutex();
    sdSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
    sdOk = SD.begin(SD_CS, sdSPI, 20000000);
    sdArchiveOldFormat();
    if (sdOk)
    {
        sdUpdateSpace();
        if (liveMode)
            Serial.printf("SD card OK: %llu MB, type %d, %u MB free\n", SD.cardSize() / (1024 * 1024), SD.cardType(), (unsigned)sdFreeMB);
    }
    else
        Serial.println("SD card NOT found/mountable (FAT32 formatted? card seated?)");

    if (!liveMode)
    {
        // Quiet logging cycle: one reading, one row, back to sleep (WiFi is never started).
        Sample s;
        takeSample(s, false);
        processSample(s, true);
        if (recActive)
            sleepUntilNextRow(); // does not return
        // The session ended in this wake-up (12 h limit or low battery): fall through to live mode so the data can be fetched.
        liveMode = true;
    }
    else if (recActive)
        pendingEvent = "resume"; // a session was recording when the board was (re)started in live mode

    startLive();
}

void loop()
{
    uint32_t start = millis();

    // Requests from the web page, handled here because the RTC and sensor are only touched from this task.
    if (pendingClockSet)
    {
        setRtc(pendingClock[0], pendingClock[1], pendingClock[2], pendingClock[3], pendingClock[4], pendingClock[5]);
        pendingClockSet = false;
        char dtn[24];
        rtcString(dtn, sizeof(dtn));
        Serial.printf("RTC set from web page, time now %s\n", dtn);
    }
    if (pendingCmd == 1)
    {
        pendingCmd = 0;
        startSession();
    }
    else if (pendingCmd == 2)
    {
        pendingCmd = 0;
        if (recActive)
            stopRequested = true;
    }

    Sample s;
    takeSample(s, true);
    processSample(s, false);
    const uint32_t nowMs = millis();

    Serial.printf("%lu,%g,%.1f,%u,%d", (unsigned long)nowMs, GAIN_FACTOR[gainCode], s.tintMs, flickerHz, s.nSat);
    for (int i = 0; i < CH_COUNT; i++)
        Serial.printf(",%u", s.raw[i]);
    for (int i = 0; i < CH_COUNT; i++)
        Serial.printf(",%.5f", s.cnt[i]);
    Serial.printf(",%.5f,%.5f,%.5f\n", s.ePpix, jPpix, s.lux);

    char nowStr[24];
    rtcString(nowStr, sizeof(nowStr));
    const int battMv = M5.Power.getBatteryVoltage();
    const int battPct = M5.Power.getBatteryLevel();
    const uint32_t elapsed = (recActive && lastEpoch >= sessionStartEpoch) ? lastEpoch - sessionStartEpoch : 0;
    char json[sizeof(lastJson)];
    int n = snprintf(json, sizeof(json),
                     "{\"ms\":%lu,\"gain\":%g,\"tint_ms\":%.1f,\"flicker_hz\":%u,\"n_sat\":%d,"
                     "\"e_ppix\":%.5f,\"j_ppix\":%.5f,\"lux\":%.5f,\"dt\":\"%s\",\"batt_mv\":%d,\"batt_pct\":%d,\"sd_free_mb\":%u,\"sd_total_mb\":%u,"
                     "\"rec\":%d,\"sid\":%u,\"el\":%u,\"mx\":%lu,\"cnt\":[",
                     (unsigned long)nowMs, GAIN_FACTOR[gainCode], s.tintMs, flickerHz, s.nSat, s.ePpix, jPpix, s.lux, nowStr, battMv, battPct,
                     (unsigned)sdFreeMB, (unsigned)sdTotalMB, recActive ? 1 : 0, (unsigned)sessionId, (unsigned)elapsed, (unsigned long)REC_MAX_S);
    for (int i = 0; i < CH_COUNT && n > 0 && n < (int)sizeof(json); i++)
        n += snprintf(json + n, sizeof(json) - n, "%s%.5f", i ? "," : "", s.cnt[i]);
    if (n > 0 && n < (int)sizeof(json) - 3)
    {
        snprintf(json + n, sizeof(json) - n, "]}");
        xSemaphoreTake(jsonMutex, portMAX_DELAY);
        memcpy(lastJson, json, sizeof(lastJson));
        xSemaphoreGive(jsonMutex);
    }

    // RGB LED: dim red while a session is recording (live mode only; off in the sleep cycle to save power).
    neopixelWrite(LED_PIN, recActive ? 24 : 0, 0, 0);

    while (Serial.available())
    {
        lastActivityMs = millis();
        int c = Serial.read();
        if (c == 'd')
            dumpLog();
        else if (c == 'b') // test helper: start a session from the serial port (uses the RTC as it is)
            pendingCmd = 1;
        else if (c == 'x') // test helper: stop the session
            pendingCmd = 2;
        else if (c == 'l' && sdOk) // list the files on the SD card
        {
            xSemaphoreTake(sdMutex, portMAX_DELAY);
            File root = SD.open("/");
            for (File f = root.openNextFile(); f; f = root.openNextFile())
                Serial.printf("SD file: %s (%u bytes)\n", f.name(), (unsigned)f.size());
            xSemaphoreGive(sdMutex);
        }
        else if (c == 't')
        {
            String line = Serial.readStringUntil('\n');
            int y, mo, d, h, mi, sec;
            if (M5Capsule.Rtc.isEnabled() && sscanf(line.c_str(), " %d-%d-%d %d:%d:%d", &y, &mo, &d, &h, &mi, &sec) == 6 &&
                y >= 2020 && y < 2100 && mo >= 1 && mo <= 12 && d >= 1 && d <= 31 && h < 24 && mi < 60 && sec < 60)
            {
                setRtc(y, mo, d, h, mi, sec);
                char dt[24];
                rtcString(dt, sizeof(dt));
                Serial.printf("RTC set, time now %s\n", dt);
            }
            else
                Serial.println("RTC set failed. Usage: t YYYY-MM-DD HH:MM:SS");
        }
        else if (c == 'e' && sdOk)
        {
            xSemaphoreTake(sdMutex, portMAX_DELAY);
            SD.remove(LOG_FILE);
            xSemaphoreGive(sdMutex);
            Serial.println("SD: log erased");
        }
    }

    // A recording session with nobody using the page (no web request or serial input) goes back to the one-row-per-minute sleep cycle.
    // (The Serial object reads as "connected" even after the PC closes the port, so it cannot be used as an activity signal.)
    if (recActive && millis() - lastActivityMs > LIVE_IDLE_TIMEOUT_MS)
        sleepUntilNextRow();

    sampleCount++;
    uint32_t elapsedMs = millis() - start;
    if (elapsedMs < SAMPLE_PERIOD_MS)
        delay(SAMPLE_PERIOD_MS - elapsedMs);
}
