# -*- coding: utf-8 -*-
"""1階 飲食店・事務所 複合店舗  電灯・コンセント設備平面図（DXF / JW_CAD 用）を作る。

建築下図は source/heimenzu02.pdf（ベクタPDF, A3, 1/50）の線・文字を実寸に換算して取り込み、
その上に電気設備（照明器具・スイッチ・コンセント・分電盤・配線・幹線）を作図する。

座標系:
  本スクリプト内の座標は「表示座標 mm」= PDF 表示座標(pt, y 下向き) × 25.4/72 × 50。
  x は図面右向き、y は図面下向き。DXF へは Y = PH - y で反転して書き出す。
  モデル空間は実寸 mm・1:1（A3 1/50 → 用紙枠 21,000 × 14,850）。

作図ルール:
  - 配線は天井隠ぺい（実線）。配線同士の交差部は「縦方向（図面 Y 方向）の配線」を切断して表示（統一）。
  - 分電盤への配線は矢印（ホームラン）と回路番号で示す。
  - 同一室に複数の点滅区分がある場合は、スイッチと器具に ア・イ… を傍記。

出力:
  output/電灯コンセント設備平面図.dxf   (R12, cp932)
  output/quantities.json                 (数量拾い出し用の集計データ → make_quantity_xlsx.py)
"""
import json
import math
import os
import sys

import ezdxf

sys.path.insert(0, os.path.dirname(__file__))
from vecutil import dedupe, merge_collinear, text_runs  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "source", "heimenzu02_vec.json")
OUT = os.path.join(ROOT, "output")

SCALE = 50
K = 25.4 / 72 * SCALE                 # pt -> 実寸 mm
CH = 2400                             # 天井高
H_SW = 1300                           # スイッチ取付高
H_OUT = 300                           # コンセント取付高
GAP = 75                              # 交差部の切断長（片側）実寸 mm = 紙上 1.5mm

# ---------------------------------------------------------------- レイヤ
LAYERS = [  # (名前, 色)  JW_CAD の 1 グループ 16 枚に収める
    ("建築", 8), ("建築_寸法", 8), ("建築_文字", 8), ("図枠", 7), ("表題欄", 7),
    ("照明器具", 6), ("スイッチ", 6), ("コンセント", 5), ("分電盤", 1),
    ("配線_電灯", 3), ("配線_コンセント", 4), ("配線_2階予備", 30), ("幹線", 1),
    ("傍記", 7), ("凡例", 7), ("注記", 7),
]

vec = json.load(open(SRC, encoding="utf-8"))
PW_pt, PH_pt = vec["size_pt"]
PH = PH_pt * K


def T(x, y):
    """表示座標 -> DXF 座標"""
    return (round(x, 2), round(PH - y, 2))


doc = ezdxf.new("R12", setup=True)
doc.encoding = "cp932"
doc.header["$LTSCALE"] = SCALE
doc.styles.new("JP", dxfattribs={"font": "msgothic.ttf"})
for n, c in LAYERS:
    doc.layers.new(n, dxfattribs={"color": c, "linetype": "CONTINUOUS"})
ms = doc.modelspace()


def line(lay, p, q, color=None):
    a = {"layer": lay}
    if color is not None:
        a["color"] = color
    ms.add_line(T(*p), T(*q), dxfattribs=a)


def circle(lay, c, r):
    ms.add_circle(T(*c), r, dxfattribs={"layer": lay})


def arc_disp(lay, c, r, a0, a1):
    """表示座標の角度 a0->a1 (度, y 下向きで時計回りが正) の円弧"""
    ms.add_arc(T(*c), r, (-a1) % 360, (-a0) % 360, dxfattribs={"layer": lay})


def solid(lay, pts):
    p = [T(*q) for q in pts]
    if len(p) == 3:
        p.append(p[2])
    # R12 SOLID の頂点順は 1,2,4,3
    ms.add_solid([p[0], p[1], p[3], p[2]], dxfattribs={"layer": lay})


def fill_circle(lay, c, r, a0=0, a1=360, n=12):
    """塗りつぶし円（扇形）。表示座標の角度 a0..a1"""
    cx, cy = c
    step = (a1 - a0) / n
    for i in range(n):
        t0 = math.radians(a0 + step * i)
        t1 = math.radians(a0 + step * (i + 1))
        solid(lay, [(cx, cy), (cx + r * math.cos(t0), cy + r * math.sin(t0)),
                    (cx + r * math.cos(t1), cy + r * math.sin(t1))])


def text(lay, x, y, s, h=100, align="BL", rot=0):
    """align: 1文字目=縦(T/M/B), 2文字目=横(L/C/R)。座標は表示座標。"""
    va = {"T": "TOP", "M": "MIDDLE", "B": "BOTTOM"}[align[0]]
    ha = {"L": "LEFT", "C": "CENTER", "R": "RIGHT"}[align[1]]
    t = ms.add_text(s, dxfattribs={"layer": lay, "height": h, "style": "JP", "rotation": rot})
    t.set_placement(T(x, y), align=ezdxf.enums.TextEntityAlignment[f"{va}_{ha}"])
    return t


def rect(lay, x0, y0, x1, y1):
    line(lay, (x0, y0), (x1, y0))
    line(lay, (x1, y0), (x1, y1))
    line(lay, (x1, y1), (x0, y1))
    line(lay, (x0, y1), (x0, y0))


# ---------------------------------------------------------------- 建築下図の取り込み
TB = (17307, 13049, 20508, 14349)          # 表題欄（表示 mm）


def inside(b, r):
    return b[0] >= r[0] - 1 and b[1] >= r[1] - 1 and b[2] <= r[2] + 1 and b[3] <= r[3] + 1


def arch_layer(b, is_text=False):
    if inside(b, TB):
        return "表題欄"
    if inside(b, (18400, 1000, 19700, 2100)):            # 方位
        return "図枠"
    x0, y0, x1, y1 = b
    if (x1 - x0 > 19000 and (y0 < 510 or y0 > 14340)) or (y1 - y0 > 13000 and (x0 < 520 or x0 > 20490)):
        return "図枠"
    # 寸法列（上・下・左・右）
    if y1 <= 1250 or (y0 >= 13700 and x1 < 17000) or x1 <= 1000 or (x0 >= 16800 and x1 <= 17000):
        return "建築_寸法"
    return "建築_文字" if is_text else "建築"


