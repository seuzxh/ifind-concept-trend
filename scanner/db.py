"""Database layer for persisting scan results to SQLite.

Provides the ``Database`` class that manages all SQLite operations
including table creation, upserts, and queries for concept
popularity, board-stock relations, K-line data, and scan results.
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
    # 1. concept_popularity
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
    # 2. board_stock_relation
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
    # 3. kline_daily
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
    # 4. kline_1min
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
    # 5. stock_daily_scan
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
    # 6. board_daily_scan
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
    """SQLite database manager for concept-trend-scanner.

    Manages table creation, connection lifecycle, and all
    CRUD operations for the six application tables.

    Attributes:
        db_path: Filesystem path to the SQLite database file.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialise the database manager.

        Creates the parent directory of *db_path* if it does not
        already exist.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def init_db(self) -> None:
        """Create all tables and indexes if they do not exist."""
        conn = self._get_conn()
        for stmt in _DDL_STATEMENTS:
            conn.execute(stmt)
        conn.commit()
        logger.info("Database schema initialised.")

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """Return the current connection, creating one if needed.

        Returns:
            A ``sqlite3.Connection`` with ``row_factory`` set to
            ``sqlite3.Row``.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection if it is open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Concept popularity (p03797)
    # ------------------------------------------------------------------

    def upsert_concept_popularity(
        self,
        records: list[ConceptPopularity],
        stat_period: str = "近一周",
    ) -> int:
        """Insert or replace concept popularity records.

        Args:
            records: List of ``ConceptPopularity`` dataclass
                instances.
            stat_period: Statistical period label.

        Returns:
            Number of rows upserted.
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
        """Return the top concepts by popularity for a date.

        Args:
            trade_date: Trading date string.
            limit: Maximum number of results.

        Returns:
            List of dicts with keys matching column names.
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
    # Board-stock relation (p03798)
    # ------------------------------------------------------------------

    def upsert_board_stocks(
        self,
        records: list[BoardStock],
        stat_period: str = "近一周",
    ) -> int:
        """Insert or replace board-stock relation records.

        Args:
            records: List of ``BoardStock`` dataclass instances.
            stat_period: Statistical period label.

        Returns:
            Number of rows upserted.
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
        """Return unique (stock_code, stock_name) from the latest
        board_stock_relation data on or before *trade_date*.

        Args:
            trade_date: Reference trading date.

        Returns:
            List of (stock_code, stock_name) tuples.
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
    # Daily K-line
    # ------------------------------------------------------------------

    def upsert_daily_klines(
        self,
        records: list[DailyKline],
    ) -> int:
        """Insert or replace daily K-line records.

        Args:
            records: List of ``DailyKline`` dataclass instances.

        Returns:
            Number of rows upserted.
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
        """Return the most recent close price before a date.

        For each stock in *stock_codes*, looks up the close price
        on the most recent trading day strictly before
        *before_date*.

        Args:
            stock_codes: List of stock code strings.
            before_date: Cutoff date (exclusive).

        Returns:
            Dict mapping stock_code to close price.
        """
        if not stock_codes:
            return {}
        conn = self._get_conn()
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
    # 1-min K-line
    # ------------------------------------------------------------------

    def upsert_kline_1min(
        self,
        records: list[KlineBar],
    ) -> int:
        """Insert or replace 1-minute K-line records.

        Args:
            records: List of ``KlineBar`` dataclass instances.

        Returns:
            Number of rows upserted.
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
    # Scan results — stocks
    # ------------------------------------------------------------------

    def save_stock_scan_results(
        self,
        trade_date: str,
        results: list[dict],
    ) -> int:
        """Insert or replace daily stock scan results.

        Args:
            trade_date: Trading date string.
            results: List of dicts with keys matching
                ``stock_daily_scan`` columns (minus ``id``,
                ``trade_date``, ``created_at``).

        Returns:
            Number of rows upserted.
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
        """Return the top-scoring stocks for a date.

        Args:
            trade_date: Trading date string.
            limit: Maximum number of results.

        Returns:
            List of dicts with keys matching column names.
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
    # Scan results — boards
    # ------------------------------------------------------------------

    def save_board_scan_results(
        self,
        trade_date: str,
        results: list[dict],
    ) -> int:
        """Insert or replace daily board scan results.

        Args:
            trade_date: Trading date string.
            results: List of dicts with keys matching
                ``board_daily_scan`` columns (minus ``id``,
                ``trade_date``, ``created_at``).

        Returns:
            Number of rows upserted.
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
        """Return the top-scoring boards for a date.

        Args:
            trade_date: Trading date string.
            limit: Maximum number of results.

        Returns:
            List of dicts with keys matching column names.
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
