# -*- coding: utf-8 -*-
"""分電盤結線図・照度計算表（A3 横・NonScale、実寸 1/50 相当の文字高で作図）。

入力: output/quantities.json（make_elec_plan.py の出力）
出力: output/分電盤結線図_照度計算表.dxf
"""
import json
import math
import os
import sys

import ezdxf

sys.path.insert(0, os.path.dirname(__file__))
from circuits import PANELS, panel_rows, phase_sum  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "output")
Q = json.load(open(os.path.join(OUT, "quantities.json"), encoding="utf-8"))
PH = 14850

doc = ezdxf.new("R12", setup=True)
doc.encoding = "cp932"
doc.styles.new("JP", dxfattribs={"font": "msgothic.ttf"})
for n, c in (("図枠", 7), ("表題欄", 7), ("結線図", 1), ("表", 7), ("文字", 7), ("注記", 7)):
    doc.layers.new(n, dxfattribs={"color": c})
ms = doc.modelspace()


def T(x, y):
    return (x, PH - y)


def line(lay, p, q):
    ms.add_line(T(*p), T(*q), dxfattribs={"layer": lay})


def rect(lay, x0, y0, x1, y1):
    for p, q in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        line(lay, p, q)


def text(lay, x, y, s, h=120, align="ML"):
    va = {"T": "TOP", "M": "MIDDLE", "B": "BOTTOM"}[align[0]]
    ha = {"L": "LEFT", "C": "CENTER", "R": "RIGHT"}[align[1]]
    t = ms.add_text(s, dxfattribs={"layer": lay, "height": h, "style": "JP"})
    t.set_placement(T(x, y), align=ezdxf.enums.TextEntityAlignment[f"{va}_{ha}"])


def breaker(x, y, kind):
    """遮断器記号（配線用遮断器: □に B / 漏電遮断器: □に E）"""
    rect("結線図", x - 110, y - 110, x + 110, y + 110)
    text("結線図", x, y, "E" if kind.startswith("ELB") else "B", 120, "MC")


# ---- 図枠・表題欄
rect("図枠", 507, 500, 20508, 14349)
TB = (17307, 13049, 20508, 14349)
rect("表題欄", *TB)
for i in range(1, 5):
    line("表題欄", (TB[0], TB[1] + 260 * i), (TB[2], TB[1] + 260 * i))
line("表題欄", (18108, TB[1]), (18108, TB[3]))
for i, (k, v) in enumerate((("図名", "分電盤結線図・照度計算表"), ("縮尺", "NonScale (A3)"), ("単位", "mm / VA"),
                            ("原図", "電灯・コンセント設備平面図による"), ("作成", "2026-10-04"))):
    yc = TB[1] + 260 * i + 130
    text("表題欄", 17707, yc, k, 100, "MC")
    text("表題欄", 19308, yc, v, 100, "MC")


# ---- 分電盤結線図
COLS = [("回路", 550), ("遮断器", 1900), ("電線", 1150), ("負荷名称", 2300), ("容量VA", 700), ("相", 400),
        ("備考", 800)]


def panel_diagram(key, x0, y0):
    p = PANELS[key]
    rows = panel_rows(key, Q["devices"])
    text("文字", x0, y0, p["name"] + "　結線図", 200, "BL")
    text("文字", x0, y0 + 280, f"設置場所：{p['room']}　電気方式：{p['system']}　幹線：{p['feeder']}", 110, "BL")
    # 主幹
    bx = x0 + 300
    ytop = y0 + 520
    line("結線図", (bx, ytop), (bx, ytop + 250))
    text("結線図", bx + 150, ytop + 60, "幹線 " + p["feeder"] + "（引込点より）", 100, "ML")
    breaker(bx, ytop + 360, "MCCB")
    text("結線図", bx + 200, ytop + 360, "主幹 " + p["main"], 110, "ML")
    rh = 330
    yb0 = ytop + 470
    hy = ytop + 760                   # 表ヘッダ
    # 表
    tx0 = bx + 900
    widths = [w for _, w in COLS]
    tx1 = tx0 + sum(widths)
    rect("表", tx0, hy - 200, tx1, hy + 200 + rh * len(rows))
    line("表", (tx0, hy + 200), (tx1, hy + 200))
    xx = tx0
    for (h, w) in COLS:
        text("表", xx + w / 2, hy, h, 95, "MC")
        xx += w
        line("表", (xx, hy - 200), (xx, hy + 200 + rh * len(rows)))
    ybus1 = hy + 200 + rh * (len(rows) - 0.5)
    line("結線図", (bx, yb0), (bx, ybus1))        # 母線
    for i, r in enumerate(rows):
        yc = hy + 200 + rh * (i + 0.5)
        line("表", (tx0, yc + rh / 2), (tx1, yc + rh / 2))
        line("結線図", (bx, yc), (bx + 450, yc))
        breaker(bx + 560, yc, r["brk"])
        line("結線図", (bx + 670, yc), (tx0, yc))
        vals = [r["cid"], r["brk"], r["cable"], r["name"], f"{r['va']:,}" if r["va"] else "-", r["phase"], r["note"]]
        xx = tx0
        for (h, w), v in zip(COLS, vals):
            if h in ("容量VA",):
                text("表", xx + w - 60, yc, v, 90, "MR")
            elif h in ("回路", "相"):
                text("表", xx + w / 2, yc, v, 90, "MC")
            else:
                text("表", xx + 50, yc, v, 85 if h != "負荷名称" else 90, "ML")
            xx += w
    rr, tt = phase_sum(rows)
    tot = sum(r["va"] for r in rows)
    yb = hy + 200 + rh * len(rows) + 250
    dem = p["demand"]
    imax = max(rr, tt) * dem / 100
    text("文字", tx0, yb, f"設備容量 合計 {tot:,} VA（R相 {rr:,.0f} VA / T相 {tt:,.0f} VA）", 110, "ML")
    text("文字", tx0, yb + 220,
         f"需要率 {dem:.1f} として 最大相電流 ≒ {max(rr, tt):,.0f}×{dem:.1f}÷100V ≒ {imax:.0f} A"
         f"　→ 主幹 {p['main'].split()[-1]} にて可", 110, "ML")
    return yb + 220