def import_arch():
    lines = merge_collinear(dedupe(vec["lines"]))
    for x0, y0, x1, y1, w in lines:
        p, q = (x0 * K, y0 * K), (x1 * K, y1 * K)
        b = (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
        line(arch_layer(b), p, q)
    for cx, cy, r, a0, sw, w in vec["arcs"]:
        c, rr = (cx * K, cy * K), r * K
        b = (c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr)
        lay = arch_layer(b)
        a_s, a_e = math.degrees(a0), math.degrees(a0 + sw)
        arc_disp(lay, c, rr, min(a_s, a_e), max(a_s, a_e))
    for cx, cy, r, w in vec["circles"]:
        circle(arch_layer((cx * K - r * K, cy * K - r * K, cx * K + r * K, cy * K + r * K)),
               (cx * K, cy * K), r * K)
    for s, o, size, rot, bb in text_runs(vec["texts"], {}):
        b = [v * K for v in bb]
        lay = arch_layer(b, True)
        if lay == "表題欄":
            continue                                # 表題欄の文字は新しく書き直す
        ms.add_text(s, dxfattribs={"layer": lay, "height": round(size * K, 1),
                                   "rotation": round(rot, 3) % 360, "style": "JP",
                                   "insert": T(o[0] * K, o[1] * K)})


import_arch()

# ---------------------------------------------------------------- 記号
DL_R, SW_R, OUT_R, BL_L, BL_W = 110, 60, 90, 1250, 230
DEV = {}           # id -> dict


def add_dev(i, kind, x, y, **kw):
    d = dict(id=i, kind=kind, x=x, y=y, **kw)
    DEV[i] = d
    return d


def extent(d, direction):
    """機器中心から direction ('L','R','U','D') 方向の記号外形までの距離"""
    k = d["kind"]
    if k == "DL":
        return DL_R
    if k == "SW":
        return SW_R
    if k == "OUT":
        return OUT_R
    if k == "BL":
        along = d["axis"] == "h"
        if direction in "LR":
            return BL_L / 2 if along else BL_W / 2
        return BL_W / 2 if along else BL_L / 2
    if k == "PNL":
        return 0
    if k == "RISER":
        return 80
    return 0


def draw_dev(d):
    k, x, y = d["kind"], d["x"], d["y"]
    if k == "DL":                                    # 埋込器具（ダウンライト）
        circle("照明器具", (x, y), DL_R)
        text("照明器具", x, y, "DL", 75, "MC")
    elif k == "BL":                                  # 蛍光灯形（LEDベースライト）
        hl, hw = (BL_L / 2, BL_W / 2) if d["axis"] == "h" else (BL_W / 2, BL_L / 2)
        rect("照明器具", x - hl, y - hw, x + hl, y + hw)
        circle("照明器具", (x, y), 55)
    elif k == "SW":                                  # 点滅器
        circle("スイッチ", (x, y), SW_R)
        fill_circle("スイッチ", (x, y), SW_R)
        if d.get("sub"):
            text("スイッチ", x + 70, y + 40, d["sub"], 80, "TL")
    elif k == "OUT":                                 # コンセント（壁側を塗る）
        circle("コンセント", (x, y), OUT_R)
        a = {"U": 180, "R": 270, "D": 0, "L": 90}[d["wall"]]   # 壁側半円の開始角（表示座標）
        fill_circle("コンセント", (x, y), OUT_R, a, a + 180, 8)
    elif k == "PNL":                                 # 分電盤
        x0, y0, x1, y1 = d["box"]
        rect("分電盤", x0, y0, x1, y1)
        line("分電盤", (x0, y1), (x1, y0))
        solid("分電盤", [(x0, y1), (x1, y0), (x1, y1)])
    elif k == "RISER":                               # 立上り
        circle("配線_2階予備", (x, y), 80)
        circle("配線_2階予備", (x, y), 25)
        p, q = (x + 57, y - 57), (x + 260, y - 260)
        line("配線_2階予備", p, q)
        arrow("配線_2階予備", p, q, 90)


def arrow(lay, p, q, size=110):
    """p->q の線の q 端に塗り矢じり"""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    b = (q[0] - ux * size, q[1] - uy * size)
    w = size * 0.35
    solid(lay, [q, (b[0] - uy * w, b[1] + ux * w), (b[0] + uy * w, b[1] - ux * w)])


# ---------------------------------------------------------------- 配線
WIRES = []         # dict(layer, pts, n, circuit, cable)
HOMERUNS = []      # dict(layer, p, q, label, circuit)


def P(v):
    return (DEV[v]["x"], DEV[v]["y"]) if isinstance(v, str) else v


def wire(layer, circuit, *pts, n=2, cable=None):
    """pts: 機器 id または座標。端が機器 id なら記号外形で切り詰める。直交折れ線のみ。"""
    raw = [P(v) for v in pts]
    tr = list(raw)
    for end, nb in ((0, 1), (-1, -2)):
        v = pts[end]
        if isinstance(v, str):
            a, b = raw[end], raw[nb]
            if abs(a[0] - b[0]) < 1e-6:
                dirn = "D" if b[1] > a[1] else "U"
            else:
                dirn = "R" if b[0] > a[0] else "L"
            e = extent(DEV[v], dirn)
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            tr[end] = (a[0] + (b[0] - a[0]) * e / L, a[1] + (b[1] - a[1]) * e / L)
    for i in range(len(raw) - 1):
        assert abs(raw[i][0] - raw[i + 1][0]) < 1e-6 or abs(raw[i][1] - raw[i + 1][1]) < 1e-6, \
            ("直交でない配線", circuit, pts)
    WIRES.append(dict(layer=layer, pts=tr, raw=raw, n=n, circuit=circuit, cable=cable,
                      ends=[pts[0], pts[-1]]))


def hv(layer, circuit, a, b, **kw):
    pa, pb = P(a), P(b)
    wire(layer, circuit, a, (pb[0], pa[1]), b, **kw)


def vh(layer, circuit, a, b, **kw):
    pa, pb = P(a), P(b)
    wire(layer, circuit, a, (pa[0], pb[1]), b, **kw)


def homerun(layer, circuit, dev, dirn, length, label=None, cable=None, lpos=None):
    d = DEV[dev]
    e = extent(d, dirn)
    ux, uy = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}[dirn]
    p = (d["x"] + ux * e, d["y"] + uy * e)
    q = (p[0] + ux * length, p[1] + uy * length)
    HOMERUNS.append(dict(layer=layer, p=p, q=q, label=label or circuit, circuit=circuit,
                         dev=dev, cable=cable, lpos=lpos, dirn=dirn))


