"""Wiring (配線) generator: one DXF layer per circuit, L-routes with large-R bends."""
import math
import cad
import data as D
import gen_plot as GP

R_BEND = 300          # 曲げ半径 (図上6mm)
CIR_COLOR = {
    'L-1-1': 1, 'L-1-2': 30, 'L-1-3': 5, 'L-1-5': 6, 'L-1-6': 150, 'L-1-7': 92, 'L-1-8': 212, 'L-1-9': 21,
    'L-1-10': 240, 'L-1-11': 200, 'L-1-12': 140, 'L-1-13': 6, 'L-1-14': 21, 'L-1-15': 160, 'L-1-16': 172,
    'L-1-17': 160, 'L-1-18': 190, 'L-1-19': 34, 'P-1-1': 10, 'P-1-2': 230, 'P-1-3': 180, 'P-1-4': 110,
}
CIR_NAME = {c[0]: c[1] for c in D.L1_CIRCUITS}
CIR_NAME.update({c[0]: c[1] for c in D.P1_CIRCUITS})
CIR_CABLE = {c[0]: c[5] for c in D.L1_CIRCUITS}
CIR_CABLE.update({c[0]: c[4] for c in D.P1_CIRCUITS})


def wlayer(sh, cir):
    nm = 'W-%s %s' % (cir, CIR_NAME[cir].replace(' ', '_'))
    sh.L(nm[:60], CIR_COLOR.get(cir, 7))


class Node:
    def __init__(self, x, y, trim, grp, kind, nid=''):
        self.x, self.y, self.trim, self.grp, self.kind, self.id = x, y, trim, grp, kind, nid

    @property
    def p(self):
        return (self.x, self.y)


TRIM = {'A': 80, 'B': 80, 'C': 150, 'E': 150, 'F': 150, 'G': 150, 'H': 150, 'I': 150, 'EM': 150, 'EX': 120,
        'SW': 80, 'OUT': 150, 'FAN': 150, 'LD': 10, 'RISER': 100}


def obstacles(floor):
    CUR_FLOOR[0] = floor
    pts = []
    if floor == 1:
        pts += [(d['x'], d['y']) for d in D.L1F]
        pts += [(d['x'], d['y'] + k) for d in D.L1F if d['t'] in 'AB' for k in (-450, -250, 250, 450)]
        pts += [(s['x'], s['y']) for s in D.SW1F]
        pts += [(o['x'], o['y']) for o in D.OUT1F]
        pts += [(f['x'], f['y']) for f in D.FAN1F]
        pts += D.GRILLE1F
        pts += _rect_pts(AC_RECT[1]) + _rect_pts(PANEL_RECT)
        pts += [(D.RISER1F[0], D.RISER1F[1])] + [(x, 8090) for x in range(13760, 14900, 250)]
        pts += [(x, y) for (x, y) in _sym_corners(D.FAN1F)]
        pts += [(d['x'] + dx, d['y'] + dy) for d in D.L1F if d['t'] == 'EX' for dx in (-110, 110) for dy in (-250, 250)]
    else:
        pts += [(d['x'], d['y']) for d in D.L2F]
        pts += [(s['x'], s['y']) for s in D.SW2F]
        pts += [(o['x'], o['y']) for o in D.OUT2F]
        pts += [(f['x'], f['y']) for f in D.FAN2F]
        pts += D.GRILLE2F
        pts += _rect_pts(AC_RECT[2]) + [(D.RISER2F[0], D.RISER2F[1])]
        pts += [(x, y) for (x, y) in _sym_corners(D.FAN2F)]
    return pts


AC_RECT = {1: [(6587, 8127, 8167, 8553), (10469, 5014, 11108, 6199), (14995, 2804, 15315, 3989),
               (9821, 12469, 10611, 12682), (12829, 12469, 13619, 12682)],
           2: [(12885, 1500, 13685, 1725), (15870, 5100, 16670, 5325)]}
PANEL_RECT = [(17263, 12487, 18491, 12787)]


