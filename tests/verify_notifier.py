"""Task 5 验证脚本.

使用 2026-06-02 真实数据验证推送报告格式.
不实际推送，仅打印生成的 Markdown 报告.
"""

import os
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
                os.environ[k.strip()] = v.strip()

from scanner.config import get_config
from scanner.db import Database
from scanner.scorer import ScoringEngine
from scanner.notifier import Notifier


def main():
    config = get_config()
    db = Database(config.db_path)
    db.init_db()

    trade_date = "2026-06-02"

    # 从 DB 获取已有评分结果
    stock_results = db.get_top_stocks(trade_date, limit=561)
    board_results = db.get_top_boards(trade_date, limit=40)

    if not stock_results:
        print("ERROR: No scan results found for", trade_date)
        return

    print(f"Loaded {len(stock_results)} stocks, "
          f"{len(board_results)} boards from DB")

    # 构建报告（不推送）
    notifier = Notifier(webhook_url="")
    report = notifier._build_report(
        trade_date, stock_results, board_results,
    )

    print("\n" + "=" * 60)
    print("Generated Markdown Report:")
    print("=" * 60)
    print(report)
    print("=" * 60)

    # 检查字节大小
    report_bytes = len(report.encode("utf-8"))
    print(f"\nReport size: {report_bytes} bytes "
          f"(limit: 4096)")
    if report_bytes > 4096:
        print("WARNING: Report exceeds 4096 bytes!")
    else:
        print("OK: Within byte limit.")

    # 验证关键内容
    assert "概念板块强势扫描" in report
    assert "Top 10 强势个股" in report
    assert "Top 5 强势板块" in report
    assert "▎" in report
    strong_count = sum(
        1 for s in stock_results if s.get("is_strong")
    )
    print(f"\nStrong stocks: {strong_count}")
    print("All assertions passed!")

    db.close()


if __name__ == "__main__":
    main()
