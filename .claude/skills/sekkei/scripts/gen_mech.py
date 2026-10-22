"""換気ダクト図・空調冷媒/ドレン配管図."""
import math
import cad
import data as D
import gen_wire as W

R_DUCT = 450
ROAD_SIDE = ('S',)   # 道路面(延焼ライン)＝南面と想定 → FD付深形フード
R_PIPE = 500

DUCT1F = [
    # (label, pts, dia, kind, hood)
    ('VD-1 EA φ150', [(8237, 6686), (4985, 6686)], 150, 'EA', (4885, 6686, 'W')),
    ('VD-2 EA φ150', [(14251, 5530), (14251, 1515)], 150, 'EA', (14251, 1415, 'S')),
    ('PF-1 EA φ150', [(9268, 12209), (9268, 12785)], 150, 'EA', None),
    ('PF-2 EA φ150', [(14146, 12232), (14146, 12785)], 150, 'EA', None),
    ('EF-1 EA φ100', [(8001, 12476), (8001, 12785)], 100, 'EA', None),
    ('EF-2 EA φ100', [(15862, 12383), (15862, 12785)], 100, 'EA', None),
    ('TF-1 EA φ100', [(13060, 6859), (13060, 8000), (12400, 8000), (12400, 12785)], 100, 'EA', (12400, 12935, 'N')),
    ('TF-2 EA φ100', [(17664, 6674), (18695, 6674)], 100, 'EA', (18795, 6674, 'E')),
    ('SA φ150', [(10735, 7848), (10735, 6700), (10250, 6700), (10250, 1515)], 150, 'SA', (10250, 1415, 'S')),
    ('SA φ150', [(8387, 3033), (8387, 1515)], 150, 'SA', (8387, 1415, 'S')),
    ('SA φ150', [(9209, 5059), (9209, 1515)], 150, 'SA', (9209, 1415, 'S')),
    ('SA φ150', [(14111, 2563), (14111, 2300), (13850, 2300), (13850, 1515)], 150, 'SA', (13850, 1415, 'S')),
    ('SA φ150', [(18420, 2196), (18420, 1515)], 150, 'SA', (18420, 1415, 'S')),
]
DUCT2F = [
    ('VD-3 EA φ150', [(14241, 4379), (14241, 1500)], 150, 'EA', (14241, 1400, 'S')),
    ('SA φ150', [(12189, 1806), (12189, 1500)], 150, 'SA', (12189, 1400, 'S')),
    ('SA φ150', [(17259, 1806), (17259, 1500)], 150, 'SA', (17259, 1400, 'S')),
    ('TF-3 EA φ100', [(17496, 6924), (17700, 6924)], 100, 'EA', (17800, 6924, 'E')),
]

PIPE = {
    'AC-1': ('φ9.52', 'φ15.88', 'VP25', True, 50),
    'AC-2': ('φ6.35', 'φ12.7', 'VP25', True, 50),
    'AC-3': ('φ6.35', 'φ12.7', 'VP25', True, 50),
    'AC-4': ('φ6.35', 'φ12.7', 'VP20', False, 20),
    'AC-5': ('φ6.35', 'φ12.7', 'VP20', False, 20),
    'AC-6': ('φ6.35', 'φ12.7', 'VP20', False, 20),
    'AC-7': ('φ6.35', 'φ9.52', 'VP20', False, 15),
}
DRAIN_DIRECT = {'AC-6': ((13285, 1500), (13285, 1150))}
RISE = {'AC-1': 2.5, 'AC-2': 2.8, 'AC-3': 2.8, 'AC-4': 2.2, 'AC-5': 2.2, 'AC-6': 2.0, 'AC-7': 2.0}


