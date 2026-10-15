"""
build_slim_puck.py (derived from build_box_enclosure.py v3, 2026-10-13)

slim_puck: JST/STEMMA connectors removed from the AS7341 and the Capsule, so both stacks shrink.
ESTIMATES (not measured, correct after printing): Capsule 7.0 mm tall, AS7341 board+parts 2.8 mm.
Objects: Slim_Base / Slim_Lid (+ Ref_Slim_*), Box_* left untouched.

Parametric build script for the squarish LightDx enclosure ("Box_Base" + "Box_Lid"),
replacing the round puck (build_puck_enclosure.py, left untouched). Same style: plain
Part-module CSG, edit PARAMETERS, re-run with the doc open, save.

Layout (Z up, Z=0 = bottom of the box, box centred on X/Y = 0):
  Box_Base  floor + one tall electronics layer, two pockets stacked along Y:
              y > 0 side  M5Capsule (40 x 24 x 14, USB-C end toward -X)
              y < 0 side  250 mAh LiPo pocket (30.4 x 20.4) that ALSO holds the AS7341 board,
                          which floats above the cell (z_pcb) held by the lid's posts
            divider wall with a battery-lead notch, USB-C plug window through the -X end wall,
            AS7341 JST plug slots at both ends of the sensor, 4 M2 holes through the thick
            blocks beside the battery pocket (counterbore below, locating recess above).
  Box_Lid   thin plate (lid_t): stepped diffuser aperture (sensor looks up), 1 mm recess for the
            top of the Capsule, 4 posts that hold the AS7341 (M2 screws come UP through its
            corner holes into the posts), 4 locating posts with blind pilots for the base screws.

The total height is the taller of the Capsule stack (floor + layer + 1.5 roof) and the sensor
stack (floor + cell + screw-head gap + AS7341 + lid plate). Raising the split plane (thicker
base, thinner lid) does not change it.

Measured by the user (2026-10-02): Capsule 40.0 x 24.0 x 14.0 (bare board + headers, no
shell); battery fits a 30.4 x 20.4 pocket; first rectangular print fitted well (2026-10-03).
ASSUMED: USB-C window height, battery-lead notch position, battery thickness (6 mm).
"""

import Part
import FreeCAD as App


# ============================== PARAMETERS ==============================

# --- Electronics ---
cap_l, cap_w, cap_h = 41.0, 24.0, 7.0        # Capsule board + headers; length 40 -> 41 (2026-10-13, 40.4 pocket was too tight)
cell_l, cell_w, cell_t = 27.5, 20.6, 6.0     # LiPo (fits 30.4 x 20.4; 602025 -> 6 mm)
clr = 0.2                                    # per-side pocket clearance
cap_pl, cap_pw = cap_l + 2 * clr, cap_w + 2 * clr
cell_pl, cell_pw = cell_l + 2 * clr, cell_w + 2 * clr
divider = 1.2

# --- Shell ---
end_wall = 1.0         # X ends: just a wall (screws moved beside the battery pocket)
side_wall = 2.0
floor_t = 1.2
layer_h = cap_h + 0.5  # Capsule layer height (0.5 headroom)
min_roof = 1.5         # minimum lid material over the Capsule
corner_r = 4.0

# --- AS7341 board (floats above the battery) ---
pcb_thickness = 1.57           # bare PCB; components stand above this to 4.53
pocket_depth = 3.0             # PCB bottom to lid underside (4.53 tall + clearance)
top_t = 2.0                    # lid thickness over the sensor (seat 1.5 + shoulder 0.5)
head_gap = 0.5                 # cell top to PCB bottom; AS7341 now held by lid pins (no screws), so only clearance

# Total height = the taller of the two stacks (Capsule layer + roof, or cell + screw heads + AS7341 + lid)
total_capsule = floor_t + layer_h + min_roof
total_sensor = floor_t + cell_t + head_gap + pocket_depth + top_t
total_h = max(total_capsule, total_sensor)
roof_t = total_h - floor_t - layer_h         # actual lid material over the Capsule

lid_t = top_t                  # lid is just this plate (+ posts below, recess)
base_h = total_h - lid_t       # split plane
z_pcb = base_h - pocket_depth  # PCB bottom, head_gap (or more) above the 6 mm cell
lid_recess = max(0.0, (floor_t + layer_h) - base_h)    # Capsule recess depth in the lid

