"""数据同步编排模块.

提供 ``DataSync`` 类，负责每日数据同步和盘中按需数据
获取。所有 API 调用前会先查询 SQLite 判断数据是否已存在，
避免重复下载。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from scanner.client import IfindClient
from scanner.db import Database
from scanner.models import (
    BoardStock,
    ConceptPopularity,
    DailyKline,
    KlineBar,
)

logger = logging.getLogger(__name__)

# API 批量请求每批最大股票数.
_BATCH_SIZE = 50


class DataSync:
    """数据同步编排器.

    管理每日人气数据同步和盘中 K 线数据获取，
    所有请求前先查 SQLite 避免重复下载.

    Attributes:
        client: ifind API 客户端.
        db: 数据库管理器.
    """

    def __init__(
        self,
        client: IfindClient,
        db: Database,
    ) -> None:
        """初始化同步编排器.

        Args:
            client: ifind API 客户端实例.
            db: 数据库管理器实例.
        """
        self.client = client
        self.db = db

    # ------------------------------------------------------------------
    # 每日同步（人气 + 成分股）
    # ------------------------------------------------------------------

    def sync_concept_popularity(
        self, date_ymd: str
    ) -> list[ConceptPopularity]:
        """同步概念人气数据.

        Args:
            date_ymd: 日期字符串（YYYYMMDD）.

        Returns:
            概念人气记录列表.
        """
        date_display = _normalize_date(date_ymd)
        logger.info(
            "Syncing concept popularity for %s.",
            date_display,
        )
        rows = self.client.get_concept_popularity(date_ymd)
        records = []
        for row in rows:
            records.append(ConceptPopularity(
                concept_name=str(
                    row.get("p03793_f001", "")
                ),
                trade_date=date_display,
                popularity=float(
                    row.get("p03793_f009", 0)
                ),
                popularity_change_rate=float(
                    row.get("p03793_f010", 0)
                ),
            ))
        count = self.db.upsert_concept_popularity(records)
        logger.info(
            "Synced %d concept popularity records.", count,
        )
        return records

    def sync_board_stocks(
        self,
        date_ymd: str,
        concept_names: list[str],
        top_n: int = 30,
    ) -> list[BoardStock]:
        """同步板块成分股数据.

        Args:
            date_ymd: 日期字符串（YYYYMMDD）.
            concept_names: 概念板块名称列表.
            top_n: 每个板块取涨跌幅前 N 只股票.

        Returns:
            板块成分股记录列表.
        """
        date_display = _normalize_date(date_ymd)
        logger.info(
            "Syncing board stocks for %d concepts.",
            len(concept_names),
        )
        all_records: list[BoardStock] = []
        for name in concept_names:
            try:
                rows = self.client.get_board_stocks(
                    date_ymd, name,
                )
            except RuntimeError:
                logger.warning(
                    "Failed to fetch board stocks: %s",
                    name,
                )
                continue
            stocks: list[BoardStock] = []
            for row in rows:
                stock_name = str(row.get("jydm_mc", ""))
                if "ST" in stock_name.upper():
                    continue
                stocks.append(BoardStock(
                    stock_code=str(row.get("jydm", "")),
                    stock_name=stock_name,
                    trade_date=date_display,
                    change_ratio=float(
                        row.get("p03794_f012", 0)
                    ),
                    period_start=str(
                        row.get("p03794_f016", "")
                    ),
                    concept_name=name,
                ))
            stocks.sort(
                key=lambda s: s.change_ratio, reverse=True,
            )
            all_records.extend(stocks[:top_n])
            time.sleep(0.1)
        count = self.db.upsert_board_stocks(all_records)
        logger.info(
            "Synced %d board stock records.", count,
        )
        return all_records

    def filter_hot_concepts(
        self,
        concepts: list[ConceptPopularity],
        top_k: int = 20,
    ) -> list[str]:
        """按热度 Top K + 变化率 Top K 去重筛选热门板块.

        Args:
            concepts: 概念人气记录列表.
            top_k: 每个维度取前 K 个.

        Returns:
            去重后的概念板块名称列表.
        """
        by_pop = sorted(
            concepts,
            key=lambda c: c.popularity,
            reverse=True,
        )[:top_k]
        by_chg = sorted(
            concepts,
            key=lambda c: c.popularity_change_rate,
            reverse=True,
        )[:top_k]
        seen: set[str] = set()
        result: list[str] = []
        for c in by_pop + by_chg:
            if c.concept_name not in seen:
                seen.add(c.concept_name)
                result.append(c.concept_name)
        return result

    # ------------------------------------------------------------------
    # 日 K 线（含预查）
    # ------------------------------------------------------------------

    def fetch_daily_klines(
        self,
        stock_codes: list[str],
        date_display: str,
        force: bool = False,
    ) -> list[DailyKline]:
        """获取日 K 线数据，仅对缺失数据的股票请求 API.

        Args:
            stock_codes: 股票代码列表.
            date_display: 日期字符串（YYYY-MM-DD）.
            force: 是否强制刷新（跳过预查）.

        Returns:
            日 K 线记录列表.
        """
        if force:
            missing = stock_codes
        else:
            existing = self.db.find_stocks_with_daily(
                date_display, stock_codes,
            )
            missing = [
                c for c in stock_codes
                if c not in existing
            ]
        if existing := (
            set(stock_codes) - set(missing)
            if not force else set()
        ):
            logger.info(
                "Skip %d stocks (daily kline exists).",
                len(existing),
            )
        if not missing:
            logger.info(
                "All daily klines exist for %s.",
                date_display,
            )
            return []
        logger.info(
            "Fetching daily klines for %d/%d stocks.",
            len(missing), len(stock_codes),
        )
        end_dt = datetime.strptime(
            date_display, "%Y-%m-%d"
        )
        start_dt = end_dt - timedelta(days=10)
        start_date = start_dt.strftime("%Y-%m-%d")

        all_records: list[DailyKline] = []
        for batch in _chunk(missing, _BATCH_SIZE):
            try:
                body = self.client.get_history_quotation(
                    codes=batch,
                    indicators=[
                        "open", "close", "high",
                        "low", "volume", "amount",
                    ],
                    startdate=start_date,
                    enddate=date_display,
                    interval="D",
                )
                records = _parse_daily_klines(body)
                all_records.extend(records)
            except RuntimeError:
                logger.warning(
                    "Failed to fetch daily klines batch.",
                )
            time.sleep(0.1)
        count = self.db.upsert_daily_klines(all_records)
        logger.info(
            "Fetched and saved %d daily kline records.",
            count,
        )
        return all_records

    # ------------------------------------------------------------------
    # 1 分钟 K 线（含预查）
    # ------------------------------------------------------------------

    def fetch_1min_klines(
        self,
        stock_codes: list[str],
        date_display: str,
        force: bool = False,
    ) -> list[KlineBar]:
        """获取 1 分钟 K 线数据，仅对缺失数据的股票请求 API.

        Args:
            stock_codes: 股票代码列表.
            date_display: 日期字符串（YYYY-MM-DD）.
            force: 是否强制刷新（跳过预查）.

        Returns:
            1 分钟 K 线记录列表.
        """
        if force:
            missing = stock_codes
        else:
            existing = self.db.find_stocks_with_1min(
                date_display, stock_codes,
            )
            missing = [
                c for c in stock_codes
                if c not in existing
            ]
        if existing := (
            set(stock_codes) - set(missing)
            if not force else set()
        ):
            logger.info(
                "Skip %d stocks (1min kline exists).",
                len(existing),
            )
        if not missing:
            logger.info(
                "All 1min klines exist for %s.",
                date_display,
            )
            return []
        logger.info(
            "Fetching 1min klines for %d/%d stocks.",
            len(missing), len(stock_codes),
        )
        starttime = f"{date_display} 09:30:00"
        endtime = f"{date_display} 09:35:00"

        all_records: list[KlineBar] = []
        for batch in _chunk(missing, _BATCH_SIZE):
            try:
                body = self.client.get_high_frequency(
                    codes=batch,
                    indicators=[
                        "open", "high", "low", "close",
                        "volume", "amount",
                        "changeRatio", "LB",
                    ],
                    starttime=starttime,
                    endtime=endtime,
                    interval="1",
                    calculate={"LB": "5"},
                )
                records = _parse_1min_klines(
                    body, date_display,
                )
                all_records.extend(records)
            except RuntimeError:
                logger.warning(
                    "Failed to fetch 1min klines batch.",
                )
            time.sleep(0.1)
        count = self.db.upsert_kline_1min(all_records)
        logger.info(
            "Fetched and saved %d 1min kline records.",
            count,
        )
        return all_records


# ======================================================================
# 模块级辅助函数
# ======================================================================

def _normalize_date(date_ymd: str) -> str:
    """将 YYYYMMDD 转为 YYYY-MM-DD."""
    if len(date_ymd) == 8 and date_ymd.isdigit():
        return (
            f"{date_ymd[:4]}-{date_ymd[4:6]}"
            f"-{date_ymd[6:8]}"
        )
    return date_ymd


def _chunk(items: list, size: int) -> list[list]:
    """将列表按指定大小分块."""
    return [
        items[i:i + size]
        for i in range(0, len(items), size)
    ]


def _parse_daily_klines(body: dict) -> list[DailyKline]:
    """解析日 K 线 API 响应为 DailyKline 列表."""
    records: list[DailyKline] = []
    tables = body.get("tables", [])
    for tbl_entry in tables:
        if not isinstance(tbl_entry, dict):
            continue
        code = tbl_entry.get("thscode", "")
        times = tbl_entry.get("time", [])
        table = tbl_entry.get("table", {})
        if not table:
            continue
        col_names = list(table.keys())
        col_values = [table[k] for k in col_names]
        n = len(col_values[0]) if col_values else 0
        for j in range(n):
            row = {
                col_names[k]: col_values[k][j]
                for k in range(len(col_names))
            }
            trade_date = (
                times[j] if j < len(times) else ""
            )
            if not trade_date:
                continue
            records.append(DailyKline(
                stock_code=code,
                trade_date=trade_date,
                open=float(row.get("open") or 0),
                high=float(row.get("high") or 0),
                low=float(row.get("low") or 0),
                close=float(row.get("close") or 0),
                volume=float(row.get("volume") or 0),
                amount=float(row.get("amount") or 0),
            ))
    return records


def _parse_1min_klines(
    body: dict, date_display: str,
) -> list[KlineBar]:
    """解析 1 分钟 K 线 API 响应为 KlineBar 列表."""
    records: list[KlineBar] = []
    tables = body.get("tables", [])
    for tbl_entry in tables:
        if not isinstance(tbl_entry, dict):
            continue
        code = tbl_entry.get("thscode", "")
        times = tbl_entry.get("time", [])
        table = tbl_entry.get("table", {})
        if not table:
            continue
        col_names = list(table.keys())
        col_values = [table[k] for k in col_names]
        n = len(col_values[0]) if col_values else 0
        for j in range(n):
            row = {
                col_names[k]: col_values[k][j]
                for k in range(len(col_names))
            }
            bar_time = (
                times[j] if j < len(times) else ""
            )
            change_ratio = row.get("changeRatio")
            records.append(KlineBar(
                stock_code=code,
                trade_date=date_display,
                bar_time=bar_time,
                open=float(row.get("open") or 0),
                high=float(row.get("high") or 0),
                low=float(row.get("low") or 0),
                close=float(row.get("close") or 0),
                volume=float(row.get("volume") or 0),
                amount=float(row.get("amount") or 0),
                change_ratio=(
                    float(change_ratio)
                    if change_ratio is not None
                    else None
                ),
            ))
    return records
