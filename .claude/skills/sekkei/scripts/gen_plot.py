"""Plot (器具配置) drawing functions."""
import math
import cad
from cad import Sheet
import data as D

LY = {
    'LT': ('E-照明-器具', 3),
    'LD': ('E-照明-ライティングダクト', 3),
    'LTX': ('E-照明-記号・点滅区分', 3),
    'EM': ('E-防災-非常照明・誘導灯(提案)', 1),
    'OUT': ('E-コンセント', 1),
    'OUTX': ('E-コンセント-記号', 1),
    'SW': ('E-スイッチ', 5),
    'SWX': ('E-スイッチ-記号', 5),
    'FAN': ('M-換気-機器', 6),
    'GR': ('M-換気-給気グリル', 3),
    'HD': ('M-換気-外壁フード', 6),
    'AC': ('M-空調-機器', 30),
    'PNL': ('E-盤・Wh', 4),
    'CHK': ('Z-チェック指摘', 1),
    'NOTE': ('E-注記', 7),
}


def lay(sh, k):
    n, c = LY[k]
    sh.L(n, c)


def fixture(sh, d, label=True, grp=True):
    t, x, y = d['t'], d['x'], d['y']
    if t in ('EM', 'EX'):
        lay(sh, 'EM')
        if t == 'EM':
            cad.sym_emergency(sh, x, y)
            if label:
                sh.text((x + 190, y + 120), '非', 110)
        else:
            cad.sym_exit(sh, x, y, d.get('orient', 'H'))
            if label:
                sh.text((x + 280, y + 150), '避C', 110)
        return
    lay(sh, 'LT')
    if t in ('A', 'B'):
        cad.sym_fluor(sh, x, y, 1250, 150, d.get('orient', 'V'))
    elif t == 'C':
        cad.sym_pendant(sh, x, y)
    elif t == 'D':
        cad.sym_spot(sh, x, y, d.get('aim', (1, 0)))
    elif t == 'E':
        cad.sym_downlight(sh, x, y)
    elif t in 'FGHI':
        cad.sym_bracket(sh, x, y, d.get('wall', 'N'))
    if label:
        lay(sh, 'LTX')
        off = (110, 110) if t not in ('A', 'B') else (110, 450)
        if t == 'D':
            off = (120, -260) if d.get('aim', (1, 0))[1] > 0 else (120, 140)
            if d.get('aim', (1, 0))[0] > 0:
                off = (-330, 60)
        s = t + (d['grp'] if grp and d.get('grp') else '')
        sh.text((x + off[0], y + off[1]), s, 120)


def ld_duct(sh, p, q, name):
    lay(sh, 'LD')
    cad.sym_ldduct(sh, p, q)
    lay(sh, 'LTX')
    horiz = abs(p[1] - q[1]) < 1
    nm = name.replace(' ', '')
    if horiz:
        sh.text((p[0] + 40, p[1] + 110), nm, 95)
    else:
        sh.text((p[0] - 110, p[1] + 60), nm, 95, 90)


def switch(sh, s, label=True):
    lay(sh, 'SW')
    cad.sym_switch(sh, s['x'], s['y'], 'V' if s['k'] == 'V' else 'S')
    if label:
        lay(sh, 'SWX')
        g = s['g']
        txt = ('3' if s['k'] == '3' else '') + g
        sh.text((s['x'] - 110, s['y']), txt, 90, 0, 'MR')


def outlet(sh, o, label=True):
    lay(sh, 'OUT')
    cad.sym_outlet(sh, o['x'], o['y'], o['w'])
    if label:
        lay(sh, 'OUTX')
        dx, dy = {'N': (0, -1), 'S': (0, 1), 'E': (-1, 0), 'W': (1, 0)}[o['w']]
        if o.get('ac') == 'AC-6':
            sh.text((o['x'], o['y'] - 420), o['t'], 100, 0, 'C')
        else:
            sh.text((o['x'] + 180, o['y'] + 60 + dy * 120), o['t'], 100)


def fan(sh, f, label=True):
    lay(sh, 'FAN')
    if f['t'] == 'VD':
        cad.sym_fan(sh, f['x'], f['y'], 300)
    else:
        cad.sym_fan(sh, f['x'], f['y'], 300)
    if label:
        sh.text((f['x'] + 190, f['y'] - 230), f['id'] + ' ' + f['g'], 100)


def grille(sh, x, y, label=True):
    lay(sh, 'GR')
    cad.sym_grille(sh, x, y, 200)
    if label:
        sh.text((x + 140, y - 200), 'SA', 90)


