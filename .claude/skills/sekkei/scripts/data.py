"""Device schedule for 樽屋 1F / 2F (DXF model coords, mm)."""

# ---------------------------------------------------------------- 照明器具表
FIXTURES = {
    'A': dict(model='XU93575 + XE57543', maker='KOIZUMI', name='LEDベースライト 逆富士 W150 1250', lamp='LED 昼白色5000K 5030lm',
              va=34, n=5, mount='直付'),
    'B': dict(model='AH92025L + AE57494', maker='KOIZUMI', name='LEDベースライト 逆富士 FHF32相当', lamp='LED 昼白色5000K 3235lm',
              va=20, n=5, mount='直付'),
    'C': dict(model='AP51063', maker='KOIZUMI', name='和風ペンダント φ500 (E26×2)', lamp='LED電球60W相当×2 電球色2700K', va=26,
              n=9, mount='吊下(フランジ)'),
    'D': dict(model='AS51473', maker='KOIZUMI', name='LEDスポットライト プラグタイプ', lamp='LED 電球色2700K 590lm', va=12, n=14,
              mount='ライティングダクト'),
    'E': dict(model='AD7251B27', maker='KOIZUMI', name='LEDダウンライト φ100', lamp='LED 電球色2700K 625lm', va=11, n=11,
              mount='埋込φ100'),
    'F': dict(model='AB43050L', maker='KOIZUMI', name='LEDブラケット 和風', lamp='LED 電球色2700K 320lm', va=11, n=4,
              mount='壁付 FL+2000'),
    'G': dict(model='AB52233', maker='KOIZUMI', name='LEDブラケット 密閉型', lamp='LED 電球色2700K 505lm', va=11, n=2,
              mount='壁付 FL+2000'),
    'H': dict(model='AB54654', maker='KOIZUMI', name='LEDコーナーブラケット', lamp='LDF4(GX53) 電球色', va=8, n=1,
              mount='壁付 FL+2000'),
    'I': dict(model='AB54650', maker='KOIZUMI', name='LEDブラケット 上下配光', lamp='LDF4(GX53) 電球色', va=8, n=1,
              mount='壁付 FL+2000'),
    'LD': dict(model='WE0222×2 / WE0223×4 / WE0241×3 / WE0242×3 / WE0243×3', maker='KOIZUMI',
               name='ライティングダクト 8000/5000/3000 各1', lamp='-', va=0, n=3, mount='直付'),
    'EM': dict(model='(提案) 電池内蔵形 LED非常用照明 低天井用', maker='-', name='非常用照明(提案)', lamp='LED', va=3, n=0,
               mount='直付/埋込'),
    'EX': dict(model='(提案) 避難口誘導灯 C級 LED 電池内蔵', maker='-', name='誘導灯(提案)', lamp='LED', va=3, n=0, mount='壁/天井'),
}

# ---------------------------------------------------------------- 1F 照明 (照明プランより座標変換)
LD1 = [  # ライティングダクト  (p, q, name)
    ((9249, 9711), (14249, 9711), 'LD 5000'),
    ((9308, 5786), (17308, 5786), 'LD 8000'),
    ((15870, 1844), (15870, 4844), 'LD 3000'),
]

L1F = []


def _f(t, x, y, cir, grp, **k):
    d = dict(t=t, x=x, y=y, cir=cir, grp=grp)
    d.update(k)
    L1F.append(d)


# 厨房 A (L-1-2) a:西列 b:東列
_f('A', 6237, 5399, 'L-1-2', 'a')
_f('A', 6237, 3397, 'L-1-2', 'a')
_f('A', 8015, 7500, 'L-1-2', 'b')
_f('A', 8015, 5399, 'L-1-2', 'b')
_f('A', 8015, 3397, 'L-1-2', 'b')
# 左倉庫 B (厨房系)
_f('B', 7298, 10814, 'L-1-2', 'k')
# 右倉庫 B ×4 (客席系)
for xx, yy in [(15800, 11500), (17700, 11500), (15800, 8890), (17700, 8890)]:
    _f('B', xx, yy, 'L-1-1', 'j')
