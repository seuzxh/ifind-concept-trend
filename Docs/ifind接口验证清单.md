# ifind 接口验证清单

> 基于 [spec](../.trae/specs/build-concept-trend-scanner/spec.md) 和 [iFinD HTTP API 用户手册](./iFinD_HTTP_API_用户手册.md) 整理。
> 对应 spec Task 0，需要在开发前完成所有接口的连通性和数据格式验证。

---

## 前置条件

- [x] 用户提供 `refresh_token`

---

## 1. Token 鉴权

| 项目 | 内容 |
|------|------|
| **接口** | `POST https://quantapi.51ifind.com/api/v1/get_access_token` |
| **Headers** | `{"Content-Type": "application/json", "refresh_token": "<用户的refresh_token>"}` |
| **预期返回** | `{"data": {"access_token": "xxx", "expired_time": "YYYY-MM-DD HH:MM:SS"}, "errorcode": 0}` |

**验证结果**：
- [x] 接口连通，返回有效 access_token
- [x] access_token 格式：`<32位hex>.signs_NjM0ODM2NDI5`
- [x] expired_time 格式：`"YYYY-MM-DD HH:MM:SS"`（如 `"2026-06-03 23:01:07"`）

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

> **注意**：`functionpara` 中的键名必须是 `date` 和 `tjzq`，
> 不能使用 `p03797_f002` / `p03797_f003`（会返回 -4001 no data）。

**返回字段说明**：

| 字段 | 含义 | 验证结果 |
|------|------|---------|
| `p03797_f001` | 概念板块名称（如 "芯片概念"） | 已确认 |
| `p03797_f002` | 交易日期（格式 `YYYY/MM/DD`） | 已确认 |
| `p03797_f009` | 自选热度（字符串数值，如 "39833.55"） | 已确认 |
| `p03797_f010` | 自选热度变化率（字符串数值） | 已确认 |

**数据格式**：列式数组，每个字段对应一个值数组，
非行式 `table_data` 字典列表。示例：
```json
{
  "tables": [{
    "table": {
      "p03797_f001": ["芯片概念", "国企改革", ...],
      "p03797_f002": ["2026/06/02", "2026/06/02", ...],
      "p03797_f009": ["39833.55110000", "33140.83080000", ...],
      "p03797_f010": ["0.2352...", "0.1084...", ...]
    }
  }]
}
```

**验证要点**：
- [x] 接口连通，返回数据非空（约 380+ 个概念板块）
- [x] 确认 `p03797_f001` 为概念板块名称
- [x] 确认 `p03797_f002` 格式为 `YYYY/MM/DD`
- [x] 确认 `p03797_f009` / `p03797_f010` 为字符串数值

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

> **注意**：`functionpara` 键名必须是 `date` / `hy` / `tjzq`，
> 不能使用 `p03798_f001` / `p03798_f002` / `p03798_f003`。

**返回字段说明**：

| 字段 | 含义 | 验证结果 |
|------|------|---------|
| `jydm` | 交易代码（格式 `600584.SH`） | 已确认 |
| `jydm_mc` | 股票中文名 | 已确认 |
| `p03798_f001` | 交易日期（格式 `YYYY/MM/DD`） | 已确认 |
| `p03798_f012` | 涨跌幅（数值） | 已确认 |
| `p03798_f016` | 区间开始日期（格式 `YYYY/MM/DD`） | 已确认 |

**数据格式**：列式数组（同 p03797）。

