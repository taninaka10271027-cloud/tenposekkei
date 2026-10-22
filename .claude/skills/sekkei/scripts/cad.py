"""Drawing helpers: R12 DXF sheet writer, filleted routes, JIS-style symbols."""
import math
import ezdxf
import r12

TXT_H = 125  # 2.5mm on paper at 1/50


class Sheet:
    def __init__(self):
        self.doc = ezdxf.new('R12', setup=True)
        self.doc.header['$DWGCODEPAGE'] = 'ANSI_932'
        self.doc.header['$LTSCALE'] = 50
        self.doc.header['$EXTMIN'] = (0, 0, 0)
        self.doc.header['$EXTMAX'] = (21000, 14850, 0)
        self.doc.header['$LIMMAX'] = (21000, 14850)
        self.msp = self.doc.modelspace()
        self.layer = '0'
        self.prev = []  # preview ents (same dict format as r12.parse)

    def L(self, name, color=7, ltype='CONTINUOUS'):
        if name not in self.doc.layers:
            self.doc.layers.add(name, color=color, linetype=ltype)
        self.layer = name
        return self

    def _a(self, extra):
        a = {'layer': self.layer}
        a.update(extra)
        return a

    def line(self, p, q, color=256, ltype=None):
        if math.dist(p, q) < 1e-6:
            return
        at = {'color': color}
        if ltype:
            at['linetype'] = ltype
        self.msp.add_line(p, q, dxfattribs=self._a(at))
        self.prev.append({'type': 'LINE', 'layer': self.layer, 'color': self._col(color), 'p1': tuple(p), 'p2': tuple(q), 'lt': ltype})

    def _col(self, c):
        if c != 256:
            return c
        return self.doc.layers.get(self.layer).dxf.color

    def circle(self, c, r, color=256):
        self.msp.add_circle(c, r, dxfattribs=self._a({'color': color}))
        self.prev.append({'type': 'CIRCLE', 'layer': self.layer, 'color': self._col(color), 'c': tuple(c), 'r': r})

    def dot(self, c, r, color=256):
        """filled circle, drawn as concentric circles (JW_CAD safe)"""
        k = r
        while k > 4:
            self.circle(c, k, color)
            k -= max(r / 5.0, 6)

    def arc(self, c, r, a0, a1, color=256, ltype=None):
        at = {'color': color}
        if ltype:
            at['linetype'] = ltype
        self.msp.add_arc(c, r, a0, a1, dxfattribs=self._a(at))
        self.prev.append({'type': 'ARC', 'layer': self.layer, 'color': self._col(color), 'c': tuple(c), 'r': r, 'a0': a0, 'a1': a1, 'lt': ltype})

    def text(self, p, s, h=TXT_H, rot=0, align='L', color=256):
        # align: L, C, R, ML, MC, MR
        hmap = {'L': 0, 'C': 1, 'R': 2, 'ML': 0, 'MC': 1, 'MR': 2}
        vmap = {'L': 0, 'C': 0, 'R': 0, 'ML': 2, 'MC': 2, 'MR': 2}
        at = self._a({'height': h, 'rotation': rot, 'color': color})
        t = self.msp.add_text(s, dxfattribs=at)
        hh, vv = hmap[align], vmap[align]
        if hh or vv:
            t.dxf.halign = hh
            t.dxf.valign = vv
            t.dxf.align_point = p
        t.dxf.insert = p
        self.prev.append({'type': 'TEXT', 'layer': self.layer, 'color': self._col(color), 'p': tuple(p), 'h': h,
                          'rot': rot, 'text': s, 'p11': tuple(p), 'h72': hh, 'v73': vv})

    def solid(self, pts, color=256):
        pts = list(pts)
        if len(pts) == 3:
            pts = pts + [pts[2]]
        self.msp.add_solid([pts[0], pts[1], pts[3], pts[2]], dxfattribs=self._a({'color': color}))
        self.prev.append({'type': 'SOLID', 'layer': self.layer, 'color': self._col(color), 'pts': pts})

    def rect(self, x0, y0, x1, y1, color=256, ltype=None):
        P = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for i in range(4):
            self.line(P[i], P[(i + 1) % 4], color, ltype)

    def poly(self, pts, color=256, closed=False, ltype=None):
        for i in range(len(pts) - 1):
            self.line(pts[i], pts[i + 1], color, ltype)
        if closed:
            self.line(pts[-1], pts[0], color, ltype)

    def save(self, path):
        self.doc.encoding = 'cp932'
        self.doc.header['$DWGCODEPAGE'] = 'ANSI_932'
        self.doc.saveas(path)
        # extents for viewers (ezdxf resets them on save for R12)
        raw = open(path, 'rb').read()
        raw = raw.replace(b'$EXTMIN\n 10\n1e+20\n 20\n1e+20\n 30\n1e+20', b'$EXTMIN\n 10\n0.0\n 20\n0.0\n 30\n0.0')
        raw = raw.replace(b'$EXTMAX\n 10\n-1e+20\n 20\n-1e+20\n 30\n-1e+20', b'$EXTMAX\n 10\n21000.0\n 20\n14850.0\n 30\n0.0')
        open(path, 'wb').write(raw)


