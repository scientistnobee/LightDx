# LightDx / M5 Spectrometer Sensor Enclosure — Project Learnings

Reference notes for making future small changes without re-deriving everything.
Written 2026-09-07.

## What this project is

An AS7341 spectral sensor PCB + M5StickC Plus, pulled out of an existing
cuvette-holder assembly and re-housed into an M5Capsule enclosure, with a
custom-designed bottom cover that holds the PCB, lets light in through a
diffuser disk, and screws onto the capsule.

## File map

| File | Purpose |
|---|---|
| `m5spectrometer_cuvette.FCStd` | **Source** assembly the PCB/M5Stick parts were copied from. Original project, not modified. |
| `Capsule_v1.1.stl` | M5Stack K129 Capsule structure, downloaded from `github.com/m5stack/M5_Hardware`. |
| `Reused_Parts.FCStd` | **Main working document.** Everything below lives here. |
| `disk_measures.txt` | OpenSCAD reference script for the white diffuser disk + retaining rim/hood — dimensions, not the enclosure itself. |
| `build_sensor_enclosure.py` | **Parametric build script** for `Sensor_Enclosure`. This is the actual source of truth for the enclosure's geometry — see "How to make changes" below. |
| `screws.png` | Reference frame from an M5Capsule product video, confirms which capsule holes are real M3 inserts vs. magnets. |

## Objects in Reused_Parts.FCStd

- **`PCB_Component`** (App::Part) — the AS7341 sensor board, copied recursively
  from the source doc. Contains the AS7341 die as a nested sub-part, plus
  passives, LEDs, connectors, board outline.
- **`M5StickC_Plus_v2`** (App::Part) — M5StickC Plus enclosure, copied
  alongside the PCB. Currently **hidden** (`Visibility = False`), not deleted.
- **`Capsule_v1_1`** (App::Part) — the capsule structure, split from the
  single-mesh STL into 3 named sub-meshes (`Capsule_Body`, `Capsule_Lid`,
  `Capsule_EndCap`) that assemble correctly using their native relative
  offsets. The STL actually contained a *duplicate* set of all 3 shells
  offset far in -X (probably a print-bed layout artifact) — that duplicate
  set was discarded.
- **`Sensor_Enclosure`** (Part::Feature) — the custom-designed bottom cover.
  **Not parametric in FreeCAD** (frozen BRep, no feature tree). Rebuilt via
  `build_sensor_enclosure.py`.

## Key measurements / findings (don't re-derive these)