# テーブル席 C ×4 / ホール右 C ×2
_f('C', 10195, 11535, 'L-1-1', 'e')
_f('C', 13275, 11535, 'L-1-1', 'e')
_f('C', 11225, 8885, 'L-1-1', 'e')
_f('C', 13955, 8885, 'L-1-1', 'e')
_f('C', 17695, 4185, 'L-1-1', 'h')
_f('C', 17695, 2285, 'L-1-1', 'h')
# D スポット (5000ダクト f / 8000ダクト g / 3000ダクト h)
for xx in (10108, 11062, 11876, 13240, 13876):
    _f('D', xx, 9711, 'L-1-1', 'f', aim=(0, -1) if xx in (11062, 13876) else (0, 1))
for xx in (9968, 11335, 12678, 14138, 15296, 16596):
    _f('D', xx, 5786, 'L-1-1', 'g', aim=(0, -1) if xx in (9968, 12678, 15296) else (0, 1))
for yy in (4292, 3414, 2624):
    _f('D', 15870, yy, 'L-1-1', 'h', aim=(1, 0))
# E ダウンライト (通路) c
for xx in (9469, 11006, 12567, 14107):
    _f('E', xx, 2670, 'L-1-1', 'c')
# F ブラケット (カウンター壁 北面) c
for xx in (9469, 11006, 12567, 14107):
    _f('F', xx, 4110, 'L-1-1', 'c', wall='S')
# G トイレ
_f('G', 12650, 7290, 'L-1-1', 'm', wall='N')   # 女子
_f('G', 17000, 7290, 'L-1-1', 'i', wall='N')   # 男子
# H 階段
_f('H', 13536, 7290, 'L-1-3', 's', wall='N')
# 非常用照明・誘導灯 (提案) 常時点灯回路
_f('EM', 7400, 4400, 'L-1-24', None)
_f('EM', 12300, 11050, 'L-1-24', None)
_f('EM', 12000, 5250, 'L-1-24', None)
_f('EM', 10250, 2400, 'L-1-24', None)
_f('EM', 16700, 5200, 'L-1-24', None)
_f('EM', 14000, 6900, 'L-1-24', None)
_f('EX', 18500, 6350, 'L-1-24', None, orient='V')
_f('EX', 17620, 5700, 'L-1-24', None, orient='V')
_f('EX', 5150, 2800, 'L-1-24', None, orient='V')

# 1F スイッチ (既存プロット位置を使用)  groups / kind  S:片切 3:3路 V:換気
SW1F = [
    dict(x=8348, y=5160, k='S', g='a'), dict(x=8498, y=5160, k='S', g='b'), dict(x=8648, y=5160, k='S', g='c'),
    dict(x=8348, y=5010, k='3', g='g'), dict(x=8498, y=5010, k='V', g='n'), dict(x=8648, y=5010, k='V', g='p'),
    dict(x=6582, y=8962, k='S', g='k'), dict(x=6582, y=9112, k='V', g='q'),
    dict(x=18492, y=7492, k='S', g='j'), dict(x=18492, y=7642, k='V', g='r'),
    dict(x=11481, y=7491, k='S', g='e'), dict(x=11481, y=7641, k='S', g='f'),
    dict(x=11631, y=7491, k='V', g='t'), dict(x=11631, y=7641, k='V', g='u'),
    dict(x=12670, y=6260, k='S', g='m'), dict(x=12670, y=6110, k='V', g='v'),
    dict(x=17375, y=6260, k='S', g='i'), dict(x=17375, y=6110, k='3', g='g'), dict(x=17375, y=5960, k='V', g='w'),
    # 追加
    dict(x=17225, y=6260, k='S', g='h', new=True),
    dict(x=13330, y=6500, k='3', g='s', new=True),
]
SW_CIR_1F = {'a': 'L-1-2', 'b': 'L-1-2', 'k': 'L-1-2', 'n': 'L-1-2', 'q': 'L-1-2'}

