# ifind 接口验证清单

> 基于 [概念板块和人气成分股筛选标准.md](../概念板块和人气成分股筛选标准.md) 和 [iFinD HTTP API 用户手册](./Docs/iFinD_HTTP_API_用户手册.md) 整理。
> 对应 spec Task 0，需要在开发前完成所有接口的连通性和数据格式验证。

---

## 前置条件

- [ ] 用户提供 `refresh_token`

---

## 1. Token 鉴权

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/get_access_token` |
| **Headers** | `{"Content-Type": "application/json", "refresh_token": "<用户的refresh_token>"}` |
| **预期返回** | `{"data": {"access_token": "xxx"}, "errorcode": 0}` |

**验证要点**：
- [ ] 接口连通，返回有效 access_token
- [ ] 记录 access_token 格式和有效期

---

## 2. 概念人气明细（热门板块筛选）

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/data_pool` |
| **Headers** | `{"Content-Type": "application/json", "access_token": "<token>"}` |
| **formData** | 见下方 |

```json
{
    "reportname": "p03797",
    "functionpara": {
        "date": "20260602",
        "tjzq": "近一周"
    },
    "outputpara": "p03797_f001,p03797_f002,p03797_f009,p03797_f010"
}
```

**返回字段说明**：

| 字段 | 含义 | 状态 |
|------|------|------|
| `p03797_f001` | 概念板块名称 | 待验证 |
| `p03797_f002` | 交易日期 | 已确认 |
| `p03797_f009` | 自选热度 | 已确认 |
| `p03797_f010` | 自选热度变化率（%） | 已确认 |

**验证要点**：
- [ ] 接口连通，返回数据非空
- [ ] 确认 `p03797_f001` 是否为概念板块名称
- [ ] 确认 `p03797_f002` 为交易日期，格式正确（YYYYMMDD？）
- [ ] 确认 `p03797_f009` 自选热度数据格式（数值类型、量级）
- [ ] 确认 `p03797_f010` 自选热度变化率数据格式
- [ ] **验证非交易日传参**（如周末 date="20260607"）是否仍返回数据
- [ ] 记录完整返回 JSON 示例

---

## 3. 概念板块热门成分股

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/data_pool` |
| **Headers** | `{"Content-Type": "application/json", "access_token": "<token>"}` |
| **formData** | 见下方 |

```json
{
    "reportname": "p03798",
    "functionpara": {
        "date": "20260602",
        "tjzq": "近一周",
        "hy": "芯片概念"
    },
    "outputpara": "jydm,jydm_mc,p03798_f001,p03798_f012,p03798_f016"
}
```

**返回字段说明**：

| 字段 | 含义 | 状态 |
|------|------|------|
| `jydm` | 交易代码（待确认格式） | 需验证 |
| `jydm_mc` | 交易代码名称 | 需验证 |
| `p03798_f001` | 交易日期 | 已确认 |
| `p03798_f012` | 涨跌幅（%） | 已确认 |
| `p03798_f016` | 区间开始日期 | 已确认 |

**验证要点**：
- [ ] 接口连通，返回数据非空
- [ ] 确认 `jydm` 格式（是否为 `300033.SZ` 还是纯数字 `300033`）
- [ ] 确认 `jydm_mc` 是否为股票中文名
- [ ] 确认 `p03798_f001` 为交易日期
- [ ] 确认 `p03798_f012` 涨跌幅数据格式
- [ ] 确认 `p03798_f016` 为区间开始日期
- [ ] 记录完整返回 JSON 示例

---

## 4. 历史日K线（获取昨收价和近5日OHLCV）

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/cmd_history_quotation` |
| **Headers** | `{"Content-Type": "application/json", "access_token": "<token>"}` |
| **formData** | 见下方 |

```json
{
    "codes": "300033.SZ",
    "indicators": "open,close,high,low,volume,amount",
    "startdate": "2025-05-26",
    "enddate": "2026-06-02",
    "functionpara": {
        "Interval": "D"
    }
}
```

**验证要点**：
- [ ] 接口连通，返回近 5 个交易日日线数据
- [ ] `open/high/low/close` 价格字段完整
- [ ] `volume/amount` 成交量/额字段完整
- [ ] 取最后一根 K 线的 close 作为昨收价，数值合理
- [ ] 验证 startdate/enddate 参数格式
- [ ] 记录完整返回 JSON 示例

---

## 5. 开盘 5 分钟 K 线（盘中实时数据）

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/high_frequency` |
| **Headers** | `{"Content-Type": "application/json", "access_token": "<token>"}` |
| **formData** | 见下方 |

```json
{
    "codes": "300033.SZ",
    "indicators": "open,high,low,close,volume,amount,changeRatio,LB",
    "starttime": "2026-06-02 09:30:00",
    "endtime": "2026-06-02 09:35:00",
    "functionpara": {
        "Interval": "1"
    }
}
```

**所有评分因子均从 5 分钟 K 线 + 日 K 线组合获取**：

| 计算指标 | 数据来源 | 计算方式 | 说明 |
|---------|---------|---------|------|
| 昨收价 (preClose) | cmd_history_quotation | 上一交易日日 K 的 `close` | 可靠的昨收价来源 |
| 涨幅 | 组合计算 | `(最后close - preClose) / preClose × 100%` | 相对昨收 |
| 实体涨幅 | high_frequency | `(最后close - 第1根open) / 第1根open × 100%` | 日内走势 |
| 成交额 | high_frequency | 5 根 K 线 `amount` 求和 | 开盘 5 分钟 |
| 量比 | high_frequency | `LB` 指标 | API 技术指标 |

**验证要点**：
- [ ] 接口连通，返回 09:30~09:35 的 5 根 1 分钟 K 线
- [ ] `open/high/low/close` 价格字段完整
- [ ] `volume/amount` 成交量/额字段完整
- [ ] `changeRatio` 涨跌幅字段完整
- [ ] `LB`（量比）技术指标字段存在且数值合理
- [ ] 返回数据条数 = 5 条（每分钟 1 条）
- [ ] 记录完整返回 JSON 示例

---

## 6. 交易日判断

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/get_trade_dates` |
| **Headers** | `{"Content-Type": "application/json", "access_token": "<token>"}` |
| **formData** | 见下方 |

```json
{
    "marketcode": "212001",
    "functionpara": {
        "mode": "1",
        "dateType": "0",
        "dateFormat": "0",
        "period": "D"
    },
    "startdate": "2026-06-01",
    "enddate": "2026-06-03"
}
```

**验证要点**：
- [ ] 接口连通，返回交易日列表
- [ ] 交易日返回对应日期，非交易日不返回
- [ ] 用已知非交易日（如周末）测试返回空
- [ ] 记录完整返回 JSON 示例

---

## 验证结果汇总

| # | 接口 | 状态 | 备注 |
|---|------|------|------|
| 1 | Token 鉴权 | 待验证 | |
| 2 | 概念人气明细 (p03797) | 待验证 | 默认统计周期：近一周 |
| 3 | 板块热门成分股 (p03798) | 待验证 | 默认统计周期：近一周 |
| 4 | 历史日K线 (cmd_history_quotation) | 待验证 | 获取昨收价 + 近5日OHLCV |
| 5 | 开盘 5 分钟 K 线 (high_frequency) | 待验证 | 含 LB 量比 |
| 6 | 交易日判断 | 待验证 | |

> 验证完成后，将每个接口的实际返回 JSON 记录到本文档末尾，并更新状态列。
