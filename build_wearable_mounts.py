"""Wearable add-ons for the LightDx slim puck (base = LightDx_base_v1.FCStd, unchanged).
Both parts glue to the flat BASE BACK (z = 0 face, outside the box); the lid / diffuser faces outward.
Frame: same as build_slim_puck.py (X right, USB end -X, origin box centre in XY, base back at z = 0).
  Strap_Plate : plate + two lug pairs on the +-Y ends, 20 mm strap gap, 1.5 mm spring bar.
  Clip_Plate  : plate + flexible pocket-clip arm (PETG), hook at the free end.
No STL export from here (user: export only when asked)."""
import FreeCAD as App
import Part

L, W, R = 40.4, 50.6, 4.0          # base outline (matches Slim_Base)
PT = 2.4                            # plate thickness (z -PT..0)
STRAP = 20.0                        # strap width = lug gap
LUG_T = 3.0                         # lug thickness (X)
LUG_OUT = 5.0                       # lug overhang beyond the box edge (Y)
LUG_DZ = 5.0                        # lug height below z=0
BAR_D = 1.8                         # spring-bar hole dia (bar 1.5, tip ~1.0)
BAR_IN = 2.5                        # hole axis distance from the lug tip (Y)
V = App.Vector


def _plate():
    p = Part.makeBox(L, W, PT, V(-L / 2, -W / 2, -PT))
    p = p.makeFillet(R, [e for e in p.Edges if abs(e.tangentAt(e.FirstParameter).z) > 0.99])
    return p


def strap_plate():
    s = _plate()
    ytip = W / 2 + LUG_OUT
    zc = -LUG_DZ / 2 - 0.4
    for sy in (1, -1):
        for sx in (1, -1):
            x0 = sx * (STRAP / 2) if sx > 0 else -(STRAP / 2) - LUG_T
            y_a = sy * (W / 2 - 3.0)          # reaches back into the plate
            ylo, yhi = sorted((y_a, sy * ytip))
            lug = Part.makeBox(LUG_T, yhi - ylo, LUG_DZ + PT * 0, V(x0, ylo, -LUG_DZ))
            # round the tip with a cylinder about X
            ycyl = sy * (ytip - BAR_D / 2 - 0.9)
            s = s.fuse(lug)
        # hole through both lugs along X
        yh = sy * (ytip - BAR_IN)
        hole = Part.makeCylinder(BAR_D / 2, STRAP + 2 * LUG_T + 2, V(-STRAP / 2 - LUG_T - 1, yh, -LUG_DZ / 2 - 0.4), V(1, 0, 0))
        s = s.cut(hole)
    return s.removeSplitter()


def clip_plate():
    s = _plate()
    gap, at, aw = 1.5, 1.6, 14.0          # fabric gap, arm thickness, arm width
    z_top = -PT - gap
    z_bot = z_top - at
    ya, yb = -12.0, W / 2 - 1.2           # arm from the free end to the +Y stem
    arm = Part.makeBox(aw, yb - ya, at, V(-aw / 2, ya, z_bot))
    stem = Part.makeBox(aw, 3.0, gap + at, V(-aw / 2, yb - 3.0, z_bot))
    # hook: wedge at the free end pointing up toward the plate
    hook = Part.makePolygon([V(0, ya, z_top), V(0, ya + 3.5, z_top), V(0, ya, z_top + 1.0), V(0, ya, z_top)])
    hook = Part.Face(hook).extrude(V(aw, 0, 0)).translate(V(-aw / 2, 0, 0))
    s = s.fuse(stem).fuse(arm).fuse(hook)
    return s.removeSplitter()


def build_and_apply(docname="Square_puck_v2"):
    doc = App.getDocument(docname)
    for n, f, vis in (("Strap_Plate", strap_plate, True), ("Clip_Plate", clip_plate, False)):
        o = doc.getObject(n) or doc.addObject("Part::Feature", n)
        o.Shape = f()
        o.ViewObject.Visibility = vis
        o.ViewObject.ShapeColor = (0.25, 0.45, 0.8) if n == "Strap_Plate" else (0.8, 0.45, 0.2)
    doc.recompute()
    return doc
