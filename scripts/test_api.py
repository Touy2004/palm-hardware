#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.phoudthasone.com/api/v1").rstrip("/")
DEVICE_CODE = os.getenv("DEVICE_CODE", "DEV-001")


def pretty_print(title: str, data):
    print(f"\n========== {title} ==========")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)


def request_json(method: str, path: str, **kwargs):
    url = f"{API_BASE_URL}{path}"

    try:
        response = requests.request(
            method=method,
            url=url,
            timeout=15,
            **kwargs,
        )

        content_type = response.headers.get("Content-Type", "")

        if "application/json" in content_type:
            body = response.json()
        else:
            body = response.text

        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "body": body,
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "body": str(exc),
        }


def test_health():
    return request_json("GET", "/")


def test_heartbeat():
    return request_json(
        "POST",
        "/devices/heartbeat",
        json={
            "device_code": DEVICE_CODE,
        },
    )


def test_create_pairing_session():
    return request_json(
        "POST",
        "/devices/pairing-sessions",
        json={
            "device_code": DEVICE_CODE,
            "purpose": "enrollment",
        },
    )


def test_pairing_status(session_id: str):
    return request_json(
        "GET",
        f"/devices/pairing-sessions/{session_id}/status",
    )


def test_identify_dummy():
    dummy_embedding = [0.0] * 128

    return request_json(
        "POST",
        "/devices/palm/identify",
        json={
            "device_code": DEVICE_CODE,
            "model_version": "mobilenetv3-palm-simclr-triplet-v1",
            "embedding_dim": 128,
            "embeddings": [dummy_embedding],
            "liveness_passed": True,
            "quality_score": 0.98,
            "thermal_min": 33.5,
            "thermal_max": 36.2,
            "thermal_avg": 35.1,
        },
    )


def main():
    parser = argparse.ArgumentParser(description="Test Palm Recognition API from Raspberry Pi")

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run health, heartbeat, and create pairing session tests",
    )

    parser.add_argument(
        "--health",
        action="store_true",
        help="Test API health endpoint",
    )

    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Test device heartbeat endpoint",
    )

    parser.add_argument(
        "--pairing",
        action="store_true",
        help="Test create pairing session endpoint",
    )

    parser.add_argument(
        "--status",
        type=str,
        default="",
        help="Test pairing status by session_id",
    )

    parser.add_argument(
        "--identify-dummy",
        action="store_true",
        help="Test identify endpoint with dummy embedding",
    )

    args = parser.parse_args()

    print("Project root:", PROJECT_ROOT)
    print("API_BASE_URL:", API_BASE_URL)
    print("DEVICE_CODE:", DEVICE_CODE)

    if not any([args.all, args.health, args.heartbeat, args.pairing, args.status, args.identify_dummy]):
        args.all = True

    if args.all or args.health:
        pretty_print("Health Check", test_health())

    if args.all or args.heartbeat:
        pretty_print("Device Heartbeat", test_heartbeat())

    if args.all or args.pairing:
        pairing_result = test_create_pairing_session()
        pretty_print("Create Pairing Session", pairing_result)

        body = pairing_result.get("body")
        if isinstance(body, dict):
            data = body.get("data") or {}
            session_id = data.get("session_id")
            session_token = data.get("session_token")

            if session_id:
                print("\nSession ID:", session_id)

            if session_token:
                print("Session Token:", session_token)
                print("QR payload suggestion:")
                print(f"palmapp://pair?session_id={session_id}&token={session_token}")

    if args.status:
        pretty_print("Pairing Status", test_pairing_status(args.status))

    if args.identify_dummy:
        pretty_print("Identify Dummy Embedding", test_identify_dummy())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(130)