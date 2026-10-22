import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r12
import cad
import preview
import data as D
import gen_plot as GP
import gen_wire as W
import gen_mech as M
import gen_sched as SC

S = os.environ.get('SEKKEI_WORK', os.getcwd()).rstrip('/') + '/'   # in/1F.dxf, in/2F.dxf, prev/
OUT = os.environ.get('SEKKEI_OUT', S + 'out').rstrip('/') + '/'
PRE = S + 'prev/'
os.makedirs(OUT, exist_ok=True)
os.makedirs(PRE, exist_ok=True)
b1 = r12.parse(S + 'in/1F.dxf')
b2 = r12.parse(S + 'in/2F.dxf')


def frame(sh):
    sh.L('_0-2_図枠', 7)
    sh.rect(500, 500, 20500, 14350)


def retitle(sh, old, new):
    """change the drawing title text copied from the base (e.g. '1階平面図　S=1/50')"""
    for e in sh.msp.query('TEXT'):
        if e.dxf.text.startswith(old):
            e.dxf.text = new
            e.dxf.height = 220
    for p in sh.prev:
        if p['type'] == 'TEXT' and p['text'].startswith(old):
            p['text'] = new
            p['h'] = 220


def cir_table(sh, x0, y0, cirs, title='■ 回路一覧'):
    sh.L('E-注記', 7)
    sh.text((x0, y0), title, 120)
    y = y0 - 220
    for c in cirs:
        name = W.CIR_NAME[c]
        sh.L(('W-%s %s' % (c, name.replace(' ', '_')))[:60], W.CIR_COLOR.get(c, 7))
        sh.line((x0, y + 30), (x0 + 350, y + 30))
        sh.L('E-注記', 7)
        sh.text((x0 + 420, y), '%s %s' % (c, name), 80)
        sh.text((x0 + 420, y - 125), '   ' + W.CIR_CABLE[c], 75)
        y -= 290
    return y


def notes(sh, x0, y0, lines, h=85):
    sh.L('E-注記', 7)
    for i, t in enumerate(lines):
        sh.text((x0, y0 - i * h * 1.75), t, h if not t.startswith('■') else 115)


COMMON_NOTES = ['■ 特記',
                '・取付高さ: コンセントFL+300 / スイッチFL+1300',
                '　厨房内(コンセント・スイッチ)FL+1500',
                '　ブラケットFL+2000 / AC用コンセントFL+2000',
                '・配線: VVFケーブル 天井隠ぺい',
                '・条数は斜線で表示(無記入=1.6mm)',
                '・電源配線は条数+2.0 (2.0mm)',
                '・スイッチ結線はJB(⊘)又は照明器具で結線',
                '・JIS C 0303 / 内線規程 / 電技解釈 による']

sheets = []


def save(sh, name, xlim=(0, 21000), ylim=(0, 14850)):
    path = OUT + name + '.dxf'
    sh.save(path)
    png = PRE + name + '.png'
    preview.render(sh.prev, png, xlim, ylim, width_in=29.7, dpi=110)
    sheets.append((name, path, png))


K = SC.calc()

# ---------------- E-01
sh = cad.Sheet()
GP.plot_1f(sh, b1, with_checks=True)
retitle(sh, '1階平面図', '1階 電灯・コンセント・換気・空調 プロット図　S=1/50')
cad.title_block(sh, 600, 600, 'E-01', '1F 設備プロット図(照明追加・照合)')
save(sh, 'E-01_1F_設備プロット図(照明追加・照合チェック)')

# ---------------- E-02
sh = cad.Sheet()
GP.plot_2f(sh, b2)
retitle(sh, '2階平面図', '2階 電灯・コンセント・換気・空調 プロット図　S=1/50')
notes(sh, 800, 10800, COMMON_NOTES + [
    '',
    '■ 2F プロット概要',
    '・照明: 照明プランより C×3, E×7, I×1',
    '・一般コンセント 8個 (2回路: L-1-13 / L-1-14)',
    '・エアコン AC-6 GV5626S(1φ200V) / AC-7 GV3626(1φ100V)',
    '　空調プラン(三菱 2026.10.16)の位置による',
    '・換気: VD-3 / TF-3 / 給気グリル×2 (換気機種選定書による)',
    '・非常用照明・誘導灯は提案 (所轄協議要)',
    '・スイッチ記号の英字は器具・換気扇の英字と対応 (3:3路)'])
cad.title_block(sh, 600, 600, 'E-02', '2F 設備プロット図')
save(sh, 'E-02_2F_設備プロット図')

# ---------------- E-03
sh = cad.Sheet()
GP.plot_1f(sh, b1, with_checks=False)
W.wire_lighting(sh, 1)
W.risers(sh, 1)
retitle(sh, '1階平面図', '1階 電灯設備配線図　S=1/50')
y = cir_table(sh, 650, 10900, ['L-1-1', 'L-1-2', 'L-1-3', 'L-1-24'])
notes(sh, 650, y - 100, COMMON_NOTES + ['・換気扇は同系統照明回路', '・非常灯/誘導灯は専用回路L-1-24', '　(他回路と共用しない・非点滅)',
                                         '・階段H(1F)/I(2F)はL-1-3 3路', '■ 2F立上り', '　' + W.RISER_LIST[:24], '　' + W.RISER_LIST[24:], '　予備L-1-20〜23 PF22×4空配管'])
cad.title_block(sh, 600, 600, 'E-03', '1F 電灯設備配線図')
save(sh, 'E-03_1F_電灯設備配線図')

