# 概念板块强势扫描系统 (Concept Trend Scanner)

每日 9:36 自动扫描 A 股热门概念板块和个股，基于多因子评分快速定位强势启动标的，辅助短线买卖决策。

## 功能概览

- **人气数据同步**：每日通过 ifind API 获取概念人气明细（p03797）和板块热门成分股（p03798），自动筛选监控标的池
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
└── db.py                # SQLite 数据存储层
config/
└── config.yaml.template # 配置文件模板
tests/
data/                    # SQLite 数据库（gitignore）
Docs/                    # API 文档
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

# 设置环境变量（refresh_token）
set IFIND_REFRESH_TOKEN=your_refresh_token_here
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

```
每日同步（含非交易日）
  │
  ├─ data_pool(p03797) → 概念人气明细 → 筛选热门板块
  ├─ data_pool(p03798) → 板块成分股 → 剔除ST → 监控标的池
  └─ 存入 SQLite

交易日 9:36
  │
  ├─ cmd_history_quotation → 日K线（获取昨收价）
  ├─ high_frequency → 开盘5分钟K线（涨幅、实体涨幅、成交额、量比）
  ├─ 多因子评分 → 个股得分 + 板块得分
  └─ Webhook 推送报告
```

## 评分因子

| 因子 | 权重 | 说明 |
|------|------|------|
| 涨幅 | 0.25 | (当前价 - 昨收) / 昨收 |
| 实体涨幅 | 0.30 | (当前价 - 开盘价) / 开盘价 |
| 成交额 | 0.20 | 开盘 5 分钟累计成交额 |
| 量比 | 0.25 | high_frequency LB 指标 |

所有权重和阈值可在 `config/config.yaml` 中调整。

## ifind API 接口

| 用途 | 接口 |
|------|------|
| 鉴权 | `POST /api/v1/get_access_token` |
| 概念人气明细 | `POST /api/v1/data_pool` (p03797) |
| 板块热门成分股 | `POST /api/v1/data_pool` (p03798) |
| 历史日K线 | `POST /api/v1/cmd_history_quotation` |
| 开盘5分钟K线 | `POST /api/v1/high_frequency` |
| 交易日查询 | `POST /api/v1/get_trade_dates` |

## SQLite 表结构

| 表 | 用途 | 写入时机 |
|----|------|---------|
| concept_popularity | 概念人气明细 | 每日（含非交易日） |
| board_stock_relation | 板块-个股关联 | 每日（含非交易日） |
| kline_daily | 日K线数据 | 交易日盘中 |
| kline_1min | 1分钟K线数据 | 交易日盘中 |
| stock_daily_scan | 个股扫描结果 | 交易日盘中 |
| board_daily_scan | 板块扫描结果 | 交易日盘中 |

详细设计见 [sqlite数据库设计.md](sqlite数据库设计.md)。

## 文档索引

### 设计文档（`Docs/`）
- [SQLite 数据库设计](Docs/sqlite数据库设计.md)
- [接口验证清单](Docs/ifind接口验证清单.md)
- [ifind API 用户手册](Docs/iFinD_HTTP_API_用户手册.md)

### 产品规格（`.trae/specs/`）
- [产品规格 Spec](.trae/specs/build-concept-trend-scanner/spec.md)
- [任务拆解 Tasks](.trae/specs/build-concept-trend-scanner/tasks.md)
- [验证清单 Checklist](.trae/specs/build-concept-trend-scanner/checklist.md)

## 后期扩展

- 集成 qlib 回测分析
- Web UI 可视化
- 更多技术指标因子（MACD、RSI）
- 多平台推送（飞书、钉钉）
