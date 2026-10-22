"""図面作図データ(配線・ダクト・配管ルート)からの数量拾い出し."""
import math
from collections import defaultdict
import cad
import data as D
import gen_wire as W
import gen_mech as M

CEIL = 2400       # 天井高
FH = {1: 3000, 2: 3000}   # 階高
PANEL_TOP = 1900  # 盤上端
H = {'SW': 1300, 'SW_K': 1500, 'OUT': 300, 'OUT_K': 1500, 'OUT_AC': 2000, 'BR': 2000, 'EX': 2100}


def in_kitchen(x, y):
    return 4935 <= x <= 8775 and 1465 <= y <= 8835


def plen(pts):
    return cad.path_len(cad.fillet(pts, W.R_BEND)) if len(pts) > 1 else 0.0


def manh(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def out_info(floor, x, y):
    lst = D.OUT1F if floor == 1 else D.OUT2F
    for o in lst:
        if abs(o['x'] - x) < 1 and abs(o['y'] - y) < 1:
            return o
    return None


def drop(node, floor):
    """天井内から器具までの立下り長 [mm]"""
    k = node.kind
    if k == 'SW':
        return CEIL - (H['SW_K'] if in_kitchen(node.x, node.y) and floor == 1 else H['SW'])
    if k == 'OUT':
        o = out_info(floor, node.x, node.y)
        if o and (o.get('ac') or 'AC' in o['t']):
            return CEIL - H['OUT_AC']
        if floor == 1 and in_kitchen(node.x, node.y):
            return CEIL - H['OUT_K']
        return CEIL - H['OUT']
    if k in ('F', 'G', 'H', 'I'):
        return CEIL - H['BR']
    if k == 'EX':
        return max(CEIL - H['EX'], 0)
    return 0


PANEL_L_TOP = ((D.PANEL_L[0] + D.PANEL_L[2]) / 2, D.PANEL_L[1])
PANEL_P_TOP = ((D.PANEL_P[0] + D.PANEL_P[2]) / 2, D.PANEL_P[1])


def split_cables(k, size):
    """k本 → VVF 3C/2C の組合せ"""
    if k <= 0:
        return []
    if k <= 3:
        return ['VVF%s-%dC' % (size, max(k, 2))]
    out = []
    while k > 0:
        if k in (4,):
            out += ['VVF%s-2C' % size] * 2
            k = 0
        elif k >= 3:
            out.append('VVF%s-3C' % size)
            k -= 3
        else:
            out.append('VVF%s-2C' % size)
            k = 0
    return out


def node_drop(n, floor):
    kind = 'SW' if n.kind == 'BOX' else n.kind
    return drop(W.Node(n.x, n.y, 0, None, kind), floor) if kind in ('SW', 'F', 'G', 'H', 'I', 'EX') else 0


JOINTS = defaultdict(int)     # (floor, 'JB'|'器具') -> 個数
CONNECT = defaultdict(int)    # floor -> 差込コネクタ数


def run():
    """returns list of cable rows: dict(cir, floor, cable, plan, vert, note)"""
    import wire2
    rows = []
    deg = defaultdict(int)
    JOINTS.clear()
    CONNECT.clear()

    def add(cir, floor, cable, plan, vert, note):
        rows.append(dict(cir=cir, floor=floor, cable=cable, plan=plan / 1000, vert=vert / 1000, note=note))

    riser_nets = {}
    # ---------------- 電灯 (照明・換気・非常)
    for floor in (1, 2):
        cirs = ['L-1-1', 'L-1-2', 'L-1-3', 'L-1-24'] if floor == 1 else ['L-1-3', 'L-1-24']
        items = [(c, wire2.build_light(floor, c)) for c in cirs if wire2.loads(floor, c)]
        wire2.layout(items, [wire2.homerun_seg(T) for c, T in items if T['homerun']] + W.RISER_FIXED.get(floor, []), floor)   # 図面と同じルート・木構造
        for cir, T in items:
            ns = T['nodes']
            touch = defaultdict(set)
            for e in T['edges']:
                a, b = ns[e['i']], ns[e['j']]
                L = plen(e['pts'])
                v = node_drop(a, floor) + node_drop(b, floor)
                pw = e['power'] and e['npow'] == 2
                k16 = e['n'] - (2 if pw else 0)
                cabs = (['VVF2.0-2C'] if pw else []) + split_cables(k16, '1.6')
                for c in cabs:
                    add(cir, floor, c, L, v, '%s→%s (%d本)' % (a.label or a.kind, b.label or b.kind, e['n']))
                for x in (e['i'], e['j']):
                    touch[x] |= e['nets']
            for i, n in enumerate(ns):
                if n.kind == 'JB':
                    JOINTS[(floor, 'JB')] += 1
                    CONNECT[floor] += len(touch[i])
                elif n.kind not in ('BOX', 'RISER') and len([e for e in T['edges'] if i in (e['i'], e['j'])]) >= 2:
                    JOINTS[(floor, '器具')] += 1
                    CONNECT[floor] += len(touch[i])
                if n.kind == 'RISER':
                    riser_nets[(cir, floor)] = touch[i]
            if T['homerun']:
                r = ns[T['root']]
                add(cir, 1, 'VVF2.0-2C', manh(r.p, PANEL_L_TOP), CEIL - PANEL_TOP, '盤への配線(ホームラン)')
    # 2F分 電灯 立上り
    for cir in ('L-1-3', 'L-1-24'):
        add(cir, 1, 'VVF2.0-2C', manh(D.RISER1F, PANEL_L_TOP), CEIL - PANEL_TOP, '盤→立上り(1F天井内)')
        nets = riser_nets.get((cir, 2), {'L', 'N'})
        k16 = len([x for x in nets if x not in ('L', 'N')])
        for c in ['VVF2.0-2C'] + split_cables(k16, '1.6'):
            add(cir, 2, c, 0, FH[1], '立上り 1F天井内→2F天井内 (=階高) %d本' % len(nets))

    # ---------------- コンセント
    for floor in (1, 2):
        OUT = D.OUT1F if floor == 1 else D.OUT2F
        cirs = []
        for o in OUT:
            if o['cir'] not in cirs:
                cirs.append(o['cir'])
        items = [(c, wire2.build_outlet(floor, c)) for c in cirs]
        fixed = list(W.P_ROUTES.values()) if floor == 1 else []
        routes = W.REF_ROUTES_1F if floor == 1 else W.REF_ROUTES_2F
        fixed += [cad.offset_poly(cad.clean_pts(p), -220) for p in routes.values()]
        fixed += [wire2.homerun_seg(T) for c, T in items if T['homerun']] + W.RISER_FIXED.get(floor, [])
        wire2.layout(items, fixed, floor)
        for cir, T in items:
            cab = W.CIR_CABLE[cir].replace(' ', '')
            ns = T['nodes']
            for e in T['edges']:
                a, b = ns[e['i']], ns[e['j']]
                aa = W.Node(a.x, a.y, 0, None, 'OUT' if a.kind == 'OUT' else a.kind)
                bb = W.Node(b.x, b.y, 0, None, 'OUT' if b.kind == 'OUT' else b.kind)
                add(cir, floor, cab, plen(e['pts']), drop(aa, floor) + drop(bb, floor), 'コンセント送り')
            if floor == 1:
                add(cir, 1, cab, manh(ns[T['root']].p, PANEL_L_TOP), CEIL - PANEL_TOP, '盤への配線(ホームラン)')
            else:
                add(cir, 1, cab, manh(D.RISER1F, PANEL_L_TOP), CEIL - PANEL_TOP, '盤→立上り(1F天井内)')
                add(cir, 2, cab, 0, FH[1], '立上り 1F天井内→2F天井内 (=階高)')

    # ---------------- 動力 (P-1)
    prow = []
    for cir, pts in W.P_ROUTES.items():
        L = plen(pts) + math.dist(*W.P_TAIL[cir])
        if cir == 'P-1-1':
            v = (CEIL - PANEL_TOP) + (CEIL - 300) + 1000  # 盤 + いけす電源(FL+300想定) + 手元開閉器 余長
            note = '盤→いけす電源(手元開閉器経由)'
        else:
            v = (CEIL - PANEL_TOP) + 300 + CEIL - 600 + 1000  # 盤 + 外壁貫通 + 外壁下り(室外機端子台FL+600) + 手元開閉器
            note = '盤→外壁貫通→室外機(手元開閉器経由)'
        cab = W.CIR_CABLE[cir].split(' + ')[0].replace(' ', '')
        prow.append(dict(cir=cir, floor=1, cable=cab, plan=L / 1000, vert=v / 1000, note=note))
        prow.append(dict(cir=cir, floor=1, cable='IV2.0', plan=L / 1000, vert=v / 1000, note='接地線(同ルート)'))
    return rows, prow, deg


def link_and_pipes():
    """空調 内外連絡線・冷媒・ドレン"""
    out = []
    for floor, routes in ((1, W.REF_ROUTES_1F), (2, W.REF_ROUTES_2F)):
        for k, pts in routes.items():
            liq, gas, dr, pkg, mx = M.PIPE[k]
            L = cad.path_len(cad.fillet(cad.clean_pts(pts), M.R_PIPE)) / 1000
            corners = len(cad.clean_pts(pts)) - 2
            rise = M.RISE[k]
            if k in M.DRAIN_DIRECT:
                dr_len = math.dist(*M.DRAIN_DIRECT[k]) / 1000 + 1.0
            elif pkg:
                dr_len = L + 1.5
            else:
                dr_len = L + 1.0
            out.append(dict(ac=k, floor=floor, liq=liq, gas=gas, ref_len=L + rise, corners=corners,
                            drain=dr, drain_len=dr_len, link_len=L + rise + 1.0, pkg=pkg))
    return out


def ducts():
    res = []
    for floor, lst in ((1, M.DUCT1F), (2, M.DUCT2F)):
        for lab, pts, dia, kind, hood in lst:
            p = cad.clean_pts(pts)
            L = cad.path_len(cad.fillet(p, M.R_DUCT)) / 1000
            res.append(dict(floor=floor, label=lab, dia=dia, kind=kind, len=L + 0.3, elbows=len(p) - 2,
                            hood=hood is not None, wallpen=1))
    return res


def switch_boxes():
    """スイッチ位置のクラスタ化 (200mm以内=同一ボックス)"""
    res = []
    for floor, lst in ((1, D.SW1F), (2, D.SW2F)):
        used = [False] * len(lst)
        for i, s in enumerate(lst):
            if used[i]:
                continue
            grp = [s]
            used[i] = True
            changed = True
            while changed:
                changed = False
                for j, t in enumerate(lst):
                    if not used[j] and any(math.dist((t['x'], t['y']), (g['x'], g['y'])) <= 200 for g in grp):
                        grp.append(t)
                        used[j] = True
                        changed = True
            ne = sum(1 for g in grp if g['k'] in 'S3')
            nv = sum(1 for g in grp if g['k'] == 'V')
            res.append(dict(floor=floor, x=grp[0]['x'], y=grp[0]['y'], n=len(grp), ns=sum(1 for g in grp if g['k'] == 'S'),
                            n3=sum(1 for g in grp if g['k'] == '3'), nv=nv, kitchen=floor == 1 and in_kitchen(grp[0]['x'], grp[0]['y']),
                            new=all(g.get('new') for g in grp)))
    return res


if __name__ == '__main__':
    rows, prow, deg = run()
    agg = defaultdict(float)
    for r in rows + prow:
        agg[(r['cable'], r['floor'])] += r['plan'] + r['vert']
    for k, v in sorted(agg.items()):
        print(k, round(v, 1))
    for x in link_and_pipes():
        print(x)
    for x in ducts():
        print(x['floor'], x['label'], round(x['len'], 2), x['elbows'])
    for x in switch_boxes():
        print(x)
