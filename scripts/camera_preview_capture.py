#!/usr/bin/env python3

import argparse
import time
from pathlib import Path

import cv2
from picamera2 import Picamera2
from libcamera import controls


def apply_sharpness_score(image):
    """
    Calculate image sharpness using Laplacian variance.
    Higher value = sharper image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    return score


def setup_camera(width, height, autofocus_mode, lens_position):
    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={
            "size": (width, height),
            "format": "RGB888",
        }
    )

    picam2.configure(config)

    if autofocus_mode == "manual":
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Manual,
            "LensPosition": float(lens_position),
        })
        print("Focus mode: manual")
        print(f"Lens position: {lens_position}")

    elif autofocus_mode == "continuous":
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Continuous,
            "AfRange": controls.AfRangeEnum.Macro,
        })
        print("Focus mode: continuous macro")

    elif autofocus_mode == "auto":
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Auto,
            "AfRange": controls.AfRangeEnum.Macro,
        })
        print("Focus mode: auto macro")

    else:
        print("Focus mode: default camera setting")

    picam2.start()
    time.sleep(1.0)

    return picam2


def main():
    parser = argparse.ArgumentParser(
        description="OpenCV real-time camera preview and full-frame palm capture"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="samples/palm_capture.jpg",
        help="Output image path",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Camera preview width",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Camera preview height",
    )

    parser.add_argument(
        "--autofocus-mode",
        type=str,
        default="manual",
        choices=["manual", "continuous", "auto", "default"],
        help="Focus mode: manual, continuous, auto, or default",
    )

    parser.add_argument(
        "--lens-position",
        type=float,
        default=8.0,
        help="Manual lens position. Higher value usually means closer focus.",
    )

    parser.add_argument(
        "--show-sharpness",
        action="store_true",
        help="Show sharpness score on preview window",
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("====================================")
    print("Palm Full Frame Camera Capture")
    print("====================================")
    print("Output:", output_path)
    print("Resolution:", args.width, "x", args.height)
    print("Autofocus mode:", args.autofocus_mode)
    print("Lens position:", args.lens_position)
    print("Press SPACE to capture full frame")
    print("Press Q or ESC to quit")
    print("====================================")

    picam2 = setup_camera(
        width=args.width,
        height=args.height,
        autofocus_mode=args.autofocus_mode,
        lens_position=args.lens_position,
    )

    window_name = "Palm Camera Preview"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            # Picamera2 returns RGB frame
            rgb_frame = picam2.capture_array()

            # Convert RGB to BGR for OpenCV display/save
            bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

            display_frame = bgr_frame.copy()

            sharpness = apply_sharpness_score(bgr_frame)

            cv2.putText(
                display_frame,
                "SPACE: Capture full frame | Q/ESC: Quit",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                display_frame,
                f"Focus: {args.autofocus_mode} | Lens: {args.lens_position}",
                (30, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 0),
                2,
                cv2.LINE_AA,
            )

            if args.show_sharpness:
                cv2.putText(
                    display_frame,
                    f"Sharpness: {sharpness:.2f}",
                    (30, 110),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(window_name, display_frame)

            key = cv2.waitKey(1) & 0xFF

            # ESC or Q
            if key == 27 or key == ord("q"):
                print("Quit.")
                break

            # SPACE
            if key == 32:
                cv2.imwrite(str(output_path), bgr_frame)
                print(f"Captured full frame: {output_path}")
                print(f"Sharpness score: {sharpness:.2f}")

                time.sleep(0.5)

    finally:
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()