"""Plan-view SVG for the slim_puck design page: X right (USB end -X, far end +X), Y up (Capsule +Y), origin at the box centre.
Solid = current model (build_slim_puck.py, 2026-10-15 after print feedback). Grey dashed = the first printed version, drawn in the same frame
(printed outline 42.4 x 50.0, divider wall aligned, y -24.7..25.3 in this frame)."""


def plan_svg():
    s = 15  # px per mm
    L, Wd = 40.4, 50.6          # current box
    LG, YG0, YG1 = 42.4, -24.7, 25.3   # printed box: length, y range
    ox, oy = 170, 80
    W_svg, H_svg = ox * 2 + LG * s + 60, oy * 2 + 52 * s + 20
    col = "currentColor"
    gh = "#8a8f98"

    def X(x):
        return ox + (x + LG / 2) * s

    def Y(y):
        return oy + (26.5 - y) * s

    p = []
    for gx in range(-20, 21, 10):
        p.append(f'<line x1="{X(gx)}" y1="{Y(-24)-8}" x2="{X(gx)}" y2="{Y(26)+8}" stroke="{col}" opacity="0.10"/>')
    for gy in range(-20, 21, 10):
        p.append(f'<line x1="{X(-LG/2)-8}" y1="{Y(gy)}" x2="{X(LG/2)+8}" y2="{Y(gy)}" stroke="{col}" opacity="0.10"/>')

    # ---- printed version (ghost) ----
    p.append(f'<rect x="{X(-LG/2)}" y="{Y(YG1)}" width="{LG*s}" height="{(YG1-YG0)*s}" rx="{4*s}" fill="none" stroke="{gh}" stroke-width="1.5" stroke-dasharray="6 4"/>')
    p.append(f'<rect x="{X(-20.2)}" y="{Y(23.3)}" width="{40.4*s}" height="{24.4*s}" fill="none" stroke="{gh}" stroke-dasharray="4 3"/>')
    p.append(f'<circle cx="{X(18.2)}" cy="{Y(7.7)}" r="{1.2*s}" fill="none" stroke="{gh}" stroke-width="1.5"/>')
    p.append(f'<circle cx="{X(15.2)}" cy="{Y(7.8)}" r="{1.0*s}" fill="none" stroke="{gh}" stroke-width="1.5"/>')
    p.append(f'<rect x="{X(LG/2)}" y="{Y(14.5+1.5)}" width="6" height="{3.0*s}" fill="none" stroke="{gh}"/>')
    p.append(f'<circle cx="{X(LG/2)+3}" cy="{Y(7.7)}" r="{1.2*s*0.7}" fill="none" stroke="{gh}"/>')

    # ---- current model ----
    p.append(f'<rect x="{X(-L/2)}" y="{Y(Wd/2)}" width="{L*s}" height="{Wd*s}" rx="{4*s}" fill="none" stroke="{col}" stroke-width="2"/>')
    p.append(f'<rect x="{X(-19.2)}" y="{Y(23.3)}" width="{38.4*s}" height="{24.4*s}" fill="#3fb35a" fill-opacity="0.22" stroke="#2a8a40"/>')
    p.append(f'<text x="{X(-8)}" y="{Y(20.6)}" text-anchor="middle" font-size="12" fill="{col}">Capsule pocket 38.4 x 24.4</text>')
    p.append(f'<rect x="{X(-13.95)}" y="{Y(-2.3)}" width="{27.9*s}" height="{21.0*s}" fill="#5b86d6" fill-opacity="0.22" stroke="#3b62b0"/>')
    p.append(f'<text x="{X(0)}" y="{Y(-21.0)}" text-anchor="middle" font-size="12" fill="{col}">Battery + AS7341 pocket 27.9 x 21.0</text>')
    p.append(f'<circle cx="{X(0)}" cy="{Y(-12.8)}" r="{6.0*s}" fill="none" stroke="#c0701a" stroke-width="1.6" stroke-dasharray="4 3"/>')
    p.append(f'<text x="{X(0)}" y="{Y(-12.8)+4}" text-anchor="middle" font-size="11" fill="#c0701a">diffuser seat dia 12.0</text>')
    for sx in (1, -1):
        for sy in (-20.5, -5.1):
            p.append(f'<circle cx="{X(sx*17.075)}" cy="{Y(sy)}" r="{1.3*s}" fill="none" stroke="{col}"/>')
    # lid: G42 tongue x 8.5..17.4, y 6.9..13.9; nub (16.2, 10.4); lid LED hole (13.2, 9.5)
    p.append(f'<rect x="{X(8.5)}" y="{Y(14.2)}" width="{8.9*s}" height="{7.0*s}" fill="#e8c34a" fill-opacity="0.35" stroke="#a8570a" stroke-dasharray="3 2"/>')
    p.append(f'<circle cx="{X(16.2)}" cy="{Y(10.7)}" r="{1.2*s}" fill="#a8570a"/>')
    p.append(f'<rect x="{X(13.2-0.8)}" y="{Y(9.3+1.7)}" width="{1.6*s}" height="{3.4*s}" rx="{0.8*s}" fill="none" stroke="#a8570a" stroke-width="1.5"/>')
    p.append(f'<line x1="{X(18.2)-4}" y1="{Y(7.7)-4}" x2="{X(16.2)+5}" y2="{Y(10.7)+5}" stroke="#a8570a" stroke-width="1.2" marker-end="url(#am)"/>')
    p.append(f'<text x="{X(10)}" y="{Y(16.1)}" text-anchor="middle" font-size="11" fill="#a8570a">G42 tongue, nub (16.2, 10.7)</text>')
    # USB window on the -X wall (y 11.8, 9.4 wide); far-wall windows on +X wall: RGB y 18.4, BOOT y 12.4
    p.append(f'<rect x="{X(-L/2)-7}" y="{Y(11.1+4.7)}" width="7" height="{9.4*s}" fill="#d33" fill-opacity="0.65"/>')
    p.append(f'<text x="{X(-LG/2)-10}" y="{Y(11.1)+4}" text-anchor="end" font-size="11" fill="#d33">USB-C window</text>')
    p.append(f'<text x="{X(-LG/2)-10}" y="{Y(11.1)+18}" text-anchor="end" font-size="11" fill="#d33">9.4 wide, y 11.1</text>')
    p.append(f'<rect x="{X(L/2)}" y="{Y(16.7+1.5)}" width="7" height="{3.0*s}" fill="#a2c" fill-opacity="0.75"/>')
    p.append(f'<circle cx="{X(L/2)+3.5}" cy="{Y(10.3)}" r="{1.2*s*0.7}" fill="#06c"/>')
    p.append(f'<text x="{X(LG/2)+12}" y="{Y(16.7)+4}" font-size="11" fill="#a2c">RGB LED window (y 16.7, z 4.9)</text>')
    p.append(f'<text x="{X(LG/2)+12}" y="{Y(10.3)+4}" font-size="11" fill="#06c">BOOT hole (y 10.3)</text>')
    p.append(f'<text x="{X(LG/2)+12}" y="{Y(14.5)+4}" font-size="10" fill="{gh}">printed: RGB y 14.5, BOOT y 7.7</text>')
    # axes
    p.append(f'<line x1="{X(-LG/2)-10}" y1="{Y(0)}" x2="{X(LG/2)+10}" y2="{Y(0)}" stroke="#d11" stroke-width="1.6" marker-end="url(#ar)"/>')
    p.append(f'<line x1="{X(0)}" y1="{Y(-25.3)+10}" x2="{X(0)}" y2="{Y(26)-10}" stroke="#118" stroke-width="1.6" marker-end="url(#ab)"/>')
    p.append(f'<text x="{X(LG/2)+14}" y="{Y(0)+4}" font-size="14" font-weight="700" fill="#d11">+X</text>')
    p.append(f'<text x="{X(0)+6}" y="{Y(26)-14}" font-size="14" font-weight="700" fill="#118">+Y</text>')
    p.append(f'<circle cx="{X(0)}" cy="{Y(0)}" r="3" fill="{col}"/><text x="{X(0)+6}" y="{Y(0)-6}" font-size="11" fill="{col}">origin (0,0) = box centre</text>')
    for gx in (-20, -10, 10, 20):
        p.append(f'<text x="{X(gx)}" y="{Y(0)+14}" text-anchor="middle" font-size="10" fill="#d11">{gx}</text>')
    for gy in (-20, -10, 10, 20):
        p.append(f'<text x="{X(0)+5}" y="{Y(gy)+4}" font-size="10" fill="#118">{gy}</text>')
    p.append(f'<text x="{X(-LG/2)+4}" y="{Y(26)-8}" font-size="11" fill="{col}" opacity="0.8">left = USB end (-X)</text>')
    p.append(f'<text x="{X(LG/2)-4}" y="{Y(-25.3)+16}" text-anchor="end" font-size="11" fill="{col}" opacity="0.8">right = far end (+X)</text>')
    p.append(f'<text x="{X(-LG/2)+4}" y="{Y(-25.3)+16}" font-size="11" fill="{col}" opacity="0.8">bottom = sensor side (-Y)</text>')
    p.append(f'<text x="{X(LG/2)-4}" y="{Y(26)-8}" text-anchor="end" font-size="11" fill="{col}" opacity="0.8">top = Capsule side (+Y)</text>')
    # overall dimensions (current box)
    p.append(f'<line x1="{X(-L/2)}" y1="{Y(-25.3)+30}" x2="{X(L/2)}" y2="{Y(-25.3)+30}" stroke="{col}" marker-start="url(#a)" marker-end="url(#a)"/>')
    p.append(f'<text x="{X(0)}" y="{Y(-25.3)+46}" text-anchor="middle" font-size="13" fill="{col}">40.4 mm (X), printed 42.4</text>')
    p.append(f'<line x1="{X(-LG/2)-50}" y1="{Y(25.3)}" x2="{X(-LG/2)-50}" y2="{Y(-25.3)}" stroke="{col}" marker-start="url(#a)" marker-end="url(#a)"/>')
    p.append(f'<text x="{X(-LG/2)-58}" y="{Y(0)}" text-anchor="middle" font-size="13" fill="{col}" transform="rotate(-90 {X(-LG/2)-58} {Y(0)})">50.6 mm (Y), printed 50.0</text>')
    # legend
    p.append(f'<line x1="{X(-LG/2)}" y1="{Y(-25.3)+62}" x2="{X(-LG/2)+30}" y2="{Y(-25.3)+62}" stroke="{col}" stroke-width="2"/><text x="{X(-LG/2)+36}" y="{Y(-25.3)+66}" font-size="11" fill="{col}">current model</text>')
    p.append(f'<line x1="{X(-LG/2)+140}" y1="{Y(-25.3)+62}" x2="{X(-LG/2)+170}" y2="{Y(-25.3)+62}" stroke="{gh}" stroke-width="1.5" stroke-dasharray="6 4"/><text x="{X(-LG/2)+176}" y="{Y(-25.3)+66}" font-size="11" fill="{gh}">first printed version</text>')
    defs = ('<defs><marker id="a" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker>'
            '<marker id="ar" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#d11"/></marker>'
            '<marker id="ab" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#118"/></marker>'
            '<marker id="am" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#a8570a"/></marker></defs>')
    return (f'<svg viewBox="0 0 {W_svg} {H_svg}" role="img" aria-label="Plan view with X and Y axes, current model and first printed version" '
            f'style="width:100%;height:auto">{defs}{"".join(p)}</svg>')
