"""
build_sensor_enclosure.py

Parametric build script for "Sensor_Enclosure" in Reused_Parts.FCStd.

This is NOT a FreeCAD parametric feature (no feature tree/sketches) - it's a
plain Python/Part-module CSG script. Sensor_Enclosure is a Part::Feature, a
frozen BRep shape; there is nothing to double-click and edit in the FreeCAD
GUI. To change a dimension:
  1. Edit the relevant value in the PARAMETERS section below.
  2. Re-run this script inside FreeCAD (Macro > Execute, or paste into the
     Python console) with the Reused_Parts document open.
  3. It finds (or creates) the "Sensor_Enclosure" object, rebuilds the shape
     from scratch with the new parameters, and recomputes the document.
  4. Save the document yourself afterward (File > Save), or call doc.save().

Geometry summary (see PARAMETERS for exact numbers):
  - Outer shell: rounded-rectangle plate matching the M5Capsule's own
    footprint and corner radius, sitting flush against the capsule's
    bottom face.
  - A shallow rectangular pocket that captures the PCB with a small
    clearance fit.
  - 4 through-holes (+ counterbore) at the PCB's own corner mounting
    hole positions.
  - 2 through-holes (+ counterbore) at the capsule's real M3 threaded-
    insert locations (confirmed by probing the capsule mesh - NOT the
    other ~8 smaller holes/magnet recesses nearby).
  - A stepped center aperture aligned to the AS7341's true optical
    window position: a wide "seat" a white diffuser disk drops into,
    narrowing to a "shoulder" bore that is both the retaining lip and
    the light path to the sensor.
  - A raised collar ("rim") fused around the aperture on the exterior
    face, standing proud of the surface to block off-axis stray light
    (like a PAR sensor cosine-corrector hood).
  - Two rectangular slots cut through the pocket's end walls, aligned
    to the PCB's two JST_SH connectors, opening a cable-access channel
    from the pocket cavity out to the enclosure's outer edge.

All coordinates are in the shared world frame of Reused_Parts.FCStd,
where the PCB is centered at world (0,0) and the capsule/enclosure are
also centered at world (0,0) in X/Y.
"""

import Part
import FreeCAD as App


# ============================== PARAMETERS ==============================

# --- Outer shell (matches the capsule's own footprint + corner radius) ---
outer_w, outer_l = 24.0, 40.0   # overall X, Y footprint (mm)
fillet_r = 3.0                    # corner radius - measured from the capsule mesh directly

# --- Vertical layering (all measured from the top face, Z=0, which is
#     flush against the capsule's bottom; enclosure extends downward) ---
base_t = 2.5           # solid base thickness, below the PCB pocket
pocket_depth = 4.6     # PCB pocket depth (PCB is 4.53mm thick + clearance)
total_h = base_t + pocket_depth   # overall enclosure thickness (7.1mm)

# --- PCB pocket (captures the PCB with a small clearance fit) ---
pocket_w, pocket_l = 18.0, 25.6   # PCB footprint (17.78 x 25.4) + clearance

# --- PCB's own 4 corner mounting holes (reused so one screw secures
#     enclosure + PCB + capsule boss together) ---
screw_xy = [(6.35, 10.16), (-6.35, 10.16), (6.35, -10.16), (-6.35, -10.16)]
screw_r_clear = 1.3     # clearance radius for M2 (dia 2.6mm)
# counterbore radius for a flush screw head. Shrunk from 2.75 to 2.2mm:
# the two Y=+10.16 holes sit only 6.07mm from the nearest M3 hole (8,16),
# and at the old radii (2.75+3.25=6.0) that left just 0.07mm of wall - a
# print with essentially no material there. Still fits an M2 SHCS head
# (~3.8mm dia) with margin.
screw_r_cbore = 2.2     # dia 4.4mm
cbore_depth = 2.0

# --- Capsule's real M3 threaded-insert locations (confirmed by probing
#     the capsule mesh: these 2 measured ~4.0-4.2mm bore vs ~2.6mm for
#     the ~8 other holes/magnet recesses nearby - do NOT add holes there) ---
m3_xy = [(8.0, 16.0), (-8.0, 16.0)]
m3_r_clear = 1.7        # M3 clearance radius (dia 3.4mm)
# counterbore radius for an M3 screw head, shrunk from 3.25 to 3.0mm (see
# note on screw_r_cbore above - this + screw_r_cbore's reduction restores
# ~0.87mm of wall between the two hole types instead of ~0.07mm). Still
# fits an M3 SHCS head (~5.5mm dia) with margin.
m3_r_cbore = 3.0        # dia 6.0mm
m3_cbore_depth = 2.5

# --- Stepped aperture for the white diffuser disk. Originally centered on
#     the AS7341 sub-part's tiny modeled "window" feature (-1.99, 0.0), but
#     a printed test (see LEARNINGS.md) showed that feature is inaccurate:
#     the real chip is centered along the board's length (Y, unchanged) but
#     was off-center across the board's width (X) by ~2mm. Corrected here
#     empirically from the physical measurement, not re-derived from CAD. ---
aperture_xy = (0.0, 0.0)
seat_radius = 6.1              # disk seat radius (0.1mm clearance over a 6.0mm disk)
seat_depth = 1.5               # = disk thickness
shoulder_inner_radius = 5.0    # narrower light-path / retaining shoulder bore
shoulder_depth = base_t - seat_depth   # remaining wall thickness (1.0mm)

