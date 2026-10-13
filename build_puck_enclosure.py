"""
build_puck_enclosure.py

Parametric build script for the low-profile circular LightDx enclosure
("Puck_Base" + "Puck_Lid") in Reused_Parts.FCStd. Same style as
build_sensor_enclosure.py: plain Part-module CSG, no FreeCAD feature tree.
To change a dimension, edit PARAMETERS, re-run with Reused_Parts open, save.

Layout (Z up, Z=0 = bottom of the puck, puck centred on X/Y = 0):
  Puck_Base  floor + one electronics layer, two side-by-side pockets:
               y > 0  M5Capsule carrier board + Stamp-S3A (USB-C end toward -X)
               y < 0  250 mAh LiPo (502030 assumed)
             divider wall between them with a battery-lead slot, a USB-C slot
             running out to the rim, 4 M2 clearance holes + counterbores in the
             bottom face (lid screws go UP from underneath into blind pilots in the lid).
  Puck_Lid   AS7341 board pocket (component side up, bare PCB side faces the
             electronics layer), stepped diffuser aperture on the top face,
             light-blocking rim, JST cable slots dropping into the base.
The aperture faces +Z (sensor looks up), opposite to the old Sensor_Enclosure.

UNVERIFIED (assumed, not measured): carrier board outline, battery size,
carrier+Stamp stack height, USB-C height. Treat the first print as a fit test.
AS7341 retention: 4 pillars hang from the lid ceiling to the PCB's component face; M2
screws go up from below through the PCB holes into blind pilots in the pillars.
"""

import math
import Part
import FreeCAD as App


# ============================== PARAMETERS ==============================

# --- Electronics (ASSUMED) ---
cell_l, cell_w, cell_t = 30.0, 20.0, 5.0     # 502030 LiPo: L along X, W along Y
carrier_l, carrier_w = 30.0, 20.0            # carrier board outline (guess)
clr = 0.2                                    # per-side pocket clearance
pocket_l = max(cell_l, carrier_l) + 2 * clr  # X extent of both pockets
pocket_w = max(cell_w, carrier_w) + 2 * clr  # Y extent of each pocket
divider = 1.2                                # wall between the two pockets

# --- Shell ---
wall = 2.0             # minimum rim wall around the pockets
floor_t = 1.5
layer_h = 8.0          # electronics layer height (carrier + Stamp stack, guess)

# Pockets: carrier at +Y, battery at -Y
carrier_y0, carrier_y1 = divider / 2, divider / 2 + pocket_w
cell_y0, cell_y1 = -(divider / 2 + pocket_w), -divider / 2

# Outer radius so the pocket corners keep `wall` mm to the edge
R_out = math.ceil(math.hypot(pocket_l / 2, carrier_y1) + wall)

base_h = floor_t + layer_h

# --- USB-C slot (carrier's USB-C end faces -X, centred on the carrier pocket) ---
usb_y = (carrier_y0 + carrier_y1) / 2
usb_w = 12.0           # plug overmould clearance
usb_z_center = 6.0     # above base bottom (guess, check against real stack)
usb_h = 6.5

# --- Battery lead slot through the divider ---
lead_x0, lead_x1 = -2.0, 2.0

# --- Lid screws: 4x M2 inserted from the UNDERSIDE of the base (clearance hole +
#     counterbore at the bottom face), threading up into blind self-tap pilots in the
#     lid's underside. Nothing is drilled through the lid top. Use ~M2x12. ---
screw_xy = [(R_out - 6.4, 0.0), (-(R_out - 6.4), 0.0),
            (0.0, R_out - 3.5), (0.0, -(R_out - 3.5))]
clear_r = 1.3          # M2 clearance through the base
cbore_r = 2.2          # M2 SHCS head (3.8mm) with margin
cbore_depth = 2.2      # from the base's bottom face
tap_r = 0.9            # M2 self-tap pilot in the lid
tap_depth = 5.0        # blind, up from the lid's bottom face (lid is 7.1 thick)

# --- Lid / AS7341 section (numbers carried over from build_sensor_enclosure.py) ---
pcb_w, pcb_l = 18.0, 25.6      # AS7341 board 17.78 x 25.4 + clearance
pocket_depth = 4.6             # board thickness incl. components 4.53 + clearance
top_t = 2.5                    # wall above the board (seat 1.5 + shoulder 1.0)
lid_h = pocket_depth + top_t   # 7.1

aperture_xy = (0.0, 0.0)
seat_radius, seat_depth = 6.1, 1.5
shoulder_inner_radius = 5.0
shoulder_depth = top_t - seat_depth

rim_enabled = False    # light-blocking collar off for easier printing; set True to restore
rim_outer_r, rim_inner_r, rim_height = 9.0, 8.25, 2.0

# AS7341 board's own 4 corner mounting holes (same pattern as the old enclosure).
# Retention: 4 pillars hang from the lid ceiling down to the PCB's component face;
# an M2 screw goes UP from below through the PCB hole into a blind self-tap pilot in
# the pillar (nothing is drilled through the lid top, so it stays flat/light-tight).
# Screw heads sit on the PCB's bare underside, inside the electronics layer (low-head
# M2 recommended; check clearance over the carrier at the Y=+10.16 pair).
pcb_screw_xy = [(6.35, 10.16), (-6.35, 10.16), (6.35, -10.16), (-6.35, -10.16)]
pcb_thickness = 1.57          # bare PCB; components stand above this to 4.53
pillar_r = 2.0                # r2.0 keeps clear of the JST slot (x>=-4.5) at y=11.5
pillar_pilot_r = 0.9          # M2 self-tap
pillar_pilot_depth = 4.0      # blind, measured up from the pillar bottom

