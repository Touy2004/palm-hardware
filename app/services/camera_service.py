import gc
import time
from typing import Callable

import cv2
import numpy as np
from libcamera import controls
from picamera2 import Picamera2

from app.utils.image_utils import draw_center_axis, sharpness_score, add_text


PreviewCallback = Callable[[np.ndarray], None]
StatusCallback = Callable[[str], None]


class CameraService:
    def __init__(self, width: int, height: int, camera_num: int = 0):
        self.width = width
        self.height = height
        self.camera_num = camera_num
        self.picam2 = None

    def open(self):
        # Make sure old camera object is fully released first
        self.close()
        time.sleep(0.5)

        camera_info = Picamera2.global_camera_info()

        if not camera_info:
            raise RuntimeError(
                "No camera detected. Run: rpicam-hello --list-cameras"
            )

        if self.camera_num >= len(camera_info):
            raise RuntimeError(
                f"Camera number {self.camera_num} not found. "
                f"Available cameras: 0 to {len(camera_info) - 1}"
            )

        self.picam2 = Picamera2(camera_num=self.camera_num)

        config = self.picam2.create_preview_configuration(
            main={
                "size": (self.width, self.height),
                "format": "RGB888",
            }
        )

        self.picam2.configure(config)

        try:
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Continuous,
                "AfRange": controls.AfRangeEnum.Macro,
            })
        except Exception as exc:
            print("Warning: autofocus control failed:", exc)

        self.picam2.start()
        time.sleep(1.0)

    def close(self):
        if self.picam2 is not None:
            try:
                self.picam2.stop()
            except Exception:
                pass

            try:
                self.picam2.close()
            except Exception:
                pass

            self.picam2 = None

            # Give libcamera time to release the device
            gc.collect()
            time.sleep(0.5)

    def capture_frame(self) -> np.ndarray:
        if self.picam2 is None:
            raise RuntimeError("Camera is not opened")

        rgb_frame = self.picam2.capture_array()
        bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

        if bgr_frame.shape[1] != self.width or bgr_frame.shape[0] != self.height:
            bgr_frame = cv2.resize(
                bgr_frame,
                (self.width, self.height),
                interpolation=cv2.INTER_AREA,
            )

        return bgr_frame

    def make_preview(self, frame: np.ndarray, lines: list[str], instruction: str = "") -> np.ndarray:
        preview = frame.copy()
        draw_center_axis(preview)
        
        if instruction:
            from app.utils.image_utils import draw_hand_guide
            draw_hand_guide(preview, instruction)
            
        add_text(preview, lines)
        return preview

    def countdown_capture(
        self,
        delay_seconds: int,
        title: str,
        instruction: str,
        on_status: StatusCallback | None = None,
        on_preview: PreviewCallback | None = None,
    ) -> np.ndarray:
        start_time = time.time()
        last_frame = None

        last_remaining = -1

        while True:
            elapsed = time.time() - start_time
            remaining = max(0, delay_seconds - int(elapsed))

            if on_status and remaining != last_remaining:
                on_status(f"{instruction}\nWaiting {remaining}s for autofocus...")
                last_remaining = remaining

            frame = self.capture_frame()
            last_frame = frame.copy()

            score = sharpness_score(frame)

            preview = self.make_preview(
                frame,
                [
                    title,
                    instruction,
                    f"Focus: {remaining}s | Sharp: {score:.1f}",
                    "Keep palm steady",
                ],
                instruction=instruction
            )

            if on_preview:
                on_preview(preview)

            if elapsed >= delay_seconds:
                break

            time.sleep(0.05)

        return last_frame

    def __del__(self):
        self.close()