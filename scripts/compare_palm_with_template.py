#!/usr/bin/env python3

import argparse
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (5, 5)
ROI_SIZE = (276, 276)
NOISE_REDUCTION_KERNEL_SIZE = 1
THRESHOLD_VALUE = 80


def load_onnx_session(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )

    input_info = session.get_inputs()[0]
    output_info = session.get_outputs()[0]

    print("Model:", model_path)
    print("Input name:", input_info.name)
    print("Input shape:", input_info.shape)
    print("Output name:", output_info.name)
    print("Output shape:", output_info.shape)

    return session


def get_model_input_size(session):
    input_shape = session.get_inputs()[0].shape

    try:
        h = int(input_shape[2])
        w = int(input_shape[3])
    except Exception:
        h = 224
        w = 224

    return w, h


def normalize_embedding(emb: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(emb)

    if norm == 0:
        return emb

    return emb / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = normalize_embedding(a)
    b = normalize_embedding(b)

    return float(np.dot(a, b))


def preprocess_lucy_resnet18(
    image_bgr: np.ndarray,
    target_size: tuple[int, int],
    debug_dir: Path | None = None,
    debug_name: str = "debug",
):
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
            "Palm segmentation failed: no contour found. "
            "Use dark background, good lighting, and keep palm large in frame."
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
        raise ValueError("ROI extraction failed: empty ROI.")

    resized = cv2.resize(
        roi,
        target_size,
        interpolation=cv2.INTER_AREA,
    )

    normalized = resized.astype(np.float32) / 255.0

    # [H, W] -> [1, 1, H, W]
    x = normalized[None, None, :, :]

    # grayscale to 3 channels: [1, 3, H, W]
    x = np.repeat(x, 3, axis=1).astype(np.float32)

    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)

        contour_view = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
        cv2.drawContours(contour_view, [largest_contour], -1, (0, 255, 0), 2)
        cv2.circle(contour_view, (cx, cy), 5, (0, 0, 255), -1)
        cv2.rectangle(contour_view, (x1, y1), (x2, y2), (255, 0, 0), 2)

        cv2.imwrite(str(debug_dir / f"{debug_name}_gray.jpg"), gray)
        cv2.imwrite(str(debug_dir / f"{debug_name}_clahe.jpg"), enhanced)
        cv2.imwrite(str(debug_dir / f"{debug_name}_binary.jpg"), binary)
        cv2.imwrite(str(debug_dir / f"{debug_name}_contour.jpg"), contour_view)
        cv2.imwrite(str(debug_dir / f"{debug_name}_roi.jpg"), roi)
        cv2.imwrite(str(debug_dir / f"{debug_name}_resized.jpg"), resized)

    return x


def get_embedding(
    session,
    image_path: Path,
    target_size: tuple[int, int],
    debug_dir: Path | None = None,
):
    image_bgr = cv2.imread(str(image_path))

    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    print("Image:", image_path)
    print("Image size:", image_bgr.shape[1], "x", image_bgr.shape[0])

    x = preprocess_lucy_resnet18(
        image_bgr=image_bgr,
        target_size=target_size,
        debug_dir=debug_dir,
        debug_name="compare_image",
    )

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    y = session.run(
        [output_name],
        {input_name: x},
    )[0]

    embedding = y.reshape(y.shape[0], -1)[0].astype(np.float32)

    return normalize_embedding(embedding)


def main():
    parser = argparse.ArgumentParser(
        description="Compare one palm image with saved enrollment_template.npy"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="models/palmprint_encoder.onnx",
        help="Path to ONNX model",
    )

    parser.add_argument(
        "--template",
        type=str,
        default="samples/enrollment_template.npy",
        help="Path to saved palm template .npy",
    )

    parser.add_argument(
        "--image",
        type=str,
        default="samples/test_palm.jpg",
        help="Palm image to compare",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Cosine similarity threshold",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save preprocessing debug images",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    template_path = Path(args.template)
    image_path = Path(args.image)

    if not template_path.exists():
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            "Create it first using evaluate_lucy_resnet18_model.py"
        )

    session = load_onnx_session(model_path)
    target_size = get_model_input_size(session)

    print("Model target input size:", target_size)

    debug_dir = image_path.parent / "compare_debug" if args.debug else None

    template = np.load(str(template_path)).astype(np.float32)
    template = normalize_embedding(template)

    compare_embedding = get_embedding(
        session=session,
        image_path=image_path,
        target_size=target_size,
        debug_dir=debug_dir,
    )

    score = cosine_similarity(template, compare_embedding)

    print("\n========== Compare Result ==========")
    print("Template:", template_path)
    print("Compare image:", image_path)
    print("Template shape:", template.shape)
    print("Compare embedding shape:", compare_embedding.shape)
    print("Template norm:", np.linalg.norm(template))
    print("Compare embedding norm:", np.linalg.norm(compare_embedding))
    print("Similarity score:", score)
    print("Threshold:", args.threshold)

    if score >= args.threshold:
        print("Decision: SAME / ACCEPT")
    else:
        print("Decision: DIFFERENT / REJECT")

    if debug_dir is not None:
        print("Debug images saved in:", debug_dir)

    print("====================================")


if __name__ == "__main__":
    main()