jst_x_min, jst_x_max = -4.5, 3.5
jst_y_inner, jst_y_outer = 11.5, 17.5   # slot drops cables down into the base layer

# ==========================================================================


def V(x, y, z):
    return App.Vector(x, y, z)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def build_base():
    solid = Part.makeCylinder(R_out, base_h, V(0, 0, 0))
    top = base_h
    tools = [
        box(-pocket_l / 2, pocket_l / 2, carrier_y0, carrier_y1, floor_t, top + 1),
        box(-pocket_l / 2, pocket_l / 2, cell_y0, cell_y1, floor_t, top + 1),
        # USB-C slot from the carrier pocket end out through the rim, open on top
        box(-R_out - 1, -pocket_l / 2 + 0.1, usb_y - usb_w / 2, usb_y + usb_w / 2,
            floor_t + usb_z_center - usb_h / 2, top + 1),
        # battery lead slot through the divider, open on top
        box(lead_x0, lead_x1, -divider / 2 - 0.1, divider / 2 + 0.1, floor_t + 1.0, top + 1),
    ]
    for (x, y) in screw_xy:
        tools.append(Part.makeCylinder(clear_r, base_h + 2, V(x, y, -1)))
        tools.append(Part.makeCylinder(cbore_r, cbore_depth + 1, V(x, y, -1)))
    for t in tools:
        solid = solid.cut(t)
    return solid.removeSplitter()


def build_lid():
    z0 = base_h
    solid = Part.makeCylinder(R_out, lid_h, V(0, 0, z0))
    tools = [box(-pcb_w / 2, pcb_w / 2, -pcb_l / 2, pcb_l / 2, z0 - 0.5, z0 + pocket_depth)]

    # JST cable slots, both ends, full pocket depth
    for sign in (1, -1):
        ya, yb = sorted((sign * jst_y_inner, sign * jst_y_outer))
        tools.append(box(jst_x_min, jst_x_max, ya, yb, z0 - 0.5, z0 + pocket_depth))

    # Blind self-tap pilots for the base screws, from the lid's bottom face
    ztop = z0 + lid_h
    for (x, y) in screw_xy:
        tools.append(Part.makeCylinder(tap_r, tap_depth + 0.5, V(x, y, z0 - 0.5)))

    # Stepped aperture: seat (disk) cut from the top, shoulder through the wall below
    ax, ay = aperture_xy
    tools.append(Part.makeCylinder(seat_radius, seat_depth + 0.5, V(ax, ay, ztop - seat_depth)))
    tools.append(Part.makeCylinder(shoulder_inner_radius, shoulder_depth + 1.0,
                                   V(ax, ay, ztop - top_t - 0.5)))
    for t in tools:
        solid = solid.cut(t)

    # AS7341 retention pillars: from the pocket ceiling down to the PCB's component
    # face (z0 + pcb_thickness), each with a blind self-tap pilot opening downward.
    pillar_z0 = z0 + pcb_thickness
    pillar_top = z0 + pocket_depth + 0.5          # overlap into the ceiling to fuse
    for (x, y) in pcb_screw_xy:
        solid = solid.fuse(Part.makeCylinder(pillar_r, pillar_top - pillar_z0, V(x, y, pillar_z0)))
    for (x, y) in pcb_screw_xy:
        solid = solid.cut(Part.makeCylinder(pillar_pilot_r, pillar_pilot_depth + 0.5,
                                            V(x, y, pillar_z0 - 0.5)))

    if not rim_enabled:
        return solid.removeSplitter()
    rim = Part.makeCylinder(rim_outer_r, rim_height, V(ax, ay, ztop)).cut(
        Part.makeCylinder(rim_inner_r, rim_height + 1, V(ax, ay, ztop - 0.5)))
    return solid.fuse(rim).removeSplitter()


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
    base = ensure(doc, "Puck_Base", "Puck Base", build_base(), (0.15, 0.15, 0.15))
    lid = ensure(doc, "Puck_Lid", "Puck Lid", build_lid(), (0.25, 0.25, 0.25))
    # Placeholder blocks showing the assumed electronics, for clash checks only
    ensure(doc, "Ref_Battery", "Ref Battery (assumed)",
           box(-cell_l / 2, cell_l / 2, -(divider / 2) - cell_w, -divider / 2,
               floor_t, floor_t + cell_t), (0.2, 0.4, 0.8), 40)
    ensure(doc, "Ref_Carrier_Stack", "Ref Carrier+Stamp (assumed)",
           box(-carrier_l / 2, carrier_l / 2, divider / 2, divider / 2 + carrier_w,
               floor_t, floor_t + layer_h - 0.5), (0.2, 0.7, 0.3), 40)
    doc.recompute()
    print(f"R_out={R_out} base_h={base_h} total_h={base_h + lid_h} (+{rim_height if rim_enabled else 0} rim)")
    for o in (base, lid):
        print(o.Name, "valid", o.Shape.isValid(), "vol", round(o.Shape.Volume, 1), o.Shape.BoundBox)
    return base, lid


if __name__ == "__main__":
    build_and_apply()
