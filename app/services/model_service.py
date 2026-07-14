from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (5, 5)
ROI_SIZE = (276, 276)
NOISE_REDUCTION_KERNEL_SIZE = 1
THRESHOLD_VALUE = 80


class PalmModelService:
    def __init__(self, model_path: Path):
        if not model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        self.model_path = model_path

        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        self.target_size = self._get_model_input_size()

    def _get_model_input_size(self) -> tuple[int, int]:
        input_shape = self.session.get_inputs()[0].shape

        try:
            h = int(input_shape[2])
            w = int(input_shape[3])
        except Exception:
            h = 224
            w = 224

        return w, h

    @staticmethod
    def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
        embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)
        norm = np.linalg.norm(embedding)

        if norm == 0:
            return embedding

        return embedding / norm

    def preprocess(self, image_bgr: np.ndarray, debug_dir: Path | None = None, debug_name: str = "debug") -> np.ndarray:
        if image_bgr is None:
            raise ValueError("Input image is None")

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT,
            tileGridSize=CLAHE_TILE_GRID_SIZE,
        )
        enhanced = clahe.apply(gray)

        denoised = cv2.medianBlur(
            enhanced,
            NOISE_REDUCTION_KERNEL_SIZE,
        )

        _, binary = cv2.threshold(
            denoised,
            THRESHOLD_VALUE,
            255,
            cv2.THRESH_BINARY,
        )

        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            raise ValueError(
                "Palm segmentation failed. Use dark background and keep palm large."
            )

        largest_contour = max(contours, key=cv2.contourArea)
        moment = cv2.moments(largest_contour)

        if moment["m00"] == 0:
            raise ValueError("Palm segmentation failed: contour moment is zero.")

        cx = int(moment["m10"] / moment["m00"])
        cy = int(moment["m01"] / moment["m00"])

        roi_width, roi_height = ROI_SIZE

        x1 = max(0, cx - roi_width // 2)
        y1 = max(0, cy - roi_height // 2)
        x2 = min(denoised.shape[1], x1 + roi_width)
        y2 = min(denoised.shape[0], y1 + roi_height)

        roi = denoised[y1:y2, x1:x2]

        if roi.size == 0:
            raise ValueError("ROI extraction failed")

        resized = cv2.resize(
            roi,
            self.target_size,
            interpolation=cv2.INTER_AREA,
        )

        normalized = resized.astype(np.float32) / 255.0

        x = normalized[None, None, :, :]
        x = np.repeat(x, 3, axis=1).astype(np.float32)

        if debug_dir is not None:
            debug_dir.mkdir(parents=True, exist_ok=True)

            contour_view = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
            cv2.drawContours(contour_view, [largest_contour], -1, (0, 255, 0), 2)
            cv2.circle(contour_view, (cx, cy), 5, (0, 0, 255), -1)
            cv2.rectangle(contour_view, (x1, y1), (x2, y2), (255, 0, 0), 2)

            cv2.imwrite(str(debug_dir / f"{debug_name}_gray.jpg"), gray)
            cv2.imwrite(str(debug_dir / f"{debug_name}_binary.jpg"), binary)
            cv2.imwrite(str(debug_dir / f"{debug_name}_contour.jpg"), contour_view)
            cv2.imwrite(str(debug_dir / f"{debug_name}_roi.jpg"), roi)
            cv2.imwrite(str(debug_dir / f"{debug_name}_resized.jpg"), resized)

        return x

    def get_embedding_from_frame(
        self,
        image_bgr: np.ndarray,
        debug_dir: Path | None = None,
        debug_name: str = "debug",
    ) -> np.ndarray:
        x = self.preprocess(
            image_bgr,
            debug_dir=debug_dir,
            debug_name=debug_name,
        )

        y = self.session.run(
            [self.output_name],
            {self.input_name: x},
        )[0]

        embedding = y.reshape(y.shape[0], -1)[0].astype(np.float32)
        return self.normalize_embedding(embedding)

    def make_template(self, embeddings: list[np.ndarray]) -> np.ndarray:
        normalized = [self.normalize_embedding(e) for e in embeddings]
        mean_embedding = np.mean(np.stack(normalized, axis=0), axis=0)
        return self.normalize_embedding(mean_embedding.astype(np.float32))

    @staticmethod
    def to_list(embedding: np.ndarray) -> list[float]:
        return [float(x) for x in embedding.tolist()]