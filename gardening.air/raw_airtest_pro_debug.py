# -*- encoding: utf-8 -*-
"""
Live Debug Preview für raw_airtest_pro
- Zeigt aktuelle Screenshots
- Markiert erkannte Templates
- Echtzeit-Debug-Fenster
"""

import cv2
import numpy as np
from raw_airtest_pro import raw_screenshot, find_template

DEBUG_WINDOW_NAME = "Airtest Live Debug"
cv2.namedWindow(DEBUG_WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(DEBUG_WINDOW_NAME, 480, 800)  # optional, anpassen

def show_live_debug(tpl_list=None, viewport=None):
    """
    tpl_list: Liste von Template Objekten, die auf Screenshot gesucht werden sollen
    viewport: falls Screenshot gecroppt werden soll
    """
    # Screenshot holen
    img_path, _ = raw_screenshot("live_debug.png", crop=True, viewport=viewport)
    img = cv2.imread(img_path)
    display_img = img.copy()

    # Templates markieren
    if tpl_list:
        for tpl in tpl_list:
            match = find_template(tpl, img_path)
            if match:
                x, y = match["result"]
                w, h = tpl.width, tpl.height
                cv2.rectangle(display_img, (x-w//2, y-h//2), (x+w//2, y+h//2), (0, 255, 0), 2)
                cv2.putText(display_img, tpl.filename, (x-w//2, y-h//2-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imshow(DEBUG_WINDOW_NAME, display_img)
    cv2.waitKey(1)  # 1 ms warten für Update

def close_debug_window():
    cv2.destroyWindow(DEBUG_WINDOW_NAME)
