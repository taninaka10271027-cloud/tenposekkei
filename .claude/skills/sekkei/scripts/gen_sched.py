"""盤結線図・負荷計算・幹線選定・凡例・盤姿図."""
import math
import cad
import data as D
import gen_wire as W

STD_BRK = [30, 40, 50, 60, 75, 100, 125, 150, 175, 200]
# CV 3心 許容電流 参考値[A] (電線管等収納・周囲30℃相当)
CE3C = [(8, 42), (14, 61), (22, 80), (38, 113), (60, 150), (100, 202)]
L_TRUNK = 15.0   # 想定幹線長 [m] (引込取付点〜Wh〜盤)


def circuit_loads():
    va = {}
    for c in D.L1_CIRCUITS:
        va[c[0]] = c[3] if c[3] is not None else 0
    for lst in (D.L1F, D.L2F):
        for d in lst:
            va[d['cir']] = va.get(d['cir'], 0) + D.FIXTURES[d['t']]['va']
    for lst in (D.FAN1F, D.FAN2F):
        for f in lst:
            va[f['cir']] += f['va']
    for lst in (D.OUT1F, D.OUT2F):
        for o in lst:
            c = [x for x in D.L1_CIRCUITS if x[0] == o['cir']][0]
            if c[3] is None:
                va[o['cir']] += 150
    return va


def counts():
    n = {}
    for lst in (D.OUT1F, D.OUT2F):
        for o in lst:
            n[o['cir']] = n.get(o['cir'], 0) + 1
    return n


def demand_factor(c):
    no = int(c[0].split('-')[-1])
    if no in (5, 6, 7, 8, 9, 13, 14):
        return 0.5
    return 1.0


def phase_assign(va):
    R = T = 0.0
    ph = {}
    for c in D.L1_CIRCUITS:
        if c[2] == '200V':
            ph[c[0]] = 'R-T'
    for c in sorted([c for c in D.L1_CIRCUITS if c[2] == '100V'], key=lambda c: -va[c[0]]):
        if R <= T:
            ph[c[0]] = 'R-N'
            R += va[c[0]] * demand_factor(c)
        else:
            ph[c[0]] = 'T-N'
            T += va[c[0]] * demand_factor(c)
    return ph


def calc():
    va = circuit_loads()
    ph = phase_assign(va)
    tot = sum(va[c[0]] for c in D.L1_CIRCUITS)
    dem = {'R-N': 0, 'T-N': 0, 'R-T': 0}
    for c in D.L1_CIRCUITS:
        dem[ph[c[0]]] += va[c[0]] * demand_factor(c)
    IR = dem['R-N'] / 100 + dem['R-T'] / 200
    IT = dem['T-N'] / 100 + dem['R-T'] / 200
    Imax = max(IR, IT)
    mainL = next(b for b in STD_BRK if b >= Imax)
    cabL = next(s for s in CE3C if s[1] >= mainL)
    eL = 17.8 * L_TRUNK * Imax / (1000 * cabL[0])
    totP = sum(c[2] for c in D.P1_CIRCUITS) + 3000  # 予備見込 3kVA
    IP = totP / (math.sqrt(3) * 200)
    mainP = max(next(b for b in STD_BRK if b >= IP * 1.1), 50)
    cabP = next(s for s in CE3C if s[1] >= mainP)
    eP = 30.8 * L_TRUNK * IP / (1000 * cabP[0])
    return dict(va=va, ph=ph, tot=tot, dem=dem, IR=IR, IT=IT, Imax=Imax, mainL=mainL, cabL=cabL, eL=eL, totP=totP, IP=IP,
                mainP=mainP, cabP=cabP, eP=eP)


def brk_sym(sh, x, y, kind='B'):
    sh.rect(x, y - 70, x + 220, y + 70)
    sh.text((x + 110, y), kind, 90, 0, 'MC')


