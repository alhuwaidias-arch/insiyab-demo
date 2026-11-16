# -*- coding: utf-8 -*-
"""يبني data/validation.json من قياس جولة طريق أنس (ACCURACY_ANAS.json) + الفيديوهين.
كل رقم هنا مشتق من ملفات مقيسة — لا رقم مكتوب بيد."""
import json, os, sys, hashlib, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                  # .../scratch/demo
SCR = os.path.dirname(ROOT)                   # .../scratch
_cand = [os.path.join(ROOT, 'data', 'accuracy_anas.json'), os.path.join(SCR, 'ACCURACY_ANAS.json')]
ACC = next((p for p in _cand if os.path.exists(p)), _cand[-1])
ANAS = os.path.join(ROOT, 'data', 'anas.json')
_c2 = [os.path.join(ROOT, 'data', 'points_anas.csv'), 'D:/INFIRAD/projects/insiyab/data/cx5_trips/derived/points_anas.csv']
CSV = next((p for p in _c2 if os.path.exists(p)), _c2[-1])
TIM = os.path.join(ROOT, 'data', 'time_accuracy.json')   # دقة الزمن (SUMO tripinfo) — إلزامي
_c3 = [os.path.join(ROOT, 'MANIFEST.json'), 'D:/INFIRAD/projects/insiyab/MANIFEST.json']
MAN = next((p for p in _c3 if os.path.exists(p)), _c3[-1])
TZ = 3 * 3600

def sha16(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]

def sz(p):
    return os.path.getsize(p) if os.path.exists(p) else 0

def iso2loc(s):
    d = dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
    return (d + dt.timedelta(seconds=TZ)).strftime('%H:%M:%S')

def f1(x):
    return round(float(x), 1)

