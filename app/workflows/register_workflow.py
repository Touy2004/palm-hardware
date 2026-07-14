import time
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from app.config.settings import AppSettings
from app.services.api_client import ApiClient
from app.services.camera_service import CameraService
from app.services.model_service import PalmModelService
from app.services.qr_service import generate_qr_image


StatusCallback = Callable[[str], None]
PreviewCallback = Callable[[np.ndarray], None]
ImageCallback = Callable[[Path], None]


CAPTURE_STEPS = [
    "1/8 normal center",
    "2/8 slightly higher",
    "3/8 slightly lower",
    "4/8 slightly left",
    "5/8 slightly right",
    "6/8 slightly closer",
    "7/8 slightly farther",
    "8/8 normal again",
]


class RegisterPalmWorkflow:
    def __init__(
        self,
        settings: AppSettings,
        camera_service: CameraService,
        on_status: StatusCallback,
        on_preview: PreviewCallback,
        on_qr: ImageCallback,
    ):
        self.settings = settings
        self.camera_service = camera_service
        self.on_status = on_status
        self.on_preview = on_preview
        self.on_qr = on_qr

        self.api = ApiClient(
            api_base_url=settings.api_base_url,
            device_code=settings.device_code,
        )

        self.model = PalmModelService(settings.model_path)

    def _wait_for_approval(
        self,
        session_id: str,
        original_session_token: str,
        timeout_seconds: int = 180,
        poll_interval: int = 2,
    ) -> str:
        start_time = time.time()
        last_status = None

        while True:
            elapsed = int(time.time() - start_time)

            if elapsed > timeout_seconds:
                raise TimeoutError("Pairing approval timeout")

            status_response = self.api.check_pairing_status(session_id)
            status = status_response["status"]

            if status != last_status:
                self.on_status(f"Pairing status: {status}")
                last_status = status

            if status == "approved":
                approved_token = (
                    status_response.get("session_token")
                    or status_response.get("approved_session_token")
                    or original_session_token
                )
                return approved_token

            if status in ["expired", "cancelled", "canceled", "rejected"]:
                raise RuntimeError(f"Pairing session ended: {status}")

            time.sleep(poll_interval)

    def _capture_8_embeddings(self) -> list[np.ndarray]:
        self.settings.register_dir.mkdir(parents=True, exist_ok=True)

        embeddings = []

        for index, instruction in enumerate(CAPTURE_STEPS, start=1):
            self.on_status(f"Prepare: {instruction}")

            frame = self.camera_service.countdown_capture(
                delay_seconds=self.settings.focus_delay,
                title="Register Palm",
                instruction=instruction,
                on_status=self.on_status,
                on_preview=self.on_preview,
            )

            image_path = self.settings.register_dir / f"enroll_{index}.jpg"
            cv2.imwrite(str(image_path), frame)

            self.on_status(f"Saved image {index}/8. Processing model...")

            embedding = self.model.get_embedding_from_frame(
                image_bgr=frame,
                debug_dir=self.settings.register_dir / "debug",
                debug_name=f"enroll_{index}",
            )

            embeddings.append(embedding)

        return embeddings

    def run(self):
        self.on_status("Checking device heartbeat...")
        self.api.heartbeat()

        self.on_status("Creating QR pairing session...")
        pairing = self.api.create_pairing_session()

        qr_payload = f"{self.settings.qr_prefix}{pairing['qr_code_data']}"
        qr_path = generate_qr_image(qr_payload, self.settings.qr_output_path)

        self.on_qr(qr_path)

        self.on_status("Scan QR with mobile app, then approve pairing.")

        approved_session_token = self._wait_for_approval(
            session_id=pairing["session_id"],
            original_session_token=pairing["session_token"],
        )

        self.on_status("Pairing approved. Capturing 8 palm images...")

        embeddings = self._capture_8_embeddings()
        template = self.model.make_template(embeddings)
        template_list = self.model.to_list(template)

        np.save(str(self.settings.register_dir / "enrollment_template.npy"), template)

        self.on_status("Uploading palm template to API...")

        response = self.api.enroll_palm(
            session_token=approved_session_token,
            model_version=self.settings.model_version,
            embedding=template_list,
            liveness_passed=self.settings.mock_liveness_passed,
            quality_score=self.settings.mock_quality_score,
        )

        template_id = ((response.get("data") or {}).get("template_id"))

        if template_id:
            self.on_status(f"Palm registered successfully.\nTemplate ID: {template_id}")
        else:
            self.on_status("Palm registered successfully.")