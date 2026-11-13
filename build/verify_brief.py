"""يتحقق أن كل رقم في data/ai_brief.md موجود في data/ai_facts.json أو مشتقّ منه بصيغة معلنة.

الغرض: منع «تحليل ذكاء اصطناعي» يحمل رقمًا مُختلقًا. أي رقم لا يُطابق ⇒ exit 3.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def all_numbers(node, out):
    if isinstance(node, dict):
        for v in node.values():
            all_numbers(v, out)
    elif isinstance(node, list):
        for v in node:
            all_numbers(v, out)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out.add(round(float(node), 2))
    return out


def derived(f):
    c, d = f["damage"]["closure"], f["damage"]["detour"]
    top3 = sum(s["added_vh"] for s in c["top_streets"][:3])
    saved = c["net_vh"] - d["net_vh"]
    dm, dd = f["arms"]["detour"]["duration_mean_min"], f["arms"]["closure"]["duration_mean_min"]
    dmg = f["damage"]
    gain = sorted(
        [(s["street"], s["added_vh"]) for s in dmg["closure"]["streets"]]
        if "streets" in dmg["closure"] else [], key=lambda x: -x[1]
    )
    return {
        "stay_pct": c["net_vh"] / c["added_vh_positive"] * 100,
        "top3_pct": top3 / c["added_vh_positive"] * 100,
        "top3_sum": top3,
        "saved": saved,
        "saved_pct": saved / c["net_vh"] * 100,
        "dur_diff": dd["mean"] - dm["mean"],
        "dur_ratio": dd["mean"] / dm["mean"],
        "policy_ratio": f["trips_mean_min"]["policy600"] / f["trips_mean_min"]["baseline"],
        # رقم سياسة مُرمَّز في اسم الذراع نفسه (policy600 ⇒ حدّ انتظار 600 ثانية)
        "policy600_wait_s": float(int([k for k in f["arms"] if k.startswith("policy")][0][6:])),
    }


def main():
    facts = json.load(open(os.path.join(D, "ai_facts.json"), encoding="utf-8"))
    brief = open(os.path.join(D, "ai_brief.md"), encoding="utf-8").read()

    allowed = {round(v, 2) for v in all_numbers(facts, set())}
    drv = derived(facts)
    for v in drv.values():
        allowed.add(round(float(v), 2))

    hits, bad = [], []
    for raw in NUM.findall(brief):
        val = round(float(raw.replace(",", "")), 2)
        if any(abs(val - a) <= 0.051 for a in allowed):
            hits.append((raw, val))
        else:
            bad.append(raw)

    print(f"facts={len(allowed)} numbers in brief={len(hits) + len(bad)} matched={len(hits)} bad={len(bad)}")
    print("derived:", {k: round(v, 2) for k, v in drv.items()})
    status = {
        "ok": not bad,
        "matched": len(hits),
        "total": len(hits) + len(bad),
        "bad": sorted(set(bad)),
        "ran_at": __import__("time").strftime("%Y-%m-%d %H:%M"),
        "source": "data/ai_brief.md ← data/ai_facts.json",
    }
    with open(os.path.join(D, "ai_brief_status.json"), "w", encoding="utf-8") as fh:
        json.dump(status, fh, ensure_ascii=False, indent=1)
    if bad:
        print("UNSUPPORTED:", sorted(set(bad)))
        print("FAIL")
        return 3
    print("OK — كل رقم في القراءة مسنود إلى data/ai_facts.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
