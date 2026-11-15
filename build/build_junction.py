"""يبني data/junction.json — أرقام مشهد التقاطع من مخرج SUMO نفسه (fcd.xml).

كل رقم هنا يُحسب من التتبّع الكامل للمركبات، لا يُكتب بيد:
  peak        أقصى عدد مركبات في خطوة زمنية واحدة داخل نافذة العرض
  turn_times  زمن دخول كل مركبة U-Turn وصلة الدوران الداخلية (lane يبدأ بـ':')
  edges       عدد حواف المشهد المقصوص
  frames      عدد إطارات الفيديو بنافذة العرض و25 إطارًا/ث

الاستخدام:
  python build/build_junction.py --fcd <fcd.xml> --net <clip.net.xml> --t0 28 --t1 46
"""
import argparse
import json
import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fcd", required=True)
    ap.add_argument("--net", required=True)
    ap.add_argument("--t0", type=float, default=28.0)
    ap.add_argument("--t1", type=float, default=46.0)
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "junction.json"))
    a = ap.parse_args()

    peak, peak_t = 0, None
    seen = set()
    turn = {}
    for _, el in ET.iterparse(a.fcd, events=("end",)):
        if el.tag != "timestep":
            continue
        t = float(el.get("time"))
        if a.t0 <= t <= a.t1:
            vehs = el.findall("vehicle")
            if len(vehs) > peak:
                peak, peak_t = len(vehs), t
            for v in vehs:
                vid, lane = v.get("id"), v.get("lane")
                seen.add(vid)
                if vid.startswith("UT_") and lane.startswith(":") and vid not in turn:
                    turn[vid] = t
        el.clear()

    tel = ET.parse(a.net).getroot()
    edges = [e for e in tel.findall("edge") if not e.get("id").startswith(":")]
    tl = tel.findall("tlLogic")

    span = a.t1 - a.t0
    out = {
        "peak_vehicles": peak,
        "peak_t": peak_t,
        "window": [a.t0, a.t1],
        "span_s": round(span, 2),
        "frames": int(round(span * a.fps)),
        "edges": len(edges),
        "traffic_lights": len(tl),
        "vehicles_total": len(seen),
        "uturn_vehicles": sorted(turn),
        "turn_times": [round(turn[k], 2) for k in sorted(turn)],
        "turn_spread_s": round(max(turn.values()) - min(turn.values()), 2) if turn else None,
        "uturn_turned": len(turn),
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("junction.json", {k: out[k] for k in ("peak_vehicles", "peak_t", "edges", "frames",
                                                "uturn_turned", "turn_times", "turn_spread_s")})


if __name__ == "__main__":
    main()
