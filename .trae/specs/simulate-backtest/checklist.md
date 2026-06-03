# Checklist

## 回溯模拟模块

- [x] BacktestRunner 类实现完成
- [x] 逐日遍历 + 交易日判断正确（非交易日跳过）
- [x] 每交易日报告保存到 `data/reports/{date}.md`
- [x] 回溯摘要保存到 `data/reports/backtest_summary.txt`

## CLI 命令

- [x] `python -m scanner backtest --help` 显示正确
- [x] `python -m scanner backtest --start 20260601 --end 20260602` 执行成功

## 端到端验证

- [x] 回溯 0601~0602 期间所有交易日均有报告文件
- [x] 每个报告文件包含两段式 Markdown 内容
- [x] backtest_summary.txt 包含每日执行摘要
- [x] 非交易日被正确跳过（0601~0602 均为交易日，无跳过案例，通过 get_trade_dates 验证）
