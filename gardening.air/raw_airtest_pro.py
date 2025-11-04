"""
raw_airtest_pro.py
Skalierungsfreies Airtest-Ersatzmodul für Emulatoren (MEmu, LDPlayer, BlueStacks).
Funktionen:
 - Unskalierte Screenshots via adb exec-out screencap -p
 - Automatische App-Viewport-Erkennung (z. B. 9:16)
 - Template Matching mit OpenCV (Airtest-kompatibel)
 - exists, all_click, q_exists, swipe, touch, drag_seed, refill
"""

import os
import subprocess
import time
from PIL import Image
import cv2
import numpy as np
from airtest.core.cv import Template

# Emulator-Loader
from emulator_loader import get_active_emulators
# ------------------ Globales ADB festlegen ------------------
ANDROID_SDK_ADB = r"C:\Users\User\AppData\Local\Android\Sdk\platform-tools\adb.exe"
ADB_PATH = ANDROID_SDK_ADB  # Full path to adb.exe

LOG_DIR = "logs"
ABS_LOG_DIR = os.path.abspath(LOG_DIR)
os.makedirs(ABS_LOG_DIR, exist_ok=True)


# ------------------ Emulator Hilfsfunktionen ------------------
def adb_exec(cmd, device_addr, text=True, **kwargs):
    """Führe adb-Befehl auf einem bestimmten Emulator aus"""
    full_cmd = [ADB_PATH, "-s", device_addr] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=text, **kwargs)


def get_display_info(device_addr):
    """Liefert Display-Auflösung und dpi"""
    out_size = adb_exec(["shell", "wm", "size"], device_addr).stdout.strip()
    out_density = adb_exec(["shell", "wm", "density"], device_addr).stdout.strip()
    w, h, dpi = None, None, None
    if "Physical size" in out_size:
        try:
            w, h = map(int, out_size.split(":")[1].strip().split("x"))
        except Exception:
            pass
    if "Physical density" in out_density or "Override density" in out_density:
        try:
            dpi = int(out_density.split()[-1])
        except Exception:
            pass
    print(f"[INFO] Emulator Display: {w}x{h} @ {dpi}dpi")
    return w, h, dpi


# ------------------ Viewport-Erkennung ------------------
def estimate_viewport(screenshot_path, app_ratio=(9, 16)):
    img = Image.open(screenshot_path)
    screen_w, screen_h = img.size
    target_ratio = app_ratio[0] / app_ratio[1]
    screen_ratio = screen_w / screen_h

    if screen_ratio > target_ratio:  # schwarze Balken links/rechts
        app_h = screen_h
        app_w = int(app_h * target_ratio)
        left = (screen_w - app_w) // 2
        top = 0
    else:                            # schwarze Balken oben/unten
        app_w = screen_w
        app_h = int(app_w / target_ratio)
        left = 0
        top = (screen_h - app_h) // 2

    right = left + app_w
    bottom = top + app_h
    print(f"[INFO] App-Viewport erkannt: ({left},{top},{right},{bottom})")
    return (left, top, right, bottom)


# ------------------ Screenshot ------------------
def raw_screenshot(device_addr, filename="raw.png", crop=True, viewport=None):
    raw_path = os.path.join(ABS_LOG_DIR, filename)
    cmd = ["exec-out", "screencap", "-p"]
    with open(raw_path, "wb") as f:
        subprocess.run([ADB_PATH, "-s", device_addr] + cmd, stdout=f, check=True)

    if crop:
        if not viewport:
            viewport = estimate_viewport(raw_path)
        img = Image.open(raw_path)
        cropped = img.crop(viewport)
        crop_path = raw_path.replace(".png", "_crop.png")
        cropped.save(crop_path)
        return crop_path, viewport
    return raw_path, None


# ------------------ Hilfsfunktion: sicheres Laden ------------------
def load_image_bgr(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"[ERROR] Konnte Bild nicht lesen: {path}")
        return None
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


