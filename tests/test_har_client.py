import base64
import json
from pathlib import Path

import pytest

from cndc_extractor.exceptions import HARClientError
from cndc_extractor.har_client import HARJsonClient


def write_har(path: Path, entries: list[dict]) -> None:
    path.write_text(json.dumps({"log": {"entries": entries}}), encoding="utf-8")


def entry(url: str, payload: object, encoding: str | None = None) -> dict:
    text = json.dumps(payload)
    content = {"text": text}
    if encoding == "base64":
        content = {"text": base64.b64encode(text.encode("utf-8")).decode("ascii"), "encoding": "base64"}
    return {"request": {"url": url}, "response": {"status": 200, "content": content}}


def test_har_reads_plain_json_and_matches_url(tmp_path: Path) -> None:
    path = tmp_path / "test.har"
    write_har(path, [entry("https://x.test/rt/fechas", [{"ok": True}])])
    assert HARJsonClient(path).get_json("https://x.test/rt/fechas") == [{"ok": True}]


def test_har_reads_base64_json(tmp_path: Path) -> None:
    path = tmp_path / "test.har"
    write_har(path, [entry("https://x.test/rt/frecuencia/historial?registros=360", [{"v": 1}], "base64")])
    assert HARJsonClient(path).get_json("https://x.test/rt/frecuencia/historial?registros=360") == [{"v": 1}]


def test_har_reports_missing_endpoint(tmp_path: Path) -> None:
    path = tmp_path / "test.har"
    write_har(path, [])
    with pytest.raises(HARClientError):
        HARJsonClient(path).get_json("https://x.test/rt/fechas")
