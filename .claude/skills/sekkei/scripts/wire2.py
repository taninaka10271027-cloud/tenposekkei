"""配線ツリー構築 (JB結線・器具ジョイント・送り配線) と 条数(電線本数)計算.

各回路の電線を「ネット」(L / N / 各スイッチ返り / 3路渡り)として、配線ツリー上の
経路を追跡し、区間ごとの条数を求める。図面描画と数量拾い出しの両方で使う。
"""
import math
from collections import defaultdict
import cad
import data as D
import gen_wire as W

PANEL_L_TOP = ((D.PANEL_L[0] + D.PANEL_L[2]) / 2, D.PANEL_L[1])
JB_OFF = 700          # スイッチボックス→JB の距離
TRIM_JB = 100


class N:
    def __init__(self, key, x, y, kind, trim, grp=None, label=''):
        self.key, self.x, self.y, self.kind, self.trim, self.grp, self.label = key, x, y, kind, trim, grp, label

    @property
    def p(self):
        return (self.x, self.y)


def boxes(floor):
    """スイッチ群(200mm以内)= 1ボックス"""
    lst = D.SW1F if floor == 1 else D.SW2F
    used = [False] * len(lst)
    res = []
    for i, s in enumerate(lst):
        if used[i]:
            continue
        grp = [i]
        used[i] = True
        ch = True
        while ch:
            ch = False
            for j, t in enumerate(lst):
                if not used[j] and any(math.dist((t['x'], t['y']), (lst[g]['x'], lst[g]['y'])) <= 200 for g in grp):
                    grp.append(j)
                    used[j] = True
                    ch = True
        sws = [lst[g] for g in grp]
        cx = sum(s['x'] for s in sws) / len(sws)
        cy = sum(s['y'] for s in sws) / len(sws)
        res.append(dict(idx=len(res), x=cx, y=cy, sws=sws))
    return res


def group_circuit():
    """点滅区分 g → 回路"""
    gc = {}
    for L in (D.L1F, D.L2F):
        for d in L:
            if d.get('grp'):
                gc[d['grp'] + ('@2' if L is D.L2F else '')] = d['cir']
    for fl, F in ((1, D.FAN1F), (2, D.FAN2F)):
        for f in F:
            gc[f['g'] + ('@2' if fl == 2 else '')] = f['cir']
    return gc


GC = group_circuit()


def gkey(g, floor):
    return g + ('@2' if floor == 2 else '')


def cir_of_switch(s, floor):
    k = gkey(s['g'], floor)
    if k in GC:
        return GC[k]
    # 3路 s は 1F/2F 共通の回路
    other = gkey(s['g'], 2 if floor == 1 else 1)
    return GC.get(other)


def loads(floor, cir):
    """回路の負荷ノード (照明器具・LD給電点・換気扇・非常灯)"""
    L = D.L1F if floor == 1 else D.L2F
    F = D.FAN1F if floor == 1 else D.FAN2F
    SW = D.SW1F if floor == 1 else D.SW2F
    res = []
    for i, d in enumerate(L):
        if d['cir'] != cir or d['t'] == 'D':
            continue
        res.append(N(('F', floor, i), d['x'], d['y'], d['t'], W.TRIM[d['t']], d.get('grp'), d['t']))
    if floor == 1:
        for (p, q, nm), g in zip(D.LD1, ('f', 'g', 'h')):
            if any(d['t'] == 'D' and d['grp'] == g and d['cir'] == cir for d in L):
                sw = [s for s in SW if s['g'] == g]
                if g in PAIRS and PAIRS[g][1][0] == floor:
                    sw = [PAIRS[g][1][1]]            # 3路は負荷側スイッチのJBから給電
                cx = sum(s['x'] for s in sw) / len(sw)
                cy = sum(s['y'] for s in sw) / len(sw)
                end = p if math.dist(p, (cx, cy)) <= math.dist(q, (cx, cy)) else q
                res.append(N(('LD', g), end[0], end[1], 'LD', 10, g, nm))
    for f in F:
        if f['cir'] == cir:
            res.append(N(('FAN', f['id']), f['x'], f['y'], 'FAN', 150, f['g'], f['id']))
    return res


def three_way_pairs():
    """g -> (supply(floor,sw), load(floor,sw))"""
    allsw = [(1, s) for s in D.SW1F if s['k'] == '3'] + [(2, s) for s in D.SW2F if s['k'] == '3']
    by = defaultdict(list)
    for fl, s in allsw:
        by[s['g']].append((fl, s))
    res = {}
    for g, lst in by.items():
        if len(lst) != 2:
            continue
        two = [x for x in lst if x[0] == 2]
        sup = two[0] if two else lst[0]
        ld = [x for x in lst if x is not sup][0]
        res[g] = (sup, ld)
    return res


PAIRS = three_way_pairs()


def _bounds_ok(p, floor):
    x0, y0, x1, y1 = W.BOUNDS[floor]
    return x0 + 100 <= p[0] <= x1 - 100 and y0 + 100 <= p[1] <= y1 - 100