def table(sh, x0, y0, cw, rows, rh=260, th=88, head=True):
    W_ = sum(cw)
    y = y0
    for i, r in enumerate(rows):
        sh.line((x0, y), (x0 + W_, y))
        xx = x0
        for c, w in zip(r, cw):
            sh.text((xx + 40, y - rh + (rh - th) / 2 + 10), str(c), th)
            xx += w
        y -= rh
    sh.line((x0, y), (x0 + W_, y))
    xx = x0
    for w in cw + [0]:
        sh.line((xx, y0), (xx, y))
        xx += w
    return y


def sheet_panels(sh):
    K = calc()
    sh.L('E-盤結線図', 7)
    # ---------------------------------------------------------- 幹線系統図
    x0, yt = 900, 13300
    sh.text((x0, yt), '■ 幹線系統図', 160)
    sh.L('E-幹線', 1)
    # 引込
    sh.circle((x0 + 600, yt - 900), 150)
    sh.text((x0 + 850, yt - 950), '引込柱 / 引込線取付点 (電力会社)', 95)
    sh.text((x0 + 850, yt - 1100), '低圧 電灯 1φ3W 100/200V・動力 3φ3W 200V 60Hz', 95)
    # 電灯側
    xa, xb = x0 + 600, x0 + 2600
    sh.line((xa, yt - 1050), (xa, yt - 1700))
    sh.line((xa, yt - 1700), (xb, yt - 1700))
    sh.line((xa, yt - 1050), (xa, yt - 1300))
    sh.line((xa, yt - 1300), (xa - 0, yt - 1300))
    # 電灯 Wh -> L-1
    for (xx, nm, lab, cab, mb, sub) in [
        (xa, '電灯', 'L-1 電灯分電盤 (1F倉庫東)', 'CV %dsq-3C' % K['cabL'][0], '主幹 MCCB 3P %dA' % K['mainL'], '1φ3W 100/200V'),
        (xb, '動力', 'P-1 動力盤 (1F倉庫東)', 'CV %dsq-3C' % K['cabP'][0], '主幹 MCCB 3P %dA' % K['mainP'], '3φ3W 200V')]:
        sh.line((xx, yt - 1700), (xx, yt - 2300))
        sh.rect(xx - 300, yt - 2900, xx + 300, yt - 2300)
        sh.text((xx, yt - 2600), 'Wh', 200, 0, 'MC')
        sh.text((xx + 380, yt - 2500), nm + '用 取引用計器', 85)
        sh.text((xx + 380, yt - 2650), '(電力会社支給)', 85)
        sh.line((xx, yt - 2900), (xx, yt - 4300))
        sh.text((xx + 80, yt - 3500), cab, 95, 90, 'C')
        sh.text((xx + 260, yt - 3500), 'L≒%dm' % L_TRUNK, 85, 90, 'C')
        sh.L('E-幹線', 1)
        if nm == '電灯':
            cad.sym_panel_L(sh, xx - 400, yt - 4700, xx + 400, yt - 4300)
        else:
            cad.sym_panel_P(sh, xx - 400, yt - 4700, xx + 400, yt - 4300)
        sh.text((xx, yt - 4900), lab, 95, 0, 'C')
        sh.text((xx, yt - 5060), sub, 85, 0, 'C')
        sh.text((xx, yt - 5210), mb, 85, 0, 'C')
        # 接地
        sh.line((xx + 400, yt - 4500), (xx + 650, yt - 4500))
        sh.line((xx + 650, yt - 4500), (xx + 650, yt - 4700))
        for k, w in enumerate((160, 110, 60)):
            sh.line((xx + 650 - w, yt - 4700 - k * 50), (xx + 650 + w, yt - 4700 - k * 50))
        sh.text((xx + 830, yt - 4800), 'ED', 85)
    sh.L('E-盤結線図', 7)
    sh.text((x0, yt - 5700), '接地 ED: D種接地工事 (100Ω以下、0.5秒以内に動作する', 85)
    sh.text((x0, yt - 5850), '漏電遮断器施設時は500Ω以下)  接地線 IV 5.5sq', 85)
    # ---------------------------------------------------------- 負荷計算・幹線選定
    yy = yt - 6400
    sh.text((x0, yy), '■ 想定負荷容量・幹線サイズ選定', 160)
    rows = [
        ('項目', 'L-1 電灯盤', 'P-1 動力盤'),
        ('電気方式', '1φ3W 100/200V', '3φ3W 200V'),
        ('設備容量', '%.1f kVA' % (K['tot'] / 1000), '%.1f kVA(予備3kVA含)' % (K['totP'] / 1000)),
        ('需要率', '一般ｺﾝｾﾝﾄ0.5 他1.0', '1.0'),
        ('R相/T相 需要VA', 'R-N %.0f / T-N %.0f' % (K['dem']['R-N'], K['dem']['T-N']), '-'),
        ('200V負荷(R-T)', '%.0f VA' % K['dem']['R-T'], '-'),
        ('設計電流', 'R %.1fA / T %.1fA' % (K['IR'], K['IT']), '%.1f A' % K['IP']),
        ('主幹ブレーカー', 'MCCB 3P %dAF/%dAT' % (max(K['mainL'], 100) if K['mainL'] > 75 else 100, K['mainL']),
         'MCCB 3P %dAF/%dAT' % (100 if K['mainP'] > 50 else 50, K['mainP'])),
        ('幹線 (許容電流)', 'CV %dsq-3C (%dA)' % K['cabL'], 'CV %dsq-3C (%dA)' % K['cabP']),
        ('電圧降下 L=%dm' % L_TRUNK, '%.2fV (%.2f%%) ≦2%%' % (K['eL'], K['eL'] / 100 * 100),
         '%.2fV (%.2f%%) ≦2%%' % (K['eP'], K['eP'] / 200 * 100)),
    ]
    y = table(sh, x0, yy - 150, [1300, 1700, 1600], rows, 250, 82)
    notes = ['※電圧降下 e=K・L・I/(1000・A)  K:1φ3W=17.8 3φ3W=30.8',
             '※許容電流は参考値。幹線長・布設条件は現地確定後に再検討',
             '※幹線・動力分岐は CVケーブル (電灯・コンセントは VVF)',
             '※契約(参考) 電灯:主開閉器契約 %dA / 動力:負荷設備契約 約%.0fkW' % (K['mainL'], K['totP'] / 1000 - 3),
             '※いけす容量は仮定(4.0kVA)。30A一杯(約10kVA)の場合 P-1主幹75A・幹線22sqとする',
             '※L≒15mは想定(引込取付点〜引込口〜Wh〜盤)。引込口開閉器は盤主幹で兼用',
             '　(引込口から盤まで8m以下の場合。超える場合は引込口に開閉器を別設)']
    for i, n in enumerate(notes):
        sh.text((x0, y - 200 - i * 170), n, 80)
    # ---------------------------------------------------------- L-1 単線結線図
    x0 = 5100
    yt = 13600
    sh.text((x0, yt), '■ L-1 電灯分電盤 単線結線図  1φ3W 100/200V 60Hz   (屋内露出形 鋼板製  1F倉庫(東))', 150)
    bx = x0 + 900
    rh = 360
    top = yt - 700
    sh.line((bx - 600, top + 500), (bx, top + 500))
    sh.text((bx - 600, top + 560), 'Wh(電灯)より', 85)
    sh.line((bx, top + 500), (bx, top + 300))
    brk_sym(sh, bx - 110, top + 220, 'B')
    sh.text((bx + 200, top + 260), '主幹 MCCB 3P %dA (中性線欠相保護付)' % K['mainL'], 85)
    sh.line((bx, top + 150), (bx, top - len(D.L1_CIRCUITS) * rh + 100))
    heads = ['回路', '分岐ブレーカー', '相', '負荷名称', '数量', '容量VA', '電線']
    cx = [bx + 820, bx + 1450, bx + 3000, bx + 3650, bx + 6650, bx + 7250, bx + 8050]
    for h, xx in zip(heads, cx):
        sh.text((xx, top + 120), h, 90)
    n = counts()
    for i, c in enumerate(D.L1_CIRCUITS):
        y = top - i * rh - 150
        sh.line((bx, y), (bx + 120, y))
        brk_sym(sh, bx + 120, y, 'E' if c[6] else 'B')
        sh.line((bx + 340, y), (bx + 760, y))
        sh.text((cx[0], y - 40), c[0], 88)
        sh.text((cx[1], y - 40), ('ELB ' if c[6] else 'MCB ') + c[4], 80)
        sh.text((cx[2], y - 40), K['ph'][c[0]], 80)
        sh.text((cx[3], y - 40), c[1], 80)
        cnt = n.get(c[0], '')
        sh.text((cx[4], y - 40), ('ｺﾝｾﾝﾄ%d' % cnt) if cnt and c[3] is None else '', 75)
        sh.text((cx[5], y - 40), '%d' % K['va'][c[0]], 80)
        sh.text((cx[6], y - 40), c[5], 80)
        sh.line((bx + 760, y - rh / 2 + 10), (bx + 9100, y - rh / 2 + 10), 8)
    yb = top - len(D.L1_CIRCUITS) * rh - 150
    sh.text((bx, yb - 100), '設備容量 %.0f VA / 需要負荷 %.0f VA (R-N:%.0f / T-N:%.0f / R-T:%.0f)  主幹負荷率 約%.0f%%' % (
        K['tot'], sum(K['dem'].values()), K['dem']['R-N'], K['dem']['T-N'], K['dem']['R-T'], K['Imax'] / K['mainL'] * 100), 88)
    sh.text((bx, yb - 280), 'B:配線用遮断器(MCB)  E:漏電遮断器(ELB 高感度高速形 30mA 0.1s)  2P1E:2極1素子  2P2E:2極2素子', 80)
    sh.text((bx, yb - 430), '照明回路は 1F客席側(L-1-1)・1F厨房関係(L-1-2)・2F(L-1-3)・予備(L-1-4)。換気扇は同系統の照明回路に接続。', 80)
    sh.text((bx, yb - 580), '2F予備回路 L-1-20〜23 (ブレーカー実装、2Fへ空配管PF22×4)。非常用照明・誘導灯は専用回路L-1-24(他の回路と共用しない)。', 80)
    # ---------------------------------------------------------- P-1
    x0 = 15500
    yt = 13600
    sh.text((x0, yt), '■ P-1 動力盤 単線結線図  3φ3W 200V', 150)
    bx = x0 + 400
    top = yt - 700
    sh.line((bx - 400, top + 500), (bx, top + 500))
    sh.text((bx - 400, top + 560), 'Wh(動力)より', 85)
    sh.line((bx, top + 500), (bx, top + 300))
    brk_sym(sh, bx - 110, top + 220, 'B')
    sh.text((bx + 200, top + 260), '主幹 MCCB 3P %dA' % K['mainP'], 85)
    sh.line((bx, top + 150), (bx, top - 6 * rh + 100))
    cx = [bx + 600, bx + 1150, bx + 2450]
    for h, xx in zip(['回路', '分岐ブレーカー', '負荷名称 / 容量・電線'], cx):
        sh.text((xx, top + 120), h, 90)
    for i, c in enumerate(D.P1_CIRCUITS):
        y = top - i * rh - 150
        sh.line((bx, y), (bx + 120, y))
        brk_sym(sh, bx + 120, y, 'E')
        sh.line((bx + 340, y), (bx + 540, y))
        sh.text((cx[0], y - 40), c[0], 85)
        sh.text((cx[1], y - 40), c[3], 75)
        sh.text((cx[2], y + 10), c[1], 75)
        s = ('%.1fkVA  ' % (c[2] / 1000) if c[2] else '') + (c[4] if c[4] != '-' else '')
        sh.text((cx[2], y - 120), s, 72)
    yb = top - 6 * rh - 150
    sh.text((bx, yb - 80), '合計 %.1f kVA (予備3kVA含) / 設計電流 %.1f A' % (K['totP'] / 1000, K['IP']), 88)
    sh.text((bx, yb - 240), 'いけす・厨房用空調(室外機電源)は 3φ200V 30A 各1回路(指定)', 80)
    sh.text((bx, yb - 390), 'PUZ-ERMP56 2台は三相200Vのため動力盤より専用回路', 80)
    sh.text((bx, yb - 540), '分岐電線: 30A回路 CV5.5sq-3C、20A回路 CV3.5sq-3C、', 80)
    sh.text((bx, yb - 690), '接地線 IV2.0 (C/D種接地)', 80)
    # 分岐 電圧降下
    yy = yb - 1000
    sh.text((bx, yy), '■ 分岐回路 電圧降下(最遠端) 参考', 120)
    rows = [('回路', '負荷', '電流A', '亘長m', '線径', '電圧降下')]
    for cir, sq, d, I, k in [('P-1-1', 5.5, 'いけす', 4000 / (math.sqrt(3) * 200), 30.8),
                             ('P-1-2', 5.5, 'AC-1', 5300 / (math.sqrt(3) * 200), 30.8),
                             ('P-1-3', 3.5, 'AC-2', 2300 / (math.sqrt(3) * 200), 30.8),
                             ('P-1-4', 3.5, 'AC-3', 2300 / (math.sqrt(3) * 200), 30.8)]:
        L = cad.path_len(cad.fillet(W.P_ROUTES[cir], 600)) / 1000 + 4
        e = k * L * I / (1000 * sq)
        rows.append((cir, d, '%.1f' % I, '%.0f' % L, 'CV%.1fsq' % sq, '%.2fV(%.1f%%)' % (e, e / 2)))
    table(sh, bx, yy - 150, [600, 600, 650, 600, 650, 1300], rows, 240, 80)
    return K