# ---------------- E-04
sh = cad.Sheet()
GP.plot_1f(sh, b1, with_checks=False)
W.wire_outlets(sh, 1)
W.wire_power(sh)
W.wire_link(sh, 1)
W.risers(sh, 1)
retitle(sh, '1階平面図', '1階 コンセント・動力設備配線図　S=1/50')
y = cir_table(sh, 650, 10900, ['L-1-5', 'L-1-6', 'L-1-7', 'L-1-8', 'L-1-9', 'L-1-10', 'L-1-11', 'L-1-12', 'L-1-15',
                                'L-1-16', 'L-1-19', 'P-1-1', 'P-1-2', 'P-1-3', 'P-1-4'])
notes(sh, 650, y - 60, ['■ 特記', '・厨房コンセントは各専用回路(ELB)', '・動力は室外機電源(内外連絡線で室内機へ)',
                        '・室外機・いけすに手元開閉器', '・2F立上り:' + W.RISER_LIST[:20], '　' + W.RISER_LIST[20:], '・取付高さは凡例(E-08)参照'], 80)
cad.title_block(sh, 600, 600, 'E-04', '1F コンセント・動力設備配線図')
save(sh, 'E-04_1F_コンセント・動力設備配線図')

# ---------------- E-05
sh = cad.Sheet()
GP.plot_2f(sh, b2)
W.wire_lighting(sh, 2)
W.risers(sh, 2)
retitle(sh, '2階平面図', '2階 電灯設備配線図　S=1/50')
y = cir_table(sh, 800, 10800, ['L-1-3', 'L-1-24'])
notes(sh, 800, y - 100, COMMON_NOTES + ['・L-1-3/L-1-24 は1F L-1盤より階段横立上り', '・階段照明(1F:H / 2F:I)はL-1-3 3路(1F⇔2F渡りVVF1.6-3C)', '・非常灯/誘導灯は専用回路L-1-24'])
cad.title_block(sh, 600, 600, 'E-05', '2F 電灯設備配線図')
save(sh, 'E-05_2F_電灯設備配線図')

# ---------------- E-06
sh = cad.Sheet()
GP.plot_2f(sh, b2)
W.wire_outlets(sh, 2)
W.wire_link(sh, 2)
W.risers(sh, 2)
retitle(sh, '2階平面図', '2階 コンセント設備配線図　S=1/50')
y = cir_table(sh, 800, 10800, ['L-1-13', 'L-1-14', 'L-1-17', 'L-1-18'])
notes(sh, 800, y - 100, COMMON_NOTES + ['・2F予備 L-1-20〜23: PF22×4 空配管', '・EV専用 L-1-19 は1F側に設置'])
cad.title_block(sh, 600, 600, 'E-06', '2F コンセント設備配線図')
save(sh, 'E-06_2F_コンセント設備配線図')

# ---------------- E-07
sh = cad.Sheet()
frame(sh)
SC.sheet_panels(sh)
cad.title_block(sh, 16200, 600, 'E-07', '盤結線図・幹線系統図・負荷計算', 'NON')
save(sh, 'E-07_電灯盤・動力盤結線図・幹線系統図')

# ---------------- E-08
sh = cad.Sheet()
frame(sh)
SC.sheet_legend(sh, K)
cad.title_block(sh, 16200, 600, 'E-08', '凡例・照明器具表・機器姿図', 'NON')
save(sh, 'E-08_凡例・照明器具表・機器姿図')

# ---------------- M-01
MECH_SKIP = ('_1-0_', '_1-1_', '_0-1_Defpoints')
sh = cad.Sheet()
cad.copy_base(sh, b1, skip_layers=MECH_SKIP, skip=GP.old_ac1)
for a in D.AC1F:
    GP.ac_unit(sh, a, 1)
GP.lay(sh, 'FAN')
for f in D.FAN1F:
    sh.text((f['x'] + 190, f['y'] - 260), f['id'], 95)
M.ducts(sh, 1)
M.piping(sh, 1)
retitle(sh, '1階平面図', '1階 換気ダクト・空調冷媒/ドレン配管図　S=1/50')
sh.L('M-注記', 7)
sh.text((600, 11000), '※空調・換気機器表は M-02 に記載', 95)
cad.title_block(sh, 600, 600, 'M-01', '1F 換気ダクト・空調配管図')
M.mech_notes(sh, 600, 10600, wrap=19)
save(sh, 'M-01_1F_換気ダクト・空調冷媒ドレン配管図')

# ---------------- M-02
sh = cad.Sheet()
cad.copy_base(sh, b2)
for f in D.FAN2F:
    GP.fan(sh, f)
for g in D.GRILLE2F:
    GP.grille(sh, g[0], g[1])
for a in D.AC2F:
    GP.ac_unit(sh, a, 2)
M.ducts(sh, 2)
M.piping(sh, 2)
retitle(sh, '2階平面図', '2階 換気ダクト・空調冷媒/ドレン配管図　S=1/50')
y = M.equip_table(sh, 12, 800, 10900)
M.mech_notes(sh, 800, y - 300)
cad.title_block(sh, 600, 600, 'M-02', '2F 換気ダクト・空調配管図')
save(sh, 'M-02_2F_換気ダクト・空調冷媒ドレン配管図')

for n, p, g in sheets:
    print(n, os.path.getsize(p))
print('L-1 main', K['mainL'], K['cabL'], 'P-1 main', K['mainP'], K['cabP'], 'tot', K['tot'], K['totP'], K['IR'], K['IT'], K['IP'])
