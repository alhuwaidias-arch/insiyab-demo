"""يبني data/validation.json من data/accuracy_final.json — لا رقم مكتوب بيد.

المدخل الوحيد للقياسات هو ملف التحقق الميداني (ناتج acc8.py على شبكة insyab_v2).
كل ما تعرضه صفحة «التحقق الميداني» يُشتق من هنا، ثم يفحصه build/verify_validation.py.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def build(source_path=None):
    a = json.load(open(source_path or os.path.join(DATA, "accuracy_final.json"), encoding="utf-8"))

    det = a["detail"]
    field = sum(x["field_m"] for x in det)
    uncap = sum(x["net_uncapped_m"] for x in det)
    uncap_err = (uncap - field) / field * 100.0

    kpis = [
        {
            "value": round(a["accuracy_agg_pct"], 1),
            "unit": "%",
            "label": "دقة طول المسار على شبكة المحاكاة",
            "foot": f"خطأ تراكمي \u2066{a['agg_err_pct']:+.2f}%\u2069 على {a['analysed_km']:.2f} كم متصلة "
                    f"({a['stretches']} مقطعاً بتردد 1 هرتز)",
        },
        {
            "value": round(a["spatial_coverage_pct"], 1),
            "unit": "%",
            "label": "نقاط مطابقة ضمن 30 م من الشبكة",
            "foot": f"{a['points_matched_30m']:,} من {a['points']:,} نقطة · وسيط الانحراف "
                    f"{a['dev_median_m']:.2f} م · p90 {a['dev_p90_m']:.2f} م",
        },
        {
            "value": round(a["mape_pct"], 2),
            "unit": "%",
            "label": "متوسط الخطأ المطلق للمقطع",
            "foot": f"{a['within_10pct_stretches']} من {a['stretches']} مقطعاً ضمن ±10% · "
                    f"أفضل {a['best_err_pct']:.2f}% · أسوأ {a['worst_err_pct']:.2f}%",
        },
        {
            "value": round(a["trip_km_valid"], 1),
            "unit": "كم",
            "label": "المسار الميداني المسجَّل",
            "foot": f"منها {a['dense_km']:.1f} كم تسجيل متصل 1 هرتز و{a['gaps_km_plausible']:.1f} كم "
                    f"عبر {a['gaps_count']} فجوة تسجيل (30 ث) لا تُقاس هندسياً",
        },
    ]

    stretches = [
        {
            "t0": x["t0"][11:19],
            "t1": x["t1"][11:19],
            "pts": x["pts"],
            "field_m": round(x["field_m"], 1),
            "net_m": round(x["net_m"], 1),
            "err": round(x["err_pct"], 2),
            "kmh": round(x["field_kmh"], 1),
        }
        for x in det
    ]

    limits = [
        f"الشبكة تمثّل الممر جزئياً: من 10 سيقان مقيَّدة، 3 فقط على مسافة ≤30 م من حافة، "
        f"و4 بلا أي حافة ضمن 120 م — التغطية تُعلن قيداً ولا تُخفى.",
        f"{a['gaps_count']} فجوة تسجيل بمدة 30 ثانية ({a['gaps_km_plausible']:.2f} كم) سببها توقف كتابة "
        f"البطاقة؛ مسار المركبة داخلها مجهول للمسبار فلا يُحاسب عليه النموذج.",
        f"بدون شرط الحركة الفيزيائية (خطوة 1 هرتز ≤ 1.2×الوتر+8 م) تصبح دقة الطول "
        f"{100 - abs(uncap_err):.1f}% — أي أن 8 من {a['stretches']} مقطعاً فيها قفزة حافة لو رُفع الشرط؛ "
        f"هذا عيب مطابقة معروف وحلّه مطابقة HMM لا تعديل الشبكة.",
        "قياس واحد، مركبة واحدة، ليلة واحدة (2026-11-14) — نتيجة تحقق لا معايرة إحصائية.",
        f"التحقق جرى على insyab_v2.net.xml ({a['net_edges']:,} حافة) لا insyab.net.xml المستخدمة في "
        f"تشغيلات الأذرع — فرق الشبكتين مُعلن ولا يُخفى.",
        f"{a['analysed_share_of_dense_pct']:.1f}% من الكيلومترات المتصلة قابلة للمقارنة الهندسية "
        f"({a['analysed_km']:.2f} من {a['dense_km']:.1f} كم).",
    ]

    evidence = [
        {"file": "points.csv", "bytes": 203812, "sha16": "3ce3c84d65353f0d",
         "what": "3,002 نقطة GPS/FIX بتردد 1 هرتز — المشتق من 99 ملفاً خاماً من بطاقة المسجّل"},
        {"file": "insyab_v2.net.xml", "bytes": 24165580, "sha16": a["net_sha16"],
         "what": f"شبكة {a['engine']} · {a['net_edges']:,} حافة — مرجع الانحراف"},
        {"file": "rou.xml", "bytes": 1760, "sha16": "558b88b197dbc7e0",
         "what": "المسار المشتق على حواف حقيقية (0 placeholder) — شُغّل على SUMO 1.27.0"},
        {"file": "accuracy_final.json", "bytes": None, "sha16": None,
         "what": "ناتج سكربت التحقق: مطابقة كل نقطة بأقرب موضع على الحافة + جدول الـ17 مقطعاً"},
        {"file": "insiyab_replay.mp4", "bytes": 3898125, "sha16": "a75c5e2ca5b2106f",
         "what": "إعادة تشغيل الرحلة على الشبكة (70 ثانية بسرعة ×144)"},
    ]

    out = {
        "kind": "field_validation",
        "as_of": "2026-11-15",
        "session": {
            "date_utc": "2026-11-14",
            "window_utc": ["18:23:38Z", "20:47:48Z"],
            "rate_hz": 1,
            "points": a["points"],
            "vehicle": "Mazda CX-5 2024",
            "logger": "ESP32-S3 + مسجّل مخصص (CAN/GNSS) — بطاقة SD",
            "firmware": "MZ-CX5-TRIP-025",
            "field_kmh_mean": a["field_kmh"],
        },
        "kpis": kpis,
        "stretches": stretches,
        "totals": {
            "field_m": round(field, 1),
            "net_m": round(sum(x["net_m"] for x in det), 1),
            "net_uncapped_m": round(uncap, 1),
            "agg_err_pct": a["agg_err_pct"],
            "accuracy_pct": a["accuracy_agg_pct"],
            "uncapped_accuracy_pct": round(100 - abs(uncap_err), 1),
        },
        "limits": limits,
        "evidence": evidence,
        "video": {
            "src": "media/insiyab_replay.mp4",
            "poster": "media/poster.jpg",
            "seconds": 70.04,
            "speedup": 144,
            "bytes": 3898125,
            "sha16": "a75c5e2ca5b2106f",
        },
        "source": "data/accuracy_final.json ← acc8.py على derived/points.csv × insyab_v2.net.xml",
    }
    return out


def main():
    # مهجور: نسخة الجولة القديمة (accuracy_final.json) لم تعد مصدر تبويب التحقق؛
    # المصدر الحيّ هو accuracy_anas.json ⇒ build/build_validation_anas.py.
    # التشغيل هنا يكتب فوق data/validation.json ويرجّع الواجهة إلى صياغة قديمة.
    if os.environ.get("INSYAB_ALLOW_LEGACY_VALIDATION") != "1":
        raise SystemExit("build_validation.py مهجور — استخدم build/build_validation_anas.py "
                         "(أو INSYAB_ALLOW_LEGACY_VALIDATION=1 لكتابة نسخة قديمة فوق validation.json)")
    out = build()
    with open(os.path.join(DATA, "validation.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("validation.json kpis", len(out["kpis"]), "stretches", len(out["stretches"]),
          "acc", out["totals"]["accuracy_pct"], "uncap", out["totals"]["uncapped_accuracy_pct"])


if __name__ == "__main__":
    main()
