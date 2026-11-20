#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انسياب — خرائط الشبكة: المشكلة، الأذرع الخمسة، والحل المُختار.

لا رقم مكتوب بيد: كل قيمة تُقرأ من data/network.json (هندسة SUMO)
ومن runs/damage_<arm>.edges.csv (أثر كل ذراع على كل ضلع)
ومن data/solutions.json (الأرقام المعروضة).

SVG لا PNG في التوليد لأن الخط العربي يُرسم صحيحًا في المتصفح، ثم يُلتقط PNG للعرض.

فخّ عربي محسوب: مع direction="rtl" يُقلب معنى text-anchor — «start» يعني حافة
يمين النص (فيتدفّق يسارًا) و«end» يعني حافته اليسرى (فيتدفّق يمينًا). لذلك
النصّ هنا يُكتب عبر T() التي تختار المرساة من الاتجاه المطلوب.

    python build/build_maps.py
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA, IMG = os.path.join(ROOT, "data"), os.path.join(ROOT, "images")
MODEL = os.environ.get("INSIYAB_MODEL", r"D:\INFIRAD\projects\insiyab")
RUNS = os.path.join(MODEL, "runs")
os.makedirs(IMG, exist_ok=True)

SKY, AMBER, RED, PURPLE = "#4c9ee0", "#d68910", "#d94a3d", "#8e5bb5"
# بلا تغيير = رمادي فاتح داكن رفيع مصمت · التقاطع = أبيض مزرق متقطّع
# الفرق بينهما الآن في ثلاث قنوات (سطوع · نمط · سماكة) لا في درجة رمادية متقاربة.
GREY, GREY_L, BG, CARD = "#6b7684", "#9aa6bb", "#081533", "#0d2150"
INK, MUTED = "#ffffff", "#a8b8d8"
ANAS, TURKI = "شارع أنس بن مالك", "طريق الأمير تركي بن عبدالعزيز الأول"
# لون الطريق المتقاطع مستقل عن سلّم التأخير (الكهرماني) وإلا التبس بالمفتاح
TURKI_C = "#e6eef9"
FONT = "Segoe UI, Tahoma, Arial, sans-serif"

net = json.load(open(os.path.join(DATA, "network.json"), encoding="utf-8"))
SOL = json.load(open(os.path.join(DATA, "solutions.json"), encoding="utf-8"))
D = SOL["display"]
SH, ST = net["shapes"], net["streets"]


def pts(e):
    _, s, ln, sp, lanes, off, n = e
    return [(SH[2 * (off + i)], SH[2 * (off + i) + 1]) for i in range(n)]