# ================================================================ 設計内容
# ---- 室の範囲（照度計算用・表示 mm、壁内法）
ROOMS = {
    "座敷（客席）": dict(rects=[(6198, 1850, 12077, 6780)], E=200, h_work=0, fix="DL", M=0.77),
    "客席（入口・レジ付近）": dict(rects=[(2358, 7704, 6098, 13139)], E=200, h_work=0, fix="DL", M=0.77),
    "客席（カウンター・通路）": dict(rects=[(6198, 8249, 12077, 10658), (6198, 6850, 8588, 8249),
                                   (10677, 7299, 11637, 8249)], E=200, h_work=0, fix="DL", M=0.77),
    "客席（ボックス席）": dict(rects=[(12177, 8249, 16067, 13139)], minus=[(15177, 8249, 16067, 9199)],
                          E=200, h_work=0, fix="DL", M=0.77),
    "便所（女子）": dict(rects=[(9184, 7299, 10577, 8149)], E=200, h_work=0, fix="DL", M=0.77),
    "便所（男子）": dict(rects=[(13679, 7299, 15078, 8149)], E=200, h_work=0, fix="DL", M=0.77),
    "厨房": dict(rects=[(6198, 10759, 12077, 13139)], E=500, h_work=850, fix="BL", M=0.69),
    "倉庫": dict(rects=[(3268, 1850, 6098, 7250)], E=200, h_work=0, fix="BL", M=0.77),
    "事務所": dict(rects=[(12177, 1850, 16067, 7200)], E=750, h_work=850, fix="BL", M=0.77),
}
FIX = {
    "DL": dict(name="LEDダウンライト φ100 埋込 1,000lm 電球色", lm=1000, W=8.5,
               U=[(0.0, 0.30), (0.6, 0.53), (0.8, 0.60), (1.0, 0.66), (1.25, 0.71), (1.5, 0.75),
                  (2.0, 0.80), (2.5, 0.83), (3.0, 0.86)]),
    "BL": dict(name="LEDベースライト 40形 逆富士 直付 6,900lm 昼白色", lm=6900, W=45,
               U=[(0.0, 0.25), (0.6, 0.45), (0.8, 0.52), (1.0, 0.58), (1.25, 0.63), (1.5, 0.67),
                  (2.0, 0.73), (2.5, 0.77), (3.0, 0.80)]),
}

# ---- 分電盤
add_dev("P1", "PNL", 6000, 4300, box=(5900, 3950, 6098, 4650), name="L-1", room="倉庫")
add_dev("P2", "PNL", 12650, 7100, box=(12300, 7000, 13000, 7200), name="L-2", room="事務所")


def lights(prefix, kind, pts, room, group=None, circuit=None, axis="h"):
    ids = []
    for i, (x, y) in enumerate(pts, 1):
        d = add_dev(f"{prefix}{i}", kind, x, y, room=room, group=group, circuit=circuit, axis=axis)
        ids.append(d["id"])
    return ids


def sw(i, x, y, room, group=None, sub=None, circuit=None, lab_pos=None):
    return add_dev(i, "SW", x, y, room=room, group=group, sub=sub, circuit=circuit, lab_pos=lab_pos)


def outlet(i, x, y, wall, room, spec, circuit, note=None, lab=None, labpos=None):
    return add_dev(i, "OUT", x, y, wall=wall, room=room, spec=spec, circuit=circuit, note=note, lab=lab,
                   labpos=labpos)


# ======== 店舗 L-1
# --- L1-2 電灯（客席・座敷・倉庫）
C = lights("c", "DL", [(x, y) for y in (8610, 10421, 12233) for x in (2981, 4228, 5475)],
           "客席（入口・レジ付近）", "ア", "L1-2")          # c1..c9 (行ごと)
E = lights("e", "DL", [(7100, 8900), (9050, 8900), (11000, 8900),
                       (7100, 10080), (9050, 10080), (11000, 10080),
                       (7100, 7800), (8150, 7800), (11000, 7800)],
           "客席（カウンター・通路）", "イ", "L1-2")
D = lights("d", "DL", [(12900, 8900), (14400, 8900), (12900, 10330), (14600, 10330), (15550, 10330),
                       (12900, 12244), (14600, 12244), (15550, 12244)],
           "客席（ボックス席）", "ウ", "L1-2")
Z = {}          # 4列×3行。テーブル1側(エ)・テーブル2側(オ)で点滅区分
for col, (x, g) in enumerate(((6895, "エ"), (8390, "エ"), (9885, "オ"), (11380, "オ")), 1):
    Z[col] = lights(f"z{col}", "DL", [(x, y) for y in (2633, 4300, 5967)], "座敷（客席）", g, "L1-2")
S = lights("s", "BL", [(4683, 3200), (4683, 5900)], "倉庫", None, "L1-2", axis="v")

sw("swA", 6010, 9830, "客席", "ア", circuit="L1-2", lab_pos="UL")
sw("swI", 6010, 10080, "客席", "イ", circuit="L1-2", lab_pos="L")
sw("swU", 6010, 10330, "客席", "ウ", circuit="L1-2", lab_pos="L")
sw("swE", 6290, 6950, "座敷（客席）", "エ", circuit="L1-2", lab_pos="UR")
sw("swO", 6290, 7130, "座敷（客席）", "オ", circuit="L1-2", lab_pos="UR")
sw("swS", 6010, 6950, "倉庫", None, circuit="L1-2")

