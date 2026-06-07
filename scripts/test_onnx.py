#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from dotenv import load_dotenv
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

MODEL_PATH = PROJECT_ROOT / os.getenv("MODEL_PATH", "models/palm_embedding_mobilenetv3.onnx")
PALM_THRESHOLD = float(os.getenv("PALM_THRESHOLD", "0.80"))

IMG_SIZE = 224


def center_crop_square(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    size = min(h, w)

    start_x = (w - size) // 2
    start_y = (h - size) // 2

    return img[start_y:start_y + size, start_x:start_x + size]


def preprocess(image_path: Path, use_center_crop: bool = False) -> np.ndarray:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    img = np.array(image)

    if use_center_crop:
        img = center_crop_square(img)

    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)

    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    l = clahe.apply(l)

    lab = cv2.merge((l, a, b))
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    img = img.astype(np.float32) / 255.0

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    img = (img - mean) / std

    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0).astype(np.float32)

    return img


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def load_session(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )

    return session


def get_embedding(session, image_path: Path, use_center_crop: bool = False) -> np.ndarray:
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    x = preprocess(image_path, use_center_crop=use_center_crop)

    embedding = session.run(
        [output_name],
        {input_name: x},
    )[0][0]

    return embedding.astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description="Test palm ONNX model on Raspberry Pi")

    parser.add_argument(
        "--image1",
        type=str,
        default=str(PROJECT_ROOT / "samples" / "palm1.jpg"),
        help="First palm image",
    )

    parser.add_argument(
        "--image2",
        type=str,
        default=str(PROJECT_ROOT / "samples" / "palm2.jpg"),
        help="Second palm image",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=str(MODEL_PATH),
        help="ONNX model path",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=PALM_THRESHOLD,
        help="Similarity threshold",
    )

    parser.add_argument(
        "--center-crop",
        action="store_true",
        help="Apply center square crop before resizing",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    image1 = Path(args.image1)
    image2 = Path(args.image2)

    print("Model:", model_path)
    print("Image 1:", image1)
    print("Image 2:", image2)
    print("Threshold:", args.threshold)
    print("Center crop:", args.center_crop)

    session = load_session(model_path)

    emb1 = get_embedding(session, image1, use_center_crop=args.center_crop)
    emb2 = get_embedding(session, image2, use_center_crop=args.center_crop)

    score = cosine_similarity(emb1, emb2)

    print("\n========== Result ==========")
    print("Embedding shape:", emb1.shape)
    print("Embedding norm 1:", np.linalg.norm(emb1))
    print("Embedding norm 2:", np.linalg.norm(emb2))
    print("Palm similarity score:", score)

    if score >= args.threshold:
        print("Decision: SAME / ACCEPT")
    else:
        print("Decision: DIFFERENT / REJECT")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Error:", exc)
        sys.exit(1)