# =================================================================== 凡例・器具表・盤姿図
LEG_ROWS = [
    ('fluor', 'A/B', 'LEDベースライト (直付) 図示器具記号・点滅区分'),
    ('pend', 'C', 'ペンダント'),
    ('spot', 'D', 'スポットライト(ライティングダクト用)'),
    ('ld', 'LD', 'ライティングダクト'),
    ('dl', 'E', 'ダウンライト'),
    ('br', 'F〜I', 'ブラケット (壁付 FL+2000)'),
    ('em', '非', '非常用照明 電池内蔵形 (提案・専用回路)'),
    ('ex', '避C', '避難口誘導灯 C級 (提案)'),
    ('out', '2', '壁付コンセント 2口 (FL+300、厨房内FL+1500)'),
    ('out', '2E', '同 接地極付'),
    ('out', '2ET', '同 接地極付接地端子付'),
    ('out', 'EET250V', 'エアコン用 単相200V 接地極付接地端子付 (FL+2000)'),
    ('out', 'WPE', '防雨形コンセント 接地極付'),
    ('out', '2E EV/AC', '専用コンセント 接地極付 (EV・AC-7)'),
    ('isu', '3φ200V', 'いけす用電源 (3φ200V 30A 端子/コンセント)'),
    ('hsw', 'S', '手元開閉器 (屋外形 ELB箱)'),
    ('sw', '●', 'タンブラスイッチ (FL+1300、厨房内FL+1500)'),
    ('sw3', '●3', '3路スイッチ'),
    ('swv', '○n', '換気扇用コントロールスイッチ (英字は換気扇の記号と対応)'),
    ('fan', 'VD/PF/TF', '換気扇 (ダクト用/パイプ用)'),
    ('gr', 'SA', '自然給気グリル'),
    ('hood', '', '外壁フード'),
    ('pl', 'L-1', '電灯分電盤'),
    ('pp', 'P-1', '動力盤'),
    ('wh', 'Wh', '電力量計 (電灯用・動力用)'),
    ('acin', 'AC-n', '空調室内機'),
    ('acout', 'AC-n', '空調室外機'),
    ('ldf', 'F', 'ライティングダクト 給電点(フィードイン)'),
    ('wire', '', '天井隠ぺい配線 (VVFケーブル)'),
    ('tick3', '///', '電線条数 (斜線の数＝電線本数)  無記入は1.6mm'),
    ('tick2p', '// 2.0', '電源配線 (条数＋2.0＝2.0mm)'),
    ('jb', '', 'VVF用ジョイントボックス (電源・器具・スイッチを結線)'),
    ('pwr', 'CV5.5sq-3C', '動力配線 (ケーブル種類・心数を記入)'),
    ('hr', 'L-1-n', '分電盤への配線 (回路番号)'),
    ('riser', '', '立上り / 引下げ'),
    ('link', '', '空調 内外連絡線'),
]


