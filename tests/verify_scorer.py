"""评分引擎验证脚本.

使用 2026-06-02 的真实数据验证 Task 4 各子任务.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scanner.db import Database
from scanner.scorer import ScoringEngine


def main():
    db_path = Path("data/scanner.db")
    if not db_path.exists():
        print("ERROR: data/scanner.db not found")
        return

    db = Database(db_path)
    db.init_db()

    trade_date = "2026-06-02"

    # --- Task 4.1: 昨收价获取 ---
    print("=" * 60)
    print("Task 4.1: 昨收价获取")
    print("=" * 60)
    pool = db.get_monitor_pool(trade_date)
    print(f"观察股池数量: {len(pool)}")
    stock_codes = [c for c, _ in pool]
    prev_closes = db.get_prev_close(stock_codes, trade_date)
    print(f"获取到昨收价: {len(prev_closes)} 只")
    sample_codes = list(prev_closes.keys())[:3]
    for code in sample_codes:
        print(f"  {code}: prev_close = {prev_closes[code]}")
    print()

    # --- Task 4.2-4.5: 因子计算 ---
    print("=" * 60)
    print("Task 4.2-4.5: 因子计算")
    print("=" * 60)
    klines = db.get_kline_1min_batch(trade_date, stock_codes)
    print(f"获取到 1min K 线: {len(klines)} 只")
    sample_code = list(klines.keys())[0]
    bars = klines[sample_code]
    print(f"  {sample_code}: {len(bars)} bars")
    first_open = bars[0]["open"]
    last_close = bars[-1]["close"]
    prev_close = prev_closes.get(sample_code, 0)
    if prev_close > 0:
        change_ratio = (last_close - prev_close) / prev_close * 100
        body_change = (last_close - first_open) / first_open * 100
        total_amount = sum(b.get("amount", 0) for b in bars)
        total_volume = sum(b.get("volume", 0) for b in bars)
        print(f"  prev_close={prev_close}, first_open={first_open}, "
              f"last_close={last_close}")
        print(f"  涨幅={change_ratio:.4f}%, 实体涨幅={body_change:.4f}%")
        print(f"  成交额={total_amount:.2f}, 成交量={total_volume:.2f}")
    print()

    # --- Task 4.6-4.7: 综合评分 + 强势标记 ---
    print("=" * 60)
    print("Task 4.6-4.7: 综合评分 + 强势标记")
    print("=" * 60)
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
    engine = ScoringEngine(db, scoring_config, board_config)
    stock_results, board_results = engine.run(trade_date)
    print(f"个股评分结果: {len(stock_results)} 条")
    print(f"强势个股数: "
          f"{sum(1 for r in stock_results if r['is_strong'])}")
    print()
    print("TOP 10 个股:")
    for i, r in enumerate(
        sorted(stock_results, key=lambda x: x["score"],
               reverse=True)[:10], 1
    ):
        strong_tag = " [STRONG]" if r["is_strong"] else ""
        print(
            f"  {i:2d}. {r['stock_code']} {r['stock_name']:<8s} "
            f"score={r['score']:6.2f} "
            f"涨幅={r['change_ratio']:+7.2f}% "
            f"实体={r['body_change_ratio']:+7.2f}% "
            f"额={r['total_amount']:>12.0f}"
            f"{strong_tag}"
        )
    print()

    # --- Task 4.8: 板块评分 ---
    print("=" * 60)
    print("Task 4.8: 板块评分")
    print("=" * 60)
    print(f"板块评分结果: {len(board_results)} 条")
    for i, r in enumerate(board_results[:10], 1):
        print(
            f"  {i:2d}. {r['concept_name']:<12s} "
            f"board_score={r['board_score']:6.2f} "
            f"strong={r['strong_count']}/{r['stock_count']} "
            f"avg_score={r['avg_score']:.2f}"
        )
    print()

    # --- Task 4.9: 验证 DB 写入 ---
    print("=" * 60)
    print("Task 4.9: 验证 DB 写入")
    print("=" * 60)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    sds_count = conn.execute(
        "SELECT COUNT(*) FROM stock_daily_scan "
        "WHERE trade_date = ?", (trade_date,)
    ).fetchone()[0]
    bds_count = conn.execute(
        "SELECT COUNT(*) FROM board_daily_scan "
        "WHERE trade_date = ?", (trade_date,)
    ).fetchone()[0]
    print(f"stock_daily_scan: {sds_count} 条")
    print(f"board_daily_scan: {bds_count} 条")

    print("\nDB TOP 5 个股:")
    for row in conn.execute(
        "SELECT stock_code, stock_name, score, "
        "change_ratio, is_strong "
        "FROM stock_daily_scan "
        "WHERE trade_date = ? "
        "ORDER BY score DESC LIMIT 5",
        (trade_date,),
    ):
        print(
            f"  {row['stock_code']} {row['stock_name']:<8s} "
            f"score={row['score']:.2f} "
            f"涨幅={row['change_ratio']:+.2f}% "
            f"strong={row['is_strong']}"
        )

    print("\nDB TOP 5 板块:")
    for row in conn.execute(
        "SELECT concept_name, board_score, "
        "strong_count, stock_count "
        "FROM board_daily_scan "
        "WHERE trade_date = ? "
        "ORDER BY board_score DESC LIMIT 5",
        (trade_date,),
    ):
        print(
            f"  {row['concept_name']:<12s} "
            f"score={row['board_score']:.2f} "
            f"strong={row['strong_count']}/"
            f"{row['stock_count']}"
        )
    conn.close()
    db.close()
    print("\n验证完成!")


if __name__ == "__main__":
    main()