# 1F 換気機器 (既存プロット位置)
FAN1F = [
    dict(id='VD-1', t='VD', x=8387, y=6686, g='n', cir='L-1-2', model='VD-18ZVX7-C', va=20, name='厨房'),
    dict(id='VD-2', t='VD', x=14251, y=5680, g='p', cir='L-1-1', model='VD-18ZVX7-C', va=20, name='ホール・カウンター席'),
    dict(id='PF-1', t='PF', x=9268, y=12059, g='t', cir='L-1-1', model='V-12PFL8', va=15, name='テーブル席'),
    dict(id='PF-2', t='PF', x=14146, y=12082, g='u', cir='L-1-1', model='V-12PFL8', va=15, name='テーブル席'),
    dict(id='EF-1', t='PF', x=8001, y=12326, g='q', cir='L-1-2', model='(機種未定)', va=15, name='倉庫(西)'),
    dict(id='EF-2', t='PF', x=15862, y=12233, g='r', cir='L-1-1', model='(機種未定)', va=15, name='倉庫(東)'),
    dict(id='TF-1', t='TF', x=13060, y=6709, g='v', cir='L-1-1', model='V-08PSD8', va=6, name='女子トイレ'),
    dict(id='TF-2', t='TF', x=17514, y=6674, g='w', cir='L-1-1', model='V-08PSD8', va=6, name='男子トイレ'),
]
GRILLE1F = [(10735, 7948), (8387, 3133), (9209, 5159), (14111, 2663), (18420, 2296)]

# 1F コンセント (既存プロット位置)  wall: 壁の方向
OUT1F = [
    dict(x=6188, y=11238, w='W', cir='L-1-5', t='2'), dict(x=5754, y=11137, w='E', cir='L-1-5', t='WPE'),
    dict(x=8572, y=12482, w='N', cir='L-1-5', t='2'), dict(x=8158, y=9038, w='S', cir='L-1-5', t='2'),
    dict(x=8978, y=7718, w='S', cir='L-1-6', t='2'), dict(x=12902, y=7568, w='S', cir='L-1-6', t='2'),
    dict(x=13055, y=7133, w='N', cir='L-1-6', t='2E'),
    dict(x=15107, y=12635, w='N', cir='L-1-7', t='2'), dict(x=14955, y=10100, w='W', cir='L-1-7', t='2'),
    dict(x=15107, y=7568, w='S', cir='L-1-7', t='2'), dict(x=17514, y=7123, w='N', cir='L-1-7', t='2E'),
    dict(x=9848, y=4185, w='S', cir='L-1-8', t='2'), dict(x=11852, y=4185, w='S', cir='L-1-8', t='2'),
    dict(x=14347, y=4185, w='S', cir='L-1-8', t='2'),
    dict(x=18544, y=4984, w='E', cir='L-1-9', t='2'), dict(x=18544, y=3035, w='E', cir='L-1-9', t='2'),
    dict(x=16608, y=3538, w='S', cir='L-1-9', t='2'), dict(x=14957, y=1839, w='S', cir='L-1-9', t='2'),
    dict(x=5492, y=1667, w='S', cir='L-1-10', t='2ET'), dict(x=7452, y=1667, w='S', cir='L-1-11', t='2ET'),
    dict(x=8422, y=1667, w='S', cir='L-1-12', t='2ET'),
    # エアコン専用 (既存"2"を200V専用へ変更)
    dict(x=9260, y=12634, w='N', cir='L-1-15', t='EET 250V', ac='AC-4'),
    dict(x=14239, y=12634, w='N', cir='L-1-16', t='EET 250V', ac='AC-5'),
    # EV 専用 (新設)
    dict(x=11350, y=6250, w='N', cir='L-1-19', t='2E EV', new=True),
]

