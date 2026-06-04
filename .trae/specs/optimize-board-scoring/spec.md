# 优化强势板块判断逻辑 Spec

## Why

当前板块评分基于该板块全部成分股（~30只）的平均得分，导致成分股多但无突出个股的板块排名偏高（如证券Ⅲ），而真正有个股爆发的板块被稀释。需要改为"自下而上"从 Top 50 强势个股反推强势板块，聚焦有真实资金流入的板块。

## What Changes

- **板块评分公式重写**：从"全股均分"改为"Top 50 个股反推"
- **板块涨幅指标**：新增板块级涨幅（成分股涨幅均值），用于展示和排序
- **报告模板更新**：Top 5 板块展示涨幅 Top 5 成分股（按涨幅降序）

## 强势板块计算规则

### 核心思路

> 先选强势个股，再由强势个股所属板块反推板块强势程度。

### Step 1: 确定强势个股池

对观察股池（~850只）完成四因子评分后，按 `score` 降序取 **Top 50** 作为强势个股池。

### Step 2: 统计每个板块的强势指标

对每个板块（~37个行业），统计以下指标：

| 指标 | 计算方式 | 含义 |
|------|---------|------|
| `top50_count` | 该板块在 Top 50 中的个股数量 | 板块内强势个股集中度 |
| `top50_avg_score` | 该板块 Top 50 个股的平均得分 | 板块内强势个股的质量 |
| `top50_avg_change` | 该板块 Top 50 个股的涨幅均值 | 板块内强势个股的平均涨幅 |
| `board_avg_change` | 该板块全部成分股的涨幅均值 | 板块整体涨幅水平 |

### Step 3: 计算板块得分

```
board_score = top50_count × 10 + top50_avg_score × 0.5
```

| 因子 | 权重 | 理由 |
|------|------|------|
| top50_count × 10 | ~55% | 板块内强势个股数量是最核心信号，乘以 10 将数量级拉到与分数可比 |
| top50_avg_score × 0.5 | ~45% | 板块内强势个股质量，缩放后与 count 贡献可比 |

**过滤规则**：仅展示 `top50_count > 0` 的板块（至少有 1 只 Top 50 个股）。

### Step 4: 排序与展示

板块按 `board_score` 降序排列，取 Top 5 展示。每个板块内展示涨幅 Top 5 成分股（按 `change_ratio` 降序）。

### 示例（2026-06-02 数据预期效果）

假设 Top 50 中有 5 只属于"通信网络设备及器件"、3 只属于"印制电路板"：

| 板块 | top50_count | top50_avg_score | board_score |
|------|-------------|-----------------|-------------|
| 通信网络设备及器件 | 5 | 85.0 | 92.5 |
| 印制电路板 | 3 | 82.0 | 71.0 |
| 火电 | 2 | 86.5 | 63.3 |

## Impact

- Affected code: `scanner/scorer.py`（`_score_boards` 方法）
- Affected code: `scanner/notifier.py`（报告模板：板块内成分股按涨幅排序）
- Affected code: `scanner/backtest.py`（摘要表头更新）
- Affected code: `scanner/db.py`（`board_daily_scan` 表新增字段）

## ADDED Requirements

### Requirement: Top 50 反推强势板块评分

系统 SHALL 使用 Top 50 强势个股反推板块评分，替代原有的全股均分方案。

#### Scenario: 正常交易日评分
- **WHEN** 评分引擎完成全部个股评分
- **THEN** 取 score Top 50 个股，统计每个板块的 top50_count、top50_avg_score、top50_avg_change、board_avg_change
- **AND** 计算 board_score = top50_count × 10 + top50_avg_score × 0.5
- **AND** 仅保留 top50_count > 0 的板块

#### Scenario: 板块无 Top 50 个股
- **WHEN** 某板块没有任何个股进入 Top 50
- **THEN** 该板块不出现在强势板块列表中

### Requirement: 板块涨幅 Top 5 展示

系统 SHALL 在推送报告中展示 Top 5 强势板块，每个板块内展示涨幅 Top 5 成分股。

#### Scenario: 推送报告板块部分
- **WHEN** 生成推送报告
- **THEN** Top 5 板块按 board_score 降序排列
- **AND** 每个板块展示涨幅 Top 5 成分股（按 change_ratio 降序）
- **AND** 板块标题显示 top50_count、board_score、board_avg_change

## MODIFIED Requirements

### Requirement: 板块评分计算

原方案：`board_score = avg_score`（全部成分股均分）

新方案：`board_score = top50_count × 10 + top50_avg_score × 0.5`（Top 50 反推）

## REMOVED Requirements

（无移除项）