LW = "配線_電灯"
# ア 客席C
for a, b in (("c1", "c2"), ("c2", "c3"), ("c4", "c5"), ("c5", "c6"), ("c7", "c8"), ("c8", "c9"),
             ("c2", "c5"), ("c5", "c8")):
    wire(LW, "L1-2", a, b)
hv(LW, "L1-2", "swA", "c6")
# イ カウンター・通路
for a, b in (("e1", "e2"), ("e2", "e3"), ("e4", "e5"), ("e5", "e6"), ("e1", "e4"), ("e7", "e8"),
             ("e7", "e1"), ("e9", "e3")):
    wire(LW, "L1-2", a, b)
wire(LW, "L1-2", "swI", "e4")
# ウ ボックス席
wire(LW, "L1-2", "d1", "d2")
wire(LW, "L1-2", "d1", "d3")
wire(LW, "L1-2", "d3", "d6")
wire(LW, "L1-2", "d3", "d4")
wire(LW, "L1-2", "d4", "d5")
wire(LW, "L1-2", "d6", "d7")
wire(LW, "L1-2", "d7", "d8")
wire(LW, "L1-2", "swU", "d3")
# 群間の渡り
vh(LW, "L1-2", "c3", "e1")                       # 客席C -> カウンター
wire(LW, "L1-2", "e3", "d1")                     # カウンター -> ボックス席
wire(LW, "L1-2", "c3", (5475, 7100), (4683, 7100), "s2")   # 客席C -> 倉庫
# 倉庫
wire(LW, "L1-2", "s1", "s2")
wire(LW, "L1-2", "swS", (5200, 6950), (5200, 5900), "s2")
# 座敷
for col in (1, 2, 3, 4):
    ids = Z[col]
    for a, b in zip(ids, ids[1:]):
        wire(LW, "L1-2", a, b)
wire(LW, "L1-2", "z11", "z21")
wire(LW, "L1-2", "z21", "z31")
wire(LW, "L1-2", "z31", "z41")
wire(LW, "L1-2", "s1", (4683, 2300), (6895, 2300), "z11")   # 倉庫 -> 座敷
hv(LW, "L1-2", "swE", "z13")
hv(LW, "L1-2", "swO", "z33")
homerun(LW, "L1-2", "s1", "R", 700)

# --- L1-1 電灯（水回り：厨房・便所）
K_ = lights("k", "BL", [(7178, 11600), (9137, 11600), (11096, 11600)], "厨房", "キ", "L1-1", axis="h")
sw("swK1", 6290, 11600, "厨房", "キ", sub="3", circuit="L1-1", lab_pos="UR")
sw("swK2", 11985, 11600, "厨房", "キ", sub="3", circuit="L1-1", lab_pos="UL")
wire(LW, "L1-1", "swK1", "k1", n=3)
wire(LW, "L1-1", "k1", "k2", n=4)
wire(LW, "L1-1", "k2", "k3", n=4)
wire(LW, "L1-1", "k3", "swK2", n=3)
homerun(LW, "L1-1", "k1", "U", 300)
lights("wf", "DL", [(10050, 7950)], "便所（女子）", None, "L1-1")
lights("wm", "DL", [(14450, 7420)], "便所（男子）", None, "L1-1")
sw("swWF", 10050, 8340, "便所（女子）", sub="L", circuit="L1-1")
sw("swWM", 14650, 8340, "便所（男子）", sub="L", circuit="L1-1")
wire(LW, "L1-1", "wf1", "swWF")
hv(LW, "L1-1", "wm1", "swWM")
homerun(LW, "L1-1", "wf1", "L", 450)
homerun(LW, "L1-1", "wm1", "L", 290, lpos="L")

# --- コンセント
LO = "配線_コンセント"
GEN2 = dict(sym="2", desc="2口コンセント 15A125V", cable="VVF2.0-2C")
GEN2E = dict(sym="2E", desc="2口コンセント 接地極付 15A125V", cable="VVF2.0-3C")
E1 = dict(sym="EET", desc="コンセント 接地極付接地端子付 15A125V（温水洗浄便座用）", cable="VVF2.0-3C")
D100 = dict(sym="E20A", desc="コンセント 接地極付 20A125V（専用）", cable="VVF2.0-3C")
D200 = dict(sym="E20A250V", desc="コンセント 接地極付 20A250V（専用）", cable="VVF2.0-3C")
DWP = dict(sym="EWP", desc="防雨形コンセント 接地極付 15A125V（専用）", cable="VVF2.0-3C")
OA = dict(sym="2E", desc="2口コンセント 接地極付 15A125V（OA専用）", cable="VVF2.0-3C")

