#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""صورة اللوحة الحيّة — من الخادم المحلي إلى PNG بنفس مقياس الشريحة (1.60:1).

الاستخدام:
    python3 build/shot_app.py                      # تبويب الحلول
    python3 build/shot_app.py solutions out.png     # صريحًا
كروم بلا واجهة بمقياس ٢× ثم تصغير ⇒ نص عربي حادّ بلا تمويج.
"""
import os
import subprocess
import sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
W, H = 1340, 838          # 1.599:1 ≈ نسبة الصورة في الشريحة (6.5 × 4.06 بوصة)
BASE = "http://127.0.0.1:8111/index.html"


def shot(view: str, out: str, wait_ms: int = 4000) -> None:
    tmp = os.path.splitext(out)[0] + "_2x.png"
    args = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2", f"--window-size={W},{H}",
            f"--virtual-time-budget={wait_ms}",
            f"--screenshot={tmp}", f"{BASE}#v={view}"]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=180)
    try:
        from PIL import Image
        im = Image.open(tmp).convert("RGB").resize((W, H), Image.LANCZOS)
        im.save(out, optimize=True)
        os.remove(tmp)
        print(f"{view}: {W}x{H} → {os.path.getsize(out)//1024} KB → {out}")
    except ImportError:      # بلا Pillow: نُبقي ٢×
        os.replace(tmp, out)
        print(f"{view}: 2x → {out}")


if __name__ == "__main__":
    view = sys.argv[1] if len(sys.argv) > 1 else "solutions"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images", f"app_{view}.png")
    shot(view, out)
