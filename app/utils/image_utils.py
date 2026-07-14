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


def draw_hand_guide(frame: np.ndarray, instruction: str) -> np.ndarray:
    h, w = frame.shape[:2]
    
    # Base box size
    box_w = int(w * 0.4)
    box_h = int(h * 0.6)
    
    # Base center
    cx, cy = w // 2, h // 2
    
    instruction_lower = instruction.lower()
    
    # Modify size and position based on instruction
    if "higher" in instruction_lower:
        cy -= int(h * 0.15)
    elif "lower" in instruction_lower:
        cy += int(h * 0.15)
    elif "left" in instruction_lower:
        cx -= int(w * 0.15)
    elif "right" in instruction_lower:
        cx += int(w * 0.15)
    elif "closer" in instruction_lower:
        box_w = int(w * 0.55)
        box_h = int(h * 0.8)
    elif "farther" in instruction_lower:
        box_w = int(w * 0.25)
        box_h = int(h * 0.4)
        
    x1 = cx - box_w // 2
    y1 = cy - box_h // 2
    x2 = cx + box_w // 2
    y2 = cy + box_h // 2
    
    # Draw viewfinder corners
    color = (0, 215, 255) # Yellow/Orange in BGR
    thickness = 3
    line_len = 40
    
    # Top-left
    cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, thickness)
    cv2.line(frame, (x1, y1), (x1, y1 + line_len), color, thickness)
    # Top-right
    cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, thickness)
    cv2.line(frame, (x2, y1), (x2, y1 + line_len), color, thickness)
    # Bottom-left
    cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, thickness)
    cv2.line(frame, (x1, y2), (x1, y2 - line_len), color, thickness)
    # Bottom-right
    cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thickness)
    cv2.line(frame, (x2, y2), (x2, y2 - line_len), color, thickness)
    
    return frame