def draw_leg_sym(sh, kind, x, y):
    if kind == 'fluor':
        cad.sym_fluor(sh, x, y, 700, 150, 'H')
    elif kind == 'pend':
        cad.sym_pendant(sh, x, y)
    elif kind == 'spot':
        cad.sym_spot(sh, x - 100, y, (1, 0))
    elif kind == 'ld':
        cad.sym_ldduct(sh, (x - 350, y), (x + 350, y))
    elif kind == 'dl':
        cad.sym_downlight(sh, x, y)
    elif kind == 'br':
        cad.sym_bracket(sh, x, y, 'N')
    elif kind == 'em':
        cad.sym_emergency(sh, x, y)
    elif kind == 'ex':
        cad.sym_exit(sh, x, y, 'H')
    elif kind == 'out':
        cad.sym_outlet(sh, x, y, 'N')
    elif kind == 'sw':
        cad.sym_switch(sh, x, y, 'S')
    elif kind == 'sw3':
        cad.sym_switch(sh, x, y, 'S')
        sh.text((x + 120, y - 50), '3', 90)
    elif kind == 'swv':
        cad.sym_switch(sh, x, y, 'V')
    elif kind == 'fan':
        cad.sym_fan(sh, x, y, 300)
    elif kind == 'gr':
        cad.sym_grille(sh, x, y, 200)
    elif kind == 'hood':
        cad.sym_hood(sh, x, y - 50, 'N', 100)
    elif kind == 'pl':
        cad.sym_panel_L(sh, x - 300, y - 120, x + 300, y + 120)
    elif kind == 'pp':
        cad.sym_panel_P(sh, x - 300, y - 120, x + 300, y + 120)
    elif kind == 'wire':
        cad.draw_segs(sh, cad.fillet([(x - 400, y - 100), (x + 100, y - 100), (x + 100, y + 120)], 200))
    elif kind == 'hr':
        sh.line((x - 300, y), (x + 300, y))
        cad.arrow(sh, (x - 300, y), (x + 300, y), 150)
    elif kind == 'riser':
        cad.sym_riser(sh, x - 250, y - 60, True)
        cad.sym_riser(sh, x + 150, y - 60, False)
    elif kind == 'isu':
        sh.circle((x, y), 150)
        sh.line((x - 100, y), (x + 60, y))
        sh.line((x + 60, y - 70), (x + 60, y + 70))
    elif kind == 'hsw':
        sh.rect(x - 130, y - 130, x + 130, y + 130)
        sh.text((x, y), 'S', 120, 0, 'MC')
    elif kind == 'wh':
        sh.rect(x - 250, y - 130, x + 250, y + 130)
        sh.text((x, y), 'Wh', 120, 0, 'MC')
    elif kind == 'acin':
        cad.sym_ac_wall(sh, x, y - 100, 600, 200, 'S')
    elif kind == 'acout':
        cad.sym_ac_outdoor(sh, x - 300, y - 130, 600, 260)
    elif kind == 'ldf':
        cad.sym_ldduct(sh, (x - 100, y), (x + 350, y))
        sh.text((x - 160, y - 40), 'F', 80, 0, 'R')
    elif kind in ('tick3', 'tick2p'):
        import wire2
        sh.line((x - 400, y), (x + 400, y))
        wire2.ticks(sh, [(x - 400, y), (x + 400, y)], 3 if kind == 'tick3' else 2, kind == 'tick2p')
    elif kind == 'jb':
        import wire2
        sh.line((x - 400, y), (x - 100, y))
        sh.line((x + 100, y), (x + 400, y))
        wire2.sym_jb(sh, x, y)
    elif kind == 'pwr':
        sh.line((x - 400, y), (x + 400, y))
        sh.text((x, y + 60), 'CV5.5sq-3C', 70, 0, 'C')
    elif kind == 'link':
        sh.line((x - 400, y), (x + 400, y), 256, 'DASHED')