# L1-3 一般（客席 入口付近・カウンター）
outlet("oc1", 2440, 9500, "L", "客席（入口・レジ付近）", GEN2, "L1-3")
outlet("oc2", 6010, 11300, "R", "客席（入口・レジ付近）", GEN2, "L1-3")
outlet("oe1", 7600, 9680, "D", "客席（カウンター・通路）", GEN2, "L1-3")
outlet("oe2", 10500, 9680, "D", "客席（カウンター・通路）", GEN2, "L1-3")
vh(LO, "L1-3", "oc1", "oc2")
wire(LO, "L1-3", "oe1", "oe2")
homerun(LO, "L1-3", "oc1", "U", 500)
homerun(LO, "L1-3", "oe1", "U", 480)
# L1-4 一般（倉庫・座敷・ボックス席）
outlet("os1", 3355, 4100, "L", "倉庫", GEN2, "L1-4")
outlet("os2", 5500, 1940, "U", "倉庫", GEN2, "L1-4")
outlet("oz1", 6290, 5300, "L", "座敷（客席）", GEN2, "L1-4")
outlet("oz2", 11990, 5300, "R", "座敷（客席）", GEN2, "L1-4")
outlet("od1", 15980, 10950, "R", "客席（ボックス席）", GEN2, "L1-4")
outlet("od2", 15980, 12850, "R", "客席（ボックス席）", GEN2, "L1-4")
vh(LO, "L1-4", "os1", "os2")
wire(LO, "L1-4", "oz1", "oz2")
wire(LO, "L1-4", "od1", "od2")
homerun(LO, "L1-4", "os2", "R", 300)
homerun(LO, "L1-4", "oz1", "U", 420)
homerun(LO, "L1-4", "od1", "U", 420)
# L1-5 厨房 一般
outlet("ok1", 6290, 11100, "L", "厨房", GEN2E, "L1-5")
outlet("ok2", 9750, 10850, "U", "厨房", GEN2E, "L1-5")
hv(LO, "L1-5", "ok1", "ok2")
homerun(LO, "L1-5", "ok1", "U", 420)
# L1-6 便所（温水洗浄便座）
outlet("ow1", 10490, 7750, "R", "便所（女子）", E1, "L1-6")
outlet("ow2", 14990, 7950, "R", "便所（男子）", E1, "L1-6")
homerun(LO, "L1-6", "ow1", "D", 250)
homerun(LO, "L1-6", "ow2", "U", 300, lpos="L")
# L1-7〜11 厨房専用（機器未定）
for i, (x, spec) in enumerate(((6750, D100), (7500, D100), (8250, D100), (9000, D200), (11600, D200)), 1):
    outlet(f"ox{i}", x, 10850, "U", "厨房", spec, f"L1-{6 + i}", lab=f"専{i}")
    homerun(LO, f"L1-{6 + i}", f"ox{i}", "U", 300)
# L1-12 活イケス専用
outlet("oik", 3080, 6150, "R", "屋外（活イケス）", DWP, "L1-12", note="活イケス用")
homerun(LO, "L1-12", "oik", "R", 560, lpos="UR")

# --- L1-13〜18 2階予備（6回路）
add_dev("R1", "RISER", 11400, 7450, room="階段")
wire("配線_2階予備", "L1-13〜18", (6000, 4650), (6000, 6500), (11400, 6500), "R1", n=0, cable="VVF2.0-3C×6")

# ======== 事務所 L-2
OL = lights("ol", "BL", [(x, y) for x in (15095, 13150) for y in (2650, 4350, 6050)], "事務所", None, "L2-1",
            axis="v")                  # ol1..3 = 窓側(ア), ol4..6 = 内側(イ)
for i in (1, 2, 3):
    DEV[f"ol{i}"]["group"] = "ア"
for i in (4, 5, 6):
    DEV[f"ol{i}"]["group"] = "イ"
sw("swOA", 15975, 6880, "事務所", "ア", circuit="L2-1", lab_pos="UL")
sw("swOI", 15975, 7080, "事務所", "イ", circuit="L2-1", lab_pos="UL")
for a, b in (("ol1", "ol2"), ("ol2", "ol3"), ("ol4", "ol5"), ("ol5", "ol6")):
    wire(LW, "L2-1", a, b)
wire(LW, "L2-1", "ol4", "ol1")
hv(LW, "L2-1", "swOA", "ol3")
hv(LW, "L2-1", "swOI", "ol6")
homerun(LW, "L2-1", "ol6", "L", 250)
outlet("og1", 13700, 1940, "U", "事務所", GEN2, "L2-2")
outlet("og2", 14600, 1940, "U", "事務所", GEN2, "L2-2")
wire(LO, "L2-2", "og1", "og2")
homerun(LO, "L2-2", "og1", "D", 300, lpos="L")
for i, (x, y, wall, dirn, ln) in enumerate(((15975, 2050, "R", "L", 450), (15975, 4500, "R", "L", 450),
                                            (12270, 3500, "L", "D", 500), (12270, 5200, "L", "D", 500)), 1):
    outlet(f"oo{i}", x, y, wall, "事務所", OA, f"L2-{2 + i}", lab=f"専{i}")
    homerun(LO, f"L2-{2 + i}", f"oo{i}", dirn, ln)

# ---- 幹線
FEEDERS = [
    dict(name="店舗 L-1", cable="ニュースラットケーブル 14sq×3", pts=[(6000, 1250), (6000, 3950)]),
    dict(name="事務所 L-2", cable="ニュースラットケーブル 8sq×3", pts=[(12700, 1250), (12700, 7000)]),
]
for f in FEEDERS:
    WIRES.append(dict(layer="幹線", pts=f["pts"], raw=f["pts"], n=0, circuit=f["name"], cable=f["cable"],
                      ends=[None, None]))

# ================================================================ 交差処理（縦線を切断）


def segments():
    out = []
    for wi, w in enumerate(WIRES):
        for a, b in zip(w["pts"], w["pts"][1:]):
            out.append((wi, a, b))
    for hi, h in enumerate(HOMERUNS):
        out.append((-1 - hi, h["p"], h["q"]))
    return out


def is_v(a, b):
    return abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) > 1e-6


def is_h(a, b):
    return abs(a[1] - b[1]) < 1e-6 and abs(a[0] - b[0]) > 1e-6


SEGS = segments()
CUTS = {}           # 縦線セグメント index -> [y...]
for i, (wi, a, b) in enumerate(SEGS):
    if not is_v(a, b):
        continue
    x = a[0]
    ylo, yhi = sorted((a[1], b[1]))
    for j, (wj, c, d) in enumerate(SEGS):
        if not is_h(c, d):
            continue
        y = c[1]
        xlo, xhi = sorted((c[0], d[0]))
        if xlo + 1 < x < xhi - 1 and ylo + 1 < y < yhi - 1:
            CUTS.setdefault(i, []).append(y)

CROSS_LOG = []


def draw_seg_with_cuts(lay, i, a, b):
    ys = CUTS.get(i)
    if not ys:
        line(lay, a, b)
        return
    x = a[0]
    ylo, yhi = sorted((a[1], b[1]))
    pieces, cur = [], ylo
    for y in sorted(ys):
        CROSS_LOG.append((lay, x, y))
        pieces.append((cur, y - GAP))
        cur = y + GAP
    pieces.append((cur, yhi))
    for p0, p1 in pieces:
        if p1 - p0 > 5:
            line(lay, (x, p0), (x, p1))


