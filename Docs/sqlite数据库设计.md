# SQLite 数据库设计

> 数据库文件：`data/scanner.db`（路径可配置）

---

## ER 关系概览

```
concept_popularity (行业人气明细)
  │  1:N
  ▼
board_stock_relation (行业-个股关联)
  │  N:1
  ▼
kline_daily (日K线数据 — 昨收价来源)
  │
  ▼
kline_1min (1分钟K线数据 — 盘中实时)
  │
  ▼
stock_daily_scan (个股每日扫描结果)
  │
  ▼
board_daily_scan (板块每日扫描结果)
```

---

## 表结构设计

### 1. concept_popularity — 行业人气明细

> 数据来源：ifind data_pool(p03793)，每日同步（含非交易日）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| trade_date | TEXT | NOT NULL | 交易日期（YYYY-MM-DD），来自 p03793_f002 |
| concept_name | TEXT | NOT NULL | 行业板块名称，来自 p03793_f001 |
| popularity | REAL | | 自选热度，来自 p03793_f009 |
| popularity_change_rate | REAL | | 自选热度变化率（%），来自 p03793_f010 |
| stat_period | TEXT | NOT NULL, DEFAULT '近一周' | 统计周期 |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引**：
- `idx_cp_date` ON (trade_date)
- `idx_cp_concept` ON (concept_name)
- `uq_cp_date_concept` UNIQUE ON (trade_date, concept_name, stat_period)

### 2. board_stock_relation — 行业-个股关联

> 数据来源：ifind data_pool(p03794)，每日同步（含非交易日）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| trade_date | TEXT | NOT NULL | 交易日期（YYYY-MM-DD），来自 p03794_f001 |
| concept_name | TEXT | NOT NULL | 行业板块名称 |
| stock_code | TEXT | NOT NULL | 交易代码，来自 jydm |
| stock_name | TEXT | | 交易代码名称，来自 jydm_mc |
| period_start_date | TEXT | | 区间开始日期，来自 p03794_f016 |
| change_ratio | REAL | | 涨跌幅（%），来自 p03794_f012 |
| stat_period | TEXT | NOT NULL, DEFAULT '近一周' | 统计周期 |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引**：
- `idx_bsr_date` ON (trade_date)
- `idx_bsr_concept` ON (concept_name)
- `idx_bsr_stock` ON (stock_code)
- `uq_bsr_unique` UNIQUE ON (trade_date, concept_name, stock_code, stat_period)

### 3. kline_daily — 日 K 线数据

> 数据来源：ifind cmd_history_quotation，盘中扫描前获取近 5 日日K线

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| stock_code | TEXT | NOT NULL | 股票代码 |
| trade_date | TEXT | NOT NULL | 交易日期（YYYY-MM-DD） |
| open | REAL | | 开盘价 |
| high | REAL | | 最高价 |
| low | REAL | | 最低价 |
| close | REAL | | 收盘价（作为次日昨收价使用） |
| volume | REAL | | 成交量 |
| amount | REAL | | 成交额 |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引**：
- `idx_kd_stock_date` ON (stock_code, trade_date)
- `uq_kd_unique` UNIQUE ON (stock_code, trade_date)

### 4. kline_1min — 1 分钟 K 线数据

> 数据来源：ifind high_frequency，盘中 9:36 采集 09:30~09:35 的数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| stock_code | TEXT | NOT NULL | 股票代码 |
| trade_date | TEXT | NOT NULL | 交易日期（YYYY-MM-DD） |
| bar_time | TEXT | NOT NULL | K 线时间（HH:MM:SS） |
| open | REAL | | 开盘价 |
| high | REAL | | 最高价 |
| low | REAL | | 最低价 |
| close | REAL | | 收盘价 |
| volume | REAL | | 成交量 |
| amount | REAL | | 成交额 |
| change_ratio | REAL | | 涨跌幅（%） |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引**：
- `idx_k1m_stock_date` ON (stock_code, trade_date)
- `uq_k1m_bar` UNIQUE ON (stock_code, trade_date, bar_time)

### 5. stock_daily_scan — 个股每日扫描结果