# --- Plan layout: pockets stacked along Y (Capsule at +Y, battery at -Y), centred in X ---
cap_inset = 1.0                    # Capsule's USB-C end pokes this far into the front wall window (2026-10-13)
x_shave = 1.0                      # print feedback 2026-10-15: ~3 mm spare beside the board at both X ends -> shave 1.5 mm off each end
cap_plx = cap_pl - cap_inset - 2 * x_shave   # pocket length along X (37.4)
L_out = 2 * end_wall + cap_plx          # closed again: 1.0 mm end walls, USB-C window in the -X wall
W_out = 2 * side_wall + cap_pw + divider + cell_pw
cap_x0, cap_x1 = -cap_plx / 2, cap_plx / 2
cell_x0, cell_x1 = -cell_pl / 2, cell_pl / 2
cell_y0 = -W_out / 2 + side_wall
cell_y1 = cell_y0 + cell_pw
cap_y0 = cell_y1 + divider
cap_y1 = cap_y0 + cap_pw
cap_cy = (cap_y0 + cap_y1) / 2
feat_cy = cap_y0 + 12.2        # Capsule features keep their y from the divider wall (old 24.4 pocket centre); print showed 2 mm spare on the outer side
cell_cx, cell_cy = 0.0, (cell_y0 + cell_y1) / 2   # sensor / aperture centre

# --- USB-C plug window through the -X end wall, cut through both parts ---
# From PXL_20261002_214107806C.jpg (end-on): USB-C ~2.5 mm below the Capsule's sticker (top)
# face, ~centred across the width; Capsule is placed sticker-up. Sized for a plug overmould.
usb_w, usb_h = 9.4, 3.8      # just the USB-C connector (8.94 x 3.26 + 0.25/side); it pokes through this window
usb_zc = floor_t + cap_h - 2.5 + 1.2   # print feedback 2026-10-15: connector sits >= 1 mm higher
usb_z0, usb_z1 = usb_zc - usb_h / 2, usb_zc + usb_h / 2

# --- Battery lead notch through the divider (x position, ASSUMED) ---
lead_x, lead_w = 11.0, 4.0
i2c_x = -11.0   # I2C (STEMMA QT) cable notch, same size as the lead notch, at the other end (2026-10-13)
lead_z0 = floor_t + 1.0

# --- Base screws (4x M2x8 from the underside) in the solid blocks beside the battery pocket.
#     Lid has 4 locating posts that drop into recesses in the base top and hold the pilots. ---
screw_x = (cell_pl / 2 + L_out / 2) / 2
screw_ys = (cell_cy - 7.7, cell_cy + 7.7)
screw_xy = [(sx * screw_x, sy) for sx in (1, -1) for sy in screw_ys]
clear_r, cbore_r, cbore_depth = 1.3, 2.2, 2.2
post_r, post_len = 2.0, 4.0            # lid locating posts
recess_r = post_r + 0.3                # base recess for them
tap_r = 0.9                            # M2 self-tap pilot
tap_depth = post_len + 1.5             # blind, from the post bottom (leaves 1 mm skin on top)

# --- Capsule LEDs + G42 button access in the lid (positions ESTIMATED from enclosure2.jpeg, 2026-10-13;
#     the flap/U-slot idea comes from the Capsule_v1.1.stl end cap: U-slot flap hinged on the inner side).
#     x measured from the Capsule's far (button) end, y from the Capsule centre line (- = sensor side). ---
cap_end_x = (cap_pl - cap_inset) / 2 - clr          # far end of the Capsule board: fixed in box coordinates (the shave is symmetric)
g42_y = feat_cy - 3.4                                # G42 tactile switch y (also the base-wall BOOT / RGB reference)
btn_x, btn_y = cap_end_x - 1.8 - 2.0, g42_y + 3.0   # pusher nub: moved 2 mm toward the USB end and 2 mm toward +Y after the print (2026-10-15)
led_w, led_l = 1.6, 3.4                            # lid LED opening: USB-C-like slit, width along X, length along Y (stadium)
led_x, led_y = cap_end_x - 4.8 - 2.0, btn_y               # white-outlined chip next to the button (power LED?), y aligned with the tongue (user 2026-10-15)
wall_dy = 3.0                                     # far-wall holes moved 4 mm toward +Y (print feedback 2026-10-15)
# Side-mounted parts at the board's far edge fire through the base's far (+X) end wall (ESTIMATED z: PCB top ~2.8 mm):
rgb_y, rgb_w, rgb_h, rgb_zc = g42_y + 6.0 + wall_dy, 3.0, 1.6, 4.9   # RGB LED (G21) window: width along y, height, centre z
boot_y, boot_r, boot_zc = feat_cy - 0.8, 1.2, 3.0                    # side BOOT (G0) switch below the G42 switch: 2.4 mm poke hole
tongue_hw, tongue_len, slot_w = 3.5, 8.9, 0.8      # tongue half width, length (hinge on the inner side), U-slot width
nub_r, nub_z0 = 1.2, 7.5                           # pusher under the tongue; bottom z (ASSUMED switch height)