def slashes(lay, a, b, n):
    """本数表示（斜線）を区間中央に n 本"""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    horiz = is_h(a, b)
    for k in range(n):
        o = (k - (n - 1) / 2) * 55
        if horiz:
            line(lay, (mx + o - 45, my + 80), (mx + o + 45, my - 80))
        else:
            line(lay, (mx - 80, my + o + 45), (mx + 80, my + o - 45))


si = 0
for wi, w in enumerate(WIRES):
    for a, b in zip(w["pts"], w["pts"][1:]):
        draw_seg_with_cuts(w["layer"], si, a, b)
        si += 1
    if w["n"] >= 3:
        segs = list(zip(w["pts"], w["pts"][1:]))
        a, b = max(segs, key=lambda s: math.hypot(s[1][0] - s[0][0], s[1][1] - s[0][1]))
        slashes(w["layer"], a, b, w["n"])
for h in HOMERUNS:
    draw_seg_with_cuts(h["layer"], si, h["p"], h["q"])
    arrow(h["layer"], h["p"], h["q"])
    si += 1

# ================================================================ 機器・傍記
for d in DEV.values():
    draw_dev(d)

LAB_H = 100


def lab_offset(pos, r):
    o = r + 40
    return {"UR": (o, -o, "BL"), "UL": (-o, -o, "BR"), "DR": (o, o, "TL"), "DL": (-o, o, "TR"),
            "L": (-o - 20, 0, "MR"), "R": (o + 20, 0, "ML"), "U": (0, -o, "BC"), "D": (0, o, "TC")}[pos]


# 器具の点滅区分記号（ア・イ…）: 同一室に複数区分がある場合のみ
ROOM_GROUPS = {}
for d in DEV.values():
    if d["kind"] in ("DL", "BL") and d.get("group"):
        ROOM_GROUPS.setdefault(d["room"], set()).add(d["group"])
ROOM_GROUPS["客席（入口・レジ付近）"] = ROOM_GROUPS["客席（カウンター・通路）"] = \
    ROOM_GROUPS["客席（ボックス席）"] = {"ア", "イ", "ウ"}   # 一体の客席空間
ROOM_GROUPS["厨房"] = {"キ"}                                   # 3路で 2 箇所点滅のため明示

for d in DEV.values():
    g = d.get("group")
    if d["kind"] in ("DL", "BL") and g and g in ROOM_GROUPS.get(d["room"], ()):
        if d["kind"] == "DL":
            text("傍記", d["x"] + 85, d["y"] - 85, g, LAB_H, "BL")
        else:
            if d["axis"] == "h":
                text("傍記", d["x"] + BL_L / 2 - 60, d["y"] - BL_W / 2 - 30, g, LAB_H, "BR")
            else:
                text("傍記", d["x"] + BL_W / 2 + 40, d["y"] - BL_L / 2 + 20, g, LAB_H, "TL")
    if d["kind"] == "SW" and g:
        dx, dy, al = lab_offset(d.get("lab_pos") or "UR", SW_R)
        text("傍記", d["x"] + dx, d["y"] + dy, g, LAB_H, al)
    if d["kind"] == "OUT":
        s = d["spec"]["sym"]
        w = d["wall"]
        # 傍記は壁と反対側
        if d.get("labpos") == "D":
            text("傍記", d["x"], d["y"] + OUT_R + 30, s, 80, "TC")
        elif w == "U" and d.get("lab"):
            text("傍記", d["x"] + OUT_R + 20, d["y"] - 10, s, 80, "TL")
            text("傍記", d["x"] + OUT_R + 20, d["y"] + 85, d["lab"], 80, "TL")
        elif w == "U":
            text("傍記", d["x"], d["y"] + OUT_R + 30, s, 80, "TC")
        elif w == "D":
            text("傍記", d["x"], d["y"] - OUT_R - 30, s, 80, "BC")
        elif w == "L":
            text("傍記", d["x"] + OUT_R + 30, d["y"] + 20, s, 80, "TL")
            if d.get("lab"):
                text("傍記", d["x"] + OUT_R + 30, d["y"] - 20, d["lab"], 80, "BL")
        else:
            text("傍記", d["x"] - OUT_R - 30, d["y"] + 20, s, 80, "TR")
            if d.get("lab"):
                text("傍記", d["x"] - OUT_R - 30, d["y"] - 20, d["lab"], 80, "BR")
        if d.get("note"):
            nx = d["x"] + (OUT_R + 30 if w in "LU" else -(OUT_R + 30))
            text("傍記", nx, d["y"] - OUT_R - 20, d["note"], 80, "BL" if w in "LU" else "BR")

# ホームランの回路番号
for h in HOMERUNS:
    q, dirn = h["q"], h["dirn"]
    lab = h["label"]
    if h.get("lpos") == "L":
        text("傍記", q[0] - 60, q[1], lab, 85, "MR")
    elif h.get("lpos") == "UR" or dirn == "R":
        text("傍記", q[0] - 40, q[1] - 70, lab, 85, "BR")
    elif dirn == "L":
        text("傍記", q[0] + 40, q[1] - 70, lab, 85, "BL")
    elif dirn == "U":
        text("傍記", q[0] + 60, q[1] + 20, lab, 85, "TL")
    else:
        text("傍記", q[0] + 60, q[1] - 20, lab, 85, "BL")

# 分電盤名・2階予備・幹線の傍記
text("傍記", 5880, 4300, "L-1", 130, "MR")
text("傍記", 5880, 4480, "店舗用分電盤", 85, "MR")
text("傍記", 12600, 6930, "L-2", 130, "BR")
text("傍記", 12600, 6760, "分電盤", 85, "BR")
text("傍記", 12600, 6640, "事務所用", 85, "BR")
text("傍記", 10780, 6440, "立上り 2階予備回路 L1-13〜18（6回路）", 85, "BL")
text("傍記", 8800, 6460, "2階予備 VVF2.0-3C×6", 80, "BC")
text("傍記", 6230, 1480, "幹線 ニュースラットケーブル 14sq×3（引込点より・別途）", 85, "BL")
text("傍記", 12780, 1480, "幹線 ニュースラットケーブル 8sq×3（引込点より・別途）", 85, "BL")
for f in FEEDERS:
    p, q = f["pts"][1], f["pts"][0]
    arrow("幹線", p, q, 130)