> 数据来源：评分引擎计算结果，仅使用前 2 根 1min K 线（09:30~09:31）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| trade_date | TEXT | NOT NULL | 扫描日期（YYYY-MM-DD） |
| stock_code | TEXT | NOT NULL | 股票代码 |
| stock_name | TEXT | | 股票名称 |
| concept_names | TEXT | | 所属行业板块（逗号分隔） |
| pre_close | REAL | | 前收盘价（来自 kline_daily T-1 日 close） |
| open_price | REAL | | 开盘价（第 1 根 1min K 线） |
| current_price | REAL | | 当前价（第 2 根 1min K 线 close） |
| change_ratio | REAL | | 涨幅（%），(current - preClose) / preClose |
| body_change_ratio | REAL | | 实体涨幅（%），基于 2min K 线计算 |
| total_amount | REAL | | 开盘 2 分钟累计成交额 |
| total_volume | REAL | | 开盘 2 分钟累计成交量 |
| vol_ratio | REAL | | 量比，来自 high_frequency LB 指标 |
| score | REAL | | 综合强势得分（0-100） |
| is_strong | INTEGER | DEFAULT 0 | 保留字段（当前未使用） |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引**：
- `idx_sds_date` ON (trade_date)
- `idx_sds_score` ON (trade_date, score DESC)
- `uq_sds_unique` UNIQUE ON (trade_date, stock_code)

### 6. board_daily_scan — 板块每日扫描结果

> 数据来源：基于 Top 50 个股反推计算

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| trade_date | TEXT | NOT NULL | 扫描日期（YYYY-MM-DD） |
| concept_name | TEXT | NOT NULL | 行业板块名称 |
| stock_count | INTEGER | | 板块内监控个股数 |
| strong_count | INTEGER | DEFAULT 0 | 保留字段（当前未使用） |
| strong_ratio | REAL | DEFAULT 0 | 保留字段（当前未使用） |
| avg_score | REAL | | 板块内全部个股平均得分 |
| board_score | REAL | | 板块综合得分 = top50_count × 10 + top50_avg_score × 0.5 |
| top50_count | INTEGER | DEFAULT 0 | 该板块在个股 Top50 中的个股数量 |
| top50_avg_score | REAL | DEFAULT 0 | 该板块 Top50 个股的平均得分 |
| top50_avg_change | REAL | DEFAULT 0 | 该板块 Top50 个股的涨幅均值 |
| board_avg_change | REAL | DEFAULT 0 | 该板块全部成分股的涨幅均值 |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引**：
- `idx_bds_date` ON (trade_date)
- `idx_bds_score` ON (trade_date, board_score DESC)
- `uq_bds_unique` UNIQUE ON (trade_date, concept_name)

---

## 数据生命周期

| 表 | 写入时机 | 保留策略 | 预估日增量 |
|----|---------|---------|-----------|
| concept_popularity | 每日同步（含非交易日） | 永久保留 | ~257 行（全部行业） |
| board_stock_relation | 每日同步（含非交易日） | 永久保留 | ~850 行（~37 行业 × ~25 个股） |
| kline_daily | 交易日盘中 9:36 | 永久保留 | ~5000 行（~850 个股 × ~5 日） |
| kline_1min | 交易日盘中 9:36 | 永久保留 | ~4250 行（~850 个股 × 5 条） |
| stock_daily_scan | 交易日盘中 9:36 | 永久保留 | ~850 行 |
| board_daily_scan | 交易日盘中 9:36 | 永久保留 | ~23 行（top50_count > 0 的板块） |

> 全部保留历史数据，供后续 qlib 回测分析使用。预估年数据量约 10 万行，SQLite 完全可承载。

---

## 查询场景

### 场景 1：获取 T 日监控标的池

```sql
SELECT DISTINCT stock_code, stock_name
FROM board_stock_relation
WHERE trade_date = 'T-1日'
ORDER BY stock_code;
```

### 场景 2：获取 T 日扫描排名

```sql
SELECT * FROM stock_daily_scan
WHERE trade_date = 'T日'
ORDER BY score DESC
LIMIT 10;
```

### 场景 3：获取板块排名

```sql
SELECT * FROM board_daily_scan
WHERE trade_date = 'T日'
ORDER BY board_score DESC
LIMIT 5;
```

### 场景 4：回溯某日某股的 K 线数据

```sql
SELECT * FROM kline_1min
WHERE stock_code = '300033.SZ' AND trade_date = '2026-06-02'
ORDER BY bar_time;
```

### 场景 5：查看某板块近 N 日的人气趋势

```sql
SELECT trade_date, concept_name, popularity, popularity_change_rate
FROM concept_popularity
WHERE concept_name = '通信网络设备及器件'
ORDER BY trade_date DESC
LIMIT 10;
```
