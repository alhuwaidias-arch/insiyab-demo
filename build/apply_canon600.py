#!/usr/bin/env python3
"""يُعيد بناء data/solutions.json على «مصفوفة العتبة الواحدة» (ttt = 600 ث).

لماذا: النقل القسري عند 300 ث كان يُفرّغ الطوابير صناعيًّا، فكانت أي مقارنة بين
ذراع عند 300 وأخرى عند 600 باطلة. هنا كل الأذرع على 600، والتكلفة تُقاس
**مقترنة بالمركبة** (Δ زمن الرحلة) لا بفرق متوسطات أذرع مختلفة الطلب.

المدخلات: runs/results.csv + analysis/qa_v7/CANON600.json
المخرج : data/solutions.json  (هو المصدر الوحيد لأرقام تبويب «الحلول»)
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
import os
import statistics as st

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # insiyab-demo/
PROJ = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))       # projects/insiyab/
CANON = os.path.join(PROJ, "tasks", "003_prototype-and-pitch", "analysis", "qa_v7", "CANON600.json")
OUT = os.path.join(HERE, "data", "solutions.json")

TAGS = {"baseline": "canon600", "closure": "closure600b", "detour": "detour600",
        "uturn": "uturn600", "works": "works300"}   # works300 مبنيّ عند 600 ث (اسم تاريخي)


def rows():
    p = os.path.join(PROJ, "runs", "results.csv")
    return list(csv.DictReader(open(p, encoding="utf-8")))


def arm_stats(allrows, tag):
    sel = [r for r in allrows if r["dir"].endswith(tag)]
    if not sel:
        return None
    def f(k):
        v = [float(r[k]) for r in sel if r.get(k)]
        return st.mean(v) if v else None
    return {"tag": tag, "n": len(sel),
            "dur_min": round(f("duration_mean_min"), 2),
            "dur_sd": round(st.pstdev([float(r["duration_mean_min"]) for r in sel]), 2),
            "speed_kmh": round(f("speed_mean_kmh") or 0, 1),
            "route_km": round((f("route_length_mean_m") or 0)/1000, 2),
            "trips": int(f("trips") or 0),
            "wait_h": round(f("waiting_mean_s") * f("trips") / 3600) if f("waiting_mean_s") else None,
            "runs": sorted(r["dir"] for r in sel)}


def main():
    old = json.load(open(OUT, encoding="utf-8"))
    canon = json.load(open(CANON, encoding="utf-8"))
    allrows = rows()

    arms = {}
    for key, tag in TAGS.items():
        s = arm_stats(allrows, tag)
        if s:
            arms[key] = {**old["arms"].get(key, {}), **s}
        elif key in old["arms"]:
            # لا تشغيل بعد على العتبة الجديدة: نُبقي القديم صريحًا (لا نُنشئ ذراعًا وهميًّا)
            arms[key] = dict(old["arms"][key])
            print(f"  !! {key}: لا تشغيل {tag} — أُبقي على المعطى السابق ({arms[key]['dur_min']} د)")

    # مقام واحد لكل الأذرع: شبكة المُطبَّق (1,603 ضلعًا) — لا خلط مقامات شبكات مختلفة
    NET_EDGES = 1603
    for a in arms.values():
        if a.get("edges_hit"):
            a["edges_total"] = NET_EDGES
            a["edges_pct"] = round(100.0 * a["edges_hit"] / NET_EDGES, 1)

    base = arms["baseline"]["dur_min"]
    for k, a in arms.items():
        a["d_min"] = round(a["dur_min"] - base, 2)

    # التكلفة المقترنة (Δ زمن رحلة لكل نافذة ذروة) من CANON600
    pair_works = canon["arms"].get("works", {})
    pair_closure = canon["arms"].get("closure", {})
    works_vh = round(pair_works.get("dur_h_mean", 0))
    closure_vh = round(pair_closure.get("dur_h_mean", 0))
    share = round(100.0 * works_vh / closure_vh) if closure_vh else None

    d = dict(old)
    d["test"] = {**old.get("test", {}), "ttt_s": 600, "seeds": 5, "network_edges": NET_EDGES,
                 "criterion": "ساعات زمن الرحلة المضافة (Δduration) — مقارنة مقترنة بالمركبة",
                 "trips": int(arms["baseline"]["trips"]),
                 "note": "كل الأذرع عند time-to-teleport = 600 ث؛ لا تُنقل مركبة قسرًا في خط الأساس."}
    d["sources"] = {**old.get("sources", {}),
                    "numbers": "analysis/qa_v7/CANON600.json",
                    "method": "analysis/make_canon600.py"}
    d["generated"] = datetime.now().astimezone().isoformat(timespec="seconds")
    d["net_edges"] = 8486     # المرسوم داخل نطاق الخريطة؛ net.xml فيه 8,488 واثنان خارج الإطار
    d["arms"] = arms
    d["paired"] = {"works": pair_works, "closure": pair_closure,
                   "works_share_of_closure_pct": share}
    dd = old.get("display", {})
    du = arms.get("uturn", {}).get("dur_min")
    dt = arms.get("detour", {}).get("dur_min")
    disp = {**dd,
            "added_vh": f"{closure_vh:,}",
            "half_vh": f"{works_vh:,}",
            "detour_vh": None, "_detour_vh_old": f"{round(pair_closure.get('dur_h_mean', 0)):,}",
            # ساعات التأخير للدوران/التحويلة غير مقيسة (زمن الرحلة وحده) ⇒ لا تُقدَّر بالتناسب
            "uturn_vh": None,
            "uturn_ratio": round(du / base, 1) if du else dd.get("uturn_ratio"),
            "detour_pct": f"{abs(round(100 * (dt - arms['closure']['dur_min']) / arms['closure']['dur_min']))}%" if dt and "closure" in arms else dd.get("detour_pct"),
            "cost_low_k": round(closure_vh * 32 * 1.0 / 1000),
            "cost_high_k": round(closure_vh * 32 * 1.3 / 1000),
            "trips": f"{arms['baseline']['trips']:,}",
            "works_share_pct": share,
            }
    d["display"] = {**disp,
                    "base_min": f"{base:.0f}",
                    "closure_min": f"{arms['closure']['dur_min']:.0f}" if "closure" in arms else old["display"]["closure_min"],
                    "extra_min": f"+{arms['closure']['dur_min'] - base:.0f}" if "closure" in arms else old["display"]["extra_min"],
                    "closure_vh": closure_vh,
                    "works_vh": works_vh,
                    "works_min": f"+{arms['works']['d_min']:.1f}" if "works" in arms else old["display"]["works_min"],
                    "works_share_pct": share,
                    "stays_pct": f"{round(100 * (1 - pair_works.get('share_unaffected_mean', 0.25)))}%",
                    "labelled_threshold": "600 ث",
                    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("wrote", OUT)
    for k in ("baseline", "closure", "detour", "uturn", "works"):
        if k in arms:
            a = arms[k]
            print(f"  {k:9s} {a['tag']:12s} n={a['n']} dur={a['dur_min']:.2f}±{a['dur_sd']:.2f} "
                  f"d={a['d_min']:+.2f} speed={a['speed_kmh']} trips={a['trips']}")
    print(f"paired: works {works_vh} h | closure {closure_vh} h | share {share}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