# --- Lid aperture (carried over from the puck) ---
diffuser_t, rim_t, boss_r = 2.0, 0.5, 8.0   # diffuser disc 2.0 thick; ledge under it 0.5 (user 2026-10-15: no raised ring, 1.0 not needed; the disc stands 0.5 proud)
seat_radius, seat_depth = 6.0, top_t - rim_t   # diffuser seat dia 12.0, 1.5 deep
shoulder_inner_radius = 5.0
boss_h = seat_depth + rim_t - top_t         # boss on the lid top: 1.0 mm, so seat (2.0) + rim (1.0) fit in lid 2.0 + boss
shoulder_depth = rim_t
rim_enabled = False
rim_outer_r, rim_inner_r, rim_height = 9.0, 8.25, 2.0

# AS7341 retention posts (puck pattern rotated 90 deg), from the PCB's component face up to the lid
pcb_screw_xy = [(10.16, 6.35), (-10.16, 6.35), (10.16, -6.35), (-10.16, -6.35)]
pillar_r = 2.0
pin_r = 1.0   # lid pin through each AS7341 corner hole (hole ~2.2 dia), replaces the M2 screws

# JST plug slots in the base, along X at both ends of the sensor; y relative to sensor centre
jst_x_inner, jst_x_outer = cell_pl / 2 - 0.3, 17.5   # measured from the sensor centre
jst_y_min, jst_y_max = -4.5, 3.5

# ==========================================================================


def V(x, y, z):
    return App.Vector(x, y, z)


def box(x0_, x1_, y0_, y1_, z0_, z1_):
    return Part.makeBox(x1_ - x0_, y1_ - y0_, z1_ - z0_, V(x0_, y0_, z0_))


def rounded_block(z0_, h):
    """Rounded-rectangle prism covering the full outline."""
    blk = box(-L_out / 2, L_out / 2, -W_out / 2, W_out / 2, z0_, z0_ + h)
    edges = [e for e in blk.Edges
             if abs(e.Vertexes[0].Point.x - e.Vertexes[1].Point.x) < 1e-6
             and abs(e.Vertexes[0].Point.y - e.Vertexes[1].Point.y) < 1e-6]
    return blk.makeFillet(corner_r, edges)


