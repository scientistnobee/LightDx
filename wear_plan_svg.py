"""Figures for the v4 / wearable sections of the design page.
plan(...)    : plan view of a strap base (X right, USB end -X, Y up, origin = box centre) with lugs, strap gap and the wall windows.
lug_side()   : side profile (looking along Y) of a lug on the base wall."""

COL = "currentColor"
GH = "#8a8f98"


def _defs():
    return ('<defs><marker id="wa" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker></defs>')


def plan(L, W, gap_y, usb_y, usb_w, boot_y, rgb_y, rgb_w, diff_y, strap=20.0, lug_t=3.0, lug_out=6.0, title=""):
    s = 13.0
    ox, oy = 190, 70
    Wd = ox * 2 + (L + 2 * lug_out) * s
    H = oy * 2 + W * s + 40
    xc = Wd / 2

    def X(x):
        return xc + x * s

    def Y(y):
        return oy + (W / 2 - y) * s + 10

    p = [_defs()]
    p.append(f'<text x="{xc}" y="22" text-anchor="middle" font-size="14" font-weight="600" fill="{COL}">{title}</text>')
    # box
    p.append(f'<rect x="{X(-L/2)}" y="{Y(W/2)}" width="{L*s}" height="{W*s}" rx="{4*s}" fill="#5b86d6" fill-opacity="0.12" stroke="{COL}" stroke-width="2"/>')
    # diffuser seat
    p.append(f'<circle cx="{X(0)}" cy="{Y(diff_y)}" r="{6.0*s}" fill="none" stroke="#c0701a" stroke-width="1.5" stroke-dasharray="4 3"/>')
    p.append(f'<text x="{X(0)}" y="{Y(diff_y)+4}" text-anchor="middle" font-size="14" fill="#c0701a">diffuser (lid side)</text>')
    # lugs (visible part beyond the wall, 3 mm; root in the wall)
    for sx in (1, -1):
        for side in (1, -1):
            y0 = gap_y + strap / 2 if side > 0 else gap_y - strap / 2 - lug_t
            xa, xb = sorted((sx * (L / 2 - 1.0), sx * (L / 2 + lug_out)))
            p.append(f'<rect x="{X(xa)}" y="{Y(y0+lug_t)}" width="{(xb-xa)*s}" height="{lug_t*s}" fill="#1f5fbf" fill-opacity="0.55" stroke="#1f5fbf" stroke-width="1.5"/>')
    # windows and holes on the walls
    p.append(f'<rect x="{X(-L/2)-5}" y="{Y(usb_y+usb_w/2)}" width="7" height="{usb_w*s}" fill="#d33" fill-opacity="0.65"/>')
    p.append(f'<text x="{X(-L/2)-lug_out*s-10}" y="{Y(usb_y)+4}" text-anchor="end" font-size="14" fill="#d33">USB-C window</text>')
    p.append(f'<text x="{X(-L/2)-lug_out*s-10}" y="{Y(usb_y)+18}" text-anchor="end" font-size="14" fill="#d33">y {usb_y:.1f}, {usb_w:.1f} wide</text>')
    p.append(f'<circle cx="{X(L/2)+1}" cy="{Y(boot_y)}" r="{1.2*s}" fill="#06c"/>')
    p.append(f'<rect x="{X(L/2)-2}" y="{Y(rgb_y+rgb_w/2)}" width="7" height="{rgb_w*s}" fill="#a2c" fill-opacity="0.75"/>')
    p.append(f'<text x="{X(L/2)+lug_out*s+10}" y="{Y(rgb_y)+4}" font-size="14" fill="#a2c">RGB window y {rgb_y:.1f}</text>')
    p.append(f'<text x="{X(L/2)+lug_out*s+10}" y="{Y(boot_y)+4}" font-size="14" fill="#06c">BOOT hole y {boot_y:.1f}</text>')
    # centre lines: puck (y = 0) and strap (y = gap_y)
    p.append(f'<line x1="{X(-L/2)-lug_out*s-6}" y1="{Y(0)}" x2="{X(L/2)+lug_out*s+6}" y2="{Y(0)}" stroke="{GH}" stroke-dasharray="6 4"/>')
    p.append(f'<line x1="{X(-L/2)-lug_out*s-6}" y1="{Y(gap_y)}" x2="{X(L/2)+lug_out*s+6}" y2="{Y(gap_y)}" stroke="#1f5fbf" stroke-dasharray="2 3"/>')
    p.append(f'<text x="{X(0)}" y="{Y(0)+13}" text-anchor="middle" font-size="13" fill="{GH}">puck centre y = 0</text>')
    p.append(f'<text x="{X(0)}" y="{Y(gap_y)-5}" text-anchor="middle" font-size="13" fill="#1f5fbf">strap centre y = {gap_y:.2f}</text>')
    # 20 mm gap dimension on the left
    xd = X(-L / 2) - lug_out * s - 120
    p.append(f'<line x1="{xd}" y1="{Y(gap_y+strap/2)}" x2="{xd}" y2="{Y(gap_y-strap/2)}" stroke="{COL}" marker-start="url(#wa)" marker-end="url(#wa)"/>')
    p.append(f'<text x="{xd-6}" y="{Y(gap_y)}" text-anchor="middle" font-size="14" fill="{COL}" transform="rotate(-90 {xd-6} {Y(gap_y)})">strap gap {strap:.0f} mm</text>')
    # overall dimensions
    yb = Y(-W / 2) + 18
    p.append(f'<line x1="{X(-L/2)}" y1="{yb}" x2="{X(L/2)}" y2="{yb}" stroke="{COL}" marker-start="url(#wa)" marker-end="url(#wa)"/>')
    p.append(f'<text x="{X(0)}" y="{yb+14}" text-anchor="middle" font-size="14" fill="{COL}">box {L:.1f} x {W:.1f}; with lugs {L+2*lug_out:.1f} (X)</text>')
    return (f'<svg viewBox="0 0 {Wd} {H}" role="img" aria-label="Strap base plan view with lugs" style="width:100%;height:auto">{"".join(p)}</svg>')


