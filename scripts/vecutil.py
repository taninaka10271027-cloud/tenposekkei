# -*- coding: utf-8 -*-
"""pdf_vec_extract.py の中間データ (vec.json) を JW_CAD 用 DXF (R12, cp932) にする。

ベクタPDFは作図し直さず、座標を実寸に換算するだけでよい:
    X = x_pt * 25.4/72 * 縮尺,  Y = (ページ高さ_pt - y_pt) * 25.4/72 * 縮尺

処理:
  1. 長さ 0 の線・重複線を除き、同じ直線上で接する線分を 1 本にまとめる
     （JW_CAD で 1 本として選べるように。破線のすき間はまとめない）
  2. 領域ファイル（--regions）でレイヤに振り分ける
  3. 太線（--thick pt 以上）は色 1（赤）にする。R12 に線幅は無いので JW の線色で太さを付ける
  4. 文字は 1 字ずつの情報を、同じ大きさ・向きで続く字ごとに 1 つの TEXT にまとめる。
     文字コードの無い字は glyphmap.json（pdf_glyph_decode.py の出力）で文字に戻す

領域ファイル (JSON) の例。上から順に判定し、最初に図形が丸ごと入る矩形のレイヤにする。
矩形は表示座標 (pt, y 下向き)。座標は render したページ画像を見て決める:
    [{"layer": "表題欄", "rect": [54, 757, 1138, 815]},
     {"layer": "凡例",   "rect": [740, 172, 1000, 513]},
     {"layer": "平面",   "rect": [54, 27, 740, 757]}]
どの矩形にも入らない図形は --default-layer（既定「図形」）、文字は「文字」に入る。
レイヤは JW_CAD の 1 グループ 16 枚に収まるよう、15 以内に抑える。

使い方:
    python pdf_vec2dxf.py vec.json out.dxf --scale 100 [--glyphmap work/glyphmap.json]
           [--regions regions.json] [--thick 0.9]
"""
import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict

import ezdxf


def dedupe(lines):
    seen = {}
    for l in lines:
        if math.hypot(l[2] - l[0], l[3] - l[1]) < 1e-4:
            continue
        a, b = (round(l[0], 2), round(l[1], 2)), (round(l[2], 2), round(l[3], 2))
        k = (min(a, b), max(a, b), l[4])
        seen.setdefault(k, l)
    return list(seen.values())


def merge_collinear(lines, ang_tol=0.003, off_tol=0.01, gap_tol=0.01):
    """同じ線幅・同じ直線上で、重なるか端点が接する線分を 1 本にまとめる。"""
    groups, keep = defaultdict(list), []
    for l in lines:
        x0, y0, x1, y1, w = l
        if math.hypot(x1 - x0, y1 - y0) < 0.5 and abs(x1 - x0) > 1e-3 and abs(y1 - y0) > 1e-3:
            keep.append(l)          # 曲線の分割片などの極短の斜線は角度が当てにならない
            continue
        a = math.atan2(y1 - y0, x1 - x0) % math.pi
        if a > math.pi - ang_tol / 2:
            a -= math.pi
        c = -x0 * math.sin(a) + y0 * math.cos(a)
        groups[(round(a / ang_tol), round(c / (off_tol * 5)), w)].append((a, c, l))
    res = list(keep)
    for g in groups.values():
        a = sum(t[0] for t in g) / len(g)
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        segs = sorted([min(l[0] * dx + l[1] * dy, l[2] * dx + l[3] * dy),
                       max(l[0] * dx + l[1] * dy, l[2] * dx + l[3] * dy), c, l] for _, c, l in g)
        cur = None
        runs = []
        for s in segs:
            if cur and s[0] <= cur[1] + gap_tol and abs(s[2] - cur[2]) < off_tol:
                cur[1] = max(cur[1], s[1])
                cur[3].append(s[3])
            else:
                if cur:
                    runs.append(cur)
                cur = [s[0], s[1], s[2], [s[3]]]
        if cur:
            runs.append(cur)
        for t0, t1, c, members in runs:
            if len(members) == 1:
                res.append(members[0])
                continue
            cc = sum(m[0] * nx + m[1] * ny for m in members) / len(members)
            res.append([t0 * dx + cc * nx, t0 * dy + cc * ny,
                        t1 * dx + cc * nx, t1 * dy + cc * ny, members[0][4]])
    return res


