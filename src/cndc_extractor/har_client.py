"""HAR-backed JSON client for reproducible tests."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .exceptions import HARClientError
from .models import JsonData


class HARJsonClient:
    """Reads JSON responses from a HAR file using request URLs."""

    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            self.har = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise HARClientError(f"No existe el archivo HAR: {path}") from exc
        except json.JSONDecodeError as exc:
            raise HARClientError(f"HAR invalido: {exc}") from exc

    def get_json(self, url: str) -> JsonData:
        for entry in self.har.get("log", {}).get("entries", []):
            request_url = entry.get("request", {}).get("url", "")
            status = int(entry.get("response", {}).get("status", 0) or 0)
            if 200 <= status < 300 and self._matches(request_url, url):
                content = entry.get("response", {}).get("content", {})
                text = content.get("text")
                if text is None:
                    raise HARClientError(f"La entrada HAR no contiene response.content.text: {url}")
                if str(content.get("encoding", "")).lower() == "base64":
                    text = base64.b64decode(text).decode("utf-8")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise HARClientError(f"Respuesta HAR no es JSON para {url}: {exc}") from exc
                if not isinstance(data, (list, dict)):
                    raise HARClientError(f"JSON HAR inesperado para {url}: {type(data).__name__}")
                return data
        raise HARClientError(f"No se encontro una respuesta HTTP exitosa en el HAR para: {url}")

    @staticmethod
    def _matches(candidate: str, wanted: str) -> bool:
        cand = urlparse(candidate)
        want = urlparse(wanted)
        if cand.scheme and want.scheme and (cand.scheme, cand.netloc, cand.path) != (
            want.scheme,
            want.netloc,
            want.path,
        ):
            return False
        if not cand.scheme and candidate.split("?")[0] != wanted.split("?")[0]:
            return False
        wanted_qs = parse_qs(want.query)
        cand_qs = parse_qs(cand.query)
        return all(cand_qs.get(key) == value for key, value in wanted_qs.items())
