#!/usr/bin/env python3

import argparse
import time
from pathlib import Path

import cv2
import numpy as np
from picamera2 import Picamera2
from libcamera import controls


CAMERA_WIDTH = 800
CAMERA_HEIGHT = 600


def setup_camera(camera_num: int = 0):
    camera_info = Picamera2.global_camera_info()

    if not camera_info:
        raise RuntimeError(
            "No camera detected.\n"
            "Run: rpicam-hello --list-cameras\n"
            "Check camera cable, IMX519 overlay, then reboot."
        )

    print("Detected cameras:")
    for i, cam in enumerate(camera_info):
        print(f"Camera {i}: {cam}")

    picam2 = Picamera2(camera_num=camera_num)

    config = picam2.create_preview_configuration(
        main={
            "size": (CAMERA_WIDTH, CAMERA_HEIGHT),
            "format": "RGB888",
        }
    )

    picam2.configure(config)

    try:
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Continuous,
            "AfRange": controls.AfRangeEnum.Macro,
        })
        print("Autofocus: continuous macro")
    except Exception as exc:
        print("Warning: autofocus control failed:", exc)
        print("Camera will use default focus setting.")

    picam2.start()
    time.sleep(1.0)

    return picam2


def capture_frame_800x600(picam2):
    rgb_frame = picam2.capture_array()
    bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

    if bgr_frame.shape[1] != CAMERA_WIDTH or bgr_frame.shape[0] != CAMERA_HEIGHT:
        bgr_frame = cv2.resize(
            bgr_frame,
            (CAMERA_WIDTH, CAMERA_HEIGHT),
            interpolation=cv2.INTER_AREA,
        )

    return bgr_frame


def sharpness_score(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def draw_center_axis(frame: np.ndarray):
    h, w = frame.shape[:2]
    cx = w // 2
    cy = h // 2

    green = (0, 255, 0)

    cv2.line(frame, (cx, 0), (cx, h), green, 2)
    cv2.line(frame, (0, cy), (w, cy), green, 2)
    cv2.circle(frame, (cx, cy), 6, green, -1)

    return frame


def countdown_capture(picam2, window_name: str, delay_seconds: int):
    print(f"Waiting {delay_seconds} seconds for autofocus...")

    start_time = time.time()
    last_frame = None

    while True:
        elapsed = time.time() - start_time
        remaining = max(0, delay_seconds - int(elapsed))

        frame = capture_frame_800x600(picam2)
        last_frame = frame.copy()

        display = frame.copy()
        draw_center_axis(display)

        sharpness = sharpness_score(frame)

        cv2.putText(
            display,
            "Capturing one palm image",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            f"Autofocus delay: {remaining}s",
            (30, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            f"Camera: 800x600 | Sharpness: {sharpness:.2f}",
            (30, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            "Keep palm steady. Use dark background.",
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
            return None

        if elapsed >= delay_seconds:
            break

    return last_frame


def main():
    parser = argparse.ArgumentParser(
        description="Capture one 800x600 palm image only"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="samples/test_palm.jpg",
        help="Output image path",
    )

    parser.add_argument(
        "--focus-delay",
        type=int,
        default=5,
        help="Seconds to wait before capture",
    )

    parser.add_argument(
        "--camera-num",
        type=int,
        default=0,
        help="Camera number, usually 0",
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    picam2 = setup_camera(camera_num=args.camera_num)

    window_name = "Capture One Palm Image"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("\n====================================")
    print("Capture One Palm Image")
    print("====================================")
    print("Camera size: 800x600")
    print("Green center X/Y axis is preview only")
    print("Saved image has no green lines")
    print("SPACE: capture")
    print("Q / ESC: quit")
    print("Output:", output_path)
    print("====================================\n")

    try:
        while True:
            frame = capture_frame_800x600(picam2)

            display = frame.copy()
            draw_center_axis(display)

            sharpness = sharpness_score(frame)

            cv2.putText(
                display,
                "SPACE: capture one image | Q/ESC: quit",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                display,
                f"Camera: 800x600 | Sharpness: {sharpness:.2f}",
                (30, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                display,
                "Center your palm on green axis lines",
                (30, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF

            if key == 27 or key == ord("q"):
                print("Quit.")
                break

            if key == 32:
                captured_frame = countdown_capture(
                    picam2=picam2,
                    window_name=window_name,
                    delay_seconds=args.focus_delay,
                )

                if captured_frame is None:
                    print("Quit.")
                    break

                cv2.imwrite(str(output_path), captured_frame)

                print("\nCaptured image saved:")
                print(output_path)
                print("Image size:", captured_frame.shape[1], "x", captured_frame.shape[0])
                print("Sharpness:", sharpness_score(captured_frame))
                print()

                break

    finally:
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()