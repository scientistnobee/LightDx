// LightDX - AS7341 serial test for M5Capsule 1.1 (Stamp-S3A / ESP32-S3)
//
// Reads the Adafruit AS7341 over I2C with auto-gain and prints all channels as CSV over USB serial.
// Uses the local AS7341 driver (copied from Pocket-Spectrometer-V2, m5-atom-lite-arduino).
// Gain/AGC approach follows Non-Invasive-Bioelectronics-Lab/Wearable_Light_Sensor_Public (MIT).
//
// Ambient-light measurement: the AS7341 onboard LED is never switched on.

#include <Wire.h>
#include <M5Capsule.h> // official M5Stack library: power hold (G46), BM8563 RTC (M5Capsule.Rtc), BMI270 (M5.Imu)
#include "AS7341.h"

// ---- Pins (Capsule v1.1 pinmap sticker: PORT.A = G13 yellow/SDA, G15 white/SCL; buzzer = G2) ----
// setup() retries with SDA/SCL swapped if 0x39 isn't found.
#define I2C_SDA 13
#define I2C_SCL 15
#define BUZZER_PIN 2

// ---- Sensor configuration ----
// Long fixed integration time, so gain is the only range knob.
// tint = (ATIME+1)*(ASTEP+1)*2.78 us = ~50 ms per pass (was 65466 -> ~182 ms).
#define SENSOR_ATIME 0
#define SENSOR_ASTEP 17999

#define GAIN_MAX_CODE 10      // 0..10 = 0.5x..512x
#define GAIN_START_CODE 5     // 16x
#define AGC_MAX_ITERATIONS 8
#define LOW_FRACTION 0.15f    // a channel below this fraction of full scale -> try more gain
#define FLICKER_EVERY_N 30    // run flicker detection every N samples (0 = never)
#define SAMPLE_PERIOD_MS 0     // back-to-back: rate = sensor read time (~0.4 s)

// Gain code -> factor, and the per-gain correction table from the Bioelectronics Lab wearable.
// NOTE: correctionGain is that lab's calibration of their own sensor; unverified for this one.
static const float GAIN_FACTOR[11] = {0.5f, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512};
static const float CORRECTION_GAIN[11] = {1.06f, 1.05f, 1.05f, 1.05f, 1.02f, 1.02f, 1.01f, 1.00f, 1.00f, 0.99f, 0.96f};

// Channel order in all arrays below.
enum { CH_F1, CH_F2, CH_F3, CH_F4, CH_F5, CH_F6, CH_F7, CH_F8, CH_CLEAR, CH_NIR, CH_COUNT };
static const char *CH_NAME[CH_COUNT] = {"F1_415", "F2_445", "F3_480", "F4_515", "F5_555",
                                        "F6_590", "F7_630", "F8_680", "Clear", "NIR"};

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

