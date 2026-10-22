"""配線レイアウトの交差数を数える (切り欠き前の幾何)"""
import sys, math
sys.path.insert(0, '.')
import wire2, gen_wire as W, cad

def xings(polys):
    segs = []
    for k, P in enumerate(polys):
        p = P['pts']
        for i in range(len(p) - 1):
            segs.append((k, p[i], p[i + 1]))
    n = 0
    for a in range(len(segs)):
        for b in range(a + 1, len(segs)):
            if segs[a][0] == segs[b][0]:
                continue
            if wire2._xing(segs[a][1], segs[a][2], segs[b][1], segs[b][2]):
                n += 1
    return n

def sheet(floor, kind):
    if kind == 'L':
        cirs = ['L-1-1', 'L-1-2', 'L-1-3', 'L-1-24'] if floor == 1 else ['L-1-3', 'L-1-24']
        items = [(c, wire2.build_light(floor, c)) for c in cirs if wire2.loads(floor, c)]
        fixed = []
    else:
        import data as D
        OUT = D.OUT1F if floor == 1 else D.OUT2F
        cirs = list(dict.fromkeys(o['cir'] for o in OUT))
        items = [(c, wire2.build_outlet(floor, c)) for c in cirs]
        fixed = list(W.P_ROUTES.values()) if floor == 1 else []
    W.obstacles(floor)
    polys = wire2.layout(items, fixed, floor) if hasattr(wire2, 'layout') else None
    if polys is None:
        polys = []
        for c, T in items:
            for e in T['edges']:
                polys.append(dict(pts=e['pts']))
    return xings(polys), sum(len(T['edges']) for c, T in items)

for fl, k, nm in ((1, 'L', 'E-03'), (1, 'O', 'E-04'), (2, 'L', 'E-05'), (2, 'O', 'E-06')):
    x, n = sheet(fl, k)
    print(nm, '区間', n, '交差', x)
