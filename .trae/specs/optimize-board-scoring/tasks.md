# Tasks

- [x] Task 1: 重写板块评分逻辑（scorer.py `_score_boards`）
  - [x] 1.1: 取 Top 50 个股，统计每个板块的 top50_count、top50_avg_score、top50_avg_change、board_avg_change
  - [x] 1.2: 计算 board_score = top50_count × 10 + top50_avg_score × 0.5
  - [x] 1.3: 过滤 top50_count = 0 的板块
  - [x] 1.4: 更新 board_daily_scan 写入字段（db.py `save_board_scan_results`）

- [x] Task 2: 更新推送报告模板（notifier.py）
  - [x] 2.1: Top 5 板块标题显示 top50_count、board_score、board_avg_change
  - [x] 2.2: 板块内成分股改为按涨幅（change_ratio）降序取 Top 5

- [x] Task 3: 更新回测摘要和 CLI 输出
  - [x] 3.1: backtest.py 摘要表头适配新字段
  - [x] 3.2: __main__.py CLI 输出适配新字段

- [x] Task 4: 回测验证
  - [x] 4.1: 清除旧评分数据，重新回测 0520-0602
  - [x] 4.2: 检查报告结果是否符合预期

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 1, Task 2, Task 3