def build_light(floor, cir):
    """returns dict(nodes, edges[(i,j,pts,n,power,nets)], root, homerun)"""
    obs = W.obstacles(floor)
    ld = loads(floor, cir)
    nodes = list(ld)
    idx = {n.key: i for i, n in enumerate(nodes)}
    riser_root = floor == 2 or cir in W.RISER_ROOT_1F
    bx = []
    for b in boxes(floor):
        sws = [s for s in b['sws'] if cir_of_switch(s, floor) == cir]
        if sws:
            bx.append(dict(b, sws=sws))
    edges_spec = []    # (i, j, power)

    def add_node(n):
        nodes.append(n)
        idx[n.key] = len(nodes) - 1
        return len(nodes) - 1

    joint_of_box = {}
    for b in bx:
        bi = add_node(N(('BOX', floor, b['idx']), b['x'], b['y'], 'BOX', 90, None, ''))
        light_groups = {s['g'] for s in b['sws'] if s['k'] in 'S3'}
        fan_groups = {s['g'] for s in b['sws'] if s['k'] == 'V'}
        ctrl = [n for n in ld if n.grp in light_groups | fan_groups]
        lights = [n for n in ld if n.grp in light_groups and n.kind != 'FAN']
        if fan_groups and len(light_groups) == 1 and lights:
            j = min(lights, key=lambda n: math.dist(n.p, b and (b['x'], b['y'])))
            ji = idx[j.key]                                   # 照明器具でジョイント
        elif fan_groups and not light_groups:
            fans = [n for n in ld if n.grp in fan_groups]
            ji = idx[min(fans, key=lambda n: math.dist(n.p, (b['x'], b['y']))).key]   # 換気扇でジョイント
        else:
            # JB: ボックスから制御負荷の方向へ JB_OFF
            if ctrl:
                cx = sum(n.x for n in ctrl) / len(ctrl)
                cy = sum(n.y for n in ctrl) / len(ctrl)
            else:
                cx, cy = b['x'], b['y'] + 1000
            best = None
            base = math.atan2(cy - b['y'], cx - b['x'])
            # JBはスイッチボックスの真上下左右 (ボックス→JBを直線に)
            for dist in (500, JB_OFF, JB_OFF + 300, JB_OFF + 600):
                for ang in (0, math.pi / 2, math.pi, -math.pi / 2):
                    p = (b['x'] + dist * math.cos(ang), b['y'] + dist * math.sin(ang))
                    if not _bounds_ok(p, floor):
                        continue
                    da = abs((ang - base + math.pi) % (2 * math.pi) - math.pi)
                    near = sum(1 for o in obs if math.dist(o, p) < 350) + sum(2 for o in obs if math.dist(o, p) < 220)
                    sc = near * 2 + da * 0.8 + abs(dist - JB_OFF) / 600
                    if best is None or sc < best[0]:
                        best = (sc, p)
            p = best[1] if best else (b['x'], b['y'] - JB_OFF)
            ji = add_node(N(('JB', floor, b['idx'], cir), p[0], p[1], 'JB', TRIM_JB, None, 'JB'))
        joint_of_box[b['idx']] = ji
        edges_spec.append((bi, ji, False, None))
    # 換気扇・照明グループ → ジョイント
    groups = defaultdict(list)
    for n in ld:
        if n.grp:
            groups[n.grp].append(idx[n.key])

    def box_for_group(g):
        cand = []
        for b in bx:
            for s in b['sws']:
                if s['g'] == g:
                    cand.append((b, s))
        if not cand:
            return None
        if g in PAIRS:
            ldfl, lds = PAIRS[g][1]
            for b, s in cand:
                if s is lds:
                    return b
        return cand[0][0]

    for g, members in groups.items():
        b = box_for_group(g)
        J = joint_of_box[b['idx']] if b else None
        # 送り配線 (同一点滅区分)
        sub = [nodes[i] for i in members]
        if len(sub) > 1:
            root = 0
            if J is not None:
                root = min(range(len(sub)), key=lambda k: math.dist(sub[k].p, nodes[J].p))
            pool = list(members) + ([J] if J is not None and J not in members else [])
            for a, c in W.mst(sub, root):
                edges_spec.append((members[a], members[c], False, pool))
        if J is not None and J not in members:
            near = min(members, key=lambda i: math.dist(nodes[i].p, nodes[J].p))
            edges_spec.append((J, near, False, list(members) + [J]))
    # 電源(送り) : ハブ = ジョイント + 非点滅負荷 + 立上り
    hubs = sorted(set(joint_of_box.values()))
    for n in ld:
        if not n.grp:
            hubs.append(idx[n.key])
    if riser_root:
        rp = D.RISER1F if floor == 1 else D.RISER2F
        r = add_node(N(('RISER', floor), rp[0], rp[1], 'RISER', 100, None, ''))
        hubs = [r] + hubs
        root = r
    else:
        root = min(hubs, key=lambda i: math.dist(nodes[i].p, PANEL_L_TOP))
        hubs.remove(root)
        hubs = [root] + hubs
    if riser_root and len(hubs) > 1:
        rest = hubs[1:]
        hn = [nodes[i] for i in rest]
        for a, c in W.mst(hn, 0) if len(hn) > 1 else []:
            edges_spec.append((rest[a], rest[c], True, list(rest)))
        near = min(rest, key=lambda i: abs(nodes[i].x - nodes[root].x) + abs(nodes[i].y - nodes[root].y))
        edges_spec.append((root, near, True, None))          # 立上り → 最寄りハブ 1本
    else:
        hn = [nodes[i] for i in hubs]
        for a, c in W.mst(hn, 0) if len(hn) > 1 else []:
            edges_spec.append((hubs[a], hubs[c], True, list(hubs)))
    # ---- 経路
    edges = []
    for i, j, pw, pool in edges_spec:
        a, b = nodes[i], nodes[j]
        pts = W.best_route(W.Node(a.x, a.y, a.trim, None, a.kind), W.Node(b.x, b.y, b.trim, None, b.kind), obs)
        edges.append(dict(i=i, j=j, pts=pts, power=pw, base_power=pw, nets=set(), pool=pool))
    # ---- ネット
    nets = defaultdict(set)
    nets['N'].add(root)
    nets['L'].add(root)
    for n in ld:
        nets['N'].add(idx[n.key])
        if not n.grp:
            nets['L'].add(idx[n.key])
    for b in bx:
        bi = idx[('BOX', floor, b['idx'])]
        for s in b['sws']:
            g = s['g']
            tgt = [idx[n.key] for n in ld if n.grp == g]
            if s['k'] == '3' and g in PAIRS:
                (sfl, ssw), (lfl, lsw) = PAIRS[g]
                nets['T1' + g].add(bi)
                nets['T2' + g].add(bi)
                if (sfl != lfl):
                    nets['T1' + g].add(root)
                    nets['T2' + g].add(root)
                if s is ssw:
                    nets['L'].add(bi)
                    if sfl != lfl or not tgt:
                        pass
                else:
                    nets['R' + g].add(bi)
                    nets['R' + g].update(tgt)
                    # 他階の負荷へ
                    other = 2 if floor == 1 else 1
                    if any(d.get('grp') == g for d in (D.L2F if other == 2 else D.L1F)):
                        nets['R' + g].add(root)
            else:
                nets['L'].add(bi)
                nets['R' + g + str(id(s))].add(bi)
                nets['R' + g + str(id(s))].update(tgt)
    # 3路 返り線: 負荷側スイッチが他階のとき、この階の負荷は立上りから
    for g, ((sfl, ssw), (lfl, lsw)) in PAIRS.items():
        if lfl != floor:
            tgt = [idx[n.key] for n in ld if n.grp == g]
            if tgt:
                nets['R' + g].update(tgt)
                nets['R' + g].add(root)
    T = dict(nodes=nodes, edges=edges, root=root, homerun=not riser_root, floor=floor, cir=cir, nets=nets)
    count_conductors(T)
    return T


