"""refresh_anas_kpis.py — يعيد بناء kpis في data/anas.json من الملفين المولَّدين
(anas.json نفسه + data/accuracy_anas.json) بنفس صيغ build/build_anas.py.

يُستخدم فقط حين لا يكون ملف الأثر الخام (trace_anas.json) موجودًا محليًّا.
كل قيمة تُحسب من البيانات، ولا رقم مكتوب بيد.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANAS = os.path.join(ROOT, "data", "anas.json")
ACC = os.path.join(ROOT, "data", "accuracy_anas.json")


def main():
    d = json.load(open(ANAS, encoding="utf-8"))
    acc = json.load(open(ACC, encoding="utf-8"))
    t = d["trace"]
    span_s = t["t1"] - t["t0"]
    d["kpis"] = [
        {"value": "%.1f" % acc["accuracy_agg_pct"], "unit": "%",
         "label": "دقة المحاكاة في طول المسار",
         "foot": "خطأ تراكمي %.2f%% على %d مقطعًا متصلًا" % (acc["agg_err_pct"], acc["stretches"])},
        {"value": "%.1f" % acc["dev_median_m"], "unit": "م",
         "label": "وسيط انحراف المسار",
         "foot": "p90 %.1f م · أقصى %.1f م" % (acc["dev_p90_m"], acc["dev_max_m"])},
        {"value": "%d" % acc["within_10pct_stretches"], "unit": "من %d" % acc["stretches"],
         "label": "مقاطع ضمن ±10%",
         "foot": "أسوأ %.1f%% · أفضل %.1f%%" % (acc["worst_err_pct"], acc["best_err_pct"])},
        {"value": "%.1f" % (span_s / 3600.0), "unit": "ساعة",
         "label": "مدة القياس الميداني على الممر",
         "foot": "%d نقطة متصلة · جولات متعددة في جلسة قياس واحدة" % acc["points"]},
    ]
    with open(ANAS, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print("anas.json kpis refreshed: " + " | ".join(k["value"] + " " + k["unit"] for k in d["kpis"]))


if __name__ == "__main__":
    main()
