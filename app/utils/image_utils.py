import cv2
import numpy as np


def sharpness_score(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def draw_center_axis(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]

    cx = w // 2
    cy = h // 2

    green = (0, 255, 0)

    cv2.line(frame, (cx, 0), (cx, h), green, 2)
    cv2.line(frame, (0, cy), (w, cy), green, 2)
    cv2.circle(frame, (cx, cy), 6, green, -1)

    return frame


def add_text(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    y = 30

    for line in lines:
        cv2.putText(
            frame,
            line,
            (12, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y += 24

    return frame