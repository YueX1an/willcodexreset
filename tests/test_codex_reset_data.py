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
