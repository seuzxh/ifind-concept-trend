"""扫描调度器.

提供 ``Scanner`` 类编排完整扫描流程：交易日判断 →
盘前同步 → 盘中扫描 → 推送。支持 APScheduler 定时
调度和手动触发。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler

from scanner.client import IfindClient
from scanner.config import Config
from scanner.db import Database
from scanner.notifier import Notifier
from scanner.scorer import ScoringEngine
from scanner.sync import DataSync

logger = logging.getLogger(__name__)


class Scanner:
    """扫描调度器.

    编排盘前同步、盘中扫描和推送的完整流程.
    支持 APScheduler 定时调度和手动触发.

    Attributes:
        config: 应用配置.
        client: ifind API 客户端.
        db: 数据库管理器.
        sync: 数据同步编排器.
        scorer: 评分引擎.
        notifier: 推送器.
    """

    def __init__(self, config: Config) -> None:
        """初始化扫描调度器.

        Args:
            config: 应用配置实例.
        """
        self.config = config
        self.db = Database(config.db_path)
        self.db.init_db()
        self.client = IfindClient(
            base_url=config.ifind_base_url,
            refresh_token=config.ifind_refresh_token,
        )
        self.sync = DataSync(self.client, self.db)
        self.scorer = ScoringEngine(
            self.db,
            config.scoring,
            config.board_scoring,
        )
        self.notifier = Notifier(
            config.webhook.get("url", ""),
        )

    def close(self) -> None:
        """关闭数据库连接."""
        self.db.close()

    # ------------------------------------------------------------------
    # 交易日判断
    # ------------------------------------------------------------------

    def is_trade_day(self, date_ymd: str) -> bool:
        """判断指定日期是否为交易日.

        Args:
            date_ymd: 日期字符串（YYYYMMDD）.

        Returns:
            是否为交易日.
        """
        try:
            dates = self.client.get_trade_dates(
                date_ymd, date_ymd,
            )
            return len(dates) > 0
        except RuntimeError:
            logger.warning(
                "Failed to check trade date for %s.",
                date_ymd,
            )
            # 简单的周末判断作为降级
            dt = datetime.strptime(date_ymd, "%Y%m%d")
            return dt.weekday() < 5

    # ------------------------------------------------------------------
    # 盘前同步（Task 6.1）
    # ------------------------------------------------------------------

    def run_daily_sync(
        self,
        date_ymd: str,
        top_n: int = 30,
    ) -> None:
        """执行盘前数据同步（人气 + 成分股 + 日K）.

        Args:
            date_ymd: 日期字符串（YYYYMMDD）.
            top_n: 每板块取涨跌幅前 N 只成分股.
        """
        logger.info(
            "Daily sync started for %s.", date_ymd,
        )
        # 1. 概念人气
        concepts = self.sync.sync_concept_popularity(
            date_ymd,
        )
        # 2. 筛选热门板块
        hot_names = self.sync.filter_hot_concepts(concepts)
        logger.info(
            "Hot concepts: %d boards.", len(hot_names),
        )
        # 3. 成分股
        board_stocks = self.sync.sync_board_stocks(
            date_ymd, hot_names, top_n,
        )
        stock_codes = list({
            bs.stock_code for bs in board_stocks
        })
        logger.info(
            "Monitor pool: %d stocks.", len(stock_codes),
        )
        # 4. 日 K 线（含预查）
        date_display = _to_display_date(date_ymd)
        self.sync.fetch_daily_klines(
            stock_codes, date_display,
        )
        logger.info(
            "Daily sync completed for %s.", date_ymd,
        )

    # ------------------------------------------------------------------
    # 盘中扫描（Task 6.2）
    # ------------------------------------------------------------------

    def run_intraday_scan(
        self,
        date_display: str,
        force: bool = False,
    ) -> tuple[list[dict], list[dict]]:
        """执行盘中扫描流程（预查 → 按需获取 → 评分 → 推送）.

        Args:
            date_display: 日期字符串（YYYY-MM-DD）.
            force: 是否强制刷新数据（跳过预查）.

        Returns:
            (stock_results, board_results) 元组.
        """
        logger.info(
            "Intraday scan started for %s.", date_display,
        )
        # 1. 获取观察股池
        pool = self.db.get_monitor_pool(date_display)
        if not pool:
            logger.warning(
                "No monitor pool for %s.", date_display,
            )
            return [], []
        stock_codes = [code for code, _ in pool]
        logger.info(
            "Monitor pool: %d stocks.", len(stock_codes),
        )
        # 2. 按需获取日 K 线
        self.sync.fetch_daily_klines(
            stock_codes, date_display, force=force,
        )
        # 3. 按需获取 1 分钟 K 线
        self.sync.fetch_1min_klines(
            stock_codes, date_display, force=force,
        )
        # 4. 评分
        stock_results, board_results = self.scorer.run(
            date_display,
        )
        logger.info(
            "Intraday scan completed: "
            "%d stocks, %d boards.",
            len(stock_results), len(board_results),
        )
        # 5. 推送
        if stock_results or board_results:
            self.notifier.send(
                date_display,
                stock_results,
                board_results,
            )
        return stock_results, board_results

    # ------------------------------------------------------------------
    # 完整流程（Task 6.4 手动/回溯）
    # ------------------------------------------------------------------

    def run_full_scan(
        self,
        date_ymd: str,
        force: bool = False,
    ) -> tuple[list[dict], list[dict]]:
        """执行完整扫描流程（同步 + 盘中扫描）.

        用于手动触发或历史回溯.

        Args:
            date_ymd: 日期字符串（YYYYMMDD）.
            force: 是否强制刷新数据.

        Returns:
            (stock_results, board_results) 元组.
        """
        date_display = _to_display_date(date_ymd)
        logger.info(
            "Full scan started for %s.", date_ymd,
        )
        # 1. 盘前同步
        self.run_daily_sync(date_ymd)
        # 2. 盘中扫描 + 推送
        results = self.run_intraday_scan(
            date_display, force=force,
        )
        logger.info(
            "Full scan completed for %s.", date_ymd,
        )
        return results

    # ------------------------------------------------------------------
    # 定时服务（APScheduler）
    # ------------------------------------------------------------------

    def serve(self) -> None:
        """启动 APScheduler 定时服务.

        盘前同步：交易日 9:00
        盘中扫描：交易日 9:36
        """
        sync_time = self.config.scheduler.get(
            "sync_time", "09:00",
        )
        scan_time = self.config.scheduler.get(
            "scan_time", "09:36",
        )

        scheduler = BlockingScheduler()
        scheduler.add_job(
            self._scheduled_sync,
            "cron",
            hour=int(sync_time.split(":")[0]),
            minute=int(sync_time.split(":")[1]),
            id="daily_sync",
            name="盘前同步",
        )
        scheduler.add_job(
            self._scheduled_scan,
            "cron",
            hour=int(scan_time.split(":")[0]),
            minute=int(scan_time.split(":")[1]),
            id="intraday_scan",
            name="盘中扫描",
        )
        logger.info(
            "Scheduler started: sync=%s, scan=%s.",
            sync_time, scan_time,
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")

    def _scheduled_sync(self) -> None:
        """定时盘前同步任务."""
        today = datetime.now().strftime("%Y%m%d")
        if not self.is_trade_day(today):
            logger.info(
                "%s is not a trade day, skip sync.", today,
            )
            return
        self.run_daily_sync(today)

    def _scheduled_scan(self) -> None:
        """定时盘中扫描任务."""
        today = datetime.now().strftime("%Y%m%d")
        if not self.is_trade_day(today):
            logger.info(
                "%s is not a trade day, skip scan.", today,
            )
            return
        date_display = _to_display_date(today)
        self.run_intraday_scan(date_display)


def _to_display_date(date_ymd: str) -> str:
    """将 YYYYMMDD 转为 YYYY-MM-DD."""
    return (
        f"{date_ymd[:4]}-{date_ymd[4:6]}-{date_ymd[6:8]}"
    )
