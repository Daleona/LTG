# -*- encoding: utf-8 -*-
"""
Optimierte Logging- & Helper-Funktionen für raw_airtest_pro
- Thread-safe
- Pro-Emulator Screenshot-Ordner
- Fehlerhandling für Tap, Swipe, Drag, Refill
- Windows-kompatibel, Airtest 1.3.6
- Multi-Emulator via connect_device()
"""

import os
import datetime
import json
import time
import threading
from raw_airtest_pro import ABS_LOG_DIR, find_template, all_matches_raw, tap, swipe, exists_raw
from airtest.core.api import snapshot, connect_device

# ------------------ Thread-Safe Lock ------------------
log_lock = threading.Lock()

# ------------------ Helper: Pfade ------------------
def get_log_file(device_addr="global"):
    safe_addr = str(device_addr).replace(":", "_")
    log_dir = os.path.join(ABS_LOG_DIR, safe_addr)
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "actions_log.json")

def get_screenshot_path(prefix, device_addr="global"):
    safe_addr = str(device_addr).replace(":", "_")
    log_dir = os.path.join(ABS_LOG_DIR, safe_addr)
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return os.path.join(log_dir, f"{prefix}_{safe_addr}_{timestamp}.png")

# ------------------ Logging ------------------
def log_action(action_type, template_name=None, position=None, confidence=None, extra=None, device_addr="global"):
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action_type,
        "template": template_name,
        "position": position,
        "confidence": confidence,
        "extra": extra
    }
    log_file = get_log_file(device_addr)
    with log_lock:
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []
        else:
            data = []
        data.append(entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[LOG][{device_addr}] {entry}")

# ------------------ Screenshot ------------------
def save_screenshot_with_timestamp(prefix="screenshot", viewport=None, device_addr="global"):
    """
    Device_addr dient nur für Log/Ordner, snapshot() läuft auf aktuell verbundenem Device
    """
    screenshot_path = get_screenshot_path(prefix, device_addr)
    try:
        snapshot(filename=screenshot_path)
        log_action("screenshot", extra={"file": screenshot_path, "viewport": viewport}, device_addr=device_addr)
        return screenshot_path, viewport
    except Exception as e:
        log_action("screenshot_error", extra={"error": str(e)}, device_addr=device_addr)
        return None, None

# ------------------ Tap / Swipe ------------------
def tap_logged(pos, device_addr=None):
    if pos is None:
        log_action("tap_error", extra={"error": "Position None", "device": device_addr}, device_addr=device_addr)
        return
    screenshot, _ = save_screenshot_with_timestamp("tap", device_addr=device_addr)
    try:
        tap(device_addr, pos)
        log_action("tap", position=pos, extra={"screenshot": screenshot, "device": device_addr}, device_addr=device_addr)
    except Exception as e:
        log_action("tap_error", position=pos, extra={"error": str(e), "screenshot": screenshot, "device": device_addr}, device_addr=device_addr)

def swipe_logged(start, end, duration=0.5, device_addr=None):
    screenshot, _ = save_screenshot_with_timestamp("swipe", device_addr=device_addr)
    try:
        swipe(start, end, duration)
        log_action("swipe", extra={"start": start, "end": end, "duration": duration, "screenshot": screenshot, "device": device_addr}, device_addr=device_addr)
    except Exception as e:
        log_action("swipe_error", extra={"error": str(e), "start": start, "end": end, "duration": duration, "screenshot": screenshot, "device": device_addr}, device_addr=device_addr)

# ------------------ Exists / All Matches ------------------
def exists_raw_logged(tpl, viewport=None, timeout=2, device_addr="global"):
    start = time.time()
    while time.time() - start < timeout:
        path, vp = save_screenshot_with_timestamp("exists", viewport, device_addr)
        match = find_template(tpl, path)
        if match:
            log_action("exists", template_name=tpl.filename, position=match["result"],
                       confidence=match["confidence"], extra={"screenshot": path}, device_addr=device_addr)
            return match["result"]
        time.sleep(0.2)
    log_action("exists", template_name=tpl.filename, position=None, confidence=None, device_addr=device_addr)
    return None

def all_matches_raw_logged(tpl, viewport=None, device_addr="global"):
    path, vp = save_screenshot_with_timestamp("allmatches", viewport, device_addr)
    matches = all_matches_raw(tpl, viewport)
    log_action("all_matches", template_name=tpl.filename, extra={"matches": matches, "screenshot": path}, device_addr=device_addr)
    return matches

# ------------------ Drag & Refill ------------------
def drag_seed_logged(seed_tpls, free_place_tpl, viewport=None, device_addr="global"):
    slot = exists_raw_logged(free_place_tpl, viewport=viewport, device_addr=device_addr)
    if not slot:
        return False
    for seed_tpl in seed_tpls:
        seed = exists_raw_logged(seed_tpl, viewport=viewport, device_addr=device_addr)
        if seed:
            swipe_logged(seed, slot, duration=0.5, device_addr=device_addr)
            log_action("drag_seed", template_name=seed_tpl.filename, extra={"to_slot": free_place_tpl.filename}, device_addr=device_addr)
            return True
    return False

def refill_logged(slot_tpl, plus_tpl, green_btn_tpl, viewport=None, device_addr="global"):
    slot = exists_raw_logged(slot_tpl, viewport=viewport, device_addr=device_addr)
    if not slot:
        return False
    tap_logged(slot, device_addr=device_addr)
    for _ in range(10):
        plus = exists_raw_logged(plus_tpl, timeout=0.5, viewport=viewport, device_addr=device_addr)
        if not plus:
            break
        tap_logged(plus, device_addr=device_addr)
    btn = exists_raw_logged(green_btn_tpl, viewport=viewport, device_addr=device_addr)
    if btn:
        tap_logged(btn, device_addr=device_addr)
        time.sleep(1)
        return True
    return False

# ------------------ HTML Report ------------------
def generate_html_report():
    html_file = os.path.join(ABS_LOG_DIR, "actions_report.html")
    html = "<html><head><meta charset='utf-8'><title>Airtest Report</title></head><body>"
    html += f"<h2>Airtest Actions Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Time</th><th>Action</th><th>Template</th><th>Position</th><th>Confidence</th><th>Screenshot</th><th>Extra</th></tr>"

    for device_dir in os.listdir(ABS_LOG_DIR):
        log_file = os.path.join(ABS_LOG_DIR, device_dir, "actions_log.json")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                continue
            for entry in log_data:
                screenshot_link = ""
                if entry.get("extra") and entry["extra"].get("screenshot"):
                    screenshot_link = f"<a href='{entry['extra']['screenshot']}' target='_blank'>Bild</a>"
                html += "<tr>"
                html += f"<td>{entry['timestamp']}</td>"
                html += f"<td>{entry['action']}</td>"
                html += f"<td>{entry['template']}</td>"
                html += f"<td>{entry['position']}</td>"
                html += f"<td>{entry['confidence']}</td>"
                html += f"<td>{screenshot_link}</td>"
                html += f"<td>{entry.get('extra')}</td>"
                html += "</tr>"

    html += "</table></body></html>"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[REPORT] HTML Report erstellt: {html_file}")
    return html_file
