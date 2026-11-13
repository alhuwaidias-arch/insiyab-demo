#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انسياب — بناء بيانات النموذج من مجلدات التشغيل الخام.

يقود كل رقم في الواجهة إلى مجلد تشغيله:
  data/canon.json    أرقام مرجعية موثّقة + مصدرها (تُفحص آليًا في tests/)
  data/arms.json     الأذرع المقيسة: لكل بذرة وللمتوسط ± الانحراف
  data/damage.json   تأخير مضاف لكل ضلع/شارع (كاشف انتقال الضرر)
  data/trips.json    توزيع أزمنة الرحلات ومتوسطها حسب نافذة الإقلاع

المصدر: <MODEL>/runs (SUMO 1.27.0). لا يُكتب رقم هنا بلا مجلد تشغيل.
"""
import csv, glob, json, os, re, statistics as st, hashlib, sys, datetime
import xml.etree.ElementTree as ET

MODEL = os.environ.get("INSIYAB_MODEL", r"D:\INFIRAD\projects\insiyab")
RUNS = os.path.join(MODEL, "runs")
OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(OUTDIR, exist_ok=True)

TAGS = {
    "baseline": "canon300",
    "closure": "closure300",
    "detour": "detour300",
    "policy600": "canon27",
}
DAMAGE = {"closure": "damage_closure300", "detour": "damage_detour300", "identity": "damage_identity"}


def sha16(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:16]


def sd(xs):
    return st.stdev(xs) if len(xs) > 1 else 0.0


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


# ---------------------------------------------------------------- runs table
rows = list(csv.DictReader(open(os.path.join(RUNS, "results.csv"), encoding="utf-8-sig")))
runs = {k: [] for k in TAGS}
for r in rows:
    d = r["dir"]
    for arm, tag in TAGS.items():
        if d.endswith("_" + tag) and r["status"] == "ok":
            runs[arm].append(r)
for arm in runs:
    runs[arm].sort(key=lambda r: int(r["seed"]))

# corridor metric (الرقم المنشور) — من ملف الفهرس الرسمي
def corridor(path):
    out = []
    if not os.path.exists(path):
        return out
    for row in csv.DictReader(open(path, encoding="utf-8-sig")):
        out.append({k: (float(v) if re.match(r"^-?\d+(\.\d+)?$", (v or "").strip()) else v)
                    for k, v in row.items()})
    return out

corr = {"baseline": corridor(os.path.join(RUNS, "corridor_canon300.csv")),
        "policy600": corridor(os.path.join(RUNS, "corridor_canon27.csv"))}

METRIC_FIELDS = [
    ("duration_mean_min", "زمن الرحلة (دقيقة)", "د"),
    ("speed_mean_kmh", "سرعة الرحلة (كم/س)", "كم/س"),
    ("timeloss_mean_s", "زمن الضياع (ثانية)", "ث"),
    ("waiting_mean_s", "زمن الانتظار (ثانية)", "ث"),
    ("route_length_mean_m", "طول المسار (متر)", "م"),
    ("trips", "رحلات مكتملة", "رحلة"),
    ("teleports", "نقل قسري (مركبة)", "مركبة"),
]

arms = {}
for arm, rr in runs.items():
    if not rr:
        continue
    per_seed = []
    for r in rr:
        m = {"seed": int(r["seed"]), "dir": r["dir"]}
        for f, _, _ in METRIC_FIELDS:
            m[f] = float(r[f]) if f == "duration_mean_min" else int(float(r[f]))
        m["ttt"] = float(r["time_to_teleport"])
        m["teleport_jam"] = json.loads(r["teleport_reasons"].replace('""', '"')).get("jam", 0) \
            if r.get("teleport_reasons") else 0
        per_seed.append(m)
    stats = {}
    for f, label, unit in METRIC_FIELDS:
        xs = [p[f] for p in per_seed]
        stats[f] = {"label": label, "unit": unit, "mean": round(mean(xs), 2), "sd": round(sd(xs), 2),
                    "values": xs}
    cm = None
    if corr.get(arm):
        dv = [c["corridor_mean_min"] for c in corr[arm] if isinstance(c.get("corridor_mean_min"), float)]
        if dv:
            cm = {"label": "زمن عبور الممر (>7 كم)", "unit": "دقيقة",
                  "mean": round(mean(dv), 2), "sd": round(sd(dv), 2),
                  "values": [round(v, 2) for v in dv],
                  "file": f"runs/corridor_{TAGS[arm]}.csv"}
    arms[arm] = {"tag": TAGS[arm], "ttt": per_seed[0]["ttt"], "n": len(per_seed),
                 "seeds": per_seed, "stats": stats, "corridor": cm,
                 "net": f"runs results.csv → {TAGS[arm]}"}

# ---------------------------------------------------------------- damage sets
damage = {}
for arm, prefix in DAMAGE.items():
    p = os.path.join(RUNS, prefix + ".edges.csv")
    if not os.path.exists(p):
        continue
    edges, streets = [], {}
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        av = float(r["added_vh"])
        edges.append([r["edge"], r["street"], round(av, 2),
                      round(float(r["delta_timeloss_s"]), 1),
                      round(float(r["entered_base"]), 0), round(float(r["entered_arm"]), 0)])
        s = streets.setdefault(r["street"], {"street": r["street"], "added_vh": 0.0, "edges": 0})
        s["added_vh"] += av
        s["edges"] += 1
    st_rows = sorted(streets.values(), key=lambda s: -s["added_vh"])
    for s in st_rows:
        s["added_vh"] = round(s["added_vh"], 1)
    pos = [e for e in edges if e[2] > 0]
    total_pos = sum(e[2] for e in pos)
    total_neg = sum(e[2] for e in edges if e[2] < 0)
    damage[arm] = {
        "file": f"runs/{prefix}.edges.csv", "sha16": sha16(p),
        "edges_total": len(edges), "edges_hit": len(pos),
        "added_vh_positive": round(total_pos, 1),
        "recovered_vh": round(-total_neg, 1),
        "net_vh": round(total_pos + total_neg, 1),
        "streets": st_rows[:40],
        "top_edges": sorted(pos, key=lambda e: -e[2])[:120],
        "edges": edges,
        "empty_edges": sum(1 for e in edges if e[4] > 0 and e[5] == 0),
    }

# ---------------------------------------------------------------- tripinfo
BUCKET = 900      # 15 min
HIST = 120        # 2-min duration bins up to 120 min

def trip_stats(dirpath, arm):
    tp = os.path.join(RUNS, dirpath, "tripinfo.xml")
    if not os.path.exists(tp):
        return None
    dur, dep_bins, arr_bins = [], {}, {}
    for ev, el in ET.iterparse(tp, events=("end",)):
        if el.tag != "tripinfo":
            continue
        d = float(el.get("duration")) / 60.0
        dep = float(el.get("depart"))
        dur.append(d)
        b = int(dep // BUCKET)
        dep_bins.setdefault(b, []).append(d)
        arr_bins[int((dep + float(el.get("duration"))) // BUCKET)] = \
            arr_bins.get(int((dep + float(el.get("duration"))) // BUCKET), 0) + 1
        el.clear()
    hist = [0] * HIST
    for d in dur:
        i = min(HIST - 1, int(d // 2))
        hist[i] += 1
    return {"n": len(dur),
            "mean": round(mean(dur), 2), "sd": round(sd(dur), 2),
            "p50": round(st.median(dur), 2),
            "p95": round(sorted(dur)[int(0.95 * (len(dur) - 1))], 2),
            "hist": hist,
            "by_depart": [[b * BUCKET / 60, round(mean(v), 2), len(v)] for b, v in sorted(dep_bins.items())],
            "by_arrive": [[b * BUCKET / 60, c] for b, c in sorted(arr_bins.items())]}

trips = {}
for arm, rr in runs.items():
    per = []
    for r in rr:
        t = trip_stats(r["dir"], arm)
        if t:
            t["seed"] = int(r["seed"])
            t["dir"] = r["dir"]
            per.append(t)
    if not per:
        continue
    # متوسط منحنيات الإقلاع على البذور (نافذة موحّدة)
    keys = sorted({b for t in per for b, _, _ in t["by_depart"]})
    curve = []
    for k in keys:
        vals = [m for t in per for b, m, _ in t["by_depart"] if b == k]
        cnt = [c for t in per for b, _, c in t["by_depart"] if b == k]
        curve.append([k, round(mean(vals), 2), int(mean(cnt))])
    hist = [round(mean([t["hist"][i] for t in per]), 1) for i in range(HIST)]
    trips[arm] = {"bucket_min": BUCKET / 60, "hist_bin_min": 2,
                  "mean": round(mean([t["mean"] for t in per]), 2),
                  "hists": {str(t["seed"]): t["hist"] for t in per},
                  "hist": hist, "curve": curve}

# ---------------------------------------------------------------- canon
CANON = {
    "network": {"edges": 8488, "lanes": 38696, "bytes": 23905165,
                "source": "data/network/insyab.net.xml (بعد رقعة U-turn)",
                "evidence": "07_evidence/BASELINE_FACTS.md §1"},
    "engine": "Eclipse SUMO 1.27.0",
    "policy": {"time_to_teleport": 300, "sim_end_s": 14400, "dial": 8.0, "seeds": [1, 2, 3, 4, 5]},
    "numbers": [
        {"id": "corridor_baseline", "label": "زمن عبور الممر (خط الأساس)", "value": 22.85, "sd": 1.97,
         "unit": "دقيقة", "arm": "baseline", "field": "corridor",
         "evidence": "runs/corridor_canon300.csv · BASELINE_FACTS.md §2.1"},
        {"id": "fleet_baseline", "label": "زمن رحلة الأسطول (خط الأساس)", "value": 19.18, "sd": 1.44,
         "unit": "دقيقة", "arm": "baseline", "field": "duration_mean_min",
         "evidence": "runs/*_canon300/metrics.json · INTERVENTION_FACTS.md §2"},
        {"id": "fleet_closure", "label": "زمن رحلة الأسطول (بعد الإغلاق)", "value": 36.04, "sd": 1.52,
         "unit": "دقيقة", "arm": "closure", "field": "duration_mean_min",
         "evidence": "runs/*_closure300/metrics.json · INTERVENTION_FACTS.md §2"},
        {"id": "delay_added", "label": "تأخير مضاف على الشبكة", "value": 1726.1, "sd": 297.0,
         "unit": "مركبة-ساعة", "arm": "closure", "field": "added_vh_positive",
         "evidence": "INTERVENTION_FACTS.md §3 (طريقتان متطابقتان 97.6%)"},
        {"id": "damage_net", "label": "صافي تأخير الأضلاع", "value": 1777.7, "sd": None,
         "unit": "مركبة-ساعة", "arm": "closure", "field": "net_vh",
         "evidence": "runs/damage_closure300.edges.csv · INTERVENTION_FACTS.md §4"},
        {"id": "recovered", "label": "ما استُرد على شوارع أخرى", "value": 207.4, "sd": None,
         "unit": "مركبة-ساعة", "arm": "closure", "field": "recovered_vh",
         "evidence": "runs/damage_closure300.edges.csv"},
        {"id": "detour_net", "label": "صافي التأخير بعد التحويلة المدعومة", "value": 1697.1, "sd": None,
         "unit": "مركبة-هour", "arm": "detour", "field": "net_vh",
         "evidence": "runs/damage_detour300.edges.csv · DETOUR_ARMS.md"},
        {"id": "corridor_policy600", "label": "زمن عبور الممر (سياسة ttt 600)", "value": 32.81, "sd": 4.79,
         "unit": "دقيقة", "arm": "policy600", "field": "corridor",
         "evidence": "runs/corridor_canon27.csv · BASELINE_FACTS.md §4"},
        {"id": "economics_rate", "label": "قيمة ساعة المركبة", "value": 32.03, "sd": None,
         "unit": "ريال/مركبة-ساعة", "arm": None, "field": None,
         "evidence": "ECONOMIC_IMPACT.md · SHC 203 ص75 جدول 4-2 (نصف أجر الساعة)"},
    ],
    "banned": ["20.3 → 41.0", "+122%", "3,183 مركبة-ساعة", "الأماسي 64.5 → 4.6",
               "9.91 كم/س (متوسط سرعة الشبكة)", "8,485 ضلعًا"],
    "limits": [
        "لا معايرة ميدانية على زمن رحلة مقيس لهذا المقطع؛ الرقم داخلي صالح للمقارنة لا للتنبؤ المطلق.",
        "tls.all-off=true: لا إشارات في الشبكة — أُزيلت واقعًا قبل نحو سنة. لا ادعاء إعادة توقيت.",
        "التوجيه بأقصر مسار زمن حرّ عند الإدخال، لا توازن ديناميكي ⇒ مقدار «انتقال الضرر» حدّ أدنى محافظ.",
        "6.2% نقل قسري (teleport) بعد 300 ث انتظار ⇒ التأخير الحقيقي أعلى من المقيس.",
        "أفق 4 ساعات (ذروة + تصريف)، ممر واحد 9.4 كم — لا يُعمَّم على الرياض.",
        "شبكة مبسّطة: بلا مشاة ولا إشارات، 8,488 ضلعًا.",
    ],
}

meta = {
    "built": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "model_root": MODEL,
    "engine": "Eclipse SUMO 1.27.0",
    "generator": "build/extract_arms.py",
    "sources": {
        "results.csv": {"sha16": sha16(os.path.join(RUNS, "results.csv"))},
        "net": {"sha16": sha16(os.path.join(MODEL, "data/network/insyab.net.xml"))},
    },
}

for name, payload in [("arms", {"arms": arms, "generated": meta["built"]}),
                      ("damage", {"damage": damage, "generated": meta["built"]}),
                      ("trips", {"trips": trips, "generated": meta["built"]}),
                      ("canon", CANON), ("meta", meta)]:
    with open(os.path.join(OUTDIR, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

print("arms:", {k: (v["n"], v["stats"]["duration_mean_min"]["mean"]) for k, v in arms.items()})
print("damage:", {k: (v["added_vh_positive"], v["net_vh"], v["recovered_vh"], v["edges_hit"]) for k, v in damage.items()})
for k, v in damage.items():
    print(" ", k, "top streets:", [(s["street"][:28], s["added_vh"]) for s in v["streets"][:4]])
print("trips:", {k: (len(v["curve"]), v["mean"]) for k, v in trips.items()})
for f in sorted(os.listdir(OUTDIR)):
    print("  ", f, os.path.getsize(os.path.join(OUTDIR, f)))
