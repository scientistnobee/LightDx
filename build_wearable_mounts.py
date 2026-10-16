"""Wearable bases for the LightDx slim puck. The puck base itself is the wearable base: lugs / clip arm are fused
directly into a copy of Slim_Base (no glued plate, no extra height). LightDx_base_v1.FCStd stays untouched.
Frame: same as build_slim_puck.py (X right, USB end -X, origin box centre in XY, base back at z = 0, lid on top).
  Wear_Base_Strap : Slim_Base + two rounded lug pairs on the +-X ends (20 mm strap gap centred at y = GAP_Y, 1.5 mm spring bar).
  Wear_Base_Clip  : Slim_Base + flexible pocket-clip arm on the back (hidden variant).
No STL export from here (user: export only when asked)."""
import FreeCAD as App
import Part

L, W = 40.4, 50.6                   # base outline (matches Slim_Base)
STRAP = 20.0                        # strap width = lug gap
LUG_T = 3.0                         # lug thickness (X)
LUG_H = 6.0                         # lug height (z 0..6), tip radius = LUG_H / 2
LUG_OUT = LUG_H / 2                 # tip centre sits this far beyond the box edge (Y)
BAR_D = 1.8                         # spring-bar hole dia (bar 1.5, tip ~1.0)
GAP_Y = -7.0                        # strap gap centre in Y: keeps lugs clear of the USB / BOOT / RGB windows (y > 6)
ROOT_IN = 1.0                       # lug root reaches this far into the 2 mm side wall
V = App.Vector


def _lug(sx, yc_gap, side):
    """Lug on the +-X end (sx = +1/-1); side = +1/-1 puts it on the +Y/-Y side of the strap gap centre."""
    y0 = yc_gap + STRAP / 2 if side > 0 else yc_gap - STRAP / 2 - LUG_T
    r = LUG_H / 2
    xc = sx * (L / 2 + LUG_OUT)
    x_root = sx * (L / 2 - ROOT_IN)
    xlo, xhi = sorted((x_root, xc))
    box = Part.makeBox(xhi - xlo, LUG_T, LUG_H, V(xlo, y0, 0))
    cyl = Part.makeCylinder(r, LUG_T, V(xc, y0, r), V(0, 1, 0))
    return box.fuse(cyl)


def strap_base(base):
    s = base
    for sx in (1, -1):
        for side in (1, -1):
            s = s.fuse(_lug(sx, GAP_Y, side))
        xc = sx * (L / 2 + LUG_OUT)
        hole = Part.makeCylinder(BAR_D / 2, STRAP + 2 * LUG_T + 2, V(xc, GAP_Y - STRAP / 2 - LUG_T - 1, LUG_H / 2), V(0, 1, 0))
        s = s.cut(hole)
    return s.removeSplitter()


def clip_base(base):
    gap, at, aw = 1.5, 1.6, 14.0         # fabric gap, arm thickness, arm width
    z_top, z_bot = -gap, -gap - at
    ya, yb = -12.0, W / 2 - 1.2          # free end .. stem on the +Y side
    arm = Part.makeBox(aw, yb - ya, at, V(-aw / 2, ya, z_bot))
    stem = Part.makeBox(aw, 3.0, gap + at, V(-aw / 2, yb - 3.0, z_bot))
    hook = Part.Face(Part.makePolygon([V(0, ya, z_top), V(0, ya + 3.5, z_top), V(0, ya, z_top + 0.9), V(0, ya, z_top)]))
    hook = hook.extrude(V(aw, 0, 0)).translate(V(-aw / 2, 0, 0))
    return base.fuse(stem).fuse(arm).fuse(hook).removeSplitter()


def build_and_apply(docname="Square_puck_v2"):
    doc = App.getDocument(docname)
    base = doc.getObject("Slim_Base").Shape
    for n in ("Strap_Plate", "Clip_Plate"):          # first-version glued plates, replaced
        if doc.getObject(n):
            doc.removeObject(n)
    for n, f, vis, col in (("Wear_Base_Strap", strap_base, True, (0.25, 0.45, 0.8)),
                           ("Wear_Base_Clip", clip_base, False, (0.8, 0.45, 0.2))):
        o = doc.getObject(n) or doc.addObject("Part::Feature", n)
        o.Shape = f(base)
        o.ViewObject.Visibility = vis
        o.ViewObject.ShapeColor = col
    doc.getObject("Slim_Base").ViewObject.Visibility = False
    doc.recompute()
    return doc
