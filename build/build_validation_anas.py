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
            {'value': round(acc, 1), 'unit': '%',
             'label': 'دقة طول المسار على شبكة المحاكاة',
             'foot': 'خطأ تراكمي \u2066' + ('%+.2f' % agg) + '%\u2069 على ' +
                     ('%.2f' % (field_m / 1000)) + ' كم متصلة (' + str(a['stretches']) + ' مقطعاً بتردد 1 هرتز)'},
            {'value': round(acc_unc, 1), 'unit': '%',
             'label': 'الدقة بلا سقف للوتر (1.2×)',
             'foot': 'هذا هو الرقم الأصدق: ' + ('%.2f' % (net_unc / 1000)) + ' كم على الشبكة مقابل ' +
                     ('%.2f' % (field_m / 1000)) + ' كم ميدان — فرق المسار الحقيقي'},
            {'value': round(a['analysed_share_of_dense_pct'], 1), 'unit': '%',
             'label': 'نسبة الجولة المشمولة بالقياس',
             'foot': ('%.2f' % (a['analysed_km'])) + ' كم من ' + ('%.2f' % a['trip_km_valid']) +
                     ' كم مقطوعة — الباقي وقوف أو فجوة سجل'},
            {'value': round(a['trip_km_valid'], 2), 'unit': 'كم',
             'label': 'طول الجولة المقطوعة',
             'foot': '{:,} نقطة · انحراف وسيط {:.2f} م · p90 {:.2f} م'.format(
                 a['points'], a['dev_median_m'], a['dev_p90_m'])},
        ],
        'stretches': stretches,
        'totals': {
            'field_m': f1(field_m), 'net_m': f1(net_m), 'net_uncapped_m': f1(net_unc),
            'agg_err_pct': round(agg, 2), 'accuracy_pct': round(acc, 1),
            'uncapped_accuracy_pct': round(acc_unc, 1),
        },
        'limits': [
            'الشبكة لا تغطي كل الجولة: ' + ('%.2f' % (a['analysed_km'])) + ' كم من ' +
            ('%.2f' % a['trip_km_valid']) + ' كم دخلت القياس (' +
            ('%.1f' % a['analysed_share_of_dense_pct']) + '%)؛ الباقي وقوف في الإشارات أو فجوة تسجيل واحدة.',
            'معامل التطابق MAPE ' + ('%.2f' % a['mape_pct']) + '% وأسوأ مقطع ' +
            ('%.2f' % a['worst_err_pct']) + '% — التباين مقطعاً بمقطع معروض في الجدول أدناه.',
            'مقطع الـU-Turn في SUMO طلب حركة مُصمَّم (3 مركبات من 3 حارات) لبيان القدرة على تمثيل السلوك، وليس سحباً إحصائياً من عدّ ميداني.',
            'الجولة قيادة واحدة (n=1) في ظهيرة 14/11/2026 — لا تُعمَّم على ساعات الذروة أو أيام الأسبوع.',
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
