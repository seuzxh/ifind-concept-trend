# Tasks

- [x] Task 1: 创建 `scanner/backtest.py` 回溯模拟模块
  - [x] 1.1 实现 `BacktestRunner` 类，封装逐日遍历 + 交易日判断
  - [x] 1.2 实现 `run_backtest(start, end, force)` 方法：逐日调用 Scanner.run_full_scan
  - [x] 1.3 实现报告保存逻辑：每交易日报告写入 `data/reports/{date}.md`
  - [x] 1.4 实现回溯摘要生成：输出到控制台 + 保存 `data/reports/backtest_summary.txt`
- [x] Task 2: 在 `__main__.py` 新增 `backtest` 子命令
  - [x] 2.1 添加 `backtest` 子命令（--start, --end, --force 参数）
  - [x] 2.2 调用 BacktestRunner 执行回溯
- [x] Task 3: 验证测试
  - [x] 3.1 运行 `python -m scanner backtest --start 20260601 --end 20260602` 验证
  - [x] 3.2 检查 `data/reports/` 目录生成的报告文件（2 个 .md + 1 个 summary）
  - [x] 3.3 检查 `backtest_summary.txt` 摘要内容
  - [x] 3.4 提交代码

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