def count_conductors(T):
    """ネットの経路を辿り、区間ごとの条数を求める"""
    nodes, edges, nets = T['nodes'], T['edges'], T['nets']
    for e in edges:
        e['nets'] = set()
    adj = defaultdict(list)
    for k, e in enumerate(edges):
        adj[e['i']].append((e['j'], k))
        adj[e['j']].append((e['i'], k))

    def path(u, v):
        prev = {u: None}
        st = [u]
        while st:
            x = st.pop()
            if x == v:
                break
            for y, k in adj[x]:
                if y not in prev:
                    prev[y] = (x, k)
                    st.append(y)
        res = []
        x = v
        while prev.get(x):
            x, k = prev[x]
            res.append(k)
        return res

    for nm, terms in nets.items():
        terms = [t for t in terms if t is not None]
        if len(terms) < 2:
            continue
        t0 = terms[0]
        used = set()
        for t in terms[1:]:
            used.update(path(t0, t))
        for k in used:
            edges[k]['nets'].add(nm)
    for e in edges:
        e['n'] = len(e['nets'])
        e['npow'] = sum(1 for x in e['nets'] if x in ('L', 'N'))
        e['power'] = (e['base_power'] or nodes[e['i']].kind == 'RISER' or nodes[e['j']].kind == 'RISER') and e['npow'] == 2


def build_outlet(floor, cir):
    obs = W.obstacles(floor)
    OUT = D.OUT1F if floor == 1 else D.OUT2F
    nodes = [N(('OUT', floor, k), o['x'], o['y'], 'OUT', 150, None, o['t']) for k, o in enumerate(OUT) if o['cir'] == cir]
    if floor == 1:
        root = min(range(len(nodes)), key=lambda i: math.dist(nodes[i].p, PANEL_L_TOP))
        homerun = True
    else:
        nodes.append(N(('RISER', 2), D.RISER2F[0], D.RISER2F[1], 'RISER', 100))
        root = len(nodes) - 1
        homerun = False
    cab = W.CIR_CABLE[cir]
    ncond = 3 if '3C' in cab else 2
    edges = []
    if floor == 2:      # 立上りからは1本 → コンセント間は送り
        outs = list(range(len(nodes) - 1))
        near = min(outs, key=lambda i: abs(nodes[i].x - nodes[root].x) + abs(nodes[i].y - nodes[root].y))
        sub = [nodes[i] for i in outs]
        pairs = [(outs[a], outs[c]) for a, c in W.mst(sub, outs.index(near))] if len(sub) > 1 else []
        pairs = [(root, near)] + pairs
    else:
        pairs = W.mst(nodes, root)
    for a, c in pairs:
        A, B = nodes[a], nodes[c]
        pts = W.best_route(W.Node(A.x, A.y, A.trim, None, 'OUT'), W.Node(B.x, B.y, B.trim, None, 'OUT'), obs)
        edges.append(dict(i=a, j=c, pts=pts, power=True, base_power=True, n=ncond, npow=ncond, nets=set(),
                          pool=None if nodes[a].kind == 'RISER' or nodes[c].kind == 'RISER'
                          else [k for k in range(len(nodes)) if nodes[k].kind != 'RISER']))
    return dict(nodes=nodes, edges=edges, root=root, homerun=homerun, floor=floor, cir=cir, ncond=ncond)


# ------------------------------------------------------------------------------ 描画
def ticks(sh, pts, n, power, size=None):
    """最長直線部の中央に条数の斜線、電源は2.0を併記"""
    best = None
    for k in range(len(pts) - 1):
        L = math.dist(pts[k], pts[k + 1])
        if best is None or L > best[0]:
            best = (L, pts[k], pts[k + 1])
    L, p, q = best
    ticks_at(sh, p, q, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), n, power, size)


