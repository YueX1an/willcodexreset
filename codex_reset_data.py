"""Pure data layer for the Codex Reset widget: fetch, parse, derive the view model."""
from __future__ import annotations

import json
import urllib.request

API_URL = "https://willcodexreset.com/api/reset-radar"

GREEN = "#34C759"
ORANGE = "#FF9F0A"
RED = "#FF453A"
GRAY = "#8E8E93"


def fetch_raw(url: str = API_URL, timeout: int = 10) -> dict:
    """GET the endpoint and return the parsed top-level JSON. Raises on any error."""
    req = urllib.request.Request(url, headers={"User-Agent": "codex-reset-widget/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def extract_data(payload: dict) -> dict:
    """Return payload['data'], or raise ValueError if the payload is not the expected shape."""
    if not isinstance(payload, dict) or payload.get("code") != 0 or not isinstance(payload.get("data"), dict):
        raise ValueError(f"unexpected payload: {str(payload)[:200]}")
    return payload["data"]