def _rect_pts(rects, step=250):
    out = []
    for x0, y0, x1, y1 in rects:
        nx = max(int((x1 - x0) / step), 1)
        ny = max(int((y1 - y0) / step), 1)
        for i in range(nx + 1):
            for j in range(ny + 1):
                out.append((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny))
    return out


def _sym_corners(fans):
    return [(f['x'] + dx, f['y'] + dy) for f in fans for dx in (-150, 150) for dy in (-150, 150)]


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.dist(p, a)
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


MIN_R = 150   # 最小曲げ半径 (図上3mm)
BOUNDS = {1: (4985, 1515, 18695, 12785), 2: (11800, 1500, 17700, 7330)}
CUR_FLOOR = [1]


def _legs_ok(pts, ta, tb):
    n = len(pts)
    if n == 2:
        return True
    for i in range(n - 1):
        L = math.dist(pts[i], pts[i + 1])
        if i == 0:
            L -= ta
        if i == n - 2:
            L -= tb
        need = MIN_R * 1.08 * (2 if 0 < i < n - 2 else 1)
        if L < need:
            return False
    return True


def candidates(a, b):
    ax, ay = a.p
    bx, by = b.p
    c = [cad.lroute(a.p, b.p, 'h'), cad.lroute(a.p, b.p, 'v')]
    if abs(ax - bx) > 30 and abs(ay - by) > 30:
        for ym in ((ay + by) / 2, ay + 450, ay - 450, by + 450, by - 450, ay + 750, ay - 750, by + 750, by - 750):
            c.append([a.p, (ax, ym), (bx, ym), b.p])
        for xm in ((ax + bx) / 2, ax + 450, ax - 450, bx + 450, bx - 450, ax + 750, ax - 750, bx + 750, bx - 750):
            c.append([a.p, (xm, ay), (xm, by), b.p])
    elif abs(ay - by) <= 30:
        for off in (350, -350):
            c.append([a.p, (ax, ay + off), (bx, ay + off), b.p])
    else:
        for off in (350, -350):
            c.append([a.p, (ax + off, ay), (ax + off, by), b.p])
    return c