// Serves web clients on their own task: sensor reads block for ~1 s and would starve handleClient().
static void webTask(void *)
{
    for (;;)
    {
        server.handleClient();
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}

// ---- SD logging: one CSV row per minute (Capsule v1.1 SD: CS G11, MOSI G12, MISO G39, SCK G14) ----
// Serial command 'd' dumps the log, 'e' erases it; the web page also serves it at /log.
#include <SPI.h>
#include <SD.h>
#define SD_CS 11
#define SD_MOSI 12
#define SD_MISO 39
#define SD_SCK 14
#define LOG_PERIOD_MS 60000
#define LOG_FILE "/lightdx_log.csv"
SPIClass sdSPI(FSPI);
static bool sdOk = false;
static SemaphoreHandle_t sdMutex;
static uint32_t lastLogMs = 0;
static bool logWrittenOnce = false;

AS7341 sensor(Wire);
float jPpix = 0;            // accumulated index x seconds (arbitrary units until K_SCALE is calibrated)
uint32_t lastSampleMs = 0;
uint8_t gainCode = GAIN_START_CODE;
uint32_t sampleCount = 0;
uint16_t flickerHz = 0;

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

// ---- RTC (BM8563) and IMU (BMI270) come from the official M5Capsule / M5Unified libraries ----
// Set the clock with the serial command "t YYYY-MM-DD HH:MM:SS" (local time).
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

static uint32_t sdTotalMB = 0, sdFreeMB = 0;
static void sdUpdateSpace()
{
    if (!sdOk)
        return;
    uint64_t total = SD.totalBytes(), used = SD.usedBytes();
    sdTotalMB = total / 1048576ULL;
    sdFreeMB = total > used ? (total - used) / 1048576ULL : 0;
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
        {
            f.print("datetime,ms,gain_x,tint_ms,flicker_hz,n_sat");
            for (int i = 0; i < CH_COUNT; i++)
                f.printf(",cnt_%s", CH_NAME[i]);
            f.println(",E_ppix,J_ppix,lux,acc_x_g,acc_y_g,acc_z_g,tilt_deg,batt_mv");
        }
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

void setup()
{
    auto m5cfg = M5.config();
    m5cfg.internal_spk = false; // we do not use the buzzer or mic; leave G2 and the mic pins alone
    m5cfg.internal_mic = false;
    M5Capsule.begin(m5cfg); // also drives the power-hold pin (G46) so the Capsule stays on with USB unplugged
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW); // keep the buzzer silent
    Serial.begin(115200);
    Serial.setTxTimeoutMs(0); // drop output instead of blocking when no USB host is reading
    uint32_t t0 = millis();
    while (!Serial && millis() - t0 < 3000)
        delay(10);
    Serial.println();
    Serial.println("LightDX AS7341 serial test (M5Capsule 1.1)");

    Serial.printf("M5Capsule: board=%d, power-hold G46 level=%d\n", (int)M5.getBoard(), gpio_get_level(GPIO_NUM_46));
    if (M5Capsule.Rtc.isEnabled())
    {
        char dt[24];
        rtcString(dt, sizeof(dt));
        Serial.printf("RTC OK (M5Capsule.Rtc), time now %s\n", dt);
    }
    else
        Serial.println("RTC NOT enabled; log datetime will be NOTSET");
    imuOk = M5.Imu.isEnabled();
    Serial.printf("IMU %s (M5.Imu type %d)\n", imuOk ? "OK" : "NOT enabled (acc columns will be empty)", (int)M5.Imu.getType());
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);
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
        while (true)
            delay(1000);
    }

    if (!sensor.begin())
    {
        Serial.println("AS7341 init failed (ID check).");
        while (true)
            delay(1000);
    }
    sensor.setMeasureMode(AS7341_MODE_SPM);
    sensor.setATime(SENSOR_ATIME);
    sensor.setAStep(SENSOR_ASTEP);
    sensor.setGain(gainCode);
    Serial.printf("AS7341 initialized. tint=%.1f ms, start gain=%gx\n", sensor.getIntegrationTime(), GAIN_FACTOR[gainCode]);
    Serial.println("cnt_* = raw / (tint_ms * gain) * correctionGain  [counts per ms per unit gain]");
    printHeader();

    jsonMutex = xSemaphoreCreateMutex();
    sdMutex = xSemaphoreCreateMutex();
    sdSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
    sdOk = SD.begin(SD_CS, sdSPI, 20000000);
    if (sdOk && SD.exists(LOG_FILE))
    {
        File old = SD.open(LOG_FILE, FILE_READ);
        String first = old.readStringUntil('\n');
        old.close();
        if (!first.endsWith(",batt_mv") && !first.endsWith(",batt_mv\r"))
        {
            SD.remove("/lightdx_log_prev.csv");
            SD.rename(LOG_FILE, "/lightdx_log_prev.csv");
            Serial.println("SD: old-format log kept as /lightdx_log_prev.csv");
        }
    }
    if (sdOk)
    {
        uint32_t t0 = millis();
        sdUpdateSpace();
        Serial.printf("SD space: %u MB free of %u MB (scan took %lu ms)\n", (unsigned)sdFreeMB, (unsigned)sdTotalMB, (unsigned long)(millis() - t0));
    }
    if (sdOk)
        Serial.printf("SD card OK: %llu MB, type %d\n", SD.cardSize() / (1024 * 1024), SD.cardType());
    else
        Serial.println("SD card NOT found/mountable (FAT32 formatted? card seated?)");
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    server.on("/", []() {
        server.sendHeader("Cache-Control", "no-store"); // phones kept showing an old copy of the page after a firmware update
        server.send_P(200, "text/html", INDEX_HTML);
    });
    server.on("/data", []() {
        char copy[sizeof(lastJson)];
        xSemaphoreTake(jsonMutex, portMAX_DELAY);
        memcpy(copy, lastJson, sizeof(copy));
        xSemaphoreGive(jsonMutex);
        server.sendHeader("Cache-Control", "no-store");
        server.send(200, "application/json", copy);
    });
    server.on("/log", []() {
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
    server.on("/settime", []() {
        int v[6];
        if (server.hasArg("t") && sscanf(server.arg("t").c_str(), "%d-%d-%d %d:%d:%d", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]) == 6 &&
            v[0] >= 2020 && v[0] < 2100 && v[1] >= 1 && v[1] <= 12 && v[2] >= 1 && v[2] <= 31 && v[3] < 24 && v[4] < 60 && v[5] < 60)
        {
            memcpy(pendingClock, v, sizeof(v));
            pendingClockSet = true;
            server.send(200, "text/plain", "ok");
        }
        else
            server.send(400, "text/plain", "bad time");
    });
    server.begin();
    xTaskCreatePinnedToCore(webTask, "web", 8192, nullptr, 1, nullptr, 0);
    Serial.printf("WiFi AP \"%s\" up, open http://%s/\n", AP_SSID, WiFi.softAPIP().toString().c_str());
}

