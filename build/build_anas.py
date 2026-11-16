"""يبني data/anas.json — بيانات واجهة «انسياب» لممر طريق أنس بن مالك.

المصادر (لا يُكتب رقم بيد هنا):
  data/network.json      شبكة insyab_v2 (مستخرجة سابقًا) — الهندسة وأسماء الشوارع.
  <trace>                trace_anas.json — مسار الجولة الميدانية 14/11 (1 هرتز).
  <accuracy>             ACCURACY_ANAS.json — أرقام المطابقة على الشبكة.
  data/_geo_meta.json    تقاطع U-Turn وإحصاءات الممر (من sumolib).

الاستخدام:
  python build/build_anas.py --trace <trace_anas.json> --accuracy <ACCURACY_ANAS.json>
"""
import argparse
import datetime as dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAD = 0.009          # درجة (~1 كم) حول الجولة لإظهار السياق
MAXLON, MAXLAT = 0.02, 0.02


def clip_bbox(trace):
    lons = [p["lon"] for p in trace]
    lats = [p["lat"] for p in trace]
    return (min(lons) - PAD, min(lats) - PAD, max(lons) + PAD, max(lats) + PAD)


def build(trace_path=None, accuracy_path=None):
    trace_path = trace_path or os.environ.get("ANAS_TRACE")
    accuracy_path = accuracy_path or os.environ.get("ANAS_ACCURACY")
    net = json.load(open(os.path.join(ROOT, "data", "network.json"), encoding="utf-8"))
    tr = json.load(open(trace_path, encoding="utf-8"))
    acc = json.load(open(accuracy_path, encoding="utf-8"))
    meta = json.load(open(os.path.join(ROOT, "data", "_geo_meta.json"), encoding="utf-8"))

    pts = tr["trace"]
    x0, y0, x1, y1 = clip_bbox(pts)
    flat = net["shapes"]
    streets = net["streets"]

    def shape_of(e):
        off, n = e[5], e[6]
        return [[flat[2 * (off + i)], flat[2 * (off + i) + 1]] for i in range(n)]

    edges = []
    kept_shapes = []
    remap = {}
    for e in net["edges"]:
        sti, ln, lanes = e[1], e[2], e[4]
        name = streets[sti] if isinstance(sti, int) and sti < len(streets) else ""
        sx = shape_of(e)
        if not sx:
            continue
        inside = any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in sx)
        if not inside:
            continue
        key = json.dumps(sx)
        if key not in remap:
            remap[key] = len(kept_shapes)
            kept_shapes.append(sx)
        edges.append({
            "s": remap[key],
            "st": name,
            "l": round(ln, 1),
            "n": lanes,
            "c": 1 if "أنس بن مالك" in name else 0,
        })

    # المسار: زمن فعلي + سرعة مشتقّة من الموضع (الـ<sog> في السجل غير موثوق)
    R = 6371008.8
    def hav(a, b):
        import math
        p1, p2 = math.radians(a[1]), math.radians(b[1])
        dp = p2 - p1
        dl = math.radians(b[0] - a[0])
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * R * math.asin(math.sqrt(h))

    t0 = pts[0]["e"]
    tp, sp = [], []
    for i, p in enumerate(pts):
        if i == 0:
            v = 0.0
        else:
            dts = max(1e-3, p["e"] - pts[i - 1]["e"])
            v = 3.6 * hav((pts[i - 1]["lon"], pts[i - 1]["lat"]), (p["lon"], p["lat"])) / dts
        sp.append(v)
        tp.append([p["e"] - t0, round(p["lon"], 6), round(p["lat"], 6), 0.0,
                   round(p.get("dev", 0.0), 1)])
    win = 3
    for i in range(len(sp)):
        w = sp[max(0, i - win):i + win + 1]
        tp[i][3] = round(sum(w) / len(w), 1)

    span_s = pts[-1]["e"] - t0
    kpis = [
        {"value": "%.1f" % acc["accuracy_agg_pct"], "unit": "%",
         "label": "دقة المحاكاة في طول المسار",
         "foot": "خطأ تراكمي %.2f%% على %d مقطعًا متصلًا" % (acc["agg_err_pct"], acc["stretches"])},
        {"value": "%.1f" % acc["dev_median_m"], "unit": "م",
         "label": "وسيط انحراف المسار", "foot": "p90 %.1f م · أقصى %.1f م" % (acc["dev_p90_m"], acc["dev_max_m"])},
        {"value": "%d" % acc["within_10pct_stretches"], "unit": "من %d" % acc["stretches"],
         "label": "مقاطع ضمن ±10%", "foot": "أسوأ %.1f%% · أفضل %.1f%%" % (acc["worst_err_pct"], acc["best_err_pct"])},
        {"value": "%.1f" % (span_s / 3600.0), "unit": "ساعة",
         "label": "مدة القياس الميداني على الممر",
         "foot": "%d نقطة متصلة · جولات متعددة في جلسة قياس واحدة" % acc["points"]},
    ]

    out = {
        "generated": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "corridor": "شارع أنس بن مالك",
        "corridor_km": meta.get("corridor_km"),
        "bbox": [round(x0, 6), round(y0, 6), round(x1, 6), round(y1, 6)],
        "streets": sorted({e["st"] for e in edges if e["st"]}),
        "edges": edges,
        "shapes": kept_shapes,
        "trace": {"n": len(tp), "t0": t0, "t1": pts[-1]["e"], "span": pts[-1]["e"] - t0, "p": tp},
        "junction": meta["junction"],
        "uturn": meta["uturn"],
        "kpis": kpis,
        "source": {
            "trace": os.path.basename(trace_path),
            "accuracy": os.path.basename(accuracy_path),
            "net": acc.get("net"),
            "engine": acc.get("engine"),
            "net_sha16": acc.get("net_sha16"),
        },
        "totals": {
            "field_m": acc["field_m"], "net_m": acc["net_m"], "agg_err_pct": acc["agg_err_pct"],
            "analysed_km": acc["analysed_km"], "analysed_share_pct": acc["analysed_share_of_dense_pct"],
            "stretches": acc["stretches"], "points": acc["points"], "gaps": acc["gaps_count"],
            "field_kmh": acc["field_kmh"], "mape_pct": acc["mape_pct"],
        },
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace")
    ap.add_argument("--accuracy")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "anas.json"))
    a = ap.parse_args()
    d = build(a.trace, a.accuracy)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print("anas.json edges=%d shapes=%d pts=%d kpis=%d bytes=%d"
          % (len(d["edges"]), len(d["shapes"]), d["trace"]["n"], len(d["kpis"]), os.path.getsize(a.out)))


if __name__ == "__main__":
    main()