def best_route(a, b, obs):
    best = None
    for k, pts in enumerate(candidates(a, b)):
        pts = cad.clean_pts(pts)
        if not _legs_ok(pts, a.trim, b.trim):
            continue
        bx0, by0, bx1, by1 = BOUNDS[CUR_FLOOR[0]]
        if any(not (bx0 <= p[0] <= bx1 and by0 <= p[1] <= by1) for p in pts):
            continue
        sc = 0
        for o in obs:
            if math.dist(o, a.p) < 40 or math.dist(o, b.p) < 40:
                continue
            dmin = min(seg_dist(o, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            if dmin < 230:
                sc += 1
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        man = abs(a.x - b.x) + abs(a.y - b.y)
        sc += 0.25 * (len(pts) - 3 if len(pts) > 3 else 0) + (L - man) / 3000.0 + k * 0.001
        if best is None or sc < best[0]:
            best = (sc, pts)
    if best is None:
        return [a.p, b.p]
    return best[1]


def edge_w(a, b):
    d = abs(a.x - b.x) + abs(a.y - b.y)
    if a.kind == 'SW' and b.kind == 'SW':
        return d * (1.0 if math.dist(a.p, b.p) < 400 else 3.0)
    if a.kind == 'SW' or b.kind == 'SW':
        s, o = (a, b) if a.kind == 'SW' else (b, a)
        return d * (1.0 if o.grp == s.grp else 3.0)
    if a.grp is None or b.grp is None or a.grp == b.grp:
        return d
    return d * 1.7


def mst(nodes, root):
    inT = {root}
    edges = []
    while len(inT) < len(nodes):
        best = None
        for i in inT:
            for j in range(len(nodes)):
                if j in inT:
                    continue
                w = edge_w(nodes[i], nodes[j])
                if best is None or w < best[0]:
                    best = (w, i, j)
        inT.add(best[2])
        edges.append((best[1], best[2]))
    return edges


def label_on_path(sh, pts, txt, h=90, side=1, minlen=1200, frac=0.5):
    # longest straight piece
    best = None
    for i in range(len(pts) - 1):
        L = math.dist(pts[i], pts[i + 1])
        if best is None or L > best[0]:
            best = (L, pts[i], pts[i + 1])
    L, p, q = best
    if L < minlen:
        return
    mx, my = p[0] + (q[0] - p[0]) * frac, p[1] + (q[1] - p[1]) * frac
    if abs(p[1] - q[1]) < 1:
        sh.text((mx, my + 60 * side), txt, h, 0, 'C')
    else:
        sh.text((mx - 60 * side, my), txt, h, 90, 'C')


def draw_edge(sh, a, b, obs, txt=None, pts=None, minlen=1200):
    if pts is None:
        pts = best_route(a, b, obs)
    pts = cad.trim_pts(pts, a.trim, b.trim)
    cad.draw_segs(sh, cad.fillet(pts, R_BEND))
    if txt:
        label_on_path(sh, pts, txt, minlen=minlen)
    return pts


HR_DIR = {'L-1-5': (0, -1), 'L-1-16': (0, -1), 'L-1-10': (0, 1), 'L-1-19': (-1, 0), 'L-1-6': (0, 1), 'L-1-7': (0, -1)}
HR_LEFT = set()
ROOT_ID = {}


def homerun(sh, node, target, cir, length=900, txt=None):
    d = cad._norm((target[0] - node.x, target[1] - node.y))
    # snap direction to the dominant axis for a clean JIS-style arrow
    if abs(d[0]) > abs(d[1]):
        d = (1 if d[0] > 0 else -1, 0)
    else:
        d = (0, 1 if d[1] > 0 else -1)
    d = HR_DIR.get(cir, d)
    p = (node.x + d[0] * node.trim, node.y + d[1] * node.trim)
    q = (p[0] + d[0] * length, p[1] + d[1] * length)
    sh.line(p, q)
    cad.arrow(sh, p, q, 160)
    t = txt or cir
    if d[1] == 0:
        sh.text((q[0] + (60 if d[0] > 0 else -60), q[1] + 50), t, 110, 0, 'L' if d[0] > 0 else 'R')
    elif cir in HR_LEFT:
        sh.text((q[0] - 80, q[1] - 200), t, 110, 0, 'R')
    else:
        sh.text((q[0] + 60, q[1] + (40 if d[1] > 0 else -140)), t, 110)


# --------------------------------------------------------------------- build nodes per circuit
def light_nodes(floor, cir):
    L = D.L1F if floor == 1 else D.L2F
    SW = D.SW1F if floor == 1 else D.SW2F
    FAN = D.FAN1F if floor == 1 else D.FAN2F
    nodes = []
    groups = set()
    for d in L:
        if d['cir'] != cir or d['t'] == 'D':
            continue
        nodes.append(Node(d['x'], d['y'], TRIM[d['t']], d['grp'], d['t']))
        if d['grp']:
            groups.add(d['grp'])
    if floor == 1:
        for (p, q, nm), g in zip(D.LD1, ('f', 'g', 'h')):
            if any(d['t'] == 'D' and d['grp'] == g and d['cir'] == cir for d in L):
                sw = [s for s in SW if s['g'] == g]
                cx = sum(s['x'] for s in sw) / len(sw)
                cy = sum(s['y'] for s in sw) / len(sw)
                end = p if math.dist(p, (cx, cy)) <= math.dist(q, (cx, cy)) else q
                nodes.append(Node(end[0], end[1], TRIM['LD'], g, 'LD', nm))
                groups.add(g)
    for f in FAN:
        if f['cir'] == cir:
            nodes.append(Node(f['x'], f['y'], TRIM['FAN'], f['g'], 'FAN', f['id']))
            groups.add(f['g'])
    for s in SW:
        if s['g'] in groups:
            nodes.append(Node(s['x'], s['y'], TRIM['SW'], s['g'], 'SW', s['k']))
    return nodes


RISER_ROOT_1F = {'L-1-3'}


def wire_lighting(sh, floor):
    import wire2
    cirs = ['L-1-1', 'L-1-2', 'L-1-3', 'L-1-24'] if floor == 1 else ['L-1-3', 'L-1-24']
    items = [(c, wire2.build_light(floor, c)) for c in cirs if wire2.loads(floor, c)]
    hr = [wire2.homerun_seg(T) for c, T in items if T['homerun']] + RISER_FIXED.get(floor, [])
    wire2.render(sh, items, fixed=hr, layer_fn=lambda c: wlayer(sh, c), floor=floor)
    for cir, T in items:
        wlayer(sh, cir)
        if T['homerun']:
            wire2.homerun_tree(sh, T, cir + ' (L-1へ)')
        else:
            r = T['nodes'][T['root']]
            dy = {'L-1-3': 170, 'L-1-24': 310}.get(cir, 170)
            sh.text((r.x - 160, r.y + dy), cir, 95, 0, 'R')


def wire_outlets(sh, floor):
    import wire2
    OUT = D.OUT1F if floor == 1 else D.OUT2F
    cirs = []
    for o in OUT:
        if o['cir'] not in cirs:
            cirs.append(o['cir'])
    items = [(c, wire2.build_outlet(floor, c)) for c in cirs]
    fixed = list(P_ROUTES.values()) if floor == 1 else []
    routes = REF_ROUTES_1F if floor == 1 else REF_ROUTES_2F
    fixed += [cad.offset_poly(cad.clean_pts(p), -220) for p in routes.values()]
    fixed += [wire2.homerun_seg(T) for c, T in items if T['homerun']] + RISER_FIXED.get(floor, [])
    wire2.render(sh, items, fixed=fixed, layer_fn=lambda c: wlayer(sh, c), floor=floor)
    for cir, T in items:
        wlayer(sh, cir)
        if T['homerun']:
            wire2.homerun_tree(sh, T, cir)
        else:
            e0 = [e for e in T['edges'] if T['root'] in (e['i'], e['j'])][0]
            label_on_path(sh, cad.trim_pts(e0['pts'], 100, 150), cir, 90, -1, minlen=0, frac=0.8)


P_ROUTES = {   # 盤P-1 → 手元開閉器S (下ろし順を入替えて交差なし)
    'P-1-1': [(17563, 12487), (17563, 10750), (9000, 10750), (9000, 9650), (5300, 9650), (5300, 8780)],
    'P-1-2': [(17443, 12487), (17443, 10850), (8300, 10850), (8300, 13020)],
    'P-1-3': [(17323, 12487), (17323, 10950), (11800, 10950), (11800, 13020)],
    'P-1-4': [(17263, 12637), (15920, 12637), (15920, 13070)],
}
P_TAIL = {    # 手元開閉器S → 機器
    'P-1-1': [(5430, 8650), (5624, 8650)],
    'P-1-2': [(8170, 13150), (7848, 13150)],
    'P-1-3': [(11670, 13150), (11553, 13150)],
    'P-1-4': [(16050, 13200), (16100, 13200)],
}


def wire_power(sh):
    import wire2
    arcs = [('A', e['c'], e['r'], e['a0'], e['a1']) for e in sh.prev
            if e['type'] == 'ARC' and e['layer'].startswith('W-L')]   # 円弧は切れないため動力側を切り欠く
    for cir, pts in P_ROUTES.items():
        wlayer(sh, cir)
        wire2.draw_cut(sh, cad.fillet(pts, R_BEND), arcs)
        sh.line(*P_TAIL[cir])
        fr = {'P-1-1': 0.22, 'P-1-2': 0.5, 'P-1-3': 0.78, 'P-1-4': 0.35}[cir]
        label_on_path(sh, pts, cir + ' ' + CIR_CABLE[cir].replace(' ', '') + ' (' + CIR_NAME[cir].split(' ')[0] + ')', 80,
                      -1 if cir in ('P-1-2', 'P-1-4') else 1, minlen=0, frac=fr)
    wlayer(sh, 'P-1-1')
    sh.text((5850, 9480), 'P-1-1 いけす 3φ200V 30A', 100)
    hand_switches(sh)


# 冷媒/内外連絡ルート (M図と共用)
REF_ROUTES_1F = {
    'AC-1': [(7377, 8553), (7377, 12988)],
    'AC-2': [(10788, 6199), (10788, 12250), (11148, 12250), (11148, 12988)],
    'AC-3': [(15155, 3989), (15155, 5300), (16000, 5300), (16000, 12250), (16505, 12250), (16505, 12988)],
    'AC-4': [(10216, 12682), (10216, 12988)],
    'AC-5': [(13224, 12682), (13224, 12988)],
}
REF_ROUTES_2F = {
    'AC-6': [(13285, 1725), (13285, 7600)],
    'AC-7': [(16270, 5325), (16270, 7600)],
}


def wire_link(sh, floor):
    sh.L('W-空調 内外連絡線', 8)
    routes = REF_ROUTES_1F if floor == 1 else REF_ROUTES_2F
    import wire2
    cutters = []
    if floor == 1:
        for p in P_ROUTES.values():
            cutters += [s_ for s_ in cad.fillet(p, R_BEND)]
    # 既に描いた配線(電灯・コンセント・動力・矢印)と交わる位置は連絡線側を切り欠く
    for e in sh.prev:
        if not e['layer'].startswith(('W-L', 'W-P')):
            continue
        if e['type'] == 'LINE' and math.dist(e['p1'], e['p2']) > 200:
            cutters.append(('L', e['p1'], e['p2']))
        elif e['type'] == 'ARC':
            cutters.append(('A', e['c'], e['r'], e['a0'], e['a1']))
    for k, pts in routes.items():
        off = cad.offset_poly(cad.clean_pts(pts), -220)
        wire2.draw_cut(sh, cad.fillet(off, R_BEND), cutters, 'DASHED')
        if len(pts) > 2 or math.dist(pts[0], pts[-1]) > 2000:
            label_on_path(sh, off, k + ' 内外連絡線 VVF2.0-3C', 80, -1)


def risers(sh, floor):
    sh.L('W-立上り・引下げ', 7)
    x, y = D.RISER1F if floor == 1 else D.RISER2F
    cad.sym_riser(sh, x, y, up=(floor == 1))
    lst = RISER_LIST
    if floor == 1:
        sh.text((x + 150, y + 330), '2F立上り', 100)
        import wire2
        (p, q) = RISER_FIXED[1][0]
        arcs = [('A', e['c'], e['r'], e['a0'], e['a1']) for e in sh.prev
                if e['type'] == 'ARC' and e['layer'].startswith('W-L')]
        wire2.draw_cut(sh, [('L', p, q)], arcs)      # 円弧と交わる位置は矢印側を切り欠く
        cad.arrow(sh, p, q, 160)
        sh.text((q[0] + 60, q[1] + 40), '2F分 (L-1へ)', 110)
    else:
        sh.text((x - 4500, y + 2300), '配線引下げ(1Fより・図中○↙) : ' + lst, 100)
        sh.text((x - 4500, y + 2100), '予備 L-1-20〜23 : PF22×4 空配管 (天井内ボックス止め)', 100)
        sh.text((x + 150, y + 160), '引下げ', 90)


def cad_node(x, y):
    return Node(x, y, 100, None, 'RISER')


RISER_FIXED = {1: [[(13700, 7100), (13700, 8000)]]}   # 2F分 ホームラン矢印
RISER_LIST = 'L-1-3(3路渡り含), L-1-13, L-1-14, L-1-17, L-1-18, L-1-24(非常)'
HAND_SW = [  # 室外機・いけす 手元開閉器 (屋外形 ELB箱)
    ('AC-1', 8300, 13150), ('AC-2', 11800, 13150), ('AC-3', 15920, 13200), ('いけす', 5300, 8650),
]


def hand_switches(sh):
    sh.L('E-動力-手元開閉器', 10)
    for nm, x, y in HAND_SW:
        sh.rect(x - 130, y - 130, x + 130, y + 130)
        sh.text((x, y), 'S', 120, 0, 'MC')
        sh.text((x + 180, y - 280), '手元開閉器(' + nm + ')', 70)
