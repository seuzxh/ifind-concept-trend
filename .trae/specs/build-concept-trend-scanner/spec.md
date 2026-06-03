# 概念板块强势扫描系统 Spec

## Why

每天开盘后（9:35）需要快速定位强势启动的概念板块和个股，辅助短线买卖决策。目前缺少一个自动化工具来完成数据采集、综合评分和结果推送的完整链路。

## What Changes

- 新建 ifind API 数据采集层：封装概念板块人气、成份股、K线等 HTTP 接口调用
- 新建 SQLite 数据存储层：持久化板块-个股关联、K线、扫描结果
- 新建多因子综合评分引擎：基于涨幅、实体涨幅、成交额、量比等指标计算强势得分
- 新建扫描调度器：支持 9:36 定时触发 + 手动触发
- 新建结果推送模块：通过企业微信 webhook 推送文本格式扫描报告
- 新建 CLI 入口：提供命令行交互界面

## Impact

- Affected code: 全新项目，无存量代码影响
- External dependencies: ifind HTTP API、企业微信 webhook

---

## ADDED Requirements

### Requirement: ifind API 接口封装

系统 SHALL 基于 ifind HTTP API（Base URL: `https://quantapi.51ifind.com`）封装以下接口。

**鉴权方式**：
- 使用 `refresh_token` 获取/更新 `access_token`（有效期 7 天，最多绑定 20 个 IP）
- 所有数据请求在 Header 中携带 `access_token`
- API 频率限制：600 次/分钟

#### Scenario: Token 管理
- **WHEN** 系统启动或 access_token 过期
- **THEN** 调用 `POST /api/v1/get_access_token` 获取当前有效 token
- **AND** 如需重新生成，调用 `POST /api/v1/update_access_token`（会使旧 token 失效）

#### Scenario: 获取概念人气明细（热门板块筛选）— 专题报表接口
- **WHEN** 需要获取最近一日热门概念板块（自选热度 Top20、自选热度变化率 Top20）
- **THEN** 调用 `POST /api/v1/data_pool`
  - reportname: `p03797`
  - functionpara: `{"date": "YYYYMMDD", "tjzq": "近一周"}`
  - outputpara: `p03797_f001,p03797_f002,p03797_f009,p03797_f010`
- **AND** 返回字段含义：
  - `p03797_f001`: 概念板块名称
  - `p03797_f002`: 交易日期
  - `p03797_f009`: 自选热度
  - `p03797_f010`: 自选热度变化率（%）
- **AND** 按自选热度降序取 Top20 + 自选热度变化率降序取 Top20，合并去重
- **NOTE**：date 参数传入自然日（非交易日也会返回数据），人气数据在非交易日也可能发生变化

#### Scenario: 获取概念板块热点成分股 — 专题报表接口
- **WHEN** 给定概念板块名称，需要获取其热门成分股
- **THEN** 调用 `POST /api/v1/data_pool`
  - reportname: `p03798`
  - functionpara: `{"date": "YYYYMMDD", "tjzq": "近一周", "hy": "概念板块名称"}`
  - outputpara: `jydm,jydm_mc,p03798_f001,p03798_f012,p03798_f016`
- **AND** 返回字段含义：
  - `jydm`: 交易代码
  - `jydm_mc`: 交易代码名称
  - `p03798_f001`: 交易日期
  - `p03798_f012`: 涨跌幅（%）
  - `p03798_f016`: 区间开始日期
- **AND** 每个板块取自选热度 Top20 + 自选热度变化率 Top20 的个股，剔除 ST 股
- **AND** 所有板块的个股合并去重，作为 T 日监控标的
- **NOTE**：人气成分股数据在非交易日也可能发生变化，同步时不受交易日限制

#### Scenario: 获取个股上一交易日日 K 线（基准数据）
- **WHEN** 盘中扫描前需要获取监控标的池上一交易日的 OHLCV 数据（用于计算涨幅）
- **THEN** 调用 `POST /api/v1/cmd_history_quotation`
  - codes: 监控标的池所有股票代码（逗号分隔）
  - indicators: `open,close,high,low,volume,amount`
  - startdate / enddate: 近 5 个交易日（取最后一根即为 T-1 日）
  - functionpara.Interval: `D`（日线）
- **AND** 取最近一根 K 线的 `close` 作为昨收价（preClose）
- **AND** 同时获取近 5 日成交额数据，可作为成交额对比基准（可选）
- **AND** 数据写入 SQLite 的 kline_daily 表，供回测分析使用

#### Scenario: 获取个股开盘 5 分钟 K 线（盘中实时数据）
- **WHEN** 在 T 日 9:36 需要获取监控标的池的开盘前 5 分钟行情数据
- **THEN** 调用 `POST /api/v1/high_frequency`
  - codes: 监控标的池所有股票代码（逗号分隔）
  - indicators: `open,high,low,close,volume,amount,changeRatio,LB`
  - starttime: `T日 09:30:00`
  - endtime: `T日 09:35:00`
  - functionpara.Interval: `1`（1 分钟）