# ------------------ Template Matching ------------------
def find_template(tpl: Template, screen_path):
    screen = load_image_bgr(screen_path)
    tpl_img = load_image_bgr(tpl.filename)
    if screen is None or tpl_img is None:
        return None
    res = cv2.matchTemplate(screen, tpl_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= tpl.threshold:
        h, w = tpl_img.shape[:2]
        center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        return {"result": center, "confidence": float(max_val)}
    return None


def exists_raw(device_addr, tpl: Template, viewport=None, timeout=2):
    """
    Sucht ein Template im aktuellen Screenshot.
    Gibt absolute Bildschirmkoordinaten (x, y) zurück, auch wenn gecroppt wurde.
    """
    start = time.time()
    while time.time() - start < timeout:
        path, vp = raw_screenshot(device_addr, "tmp_screen.png", crop=True, viewport=viewport)
        match = find_template(tpl, path)
        if match:
            x, y = match["result"]
            conf = match["confidence"]
            # Offset aus dem Crop-Bereich addieren, damit der Tap stimmt
            if vp:
                left, top, _, _ = vp
                x += left
                y += top
            abs_pos = (int(x), int(y))
            print(f"[OK] {tpl.filename} gefunden @ {abs_pos} (conf={conf:.2f})")
            return abs_pos
        time.sleep(0.3)
    return None


def all_matches_raw(device_addr, tpl: Template, viewport=None):
    """
    Liefert alle Treffer des Templates mit globalen Bildschirmkoordinaten.
    """
    path, vp = raw_screenshot(device_addr, "tmp_screen.png", crop=True, viewport=viewport)
    screen = load_image_bgr(path)
    tpl_img = load_image_bgr(tpl.filename)
    if screen is None or tpl_img is None:
        return []
    res = cv2.matchTemplate(screen, tpl_img, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= tpl.threshold)
    h, w = tpl_img.shape[:2]
    matches = []
    for (x, y) in zip(loc[1], loc[0]):
        cx, cy = int(x + w / 2), int(y + h / 2)
        if vp:
            left, top, _, _ = vp
            cx += left
            cy += top
        matches.append((cx, cy))
    print(f"[INFO] {len(matches)} Treffer für {tpl.filename}")
    return matches


# ------------------ Interaktionen ------------------
def tap(device_addr, pos):
    x, y = map(int, pos)
    adb_exec(["shell", "input", "tap", str(x), str(y)], device_addr)
    print(f"[TOUCH] {x},{y}")


def swipe(device_addr, start, end, duration=0.5):
    x1, y1 = map(int, start)
    x2, y2 = map(int, end)
    adb_exec(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(int(duration*1000))], device_addr)
    print(f"[SWIPE] {start} -> {end}")


# ------------------ High-Level Aktionen ------------------
def all_click_raw(device_addr, tpl, viewport=None):
    matches = all_matches_raw(device_addr, tpl, viewport)
    for pos in matches:
        tap(device_addr, pos)
        time.sleep(0.2)
    return len(matches)


def q_exists_raw(device_addr, tpl, timeout=2, viewport=None):
    start = time.time()
    while time.time() - start < timeout:
        pos = exists_raw(device_addr, tpl, viewport)
        if pos:
            return pos
        time.sleep(0.2)
    return None


def drag_seed(device_addr, seed_tpls, free_place_tpl, viewport=None):
    slot = q_exists_raw(device_addr, free_place_tpl, viewport=viewport)
    if not slot:
        return False
    for seed_tpl in seed_tpls:
        seed = q_exists_raw(device_addr, seed_tpl, viewport=viewport)
        if seed:
            swipe(device_addr, seed, slot, duration=0.5)
            return True
    return False


def refill(device_addr, slot_tpl, plus_tpl, green_btn_tpl, viewport=None):
    slot = q_exists_raw(device_addr, slot_tpl, viewport=viewport)
    if not slot:
        return False
    tap(device_addr, slot)
    for _ in range(10):
        plus = q_exists_raw(device_addr, plus_tpl, timeout=0.5, viewport=viewport)
        if not plus:
            break
        tap(device_addr, plus)
    btn = q_exists_raw(device_addr, green_btn_tpl, viewport=viewport)
    if btn:
        tap(device_addr, btn)
        time.sleep(1)
        return True
    return False
