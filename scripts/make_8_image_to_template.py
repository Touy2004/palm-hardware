#!/usr/bin/env python3

import argparse
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


# Preprocessing values from Lucy ResNet-18 palm prototype
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

    # Expected example: [1, 3, 224, 224]
    try:
        h = int(input_shape[2])
        w = int(input_shape[3])
    except Exception:
        h = 224
        w = 224

    return w, h


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

    denoised = cv2.medianBlur(enhanced, NOISE_REDUCTION_KERNEL_SIZE)

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
            "Use dark background and good lighting."
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
    debug_name: str = "debug",
):
    image_bgr = cv2.imread(str(image_path))

    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    x = preprocess_lucy_resnet18(
        image_bgr=image_bgr,
        target_size=target_size,
        debug_dir=debug_dir,
        debug_name=debug_name,
    )

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    y = session.run(
        [output_name],
        {input_name: x},
    )[0]

    embedding = y.reshape(y.shape[0], -1)[0].astype(np.float32)

    return embedding


def normalize_embedding(emb: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(emb)

    if norm == 0:
        return emb

    return emb / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = normalize_embedding(a)
    b = normalize_embedding(b)

    return float(np.dot(a, b))


def make_template(embeddings: list[np.ndarray]) -> np.ndarray:
    normalized_embeddings = [normalize_embedding(e) for e in embeddings]
    mean_emb = np.mean(np.stack(normalized_embeddings, axis=0), axis=0)

    return normalize_embedding(mean_emb.astype(np.float32))


def load_enrollment_images(image_dir: Path):
    image_paths = []

    for i in range(1, 9):
        path = image_dir / f"enroll_{i}.jpg"

        if not path.exists():
            raise FileNotFoundError(f"Missing image: {path}")

        image_paths.append(path)

    return image_paths


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Lucy ResNet-18 ONNX palm model using 8 captured images"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="models/palmprint_encoder.onnx",
        help="Path to ONNX model",
    )

    parser.add_argument(
        "--image-dir",
        type=str,
        default="samples/enrollment_8",
        help="Directory containing enroll_1.jpg to enroll_8.jpg",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Cosine similarity threshold",
    )

    parser.add_argument(
        "--compare-image",
        type=str,
        default="",
        help="Optional image to compare against 8-image template",
    )

    parser.add_argument(
        "--save-template",
        type=str,
        default="samples/enrollment_template.npy",
        help="Path to save average template embedding",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save preprocessing debug images",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    image_dir = Path(args.image_dir)

    session = load_onnx_session(model_path)
    target_size = get_model_input_size(session)

    print("Model target input size:", target_size)

    image_paths = load_enrollment_images(image_dir)

    debug_dir = image_dir / "model_debug" if args.debug else None

    embeddings = []

    print("\nRunning model on 8 enrollment images...\n")

    for i, image_path in enumerate(image_paths, start=1):
        emb = get_embedding(
            session=session,
            image_path=image_path,
            target_size=target_size,
            debug_dir=debug_dir,
            debug_name=f"enroll_{i}",
        )

        embeddings.append(emb)

        print(f"Image {i}: {image_path}")
        print(f"  Embedding shape: {emb.shape}")
        print(f"  Embedding norm:  {np.linalg.norm(emb):.6f}")

    template = make_template(embeddings)

    save_template_path = Path(args.save_template)
    save_template_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(save_template_path), template)

    print("\n========== Enrollment Template Result ==========")
    print("Images:", len(image_paths))
    print("Template shape:", template.shape)
    print("Template norm:", np.linalg.norm(template))
    print("Template saved:", save_template_path)
    print()

    scores = []

    for i, emb in enumerate(embeddings, start=1):
        score = cosine_similarity(template, emb)
        scores.append(score)

        decision = "GOOD" if score >= args.threshold else "LOW"

        print(f"Image {i} vs template: {score:.6f}  {decision}")

    print()
    print(f"Average score: {np.mean(scores):.6f}")
    print(f"Min score:     {np.min(scores):.6f}")
    print(f"Max score:     {np.max(scores):.6f}")
    print(f"Threshold:     {args.threshold}")
    print("================================================")

    if args.compare_image:
        compare_path = Path(args.compare_image)

        print("\nRunning compare image test...")

        compare_emb = get_embedding(
            session=session,
            image_path=compare_path,
            target_size=target_size,
            debug_dir=debug_dir,
            debug_name="compare_image",
        )

        compare_score = cosine_similarity(template, compare_emb)

        print("\n========== Compare Result ==========")
        print("Compare image:", compare_path)
        print("Similarity score:", compare_score)
        print("Threshold:", args.threshold)

        if compare_score >= args.threshold:
            print("Decision: SAME / ACCEPT")
        else:
            print("Decision: DIFFERENT / REJECT")

        print("====================================")

    if debug_dir is not None:
        print("\nDebug images saved in:", debug_dir)


if __name__ == "__main__":
    main()