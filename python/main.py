# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

import base64

from arduino.app_utils import App, Bridge, Logger
from arduino.app_utils.image import draw_bounding_boxes, get_image_bytes
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from datetime import datetime, UTC

logger = Logger("ITS_LOGO_DETECTION")
_logged_frame_dims = False

ui = WebUI()
# camera_preview=True makes the callback receive the exact frame the detections were
# computed on, so bounding boxes drawn on it line up correctly (the brick's built-in
# /embed preview draws boxes on a different, misaligned frame).
detection_stream = VideoObjectDetection(confidence=0.15, debounce_sec=0.3, camera_preview=True)

ui.on_message("override_th", lambda sid, threshold: detection_stream.override_threshold(threshold))

# Register a callback for when all objects are detected
def send_detections_to_ui(detections: dict, frame: bytes):
  global _logged_frame_dims
  if frame is not None:
    if not _logged_frame_dims:
      logger.info(f"DEBUG raw frame type={type(frame)} shape/len={getattr(frame, 'shape', len(frame))}")
      _logged_frame_dims = True
    annotated_frame = draw_bounding_boxes(frame, detections)
    if _logged_frame_dims is True:
      logger.info(f"DEBUG annotated frame type={type(annotated_frame)} size={getattr(annotated_frame, 'size', getattr(annotated_frame, 'shape', None))}")
      _logged_frame_dims = "done"
    jpeg_bytes = get_image_bytes(annotated_frame)
    ui.send_message("frame", message=base64.b64encode(jpeg_bytes).decode("ascii"))

  if detections:
    Bridge.call("showDetection")   # <-- notifica la matrice LED

  for key, values in detections.items():
    for value in values:
      entry = {
        "content": key,
        "confidence": value.get("confidence"),
        "timestamp": datetime.now(UTC).isoformat()
      }
      ui.send_message("detection", message=entry)


detection_stream.on_detect_all(send_detections_to_ui)


App.run()