def ticks_at(sh, p, q, m, n, power, size=None):
    d = cad._norm((q[0] - p[0], q[1] - p[1]))
    nr = (-d[1], d[0])
    sp = 55
    start = -(n - 1) * sp / 2
    # 斜線: 線方向から60°
    v = (d[0] * 0.5 + nr[0] * 0.866, d[1] * 0.5 + nr[1] * 0.866)
    for k in range(n):
        c = (m[0] + d[0] * (start + k * sp), m[1] + d[1] * (start + k * sp))
        sh.line((c[0] - v[0] * 90, c[1] - v[1] * 90), (c[0] + v[0] * 90, c[1] + v[1] * 90))
    if power or size:
        t = size or '2.0'
        horiz = abs(d[1]) < 0.5
        if horiz:
            tp = (m[0], m[1] + 105)
            sh.text(tp, t, 85, 0, 'C')
        else:
            tp = (m[0] - 105, m[1])
            sh.text(tp, t, 85, 90, 'C')


def sym_jb(sh, x, y, r=100):
    """VVF用ジョイントボックス"""
    sh.circle((x, y), r)
    k = r * 0.707
    sh.line((x - k, y - k), (x + k, y + k))


def draw_tree(sh, T):
    nodes = T['nodes']
    for e in T['edges']:
        a, b = nodes[e['i']], nodes[e['j']]
        pts = cad.trim_pts(e['pts'], a.trim, b.trim)
        cad.draw_segs(sh, cad.fillet(pts, W.R_BEND))
        if e['n'] > 0:
            ticks(sh, pts, e['n'], e['power'] and e['npow'] > 0)
    for n in nodes:
        if n.kind == 'JB':
            sym_jb(sh, n.x, n.y)


def homerun_tree(sh, T, label):
    r = T['nodes'][T['root']]
    p, q = homerun_seg(T)
    arcs = [('A', e['c'], e['r'], e['a0'], e['a1']) for e in sh.prev
            if e['type'] == 'ARC' and e['layer'].startswith('W-L')]
    draw_cut(sh, [('L', p, q)], arcs)        # 円弧と交わる位置は矢印側を切り欠く
    cad.arrow(sh, p, q, 160)
    d = cad._norm((q[0] - p[0], q[1] - p[1]))
    if abs(d[1]) < 0.5:
        sh.text((q[0] + (60 if d[0] > 0 else -60), q[1] + 50), label, 110, 0, 'L' if d[0] > 0 else 'R')
    else:
        sh.text((q[0] + 60, q[1] + (40 if d[1] > 0 else -140)), label, 110)
    # 条数 (電源2本 or 3本) 2.0
    d = cad._norm((PANEL_L_TOP[0] - r.x, PANEL_L_TOP[1] - r.y))
    d = (1 if d[0] > 0 else -1, 0) if abs(d[0]) > abs(d[1]) else (0, 1 if d[1] > 0 else -1)
    d = W.HR_DIR.get(T['cir'], d)
    p = (r.x + d[0] * r.trim, r.y + d[1] * r.trim)
    q = (p[0] + d[0] * 600, p[1] + d[1] * 600)
    ticks(sh, [p, q], T.get('ncond', 2), True)


# ------------------------------------------------------------------------------ 重なり回避・交差切り欠き
SEP = 100        # 平行線の離隔
GAP = 70         # 交差部の切り欠き (片側)


def _segs(pts):
    out = []
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        if abs(a[1] - b[1]) < 1:
            out.append(('H', a[1], min(a[0], b[0]), max(a[0], b[0]), k))
        elif abs(a[0] - b[0]) < 1:
            out.append(('V', a[0], min(a[1], b[1]), max(a[1], b[1]), k))
        else:
            out.append((None, 0, 0, 0, k))
    return out


def _conflict(o, c, lo, hi, placed):
    for po, pc, plo, phi in placed:
        if po == o and abs(pc - c) < SEP - 1 and min(hi, phi) - max(lo, plo) > 120:
            return True
    return False


def _shift(pts, k, d, o, t0, t1, al0=0, al1=0):
    """区間kを直角方向にdずらす。端部は器具記号内で接続点をずらせる場合はそのまま、
    できない場合は器具から出た位置でクランク"""
    n = len(pts)
    A, B = pts[k], pts[k + 1]
    L = math.dist(A, B)
    u = ((B[0] - A[0]) / L, (B[1] - A[1]) / L)
    off = (0, d) if o == 'H' else (d, 0)
    mv = lambda p: (p[0] + off[0], p[1] + off[1])
    lead0, lead1 = t0 + 35, t1 + 35
    if k == 0 and abs(d) <= al0:
        prefix = [mv(A)]                       # 記号内で接続点をずらす
    elif k == 0:
        if L < lead0 + lead1 + 200:
            return None
        L0 = (A[0] + u[0] * lead0, A[1] + u[1] * lead0)
        prefix = [A, L0, mv(L0)]
    else:
        prefix = pts[:k] + [mv(A)]
    if k + 1 == n - 1 and abs(d) <= al1:
        suffix = [mv(B)]
    elif k + 1 == n - 1:
        if L < lead0 + lead1 + 200:
            return None
        L1 = (B[0] - u[0] * lead1, B[1] - u[1] * lead1)
        suffix = [mv(L1), L1, B]
    else:
        suffix = [mv(B)] + pts[k + 2:]
    return prefix + suffix


