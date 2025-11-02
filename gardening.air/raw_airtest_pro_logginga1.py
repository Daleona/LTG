import datetime
import json

# ------------------ Logging ------------------
LOG_FILE = os.path.join(ABS_LOG_DIR, "actions_log.json")
log_data = []

def log_action(action_type, template_name=None, position=None, confidence=None, extra=None):
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action_type,
        "template": template_name,
        "position": position,
        "confidence": confidence,
        "extra": extra
    }
    log_data.append(entry)
    # sofort in JSON schreiben
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    print(f"[LOG] {entry}")

# ------------------ Screenshot Logging ------------------
def save_screenshot_with_log(filename="raw.png", viewport=None):
    path, vp = raw_screenshot(filename, crop=True, viewport=viewport)
    log_action("screenshot", template_name=None, position=None, extra={"file": path, "viewport": vp})
    return path, vp

# ------------------ Template-Logging ------------------
def exists_raw_logged(tpl: Template, viewport=None, timeout=2):
    start = time.time()
    while time.time() - start < timeout:
        path, vp = save_screenshot_with_log("tmp_screen.png", viewport=viewport)
        match = find_template(tpl, path)
        if match:
            log_action("exists", template_name=tpl.filename, position=match["result"], confidence=match["confidence"])
            return match["result"]
        time.sleep(0.2)
    log_action("exists", template_name=tpl.filename, position=None, confidence=None)
    return None

def all_matches_raw_logged(tpl: Template, viewport=None):
    path, vp = save_screenshot_with_log("tmp_screen.png", viewport=viewport)
    screen = cv2.imread(path)
    tpl_img = cv2.imread(tpl.filename)
    res = cv2.matchTemplate(screen, tpl_img, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= tpl.threshold)
    h, w = tpl_img.shape[:2]
    matches = [(int(x + w/2), int(y + h/2)) for (x, y) in zip(loc[1], loc[0])]
    log_action("all_matches", template_name=tpl.filename, extra={"matches": matches})
    return matches

# ------------------ Aktionen mit Logging ------------------
def tap_logged(pos):
    tap(pos)
    log_action("tap", position=pos)

def swipe_logged(start, end, duration=0.5):
    swipe(start, end, duration)
    log_action("swipe", extra={"start": start, "end": end, "duration": duration})

def drag_seed_logged(seed_tpls, free_place_tpl, viewport=None):
    slot = exists_raw_logged(free_place_tpl, viewport=viewport)
    if not slot:
        return False
    for seed_tpl in seed_tpls:
        seed = exists_raw_logged(seed_tpl, viewport=viewport)
        if seed:
            swipe_logged(seed, slot, duration=0.5)
            log_action("drag_seed", template_name=seed_tpl.filename, extra={"to_slot": free_place_tpl.filename})
            return True
    return False

def refill_logged(slot_tpl, plus_tpl, green_btn_tpl, viewport=None):
    slot = exists_raw_logged(slot_tpl, viewport=viewport)
    if not slot:
        return False
    tap_logged(slot)
    for _ in range(10):
        plus = exists_raw_logged(plus_tpl, timeout=0.5, viewport=viewport)
        if not plus:
            break
        tap_logged(plus)
    btn = exists_raw_logged(green_btn_tpl, viewport=viewport)
    if btn:
        tap_logged(btn)
        time.sleep(1)
        return True
    return False

# ------------------ Screenshot Logging mit Zeitstempel ------------------
def save_screenshot_with_timestamp(prefix="screenshot", viewport=None):
    """
    Macht einen unskalierten Screenshot und speichert ihn mit Zeitstempel.
    Gibt den Pfad und Viewport zurück.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp}.png"
    path, vp = raw_screenshot(filename, crop=True, viewport=viewport)
    log_action("screenshot", extra={"file": path, "viewport": vp})
    return path, vp

# ------------------ HTML-Report ------------------
def generate_html_report():
    html_file = os.path.join(ABS_LOG_DIR, "actions_report.html")
    html = "<html><head><meta charset='utf-8'><title>Airtest Report</title></head><body>"
    html += f"<h2>Airtest Actions Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Time</th><th>Action</th><th>Template</th><th>Position</th><th>Confidence</th><th>Extra</th></tr>"
    for entry in log_data:
        html += "<tr>"
        html += f"<td>{entry['timestamp']}</td>"
        html += f"<td>{entry['action']}</td>"
        html += f"<td>{entry['template']}</td>"
        html += f"<td>{entry['position']}</td>"
        html += f"<td>{entry['confidence']}</td>"
        html += f"<td>{entry['extra']}</td>"
        html += "</tr>"
    html += "</table></body></html>"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[REPORT] HTML Report erstellt: {html_file}")
    return html_file
