#!/usr/bin/env python3
"""PpIX-weighted index weights for the AS7341 (LightDX).

Finds non-negative weights w_i (one per channel F1..F8) so that

    E_ppix = sum_i w_i * cnt_i            (cnt_i = gain/tint-normalised counts from the firmware)

approximates the PpIX-weighted irradiance  T = integral E(l) * A_norm(l) dl  for real illuminants.

Inputs (analysis/data/, created with PLACEHOLDER values on first run -- replace them):
  as7341_response.csv   wavelength_nm,F1..F8      relative channel responsivity R_i(l)
  ppix_absorption.csv   wavelength_nm,A_norm      PpIX absorption normalised to 1 at 635 nm
  cie_daylight_basis.csv  CIE S0,S1,S2 (real data, exported from colour-science)

Fit objective (non-negative least squares, stacked):
  (a) spectral match: sum_l Dbar(l) * (sum_i w_i R_i(l) - A(l))^2   (Dbar = mean daylight SPD)
  (b) dose match:     sum_k (sum_i w_i c_ik / T_k - 1)^2 over daylight illuminants k
      with c_ik = integral R_i S_k, T_k = integral A S_k.
Output: weights table, error table over test illuminants, firmware/.../ppix_weights.h

Units: the placeholder responsivities are peak-normalised (equal peak sensitivity assumed), so
E_ppix is in ARBITRARY units until a calibration scale K_SCALE is applied (see firmware).
"""
import argparse
import csv
import os
import numpy as np
from scipy.optimize import nnls

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
HEADER_OUT = os.path.join(HERE, "..", "firmware", "capsule_serial_test", "ppix_weights.h")
WL = np.arange(350.0, 801.0, 1.0)  # nm grid
CH = ["F1_415", "F2_445", "F3_480", "F4_515", "F5_555", "F6_590", "F7_630", "F8_680"]


def gauss(wl, centre, fwhm):
    return np.exp(-4.0 * np.log(2.0) * ((wl - centre) / fwhm) ** 2)


# ---------------------------------------------------------------- placeholder data
def write_placeholders():
    os.makedirs(DATA, exist_ok=True)
    resp = os.path.join(DATA, "as7341_response.csv")
    if not os.path.exists(resp):
        centres = [415, 445, 480, 515, 555, 590, 630, 680]
        fwhm = [26, 30, 36, 39, 39, 40, 50, 52]  # ASSUMED from memory of the ams datasheet table
        with open(resp, "w", newline="") as f:
            f.write("# PLACEHOLDER: Gaussian channels, equal peak sensitivity. Replace with digitised\n"
                    "# ams AS7341 datasheet spectral responsivity (and per-channel peak sensitivities).\n")
            w = csv.writer(f)
            w.writerow(["wavelength_nm"] + CH)
            for l in WL:
                w.writerow([f"{l:g}"] + [f"{gauss(l, c, fw):.6g}" for c, fw in zip(centres, fwhm)])
    ppix = os.path.join(DATA, "ppix_absorption.csv")
    if not os.path.exists(ppix):
        # Soret ~407 nm, Q bands 505/540/575/630 nm; relative eps 171k/14k/11k/7.2k/5k (PpIX, organic solvent)
        bands = [(407, 22, 171.0), (505, 30, 14.0), (540, 30, 11.0), (575, 25, 7.2), (630, 18, 5.0)]
        a = sum(h * gauss(WL, c, fw) for c, fw, h in bands)
        a = a / np.interp(635.0, WL, a)
        with open(ppix, "w", newline="") as f:
            f.write("# PLACEHOLDER: Gaussian bands from a peak table. Replace with a published/lab PpIX spectrum.\n"
                    "# Normalised to 1 at 635 nm (red-equivalent dose convention; confirm with the lab).\n")
            w = csv.writer(f)
            w.writerow(["wavelength_nm", "A_norm"])
            for l, v in zip(WL, a):
                w.writerow([f"{l:g}", f"{v:.6g}"])


def load_table(name):
    path = os.path.join(DATA, name)
    rows = [r for r in csv.reader(l for l in open(path) if not l.startswith("#"))]
    head, body = rows[0], np.array(rows[1:], dtype=float)
    return head, body


def on_grid(body):
    return np.column_stack([np.interp(WL, body[:, 0], body[:, j], left=0.0, right=0.0)
                            for j in range(1, body.shape[1])])


# ---------------------------------------------------------------- illuminants
def daylight(cct, basis):
    t = cct
    if t <= 7000:
        x = 0.244063 + 0.09911e3 / t + 2.9678e6 / t**2 - 4.6070e9 / t**3
    else:
        x = 0.237040 + 0.24748e3 / t + 1.9018e6 / t**2 - 2.0064e9 / t**3
    y = -3.0 * x * x + 2.870 * x - 0.275
    m = 0.0241 + 0.2562 * x - 0.7341 * y
    m1 = (-1.3515 - 1.7703 * x + 5.9114 * y) / m
    m2 = (0.0300 - 31.4424 * x + 30.0717 * y) / m
    s = basis[:, 1] + m1 * basis[:, 2] + m2 * basis[:, 3]
    return np.interp(WL, basis[:, 0], s, left=0.0, right=0.0)


