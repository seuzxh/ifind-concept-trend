# 概念板块强势扫描系统 (Concept Trend Scanner)

每日 9:36 自动扫描 A 股热门概念板块和个股，基于多因子评分快速定位强势启动标的，辅助短线买卖决策。

## 功能概览

- **人气数据同步**：每日通过 ifind API 获取概念人气明细（p03797）和板块热门成分股（p03798），自动筛选观察股池
- **智能预查**：所有 API 调用前先查 SQLite，已有数据则跳过下载，避免重复请求消耗配额
- **多因子评分**：基于涨幅、实体涨幅、成交额、量比四个因子加权计算个股/板块强势得分
- **结果推送**：通过企业微信 Webhook 推送 Top 5 板块 + Top 10 个股扫描报告
- **定时 + 手动**：支持 APScheduler 定时调度和 CLI 手动触发

## 项目结构

```
scanner/                 # 主包
├── __init__.py
├── __main__.py          # CLI 入口
├── config.py            # 配置加载（YAML + 环境变量）
├── client.py            # ifind HTTP API 客户端
├── models.py            # 数据模型（dataclass）
├── db.py                # SQLite 数据存储层（含预查方法）
├── sync.py              # 数据同步编排（含预查逻辑）
├── scorer.py            # 多因子综合评分引擎
└── scheduler.py         # 扫描调度器（每日同步 + 盘中扫描）
config/
└── config.yaml.template # 配置文件模板
tests/
├── verify_api.py        # 接口验证脚本
├── fetch_today.py       # 数据采集脚本
├── verify_scorer.py     # 评分引擎验证脚本
└── verify_sync_scheduler.py  # 预查+调度验证脚本
data/                    # SQLite 数据库（gitignore）
Docs/                    # API 文档和设计文档
```

## 快速开始

### 1. 环境准备

```bash
# 创建 conda 环境
conda create -n concept-trend python=3.10 -y
conda activate concept-trend

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置模板
copy config\config.yaml.template config\config.yaml

# 创建 .env 文件并设置 refresh_token
copy .env.example .env
# 编辑 .env，填入 IFIND_REFRESH_TOKEN=your_token_here
```

### 3. 运行

```bash
# 手动扫描
python -m scanner scan

# 启动定时服务
python -m scanner serve

# 手动数据同步
python -m scanner sync
```

## 数据流程

### 每日同步（交易日盘前 9:00，由 `DataSync` 编排）

```
data_pool(p03797) → 全部概念人气明细
    └─ 筛选：热度 Top20 + 变化率 Top20 → 按名称去重 → 热门板块列表
data_pool(p03798) → 逐板块获取成分股
    └─ 筛选：每板块涨跌幅 Top30 → 剔除 ST → 合并去重 → 观察股池
cmd_history_quotation → 预查 SQLite → 仅对缺失股票获取日K线
全部写入 SQLite
```

### 交易日盘中 9:36（由 `Scanner` 编排）

```
get_trade_dates → 判断是否交易日（非交易日跳过）
预查 SQLite → 筛选已有日K线/1min数据的股票
cmd_history_quotation → 仅对缺失股票获取 T-1 日日K线（昨收价）
high_frequency → 仅对缺失股票获取开盘 5 分钟实时行情
多因子评分 → 个股强势得分 + 板块强势得分
webhook → 推送扫描报告至企业微信
```

## 数据预查机制

所有 API 调用前先查询 SQLite 判断数据是否已存在：

| 表 | 预查逻辑 | 跳过条件 |
|----|---------|---------|
| kline_daily | `find_stocks_with_daily(date, codes)` | 该日期已有日K线记录 |
| kline_1min | `find_stocks_with_1min(date, codes, min_bars=5)` | 该日期已有 ≥5 条 1min K线 |

- 预查命中时跳过 API 调用，记录 skip 日志
- 支持 `force=True` 参数绕过预查强制刷新

## 观察股池筛选逻辑

1. **概念板块筛选**：从 p03797 全部概念中，按自选热度取 Top20 + 按自选热度变化率取 Top20，按板块名称合并去重（约 40 个板块）
2. **成分股筛选**：每个板块按涨跌幅（p03798_f012）降序取 Top30，剔除 ST 股，所有板块个股合并去重（约 500~600 只）

## 评分因子

| 因子 | 权重 | 说明 |
|------|------|------|
| 涨幅 | 0.25 | (当前价 - 昨收) / 昨收 × 100% |
| 实体涨幅 | 0.30 | (当前价 - 开盘价) / 开盘价 × 100% |
| 成交额 | 0.20 | 开盘 5 分钟累计成交额（百分位归一化） |
| 量比 | 0.25 | high_frequency LB 指标（需 calculate: {"LB": "5"}） |

