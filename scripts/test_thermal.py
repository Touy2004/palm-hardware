#!/usr/bin/env python3

import argparse
import sys
import time
from statistics import mean


def test_mlx90640(refresh_rate_hz: int = 4, loop: bool = False):
    try:
        import board
        import busio
        import adafruit_mlx90640
    except ImportError as exc:
        print("Missing thermal sensor libraries.")
        print("Install with:")
        print("pip install adafruit-blinka adafruit-circuitpython-mlx90640")
        raise exc

    i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)

    mlx = adafruit_mlx90640.MLX90640(i2c)

    if refresh_rate_hz == 2:
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
    elif refresh_rate_hz == 4:
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
    elif refresh_rate_hz == 8:
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_8_HZ
    else:
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

    frame = [0] * 768

    print("MLX90640 thermal sensor started.")
    print("Put your palm in front of the sensor.")
    print("Press CTRL+C to stop.")

    while True:
        try:
            mlx.getFrame(frame)

            thermal_min = min(frame)
            thermal_max = max(frame)
            thermal_avg = mean(frame)

            print(
                f"thermal_min={thermal_min:.2f}°C | "
                f"thermal_max={thermal_max:.2f}°C | "
                f"thermal_avg={thermal_avg:.2f}°C"
            )

            if not loop:
                break

            time.sleep(0.5)

        except ValueError:
            continue


def simple_liveness_test(background_avg: float, palm_avg: float, threshold: float):
    diff = palm_avg - background_avg

    print("\n========== Liveness Test ==========")
    print(f"Background avg: {background_avg:.2f}°C")
    print(f"Palm avg:       {palm_avg:.2f}°C")
    print(f"Difference:     {diff:.2f}°C")
    print(f"Threshold:      {threshold:.2f}°C")

    if diff >= threshold:
        print("Liveness: PASSED")
    else:
        print("Liveness: FAILED")


def main():
    parser = argparse.ArgumentParser(description="Test thermal sensor on Raspberry Pi")

    parser.add_argument(
        "--sensor",
        type=str,
        default="mlx90640",
        choices=["mlx90640"],
        help="Thermal sensor type",
    )

    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously read thermal sensor",
    )

    parser.add_argument(
        "--refresh-rate",
        type=int,
        default=4,
        choices=[2, 4, 8],
        help="MLX90640 refresh rate",
    )

    parser.add_argument(
        "--background-avg",
        type=float,
        default=None,
        help="Background average temperature for liveness test",
    )

    parser.add_argument(
        "--palm-avg",
        type=float,
        default=None,
        help="Palm average temperature for liveness test",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=3.0,
        help="Temperature difference threshold",
    )

    args = parser.parse_args()

    if args.background_avg is not None and args.palm_avg is not None:
        simple_liveness_test(
            background_avg=args.background_avg,
            palm_avg=args.palm_avg,
            threshold=args.threshold,
        )
        return

    if args.sensor == "mlx90640":
        test_mlx90640(
            refresh_rate_hz=args.refresh_rate,
            loop=args.loop,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(130)
    except Exception as exc:
        print("Error:", exc)
        sys.exit(1)