def lug_side(base_h=14.2, lug_h=6.0, lug_out=6.0, hole_d=1.8):
    s = 28.0
    W, H = 600, 330
    x0, zb = 170, 290          # wall outer face x, z = 0 baseline

    def Z(z):
        return zb - z * s

    r = lug_h / 2
    p = [_defs()]
    p.append(f'<text x="{W/2}" y="22" text-anchor="middle" font-size="14" font-weight="600" fill="{COL}">Lug, side view (looking along Y)</text>')
    # wall (lower 8.5 mm shown), box interior to the left
    p.append(f'<rect x="{x0-60}" y="{Z(8.5)}" width="60" height="{8.5*s}" fill="#5b86d6" fill-opacity="0.25" stroke="{COL}" stroke-width="2"/>')
    p.append(f'<text x="{x0-30}" y="{Z(4.25)}" text-anchor="middle" font-size="14" fill="{COL}">base wall</text>')
    # lug: box + semicircle
    p.append(f'<path d="M {x0} {Z(0)} L {x0+(lug_out-r)*s} {Z(0)} A {r*s} {r*s} 0 0 0 {x0+(lug_out-r)*s} {Z(lug_h)} L {x0} {Z(lug_h)} Z" fill="#1f5fbf" fill-opacity="0.55" stroke="#1f5fbf" stroke-width="2"/>')
    hx, hz = x0 + (lug_out - r) * s, Z(lug_h / 2)
    p.append(f'<circle cx="{hx}" cy="{hz}" r="{hole_d/2*s}" fill="var(--card,#fff)" stroke="{COL}" stroke-width="1.5"/>')
    p.append(f'<text x="{x0+10}" y="{Z(lug_h)-14}" font-size="14" fill="{COL}">bar hole dia {hole_d} (spring bar 1.5), runs along Y</text>')
    # flat back
    p.append(f'<line x1="{x0-80}" y1="{Z(0)}" x2="{x0+110}" y2="{Z(0)}" stroke="{COL}" stroke-width="2"/>')
    p.append(f'<text x="{x0-80}" y="{Z(0)+16}" font-size="14" fill="{COL}">flat back (z = 0), against the body</text>')
    # dims
    xd = x0 + lug_out * s + 28
    p.append(f'<line x1="{xd}" y1="{Z(0)}" x2="{xd}" y2="{Z(lug_h)}" stroke="{COL}" marker-start="url(#wa)" marker-end="url(#wa)"/>')
    p.append(f'<text x="{xd+8}" y="{Z(lug_h/2)+4}" font-size="14" fill="{COL}">{lug_h:.0f} mm tall, tip radius {r:.0f}</text>')
    p.append(f'<line x1="{x0}" y1="{Z(0)+34}" x2="{x0+lug_out*s}" y2="{Z(0)+34}" stroke="{COL}" marker-start="url(#wa)" marker-end="url(#wa)"/>')
    p.append(f'<text x="{x0+lug_out*s/2}" y="{Z(0)+30}" text-anchor="middle" font-size="14" fill="{COL}">{lug_out:.0f} mm out (tip centre 3 mm from the wall)</text>')
    p.append(f'<text x="{x0-80}" y="{Z(8.5)-30}" font-size="14" fill="{COL}" opacity="0.8">lug is 3 mm thick (along Y); two pairs, 20 mm apart</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Lug side profile" style="width:100%;height:auto">{"".join(p)}</svg>'