void loop()
{
    uint32_t start = millis();

    uint16_t raw[CH_COUNT];
    readWithAgc(raw);

    if (FLICKER_EVERY_N > 0 && sampleCount % FLICKER_EVERY_N == 0)
        flickerHz = sensor.getFlickerFrequency(); // 0 = none/unknown, 100 or 120 Hz

    const float tintMs = sensor.getIntegrationTime();
    const uint32_t fullScale = min<uint32_t>(65535, (uint32_t)(SENSOR_ATIME + 1) * (SENSOR_ASTEP + 1));
    int nSat = 0;
    for (int i = 0; i < CH_COUNT; i++)
        if (raw[i] >= fullScale)
            nSat++;

    float cnt[CH_COUNT];
    for (int i = 0; i < CH_COUNT; i++)
        cnt[i] = raw[i] / (tintMs * GAIN_FACTOR[gainCode]) * CORRECTION_GAIN[gainCode];

    // PpIX-weighted index: weighted sum of F1-F8 (weights from analysis/ppix_weights.py).
    float ePpix = 0;
    for (int i = 0; i < 8; i++)
        ePpix += W_PPIX[i] * cnt[CH_F1 + i];
    ePpix *= K_SCALE;
    float lux = 0;
    for (int i = 0; i < 8; i++)
        lux += W_LUX[i] * cnt[CH_F1 + i];
    lux *= LUX_K;
    // Integrate over the real time since the previous sample; skip saturated samples (invalid).
    uint32_t nowMs = millis();
    if (lastSampleMs != 0 && nSat == 0)
        jPpix += ePpix * (nowMs - lastSampleMs) / 1000.0f;
    lastSampleMs = nowMs;

    Serial.printf("%lu,%g,%.1f,%u,%d", (unsigned long)nowMs, GAIN_FACTOR[gainCode], tintMs, flickerHz, nSat);
    for (int i = 0; i < CH_COUNT; i++)
        Serial.printf(",%u", raw[i]);
    for (int i = 0; i < CH_COUNT; i++)
        Serial.printf(",%.5f", cnt[i]);
    Serial.printf(",%.5f,%.5f,%.5f\n", ePpix, jPpix, lux);

    char nowStr[24];
    rtcString(nowStr, sizeof(nowStr));
    const int battMv = M5.Power.getBatteryVoltage();
    const int battPct = M5.Power.getBatteryLevel();
    char json[sizeof(lastJson)];
    int n = snprintf(json, sizeof(json),
                     "{\"ms\":%lu,\"gain\":%g,\"tint_ms\":%.1f,\"flicker_hz\":%u,\"n_sat\":%d,"
                     "\"e_ppix\":%.5f,\"j_ppix\":%.5f,\"lux\":%.5f,\"dt\":\"%s\",\"batt_mv\":%d,\"batt_pct\":%d,\"sd_free_mb\":%u,\"sd_total_mb\":%u,\"cnt\":[",
                     (unsigned long)nowMs, GAIN_FACTOR[gainCode], tintMs, flickerHz, nSat, ePpix, jPpix, lux, nowStr, battMv, battPct, (unsigned)sdFreeMB, (unsigned)sdTotalMB);
    for (int i = 0; i < CH_COUNT && n > 0 && n < (int)sizeof(json); i++)
        n += snprintf(json + n, sizeof(json) - n, "%s%.5f", i ? "," : "", cnt[i]);
    if (n > 0 && n < (int)sizeof(json) - 3)
    {
        snprintf(json + n, sizeof(json) - n, "]}");
        xSemaphoreTake(jsonMutex, portMAX_DELAY);
        memcpy(lastJson, json, sizeof(lastJson));
        xSemaphoreGive(jsonMutex);
    }

    if (!logWrittenOnce || nowMs - lastLogMs >= LOG_PERIOD_MS)
    {
        char row[400];
        char dt[24];
        rtcString(dt, sizeof(dt));
        int m = snprintf(row, sizeof(row), "%s,%lu,%g,%.1f,%u,%d", dt, (unsigned long)nowMs, GAIN_FACTOR[gainCode], tintMs, flickerHz, nSat);
        for (int i = 0; i < CH_COUNT; i++)
            m += snprintf(row + m, sizeof(row) - m, ",%.5f", cnt[i]);
        m += snprintf(row + m, sizeof(row) - m, ",%.5f,%.5f,%.5f", ePpix, jPpix, lux);
        // Accelerometer snapshot (g); tilt = angle between sensor Z axis and gravity (0 = flat, face up).
        float ax, ay, az;
        if (imuOk && M5.Imu.getAccel(&ax, &ay, &az))
        {
            float mag = sqrtf(ax * ax + ay * ay + az * az);
            float tilt = mag > 0.1f ? acosf(constrain(az / mag, -1.0f, 1.0f)) * 57.29578f : NAN;
            snprintf(row + m, sizeof(row) - m, ",%.4f,%.4f,%.4f,%.1f,%d", ax, ay, az, tilt, battMv);
        }
        else
            snprintf(row + m, sizeof(row) - m, ",,,,,%d", battMv);
        logRow(row);
        lastLogMs = nowMs;
        logWrittenOnce = true;
    }
    if (pendingClockSet)
    {
        m5::rtc_datetime_t t;
        t.date.year = pendingClock[0]; t.date.month = pendingClock[1]; t.date.date = pendingClock[2];
        t.time.hours = pendingClock[3]; t.time.minutes = pendingClock[4]; t.time.seconds = pendingClock[5];
        M5Capsule.Rtc.setDateTime(t);
        pendingClockSet = false;
        char dtn[24];
        rtcString(dtn, sizeof(dtn));
        Serial.printf("RTC set from web page, time now %s\n", dtn);
    }
    while (Serial.available())
    {
        int c = Serial.read();
        if (c == 'd')
            dumpLog();
        else if (c == 't')
        {
            String line = Serial.readStringUntil('\n');
            int y, mo, d, h, mi, sec;
            if (M5Capsule.Rtc.isEnabled() && sscanf(line.c_str(), " %d-%d-%d %d:%d:%d", &y, &mo, &d, &h, &mi, &sec) == 6 &&
                y >= 2020 && y < 2100 && mo >= 1 && mo <= 12 && d >= 1 && d <= 31 && h < 24 && mi < 60 && sec < 60)
            {
                m5::rtc_datetime_t t;
                t.date.year = y; t.date.month = mo; t.date.date = d;
                t.time.hours = h; t.time.minutes = mi; t.time.seconds = sec;
                M5Capsule.Rtc.setDateTime(t);
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

    sampleCount++;
    uint32_t elapsed = millis() - start;
    if (elapsed < SAMPLE_PERIOD_MS)
        delay(SAMPLE_PERIOD_MS - elapsed);
}
