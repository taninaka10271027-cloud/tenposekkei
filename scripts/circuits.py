# -*- coding: utf-8 -*-
"""分電盤の回路構成（結線図・数量表で共用）。

負荷容量の考え方:
  - 照明: 器具の消費電力（DL 8.5W, ベースライト 45W）を VA とみなす（力率 ≒ 1）
  - 一般コンセント: 1 箇所 150VA（内線規程の算定値）
  - 専用コンセント・温水洗浄便座・活イケス: 機器未定のため想定値（備考に明記）
  - 2階予備: 行先未定のため容量は計上しない（2階計画確定時に幹線・主幹を再検討）
相: R = 第1相-中性線(100V), T = 第2相-中性線(100V), RT = 200V
"""

MCB = "MCB 2P1E 20AF/20AT"
MCB2 = "MCB 2P2E 20AF/20AT"
ELB = "ELB 2P2E 20AF/20AT 30mA"

PANELS = {
    "L-1": dict(
        name="店舗用分電盤 L-1", room="倉庫",
        feeder="ニュースラットケーブル 14sq×3", system="1φ3W 100/200V",
        main="MCCB 3P 60AF/60AT", demand=0.8,
        circuits=[
            # 番号, 名称, 遮断器, 電線, 相, VA(None=器具から算出), 備考
            ("1", "電灯（水回り：厨房・便所）", ELB, "VVF1.6-2C/3C", "R", None, ""),
            ("2", "電灯（客席・座敷・倉庫）", MCB, "VVF1.6-2C", "T", None, ""),
            ("3", "コンセント（客席 入口・カウンター）", MCB, "VVF2.0-2C", "R", None, ""),
            ("4", "コンセント（倉庫・座敷・ボックス席）", MCB, "VVF2.0-2C", "T", None, ""),
            ("5", "コンセント（厨房 一般）", ELB, "VVF2.0-3C", "R", None, ""),
            ("6", "コンセント（便所 温水洗浄便座）", ELB, "VVF2.0-3C", "T", 1400, "想定 700VA×2"),
            ("7", "厨房専用1 100V", ELB, "VVF2.0-3C", "R", 1500, "機器未定・想定"),
            ("8", "厨房専用2 100V", ELB, "VVF2.0-3C", "T", 1500, "機器未定・想定"),
            ("9", "厨房専用3 100V", ELB, "VVF2.0-3C", "R", 1500, "機器未定・想定"),
            ("10", "厨房専用4 200V", ELB, "VVF2.0-3C", "RT", 2000, "機器未定・想定"),
            ("11", "厨房専用5 200V", ELB, "VVF2.0-3C", "RT", 2000, "機器未定・想定"),
            ("12", "活イケス専用（屋外 防雨）", ELB, "VVF2.0-3C", "T", 1000, "想定"),
            ("13", "2階予備1", MCB2, "VVF2.0-3C", "-", 0, "2階計画後に確定"),
            ("14", "2階予備2", MCB2, "VVF2.0-3C", "-", 0, "2階計画後に確定"),
            ("15", "2階予備3", MCB2, "VVF2.0-3C", "-", 0, "2階計画後に確定"),
            ("16", "2階予備4", MCB2, "VVF2.0-3C", "-", 0, "2階計画後に確定"),
            ("17", "2階予備5", MCB2, "VVF2.0-3C", "-", 0, "2階計画後に確定"),
            ("18", "2階予備6", MCB2, "VVF2.0-3C", "-", 0, "2階計画後に確定"),
            ("19", "予備", MCB, "-", "-", 0, "スペース"),
            ("20", "予備", MCB, "-", "-", 0, "スペース"),
        ]),
    "L-2": dict(
        name="事務所用分電盤 L-2", room="事務所",
        feeder="ニュースラットケーブル 8sq×3", system="1φ3W 100/200V",
        main="MCCB 3P 50AF/40AT", demand=0.8,
        circuits=[
            ("1", "電灯（事務所）", MCB, "VVF1.6-2C", "R", None, ""),
            ("2", "コンセント（事務所 一般）", MCB, "VVF2.0-2C", "T", None, ""),
            ("3", "OA専用1", MCB, "VVF2.0-3C", "R", 1200, "想定"),
            ("4", "OA専用2", MCB, "VVF2.0-3C", "T", 1200, "想定"),
            ("5", "OA専用3", MCB, "VVF2.0-3C", "R", 1200, "想定"),
            ("6", "OA専用4", MCB, "VVF2.0-3C", "T", 1200, "想定"),
            ("7", "予備", MCB, "-", "-", 0, "スペース"),
            ("8", "予備", MCB, "-", "-", 0, "スペース"),
        ]),
}

W_FIX = {"DL": 8.5, "BL": 45}
VA_OUTLET = 150


def circuit_va(panel_key, no, devices):
    """器具配置から回路の負荷容量を算出（VA 未指定の回路用）"""
    cid = "L%s-%s" % (panel_key[-1], no)
    va = 0
    for d in devices:
        if d.get("circuit") != cid:
            continue
        if d["kind"] in W_FIX:
            va += W_FIX[d["kind"]]
        elif d["kind"] == "OUT":
            va += VA_OUTLET
    return round(va)


def panel_rows(panel_key, devices):
    rows = []
    for no, name, brk, cable, ph, va, note in PANELS[panel_key]["circuits"]:
        v = circuit_va(panel_key, no, devices) if va is None else va
        rows.append(dict(no=no, cid="L%s-%s" % (panel_key[-1], no), name=name, brk=brk, cable=cable,
                         phase=ph, va=v, note=note))
    return rows


def phase_sum(rows):
    r = sum(x["va"] for x in rows if x["phase"] == "R") + sum(x["va"] for x in rows if x["phase"] == "RT") / 2
    t = sum(x["va"] for x in rows if x["phase"] == "T") + sum(x["va"] for x in rows if x["phase"] == "RT") / 2
    return r, t
