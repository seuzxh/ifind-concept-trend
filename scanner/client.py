"""ifind HTTP 客户端，用于获取概念板块和个股数据.

提供 ``IfindClient`` 类，负责处理鉴权流程（refresh_token
-> access_token）、令牌过期自动续期，以及基于限流策略
的 API 请求。
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

# 令牌过期错误码，触发自动刷新.
_TOKEN_EXPIRED_CODES = frozenset({
    -1010,   # 账号已登出
    -1302,   # access_token 过期或非法
})

# 限流错误码.
_RATE_LIMIT_CODE = -4400

# 连续请求的最小间隔（秒）.
# 600 次/分钟 => 10 次/秒 => 间隔 0.1 秒.
_MIN_REQUEST_INTERVAL = 0.1


class IfindClient:
    """ifind 量化 API 的 HTTP 客户端.

    负责令牌生命周期管理、令牌过期自动重试以及基础限流.

    Attributes:
        base_url: ifind API 基础地址（不含末尾斜杠）.
        refresh_token: 长期有效的刷新令牌.
    """

    def __init__(
        self,
        base_url: str,
        refresh_token: str,
    ) -> None:
        """初始化客户端.

        Args:
            base_url: API 基础地址，
                如 ``https://quantapi.51ifind.com``.
            refresh_token: 从 ifind 平台获取的长期刷新令牌.
        """
        self.base_url = base_url.rstrip("/")
        self.refresh_token = refresh_token
        self._access_token: str = ""
        self._session = requests.Session()
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # 令牌管理
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """获取当前有效的 access_token.

        Returns:
            有效的 access_token 字符串.

        Raises:
            RuntimeError: 服务端响应中未包含 access_token.
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
        """强制生成新的 access_token.

        此操作会使之前签发的所有令牌失效.

        Returns:
            新创建的 access_token 字符串.

        Raises:
            RuntimeError: 服务端响应中未包含 access_token.
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
        """确保缓存中已有有效的 access_token."""
        if not self._access_token:
            self._get_access_token()

    # ------------------------------------------------------------------
    # 核心请求方法
    # ------------------------------------------------------------------

    def _request(
        self,
        endpoint: str,
        data: dict,
    ) -> dict:
        """发送带鉴权的 POST 请求并返回解析后的 JSON.

        令牌过期时自动刷新并重试一次.

        Args:
            endpoint: API 路径，如 ``/api/v1/data_pool``.
            data: 要发送的 JSON 请求体.

        Returns:
            服务端返回的解析后 JSON 响应.

        Raises:
            RuntimeError: API 返回非零 errorcode 且
                该错误与令牌过期无关.
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

        # 令牌过期时自动刷新并重试
        if errorcode in _TOKEN_EXPIRED_CODES:
            logger.info(
                "Token expired (errorcode=%s), refreshing.",
                errorcode,
            )
            self._refresh_access_token()
            headers["access_token"] = self._access_token
            response = self._post_with_rate_limit(
                url, headers, data
            )
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
        """在遵守最小请求间隔的前提下执行 POST 请求.

        Args:
            url: 完整的请求 URL.
            headers: HTTP 请求头（须包含 access_token）.
            data: JSON 请求体.

        Returns:
            ``requests.Response`` 对象.

        Raises:
            RuntimeError: 收到限流响应.
        """
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

        resp = self._session.post(url, json=data, headers=headers)
        self._last_request_time = time.monotonic()

        # 在 HTTP 层面处理限流响应
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
    # 数据池接口（专题报表）
    # ------------------------------------------------------------------

    def get_concept_popularity(
        self,
        date: str,
        tjzq: str = "近一周",
    ) -> list[dict]:
        """从数据池 p03797 获取概念人气排名.

        Args:
            date: 交易日期，如 ``"2026-06-02"``.
            tjzq: 统计周期筛选条件（默认 ``"近一周"``）.

        Returns:
            API 返回的原始记录字典列表.
        """
        data = {
            "reportname": "p03797",
            "functionpara": {
                "date": date,
                "tjzq": tjzq,
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
        """从数据池 p03798 获取热门板块成分股.

        Args:
            date: 交易日期，如 ``"2026-06-02"``.
            concept_name: 概念板块名称.
            tjzq: 统计周期筛选条件（默认 ``"近一周"``）.

        Returns:
            API 返回的原始记录字典列表.
        """
        data = {
            "reportname": "p03798",
            "functionpara": {
                "date": date,
                "hy": concept_name,
                "tjzq": tjzq,
            },
            "outputpara": (
                "jydm:Y,jydm_mc:Y,p03798_f001:Y,"
                "p03798_f012:Y,p03798_f016:Y"
            ),
        }
        body = self._request("/api/v1/data_pool", data)
        return self._extract_table_rows(body)

    # ------------------------------------------------------------------
    # 高频数据（1分钟 K 线）
    # ------------------------------------------------------------------

    def get_high_frequency(
        self,
        codes: list[str],
        indicators: list[str],
        starttime: str,
        endtime: str,
        interval: str = "1",
    ) -> dict:
        """获取日内高频 K 线数据.

        Args:
            codes: 证券代码列表，
                如 ``["300033.SZ", "600030.SH"]``.
            indicators: 指标名称列表，
                如 ``["open", "close"]``.
            starttime: 起始时间，
                如 ``"2026-06-02 09:30:00"``.
            endtime: 结束时间，
                如 ``"2026-06-02 09:35:00"``.
            interval: K 线周期（默认 ``"1"`` 即1分钟）.

        Returns:
            以 ``tables`` 为键的原始 API 响应字典.
        """
        data = {
            "codes": ",".join(codes),
            "indicators": ",".join(indicators),
            "starttime": starttime,
            "endtime": endtime,
            "functionpara": {
                "Fill": "Original",
                "Interval": interval,
            },
        }
        return self._request(
            "/api/v1/high_frequency", data
        )

    # ------------------------------------------------------------------
    # 历史行情（日 K 线）
    # ------------------------------------------------------------------

    def get_history_quotation(
        self,
        codes: list[str],
        indicators: list[str],
        startdate: str,
        enddate: str,
        interval: str = "D",
    ) -> dict:
        """获取历史日（或周/月）K 线数据.

        Args:
            codes: 证券代码列表，
                如 ``["300033.SZ"]``.
            indicators: 指标名称列表，
                如 ``["open", "close", "volume"]``.
            startdate: 起始日期，如 ``"2026-05-26"``.
            enddate: 结束日期，如 ``"2026-06-02"``.
            interval: ``"D"``（日）、``"W"``、``"M"`` 等.

        Returns:
            以 ``tables`` 为键的原始 API 响应字典.
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
    # 交易日历
    # ------------------------------------------------------------------

    def get_trade_dates(
        self,
        startdate: str,
        enddate: str,
        marketcode: str = "212001",
    ) -> list[str]:
        """获取指定市场的交易日列表.

        Args:
            startdate: 起始日期，如 ``"2026-06-01"``.
            enddate: 结束日期，如 ``"2026-06-03"``.
            marketcode: 交易所代码
                （默认 ``"212001"`` 上交所）.

        Returns:
            ``"YYYY-MM-DD"`` 格式的日期字符串列表.
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
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_table_rows(body: dict) -> list[dict]:
        """从 data_pool / 行情响应中提取行数据.

        API 返回列式数组格式：``tables[0]["table"]`` 中每个
        字段对应一个值数组，需要按索引转置为行字典列表。

        Args:
            body: 完整的 API 响应字典.

        Returns:
            行字典列表，若无数据则返回空列表.
        """
        tables = body.get("tables", [])
        if not tables:
            return []
        table = tables[0].get("table", {})
        if not table:
            return []

        # 先尝试 table_data 行式格式（兼容旧版）
        rows = table.get("table_data")
        if isinstance(rows, list) and rows:
            return rows

        # 列式数组格式：将每列按索引转置为行字典
        col_names = list(table.keys())
        col_values = [table[k] for k in col_names]
        if not col_values:
            return []
        n_rows = len(col_values[0])
        return [
            {col_names[j]: col_values[j][i]
             for j in range(len(col_names))}
            for i in range(n_rows)
        ]

    @staticmethod
    def _extract_date_list(body: dict) -> list[str]:
        """从 get_trade_dates 响应中提取日期字符串.

        Args:
            body: 完整的 API 响应字典.

        Returns:
            日期字符串列表.
        """
        tables = body.get("tables", [])

        # get_trade_dates 返回 {"time": [...]}，而非列表
        if isinstance(tables, dict):
            dates = tables.get("time", [])
            if isinstance(dates, list):
                return dates
            return []

        # 兼容其他接口的 tables 列表格式
        if not tables:
            return []
        table = tables[0].get("table", {})
        rows = table.get("table_data", [])
        if not rows:
            return []
        dates: list[str] = []
        for row in rows:
            for val in row.values():
                if isinstance(val, str) and val.strip():
                    dates.append(val.strip())
                    break
        return dates
