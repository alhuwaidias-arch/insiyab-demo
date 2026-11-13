#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انسياب — استخراج هندسة الشبكة إلى JSON للواجهة.

Input : D:\\INFIRAD\\projects\\insiyab\\data\\network\\insyab.net.xml  (SUMO 1.27.0)
Output: data/network.json

كل نقطة تُخزَّن بإحداثيات جغرافية (lon/lat، 5 منازل ≈ 1 م) لأن الواجهة ترسمها
إسقاطًا محليًا بلا إنترنت، وتستطيع تمريرها إلى خريطة حقيقية عند توفر الشبكة.
لا رقم هندسي هنا يُنشر في العرض: هذه هندسة فقط، والأرقام في data/canon.json.
"""
import json, os, sys, datetime

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
if not os.path.isdir(os.path.join(SUMO_HOME, "tools")) and os.environ.get("SUMO_HOME", "").startswith("C:"):
    SUMO_HOME = os.environ["SUMO_HOME"]
sys.path.insert(0, os.path.join(SUMO_HOME, "tools"))
import sumolib  # noqa: E402

NET = sys.argv[1] if len(sys.argv) > 1 else r"D:\INFIRAD\projects\insiyab\data\network\insyab.net.xml"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "network.json")

net = sumolib.net.readNet(NET)
edges = [e for e in net.getEdges() if not e.getID().startswith(":")]

streets, street_idx = [], {}
shapes, feats = [], []
for e in edges:
    name = (e.getName() or "").strip()
    if name not in street_idx:
        street_idx[name] = len(streets)
        streets.append(name)
    xy = e.getShape()
    ll = [net.convertXY2LonLat(x, y) for x, y in xy]
    off = len(shapes) // 2                      # إزاحة بالنقاط داخل مصفوفة مسطّحة
    for lon, lat in ll:
        shapes.append(round(lon, 5)); shapes.append(round(lat, 5))
    feats.append([
        e.getID(),                                   # 0 id
        street_idx[name],                            # 1 street index
        round(sum(l.getLength() for l in e.getLanes()), 1),  # 2 length m
        round(e.getSpeed(), 2),                      # 3 free-flow m/s
        len(e.getLanes()),                           # 4 lanes
        off,                                         # 5 shape offset (points)
        len(ll),                                     # 6 shape point count
    ])

corridor_names = [n for n in streets if "أنس بن مالك" in n]
payload = {
    "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "engine": "Eclipse SUMO 1.27.0",
    "source": os.path.basename(NET),
    "fields": ["id", "street", "length_m", "speed_ms", "lanes", "shape_off", "shape_n"],
    "streets": streets,
    "corridor_streets": corridor_names,
    "edges": feats,
    "shapes": shapes,
    "counts": {"edges": len(feats), "streets": len(streets), "lanes": sum(f[4] for f in feats)},
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
print(f"OK edges={len(feats)} streets={len(streets)} shapes={len(shapes)} bytes={os.path.getsize(OUT)}")
print("corridor street names:", corridor_names)
