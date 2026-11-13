"""يبني حزمة حقائق مضغوطة (data/ai_facts.json) تُغذّى للنموذج وللتحقق.

كل رقم في الحزمة مأخوذ من ملفات مشتقة من runs/*: لا حساب جديد هنا.
"""
import json
import os

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    canon = load("canon.json")
    arms = load("arms.json")["arms"]
    dmg = load("damage.json")["damage"]
    trips = load("trips.json")["trips"]

    def arm_stats(a):
        s = arms[a]["stats"]
        out = {}
        for k, v in s.items():
            out[k] = {"mean": round(v["mean"], 2), "sd": round(v["sd"], 2)}
        return out

    facts = {
        "project": {
            "name": "انسياب",
            "city": "الرياض",
            "corridor": "شارع أنس بن مالك",
            "intervention": "إغلاق تقاطع أنس × تركي",
            "engine": "SUMO 1.27.0",
            "network": {"edges": 8488, "streets": 1169},
        },
        "arms": {a: arm_stats(a) for a in arms},
        "damage": {
            a: {
                "added_vh_positive": round(dmg[a].get("added_vh_positive", 0), 1),
                "net_vh": round(dmg[a].get("net_vh", 0), 1),
                "recovered_vh": round(dmg[a].get("recovered_vh", 0), 1),
                "edges_hit": dmg[a].get("edges_hit"),
                "empty_edges": dmg[a].get("empty_edges"),
                "top_streets": [
                    {"street": s["street"], "added_vh": round(s["added_vh"], 1)}
                    for s in dmg[a]["streets"][:6]
                ],
            }
            for a in dmg
        },
        "trips_mean_min": {a: round(trips[a]["mean"], 2) for a in trips},
        "canon_numbers": [
            {"arm": n.get("arm"), "field": n.get("field"), "value": n.get("value"), "unit": n.get("unit")}
            for n in canon["numbers"]
        ],
        "banned_numbers": canon.get("banned", []),
        "policy": canon.get("policy"),
        "limits": canon.get("limits", []),
    }
    p = os.path.join(D, "ai_facts.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=1)
    print("OK", p, os.path.getsize(p), "bytes",
          "| arms:", ",".join(facts["arms"]), "| canon:", len(facts["canon_numbers"]),
          "| limits:", len(facts["limits"]))


if __name__ == "__main__":
    main()
