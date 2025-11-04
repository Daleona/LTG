# -*- encoding: utf-8 -*-
# gardening.py (Airtest 1.3.6, Multi-Emulator, Threading-fähig)

import sys
import os
import time
import threading

sys.path.append(os.path.dirname(__file__))

from raw_airtest_pro import ABS_LOG_DIR
from raw_airtest_pro_logging import (
    tap_logged, swipe_logged, drag_seed_logged, refill_logged, exists_raw_logged, generate_html_report
)
from raw_airtest_pro_debug import show_live_debug, close_debug_window
from emulator_loader import get_active_emulators
from airtest.core.api import connect_device
from airtest.core.cv import Template

# ------------------ Templates ------------------
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "img")
#TEMPLATE_DIR = os.path.dirname(__file__)

FREE_PLACE        = Template(os.path.join(TEMPLATE_DIR, "Empty.png"), threshold=0.65, rgb=True)
EMPTY_POT         = Template(os.path.join(TEMPLATE_DIR, "Pot.png"), threshold=0.70, rgb=True)
WHITE_SEED        = Template(os.path.join(TEMPLATE_DIR, "WhiteSeed.png"), threshold=0.71, rgb=True)
RED_SEED          = Template(os.path.join(TEMPLATE_DIR, "RedSeed.png"), threshold=0.71, rgb=True)
EMPTY_WHITE_SEED  = Template(os.path.join(TEMPLATE_DIR, "1738862123798.png"), threshold=0.70, rgb=True)
EMPTY_RED_SEED    = Template(os.path.join(TEMPLATE_DIR, "1745241205672.png"), threshold=0.70, rgb=True)
PLUS_SIGN         = Template(os.path.join(TEMPLATE_DIR, "PlusSign.png"), threshold=0.70, rgb=True)
GREEN_BUTTON      = Template(os.path.join(TEMPLATE_DIR, "GreenButton.png"), threshold=0.69, rgb=True)
WATER_BTN         = Template(os.path.join(TEMPLATE_DIR, "GiesKanne.png"), threshold=0.70, rgb=True)
DO_CUT            = Template(os.path.join(TEMPLATE_DIR, "1738602489796.png"), threshold=0.70, rgb=True)
DO_PIK            = Template(os.path.join(TEMPLATE_DIR, "PickUp.png"), threshold=0.70, rgb=True, target_pos=1)

MAX_FAILS = 3

# ------------------ Helper-Funktionen ------------------
def plant_one(device_addr):
    """
    Pflanzt einen Seed auf einem freien Platz:
    - Klick auf FREE_PLACE
    - Warte 2 Sekunden, bis Seeds sichtbar sind
    - Drag von Seed zu EMPTY_POT (1 Sekunde)
    - Drag zurück zu FREE_PLACE (1 Sekunde)
    """
    free_pos = exists_raw_logged(FREE_PLACE, device_addr=device_addr)
    if not free_pos:
        print(f"[{device_addr}] Kein freier Platz gefunden.")
        return False

    for seed_tpl in [WHITE_SEED, RED_SEED]:
        seed_pos = exists_raw_logged(seed_tpl, device_addr=device_addr)
        if not seed_pos:
            # Nachfüllen, falls Seed fehlt
            refill_tpl = EMPTY_WHITE_SEED if seed_tpl == WHITE_SEED else EMPTY_RED_SEED
            if refill_logged(refill_tpl, PLUS_SIGN, GREEN_BUTTON, device_addr=device_addr):
                seed_pos = exists_raw_logged(seed_tpl, device_addr=device_addr)
            if not seed_pos:
                continue  # nächster Seed

        # 1️⃣ Klick auf FREE_PLACE
        tap_logged(free_pos, device_addr=device_addr)
        time.sleep(2)  # Warte, bis Seeds sichtbar werden

        # 2️⃣ Drag Seed -> EMPTY_POT
        pot_pos = exists_raw_logged(EMPTY_POT, device_addr=device_addr)
        if pot_pos:
            swipe_logged(seed_pos, pot_pos, duration=1, device_addr=device_addr)
            time.sleep(1)

            # 3️⃣ Drag zurück zu FREE_PLACE
            swipe_logged(pot_pos, free_pos, duration=1, device_addr=device_addr)
            time.sleep(0.5)
            print(f"[{device_addr}] Seed {seed_tpl.filename} gepflanzt.")
            return True

    print(f"[{device_addr}] Keine Seeds verfügbar.")
    return False

def water_cut_pick(device_addr):
    btn = exists_raw_logged(WATER_BTN, timeout=1, device_addr=device_addr)
    if btn:
        print(f"[{device_addr}] Bewässerung gestartet.")
        tap_logged(btn, device_addr=device_addr)
        time.sleep(2)

    # Schneiden & Aufsammeln
    cut_hits = drag_seed_logged([DO_CUT], FREE_PLACE, device_addr=device_addr)
    pik_hits = drag_seed_logged([DO_PIK], FREE_PLACE, device_addr=device_addr)
    print(f"[{device_addr}] {cut_hits} Schneiden- und {pik_hits} Aufsammel-Icons geklickt.")

# ------------------ Hauptloop pro Emulator ------------------
def gardening_loop(device_addr):
    # Device verbinden
    try:
        dev = connect_device(f"Android:///{device_addr}?cap_method=JAVACAP")
        print(f"[{device_addr}] Device verbunden")
    except Exception as e:
        print(f"[{device_addr}] Fehler beim Verbinden: {e}")
        return

    print(f"\n==============================")
    print(f"🌿 Starte Gardening auf Emulator: {device_addr}")
    print(f"==============================")

    fail_count = 0
    while True:
        planted = 0
        for _ in range(9):
            try:
                if plant_one(device_addr):
                    planted += 1
                    fail_count = 0
                else:
                    fail_count += 1
            except Exception as e:
                print(f"[{device_addr}] Fehler beim Pflanzen: {e}")
                fail_count += 1

            time.sleep(0.5)
            if fail_count >= MAX_FAILS:
                print(f"[{device_addr}] {fail_count} Fehlversuche – warte 60s.")
                fail_count = 0
                time.sleep(60)
                break

        print(f"[{device_addr}] {planted} Pflanzen gesetzt.")


        try:
            water_cut_pick(device_addr)
            show_live_debug(tpl_list=[FREE_PLACE, WHITE_SEED, RED_SEED, WATER_BTN, DO_CUT, DO_PIK])
        except Exception as e:
            print(f"[{device_addr}] Fehler bei Bewässerung/Ernte: {e}")

        print(f"[{device_addr}] Pause 100 s …")
        time.sleep(100)

        try:
            generate_html_report()
            close_debug_window()
        except Exception as e:
            print(f"[{device_addr}] Fehler beim Report/DebugWindow: {e}")

# ------------------ Main ------------------
if __name__ == "__main__":
    DEVICE_ADDRS = get_active_emulators()
    if not DEVICE_ADDRS:
        print("⚠️  Keine aktiven Emulatoren gefunden.")
        sys.exit(1)

    threads = []
    for addr in DEVICE_ADDRS:
        t = threading.Thread(target=gardening_loop, args=(addr,), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Gardening beendet durch Benutzer.")