def separate(polys, fixed=()):
    """polys を順に配置し、平行重なりを SEP ずらす。ずらし方向は交差が増えない側を選ぶ"""
    placed = []
    placed_lines = []
    for fp in fixed:
        fp = cad.clean_pts(fp)
        for o, c, lo, hi, k in _segs(fp):
            if o:
                placed.append((o, c, lo, hi))
        placed_lines += [(fp[i], fp[i + 1]) for i in range(len(fp) - 1)]
    # 後で配置される線とも交差判定するため、全ポリラインの現形状を参照
    for idx, P in enumerate(polys):
        pts = [tuple(p) for p in P['pts']]
        later = []
        for Q in polys[idx + 1:]:
            q = Q['pts']
            later += [(q[i], q[i + 1]) for i in range(len(q) - 1)]
        ref = placed_lines + later
        for _ in range(8):
            changed = False
            for o, c, lo, hi, k in _segs(pts):
                if not o or not _conflict(o, c, lo, hi, placed):
                    continue
                best = None
                for d in (SEP, -SEP, 2 * SEP, -2 * SEP, 3 * SEP, -3 * SEP):
                    if _conflict(o, c + d, lo, hi, placed):
                        continue
                    new = _shift(pts, k, d, o, P['t0'], P['t1'], P.get('al0', 0), P.get('al1', 0))
                    if not new:
                        continue
                    new = cad.clean_pts(new)
                    sc = _count_x(new, ref) * 10 + abs(d) / SEP
                    if best is None or sc < best[0]:
                        best = (sc, new)
                if best:
                    pts = best[1]
                    changed = True
                    break
            if not changed:
                break
        P['pts'] = pts
        for o, c, lo, hi, k in _segs(pts):
            if o:
                placed.append((o, c, lo, hi))
        placed_lines += [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    return polys


def _xing(p, q, r, s):
    """直線分 pq と rs の交点 (端部除く)"""
    d1 = (q[0] - p[0], q[1] - p[1])
    d2 = (s[0] - r[0], s[1] - r[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((r[0] - p[0]) * d2[1] - (r[1] - p[1]) * d2[0]) / den
    v = ((r[0] - p[0]) * d1[1] - (r[1] - p[1]) * d1[0]) / den
    L1, L2 = math.hypot(*d1), math.hypot(*d2)
    if L1 < 1 or L2 < 1:
        return None
    if 2 / L1 < t < 1 - 2 / L1 and 2 / L2 < v < 1 - 2 / L2:
        return t, v
    return None


def _cut_ok(seg, t):
    L = math.dist(seg[1], seg[2])
    return t * L > GAP + 15 and (1 - t) * L > GAP + 15


def render(sh, items, fixed=(), layer_fn=None, floor=1):
    """items: list of (cir, T). 平行離隔→交差切り欠き→描画"""
    polys = layout(items, fixed, floor)
    for P in polys:
        P['tp'] = cad.trim_pts(P['pts'], P['t0'], P['t1'])
        P['segs'] = cad.fillet(P['tp'], W.R_BEND)
        P['cuts'] = defaultdict(list)
    # 交差: 優先度の低い側(スイッチ線・縦線)を切る。円弧との交差は直線側を切る
    fixed_segs = []
    for fp in fixed:
        fixed_segs += cad.fillet(cad.clean_pts(fp), W.R_BEND)
    for a in range(len(polys)):
        A = polys[a]
        for ia, sa in enumerate(A['segs']):
            if sa[0] != 'L':
                continue
            for t in _cuts_for(sa, fixed_segs):
                A['cuts'][ia].append(t)
            for b in range(len(polys)):
                if b == a:
                    continue
                B = polys[b]
                for ib, sb in enumerate(B['segs']):
                    if sb[0] == 'A':
                        for t in _line_arc_t(sa[1], sa[2], sb) if sb[2] > 1 else []:
                            A['cuts'][ia].append(t)
                        continue
                    if b < a:
                        continue
                    x = _xing(sa[1], sa[2], sb[1], sb[2])
                    if not x:
                        continue
                    va = abs(sa[1][0] - sa[2][0]) < 1
                    if A['pw'] != B['pw']:
                        cut_a = not A['pw']
                    else:
                        cut_a = va
                    if cut_a and not _cut_ok(sa, x[0]) and _cut_ok(sb, x[1]):
                        cut_a = False
                    elif not cut_a and not _cut_ok(sb, x[1]) and _cut_ok(sa, x[0]):
                        cut_a = True
                    if cut_a:
                        A['cuts'][ia].append(x[0])
                    else:
                        B['cuts'][ib].append(x[1])
    # 描画
    cut_pts = []
    all_lines = []
    for P in polys:
        for k, s_ in enumerate(P['segs']):
            if s_[0] == 'L':
                all_lines.append((s_[1], s_[2], P))
                for t in P['cuts'].get(k, []):
                    cut_pts.append(_lerp(s_[1], s_[2], t))
    for fs in fixed_segs:
        if fs[0] == 'L':
            all_lines.append((fs[1], fs[2], None))
    obs = W.obstacles(floor)
    placed_ticks = []
    for P in polys:
        layer_fn(P['cir'])
        for k, s_ in enumerate(P['segs']):
            if s_[0] != 'L':
                if s_[2] > 1:
                    sh.arc(s_[1], s_[2], s_[3], s_[4])
                continue
            _draw_line_gaps(sh, s_[1], s_[2], P['cuts'].get(k, []))
        if P['n'] > 0:
            spot = _tick_spot(P, all_lines, cut_pts, placed_ticks, obs)
            if spot:
                _, p, q, m = spot
                ticks_at(sh, p, q, m, P['n'], P['pw'])
                placed_ticks.append(m)
            else:
                ticks(sh, P['tp'], P['n'], P['pw'])
    for cir, T in items:
        layer_fn(cir)
        for n in T['nodes']:
            if n.kind == 'JB':
                sym_jb(sh, n.x, n.y)
            elif n.kind == 'LD':     # ライティングダクト給電点(フィードイン)
                sh.text((n.x - 90, n.y - 90), 'F', 90, 0, 'R')


def _lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)



# ------------------------------------------------------------------------------ 交差を避けるルート選定
def _cands(a, b):
    ax, ay = a.p
    bx, by = b.p
    if abs(ax - bx) < 30 and abs(ay - by) >= 30:      # ほぼ縦一直線 → 直交に
        c = [[a.p, (ax, by)]]
    elif abs(ay - by) < 30 and abs(ax - bx) >= 30:
        c = [[a.p, (bx, ay)]]
    else:
        c = [cad.lroute(a.p, b.p, 'h'), cad.lroute(a.p, b.p, 'v')]
    offs = (0, 100, -100, 200, -200, 300, -300, 450, -450, 600, -600, 1000, -1000, 1500, -1500, 2200, -2200)
    if abs(ax - bx) > 30 and abs(ay - by) > 30:
        for base in ((ay + by) / 2, ay, by):
            for o in offs:
                ym = base + o
                c.append([a.p, (ax, ym), (bx, ym), b.p])
        for base in ((ax + bx) / 2, ax, bx):
            for o in offs:
                xm = base + o
                c.append([a.p, (xm, ay), (xm, by), b.p])
    elif abs(ay - by) <= 30:
        for o in offs[1:]:
            c.append([a.p, (ax, ay + o), (bx, ay + o), b.p])
    else:
        for o in offs[1:]:
            c.append([a.p, (ax + o, ay), (ax + o, by), b.p])
    return c


def _count_x(pts, placed_lines):
    n = 0
    for i in range(len(pts) - 1):
        for (p, q) in placed_lines:
            if _xing(pts[i], pts[i + 1], p, q):
                n += 1
    return n


def _par(pts, placed_lines):
    n = 0
    for o, c, lo, hi, k in _segs(pts):
        if not o:
            continue
        for p, q in placed_lines:
            if o == 'H' and abs(p[1] - q[1]) < 1 and abs(p[1] - c) < SEP - 1:
                if min(hi, max(p[0], q[0])) - max(lo, min(p[0], q[0])) > 120:
                    n += 1
            if o == 'V' and abs(p[0] - q[0]) < 1 and abs(p[0] - c) < SEP - 1:
                if min(hi, max(p[1], q[1])) - max(lo, min(p[1], q[1])) > 120:
                    n += 1
    return n


USED = defaultdict(set)    # (x,y) -> 使用済みの出口方向


def _dir(p, q):
    if abs(p[0] - q[0]) >= abs(p[1] - q[1]):
        return 'E' if q[0] > p[0] else 'W'
    return 'N' if q[1] > p[1] else 'S'


def _exit_pen(a, b, pts):
    ka, kb = (round(pts[0][0]), round(pts[0][1])), (round(pts[-1][0]), round(pts[-1][1]))
    pen = 0
    if _dir(pts[0], pts[1]) in USED[ka]:
        pen += 1
    if _dir(pts[-1], pts[-2]) in USED[kb]:
        pen += 1
    return pen


def _mark_exit(a, b, pts):
    USED[(round(pts[0][0]), round(pts[0][1]))].add(_dir(pts[0], pts[1]))
    USED[(round(pts[-1][0]), round(pts[-1][1]))].add(_dir(pts[-1], pts[-2]))


def _score_route(a, b, pts, placed, obs, man, k):
    ob = 0
    for o in obs:
        if math.dist(o, a.p) < 40 or math.dist(o, b.p) < 40:
            continue
        dmin = min(W.seg_dist(o, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        if dmin < 150:
            ob += 8          # 記号を貫通
        elif dmin < 230:
            ob += 0.5
    L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    return 6.0 * _count_x(pts, placed) + 2.0 * ob + 3.0 * _par(pts, placed) + (L - man) / 1200.0 \
        + 0.15 * (len(pts) - 2) + 2.0 * _exit_pen(a, b, pts) + k * 1e-4


PORT_R = {'JB': 100, 'C': 150, 'E': 150, 'EM': 150, 'F': 150, 'G': 150, 'H': 150, 'I': 150, 'RISER': 100}


def _ports(n):
    """円形記号の1/8点 (45°方向) : [(点, 外向き法線)]"""
    r = PORT_R.get(n.kind)
    if not r:
        return []
    k = 0.7071
    return [((n.x + sx * r * k, n.y + sy * r * k), (sx * k, sy * k)) for sx in (1, -1) for sy in (1, -1)]


def _outward(p0, p1, nrm):
    d = (p1[0] - p0[0], p1[1] - p0[1])
    return d[0] * nrm[0] + d[1] * nrm[1] > 1e-6


def _port_routes(a, b):
    """1/8点から出入りする直交ルート候補"""
    out = []
    pa = [(None, None)] + _ports(a)
    pb = [(None, None)] + _ports(b)
    for (sa, na) in pa:
        for (eb, nb) in pb:
            if sa is None and eb is None:
                continue
            p0 = sa or a.p
            p1 = eb or b.p
            for first in ('h', 'v'):
                pts = cad.lroute(p0, p1, first)
                if abs(p0[0] - p1[0]) < 30 or abs(p0[1] - p1[1]) < 30:
                    if not (abs(p0[0] - p1[0]) < 1 or abs(p0[1] - p1[1]) < 1):
                        continue           # 斜めは不可
                pts = cad.clean_pts(pts)
                if len(pts) < 2:
                    continue
                if sa is not None and not _outward(pts[0], pts[1], na):
                    continue
                if eb is not None and not _outward(pts[-1], pts[-2], nb):
                    continue
                out.append((pts, 0 if sa is not None else a.trim, 0 if eb is not None else b.trim))
    return out


def _best(a, b, placed, obs, bnd):
    x0, y0, x1, y1 = bnd
    man = abs(a.x - b.x) + abs(a.y - b.y)
    best = None
    for k, (pts, ta, tb) in enumerate(_port_routes(a, b)):
        if len(pts) > 2 and not W._legs_ok(pts, ta, tb):
            continue
        if any(not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1) for p in pts):
            continue
        sc = _score_route(a, b, pts, placed, obs, man, 0) + 0.05
        if best is None or sc < best[0]:
            best = (sc, pts)
    for k, pts in enumerate(_cands(a, b)):
        pts = cad.clean_pts(pts)
        if len(pts) > 2 and not W._legs_ok(pts, a.trim, b.trim):
            continue
        if any(not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1) for p in pts):
            continue
        sc = _score_route(a, b, pts, placed, obs, man, k)
        if best is None or sc < best[0]:
            best = (sc, pts)
    if best is None:
        for k, pts in enumerate(_cands(a, b)):
            pts = cad.clean_pts(pts)
            sc = _score_route(a, b, pts, placed, obs, man, k)
            if best is None or sc < best[0]:
                best = (sc, pts)
    return best[1] if best else [a.p, b.p]


def route_all(items, fixed, floor, passes=6):
    """全回路の区間を順に、交差・重なり・器具干渉・長さ最小となるルートで配置し、
    交差の残る区間は引き剥がして再配線 (rip-up & reroute)"""
    obs = W.obstacles(floor)
    bnd = W.BOUNDS[floor]
    fixed_lines = []
    for fp in fixed:
        fp = cad.clean_pts(fp)
        fixed_lines += [(fp[i], fp[i + 1]) for i in range(len(fp) - 1)]
    jobs = []
    for cir, T in items:
        ns = T['nodes']
        for e in T['edges']:
            a, b = ns[e['i']], ns[e['j']]
            pw = bool(e['power'] and e.get('npow', 0) > 0)
            jobs.append((0 if pw else 1, -(abs(a.x - b.x) + abs(a.y - b.y)), a, b, e))
    jobs.sort(key=lambda j: (j[0], j[1]))

    def lines_of(e):
        p = e['pts']
        return [(p[i], p[i + 1]) for i in range(len(p) - 1)]

    placed = list(fixed_lines)
    USED.clear()
    for _, _, a, b, e in jobs:
        e['pts'] = _best(a, b, placed, obs, bnd)
        placed += lines_of(e)
        _mark_exit(a, b, e['pts'])
    for _ in range(passes):
        improved = False
        for idx, (_, _, a, b, e) in enumerate(jobs):
            others = list(fixed_lines)
            for jdx, j in enumerate(jobs):
                if jdx != idx:
                    others += lines_of(j[4])
            if _count_x(e['pts'], others) == 0 and _par(e['pts'], others) == 0:
                continue
            USED.clear()
            for jdx, j in enumerate(jobs):
                if jdx != idx:
                    _mark_exit(j[2], j[3], j[4]['pts'])
            man = abs(a.x - b.x) + abs(a.y - b.y)
            cur = _score_route(a, b, e['pts'], others, obs, man, 0)
            new = _best(a, b, others, obs, bnd)
            if _score_route(a, b, new, others, obs, man, 0) < cur - 1e-6:
                e['pts'] = new
                improved = True
        if not improved:
            break
    _swap_topology(items, fixed_lines, obs, bnd)


def _swap_topology(items, fixed_lines, obs, bnd, passes=4):
    """交差する送り区間を、同じ系統内の別の2点で繋ぎ替える (木構造は維持)"""
    allE = [(T, e) for c, T in items for e in T['edges']]

    def lines(e):
        p = e['pts']
        return [(p[i], p[i + 1]) for i in range(len(p) - 1)]

    for _ in range(passes):
        improved = False
        for T, e in allE:
            if not e.get('pool'):
                continue
            others = list(fixed_lines)
            for T2, e2 in allE:
                if e2 is not e:
                    others += lines(e2)
            if _count_x(e['pts'], others) == 0:
                continue
            ns = T['nodes']
            a, b = ns[e['i']], ns[e['j']]
            man0 = abs(a.x - b.x) + abs(a.y - b.y)
            cur = _score_route(a, b, e['pts'], others, obs, man0, 0)
            # 区間を外したときの成分
            adj = defaultdict(list)
            for e2 in T['edges']:
                if e2 is not e:
                    adj[e2['i']].append(e2['j'])
                    adj[e2['j']].append(e2['i'])
            comp = {e['i']}
            st = [e['i']]
            while st:
                x = st.pop()
                for y in adj[x]:
                    if y not in comp:
                        comp.add(y)
                        st.append(y)
            pool = set(e['pool'])
            A = [x for x in pool if x in comp]
            B = [x for x in pool if x not in comp]
            best = None
            for x in A:
                for y in B:
                    if {x, y} == {e['i'], e['j']}:
                        continue
                    na, nb = ns[x], ns[y]
                    man = abs(na.x - nb.x) + abs(na.y - nb.y)
                    if man > 2 * man0 + 3000:
                        continue
                    pts = _best(na, nb, others, obs, bnd)
                    sc = _score_route(na, nb, pts, others, obs, man, 0) + (man - man0) / 1500.0
                    if best is None or sc < best[0]:
                        best = (sc, x, y, pts)
            if best and best[0] < cur - 0.5:
                e['i'], e['j'], e['pts'] = best[1], best[2], best[3]
                improved = True
        if not improved:
            break
    for c, T in items:
        if 'nets' in T:
            count_conductors(T)


def layout(items, fixed, floor):
    route_all(items, fixed, floor)
    polys = []
    for cir, T in items:
        ns = T['nodes']
        for e in T['edges']:
            a, b = ns[e['i']], ns[e['j']]
            port0 = math.dist(e['pts'][0], a.p) > 1
            port1 = math.dist(e['pts'][-1], b.p) > 1
            base = dict(t0=0 if port0 else a.trim, t1=0 if port1 else b.trim, e=e, T=T, cir=cir,
                        al0=0 if port0 else _allow(a), al1=0 if port1 else _allow(b))
            pw2 = bool(e['power'] and e.get('npow', 0) == 2)     # 電源 L・N の2本
            nsw = e['n'] - (2 if pw2 else 0)                    # スイッチ線(1.6)
            if pw2:
                polys.append(dict(base, pts=list(e['pts']), pw=True, n=2, main=True))
            if nsw > 0:
                polys.append(dict(base, pts=list(e['pts']), pw=False, n=nsw, main=not pw2))
    polys.sort(key=lambda P: (0 if P['pw'] else 1))
    separate(polys, fixed)
    for P in polys:
        if P['main']:
            P['e']['pts'] = P['pts']
    return polys


def homerun_seg(T):
    """ホームラン矢印の線分 (重なり・交差判定用)"""
    r = T['nodes'][T['root']]
    d = cad._norm((PANEL_L_TOP[0] - r.x, PANEL_L_TOP[1] - r.y))
    d = (1 if d[0] > 0 else -1, 0) if abs(d[0]) > abs(d[1]) else (0, 1 if d[1] > 0 else -1)
    d = W.HR_DIR.get(T['cir'], d)
    p = (r.x + d[0] * r.trim, r.y + d[1] * r.trim)
    q = (p[0] + d[0] * 900, p[1] + d[1] * 900)
    return [p, q]



# ------------------------------------------------------------------------------ 円弧との交差・切り欠き描画・斜線配置
def _line_arc_t(p, q, arc):
    """直線分pqと円弧の交点のパラメータt (0..1) のリスト"""
    _, C, r, a0, a1 = arc
    dx, dy = q[0] - p[0], q[1] - p[1]
    fx, fy = p[0] - C[0], p[1] - C[1]
    A = dx * dx + dy * dy
    B = 2 * (fx * dx + fy * dy)
    Cc = fx * fx + fy * fy - r * r
    disc = B * B - 4 * A * Cc
    if A < 1e-9 or disc < 0:
        return []
    out = []
    for sgn in (-1, 1):
        t = (-B + sgn * math.sqrt(disc)) / (2 * A)
        if 0 < t < 1:
            x, y = p[0] + dx * t, p[1] + dy * t
            ang = math.degrees(math.atan2(y - C[1], x - C[0])) % 360
            span = (a1 - a0) % 360
            if (ang - a0) % 360 <= span:
                out.append(t)
    return out


def _cuts_for(seg, others):
    """seg(L) が others(L/A) と交わる位置 t"""
    ts = []
    for o in others:
        if o[0] == 'L':
            x = _xing(seg[1], seg[2], o[1], o[2])
            if x:
                ts.append(x[0])
        elif o[2] > 1:
            ts += _line_arc_t(seg[1], seg[2], o)
    return ts


def draw_cut(sh, segs, cutters, ltype=None):
    """segs を描画し、cutters と交わる位置を切り欠く"""
    for s_ in segs:
        if s_[0] != 'L':
            if s_[2] > 1:
                sh.arc(s_[1], s_[2], s_[3], s_[4], 256, ltype)
            continue
        _draw_line_gaps(sh, s_[1], s_[2], _cuts_for(s_, cutters), ltype)


def _draw_line_gaps(sh, p, q, ts, ltype=None):
    L = math.dist(p, q)
    if L < 1:
        return
    cur = 0.0
    for t in sorted(ts):
        g = min(GAP, max(t * L - 10, 25), max((1 - t) * L - 10, 25))
        t0, t1 = max(t - g / L, 0), min(t + g / L, 1)
        if t0 > cur:
            sh.line(_lerp(p, q, cur), _lerp(p, q, t0), 256, ltype)
        cur = max(cur, t1)
    if cur < 1:
        sh.line(_lerp(p, q, cur), q, 256, ltype)


def _tick_spot(P, all_lines, all_cuts_pts, placed_ticks, obs):
    """斜線(条数)を置く位置: 切り欠き・他の線・他の斜線・器具から離れた直線部"""
    best = None
    for k, s_ in enumerate(P['segs']):
        if s_[0] != 'L':
            continue
        p, q = s_[1], s_[2]
        L = math.dist(p, q)
        if L < 260:
            continue
        for f in (0.5, 0.35, 0.65, 0.25, 0.75, 0.15, 0.85):
            m = _lerp(p, q, f)
            if min(f * L, (1 - f) * L) < 130:
                continue
            dl = min([W.seg_dist(m, a, b) for (a, b, own) in all_lines if own is not P] or [9999])
            dc = min([math.dist(m, c) for c in all_cuts_pts] or [9999])
            dt = min([math.dist(m, t) for t in placed_ticks] or [9999])
            do = min([math.dist(m, o) for o in obs] or [9999])
            sc = min(dl, 300) + min(dc, 400) * 1.2 + min(dt, 500) + min(do, 300) * 0.8 + L * 0.02
            if dc < 260:
                sc -= 1000       # 切り欠きの近く
            if do < 180:
                sc -= 600        # 器具記号の上
            if best is None or sc > best[0]:
                best = (sc, p, q, m)
    return best


ROUND_SYM = ('C', 'E', 'F', 'G', 'H', 'I', 'EM', 'OUT', 'FAN')


def _allow(n):
    """器具記号内で接続点をずらせる量"""
    return n.trim * 0.8 if n.kind in ROUND_SYM else 0
