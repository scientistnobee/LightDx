# Capsule serial test (AS7341 on M5Capsule 1.1 / Stamp-S3A)

Prints all AS7341 channels (F1-F8, Clear, NIR, plus flicker Hz) as CSV at 115200 baud, with auto-gain.

## Wiring
**Power the Adafruit board's Vin from 3.3 V (Capsule header P1 pin 4), NOT from the Grove 5 V:** its
SDA/SCL pull-ups go to Vin, which would put 5 V on the ESP32-S3 pins.
Adafruit AS7341 -> Capsule: SDA = G13, SCL = G15 (Port A), GND, Vin = 3V3 (per the Capsule v1.1 pinmap sticker; the
sketch retries with SDA/SCL swapped if 0x39 isn't found, and prints an I2C scan at startup).

## Build / flash (arduino-cli)
    arduino-cli compile --fqbn esp32:esp32:m5stack_stamp_s3:CDCOnBoot=cdc .
    arduino-cli upload  --fqbn esp32:esp32:m5stack_stamp_s3:CDCOnBoot=cdc -p COMx .
    arduino-cli monitor -p COMx -c baudrate=115200
If upload can't connect, hold the Stamp's G0 button while plugging in USB.
In the Arduino IDE: board "M5StampS3", USB CDC On Boot "Enabled".

## WiFi live view
The Capsule runs a WiFi access point: SSID `LightDX`, password `lightdx123` (edit `AP_SSID`/`AP_PASS`).
Join it from a phone/PC and open `http://192.168.4.1/` for a live 8-band bar chart (F1-F8) plus E_ppix,
J_ppix, lux, gain/tint, flicker and saturation. `http://192.168.4.1/data` returns the latest sample as JSON.
Serial CSV output is unchanged. The page refreshes once per sample (~1 s). No internet is needed or provided.

## Output columns
`ms, gain_x, tint_ms, flicker_hz, n_sat, raw_<ch> x10, cnt_<ch> x10`
- `raw_*`: ADC counts at the current gain. `n_sat`: channels at full scale (reading invalid).
- `cnt_*` = raw / (tint_ms * gain) * correctionGain[gain]  (gain-independent, comparable across gains).
- `flicker_hz`: 0 = none/unknown, 100 or 120 Hz; refreshed every 10th sample.

## Notes
- ATIME=0, ASTEP=65466 (~182 ms per pass); gain is the only range control (AGC, 0.5x-512x, starts 16x).
- AGC: any channel at full scale -> gain down; any channel <= 10000 -> gain up (never to a gain that
  already saturated). Approach from Non-Invasive-Bioelectronics-Lab/Wearable_Light_Sensor_Public (MIT).
- `CORRECTION_GAIN` is that lab's calibration of their sensor; unverified for this one.
- The AS7341 onboard LED is never enabled (ambient-light measurement).
- `AS7341.h/.cpp` are copied unchanged from Pocket-Spectrometer-V2 (m5-atom-lite-arduino).
