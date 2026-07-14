import json
import requests


class ApiClient:
    def __init__(self, api_base_url: str, device_code: str):
        self.api_base_url = api_base_url.rstrip("/")
        self.device_code = device_code

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.api_base_url}{path}"

        try:
            response = requests.request(method, url, timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise RuntimeError(f"Request failed: {exc}") from exc

        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        if response.status_code < 200 or response.status_code >= 300:
            if isinstance(data, dict) and "message" in data:
                raise RuntimeError(data["message"])
            raise RuntimeError(
                f"API error {response.status_code}\n"
                f"URL: {url}\n"
                f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}"
            )

        return data

    @staticmethod
    def _data(response_json):
        data = response_json.get("data")
        return data if isinstance(data, dict) else {}

    def heartbeat(self):
        payload = {"device_code": self.device_code}
        return self._request("POST", "/devices/heartbeat", json=payload)

    def create_pairing_session(self):
        payload = {
            "device_code": self.device_code,
            "purpose": "enrollment",
        }

        response = self._request(
            "POST",
            "/devices/pairing-sessions",
            json=payload,
        )

        data = self._data(response)

        session_id = data.get("session_id")
        session_token = data.get("session_token")
        qr_code_data = data.get("qr_code_data") or session_token

        if not session_id:
            raise RuntimeError("Missing session_id from pairing session response")

        if not qr_code_data:
            raise RuntimeError("Missing session_token or qr_code_data from response")

        return {
            "session_id": session_id,
            "session_token": session_token or qr_code_data,
            "qr_code_data": qr_code_data,
            "raw": response,
        }

    def check_pairing_status(self, session_id: str):
        response = self._request(
            "GET",
            f"/devices/pairing-sessions/{session_id}/status",
        )

        data = self._data(response)

        return {
            "status": data.get("status", "unknown"),
            "session_token": data.get("session_token"),
            "approved_session_token": data.get("approved_session_token"),
            "raw": response,
        }

    def enroll_palm(
        self,
        session_token: str,
        model_version: str,
        embedding: list[float],
        liveness_passed: bool,
        quality_score: float,
    ):
        payload = {
            "device_code": self.device_code,
            "session_token": session_token,
            "model_version": model_version,
            "embedding_dim": len(embedding),
            "embeddings": [embedding],
            "liveness_passed": liveness_passed,
            "quality_score": quality_score,
        }

        return self._request(
            "POST",
            "/devices/palm/enroll",
            json=payload,
        )

    def process_attendance(
        self,
        model_version: str,
        embedding: list[float],
        liveness_passed: bool,
        quality_score: float,
    ):
        payload = {
            "device_code": self.device_code,
            "model_version": model_version,
            "embedding_dim": len(embedding),
            "embeddings": [embedding],
            "liveness_passed": liveness_passed,
            "quality_score": quality_score,
        }

        return self._request(
            "POST",
            "/devices/attendance/palm",
            json=payload,
        )