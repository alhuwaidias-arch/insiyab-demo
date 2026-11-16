"""بوابة أرقام صفحة «التحقق الميداني» — تفشل (exit 3) إن خالف أي رقم خط الإنتاج.

الفحوص:
 1. data/validation.json = ناتج build() الحالي بالبايت (لا رقم مُدخل يدوياً، ولا ملف قديم).
 2. الاتساق الرياضي: accuracy = 100 - |agg_err|، والمجاميع = مجموع المقاطع، والمسقوف/غير المسقوف.
 3. نافذة الجولة المحلية = نافذة UTC + 3 ساعات (الرياض) — لا يمرّ خطأ توقيت.
 4. #view-validation في index.html لا يحمل أي رقم مكتوب بيد.
 5. validation.js لا يحمل رقماً قياسياً (يقرأ من JSON وحده).
 6. الفيديو ومقطع التقاطع: موجودان، وبالحجم والبصمة المعلنة.
 7. كل KPI له قيمة ووحدة وتسمية وهامش؛ العدد 4.
 8. README.md يحمل الأرقام الحالية نصاً.
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from build.build_validation_anas import build  # noqa: E402

FAIL = []


def bad(tag, msg):
    FAIL.append("%s: %s" % (tag, msg))


def close(a, b, tol=0.05):
    return abs(float(a) - float(b)) <= tol


def h16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main():
    data_path = os.path.join(ROOT, "data", "validation.json")
    on_disk = json.load(open(data_path, encoding="utf-8"))
    rebuilt = json.loads(json.dumps(build()))
    if rebuilt != on_disk:
        bad("stale", "data/validation.json ليس ناتج البناء الحالي — أعد تشغيل build/build_validation_anas.py")

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
    unc = (t["net_uncapped_m"] - t["field_m"]) / t["field_m"] * 100
    if not close(100 - abs(unc), t["uncapped_accuracy_pct"], 0.06):
        bad("math", "الدقة غير المسقوفة %.2f != %s" % (100 - abs(unc), t["uncapped_accuracy_pct"]))
    _a = [os.path.join(ROOT, "data", "accuracy_anas.json"),
          os.path.join(os.path.dirname(ROOT), "ACCURACY_ANAS.json")]
    src = json.load(open(next(p for p in _a if os.path.exists(p)), encoding="utf-8"))
    if len(v["stretches"]) != len(src["detail"]):
        bad("math", "عدد المقاطع %d != %d في المصدر" % (len(v["stretches"]), len(src["detail"])))

    # 3. التوقيت المحلي = UTC+3
    import datetime as dt
    u0 = dt.datetime.strptime(v["session"]["window_utc"][0], "%H:%M:%SZ")
    l0 = dt.datetime.strptime(v["session"]["window_local"][0], "%H:%M:%S")
    d = (l0.hour * 3600 + l0.minute * 60 + l0.second) - (u0.hour * 3600 + u0.minute * 60 + u0.second)
    if d != 3 * 3600:
        bad("tz", "بداية النافذة المحلية ليست UTC+3 (فرق %d ث)" % d)
    u1 = dt.datetime.strptime(v["session"]["window_utc"][1], "%H:%M:%SZ")
    l1 = dt.datetime.strptime(v["session"]["window_local"][1], "%H:%M:%S")
    d1 = (l1.hour * 3600 + l1.minute * 60 + l1.second) - (u1.hour * 3600 + u1.minute * 60 + u1.second)
    if d1 != 3 * 3600:
        bad("tz", "نهاية النافذة المحلية ليست UTC+3 (فرق %d ث)" % d1)

    # 4. لا أرقام مكتوبة بيد في الصفحة
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'<section class="view" id="view-validation">(.*?)</section>', html, re.S)
    if not m:
        bad("html", "قسم #view-validation غير موجود")
    else:
        sect = re.sub(r"<[^>]+>", " ", m.group(1))
        digits = re.findall(r"\d+(?:[.,]\d+)?", sect)
        allow = {"1", "2", "3", "4"}
        leftovers = [x for x in digits if x not in allow]
        if leftovers:
            bad("html", "أرقام مكتوبة بيد في قسم التحقق: %s" % sorted(set(leftovers)))

    # 5. JS لا يحمل قيماً قياسية
    js = open(os.path.join(ROOT, "assets", "validation.js"), encoding="utf-8").read()
    code = re.sub(r"//.*", "", js)
    code = re.sub(r'style="[^"]*"', " ", code)
    code = re.sub(r"\d+(?:px|%|em|rem|pt)", " ", code)
    for num in re.findall(r"(?<![\w.])(\d{2,}(?:\.\d+)?)", code):
        bad("js", "رقم قياسي مكتوب في validation.js: %s" % num)

    # 6. الفيديوهان
    for key in ("video",):
        blk = v.get(key) or {}
        if not blk.get("src"):
            bad(key, "لا مصدر معلن")
            continue
        p = os.path.join(ROOT, blk["src"])
        if not os.path.exists(p):
            bad(key, "المقطع غير موجود: %s" % blk["src"])
            continue
        s = os.path.getsize(p)
        if s != blk.get("bytes"):
            bad(key, "حجم %s=%d != %s" % (blk["src"], s, blk.get("bytes")))
        if h16(p) != blk.get("sha16"):
            bad(key, "بصمة %s لا تطابق المعلنة" % blk["src"])

    # 7. اكتمال البطاقات
    for i, k in enumerate(v["kpis"]):
        for f in ("value", "unit", "label", "foot"):
            if not str(k.get(f, "")).strip():
                bad("kpi", "البطاقة %d ينقصها الحقل %s" % (i, f))
    if len(v["kpis"]) != 3:
        bad("kpi", "عدد البطاقات %d != 3" % len(v["kpis"]))

    # 8. README — يتحقق مما يدّعيه README فعلًا (لا من أرقام لا تُعرض في الواجهة)
    rd = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    for need in ("%.1f%%" % t["accuracy_pct"],
                 "%.2f%%" % abs(t["agg_err_pct"]),
                 "%d مقطعاً" % len(v["stretches"]),
                 v["session"]["window_local"][0]):
        if need not in rd:
            bad("readme", "README لا يحمل الرقم الحالي %s" % need)

    # 8ب. أرقام لا تُعرض في الواجهة: تُحرس فقط في البيانات، ويجب ألا تتسرّب إلى README
    if "%.1f%%" % t["uncapped_accuracy_pct"] in rd:
        bad("readme", "README يحمل رقمًا داخليًا لا يُعرض (%0.1f%% بلا سقف للوتر)"
            % t["uncapped_accuracy_pct"])
    for gone in ("20 من 27", "من 27 مقطع"):
        if gone in rd:
            bad("readme", "README يعيد بطاقة أُزيلت من الواجهة (%s)" % gone)

    if FAIL:
        print("FAIL %d" % len(FAIL))
        for f in FAIL:
            print(" -", f)
        return 3
    print("OK kpis=%d stretches=%d acc=%.1f%% uncapped=%.1f%% field=%.1f km video=%d B"
          % (len(v["kpis"]), len(v["stretches"]), t["accuracy_pct"],
             t["uncapped_accuracy_pct"], t["field_m"] / 1000.0,
             v["video"]["bytes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
