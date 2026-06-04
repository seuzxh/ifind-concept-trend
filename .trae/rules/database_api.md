# SQLite 数据库 API 规则

> 数据库文件路径：`data/scanner.db`（可通过 `config/config.yaml` 配置）
> 代码位置：`scanner/db.py` — `Database` 类
> 数据模型：`scanner/models.py` — ConceptPopularity / BoardStock / KlineBar / DailyKline

---

## 概览

本系统使用 SQLite 存储行业板块强势扫描的全部数据，共 6 张表，分为 3 层：

| 层级 | 表名 | 用途 |
|------|------|------|
| 原始数据层 | concept_popularity | 行业人气数据（来自 ifind p03793） |
| 原始数据层 | board_stock_relation | 行业-个股关联关系（来自 ifind p03794） |
| 原始数据层 | kline_daily | 日K线数据（来自 ifind cmd_history_quotation） |
| 原始数据层 | kline_1min | 1分钟K线数据（来自 ifind high_frequency） |
| 计算结果层 | stock_daily_scan | 个股每日扫描评分结果 |
| 计算结果层 | board_daily_scan | 板块每日扫描评分结果 |

ER 关系：concept_popularity → board_stock_relation → kline_daily / kline_1min → stock_daily_scan → board_daily_scan

---

## Database 类初始化

```python
from scanner.db import Database

db = Database(db_path=Path("data/scanner.db"))
db.init_db()  # 创建表和索引（幂等操作）
```

- 所有表使用 `INSERT OR REPLACE`（upsert），相同唯一键数据会被覆盖
- 连接在首次使用时创建，通过 `db.close()` 关闭

---

## 写入 API

### upsert_concept_popularity(records, stat_period="近一周") -> int

写入行业人气数据。

- **数据来源**：ifind p03793 接口
- **写入时机**：每日同步（含非交易日），盘中 9:35 前完成
- **唯一键**：(trade_date, concept_name, stat_period)
- **参数 records**：`list[ConceptPopularity]`，字段包括 trade_date, concept_name, popularity, popularity_change_rate
- **筛选逻辑**：先写入全部行业数据，再通过 `get_hot_concepts` 按人气 Top20 + 变化率 Top20 去重筛选出约 37 个热门行业

### upsert_board_stocks(records, stat_period="近一周") -> int

写入板块-个股关联关系。

- **数据来源**：ifind p03794 接口（仅热门行业）
- **写入时机**：每日同步，紧跟行业人气数据之后
- **唯一键**：(trade_date, concept_name, stock_code, stat_period)
- **参数 records**：`list[BoardStock]`，字段包括 trade_date, concept_name, stock_code, stock_name, period_start_date, change_ratio
- **筛选逻辑**：每个板块按涨跌幅降序取 Top30，剔除 ST 股

### upsert_daily_klines(records) -> int

写入日K线数据。

- **数据来源**：ifind cmd_history_quotation 接口
- **写入时机**：交易日盘中 9:36 前获取观察股池近 5 个交易日日K线
- **唯一键**：(stock_code, trade_date)
- **参数 records**：`list[DailyKline]`，字段包括 stock_code, trade_date, open, high, low, close, volume, amount
- **核心用途**：提供"昨收价"（T-1 日 close），用于计算涨幅

### upsert_kline_1min(records) -> int

写入1分钟K线数据。

- **数据来源**：ifind high_frequency 接口
- **写入时机**：交易日 9:36 采集 09:30~09:35 的 5 根 1min K 线
- **唯一键**：(stock_code, trade_date, bar_time)
- **参数 records**：`list[KlineBar]`，字段包括 stock_code, trade_date, bar_time, open, high, low, close, volume, amount, change_ratio
- **核心用途**：提供开盘价、当前价、累计成交额/量、量比等盘中扫描指标

### save_stock_scan_results(trade_date, results) -> int

写入个股每日扫描评分结果。

- **数据来源**：评分引擎计算（非外部 API）
- **写入时机**：交易日 9:36 盘中扫描完成后
- **唯一键**：(trade_date, stock_code)
- **参数 results**：`list[dict]`，每个字典包含：stock_code, stock_name, concept_names, pre_close, open_price, current_price, change_ratio, body_change_ratio, total_amount, total_volume, vol_ratio, score
- **评分公式**：score = 涨幅×0.25 + 实体涨幅×0.30 + 成交额×0.20 + 量比×0.25（仅用前 2 根 1min K 线）

### save_board_scan_results(trade_date, results) -> int

写入板块每日扫描评分结果。

