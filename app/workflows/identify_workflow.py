from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from app.config.settings import AppSettings
from app.services.api_client import ApiClient
from app.services.camera_service import CameraService
from app.services.model_service import PalmModelService


StatusCallback = Callable[[str], None]
PreviewCallback = Callable[[np.ndarray], None]


class IdentifyWorkflow:
    def __init__(
        self,
        settings: AppSettings,
        camera_service: CameraService,
        on_status: StatusCallback,
        on_preview: PreviewCallback,
    ):
        self.settings = settings
        self.camera_service = camera_service
        self.on_status = on_status
        self.on_preview = on_preview

        self.api = ApiClient(
            api_base_url=settings.api_base_url,
            device_code=settings.device_code,
        )

        self.model = PalmModelService(settings.model_path)

    def _capture_embedding(self) -> list[float]:
        self.settings.attendance_dir.mkdir(parents=True, exist_ok=True)

        frame = self.camera_service.countdown_capture(
            delay_seconds=self.settings.focus_delay,
            title="Identify Palm",
            instruction="Place palm at center",
            on_status=self.on_status,
            on_preview=self.on_preview,
        )

        image_path = self.settings.attendance_dir / "identify_palm.jpg"
        cv2.imwrite(str(image_path), frame)

        self.on_status("Processing palm model...")

        embedding = self.model.get_embedding_from_frame(
            image_bgr=frame,
            debug_dir=self.settings.attendance_dir / "debug",
            debug_name="identify",
        )

        return self.model.to_list(embedding)

    def run(self):
        self.on_status("Capturing palm to identify...")

        embedding = self._capture_embedding()

        self.on_status("Sending identify request...")

        response = self.api.identify_palm(
            model_version=self.settings.model_version,
            embedding=embedding,
            liveness_passed=self.settings.mock_liveness_passed,
            quality_score=self.settings.mock_quality_score,
        )

        data = response.get("data") or {}
        user = data.get("user") or {}

        full_name = user.get("full_name", "Unknown user")
        
        action = "Identify"

        self.on_status(f"IDENTIFIED successfully\n{full_name}")

        return {
            "full_name": full_name,
            "action": action
        }