- **AND** 结合日 K 线的昨收价，计算所有评分因子：

  | 计算指标 | 数据来源 | 计算方式 | 说明 |
  |---------|---------|---------|------|
  | 昨收价 (preClose) | cmd_history_quotation | 上一交易日日 K 的 `close` | 可靠的昨收价来源 |
  | 开盘价 (openPrice) | high_frequency | 第 1 根 K 线的 `open` | 集合竞价产生的开盘价 |
  | 当前价 (currentPrice) | high_frequency | 最后一根 K 线的 `close` | 9:35 时刻的最新价 |
  | 涨幅 (changeRatio) | 组合计算 | `(currentPrice - preClose) / preClose × 100%` | 相对昨收的涨跌幅 |
  | 实体涨幅 (bodyChange) | high_frequency | `(currentPrice - openPrice) / openPrice × 100%` | 日内真实走势强度 |
  | 累计成交额 (totalAmount) | high_frequency | 5 根 K 线 `amount` 求和 | 开盘 5 分钟总成交额 |
  | 累计成交量 (totalVolume) | high_frequency | 5 根 K 线 `volume` 求和 | 开盘 5 分钟总成交量 |
  | 量比 (volRatio) | high_frequency | `LB` 指标 | API 技术指标直接提供 |

#### Scenario: 交易日判断
- **WHEN** 需要判断某日是否为交易日
- **THEN** 调用 `POST /api/v1/get_trade_dates`
  - marketcode: `212001`（上交所）
  - functionpara: `mode=1, dateType=0`
  - startdate / enddate: 查询日期

### Requirement: 数据存储模块

系统 SHALL 使用 SQLite 存储数据，包含以下核心表：

#### Scenario: 概念板块人气存储
- **WHEN** 通过 p03797 采集到概念人气明细数据
- **THEN** 写入 concept_popularity 表（板块名称、自选热度、自选热度变化率、采集日期）
- **AND** 支持按日期查询历史人气数据

#### Scenario: 板块-个股关联存储
- **WHEN** 通过 p03798 采集到板块成分股数据
- **THEN** 写入 board_stock_relation 表（板块名称、股票代码、股票名称、涨跌幅、关联日期）
- **AND** 每日更新关联关系（含非交易日，因人气数据在非交易日也可能变化）

#### Scenario: K 线数据存储
- **WHEN** 采集到个股 K 线数据
- **THEN** 写入 kline_1min 表（股票代码、时间戳、OHLCV、采集日期）

#### Scenario: 扫描结果存储
- **WHEN** 扫描完成
- **THEN** 写入 scan_result 表（扫描日期、板块得分、个股得分、综合排名）
- **AND** 保留全部历史数据供后续回测使用

### Requirement: 多因子综合评分引擎

系统 SHALL 基于以下因子计算强势得分：

#### 因子定义与数据来源

| 因子 | 权重（初始） | 数据来源 | 计算方式 |
|------|-------------|---------|---------|
| 涨幅 | 0.25 | high_frequency + cmd_history_quotation | `(最后close - 昨收) / 昨收 × 100%`，昨收来自日K |
| 实体涨幅 | 0.30 | high_frequency 5min K 线 | `(最后close - 第1根open) / 第1根open × 100%` |
| 成交额 | 0.20 | high_frequency 5min K 线 | 5 根 K 线 `amount` 求和 |
| 量比 | 0.25 | high_frequency 的 `LB` 指标 | API 技术指标直接提供 |

#### Scenario: 个股强势评分
- **WHEN** 输入个股的涨幅、实体涨幅、成交额、量比数据
- **THEN** 系统按加权公式计算个股强势得分（0-100 分）
- **AND** 涨幅 > 7% 或实体涨幅 > 5% 的个股标记为"强势"

#### Scenario: 概念板块强势评分
- **WHEN** 输入概念板块内所有成份股的评分数据
- **THEN** 系统计算板块强势得分 = 板块内强势个股占比 × 60% + 板块平均得分 × 40%
- **AND** 输出板块强势排名

#### Scenario: 阈值可配置
- **WHEN** 用户修改配置文件中的阈值参数
- **THEN** 系统使用新阈值进行评分计算，无需修改代码

### Requirement: 扫描调度器

系统 SHALL 支持两种触发方式：

#### Scenario: 定时触发
- **WHEN** 到达每个交易日 9:36（可配置）
- **THEN** 系统自动执行完整扫描流程：数据采集 → 评分计算 → 结果推送
- **AND** 在非交易日自动跳过盘中扫描
- **NOTE**：人气数据同步（盘前）不受交易日限制，每日执行；盘中扫描仅在交易日执行

#### Scenario: 手动触发
- **WHEN** 用户通过 CLI 执行扫描命令
- **THEN** 系统立即执行完整扫描流程并输出结果
- **AND** 支持指定日期参数进行历史数据回溯扫描

### Requirement: 结果推送模块

系统 SHALL 将扫描结果通过 webhook 推送：