def ac_unit(sh, a, floor):
    lay(sh, 'AC')
    x, y = a['ind']
    if a['kind'].startswith('壁掛'):
        if floor == 2:
            cad.sym_ac_wall(sh, x, y, 800, 225, a['wall'])
    ox, oy, w, d = a['out']
    if a.get('newout') or floor == 2:
        cad.sym_ac_outdoor(sh, ox, oy, w, d)
    sh.text((ox, oy + d + 60), a['id'] + ' 室外機', 100)
    if floor == 2 or a['id'] in ('AC-1', 'AC-2', 'AC-3', 'AC-4', 'AC-5'):
        ty = y + (330 if floor == 2 and a['wall'] == 'S' else -380)
        if floor == 1:
            ty = y + 380 if a['id'] in ('AC-1',) else y - 380
            if a['id'] in ('AC-4', 'AC-5'):
                ty = y - 300
        sh.text((x - 380, ty), a['id'], 110)


def hood(sh, x, y, wall, new=False):
    lay(sh, 'HD')
    cad.sym_hood(sh, x, y, wall, 100)


def wh_meters(sh, add_power=True):
    lay(sh, 'PNL')
    if add_power:
        sh.rect(17200, 12935, 17800, 13235)
        sh.text((17500, 13085), 'Wh', 200, 0, 'MC')
        sh.text((17500, 13300), '動力用(追加)', 90, 0, 'C')
    sh.text((18178, 13300), '電灯用', 90, 0, 'C')
    sh.text((18850, 12620), 'L-1', 140)
    sh.text((17300, 12300), 'P-1', 140)


def check_mark(sh, x, y, no, r=450):
    lay(sh, 'CHK')
    sh.circle((x, y), r)
    sh.circle((x + r * 0.75, y + r * 0.75), 140)
    sh.text((x + r * 0.75, y + r * 0.75), str(no), 130, 0, 'MC')


CHECKS = [
    # (no, x, y, text)
    (1, 10790, 5700, 'ライティングダクト8000(D×6)がAC-2 2方向カセット(PL-RP56)と平面干渉。また空調プランのAC-2位置はX≒12,000付近で既存プロットと約1.2m相違→位置確認・調整要'),
    (2, 14110, 2665, '通路ダウンライトE(東端)と給気グリル(SA)が同一位置。グリルを東へ約400移設等の調整要'),
    (3, 16300, 13700, '1F室内機5台(AC-1〜5)に対し既存プロットの室外機は4台。AC-3用室外機を本図で追加'),
    (4, 7370, 13150, 'AC-1室外機 PUZ-ERMP140LA16 は W950×D330(+25)。既存プロットW700で作図→実寸で追記'),
    (5, 4900, 2100, '申請用換気計画:厨房VD-1→西面(Y≒6,690)・ホールVD-2→南面へ排気。既存フード(西面Y≒2,100/東面Y≒2,300)と不一致'),
    (6, 13060, 6709, 'トイレ用パイプファン(V-08PSD8)の屋外フード(P-13VS4)がプロットに無い→ダクト図に追記'),
    (7, 8001, 12326, '倉庫(西・東)の換気扇は申請用換気計画書に記載なし(倉庫は24h換気対象外)。機種・要否確認'),
    (8, 8387, 3133, '給気グリル位置が申請用計画とずれ(厨房 X≒8,390⇔7,440 / ホール南 X≒14,110⇔12,930)。申請図と整合確認'),
    (9, 5754, 11137, '屋外防水コンセント(WP)が印刷されない画層"_0-1_Defpoints"に作図→画層変更要'),
    (10, 17563, 12637, '動力盤記号・トイレ換気扇記号が画層"_0-0_0"に作図。いけす電源が給気グリルと同画層"_1-3_"→画層整理要'),
    (11, 9600, 12250, 'テーブル席北壁のコンセント2箇所は壁掛AC(GV5626S 単相200V)用。"EET 200V エアコン専用"へ変更(本図回路化)'),
    (12, 11000, 2400, '照度分布でホール通路は100〜200lx。JIS Z 9110の飲食店客席(200〜300lx程度)を下回る部分あり→施主確認'),
    (13, 18500, 6350, '非常用照明・誘導灯が照明プランに無い。建基法施行令126条の4/消防法施行令26条の対象→提案配置を追記(所轄協議要)'),
    (14, 17500, 13085, '電力量計はWh1台のみ。電灯・動力の契約別のため動力用Whを追加'),
    (15, 11350, 6250, 'EV電源(100V 20A)がプロットに無い→専用コンセント(2E)を追加'),
    (16, 5000, 5220, '厨房(ガスバーナー・焼台)の火気使用室換気(建基法28条3項)の厨房フード・排気ファンが計画に無い。厨房設備業者に確認し電源回路・負荷を追加'),
    (17, 13060, 7700, 'TF-1(女子)はφ100ダクト約7m+曲り2箇所。V-08PSD8の静圧確認、不足時はダクト用換気扇へ変更'),
]


