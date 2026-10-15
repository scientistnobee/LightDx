"""
make_slim_design_page.py - renders the slim_puck STLs (no FreeCAD needed) and writes
LightDx_slim_puck_design.html (self-contained: renders + photos embedded as base64).

Run:  python make_slim_design_page.py
Reads Slim_Puck_Base.stl / Slim_Puck_Lid.stl (assembled coordinates) and the three
measurement photos; writes renders/*.png and the html next to this script.
The model numbers below mirror build_slim_puck.py (2026-10-13 build, pre-measurement estimates).
"""
import base64, io, os, struct, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "renders")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- mesh helpers
def load_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        v = np.array(re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data), dtype=float)
        return v.reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return rec["v"].astype(float)


def box_tris(x0, x1, y0, y1, z0, z1):
    p = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array([[p[a], p[b], p[c]] for a, b, c in f])


def rot(az, el):
    """Rotation: world (x right, y depth-ish, z up) -> screen. az about z, el about x."""
    a, e = np.radians(az), np.radians(el)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return Rx @ Rz


def render(items, az, el, fname, size=(1500, 1000), pad=0.06, title=None):
    """items: list of (tris, rgb, alpha). Painter's algorithm, flat shading."""
    R = rot(az, el)
    light = np.array([-0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    allp = []
    for tris, rgb, alpha in items:
        t = tris @ R.T
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1
        n = n / ln[:, None]
        # screen: x right, y up is index 2 after Rx? use (x, z) as 2D, y as depth (toward viewer = negative)
        facing = n[:, 1] < 0 if alpha >= 1 else np.ones(len(n), bool)
        sh = 0.35 + 0.65 * np.abs(n @ (R @ light))
        for i in np.nonzero(facing)[0]:
            polys.append(t[i][:, [0, 2]])
            c = np.clip(np.array(rgb) * sh[i], 0, 1)
            cols.append((*c, alpha))
            depth.append(t[i][:, 1].mean())
        allp.append(t[:, :, [0, 2]].reshape(-1, 2))
    allp = np.vstack(allp)
    order = np.argsort(depth)[::-1]
    polys = [polys[i] for i in order]; cols = [cols[i] for i in order]
    fig = plt.figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect("equal"); ax.axis("off")
    pc = PolyCollection(polys, facecolors=cols, edgecolors=[(0, 0, 0, 0.25)] * len(polys), linewidths=0.3)
    ax.add_collection(pc)
    lo, hi = allp.min(0), allp.max(0); span = (hi - lo).max()
    ax.set_xlim(lo[0] - span * pad, hi[0] + span * pad)
    ax.set_ylim(lo[1] - span * pad, hi[1] + span * pad)
    fig.savefig(os.path.join(OUT, fname), facecolor="white")
    plt.close(fig)
    return fname


# ---------------------------------------------------------------- model numbers (build_slim_puck.py)
# FreeCAD renders (saved from the open model by the MCP; STL/matplotlib renderer above is only a fallback)
renders = {
    "assembled": "fc_assembled_iso.png", "assembled_back": "fc_assembled_top.png",
    "exploded": "fc_base_open_iso.png", "base_open": "fc_base_open_top.png",
    "lid_top": "fc_lid_iso.png", "lid_under": "fc_lid_underside.png",
    "front": "fc_front_usb_end.png", "back": "fc_far_end.png",
}
print("renders:", renders)


# ---------------------------------------------------------------- embedding
def b64_png(path):
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def b64_jpg(path, maxw=1000):
    im = Image.open(path).convert("RGB"); im.thumbnail((maxw, maxw))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


R = {k: b64_png(os.path.join(OUT, v)) for k, v in renders.items()}
P = {k: b64_jpg(os.path.join(HERE, f)) for k, f in (("together", "all_together.jpeg"), ("battery", "battery1.jpeg"), ("board", "caspule_board.jpeg"))}

# ---------------------------------------------------------------- SVG: side stack comparison
def stack_svg():
    s = 28  # px per mm
    W, H = 1010, 450
    base_y = 395
    def rect(x, h, w, fill, label, ytop_offset=0, textcol="#111"):
        y = base_y - (h + ytop_offset) * s
        return (f'<rect x="{x}" y="{y:.1f}" width="{w}" height="{h * s:.1f}" fill="{fill}" stroke="#222" stroke-width="1"/>'
                f'<text x="{x + w / 2}" y="{y + h * s / 2 + (4 if h * s >= 15 else 3):.1f}" text-anchor="middle" font-size="{12 if h * s >= 15 else 9}" fill="{textcol}">{label}</text>')
    def col(x0, title, parts, total, note):
        out = [f'<text x="{x0 + 80}" y="24" text-anchor="middle" font-size="14" font-weight="600" fill="currentColor">{title}</text>']
        z = 0
        for h, fill, label, tc in parts:
            out.append(rect(x0, h, 160, fill, label, z, tc)); z += h
        out.append(f'<line x1="{x0 + 170}" y1="{base_y}" x2="{x0 + 170}" y2="{base_y - total * s:.1f}" stroke="currentColor" stroke-width="1.2"/>')
        out.append(f'<text x="{x0 + 178}" y="{base_y - total * s / 2:.1f}" font-size="13" fill="currentColor">{total:.1f} mm</text>')
        out.append(f'<text x="{x0 + 80}" y="{base_y + 22}" text-anchor="middle" font-size="12" fill="currentColor">{note}</text>')
        return "".join(out)
    cur = [(1.2, "#8a8f98", "floor 1.2", "#111"), (6.0, "#5b86d6", "cell 6.0 (est.)", "#fff"),
           (0.5, "#fff", "gap 0.5", "#111"), (3.0, "#e0a050", "AS7341 pocket 3.0", "#111"), (2.0, "#b5bac4", "lid 2.0", "#111")]
    new = [(1.2, "#8a8f98", "floor 1.2", "#111"), (4.5, "#5b86d6", "battery 4.5", "#fff"),
           (2.5, "#e0a050", "AS7341 2.5", "#111"), (0.3, "#fff", "clr 0.3", "#111"), (2.0, "#b5bac4", "lid 2.0", "#111")]
    cap_cur = [(1.2, "#8a8f98", "floor 1.2", "#111"), (7.0, "#3fb35a", "Capsule 7.0 (est.)", "#fff"), (2.5, "#fff", "air 2.5", "#111"), (2.0, "#b5bac4", "lid 2.0", "#111")]
    cap_new = [(1.2, "#8a8f98", "floor 1.2", "#111"), (6.0, "#3fb35a", "Capsule 6.0", "#fff"), (0.3, "#fff", "clr 0.3", "#111"), (2.0, "#b5bac4", "lid 2.0", "#111")]
    parts = (col(10, "Sensor side: now", cur, 12.7, "battery + AS7341 stack") +
             col(260, "Sensor side: measured", new, 9.0 + 1.5, "stack 7.0 + 0.3") +
             col(510, "Capsule side: now", cap_cur, 12.2, "pocket sized to 12.7") +
             col(760, "Capsule side: measured", cap_new, 9.5, ""))
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Height stacks, current model versus measured parts" style="width:100%;height:auto">'
            f'<line x1="0" y1="{base_y}" x2="{W}" y2="{base_y}" stroke="currentColor" stroke-width="1" opacity="0.4"/>{parts}</svg>')


# ---------------------------------------------------------------- SVG: plan with dimensions
from slim_plan_svg import plan_svg


HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LightDx slim_puck design</title>
<style>
:root {{ --bg:#f6f7f9; --fg:#14171c; --mut:#5a6270; --card:#fff; --line:#d9dde4; --acc:#1f5fbf; --warn:#a8570a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14171c; --fg:#e8ebf0; --mut:#9aa3b2; --card:#1d2229; --line:#2f3743; --acc:#7fb0ff; --warn:#f0a35a; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif; }}
main {{ max-width:1000px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:1.8rem; margin:0 0 4px; }} h2 {{ font-size:1.25rem; margin:36px 0 8px; }} h3 {{ font-size:1rem; margin:0 0 6px; }}
p.sub {{ color:var(--mut); margin:0 0 20px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
.grid {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); }}
img {{ max-width:100%; height:auto; border-radius:6px; display:block; background:#fff; }}
figure {{ margin:0; }} figcaption {{ color:var(--mut); font-size:.88rem; margin-top:6px; }}
table {{ width:100%; border-collapse:collapse; font-size:.95rem; }}
th,td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--mut); font-weight:600; }}
td.n {{ font-variant-numeric:tabular-nums; white-space:nowrap; }}
.tag {{ display:inline-block; font-size:.75rem; padding:1px 7px; border-radius:99px; border:1px solid var(--line); color:var(--mut); }}
.warn {{ color:var(--warn); }} .acc {{ color:var(--acc); }}
.scroll {{ overflow-x:auto; }}
.chg th:nth-child(1) {{ width:17%; }} .chg th:nth-child(2), .chg th:nth-child(3) {{ width:21%; }} .chg th:nth-child(4) {{ width:41%; }}
.chg td.n {{ white-space:normal; }}
</style></head><body><main>
<h1>LightDx slim_puck</h1>
<p class="sub">Design page, 2026-10-15 (updated with the feedback from the second print). Renders are FreeCAD views of the saved model <code>Square_puck_v2.FCStd</code> (Slim_Base, Slim_Lid); the STLs in the folder match it, and the state is committed to GitHub (tag <code>slim-puck-print2</code>). Heights are still the old estimates (12.7 mm total). Measurements are the user's caliper readings from 2026-10-15.</p>

<h2>Changes since the first print (2026-10-15, including the second-print feedback)</h2>
<div class="card scroll"><table class="chg">
<tr><th>Item</th><th>First printed version</th><th>Current model</th><th>Why</th></tr>
<tr><td>Box length (X)</td><td class="n">42.4 mm</td><td class="n acc">40.4 mm</td><td>2 mm spare along X beside the Capsule: 1 mm shaved off each end</td></tr>
<tr><td>Capsule pocket length</td><td class="n">40.4 mm</td><td class="n acc">38.4 mm</td><td>same; USB-C connector now pokes about 1.5 mm further into its window</td></tr>
<tr><td>Box width (Y), Capsule / battery pocket width</td><td class="n">50.0 / 24.4 / 20.4 mm</td><td class="n acc">50.6 / 24.4 / 21.0 mm</td><td>the 2 mm spare was in X, so the Capsule width is unchanged; the battery pocket got +0.6 mm for wires and tape</td></tr>
<tr><td>USB-C window height</td><td class="n">centre z 5.7 mm</td><td class="n acc">centre z 6.9 mm (+1.2)</td><td>connector sat higher than the window</td></tr>
<tr><td>Diffuser seat diameter</td><td class="n">11.2 mm</td><td class="n acc">12.0 mm</td><td>printed too small; 12.4 was then 0.4 mm too big</td></tr>
<tr><td>G42 pusher nub and tongue</td><td class="n">nub at (18.2, 8.4)</td><td class="n acc">(16.2, 10.7): 2 mm left, 3 mm up</td><td>lid photo (2 mm left, 2 mm up), then second print: 1 mm further up and a 1.5 mm shorter nub (bottom z 7.5, was 6.0)</td></tr>
<tr><td>Lid power-LED opening</td><td class="n">round hole dia 2.0 at (15.2, 8.5)</td><td class="n acc">slit 1.6 x 3.4 (long in Y) at (13.2, 10.7)</td><td>user: USB-C-like slit, centred on the tongue in Y (y 10.7, same as the nub)</td></tr>
<tr><td>Far-wall RGB LED window</td><td class="n">y 15.2</td><td class="n acc">y 16.7, centre z 4.9 (was 3.4)</td><td>second print: 1 mm down in Y, 1.5 mm up in height (BOOT-to-RGB spacing is now 6.4 mm; 6.0 measured)</td></tr>
<tr><td>Far-wall BOOT hole</td><td class="n">y 8.4</td><td class="n acc">y 10.3</td><td>second print: 1 mm up in Y</td></tr>
<tr><td>Height</td><td class="n">12.7 mm</td><td class="n">12.7 mm (unchanged)</td><td>heights worked well</td></tr>
</table>
<p class="warn" style="margin:10px 0 0">The second-print changes are not printed yet. Screw blocks at the X ends are now 5.75 mm wide, so a small screw head is needed (the 4.4 mm counterbore leaves about 0.7 mm to the outside).
y values are in the figure frame of section 4 (box centre = 0); the printed box is drawn dashed there.</p></div>

<h2>1. Measured parts</h2>
<div class="card scroll"><table>
<tr><th>Part</th><th>Measured (2026-10-15)</th><th>Model used until now</th></tr>
<tr><td>Capsule board (headers incl., no shell)</td><td class="n">6 mm tall</td><td class="n">7 mm (estimate)</td></tr>
<tr><td>Battery alone</td><td class="n">4.5 mm</td><td class="n">6 mm (602025 nominal)</td></tr>
<tr><td>AS7341 board, connectors removed</td><td class="n">2.5 mm</td><td class="n">2.8 mm (pocket 3.0)</td></tr>
<tr><td>Battery + AS7341 stacked</td><td class="n">7 mm tall, 25 mm long, 20 mm wide</td><td class="n">6 + 0.5 gap + 3.0 = 9.5 tall; pocket 27.9 x 20.4</td></tr>
</table></div>
<div class="grid" style="margin-top:14px">
<figure class="card"><img alt="Capsule board, battery and AS7341 laid out on a table" src="{P['together']}"><figcaption>Capsule underside (SD slot, USB-C, side switch at the end), battery and the AS7341 wired to it.</figcaption></figure>
<figure class="card"><img alt="Battery and AS7341 stacked, held between two fingers" src="{P['battery']}"><figcaption>Battery + AS7341 stack seen from the side: the 7 mm figure.</figcaption></figure>
<figure class="card"><img alt="Capsule board from the side with header labels" src="{P['board']}"><figcaption>Capsule board from the side: PCB with the labelled header strip on top, SD/USB parts underneath. 6 mm overall.</figcaption></figure>
</div>

<h2>2. Height: what the new numbers change</h2>
<div class="card">{stack_svg()}
<p style="margin:8px 0 0;color:var(--mut)">Left pair: the AS7341-over-battery stack (it sets the box height). Right pair: the Capsule side, which has spare depth. Clearances of 0.3 mm are proposed values, not measured.</p></div>
<div class="card scroll" style="margin-top:14px"><table>
<tr><th>Dimension</th><th>Built (exported STLs)</th><th>Proposed with measured parts</th></tr>
<tr><td>Total height</td><td class="n">12.7 mm (base 10.7 + lid 2.0)</td><td class="n acc">about 10.5 mm (base 8.5 + lid 2.0)</td></tr>
<tr><td>Sensor stack under the lid</td><td class="n">9.5 mm (cell 6 + gap 0.5 + AS7341 pocket 3)</td><td class="n">7.3 mm (7.0 stack + 0.3)</td></tr>
<tr><td>Capsule pocket depth</td><td class="n">10.2 mm (7.0 + 3.2 spare)</td><td class="n">7.3 mm (6.0 + 1.3 spare)</td></tr>
<tr><td>Battery + AS7341 pocket</td><td class="n">27.9 x 21.0</td><td class="n">25.8 x 20.4 (25 + 0.8, 20 + 0.4)</td></tr>
<tr><td>Footprint</td><td class="n">40.4 x 50.6 (printed 42.4 x 50.0)</td><td class="n">40.4 x 50.6 (proposal keeps this)</td></tr>
</table>
<p class="warn" style="margin:10px 0 0">Check before rebuilding: the Adafruit AS7341 board is 25.4 mm long, slightly more than the 25 mm you measured for the stack. I would keep the pocket at 25.8 mm so the board fits either way. Not rebuilt yet: the STLs are unchanged.</p></div>

<h2>3. Renders of the exported model</h2>
<div class="grid">
<figure class="card"><img alt="Assembled slim puck, front-left view" src="{R['assembled']}"><figcaption>Assembled, 40.4 x 50.6 x 12.7 mm. Diffuser seat dia 12.0 mm; G42 button tongue and power-LED hole in the lid.</figcaption></figure>
<figure class="card"><img alt="Assembled slim puck from above" src="{R['assembled_back']}"><figcaption>Top view of the assembled box.</figcaption></figure>
</div>
<figure class="card" style="margin-top:14px"><img alt="Base with Capsule, battery and AS7341 envelopes" src="{R['exploded']}"><figcaption>Base with part envelopes: green = Capsule (40 x 24 x 7), blue = battery (27.5 x 20 x 6), orange = AS7341 board held by four lid pins above the cell.</figcaption></figure>
<div class="grid" style="margin-top:14px">
<figure class="card"><img alt="Base from above with part envelopes" src="{R['base_open']}"><figcaption>Base, plan: Capsule pocket (top), battery + AS7341 pocket (bottom), divider with the two cable notches at x = -11 and +11.</figcaption></figure>
<figure class="card"><img alt="Lid from above" src="{R['lid_top']}"><figcaption>Lid, top: diffuser seat and the U-slot tongue over the G42 button.</figcaption></figure>
<figure class="card"><img alt="Lid from below" src="{R['lid_under']}"><figcaption>Lid, underside: four base-screw posts, four AS7341 pillars with pins, and the button nub.</figcaption></figure>
</div>
<div class="grid" style="margin-top:14px">
<figure class="card"><img alt="USB end of the box" src="{R['front']}"><figcaption>USB-C end (-X): 9.4 x 3.8 mm window.</figcaption></figure>
<figure class="card"><img alt="Far end of the box" src="{R['back']}"><figcaption>Far end (+X): RGB LED window and BOOT hole (positions estimated).</figcaption></figure>
</div>

<h2>4. Plan with X and Y axes (current model vs first print)</h2>
<p class="sub" style="margin-bottom:8px">Looking down on the base. X runs left to right (USB end at -X, far end at +X), Y runs bottom to top (battery/AS7341 side at -Y, Capsule side at +Y). Origin is the box centre; all positions in mm. In this figure "horizontal" = X and "vertical" = Y.</p>
<div class="card">{plan_svg()}</div>

<h2>5. Feature list and status</h2>
<div class="card scroll"><table>
<tr><th>Feature</th><th>Value</th><th>Status</th></tr>
<tr><td>Outline, height</td><td class="n">40.4 x 50.6 x 12.7 mm; floor 1.2, lid 2.0, end walls 1.0, side walls 2.0</td><td><span class="tag">built</span></td></tr>
<tr><td>Capsule pocket</td><td class="n">38.4 x 24.4 (battery pocket 27.9 x 21.0); USB-C connector should now stick out about 1.5 mm past the front wall (it touched the wall in the print)</td><td><span class="tag">built</span></td></tr>
<tr><td>USB-C window</td><td class="n">9.4 x 3.8, centre z 6.9 (raised 1.2 after the print)</td><td><span class="tag">height to verify</span></td></tr>
<tr><td>AS7341 retention</td><td class="n">4 lid pins, 2.0 mm, no screws</td><td><span class="tag">fit to verify</span></td></tr>
<tr><td>Diffuser seat</td><td class="n">dia 12.0 (was 11.2, then 12.4), 1.5 deep; aperture dia 10; rim under the diffuser 0.5 thick. The diffuser is 2.0 mm thick, so it stands 0.5 mm proud of the lid; no raised ring (kept thin on purpose, to be checked with the manufacturer)</td><td><span class="tag">built</span></td></tr>
<tr><td>Divider notches</td><td class="n">4 mm wide at x = +11 (battery lead), -11 (I2C cable)</td><td><span class="tag">built</span></td></tr>
<tr><td>G42 button</td><td class="n">U-slot tongue 7 x 8.9, slot 0.8, nub at (16.2, 10.7), nub bottom z 7.5 (1.5 mm shorter)</td><td><span class="tag">estimated</span></td></tr>
<tr><td>Power LED</td><td class="n">slit 1.6 x 3.4 (long in Y) in the lid at (13.2, 10.7) (position a guess)</td><td><span class="tag">estimated</span></td></tr>
<tr><td>RGB LED (G21, side mounted)</td><td class="n">3.0 x 1.6 window in the far wall at y 16.7, z 4.9</td><td><span class="tag">estimated</span></td></tr>
<tr><td>BOOT (G0, side mounted)</td><td class="n">dia 2.4 hole in the far wall at y 10.3, z 3.0</td><td><span class="tag">estimated</span></td></tr>
<tr><td>Base screws</td><td class="n">4 x M2 x 8 from below</td><td><span class="tag">built</span></td></tr>
</table></div>
<p class="sub" style="margin-top:20px">Sources: <code>build_slim_puck.py</code>, <code>LEARNINGS.md</code> ("Enclosure: v3 and slim_puck"), memory note on the 2026-10-15 measurements. Regenerate this page with <code>make_slim_design_page.py</code>.</p>
</main></body></html>
"""
open(os.path.join(HERE, "LightDx_slim_puck_design.html"), "w", encoding="utf-8").write(HTML)
print("wrote html", len(HTML) // 1024, "KB")