def read_damage(name):
    p = os.path.join(RUNS, name or "")
    out = {}
    if not name or not os.path.exists(p):
        return out
    with open(p, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                out[r["edge"]] = float(r["added_vh"] or 0)
            except ValueError:
                pass
    return out


_A = SOL["arms"]


def _m(k):
    """زمن الرحلة لذراع بالدقيقة، مقرَّبًا — لا رقم مكتوب بيد."""
    return f"{_A[k]['dur_min']:.0f}"


def _x(k):
    """فرق الذراع عن خط الأساس بالدقيقة، بإشارته."""
    return f"{_A[k]['dur_min'] - _A['baseline']['dur_min']:+.0f}"


ARMS = [
    ("baseline", None, "خط الأساس", f"{_m('baseline')} دقيقة · بلا إغلاق", GREY),
    ("closure", "damage_closure300.edges.csv", "إغلاق كامل",
     f"+{D['closure_vh']:,} ساعة تأخير · {_m('closure')} د/رحلة", RED),
    ("detour", "damage_detour300.edges.csv", "توسعة المجاورة",
     f"{_m('detour')} د · تعادل الإغلاق — مرفوض", AMBER),
    ("uturn", "damage_uturn300.edges.csv", "دوران إجباري",
     f"{_m('uturn')} د ({_x('uturn')} عن الأساس) — مرفوض", PURPLE),
    ("works", "damage_works300.edges.csv", "المُطبَّق: حارتان لكل اتجاه",
     f"+{D['works_vh']:,} ساعة · {D['works_share_pct']}% من الإغلاق", SKY),
]
dmg = {k: read_damage(f) for k, f, _, _, _ in ARMS if f}

ap = [p for e in net["edges"] if ST[e[1]] == ANAS for p in pts(e)]
lon0, lon1 = min(p[0] for p in ap), max(p[0] for p in ap)
lat0, lat1 = min(p[1] for p in ap), max(p[1] for p in ap)
pad = 0.010
WB = (lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad)

best = (1e9, None)
for e in net["edges"]:
    if ST[e[1]] != ANAS:
        continue
    for p in pts(e):
        for f in net["edges"]:
            if ST[f[1]] != TURKI:
                continue
            for q in pts(f):
                d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
                if d < best[0]:
                    best = (d, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
JUNC = best[1]

GEOM = [(e[0], ST[e[1]], pts(e)) for e in net["edges"]]
VMAX = {k: max([v for v in d.values() if v > 0] or [1]) for k, d in dmg.items()}

# نافذة العرض = اتحاد الأضلاع التي يتغيّر تأخيرها في أي ذراع، وهامش 0.8 كم.
# الممر 8.8 كم فتُصبح الأضلاع المتأثرة نقاطًا لا تُقرأ؛ التكبير يجعل الكثافة تُرى.
_hit = {eid for d in dmg.values() for eid, v in d.items() if v >= 5}
_hp = [p for eid, street, ps in GEOM if eid in _hit for p in ps] or ap
_zpad_lon, _zpad_lat = 0.008, 0.006
ZB = (min(max(min(p[0] for p in _hp) - _zpad_lon, WB[0]), JUNC[0]),
      min(max(min(p[1] for p in _hp) - _zpad_lat, WB[1]), JUNC[1]),
      max(min(max(p[0] for p in _hp) + _zpad_lon, WB[2]), JUNC[0]),
      max(min(max(p[1] for p in _hp) + _zpad_lat, WB[3]), JUNC[1]))


# ── نص عربي: المرساة تُختار من الاتجاه المطلوب ───────────────────────────────
def T(x, y, s, size=20, fill=INK, anchor="r", weight=None, opacity=None):
    """anchor: r = النص ينتهي عند x (محاذاة يمين) · l = يبدأ عند x (محاذاة يسار) · c = وسط."""
    ta = {"r": "start", "l": "end", "c": "middle"}[anchor]
    w = f' font-weight="{weight}"' if weight else ""
    o = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return (f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" font-size="{size}"{w}{o} '
            f'text-anchor="{ta}" direction="rtl">{s}</text>')


def make_proj(w, h, m=26, box=None):
    box = box or ZB
    kx = math.cos(math.radians((box[1] + box[3]) / 2))
    sx, sy = (box[2] - box[0]) * kx, box[3] - box[1]
    s = min((w - 2 * m) / sx, (h - 2 * m) / sy)
    ox, oy = (w - sx * s) / 2, (h - sy * s) / 2

    def P(p):
        return (ox + (p[0] - box[0]) * kx * s, h - oy - (p[1] - box[1]) * s)
    return P


def path(ps, P):
    return " ".join(("M" if i == 0 else "L") + f"{P(p)[0]:.1f} {P(p)[1]:.1f}"
                    for i, p in enumerate(ps))


def heat(v, vmax):
    """سلّم لوغاريتمي: التأخير يتراكم على قليل من الأضلاع، فالمقياس الخطّي يحوّل
    كل شيء إلى كهرماني باهت. اللوغاريتم يُظهر الكثافة التي يراها القارئ."""
    if v is None or v < 5:
        return GREY, 1.0
    t = math.log1p(v) / math.log1p(max(vmax, 1e-9))
    col = AMBER if t < .45 else ("#e2701e" if t < .72 else RED)
    return col, 1.7 + 4.0 * t


def swatch(x, y, colr, dash="", wd=34, thick=8, casing=False):
    """شريط المفتاح خطٌّ لا مستطيل: النمط المتقطّع وحدّ التمييز لا يظهران على
    مستطيل مُعبّأ (dasharray وstroke بلا أثر على الشكل الممتلئ)."""
    out = []
    if casing:                                  # حاشية بيضاء تحت الشريط = «مقطع»
        out.append(f'<line x1="{x}" y1="{y}" x2="{x+wd}" y2="{y}" stroke="#f0f6ff" '
                   f'stroke-width="{thick+7}" stroke-linecap="round"/>')
    out.append(f'<line x1="{x}" y1="{y}" x2="{x+wd}" y2="{y}" stroke="{colr}" '
               f'stroke-width="{thick}" stroke-linecap="round" {dash}/>')
    return "".join(out)


def doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>')


def network(P, arm=None, vmax=None, anas=True, turki=True, base_w=1.0, base_op=.9):
    d = dmg.get(arm, {}) if arm else {}
    vmax = vmax or VMAX.get(arm, 1)
    rest = " ".join(path(ps, P) for eid, street, ps in GEOM
                    if street not in (ANAS, TURKI) and not (d.get(eid, 0) >= 5))
    out = [f'<path d="{rest}" fill="none" stroke="#2b3f6b" stroke-width="{base_w}" '
           f'stroke-opacity="{base_op}" stroke-linecap="round"/>']
    # حاشية داكنة تحت الأضلاع المتأثرة ليفصلها اللون عن زحام الشبكة
    case = " ".join(path(ps, P) for eid, street, ps in GEOM if d.get(eid, 0) >= 5)
    if case:
        out.append(f'<path d="{case}" fill="none" stroke="#050e24" stroke-width="7" '
                   f'stroke-opacity=".55" stroke-linecap="round"/>')
    for eid, street, ps in GEOM:
        v = d.get(eid, 0)
        if v >= 5:
            col, wd = heat(v, vmax)
            out.append(f'<path d="{path(ps, P)}" fill="none" stroke="{col}" '
                       f'stroke-width="{wd:.2f}" stroke-linecap="round"/>')
    if turki:
        for eid, street, ps in GEOM:
            if street == TURKI:
                out.append(f'<path d="{path(ps, P)}" fill="none" stroke="{TURKI_C}" stroke-width="2.6" '
                           f'stroke-opacity=".5" stroke-dasharray="9 6" stroke-linecap="round"/>')
    if anas:
        for eid, street, ps in GEOM:
            if street == ANAS:
                out.append(f'<path d="{path(ps, P)}" fill="none" stroke="{SKY}" stroke-width="3.4" '
                           f'stroke-opacity=".7" stroke-linecap="round"/>')
    return "".join(out)


def junction(P, r=8, closed=False):
    x, y = P(JUNC)
    if closed:
        k = r * 1.5
        return (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r*3.2:.0f}" fill="{RED}" fill-opacity=".14"/>'
                f'<path d="M {x-k:.0f} {y-k:.0f} L {x+k:.0f} {y+k:.0f} M {x+k:.0f} {y-k:.0f} '
                f'L {x-k:.0f} {y+k:.0f}" stroke="{RED}" stroke-width="{r*0.55:.1f}" '
                f'stroke-linecap="round"/>')
    return (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r*2.8:.0f}" fill="{SKY}" fill-opacity=".16"/>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{SKY}"/>')


# ── 1 · المشكلة ──────────────────────────────────────────────────────────────
def fig_problem(w=1600, h=900):
    P = make_proj(w, h, m=40, box=WB)
    x, y = P(JUNC)
    b = [network(P)]
    b.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="52" fill="{RED}" fill-opacity=".16"/>')
    b.append(f'<path d="M {x-22:.0f} {y-22:.0f} L {x+22:.0f} {y+22:.0f} M {x+22:.0f} {y-22:.0f} '
             f'L {x-22:.0f} {y+22:.0f}" stroke="{RED}" stroke-width="8" stroke-linecap="round"/>')
    b.append(T(x - 76, y - 6, "التقاطع مغلق", 26, INK, "r", "700"))
    b.append(T(x - 76, y + 28, "لأعمال تطوير طريق الأمير تركي الأول", 19, "#ffb3ab", "r"))
    west, east = min(ap, key=lambda p: p[0]), max(ap, key=lambda p: p[0])
    for p, anchor, dx, dy, lab in ((west, "l", 16, -16, "شارع أنس بن مالك — الغرب"),
                                   (east, "r", -16, -16, "شارع أنس بن مالك — الشرق")):
        px, py = P(p)
        b.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="8" fill="{SKY}"/>')
        b.append(T(px + dx, py + dy, lab, 21, "#dce6f7", anchor))
    # اسم الطريق المتقاطع على خطّه نفسه — لا يترك للقارئ أن يستنتج
    tp = [p for e in net["edges"] if ST[e[1]] == TURKI for p in pts(e)]
    # التسمية على منتصف الجزأين — الطرف الشمالي يقع تحت بطاقة العنوان
    _y = JUNC[1]
    north = [p for p in tp if p[1] < _y - 0.004]
    south = [p for p in tp if p[1] > _y + 0.004]
    tN = min(north, key=lambda p: abs(p[1] - (_y - 0.007))) if north else max(tp, key=lambda p: p[1])
    tS = min(south, key=lambda p: abs(p[1] - (_y + 0.007))) if south else min(tp, key=lambda p: p[1])
    for p, anchor, dy, lab in ((tN, "l", -14, TURKI), (tS, "r", 26, TURKI)):
        px, py = P(p)
        b.append(T(px + (16 if anchor == "l" else -16), py + dy, lab, 20, "#ffd79a", anchor))
    b.append(f'<rect x="34" y="30" width="770" height="140" rx="14" fill="#081b4a" fill-opacity=".9"/>')
    b.append(T(784, 80, "ما نفعله بالضبط", 34, INK, "r", "700"))
    b.append(T(784, 120, "نغلق تقاطع أنس بن مالك مع طريق الأمير تركي الأول مدة الأعمال", 21, MUTED, "r"))
    b.append(T(784, 152, "ونقيس أين يذهب التأخير، وأي تدبير يخففه فعلًا", 21, MUTED, "r"))
    lx = 40                                   # المفتاح رأسًا: مفتاحٌ لكل سطر، لا تزاحم أفقي
    bw_, bh_ = 500, 132
    ly = h - 26 - bh_
    b.append(f'<rect x="{lx-16}" y="{ly}" width="{bw_}" height="{bh_}" rx="12" fill="#081b4a" fill-opacity=".92"/>')
    for i, (colr, dash, lab) in enumerate(((SKY, "", "شارع أنس بن مالك (المحور)"),
                                          (TURKI_C, ' stroke-dasharray="7 5"', TURKI),
                                          (RED, "", "التقاطع المُغلق"))):
        yy = ly + 30 + i * 28
        b.append(swatch(lx + bw_ - 58, yy - 5, colr, dash, wd=30, thick=8))
        b.append(T(lx + bw_ - 68, yy + 6, lab, 18, "#dbe5f7", "r"))
    b.append(T(lx + 2, ly + bh_ - 12, "الشبكة من نموذج المحاكاة (SUMO)، لا خريطة زخرفية", 17, MUTED, "l"))
    open(os.path.join(IMG, "map_problem.svg"), "w", encoding="utf-8").write(doc(w, h, "".join(b)))


# ── 2 · الأذرع الخمسة ───────────────────────────────────────────────────────
def fig_arms(W=1680, H=1272):
    pw, ph = (W - 4 * 18) // 3, 566
    hh = 78
    vmax = max(VMAX.values()) if VMAX else 1
    b = [T(W - 30, 52, "خط الأساس وأربعة حلول — الشبكة نفسها والطلب نفسه", 30, INK, "r", "700"),
         T(W - 30, 86, "كل لوحة تُظهر أين يظهر التأخير — والتقاطع واحد في الجميع", 20, MUTED, "r")]
    for i, (arm, f, title, big, accent) in enumerate(ARMS):
        # RTL: اللوحة 1 أقصى اليمين، ثم 2، ثم 3 — وإلا قرأها القارئ العربي معكوسة
        col, row = 2 - (i % 3), i // 3
        x0, y0 = 18 + col * (pw + 18), 106 + row * (ph + 18)
        P = make_proj(pw, ph - hh, m=16)
        b.append(f'<g transform="translate({x0},{y0})">'
                 f'<rect width="{pw}" height="{ph}" rx="16" fill="{CARD}" stroke="{accent}" '
                 f'stroke-opacity="{0.85 if arm == "works" else 0.28}" '
                 f'stroke-width="{2.5 if arm == "works" else 1}"/>')
        b.append(f'<rect x="16" y="16" width="40" height="28" rx="8" fill="{accent}" fill-opacity=".9"/>')
        b.append(f'<text x="36" y="37" fill="#08122e" font-size="19" font-weight="700" '
                 f'text-anchor="middle">{i+1}</text>')
        b.append(T(pw - 18, 40, title, 24, INK, "r", "700"))
        b.append(T(pw - 18, 68, big, 20, accent, "r", "700"))
        _closed = arm in ("closure", "uturn")
        b.append(f'<g transform="translate(0,{hh})">{network(P, arm, vmax)}'
                 f'{junction(P, 7 if arm == "works" else 6, closed=_closed)}</g></g>')
    # خلية المفتاح
    x0, y0 = 18, 106 + (ph + 18)          # خلية المفتاح: يسار الصف الثاني
    b.append(f'<g transform="translate({x0},{y0})"><rect width="{pw}" height="{ph}" rx="16" '
             f'fill="{CARD}" fill-opacity=".72"/>')
    b.append(T(pw - 20, 48, "كيف تُقرأ الخريطة", 24, INK, "r", "700"))
    # كل صفّ: اسم + شرح تحت بعضهما، ومسافة 64px بين الصفوف ⇒ لا تلامس بين صفّين
    rows = [(RED, "", "تأخير كبير", "أضلاع يزيد تأخيرها كثيرًا"),
            (AMBER, "", "تأخير متوسط", "أضلاع تتأثر جزئيًا"),
            (GREY, "", "بلا تغيير", "خط رمادي رفيع مصمت — لم يتغير تأخيرها"),
            (SKY, "", "المحور", "شارع أنس بن مالك"),
            (TURKI_C, ' stroke-dasharray="8 6"', "المتقاطع", "خط متقطّع رفيع — طريق الأمير تركي الأول")]
    ty = 100
    for colr, dash, name, note in rows:
        b.append(swatch(pw - 48, ty - 8, colr, dash, wd=32,
                        thick=7, casing=dash.startswith(' casing')))
        b.append(T(pw - 58, ty - 2, name, 19, INK, "r", "700"))
        b.append(T(pw - 58, ty + 21, note, 15, MUTED, "r"))
        ty += 62
    b.append(T(pw - 20, ty + 12, "سماكة الخط = حجم التأخير على الضلع", 16, "#cfd9e6", "r"))
    b.append("</g>")
    open(os.path.join(IMG, "map_arms.svg"), "w", encoding="utf-8").write(doc(W, H, "".join(b)))


# ── 3 · الحل المُختار ────────────────────────────────────────────────────────
WORKS_EDGES = ("40639443#9", "244175211#17")   # مقطع الأعمال: ضلعا المحور عبر التقاطع


def fig_chosen(w=1600, h=900, fs=1.0, chrome=True, out="map_chosen"):
    """لوحة الحل المُختار — تُقرأ بذاتها: أين التقاطع، وأين يضيق المحور إلى
    حارتين لكل اتجاه، وما معنى اللون والسماكة. لا شارتا مراحل: الوضع المطبَّق
    فعليًا يُبقي الاتجاهين سالكين معًا ويضيّق المقطع فقط.

    fs     : مضاعف أحجام الخط (شريحة العرض تحتاج ≈2× لأنها تصغير)
    chrome : إطار العنوان والمفتاح والحاشية — تُحذف حين يحملها نصّ الشريحة
    out    : اسم ملف الإخراج"""
    P = make_proj(w, h - 10, m=34, box=WB)
    x, y = P(JUNC)
    b = [f'<defs><marker id="arw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" '
         f'markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="{SKY}"/></marker>'
         f'<marker id="arw2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" '
         f'markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#f0f6ff"/></marker></defs>']
    b.append(network(P, "works", VMAX["works"]))
    b.append(junction(P, 9))

    cor = sorted(((eid, ps) for eid, street, ps in GEOM if street == ANAS),
                 key=lambda t: sum(p[0] for p in t[1]) / len(t[1]))

    def seg_at(f):
        return cor[int(len(cor) * f)][1] if len(cor) > 3 else None

    # سهمان متعاكسان: المحور مفتوح في الاتجاهين (حارتان لكل اتجاه)
    for f, rev in ((.30, False), (.70, True)):
        ps = seg_at(f)
        if not ps:
            continue
        a, c = (ps[0], ps[-1]) if ps[0][0] < ps[-1][0] else (ps[-1], ps[0])
        if rev:
            a, c = c, a
        pa, pc = P(a), P(c)
        b.append(f'<path d="M {pa[0]:.0f} {pa[1]:.0f} L {pc[0]:.0f} {pc[1]:.0f}" stroke="{SKY}" '
                 f'stroke-width="4.2" stroke-opacity=".95" fill="none" marker-end="url(#arw)"/>')

    # مقطع الأعمال: إطار أبيض حول الضلعين المضيّقين + شريحة تسمية على خطّ قائد
    wps = [ps for eid, street, ps in GEOM if eid in WORKS_EDGES]
    if wps:
        _w = [p for ps in wps for p in ps]
        fx = sum(along(p) for p in _w) / len(_w)
        wx, wy = P((sum(p[0] for p in _w) / len(_w), sum(p[1] for p in _w) / len(_w)))
        b.append(f'<path d="{" ".join(path(ps, P) for ps in wps)}" fill="none" stroke="#f0f6ff" '
                 f'stroke-width="7.5" stroke-opacity=".22" stroke-linecap="round"/>')
        ANCH = "l" if fx < .35 else ("r" if fx > .65 else "c")
        ly_ = wy - 46 * fs
        b.append(f'<path d="M {wx:.0f} {wy - 12:.0f} L {wx:.0f} {ly_ + 10:.0f}" stroke="#f0f6ff" '
                 f'stroke-width="1.6" stroke-opacity=".55" stroke-dasharray="4 4"/>')
        b.append(T(wx + (12 if ANCH == "l" else (-12 if ANCH == "r" else 0)), ly_,
                   "مقطع الأعمال: حارتان لكل اتجاه — لا مسار مغلق", round(19 * fs),
                   "#eaf2ff", ANCH, "700"))

    # أسماء الشوارع على خطوطها، ومفصولة عن التسمية السابقة مكانيًّا
    cand = [f for f in (.5, .28, .72, .16, .84)]
    if wps:
        cand = [f for f in cand if abs(f - fx) > .17] or [.5]
    nm = seg_at(cand[0])
    if nm:
        nx, ny = P(nm[len(nm) // 2])
        # تحت المحور لا فوقه: تسمية مقطع الأعمال تحجز الحيّز العلوي
        b.append(T(nx, ny + 34 * fs, "شارع أنس بن مالك", round(21 * fs), "#dce6f7", "c"))
    tp = [p for e in net["edges"] if ST[e[1]] == TURKI for p in pts(e)]
    tS = min(tp, key=lambda p: p[1])
    tpx, tpy = P(tS)
    b.append(T(tpx - 16, tpy - 10, TURKI, round(19 * fs), "#cfd9e6", "r"))

    if chrome:
        b.append(f'<rect x="34" y="28" width="900" height="132" rx="14" fill="#081b4a" fill-opacity=".92"/>')
        b.append(T(918, 76, "الحل المُطبَّق على الخريطة", 33, INK, "r", "700"))
        b.append(T(918, 112, f"حارتان لكل اتجاه · {D['works_vh']} ساعة تأخير مضاف · "
                             f"بلا التفاف", 23, SKY, "r", "700"))
        b.append(T(918, 142, f"{SOL['arms']['works']['edges_hit']} ضلعًا يتأثر فقط من "
                             f"{SOL['arms']['works']['edges_total']:,} ضلعًا في نطاق القياس", 19, MUTED, "r"))

        # مفتاح مقروء: كل بند على سطرين (الاسم ثم شرحه تحته). في سطر واحد كان
        # الشرح (يمينًا) يدخل تحت الاسم الطويل مثل «طريق الأمير تركي الأول».
        lx, bw = w - 34 - 700, 700     # الزاوية اليمنى: لا تتعارض مع التقاطع في الوسط
        rows = [(SKY, "", "المحور مفتوح في الاتجاهين", "سهمان متعاكسان على الشارع نفسه"),
                (SKY, ' casing', "مقطع الأعمال", "حارتان لكل اتجاه — لا مسار مغلق"),
                (TURKI_C, ' stroke-dasharray="8 6"', "طريق الأمير تركي الأول", "الطريق المتقاطع"),
                (RED, "", "تأخير كبير", "سماكة أكبر = تأخير أكبر على الضلع"),
                ("#e2701e", "", "تأخير متوسط", "أضلاع تتأثر جزئيًا"),
                (GREY, "", "بلا تغيير", "لم يتغير تأخيرها")]
        bh = 78 + 46 * len(rows)
        ly = h - 42 - bh               # فوق الحاشية بمسافة، ولا تلامسها
        b.append(f'<rect x="{lx}" y="{ly}" width="{bw}" height="{bh}" rx="12" fill="#081b4a" fill-opacity=".92"/>')
        b.append(T(lx + bw - 34, ly + 36, "كيف تُقرأ الخريطة", 22, INK, "r", "700"))
        for i, (colr, dash, name, note) in enumerate(rows):
            yy = ly + 78 + i * 46
            b.append(swatch(lx + bw - 76, yy - 8, colr, dash if not dash.startswith(' casing') else "",
                            wd=36, thick=8, casing=dash.startswith(' casing')))
            b.append(T(lx + bw - 88, yy, name, 18, INK, "r", "700"))
            b.append(T(lx + bw - 88, yy + 21, note, 14, MUTED, "r"))
        b.append(T(40, h - 26, "السهم = اتجاه الحركة · سماكة الخط = حجم التأخير المضاف على الضلع",
                   18, MUTED, "l"))
    open(os.path.join(IMG, out + ".svg"), "w", encoding="utf-8").write(doc(w, h, "".join(b)))


# ── 4 · كثافة التأخير على طول الطريق ─────────────────────────────────────────
def along(pt):
    """موضع النقطة على المحور كنسبة 0..1 من غربه إلى شرقه.
    المحور يُقاس بإحداثيّ الطول لا بطول المسار: المسار مُجزَّأ (اتجاهان)، وجمع
    أطواله يضخّم الطول (12.3 كم مقابل 8.8 كم في العرض) فيتعارض الرقمان بلا داعٍ."""
    return max(0.0, min(1.0, (pt[0] - lon0) / (lon1 - lon0)))


def fig_density(W=1600, H=980):
    nb = 44
    x0, x1 = 44, W - 336          # عمود التسميات على اليمين، والشريط إلى يساره
    bw = (x1 - x0) / nb
    rows, gmax = [], 0
    for arm, f, title, big, accent in ARMS:
        d = dmg.get(arm, {})
        cells = [0.0] * nb
        for eid, street, ps in GEOM:
            v = d.get(eid, 0)
            if v < 5:
                continue
            k = min(nb - 1, int(along(ps[len(ps) // 2]) * nb))
            cells[k] += v
        gmax = max(gmax, max(cells))
        rows.append((title, big, accent, cells, sum(cells)))

    b = [T(W - 40, 54, "أين يقع التأخير على الطريق نفسه؟", 32, INK, "r", "700"),
         T(W - 40, 92, "المحور من غربه إلى شرقه؛ شدّة اللون = مجموع التأخير المضاف في ذلك الجزء من الطريق",
           20, MUTED, "r")]
    y = 132
    for title, big, accent, cells, tot in rows:
        b.append(T(W - 44, y + 24, title, 22, INK, "r", "700"))
        b.append(T(W - 44, y + 52, big, 18, accent, "r"))
        for i, v in enumerate(cells):
            if v < 5:
                b.append(f'<rect x="{x0 + i*bw:.1f}" y="{y}" width="{bw-2:.1f}" height="56" rx="3" '
                         f'fill="#16233f"/>')
                continue
            t = math.log1p(v) / math.log1p(max(gmax, 1e-9))
            col = AMBER if t < .45 else ("#e2701e" if t < .72 else RED)
            b.append(f'<rect x="{x0 + i*bw:.1f}" y="{y}" width="{bw-2:.1f}" height="56" rx="3" '
                     f'fill="{col}" fill-opacity="{.35 + .65*t:.2f}"/>')
        y += 92
    # محور المسافة
    b.append(f'<line x1="{x0}" y1="{y-14}" x2="{x1}" y2="{y-14}" stroke="#3b4f7d" stroke-width="1.5"/>')
    for frac, lab in ((0, "الغرب"), (.25, "25%"), (.5, "50%"), (.75, "75%"), (1, "الشرق")):
        xx = x0 + frac * (x1 - x0)
        b.append(f'<line x1="{xx:.1f}" y1="{y-20}" x2="{xx:.1f}" y2="{y-8}" stroke="#5c719e" stroke-width="1.5"/>')
        b.append(T(xx - 14 if frac == 0 else xx + 18, y + 14, lab, 17, MUTED,
                   "l" if frac == 0 else "c"))
    jx = x0 + along(JUNC) * (x1 - x0)
    b.append(f'<circle cx="{jx:.1f}" cy="{y-30}" r="7" fill="{SKY}"/>')
    b.append(T(jx - 14, y - 34, "التقاطع", 18, SKY, "l", "700"))
    b.append(T(W - 40, y + 46, "كل شريحة ≈ 2% من طول المحور", 17, MUTED, "r"))
    open(os.path.join(IMG, "map_density.svg"), "w", encoding="utf-8").write(doc(W, H, "".join(b)))
    return nb, gmax


if __name__ == "__main__":
    fig_problem()
    fig_arms()
    fig_chosen()
    fig_chosen(fs=2.0, chrome=False, out="map_chosen_slide")
    nb, gmax = fig_density()
    print("buckets %d | gmax %.0f" % (nb, gmax))
    print("junction %.5f %.5f | edges %d | hit-edges %d" % (JUNC[0], JUNC[1], len(GEOM), len(_hit)))
    print("zoom box km: %.1f x %.1f" % ((ZB[2]-ZB[0]) * 111.32 * math.cos(math.radians(24.8)),
                                        (ZB[3]-ZB[1]) * 110.57))
    print("vmax:", {k: round(v, 1) for k, v in VMAX.items()})
    for n in ("map_problem", "map_arms", "map_chosen", "map_density"):
        print(n, os.path.getsize(os.path.join(IMG, n + ".svg")) // 1024, "KB")
