"""Reusable HTTP JSON client."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .exceptions import HTTPClientError
from .models import JsonData

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class HTTPJsonClient:
    """Small JSON client with bounded retries and clear errors."""

    def __init__(self, timeout: float = 30, retries: int = 3, logger: logging.Logger | None = None) -> None:
        self.timeout = timeout
        self.retries = max(0, retries)
        self.logger = logger or logging.getLogger("cndc_extractor")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "CNDC-Graficas-Extractor/0.1 (+https://www.cndc.bo)",
            }
        )

    def get_json(self, url: str) -> JsonData:
        last_error: Exception | None = None
        attempts = self.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                self.logger.info("Consultando URL: %s", url)
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code in RETRY_STATUS_CODES and attempt < attempts:
                    self.logger.warning(
                        "Reintento %s/%s por estado HTTP %s en %s",
                        attempt,
                        attempts - 1,
                        response.status_code,
                        url,
                    )
                    time.sleep(attempt * 1.5)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.lower():
                    raise HTTPClientError(f"La respuesta no parece JSON ({content_type}) para {url}")
                data: Any = response.json()
                if not isinstance(data, (list, dict)):
                    raise HTTPClientError(f"JSON inesperado en {url}: {type(data).__name__}")
                self.logger.info("JSON recibido de %s: tipo=%s", url, type(data).__name__)
                return data
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    self.logger.warning("Reintento %s/%s por error: %s", attempt, attempts - 1, exc)
                    time.sleep(attempt * 1.5)
                    continue
                break
            except ValueError as exc:
                raise HTTPClientError(f"No se pudo interpretar JSON de {url}: {exc}") from exc
        raise HTTPClientError(f"No se pudo consultar {url}: {last_error}") from last_error