- **AS7341 optical aperture position — CORRECTED, was wrong**: originally
  computed as world `(-1.99, 0, -2.545)` from a tiny (0.9×0.9mm) sub-feature
  inside the AS7341 CAD part (literally labeled "AS7341", found via a small
  cylindrical bore at local `(12.7, 7.9, 2.545)`, mapped to world via
  `pcb.getGlobalPlacement()`). **A physical print showed this feature is
  inaccurate** — real imported-component 3D models often get small cosmetic
  details like an optical window wrong even when pins/pads are correct. A
  test print + reference photo (`IMG_0550.jpeg`, the bare Adafruit AS7341
  board) confirmed via direct user measurement: the real chip is centered
  along the board's length (Y — unchanged) but was off-center across the
  board's width (X) by ~2mm. **Current value: `aperture_xy = (0.0, 0.0)`**
  — centered on the PCB, set empirically from the physical part, not
  re-derived from the CAD sub-feature. If more correction is ever needed
  again, trust another physical test print over the CAD feature.
  **Gotcha** (still valid, just don't over-trust the endpoint): a nested
  `App::Part` child's `.Shape`/`.Placement` does *not* include the parent's
  transform — use `obj.getGlobalPlacement()` composed with the sub-part's
  local face coordinates to get a world position at all; the sub-part's own
  `Placement.Base` is not its physical location, just its local origin.
- **PCB footprint**: 17.78 × 25.4 × 4.53mm thick.
- **PCB's own 4 corner mounting holes**: world `(±6.35, ±10.16)` relative to
  PCB center, ⌀5.08mm counterbore / ⌀2.5mm through. These double as the
  enclosure's PCB-retaining holes.
- **PCB orientation**: flipped 180° so the AS7341 aperture faces **−Z (down)**
  — sensor receives light from below the capsule. PCB hangs just below the
  capsule's bottom face (its top surface flush at Z=0), not embedded inside.
- **JST connectors**: two `JST_SH` connectors at the PCB's Y-extremes
  (world Y ≈ ±12.7), X range −4 to 2. They sit right at the pocket's end
  walls — needed dedicated cable-access slots cut through the enclosure.
- **Capsule corner radius**: measured directly from the mesh via
  `mesh.crossSections()` at several Z heights → consistently **3.0mm**. (First
  guess of 6mm was wrong and visibly mismatched the capsule's real edges.)
- **Capsule bottom holes**: found 10 hole-like features on the capsule mesh
  (2 columns at X=±8, 5 rows each at Y = −16,−8,0,8,16, 8mm pitch) using
  `mesh.foraminate()` raycasting. **Only 2 of these are real M3 threaded
  inserts** — both at `(±8, 16)`, measured bore ⌀4.0–4.2mm. The other 8 are
  smaller (⌀2.6mm) and turned out to be a mix of assembly holes and the
  capsule's 4 magnet recesses (confirmed against `screws.png`, which labels
  them "MAGNET × 4" and "M3 螺丝安装孔位"). Don't add screw holes at the other
  8 positions.

## Sensor_Enclosure design summary

- Outer shell: 24×40mm rounded rectangle (fillet 3mm, matches capsule),
  7.1mm thick, sits flush against the capsule's bottom (Z=0).
- PCB pocket: 18×25.6×4.6mm deep, captures the PCB with clearance.
- 4 PCB-corner holes + counterbore (reused from the PCB's own pattern).
- 2 M3 holes + counterbore, only at the capsule's real insert locations.
- Stepped center aperture aligned to the true AS7341 position: ⌀12.2mm seat
  (1.5mm deep) for a white diffuser disk to drop into, narrowing to a ⌀10mm
  shoulder bore (1.0mm) that acts as both retaining lip and light path.
- Raised collar ("rim") fused around the aperture on the exterior face
  (⌀18mm outer / ⌀16.5mm inner / 2mm tall) — blocks off-axis stray light,
  PAR-sensor cosine-corrector style. Matches `disk_measures.txt`'s `rim()`
  module.
- Two JST cable-access slots cut through the pocket's end walls.

## How to make small changes

`Sensor_Enclosure` is a static `Part::Feature` — there's no FreeCAD feature
tree to edit. To change a dimension:

1. Open `build_sensor_enclosure.py` — every dimension is a named variable in
   the `PARAMETERS` section at the top, with a comment explaining it.
2. Edit the value(s) you want to change.
3. Run the script inside FreeCAD with `Reused_Parts.FCStd` open (Macro >
   Execute, or paste into the Python console, or ask Claude to run it via
   the FreeCAD MCP tools). It calls `build_and_apply()`, which rebuilds the
   whole shape from scratch and replaces `Sensor_Enclosure`'s geometry.
4. Save the document.

If a change affects the diffuser disk or rim specifically, also update
`disk_measures.txt` to keep the two files consistent (they currently share
the same numbers: `seat_radius=6.1`, `disk_radius=6.0`,
`shoulder_inner_radius=5.0`, rim ⌀18/⌀16.5×2mm).

## Open assumptions worth double-checking later

- **Diffuser disk**: assumed 6.0mm radius, 1.5mm thick. Never confirmed
  against a physical part — adjust `disk_radius`/`disk_thickness` in both
  files if the real disk differs.
- **PCB screws**: assumed M2 for the 4 corner holes (based on the PCB's own
  hole diameter), M3 confirmed for the capsule insert holes.
- `Sensor_Enclosure` **has now been printed once** (2026-09-07, exported as
  `Reused_Parts-Sensor Enclosure1.step` — that STEP file is now **stale**,
  it predates the aperture-centering fix AND the counterbore/JST-slot fixes
  below; export a fresh one before the next print). First print surfaced:
  1. the aperture-centering bug, fixed above (`aperture_xy` now `(0,0)`);
  2. the two Y=+10.16 PCB corner holes were only 0.069mm of wall away from
     the nearby M3 hole's counterbore (basically no material) — fixed by
     shrinking `screw_r_cbore` 2.75→2.2mm and `m3_r_cbore` 3.25→3.0mm,
     restoring ~0.87mm of wall there. Still fits M2/M3 SHCS heads with
     margin.
  3. the JST cable slots were too tight in the board-width (X) direction —
     widened by 1mm total, but **only on the +X side** (`jst_x_max`
     2.5→3.5, `jst_x_min` left at -4.5): the -X side only had 0.55mm to the
     nearby PCB hole already, so widening it too would have dropped that to
     ~0.05mm, another near-zero wall. +X had 2.55mm to spare.
  Other clearances (0.1mm disk fit, M2/M3 thread fits) are still
  unconfirmed design estimates pending the next physical test.
- Reference photos from the first print/part inspection: `screws.png`
  (capsule M3/magnet labels), `IMG_0548.jpeg`/`IMG_0549.jpeg` (printed
  enclosure showing the aperture misalignment), `IMG_0550.jpeg` (clean
  top-down shot of the bare Adafruit AS7341 board — useful reference for
  any future component-position questions).
- `M5StickC_Plus_v2` was chosen arbitrarily over a near-duplicate
  `M5StickC_Plus_v001` found in the source file (they looked structurally
  identical). It's currently hidden but still in the document, unused by the
  enclosure design.

## Puck redesign (started 2026-10-02) - flat circular enclosure

Replaces capsule shell + stacked `Sensor_Enclosure` (~25.3 mm tall). Old parts are untouched.
Script: `build_puck_enclosure.py` (same edit-variables-and-rerun workflow as above).
Objects added to `Reused_Parts.FCStd` (doc NOT saved yet): `Puck_Base`, `Puck_Lid`,
`Ref_Battery`, `Ref_Carrier_Stack` (transparent placeholders for clash checks).

- Layout: base = floor + one electronics layer with carrier(+Stamp-S3A) at +Y and
  battery at -Y; lid = AS7341 pocket (sensor faces +Z) + diffuser seat + rim. Ø56 x
  16.6 mm. The light-blocking rim is **switched off** (`rim_enabled = False` in the
  script, for easier printing; set True to restore the Ø18 x 2 mm collar and 18.6 mm
  total height; revisit once diffuser stray-light behaviour is tested). 4 M2 screws (~M2x12) join lid to base, inserted from the
  underside of the base (clearance hole + 2.2 mm counterbore in the base bottom, blind
  5 mm self-tap pilot in the lid underside; lid top is unbroken). Min wall around
  them 1.3 mm.
- **Assumed, not measured**: battery 30x20x5 (502030), carrier outline 30x20,
  carrier+Stamp stack 8 mm, USB-C centre 6 mm above base bottom. First print = fit test.
- Capsule facts (from `K129-V11_Capsule_v1.1_main_pictures_*.webp`, Stamp-S3A size PDF):
  the Stamp-S3A (18x24x4.7) plugs into 2x9 female headers on the carrier; its USB-C is a
  female receptacle at one end, Grove HY2.0-4P on the carrier directly below it. In
  `Capsule_Body` the +Y end wall has the USB-C opening (Z~12.5-15.5) above the Grove
  opening (Z~5.5-10.5). The STL is shell only (cavity ~18-20 x 34 x 13 mm, Z 2-15).
- AS7341 retention (user's design): 4 pillars (r2.0) hang from the lid ceiling to the
  PCB's component face, each with a blind M2 self-tap pilot (r0.9, 4 mm) opening
  downward; screws go UP from the electronics side through the PCB corner holes. Lid
  top has no holes there (flat, light-tight). Verified: no pillar/component clash with
  the real PCB model (frame map: x, -y, base_h - z_old), no lid/board overlap.
- Open items: screw-head clearance under the PCB (low-head M2; unverified over the
  carrier at Y=+10.16), battery-lead slot position vs. real connector, Stamp STL not imported.
- Option to cut ~3 mm more: nest the AS7341 board over the battery (5 mm cell leaves
  slack in the 8 mm layer), at the cost of an off-centre aperture.

### State at end of 2026-10-02 session / how to resume

- `Reused_Parts.FCStd` was **not saved** with the puck objects. Nothing is lost: re-open
  `Reused_Parts.FCStd`, run `build_puck_enclosure.py` (it creates `Puck_Base`, `Puck_Lid`,
  `Ref_Battery`, `Ref_Carrier_Stack`), then save. No STEP exported yet.
- Exported `Puck_Base.stl` and `Puck_Lid.stl` (project folder, assembled positions,
  rim off, first fit-test versions with ASSUMED electronics sizes). Print the lid flipped
  (top face down) so the pillars/pilots point up; print the base as exported.
- Dimensions: puck Ø56 mm; body 16.6 mm (rim off; +2 mm if enabled), vs ~25.3 mm for capsule + old cover
  (capsule shell 16.2 + old enclosure 9.1 incl. rim).
- Earlier mistake corrected: I first read the Stamp-S3A's USB-C as a male plug. It is a
  female receptacle (end-on photo `..._main_pictures_13.webp`). The 12x5 mm opening at Z~6-11
  in the STL's +Y wall is the Grove port, not USB-C.
- Context from `lightdx_memory.md`: the user's LightDX notes recommend the M5StickS3
  (has a display) over the Capsule as the final platform; the Capsule is the prototype,
  so keep the puck parametric. BMI270 IMU gives orientation correction, so keep the
  carrier plane parallel to the AS7341 plane.
- Next steps: (1) measure the real battery and carrier and update the ASSUMED block;
  (2) confirm under-PCB screw-head clearance over the carrier; (3) place the battery-lead
  slot at the real connector; (4) import `Stamp-S3A.stl` (from m5stack/M5_Hardware,
  `Products/S007-V033_Stamp-S3A/Structures`) as a hidden reference and check the USB-C
  slot height; (5) export STEP for a fit-test print.
- Method notes: the capsule STL cavity was mapped by firing `mesh.foraminate` rays
  (returns a dict {facet: (x,y,z)}) in a grid and merging inside/outside intervals;
  port openings were found by probing each end wall the same way. `crossSections` on the
  shell mesh gave hundreds of loose segments and was not useful for the cavity.
  Sources for the Stamp-S3A: docs.m5stack.com/en/core/Stamp-S3A and its size PDF.

## Firmware: AS7341 serial test on the Capsule (started 2026-10-02)

What LightDX actually is: wearable PpIX dosimeter for daylight PDT (see `lightdx_memory.md`).
J_eff = ∫E(λ)·A_norm(λ)dt; no PpIX A_norm data yet, so the firmware does NOT compute dose.

Files: `firmware/capsule_serial_test/` — `capsule_serial_test.ino`, `AS7341.h/.cpp` (copied
unchanged from `scientistnobee/Pocket-Spectrometer-V2`, `Software/m5-atom-lite-arduino`), `README.md`.
Status: **flashed and working** (Capsule on COM8, first run after 2026-10-02): I2C scan finds
0x39, init OK, CSV streams ~1 line/s (flicker detection every 10th sample adds ~0.6 s). In a dim
scene AGC settled at 512x with raw counts 0-58 and no saturation. Still to test: bright light
(AGC step-down, n_sat), flicker_hz under mains LEDs/fluorescents, gain-normalised stability.
Build: `arduino-cli compile --fqbn esp32:esp32:m5stack_stamp_s3:CDCOnBoot=cdc .` (esp32 core
3.3.12 installed; hold BTN0/G0 while plugging USB if upload can't connect).

- **Capsule v1.1 pins** (`K129-V11-pinmap-sticker.jpg`, `Sch_M5Capsule_sch_01.png`): Port A
  Grove = G15 SCL (white), G13 SDA (yellow), 5V OUT, GND. Buzzer G2 (via 470 Ω + transistor),
  IR G4, RGB G21, BtnA/wake G42, BTN0 G0, mic CLK40/DAT41, SD CS11/MOSI12/MISO39/SCK14.
  Internal I2C (BM8563 RTC + BMI270 IMU) is a separate bus: SDA G8, SCL G10. G13/G15 also on P2 header.
- **No I2C pull-ups on the Capsule**; Grove VCC = 5 V (+5VOUT via R1 0 Ω); no 3.3 V on Port A.
  G13/G15 have 3V3-rated ESD diodes (PESDNC2FD3V3B), so bus must stay at 3.3 V. Pull-up voltage is
  set by the Adafruit AS7341 board. **Checked (Adafruit-AS7341-PCB `Adafruit_AS7341.sch`)**: Vin 3-5 V
  -> AP7312 regulator (1.8 V for the chip, 3.3 V spare); SDA/SCL go through a BSS138 level shifter
  (gate at 1.8 V) with 10K pull-ups on the host side to **VCC (= Vin)** and on the chip side to 1.8 V
  (inferred from the 4-pack R3 net connections). So powering it from the Capsule Grove 5 V would pull
  SDA/SCL up to 5 V -> **DON'T**. Power its Vin/VCC from 3.3 V (header P1 pin 4); use Grove only for
  SDA(G13)/SCL(G15) + GND (leave the Grove red wire unconnected / use header 3V3). Adafruit also sells
  an AS7343 board (different chip, ID/SMUX; our driver is AS7341-only) — confirm the chip marking.
- **Sound issue**: the Capsule made noise when first connected. Buzzer is G2, which the I2C code
  never touches; probably the factory firmware (not confirmed). Sketch now drives G2 low at boot.
- **Gain/AGC** (adapted from Non-Invasive-Bioelectronics-Lab/Wearable_Light_Sensor_Public,
  MIT, `Version 2/software_examples/arduino-version/light_sensor/LS.ino`): fixed ATIME=0,
  ASTEP=65466 (~182 ms/pass); gain codes 0..10 = 0.5x..512x, start 16x; saturated (>= full scale)
  -> gain down; any channel <= 10000 -> gain up, never to a gain that saturated. Normalised
  counts = raw/(tint_ms·gain)·correctionGain[gain]. Their `correctionGain` table is THEIR
  sensor calibration, unverified for ours. Their AGC as fetched had no exit when in range
  (possibly lost in summarising); ours has a proper exit and an 8-iteration cap.
- **Bug in the Atom code**: it reports integration time as (ATIME+1)·2.78 ms; correct is
  (ATIME+1)·(ASTEP+1)·2.78 µs (30·600 → ~50 ms, not 83 ms). Driver's `getIntegrationTime()` is right.
- Driver notes: `getSpectralData()` prints debug to Serial — sketch uses `getChannelData(i)`
  instead. Pass F1F4CN gives idx0-3 = F1-F4, 4 = Clear, 5 = NIR; F5F8CN gives idx0-3 = F5-F8.
  `getFlickerFrequency()` returns 0/100/120 Hz (the "11th channel").
- Output = CSV at 115200: `ms,gain_x,tint_ms,flicker_hz,n_sat,raw_x10,cnt_x10`.
- Next: wire Adafruit Vin to 3.3 V, flash/test; logging (web UI/AP now done, see "WiFi live view"); get PpIX A_norm(λ) + AS7341 response data for J_eff;
  IMU orientation correction (BMI270 on G8/G10).

### PpIX-weighted index (started 2026-10-02) — v1, UNCALIBRATED, placeholder inputs
- Method: matched-filter weights, not spectrum reconstruction. `E_ppix = K_SCALE · Σ w_i · cnt_i`
  (i = F1..F8, cnt = gain/tint-normalised counts), `J_ppix = Σ E_ppix·Δt` (skipped when a channel
  is saturated). Weights from `analysis/ppix_weights.py`: stacked NNLS = dose match over CIE
  daylight 4000-15000 K + spectral match of ΣwR to A_norm. Writes
  `firmware/capsule_serial_test/ppix_weights.h`; sketch prints `E_ppix,J_ppix` as the last 2 CSV columns.
- Convention chosen: A_norm = PpIX absorption normalised to 1 at **635 nm** (red-equivalent) —
  **confirm with the lab** that this matches the 8 / 3.5-4 J/cm² thresholds.
- **Inputs are placeholders** (`analysis/data/`): `as7341_response.csv` = Gaussians (FWHM
  26/30/36/39/39/40/50/52 nm assumed from memory, equal peak sensitivity assumed);
  `ppix_absorption.csv` = Gaussians from a peak table. `cie_daylight_basis.csv` is real (colour-science).
  Replace with the ams datasheet responsivity (incl. per-channel absolute sensitivity) and a
  published/lab PpIX spectrum, rerun the script, recompile.
- First result (placeholders, in-model only): weights F1 32.7, F4 3.3, F5 1.9, F7 0.52, F6 0.39,
  F3 0.36, F2 = F8 = 0; daylight error within ±7 % (training and held-out), synthetic lamps up to
  ~19 % (rough lamp models). F1 (415 nm) dominates, i.e. the index leans on the Soret band.
  These errors are model errors only; real sensor error needs real calibration.
- Absolute scale: `K_SCALE = 1` -> arbitrary units. Stop-gap: lux meter + modelled E_eff/lux from a
  D-series SPD (~±10-20 %). Proper: paired spectroradiometer data, refit w (NNLS/ridge, CV).
- Risks: full sun may saturate even at 0.5x with fixed 182 ms (add a tint step to AGC);
  F1 only partly covers the Soret peak (405-410 nm) and nothing below ~380 nm is seen; cosine
  response needs the diffuser (+ IMU later).
- Status: **flashed 2026-10-11** (PpIX + lux columns + WiFi view); serial output verified (AS7341 at
  0x39, CSV ~1 line/s, AP message printed). The Capsule had dropped off COM8; unplug, hold G0 while
  re-plugging USB, and it re-enumerated on COM8 (`arduino-cli board list` to check).

### WiFi live view (added 2026-10-11)
- The Capsule runs a WiFi **access point** (no internet): SSID `LightDX`, password `lightdx123`
  (`AP_SSID`/`AP_PASS` in the sketch). Join it and open `http://192.168.4.1/`.
- Page = live 8-band bar chart (F1-F8, 415-680 nm, bars normalised to the tallest) plus E_ppix, J_ppix,
  lux, gain/tint, flicker, n_sat. Polls `/data` (JSON of the latest sample) once per second. Serial CSV unchanged.
- Files: `firmware/capsule_serial_test/html_content.h` (page, PROGMEM raw string, own code, not the Atom
  repo's UI) and the WebServer code in the `.ino`. `handleClient()` runs in the wait between samples, so
  the page can lag while the sensor is mid-read (a few hundred ms to ~1 s with flicker detection).
- It shows the 8 AS7341 bands, not a continuous spectrum (same as the Pocket Spectrometer's plot).
- **First version failed** on Android and iPhone (AP visible at 91 %, WPA2, from the PC scan). Cause found:
  `handleClient()` was only called in the leftover time of the 1 s loop, and a read cycle takes
  ~0.7-1.0 s, so the server was almost never serviced. Fix (flashed 2026-10-11): web server runs in its
  own FreeRTOS task (core 0); latest JSON handed over under a mutex. **Retest from a phone pending.**
  Phone tips: turn off mobile data, accept "stay connected / no internet", use `http://` not `https://`.
- **Page confirmed working** from a phone after the task fix (2026-10-11). Update rate then felt slow:
  `SAMPLE_PERIOD_MS` was 1000 and the page polled at 1 s. Now `SAMPLE_PERIOD_MS 0`, flicker every 30th
  sample, page polls every 300 ms (no overlapping fetches). Measured sample interval ~0.70 s (~1.4 Hz) —
  limited by two 182 ms integration passes plus driver overhead; faster needs a shorter ATIME/ASTEP
  (less range/SNR) or reading only one pass. J_ppix uses real dt so it is unaffected.
- **Shorter integration tried (2026-10-11):** ASTEP 65466 -> 17999 (tint 182 -> 50 ms). Full scale is now
  18000 counts, so the AGC "too low" test became `LOW_FRACTION 0.15 * fullScale` (the old fixed 10000 would
  have been 55 % of range and pushed gain to saturation). Sample interval 0.70 s -> **0.43 s (2.3 Hz)**:
  only ~0.1 s of that is integration, the other ~0.33 s is driver/I2C/mode-switch overhead, so going
  below 50 ms gains little. Dim room: gain stays at the 512x limit, raw ~100-1600 counts, noise ~±1-2
  counts (stable). cnt_* is normalised by tint so values stay comparable with the 182 ms data, but
  saturation now happens at 3.6x lower light: recheck bright light / daylight (AGC step-down, n_sat).
- **Final state (2026-10-11):** flashed on COM8 and working: serial CSV ~2.3 Hz, WiFi AP `LightDX` /
  `lightdx123`, live page at `http://192.168.4.1/` confirmed from a phone. Settings: ATIME 0, ASTEP 17999
  (50 ms), `SAMPLE_PERIOD_MS 0`, flicker every 30th sample, page polls every 300 ms.
- One report of "no spectra showing" after the 50 ms change; serial showed the sensor loop and AP healthy
  and the user then said it was up again. Cause not found (not reproduced); suspected phone-side stale
  connection / dropped network. If it recurs, note whether bars are blank or numbers freeze, and test
  `/data` directly from a PC joined to the AP.
- Still open: bright light / daylight test at 50 ms (AGC step-down, n_sat); real calibration of
  K_SCALE / LUX_K and PpIX inputs; logging (SD / CSV download); IMU orientation correction. Still arbitrary units
  for E_ppix/J_ppix/lux until K_SCALE/LUX_K are calibrated. No logging yet (no SD/CSV download).

## Useful FreeCAD/MCP techniques learned this session

- Cross-document part reuse: `target_doc.copyObject(source_objs, True)`
  copies objects *and* their full dependency tree between open documents.
- After a cross-doc copy, new objects sometimes don't render until you
  toggle `Visibility` off/on plus a full `doc.recompute(None, True, True)` —
  a known FreeCAD scenegraph refresh quirk.
- For STL/Mesh objects (no BREP faces), use `mesh.getSeparateComponents()` to
  split disconnected shells, `mesh.foraminate(point, dir)` to raycast for
  holes, and `mesh.crossSections([(point, normal)], 0.0)` to get 2D outline
  segments at a given plane (useful for measuring corner radii, hole
  positions, etc. on organic/imported meshes with no parametric history).

## Photos_Caspule (2026-10-02) - reference photos of printed puck + electronics

15 photos in `Photos_Caspule/` (PXL_20261002_*.jpg). What they show:
- Bare M5Capsule board out of its white shell: header rows on both long sides, USB-C at
  one short end, 2-pin JST battery connector + buzzer + button at the other end, SD slot
  on the underside.
- Battery is a ZEC **602025**, 3.7 V, 250 mAh -> nominal 6 x 20 x 25 mm (T x W x L) plus a
  protection-board/tape end. This differs from the 30x20x5 assumed in the puck redesign;
  **measure it with calipers before the next iteration** (esp. the 6 mm thickness).
- A 3D-printed circular puck base (4 screw holes at 90 deg, two rectangular pockets,
  one with a corner notch): battery in one pocket, capsule board and the AS7341
  (Adafruit, STEMMA QT, 4 mounting holes) tried in different orientations/positions.
- Stacked side views (AS7341 under the capsule board, battery alongside) show the real
  stack height and the Qwiic/JST connectors and cable bends that drive it.
- The photos are rough hand shots with no scale reference, so no dimensions were taken
  from them.

## Rectangular box redesign (2026-10-02) - replaces the round puck idea

Why: the Capsule board (40 x 24 x 14 mm bare, measured) did not fit the round base's pocket.
Script: `build_box_enclosure.py` -> `Box_Base`, `Box_Lid`, `Ref_Box_Capsule`, `Ref_Box_Battery`
(new objects; puck objects and `Reused_Parts.FCStd` contents untouched). **Run in FreeCAD (unsaved, in Reused_Parts): both solids valid, 0 clash with the Capsule/battery refs and base vs lid**
(no `freecadcmd` on the MCP machine, so headless runs do not work; use the GUI RPC). Puck objects live in `Puck_round.FCStd`.
- Layout along X: 6.5 end wall | Capsule pocket 40.4 x 24.4 | 1.2 divider | battery pocket
  30.4 x 20.4 | 6.5 end wall -> 85 x 28.4 mm, corner r4. Layer 14.5, floor 1.5, lid 7.1 ->
  **23.1 mm total** (vs 25.3 old; round puck with assumed sizes was 23.7). Only ~2 mm gain: the
  14 mm board sets the height. Real saving needs the AS7341 nested over the battery (6 mm cell
  in a 14.5 mm layer) -> ~18.5 mm; not done because the user likes the lid as is.
- AS7341 lid kept, rotated 90 deg (long axis along X), centred over the battery pocket;
  4 M2 screws up from the underside in the thick end walls at (+-39.25, +-8.5).
- USB-C slot from photo `PXL_20261002_214107806C.jpg` (end-on, scale ~35 px/mm from the 8.9 mm receptacle): centre ~2.5 mm below the sticker face, 11 mm wide, z 11.0 up to the lid. Estimated from a hand-held photo (+-0.5 mm); the capsule goes in sticker-up. Assumed: battery-lead notch at y=+8,
  battery 6 mm thick.
- **Squarish revision (same day)**: pockets now stacked along Y (Capsule +Y, battery -Y, both centred in X)
  -> 53.4 x 50.0 x 23.1 mm instead of 85 x 28.4. Screws stay in the 6.5 mm end walls at
  (+-23.45, -17 / +20.5); lead notch moved to x=+14 in the divider; sensor/aperture centre (0, -12.8).
  Re-run in FreeCAD: valid, no clashes. Same Box_* object names (replaced in place, unsaved).
- **Split Capsule (same day)**: the Capsule's 14.5 mm layer is shared between base and lid. Lid has a
  5.6 mm recess (same XY as the Capsule pocket, 1.5 mm roof + 0.5 headroom = 2.0 mm over the board);
  base is 10.4 mm, lid 7.1 mm -> **17.5 mm total** (was 23.1; old stack 25.3). USB-C plug window 12 x 6.5
  at z 9.75-16.25 is cut through both parts (centre 2.5 mm below the sticker face). Screws: M2x12 still
  reach the lid pilots (head at z=2.2, tip z~14.2, lid starts 10.4). Valid, no clashes in FreeCAD (unsaved).
  Lid now has a deep recess: print it top-face-down as before.

## Box v2 (2026-10-03): shorter, thin lid (after the first rectangular print fitted well)
`build_box_enclosure.py` rewritten (run in FreeCAD, NOT saved/exported yet; v1 STLs are what was printed).
- X length 53.4 -> **44.4 mm** (2 mm end walls around the 40.4 pocket); 44.4 x 50 x 17.5.
- Lid 7.1 -> **2.5 mm plate**, base 10.4 -> 15.0. Total height is still 17.5: it is set by the
  Capsule (floor 1.5 + 14.5 layer + 1.5 roof), so moving the split plane does not reduce it. The
  AS7341 board now sits inside the base pocket (PCB bottom z=10.4, 2.9 mm over the 6 mm cell for
  screw heads), held by 4 posts hanging 3.5 mm below the lid; JST plug slots are cut in the base.
- Screws moved from the end walls to the solid blocks beside the battery pocket, (+-18.7, cell_cy +-7.7):
  M2x14 from below, lid has 4 locating posts (r2, 4 mm) that drop into recesses in the base top and carry
  the blind pilots. All four screws are on the battery half: check the lid at the +Y (Capsule) edge.
- Capsule recess in lid is 1.0 mm (1.5 mm roof above it). Clash checks OK for Capsule, battery, AS7341 envelope.
- **Capsule height 13 mm (user estimate, 2026-10-04)**: the 14 mm included the battery stuck under the board in the
  original; without it the board+headers are ~13 mm (to be confirmed with calipers). `cap_h=13.0` -> total height
  **16.6 mm** (was 17.5): now limited by the sensor stack (floor 1.5 + cell 6 + 2.0 screw-head gap + AS7341 4.6 + lid 2.5)
  rather than the Capsule stack (16.5). Base 14.1, lid 2.5, Capsule recess 0.9 (1.6 roof). Clash checks OK; unsaved.
- **Exports (2026-10-04)**: `Box_Base_v2.stl`, `Box_Lid_v2.stl` (assembled positions; v1 files = what was printed are untouched).
  Drawing sheet `Square_puck_v2_drawings.png/.pdf`: base and lid plans, sections A-A (battery + AS7341), B-B (Capsule + battery),
  C-C (screws/posts), D-D (USB-C window), key dimensions. Generated from slices of the FreeCAD solids, so it matches the STLs.
  `Reused_Parts` FCStd still holds the unsaved v2 model; re-run `build_box_enclosure.py` to regenerate.
- Learnings page: LightDx_enclosure_learnings.html (self-contained, with photos and drawings)
- **SD logging (added + verified 2026-10-11):** Capsule SD slot (CS G11, MOSI G12, MISO G39, SCK G14,
  `SPIClass(FSPI)`, 20 MHz). 30 GB card mounted OK. Appends one CSV row to `/lightdx_log.csv` at boot and
  then every 60 s (`LOG_PERIOD_MS`); header written on file creation. Columns: `ms,gain_x,tint_ms,
  flicker_hz,n_sat,cnt_F1..F8,cnt_Clear,cnt_NIR,E_ppix,J_ppix,lux` (normalised cnt, not raw). Read back
  here: send `d` over serial (dumps the file), `e` erases it; also downloadable at `http://192.168.4.1/log`.
  Verified by dump: header + rows at ms 2934 and 63041 (60.1 s apart), values match the live stream.
  Caveats: `ms` is time since boot (restarts at 0 on every reset, incl. when a serial tool toggles
  DTR/RTS), there is no wall-clock yet (BM8563 RTC on G8/G10 unused); the "file size now N bytes" print
  after a write reads the size before the flush (shows 0/stale), the dump shows the true size. Card is
  opened/closed per write, so pulling it between writes is safe. Needs FAT32 (the 30 GB card worked).
- **RTC timestamps (added + verified 2026-10-11):** BM8563 at 0x51 on the Capsule's internal I2C bus
  (`Wire1`, SDA G8 / SCL G10; the BMI270 shares this bus). Log rows now start with a `datetime` column
  (`YYYY-MM-DD HH:MM:SS`, local time; `NOTSET` if the chip is missing or reports power loss). Serial:
  `t YYYY-MM-DD HH:MM:SS` sets the clock. At boot, if the VL (power-lost) flag is set, it is set from the
  compile time (only approximate). Verified: set from the PC clock, the next logged row read back
  `2026-10-11 03:03:30,62841,...` matching the PC. The old test log was erased because the header changed
  (log format is now `datetime,ms,gain_x,...`). Before I set it, the RTC already held a plausible time
  (~1 min behind the PC), so it was running. **Not yet verified:** that it keeps time across a full
  power-off (does the Capsule's battery back it up when the switch is off / USB unplugged?). `J_ppix`
  still restarts at 0 on every boot; `datetime` + `ms` now make session starts identifiable in the log.
  Gotcha: Arduino auto-prototypes need `struct RtcTime` declared above the first function.
- **Accelerometer in the log (added + verified 2026-10-11):** BMI270 on the internal bus (`Wire1`, 0x68,
  falls back to 0x69). Library: **SparkFun BMI270 Arduino Library 1.0.3** (installed with
  `arduino-cli lib install`; it uploads the BMI270 config blob itself; `beginI2C(addr, Wire1)`,
  `getSensorData()`, `imu.data.accelX/Y/Z` in g). Each minute row now ends with
  `acc_x_g,acc_y_g,acc_z_g,tilt_deg` (single snapshot at log time, not an average; empty fields if the
  IMU is missing). `tilt_deg` = angle between the sensor Z axis and gravity (0 = flat, Z up), i.e. the
  first input for the cosine/orientation correction. Verified row: `0.0725,0.1826,0.9807,11.3`
  (|a| = 1.00 g, tilt 11.3 deg consistent). Gyro not logged. Log erased again (header changed):
  format is now `datetime,ms,gain_x,tint_ms,flicker_hz,n_sat,cnt_F1..F8,Clear,NIR,E_ppix,J_ppix,lux,acc_x_g,acc_y_g,acc_z_g,tilt_deg`.
  Not tested: moving the device (axes signs/orientation vs. the real puck mounting still to be checked).
- **Pins cross-checked against M5Stack's own table (M5Unified `M5Unified.inl`, 2026-10-11):** Capsule internal
  I2C SCL 10 / SDA 8 (RTC + IMU), Port A SCL 15 / SDA 13, SD SCK 14 / MOSI 12 / MISO 39 / CS 11, buzzer 2,
  RGB LED 21, mic 40/41, buttons G42 + G0 - all match what the sketch uses (they also worked on hardware).
  M5Stack also ships the `M5Capsule` library (thin wrapper) which depends on **M5Unified** (has `M5.Rtc`
  and `M5.Imu` drivers); not used - the hand-written RTC code and SparkFun BMI270 library already work.
  **FINDING: POWER_HOLD = GPIO46** for the Capsule. M5Unified drives it high at start ("those boards would
  power off otherwise"). Our sketch never sets G46, so on battery (USB unplugged) the Capsule may power
  off by itself. TODO: `pinMode(46, OUTPUT); digitalWrite(46, HIGH);` at the top of `setup()`, then test
  running from the battery and the RTC across a real power-off. Not done yet.
- **PORTED to the official M5Stack libraries (2026-10-11), supersedes the hand-written RTC/IMU notes above.**
  Libraries (arduino-cli): `M5Capsule` 1.0.1 + `M5Unified` 0.2.25 + `M5GFX` 0.2.32; the SparkFun BMI270
  library is no longer used (can be uninstalled). `setup()` calls `M5Capsule.begin(cfg)` (internal speaker/mic
  disabled in cfg), which auto-detects the board, drives **POWER_HOLD G46 high**, and starts `M5Capsule.Rtc`
  (BM8563) and `M5.Imu` (BMI270). Our code still owns: AS7341 on Arduino `Wire` (G13/G15; M5Unified leaves
  Port A alone unless `external_rtc/imu` is set - its internal bus is I2C port 1, Wire is port 0, no clash),
  SD (SPI), WiFi AP/web server, AGC, PpIX/lux. Serial `t YYYY-MM-DD HH:MM:SS` now calls `Rtc.setDateTime`;
  `NOTSET` is logged if the RTC is missing or `getVoltLow()` (time lost).
  Verified on hardware right after flashing: `M5Capsule: board=139` (= `board_M5Capsule`, auto-detected),
  `power-hold G46 level=1`, RTC OK, `IMU OK type 6` (= `imu_bmi270`), AS7341 0x39, SD 30 GB, WiFi AP up,
  clock set and a logged row read back: `2026-10-11 03:43:52,63474,...,0.0747,0.2683,0.9634,16.1`.
  Flash use 88 % (was 76 %). Old pre-port sketch kept only in the session scratchpad.
  **Still to verify:** (1) running from the battery with USB unplugged (G46 hold now set, untested);
  (2) RTC keeps time through a real power-off; (3) web page re-checked from a phone after the port;
  (4) IMU axis directions once mounted in the puck (M5Unified applies no axis remap for the Capsule).
- **Battery test result (user, 2026-10-11):** ran from the battery with USB unplugged and the web page
  stayed up, so the G46 power-hold fix works. The copied `log.csv` (23 rows, 03:43-04:11) has NO `ms`
  reset, i.e. it holds no power-off, so the RTC-across-power-off test (item 2) is still open. Accelerometer
  verified under motion (tilt 0.4 deg flat -> 40/36/57 deg handled; |a| ~1.00 g at rest).
  Two unexplained anomalies in that log: (a) rows 2-12 are ~91 s apart instead of 60 s (probably serial
  writes blocking while the user kept re-plugging USB with nobody reading; fix below), (b) the RTC ran ~44 s
  ahead of uptime (`ms`) for rows 2-12 and then agreed again after 04:00:38 (RTC +30 s vs ms +60 s on one
  step) - cause unknown, re-test with USB idle for 15-20 min. The USB data link to the PC has been
  down since (no Espressif device enumerates; only COM3 = the PC's Intel AMT port).
- **Web page upgrade - written and COMPILED (89 % flash) but NOT YET FLASHED (USB down):** page now has
  device time (RTC), battery (V and % via M5.Power ADC on G6 - estimate, no charging flag on the Capsule),
  SD free space (cached `SD.usedBytes()`, refreshed after each log write; the first scan time is printed
  at boot), a "Download data (CSV)" link (`/log`, sent as an attachment) and a "Set device clock from this
  phone" button (`/settime?t=YYYY-MM-DD HH:MM:SS`, applied in `loop()` so the RTC bus is only touched
  from one task). Serial TX is now non-blocking (`Serial.setTxTimeoutMs(0)`). The CSV gained a trailing
  `batt_mv` column; an old-format log is renamed to `/lightdx_log_prev.csv` at boot instead of mixed.
  Pre-change sketch/page copies are in the session scratchpad.
- **First long run, `log2.csv` (analysed 2026-10-12):** 1128 rows, 2026-10-11 03:43:52 -> 22:40:11 (uptime
  18.96 h), exactly one row/min, no reboot, no NOTSET, no gaps after 04:01. Firmware = M5 port, before the
  web-page upgrade (no battery column). The log ENDS 22:40:11 on 10-11, so 10-12 morning was not captured
  (cause unknown: probably battery empty, or powered off / card pulled; on battery it ran ~18.5 h, far
  longer than the "few hours" I guessed).
  * Clock: after the first 17 min (the USB-fiddling period, where the 91 s gaps and the RTC-vs-uptime
    mismatches all sit) the RTC and uptime agree to -3 s over 18.63 h (~45 ppm), so the RTC itself looks
    fine; the early anomalies coincide with the USB re-plugging. Power-off survival is still untested
    (no reboot occurred).
  * Light (arbitrary units, LUX_K = 1): dark 05-06 h (~0.0000); first light 07:53 (>=0.005), >=0.1 from
    09:38 to 17:29, peak 0.59 at 14:23, <0.005 after 18:42; steady ~0.0025 from 20-22 h with a clearly
    warmer spectrum (artificial light). Never saturated (0 rows with n_sat>0); gain 512x most of the day,
    256x at the brightest, so the sensor saw only dim light (indoors / behind glass / shaded) - the
    bright-light AGC step-down test at 50 ms is STILL OPEN. flicker_hz = 0 throughout (checked only every
    30th sample, so weak evidence at night).
  * Orientation: tilt 16 deg (03h), handled 04h, then 77-79 deg all day (Capsule on its side), 88 deg after
    ~20:30 (moved slightly). |a| 0.985-0.995 g at rest (slightly under 1 g: BMI270 scale/offset not
    calibrated). Tilt is of the Capsule, not necessarily the cabled AS7341 head.
- **Low-power design research (2026-10-12), NOT implemented (USB down):** M5 docs: battery 250 mAh, BM8563
  "supports timed wake-up"; no sleep-current figure published. M5Unified `M5Capsule.Power.timerSleep(s)`
  sets the BM8563 alarm and then `_powerOff(true)` pulses POWER_HOLD G46 low = whole board powers OFF on
  battery (RTC alarm powers it back on, firmware restarts from `setup()`); on USB it cannot cut power so it
  falls back to ESP32 deep sleep with an ext0 wake on the RTC INT pin. `timerSleep(rtc_time_t)` is
  minute-aligned (alarm at the next minute boundary, seconds ignored). `Power.powerOff()` = off with no timer.
  Plan: wake each minute -> init -> AS7341 read (AGC start gain kept in Preferences, written only when it
  changes) -> SD append -> `timerSleep(next minute)`; WiFi page only in "live mode" (button/USB/cold boot,
  ~10 min); J_ppix restored from the last SD row. Estimate (not measured): ~1.5-2 s awake per minute at
  ~60-80 mA -> ~2 mA average -> ~5 days on 250 mAh, vs ~3 h with the WiFi AP always on. Needs a real
  current measurement (USB power meter / multimeter). Correction to the earlier note: 250 mAh over 18.5 h
  would be only ~13 mA average, impossible with the WiFi AP always on, so the 18 h run was almost certainly
  on USB power for much of it - the log end at 22:40 is NOT evidence of battery life.

## Session-based recording design (decided 2026-10-13, NOT implemented)

User decision: logging and J_ppix accumulation happen only when the user asks from the app; otherwise no logging.

- **Start / Stop** from the web page. Start sets the RTC from the phone, begins a session (new session id), resets J_ppix to 0. Stop writes a summary row (duration, final J_ppix) and ends the session.
- **Idle:** live spectrum view works as now, but nothing is written to SD and J_ppix is not accumulated.
- **Recording is autonomous:** continues if the phone disconnects. Session state (active flag, start time, running J_ppix, session id) must be persisted so a reset or brownout resumes it.
- **Safety stops:** automatic stop after 12 h (user's choice) or when the battery is low; both write a closing row.
- **Stop does NOT power the board off** (user's choice); it just ends the session.
- **Indicators:** "REC" on the page and the RGB LED, so a forgotten Start is obvious.
- **Low power interaction:** between samples the board powers off with timerSleep (60 s wake interval, user's choice); the phone can only reach it after a button press or USB plug-in (live mode). Waking from the app would need BLE (later).
- Order: finish the Step 1 test of the web-page upgrade (current always-logging behaviour) first, then build sessions + low-power cycle together.

## Step 1 results: web-page upgrade flashed and tested (2026-10-13)

Flashed the web-upgrade firmware plus `Cache-Control: no-store` on `/` (phones kept showing the old page after the update). Verified from the phone screenshot and a serial dump of the SD log (14:06-14:45):
- Page shows device time (RTC), battery, SD free (29.7 GB of 29.7 GB), Download CSV link and "Set device clock from this phone" button; the button set the clock (page: "clock set to 14:30:57", device time 14:31:14 shortly after).
- Row spacing: uptime (ms) steps of 60.0-60.4 s; RTC steps 60 s (occasionally 61). The earlier 91 s gaps are gone, so serial TX blocking was the cause (fixed by `Serial.setTxTimeoutMs(0)`).
- RTC vs uptime over one 12-minute stretch (14:32:48 to 14:44:49): 721 s vs 720.8 s.
- One RTC jump of +7 s with no uptime jump at 14:23-14:24 (probably the Set-clock button).
- The new log header ends `...,tilt_deg,batt_mv`. Accelerometer: z about 1.00 g, tilt about 2 deg, flat.
- Opening/closing the USB serial port from Python (pyserial) RESETS the board; every row with ms about 3374 is such a reboot. J_ppix (RAM only) restarts then.
- Battery reading is NOT trustworthy on USB: 4.38 V falling to 4.31 V over 40 min, above the 4.2 V Li-ion maximum (charger raises the pin voltage and/or the ADC scale is off). Re-check on battery power only.
- Not yet verified: the Download link actually saving a file on the phone; the old-format log rename to `lightdx_log_prev.csv`.

## Step 2: session recording + 60 s low-power cycle (implemented and tested 2026-10-13, NOT yet pushed)

Firmware: `firmware/capsule_serial_test/` (working tree, branch `step2-wip`; GitHub still has only v1 / v1.1). 1,198,615 bytes (91 % flash), RAM 16 %.

**Design as built**
- Log columns: `datetime,session,event,elapsed_s,ms,gain_x,tint_ms,flicker_hz,n_sat,cnt_F1..F8,cnt_Clear,cnt_NIR,E_ppix,J_ppix,lux,acc_x_g,acc_y_g,acc_z_g,tilt_deg,batt_mv`. Events: start, resume, sample, stop, auto_12h, batt_low.
- Constants: `LOG_PERIOD_S 60`, `REC_MAX_S 12 h`, `BATT_LOW_MV 3300`, `LIVE_IDLE_TIMEOUT_MS` 10 min (test build used 40 s via `--build-property "compiler.cpp.extra_flags=-DLIVE_IDLE_TIMEOUT_MS=40000UL"`).
- Session state in NVS (`Preferences` ns "lightdx": rec, sid, start, lastep, lastrow, j, gain). J_ppix = session dose, integrated only while recording.
- Live mode (WiFi AP `LightDX`/`lightdx123`, http://192.168.4.1/) on cold boot / button / USB plug. While recording and no web activity for the idle timeout -> quiet cycle: timer wake, sample, row, sleep, no WiFi. Not recording: stays awake (no auto-off decided; battery drain open item).
- Web page: REC banner, Start (sends phone time) / Stop, session J_ppix, device time, battery, SD free, Download CSV, Set clock.

**Library findings (M5Capsule 1.0.1 / M5Unified 0.2.25)**
- Capsule config has no `_rtcIntPin`, so use `M5.Power.timerSleep(int seconds)` (arms BM8563 countdown + ESP32 timer). On battery it pulses G46 low (board fully off, RTC INT powers it back on); on USB it falls back to `esp_deep_sleep_start()`.
- Wake cause: `m5cfg.disable_rtc_irq = false`, then `Rtc.getIRQstatus()` after `begin`, then `Rtc.disableIRQ()`.
- Countdown <=255 s uses the 1 Hz clock. Sleep seconds = 60 - RTC seconds (+60 if <8) so rows land on the minute.
- `if (Serial)` stays true after the PC closes the port: NOT usable as an activity signal (removed).
- Opening/closing the USB serial port with pyserial resets the board; the USB port enumerates ~0.3 s before app code runs. While asleep on USB the COM port disappears; the awake window is only ~1.4 s per minute, too short for `arduino-cli upload` (all attempts failed). To reflash: press reset (40 s live window in the test build) or hold G0 while replugging.
- `build.extra_flags` override drops the CDC flags (compile error); use `compiler.cpp.extra_flags`.
- Old-format logs are renamed (`lightdx_log_prev.csv`, `_prev1`), never deleted.

**Test results**
- USB deep-sleep cycle: ~1.4 s to sample, ~1.7 s awake per minute, one row per minute, session and J_ppix persisted.
- BATTERY PATH PASSED: session 3, 15:25:31 -> 22:05:04 (6.7 h), 401 rows; 382/398 gaps exactly 60 s (rest 59-62 s, plus three longer gaps 84/118/92 s caused by my serial connections and the replug); awake ~1.6 s per wake; J_ppix continued across wakes (0.77 -> 3240 arb. units); events 1 start, 396 sample, 4 resume (resume = serial open or replug, not failures).
- Battery on the real cell: 4.25 V (16:16) -> 4.19 V (21:41), ~56 mV in 5.4 h. USB-inflated readings seen at replug (4.51-4.55 V). Unplug time not logged, so no mAh figure yet. Needs a run to ~3.3 V for a real endurance number.

**Not yet verified**: phone REC banner and Start/Stop buttons; phone could not see the `LightDX` hotspot because the board was in its sleep cycle (WiFi only in live mode) and the 40 s test build sleeps too soon; `auto_12h` event; bright-light behaviour at 50 ms; lux/PpIX calibration; IMU axes in the puck.

## Second capsule + new AS7341 (2026-10-13)
- Flashed the pushed v1.1 firmware (built from the git tag into a scratch folder) onto a second capsule, port COM9 (first capsule is COM8). The first cable was charge-only; swapping the cable made it enumerate.
- New AS7341 answers at 0x39 only on swapped pins (SDA 15 / SCL 13); the firmware's swapped-pin fallback handles it. RTC and IMU OK; SD card not found (reseat/format FAT32); RTC NOTSET.
- Tilting the sensor changed Clear raw from ~231 to ~2300 at 512x gain, no saturation; spectral shape moved plausibly.

## STATE AT END OF 2026-10-13 / TODO TOMORROW
- Capsule 1 (COM8, USB powered, flashed with the 40 s test build) is recording session 3 (started 15:25). It auto-stops at ~03:25 (`auto_12h`), then stays awake in live mode. Do not open its serial port.
- Tomorrow: download the log (reset the board, `python -I sess.py COM8 22 "14:d"` style), check the 12 h run (gaps, batt curve, auto_12h row); reflash the DEFAULT 10-minute build (already compiled from the working tree; press reset or hold G0 on replug); test the phone page (REC banner, Start/Stop, clock, download); then update firmware README, commit and, with user approval, push as v1.2.
- Open items: idle live-mode auto-off policy, bright-light test, calibrate LUX_K/K_SCALE, IMU axes, compare two AS7341 units under the same lamp.

## Daily log files + buzzer fix (coded and COMPILED 2026-10-13 evening, NOT flashed or tested)
- Log is now one file per day: `/lightdx_YYYY-MM-DD.csv` (date from the RTC at row time; `/lightdx_NOTSET.csv` if the clock is invalid). Header written when a day file is created; a day file with a mismatching header is renamed `..._prevN.csv`. A session crossing midnight continues in the next day's file (use the `session` column to join).
- Web: `/log` = today, `/log?d=YYYY-MM-DD` = that day, `/files` = "YYYY-MM-DD,bytes" lines; page shows "today" plus the last 14 day links. Serial: `d` today, `D YYYY-MM-DD` another day, `e` erase today only.
- The old single `/lightdx_log.csv` (and `_prev` files) are left untouched on the SD card.
- Buzzer: user hears an insect-like buzz/chirp on every wake of capsule 1. G2 is now pulled low as the first line of `setup()` (before `M5Capsule.begin`). If it persists on battery (power-off between wakes), it is a power-transient click and needs hardware (remove/damp the buzzer) or never powering off. Untested.
- Build: 1,201,331 bytes (91 % flash), RAM 16 %. Test tomorrow when reflashing: day file names, header, midnight rollover (set RTC near 23:59 to test), `/files` links on the phone, `D` command, buzzer.

## Results 2026-10-14 (morning)
- Overnight run of session 3 (old build, USB + battery mix): 538 rows 15:25 -> 01:14 (9.8 h), 507/545 gaps exactly 60 s, J_ppix reached 6451 across ~590 power-offs. Battery on the cell 4.30 V -> 4.18 V over ~9 h (readings of 4.4-4.55 V are USB charging). Auto 12 h stop (due ~03:25) not yet observed.
- Flashed the daily-file + early-buzzer-pin-low build (default 10 min idle) onto capsule 1 while the session was recording: session and J_ppix survived the reflash (elapsed continued at 35,414 s). `/lightdx_2026-10-14.csv` created with a correct header; the old `lightdx_log.csv` and `_prev` files were left untouched.
- User confirmed: the `LightDX` hotspot is visible from the phone with the 10-minute build, and the insect-like buzz on wake is gone (G2 pulled low first in setup works; no hardware fix needed).
- Still to verify: phone page Start/Stop/REC banner, set-clock, day download links, midnight rollover, auto_12h row.

## Phone page test 2026-10-14 01:22-01:34 (daily-file build)
- Verified from the phone: REC banner (timer correct), live spectrum, device time = phone time, download of `lightdx_2026-10-14.csv` (21 rows, correct header), Start, Stop, Set clock. Session 4 start->stop in 12 s, J_ppix reset to 0 then 4.5.
- Bug found: pressing Start while session 3 was recording began session 4 WITHOUT a closing row for session 3. Fixed in source (start now logs a "stop" row for the running session first). Compiled (1,201,455 bytes), not yet flashed.
- Battery tile showed "4.36 V (100%)" on USB. Page now shows "USB power (x V, not the cell)" above 4.25 V. Not yet flashed.
- While the page is open the board stays in live mode (uptime ms keeps counting, rows still every 60 s but not on the minute); the sleep cycle only resumes 10 min after the last request.

## v1.2 released 2026-10-14
Flashed to capsule 1 and verified over serial: Start while recording -> session 5 closed with a `stop` row (7 s, J 2.65), session 6 starts at the same second with J 0; stop row for 6. v1.2 = session recording + 60 s low-power cycle, daily log files, buzzer pin low first, USB battery label, phone Start/Stop/download/set-clock verified.

## STATE AT END OF 2026-10-14 SESSION (supersedes the earlier "state / TODO tomorrow")
- GitHub `main` = v1.2 (3aafe85, tag v1.2). Capsule 1 (COM8, old AS7341 on default pins) runs v1.2, no session recording, awake in live mode on USB (will drain the battery if unplugged without starting a session: the sleep cycle only runs while recording).
- Capsule 2 (COM9, new AS7341 on swapped pins 15/13, no SD, RTC unset) runs v1.1 from the git tag. It has NOT been updated to v1.2.
- Verified: session start/stop/auto-close from the phone, REC banner, device time, set clock, daily day-file download, 60 s battery wake cycle (6.7-9.8 h runs), buzz gone, start-while-recording closes the old session.
- Not verified: auto_12h row, midnight rollover to a new day file, batt_low stop at 3.3 V, full battery endurance run to empty, calibration of E_ppix/lux (arbitrary units), IMU axes in the puck, bright-light AGC at 50 ms, two-sensor comparison under one lamp.
- Open decisions: auto-off / low-power policy for live mode when NOT recording; flash capsule 2 with v1.2 (needs an SD card).
- Tips: opening COM port resets the board; flash while awake (press reset, or hold G0 on replug); long compile ~8 min; use Edit/Write tools, not Python replacement strings, for C escapes.

## Enclosure: v3 and slim_puck (2026-10-13)
Model: `Square_puck_v2.FCStd` (saved; v3 box objects `Box_*` kept but hidden, slim objects `Slim_Base`, `Slim_Lid`, `Ref_Slim_*` visible).
Scripts (run in FreeCAD via the MCP, `build_and_apply("Square_puck_v2")`): `build_box_enclosure.py` = v3, `build_slim_puck.py` = slim_puck;
older slim steps kept as `build_slim_puck_rev1..rev9.py`, v2 as `build_box_enclosure_v2_prev.py`.

**v3** (first printed fit after the user's tweaks): Capsule length 40 -> 41 (pocket 41.4, the 40.4 pocket was very tight), diffuser seat radius 6.1 -> 5.6 (dia 12.2 -> 11.2; through-aperture unchanged, dia 10),
second divider notch for the I2C cable mirrored at x = -14 (battery-lead notch at +14). 45.4 x 50 x 16.6. Exports `Box_Base_v3.stl`, `Box_Lid_v3.stl`. User printed it: fits "very well".

**Hardware change (user, 2026-10-13):** the I2C (STEMMA QT/JST) connectors were removed from the AS7341 and the new Capsule (wires soldered), photos `enclosure1.jpeg`, `enclosure2.jpeg`.
User said roughly half the base height was now free.

**slim_puck, current state: 42.4 x 50 x 12.7 mm** (`Slim_Puck_Base.stl`, `Slim_Puck_Lid.stl`, exported 2026-10-13 23:57, NOT printed yet). Base 10.7 + lid 2.0.
- ESTIMATES, user said to correct after printing: Capsule height 7.0 mm (was 13), AS7341 board + parts 2.8 mm (pocket depth 3.0). Not measured with calipers.
- AS7341 is held by 4 lid posts with 2 mm pins through its corner holes (no screws), 0.5 mm over the cell (was 2.0 for screw heads). Lid pins in the board holes show as a 19.7 mm3 "clash": intended.
- Floor 1.2, lid 2.0 (seat 1.5 + 0.5 shoulder), both end walls 1.0, side walls 2.0. Battery/AS7341 pocket 27.9 long (was 30.4; user: pocket was >= 2.5 mm too big), width 20.4 unchanged.
- Base screws: M2x8 (not 14), in the 7 mm blocks beside the cell. Divider notches at x = +-11 (lead, I2C).
- Height is set by the sensor stack (1.2 floor + 6 cell + 0.5 + 3.0 + 2.0 = 12.7); the Capsule stack is only 10.2. 7.5 mm total is not reachable with the AS7341 over the 6 mm cell and the 42 x 50 footprint (user ruled out a bigger footprint).
- Length: Capsule pocket 40.4 (cap_inset = 1.0): the USB-C end pokes up to 1 mm into the front wall window. USB window 9.4 x 3.8 mm (connector 8.94 x 3.26 + clearance), centre z = floor + cap_h - 2.5 = 5.7 (from an old photo, to verify).
  Earlier idea of an open USB end was dropped; the user chose a closed wall with a connector-sized window.
- Lid features, positions estimated from `enclosure2.jpeg` (rows: x from the far end, y from the Capsule centre line, - = sensor side): G42 tactile button at 1.8 mm from the end, y -3.4: U-slot tongue 7 wide x 8.9 long, slot 0.8, hinged on the inner side, nub r1.2 down to z = 6.0 (switch height ASSUMED; 2 mm PLA may be too stiff, thin to ~1 mm if so).
  2 mm hole over the chip next to the button (maybe the power LED), y -4.3, 4.8 mm from the end (a guess).
- Base far end wall: RGB LED (G21) is SIDE mounted at the board edge beside the buzzer (user): window 3.0 x 1.6 mm at y +3.4, z 3.4. Side-mounted BOOT switch (G0), "just below the top tactile switch": 2.4 mm hole at y = button y, z 3.0. Both z values assume the PCB top is at z ~2.8: guesses.
- Capsule_v1.1.stl (M5 shell): the end cap has a 16 x 9.5 mm flap with a U-slot at y -18..-8.5, plus a 5 x 0.6 mm groove (a fingerprint mark, not an LED window). Capsule = 24 x 40 shell, USB-C protrudes ~1 mm. Only used as a template for the flap.
- Open to verify when printed: Capsule real height and connector height, pin fit in AS7341 holes (2.0 vs ~2.2 hole), 1.0 mm walls and 0.5 mm shoulder strength, tongue stiffness, LED/switch hole positions, whether screws M2x8 are enough.

## Measurements 2026-10-15 + design page
User calipers: Capsule board (headers incl.) 6 mm; battery 4.5 mm; AS7341 2.5 mm; battery + AS7341 stacked 7 mm tall x 25 long x 20 wide (photos `all_together.jpeg`, `battery1.jpeg`, `caspule_board.jpeg`).
Model/STLs still use the old estimates (7 / 6 / 3.0). Proposed rebuild: cap_h 6.0, cell_t 4.5, AS7341 2.5 (stack 7.0 + 0.3 clearance), pocket 25.8 x 20.4 (the Adafruit AS7341 is 25.4 long: keep >= 25.8), total height ~10.5 mm (was 12.7), footprint unchanged. NOT applied yet.
Design page: `LightDx_slim_puck_design.html` (self-contained, built by `make_slim_design_page.py` from FreeCAD views saved in `renders/fc_*.png` + the photos). Capture tip: in FreeCAD call `v.setAnimationEnabled(False)` and `Gui.updateGui()` before `saveImage`, otherwise the standard views are saved mid-rotation.

## Print feedback on Slim_Puck_Base/Lid (2026-10-15, first print of the 2026-10-13 STLs)
Photos in `3D_print_photos/`. Heights worked well (12.7 mm), unchanged. Applied in `build_slim_puck.py` (saved in `Square_puck_v2.FCStd`; STLs NOT re-exported yet):
- USB-C connector sits higher than the window: window raised 1.2 mm (centre z 5.7 -> 6.9).
- Capsule pocket had 2 mm spare in width: cap_w 24 -> 22 (pocket 22.4), taken off the outer side (board sits against the divider wall); features keep their y from the divider wall (`feat_cy`). Box 42.4 x 48.0.
- Diffuser seat printed too small: dia 11.2 -> 12.4 (r 6.2).
- G42 pusher nub (and its U-slot tongue + the 2 mm lid LED hole) moved 2 mm toward the USB end (-X) and 2 mm toward +Y (outer wall side): nub (16.2, 10.4), hole (13.2, 9.5). Direction read from the lid photo (underside, flipped about the X axis: image down = +Y).
- Far-end wall holes (RGB LED window y 14.4, BOOT hole y 8.4): photo 1 has arrows pointing toward +Y (right when looking at the far end from outside); distance not stated, NOT applied yet.
- Axis convention for the design page figure: X right (USB end -X, far end +X), Y up (Capsule +Y, battery/AS7341 -Y), origin at box centre.
- (2026-10-15, later) Photo `3D_print_photos/WhatsApp Image 2026-10-15 at 12.32.21.jpeg` (assembled base, USB end left): ~3 mm spare beside the Capsule at both X ends. Shaved 1.5 mm off each end (`x_shave`): Capsule pocket 40.4 -> 37.4, box 42.4 -> 39.4 mm x 48.0 x 12.7. Feature positions kept in box coordinates (symmetric shave), so the USB connector now pokes ~1.5 mm further into its 1.0 mm wall window; screw blocks are 5.75 mm wide (tight for the 4.4 mm counterbore, user will use small screw heads). Far-wall holes moved 4 mm toward +Y: RGB window y = 18.4, BOOT hole y = 12.4. Not exported yet; design page not regenerated yet.
- (2026-10-15, later) Lid LED opening is now a USB-C-like slit 1.6 (X) x 3.4 (Y) at (13.2, 10.0); far-wall BOOT hole at y = 10.0; RGB window stays at y 18.4 (spacing to BOOT now 8.4, user had measured 6.0: to confirm). Nub/tongue centre is y 10.4 (0.4 mm off the user's "10 mm"). Design page updated, STLs NOT exported yet.
- 2026-10-15 (2nd print): Capsule and battery pockets did not fit width-wise after my 2 mm trim. Restored cap_w 24 (pocket 24.4), widened battery pocket 20.4 -> 21.0 (cell_w 20.6). Box now 39.4 x 50.6 x 12.7. Lid LED slit and BOOT hole y are now relative to the divider (feat_cy - 1.8) so they stay aligned with the tongue; absolute box-centre y is 9.3 (nub 9.7). STLs re-exported. Previous script: build_slim_puck_rev16.py.
- 2026-10-15 (correction): the "2 mm spare" was along X, not Y. x_shave 1.5 -> 1.0 (Capsule pocket 38.4 long, box 40.4); Capsule width back to 24.4, battery pocket 21.0; box 40.4 x 50.6 x 12.7. Diffuser seat dia 12.4 -> 12.0 (seat_radius 6.0). Nub y 9.7, LED slit / BOOT y 9.3, RGB y 17.7 (all relative to the divider wall). STLs re-exported, design page + plan diagram regenerated. Previous script: build_slim_puck_rev17.py.
- 2026-10-15 (2nd print feedback, "very close"): G42 tongue + nub 1 mm toward +Y (nub y 10.7); nub 1.5 mm shorter (nub_z0 6.0 -> 7.5); BOOT hole +1 mm Y (y 10.3); RGB window -1 mm Y (y 16.7) and +1.5 mm height (zc 4.9). Lid LED slit left at y 9.3 (not asked). STLs re-exported, page regenerated. Previous script: build_slim_puck_rev18.py.
- 2026-10-15: lid LED slit now centred on the tongue in Y (led_y = btn_y = 10.7; was 9.3). Design page "Changes" table fixed (wrapping, column widths). STLs re-exported.
- 2026-10-15: diffuser rim (ledge under the disc) 0.5 -> 1.0 mm thick: seat depth 1.5 -> 1.0 (lid stays 2.0, radial ledge already 1.0 mm: seat dia 12.0, aperture dia 10). Check that the diffuser disc is <= 1.0 mm thick so it does not stand proud. Previous script: build_slim_puck_rev19.py.
- 2026-10-15: diffuser disc is 2.0 mm thick. Seat 2.0 deep, rim under it 1.0, so a 1.0 mm raised ring (dia 16) on the lid top around the seat (lid itself stays 2.0; box 12.7, 13.7 at the ring). Alternative if the ring is unwanted: seat 1.0 deep and the disc stands 1.0 proud. Previous script: build_slim_puck_rev20.py.
- 2026-10-15: raised ring dropped (user). Diffuser disc is 2.0 mm thick; seat stays 1.5 deep with a 0.5 mm ledge, disc stands 0.5 mm proud; user will see if the manufacturer complains. Previous script: build_slim_puck_rev21.py.
- 2026-10-16: Second print worked well. Frozen as base model: `LightDx_base_v1.FCStd` (copy of Square_puck_v2.FCStd at d993598, tag `base-v1`). Never edit it. From here the puck becomes a wearable (clip / watch strap); mounts are separate add-on parts, built in Square_puck_v2.FCStd. No STL export until asked.
- 2026-10-16: Wearable add-ons v1 (build_wearable_mounts.py, in Square_puck_v2.FCStd; no STLs yet). Both glue to the flat base back (z=0), diffuser/lid faces outward. Strap_Plate: 2.4 mm plate + lug pairs on +-Y ends, strap 20 mm (user), 3 mm lugs, 1.8 mm spring-bar hole at 2.5 mm from tip, lug tip at y +-30.3. Clip_Plate: 2.4 mm plate + 14 mm wide, 1.6 mm PETG clip arm, 1.5 mm fabric gap, hook at free end; total height 18.2 mm. Both valid, no overlap with base. Unverified: lug strength, clip spring force, glue vs. other attachment.
- 2026-10-16: Wearable v2 (user: no glued plate, base IS the wearable base, no extra height, rounded lugs). build_wearable_mounts.py now fuses lugs into a copy of Slim_Base -> `Wear_Base_Strap`: height stays 10.7 base / 12.7 total, lugs 3 mm thick x 6 mm tall (z 0..6), round tips r3, 1.8 mm spring-bar hole through both lugs at 3 mm beyond the wall, 20 mm gap, total Y length 62.6. Hidden variant `Wear_Base_Clip` (clip arm fused to the base back, +3.1 mm below). Strap_Plate/Clip_Plate removed. Lid unchanged. No STLs yet.
- 2026-10-16: Wearable v3: lugs moved from the +-Y ends to the +-X ends (user request); strap runs along X. Lug pairs 3 mm thick, 6 mm tall, round tips, 20 mm gap, spring-bar hole along Y. Gap centre shifted to y = -7 (GAP_Y) so lugs miss the USB window (y 6.4..15.8, z 5..8.8), BOOT hole (y 9.1..11.5) and RGB window (y 15.2..18.2): lugs at y 3..6 and -20..-17. Total X length 52.4. Valid, no lid overlap. No STLs yet.
- 2026-10-16: Wearable v4 (user chose centred strap, 20 mm): GAP_Y = 1.85. Upper lug y 11.85..14.85 sits between the BOOT hole (to 11.5) and the RGB window (from 15.2); lower lug y -11.15..-8.15. Strap off-centre by only 1.85 mm. Known trade-off: on the -X end the same lug stands in front of the USB-C window, so the strap (spring bar) must be removed to plug in. BOOT/RGB openings verified still open. No STLs yet.
- 2026-10-16: Wearable v5: lug root was protruding into the USB-C window (-X wall). Cut the window (y 6.4..15.8, z 5.0..8.8) through the lug too, so the lug is notched above z 5 and the window is clear. Final part will be metal, so lug strength is not a concern. Lug below z 5 still sits in front of the window (plug body may still touch it: check on the first fit). No STLs yet.
- 2026-10-16: Wearable strap base ACCEPTED by the user (v5, commit 286f85b): lugs on the +-X ends, 20 mm strap, gap centre y = 1.85 (1.85 mm off-centre). Tried exact centring (y = 0): lug inner face at y 10 overlaps the BOOT hole (y 9.1..11.5, z 1.8..4.2), which sits exactly on the spring-bar seat (y 10.., z 3), so the bar would lose its seat. Reverted. Exact centring would need the BOOT hole moved >= 2 mm in a future print, not worth it. USB-C window is cut through the +-X lug (notch above z 5); strap bar is removed to charge. Final part will be metal. Clip variant (hidden Wear_Base_Clip) still unreviewed. No wearable STLs exported yet (export on request).
- 2026-10-16: Exported Wear_Base_Strap.stl (accepted strap base v5, 52.4 x 50.6 x 10.7 mm, watertight mesh). Lid is unchanged: use the existing Slim_Puck_Lid.stl. Clip variant not exported.
- 2026-10-16: Normal puck v4 built (`build_normal_puck_v4.py`, objects V4_Base/V4_Lid/Ref_V4_* in Square_puck_v2.FCStd; no STLs). For the Capsule/AS7341 WITH connectors. 43.4 x 50.0 x 16.2 mm (base 14.2 + lid 2.0; was v3 45.4 x 50 x 16.6). Carried over from the slim print: floor 1.2, end walls 1.0, side 2.0, lid 2.0; diffuser seat dia 12.0 / 1.5 deep / 0.5 ledge / aperture dia 10 (no boss); AS7341 held by lid pins (no screws); G42 tongue + nub, lid LED slit 1.6 x 3.4, BOOT hole dia 2.4 (y 10.3, z 3.0) and RGB window (y 16.7, z 4.9) from the divider wall; closed -X wall with a narrow USB-C window 9.4 wide. KEPT from v3 (connectors): Capsule pocket 41.4 x 24.4, cap_h 13, battery pocket 30.4 x 20.4, JST plug slots, cable notches at x = +-14, AS7341 pocket depth 4.6, M2x14 base screws. ASSUMED (verify in print): USB window 9.4 x 6.5 at z = top - 2.5 (v3 value, NOT the slim +1.2), far-wall features sit 3.0 mm from the far wall, nub bottom z = Capsule top - 0.7 (13.5), BOOT/RGB z as in slim. Checks: both parts valid, 1 solid each; only intended overlaps (nub/Capsule 3.2 mm3, lid pins/AS7341 19.7 mm3). Fix during build: the nub was floating (the 0.5 mm Capsule recess lifts the lid ceiling), so it now extends through the recess.
