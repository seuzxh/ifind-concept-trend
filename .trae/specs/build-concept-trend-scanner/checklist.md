# Checklist

## 接口验证 — Task 0

### 0.1 Token 鉴权
- [x] get_access_token 接口连通，返回有效 access_token
- [x] 确认 access_token 有效期（7 天）
- [x] 确认 refresh_token 可正常使用

### 0.2 概念人气明细 (p03797)
- [x] data_pool(p03797) 接口连通，返回数据（约 380+ 个概念板块）
- [x] 确认 `p03797_f001` 字段为概念板块名称
- [x] 确认 `p03797_f002` 字段为交易日期（格式 YYYY/MM/DD）
- [x] 确认 `p03797_f009` 字段为自选热度（字符串数值）
- [x] 确认 `p03797_f010` 字段为自选热度变化率（字符串数值）
- [x] 确认 functionpara 参数名为 `date` / `tjzq`（非 p03797_f002/f003）
- [x] 确认返回格式为列式数组（每个字段一个数组）

### 0.3 板块热门成分股 (p03798)
- [x] data_pool(p03798) 接口连通，返回数据
- [x] 确认 `jydm` 字段为交易代码（格式 600584.SH）
- [x] 确认 `jydm_mc` 字段为交易代码名称
- [x] 确认 `p03798_f001` 字段为交易日期
- [x] 确认 `p03798_f012` 字段为涨跌幅（数值）
- [x] 确认 `p03798_f016` 字段为区间开始日期
- [x] 确认 functionpara 参数名为 `date` / `hy` / `tjzq`
- [x] 确认返回格式为列式数组

### 0.4 历史日K线 (cmd_history_quotation)
- [x] 接口连通，返回近 5 个交易日日线数据
- [x] `open/high/low/close` 价格字段完整
- [x] `volume/amount` 成交量/额字段完整
- [x] 取最后一根 K 线的 close 作为昨收价，数值合理
- [x] 确认 thscode 和 time 在 tables[0] 外层，指标在 tables[0].table 内
- [x] 确认返回格式为列式数组

### 0.5 开盘 5 分钟 K 线 (high_frequency)
- [x] 接口连通，返回 09:30~09:35 的 6 根 1 分钟 K 线
- [x] `open/high/low/close` 价格字段完整
- [x] `volume/amount` 成交量/额字段完整
- [x] `changeRatio` 涨跌幅字段完整
- [x] `LB`（量比）技术指标字段存在且数值合理（需 `calculate: {"LB": "5"}` 参数）
- [x] 确认返回格式为列式数组

### 0.6 交易日判断 (get_trade_dates)
- [x] 接口连通，正确返回交易日列表
- [x] 交易日返回日期，周末不在返回中
- [x] 确认返回格式为 `tables.time` 字典（非列表）

### 0.7 验证结果整理
- [x] 每个接口的返回 JSON 格式已记录（见 Docs/ifind接口验证清单.md）
- [x] client.py 参数名和数据解析已根据验证结果修复

## 数据采集 — Task 2

### 2.1 HTTP 客户端
- [x] IfindClient 封装完成（Token 管理、速率限制、错误处理）
- [x] refresh_token 通过环境变量读取，不进代码

### 2.2~2.6 接口方法
- [x] get_concept_popularity 方法实现正确（p03797）
- [x] get_board_stocks 方法实现正确（p03798）
- [x] get_history_quotation 方法实现正确（cmd_history_quotation）
- [x] get_high_frequency 方法实现正确（含 calculate 参数）
- [x] get_trade_dates 方法实现正确

### 2.7 数据解析
- [x] _extract_table_rows 支持列式数组转行式字典列表
- [x] _extract_date_list 支持 tables.time 字典格式

### 2.8 单元测试
- [ ] 接口调用单元测试编写完成（基于验证结果 mock 数据）

## 数据存储 — Task 3

### 3.1 表结构
- [x] concept_popularity 表创建正确
- [x] board_stock_relation 表创建正确
- [x] kline_daily 表创建正确
- [x] kline_1min 表创建正确
- [x] stock_daily_scan 表创建正确
- [x] board_daily_scan 表创建正确

### 3.2 CRUD 接口
- [x] upsert 接口支持 INSERT OR REPLACE
- [x] query 接口支持按日期、股票代码查询

### 3.3 每日数据同步编排
- [x] 概念板块筛选：热度 Top20 + 变化率 Top20 合并去重
- [x] 成分股筛选：每板块按涨跌幅取 Top30，剔除 ST 股
- [x] 去重得观察股池（实际验证：40 个板块 → 561 只去重股票）
- [x] 批量获取日K线和 1 分钟 K 线并存入 SQLite

### 3.4 scan_result 表
- [ ] stock_daily_scan 表写入和查询接口实现
- [ ] board_daily_scan 表写入和查询接口实现

## 多因子评分引擎 — Task 4

### 4.1~4.5 因子计算
- [ ] 昨收价从 kline_daily 表正确获取（T-1 日 close）
- [ ] 涨幅计算正确：（最后 close - 昨收）/ 昨收 × 100%
- [ ] 实体涨幅计算正确：（最后 close - 第1根 open） / 第1根 open × 100%
- [ ] 成交额累计正确：5 根 K 线 amount 求和
- [ ] 量比获取正确：从 kline_1min 取最后一根 K 线的 LB 值

### 4.6~4.8 评分与标记
- [ ] 加权综合评分公式实现正确（权重可配置）
- [ ] 强势个股标记逻辑正确（涨幅 > 7% 或实体涨幅 > 5%）
- [ ] 概念板块评分公式正确（强势占比 × 60% + 平均得分 × 40%）

### 4.9~4.10 结果存储与测试
- [ ] 评分结果写入 stock_daily_scan 和 board_daily_scan 表
- [ ] 评分引擎单元测试编写完成

## 推送模块 — Task 5

- [ ] 企业微信 webhook 推送成功
- [ ] 推送报告内容清晰（Top 5 板块 + Top 10 个股）
- [ ] 推送失败时不阻塞主流程，日志记录正常

## 扫描调度器 — Task 6

- [ ] 每日同步调度正常（含非交易日）
- [ ] 盘中扫描在交易日 9:36 正确触发
- [ ] 非交易日自动跳过盘中扫描
- [ ] 手动触发扫描正常工作
- [ ] 指定日期回溯扫描正常工作

## CLI 入口 — Task 7

- [ ] `python -m scanner scan` 命令正常执行（支持 --date 参数）
- [ ] `python -m scanner serve` 命令正常启动定时服务
- [ ] `python -m scanner sync` 命令正常执行数据同步

## 集成测试 — Task 8

- [ ] 手动触发完整扫描流程验证通过
- [ ] 定时触发验证通过
- [ ] 历史回溯扫描验证通过
- [ ] 推送验证通过

## 代码质量

- [ ] 所有代码符合 Google Python 编码规范
- [ ] 类型注解覆盖公开 API
- [ ] 关键模块有单元测试覆盖
