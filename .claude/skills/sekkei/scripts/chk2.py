import os
"""配線(W-画層)の 切り欠きなし交差(直線・円弧) と 100未満平行 を検査"""
import ezdxf, glob, math, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wire2
def ents(f):
    d = ezdxf.readfile(f)
    L, A = [], []
    for e in d.modelspace():
        ly = e.dxf.layer
        if not ly.startswith('W-'):
            continue
        if e.dxftype() == 'LINE':
            p, q = (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)
            if math.dist(p, q) > 200:
                L.append((ly, p, q))
        elif e.dxftype() == 'ARC' and e.dxf.radius > 20:
            A.append((ly, ('A', (e.dxf.center.x, e.dxf.center.y), e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle)))
    return L, A
import r12
NODES = []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D
for L in (D.L1F, D.L2F):
    NODES += [(d['x'], d['y']) for d in L]
def at_node(pt):   # 器具・JBでの合流点は交差とみなさない
    return any(math.dist(pt, n) < 200 for n in NODES)
tot = 0
for f in sorted(glob.glob(os.environ.get('SEKKEI_OUT', os.getcwd() + '/out').rstrip('/') + '/E-0[3-6]*.dxf')):
    L, A = ents(f)
    xs, par, ex = 0, 0, []
    for i in range(len(L)):
        la, p, q = L[i]
        for j in range(i + 1, len(L)):
            lb, r, s = L[j]
            x = wire2._xing(p, q, r, s)
            if x:
                Lp, Lr = math.dist(p, q), math.dist(r, s)
                if 5 / Lp < x[0] < 1 - 5 / Lp and 5 / Lr < x[1] < 1 - 5 / Lr:
                    xs += 1; ex.append(('交差', la[:10], lb[:10], tuple(round(v) for v in (p[0] + (q[0]-p[0])*x[0], p[1] + (q[1]-p[1])*x[0]))))
            ha, hb = abs(p[1]-q[1]) < 1, abs(r[1]-s[1]) < 1
            va, vb = abs(p[0]-q[0]) < 1, abs(r[0]-s[0]) < 1
            if (ha and hb and abs(p[1]-r[1]) < 99) or (va and vb and abs(p[0]-r[0]) < 99):
                k = 0 if ha else 1
                lo = max(min(p[k], q[k]), min(r[k], s[k])); hi = min(max(p[k], q[k]), max(r[k], s[k]))
                if hi - lo > 120:
                    par += 1; ex.append(('平行', la[:10], lb[:10], (round(p[0]), round(p[1]))))
        for lb, arc in A:
            for t in wire2._line_arc_t(p, q, arc):
                Lp = math.dist(p, q)
                if 5 / Lp < t < 1 - 5 / Lp and not at_node((p[0] + (q[0]-p[0])*t, p[1] + (q[1]-p[1])*t)):
                    xs += 1; ex.append(('円弧交差', la[:10], lb[:10], tuple(round(v) for v in (p[0] + (q[0]-p[0])*t, p[1] + (q[1]-p[1])*t))))
    print(f.split('/')[-1][:18], '切欠なし交差', xs, '平行<100', par)
    for e in ex[:12]:
        print('   ', e)
    tot += xs + par
print('TOTAL', tot)