#### Scenario: 推送扫描报告
- **WHEN** 扫描完成
- **THEN** 将结果以文本格式推送到企业微信 webhook
- **AND** 推送内容包括：Top 5 强势概念板块（板块名、得分、强势个股数）、Top 10 强势个股（股票名、代码、得分、关键指标）

#### Scenario: 推送失败处理
- **WHEN** webhook 推送失败
- **THEN** 记录日志并保留扫描结果到本地，不阻塞后续流程

### Requirement: CLI 命令行入口

系统 SHALL 提供 CLI 入口支持以下命令：

#### Scenario: 执行扫描
- **WHEN** 用户执行 `python -m scanner scan`
- **THEN** 立即触发一次扫描并输出结果

#### Scenario: 启动定时服务
- **WHEN** 用户执行 `python -m scanner serve`
- **THEN** 启动定时调度服务，等待 9:36 自动触发

#### Scenario: 数据同步
- **WHEN** 用户执行 `python -m scanner sync`
- **THEN** 手动触发数据采集和存储，不执行评分

---

## 需要用户提供的信息

### 1. 鉴权信息（P0）
- `refresh_token`（用于获取 access_token）

### 2. 接口返回字段确认（P0）

p03797 和 p03798 的 outputpara 中部分字段含义需确认：

| 报表 | 字段 | 含义 | 状态 |
|------|------|------|------|
| p03797 | `p03797_f001` | 概念板块名称 | 待验证 |
| p03797 | `p03797_f002` | 交易日期 | 已确认 |
| p03797 | `p03797_f009` | 自选热度 | 已确认 |
| p03797 | `p03797_f010` | 自选热度变化率（%） | 已确认 |
| p03798 | `jydm` | 交易代码 | 待验证 |
| p03798 | `jydm_mc` | 交易代码名称 | 待验证 |
| p03798 | `p03798_f001` | 交易日期 | 已确认 |
| p03798 | `p03798_f012` | 涨跌幅（%） | 已确认 |
| p03798 | `p03798_f016` | 区间开始日期 | 已确认 |

### 3. 企业微信 Webhook（P1）
- Webhook URL（可后续提供）

---

## 数据流程总览

```
每日同步（含非交易日，如每日 20:00 或 T日 9:00）
  │
  ├─ 1. data_pool(p03797) ──→ 获取最近一日概念人气明细（统计周期：近一周）
  │    └─ 筛选：自选热度 Top20 + 自选热度变化率 Top20 → 去重得热门概念板块列表
  │
  ├─ 2. data_pool(p03798) ──→ 逐个板块获取热门成分股（统计周期：近一周）
  │    └─ 筛选：自选热度 Top20 + 自选热度变化率 Top20 → 剔除ST → 去重得监控标的池
  │
  └─ 3. 存入 SQLite（板块-个股关联）
  │
  └─ NOTE：人气数据在非交易日也可能变化，因此每日都需同步

交易日盘中 (T日 9:36)
  │
  ├─ 4. get_trade_dates ──→ 确认 T 是否交易日（非交易日跳过后续步骤）
  │
  ├─ 5. cmd_history_quotation ──→ 获取监控标的池近 5 日日K线
  │    └─ 取 T-1 日 close 作为昨收价，存入 kline_daily 表
  │
  ├─ 6. high_frequency ──→ 获取监控标的池的开盘 5 分钟 K 线（09:30~09:35）
  │    ├─ indicators: open,high,low,close,volume,amount,changeRatio,LB
  │    └─ 结合昨收价计算：涨幅、实体涨幅、累计成交额、量比
  │
  ├─ 7. 评分引擎 ──→ 计算个股强势得分 + 板块强势得分
  │
  ├─ 8. 存入 SQLite（扫描结果）
  │
  └─ 9. webhook 推送 ──→ 企业微信推送扫描报告
```

---

## ifind API 接口速查表

| 用途 | URL | Method | 关键参数 |
|------|-----|--------|---------|
| 获取 Token | `/api/v1/get_access_token` | POST | Header: refresh_token |
| 更新 Token | `/api/v1/update_access_token` | POST | Header: refresh_token |
| 概念人气明细 | `/api/v1/data_pool` | POST | reportname: p03797 |
| 板块热门成分股 | `/api/v1/data_pool` | POST | reportname: p03798 |
| 历史日K线 | `/api/v1/cmd_history_quotation` | POST | codes, indicators, startdate, enddate, Interval=D |
| 开盘5分钟K线 | `/api/v1/high_frequency` | POST | codes, indicators, starttime=09:30, endtime=09:35 |
| 交易日查询 | `/api/v1/get_trade_dates` | POST | marketcode, functionpara, startdate |

---

## 后期扩展（不在本期范围内）

- 集成 qlib 进行回测分析和策略优化
- 增加 Web UI 可视化展示
- 支持港股通标的
- 增加更多因子（如 MACD、RSI 等技术指标）
- 支持多平台推送（飞书、钉钉等）