def text_runs(texts, gm):
    """1 字ずつの文字を、同じ大きさ・向きで隣り合う字ごとにまとめる。"""
    runs = []
    for t in texts:
        ch = t["u"] if t["u"] is not None else gm.get("%s|%d" % (t["font"], t["gid"]), [None])[0]
        if ch is None:
            ch = "?"
        c = dict(t, ch=ch)
        if not c["vertical"] and runs and not runs[-1][0]["vertical"]:
            p = runs[-1][-1]
            dx, dy = p["dir"]
            pw = abs((p["bbox"][2] - p["bbox"][0]) * dx + (p["bbox"][3] - p["bbox"][1]) * dy)
            ex = (p["o"][0] + pw * dx, p["o"][1] + pw * dy)
            if (abs(p["size"] - c["size"]) < 0.01 and abs(dx - c["dir"][0]) < 1e-3
                    and abs(dy - c["dir"][1]) < 1e-3
                    and math.hypot(ex[0] - c["o"][0], ex[1] - c["o"][1]) < 0.3 * c["size"]):
                runs[-1].append(c)
                continue
        runs.append([c])
    out = []
    for r in runs:
        while r and r[0]["ch"] in " 　":
            r = r[1:]
        while r and r[-1]["ch"] in " 　":
            r = r[:-1]
        if not r:
            continue
        s = "".join(c["ch"] for c in r)
        c0 = r[0]
        size = c0["size"]
        bb = [min(c["bbox"][0] for c in r), min(c["bbox"][1] for c in r),
              max(c["bbox"][2] for c in r), max(c["bbox"][3] for c in r)]
        dx, dy = c0["dir"]
        if c0["vertical"]:
            # 縦書き: 字の底辺は流れ方向から 90°。bbox 中心に字の中心が来るよう基点を逆算
            rot = math.degrees(math.atan2(dy, dx)) - 90.0
            rr = math.radians(rot)
            u = (math.cos(rr), -math.sin(rr))
            up = (-math.sin(rr), -math.cos(rr))
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            o = (cx - 0.5 * size * u[0] - 0.38 * size * up[0],
                 cy - 0.5 * size * u[1] - 0.38 * size * up[1])
        else:
            rot = math.degrees(math.atan2(-dy, dx))
            o = tuple(c0["o"])
        out.append((s, o, size, rot, bb))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vec")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, required=True, help="縮尺の分母（1/100 なら 100）")
    ap.add_argument("--glyphmap")
    ap.add_argument("--regions")
    ap.add_argument("--thick", type=float, default=0.9, help="太線とみなす線幅 pt")
    ap.add_argument("--default-layer", default="図形")
    ap.add_argument("--no-merge", action="store_true", help="線の結合をしない")
    a = ap.parse_args()

    v = json.load(open(a.vec, encoding="utf-8"))
    gm = json.load(open(a.glyphmap, encoding="utf-8")) if a.glyphmap else {}
    regions = json.load(open(a.regions, encoding="utf-8")) if a.regions else []
    K = 25.4 / 72 * a.scale
    PW, PH = v["size_pt"]

    def X(x, y):
        return (round(x * K, 3), round((PH - y) * K, 3))

    def layer_of(b, text=False):
        for r in regions:
            x0, y0, x1, y1 = r["rect"]
            if b[0] >= x0 and b[1] >= y0 and b[2] <= x1 and b[3] <= y1:
                return r["layer"]
        return "文字" if text else a.default_layer

    names = []
    for r in regions:
        if r["layer"] not in names:
            names.append(r["layer"])
    for n in (a.default_layer, "文字"):
        if n not in names:
            names.append(n)
    if len(names) > 16:
        print("※ レイヤが %d 枚。JW_CAD の 1 グループ 16 枚を超える" % len(names))

    doc = ezdxf.new("R12", setup=True)
    doc.encoding = "cp932"
    doc.header["$LTSCALE"] = a.scale
    doc.styles.new("JP", dxfattribs={"font": "msgothic.ttf"})
    for i, n in enumerate(names):
        doc.layers.new(n, dxfattribs={"color": [7, 2, 3, 4, 5, 6, 8, 9][i % 8],
                                      "linetype": "CONTINUOUS"})
    ms = doc.modelspace()

    def attrs(lay, w):
        d = {"layer": lay}
        if w >= a.thick:
            d["color"] = 1
        return d

    lines = dedupe(v["lines"])
    if not a.no_merge:
        lines = merge_collinear(lines)
    stat = Counter()
    for l in lines:
        b = (min(l[0], l[2]), min(l[1], l[3]), max(l[0], l[2]), max(l[1], l[3]))
        lay = layer_of(b)
        ms.add_line(X(l[0], l[1]), X(l[2], l[3]), dxfattribs=attrs(lay, l[4]))
        stat[lay] += 1
    for cx, cy, r, w in v["circles"]:
        lay = layer_of((cx - r, cy - r, cx + r, cy + r))
        ms.add_circle(X(cx, cy), r * K, dxfattribs=attrs(lay, w))
        stat[lay] += 1
    for cx, cy, r, a0, sw, w in v["arcs"]:
        # 表示座標 (y 下向き) の a0..a0+sw は、DXF (y 上向き) では -(a0+sw)..-a0
        pts = [(cx + r * math.cos(a0 + sw * t), cy + r * math.sin(a0 + sw * t))
               for t in (0, 0.25, 0.5, 0.75, 1)]
        b = (min(p[0] for p in pts), min(p[1] for p in pts),
             max(p[0] for p in pts), max(p[1] for p in pts))
        lay = layer_of(b)
        ms.add_arc(X(cx, cy), r * K, math.degrees(-(a0 + sw)) % 360,
                   math.degrees(-a0) % 360, dxfattribs=attrs(lay, w))
        stat[lay] += 1
    unknown = 0
    for s, o, size, rot, bb in text_runs(v["texts"], gm):
        unknown += s.count("?")
        lay = layer_of(bb, text=True)
        ms.add_text(s, dxfattribs={"layer": lay, "height": round(size * K, 1),
                                   "rotation": round(rot, 3) % 360, "style": "JP",
                                   "insert": X(*o)})
        stat["文字:" + lay] += 1
    used = {e.dxf.layer for e in ms}
    for n in names:
        if n not in used:
            doc.layers.remove(n)          # 図形の無いレイヤは残さない
    doc.saveas(a.out)

    raw = open(a.out, "rb").read()
    print("saved %s  (A?: %.0f x %.0f mm @1/%g)" % (a.out, PW * K, PH * K, a.scale))
    print("  線 %d 本（元 %d 本）/ 円 %d / 円弧 %d" % (len(lines), len(v["lines"]),
                                               len(v["circles"]), len(v["arcs"])))
    print("  レイヤ別:", dict(stat))
    if unknown:
        print("※ 文字に戻せなかった字が %d 字（? で出力）。glyphmap を確認する" % unknown)
    if b"\\U+" in raw:
        print("※ \\U+ エスケープが残っている。doc.encoding を確認")
    return 0


if __name__ == "__main__":
    sys.exit(main())