- 评分方式：每个因子在当批股票中做百分位归一化（0-100），再加权求和
- 强势标记：涨幅 > 7% 或实体涨幅 > 5% 的个股标记为"强势"
- 板块评分：强势占比 × 60% + 板块平均得分 × 40%

所有权重和阈值可在 `config/config.yaml` 中调整。

## ifind API 接口

| 用途 | 接口 | 关键参数 |
|------|------|---------|
| 鉴权 | `POST /api/v1/get_access_token` | Header: refresh_token |
| 概念人气明细 | `POST /api/v1/data_pool` | p03797, functionpara: date/tjzq |
| 板块热门成分股 | `POST /api/v1/data_pool` | p03798, functionpara: date/hy/tjzq |
| 历史日K线 | `POST /api/v1/cmd_history_quotation` | Interval=D |
| 开盘5分钟K线 | `POST /api/v1/high_frequency` | calculate: {"LB": "5"} |
| 交易日查询 | `POST /api/v1/get_trade_dates` | marketcode: 212001 |

## SQLite 表结构

| 表 | 用途 | 写入时机 |
|----|------|---------|
| concept_popularity | 概念人气明细 | 交易日盘前 9:00 |
| board_stock_relation | 板块-个股关联 | 交易日盘前 9:00 |
| kline_daily | 日K线数据 | 交易日盘中 |
| kline_1min | 1分钟K线数据 | 交易日盘中 |
| stock_daily_scan | 个股扫描结果 | 交易日盘中 |
| board_daily_scan | 板块扫描结果 | 交易日盘中 |

详细设计见 [sqlite数据库设计.md](Docs/sqlite数据库设计.md)。

## 推送报告

扫描完成后通过企业微信群机器人 Webhook 推送 Markdown 格式报告，采用两段式结构：

**第一段：Top 10 强势个股（按板块归类）**
- 个股按 score 降序取 Top 10，每只归入其所属板块中 board_score 最高的板块
- 按板块分组显示，全局编号 1~10 连续，强势个股加粗

**第二段：Top 5 强势板块（含 Top 5 成分股）**
- 板块按 board_score 降序取 Top 5，每个板块展示归属个股 Top 5
- 板块头显示排名、得分、强势个股数/总数

详细模板见 [推送报告模板.md](Docs/推送报告模板.md)。

## 核心模块

| 模块 | 类 | 职责 |
|------|-----|------|
| `scanner/client.py` | `IfindClient` | ifind HTTP 客户端（鉴权、限流、列式解析） |
| `scanner/db.py` | `Database` | SQLite 持久化（DDL、upsert、预查、查询） |
| `scanner/sync.py` | `DataSync` | 数据同步编排（人气/成分股/K线 + 预查跳过） |
| `scanner/scorer.py` | `ScoringEngine` | 多因子评分引擎（归一化 + 加权 + 强势标记） |
| `scanner/scheduler.py` | `Scanner` | 扫描调度器（每日同步 + 盘中扫描编排） |
| `scanner/config.py` | `Config` | 配置加载（YAML + 环境变量） |

## 文档索引

### 设计文档（`Docs/`）
- [SQLite 数据库设计](Docs/sqlite数据库设计.md)
- [推送报告模板](Docs/推送报告模板.md)
- [接口验证清单](Docs/ifind接口验证清单.md)
- [ifind API 用户手册](Docs/iFinD_HTTP_API_用户手册.md)

### 产品规格（`.trae/specs/`）
- [产品规格 Spec](.trae/specs/build-concept-trend-scanner/spec.md)
- [任务拆解 Tasks](.trae/specs/build-concept-trend-scanner/tasks.md)
- [验证清单 Checklist](.trae/specs/build-concept-trend-scanner/checklist.md)

### 智能体规则（`.trae/rules/`）
- [项目规则](.trae/rules/project_rules.md)
- [数据库 API 规则](.trae/rules/database_api.md)

## 开发进度

- [x] Task 0: 接口预验证（6 个接口全部通过）
- [x] Task 1: 项目基础结构搭建
- [x] Task 2: ifind API 数据采集模块
- [x] Task 3: SQLite 数据存储模块（含数据预查逻辑）
- [x] Task 4: 多因子综合评分引擎（561 只个股 + 40 个板块评分验证通过）
- [ ] Task 5: 结果推送模块
- [x] Task 6.2: 盘中扫描编排（Scanner + DataSync + 预查）
- [ ] Task 6: 扫描调度器（剩余 6.1/6.3/6.4）
- [ ] Task 7: CLI 命令行入口
- [ ] Task 8: 端到端集成测试

## 后期扩展

- 集成 qlib 回测分析
- Web UI 可视化
- 更多技术指标因子（MACD、RSI）
- 多平台推送（飞书、钉钉）
