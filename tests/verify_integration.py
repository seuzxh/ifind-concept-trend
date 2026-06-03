"""端到端集成测试 (Task 8).

验证完整扫描流程：
  8.1 手动 scan 命令验证
  8.3 历史回溯验证
  8.4 推送报告格式验证
"""

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
project_root = Path(__file__).resolve().parent.parent

env_path = project_root / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from scanner.config import get_config
from scanner.db import Database
from scanner.notifier import Notifier
from scanner.scheduler import Scanner


def test_8_1_manual_scan():
    """Task 8.1: 手动 scan 完整流程验证."""
    print("=" * 60)
    print("Task 8.1: 手动 scan 完整流程验证")
    print("=" * 60)

    config = get_config()
    scanner = Scanner(config)

    date_ymd = "20260602"
    date_display = "2026-06-02"

    # 完整流程（数据已存在，预查会跳过 API）
    stock_results, board_results = scanner.run_full_scan(
        date_ymd, force=False,
    )

    # 验证结果
    assert len(stock_results) > 0, "stock_results 为空"
    assert len(board_results) > 0, "board_results 为空"
    assert len(stock_results) == 561, (
        f"预期 561 只, 实际 {len(stock_results)}"
    )
    assert len(board_results) == 40, (
        f"预期 40 个板块, 实际 {len(board_results)}"
    )

    # 验证 DB 写入
    conn = sqlite3.connect(str(config.db_path))
    sds = conn.execute(
        "SELECT COUNT(*) FROM stock_daily_scan "
        "WHERE trade_date = ?", (date_display,),
    ).fetchone()[0]
    bds = conn.execute(
        "SELECT COUNT(*) FROM board_daily_scan "
        "WHERE trade_date = ?", (date_display,),
    ).fetchone()[0]
    conn.close()

    assert sds == 561, f"DB 个股: 预期 561, 实际 {sds}"
    assert bds == 40, f"DB 板块: 预期 40, 实际 {bds}"

    # 验证评分字段
    top_stock = max(stock_results, key=lambda s: s["score"])
    assert top_stock["score"] > 0, "score 应 > 0"
    assert "change_ratio" in top_stock
    assert "is_strong" in top_stock

    scanner.close()
    print(f"  PASS: {len(stock_results)} 只个股, "
          f"{len(board_results)} 个板块")
    print(f"  DB: {sds} 条个股, {bds} 条板块")
    print(f"  TOP1: {top_stock['stock_code']} "
          f"{top_stock['stock_name']} "
          f"score={top_stock['score']:.2f}")
    return True


def test_8_3_backtest():
    """Task 8.3: 历史回溯扫描验证."""
    print()
    print("=" * 60)
    print("Task 8.3: 历史回溯扫描验证")
    print("=" * 60)

    config = get_config()
    db = Database(config.db_path)

    # 检查 DB 中是否有多个日期的数据
    conn = sqlite3.connect(str(config.db_path))
    dates = conn.execute(
        "SELECT DISTINCT trade_date FROM kline_daily "
        "ORDER BY trade_date",
    ).fetchall()
    conn.close()

    print(f"  DB 中日K线日期: {[d[0] for d in dates]}")

    # 使用已有数据验证回溯逻辑
    if len(dates) >= 2:
        backtest_date = dates[0][0]
        date_ymd = backtest_date.replace("-", "")
        print(f"  回溯日期: {backtest_date}")

        scanner = Scanner(config)
        pool = db.get_monitor_pool(backtest_date)
        if pool:
            prev_closes = db.get_prev_close(
                [c for c, _ in pool], backtest_date,
            )
            print(f"  观察股池: {len(pool)} 只")
            print(f"  昨收价获取: {len(prev_closes)} 只")
            assert len(prev_closes) > 0, "回溯昨收价应为非空"
        else:
            print("  注意: 该日期无观察股池数据（可能为非交易日）")
        scanner.close()
    else:
        print("  仅有一个日期的数据，跳过回溯验证")

    db.close()
    print("  PASS")
    return True


def test_8_4_notifier():
    """Task 8.4: 推送报告格式验证."""
    print()
    print("=" * 60)
    print("Task 8.4: 推送报告格式验证")
    print("=" * 60)

    config = get_config()
    db = Database(config.db_path)

    date_display = "2026-06-02"
    stock_results = db.get_top_stocks(date_display, limit=561)
    board_results = db.get_top_boards(date_display, limit=40)

    assert len(stock_results) > 0, "无扫描结果数据"

    notifier = Notifier(webhook_url="")
    report = notifier._build_report(
        date_display, stock_results, board_results,
    )

    # 验证报告结构
    assert "概念板块强势扫描" in report
    assert "Top 10 强势个股" in report
    assert "Top 5 强势板块" in report
    assert "▎" in report
    assert "得分" in report

    # 验证字节大小
    report_bytes = len(report.encode("utf-8"))
    assert report_bytes <= 4096, (
        f"报告 {report_bytes} 字节超过 4096 限制"
    )

    # 验证两段式结构
    lines = report.split("\n")
    top10_idx = next(
        i for i, l in enumerate(lines)
        if "Top 10" in l
    )
    top5_idx = next(
        i for i, l in enumerate(lines)
        if "Top 5" in l
    )
    assert top10_idx < top5_idx, (
        "Top 10 应在 Top 5 之前"
    )

    # 验证强势标记
    strong_lines = [
        l for l in lines if "**" in l and "得分" in l
    ]
    assert len(strong_lines) > 0, "应有强势个股加粗标记"

    # 验证成交额格式
    has_amount = any("亿" in l or "万" in l for l in lines)
    assert has_amount, "应有成交额格式化（亿/万）"

    db.close()
    print(f"  报告大小: {report_bytes} 字节 (<= 4096)")
    print(f"  Top 10 位置: 第 {top10_idx + 1} 行")
    print(f"  Top 5 位置: 第 {top5_idx + 1} 行")
    print(f"  强势标记行: {len(strong_lines)} 行")
    print("  PASS")
    return True


def main():
    passed = 0
    failed = 0

    tests = [
        ("8.1", test_8_1_manual_scan),
        ("8.3", test_8_3_backtest),
        ("8.4", test_8_4_notifier),
    ]

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"集成测试结果: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