# ------------------------------------------------------------------ base copy
LAYER_COL = {}


def copy_base(sh, ents, skip_layers=(), only_layers=None, recolor=None, skip=None):
    for e in ents:
        if e['layer'] in skip_layers:
            continue
        if skip is not None and skip(e):
            continue
        if only_layers is not None and e['layer'] not in only_layers:
            continue
        sh.L(e['layer'], 7)
        col = e['color'] if e['color'] not in (0,) else 256
        if recolor is not None:
            col = recolor
        if e['type'] == 'LINE':
            sh.line(e['p1'], e['p2'], col)
        elif e['type'] == 'CIRCLE':
            sh.circle(e['c'], e['r'], col)
        elif e['type'] == 'ARC':
            sh.arc(e['c'], e['r'], e['a0'], e['a1'], col)
        elif e['type'] == 'TEXT':
            al = 'L'
            if e['h72'] == 1:
                al = 'C'
            sh.text(e['p11'] if e['h72'] else e['p'], e['text'], e['h'], e['rot'], al, col)


# ------------------------------------------------------------------ routes
def _norm(v):
    l = math.hypot(*v)
    return (v[0] / l, v[1] / l) if l > 1e-9 else (0.0, 0.0)


def fillet(points, R):
    """polyline -> list of segments ('L',p,q) / ('A',c,r,a0,a1) with corner radius up to R"""
    pts = clean_pts(points)
    if len(pts) < 2:
        return []
    n = len(pts)
    Rs = R if isinstance(R, (list, tuple)) else [R] * (n - 2)
    seglen = [math.dist(pts[i], pts[i + 1]) for i in range(n - 1)]
    out = []
    cur = pts[0]
    for i in range(1, n - 1):
        A, P, B = pts[i - 1], pts[i], pts[i + 1]
        u = _norm((A[0] - P[0], A[1] - P[1]))
        v = _norm((B[0] - P[0], B[1] - P[1]))
        cosang = max(-1, min(1, u[0] * v[0] + u[1] * v[1]))
        th = math.acos(cosang)
        tan_h = math.tan(th / 2)
        avail_in = seglen[i - 1] * (1.0 if i - 1 == 0 else 0.5)
        avail_out = seglen[i] * (1.0 if i == n - 2 else 0.5)
        t = Rs[i - 1] / tan_h
        t = min(t, avail_in * 0.95, avail_out * 0.95)
        r = t * tan_h
        T1 = (P[0] + u[0] * t, P[1] + u[1] * t)
        T2 = (P[0] + v[0] * t, P[1] + v[1] * t)
        bis = _norm((u[0] + v[0], u[1] + v[1]))
        dc = r / math.sin(th / 2)
        C = (P[0] + bis[0] * dc, P[1] + bis[1] * dc)
        out.append(('L', cur, T1))
        a1 = math.degrees(math.atan2(T1[1] - C[1], T1[0] - C[0]))
        a2 = math.degrees(math.atan2(T2[1] - C[1], T2[0] - C[0]))
        cz = (T1[0] - C[0]) * (T2[1] - C[1]) - (T1[1] - C[1]) * (T2[0] - C[0])
        if cz > 0:
            out.append(('A', C, r, a1 % 360, a2 % 360))
        else:
            out.append(('A', C, r, a2 % 360, a1 % 360))
        cur = T2
    out.append(('L', cur, pts[-1]))
    return out


