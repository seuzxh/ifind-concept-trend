"""检查芯片概念成分股的K线数据."""
import sqlite3

conn = sqlite3.connect("data/scanner.db")

stocks = conn.execute(
    "SELECT DISTINCT stock_code, stock_name "
    "FROM board_stock_relation WHERE concept_name='芯片概念' LIMIT 5"
).fetchall()
print("芯片概念成分股样本:")
for s in stocks:
    print(f"  {s[0]} {s[1]}")

if stocks:
    code = stocks[0][0]
    print(f"\n=== {code} 日K线 ===")
    for row in conn.execute(
        "SELECT * FROM kline_daily WHERE stock_code=? ORDER BY trade_date",
        (code,),
    ):
        print(row)

    print(f"\n=== {code} 1分钟K线 ===")
    for row in conn.execute(
        "SELECT * FROM kline_1min WHERE stock_code=? ORDER BY bar_time",
        (code,),
    ):
        print(row)

conn.close()