- **数据来源**：基于 Top 50 个股反推计算
- **写入时机**：交易日 9:36 个股扫描完成后
- **唯一键**：(trade_date, concept_name)
- **参数 results**：`list[dict]`，每个字典包含：concept_name, stock_count, avg_score, board_score, top50_count, top50_avg_score, top50_avg_change, board_avg_change
- **评分公式**：board_score = top50_count × 10 + top50_avg_score × 0.5
- **过滤规则**：仅保留 top50_count > 0 的板块

---

## 查询 API

### get_hot_concepts(trade_date, limit=20) -> list[dict]

获取指定日期人气最高的行业板块列表，按 popularity 降序。

返回：[{concept_name, popularity, popularity_change_rate}, ...]

### get_monitor_pool(trade_date) -> list[tuple[str, str]]

获取截至指定日期最新的观察股池（去重后的 stock_code, stock_name）。

查询逻辑：取 board_stock_relation 中 ≤ trade_date 最近一个交易日的去重记录。

### get_prev_close(stock_codes, before_date) -> dict[str, float]

批量获取指定股票在某日期之前最近一日的收盘价。

返回：{stock_code: close_price}，用于计算涨幅。

### get_top_stocks(trade_date, limit=10) -> list[dict]

获取指定日期评分最高的个股列表，按 score 降序。

返回完整扫描结果字段（不含 id, trade_date, created_at）。

### get_top_boards(trade_date, limit=5) -> list[dict]

获取指定日期评分最高的板块列表，按 board_score 降序。

返回完整板块扫描结果字段。

---

## 数据流转时序

```
每日同步（含非交易日）
  1. p03793 → upsert_concept_popularity() → get_hot_concepts() 筛选 ~37 行业
  2. p03794 ×37 → upsert_board_stocks() → 每行业 Top30 剔除 ST → ~800 股观察池

交易日盘中 9:36
  3. cmd_history_quotation → upsert_daily_klines() → 近 5 日日K
  4. high_frequency → upsert_kline_1min() → 09:30~09:35 的 5 根 1min K 线
  5. get_prev_close() 获取昨收价
  6. 评分引擎计算 → save_stock_scan_results()
  7. 板块聚合计算 → save_board_scan_results()
  8. get_top_boards() + get_top_stocks() → 推送通知
```

---

## 数据预查规则（避免重复下载）

**每次调用 ifind API 获取数据前，必须先查询 SQLite 判断该数据是否已存在，已存在则跳过下载。**

各表的预查方式：

| 表 | 预查 SQL | 说明 |
|----|---------|------|
| concept_popularity | `SELECT COUNT(*) FROM concept_popularity WHERE trade_date = ?` | count > 0 则跳过当日 p03793 下载 |
| board_stock_relation | `SELECT COUNT(*) FROM board_stock_relation WHERE trade_date = ?` | count > 0 则跳过当日 p03794 下载 |
| kline_daily | `SELECT COUNT(*) FROM kline_daily WHERE trade_date = ? AND stock_code IN (...)` | 按日期+股票列表批量预查，已有记录的跳过 |
| kline_1min | `SELECT COUNT(*) FROM kline_1min WHERE trade_date = ? AND stock_code = ?` | 按日期+单只股票预查，5 条（09:30~09:35）齐全则跳过 |
| stock_daily_scan | 由评分引擎写入，不涉及外部下载 | — |
| board_daily_scan | 由评分引擎写入，不涉及外部下载 | — |

执行原则：

1. **必须预查**：所有调用 ifind API 的代码路径，在发起 HTTP 请求前必须先查 SQLite
2. **按需跳过**：已有数据则跳过该批次的 API 调用，减少不必要的网络请求和配额消耗
3. **强制覆盖场景**：若需强制刷新（如数据修正），应提供显式的 `force=True` 参数绕过预查
4. **日志记录**：预查命中时应记录 skip 日志，便于排查；预查未命中时记录 fetch 日志

---

## 开发注意事项

- 所有写入操作使用 `INSERT OR REPLACE`，天然幂等，可安全重跑
- `row_factory = sqlite3.Row`，查询结果通过 `dict(row)` 转为字典
- `get_prev_close` 使用动态占位符拼接 `IN (?)`，stock_codes 列表来自数据库查询，不存在 SQL 注入风险
- 数据库文件默认位于 `data/scanner.db`，父目录不存在时自动创建
- 全部数据永久保留，供后续 qlib 回测分析使用
- 预估年数据量约 10 万行，SQLite 完全可承载
