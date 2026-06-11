#!/usr/bin/env python3

import argparse
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from picamera2 import Picamera2
from libcamera import controls


# Preprocessing for lucytrandev/palm-recognition-prototype
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (5, 5)
ROI_SIZE = (276, 276)
TARGET_SIZE = (138, 138)
NOISE_REDUCTION_KERNEL_SIZE = 1
THRESHOLD_VALUE = 80


def setup_camera(width: int, height: int):
    """
    Setup Raspberry Pi camera with continuous autofocus.
    Good for Arducam IMX519 autofocus module.
    """

    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={
            "size": (width, height),
            "format": "RGB888",
        }
    )

    picam2.configure(config)

    picam2.set_controls({
        "AfMode": controls.AfModeEnum.Continuous,
        "AfRange": controls.AfRangeEnum.Macro,
    })

    picam2.start()

    return picam2


def sharpness_score(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def preprocess_lucy_resnet18(
    image_bgr: np.ndarray,
    debug_dir: Path | None = None,
    debug_name: str = "debug",
):
    """
    Preprocess image like lucytrandev palm-recognition-prototype.

    Input:
        BGR image from OpenCV

    Output:
        Tensor shape: [1, 3, 138, 138]
    """

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
            "Use darker background and good lighting."
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
        TARGET_SIZE,
        interpolation=cv2.INTER_AREA,
    )

    normalized = resized.astype(np.float32) / 255.0

    # [H, W] -> [1, 1, H, W]
    x = normalized[None, None, :, :]

    # Repeat grayscale image to 3 channels
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


def get_embedding(session, image_bgr: np.ndarray, debug_dir=None, debug_name="debug"):
    x = preprocess_lucy_resnet18(
        image_bgr,
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


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def countdown_capture(
    picam2,
    window_name: str,
    delay_seconds: int,
    capture_label: str,
):
    """
    Wait delay_seconds while camera autofocus works.
    Then capture one full frame.
    """

    print(f"{capture_label}: waiting {delay_seconds} seconds for autofocus...")

    start_time = time.time()

    last_frame_bgr = None

    while True:
        elapsed = time.time() - start_time
        remaining = max(0, delay_seconds - int(elapsed))

        rgb_frame = picam2.capture_array()
        bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        last_frame_bgr = bgr_frame.copy()

        display = bgr_frame.copy()
        sharpness = sharpness_score(display)

        cv2.putText(
            display,
            f"{capture_label}",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            f"Autofocus delay: {remaining}s",
            (30, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            f"Sharpness: {sharpness:.2f}",
            (30, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            "Keep palm steady. Use dark background.",
            (30, 165),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow(window_name, display)

        key = cv2.waitKey(1) & 0xFF

        if key == 27 or key == ord("q"):
            return None

        if elapsed >= delay_seconds:
            break

    return last_frame_bgr


def main():
    parser = argparse.ArgumentParser(
        description="Test Lucy ResNet-18 ONNX palm model with Raspberry Pi autofocus camera"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="models/palmprint_encoder.onnx",
        help="Path to ResNet-18 palm ONNX model",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Cosine similarity threshold",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Camera width. Dataset style is 800.",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=600,
        help="Camera height. Dataset style is 600.",
    )

    parser.add_argument(
        "--focus-delay",
        type=int,
        default=5,
        help="Seconds to wait before capture for autofocus",
    )

    parser.add_argument(
        "--save-dir",
        type=str,
        default="samples/lucy_resnet18_autofocus_test",
        help="Directory to save captured images",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save preprocessing debug images",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    debug_dir = save_dir / "debug" if args.debug else None

    image1_path = save_dir / "test_palm_1.jpg"
    image2_path = save_dir / "test_palm_2.jpg"

    session = load_onnx_session(model_path)

    picam2 = setup_camera(
        width=args.width,
        height=args.height,
    )

    window_name = "Palm Model Autofocus Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("\n====================================")
    print("Palm Model Autofocus Camera Test")
    print("====================================")
    print("Camera size:", args.width, "x", args.height)
    print("Autofocus: Continuous Macro")
    print("Focus delay:", args.focus_delay, "seconds")
    print("Threshold:", args.threshold)
    print("SPACE: start capture image 1")
    print("Q / ESC: quit")
    print("====================================\n")

    captured_count = 0
    image1_bgr = None
    image2_bgr = None

    try:
        while True:
            rgb_frame = picam2.capture_array()
            bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

            display = bgr_frame.copy()
            sharpness = sharpness_score(display)

            cv2.putText(
                display,
                f"Captured: {captured_count}/2",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                display,
                "SPACE: Capture | Q/ESC: Quit",
                (30, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                display,
                f"Autofocus: continuous macro | Sharpness: {sharpness:.2f}",
                (30, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                display,
                "Use dark background. Keep palm steady.",
                (30, 165),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF

            if key == 27 or key == ord("q"):
                print("Quit.")
                break

            if key == 32:
                if captured_count == 0:
                    image1_bgr = countdown_capture(
                        picam2=picam2,
                        window_name=window_name,
                        delay_seconds=args.focus_delay,
                        capture_label="Capturing Image 1",
                    )

                    if image1_bgr is None:
                        print("Quit.")
                        break

                    cv2.imwrite(str(image1_path), image1_bgr)
                    print("Captured image 1:", image1_path)
                    print("Image 1 size:", image1_bgr.shape[1], "x", image1_bgr.shape[0])

                    captured_count = 1

                    print("Now press SPACE again to capture image 2.")

                elif captured_count == 1:
                    image2_bgr = countdown_capture(
                        picam2=picam2,
                        window_name=window_name,
                        delay_seconds=args.focus_delay,
                        capture_label="Capturing Image 2",
                    )

                    if image2_bgr is None:
                        print("Quit.")
                        break

                    cv2.imwrite(str(image2_path), image2_bgr)
                    print("Captured image 2:", image2_path)
                    print("Image 2 size:", image2_bgr.shape[1], "x", image2_bgr.shape[0])

                    captured_count = 2

                    print("\nRunning model...")

                    try:
                        emb1 = get_embedding(
                            session=session,
                            image_bgr=image1_bgr,
                            debug_dir=debug_dir,
                            debug_name="image1",
                        )

                        emb2 = get_embedding(
                            session=session,
                            image_bgr=image2_bgr,
                            debug_dir=debug_dir,
                            debug_name="image2",
                        )

                        sim = cosine_similarity(emb1, emb2)

                        print("\n========== Result ==========")
                        print("Image 1:", image1_path)
                        print("Image 2:", image2_path)
                        print("Embedding shape:", emb1.shape)
                        print("Embedding norm 1:", np.linalg.norm(emb1))
                        print("Embedding norm 2:", np.linalg.norm(emb2))
                        print("Palm similarity score:", sim)
                        print("Threshold:", args.threshold)

                        if sim >= args.threshold:
                            print("Decision: SAME / ACCEPT")
                        else:
                            print("Decision: DIFFERENT / REJECT")

                        if debug_dir is not None:
                            print("Debug images saved in:", debug_dir)

                        print("============================\n")

                    except Exception as exc:
                        print("\nERROR:", exc)
                        print("Try darker background, better lighting, or keep palm larger in frame.\n")

                    print("Press SPACE to reset and start another test, or Q to quit.")

                else:
                    captured_count = 0
                    image1_bgr = None
                    image2_bgr = None
                    print("Reset. Press SPACE to capture image 1 again.")

                time.sleep(0.5)

    finally:
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()