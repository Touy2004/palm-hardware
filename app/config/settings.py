from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


def env_str(key: str, default: str) -> str:
    return os.getenv(key, default)


def env_int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def env_float(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


def env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)

    if value is None:
        return default

    return value.strip().lower() in ["true", "1", "yes", "y"]


@dataclass
class AppSettings:
    api_base_url: str
    device_code: str
    model_version: str
    model_path: Path

    camera_width: int
    camera_height: int
    focus_delay: int
    camera_num: int

    gui_width: int
    gui_height: int

    qr_prefix: str

    mock_liveness_passed: bool
    mock_thermal_min: float
    mock_thermal_max: float
    mock_thermal_avg: float
    mock_quality_score: float

    register_dir: Path
    attendance_dir: Path
    qr_output_path: Path


def load_settings() -> AppSettings:
    register_dir = Path("samples/gui/register")
    attendance_dir = Path("samples/gui/attendance")

    return AppSettings(
        api_base_url=env_str("API_BASE_URL", "https://api.phoudthasone.com/api/v1").rstrip("/"),
        device_code=env_str("DEVICE_CODE", "DEV-001"),
        model_version=env_str("MODEL_VERSION", "resnet18-palm-onnx-v1"),
        model_path=Path(env_str("MODEL_PATH", "models/palmprint_encoder.onnx")),

        camera_width=env_int("CAMERA_WIDTH", 800),
        camera_height=env_int("CAMERA_HEIGHT", 600),
        focus_delay=env_int("FOCUS_DELAY", 5),
        camera_num=env_int("CAMERA_NUM", 0),

        gui_width=env_int("GUI_WIDTH", 480),
        gui_height=env_int("GUI_HEIGHT", 320),

        qr_prefix=env_str("QR_PREFIX", ""),

        mock_liveness_passed=env_bool("MOCK_LIVENESS_PASSED", True),
        mock_thermal_min=env_float("MOCK_THERMAL_MIN", 33.5),
        mock_thermal_max=env_float("MOCK_THERMAL_MAX", 36.2),
        mock_thermal_avg=env_float("MOCK_THERMAL_AVG", 35.1),
        mock_quality_score=env_float("MOCK_QUALITY_SCORE", 0.98),

        register_dir=register_dir,
        attendance_dir=attendance_dir,
        qr_output_path=Path("samples/gui/pairing_qr.png"),
    )