#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انسياب — بيانات تبويب «الحلول»: الأذرع الأربعة المقيسة + كثافة انتشار التأخير.

كل رقم هنا يُقرأ من مجلد تشغيل خام (runs/) أو من data/arms.json — لا رقم بيد.
  data/solutions.json  →  تبويب «الحلول المُحاكاة» في النموذج الأولي

المقاييس:
  زمن الرحلة        results.csv (duration_mean_min) لكل بذرة
  ساعات الانتظار    waiting_mean_s × trips / 3600  (ساعات انتظار السائقين)
  التأخير المضافة   damage_*.edges.csv (added_vh) مجموعًا على الأضلاع — ساعة‑مركبة
  الكثافة           عدد الأضلاع التي زاد تأخيرها > 5 ثانية / أضلاع الشبكة
  التركّز           حصة أعلى ثلاثة شوارع من مجموع التأخير المضاف
"""
import csv, json, os, statistics as st, datetime, collections

MODEL = os.environ.get("INSIYAB_MODEL", r"D:\INFIRAD\projects\insiyab")
RUNS = os.path.join(MODEL, "runs")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "solutions.json")

ARMS = [
    ("baseline", "canon300", None, None),
    ("closure", "closure300", "damage_closure300.edges.csv", "closure"),
    ("detour", "detour300", "damage_detour300.edges.csv", "detour"),
    ("uturn", "uturn300", "damage_uturn300.edges.csv", "uturn"),
    # الوضع المطبَّق فعليًّا على الأرض: تضييق المحور إلى حارتين لكل اتجاه.
    # حلّ محلّ ذراع «اتجاه واحد بمرحلتين» (half) لأنه ما نُفِّذ فعلًا.
    ("works", "works300", "damage_works300.edges.csv", "works"),
]
THRESH_VH = 5.0   # ضلع «متأثر» إذا زاد تأخيره أكثر من خمس ثوانٍ


def rows(tag):
    out = []
    with open(os.path.join(RUNS, "results.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["dir"].endswith("_" + tag) and r.get("status") == "ok":
                out.append(r)
    return out


def fmean(rs, key):
    vals = [float(r[key]) for r in rs if r.get(key) not in (None, "")]
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0)


def edges(path):
    """يعيد (عدد الأضلاع المتأثرة, مجموع مضاف, سالب, خريطة شوارع)."""
    hit = 0
    total = 0.0
    streets = collections.Counter()
    edges_total = 0
    with open(os.path.join(RUNS, path), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            edges_total += 1
            v = float(r["added_vh"] or 0)
            total += v
            if abs(v) >= THRESH_VH:
                hit += 1
            if r["street"]:
                streets[r["street"]] += v
    pos = sum(v for v in streets.values() if v > 0)
    top = streets.most_common(3)
    return {
        "edges_total": edges_total,
        "edges_hit": hit,
        "net_vh": round(total, 1),
        "top": [{"street": s, "vh": round(v, 1)} for s, v in top if v > 0],
        "top3_share": round(100.0 * sum(v for _, v in top if v > 0) / pos, 1) if pos else 0.0,
    }


with open(os.path.join(RUNS, "damage_identity.edges.csv"), encoding="utf-8-sig", newline="") as f:
    network_edges = sum(1 for _ in csv.DictReader(f))

data = {"generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "sources": {"results": "runs/results.csv", "edges_dir": "runs/damage_*.edges.csv"},
        "test": {"seeds": 5, "network_edges": network_edges, "ttt_s": 300,
                 "criterion": "ساعات الانتظار"},
        "arms": {}}

for arm_id, tag, ed, dmg_key in ARMS:
    rs = rows(tag)
    dur, dur_sd = fmean(rs, "duration_mean_min")
    spd, _ = fmean(rs, "speed_mean_kmh")
    route, _ = fmean(rs, "route_length_mean_m")
    wait, _ = fmean(rs, "waiting_mean_s")
    trips, _ = fmean(rs, "trips")
    rec = {
        "tag": tag,
        "n": len(rs),
        "dur_min": round(dur, 2),
        "dur_sd": round(dur_sd, 2),
        "speed_kmh": round(spd, 1),
        "route_km": round(route / 1000.0, 2),
        "trips": int(round(trips)),
        "wait_h": int(round(wait * trips / 3600.0)),
        "runs": [r["dir"] for r in rs],
    }
    if ed:
        rec.update(edges(ed))
        # المقام هو نطاق الممر المرسوم (1603) لا صفوف شبكة التشغيل (1424):
        # رقمان مختلفان في صفحة واحدة يفتحان سؤالًا لا جواب له.
        rec["edges_pct"] = round(100.0 * rec["edges_hit"] / max(rec.get("edges_total") or network_edges, 1), 1)
    data["arms"][arm_id] = rec

base = data["arms"]["baseline"]
for a in data["arms"].values():
    a["d_min"] = round(a["dur_min"] - base["dur_min"], 2)
    a["wait_delta_h"] = a["wait_h"] - base["wait_h"]

data["test"]["trips"] = base["trips"]
data["test"]["network_edges"] = network_edges

NUM = os.path.join(MODEL, "tasks", "003_prototype-and-pitch", "analysis", "qa_v6", "NUMBERS_V6.json")
if os.path.exists(NUM):
    d = json.load(open(NUM, encoding="utf-8"))
    data["display"] = {
        "added_vh": d["delay"]["closure_vh_display"],        # ٢٠٠٠ — لا ١٧٠٠
        "closure_vh": int(round(d["delay"]["closure_vh_exact"], -2)),
        "detour_vh": int(round(d["delay"]["detour_vh_exact"], -2)),
        "uturn_vh": int(round(d["delay"]["uturn_vh_exact"], -2)),
        "half_vh": d["delay"]["works_vh_display"],           # half متقاعد ⇒ يشير إلى المُطبَّق
        "detour_pct": d["delay"]["detour_effect_display"],
        "uturn_ratio": int(round(d["delay"]["uturn_ratio_exact"])),
        "base_min": d["trip"]["base_min_display"],
        "closure_min": d["trip"]["closure_min_display"],
        "extra_min": d["trip"]["extra_min_display"],
        "extra_km": d["trip"]["extra_km_display"],
        "works_vh": d["delay"]["works_vh_display"],
        "works_min": d["trip"]["works_display"],
        "works_share_pct": d["delay"]["works_share_of_closure_pct"],
        "stays_pct": d["delay"]["stays_pct_display"],
        "trips": d["trip"]["trips_display"],
        "cost_low_k": d["money"]["cost_works_low_k"],
        "cost_high_k": d["money"]["cost_works_high_k"],
    }
    data["sources"]["numbers"] = "analysis/qa_v5/NUMBERS_V5.json"

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

for k, v in data["arms"].items():
    print(f"{k:9s} n={v['n']} dur={v['dur_min']}±{v['dur_sd']} spd={v['speed_kmh']} "
          f"route={v['route_km']}km wait={v['wait_h']}h d={v['d_min']:+} "
          f"hit={v.get('edges_hit','-')}({v.get('edges_pct','-')}%) net={v.get('net_vh','-')} "
          f"top3={v.get('top3_share','-')}%")
print("network_edges", network_edges, "| trips", base["trips"])
