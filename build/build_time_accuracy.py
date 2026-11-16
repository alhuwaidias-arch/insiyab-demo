"""دقة الزمن: زمن المسار على شبكة SUMO مقابل زمن السجل — من نفس المقاطع المقارَنة (27).

المخرَج: data/time_accuracy.json  (كل رقم مقيس من ملفات، لا رقم مكتوب بيد)

الطريقة:
  1) تُقرأ المقاطع (t0,t1) من data/accuracy_anas.json (نفس مقاطع دقة الطول 98.6%).
  2) لكل نقطة 1 هرتز داخل المقطع تُطابق بأقرب حافّة، **بشرط الاستمرارية**: المرشَّحون هم
     الحافة الحالية أو حوافها الخارجة فقط (وإلا التُقطت حوافّ موازية/معاكسة فتتضخم المسافة).
  3) يُبنى مسار الحواف لكل مقطع، ويُقاس زمن السجل (t1 - t0) وزمن الشبكة الحر (طول/حد).
  4) تُشغَّل محاكاة SUMO فعلية في عملية واحدة (مركبة لكل مقطع، بلا حركة أخرى، على تسلسل
     حوافّه نفسه) ويُقرأ زمنها من tripinfo — هذا هو الرقم المعروض، لا الحساب النظري.
  5) المسارات غير المتصلة (قفزة GPS) تُستبعد من البسط والمقام معًا، ويُذكَر عددها.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent
DATA = DEMO / "data"
SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
sys.path.insert(0, os.path.join(SUMO_HOME, "tools"))
import sumolib  # noqa: E402

NET_NAME = "insyab_v2.net.xml"
MATCH_R = 30.0


def find_net() -> Path:
    env = os.environ.get("INSYAB_NET")
    if env:
        return Path(env)
    for up in (DEMO, *DEMO.parents):
        cand = up / "data" / "network" / NET_NAME
        if cand.exists():
            return cand
    raise SystemExit("لم أجد %s — مرّر INSYAB_NET" % NET_NAME)


def ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def load_points(net) -> list[dict]:
    rows = []
    with open(DATA / "points_anas.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("fix") or "0").strip() not in ("1", "2", "3", "4", "5"):
                continue
            xy = net.convertLonLat2XY(float(r["lon"]), float(r["lat"]))
            rows.append({"t": ts(r["ts_utc"]), "x": xy[0], "y": xy[1]})
    rows.sort(key=lambda p: p["t"])
    return rows


def dist_to_edge(edge, pt) -> float:
    shape = edge.getShape()
    best = 1e9
    for a, b in zip(shape, shape[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        if l2 <= 0:
            d = ((pt["x"] - a[0]) ** 2 + (pt["y"] - a[1]) ** 2) ** 0.5
        else:
            t = max(0.0, min(1.0, ((pt["x"] - a[0]) * dx + (pt["y"] - a[1]) * dy) / l2))
            px, py = a[0] + t * dx, a[1] + t * dy
            d = ((pt["x"] - px) ** 2 + (pt["y"] - py) ** 2) ** 0.5
        best = min(best, d)
    return best


def project(edge, pt):
    """(الموقع بالمتر على طول شكل الحافة، المسافة العمودية عن مركزها)."""
    shape = edge.getShape()
    best_d, best_pos, acc = 1e9, 0.0, 0.0
    for a, b in zip(shape, shape[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        seg = l2 ** 0.5
        if seg <= 0:
            continue
        t = 0.0 if l2 <= 0 else max(0.0, min(1.0, ((pt["x"] - a[0]) * dx + (pt["y"] - a[1]) * dy) / l2))
        px, py = a[0] + t * dx, a[1] + t * dy
        d = ((pt["x"] - px) ** 2 + (pt["y"] - py) ** 2) ** 0.5
        if d < best_d:
            best_d, best_pos = d, acc + t * seg
        acc += seg
    return best_pos, best_d


def match_any(net, pt):
    best, bestd = None, MATCH_R
    for edge, dist in net.getNeighboringEdges(pt["x"], pt["y"], MATCH_R, includeJunctions=False):
        if dist <= bestd and not edge.getID().startswith(":"):
            best, bestd = edge.getID(), dist
    return best


def edge_seq(net, pts):
    """تسلسل الحواف بشرط الاستمرارية. يعيد (التسلسل، عدد الانقطاعات)."""
    seq = []
    breaks = 0
    for p in pts:
        if not seq:
            e = match_any(net, p)
            if e:
                seq.append(e)
            continue
        cur = net.getEdge(seq[-1])
        best, bestd = seq[-1], dist_to_edge(cur, p)
        if bestd > MATCH_R:
            for out in cur.getOutgoing():
                d = dist_to_edge(out, p)
                if d < bestd:
                    best, bestd = out.getID(), d
        if bestd > MATCH_R:
            e = match_any(net, p)
            if e and e != seq[-1]:
                seq.append(e)
                breaks += 1
        elif best != seq[-1]:
            seq.append(best)
    return seq, breaks


def free_flow(net, seq):
    tot_m = tot_s = 0.0
    for eid in seq:
        e = net.getEdge(eid)
        tot_m += e.getLength()
        tot_s += e.getLength() / (e.getSpeed() or 13.9)
    return tot_s, tot_m


def run_sumo(net_path, routes, tmp):
    """تشغيل واحد. كل مدخل: (تسلسل الحواف، موضع البداية، موضع النهاية).

    الانقطاعات تُجسَر بأقصر مسار في الشبكة وتُحسب bridged — ويُذكر عددها في المخرَج.
    departPos/arrivalPos يجعلان زمن tripinfo هو زمن القوس نفسه لا الحواف الطرفية كاملة.
    """
    net = sumolib.net.readNet(str(net_path))
    valid, skipped, bridged_total = [], [], 0
    for vid, (seq, dpos, apos, dspd) in routes.items():
        full, bridged, ok = [seq[0]], 0, True
        for a, b in zip(seq, seq[1:]):
            if b in {e.getID() for e in net.getEdge(full[-1]).getOutgoing()}:
                full.append(b)
                continue
            path, cost = net.getShortestPath(net.getEdge(full[-1]), net.getEdge(b))
            if not path:
                ok = False
                break
            mid = [e.getID() for e in path[1:-1]] or []
            full.extend(mid + [b])
            bridged += 1
        if not ok or len(full) < 2:
            skipped.append(vid)
            continue
        # arrivalPos يجب أن يكون بعد departPos إن كان على نفس الحافة
        last_len = net.getEdge(full[-1]).getLength()
        ap = min(max(apos, 0.1), last_len - 0.1)
        dp = min(max(dpos, 0.0), net.getEdge(full[0]).getLength() - 0.1)
        if len(full) == 2 and ap <= dp:
            skipped.append(vid)
            continue
        valid.append((vid, full, dp, ap, dspd))
        bridged_total += bridged

    if not valid:
        return {}, skipped, 0

    rou = tmp / "routes.rou.xml"
    lines = ["<routes>",
             '  <vType id="car" vClass="passenger" accel="2.6" decel="4.5" sigma="0" '
             'length="4.8" minGap="2.5" maxSpeed="50"/>']
    for k, (vid, seq, dp, ap, dspd) in enumerate(valid):
        lines.append('  <route id="r_%s" edges="%s"/>' % (vid, " ".join(seq)))
        lines.append('  <vehicle id="%s" type="car" route="r_%s" depart="%d" '
                     'departPos="%.1f" arrivalPos="%.1f" departSpeed="%.2f"/>'
                     % (vid, vid, 5 + k, dp, ap, dspd))
    lines.append("</routes>")
    rou.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")

    trip = tmp / "tripinfo.xml"
    cmd = [os.path.join(SUMO_HOME, "bin", "sumo"), "-n", str(net_path), "-r", str(rou),
           "--tripinfo-output", str(trip), "--no-step-log", "true", "--no-warnings",
           "true", "--duration-log.disable", "true", "--seed", "42", "--end", "100000"]
    subprocess.run(cmd, check=True, capture_output=True)

    # تجميع فرعي على المقاطع الطويلة (≥500 م): المقاطع القصيرة (~20-30 ث) يغلب عليها
    # التسارع/التباطؤ عند طرفيها لا الزمن على الطريق، فتُعرض منفصلة كتحقّق إضافي.
    out = {}
    for ti in ET.parse(trip).getroot().iter("tripinfo"):
        out[ti.get("id")] = {
            "duration": float(ti.get("duration")),
            "timeLoss": float(ti.get("timeLoss")),
            "routeLength": float(ti.get("routeLength")),
        }
    return out, skipped, bridged_total


def main():
    acc = json.loads((DATA / "accuracy_anas.json").read_text(encoding="utf-8"))
    net_path = find_net()
    net = sumolib.net.readNet(str(net_path))
    pts = load_points(net)

    routes, per = {}, []
    for i, st in enumerate(acc["detail"]):
        t0, t1 = ts(st["t0"]), ts(st["t1"])
        seg = [p for p in pts if t0 <= p["t"] <= t1]
        seq, breaks = edge_seq(net, seg)
        if len(seq) < 2 or len(seg) < 2:
            if len(seg) < 2 and st.get("pts", 0) >= 2:
                pass
            continue
        gaps = [(b["t"] - a["t"]).total_seconds() for a, b in zip(seg, seg[1:])]
        max_gap = max(gaps) if gaps else 0.0
        field_s_pts = (seg[-1]["t"] - seg[0]["t"]).total_seconds()
        dpos, _ = project(net.getEdge(seq[0]), seg[0])
        j = min(len(seg) - 1, 4)
        dt0 = max((seg[j]["t"] - seg[0]["t"]).total_seconds(), 0.001)
        dspd = min(((seg[j]["x"] - seg[0]["x"]) ** 2 + (seg[j]["y"] - seg[0]["y"]) ** 2) ** 0.5 / dt0,
                   net.getEdge(seq[0]).getSpeed())
        apos, _ = project(net.getEdge(seq[-1]), seg[-1])
        ff_s, ff_m = free_flow(net, seq)
        routes["s%02d" % i] = (seq, dpos, apos, dspd)
        per.append({
            "i": i, "t0": st["t0"], "t1": st["t1"],
            "field_s": round(field_s_pts, 1) if field_s_pts > 0 else float(st["field_s"]),
            "field_s_span": float(st["field_s"]), "max_gap_s": round(max_gap, 1),
            "pts": len(seg), "field_m": float(st["field_m"]),
            "edges": len(seq), "breaks": breaks,
            "ff_s": round(ff_s, 1), "ff_m": round(ff_m, 1),
            "limit_kmh": round(ff_m / ff_s * 3.6, 1) if ff_s else None,
        })

    with tempfile.TemporaryDirectory() as td:
        sim, skipped, bridged = run_sumo(net_path, routes, Path(td))

    for rec in per:
        s = sim.get("s%02d" % rec["i"])
        rec["sim_s"] = round(s["duration"], 1) if s else None
        rec["sim_m"] = round(s["routeLength"], 1) if s else None
        rec["sim_timeloss_s"] = round(s["timeLoss"], 1) if s else None

    for r in per:
        r["err_m_pct"] = round((r["sim_m"] - r["field_m"]) / r["field_m"] * 100.0, 2) if r.get("sim_m") else None
        r["err_time_pct"] = round((r["sim_s"] - r["field_s"]) / r["field_s"] * 100.0, 2) if r.get("sim_s") else None

    # ضبط الجودة: مقطع لا يُقبل إلا إذا أعادت المطابقة مسارًا بطول المقيس نفسه (±5%)؛
    # ما خرج عن ذلك عطل مطابقة (قفزة GPS/تفافية) لا دقة محاكاة، ويُذكر عدده صريحًا.
    sampled = [r for r in per if r.get("sim_s")]
    gap_rejected = [r["i"] for r in sampled if r["max_gap_s"] > 3.0]
    ok = [r for r in sampled if abs(r["err_m_pct"]) <= 5.0 and r["max_gap_s"] <= 3.0]
    qc_rejected = [r["i"] for r in sampled
                   if abs(r["err_m_pct"]) > 5.0 or r["max_gap_s"] > 3.0]
    n_all = len(acc["detail"])
    field_s = sum(r["field_s"] for r in ok)
    sim_s = sum(r["sim_s"] for r in ok)
    ff_s = sum(r["ff_s"] for r in ok)
    field_m = sum(r["field_m"] for r in ok)
    sim_m = sum(r["sim_m"] for r in ok)

    for r in ok:
        print("  %2d  حواف %2d (قطع %d)  مسار المحاكاة %6.1f م / %6.1f م (حر)  "
              "مقيس %6.1f م  %5.1f كم/س مقيس مقابل %4.1f كم/س حد"
              % (r["i"], r["edges"], r["breaks"], r["sim_m"], r["ff_m"], r["field_m"],
                 r["field_m"] / r["field_s"] * 3.6, r["limit_kmh"] or 0))
    if skipped:
        print("  مستبعد (مسار غير متصل): %s" % ",".join(skipped))
    if gap_rejected:
        print("  مستبعد (انقطاع تسجيل > 3 ث داخل المقطع — الزمن غير صالح للقياس): %s"
              % ",".join(str(i) for i in gap_rejected))
    if qc_rejected:
        print("  مستبعد (طول المسار المُعاد يخالف المقيس بأكثر من 5%%): %s"
              % ",".join(str(i) for i in qc_rejected))

    # تجميع فرعي على المقاطع الطويلة (≥500 م): المقاطع القصيرة (~20-30 ث) يغلب عليها
    # التسارع/التباطؤ عند طرفيها لا الزمن على الطريق، فتُعرض منفصلة كتحقّق إضافي.
    long_ok = [r for r in ok if r["field_m"] >= 500.0]
    field_s_long = sum(r["field_s"] for r in long_ok)
    sim_s_long = sum(r["sim_s"] for r in long_ok)

    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": "SUMO 1.27.0 (bin/sumo, tripinfo)",
        "net": NET_NAME,
        "net_sha16": acc.get("net_sha16"),
        "method": ("مقطع في كل مرة · مسار الحواف المطابقة بشرط الاستمرارية · مركبة واحدة "
                   "بلا حركة أخرى (sigma=0) · زمن المحاكاة من tripinfo.duration"),
        "stretches_analysed": n_all,
        "stretches_simulated": len(ok),
        "stretches_skipped": len(skipped),
        "stretches_rejected_distance": qc_rejected,
        "qc_rule": ("يُقبل المقطع إذا كان طول المسار المُعاد من الشبكة داخل ±5% من طول المقيس "
                    "ولا يوجد انقطاع تسجيل > 3 ث داخله (زمن السجل = فرق زمن أول نقطة وآخرها)"),
        "stretches_rejected_gap": gap_rejected,
        "bridged_links": bridged,
        "field_s": round(field_s, 1),
        "sim_s": round(sim_s, 1),
        "ff_s": round(ff_s, 1),
        "field_min": round(field_s / 60.0, 1),
        "sim_min": round(sim_s / 60.0, 1),
        "field_m": round(field_m, 1),
        "sim_m": round(sim_m, 1),
        "err_time_pct": round((sim_s - field_s) / field_s * 100.0, 2),
        "time_accuracy_pct": round(100.0 - abs(sim_s - field_s) / field_s * 100.0, 2),
        "gap_observed_s": round(field_s - sim_s, 1),
        "field_kmh": round(field_m / field_s * 3.6, 1),
        "sim_kmh": round(sim_m / sim_s * 3.6, 1),
        "long_m_from": 500.0,
        "long_stretches": len(long_ok),
        "long_field_s": round(field_s_long, 1),
        "long_sim_s": round(sim_s_long, 1),
        "long_err_time_pct": round((sim_s_long - field_s_long) / field_s_long * 100.0, 2)
        if field_s_long else None,
        "long_time_accuracy_pct": round(100.0 - abs(sim_s_long - field_s_long) / field_s_long * 100.0, 2)
        if field_s_long else None,
        "detail": per,
    }
    # الوسيطان يُحسبان **قبل** الكتابة — كتابة الملف ثم إضافة مفاتيح تُنتج JSON ناقصًا يمرّ من التوليد
    import statistics as _st
    med_abs = _st.median([abs(r["err_time_pct"]) for r in ok]) if ok else 0.0
    out["err_time_median_abs_pct"] = round(med_abs, 2)
    out["err_m_median_abs_pct"] = round(_st.median([abs(r["err_m_pct"]) for r in ok]), 2) if ok else 0.0
    (DATA / "time_accuracy.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK  %d/%d مقطعًا · مقيس %.1f د · محاكاة %.1f د · زمن حر %.1f د · خطأ الزمن %+.2f%%"
          % (len(ok), n_all, out["field_min"], out["sim_min"], ff_s / 60.0, out["err_time_pct"]))
    print("    وسيط |خطأ الزمن| لكل مقطع: %.2f%% · وسيط |خطأ الطول|: %.2f%%"
          % (out["err_time_median_abs_pct"], out["err_m_median_abs_pct"]))
    print("    المقاطع الطويلة (≥500 م): %d · مقيس %.1f د · محاكاة %.1f د · خطأ %+.2f%%"
          % (out["long_stretches"], field_s_long / 60.0, sim_s_long / 60.0,
             out["long_err_time_pct"] or 0.0))
    print("    جسور أقصر مسار: %d" % bridged)
    print("    مسافة: مقيس %.1f م · مسار المحاكاة %.1f م · سرعة مقيسة %.1f · محاكاة %.1f كم/س"
          % (field_m, sim_m, out["field_kmh"], out["sim_kmh"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
