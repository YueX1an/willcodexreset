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


from datetime import datetime, tzinfo


def prob_color(p: int) -> str:
    if p >= 70:
        return RED
    if p >= 30:
        return ORANGE
    return GREEN


def verdict_color(v: str) -> str:
    v = (v or "").lower()
    if v in ("elevated", "high", "severe"):
        return RED
    if v in ("moderate", "medium"):
        return ORANGE
    if v in ("low", "calm", "quiet"):
        return GREEN
    return GRAY


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_local_hhmm(iso_utc: str, tz: tzinfo) -> str:
    return _parse_iso(iso_utc).astimezone(tz).strftime("%H:%M")


def days_since(iso_utc: str, now: datetime) -> int:
    return (now - _parse_iso(iso_utc)).days


def last_confirmed_reset(timeline: list) -> str | None:
    confirmed = [t for t in (timeline or []) if t.get("resetConfirmed") and t.get("time")]
    if not confirmed:
        return None
    return max(confirmed, key=lambda t: t["time"])["time"]


def derive_view(data: dict, tz: tzinfo, now: datetime | None = None) -> dict:
    """Turn raw API `data` into everything the UI needs to render."""
    now = now or datetime.now(tz)
    last = last_confirmed_reset(data.get("timeline"))
    posts = data.get("tiboRelevantPosts") or []
    p24 = int(data.get("probability24h", 0))
    p48 = int(data.get("probability48h", 0))
    verdict = (data.get("verdict") or "").strip()
    return {
        "prob24h": p24,
        "prob48h": p48,
        "prob24h_color": prob_color(p24),
        "prob48h_color": prob_color(p48),
        "verdict": verdict.upper() if verdict else "—",
        "verdict_color": verdict_color(verdict),
        "last_reset_date": _parse_iso(last).astimezone(tz).strftime("%Y-%m-%d") if last else None,
        "last_reset_days": days_since(last, now) if last else None,
        "preview": posts[0].get("detail") if posts else None,
        "updated_hhmm": fmt_local_hhmm(data["updatedAt"], tz) if data.get("updatedAt") else "--:--",
    }