# --- Raised light-blocking collar ("rim") around the aperture, fused
#     onto the exterior face (matches disk_measures.txt's rim() module) ---
rim_outer_r = 9.0     # dia 18mm
rim_inner_r = 8.25    # dia 16.5mm
rim_height = 2.0

# --- JST connector cable-access slots (both PCB ends) ---
# connector spans X -4..2. Widened 1mm total per user feedback on the first
# print, but ALL of it added on the +X side: the -X side only has 0.55mm to
# the nearby PCB corner hole's clearance bore already (widening it further
# would drop that to ~0.05mm, another near-zero wall), while +X had 2.55mm
# to spare. Net: same 1mm-wider opening, no new thin walls.
jst_x_min, jst_x_max = -4.5, 3.5
jst_y_inner = 11.5      # slot starts just inside the pocket, ahead of the connector
jst_y_outer = 20.5      # cuts clean through the flange to the enclosure's outer edge

# ==========================================================================


def build_shape():
    """Construct and return the Sensor_Enclosure solid from the parameters above."""

    # Outer rounded-rectangle shell
    box = Part.makeBox(outer_w, outer_l, total_h,
                        App.Vector(-outer_w / 2, -outer_l / 2, -total_h))
    vert_edges = [e for e in box.Edges
                  if abs(e.Vertexes[1].Point.z - e.Vertexes[0].Point.z) > total_h * 0.9]
    box = box.makeFillet(fillet_r, vert_edges)

    # PCB pocket, cut in from the top face
    pocket = Part.makeBox(pocket_w, pocket_l, pocket_depth + 1,
                           App.Vector(-pocket_w / 2, -pocket_l / 2, -pocket_depth))
    solid = box.cut(pocket)

    tools = []

    # PCB's own 4 corner mounting holes + counterbore
    for (x, y) in screw_xy:
        tools.append(Part.makeCylinder(screw_r_clear, total_h + 2,
                                        App.Vector(x, y, -total_h - 1)))
        tools.append(Part.makeCylinder(screw_r_cbore, cbore_depth + 0.5,
                                        App.Vector(x, y, -total_h - 0.25)))

    # Capsule's 2 real M3 insert holes + counterbore
    for (x, y) in m3_xy:
        tools.append(Part.makeCylinder(m3_r_clear, total_h + 2,
                                        App.Vector(x, y, -total_h - 1)))
        tools.append(Part.makeCylinder(m3_r_cbore, m3_cbore_depth + 0.5,
                                        App.Vector(x, y, -total_h - 0.25)))

    # Stepped aperture: wide seat (disk) + narrow shoulder (light path/retainer)
    ax, ay = aperture_xy
    tools.append(Part.makeCylinder(seat_radius, seat_depth + 0.5,
                                    App.Vector(ax, ay, -total_h - 0.25)))
    tools.append(Part.makeCylinder(shoulder_inner_radius, shoulder_depth + 0.5,
                                    App.Vector(ax, ay, -total_h + seat_depth - 0.25)))

    # JST cable-access slots, both ends, full pocket depth
    for sign in (1, -1):
        y0, y1 = sign * jst_y_inner, sign * jst_y_outer
        ymin, ymax = min(y0, y1), max(y0, y1)
        tools.append(Part.makeBox(jst_x_max - jst_x_min, ymax - ymin, pocket_depth + 0.5,
                                   App.Vector(jst_x_min, ymin, -pocket_depth)))

    for t in tools:
        solid = solid.cut(t)

    # Raised light-blocking collar, fused onto the exterior face
    rim_outer = Part.makeCylinder(rim_outer_r, rim_height,
                                   App.Vector(ax, ay, -total_h - rim_height))
    rim_inner = Part.makeCylinder(rim_inner_r, rim_height + 1,
                                   App.Vector(ax, ay, -total_h - rim_height - 0.5))
    rim_solid = rim_outer.cut(rim_inner)

    solid = solid.fuse(rim_solid)
    solid = solid.removeSplitter()

    return solid


def build_and_apply(doc_name="Reused_Parts", obj_name="Sensor_Enclosure"):
    """Rebuild the shape and apply it to the named object (creating it if needed)."""
    doc = App.getDocument(doc_name)
    obj = doc.getObject(obj_name)
    if obj is None:
        obj = doc.addObject("Part::Feature", obj_name)
        obj.Label = "Sensor Enclosure"
        obj.ViewObject.ShapeColor = (0.15, 0.15, 0.15, 1.0)

    obj.Shape = build_shape()
    doc.recompute()
    print(f"{obj_name} rebuilt. bbox={obj.Shape.BoundBox} valid={obj.Shape.isValid()}")
    return obj


if __name__ == "__main__":
    build_and_apply()
