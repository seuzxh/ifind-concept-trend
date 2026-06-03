"""Task 3.5 + 6.2 验证脚本.

验证数据预查逻辑和盘中扫描编排流程.
使用 2026-06-02 的已有数据测试预查跳过行为.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
project_root = Path(__file__).resolve().parent.parent

# 加载 .env
env_path = project_root / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from scanner.config import get_config
from scanner.db import Database
from scanner.sync import DataSync
from scanner.scorer import ScoringEngine
from scanner.scheduler import Scanner


def main():
    config = get_config()
    db = Database(config.db_path)
    db.init_db()

    trade_date = "2026-06-02"

    print("=" * 60)
    print("Task 3.5: 数据预查逻辑验证")
    print("=" * 60)

    # 获取观察股池
    pool = db.get_monitor_pool(trade_date)
    stock_codes = [c for c, _ in pool]
    print(f"观察股池: {len(stock_codes)} 只")

    # 测试日 K 线预查
    existing_daily = db.find_stocks_with_daily(
        trade_date, stock_codes,
    )
    print(
        f"已有日K线 ({trade_date}): "
        f"{len(existing_daily)} 只"
    )
    missing_daily = [
        c for c in stock_codes
        if c not in existing_daily
    ]
    print(f"缺失日K线: {len(missing_daily)} 只")

    # 测试 1min K 线预查
    existing_1min = db.find_stocks_with_1min(
        trade_date, stock_codes,
    )
    print(
        f"已有1min K线 ({trade_date}): "
        f"{len(existing_1min)} 只"
    )
    missing_1min = [
        c for c in stock_codes
        if c not in existing_1min
    ]
    print(f"缺失1min K线: {len(missing_1min)} 只")

    print()
    print("=" * 60)
    print("Task 6.2: 盘中扫描编排验证 (使用已有数据)")
    print("=" * 60)

    from scanner.client import IfindClient
    client = IfindClient(
        base_url=config.ifind_base_url,
        refresh_token=config.ifind_refresh_token,
    )

    sync = DataSync(client, db)
    scoring_config = {
        "weight_change_ratio": 0.25,
        "weight_body_change": 0.30,
        "weight_amount": 0.20,
        "weight_vol_ratio": 0.25,
        "strong_change_threshold": 7.0,
        "strong_body_threshold": 5.0,
    }
    board_config = {
        "strong_ratio_weight": 0.6,
        "avg_score_weight": 0.4,
    }
    scorer = ScoringEngine(db, scoring_config, board_config)
    scanner = Scanner(sync, db, scorer)

    # 执行盘中扫描（force=False 会跳过已有数据）
    stock_results, board_results = (
        scanner.run_intraday_scan(trade_date, force=False)
    )
    print(f"\n扫描结果:")
    print(f"  个股: {len(stock_results)} 条")
    print(f"  板块: {len(board_results)} 条")
    print(f"  强势个股: "
          f"{sum(1 for r in stock_results if r['is_strong'])} 只")

    # TOP 5
    print("\nTOP 5 个股:")
    for i, r in enumerate(
        sorted(
            stock_results,
            key=lambda x: x["score"],
            reverse=True,
        )[:5], 1
    ):
        print(
            f"  {i}. {r['stock_code']} "
            f"{r['stock_name']:<8s} "
            f"score={r['score']:.2f}"
        )
    print("\nTOP 5 板块:")
    for i, r in enumerate(board_results[:5], 1):
        print(
            f"  {i}. {r['concept_name']:<12s} "
            f"score={r['board_score']:.2f}"
        )

    db.close()
    print("\n验证完成!")


if __name__ == "__main__":
    main()
