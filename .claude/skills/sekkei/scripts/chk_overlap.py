import os
import ezdxf, glob, math, sys
def lines(f):
    d = ezdxf.readfile(f)
    out = []
    for e in d.modelspace().query('LINE'):
        ly = e.dxf.layer
        if not (ly.startswith('W-L') or ly.startswith('W-P')):
            continue
        p, q = (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)
        if math.dist(p, q) < 220:
            continue
        out.append((ly, p, q))
    return out
for f in sorted(glob.glob(os.environ.get('SEKKEI_OUT', os.getcwd() + '/out').rstrip('/') + '/E-0[3-6]*.dxf')):
    L = lines(f)
    par = 0; xs = 0; ex = []
    for i in range(len(L)):
        for j in range(i + 1, len(L)):
            (la, p, q), (lb, r, s) = L[i], L[j]
            ha, hb = abs(p[1]-q[1]) < 1, abs(r[1]-s[1]) < 1
            va, vb = abs(p[0]-q[0]) < 1, abs(r[0]-s[0]) < 1
            if (ha and hb and abs(p[1]-r[1]) < 95) or (va and vb and abs(p[0]-r[0]) < 95):
                k = 0 if ha else 1
                lo = max(min(p[k], q[k]), min(r[k], s[k])); hi = min(max(p[k], q[k]), max(r[k], s[k]))
                if hi - lo > 120:
                    par += 1; ex.append(('平行', la[:12], lb[:12], round(p[0]), round(p[1])))
            if (ha and vb) or (va and hb):
                H, V = ((p, q), (r, s)) if ha else ((r, s), (p, q))
                x, y = V[0][0], H[0][1]
                if min(H[0][0], H[1][0]) + 5 < x < max(H[0][0], H[1][0]) - 5 and min(V[0][1], V[1][1]) + 5 < y < max(V[0][1], V[1][1]) - 5:
                    xs += 1; ex.append(('交差', la[:12], lb[:12], round(x), round(y)))
    print(f.split('/')[-1][:20], '平行重なり', par, '交差(切欠なし)', xs)
    for e in ex[:8]:
        print('   ', e)