def build_base():
    solid = rounded_block(0, base_h)
    top = base_h
    ax, ay = cell_cx, cell_cy
    tools = [
        box(cap_x0, cap_x1, cap_y0, cap_y1, floor_t, top + 1),
        box(cell_x0, cell_x1, cell_y0, cell_y1, floor_t, top + 1),
        # USB-C plug window out through the -X end wall
        box(-L_out / 2 - 1, cap_x0 + 0.1, feat_cy - usb_w / 2, feat_cy + usb_w / 2, usb_z0, usb_z1),
        # RGB LED window and BOOT switch hole through the far end wall
        box(cap_x1 - 0.1, L_out / 2 + 1, rgb_y - rgb_w / 2, rgb_y + rgb_w / 2, rgb_zc - rgb_h / 2, rgb_zc + rgb_h / 2),
        Part.makeCylinder(boot_r, L_out / 2 + 1 - cap_x1 + 0.1, V(cap_x1 - 0.1, boot_y, boot_zc), V(1, 0, 0)),
        # battery lead notch through the divider, open on top
        box(lead_x - lead_w / 2, lead_x + lead_w / 2, cell_y1 - 0.1, cap_y0 + 0.1, lead_z0, top + 1),
        # I2C cable notch through the divider, mirrored to the other end
        box(i2c_x - lead_w / 2, i2c_x + lead_w / 2, cell_y1 - 0.1, cap_y0 + 0.1, lead_z0, top + 1),
    ]
    # AS7341 JST plug slots beyond the ends of the pocket, from the PCB level up
    for sign in (1, -1):
        xa, xb = sorted((ax + sign * jst_x_inner, ax + sign * jst_x_outer))
        tools.append(box(xa, xb, ay + jst_y_min, ay + jst_y_max, z_pcb - 0.5, top + 1))
    for (x, y) in screw_xy:
        tools.append(Part.makeCylinder(clear_r, base_h + 2, V(x, y, -1)))
        tools.append(Part.makeCylinder(cbore_r, cbore_depth + 1, V(x, y, -1)))
        tools.append(Part.makeCylinder(recess_r, post_len + 0.3 + 1, V(x, y, top - post_len - 0.3)))
    for t in tools:
        solid = solid.cut(t)
    return solid.removeSplitter()


def build_lid():
    z0 = base_h
    ztop = z0 + lid_t
    ax, ay = cell_cx, cell_cy
    solid = rounded_block(z0, lid_t)

    if boss_h > 0:
        solid = solid.fuse(Part.makeCylinder(boss_r, boss_h + 0.1, V(ax, ay, ztop - 0.1)))

    # Posts hang below the plate: 4 locating posts for the base screws, 4 for the AS7341
    for (x, y) in screw_xy:
        solid = solid.fuse(Part.makeCylinder(post_r, post_len + 0.5, V(x, y, z0 - post_len)))
    pillar_z0 = z0 - pocket_depth + pcb_thickness        # PCB component face
    for (x, y) in pcb_screw_xy:
        solid = solid.fuse(Part.makeCylinder(pillar_r, z0 + 0.5 - pillar_z0, V(ax + x, ay + y, pillar_z0)))
        solid = solid.fuse(Part.makeCylinder(pin_r, pcb_thickness + 0.01, V(ax + x, ay + y, pillar_z0 - pcb_thickness)))

    tools = [
        # recess for the top of the Capsule (same XY as its base pocket)
        box(cap_x0, cap_x1, cap_y0, cap_y1, z0 - 0.5, z0 + max(lid_recess, 0.1)),
        # USB-C plug window through the -X end wall of the lid
        # stepped aperture: seat (disk) cut from the top, shoulder through the plate below
        Part.makeCylinder(seat_radius, seat_depth + 0.5, V(ax, ay, ztop + boss_h - seat_depth)),
        Part.makeCylinder(shoulder_inner_radius, top_t + boss_h - seat_depth + 1.0, V(ax, ay, ztop - top_t - 0.5)),
    ]
    if usb_z1 > z0 - 0.5:   # USB window reaches into the lid only if the Capsule is tall
        tools.append(box(-L_out / 2 - 1, cap_x0 + 0.1, feat_cy - usb_w / 2, feat_cy + usb_w / 2, z0 - 0.5, usb_z1))
    # LED holes
    # LED slit (stadium, long in Y)
    tools.append(box(led_x - led_w / 2, led_x + led_w / 2, led_y - (led_l - led_w) / 2, led_y + (led_l - led_w) / 2, z0 - 1, ztop + 1))
    for sy in (1, -1):
        tools.append(Part.makeCylinder(led_w / 2, lid_t + 2, V(led_x, led_y + sy * (led_l - led_w) / 2, z0 - 1)))
    # U-slot around the G42 button tongue (hinge at the inner end, free end toward the far wall)
    t_x1 = btn_x + 1.2                          # free end of the tongue (1.2 mm beyond the nub)
    t_x0 = t_x1 - tongue_len                    # hinge line
    for sgn in (1, -1):
        ya, yb = sorted((btn_y + sgn * tongue_hw, btn_y + sgn * (tongue_hw + slot_w)))
        tools.append(box(t_x0, t_x1 + slot_w, ya, yb, z0 - 1, ztop + 1))
    tools.append(box(t_x1, t_x1 + slot_w, btn_y - tongue_hw - slot_w, btn_y + tongue_hw + slot_w, z0 - 1, ztop + 1))
    for t in tools:
        solid = solid.cut(t)
    solid = solid.fuse(Part.makeCylinder(nub_r, z0 + 0.1 - nub_z0, V(btn_x, btn_y, nub_z0)))
    # blind self-tap pilots (base screws and AS7341 screws), opening downward
    for (x, y) in screw_xy:
        solid = solid.cut(Part.makeCylinder(tap_r, tap_depth + 0.5, V(x, y, z0 - post_len - 0.5)))


    if not rim_enabled:
        return solid.removeSplitter()
    rim = Part.makeCylinder(rim_outer_r, rim_height, V(ax, ay, ztop)).cut(
        Part.makeCylinder(rim_inner_r, rim_height + 1, V(ax, ay, ztop - 0.5)))
    return solid.fuse(rim).removeSplitter()


