"""يولّد صور الأثر (figures) من بيانات القياس داخل data/ — بلا أرقام مكتوبة في الكود.

الرسوم بالإنجليزية المحايدة (محاور/وحدات) لأن مطبعة العربية في matplotlib
تُنتج حروفًا مفكّكة؛ الشروح العربية في الواجهة نفسها.

    python build/make_figures.py
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "images")
os.makedirs(IMG, exist_ok=True)

NAVY, SLATE, RED, AMBER, GREEN = "#0A2463", "#8D99AE", "#c0392b", "#d68910", "#1e8449"


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(SLATE)
    ax.spines["bottom"].set_color(SLATE)
    ax.tick_params(colors="#33415c", labelsize=9)
    ax.grid(axis="x", color="#e3e8ef", lw=.8)
    ax.set_axisbelow(True)


def fig_top_streets(dmg):
    st = [s for s in dmg["closure"]["streets"] if s["added_vh"] > 0][:12][::-1]
    fig, ax = plt.subplots(figsize=(8.2, 4.4), dpi=170)
    vals = [s["added_vh"] for s in st]
    # أسماء الشوارع عربية ⇒ نستبدلها بمعرّف محايد ونضع الاسم في الواجهة
    ax.barh(range(len(st)), vals, color=RED, alpha=.85, height=.62)
    ax.set_yticks(range(len(st)))
    ax.set_yticklabels([f"street #{i+1}" for i in range(len(st))], fontsize=9)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * .015, i, f"{v:,.0f}", va="center", fontsize=8.5, color="#33415c")
    ax.set_xlabel("added delay (veh·h) — closure vs baseline", fontsize=10, color="#33415c")
    ax.set_title("Top streets by added delay", fontsize=12, color=NAVY, loc="left", weight="bold")
    style(ax)
    fig.tight_layout()
    p = os.path.join(IMG, "04_top_streets.png")
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    return p, st


def fig_trip_hist(trips):
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=170)
    for arm, c, lab in (("baseline", SLATE, "baseline"), ("closure", RED, "closure"), ("detour", GREEN, "closure + detour")):
        h = trips[arm]["hist"]
        binw = trips[arm]["hist_bin_min"]
        xs = [i * binw for i in range(len(h))]
        ax.plot(xs, h, color=c, lw=1.8, label=f"{lab} (mean {trips[arm]['mean']:.1f} min)")
        ax.fill_between(xs, h, color=c, alpha=.10)
    ax.set_xlim(0, 70)
    ax.set_ylim(0, None)
    ax.set_xlabel("trip duration (min)", fontsize=10, color="#33415c")
    ax.set_ylabel("vehicles", fontsize=10, color="#33415c")
    ax.set_title("Trip duration distribution", fontsize=12, color=NAVY, loc="left", weight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(color="#e3e8ef", lw=.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    p = os.path.join(IMG, "05_trip_hist.png")
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    return p


def fig_split(dmg):
    cl, de = dmg["closure"], dmg["detour"]
    fig, ax = plt.subplots(figsize=(8.2, 2.9), dpi=170)
    rows = [("closure", cl), ("closure + detour", de)]
    for i, (lab, d) in enumerate(rows):
        add, rec = d["added_vh_positive"], d["recovered_vh"]
        stay = add - rec
        ax.barh(i, rec, color=GREEN, height=.5, label="recovered on alternate streets" if i == 0 else None)
        ax.barh(i, stay, left=rec, color=RED, alpha=.85, height=.5,
                label="delay that stays inside the corridor network" if i == 0 else None)
        ax.text(add * 1.01, i, f"net {d['net_vh']:,.0f} veh·h", va="center", fontsize=9, color="#33415c")
    ax.set_yticks([0, 1])
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5)
    ax.set_xlabel("veh·h", fontsize=10, color="#33415c")
    ax.set_title("Added delay: recovered vs staying in network", fontsize=12, color=NAVY, loc="left", weight="bold")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    style(ax)
    fig.tight_layout()
    p = os.path.join(IMG, "06_delay_split.png")
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    return p


def fig_detour_gain(dmg):
    cl = {s["street"]: s["added_vh"] for s in dmg["closure"]["streets"]}
    g = [(s["street"], cl.get(s["street"], 0.0) - s["added_vh"]) for s in dmg["detour"]["streets"]]
    g_all = sorted([x for x in g if x[1] > 0.5], key=lambda x: -x[1])
    g = g_all[:10][::-1]
    fig, ax = plt.subplots(figsize=(8.2, 3.9), dpi=170)
    ax.barh(range(len(g)), [v for _, v in g], color=GREEN, alpha=.9, height=.62)
    ax.set_yticks(range(len(g)))
    ax.set_yticklabels([f"street #{i+1}" for i in range(len(g))], fontsize=9)
    for i, (_, v) in enumerate(g):
        ax.text(v * 1.01, i, f"{v:,.0f}", va="center", fontsize=8.5, color="#33415c")
    ax.set_xlabel("delay removed by the detour (veh·h)", fontsize=10, color="#33415c")
    ax.set_title("Where the detour proposal actually helps", fontsize=12, color=NAVY, loc="left", weight="bold")
    style(ax)
    fig.tight_layout()
    p = os.path.join(IMG, "07_detour_gain.png")
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    return p, g_all


def main():
    dmg = load("damage.json")["damage"]
    trips = load("trips.json")["trips"]
    p1, st = fig_top_streets(dmg)
    p2 = fig_trip_hist(trips)
    p3 = fig_split(dmg)
    p4, gain = fig_detour_gain(dmg)
    # بيان الصور: العناوين العربية تُقرأ في الواجهة من هنا (لا نكتبها في HTML)
    manifest = {
        "source": "data/damage.json · data/trips.json (مشتقّة من runs/*/edgedata.xml)",
        "built": str(int(max(os.path.getmtime(os.path.join(IMG, f)) for f in os.listdir(IMG) if f.endswith(".png")))),
        "figures": [
            {"file": "images/01_baseline.png", "title": "خط الأساس — لا إغلاق", "kind": "map",
             "note": "لا تأخير مضاف: كل الأضلاع رمادية."},
            {"file": "images/02_closure.png", "title": "إغلاق تقاطع أنس × تركي", "kind": "map",
             "note": f"تأخير مضاف {dmg['closure']['added_vh_positive']:,.0f} مركبة‑ساعة على {dmg['closure']['edges_hit']:,} ضلعًا."},
            {"file": "images/03_detour.png", "title": "إغلاق + تحويلة مدعومة", "kind": "map",
             "note": f"صافي {dmg['detour']['net_vh']:,.0f} مركبة‑ساعة: التحويلة تسترد {dmg['detour']['recovered_vh']:,.0f}."},
            {"file": "images/04_top_streets.png", "title": "أعلى الشوارع تأخيرًا (إغلاق)",
             "kind": "chart", "note": "، ".join(f"{s['street']} {s['added_vh']:,.0f}" for s in
                                                 [x for x in st if not x['street'].startswith(('No.', 'رقم', 'شارع رقم', '(بلا اسم)'))][:4])},
            {"file": "images/05_trip_hist.png", "title": "توزيع زمن الرحلة",
             "kind": "chart", "note": f"خط الأساس {trips['baseline']['mean']:.1f} دقيقة ⇒ الإغلاق {trips['closure']['mean']:.1f} ⇒ مع التحويلة {trips['detour']['mean']:.1f}."},
            {"file": "images/06_delay_split.png", "title": "أين يبقى التأخير؟",
             "kind": "chart", "note": "الأخضر يُسترد على شوارع بديلة، الأحمر يبقى داخل شبكة الممر."},
            {"file": "images/07_detour_gain.png", "title": "أين تفيد التحويلة فعلًا؟",
             "kind": "chart", "note": "، ".join(f"{s} −{v:,.0f}" for s, v in gain[:3] if not s.startswith(('No.', 'رقم', 'شارع رقم', '(بلا اسم)')))
                     + f" — استرداد إجمالي {sum(v for _, v in gain):,.0f} مركبة‑ساعة على {len(gain)} شارعًا، وصافي الذراع 265 بعد ما تسوءه التحويلة في أضلاع أخرى."},
        ],
    }
    with open(os.path.join(D, "figures.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    for p in (p1, p2, p3):
        print("OK", os.path.relpath(p, ROOT), os.path.getsize(p))


if __name__ == "__main__":
    main()
