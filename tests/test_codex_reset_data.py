import io
import json
import urllib.request

import pytest

import codex_reset_data as D

SAMPLE = {
    "code": 0,
    "message": "ok",
    "data": {
        "updatedAt": "2026-10-13T04:53:51.024Z",
        "probability24h": 89,
        "probability48h": 99,
        "verdict": "elevated",
        "timeline": [
            {"time": "2026-10-07T03:00:00.000Z", "resetConfirmed": True},
            {"time": "2026-10-10T03:00:00.000Z", "resetConfirmed": False},
        ],
        "tiboRelevantPosts": [{"detail": "Global reset landing by EOD PST time. Enjoy"}],
    },
}


def test_extract_data_ok():
    assert D.extract_data(SAMPLE)["probability24h"] == 89


def test_extract_data_rejects_bad_payload():
    with pytest.raises(ValueError):
        D.extract_data({"code": 1, "data": None})
    with pytest.raises(ValueError):
        D.extract_data("not a dict")


def test_fetch_raw_parses_json(monkeypatch):
    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        return FakeResp(json.dumps(SAMPLE).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert D.fetch_raw("http://example.invalid")["code"] == 0


from datetime import datetime, timezone, timedelta

TZ8 = timezone(timedelta(hours=8))


def test_prob_color_thresholds():
    assert D.prob_color(10) == D.GREEN
    assert D.prob_color(29) == D.GREEN
    assert D.prob_color(30) == D.ORANGE
    assert D.prob_color(69) == D.ORANGE
    assert D.prob_color(70) == D.RED
    assert D.prob_color(99) == D.RED


def test_verdict_color_mapping():
    assert D.verdict_color("elevated") == D.RED
    assert D.verdict_color("moderate") == D.ORANGE
    assert D.verdict_color("low") == D.GREEN
    assert D.verdict_color("weird") == D.GRAY
    assert D.verdict_color("") == D.GRAY


def test_fmt_local_hhmm_converts_utc_to_tz():
    assert D.fmt_local_hhmm("2026-10-13T04:53:51.024Z", TZ8) == "12:53"


def test_days_since():
    now = datetime(2026, 10, 13, 12, 0, tzinfo=TZ8)
    assert D.days_since("2026-10-07T03:00:00.000Z", now) == 6


def test_last_confirmed_reset_picks_latest_and_none():
    assert D.last_confirmed_reset(SAMPLE["data"]["timeline"]) == "2026-10-07T03:00:00.000Z"
    assert D.last_confirmed_reset([]) is None
    assert D.last_confirmed_reset([{"time": "2026-10-10T00:00:00Z", "resetConfirmed": False}]) is None


def test_derive_view_full():
    now = datetime(2026, 10, 13, 12, 53, tzinfo=TZ8)
    vm = D.derive_view(SAMPLE["data"], TZ8, now=now)
    assert vm["prob24h"] == 89
    assert vm["prob48h"] == 99
    assert vm["verdict"] == "ELEVATED"
    assert vm["verdict_color"] == D.RED
    assert vm["prob24h_color"] == D.RED
    assert vm["last_reset_date"] == "2026-10-07"
    assert vm["last_reset_days"] == 6
    assert vm["preview"] == "Global reset landing by EOD PST time. Enjoy"
    assert vm["updated_hhmm"] == "12:53"


def test_derive_view_without_optional_fields():
    now = datetime(2026, 10, 13, 12, 0, tzinfo=TZ8)
    vm = D.derive_view({"probability24h": 5, "probability48h": 5, "updatedAt": "2026-10-13T04:00:00Z"}, TZ8, now=now)
    assert vm["preview"] is None
    assert vm["last_reset_date"] is None
    assert vm["last_reset_days"] is None
    assert vm["verdict"] == "—"
    assert vm["verdict_color"] == D.GRAY
    assert vm["prob24h_color"] == D.GREEN