def checks_layer(sh, items=CHECKS, table_xy=(600, 11250)):
    for no, x, y, t in items:
        check_mark(sh, x, y, no, 380)
    lay(sh, 'CHK')
    x0, y0 = table_xy
    sh.text((x0, y0), '■ 既存プロット・各プラン照合チェック', 140)
    yy = y0 - 260
    for no, x, y, t in items:
        lines = [t[i:i + 22] for i in range(0, len(t), 22)]
        sh.text((x0, yy), '(%d)' % no, 95)
        for ln in lines:
            sh.text((x0 + 300, yy), ln, 95)
            yy -= 150
        yy -= 40


def old_ac1(e):
    """既存プロットのAC-1室外機(W700) → 実寸記号に置換するため配線図・M図では非表示"""
    pts = [e.get('p1'), e.get('p2')]
    return e['layer'] == '_1-6_' and e['type'] == 'LINE' and all(p and 6890 <= p[0] <= 7600 and 12980 <= p[1] <= 13270 for p in pts)


def plot_1f(sh, base, with_checks=True, labels=True):
    cad.copy_base(sh, base, skip=None if with_checks else old_ac1)
    # 既存WP(Defpoints画層)を印刷画層に複写
    lay(sh, 'OUT')
    cad.sym_outlet(sh, 5754, 11137, 'E')
    lay(sh, 'OUTX')
    sh.text((5600, 10800), 'WPE', 100, 0, 'R')
    for d in D.L1F:
        fixture(sh, d, labels)
    for p, q, n in D.LD1:
        ld_duct(sh, p, q, n)
    for s in D.SW1F:
        if s.get('new'):
            switch(sh, s, False)
    if labels:
        for s in D.SW1F:
            lay(sh, 'SWX')
            g = s['g']
            txt = ('3' if s['k'] == '3' else '') + g
            sh.text((s['x'] - 110, s['y']), txt, 85, 0, 'MR')
    for o in D.OUT1F:
        if o.get('new'):
            outlet(sh, o)
        elif o.get('ac'):
            lay(sh, 'OUTX')
            sh.text((o['x'] - 150, o['y'] - 420), 'EET250V(' + o['ac'] + '用)', 85, 0, 'R' if o['ac'] == 'AC-4' else 'L')
    for a in D.AC1F:
        ac_unit(sh, a, 1)
    # 1F fans labels
    lay(sh, 'FAN')
    for f in D.FAN1F:
        sh.text((f['x'] + 190, f['y'] - 260), f['id'] + ' ' + f['g'], 95)
    # toilet hoods / new hoods per ventilation plan
    hood(sh, 12400, 12935, 'N')
    hood(sh, 18795, 6674, 'E')
    hood(sh, 4885, 6686, 'W')
    hood(sh, 14251, 1415, 'S')
    lay(sh, 'AC')
    sh.text((5000, 13450), '室外機:1F北面 地上置き', 100)
    wh_meters(sh)
    if with_checks:
        checks_layer(sh)


def plot_2f(sh, base, labels=True):
    cad.copy_base(sh, base)
    for d in D.L2F:
        fixture(sh, d, labels)
    for s in D.SW2F:
        switch(sh, s, labels)
    for o in D.OUT2F:
        outlet(sh, o, labels)
    for f in D.FAN2F:
        fan(sh, f, labels)
    for g in D.GRILLE2F:
        grille(sh, g[0], g[1], labels)
    for x, y, w in [(14241, 1400, 'S'), (12189, 1400, 'S'), (17259, 1400, 'S'), (17800, 6924, 'E')]:
        hood(sh, x, y, w)
    for a in D.AC2F:
        ac_unit(sh, a, 2)
    lay(sh, 'AC')
    sh.text((10800, 8450), '室外機 AC-6・AC-7 : 1F屋根上 架台設置', 110)