# 1F 空調
AC1F = [
    dict(id='AC-1', name='厨房', model='PC-RP140HA22 / PUZ-ERMP140LA16', kind='天吊形(厨房用)', pw='3φ200V', cir='P-1-2',
         ind=(7377, 8340), out=(6898, 12988, 950, 330), newout=True),
    dict(id='AC-2', name='カウンター席', model='PL-RP56LA22 / PUZ-ERMP56KA16', kind='2方向天井カセット', pw='3φ200V', cir='P-1-3',
         ind=(10788, 5606), out=(10744, 12988, 809, 300)),
    dict(id='AC-3', name='テーブル席(東)', model='PM-RP56FA22 / PUZ-ERMP56KA16', kind='1方向天井カセット', pw='3φ200V', cir='P-1-4',
         ind=(15155, 3396), out=(16100, 12988, 809, 300), newout=True),
    dict(id='AC-4', name='テーブル席(北西)', model='MSZ-GV5626S-W / MUCZ-G5626S', kind='壁掛形', pw='1φ200V', cir='L-1-15',
         ind=(10216, 12575), out=(9882, 12988, 800, 285)),
    dict(id='AC-5', name='テーブル席(北東)', model='MSZ-GV5626S-W / MUCZ-G5626S', kind='壁掛形', pw='1φ200V', cir='L-1-16',
         ind=(13224, 12575), out=(12890, 12988, 800, 285)),
]
ISU = dict(x=5774, y=8625, cir='P-1-1')
PANEL_L = (17891, 12485, 18491, 12785)
PANEL_P = (17263, 12487, 17863, 12787)
RISER1F = (13700, 7000)   # 1F→2F 配線立上り位置
RISER2F = (13700, 7000)

# ---------------------------------------------------------------- 2F
L2F = []


def _g(t, x, y, cir, grp, **k):
    d = dict(t=t, x=x, y=y, cir=cir, grp=grp)
    d.update(k)
    L2F.append(d)


_g('C', 13250, 2960, 'L-1-3', 'b')
_g('C', 16275, 4235, 'L-1-3', 'c')
_g('C', 16275, 2460, 'L-1-3', 'c')
for xx, yy in [(12599, 6650), (13441, 6650), (12599, 5060), (13441, 5060), (14600, 5828)]:
    _g('E', xx, yy, 'L-1-3', 'a')
_g('E', 16255, 5800, 'L-1-3', 'e')
_g('E', 17300, 6320, 'L-1-3', 'd')
_g('I', 15262, 7330, 'L-1-3', 's', wall='N')
_g('EM', 12300, 3700, 'L-1-24', None)
_g('EM', 15400, 3300, 'L-1-24', None)
_g('EM', 15300, 5900, 'L-1-24', None)
_g('EX', 14450, 6250, 'L-1-24', None, orient='H')

SW2F = [
    dict(x=14080, y=6550, k='3', g='s'), dict(x=14080, y=6700, k='S', g='a'), dict(x=14080, y=6850, k='S', g='b'),
    dict(x=11850, y=4598, k='V', g='f'),
    dict(x=14850, y=4600, k='S', g='c'),
    dict(x=16700, y=5900, k='S', g='d'), dict(x=16700, y=6050, k='V', g='g'), dict(x=16700, y=6200, k='S', g='e'),
]
FAN2F = [
    dict(id='VD-3', t='VD', x=14241, y=4529, g='f', cir='L-1-3', model='VD-18ZVX7-C', va=20, name='2Fホール・カウンター'),
    dict(id='TF-3', t='TF', x=17346, y=6924, g='g', cir='L-1-3', model='V-08PSD8', va=6, name='2Fトイレ'),
]
GRILLE2F = [(12189, 1906), (17259, 1906)]
OUT2F = [
    dict(x=11810, y=2600, w='W', cir='L-1-13', t='2'), dict(x=11810, y=3900, w='W', cir='L-1-13', t='2'),
    dict(x=13150, y=5885, w='N', cir='L-1-13', t='2E'), dict(x=14400, y=1500, w='S', cir='L-1-13', t='2'),
    dict(x=14800, y=2000, w='W', cir='L-1-14', t='2'), dict(x=17700, y=3200, w='E', cir='L-1-14', t='2'),
    dict(x=16300, y=1500, w='S', cir='L-1-14', t='2'), dict(x=17700, y=6000, w='E', cir='L-1-14', t='2E'),
    dict(x=12600, y=1500, w='S', cir='L-1-17', t='EET 250V', ac='AC-6'),
    dict(x=16900, y=5300, w='N', cir='L-1-18', t='2E AC', ac='AC-7'),
]
AC2F = [
    dict(id='AC-6', name='2Fホール', model='MSZ-GV5626S-W / MUCZ-G5626S', kind='壁掛形', pw='1φ200V', cir='L-1-17',
         ind=(13285, 1500), wall='S', out=(12900, 7600, 800, 285)),
    dict(id='AC-7', name='2F個室', model='MSZ-GV3626-W / MUCZ-G3626', kind='壁掛形', pw='1φ100V', cir='L-1-18',
         ind=(16270, 5325), wall='N', out=(15920, 7600, 699, 249)),
]

