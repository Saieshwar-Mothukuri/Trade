"""
Low-level Binance Futures Testnet REST client.

Handles:
- HMAC-SHA256 request signing
- Timestamping
- HTTP session management
- Structured logging of every request/response
- Retry on transient network errors
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import get_logger

logger = get_logger("client")

BASE_URL = "https://testnet.binancefuture.com"

# Paths
_NEW_ORDER = "/fapi/v1/order"
_EXCHANGE_INFO = "/fapi/v1/exchangeInfo"
_ACCOUNT = "/fapi/v2/account"


def _build_session(retries: int = 3) -> requests.Session:
    """Return a requests Session with automatic retries on network errors."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "DELETE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API.

    Parameters
    ----------
    api_key:    Testnet API key
    api_secret: Testnet API secret
    base_url:   Override base URL (useful in tests / alternate environments)
    timeout:    Per-request timeout in seconds
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()  # bytes for HMAC
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = _build_session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Public API helpers
    # ------------------------------------------------------------------

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange info (no auth required)."""
        return self._get(_EXCHANGE_INFO, signed=False)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account details (signed)."""
        return self._get(_ACCOUNT, signed=True)

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a new futures order.

        Parameters
        ----------
        params: Pre-validated dict from validators.validate_all()

        Returns
        -------
        Raw API response dict
        """
        logger.info("Placing order | params=%s", params)
        response = self._post(_NEW_ORDER, params=params, signed=True)
        logger.info("Order response | %s", response)
        return response

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._api_secret, query_string.encode(), hashlib.sha256
        ).hexdigest()

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params["timestamp"] = self._timestamp()
            qs = urlencode(params)
            params["signature"] = self._sign(qs)

        url = f"{self._base_url}{path}"
        logger.debug("GET %s | params=%s", url, {k: v for k, v in params.items() if k != "signature"})

        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error on GET %s: %s", path, exc)
            raise ConnectionError(f"Cannot reach Binance testnet ({exc})") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout on GET %s: %s", path, exc)
            raise TimeoutError(f"Request timed out ({exc})") from exc

    def _post(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params["timestamp"] = self._timestamp()
            qs = urlencode(params)
            params["signature"] = self._sign(qs)

        url = f"{self._base_url}{path}"
        logger.debug(
            "POST %s | body=%s",
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            resp = self._session.post(url, data=params, timeout=self._timeout)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error on POST %s: %s", path, exc)
            raise ConnectionError(f"Cannot reach Binance testnet ({exc})") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout on POST %s: %s", path, exc)
            raise TimeoutError(f"Request timed out ({exc})") from exc

    @staticmethod
    def _handle_response(resp: requests.Response) -> Dict[str, Any]:
        logger.debug("HTTP %s | url=%s", resp.status_code, resp.url)
        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response | status=%s | body=%s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
            raise

        if not resp.ok:
            code = data.get("code", resp.status_code)
            msg = data.get("msg", resp.text)
            logger.error("API error | code=%s | msg=%s", code, msg)
            raise RuntimeError(f"Binance API error {code}: {msg}")

        return data