def draw_segs(sh, segs, color=256, ltype=None):
    for s in segs:
        if s[0] == 'L':
            sh.line(s[1], s[2], color, ltype)
        elif s[2] > 1:
            sh.arc(s[1], s[2], s[3], s[4], color, ltype)


def offset_poly(pts, d):
    """miter offset of polyline (left positive)"""
    n = len(pts)
    segs = []
    for i in range(n - 1):
        t = _norm((pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
        nr = (-t[1] * d, t[0] * d)
        segs.append(((pts[i][0] + nr[0], pts[i][1] + nr[1]), (pts[i + 1][0] + nr[0], pts[i + 1][1] + nr[1]), t))
    out = [segs[0][0]]
    for i in range(1, len(segs)):
        p1, _, t1 = segs[i - 1]
        p2, _, t2 = segs[i]
        den = t1[0] * t2[1] - t1[1] * t2[0]
        if abs(den) < 1e-9:
            out.append(segs[i][0])
            continue
        s = ((p2[0] - p1[0]) * t2[1] - (p2[1] - p1[1]) * t2[0]) / den
        out.append((p1[0] + t1[0] * s, p1[1] + t1[1] * s))
    out.append(segs[-1][1])
    return out


def turn_signs(pts):
    sg = []
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        sg.append(1 if cr > 0 else -1)
    return sg


def thick_path(sh, pts, R, w, color=256, center=True, cap=True):
    pts = clean_pts(pts)
    d = w / 2.0
    sg = turn_signs(pts)
    left = offset_poly(pts, d)
    right = offset_poly(pts, -d)
    draw_segs(sh, fillet(left, [max(R - s * d, 20) for s in sg]), color)
    draw_segs(sh, fillet(right, [max(R + s * d, 20) for s in sg]), color)
    if center:
        draw_segs(sh, fillet(pts, R), color, 'CENTER')
    if cap:
        sh.line(left[0], right[0], color)
        sh.line(left[-1], right[-1], color)


def clean_pts(points):
    pts = [tuple(points[0])]
    for p in points[1:]:
        if math.dist(p, pts[-1]) > 1:
            pts.append(tuple(p))
    k = 1
    while k < len(pts) - 1:
        a, b, c = pts[k - 1], pts[k], pts[k + 1]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-6 * math.dist(a, b) * math.dist(b, c) + 1e-9:
            pts.pop(k)
        else:
            k += 1
    return pts


def path_len(segs):
    L = 0
    for s in segs:
        if s[0] == 'L':
            L += math.dist(s[1], s[2])
        else:
            L += s[2] * math.radians((s[4] - s[3]) % 360)
    return L


def lroute(p, q, first='h'):
    if abs(p[0] - q[0]) < 30 or abs(p[1] - q[1]) < 30:
        return [p, q]
    if first == 'h':
        return [p, (q[0], p[1]), q]
    return [p, (p[0], q[1]), q]


def trim_pts(pts, t0, t1):
    pts = [tuple(p) for p in pts]
    if t0 > 0 and len(pts) >= 2:
        d = _norm((pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]))
        L = math.dist(pts[0], pts[1])
        t = min(t0, L * 0.45)
        pts[0] = (pts[0][0] + d[0] * t, pts[0][1] + d[1] * t)
    if t1 > 0 and len(pts) >= 2:
        d = _norm((pts[-2][0] - pts[-1][0], pts[-2][1] - pts[-1][1]))
        L = math.dist(pts[-1], pts[-2])
        t = min(t1, L * 0.45)
        pts[-1] = (pts[-1][0] + d[0] * t, pts[-1][1] + d[1] * t)
    return pts


def arrow(sh, p, q, size=150, color=256):
    """arrow head at q pointing from p"""
    d = _norm((q[0] - p[0], q[1] - p[1]))
    n = (-d[1], d[0])
    b = (q[0] - d[0] * size, q[1] - d[1] * size)
    sh.solid([q, (b[0] + n[0] * size * 0.3, b[1] + n[1] * size * 0.3), (b[0] - n[0] * size * 0.3, b[1] - n[1] * size * 0.3)], color)


# ------------------------------------------------------------------ symbols
def wall_dir(w):
    return {'N': (0, 1), 'S': (0, -1), 'E': (1, 0), 'W': (-1, 0)}[w]


def sym_fluor(sh, x, y, length=1250, width=150, orient='V'):
    if orient == 'V':
        sh.rect(x - width / 2, y - length / 2, x + width / 2, y + length / 2)
    else:
        sh.rect(x - length / 2, y - width / 2, x + length / 2, y + width / 2)
    sh.circle((x, y), 60)


def sym_pendant(sh, x, y, r=150):
    sh.circle((x, y), r)
    sh.line((x - r, y), (x + r, y))


def sym_downlight(sh, x, y, r=150):
    sh.circle((x, y), r)
    sh.circle((x, y), r * 0.45)


def sym_spot(sh, x, y, aim=(1, 0), r=100):
    sh.circle((x, y), r)
    d = _norm(aim)
    p = (x + d[0] * r, y + d[1] * r)
    q = (x + d[0] * (r + 180), y + d[1] * (r + 180))
    sh.line(p, q)
    arrow(sh, p, q, 90)


def sym_bracket(sh, x, y, wall='N', r=150):
    """JIS 壁付照明 ◐ : wall side half hatched"""
    sh.circle((x, y), r)
    d = wall_dir(wall)
    nrm = (-d[1], d[0])
    sh.line((x - nrm[0] * r, y - nrm[1] * r), (x + nrm[0] * r, y + nrm[1] * r))
    for k in range(1, 12):
        off = r * k / 12.0
        half = math.sqrt(max(r * r - off * off, 0))
        c = (x + d[0] * off, y + d[1] * off)
        sh.line((c[0] - nrm[0] * half, c[1] - nrm[1] * half), (c[0] + nrm[0] * half, c[1] + nrm[1] * half))


def sym_ldduct(sh, p, q, w=70):
    d = _norm((q[0] - p[0], q[1] - p[1]))
    n = (-d[1] * w / 2, d[0] * w / 2)
    sh.line((p[0] + n[0], p[1] + n[1]), (q[0] + n[0], q[1] + n[1]))
    sh.line((p[0] - n[0], p[1] - n[1]), (q[0] - n[0], q[1] - n[1]))
    sh.line((p[0] + n[0], p[1] + n[1]), (p[0] - n[0], p[1] - n[1]))
    sh.line((q[0] + n[0], q[1] + n[1]), (q[0] - n[0], q[1] - n[1]))


def sym_emergency(sh, x, y):
    """非常用照明 (JIS C 0303 ●) 電池内蔵形"""
    sh.dot((x, y), 150)
    sh.circle((x, y), 150)


def sym_exit(sh, x, y, orient='H'):
    """誘導灯 避難口 C級: ▭ + ⊗"""
    if orient == 'H':
        sh.rect(x - 250, y - 110, x + 250, y + 110)
    else:
        sh.rect(x - 110, y - 250, x + 110, y + 250)
    sh.circle((x, y), 90)
    k = 90 * 0.707
    sh.line((x - k, y - k), (x + k, y + k))
    sh.line((x - k, y + k), (x + k, y - k))


def sym_outlet(sh, x, y, wall='N', r=150):
    """JIS 壁付コンセント  ⦶ (壁側に2本線)"""
    sh.circle((x, y), r)
    d = wall_dir(wall)
    nrm = (-d[1], d[0])
    for s in (-0.4, 0.4):
        a = (x + nrm[0] * r * s + d[0] * r * 0.92, y + nrm[1] * r * s + d[1] * r * 0.92)
        b = (x + nrm[0] * r * s - d[0] * r * 0.6, y + nrm[1] * r * s - d[1] * r * 0.6)
        sh.line(a, b)
    sh.line((x + d[0] * r * 0.6 + nrm[0] * r * 0.4, y + d[1] * r * 0.6 + nrm[1] * r * 0.4),
            (x + d[0] * r * 0.6 - nrm[0] * r * 0.4, y + d[1] * r * 0.6 - nrm[1] * r * 0.4))


def sym_switch(sh, x, y, kind='S'):
    if kind == 'V':  # 換気扇用 (既存凡例に合わせ○)
        sh.circle((x, y), 75)
    else:
        sh.dot((x, y), 75)


def sym_fan(sh, x, y, s=300):
    sh.rect(x - s / 2, y - s / 2, x + s / 2, y + s / 2)
    sh.circle((x - s / 4, y), s / 4)
    sh.circle((x + s / 4, y), s / 4)


def sym_grille(sh, x, y, s=200):
    sh.rect(x - s / 2, y - s / 2, x + s / 2, y + s / 2)
    sh.circle((x - s / 4.7, y - s / 4.7), s * 0.3)
    sh.circle((x + s / 4.7, y + s / 4.7), s * 0.3)


def sym_hood(sh, x, y, wall='N', r=100):
    """外壁フード(半円) wall: 外壁方向"""
    a0 = {'N': 0, 'S': 180, 'E': 270, 'W': 90}[wall]
    sh.arc((x, y), r, a0, a0 + 180)
    d = wall_dir(wall)
    n = (-d[1], d[0])
    sh.line((x + n[0] * r * 1.1, y + n[1] * r * 1.1), (x - n[0] * r * 1.1, y - n[1] * r * 1.1))


def sym_ac_wall(sh, x, y, w=800, d=225, wall='S'):
    """壁掛形室内機"""
    if wall in 'NS':
        s = 1 if wall == 'S' else -1
        y0 = y
        y1 = y + s * d
        sh.rect(x - w / 2, min(y0, y1), x + w / 2, max(y0, y1))
        sh.line((x - w / 2 + 50, y0 + s * 50), (x + w / 2 - 50, y0 + s * 50))
    else:
        s = 1 if wall == 'W' else -1
        x0, x1 = x, x + s * d
        sh.rect(min(x0, x1), y - w / 2, max(x0, x1), y + w / 2)
        sh.line((x0 + s * 50, y - w / 2 + 50), (x0 + s * 50, y + w / 2 - 50))


def sym_ac_outdoor(sh, x0, y0, w, d):
    sh.rect(x0, y0, x0 + w, y0 + d)
    sh.line((x0, y0), (x0 + w, y0 + d))
    sh.line((x0, y0 + d), (x0 + w, y0))


def sym_riser(sh, x, y, up=True, r=100):
    """立上り(↗)/引下げ(↙)"""
    sh.circle((x, y), r)
    if up:
        p, q = (x + r * 0.7, y + r * 0.7), (x + r * 2.2, y + r * 2.2)
    else:
        p, q = (x + r * 2.2, y + r * 2.2), (x + r * 0.7, y + r * 0.7)
    sh.line(p, q)
    arrow(sh, p, q, 80)


def sym_panel_L(sh, x0, y0, x1, y1):
    """分電盤 (JIS: 対角線の片側を塗る)"""
    sh.rect(x0, y0, x1, y1)
    sh.line((x0, y0), (x1, y1))
    n = 9
    for k in range(1, n + 1):
        t = k / (n + 1)
        y = y0 + (y1 - y0) * t
        x = x0 + (x1 - x0) * t
        sh.line((x0, y), (x, y))


def sym_panel_P(sh, x0, y0, x1, y1):
    """動力盤 (両対角+ハッチ)"""
    sh.rect(x0, y0, x1, y1)
    sh.line((x0, y0), (x1, y1))
    sh.line((x0, y1), (x1, y0))
    ym = (y0 + y1) / 2
    sh.line((x0, ym), (x1, ym))


def title_block(sh, x0, y0, dwg_no, title, scale='1/50', note=''):
    sh.L('_0-2_図枠', 7)
    w, h = 3100, 1550
    sh.rect(x0, y0, x0 + w, y0 + h)
    rows = [('件名', '樽屋 新築（改装）工事　電気設備'), ('図面名', title), ('図番', dwg_no + '　　縮尺 ' + scale + '（A3）'),
            ('日付', '2026年10月22日　' + note)]
    rh = h / len(rows)
    for i, (k, v) in enumerate(rows):
        yy = y0 + h - (i + 1) * rh
        sh.line((x0, yy), (x0 + w, yy))
        sh.text((x0 + 60, yy + rh * 0.3), k, 110)
        sh.text((x0 + 700, yy + rh * 0.3), v, 120 if len(v) < 26 else 100)
    sh.line((x0 + 640, y0), (x0 + 640, y0 + h))