# ---------------------------------------------------------------- 回路表
# (no, name, phase, V, VA, breaker, cable, elb)
L1_CIRCUITS = [
    ('L-1-1', '1F 客席側 照明・換気', '100V', None, '2P1E 20A', 'VVF 2.0-2C (SW回り1.6)', False),
    ('L-1-2', '1F 厨房関係 照明・換気', '100V', None, '2P1E 20A', 'VVF 2.0-2C (SW回り1.6)', False),
    ('L-1-3', '2F 照明・換気・階段(1F H含)', '100V', None, '2P1E 20A', 'VVF 2.0-2C (SW回り1.6)', False),
    ('L-1-4', '照明 予備', '100V', 0, '2P1E 20A', '-', False),
    ('L-1-5', '1F 倉庫(西)・屋外WPE コンセント', '100V', None, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-6', '1F テーブル席・女子トイレ コンセント', '100V', None, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-7', '1F 倉庫(東)・男子トイレ コンセント', '100V', None, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-8', '1F カウンター コンセント', '100V', None, '2P1E 20A', 'VVF 2.0-2C', False),
    ('L-1-9', '1F ホール コンセント', '100V', None, '2P1E 20A', 'VVF 2.0-2C', False),
    ('L-1-10', '1F 厨房 専用コンセント K-1', '100V', 1200, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-11', '1F 厨房 専用コンセント K-2', '100V', 1200, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-12', '1F 厨房 専用コンセント K-3', '100V', 1200, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-13', '2F ホール コンセント', '100V', None, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-14', '2F 個室・トイレ コンセント', '100V', None, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-15', 'AC-4 1F テーブル席 エアコン専用', '200V', 2000, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-16', 'AC-5 1F テーブル席 エアコン専用', '200V', 2000, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-17', 'AC-6 2F ホール エアコン専用', '200V', 2000, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-18', 'AC-7 2F 個室 エアコン専用', '100V', 1400, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-19', 'EV 専用', '100V', 1500, '2P2E 20A 30mA', 'VVF 2.0-3C(E)', True),
    ('L-1-20', '2F 予備', '100V', 500, '2P1E 20A', '-', False),
    ('L-1-21', '2F 予備', '100V', 500, '2P1E 20A', '-', False),
    ('L-1-22', '2F 予備', '100V', 500, '2P2E 20A 30mA', '-', True),
    ('L-1-23', '2F 予備', '100V', 500, '2P2E 20A 30mA', '-', True),
    ('L-1-24', '非常用照明・誘導灯 専用', '100V', None, '2P1E 20A (赤表示)', 'VVF 2.0-2C', False),
    ('L-1-25', '予備', '100V', 0, '2P2E 20A 30mA', '-', True),
]
P1_CIRCUITS = [
    ('P-1-1', 'いけす (クーラー・ポンプ)', 4000, 'ELB 3P 30A 30mA', 'CV 5.5sq-3C + IV2.0', '30A指定'),
    ('P-1-2', 'AC-1 厨房 PUZ-ERMP140LA16', 5300, 'ELB 3P 30A 30mA', 'CV 5.5sq-3C + IV2.0', '30A指定'),
    ('P-1-3', 'AC-2 カウンター席 PUZ-ERMP56KA16', 2300, 'ELB 3P 20A 30mA', 'CV 3.5sq-3C + IV2.0', ''),
    ('P-1-4', 'AC-3 テーブル席(東) PUZ-ERMP56KA16', 2300, 'ELB 3P 20A 30mA', 'CV 3.5sq-3C + IV2.0', ''),
    ('P-1-5', '予備', 0, 'ELB 3P 30A 30mA', '-', ''),
    ('P-1-6', '予備', 0, 'ELB 3P 20A 30mA', '-', ''),
]