def sheet_legend(sh, K):
    sh.L('E-凡例', 7)
    x0, yt = 800, 13700
    sh.text((x0, yt), '■ 凡例 (JIS C 0303 による)', 160)
    rh = 305
    y = yt - 300
    sh.line((x0, y), (x0 + 5200, y))
    for kind, mark, desc in LEG_ROWS:
        sh.L('E-凡例', 7)
        draw_leg_sym(sh, kind, x0 + 600, y - rh / 2)
        sh.text((x0 + 1150, y - rh / 2 - 40), mark, 90)
        sh.text((x0 + 2000, y - rh / 2 - 40), desc, 88)
        y -= rh
        sh.line((x0, y), (x0 + 5200, y), 8)
    sh.line((x0, yt - 300), (x0, y))
    sh.line((x0 + 1100, yt - 300), (x0 + 1100, y))
    sh.line((x0 + 1950, yt - 300), (x0 + 1950, y))
    sh.line((x0 + 5200, yt - 300), (x0 + 5200, y))
    sh.text((x0, y - 250), '器具・換気扇記号の右の英字(a,b…)は点滅区分で、同じ英字のスイッチで点滅する。3は3路。', 85)
    sh.text((x0, y - 400), '配線は回路毎に別画層 (W-L-1-n / W-P-1-n) に作図。同一点滅区分の器具・コンセントは送り配線。', 85)
    sh.text((x0, y - 550), '照明+換気の系統は照明器具でジョイントし、スイッチ・換気扇へ配線。2.0表記区間で3本以上の場合、電源2本は2.0・他は1.6。', 85)
    # ---------------------------------------------------- 照明器具表
    x1 = 6600
    sh.text((x1, yt), '■ 照明器具表 (照明プラン KOIZUMI 2026.10.18 による)', 160)
    rows = [('記号', '品番', '名称', '光源', '取付', 'VA', '1F', '2F')]
    for k in 'ABCDEFGHI':
        f = D.FIXTURES[k]
        n1 = sum(1 for d in D.L1F if d['t'] == k)
        n2 = sum(1 for d in D.L2F if d['t'] == k)
        rows.append((k, f['model'], f['name'], f['lamp'], f['mount'], f['va'], n1, n2))
    rows.append(('LD', 'WE0222/0223 他', 'ライティングダクト(黒)', '8000/5000/3000', '直付', '-', 3, 0))
    n1 = sum(1 for d in D.L1F if d['t'] == 'EM'); n2 = sum(1 for d in D.L2F if d['t'] == 'EM')
    rows.append(('非', '(提案)', '非常用照明 電池内蔵LED', 'LED', '直付/埋込', 3, n1, n2))
    n1 = sum(1 for d in D.L1F if d['t'] == 'EX'); n2 = sum(1 for d in D.L2F if d['t'] == 'EX')
    rows.append(('避C', '(提案)', '避難口誘導灯 C級', 'LED', '壁/天井', 3, n1, n2))
    yb = table(sh, x1, yt - 250, [400, 1850, 2050, 1750, 1150, 380, 330, 330], rows, 300, 78)
    sh.text((x1, yb - 220), '※非常用照明・誘導灯は照明プランに無いため法規対応として提案配置(建基法施行令126条の4・消防法施行令26条)。', 82)
    sh.text((x1, yb - 370), '　所轄消防・確認検査機関と協議の上、機種・台数を確定のこと。常時充電のため非点滅の照明回路に接続。', 82)
    # ---------------------------------------------------- 設置高さ・一般事項
    yy = yb - 750
    sh.text((x1, yy), '■ 取付高さ (FL基準・器具中心)', 140)
    rows = [('機器', '取付高さ'), ('一般コンセント', 'FL+300'), ('スイッチ', 'FL+1300'), ('厨房内 コンセント・スイッチ', 'FL+1500'),
            ('ブラケット照明', 'FL+2000'), ('エアコン用コンセント', 'FL+2000 (機器横)'), ('分電盤・動力盤', '盤上端 FL+1900'),
            ('誘導灯(避難口)', '扉上部 (FL+2100程度)')]
    table(sh, x1, yy - 150, [2500, 2200], rows, 260, 85)
    xn = x1 + 5100
    notes = [
        '■ 一般事項',
        '1. 本図は電気設備技術基準・同解釈、内線規程(JEAC8001)、',
        '   JIS C 0303(構内電気設備の配線用図記号)に準拠する。',
        '2. 電灯・コンセント配線は VVFケーブル 天井・壁内隠ぺい',
        '   (20A分岐 1.6mm以上、専用回路は2.0mm)。',
        '   幹線・動力分岐は CVケーブル、接地線は IV。',
        '3. 水気のある場所(厨房・トイレ)・屋外・エアコン・EVは',
        '   漏電遮断器(30mA 0.1秒)で保護する。',
        '4. コンセント回路は1回路3〜4個、厨房は専用回路。',
        '5. 接地: 300V以下 D種接地。200Vコンセントは接地極付。',
        '6. 換気扇は同系統の照明回路に接続(換気扇用SWで操作)。',
        '7. 1F⇔2Fの配線は階段横 立上り位置より。2F予備4回路は',
        '   PF22×4 空配管(呼線入)とする。非常灯・誘導灯は専用回路。',
        '8. 器具位置は照明プランPDFより座標変換(誤差±100程度)。',
        '   施工前に天井伏図・設備機器と調整のこと。',
    ]
    for i, n in enumerate(notes):
        sh.text((xn, yy - i * 175), n, 85 if not n.startswith('■') else 140)
    # ---------------------------------------------------- 機器姿図
    xs = 15100
    sh.text((xs, yt), '■ 機器姿図 (盤外形・参考)', 160)

    def panel_fig(x, y, w, h, d, name, spec, ncol, nrow, main):
        s = 0.9  # 1/50→図上 1:… 縮尺 1/20相当で描くため ×2.5
        k = 2.5
        sh.rect(x, y - h * k, x + w * k, y)
        sh.rect(x + 60, y - h * k + 60, x + w * k - 60, y - 60)
        # main breaker
        mx = x + w * k / 2
        sh.rect(mx - 120, y - 420, mx + 120, y - 160)
        sh.text((mx + 170, y - 300), main, 70)
        # branches
        bw, bh = 150, 230
        gx0 = x + 250
        for r in range(nrow):
            for c in range(ncol):
                bx = gx0 + c * (bw + 40)
                by = y - 700 - r * (bh + 90)
                if bx + bw > x + w * k - 200:
                    continue
                sh.rect(bx, by - bh, bx + bw, by)
        # side view
        sx = x + w * k + 250
        sh.rect(sx, y - h * k, sx + d * k, y)
        sh.text((x, y + 120), name, 110)
        sh.text((x, y - h * k - 200), 'W%d×H%d×D%d' % (w, h, d), 90)
        for i, t in enumerate(spec):
            sh.text((x, y - h * k - 380 - i * 160), t, 80)

    panel_fig(xs, yt - 450, 600, 1000, 160, 'L-1 電灯分電盤 (正面・側面 S=1/20)',
              ['屋内露出形 鋼板製 1.6t 扉付 マンセル5Y7/1', '主幹 MCCB 3P %dA 分岐 25回路 (予備含)' % K['mainL'],
               '1φ3W 100/200V 60Hz  名札・回路表示付'], 5, 5, 'MCCB')
    panel_fig(xs + 2600, yt - 450, 500, 700, 160, 'P-1 動力盤 (正面・側面 S=1/20)',
              ['屋内露出形 鋼板製 1.6t 扉付', '主幹 MCCB 3P %dA 分岐 ELB 6回路' % K['mainP'], '3φ3W 200V 60Hz'], 3, 2, 'MCCB')
    # Wh box
    yw = yt - 4400
    sh.text((xs, yw), 'Wh 計器箱 (屋外 北面外壁 電灯用・動力用 各1)', 100)
    for i in range(2):
        bx = xs + i * 1500
        sh.rect(bx, yw - 1300, bx + 1000, yw - 200)
        sh.circle((bx + 500, yw - 650), 250)
        sh.text((bx + 500, yw - 650), 'Wh', 140, 0, 'MC')
        sh.text((bx + 500, yw - 1450), ('電灯' if i == 0 else '動力') + ' W400×H440(参考)', 75, 0, 'C')
