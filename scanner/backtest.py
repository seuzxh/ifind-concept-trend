"""回溯模拟测试模块.

提供 ``BacktestRunner`` 类，对指定日期范围逐日执行
完整扫描流程，保存推送报告和执行摘要用于回溯分析。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from scanner.notifier import Notifier
from scanner.scheduler import Scanner

logger = logging.getLogger(__name__)


class BacktestRunner:
    """回溯模拟运行器.

    逐日遍历日期范围，对交易日执行完整扫描流程，
    保存推送报告到文件（不实际推送 webhook）。

    Attributes:
        scanner: 扫描调度器.
        reports_dir: 报告保存目录.
    """

    def __init__(
        self,
        scanner: Scanner,
        reports_dir: Path,
    ) -> None:
        """初始化回溯运行器.

        Args:
            scanner: 扫描调度器实例.
            reports_dir: 报告保存目录路径.
        """
        self.scanner = scanner
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        start_ymd: str,
        end_ymd: str,
        force: bool = False,
    ) -> list[dict]:
        """执行回溯模拟.

        Args:
            start_ymd: 起始日期（YYYYMMDD）.
            end_ymd: 结束日期（YYYYMMDD）.
            force: 是否强制刷新数据.

        Returns:
            每日执行结果字典列表.
        """
        start_dt = datetime.strptime(start_ymd, "%Y%m%d")
        end_dt = datetime.strptime(end_ymd, "%Y%m%d")

        logger.info(
            "Backtest started: %s ~ %s.",
            start_ymd, end_ymd,
        )

        # 批量获取交易日列表
        trade_dates = self._get_trade_dates(
            start_ymd, end_ymd,
        )

        results: list[dict] = []
        current = start_dt
        while current <= end_dt:
            date_ymd = current.strftime("%Y%m%d")
            date_display = current.strftime("%Y-%m-%d")

            if date_ymd not in trade_dates:
                logger.info(
                    "%s skipped (non-trade day).",
                    date_display,
                )
                results.append({
                    "date": date_display,
                    "status": "skipped",
                    "reason": "non-trade day",
                })
                current += timedelta(days=1)
                continue

            result = self._run_single_day(
                date_ymd, date_display, force,
            )
            results.append(result)
            current += timedelta(days=1)

        # 生成摘要
        self._save_summary(results)
        logger.info(
            "Backtest completed: %d dates, "
            "%d trade days processed.",
            len(results),
            sum(
                1 for r in results
                if r["status"] == "success"
            ),
        )
        return results

    def _get_trade_dates(
        self,
        start_ymd: str,
        end_ymd: str,
    ) -> set[str]:
        """获取日期范围内的交易日集合.

        Args:
            start_ymd: 起始日期.
            end_ymd: 结束日期.

        Returns:
            交易日日期字符串集合（YYYYMMDD）.
        """
        try:
            date_list = self.scanner.client.get_trade_dates(
                start_ymd, end_ymd,
            )
            normalized = set()
            for d in date_list:
                if isinstance(d, str):
                    clean = (
                        d.replace("-", "")
                        .replace("/", "")
                    )
                    normalized.add(clean)
            return normalized
        except RuntimeError:
            logger.warning(
                "Failed to fetch trade dates, "
                "falling back to weekday check.",
            )
            dates = set()
            start = datetime.strptime(start_ymd, "%Y%m%d")
            end = datetime.strptime(end_ymd, "%Y%m%d")
            cur = start
            while cur <= end:
                if cur.weekday() < 5:
                    dates.add(cur.strftime("%Y%m%d"))
                cur += timedelta(days=1)
            return dates

    def _run_single_day(
        self,
        date_ymd: str,
        date_display: str,
        force: bool,
    ) -> dict:
        """执行单个交易日的回溯.

        Args:
            date_ymd: 日期 YYYYMMDD.
            date_display: 日期 YYYY-MM-DD.
            force: 是否强制刷新.

        Returns:
            执行结果字典.
        """
        logger.info(
            "Processing %s ...", date_display,
        )
        try:
            stock_results, board_results = (
                self.scanner.run_full_scan(
                    date_ymd, force=force,
                )
            )

            # 生成报告（不推送）
            report = ""
            if stock_results or board_results:
                report = self.scanner.notifier._build_report(
                    date_display,
                    stock_results,
                    board_results,
                )

            # 保存报告文件
            if report:
                report_path = (
                    self.reports_dir / f"{date_display}.md"
                )
                report_path.write_text(
                    report, encoding="utf-8",
                )
                logger.info(
                    "Report saved: %s", report_path,
                )

            strong_count = sum(
                1 for s in stock_results
                if s.get("is_strong")
            )

            return {
                "date": date_display,
                "status": "success",
                "pool_count": len(stock_results),
                "board_count": len(board_results),
                "strong_count": strong_count,
                "top_board": (
                    board_results[0]["concept_name"]
                    if board_results else ""
                ),
                "top_stock": (
                    f"{stock_results[0]['stock_name']}"
                    f"({stock_results[0]['stock_code']})"
                    if stock_results else ""
                ),
                "top_score": (
                    stock_results[0]["score"]
                    if stock_results else 0
                ),
                "report_saved": bool(report),
            }
        except Exception as exc:
            logger.error(
                "Failed for %s: %s", date_display, exc,
            )
            return {
                "date": date_display,
                "status": "error",
                "reason": str(exc),
            }

    def _save_summary(
        self, results: list[dict],
    ) -> None:
        """保存回溯摘要文件.

        Args:
            results: 每日执行结果列表.
        """
        summary_path = (
            self.reports_dir / "backtest_summary.txt"
        )

        success = [
            r for r in results if r["status"] == "success"
        ]
        skipped = [
            r for r in results
            if r["status"] == "skipped"
        ]
        errors = [
            r for r in results if r["status"] == "error"
        ]

        lines = [
            "=" * 60,
            "回溯模拟摘要",
            "=" * 60,
            f"日期范围: {results[0]['date']} ~ "
            f"{results[-1]['date']}",
            f"总天数: {len(results)}",
            f"交易日: {len(success)}",
            f"非交易日: {len(skipped)}",
            f"失败: {len(errors)}",
            "=" * 60,
            "",
            f"{'日期':<14s} {'状态':<8s} "
            f"{'股池':>6s} {'板块':>4s} "
            f"{'强势':>4s} {'TOP板块':<14s} "
            f"{'TOP个股':<16s} {'得分':>6s}",
            "-" * 80,
        ]

        for r in results:
            if r["status"] == "skipped":
                lines.append(
                    f"{r['date']:<14s} {'跳过':<8s} "
                    f"{'---':>6s} {'---':>4s} "
                    f"{'---':>4s} {'---':<14s} "
                    f"{'---':<16s} {'---':>6s}"
                )
            elif r["status"] == "error":
                lines.append(
                    f"{r['date']:<14s} {'错误':<8s} "
                    f"{r.get('reason', '')}"
                )
            else:
                lines.append(
                    f"{r['date']:<14s} {'成功':<8s} "
                    f"{r.get('pool_count', 0):>6d} "
                    f"{r.get('board_count', 0):>4d} "
                    f"{r.get('strong_count', 0):>4d} "
                    f"{r.get('top_board', ''):<14s} "
                    f"{r.get('top_stock', ''):<16s} "
                    f"{r.get('top_score', 0):>6.2f}"
                )

        lines.append("-" * 80)
        lines.append("")

        summary_path.write_text(
            "\n".join(lines), encoding="utf-8",
        )
        logger.info(
            "Summary saved: %s", summary_path,
        )

        # 同时打印到控制台
        print("\n".join(lines))