**验证要点**：
- [x] 接口连通，返回数据非空
- [x] 确认 `jydm` 格式为 `XXXXXX.SH/SZ`

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
    "startdate": "2026-05-26",
    "enddate": "2026-06-02",
    "functionpara": {
        "Interval": "D"
    }
}
```

**数据格式**：列式数组。`thscode` 和 `time` 在
`tables[0]` 外层，指标数据在 `tables[0].table` 内。
```json
{
  "tables": [{
    "thscode": "300033.SZ",
    "time": ["2026-05-26", ..., "2026-06-02"],
    "table": {
      "open": [232, 239.75, ...],
      "close": [241.91, 238.99, ..., 226.23],
      "volume": [11559300, ...],
      "amount": [2690062580, ...]
    }
  }]
}
```

**验证要点**：
- [x] 接口连通，返回 6 个交易日数据
- [x] `open/high/low/close` 价格字段完整
- [x] `volume/amount` 成交量/额字段完整
- [x] 最后一根 K 线 close = 226.23（2026-06-02）

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
    "indicators": "LB,open,high,low,close,volume,amount,changeRatio",
    "functionpara": {
        "Fill": "Original",
        "Interval": "1",
        "calculate": {
            "LB": "5"
        }
    },
    "starttime": "2026-06-02 09:30:00",
    "endtime": "2026-06-02 09:35:00"
}
```

> **关键**：`LB` 量比指标需要在 `functionpara.calculate`
> 中指定计算参数 `{"LB": "5"}`（5日周期），
> 否则 API 会静默忽略该指标不返回数据。

**数据格式**：列式数组（同上）。LB 作为 table 中的
一个字段返回，值为浮点数。

```json
{
  "tables": [{
    "thscode": "300033.SZ",
    "time": ["2026-06-02 09:30", ..., "2026-06-02 09:35"],
    "table": {
      "open": [227.98, 227.87, 224.51, 222.79, 221.8, 222.1],
      "close": [227.98, 224.9, 222.69, 222.34, 222.01, 222.79],
      "volume": [34700, 407180, 675200, 648280, 555843, 280964],
      "amount": [7910906, 91982651.8, ...],
      "changeRatio": [-0.3889, -1.351, ...],
      "LB": [0.426, 2.714, 4.574, 5.421, 5.703, 5.327]
    }
  }]
}
```

**验证要点**：
- [x] 接口连通，返回 6 根 1 分钟 K 线（09:30~09:35）
- [x] `open/high/low/close` 价格字段完整
- [x] `volume/amount` 成交量/额字段完整
- [x] `changeRatio` 涨跌幅字段完整
- [x] `LB` 量比字段存在且数值合理（范围 0.43 ~ 5.70）

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
    "startdate": "2026-05-30",
    "enddate": "2026-06-03"
}
```

**数据格式**：`tables` 为字典（非列表），`time` 键
直接包含日期字符串列表。
```json
{
  "tables": {
    "time": ["2026-06-01", "2026-06-02", "2026-06-03"]
  }
}
```

**验证要点**：
- [x] 接口连通，返回交易日列表
- [x] 2026-05-30（周六）和 2026-05-31（周日）不在返回中
- [x] 返回 2026-06-01、06-02、06-03 三个交易日

---

## 验证结果汇总

| # | 接口 | 状态 | 备注 |
|---|------|------|------|
| 1 | Token 鉴权 | **通过** | access_token 有效期 7 天 |
| 2 | 概念人气明细 (p03797) | **通过** | 列式数组；需用 `date`/`tjzq` 参数 |
| 3 | 板块热门成分股 (p03798) | **通过** | 列式数组；需用 `date`/`hy`/`tjzq` 参数 |
| 4 | 历史日K线 (cmd_history_quotation) | **通过** | 列式数组；thscode/time 在外层 |
| 5 | 开盘 5 分钟 K 线 (high_frequency) | **通过** | LB 需 `calculate: {LB: "5"}` 参数 |
| 6 | 交易日判断 | **通过** | tables 为 dict，非 list |

### 已修复的代码问题

1. **p03797/p03798 functionpara 参数名**：
   client.py 从 `p03797_f002` 改为 `date`，从 `p03798_f001` 改为 `date`
2. **数据解析器**：`_extract_table_rows` 从行式解析改为列式数组转置
3. **交易日解析器**：`_extract_date_list` 支持 `tables.time` 字典格式
4. **high_frequency functionpara**：添加 `Fill: "Original"` 和 `calculate: {LB: "5"}`