# 室名（原図に無い用途名 = 質疑回答による）
for s, x, y in (("座 敷（客席）", 9137, 3450), ("客 席", 4228, 9500), ("客 席", 9050, 9350),
                ("厨 房", 8100, 12150), ("客 席", 13700, 9700)):
    text("注記", x, y, s, 160, "MC")

# ================================================================ 凡例・注記
LX, LY = 17150, 2300


def legend():
    y = LY
    text("凡例", LX, y, "凡　例", 180, "BL")
    line("凡例", (LX, y + 60), (20350, y + 60))
    y += 330
    sx = LX + 250
    tx = LX + 800

    def row(draw, s1, s2=None):
        nonlocal y
        draw(sx, y)
        text("凡例", tx, y - 10, s1, 95, "BL")
        if s2:
            text("凡例", tx, y + 25, s2, 80, "TL")
        y += 400 if s2 else 300

    def dl(x, yy):
        circle("凡例", (x, yy), DL_R)
        text("凡例", x, yy, "DL", 75, "MC")

    def bl(x, yy):
        rect("凡例", x - 300, yy - 60, x + 300, yy + 60)
        circle("凡例", (x, yy), 40)

    def swd(sub):
        def f(x, yy):
            fill_circle("凡例", (x, yy), SW_R)
            circle("凡例", (x, yy), SW_R)
            if sub:
                text("凡例", x + 70, yy + 40, sub, 80, "TL")
        return f

    def outd(sub):
        def f(x, yy):
            circle("凡例", (x, yy), OUT_R)
            fill_circle("凡例", (x, yy), OUT_R, 90, 270, 8)
            text("凡例", x + OUT_R + 30, yy + 20, sub, 75, "TL")
        return f

    def pnl(x, yy):
        rect("凡例", x - 250, yy - 80, x + 250, yy + 80)
        line("凡例", (x - 250, yy + 80), (x + 250, yy - 80))
        solid("凡例", [(x - 250, yy + 80), (x + 250, yy - 80), (x + 250, yy + 80)])

    def ln(lay_n=0):
        def f(x, yy):
            line("凡例", (x - 300, yy), (x + 300, yy))
            if lay_n:
                for k in range(lay_n):
                    o = (k - (lay_n - 1) / 2) * 55
                    line("凡例", (x + o - 45, yy + 80), (x + o + 45, yy - 80))
        return f

    def hr(x, yy):
        line("凡例", (x - 300, yy), (x + 250, yy))
        arrow("凡例", (x - 300, yy), (x + 250, yy))

    def riser(x, yy):
        circle("凡例", (x, yy), 80)
        circle("凡例", (x, yy), 25)
        line("凡例", (x + 57, yy - 57), (x + 220, yy - 220))
        arrow("凡例", (x + 57, yy - 57), (x + 220, yy - 220), 80)

    def cross(x, yy):
        line("凡例", (x - 300, yy), (x + 300, yy))
        line("凡例", (x, yy - 200), (x, yy - GAP))
        line("凡例", (x, yy + GAP), (x, yy + 200))

    row(dl, "LEDダウンライト φ100 埋込", "1,000lm 電球色 約8.5W")
    row(bl, "LEDベースライト 40形 逆富士", "直付 6,900lm 昼白色 約45W")
    row(swd(None), "片切スイッチ 15A", "FL+1,300")
    row(swd("3"), "3路スイッチ 15A", "FL+1,300")
    row(swd("L"), "確認表示灯内蔵スイッチ", "FL+1,300（便所）")
    row(outd("2"), "2口コンセント 15A125V", "FL+300")
    row(outd("2E"), "2口コンセント 接地極付", "FL+300")
    row(outd("EET"), "コンセント 接地極付接地端子付", "FL+300（温水洗浄便座用）")
    row(outd("E20A"), "専用コンセント 接地極付 20A125V", "FL+300（厨房 機器未定）")
    row(outd("E20A250V"), "専用コンセント 接地極付 20A250V", "FL+300（厨房 機器未定）")
    row(outd("EWP"), "防雨形コンセント 接地極付", "FL+300（屋外 活イケス用）")
    row(pnl, "分電盤", "L-1 店舗用 / L-2 事務所用")
    row(ln(), "天井隠ぺい配線", "電灯 VVF1.6-2C / コンセント VVF2.0-2C")
    row(ln(3), "同上 3本（数字＝電線本数）", "VVF1.6-3C　4本は VVF1.6-2C×2")
    row(hr, "分電盤へ（ホームラン）", "傍記＝盤名-回路番号")
    row(riser, "立上り（2階へ）")
    row(cross, "配線交差部", "縦方向（Y方向）の配線を切断して表示")
    row(lambda x, yy: text("凡例", x, yy, "ア", 100, "MC"), "点滅区分記号",
        "同記号のスイッチで点滅")
    return y


ly = legend()
NOTES = [
    "【特記】",
    "1. 天井高 CH=2,400",
    "2. 取付高さ（特記なき限り）",
    "   スイッチ FL+1,300 / コンセント FL+300",
    "3. 照度計算（光束法）",
    "   客席・座敷・便所 DL 床面200lx",
    "   倉庫200lx(床面) 厨房500lx・",
    "   事務所750lx(作業面FL+850)",
    "4. 厨房専用回路(専1〜5)は機器未定の",
    "   ため仮設定。機器確定後に電圧・",
    "   容量・形状・取付高さを確認",
    "5. 2階予備6回路は L-1 に確保し、",
    "   階段部で立上り(行先は2階計画後)",
    "6. 引込点・電力量計・弱電・空調・",
    "   換気扇・EV電源は別途",
]
yy = ly + 80
for s in NOTES:
    text("注記", LX, yy, s, 90, "BL")
    yy += 165

