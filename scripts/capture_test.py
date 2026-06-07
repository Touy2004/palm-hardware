#!/usr/bin/env python3

import argparse
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image
from dotenv import load_dotenv
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

DEFAULT_WIDTH = int(os.getenv("CAPTURE_WIDTH", "1280"))
DEFAULT_HEIGHT = int(os.getenv("CAPTURE_HEIGHT", "720"))


def run_command(command):
    print("Running:", " ".join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")


def list_cameras():
    run_command(["rpicam-hello", "--list-cameras"])


def capture_image(output_path: Path, width: int, height: int, timeout_ms: int):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "rpicam-still",
        "-o",
        str(output_path),
        "--width",
        str(width),
        "--height",
        str(height),
        "--timeout",
        str(timeout_ms),
        "--nopreview",
    ]

    run_command(command)

    if not output_path.exists():
        raise FileNotFoundError(f"Capture failed. File not found: {output_path}")

    with Image.open(output_path) as img:
        print(f"Saved: {output_path}")
        print(f"Image size: {img.size}")
        print(f"Image mode: {img.mode}")


def main():
    parser = argparse.ArgumentParser(description="Test RGB camera capture on Raspberry Pi")

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available cameras",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "samples" / "palm_test.jpg"),
        help="Output image path",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of images to capture",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help="Capture width",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help="Capture height",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1000,
        help="Camera warm-up timeout in milliseconds",
    )

    args = parser.parse_args()

    if args.list:
        list_cameras()
        return

    output_path = Path(args.output)

    if args.count <= 1:
        capture_image(output_path, args.width, args.height, args.timeout)
        return

    stem = output_path.stem
    suffix = output_path.suffix or ".jpg"
    parent = output_path.parent

    for index in range(1, args.count + 1):
        path = parent / f"{stem}_{index:02d}{suffix}"
        print(f"\nCapture {index}/{args.count}")
        capture_image(path, args.width, args.height, args.timeout)
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Error:", exc)
        sys.exit(1)