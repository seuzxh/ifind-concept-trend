"""检查 SQLite 数据库中的数据量."""
import sqlite3

conn = sqlite3.connect("data/scanner.db")
tables = [
    "concept_popularity",
    "board_stock_relation",
    "kline_daily",
    "kline_1min",
]
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t}: {count}")

print("\n=== 概念人气 TOP5 ===")
for row in conn.execute(
    "SELECT * FROM concept_popularity ORDER BY popularity DESC LIMIT 5"
):
    print(row)

print("\n=== 日K线样本 (300033.SZ) ===")
for row in conn.execute(
    "SELECT * FROM kline_daily WHERE stock_code='300033.SZ' "
    "ORDER BY trade_date"
):
    print(row)

print("\n=== 1分钟K线样本 (300033.SZ) ===")
for row in conn.execute(
    "SELECT * FROM kline_1min WHERE stock_code='300033.SZ' "
    "ORDER BY bar_time"
):
    print(row)

conn.close()
