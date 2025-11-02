# -*- encoding: utf-8 -*-
# gardening.py

import sys
import os
import time
import threading
from airtest.core.cv import Template

# Füge das Verzeichnis des Skripts zum Python-Pfad hinzu
sys.path.append(os.path.dirname(__file__))

# Airtest Funktionen importieren
from raw_airtest_pro import *
from raw_airtest_pro_logging import *
from raw_airtest_pro_debug import show_live_debug, close_debug_window

# Emulator-Loader
from emulator_loader import get_active_emulators

print("Working dir:", os.getcwd())
print("This file dir:", os.path.dirname(__file__))

# ------------------ Templates ------------------
TEMPLATE_DIR = os.path.dirname(__file__)

FREE_PLACE        = Template(os.path.join(TEMPLATE_DIR, "Empty.png"), threshold=0.70, rgb=True)
POT               = Template(os.path.join(TEMPLATE_DIR, "1738661496825.png"), threshold=0.70, rgb=True)
WHITE_SEED        = Template(os.path.join(TEMPLATE_DIR, "1739141267692.png"), threshold=0.71, rgb=True)
RED_SEED          = Template(os.path.join(TEMPLATE_DIR, "1745241060170.png"), threshold=0.71, rgb=True)
EMPTY_WHITE_SEED  = Template(os.path.join(TEMPLATE_DIR, "1738862123798.png"), threshold=0.76, rgb=True)
EMPTY_RED_SEED    = Template(os.path.join(TEMPLATE_DIR, "1745241205672.png"), threshold=0.76, rgb=True)
PLUS_SIGN         = Template(os.path.join(TEMPLATE_DIR, "1738862234366.png"), threshold=0.70, rgb=True)
GREEN_BUTTON      = Template(os.path.join(TEMPLATE_DIR, "1738862265193.png"), threshold=0.79, rgb=True)
WATER_BTN         = Template(os.path.join(TEMPLATE_DIR, "GiesKanne.png"), threshold=0.50, rgb=True)
DO_CUT            = Template(os.path.join(TEMPLATE_DIR, "1738602489796.png"), threshold=0.70, rgb=True)
DO_PIK            = Template(os.path.join(TEMPLATE_DIR, "PickUp.png"), threshold=0.50, rgb=True, target_pos=1)

# ------------------ Helper-Funktionen ------------------
def plant_one(device_addr):
    if not q_exists_raw(device_addr, FREE_PLACE):
        print(f"[{device_addr}] Kein freier Platz gefunden.")
        return False
    if drag_seed(device_addr, [WHITE_SEED, RED_SEED], FREE_PLACE):
        print(f"[{device_addr}] Seed gepflanzt.")
        return True
    if refill(device_addr, EMPTY_WHITE_SEED, PLUS_SIGN, GREEN_BUTTON) or refill(device_addr, EMPTY_RED_SEED, PLUS_SIGN, GREEN_BUTTON):
        if drag_seed(device_addr, [WHITE_SEED, RED_SEED], FREE_PLACE):
            print(f"[{device_addr}] Seed nachgefüllt & gepflanzt.")
            return True
    print(f"[{device_addr}] Keine Seeds verfügbar.")
    return False

def water_cut_pick(device_addr):
    btn = q_exists_raw(device_addr, WATER_BTN, timeout=1)
    if btn:
        print(f"[{device_addr}] Bewässerung gestartet.")
        tap_logged(btn, device_addr)  # btn = Position, device_addr = Name
        time.sleep(2)
    hits_cut = all_click_raw(device_addr, DO_CUT)
    hits_pik = all_click_raw(device_addr, DO_PIK)
    print(f"[{device_addr}] {hits_cut} Schneiden- und {hits_pik} Aufsammel-Icons geklickt.")

# ------------------ Hauptloop pro Emulator ------------------
MAX_FAILS = 5

def gardening_loop(device_addr):
    # Log-Verzeichnis pro Emulator
    emulator_log_dir = os.path.join(ABS_LOG_DIR, device_addr.replace(":", "_"))
    os.makedirs(emulator_log_dir, exist_ok=True)

    print(f"\n==============================")
    print(f"🌿 Starte Gardening auf Emulator: {device_addr}")
    print(f"==============================")

    fail_count = 0
    while True:
        planted = 0
        for _ in range(9):
            try:
                if plant_one(device_addr):
                    tpls_to_check = [FREE_PLACE, WHITE_SEED, RED_SEED, WATER_BTN, DO_CUT, DO_PIK]
                    show_live_debug(tpl_list=tpls_to_check)
                    planted += 1
                    fail_count = 0
                else:
                    fail_count += 1
            except Exception as e:
                print(f"[{device_addr}] Fehler beim Pflanzen: {e}")
                fail_count += 1

            time.sleep(0.5)
            if fail_count >= MAX_FAILS:
                print(f"[{device_addr}] {fail_count} Fehlversuche hintereinander – warte 60s.")
                fail_count = 0
                time.sleep(60)
                break

        print(f"[{device_addr}] {planted} Pflanzen gesetzt.")
        try:
            water_cut_pick(device_addr)
            tpls_to_check = [FREE_PLACE, WHITE_SEED, RED_SEED, WATER_BTN, DO_CUT, DO_PIK]
            show_live_debug(tpl_list=tpls_to_check)
        except Exception as e:
            print(f"[{device_addr}] Fehler bei Bewässerung/Ernte: {e}")

        print(f"[{device_addr}] Pause 100 s …")
        time.sleep(100)

        try:
            generate_html_report()  # globaler Report, optional pro Emulator in eigenem Ordner
            close_debug_window()
        except Exception as e:
            print(f"[{device_addr}] Fehler beim Report/DebugWindow: {e}")

# ------------------ Main ------------------
if __name__ == "__main__":
    DEVICE_ADDRS = get_active_emulators()
    if not DEVICE_ADDRS:
        print("⚠️  Keine aktiven Emulatoren gefunden (Flag=x).")
        sys.exit(1)

    threads = []
    for addr in DEVICE_ADDRS:
        t = threading.Thread(target=gardening_loop, args=(addr,), daemon=True)
        t.start()
        threads.append(t)

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Gardening beendet durch Benutzer.")