def pcb_envelope():
    """AS7341 board (1.57) + its two JST connectors (to 4.53), the tall parts, at z_pcb."""
    ax, ay = cell_cx, cell_cy
    s = box(ax - 12.7, ax + 12.7, ay - 8.89, ay + 8.89, z_pcb, z_pcb + pcb_thickness)
    s = s.fuse(box(ax - 8, ax + 8, ay - 6, ay + 6, z_pcb + pcb_thickness, z_pcb + 2.8))   # chips + LED, connectors removed
    return s


def ensure(doc, name, label, shape, color, transparency=0):
    obj = doc.getObject(name)
    if obj is None:
        obj = doc.addObject("Part::Feature", name)
        obj.Label = label
    obj.Shape = shape
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.Transparency = transparency
    return obj


def build_and_apply(doc_name="Reused_Parts"):
    doc = App.getDocument(doc_name)
    base = ensure(doc, "Slim_Base", "Slim Base", build_base(), (0.15, 0.15, 0.15))
    lid = ensure(doc, "Slim_Lid", "Slim Lid", build_lid(), (0.25, 0.25, 0.25))
    cap = ensure(doc, "Ref_Slim_Capsule", "Ref Slim Capsule",
                 box(cap_x0 + clr, cap_x1 - clr, cap_cy - cap_w / 2, cap_cy + cap_w / 2,
                     floor_t, floor_t + cap_h), (0.2, 0.7, 0.3), 40)
    cell = ensure(doc, "Ref_Slim_Battery", "Ref Slim Battery",
                  box(cell_cx - cell_l / 2, cell_cx + cell_l / 2, cell_cy - cell_w / 2,
                      cell_cy + cell_w / 2, floor_t, floor_t + cell_t), (0.2, 0.4, 0.8), 40)
    pcb = ensure(doc, "Ref_Slim_AS7341", "Ref Slim AS7341", pcb_envelope(), (0.8, 0.5, 0.1), 40)
    for n in ("Box_Base","Box_Lid","Ref_Box_Capsule","Ref_Box_Battery","Ref_Box_AS7341"):
        o = doc.getObject(n)
        if o: o.ViewObject.Visibility = False
    doc.recompute()
    print(f"L_out={L_out:.1f} W_out={W_out:.1f} base_h={base_h} lid_t={lid_t} total_h={base_h + lid_t}")
    print(f"stacks: capsule {total_capsule:.2f} sensor {total_sensor:.2f}; roof over Capsule {roof_t:.2f}; recess {lid_recess:.2f}; z_pcb {z_pcb:.2f} (gap over cell {z_pcb - floor_t - cell_t:.2f})")
    for o in (base, lid):
        print(o.Name, "valid", o.Shape.isValid(), "solids", len(o.Shape.Solids),
              "vol", round(o.Shape.Volume, 1), o.Shape.BoundBox)
    for name, ref in (("capsule", cap), ("battery", cell), ("as7341", pcb)):
        for o in (base, lid):
            print("clash", name, o.Name, round(o.Shape.common(ref.Shape).Volume, 3))
    print("clash base-lid", round(base.Shape.common(lid.Shape).Volume, 3))
    print("clash battery-as7341", round(cell.Shape.common(pcb.Shape).Volume, 3),
          "capsule-as7341", round(cap.Shape.common(pcb.Shape).Volume, 3))
    return base, lid


if __name__ == "__main__":
    build_and_apply()