# ---------------------------------------------------------------- 表題欄（原図の枠線を使い、文字を書き直す）
TITLE = [("図名", "電灯・コンセント設備平面図"), ("縮尺", "1/50 (A3)"), ("単位", "mm"),
         ("原図", "平面図 heimenzu02 より作図"), ("作成", "2026-10-04")]
for i, (k, v) in enumerate(TITLE):
    yc = 13049 + 260 * i + 130
    text("表題欄", 17707, yc, k, 100, "MC")
    text("表題欄", 19308, yc, v, 100, "MC")

doc.saveas(os.path.join(OUT, "電灯コンセント設備平面図.dxf"))

# ================================================================ 数量拾い出し用データ
PANEL_XY = {"L1": (DEV["P1"]["x"], DEV["P1"]["y"]), "L2": (DEV["P2"]["x"], DEV["P2"]["y"])}


def seglen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def drop(dev_id):
    if not isinstance(dev_id, str):
        return 0
    k = DEV[dev_id]["kind"]
    return {"SW": CH - H_SW, "OUT": CH - H_OUT}.get(k, 0)


def cable_of(circuit, layer, n):
    if layer == "幹線":
        return None
    if layer == LW:
        return {2: "VVF1.6-2C", 3: "VVF1.6-3C", 4: "VVF1.6-2C×2"}[n]
    # コンセント回路: 回路の器具仕様で決める
    for d in DEV.values():
        if d["kind"] == "OUT" and d["circuit"] == circuit:
            return d["spec"]["cable"]
    return "VVF2.0-2C"


cable_runs = []      # (circuit, cable, 平面長, 立下り, 区分)
for w in WIRES:
    if w["layer"] in ("幹線", "配線_2階予備"):
        continue
    L = seglen(w["raw"])
    dr = sum(drop(e) for e in w["ends"])
    cable_runs.append(dict(circuit=w["circuit"], cable=cable_of(w["circuit"], w["layer"], w["n"]),
                           plan=L, drop=dr, kind="器具間"))
for h in HOMERUNS:
    pk = h["circuit"].split("-")[0]
    px, py = PANEL_XY[pk]
    d = DEV[h["dev"]]
    L = abs(d["x"] - px) + abs(d["y"] - py)        # 盤までの直交距離
    dr = drop(h["dev"]) + (CH - 1800)              # 器具側立下り + 盤側立下り(盤上端FL+1,800)
    cable_runs.append(dict(circuit=h["circuit"], cable=cable_of(h["circuit"], h["layer"], 2),
                           plan=L, drop=dr, kind="ホームラン"))
w2f = [w for w in WIRES if w["layer"] == "配線_2階予備"][0]
spare_len = seglen(w2f["raw"]) + (CH - 1800) + 3000          # 盤側立下り + 2階床上げ分(想定 3.0m)
feeders = []
for f in FEEDERS:
    feeders.append(dict(name=f["name"], cable=f["cable"], plan=seglen(f["pts"]), drop=CH - 1800))

devices = []
for d in DEV.values():
    e = dict(id=d["id"], kind=d["kind"], room=d.get("room"), circuit=d.get("circuit"), group=d.get("group"))
    if d["kind"] == "OUT":
        e["spec"] = d["spec"]["desc"]
        e["sym"] = d["spec"]["sym"]
    if d["kind"] == "SW":
        e["sub"] = d.get("sub")
        e["x"], e["y"] = d["x"], d["y"]
    devices.append(e)


def area(r):
    a = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in r["rects"])
    a -= sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in r.get("minus", []))
    return a / 1e6


def interp(tab, k):
    for (k0, u0), (k1, u1) in zip(tab, tab[1:]):
        if k <= k1:
            return u0 + (u1 - u0) * (k - k0) / (k1 - k0)
    return tab[-1][1]


calc = []
for name, r in ROOMS.items():
    x0, y0, x1, y1 = r["rects"][0]
    X, Y = (x1 - x0) / 1000, (y1 - y0) / 1000
    A = area(r)
    Hh = (CH - r["h_work"]) / 1000
    k = X * Y / (Hh * (X + Y))
    f = FIX[r["fix"]]
    U = interp(f["U"], k)
    Nreq = r["E"] * A / (f["lm"] * U * r["M"])
    N = sum(1 for d in DEV.values() if d["kind"] == r["fix"] and d.get("room") == name)
    Ecalc = N * f["lm"] * U * r["M"] / A
    calc.append(dict(room=name, X=X, Y=Y, A=round(A, 2), H=Hh, k=round(k, 2), fix=f["name"], lm=f["lm"],
                     U=round(U, 3), M=r["M"], E=r["E"], Nreq=round(Nreq, 2), N=N, Ecalc=round(Ecalc),
                     work="床面" if r["h_work"] == 0 else f"作業面 FL+{r['h_work']}"))

edges = [[e if isinstance(e, str) else None for e in w["ends"]] for w in WIRES if w["layer"] in (LW, LO)]
edges += [[h["dev"], "HOMERUN"] for h in HOMERUNS]
json.dump(dict(devices=devices, cable_runs=cable_runs, edges=edges, feeders=feeders, spare_len=spare_len, calc=calc,
               fixtures=FIX, crossings=len(CROSS_LOG)),
          open(os.path.join(OUT, "quantities.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 検証
raw = open(os.path.join(OUT, "電灯コンセント設備平面図.dxf"), "rb").read()
assert b"\\U+" not in raw, "cp932 エスケープ残り"
from collections import Counter  # noqa: E402
print("entities:", dict(Counter(e.dxftype() for e in ms)))
print("layers:", len(doc.layers), [l.dxf.name for l in doc.layers])
print("crossings cut:", len(CROSS_LOG), CROSS_LOG)
for c in calc:
    print(f"{c['room']:<14} A={c['A']:6.2f} k={c['k']:.2f} U={c['U']:.3f} Nreq={c['Nreq']:5.2f} N={c['N']:2d} E={c['Ecalc']}")