yend1 = panel_diagram("L-1", 800, 1000)
yend2 = panel_diagram("L-2", 11300, 1000)

# ---- 照度計算表
CX, CY = 11300, yend2 + 650
text("文字", CX, CY, "照度計算表（光束法　N = E・A ／ (F・U・M)）", 200, "BL")
CC = [("室名", 1650), ("面積㎡", 600), ("基準面", 900), ("室指数", 550), ("器具", 900), ("光束lm", 650),
      ("照明率", 550), ("保守率", 550), ("設計照度", 650), ("必要台数", 650), ("設置台数", 650), ("計算照度", 650)]
hy = CY + 450
rh = 330
x1 = CX + sum(w for _, w in CC)
calc = Q["calc"]
rect("表", CX, hy - 190, x1, hy + 190 + rh * len(calc))
line("表", (CX, hy + 190), (x1, hy + 190))
xx = CX
for h, w in CC:
    text("表", xx + w / 2, hy, h, 85, "MC")
    xx += w
    line("表", (xx, hy - 190), (xx, hy + 190 + rh * len(calc)))
for i, c in enumerate(calc):
    yc = hy + 190 + rh * (i + 0.5)
    line("表", (CX, yc + rh / 2), (x1, yc + rh / 2))
    vals = [c["room"], f"{c['A']:.2f}", c["work"], f"{c['k']:.2f}",
            "ダウンライト" if c["lm"] == 1000 else "ベースライト", f"{c['lm']:,}", f"{c['U']:.2f}",
            f"{c['M']:.2f}", f"{c['E']}lx", f"{c['Nreq']:.1f}", f"{c['N']}台", f"{c['Ecalc']}lx"]
    xx = CX
    for (h, w), v in zip(CC, vals):
        if h == "室名":
            text("表", xx + 50, yc, v, 85, "ML")
        else:
            text("表", xx + w / 2, yc, v, 80, "MC")
        xx += w
ny = hy + 190 + rh * len(calc) + 300
NOTES = [
    "・天井高 2,400。床面基準は H=2.4m、作業面(FL+850)基準は H=1.55m で室指数を算出",
    "・照明率は反射率 天井70%・壁50%・床10% の一般的な値（器具選定後にメーカー照明率表で再確認）",
    "・保守率 0.77（LED・普通環境）、厨房は 0.69（汚れやすい環境）",
    "・ダウンライト：φ100 埋込 1,000lm（約8.5W）　ベースライト：40形 逆富士 6,900lm（約45W）",
    "・設計照度は JIS Z 9110 を参考（飲食店客席・便所 200lx 以上、調理室 500lx、事務室 750lx）",
    "・事務所は 2列×3灯（窓側ア／内側イ）の配置で計算照度 約1,000lx（750lx 以上を確保）",
]
for s in NOTES:
    text("注記", CX, ny, s, 90, "ML")
    ny += 180

# ---- 幹線・共通事項（左下）
ny = yend1 + 700
text("文字", 800, ny, "幹線・共通事項", 180, "BL")
ny += 300
for s in [
    "・幹線　店舗 L-1：ニュースラットケーブル 14sq×3（1φ3W 100/200V）",
    "　　　　事務所 L-2：ニュースラットケーブル 8sq×3（1φ3W 100/200V）",
    "・引込点・電力量計は別途。幹線の亘長確定後に電圧降下を確認すること",
    "・2階予備 L1-13〜18 は容量未計上。2階負荷確定時に主幹・幹線容量を再検討",
    "・水回り（厨房・便所）・屋外・厨房専用回路は漏電遮断器(30mA)とする",
    "・コンセント接地(E)は分電盤の接地端子より（D種接地）",
]:
    text("注記", 800, ny, s, 100, "ML")
    ny += 200

doc.saveas(os.path.join(OUT, "分電盤結線図_照度計算表.dxf"))
raw = open(os.path.join(OUT, "分電盤結線図_照度計算表.dxf"), "rb").read()
assert b"\\U+" not in raw
print("saved; last y", yend2, ny)
