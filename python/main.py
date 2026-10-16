# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

import glob
import logging
import threading
import time
from collections import deque

from arduino.app_utils import App, Bridge, Logger
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from datetime import datetime, UTC

logger = Logger("ITS_LOGO_DETECTION")
_logged_sample = False


class ErrorToMatrixHandler(logging.Handler):
  """Blinks ERR on the LED matrix for any ERROR+ log raised in this app's own process."""

  def __init__(self):
    super().__init__(level=logging.ERROR)

  def emit(self, record):
    try:
      Bridge.call("showError")
    except Exception:
      pass


logging.getLogger().addHandler(ErrorToMatrixHandler())


def _camera_watchdog():
  # The camera read failures logged by the video_objectdetection brick happen in a
  # separate runner process/container, invisible to this app's own Python logger, so
  # we poll device presence directly instead: no USB camera symlink means no camera.
  camera_missing = False
  while True:
    now_missing = not glob.glob("/dev/v4l/by-id/*")
    if now_missing != camera_missing:
      camera_missing = now_missing
      logger.info(f"DEBUG camera_watchdog: camera_missing={camera_missing}")
    if camera_missing:
      try:
        Bridge.call("showError")
      except Exception:
        pass
    time.sleep(1)


threading.Thread(target=_camera_watchdog, daemon=True).start()

# ---------------------------------------------------------------------------
# PARAMETRI DI FILTRO (da tarare sul banco)
# ---------------------------------------------------------------------------
BRICK_CONFIDENCE = 0.5   # soglia passata al brick (prima era 0.15: troppo bassa)
CONF_MIN = 0.6           # soglia applicata da noi dopo il brick
MIN_W_PX = 0             # FOMO: box a dimensione fissa (1 cella = 16 px su 640x480),
MIN_H_PX = 0             # quindi il filtro sulla dimensione è disattivato
HISTORY_N = 5            # finestra temporale: ultimi N callback
CONFIRM_K = 3            # l'oggetto è valido se visto in almeno K degli ultimi N
# ---------------------------------------------------------------------------

_history = {}            # label -> deque di bool (rilevato / non rilevato)

ui = WebUI()
# Live video comes from the brick's own continuous /embed MJPEG stream (see index.html),
# not from frames pushed here - on_detect_all only fires when something is detected, so
# pushing frames from this callback left the video frozen whenever nothing was detected.
detection_stream = VideoObjectDetection(confidence=BRICK_CONFIDENCE, debounce_sec=0.3)

ui.on_message("override_th", lambda sid, threshold: detection_stream.override_threshold(threshold))


def box_size(value: dict):
  """Restituisce (larghezza, altezza) della box in pixel, o None se assente.
  Gestisce sia il formato xyxy sia x/y/width/height."""
  b = value.get("bounding_box_xyxy") or value.get("bounding_box") or value.get("bbox")
  if b is None:
    return None
  if isinstance(b, dict):
    if "width" in b and "height" in b:
      return b["width"], b["height"]
    if "x2" in b:
      return b["x2"] - b["x1"], b["y2"] - b["y1"]
    return None
  x1, y1, x2, y2 = b[:4]   # formato (x1, y1, x2, y2)
  return x2 - x1, y2 - y1


def filter_detections(detections: dict) -> dict:
  """1) soglia di confidenza  2) dimensione minima  3) conferma su più frame."""
  global _logged_sample
  current = {}

  for label, values in (detections or {}).items():
    if not _logged_sample and values:
      logger.info(f"DEBUG formato rilevamento: {values[0]}")   # verifica i nomi dei campi
      _logged_sample = True

    kept = []
    for v in values:
      if (v.get("confidence") or 0) < CONF_MIN:
        continue
      size = box_size(v)
      if size is not None:
        w, h = size
        if w < MIN_W_PX or h < MIN_H_PX:
          continue
      kept.append(v)
    if kept:
      current[label] = kept

  # Filtro temporale: aggiorna la storia di tutte le etichette note
  for label in set(_history) | set(current):
    hist = _history.setdefault(label, deque(maxlen=HISTORY_N))
    hist.append(label in current)

  return {label: vals for label, vals in current.items()
          if sum(_history[label]) >= CONFIRM_K}


# Register a callback for when all objects are detected
def send_detections_to_ui(detections: dict):
  confirmed = filter_detections(detections)

  if confirmed:
    Bridge.call("showDetection")   # <-- notifica la matrice LED (solo rilevamenti confermati)

  for key, values in confirmed.items():
    for value in values:
      entry = {
        "content": key,
        "confidence": value.get("confidence"),
        "timestamp": datetime.now(UTC).isoformat()
      }
      ui.send_message("detection", message=entry)


detection_stream.on_detect_all(send_detections_to_ui)


App.run()