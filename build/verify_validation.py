"""بوابة أرقام صفحة «التحقق الميداني» — تفشل (exit 3) إن خالف أي رقم خط الإنتاج.

الفحوص:
 1. data/validation.json يساوي إعادةَ بناء من data/accuracy_final.json (لا رقم مُدخل يدوياً).
 2. الاتساق الرياضي: accuracy = 100 - |agg_err|، والمجاميع تساوي مجموع المقاطع.
 3. قسم #view-validation في index.html لا يحمل أي رقم مكتوب بيد (لا [0-9] خارج السماح).
 4. validation.js لا يحمل رقماً قياسياً (يقرأ من JSON وحده).
 5. ملف الفيديو موجود وبالحجم والبصمة المعلنة.
 6. كل KPI له قيمة ووحدة وتسمية وهامش (لا خانة فارغة).
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from build.build_validation import build  # noqa: E402

FAIL = []


def bad(tag, msg):
    FAIL.append("%s: %s" % (tag, msg))


def close(a, b, tol=0.05):
    return abs(float(a) - float(b)) <= tol


def main():
    data_path = os.path.join(ROOT, "data", "validation.json")
    on_disk = json.load(open(data_path, encoding="utf-8"))
    rebuilt = build()
    if json.loads(json.dumps(rebuilt)) != on_disk:
        bad("stale", "data/validation.json ليس ناتج البناء الحالي — أعد تشغيل build/build_validation.py")

    v = on_disk
    t = v["totals"]

    # 2. الاتساق الرياضي
    if not close(100 - abs(t["agg_err_pct"]), t["accuracy_pct"], 0.06):
        bad("math", "accuracy != 100-|err| (%s vs %s)" % (t["accuracy_pct"], t["agg_err_pct"]))
    s_field = round(sum(r["field_m"] for r in v["stretches"]), 1)
    s_net = round(sum(r["net_m"] for r in v["stretches"]), 1)
    if not close(s_field, t["field_m"], 0.11):
        bad("math", "مجموع الميدان %s != %s" % (s_field, t["field_m"]))
    if not close(s_net, t["net_m"], 0.11):
        bad("math", "مجموع الشبكة %s != %s" % (s_net, t["net_m"]))
    err = (t["net_m"] - t["field_m"]) / t["field_m"] * 100
    if not close(err, t["agg_err_pct"], 0.02):
        bad("math", "الخطأ المشتق %.3f != %s" % (err, t["agg_err_pct"]))
    if len(v["stretches"]) != len(json.load(open(os.path.join(ROOT, "data", "accuracy_final.json"),
                                                encoding="utf-8"))["detail"]):
        bad("math", "عدد المقاطع لا يساوي عدد مقاطع المصدر")

    # 3. لا أرقام مكتوبة بيد في الصفحة (تُستثنى المعرّفات والأنماط والبنية)
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'<section class="view" id="view-validation">(.*?)</section>', html, re.S)
    if not m:
        bad("html", "قسم #view-validation غير موجود")
    else:
        sect = re.sub(r"<[^>]+>", " ", m.group(1))          # النص الظاهر فقط
        digits = re.findall(r"\d+(?:[.,]\d+)?", sect)
        allow = {"1", "2", "3", "4"}                        # g2/g4 ليست نصاً؛ السماح أشكال البنية
        leftovers = [d for d in digits if d not in allow]
        if leftovers:
            bad("html", "أرقام مكتوبة بيد في قسم التحقق: %s" % sorted(set(leftovers)))

    # 4. JS لا يحمل قيماً قياسية
    js = open(os.path.join(ROOT, "assets", "validation.js"), encoding="utf-8").read()
    code = re.sub(r"//.*", "", js)
    code = re.sub(r'style="[^"]*"', " ", code)          # قيم التنسيق ليست قياساً
    code = re.sub(r"\d+(?:px|%|em|rem|pt)", " ", code)   # وحدات التنسيق
    for num in re.findall(r"(?<![\w.])(\d{2,}(?:\.\d+)?)", code):
        bad("js", "رقم قياسي مكتوب في validation.js: %s" % num)

    # 5. الفيديو
    vp = os.path.join(ROOT, v["video"]["src"])
    if not os.path.exists(vp):
        bad("video", "المقطع غير موجود: %s" % v["video"]["src"])
    else:
        sz = os.path.getsize(vp)
        if sz != v["video"]["bytes"]:
            bad("video", "حجم المقطع %d != %d" % (sz, v["video"]["bytes"]))
        h16 = hashlib.sha256(open(vp, "rb").read()).hexdigest()[:16]
        if h16 != v["video"]["sha16"]:
            bad("video", "بصمة المقطع %s != %s" % (h16, v["video"]["sha16"]))

    # 6. اكتمال البطاقات
    for i, k in enumerate(v["kpis"]):
        for f in ("value", "unit", "label", "foot"):
            if not str(k.get(f, "")).strip():
                bad("kpi", "البطاقة %d ينقصها الحقل %s" % (i, f))
    if len(v["kpis"]) != 4:
        bad("kpi", "عدد البطاقات %d != 4" % len(v["kpis"]))

    # 7. README لا ينحرف عن الأرقام
    rd = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    cov = [k for k in v["kpis"] if "مطابقة" in k["label"]][0]["value"]
    for need in ("%.1f%%" % t["accuracy_pct"],
                 "%.1f%%" % float(cov),
                 "%.1f%%" % t["uncapped_accuracy_pct"],
                 "{:,.1f}".format(t["field_m"]),
                 "{:,.1f}".format(t["net_m"]),
                 "%.1f%%" % abs(t["agg_err_pct"]),
                 "أسوأ %s%%" % [k for k in v["kpis"] if "متوسط الخطأ" in k["label"]][0]["foot"]
                 .split("أسوأ ")[1].split("%")[0]):
        if need not in rd:
            bad("readme", "README لا يحمل الرقم الحالي %s" % need)

    if FAIL:
        print("FAIL %d" % len(FAIL))
        for f in FAIL:
            print(" -", f)
        return 3
    print("OK kpis=%d stretches=%d acc=%.1f%% uncapped=%.1f%% video=%d B"
          % (len(v["kpis"]), len(v["stretches"]), t["accuracy_pct"],
             t["uncapped_accuracy_pct"], v["video"]["bytes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