def ducts(sh, floor):
    lst = DUCT1F if floor == 1 else DUCT2F
    for lab, pts, dia, kind, hood in lst:
        sh.L('M-換気-ダクト ' + ('排気EA' if kind == 'EA' else '給気SA'), 6 if kind == 'EA' else 5)
        cad.thick_path(sh, pts, R_DUCT, dia)
        # label
        best = max(range(len(pts) - 1), key=lambda i: math.dist(pts[i], pts[i + 1]))
        p, q = pts[best], pts[best + 1]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        txt = lab + ' スパイラルダクト' if dia == 150 else lab + ' 塩ビ/スパイラル'
        if abs(p[1] - q[1]) < 1:
            sh.text((mx, my + dia / 2 + 50), txt, 85, 0, 'C')
        else:
            sh.text((mx - dia / 2 - 50, my), txt, 85, 90, 'C')
        if hood:
            sh.L('M-換気-外壁フード', 6)
            cad.sym_hood(sh, hood[0], hood[1], hood[2], 100)
            hx, hy = hood[0], hood[1]
            fd = hood[2] in ROAD_SIDE
            nm = ('P-18VSD4' if dia == 150 else 'P-13VSD4') if fd else ('P-18VS4' if dia == 150 else 'P-13VS4')
            if fd:
                sh.L('M-換気-防火ダンパー(FD)', 1)
                sh.rect(hx + 130, hy + 40, hx + 400, hy + 200)
                sh.text((hx + 265, hy + 120), 'FD', 90, 0, 'MC')
                sh.L('M-換気-外壁フード', 6)
            dx = {'N': (0, 160), 'S': (0, -260 - 150 * (int(hx // 100) % 2)), 'E': (160, 0), 'W': (-160, 0)}[hood[2]]
            sh.text((hx + dx[0], hy + dx[1]), nm, 80, 0, 'R' if hood[2] == 'W' else 'C')


def piping(sh, floor):
    routes = W.REF_ROUTES_1F if floor == 1 else W.REF_ROUTES_2F
    for k, pts in routes.items():
        liq, gas, dr, pkg, mx = PIPE[k]
        pts = cad.clean_pts(pts)
        sh.L('M-空調-冷媒配管', 4)
        for off in (-35, 35):
            o = cad.offset_poly(pts, off)
            sg = cad.turn_signs(pts)
            cad.draw_segs(sh, cad.fillet(o, [R_PIPE - s * off for s in sg]))
        Lm = cad.path_len(cad.fillet(pts, R_PIPE)) / 1000.0 + RISE[k]
        sh.L('M-空調-ドレン配管', 150)
        if k in DRAIN_DIRECT:
            p0, p1 = DRAIN_DIRECT[k]
            sh.line(p0, p1, 256, 'DASHED')
            sh.text((p1[0] + 80, p1[1] - 60), 'ドレン %s 南面外壁より直接屋外排水(自然勾配)' % dr, 80)
        else:
            od = cad.offset_poly(pts, 180)
            sg = cad.turn_signs(pts)
            cad.draw_segs(sh, cad.fillet(od, [max(R_PIPE - s * 180, 50) for s in sg]), 256, 'DASHED')
        sh.L('M-空調-配管記号', 4)
        txt = '%s 冷媒 液%s/ガス%s 被覆銅管 実長約%.0fm(許容%dm以下)' % (k, liq, gas, Lm, mx)
        txt2 = 'ドレン %s 保温付 勾配1/100以上 屋外排水' % dr if k not in DRAIN_DIRECT else '冷媒管 天井内隠ぺい→北面外壁貫通→屋根上'
        best = max(range(len(pts) - 1), key=lambda i: math.dist(pts[i], pts[i + 1]))
        p, q = pts[best], pts[best + 1]
        mx_, my_ = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        if abs(p[1] - q[1]) < 1:
            sh.text((mx_, my_ + 100), txt, 80, 0, 'C')
            sh.text((mx_, my_ + 300), txt2, 80, 0, 'C')
        else:
            if math.dist(p, q) > 3000:
                sh.text((mx_ - 120, my_), txt, 80, 90, 'C')
                sh.text((mx_ + 320, my_), txt2, 80, 90, 'C')
            else:
                # short through-wall run: put note beside outdoor unit
                sh.text((q[0] + 450, q[1] - 260), k + ' 液' + liq + '/ガス' + gas + ' 壁貫通 実長約%.0fm' % Lm, 75)
                sh.text((q[0] + 450, q[1] - 400), 'ドレン ' + dr + ' 壁貫通 屋外排水', 75)


def equip_table(sh, floor, x0, y0):
    sh.L('M-機器表', 7)
    rows = []
    if floor == 12:
        y = equip_table(sh, 1, x0, y0)
        return equip_table(sh, 2, x0, y - 450)
    if floor == 1:
        rows.append(('記号', '名称', '形式', '電源', '能力/風量'))
        for a in D.AC1F:
            rows.append((a['id'], a['name'], a['model'], a['pw'] + ' ' + a['cir'], ''))
        cap = {'AC-1': '冷12.5/暖14.0kW', 'AC-2': '冷5.0/暖5.6kW', 'AC-3': '冷5.0/暖5.6kW', 'AC-4': '冷5.6/暖6.7kW',
               'AC-5': '冷5.6/暖6.7kW'}
        rows = [rows[0]] + [(r[0], r[1], r[2], r[3], cap[r[0]]) for r in rows[1:]]
        for f in D.FAN1F:
            q = {'VD': '180m3/h(24h弱)', 'PF': '153m3/h(2台)' if f['id'].startswith('PF') else '-', 'TF': '70.5m3/h'}[f['t']]
            rows.append((f['id'], f['name'], f['model'], '100V ' + f['cir'], q))
        rows.append(('SA', '自然給気グリル', 'P-18GLF6 ×5(1F)', '-', 'φ150'))
    else:
        rows.append(('記号', '名称', '形式', '電源', '能力/風量'))
        cap = {'AC-6': '冷5.6/暖6.7kW', 'AC-7': '冷3.6/暖4.2kW'}
        for a in D.AC2F:
            rows.append((a['id'], a['name'], a['model'], a['pw'] + ' ' + a['cir'], cap[a['id']]))
        for f in D.FAN2F:
            rows.append((f['id'], f['name'], f['model'], '100V ' + f['cir'], '180m3/h' if f['t'] == 'VD' else '70.5m3/h'))
        rows.append(('SA', '自然給気グリル', 'P-18GLF6 ×2(2F)', '-', 'φ150'))
    cw = [550, 1500, 2900, 1250, 1350]
    rh = 230
    W_ = sum(cw)
    sh.text((x0, y0 + 80), '■ %s 空調・換気機器表 (空調:三菱電機プラン2026.10.16 / 換気:機種選定書T263764)' % ('1F' if floor == 1 else '2F'), 110)
    y = y0
    for i, r in enumerate(rows):
        sh.line((x0, y), (x0 + W_, y))
        xx = x0
        for c, w in zip(r, cw):
            sh.text((xx + 40, y - rh + 70), c, 80)
            xx += w
        y -= rh
    sh.line((x0, y), (x0 + W_, y))
    xx = x0
    for w in cw + [0]:
        sh.line((xx, y0), (xx, y))
        xx += w
    return y


def mech_notes(sh, x0, y0, wrap=None):
    sh.L('M-注記', 7)
    notes = [
        '■ 特記事項 (換気・空調)',
        '1. ダクトは スパイラルダクト(亜鉛鉄板)φ150 / φ100、曲りはベンド大R(R≧ダクト径×1.5)とする。',
        '2. 外壁フードは深形フード。道路面(南面・延焼ライン)は防火ダンパー付(P-18VSD4 FD付)とする。',
        '   ※道路面＝南面(図面下側)と想定。東面も道路の場合はTF-2/TF-3のフードもFD付に変更。',
        '3. 換気量・圧損は 換気機種選定書(T263764)による。ルート変更時は圧損再計算(機外静圧60Pa以下)。',
        '4. 冷媒管は 被覆銅管(断熱材付)、支持間隔1.5m以下、気密試験・真空引き後に冷媒追加充填。',
        '5. ドレン管は 硬質塩ビ管 VP(保温付)、勾配1/100以上、トラップ・掃除口設置。カセット形は内蔵ドレンアップ使用。',
        '6. 室内外連絡線・リモコン線は空調メーカー指定サイズとする(図示 VVF2.0-3C)。',
        '7. 室外機周囲は据付説明書の必要スペースを確保。屋根上は防振架台・転倒防止アンカー。',
        '8. 厨房(火気使用室)の厨房フード・排気ファンは本計画外。厨房設備業者と調整(建基法28条3項)。',
        '9. 倉庫換気扇EF-1/2は機種未定(要決定)。TF-1はダクト長約7mのため静圧確認。',
    ]
    y = y0
    for n in notes:
        parts = [n] if not wrap else [n[i:i + wrap] for i in range(0, len(n), wrap)]
        for k, p in enumerate(parts):
            sh.text((x0 + (0 if k == 0 else 250), y), p, 85 if not n.startswith('■') else 120)
            y -= 160
        y -= 30
