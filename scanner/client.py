"""ifind HTTP client for fetching concept board and stock data.

Provides ``IfindClient`` which handles authentication (refresh_token
-> access_token), automatic token renewal on expiry, and rate-limit
aware requests to the ifind Quant API.
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

# Token-expiry error codes that trigger an automatic refresh.
_TOKEN_EXPIRED_CODES = frozenset({
    -1010,   # account logged out
    -1302,   # access_token expired or illegal
})

# Rate-limit error code.
_RATE_LIMIT_CODE = -4400

# Minimum interval (seconds) between consecutive API calls.
# 600 req/min => 10 req/sec => 0.1s between calls.
_MIN_REQUEST_INTERVAL = 0.1


class IfindClient:
    """HTTP client for the ifind Quant API.

    Handles token lifecycle, automatic retries on token expiry,
    and basic rate limiting.

    Attributes:
        base_url: Base URL of the ifind API (no trailing slash).
        refresh_token: Long-lived refresh token for authentication.
    """

    def __init__(
        self,
        base_url: str,
        refresh_token: str,
    ) -> None:
        """Initialise the client.

        Args:
            base_url: e.g. ``https://quantapi.51ifind.com``.
            refresh_token: Long-lived refresh token obtained from
                the ifind platform.
        """
        self.base_url = base_url.rstrip("/")
        self.refresh_token = refresh_token
        self._access_token: str = ""
        self._session = requests.Session()
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """Fetch the current valid access token.

        Returns:
            A valid access token string.

        Raises:
            RuntimeError: If the server response lacks an access_token.
        """
        url = f"{self.base_url}/api/v1/get_access_token"
        headers = {
            "Content-Type": "application/json",
            "refresh_token": self.refresh_token,
        }
        resp = self._session.post(url, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        token = body.get("data", {}).get("access_token")
        if not token:
            raise RuntimeError(
                "No access_token in response: %s", body
            )
        self._access_token = token
        logger.info("Obtained access_token successfully.")
        return self._access_token

    def _refresh_access_token(self) -> str:
        """Force-generate a new access token.

        Invalidates all previously issued tokens.

        Returns:
            The newly created access token string.

        Raises:
            RuntimeError: If the server response lacks an access_token.
        """
        url = f"{self.base_url}/api/v1/update_access_token"
        headers = {
            "Content-Type": "application/json",
            "refresh_token": self.refresh_token,
        }
        resp = self._session.post(url, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        token = body.get("data", {}).get("access_token")
        if not token:
            raise RuntimeError(
                "No access_token in refresh response: %s", body
            )
        self._access_token = token
        logger.info("Refreshed access_token successfully.")
        return self._access_token

    def _ensure_token(self) -> None:
        """Make sure a cached access token is available."""
        if not self._access_token:
            self._get_access_token()

    # ------------------------------------------------------------------
    # Core request helper
    # ------------------------------------------------------------------

    def _request(
        self,
        endpoint: str,
        data: dict,
    ) -> dict:
        """Send an authenticated POST and return parsed JSON.

        Automatically refreshes the access token on expiry and
        retries the request once.

        Args:
            endpoint: API path, e.g. ``/api/v1/data_pool``.
            data: JSON body to send.

        Returns:
            Parsed JSON response from the server.

        Raises:
            RuntimeError: If the API returns a non-zero errorcode
                that is not related to token expiry.
        """
        self._ensure_token()
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "access_token": self._access_token,
        }

        response = self._post_with_rate_limit(url, headers, data)
        body = response.json()
        errorcode = body.get("errorcode", 0)

        if errorcode in _TOKEN_EXPIRED_CODES:
            logger.info(
                "Token expired (errorcode=%s), refreshing.",
                errorcode,
            )
            self._refresh_access_token()
            headers["access_token"] = self._access_token
            response = self._post_with_rate_limit(url, headers, data)
            body = response.json()
            errorcode = body.get("errorcode", 0)

        if errorcode != 0:
            errmsg = body.get("errmsg", "unknown error")
            raise RuntimeError(
                f"API error {errorcode}: {errmsg}"
            )

        return body

    def _post_with_rate_limit(
        self,
        url: str,
        headers: dict,
        data: dict,
    ) -> requests.Response:
        """Execute a POST respecting the minimum request interval.

        Args:
            url: Full request URL.
            headers: HTTP headers (must include access_token).
            data: JSON body.

        Returns:
            The ``requests.Response`` object.

        Raises:
            RuntimeError: If a rate-limit response is received.
        """
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

        resp = self._session.post(url, json=data, headers=headers)
        self._last_request_time = time.monotonic()

        # Handle rate-limit response at HTTP level.
        if resp.status_code == 200:
            body = resp.json()
            if body.get("errorcode") == _RATE_LIMIT_CODE:
                raise RuntimeError(
                    "API rate limit exceeded: %s",
                    body.get("errmsg", ""),
                )
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Data pool (专题报表)
    # ------------------------------------------------------------------

    def get_concept_popularity(
        self,
        date: str,
        tjzq: str = "近一周",
    ) -> list[dict]:
        """Fetch concept popularity ranking from data pool p03797.

        Args:
            date: Trading date, e.g. ``"2026-06-02"``.
            tjzq: Statistical period filter (default ``"近一周"``).

        Returns:
            List of raw record dicts from the API.
        """
        data = {
            "reportname": "p03797",
            "functionpara": {
                "p03797_f002": date,
                "p03797_f003": tjzq,
            },
            "outputpara": (
                "p03797_f001:Y,p03797_f002:Y,"
                "p03797_f009:Y,p03797_f010:Y"
            ),
        }
        body = self._request("/api/v1/data_pool", data)
        return self._extract_table_rows(body)

    def get_board_stocks(
        self,
        date: str,
        concept_name: str,
        tjzq: str = "近一周",
    ) -> list[dict]:
        """Fetch hot board constituent stocks (data pool p03798).

        Args:
            date: Trading date, e.g. ``"2026-06-02"``.
            concept_name: Name of the concept board.
            tjzq: Statistical period filter (default ``"近一周"``).

        Returns:
            List of raw record dicts from the API.
        """
        data = {
            "reportname": "p03798",
            "functionpara": {
                "p03798_f001": date,
                "p03798_f002": concept_name,
                "p03798_f003": tjzq,
            },
            "outputpara": (
                "jydm:Y,jydm_mc:Y,p03798_f001:Y,"
                "p03798_f012:Y,p03798_f016:Y"
            ),
        }
        body = self._request("/api/v1/data_pool", data)
        return self._extract_table_rows(body)

    # ------------------------------------------------------------------
    # High-frequency (1min K-line)
    # ------------------------------------------------------------------

    def get_high_frequency(
        self,
        codes: list[str],
        indicators: list[str],
        starttime: str,
        endtime: str,
        interval: str = "1",
    ) -> dict:
        """Fetch intraday high-frequency K-line data.

        Args:
            codes: List of stock codes,
                e.g. ``["300033.SZ", "600030.SH"]``.
            indicators: List of indicator names,
                e.g. ``["open", "close"]``.
            starttime: Start datetime,
                e.g. ``"2026-06-02 09:30:00"``.
            endtime: End datetime,
                e.g. ``"2026-06-02 09:35:00"``.
            interval: Bar interval (default ``"1"`` for 1min).

        Returns:
            Raw API response dict keyed by ``tables``.
        """
        data = {
            "codes": ",".join(codes),
            "indicators": ",".join(indicators),
            "starttime": starttime,
            "endtime": endtime,
            "functionpara": {"Interval": interval},
        }
        return self._request(
            "/api/v1/high_frequency", data
        )

    # ------------------------------------------------------------------
    # History quotation (daily K-line)
    # ------------------------------------------------------------------

    def get_history_quotation(
        self,
        codes: list[str],
        indicators: list[str],
        startdate: str,
        enddate: str,
        interval: str = "D",
    ) -> dict:
        """Fetch historical daily (or weekly/monthly) K-line data.

        Args:
            codes: List of stock codes,
                e.g. ``["300033.SZ"]``.
            indicators: List of indicator names,
                e.g. ``["open", "close", "volume"]``.
            startdate: Start date, e.g. ``"2026-05-26"``.
            enddate: End date, e.g. ``"2026-06-02"``.
            interval: ``"D"`` (daily), ``"W"``, ``"M"``, etc.

        Returns:
            Raw API response dict keyed by ``tables``.
        """
        data = {
            "codes": ",".join(codes),
            "indicators": ",".join(indicators),
            "startdate": startdate,
            "enddate": enddate,
            "functionpara": {"Interval": interval},
        }
        return self._request(
            "/api/v1/cmd_history_quotation", data
        )

    # ------------------------------------------------------------------
    # Trade dates
    # ------------------------------------------------------------------

    def get_trade_dates(
        self,
        startdate: str,
        enddate: str,
        marketcode: str = "212001",
    ) -> list[str]:
        """Fetch trade dates for a given market.

        Args:
            startdate: Start date, e.g. ``"2026-06-01"``.
            enddate: End date, e.g. ``"2026-06-03"``.
            marketcode: Exchange code (default ``"212001"`` SSE).

        Returns:
            List of date strings in ``"YYYY-MM-DD"`` format.
        """
        data = {
            "marketcode": marketcode,
            "functionpara": {
                "mode": "1",
                "dateType": "0",
                "period": "D",
                "dateFormat": "0",
            },
            "startdate": startdate,
            "enddate": enddate,
        }
        body = self._request(
            "/api/v1/get_trade_dates", data
        )
        return self._extract_date_list(body)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_table_rows(body: dict) -> list[dict]:
        """Extract rows from a data_pool / quotation response.

        The API wraps results inside ``tables[0]["table"]``
        as a list of dicts (field -> value).

        Args:
            body: Full API response dict.

        Returns:
            List of row dicts, or an empty list if no data.
        """
        tables = body.get("tables", [])
        if not tables:
            return []
        table = tables[0].get("table", {})
        rows = table.get("table_data", [])
        return rows if isinstance(rows, list) else []

    @staticmethod
    def _extract_date_list(body: dict) -> list[str]:
        """Extract date strings from a get_trade_dates response.

        Args:
            body: Full API response dict.

        Returns:
            List of date strings.
        """
        tables = body.get("tables", [])
        if not tables:
            return []
        table = tables[0].get("table", {})
        rows = table.get("table_data", [])
        if not rows:
            return []
        # Each row is a dict with a date field; the key varies.
        dates: list[str] = []
        for row in rows:
            for val in row.values():
                if isinstance(val, str) and val.strip():
                    dates.append(val.strip())
                    break
        return dates
