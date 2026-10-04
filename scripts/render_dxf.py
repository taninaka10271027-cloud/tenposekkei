# -*- coding: utf-8 -*-
"""DXF を PNG に描画して目視確認する。

JW_CAD を開かずに「文字が重なっていないか」「図枠からはみ出していないか」を
確認するための道具。必ず一度は目で見ること。座標が正しくても、寸法文字と
通り芯符号が重なっているような図面は使い物にならない。

使い方:
    python render_dxf.py plan.dxf out.png [--paper 297 210] [--scale 200]

実装メモ:
  TEXT は ezdxf のバックエンドに任せず matplotlib で描き直している。
  ezdxf のフォント解決は STYLE の font 名に依存し、日本語が豆腐になるため。
  フォントは Meiryo を使う。MS Gothic (msgothic.ttc) は埋め込みビットマップを
  持っていて、特定サイズでグリフのパスが空になり文字が消える。
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/BIZ-UDGothicR.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
HA = {0: "left", 1: "center", 2: "right", 3: "left", 4: "center", 5: "left"}
VA = {0: "baseline", 1: "bottom", 2: "center", 3: "top"}


def pick_font():
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return FontProperties(fname=f)
    return FontProperties()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("png")
    ap.add_argument("--paper", nargs=2, type=float, default=[297.0, 210.0])
    ap.add_argument("--scale", type=float, default=200.0)
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--color", action="store_true", help="レイヤ色で描画（既定は黒）")
    a = ap.parse_args()

    W, H = a.paper[0] * a.scale, a.paper[1] * a.scale
    fp = pick_font()

    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()

    texts = []
    for t in list(msp.query("TEXT")):
        ha, va = t.dxf.get("halign", 0), t.dxf.get("valign", 0)
        pt = t.dxf.align_point if (ha or va) else t.dxf.insert
        texts.append((pt.x, pt.y, t.dxf.height, t.dxf.text,
                      HA.get(ha, "left"), VA.get(va, "baseline"), t.dxf.rotation))
        msp.delete_entity(t)

    fig = plt.figure(figsize=(a.paper[0] / 25.4, a.paper[1] / 25.4), dpi=a.dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    cfg = Configuration(color_policy=ColorPolicy.COLOR if a.color else ColorPolicy.BLACK,
                        lineweight_scaling=0.6,
                        background_policy=BackgroundPolicy.WHITE)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(
        msp, finalize=False)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    d = ax.transData.transform([(0, 0), (1000, 0)])
    pt_per_unit = (d[1][0] - d[0][0]) / 1000.0 * 72.0 / fig.dpi
    for x, y, h, s, ha, va, rot in texts:
        f = fp.copy()
        # fontsize= と fontproperties= を併用すると無視されることがあるので
        # サイズは FontProperties 側に入れる。
        f.set_size(h * pt_per_unit)
        ax.text(x, y, s, fontproperties=f, ha=ha, va=va, rotation=rot, color="black",
                rotation_mode="anchor")   # 挿入点を軸に回す（既定は文字の中心で回り、位置がずれる）

    fig.savefig(a.png, facecolor="white")
    print("rendered %s  (%d texts, paper %.0fx%.0f @1/%.0f)"
          % (a.png, len(texts), a.paper[0], a.paper[1], a.scale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