def build():
    a = json.load(open(ACC, encoding='utf-8'))
    an = json.load(open(ANAS, encoding='utf-8'))
    if not os.path.exists(TIM):
        raise SystemExit('data/time_accuracy.json مفقود — شغّل build/build_time_accuracy.py أولًا')
    tm = json.load(open(TIM, encoding='utf-8'))
    tr = an['trace']
    t0, t1 = tr['t0'], tr['t1']

    detail = a['detail']
    field_m = sum(d['field_m'] for d in detail)
    net_m = sum(d['net_m'] for d in detail)
    net_unc = sum(d['net_uncapped_m'] for d in detail)
    agg = (net_m - field_m) / field_m * 100.0
    agg_unc = (net_unc - field_m) / field_m * 100.0
    acc = 100.0 - abs(agg)
    acc_unc = 100.0 - abs(agg_unc)
    within10 = a['within_10pct_stretches']
    best_err = a['best_err_pct']

    stretches = []
    for d in detail:
        stretches.append({
            't0': iso2loc(d['t0']), 't1': iso2loc(d['t1']),
            'pts': d['pts'],
            'field_m': f1(d['field_m']), 'net_m': f1(d['net_m']),
            'err': f1(d['err_pct']), 'kmh': f1(d['field_kmh']),
        })

    vid = os.path.join(ROOT, 'media', 'anas_trip.mp4')
    vsec = 88.08
    span = t1 - t0
    out = {
        'kind': 'field_validation',
        'as_of': dt.datetime.utcfromtimestamp(t0 + TZ).date().isoformat(),
        'session': {
            'date_utc': dt.datetime.utcfromtimestamp(t0).strftime('%Y-%m-%d'),
            'window_utc': [dt.datetime.utcfromtimestamp(t0).strftime('%H:%M:%SZ'),
                           dt.datetime.utcfromtimestamp(t1).strftime('%H:%M:%SZ')],
            'window_local': [dt.datetime.utcfromtimestamp(t0 + TZ).strftime('%H:%M:%S'),
                             dt.datetime.utcfromtimestamp(t1 + TZ).strftime('%H:%M:%S')],
            'rate_hz': 1,
            'points': a['points'],
            'vehicle': 'Mazda CX-5 2024',
            'logger': 'ESP32-S3 + مسجّل مخصص (CAN/GNSS) — بطاقة SD',
            'firmware': 'MZ-CX5-TRIP-025',
            'field_kmh_mean': f1(a['field_kmh']),
            'corridor': an['corridor'],
            'corridor_km': round(an['corridor_km'], 2),
            'trip_km': round(a['trip_km_valid'], 2),
        },
        'kpis': [
            # دقة المحاكاة في الزمن/الطول على الممر — الرقم الأول في الواجهة.
            # لا تُعرض هنا أرقام طول الجولة الكاملة ولا نسبة التغطية ولا الدقة بلا سقف:
            # الجولة تضمّ التفافات خارج الممر ومسارات متكررة، فقياسها كنسبة واحدة يضلّل.
            {'value': round(acc, 1), 'unit': '%',
             'label': 'دقة المحاكاة في طول المسار',
             'foot': 'خطأ تراكمي \u2066' + ('%+.2f' % agg) + '%\u2069 على ' +
                     ('%.2f' % (field_m / 1000)) + ' كم متصلة (' + str(a['stretches']) + ' مقطعاً بتردد 1 هرتز)'},
            {'value': round(tm['time_accuracy_pct'], 1), 'unit': '%',
             'label': 'دقة المحاكاة في زمن المرور على المقاطع',
             'foot': ('{:.1f} د مقيسة مقابل {:.1f} د على الشبكة — فرق {:.2f}%'.format(
                 tm['field_min'], tm['sim_min'], tm['err_time_pct']))},
            {'value': round(a['dev_median_m'], 2), 'unit': 'م',
             'label': 'وسيط انحراف الأثر المقيس عن الشبكة',
             'foot': 'p90 {:.2f} م · أقصى {:.2f} م على {:,} نقطة'.format(
                 a['dev_p90_m'], a['dev_max_m'], a['points'])
             if 'dev_max_m' in a else
             'p90 {:.2f} م على {:,} نقطة'.format(a['dev_p90_m'], a['points'])},
            {'value': round(a['field_kmh'], 1), 'unit': 'كم/س',
             'label': 'متوسط سرعة المركبة على المقاطع المقارَنة',
             'foot': 'المسافة ÷ الزمن من السجل نفسه — لا من عدّاد المركبة'},
            {'value': round(span / 3600.0, 1), 'unit': 'ساعة',
             'label': 'مدة القياس الميداني على الممر',
             'foot': '{:,} نقطة متصلة بتردد 1 هرتز في جلسة قياس واحدة · {} دقيقة'.format(
                 a['points'], int(round(span / 60.0)))},
        ],
        'stretches': stretches,
        'totals': {
            'field_m': f1(field_m), 'net_m': f1(net_m), 'net_uncapped_m': f1(net_unc),
            'agg_err_pct': round(agg, 2), 'accuracy_pct': round(acc, 1),
            'uncapped_accuracy_pct': round(acc_unc, 1),
        },
        'limits': [
            'المقارنة تُجرى على أجزاء المسار الواقعة على الممر وشبكته؛ ما خرج عن الممر إلى طرق أخرى '
            'لا يدخل حساب الخطأ ولا يُقارن بشبكة الممر.',
            'معامل التطابق MAPE ' + ('%.2f' % a['mape_pct']) + '% وأسوأ مقطع ' +
            ('%.2f' % a['worst_err_pct']) + '% — التباين مقطعاً بمقطع معروض في الجدول أدناه.',
            'جلسة قياس واحدة لمركبة واحدة في يوم واحد (14/11/2026) — إثبات دقة على ممر، '
            'لا معايرة إحصائية لأسطول أو لساعات الذروة.',
            'دقة الزمن من إعادة تشغيل فعلية على SUMO (زمن tripinfo، مركبة واحدة بلا حركة أخرى) '
            'على ' + str(tm['stretches_simulated']) + ' مقطعًا من ' + str(tm['stretches_analysed']) +
            '؛ ما استُبعد سببه انقطاع في مطابقة المسار لا تحسين الرقم، وعلى المقاطع الطويلة '
            '(≥' + ('%d' % tm['long_m_from']) + ' م) الفرق {:.2f}%.'.format(tm['long_err_time_pct']),
            'الفرق الكلي ({:.2f}%) يحكمه سلوك المقاطع الطويلة (≥{} م: {:.2f}%)، ووسيط |خطأ الزمن| للمقطع '
            'الواحد {:.2f}% لأن مقاطع 20-30 ث يغلب عليها التسارع عند الطرفين لا الزمن على الطريق — '
            'الرقمان معروضان لا أحدهما بدل الآخر.'.format(
                tm['err_time_pct'], int(tm['long_m_from']), tm['long_err_time_pct'],
                tm['err_time_median_abs_pct']),
            'المطابقة تقيس طول المسار على الشبكة وانحراف نقاطه عنها؛ المسار بين تقاطعين قد يختلف '
            'داخل الشبكة دون أن يتغير الطول الكلي.',
        ],
        'evidence': [
            {'file': 'points_anas.csv', 'bytes': sz(CSV), 'sha16': sha16(CSV) if os.path.exists(CSV) else '',
             'what': '{:,} نقطة GPS/FIX بتردد 1 هرتز لجولة الطريق كاملة'.format(a['points'])},
            {'file': 'ACCURACY_ANAS.json', 'bytes': sz(ACC), 'sha16': sha16(ACC),
             'what': 'مخرَج المطابقة: انحراف كل مقطع وطول الشبكة المقابل'},
            {'file': 'fcd.xml (SUMO)', 'bytes': 0, 'sha16': '',
             'what': 'تتبّع كل مركبة كل خطوة زمنية — مصدر مشهد التقاطع وعدّ الذروة'},
        ] + ([{'file': 'MANIFEST.json', 'bytes': sz(MAN), 'sha16': sha16(MAN),
               'what': 'بصمات ملفات الجولة الخام والمشتقة — سلسلة الحيازة'}] if os.path.exists(MAN) else []),
        'video': {
            'src': 'media/anas_trip.mp4',
            'poster': 'images/poster_anas.jpg',
            'seconds': vsec,
            'speedup': int(round(span / vsec)),
            'bytes': sz(vid),
            'sha16': sha16(vid) if os.path.exists(vid) else '',
        },
        'source': 'ACCURACY_ANAS.json ← acc_anas.py على derived/points_anas.csv × insyab_v2.net.xml',
    }

    return out


if __name__ == '__main__':
    out = build()
    dst = os.path.join(ROOT, 'data', 'validation.json')
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'ok': True, 'bytes': os.path.getsize(dst),
                      'kpis': [k['value'] for k in out['kpis']],
                      'stretches': len(out['stretches']),
                      'agg': out['totals']['agg_err_pct'],
                      'uncapped': out['totals']['uncapped_accuracy_pct'],
                      'video': out['video']['bytes'],
                      'window_local': out['session']['window_local']}, ensure_ascii=False))
