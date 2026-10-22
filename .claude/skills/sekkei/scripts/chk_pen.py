import sys, math
sys.path.insert(0, '.')
import wire2, gen_wire as W, data as D, cad
def sheet(fl, kind):
    if kind == 'L':
        cirs = ['L-1-1', 'L-1-2', 'L-1-3', 'L-1-24'] if fl == 1 else ['L-1-3', 'L-1-24']
        items = [(c, wire2.build_light(fl, c)) for c in cirs if wire2.loads(fl, c)]
        fixed = [wire2.homerun_seg(T) for c, T in items if T['homerun']] + W.RISER_FIXED.get(fl, [])
    else:
        OUT = D.OUT1F if fl == 1 else D.OUT2F
        cirs = list(dict.fromkeys(o['cir'] for o in OUT))
        items = [(c, wire2.build_outlet(fl, c)) for c in cirs]
        fixed = (list(W.P_ROUTES.values()) if fl == 1 else [])
        routes = W.REF_ROUTES_1F if fl == 1 else W.REF_ROUTES_2F
        fixed += [cad.offset_poly(cad.clean_pts(p), -220) for p in routes.values()]
        fixed += [wire2.homerun_seg(T) for c, T in items if T['homerun']] + W.RISER_FIXED.get(fl, [])
    polys = wire2.layout(items, fixed, fl)
    # 記号: 器具・スイッチ・コンセント・換気扇
    syms = []
    L = D.L1F if fl == 1 else D.L2F
    syms += [(d['x'], d['y'], d['t']) for d in L if d['t'] not in 'AB']
    syms += [(s['x'], s['y'], 'SW') for s in (D.SW1F if fl == 1 else D.SW2F)]
    syms += [(o['x'], o['y'], 'OUT') for o in (D.OUT1F if fl == 1 else D.OUT2F)]
    syms += [(f['x'], f['y'], 'FAN') for f in (D.FAN1F if fl == 1 else D.FAN2F)]
    pen = []
    for P in polys:
        pts = P['pts']
        a, b = pts[0], pts[-1]
        for x, y, t in syms:
            if math.dist((x, y), a) < 200 or math.dist((x, y), b) < 200:
                continue
            r = 75 if t == 'SW' else 120
            if min(W.seg_dist((x, y), pts[i], pts[i + 1]) for i in range(len(pts) - 1)) < r:
                pen.append((P['cir'], t, x, y))
    return pen
for fl, k, nm in ((1, 'L', 'E-03'), (1, 'O', 'E-04'), (2, 'L', 'E-05'), (2, 'O', 'E-06')):
    p = sheet(fl, k)
    print(nm, '記号貫通', len(p), p[:8])