def blackbody(t):
    l = WL * 1e-9
    return 1.0 / (l**5 * (np.exp(1.4388e-2 / (l * t)) - 1.0))


def synthetic_lamps():
    """Rough synthetic spectra (NOT measured) to show behaviour on non-daylight sources."""
    lamps = {"incandescent 2856K": blackbody(2856.0)}
    led_blue = gauss(WL, 450, 22)
    lamps["LED warm (~3000K)"] = 0.35 * led_blue + 1.0 * gauss(WL, 600, 110)
    lamps["LED cool (~6500K)"] = 1.0 * led_blue + 0.9 * gauss(WL, 560, 105)
    fl = 0.35 * gauss(WL, 580, 120) + 0.25 * gauss(WL, 540, 90)
    for c, h in [(405, 0.6), (436, 1.0), (546, 1.2), (578, 0.5)]:
        fl = fl + h * gauss(WL, c, 3.0)
    lamps["fluorescent (lines)"] = fl
    return lamps


# ---------------------------------------------------------------- fit
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mu", type=float, default=0.3, help="weight of the spectral-match rows")
    ap.add_argument("--no-header", action="store_true", help="do not write the firmware header")
    args = ap.parse_args()

    write_placeholders()
    _, rbody = load_table("as7341_response.csv")
    _, abody = load_table("ppix_absorption.csv")
    R = on_grid(rbody)[:, :8]          # (L, 8)
    A = on_grid(abody)[:, 0]           # (L,)
    basis = np.loadtxt(os.path.join(DATA, "cie_daylight_basis.csv"), delimiter=",", skiprows=2)

    train_cct = [4000, 4500, 5000, 5500, 6500, 7500, 10000, 15000]  # direct sun -> shade / blue sky
    train = {f"D{c}": daylight(c, basis) for c in train_cct}
    dbar = np.mean([s / np.trapezoid(s, WL) for s in train.values()], axis=0)

    # stacked NNLS: dose-match rows + spectral-match rows
    rows, rhs = [], []
    for s in train.values():
        c = np.trapezoid(R * s[:, None], WL, axis=0)
        t = np.trapezoid(A * s, WL)
        rows.append(c / t)
        rhs.append(1.0)
    sw = np.sqrt(args.mu * dbar / dbar.max())
    spec_rows = (R * sw[:, None])
    spec_rhs = A * sw
    # normalise the spectral block so it is comparable with the dose rows
    nfac = 1.0 / np.sqrt(len(WL))
    M = np.vstack([np.array(rows), spec_rows * nfac * 10.0])
    b = np.concatenate([rhs, spec_rhs * nfac * 10.0])
    w, resid = nnls(M, b, maxiter=10000)

    print("Channel weights w_i (arbitrary units, see header comment):")
    for n, v in zip(CH, w):
        print(f"  {n:8s} {v:.6g}")

    def table(title, spectra):
        print(f"\n{title}\n  {'illuminant':24s} {'true T':>10s} {'model':>10s} {'error %':>9s}")
        errs = []
        for name, s in spectra.items():
            t = np.trapezoid(A * s, WL)
            m = float(np.dot(w, np.trapezoid(R * s[:, None], WL, axis=0)))
            e = 100.0 * (m - t) / t
            errs.append(e)
            print(f"  {name:24s} {t:10.4g} {m:10.4g} {e:9.1f}")
        return errs

    ed = table("Training daylight set", train)
    test = {f"D{c}": daylight(c, basis) for c in [4200, 5200, 6000, 8000, 12000, 20000]}
    et = table("Held-out daylight set", test)
    el = table("Synthetic lamps (rough, not measured)", synthetic_lamps())
    print(f"\nDaylight |error| max: train {np.max(np.abs(ed)):.1f} %, held-out {np.max(np.abs(et)):.1f} %")
    print(f"Lamp errors (expected larger): max {np.max(np.abs(el)):.1f} %")

    if not args.no_header:
        with open(HEADER_OUT, "w") as f:
            f.write("// GENERATED by analysis/ppix_weights.py -- do not edit by hand.\n"
                    "// E_ppix = sum_i W_PPIX[i] * cnt_i  (cnt = gain/tint-normalised counts, F1..F8).\n"
                    "// Arbitrary units until K_SCALE is calibrated. Based on PLACEHOLDER responsivity and\n"
                    "// PpIX spectra unless analysis/data/*.csv were replaced with real data.\n"
                    "#pragma once\n")
            f.write("static const float W_PPIX[8] = {" + ", ".join(f"{v:.8e}f" for v in w) + "};\n")
        print("\nWrote", os.path.normpath(HEADER_OUT))


if __name__ == "__main__":
    main()
