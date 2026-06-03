# iFinD HTTP API 用户手册

| 版本 | 时间 | 更新说明 |
| --- | --- | --- |
| 1.0 | 2021-12-29 | 初版发布 |
| 2.0 | 2024-03-29 | 迭代版本 |
| 2.1 | 2025-08-25 | 说明修正 |

## 目录

- 一、TOKEN获取与使用
  - 1、refresh token说明
  - 2、access token说明
    - 1）、获取当前有效的access token
    - 2）、获取一个新的access token
    - 3）、使用access token向同花顺服务器取数
- 二、各函数URL及formData生成逻辑
  - 1、基础数据
  - 2、日期序列
  - 3、历史行情
  - 4、高频序列
  - 5、实时行情
  - 6、经济数据库(EDB)
  - 7、专题报表函数
  - 8、组合管理
    - (1）组合新建
    - (2）组合导入
      - 1).模板导入
      - 2).文件导入
      - 3).状态查询
    - (3)现金存取
    - (4)普通交易
    - (5)交易流水
    - (6)组合监控
    - (7)持仓分析
    - (8)绩效指标
    - (9)风险指标
  - 9、智能选股
  - 10、基金实时估值(分钟)
  - 11、基金实时估值(日)
  - 12、日期查询函数
  - 13、日期偏移函数
  - 14、数据量查询
  - 15、错误信息查询
  - 16、证券代码证券简称转同花顺代码
  - 17、公告查询
- 三、错误说明
- 四、适用范围
- 五、版本管理

---

iFinD HTTPAPI是对过去各语言SDK形式的一个补充，用户可以以API形式直接向同花顺服务器发送HTTP请求，运行环境不再需要下载SDK，从而使用户摆脱设备、语言、环境的限制。

## 一、TOKEN获取与使用

接口鉴权方案分为长期的refresh_token和短期的access_token。

### 1、refresh token说明

**作用：** refresh_token只用来请求当前有效的access_token或者获取一个新access_token。

**有效期：** refresh_token与获取时账号到期日一致，如账号有续期或者权限变更，需要更新refresh_token来更新权限。

**获取方式：** refresh_token可以通过Windows接口包中超级命令客户端"工具-refresh_token查询/更新"或者网页版本超级命令-账号信息查看或者更新。

**注意：** refresh_token更新后，所有环境过去的refresh_token、access_token均会失效，更新refresh_token相当于更改HTTP接口的账号密码。

### 2、access token说明

**作用：** access_token用来直接向同花顺服务器请求数据。

**有效期：** access_token会在初次生成的七天后失效。

**注意：** 单个access_token最多支持绑定20个IP。

#### 1）、获取当前有效的access token

请求参数

| 项目 | 传参说明 |
| --- | --- |
| URL | https://quantapi.51ifind.com/api/v1/get_access_token |
| requestMethod | POST/GET |
| requestHeaders | {"Content-Type":"application/json","refresh_token":user_refresh_token} |

注：refresh_token放BODY也可

#### 2）、获取一个新的access_token

获取一个新的access_token会造成所有旧的access_token失效

请求参数

| 项目 | 传参说明 |
| --- | --- |
| URL | https://quantapi.51ifind.com/api/v1/update_access_token |
| requestMethod | POST/GET |
| requestHeaders | {"Content-Type":"application/json","refresh_token":user_refresh_token} |

示例——使用python请求当前有效的access_token

```python
import requests
import json
getAccessTokenUrl = 'https://quantapi.51ifind.com/api/v1/get_access_token'
refreshToken = 'eyJzaWduX3RpbWUiOiIyMDIxLTEyduX3RpbWUiOiIyMjI1In0=.eyJ1aWQiOiIxMDYxMDUwMDMifQ==.F4CBBBC230969B0F220F9D6ECB666A230969B0F220FFBBCDA4156A3B78A1BB896'
getAccessTokenHeader = {"Content-Type": "application/json", "refresh_token": refreshToken}
getAccessTokenResponse = requests.post(url=getAccessTokenUrl, headers=getAccessTokenHeader)
accessToken = json.loads(getAccessTokenResponse.content)['data']['access_token']
print(accessToken)
```

#### 3）、使用access_token向同花顺服务器取数

**使用超级命令协助获取协议**

基础函数、日期序列函数、EDB函数、专题报表函数的指标与科目过多，很难把所有内容都集中在文档中，目前还是推荐用户使用WindowsSDK接口包中的超级命令终端或者网页版本超级命令协助获取协议。

**协议说明**

- requestMethod需要为POST
- requestHeaders需要包含`{"Content-Type":"application/json","access_token":user_access_token}`
- 各函数的formData或者requestURL见下方协议或者使用超级命令生成
- 请求参数需要统一处理为urlencode，请求参数压缩支持：`Accept-Encoding: gzip,deflate`
- 返回内容统一为unicode编码

示例——以Python请求300033实时行情为例

```python
# -*- coding: utf-8 -*-
import requests
thsUrl = 'https://quantapi.51ifind.com/api/v1/real_time_quotation'
accessToken = '12fe737bc2014f39f195a2b7b03e3b11ec63b66b'
thsHeaders = {"Content-Type": "application/json", "access_token": accessToken}
thsPara = {"codes": "300033.SZ", "indicators": "open,high,low,latest"}
thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
print(thsResponse.content)
```

## 二、各函数URL及formData生成逻辑

### 1、基础数据

**URL**

```
https://quantapi.51ifind.com/api/v1/basic_data_service
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"300033.SZ,600030.SH"` |
| indipara | 是 | 各个指标及其相关参数，indicator代表指标英文名，indiparams代表该指标的用户层的参数，otherparams代表用户无需知晓但传输给服务端所需的其他参数。otherparams中sys用来标记服务端所需的name中为True的参数。推荐使用超级命令生成。 | 见下方代码块 |

**示例**

```python
para = {
    "codes": "300033.SZ,600030.SH",
    "indipara": [{
        "indicator": "ths_roe_stock",
        "indiparams": ["20241231"]
    }, {
        "indicator": "ths_roe_avg_by_ths_stock",
        "indiparams": ["20241231"]
    }]
}
```

该示例表示提取同花顺和中信证券在2024年年报的净资产收益率ROE;净资产收益率ROE(平均,同花顺计算)

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括thscode、table（具体的数据内容）等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 2、日期序列

**URL**

```
https://quantapi.51ifind.com/api/v1/date_sequence
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"300033.SZ,600030.SH"` |
| functionpara | 否 | key-value格式。所有key均取默认时，functionpara省略。 | 见下方说明 |
| startdate | 是 | 开始日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种日期格式 | `"startdate":"2018-01-01"` |
| enddate | 是 | 结束日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种日期格式 | `"enddate":"2018-01-01"` |
| indipara | 是 | 各个指标及其相关参数，indicator代表指标英文名，indiparams代表该指标的用户层的参数，otherparams代表用户无需知晓但传输给服务端所需的其他参数。otherparams中sys用来标记服务端所需的name中为True的参数。推荐使用Windows超级命令生成。 | 见下方代码块 |

**functionpara说明**

| 名称 | keys | value说明 | 省略时逻辑 |
| --- | --- | --- | --- |
| 时间周期 | Interval | D-日 W-周 M-月 Q-季 S-半年 Y-年 | D-日 |
| 日期类型 | Days | Tradedays-交易日 Alldays-日历日 | Tradedays-交易日 |
| 非交易间隔处理 | Fill | Previous-沿用之前数据 Blank-空值 | Previous-沿用之前数据 |

**示例**

```python
para = {
    "codes": "300033.SZ,600030.SH",
    "startdate": "20230101",
    "enddate": "20241231",
    "functionpara": {
        "Days": "Alldays",
        "Fill": "Blank",
        "Interval": "Y"
    },
    "indipara": [{
        "indicator": "ths_total_equity_atoopc_stock",
        "indiparams": ["", "100"]
    }, {
        "indicator": "ths_regular_report_actual_dd_stock",
        "indiparams": [""]
    }]
}
```

该示例表示提取同花顺和中信证券在2023-24年年报的归属于母公司所有者权益合计;定期报告实际披露日期

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括thscode、table（具体的数据内容）等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 3、历史行情

**URL**

