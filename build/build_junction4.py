"""يبني data/junction.json لمشهد «أربعة مسارات وثلاث محاولات دوران» من مخرج SUMO وحده.

كل رقم هنا محسوب من خطوات fcd ومن ملف الشبكة — لا رقم مكتوب بيد:
  peak*              أعلى عدد مركبات في خطوة واحدة داخل نافذة العرض
  lanes[]            لكل حارة اقتراب: متوسط السرعة، أعلى عدد متوقف، أطول طابور (م)
  uturn_*            بدأ/أكمل/أعلى انتظار متزامن، معدل الإنجاز (مركبة/ساعة)، متوسط الانتظار
  triple_*           ثوانٍ تكون فيها ثلاث مركبات دوران على ثلاث حارات مختلفة داخل 40 م من الخط
  straight_free      نسبة الخطوات التي خلا فيها المسار الأول من أي مركبة متوقفة
  demand, net, clip  معاملات الطلب وخصائص الشبكة وبيانات المقطع

  python build/build_junction4.py --fcd F --net N --clip C --t0 100 --t1 145 \
      --demand '{"thru_vph":1200}'
"""
import argparse
import json
import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES = ["app_0", "app_1", "app_2", "app_3"]
STOP_X = 458.0          # خط التوقف على حافة الاقتراب
NEAR = 40.0             # نافذة «قريب من الفتحة»
IS_UT = lambda v: v.startswith(("f_ut", "UT"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fcd", required=True)
    ap.add_argument("--net", required=True)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--t0", type=float, default=100.0)
    ap.add_argument("--t1", type=float, default=145.0)
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--demand", default="{}")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "junction.json"))
    a = ap.parse_args()

    acc = {l: {"n": 0, "sp": 0.0, "stop_max": 0, "queue_m": 0.0, "free_steps": 0, "steps": 0}
           for l in LANES}
    peak, peak_t = 0, None
    seen = set()
    ut_first, ut_done = {}, {}
    wait_peak = 0
    triple_steps = 0
    triple_events = 0
    in_episode = False
    steps_in = 0
    jam_onset = None
    stop_steps = 0.0

    for _, el in ET.iterparse(a.fcd, events=("end",)):
        if el.tag != "timestep":
            continue
        t = round(float(el.get("time")), 2)
        if not (a.t0 <= t <= a.t1):
            el.clear()
            continue
        vehs = el.findall("vehicle")
        steps_in += 1
        if len(vehs) > peak:
            peak, peak_t = len(vehs), t
        per_lane_stop = {l: [] for l in LANES}
        near = {l: 0 for l in LANES}
        waiting = 0
        for v in vehs:
            vid = v.get("id")
            lane = v.get("lane")
            sp = float(v.get("speed"))
            x = float(v.get("x"))
            seen.add(vid)
            if lane in acc:
                acc[lane]["n"] += 1
                acc[lane]["sp"] += sp
                if sp < 0.3:
                    per_lane_stop[lane].append(x)
            if IS_UT(vid):
                if lane.startswith("app_"):
                    ut_first.setdefault(vid, t)
                    waiting += 1
                    if lane in near and (STOP_X - x) <= NEAR:
                        near[lane] = 1
                elif lane.startswith("wb_") or lane.startswith("wb_in_"):
                    ut_done.setdefault(vid, t)
        wait_peak = max(wait_peak, waiting)
        tot_stop = 0
        for l in LANES:
            st = per_lane_stop[l]
            acc[l]["steps"] += 1
            acc[l]["stop_max"] = max(acc[l]["stop_max"], len(st))
            if st:
                acc[l]["queue_m"] = max(acc[l]["queue_m"], round(STOP_X - min(st), 1))
            else:
                acc[l]["free_steps"] += 1
            tot_stop += len(st)
        if tot_stop >= 10 and jam_onset is None:
            jam_onset = t
        stop_steps += tot_stop
        if near["app_3"] and near["app_2"] and near["app_1"]:
            triple_steps += 1
            if not in_episode:
                triple_events += 1
                in_episode = True
        else:
            in_episode = False
        el.clear()

    span = a.t1 - a.t0
    lanes = []
    for l in LANES:
        d = acc[l]
        lanes.append({
            "lane": l,
            "mean_kmh": round(d["sp"] / d["n"] * 3.6, 1) if d["n"] else 0.0,
            "stopped_max": d["stop_max"],
            "queue_m": d["queue_m"],
            "free_share_pct": round(100.0 * d["free_steps"] / max(1, d["steps"]), 1),
        })

    started = [v for v, t0 in ut_first.items()]
    done = [v for v in started if v in ut_done]
    waits = [round(ut_done[v] - ut_first[v], 1) for v in done]
    net = ET.parse(a.net).getroot()
    edges = [e for e in net.findall("edge") if not e.get("id").startswith(":")]
    conns_to_ut = 0
    for c in net.findall("connection"):
        if c.get("to") == "ut":
            conns_to_ut += 1
    ut_lane = net.find("edge[@id='ut']/lane")
    clip_bytes = os.path.getsize(a.clip)

    out = {
        "scene": "sumo4 — أربعة مسارات، ثلاث محاولات دوران، فتحة واحدة",
        "window": [a.t0, a.t1],
        "span_s": round(span, 2),
        "fps": a.fps,
        "frames": int(round(span * a.fps)),
        "peak_vehicles": peak,
        "peak_t": peak_t,
        "vehicles_total": len(seen),
        "lanes": lanes,
        "jam_onset_s": jam_onset,
        "stopped_mean_total": round(stop_steps / max(1, steps_in), 1),
        "uturn_started": len(started),
        "uturn_completed": len(done),
        "uturn_waiting_peak": wait_peak,
        "uturn_throughput_veh_h": round(3600.0 * len(done) / span, 1),
        "uturn_mean_wait_s": round(sum(waits) / len(waits), 1) if waits else None,
        "uturn_wait_max_s": max(waits) if waits else None,
        "triple_overlap_s": round(triple_steps * 0.2, 1),
        "triple_events": triple_events,
        "straight_free_pct": lanes[0]["free_share_pct"],
        "demand": json.loads(a.demand),
        "net": {
            "edges": len(edges),
            "approach_lanes": len(LANES),
            "connections_to_uturn": conns_to_ut,
            "uturn_lane_speed_ms": float(ut_lane.get("speed")) if ut_lane is not None else None,
            "uturn_lane_length_m": float(ut_lane.get("length")) if ut_lane is not None else None,
            "traffic_lights": len(net.findall("tlLogic")),
        },
        "clip": {
            "src": "media/uturn_clip.mp4",
            "bytes": clip_bytes,
            "duration_s": round(span * (1.0), 1),
            "frames": int(round(span * a.fps)),
        },
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("peak_vehicles", "peak_t", "uturn_started",
                                          "uturn_completed", "uturn_throughput_veh_h",
                                          "triple_overlap_s", "triple_events",
                                          "straight_free_pct", "jam_onset_s",
                                          "uturn_mean_wait_s", "clip")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
