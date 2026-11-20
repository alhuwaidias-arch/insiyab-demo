#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SVG → PNG بنفس طريقة العرض: كروم بلا واجهة بمقياس ٢× ثم تصغير إلى العرض
الطبيعي. كروم هو من يشكّل العربية (cairosvg لا يشكّلها فتُخرج حروفًا مفكّكة).

الاستخدام:
    uv run --python 3.12 --with pillow python build/rasterize_maps.py [اسم...]
"""
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(HERE)
IMG = os.path.join(DEMO, "images")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT = ("map_problem", "map_arms", "map_chosen", "map_chosen_slide", "map_density")


def size(svg_path):
    head = open(svg_path, encoding="utf-8").read(600)
    w = int(re.search(r'\swidth="(\d+)"', head).group(1))
    h = int(re.search(r'\sheight="(\d+)"', head).group(1))
    return w, h


def shot(name):
    svg = os.path.join(IMG, name + ".svg")
    png = os.path.join(IMG, name + ".png")
    w, h = size(svg)
    tmp = os.path.join(IMG, "_" + name + "_2x.png")
    args = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2", "--default-background-color=00000000",
            f"--window-size={w},{h}", f"--screenshot={tmp}", "file:///" + svg.replace("\\", "/")]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=180)
    im = Image.open(tmp).convert("RGB")
    im = im.resize((w, h), Image.LANCZOS)      # تنزيل من ٢× ⇒ حواف نظيفة
    im.save(png, optimize=True)
    os.remove(tmp)
    print(f"{name}: {w}x{h} → {os.path.getsize(png)//1024} KB")


if __name__ == "__main__":
    for n in (sys.argv[1:] or DEFAULT):
        shot(n)