```
https://quantapi.51ifind.com/api/v1/cmd_history_quotation
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"300033.SZ,600030.SH"` |
| indicators | 是 | 半角逗号分隔的所有指标 | `"indicators":"preClose,open"` |
| functionpara | 否 | key-value格式。所有key均取默认时，functionpara省略。 | 见下方说明 |
| startdate | 是 | 开始日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种日期格式 | `"startdate":"2018-01-01"` |
| enddate | 是 | 结束日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种日期格式 | `"enddate":"2018-01-01"` |

**indicators参数说明**

| 指标名 | 指标说明 | 指标备注 |
| --- | --- | --- |
| preClose | 前收盘价 |  |
| open | 开盘价 |  |
| high | 最高价 |  |
| low | 最低价 |  |
| close | 收盘价 |  |
| avgPrice | 均价 |  |
| change | 涨跌 |  |
| changeRatio | 涨跌幅 |  |
| volume | 成交量 |  |
| amount | 成交额 |  |
| turnoverRatio | 换手率 |  |
| transactionAmount | 成交笔数 |  |
| totalShares | 总股本 |  |
| totalCapital | 总市值 |  |
| floatSharesOfAShares | A股流通股本 |  |
| floatSharesOfBShares | B股流通股本 |  |
| floatCapitalOfAShares | A股流通市值 |  |
| floatCapitalOfBShares | B股流通市值 |  |
| pe_ttm | 市盈率（TTM） |  |
| pe | PE市盈率 |  |
| pb | PB市净率 |  |
| ps | PS市销率 |  |
| pcf | PCF市现率 |  |
| ths_trading_status_stock | 交易状态 |  |
| ths_up_and_down_status_stock | 涨跌停状态 |  |
| ths_af_stock | 复权因子 |  |
| ths_vol_after_trading_stock | 盘后成交量 |  |
| ths_trans_num_after_trading_stock | 盘后成交笔数 |  |
| ths_amt_after_trading_stock | 盘后成交额 |  |
| ths_vaild_turnover_stock | 有效换手率 |  |
| netAssetValue | 单位净值 | 基金专用 |
| adjustedNAV | 复权单位净值 | 基金专用 |
| accumulatedNAV | 累计单位净值 | 基金专用 |
| premium | 贴水 | 基金专用 |
| premiumRatio | 贴水率 | 基金专用 |
| estimatedPosition | 估算仓位 | 基金专用 |
| floatCapital | 流通市值 | 指数专用 |
| pe_ttm_index | PE(TTM) | 指数专用 |
| pb_mrq | PB(MRQ) | 指数专用 |
| pe_indexPublisher | PE(指数发布方） | 指数专用 |
| yieldMaturity | 到期收益率 | 债券专用 |
| remainingTerm | 剩余期限 | 债券专用 |
| maxwellDuration | 麦氏久期 | 债券专用 |
| modifiedDuration | 修正久期 | 债券专用 |
| convexity | 凸性 | 债券专用 |
| close_2330 | 收盘价（23：30） | 外汇交易中心专用 |
| openInterest | 持仓量 | 期权专用 |
| positionChange | 持仓变动 | 期权专用 |
| preSettlement | 前结算价 | 期货专用 |
| settlement | 结算价 | 期货专用 |
| change_settlement | 涨跌（结算价） | 期货专用 |
| chg_settlement | 涨跌幅（结算价） | 期货专用 |
| openInterest | 持仓量 | 期货专用 |
| positionChange | 持仓变动 | 期货专用 |
| amplitude | 振幅 | 期货专用 |

**functionpara参数说明**

| 名称 | keys | value说明 | 省略时逻辑 |
| --- | --- | --- | --- |
| 时间周期 | Interval | D-日 W-周 M-月 Q-季 S-半年 Y-年 同抽样周期二选一，返回周期汇总统计值 | D-日 |
| 抽样周期 | SampleInterval | D-日 W-周 M-月 Q-季 S-半年 Y-年 同时间周期二选一，返回周期最后一个交易日日频数据 | D-日 |
| 复权方式 | CPS | 1-不复权 2-前复权（分红再投） 3-后复权（分红再投） 4-全流通前复权（分红再投） 5-全流通后复权（分红再投） 6-前复权（现金分红） 7-后复权（现金分红） | 1-不复权 |
| 报价类型 | PriceType | 1-全价 2-净价 仅债券生效 | 1-全价 |
| 非交易间隔处理 | Fill | Previous-沿用之前数据 Blank-空值 具体数值-自定义数值 Omit-缺省值 | Previous-沿用之前数据 |
| 设定复权基点 | BaseDate | 复权基点日期，"YYYY-MM-DD" | 后复权按上市日，前复权按最新日 |
| 货币 | Currency | MHB-美元 GHB-港元 RMB-人民币 YSHB-原始货币 | YSHB-原始货币 |

**示例**

```python
para = {
    "codes": "300033.SZ,600030.SH",
    "indicators": "open,close,volume",
    "startdate": "2024-08-25",
    "enddate": "2025-08-25",
    "functionpara": {
        "Interval": "W",
        "CPS": "3",
        "Currency": "RMB",
        "Fill": "Blank"
    }
}
```

该示例表示提取同花顺和中信证券在20240825-20250825年周频率的开盘价、收盘价、成交量后复权分红再投数据

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括thscode、table（具体的数据内容）等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 4、高频序列

**URL**

```
https://quantapi.51ifind.com/api/v1/high_frequency
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"300033.SZ,600030.SH"` |
| indicators | 是 | 半角逗号分隔所有指标 | `"indicators":"open,high"` |
| functionpara | 否 | key-value格式。所有key均取默认时，functionpara省略。技术指标额外在calculate生成，生成规则见下文。 | 见下方代码块 |
| starttime | 是 | 开始日期，支持"YYYYMMDD HH:mm:ss""YYYY-MM-DD HH:mm:ss""YYYY/MM/DD HH:mm:ss"三种时间格式 | `"starttime":"2018-01-01 09:15:00"` |
| endtime | 是 | 结束日期，支持"YYYYMMDD HH:mm:ss""YYYY-MM-DD HH:mm:ss""YYYY/MM/DD HH:mm:ss"三种日期格式 | `"endtime":"2018-01-01 15:15:00"` |

**indicators参数说明**

| 指标名 | 指标说明 | 指标备注 |
| --- | --- | --- |
| open | 开盘价 | 通用 |
| high | 最高价 | 通用 |
| low | 最低价 | 通用 |
| close | 收盘价 | 通用 |
| avgPrice | 均价 | 通用 |
| volume | 成交量 | 通用 |
| amount | 成交额 | 通用 |
| change | 涨跌 | 通用 |
| changeRatio | 涨跌幅 | 通用 |
| turnoverRatio | 换手率 | 通用 |
| sellVolume | 内盘 | 通用 |
| buyVolume | 外盘 | 通用 |
| changeRatio_accumulated | 涨跌幅(累计) | 股票，仅支持当天 |
| BBI | BBI多空指数 | 股票 |
| DDI | DDI方向标准离差指数 | 股票 |
| DMA | DMA平均线差 | 股票 |
| MA | MA简单移动平均 | 股票 |
| EXPMA | EXPMA指数平均数 | 股票 |
| MACD | MACD指数平滑异同平均 | 股票 |
| MTM | MTM动力指标 | 股票 |
| PRICEOSC | PRICEOSC价格振荡指标 | 股票 |
| TRIX | TRIX三重指数平滑平均 | 股票 |
| BIAS | BIAS乖离率 | 股票 |
| CCI | CCI顺势指标 | 股票 |
| DBCD | DBCD异同离差乖离率 | 股票 |
| DPO | DPO区间震荡线 | 股票 |
| KDJ | KDJ随机指标 | 股票 |
| LWR | LWR威廉指标 | 股票 |
| ROC | ROC变动速率 | 股票 |
| RSI | RSI相对强弱指标 | 股票 |
| SI | SI摆动指标 | 股票 |
| SRDM | SRDM动向速度比率 | 股票 |
| VROC | VROC量变动速率 | 股票 |
| VRSI | VRSI量相对强弱 | 股票 |
| WR | WR威廉指标 | 股票 |
| ARBR | ARBR人气意愿指标 | 股票 |
| CR | CR能量指标 | 股票 |
| PSY | PSY心理指标 | 股票 |
| VR | VR成交量比率 | 股票 |
| WAD | WAD威廉聚散指标 | 股票 |
| MFI | MFI资金流向指标 | 股票 |
| OBV | OBV能量潮 | 股票 |
| PVT | PVT量价趋势指标 | 股票 |
| WVAD | WVAD威廉变异离散量 | 股票 |
| BBIBOLL | BBIBOLL多空布林线 | 股票 |
| BOLL | BOLL布林线 | 股票 |
| CDP | CDP逆势操作 | 股票 |
| ENV | ENV指标 | 股票 |
| MIKE | MIKE麦克指标 | 股票 |
| LB | 量比 | 股票 |
| VMA | VMA量简单移动平均 | 股票 |
| VMACD | VMACD量指数平滑异同平均 | 股票 |
| VOSC | VOSC成交量震荡 | 股票 |
| TAPI | TAPI加权指数成交值 | 股票 |
| VSTD | VSTD成交量标准差 | 股票 |
| ADTM | ADTM动态买卖气指标 | 股票 |
| MI | MI动量指标 | 股票 |
| MICD | MICD异同离差动力指数 | 股票 |
| RC | RC变化率指数 | 股票 |
| RCCD | RCCD异同离差变化率指数 | 股票 |
| SRMI | SRMI(MI修正指标) | 股票 |
| DPTB | DPTB大盘同步指标 | 股票 |
| JDQS | JDQS阶段强势指标 | 股票 |
| JDRS | JDRS阶段弱势指标 | 股票 |
| ZDZB | ZDZB筑底指标 | 股票 |
| ATR | ATR真实波幅 | 股票 |
| MASS | MASS梅丝线 | 股票 |
| STD | STD标准差 | 股票 |
| VHF | VHF纵横指标 | 股票 |
| CVLT | CVLT佳庆离散指标 | 股票 |

**技术指标规则说明**

选择技术指标时，需同时在functionpara的calculate字段以indicators为key，以半角逗号拼接各个参数字符串为value。为下列特殊的参数额外使用下列英文名，其他的沿用下拉框英文值。

**indicators参数说明（技术指标参数）**

| 指标名 | 指标说明 | 指标备注 |
| --- | --- | --- |
| BBI | BBI多空指数 | {周期1},{周期2},{周期3},{周期4} |
| DDI | DDI方向标准离差指数 | {周期1},{周期2},{平滑因子},{周期3},{DDIorADDIorAD} |
| DMA | DMA平均线差 | {短周期},{长周期},{周期},{DDDorAMA} |
| MA | MA简单移动平均 | {周期} |
| EXPMA | EXPMA指数平均数 | {周期} |
| MACD | MACD指数平滑异同平均 | {短周期},{长周期},{周期},{DIFForDEAorMACD} |
| MTM | MTM动力指标 | {间隔周期},{周期},{MTMorMTMMA} |
| PRICEOSC | PRICEOSC价格振荡指标 | {短周期},{长周期} |
| TRIX | TRIX三重指数平滑平均 | {周期1},{周期2},{TRIXorTRMA} |
| BIAS | BIAS乖离率 | {周期} |
| CCI | CCI顺势指标 | {周期} |
| DBCD | DBCD异同离差乖离率 | {周期1},{周期2},{周期3},{DBCDorMM} |
| DPO | DPO区间震荡线 | {周期1},{周期2},{DPOorMADPO} |
| KDJ | KDJ随机指标 | {周期},{周期1},{周期2},{KorDorJ} |
| LWR | LWR威廉指标 | {周期},{周期1},{周期2},{LWR1orLWR2} |
| ROC | ROC变动速率 | {间隔周期},{周期},{ROCorROCMA} |
| RSI | RSI相对强弱指标 | {周期} |
| SI | SI摆动指标 |  |
| SRDM | SRDM动向速度比率 | {周期},{SRDMorASRDM} |
| VROC | VROC量变动速率 | {周期} |
| VRSI | VRSI量相对强弱 | {周期} |
| WR | WR威廉指标 | {周期} |
| ARBR | ARBR人气意愿指标 | {周期},{ARorBR} |
| CR | CR能量指标 | {周期} |
| PSY | PSY心理指标 | {周期1},{周期2},{PSYorMAPSY} |
| VR | VR成交量比率 | {周期} |
| WAD | WAD威廉聚散指标 | {周期},{WADorMAWAD} |
| MFI | MFI资金流向指标 | {周期} |
| OBV | OBV能量潮 | {OBVorOBV_XZ} |
| PVT | PVT量价趋势指标 |  |
| WVAD | WVAD威廉变异离散量 | {周期1},{周期2},{WVADorMAWVAD} |
| BBIBOLL | BBIBOLL多空布林线 | {周期},{宽带},{BBIBOLLorUPRorDWN} |
| BOLL | BOLL布林线 | {周期},{宽带},{MIDorUPPERorLOWER} |
| CDP | CDP逆势操作 | {CDPorAHorALorNHorNL} |
| ENV | ENV指标 | {周期},{UPPERorLOWER} |
| MIKE | MIKE麦克指标 | {周期},{WRorMRorSRorWSorMSorSS} |
| LB | 量比 | {周期} |
| VMA | VMA量简单移动平均 | {周期} |
| VMACD | VMACD量指数平滑异同平均 | {短周期},{长周期},{周期},{DIFForDEAorMACD} |
| VOSC | VOSC成交量震荡 | {短周期},{长周期} |
| TAPI | TAPI加权指数成交值 | {周期},{TAPIorMATAPI} |
| VSTD | VSTD成交量标准差 | {周期} |
| ADTM | ADTM动态买卖气指标 | {周期},{周期1},{ADTMorMAADTM} |
| MI | MI动量指标 | {周期},{AorMI} |
| MICD | MICD异同离差动力指数 | {周期},{周期1},{周期2},{DIForMICD} |
| RC | RC变化率指数 | {周期} |
| RCCD | RCCD异同离差变化率指数 | {周期},{周期1},{周期2},{DIForRCCD} |
| SRMI | SRMI(MI修正指标) | {周期} |
| DPTB | DPTB大盘同步指标 | {周期},{000001or000010or399001or000300} |
| JDQS | JDQS阶段强势指标 | {周期},{000001or000010or399001or000300} |
| JDRS | JDRS阶段弱势指标 | {周期},{000001or000010or399001or000300} |
| ZDZB | ZDZB筑底指标 | {周期},{周期1},{周期2},{BorD} |
| ATR | ATR真实波幅 | {周期},{TRorATR} |
| MASS | MASS梅丝线 | {周期1},{周期2} |
| STD | STD标准差 | {周期} |
| VHF | VHF纵横指标 | {周期} |
| CVLT | CVLT佳庆离散指标 | {周期} |

**functionpara控件说明**

| 名称 | keys | value说明 | 省略时逻辑 |
| --- | --- | --- | --- |
| 设置时间区间-开始时间 | Limitstart | 限定每个交易日数据的开始时间 |  |
| 设置时间区间-结束时间 | Limitend | 限定每个交易日数据的截止时间 |  |
| 时间周期 | Interval | 1-1分钟 3-3分钟 5-5分钟 10-10分钟 15-15分钟 30-30分钟 60-60分钟 | 1-1分钟 |
| 非交易间隔处理 | Fill | Previous-沿用之前数据 Blank-空值 具体数值-自定义数值 Original-不处理 | Original-不处理 |
| 分红再投复权方式 | CPS | 后复权（分红方案计算）-backward1 前复权（交易所价格计算）-forward3 后复权（交易所价格计算）-backward3 全流通前复权（分红方案计算）-forward2 全流通后复权（分红方案计算）-backward2 全流通前复权（交易所价格计算）-forward4 全流通后复权（交易所价格计算）-backward4 不复权-no | no-不复权 |
| 时间戳格式 | Timeformat | BeiJingTime-北京时间 LocalTime-当地时间 | BeiJingTime-北京时间 |
| 设定复权基点 | BaseDate | 复权基点日期，"YYYY-MM-DD" | 后复权按上市日，前复权按最新日 |

**示例**

```python
para = {
    "codes": "300033.SZ,600030.SH",
    "indicators": "open,high,SI,MACD,DPTB,OBV,KDJ",
    "starttime": "2018-01-01 09:15:00",
    "endtime": "2018-01-01 09:50:00",
    "functionpara": {
        "Interval": "1",
        "Fill": "Original",
        "calculate": {
            "SI": "",
            "MACD": "12,26,9,MACD",
            "DPTB": "7,000001",
            "OBV": "OBV_XZ",
            "KDJ": "9,3,3,K",
        }
    }
}
```

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括thscode、table（具体的数据内容）等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 5、实时行情

**URL**

```
https://quantapi.51ifind.com/api/v1/real_time_quotation
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"300033.SZ,600030.SH"` |
| indicators | 是 | 半角逗号分隔的所有指标 | `"indicators":"open,high"` |
| functionpara | 否 | key-value格式。仅包含债券报价方式（pricetype）控件失效时，不生成，否则生成。 | 见下方代码块 |

**indicators参数说明**

| 指标名 | 指标说明 | 指标备注 |
| --- | --- | --- |
| tradeDate | 交易日期 | 通用 |
| tradeTime | 交易时间 | 通用 |
| preClose | 前收盘价 | 通用 |
| open | 开盘价 | 通用 |
| high | 最高价 | 通用 |
| low | 最低价 | 通用 |
| latest | 最新价 | 通用 |
| avgPrice | 均价 | 通用 |
| change | 涨跌 | 通用 |
| changeRatio | 涨跌幅 | 通用 |
| totalShares | 总股本 | 股票 |
| totalCapital | 总市值 | 股票 |
| pb | 市净率 | 股票 |
| riseDayCount | 连涨天数 | 股票 |
| suspensionFlag | 停牌标志 | 股票 |
| tradeStatus | 交易状态 | 股票 |
| mv | 流通市值 | 股票 |
| vol_ratio | 量比 | 股票 |
| committee | 委比 | 股票 |
| commission_diff | 委差 | 股票 |
| pe_ttm | 市盈率TTM | 股票 |
| pbr_lf | 市净率LF | 股票 |
| swing | 振幅 | 股票 |
| lastest_price | 最新成交价 | 股票 |
| af_backward | 后复权因子(分红方案计算) | 股票 |
| priceDiff | 买卖价差 | 港股专用 |
| sharesPerHand | 每手股数 | 港股专用 |
| expiryDate | 到期日 | 港股专用 |
| tradeStatus | 交易状态 | 港股专用 |
| iopv | IOPV(净值估值) | 基金专用 |
| premium | 折价 | 基金专用 |
| riseCount | 上涨家数 | 指数专用 |
| fallCount | 下跌家数 | 指数专用 |
| upLimitCount | 涨停家数 | 指数专用 |
| downLimitCount | 跌停家数 | 指数专用 |
| suspensionCount | 停牌家数 | 指数专用 |
| pure_bond_value_cb | 纯债价值 | 指数专用 |
| surplus_term | 剩余期限(天) | 指数专用 |
| dealDirection | 成交方向 | 期货期权专用 |
| dealtype | 成交性质 | 期货期权专用 |
| impliedVolatility | 隐含波动率 | 期权专用 |
| historyVolatility | 历史波动率 | 期权专用 |
| delta | Delta | 期权专用 |
| gamma | Gamma | 期权专用 |
| vega | Vega | 期权专用 |
| theta | Theta | 期权专用 |
| rho | Rho | 期权专用 |
| pre_open_interest | 前持仓量 | 期权专用 |
| pre_implied_volatility | 前隐含波动率 | 期权专用 |
| volume_pcr_total | 成交量pcr(品种) | 期权专用 |
| volume_pcr_month | 成交量pcr(同月) | 期权专用 |

**示例**

```python
para = {
    "codes": "300033.SZ,600000.SH",
    "indicators": "open,high",
}
```

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括thscode、table（具体的数据内容）等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 6、经济数据库(EDB)

**URL**

```
https://quantapi.51ifind.com/api/v1/edb_service
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| indicators | 是 | 半角逗号分隔的所有指标，宏观指标过多，推荐使用Windows超级命令生成。 | `"indicators":"M001620326,M002822183"` |
| functionpara | 否 | key-value格式,省略时不进行更新时间筛选。两个时间控件更新起始时间（startrtime）和更新结束时间（endrtime），不勾选时省略 | 见下方代码块 |
| startdate | 是 | 开始日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种时间格式 | `"startdate":"2018-01-01"` |
| enddate | 是 | 结束日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种日期格式 | `"enddate":"2018-01-01"` |

**示例**

```python
para = {
    "indicators": "M001620326,M002822183",
    "startdate": "2018-01-01",
    "enddate": "2018-01-01",
    "functionpara": {
        "startrtime": "2018-01-01 09:15:00",
        "endrtime": "2018-01-01 10:15:00",
    }
}
```

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括ID、time等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 7、专题报表函数

**URL**

```
https://quantapi.51ifind.com/api/v1/data_pool
```

**formData**

报表过多，推荐使用超级命令查看生成命令。

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| reportname | 是 |  | `"reportname":"p03341"` |
| functionpara | 是 | key-value的参数，key按照过去的指标名称 | 见下方代码块 |
| outputpara | 是 | 半角逗号分隔的Y/N来控制是否显示该字段 | `"outputpara":"date:Y,thscode:Y,security_name:Y,weight:Y"` |

**示例**

```python
para = {
    "reportname": "p03341",
    "functionpara": {
        "sdate": "20210421",
        "edate": "20211119",
        "xmzt": "全部",
        "jcsslx": "全部",
        "jys": "全部"
    },
    "outputpara": "p03341_f001:Y,p03341_f002:Y"
}
```

提取'REITs项目一览'报表函数数据，对应报表编码'p03341'

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括p03341_f001、p03341_f002（具体的数据内容）等 |
| datatype | 指标格式 | 报表函数暂为空，忽略 |
| inputParams | 输入参数 | 报表函数暂为空，忽略 |
| outParams | 输出指标 | 返回报表指标与中文名称，如：`'p03291_f002':'同花顺代码'` |
| descrs | 输出信息 | 如：`'name':'p03291_f001','type':'DT_DATE','attrs': []` |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 8、组合管理

#### (1）组合新建

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 |  | `"func":"newportf"` |
| 组合名称 | name | 是 |  | `"name":"股债策略组合"` |
| 所属分组 | group | 是 |  | `"group": 11580` |
| 业绩基准，基准代码和名称 | performbm | 否，默认填充沪深300 | 键值对 | `"performbm": {"code":"000300.SH","name":"沪深300"}` |
| 跌价基准，基准代码、基准名称、基准类型 | supbm | 否，省略时为空 | 键值对 | `"supbm":{"code":"000001.SH","name":"上证指数","benchmarkType":"1"}` |
| 交易日 | tday | 否，默认国内交易所 | 枚举值国内交易所、港股、美股、国内银行间 | `"tday":"国内交易所"` |
| 基准货币 | currency | 否，默认人民币 | 枚举值CND、HKD、USD | `"currency":"CNY"` |
| 融资利率% | finacrate | 否，默认为空 |  | `"finacrate":"7.5"` |
| 融券利率% | secrate | 否，默认为空 |  | `"secrate":"5.5"` |
| 组合说明 | info | 否，默认为空 |  | `"info":"股票与债券结合的策略组合"` |

**示例**

```python
para = {
    "func": "newportf",
    "name": "股债联动",
    "group": 11580,
    "performbm": {
        "code": "000300.SH",
        "name": "沪深300"
    },
    "supbm": {
        "code": "",
        "name": "",
    },
    "tday": "国内交易所",
    "curency": "CNY",
    "finacrate": "",
    "secrate": "",
    "info": "股票与债券结合的策略组合"
}
```

#### (2）组合导入

##### 1).模板导入

通过读取组合文件的内容，进行上传完成组合导入。

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | importf | `"func":"importf"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 组合内容 | content | 是 | 二维表 |  |

**示例**

```python
para = {
    "func": "importf",
    "name": "股债策略组合",
    "portfid": 161390,
    "content": [
        [
            "交易日期", "证券代码", "业务类型", "数量", "价格",
            "成交金额", "费用", "证券类型"
        ],
        [
            "2020-03-30", "CNY", "现金存入", "", "",
            10000000, "", ""
        ],
        [
            "2020-04-01", "600000.SH", "买入", 100, 10.09,
            1009, 5.225, "A股"
        ],
    ]
}
```

##### 2).文件导入

通过文件对象的形式提交，来实现组合导入。

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | fileimport | `"func":"fileimport"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 组合文件 | file | 是 | 文件对象 | file:{本地文件} |

**示例**

```python
para = {
    "func": "fileimport",
    "name": "股债策略组合",
    "portid": 161930,
    "file": "股债策略组合内容.xlsx"
}
# file_object为待导入组合的文件对象
files = {
    "file": ("股债策略组合内容.xlsx", open("C:\demo\股债策略组合内容.xlsx", 'rb'))
}
```

##### 3).状态查询

适用于大文件导入、导入历史持仓计算量较大的组合导入时，查询导入状态。

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | fileimport | `"func":"query_commit"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 组合文件 | jobid | 是 | 文件导入后返回 | `"jobid":21` |

**示例**

```python
para = {
    "func": "query_commit",
    "portid": 161930,
    "jobid": 21
}
```

#### (3)现金存取

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | cashacs | `"func":"cashacs"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 功能参数 | functionpara | 是 |  | `"functionpara":{"acesscls":"101","amount":"10000"}` |

**functionpara说明**

| 名称 | key | value | 省略时 |
| --- | --- | --- | --- |
| 存取类型 | acesscls | 存入-不计入收益：101；取出-不计入收益：102 | 不能省略 |
| 现金数额 | amount |  | 不能省略 |

**示例**

```python
para = {
    "func": "cashacs",
    "name": "bldptf5",
    "portfid": 161390,
    "functionpara": {
        "acesscls": "101",
        "amount": "10000"
    }
}
```

#### (4)普通交易

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | deal | `"func": "deal"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 功能参数 | functionpara | 是 |  |  |

**functionpara说明**

| 名称 | key | value | 省略时 |
| --- | --- | --- | --- |
| 行情代码 | thscode |  | 不能省略 |
| 交易方向 | direct | 买入：buy；卖出：sell | 不能省略 |
| 标的名称 | codeName |  | 不能省略 |
| 交易市场 | marketCode |  | 不能省略 |
| 标的类型 | securityType |  | 不能省略 |
| 成交价格 | price |  | 不能省略 |
| 成交数量 | volume |  | 不能省略 |
| 结算货币 | currency |  | 不能省略 |
| 费用 | fee |  | 不能省略 |
| 费率 | feep |  | 不能省略 |
| 汇率 | rate |  | 不能省略 |
| 分红方式 | bonus | 适用基金，现金分红：1；红利再投资：2 |  |

**示例**

```python
para = {
    "func": "deal",
    "name": "股债策略组合",
    "portfid": 161390,
    "functionpara": {
        "thscode": "300033",
        "direct": "buy",
        "codeName": "同花顺",
        "marketCode": "212100",
        "securityType": "001001",
        "price": 78.7,
        "volume": 100,
        "currency": "CNY",
        "fee": "0",
        "feep": 0,
        "rate": "1.00",
        "bonus": ""
    }
}
```

#### (5)交易流水

目前支持最大时间区间为7天

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | query_exchange_records | `"func":"query_exchange_records"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 指标 | indicators | 是 |  | `"indicators": "date,code,name,dealPrice"` |
| 开始时间 | startdate | 是 |  | `"startdate":"2022-10-18"` |
| 结束时间 | enddate | 是 |  | `"enddate":"2022-10-20"` |
| 功能参数 | functionpara | 否 |  | `"functionpara":{"keyword":""}` |

**indicators说明**

| 指标名称 | 英文名称 | 备注 |
| --- | --- | --- |
| 交易日期 | date |  |
| 证券代码 | code |  |
| 证券简称 | name |  |
| 成交价格 | dealPrice |  |
| 成交数量 | dealNumber |  |
| 发生金额 | realPrice |  |
| 业务名称 | businessName |  |
| 手续费 | serviceCharge |  |
| 证券类型 | type |  |
| 币种 | currency |  |
| 汇率 | exchangeRate |  |
| 市场 | marketName |  |
| 备注信息 | importType |  |

**functionpara说明**

| 名称 | key | value | 省略时 |
| --- | --- | --- | --- |
| 关键字 | keyword |  | 默认为空 |

**示例**

```python
para = {
    "func": "query_exchange_records",
    "name": "股债策略组合",
    "portfid": 161390,
    "indicators": "date,code,name,dealPrice,dealNumber,realPrice,businessName,serviceCharge,type,currency,exchangeRate,marketName,importType",
    "startdate": "2022-10-18",
    "enddate": "2022-10-20",
    "functionpara": {
        "keyword": ""
    }
}
```

#### (6)组合监控

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | query_overview | `"func":"query_overview"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 指标 | indicators | 是 |  |  |

**indicators说明**

| 指标名称 | 英文名称 | 备注 |
| --- | --- | --- |
| 资产分类 | category |  |
| 证券代码 | thscode |  |
| 证券简称 | stockName |  |
| 最新价格 | newPrice |  |
| 涨跌 | increase |  |
| 涨跌幅 | increseRate |  |
| 持仓数量 | number |  |
| 持仓市值 | marketValue |  |
| 最新权重 | weight |  |
| 当日盈亏 | todayProfit |  |
| 浮动盈亏 | floatProfit |  |
| 浮动盈亏率 | floatProfitRate |  |
| 累计盈亏 | totalProfit |  |
| 累计盈亏率 | totalProfitRate |  |
| 分红派息 | interestIncome |  |
| 已实现盈利 | realizedProfit |  |
| 成本价格 | positionPrice |  |
| 持仓成本 | positionCost |  |
| 保本价格 | breakevenPrice |  |
| 手续费 | serviceCharge |  |
| 币种 | moneyType |  |
| 汇率 | currentPrice |  |
| 更新时间 | updateTime |  |

**示例**

```python
para = {
    "func": "query_overview",
    "name": "股债策略组合",
    "portfid": 161390,
    "indicators": "category,thscode,stockName,newPrice,increase,increaseRate,number,marketValue,weight,todayProfit,floatProfit,floatProfitRate,totalProfit,totalProfitRate,interestIncome,realizedProfit,positionPrice,positionCost,breakevenPrice,serviceCharge,moneyType,currentPrices,updateTime"
}
```

#### (7)持仓分析

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | query_positions | `"func":"query_positions"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 指标 | indicators | 是 |  |  |
| 功能参数 | functionpara | 是 |  | `"functionpara": {"penetrate": "false"}` |

**indicators说明**

| 指标名称 | 英文名称 | 备注 |
| --- | --- | --- |
| 证券类型 | categoryName |  |
| 证券名称 | securityName |  |
| 证券代码 | thsCode |  |
| 权重 | weight |  |
| 持仓市值 | marketPrice |  |
| 持仓成本 | cost |  |
| 浮动盈亏 | wavepl |  |
| 累计收益 | cumpl |  |
| 收盘价 | price |  |
| 涨跌幅 | increaseRate |  |
| 持仓数量 | amount |  |
| 持仓成本价 | costPrice |  |

**functionpara说明**

| 名称 | key | value | 省略时 |
| --- | --- | --- | --- |
| 是否穿透 | penetrate | 不穿透：false；穿透：true | 不能省略 |

**示例**

```python
para = {
    "func": "query_positions",
    "name": "股债策略组合",
    "portfid": 161390,
    "indicators": "categoryName,securityName,thsCode,weight,marketPrice,cost,wavepl,cumpl,price,increaseRate,amount,costPrice",
    "date": "2022-10-19",
    "functionpara": {
        "penetrate": "false"
    }
}
```

#### (8)绩效指标

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | query_perform | `"func":"query_perform"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 日期 | date | 是 | 适用于当日实时 | `"date":"2020-06-02"` |
| 开始日期 | startdate | 是 | 开始日期适用于区间 | `"startdate":"2020-06-02"` |
| 结束日期 | enddate | 是 | 开始日期适用于区间 | `"enddate":"2020-06-02"` |
| 业绩基准 | performbm | 是 |  | `"performbm":"000300"` |
| 功能参数 | functionpara | 是 |  | `"functionpara":{"pfclass":"utnv","cycle":"day"}` |

**functionpara说明**

| 名称 | key | value | 省略时 |
| --- | --- | --- | --- |
| 业绩类型 | pfclass | 业绩表现：perform 净资产：nasset 组合净值：utnv | 不能省略 |
| 周期 | cycle | 当日实时:rquota 日:day 周:week 月:month 半年:halfYear 年:year | 不能省略 |

**示例**

```python
para = {
    "func": "query_perform",
    "name": "股债策略组合",
    "portfid": 161390,
    "performbm": "000300",
    "startdate": "2020-06-02",
    "enddate": "2022-10-20",
    "functionpara": {
        "pfclass": "utnv",
        "cycle": "day"
    }
}
```

#### (9)风险指标

**URL**

```
https://quantapi.51ifind.com/api/v1/portfolio_manage
```

**formData**

| 名称 | key | 是否必须 | value | 示例 |
| --- | --- | --- | --- | --- |
| 功能名称 | func | 是 | query_risk_profits | `"func":"query_risk_profits"` |
| 组合名称 | name | 否 |  | `"name":"股债策略组合"` |
| 组合ID | portfid | 是 |  | `"portfid":161390` |
| 指标 | indicators | 是 |  | `"indicators": ["alpha,yield,annual_yield,sharpe_ratio"]` |
| 开始日期 | startdate | 是 |  | `"startdate":"2021-10-19"` |
| 结束日期 | enddate | 是 |  | `"enddate":"2022-10-19"` |
| 功能参数 | functionpara | 是 |  | `"functionpara":{"cycle":"day","benchmark":"000300"}` |

**indicators说明**

| 指标名称 | 英文名称 | 备注 |
| --- | --- | --- |
| ALPHA | ALPHA |  |
| 累计收益 | yield |  |
| 年化收益 | annual_yield |  |
| 夏普比率 | sharpe_ratio |  |
| 信息比率 | information_ratio |  |
| 索提诺比率 | sortino_ratio |  |
| 詹森阿尔法 | jensen_alpha |  |
| 特雷诺比率 | treynor_ratio |  |
| 胜率 | win_ratio |  |
| 正收益期数 | positiveMonth |  |
| BETA | beta |  |
| 年化波动率 | annual_volatility |  |
| 跟踪误差 | tracking_error |  |
| 下行风险 | downside_risk |  |
| 在险价值 | value_at_risk |  |
| 最大回撤 | max_drawdown |  |
| 最大回撤形成期 | maxdrawdownRepairNum |  |
| 最大回撤修复期 | maxdownNum |  |
| 连续下跌最大幅度 | max_cont_decline |  |
| R-square | rSquare |  |

**functionpara说明**

| 名称 | key | value | 省略时 |
| --- | --- | --- | --- |
| 数据频率 | cycle | 日:day;周:week;月:month;季:season;年:year | 不能省略 |
| 计算基准 | benchmark |  | 不能省略 |

**示例**

```python
para = {
    "func": "query_risk_profits",
    "name": "股债策略组合",
    "portfid": 161390,
    "indicators": ["alpha,yield,annual_yield,sharpe_ratio"],
    "startdate": "2021-10-19",
    "enddate": "2022-10-19",
    "functionpara": {
        "cycle": "day",
        "benchmark": "000300"
    }
}
```

### 9、智能选股

**URL**

```
https://quantapi.51ifind.com/api/v1/smart_stock_picking
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| searchstring | 是 | 搜索关键词 | `"searchstring":"个股热度"` |
| searchtype | 是 | 搜索类别 | `"searchtype":"stock"` |

**示例**

```python
para = {
    "searchstring": "个股热度",
    "searchtype": "stock"
}
```

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括ID、time等 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| inputParams | 输入参数 | 返回输入的参数 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

### 10、基金实时估值(分钟)

**URL**

```
https://quantapi.51ifind.com/api/v1/fund_valuation
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"000001.OF,000003.OF"` |
| functionpara | 是 | key-value的参数 | 见下方表格 |
| outputpara | 是 | 半角逗号分隔的Y/N来控制是否显示该字段 | `"changeRatioValuation:Y,realTimeValuation:Y,Deviation30TDays:Y"` |

**functionpara参数说明**

| 名称 | keys | value说明 | 省略时逻辑 |
| --- | --- | --- | --- |
| 仅返回最新估值 | onlyLastest | 1-仅返回最新估值 0-返回时间区间估值 | 不能省略 |
| 开始时间 | beginTime |  | 仅返回最新估值可省略 |
| 结束时间 | endTime |  | 仅返回最新估值可省略 |

**outputpara说明**

| 字段名称 | 字段中文 |
| --- | --- |
| changeRatioValuation | 估值涨跌幅 |
| realTimeValuation | 基金实时估值 |
| Deviation30TDays | 30交易日估算平均偏差（%） |
| rank | 请求基金最新估值涨跌幅排名 |

**示例**

```python
para = {
    "codes": "000001.OF,000003.OF",
    "functionpara": {
        "onlyLastest": "0",
        "beginTime": "2021-08-24 09:15:00",
        "endTime": "2021-08-24 15:15:00"
    },
    "outputpara": "date:Y,thscode:Y,security_name:Y,weight:Y"
}
```

**输出：**

| 属性 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |
| datatype | 指标格式 | 返回获取数据的指标格式 |
| tables | 结构体 | 包括基金实时估值、估值涨跌幅、30日平均偏差等 |
| inputParams | 输入参数 | 基金实时估值函数暂为空，忽略 |

### 11、基金实时估值(日)

**URL**

```
https://quantapi.51ifind.com/api/v1/final_fund_valuation
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码 | `"codes":"000001.OF,000003.OF"` |
| functionpara | 是 | key-value的参数，包括开始日期beginDate，截止日期endDate | 见下方示例 |
| outputpara | 是 | 半角逗号分隔的Y/N来控制是否显示该字段 | `"finalValuation:Y,netAssetValue:Y,deviation:Y"` |

**outputpara说明**

| 字段名称 | 字段中文 |
| --- | --- |
| finalValuation | 日最终估值 |
| netAssetValue | 日实际净值 |
| deviation | 估值相对净值偏差率（%） |

**示例**

```python
para = {
    "codes": "000001.OF;000003.OF",
    "functionpara": {
        "beginDate": "2021-06-01",
        "endDate": "2021-09-02"
    },
    "outputpara": "finalValuation:Y,netAssetValue:Y,deviation:Y"
}
```

### 12、日期查询函数

**URL**

```
https://quantapi.51ifind.com/api/v1/get_trade_dates
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| marketcode | 是 | 见下方说明 | `"marketcode":"212001"` |
| functionpara | 是 | key-value的参数 | 见下方代码块 |
| startdate | 是 | 开始日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种时间格式 | `"startdate":"2018-01-01"` |
| enddate | 是 | 结束日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种日期格式 | `"enddate":"2018-01-01"` |

**marketcode说明**

| 交易所代码 | 交易所名称 |
| --- | --- |
| 212001 | 上交所 |
| 212100 | 深交所 |
| 212200 | 港交所 |
| 212020001 | 中国金融期货交易所 |
| 212020002 | 上海黄金交易所 |
| 212020003 | 郑州商品交易所 |
| 212020004 | 大连商品交易所 |
| 212004 | 银行间债券市场 |
| 212005 | 代办转让市场 |
| 212020006 | 伦敦金属交易所(LME) |
| 212020007 | 纽约商业期货交易所(NYMEX) |
| 212020008 | 上海期货交易所 |
| 212020010 | 纽约商品交易所(COMEX) |
| 212020011 | 纽约期货交易所(NYBOT) |
| 212020012 | 芝加哥商品交易所(CBOT) |
| 212020013 | 洲际交易所(ICE) |
| 212020014 | 马来西亚衍生品交易所 |
| 212020015 | 芝加哥商业交易所(CME) |
| 212010 | 美国纽约证券交易所 |
| 212011 | 美国NASDAQ证券交易所 |
| 212049 | 美国证券交易所 |
| 212050 | NYSEArca |
| 212012 | 英国伦敦证券交易所 |
| 212013 | 新加坡证券交易所 |
| 212014 | 荷兰阿姆斯特丹证券交易所 |
| 212015 | 挪威奥斯陆证券交易所 |
| 212016 | 澳大利亚证券交易所 |
| 212017 | 法国巴黎证券交易所 |
| 212018 | 比利时布鲁塞尔证券交易所 |
| 212020016 | 天津贵金属交易所 |
| 212024 | 德国法兰克福证券交易所 |
| 212025 | 日本东京证券交易所 |
| 212026 | 加拿大多伦多证券交易所 |
| 212027 | 韩国证券交易所 |
| 212029 | 马来西亚吉隆坡证券交易所 |
| 212031 | 马德里证券交易所 |
| 212033 | 墨西哥证券交易所 |
| 212035 | 瑞士证券交易所 |
| 212036 | 巴西圣保罗证券期货交易所 |
| 212037 | 瑞典斯德哥尔摩证券交易所 |
| 212039 | 台湾证券交易所 |
| 212040 | 泰国证券交易所 |
| 212041 | 奥地利维也纳证券交易所 |
| 212045 | 意大利米兰证券交易所 |
| 212047 | 印度尼西亚证券交易所 |
| 212051 | 美国IEX证券交易所 |
| 212053 | 新西兰证券交易所 |
| 212055 | 美国OTC市场 |
| 212061 | 菲律宾证券交易所 |
| 212062 | 孟买证券交易所 |
| 212063 | 布宜诺斯艾利斯证券交易所 |
| 212203 | 特拉维夫证券交易所 |
| 212205 | 莫斯科证券交易所 |
| 212210 | BATS交易所 |

**functionpara说明**

| 对应字段 | 字段类型 | 是否可省略 | 命令生成示例说明 |
| --- | --- | --- | --- |
| 函数模式 | 字符串 | 不可 | 查询区间日期 `"mode":"1"` 查询区间日期数目 `"mode":"2"` |
| 日期类型 | 字符串 | 不可 | 交易日 `"dateType":"0"` 日历日 `"dateType":"1"` |
| 日期格式 | 字符串 | 不可 | YYYY-MM-DD `"dateFormat":"0"` YYYY/MM/DD `"dateFormat":"1"` YYYYMMDD `"dateFormat":"2"` |
| 时间周期 | 字符串 | 不可 | 日`"period":"D"` 周`"period":"W"` 月`"period":"M"` 季`"period":"Q"` 半年`"period":"S"` 年`"period":"Y"` |
| 时间周期偏移 | 字符串 | 不可 | 时间周期正数第1日`"periodnum":"1"` 时间周期倒数第1日`"periodnum":"-1"` |

**示例**

```python
para = {
    "marketcode": "212001",
    "functionpara": {
        "mode": "1",
        "dateType": "0",
        "period": "D",
        "dateFormat": "0"
    },
    "startdate": "2025-09-10",
    "enddate": "2025-09-10"
}
```

### 13、日期偏移函数

**URL**

```
https://quantapi.51ifind.com/api/v1/get_trade_dates
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| marketcode | 是 | 见日期查询函数说明 | `"marketcode":"212001"` |
| functionpara | 是 | key-value的参数 | 见下方代码块 |
| startdate | 是 | 基准日期，支持"YYYYMMDD""YYYY-MM-DD""YYYY/MM/DD"三种时间格式 | `"startdate":"2018-01-01"` |

**functionpara说明**

| 对应字段 | 字段类型 | 是否可省略 | 省略时逻辑 | 命令生成示例说明 |
| --- | --- | --- | --- | --- |
| 日期类型 | 字符串 | 不可 |  | 交易日 `"dateType":"0"` 日历日 `"dateType":"1"` |
| 日期格式 | 字符串 | 不可 |  | YYYY-MM-DD `"dateFormat":"0"` YYYY/MM/DD `"dateFormat":"1"` YYYYMMDD `"dateFormat":"2"` |
| 前推后退 | 字符串 | 不可 |  | 前推`"offset":"-5"` 后推`"offset":"5"` |
| 时间周期 | 字符串 | 不可 |  | 日`"period":"D"` 周`"period":"W"` 月`"period":"M"` 季`"period":"Q"` 半年`"period":"S"` 年`"period":"Y"` |
| 时间周期内偏移 | 字符串 | 可 | 默认 | 默认省略 时间周期正数第1日`"periodnum":"1"` 时间周期倒数第1日`"periodnum":"-1"` |
| 输出选项 | 字符串 | 不可 |  | 所有日期 `"output":"sequencedate"` 单个日期 `"output":"singledate"` |

**示例**

```python
para = {
    "marketcode": "212001",
    "functionpara": {
        "dateType": "0",
        "period": "D",
        "offset": "-1",
        "dateFormat": "0",
        "output": "sequencedate"
    },
    "startdate": "2025-09-10"
}
```

### 14、数据量查询

无需参数，仅需要传入token访问url即可

**URL**

```
https://quantapi.51ifind.com/api/v1/get_data_volume
```

**示例**

```python
Headers = {
    "Content-Type": "application/json",
    "access_token": "xxxxxxxxxx"
}
```

### 15、错误信息查询

**URL**

```
https://quantapi.51ifind.com/api/v1/get_error_message
```

**示例**

```python
para = {
    "errorcode": -1
}
```

### 16、证券代码证券简称转同花顺代码

**URL**

```
https://quantapi.51ifind.com/api/v1/get_thscode
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| seccode/secname | 是 | 行情代码/简称 | `"seccode":"000001"` |
| mode | 是 | seccode/secname | `"mode":"seccode"` |
| sectype | 是 | 证券类型 | `"sectype":"001"` |
| market | 是 | 市场 | `"market":"212001"` |
| tradestatus | 是 | 0，1，2 | `"tradestatus":"0"` |
| isexact | 是 | 0，1 | `"isexact":"1"` |

**示例**

```python
para = {
    "seccode": "300033",
    "functionpara": {
        "mode": "seccode",
        "sectype": "",
        "market": "",
        "tradestatus": "0",
        "isexact": "0"
    }
}
```

### 17、公告查询

**URL**

```
https://quantapi.51ifind.com/api/v1/report_query
```

**formData**

| key | 是否必须 | value | 示例 |
| --- | --- | --- | --- |
| codes | 是 | 半角逗号分隔的所有代码，如参数内容为空下面functionpara中mode参数板块必填 | `"codes":"300033.SZ,600030.SH"` |
| functionpara | 否 | key-value格式。所有key均取默认时，functionpara省略。 | 见下方说明 |
| outputpara | 是 | 输出指标 | 见下方说明 |

**functionpara说明**

| 名称 | keys | value说明 | 是否可省略 | 示例 |
| --- | --- | --- | --- | --- |
| 提取方式 | mode | allAStock-全部A股，allBond-全部债券 等按照证券板块全部代码提取 | 可 | `"mode":"allAStock"` |
| 公告类型 | reportType | 903-全部；901002004-上市公告书等 | 可 | reportType:901 |
| 公告开始日期 | beginrDate | 根据公告开始日期筛选 | 可 | `"beginrDate":"2024-09-10"` |
| 公告截止日期 | endrDate | 根据公告截止日期筛选 | 可 | `"endrDate":"2025-09-10"` |
| 发布开始时间 | begincTime | 根据发布时间筛选 | 可 | `"begincTime":"2023-09-10 19:50:36"` |
| 发布截止时间 | endcTime | 根据发布时间筛选 | 可 | `"endcTime":"2025-09-10 20:50:36"` |
| 开始seq | beginSeq | 根据seq筛选 | 可 | `"beginSeq":"4569556291"` |
| 截止seq | endSeq | 根据seq筛选 | 可 | `"endSeq":"4679626676"` |
| 标题关键词 | keyWord | 根据公告标题关键词筛选 | 可 | `"keyWord":"半年度报告"` |

**outputpara说明**

| 字段名称 | 字段中文 |
| --- | --- |
| reportDate | 公告日期 |
| thscode | 证券代码 |
| secName | 证券简称 |
| ctime | 发布时间 |
| reportTitle | 公告标题 |
| pdfURL | 公告链接 |
| seq | 唯一标号 |

注意：用户可以通过查询到的'pdfURL'下载公告文件。

**示例**

```python
para = {
    "codes": "300033.SZ,600000.SH",
    "functionpara": {
        "reportType": "901"
    },
    "beginrDate": "2024-09-10",
    "endrDate": "2025-09-10",
    "outputpara": "reportDate:Y,thscode:Y,secName:Y,ctime:Y,reportTitle:Y,pdfURL:Y,seq:Y"
}
```

**输出：**

| 字段 | 字段名称 | 字段描述 |
| --- | --- | --- |
| errorcode | 错误ID | 代码运行错误码，errorcode=0表示代码运行正常。若为其他则需查找错误原因 |
| errmsg | 错误信息 | 若errorcode返回非空，此处会返回具体的错误信息 |
| tables | 结构体 | 返回内容包括thscode、reportDate等outputpara选择返回的指标 |
| datatype | 指标格式 | 返回获取数据的指标格式，目前本函数返回为空 |
| inputParams | 输入参数 | 返回输入的参数，目前本函数返回为空 |
| perf | 处理时间 | 返回请求命令整体耗时（ms） |
| dataVol | 数据量 | 返回当前命令消耗的数据量 |

## 三、错误说明

| 错误码 | 错误信息 | 错误提示 |
| --- | --- | --- |
| -1010 | your account has been logged out. | token已失效 |
| -1000 | data svr error! | 数据服务器错误 |
| -1001 | gw svr error! | 网关服务器错误 |
| -1002 | timeout! | 超时 |
| -1003 | access-token cannot be empty! | 数据服务器错误 |
| -1004 | data svr hq error! | 传值不能为空 |
| -1005 | auth user error! | 用户验证错误 |
| -1201 | failed, please change your input condition. | 查询失败 |
| -1202 | there are errors in your parameters, please have a check. | 参数错误 |
| -1203 | parsing failed. | 解析失败 |
| -1300 | Not legal User | token无效 |
| -1301 | Refresh_Token is expired or illegal | refresh_token无效 |
| -1302 | Access_Token is expired or illegal | Access_Token无效 |
| -1303 | Device exceed limit | access_token绑定超过20个IP |
| -1305 | Exceeded the maximum number of token acquistions for the day | 每天请求token次数超过限制 |
| -4001 | no data. | 数据为空 |
| -4100 | please log in first! | 请先登录iFind |
| -4101 | database execution error | 数据库执行错误 |
| -4102 | server internal error. | 服务端请求超时 |
| -4103 | unreasonable request! your account has been locked. please contact the saler to unlock | 超时请求过多，账号被锁 |
| -4201 | the data server is incorrect | 数据服务器取值错误 |
| -4203 | request format is wrong | 请求格式错误 |
| -4204 | wrong time format | 错误的时间格式 |
| -4205 | the start time can not be greater than the end time | 开始时间不能大于结束时间 |
| -4206 | include the wrong thscode | 含有错误的同花顺代码 |
| -4207 | sorry, currently we do not support bonds of this market. | 用户参数错误:不支持银行间债券 |
| -4208 | sorry, currently we just support kinds of securities of SSE, SZSE and CFFEX. | 目前仅支持上交所深交所 |
| -4209 | sorry, the startDate and endDate of Shopshot command should be the same, please have a check. | 起始、结束日期要求同一天 |
| -4210 | error happen with input parameters, please have a check. | 输入参数错误 |
| -4211 | sorry, there is no trading date in the date range, please have a check | 时间区间内无交易日 |
| -4212 | sorry, the input endDate is earlier than the listDates of the input security codes | 时间区间内股票未上市 |
| -4230 | you currently do not have permission for real-time Us stock market quotes | 没有美股实时行情权限 |
| -4213 | sorry, startDate can't later than endDate in the command, please have a check | 开始日期大于截止日期 |
| -4301 | sorry, your usage of basic data has exceeded 5 million this week. | 对不起，这周基础数据提取已经超过500万条 |
| -4302 | sorry, your usage of quote data has exceeded 150 million this week. | 对不起，这周报价数据提取已经超过1亿5千万条 |
| -4303 | sorry, your usage of EDB data has exceeded 5 million this week. | 对不起，这周EDB数据提取已经超过500万条 |
| -4317 | sorry, your usage of data has exceeded 1w this week. | 对不起，您本周数据量已超过1万 |
| -4318 | sorry, your usage of data has exceeded this month. | 对不起，本月使用量已经超限 |
| -4320 | sorry, your account must use the corresponding. | 抱歉，您的账户必须使用对应客户端 |
| -4321 | sorry, the free Acount can support requiring 10W data at most, please modify your input params! | 免费账号单次提取限制10万 |
| -4304 | sorry, the HighFrequeceSequence command can support requiring 200W data at most, please modify your input params | 单条命令请求数据量过大 |
| -4305 | sorry, the BasicData command can support requiring 20W data at most, please modify your input params | 单条命令请求数据量过大 |
| -4306 | sorry, the Snapshot command can support requiring 200W data at most, please modify your input params | 单条命令请求数据量过大 |
| -4319 | sorry, the free Acount can support requiring 5W data at most, please modify your input params | 免费用户单条命令请求数据量过大 |
| -4322 | sorry, the free Acount can support requiring 1W data at most, please modify your input params | 免费用户单条命令请求数据量过大 |
| -4307 | data extraction is overrun. | 数据提取量超限 |
| -4308 | the range between startDate and endDate must be smaller than 1 month. Please check your input parameters. | 请求区间不能超过一个月 |
| -4309 | sorry, trial account can get 1 year data for authority limited, so as to acquire more data, please transfer it to formal account | 超出时间限制 |
| -4310 | sorry, trial account can get 1 month data for authority limited, so as to acquire more data, please transfer it to formal account | 超出时间限制 |
| -4311 | sorry, trial account can get 5 year data for authority limited, so as to acquire more data, please transfer it to formal account | 超出时间限制 |
| -4312 | sorry, the HistoryQuotes command can support requiring 200W data at most, please modify your input params | 超出200W限制 |
| -4313 | sorry, the interval should be smaller than 3 years, please change your startDate or endDate. | 对不起，开始时间与结束时间间隔不能超过3年 |
| -4314 | sorry, the interval should be smaller than 6 months, please change your startDate or endDate. | 对不起，开始时间与结束时间间隔不能超过6个月 |
| -4315 | sorry, the interval should be smaller than 3 months, please change your startDate or endDate. | 对不起，开始时间与结束时间间隔不能超过3个月 |
| -4316 | sorry, the interval should be smaller than 1 year, please change your startDate or endDate. | 对不起，开始时间与结束时间间隔不能超过1年 |
| -4400 | sorry, we just support 600 requests per minute. | 对不起，我们每分钟最多支持600条数据请求 |
| -5001 | sorry, data server parameter error. | 请求远程服务器参数错误 |
| -5002 | sorry, data server is busy now. | 查询失败 |
| -5003 | sorry, does not support the stockbox selection calculation. | 不支持该股权查询 |
| -5004 | sorry, data process waiting timeout. | 等待超时 |
| -5005 | sorry, data calculation error. | 计算错误 |
| -5006 | sorry, data process query failed. | 查询失败 |
| -5007 | sorry, data process Waiting for calculation. | 等待计算 |
| -5008 | sorry, data process calculating. | 正在计算 |
| -5009 | sorry, must complete the last instruction request. | 必须完成上一次计算请求 |
| -5010 | sorry, only supports single code incoming. | 仅支持单代码传入 |
| -5100 | Sorry, account type is not supported. | 抱歉，您的账户类型不支持 |
| -5101 | Please confirm, you have not used the amount of date for the month. | 请确认，您尚未使用本月的数据量 |
| -5102 | Sorry, you have exceeded the maximum number of cleaes. | 抱歉，您已超过最大清零次数 |
| -5103 | Sorry, Do not allow accounts to operate in unbound maccode environments. | 抱歉，不允许账户在非绑定mac代码环境中运行 |
| -5104 | Sorry, this maccode has been bound. | 抱歉，该机器的mac已被绑定 |
| -5000 | please enter a reasonable expected dividend growth rate | 请输入合理的预期红利增长率数值 |

## 四、适用范围

本接口规范适用于同花顺数据接口与服务商端接口

同花顺公司保留本接口最终解释权利

## 五、版本管理

版本信息体现在各函数的url中，新版本版本号逐渐向上累加，旧版本在有用户使用情况下保持不变