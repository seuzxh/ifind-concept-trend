"""概念板块强势扫描系统 CLI 入口.

支持三个子命令：
  - ``scan``  : 手动触发盘中扫描（支持 --date 回溯）
  - ``serve`` : 启动 APScheduler 定时服务
  - ``sync``  : 手动触发盘前数据同步
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from scanner.config import get_config
from scanner.scheduler import Scanner

__version__ = "0.2.0"


def _setup_logging() -> None:
    """配置日志格式和级别."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] "
               "%(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_env() -> None:
    """从 .env 文件加载环境变量."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if (
                line
                and not line.startswith("#")
                and "=" in line
            ):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main(argv: list[str] | None = None) -> None:
    """CLI 主入口.

    Args:
        argv: 命令行参数，默认使用 sys.argv[1:].
    """
    _load_env()
    _setup_logging()

    parser = argparse.ArgumentParser(
        prog="scanner",
        description="概念板块强势扫描系统",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{__version__}",
    )

    sub = parser.add_subparsers(
        dest="command",
        help="可用命令",
    )

    # scan 命令
    scan_parser = sub.add_parser(
        "scan",
        help="手动触发盘中扫描",
    )
    scan_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="指定日期（YYYYMMDD），默认今天",
    )
    scan_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="强制刷新数据（跳过预查）",
    )

    # serve 命令
    sub.add_parser(
        "serve",
        help="启动定时服务（盘前同步 + 盘中扫描）",
    )

    # sync 命令
    sync_parser = sub.add_parser(
        "sync",
        help="手动触发盘前数据同步",
    )
    sync_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="指定日期（YYYYMMDD），默认今天",
    )

    # backtest 命令
    bt_parser = sub.add_parser(
        "backtest",
        help="回溯模拟测试",
    )
    bt_parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="回溯起始日期（YYYYMMDD）",
    )
    bt_parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="回溯结束日期（YYYYMMDD）",
    )
    bt_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="强制刷新数据（跳过预查）",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    config = get_config()
    scanner = Scanner(config)

    try:
        if args.command == "scan":
            date_ymd = args.date or _today_ymd()
            _cmd_scan(scanner, date_ymd, args.force)
        elif args.command == "serve":
            _cmd_serve(scanner)
        elif args.command == "sync":
            date_ymd = args.date or _today_ymd()
            _cmd_sync(scanner, date_ymd)
        elif args.command == "backtest":
            _cmd_backtest(
                scanner, args.start, args.end, args.force,
            )
    finally:
        scanner.close()


def _cmd_scan(
    scanner: Scanner,
    date_ymd: str,
    force: bool,
) -> None:
    """执行 scan 命令.

    Args:
        scanner: 扫描调度器.
        date_ymd: 日期字符串（YYYYMMDD）.
        force: 是否强制刷新.
    """
    from datetime import datetime

    logging.info(
        "Manual scan for %s (force=%s).",
        date_ymd, force,
    )
    stock_results, board_results = scanner.run_full_scan(
        date_ymd, force=force,
    )
    if not stock_results:
        print(f"No results for {date_ymd}.")
        return

    print(f"\n=== 扫描结果 {date_ymd} ===")
    print(f"个股: {len(stock_results)} 条")
    print(f"板块: {len(board_results)} 条")
    strong = sum(
        1 for s in stock_results if s.get("is_strong")
    )
    print(f"强势个股: {strong} 只")

    print("\nTOP 5 板块:")
    for i, b in enumerate(board_results[:5], 1):
        print(
            f"  {i}. {b['concept_name']:<12s} "
            f"score={b['board_score']:.2f} "
            f"strong={b['strong_count']}/{b['stock_count']}"
        )

    print("\nTOP 10 个股:")
    for i, s in enumerate(
        sorted(
            stock_results,
            key=lambda x: x["score"],
            reverse=True,
        )[:10], 1
    ):
        tag = " [STRONG]" if s.get("is_strong") else ""
        print(
            f"  {i:2d}. {s['stock_code']} "
            f"{s['stock_name']:<8s} "
            f"score={s['score']:.2f} "
            f"change={s['change_ratio']:+.2f}%{tag}"
        )


def _cmd_serve(scanner: Scanner) -> None:
    """执行 serve 命令.

    Args:
        scanner: 扫描调度器.
    """
    logging.info("Starting scheduler service...")
    scanner.serve()


def _cmd_sync(
    scanner: Scanner,
    date_ymd: str,
) -> None:
    """执行 sync 命令.

    Args:
        scanner: 扫描调度器.
        date_ymd: 日期字符串（YYYYMMDD）.
    """
    logging.info("Manual sync for %s.", date_ymd)
    scanner.run_daily_sync(date_ymd)
    print(f"Sync completed for {date_ymd}.")


def _today_ymd() -> str:
    """返回今天的 YYYYMMDD 字符串."""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d")


def _cmd_backtest(
    scanner: Scanner,
    start_ymd: str,
    end_ymd: str,
    force: bool,
) -> None:
    """执行 backtest 命令.

    Args:
        scanner: 扫描调度器.
        start_ymd: 起始日期.
        end_ymd: 结束日期.
        force: 是否强制刷新.
    """
    from pathlib import Path

    from scanner.backtest import BacktestRunner

    reports_dir = Path("data/reports")
    logging.info(
        "Backtest: %s ~ %s (force=%s).",
        start_ymd, end_ymd, force,
    )
    runner = BacktestRunner(scanner, reports_dir)
    results = runner.run(start_ymd, end_ymd, force)

    success = sum(
        1 for r in results if r["status"] == "success"
    )
    print(
        f"\nBacktest completed: "
        f"{success} trade days processed."
    )


if __name__ == "__main__":
    main()
