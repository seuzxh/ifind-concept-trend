# 行业板块接口升级 Spec

## Why
当前系统使用 p03797/p03798 获取"概念板块"人气数据，需切换为 p03793/p03794 获取"同花顺三级行业"人气数据，以获取更精准的行业分类数据。

## What Changes
- p03797（概念人气明细）→ p03793（行业人气明细）
- p03798（板块热门成分股）→ p03794（行业人气明细-当月推荐明细）
- 新增 `hyfl` 参数（行业分类，固定值 `同花顺三级行业`）
- 字段名从 `p03797_*` 变更为 `p03793_*`，`p03798_*` 变更为 `p03794_*`

## Impact
- Affected code: `scanner/client.py`（接口调用）、`scanner/sync.py`（字段解析）、`scanner/db.py`（表注释）、`scanner/models.py`（模型注释）
- Affected docs: `spec.md`、`README.md`、`Docs/ifind接口验证清单.md`

## MODIFIED Requirements

### Requirement: 行业人气明细接口（原概念人气明细）

#### Scenario: 获取行业人气排名
- **WHEN** 调用 `get_concept_popularity(date)`
- **THEN** 请求 `POST /api/v1/data_pool`，参数为：
  - reportname: `p03793`
  - functionpara: `{"date": date, "hyfl": "同花顺三级行业", "tjzq": "近一周"}`
  - outputpara: `p03793_f001,p03793_f002,p03793_f009,p03793_f010`
- **AND** 字段映射：
  - `p03793_f001` → 行业名称（原 `p03797_f001` 概念名称）
  - `p03793_f002` → 交易日期
  - `p03793_f009` → 自选热度
  - `p03793_f010` → 自选热度变化率

### Requirement: 行业成分股接口（原板块热门成分股）

#### Scenario: 获取行业成分股
- **WHEN** 调用 `get_board_stocks(date, concept_name)`
- **THEN** 请求 `POST /api/v1/data_pool`，参数为：
  - reportname: `p03794`
  - functionpara: `{"date": date, "hyfl": "同花顺三级行业", "tjzq": "近一周", "hy": concept_name}`
  - outputpara: `jydm,jydm_mc,p03794_f001,p03794_f012,p03794_f016`
- **AND** 字段映射：
  - `jydm` → 交易代码
  - `jydm_mc` → 交易代码名称
  - `p03794_f001` → 交易日期
  - `p03794_f012` → 涨跌幅
  - `p03794_f016` → 区间开始日期
