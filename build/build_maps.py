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
GREY, BG, CARD, INK, MUTED = "#8d99ae", "#081533", "#0d2150", "#ffffff", "#a8b8d8"
ANAS, TURKI = "شارع أنس بن مالك", "طريق الأمير تركي بن عبدالعزيز الأول"
# لون الطريق المتقاطع مستقل عن سلّم التأخير (الكهرماني) وإلا التبس بالمفتاح
TURKI_C = "#9fb3c8"
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


ARMS = [
    ("baseline", None, "خط الأساس", f"{D['base_min']} دقيقة · بلا إغلاق", GREY),
    ("closure", "damage_closure300.edges.csv", "إغلاق كامل", f"+{D['added_vh']} ساعة انتظار", RED),
    ("detour", "damage_detour300.edges.csv", "توسعة المجاورة", f"−{D['detour_pct']} من التأخير", AMBER),
    ("uturn", "damage_uturn300.edges.csv", "دوران", f"×{D['uturn_ratio']} التأخير — مرفوض", PURPLE),
    ("half", "damage_halfe.edges.csv", "المُختار: اتجاه واحد بمرحلتين", f"−{D['half_vh']} ساعة انتظار", SKY),
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
                out.append(f'<path d="{path(ps, P)}" fill="none" stroke="{TURKI_C}" stroke-width="2.4" '
                           f'stroke-opacity=".45" stroke-dasharray="7 5" stroke-linecap="round"/>')
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
    b.append(T(x - 60, y - 6, "التقاطع مغلق", 26, INK, "l", "700"))
    b.append(T(x - 60, y + 28, "لأعمال تطوير طريق الأمير تركي الأول", 19, "#ffb3ab", "l"))
    west, east = min(ap, key=lambda p: p[0]), max(ap, key=lambda p: p[0])
    for p, anchor, dx, dy, lab in ((west, "l", 16, -16, "شارع أنس بن مالك — الغرب"),
                                   (east, "r", -16, -16, "شارع أنس بن مالك — الشرق")):
        px, py = P(p)
        b.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="8" fill="{SKY}"/>')
        b.append(T(px + dx, py + dy, lab, 21, "#dce6f7", anchor))
    # اسم الطريق المتقاطع على خطّه نفسه — لا يترك للقارئ أن يستنتج
    tp = [p for e in net["edges"] if ST[e[1]] == TURKI for p in pts(e)]
    tN, tS = max(tp, key=lambda p: p[1]), min(tp, key=lambda p: p[1])
    for p, anchor, dy, lab in ((tN, "l", -14, TURKI), (tS, "r", 26, TURKI)):
        px, py = P(p)
        b.append(T(px + (16 if anchor == "l" else -16), py + dy, lab, 20, "#ffd79a", anchor))
    b.append(f'<rect x="34" y="30" width="770" height="140" rx="14" fill="#081b4a" fill-opacity=".9"/>')
    b.append(T(784, 80, "ما نفعله بالضبط", 34, INK, "r", "700"))
    b.append(T(784, 120, "نغلق تقاطع أنس بن مالك مع طريق الأمير تركي الأول مدة الأعمال", 21, MUTED, "r"))
    b.append(T(784, 152, "ونقيس أين يذهب التأخير، وأي تدبير يخففه فعلًا", 21, MUTED, "r"))
    lx, ly = 40, h - 78
    b.append(f'<rect x="{lx-16}" y="{ly-34}" width="720" height="86" rx="12" fill="#081b4a" fill-opacity=".92"/>')
    for i, (colr, dash, lab) in enumerate(((SKY, "", "شارع أنس بن مالك (المحور)"),
                                          (TURKI_C, ' stroke-dasharray="7 5"', TURKI),
                                          (RED, "", "التقاطع المُغلق"))):
        b.append(f'<rect x="{lx + i*258}" y="{ly-6}" width="28" height="9" rx="4" fill="{colr}"/>')
        b.append(T(lx + i*258 + 36, ly + 4, lab, 18, "#dbe5f7", "l"))
    b.append(T(lx + 2, ly + 34, "الشبكة من نموذج المحاكاة (SUMO)، لا خريطة زخرفية", 17, MUTED, "l"))
    open(os.path.join(IMG, "map_problem.svg"), "w", encoding="utf-8").write(doc(w, h, "".join(b)))


# ── 2 · الأذرع الخمسة ───────────────────────────────────────────────────────
def fig_arms(W=1680, H=1230):
    pw, ph = (W - 4 * 18) // 3, 566
    hh = 78
    vmax = max(VMAX.values()) if VMAX else 1
    b = [T(W - 30, 52, "أربعة أذرع على الشبكة نفسها والطلب نفسه", 30, INK, "r", "700"),
         T(W - 30, 86, "كل لوحة تُظهر أين يظهر التأخير — والتقاطع واحد في الخمس", 20, MUTED, "r")]
    for i, (arm, f, title, big, accent) in enumerate(ARMS):
        # RTL: اللوحة 1 أقصى اليمين، ثم 2، ثم 3 — وإلا قرأها القارئ العربي معكوسة
        col, row = 2 - (i % 3), i // 3
        x0, y0 = 18 + col * (pw + 18), 106 + row * (ph + 18)
        P = make_proj(pw, ph - hh, m=16)
        b.append(f'<g transform="translate({x0},{y0})">'
                 f'<rect width="{pw}" height="{ph}" rx="16" fill="{CARD}" stroke="{accent}" '
                 f'stroke-opacity="{0.85 if arm == "half" else 0.28}" '
                 f'stroke-width="{2.5 if arm == "half" else 1}"/>')
        b.append(f'<rect x="16" y="16" width="40" height="28" rx="8" fill="{accent}" fill-opacity=".9"/>')
        b.append(f'<text x="36" y="37" fill="#08122e" font-size="19" font-weight="700" '
                 f'text-anchor="middle">{i+1}</text>')
        b.append(T(pw - 18, 40, title, 24, INK, "r", "700"))
        b.append(T(pw - 18, 68, big, 20, accent, "r", "700"))
        _closed = arm in ("closure", "uturn")
        b.append(f'<g transform="translate(0,{hh})">{network(P, arm, vmax)}'
                 f'{junction(P, 7 if arm == "half" else 6, closed=_closed)}</g></g>')
    # خلية المفتاح
    x0, y0 = 18, 106 + (ph + 18)          # خلية المفتاح: يسار الصف الثاني
    b.append(f'<g transform="translate({x0},{y0})"><rect width="{pw}" height="{ph}" rx="16" '
             f'fill="{CARD}" fill-opacity=".72"/>')
    b.append(T(pw - 20, 48, "كيف تُقرأ الخريطة", 24, INK, "r", "700"))
    rows = [(RED, "تأخير كبير", "أضلاع يزيد تأخيرها كثيرًا"),
            (AMBER, "تأخير متوسط", "أضلاع تتأثر جزئيًا"),
            (GREY, "بلا تغيير", "أضلاع لم يتغير تأخيرها"),
            (SKY, "المحور", "شارع أنس بن مالك"),
            (TURKI_C, "المتقاطع", "طريق الأمير تركي الأول")]
    ty = 108
    for colr, name, note in rows:
        b.append(f'<rect x="{pw-44}" y="{ty-14}" width="26" height="9" rx="4" fill="{colr}"/>')
        b.append(T(pw - 56, ty - 2, name, 19, INK, "r", "700"))
        b.append(T(pw - 56, ty + 24, note, 15, MUTED, "r"))
        ty += 70
    b.append(T(pw - 20, ty + 8, "سماكة الخط = حجم التأخير على الضلع", 15, MUTED, "r"))
    b.append("</g>")
    open(os.path.join(IMG, "map_arms.svg"), "w", encoding="utf-8").write(doc(W, H, "".join(b)))


# ── 3 · الحل المُختار ────────────────────────────────────────────────────────
def fig_chosen(w=1600, h=900):
    """لوحة الحل المُختار — تُقرأ بذاتها: أين التقاطع، أين يبقى المحور مفتوحًا،
    وما المرحلتان، وما معنى اللون والسماكة."""
    P = make_proj(w, h - 10, m=34, box=WB)
    x, y = P(JUNC)
    b = [f'<defs><marker id="arw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" '
         f'markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="{SKY}"/></marker></defs>']
    b.append(network(P, "half", VMAX["half"]))
    b.append(junction(P, 9))

    # أسهم على المحور نفسه: اتجاه واحد، والاتجاه المقابل لا يسير في هذا الوقت
    cor = sorted(((eid, ps) for eid, street, ps in GEOM if street == ANAS),
                 key=lambda t: sum(p[0] for p in t[1]) / len(t[1]))
    picks = [cor[int(len(cor) * f)] for f in (.18, .82)] if len(cor) > 3 else []
    for _eid, ps in picks:
        a, c = (ps[0], ps[-1]) if ps[0][0] < ps[-1][0] else (ps[-1], ps[0])
        pa, pc = P(a), P(c)
        b.append(f'<path d="M {pa[0]:.0f} {pa[1]:.0f} L {pc[0]:.0f} {pc[1]:.0f}" stroke="{SKY}" '
                 f'stroke-width="4.2" stroke-opacity=".95" fill="none" marker-end="url(#arw)"/>')

    # أسماء الشوارع على خطوطها — لا يترك للقارئ أن يستنتج
    west = min(ap, key=lambda p: p[0])
    px, py = P(west)
    b.append(T(px + 18, py - 14, "شارع أنس بن مالك", 21, "#dce6f7", "l"))
    tp = [p for e in net["edges"] if ST[e[1]] == TURKI for p in pts(e)]
    tS = min(tp, key=lambda p: p[1])
    tpx, tpy = P(tS)
    b.append(T(tpx - 16, tpy - 10, TURKI, 19, "#cfd9e6", "r"))

    # المرحلتان: شارتا رقم قرب طرفي المحور
    for k, (p, lab) in enumerate(((west, "المرحلة ١: نصف المحور مفتوح"),
                                  (max(ap, key=lambda p: p[0]), "المرحلة ٢: يُقلب بعد انتهاء الأولى")), 1):
        qx, qy = P(p)
        b.append(f'<circle cx="{qx:.0f}" cy="{qy:.0f}" r="15" fill="{SKY}" fill-opacity=".95"/>')
        b.append(f'<text x="{qx:.0f}" y="{qy+6:.0f}" fill="#08122e" font-size="17" '
                 f'font-weight="700" text-anchor="middle">{k}</text>')
        b.append(T(qx, qy - 26, lab, 18, "#dce6f7", "c"))

    b.append(f'<rect x="34" y="28" width="880" height="132" rx="14" fill="#081b4a" fill-opacity=".92"/>')
    b.append(T(898, 76, "الحل المُختار على الخريطة", 33, INK, "r", "700"))
    b.append(T(898, 112, f"اتجاه واحد بمرحلتين · −{D['half_vh']} ساعة انتظار · "
                         f"+{D['half_extra_km']} كم التفاف", 23, SKY, "r", "700"))
    b.append(T(898, 142, f"{SOL['arms']['half']['edges_hit']} ضلعًا يتأثر فقط من "
                         f"{SOL['arms']['half']['edges_total']:,} ضلعًا في نطاق القياس", 19, MUTED, "r"))

    # مفتاح مقروء بدل سطر صغير في الحاشية
    lx, ly = 34, h - 214
    b.append(f'<rect x="{lx}" y="{ly}" width="600" height="178" rx="12" fill="#081b4a" fill-opacity=".92"/>')
    b.append(T(lx + 568, ly + 32, "كيف تُقرأ الخريطة", 22, INK, "r", "700"))
    rows = [(SKY, "", "المحور مفتوح — اتجاه واحد"),
            (TURKI_C, ' stroke-dasharray="7 5"', TURKI),
            (RED, "", "تأخير كبير على الضلع"),
            ("#e2701e", "", "تأخير متوسط"),
            (GREY, "", "بلا تغيير")]
    for i, (colr, dash, lab) in enumerate(rows):
        yy = ly + 58 + i * 21
        b.append(f'<rect x="{lx + 540}" y="{yy - 9}" width="30" height="9" rx="4" fill="{colr}"/>'
                 + (f'<rect x="{lx + 540}" y="{yy - 9}" width="30" height="9" rx="4" fill="none" '
                    f'stroke="{colr}" stroke-width="2" stroke-dasharray="6 4"/>' if dash else ""))
        b.append(T(lx + 524, yy, lab, 18, "#dbe5f7", "r"))
    b.append(T(w - 40, h - 26, "السهم = الاتجاه المفتوح · سماكة الخط = حجم التأخير المضاف على الضلع",
               18, MUTED, "r"))
    b.append(T(lx + 568, ly + 152, "المرحلتان: يُقلب الاتجاه بعد انتهاء أعمال الجهة الأولى", 16, MUTED, "r"))
    open(os.path.join(IMG, "map_chosen.svg"), "w", encoding="utf-8").write(doc(w, h, "".join(b)))


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
    b.append(T(W - 40, y + 46, "كل خليج ≈ 2% من طول المحور", 17, MUTED, "r"))
    open(os.path.join(IMG, "map_density.svg"), "w", encoding="utf-8").write(doc(W, H, "".join(b)))
    return nb, gmax


if __name__ == "__main__":
    fig_problem()
    fig_arms()
    fig_chosen()
    nb, gmax = fig_density()
    print("buckets %d | gmax %.0f" % (nb, gmax))
    print("junction %.5f %.5f | edges %d | hit-edges %d" % (JUNC[0], JUNC[1], len(GEOM), len(_hit)))
    print("zoom box km: %.1f x %.1f" % ((ZB[2]-ZB[0]) * 111.32 * math.cos(math.radians(24.8)),
                                        (ZB[3]-ZB[1]) * 110.57))
    print("vmax:", {k: round(v, 1) for k, v in VMAX.items()})
    for n in ("map_problem", "map_arms", "map_chosen", "map_density"):
        print(n, os.path.getsize(os.path.join(IMG, n + ".svg")) // 1024, "KB")
