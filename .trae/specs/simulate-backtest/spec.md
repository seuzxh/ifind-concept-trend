# 回溯模拟测试 Spec

## Why
需要验证系统在历史日期（0520 至今）的完整运行表现，确保每日同步、盘中扫描、推送报告的端到端流程可靠，同时保存每日推送记录用于回溯分析。

## What Changes
- 新增 `scanner/backtest.py` 回溯模拟模块
- 新增 `data/reports/` 目录保存每日推送报告 Markdown 文件
- 在 `__main__.py` 新增 `backtest` CLI 子命令

## Impact
- Affected specs: build-concept-trend-scanner（复用现有 Scanner/Notifier）
- Affected code: `scanner/__main__.py`（新增 backtest 子命令）

## ADDED Requirements

### Requirement: 回溯模拟运行

系统 SHALL 支持对指定日期范围逐日模拟执行完整扫描流程。

#### Scenario: 逐日回溯扫描
- **WHEN** 用户执行 `python -m scanner backtest --start 20260520 --end 20260602`
- **THEN** 系统逐日遍历日期范围，对每个交易日执行完整流程：
  1. 调用 `get_trade_dates` 判断是否交易日，非交易日跳过
  2. 执行盘前同步（p03797 → p03798 → kline_daily）
  3. 执行盘中扫描（kline → 评分）
  4. 生成推送报告并保存到 `data/reports/{YYYY-MM-DD}.md`
  5. 记录执行日志到控制台和回溯摘要文件

#### Scenario: 回溯报告保存
- **WHEN** 某交易日扫描完成
- **THEN** 推送报告 Markdown 内容写入 `data/reports/{trade_date}.md`
- **AND** 不实际调用 webhook 推送（回测模式仅保存文件）

#### Scenario: 回溯摘要记录
- **WHEN** 全部日期回溯完成
- **THEN** 输出摘要信息：总交易日数、成功/失败数、每日观察股池数、强势个股数
- **AND** 摘要保存到 `data/reports/backtest_summary.txt`

### Requirement: Backtest CLI 命令

#### Scenario: 命令行参数
- **WHEN** 用户执行 `python -m scanner backtest`
- **THEN** 支持以下参数：
  - `--start YYYYMMDD`（必需）：回溯起始日期
  - `--end YYYYMMDD`（必需）：回溯结束日期
  - `--force`：强制刷新数据（跳过预查）
