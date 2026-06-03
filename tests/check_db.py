"""Check database for concept vs industry board data."""

import sqlite3

conn = sqlite3.connect("data/scanner.db")
cur = conn.cursor()

lines = []

# Total distinct concepts
cur.execute(
    "SELECT DISTINCT concept_name FROM concept_popularity "
    "ORDER BY concept_name"
)
rows = cur.fetchall()
lines.append(f"Total distinct concepts: {len(rows)}")
for r in rows[:30]:
    lines.append(f"  {r[0]}")
lines.append("  ...")

# Check for 概念 boards
cur.execute(
    "SELECT DISTINCT concept_name FROM concept_popularity "
    "WHERE concept_name LIKE '%概念%'"
)
concept_rows = cur.fetchall()
lines.append(f"\nBoards with '概念': {len(concept_rows)}")
for r in concept_rows[:20]:
    lines.append(f"  {r[0]}")

# Check board_stock_relation
cur.execute(
    "SELECT DISTINCT concept_name FROM board_stock_relation "
    "WHERE concept_name LIKE '%概念%'"
)
bs_concept = cur.fetchall()
lines.append(f"\nboard_stock_relation with '概念': {len(bs_concept)}")
for r in bs_concept[:20]:
    lines.append(f"  {r[0]}")

# Check board_daily_scan
cur.execute(
    "SELECT DISTINCT concept_name FROM board_daily_scan "
    "WHERE concept_name LIKE '%概念%'"
)
bd_concept = cur.fetchall()
lines.append(f"\nboard_daily_scan with '概念': {len(bd_concept)}")
for r in bd_concept[:10]:
    lines.append(f"  {r[0]}")

# Show top boards from latest date
cur.execute(
    "SELECT concept_name, board_score, strong_ratio, "
    "strong_count, stock_count "
    "FROM board_daily_scan "
    "WHERE trade_date = '2026-06-02' "
    "ORDER BY board_score DESC LIMIT 10"
)
lines.append("\nTop 10 boards on 2026-06-02:")
for r in cur.fetchall():
    lines.append(
        f"  {r[0]:30s} score={r[1]:.2f} "
        f"strong={r[3]}/{r[4]}"
    )

# Per-date concept count
cur.execute(
    "SELECT trade_date, COUNT(DISTINCT concept_name) "
    "FROM concept_popularity GROUP BY trade_date "
    "ORDER BY trade_date"
)
lines.append("\nPer-date concept counts:")
for r in cur.fetchall():
    lines.append(f"  {r[0]}: {r[1]} concepts")

conn.close()

result = "\n".join(lines)
with open("tests/check_result.txt", "w", encoding="utf-8") as f:
    f.write(result)
print("Done. Output saved to tests/check_result.txt")
