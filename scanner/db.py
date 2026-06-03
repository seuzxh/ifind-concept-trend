"""概念板块强势扫描系统的 SQLite 数据库持久化层.

提供 ``Database`` 类，管理全部 SQLite 操作，包括
表创建、upsert 及查询概念人气、板块-个股关系、
K 线数据和扫描结果。
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from scanner.models import (
    BoardStock,
    ConceptPopularity,
    DailyKline,
    KlineBar,
)

logger = logging.getLogger(__name__)

_DDL_STATEMENTS = [
    # 1. 概念人气表
    """CREATE TABLE IF NOT EXISTS concept_popularity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        popularity REAL,
        popularity_change_rate REAL,
        stat_period TEXT NOT NULL DEFAULT '近一周',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_cp_date
        ON concept_popularity(trade_date)""",
    """CREATE INDEX IF NOT EXISTS idx_cp_concept
        ON concept_popularity(concept_name)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_cp_date_concept
        ON concept_popularity(
            trade_date, concept_name, stat_period
        )""",
    # 2. 板块-个股关系表
    """CREATE TABLE IF NOT EXISTS board_stock_relation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        period_start_date TEXT,
        change_ratio REAL,
        stat_period TEXT NOT NULL DEFAULT '近一周',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_bsr_date
        ON board_stock_relation(trade_date)""",
    """CREATE INDEX IF NOT EXISTS idx_bsr_concept
        ON board_stock_relation(concept_name)""",
    """CREATE INDEX IF NOT EXISTS idx_bsr_stock
        ON board_stock_relation(stock_code)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_bsr_unique
        ON board_stock_relation(
            trade_date, concept_name,
            stock_code, stat_period
        )""",
    # 3. 日 K 线表
    """CREATE TABLE IF NOT EXISTS kline_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        amount REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_kd_stock_date
        ON kline_daily(stock_code, trade_date)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_kd_unique
        ON kline_daily(stock_code, trade_date)""",
    # 4. 1 分钟 K 线表
    """CREATE TABLE IF NOT EXISTS kline_1min (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        bar_time TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        amount REAL,
        change_ratio REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_k1m_stock_date
        ON kline_1min(stock_code, trade_date)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_k1m_bar
        ON kline_1min(stock_code, trade_date, bar_time)""",
    # 5. 个股每日扫描结果表
    """CREATE TABLE IF NOT EXISTS stock_daily_scan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        concept_names TEXT,
        pre_close REAL,
        open_price REAL,
        current_price REAL,
        change_ratio REAL,
        body_change_ratio REAL,
        total_amount REAL,
        total_volume REAL,
        vol_ratio REAL,
        score REAL,
        is_strong INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_sds_date
        ON stock_daily_scan(trade_date)""",
    """CREATE INDEX IF NOT EXISTS idx_sds_score
        ON stock_daily_scan(trade_date, score DESC)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_sds_unique
        ON stock_daily_scan(trade_date, stock_code)""",
    # 6. 板块每日扫描结果表
    """CREATE TABLE IF NOT EXISTS board_daily_scan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        stock_count INTEGER,
        strong_count INTEGER,
        strong_ratio REAL,
        avg_score REAL,
        board_score REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_bds_date
        ON board_daily_scan(trade_date)""",
    """CREATE INDEX IF NOT EXISTS idx_bds_score
        ON board_daily_scan(trade_date, board_score DESC)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_bds_unique
        ON board_daily_scan(trade_date, concept_name)""",
]


class Database:
    """概念板块强势扫描系统的 SQLite 数据库管理器.

    管理表创建、连接生命周期以及六张应用表的全部
    增删改查操作.

    Attributes:
        db_path: SQLite 数据库文件的文件系统路径.
    """

    def __init__(self, db_path: Path) -> None:
        """初始化数据库管理器.

        若 *db_path* 的父目录不存在则自动创建.

        Args:
            db_path: SQLite 数据库文件路径.
        """
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def init_db(self) -> None:
        """若表和索引不存在则创建."""
        conn = self._get_conn()
        for stmt in _DDL_STATEMENTS:
            conn.execute(stmt)
        conn.commit()
        logger.info("Database schema initialised.")

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """返回当前连接，若不存在则创建.

        Returns:
            设置了 ``row_factory = sqlite3.Row`` 的
            ``sqlite3.Connection`` 实例.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """若数据库连接处于打开状态则关闭."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # 概念人气（p03797）
    # ------------------------------------------------------------------

    def upsert_concept_popularity(
        self,
        records: list[ConceptPopularity],
        stat_period: str = "近一周",
    ) -> int:
        """插入或替换概念人气记录.

        Args:
            records: ``ConceptPopularity`` 数据类实例列表.
            stat_period: 统计周期标签.

        Returns:
            插入或替换的行数.
        """
        if not records:
            return 0
        conn = self._get_conn()
        count = 0
        for rec in records:
            conn.execute(
                """INSERT OR REPLACE INTO concept_popularity
                   (trade_date, concept_name, popularity,
                    popularity_change_rate, stat_period)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    rec.trade_date,
                    rec.concept_name,
                    rec.popularity,
                    rec.popularity_change_rate,
                    stat_period,
                ),
            )
            count += 1
        conn.commit()
        logger.info(
            "Upserted %d concept popularity records.", count,
        )
        return count

    def get_hot_concepts(
        self,
        trade_date: str,
        limit: int = 20,
    ) -> list[dict]:
        """返回指定日期按人气值排名前 N 的概念.

        Args:
            trade_date: 交易日期字符串.
            limit: 最大返回条数.

        Returns:
            键名与列名对应的字典列表.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT concept_name, popularity,
                      popularity_change_rate
               FROM concept_popularity
               WHERE trade_date = ?
               ORDER BY popularity DESC
               LIMIT ?""",
            (trade_date, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 板块-个股关系（p03798）
    # ------------------------------------------------------------------

    def upsert_board_stocks(
        self,
        records: list[BoardStock],
        stat_period: str = "近一周",
    ) -> int:
        """插入或替换板块-个股关系记录.

        Args:
            records: ``BoardStock`` 数据类实例列表.
            stat_period: 统计周期标签.

        Returns:
            插入或替换的行数.
        """
        if not records:
            return 0
        conn = self._get_conn()
        count = 0
        for rec in records:
            conn.execute(
                """INSERT OR REPLACE INTO board_stock_relation
                   (trade_date, concept_name, stock_code,
                    stock_name, period_start_date,
                    change_ratio, stat_period)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec.trade_date,
                    rec.concept_name,
                    rec.stock_code,
                    rec.stock_name,
                    rec.period_start,
                    rec.change_ratio,
                    stat_period,
                ),
            )
            count += 1
        conn.commit()
        logger.info(
            "Upserted %d board-stock records.", count,
        )
        return count

    def get_monitor_pool(
        self,
        trade_date: str,
    ) -> list[tuple[str, str]]:
        """返回截至指定日期最新的板块成分股去重列表.

        查询 board_stock_relation 中 *trade_date* 当天或
        之前最近一个交易日的去重 (stock_code, stock_name).

        Args:
            trade_date: 参考交易日期.

        Returns:
            (stock_code, stock_name) 元组列表.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT DISTINCT stock_code, stock_name
               FROM board_stock_relation
               WHERE trade_date = (
                   SELECT MAX(trade_date)
                   FROM board_stock_relation
                   WHERE trade_date <= ?
               )
               ORDER BY stock_code""",
            (trade_date,),
        )
        return [
            (row["stock_code"], row["stock_name"])
            for row in cursor.fetchall()
        ]

    # ------------------------------------------------------------------
    # 日 K 线
    # ------------------------------------------------------------------

    def upsert_daily_klines(
        self,
        records: list[DailyKline],
    ) -> int:
        """插入或替换日 K 线记录.

        Args:
            records: ``DailyKline`` 数据类实例列表.

        Returns:
            插入或替换的行数.
        """
        if not records:
            return 0
        conn = self._get_conn()
        count = 0
        for rec in records:
            conn.execute(
                """INSERT OR REPLACE INTO kline_daily
                   (stock_code, trade_date, open, high,
                    low, close, volume, amount)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec.stock_code,
                    rec.trade_date,
                    rec.open,
                    rec.high,
                    rec.low,
                    rec.close,
                    rec.volume,
                    rec.amount,
                ),
            )
            count += 1
        conn.commit()
        logger.info(
            "Upserted %d daily kline records.", count,
        )
        return count

    def get_prev_close(
        self,
        stock_codes: list[str],
        before_date: str,
    ) -> dict[str, float]:
        """返回指定股票在某个日期之前最近一日的收盘价.

        对 *stock_codes* 中的每只股票，查询严格早于
        *before_date* 的最近一个交易日的收盘价.

        Args:
            stock_codes: 证券代码字符串列表.
            before_date: 截止日期（不含）.

        Returns:
            证券代码 -> 收盘价的映射字典.
        """
        if not stock_codes:
            return {}
        conn = self._get_conn()
        # 动态构建占位符列表
        placeholders = ",".join("?" for _ in stock_codes)
        cursor = conn.execute(
            f"""SELECT stock_code, close
                FROM kline_daily
                WHERE trade_date = (
                    SELECT MAX(trade_date)
                    FROM kline_daily
                    WHERE trade_date < ?
                )
                AND stock_code IN ({placeholders})""",
            (before_date, *stock_codes),
        )
        return {
            row["stock_code"]: row["close"]
            for row in cursor.fetchall()
        }

    # ------------------------------------------------------------------
    # 1 分钟 K 线
    # ------------------------------------------------------------------

    def upsert_kline_1min(
        self,
        records: list[KlineBar],
    ) -> int:
        """插入或替换 1 分钟 K 线记录.

        Args:
            records: ``KlineBar`` 数据类实例列表.

        Returns:
            插入或替换的行数.
        """
        if not records:
            return 0
        conn = self._get_conn()
        count = 0
        for rec in records:
            conn.execute(
                """INSERT OR REPLACE INTO kline_1min
                   (stock_code, trade_date, bar_time,
                    open, high, low, close,
                    volume, amount, change_ratio)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec.stock_code,
                    rec.trade_date,
                    rec.bar_time,
                    rec.open,
                    rec.high,
                    rec.low,
                    rec.close,
                    rec.volume,
                    rec.amount,
                    rec.change_ratio,
                ),
            )
            count += 1
        conn.commit()
        logger.info(
            "Upserted %d 1-min kline records.", count,
        )
        return count

    # ------------------------------------------------------------------
    # 扫描结果 — 个股
    # ------------------------------------------------------------------

    def save_stock_scan_results(
        self,
        trade_date: str,
        results: list[dict],
    ) -> int:
        """插入或替换每日个股扫描结果.

        Args:
            trade_date: 交易日期字符串.
            results: 字典列表，键名对应 ``stock_daily_scan``
                表列（不含 ``id``、``trade_date``、
                ``created_at``）.

        Returns:
            插入或替换的行数.
        """
        if not results:
            return 0
        conn = self._get_conn()
        count = 0
        for row in results:
            conn.execute(
                """INSERT OR REPLACE INTO stock_daily_scan
                   (trade_date, stock_code, stock_name,
                    concept_names, pre_close, open_price,
                    current_price, change_ratio,
                    body_change_ratio, total_amount,
                    total_volume, vol_ratio, score,
                    is_strong)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?)""",
                (
                    trade_date,
                    row.get("stock_code"),
                    row.get("stock_name"),
                    row.get("concept_names"),
                    row.get("pre_close"),
                    row.get("open_price"),
                    row.get("current_price"),
                    row.get("change_ratio"),
                    row.get("body_change_ratio"),
                    row.get("total_amount"),
                    row.get("total_volume"),
                    row.get("vol_ratio"),
                    row.get("score"),
                    row.get("is_strong", 0),
                ),
            )
            count += 1
        conn.commit()
        logger.info(
            "Saved %d stock scan results for %s.",
            count, trade_date,
        )
        return count

    def get_top_stocks(
        self,
        trade_date: str,
        limit: int = 10,
    ) -> list[dict]:
        """返回指定日期评分最高的个股.

        Args:
            trade_date: 交易日期字符串.
            limit: 最大返回条数.

        Returns:
            键名与列名对应的字典列表.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT stock_code, stock_name,
                      concept_names, pre_close,
                      open_price, current_price,
                      change_ratio, body_change_ratio,
                      total_amount, total_volume,
                      vol_ratio, score, is_strong
               FROM stock_daily_scan
               WHERE trade_date = ?
               ORDER BY score DESC
               LIMIT ?""",
            (trade_date, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 扫描结果 — 板块
    # ------------------------------------------------------------------

    def save_board_scan_results(
        self,
        trade_date: str,
        results: list[dict],
    ) -> int:
        """插入或替换每日板块扫描结果.

        Args:
            trade_date: 交易日期字符串.
            results: 字典列表，键名对应 ``board_daily_scan``
                表列（不含 ``id``、``trade_date``、
                ``created_at``）。

        Returns:
            插入或替换的行数.
        """
        if not results:
            return 0
        conn = self._get_conn()
        count = 0
        for row in results:
            conn.execute(
                """INSERT OR REPLACE INTO board_daily_scan
                   (trade_date, concept_name, stock_count,
                    strong_count, strong_ratio,
                    avg_score, board_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    trade_date,
                    row.get("concept_name"),
                    row.get("stock_count"),
                    row.get("strong_count"),
                    row.get("strong_ratio"),
                    row.get("avg_score"),
                    row.get("board_score"),
                ),
            )
            count += 1
        conn.commit()
        logger.info(
            "Saved %d board scan results for %s.",
            count, trade_date,
        )
        return count

    def get_top_boards(
        self,
        trade_date: str,
        limit: int = 5,
    ) -> list[dict]:
        """返回指定日期评分最高的板块.

        Args:
            trade_date: 交易日期字符串.
            limit: 最大返回条数.

        Returns:
            键名与列名对应的字典列表.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT concept_name, stock_count,
                      strong_count, strong_ratio,
                      avg_score, board_score
               FROM board_daily_scan
               WHERE trade_date = ?
               ORDER BY board_score DESC
               LIMIT ?""",
            (trade_date, limit),
        )
        return [dict(row) for row in cursor.fetchall()]
