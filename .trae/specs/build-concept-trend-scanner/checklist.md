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
- [x] get_kline_1min_batch 批量查询 1min K 线（按股票分组）
- [x] get_stock_concepts 查询股票所属概念板块列表

### 3.3 每日数据同步编排
- [x] 概念板块筛选：热度 Top20 + 变化率 Top20 合并去重
- [x] 成分股筛选：每板块按涨跌幅取 Top30，剔除 ST 股
- [x] 去重得观察股池（实际验证：40 个板块 → 561 只去重股票）
- [x] 批量获取日K线和 1 分钟 K 线并存入 SQLite

### 3.4 scan_result 表
- [x] stock_daily_scan 表写入（save_stock_scan_results）验证通过（561 条）
- [x] board_daily_scan 表写入（save_board_scan_results）验证通过（40 条）
- [x] get_top_stocks / get_top_boards 查询接口可用

## 多因子评分引擎 — Task 4

### 4.1~4.5 因子计算
- [x] 昨收价从 kline_daily 表正确获取（T-1 日 close，561 只全部获取成功）
- [x] 涨幅计算正确：（最后 close - 昨收）/ 昨收 × 100%
- [x] 实体涨幅计算正确：（最后 close - 第1根 open） / 第1根 open × 100%
- [x] 成交额累计正确：5 根 K 线 amount 求和
- [x] 量比因子预留（LB 暂未入库，默认 0，待后续 high_frequency LB 数据入库后补充）

### 4.6~4.8 评分与标记
- [x] 加权综合评分公式实现正确（百分位归一化 + 四因子加权，权重可配置）
- [x] 强势个股标记逻辑正确（涨幅 > 7% 或实体涨幅 > 5%，验证：25 只标记为强势）
- [x] 概念板块评分公式正确（强势占比 × 60% + 平均得分 × 40%，验证：40 个板块评分完成）

### 4.9~4.10 结果存储与测试
- [x] 评分结果写入 stock_daily_scan 和 board_daily_scan 表（DB 查询验证一致）
- [x] 评分引擎验证测试编写完成（tests/verify_scorer.py，真实数据验证通过）

### 验证数据摘要（2026-06-02）
- TOP 1 个股：301205.SZ 联特科技 score=86.07 涨幅=+9.39% [STRONG]
- TOP 1 板块：共封装光学(CPO) board_score=42.51 strong=8/30
- 561 只个股全部评分，40 个板块全部聚合

## 推送模块 — Task 5

- [x] 飞书 webhook 推送实现（交互卡片格式，msg_type=interactive + markdown card）
- [x] 扫描报告模板设计：
  - [x] 标题：`### 概念板块强势扫描 {T日}`
  - [x] 概览行：扫描时间 / 观察股池数 / 强势个股数
  - [x] Top 5 强势板块：排名、板块名、得分、强势N/总数M
  - [x] Top 10 强势个股：排名、代码、名称、得分、涨幅、实体涨幅、成交额
  - [x] 强势个股加粗显示
  - [x] Markdown 内容不超过 20480 字节（飞书限制 20KB）
- [x] 推送失败时 logger.error 记录异常，不阻塞主流程
- [x] Webhook URL 从 config.yaml 读取
- [x] 飞书推送连通性测试通过（HTTP 200，msg: success）

## 扫描调度器 — Task 6

- [x] 每日同步调度正常（含非交易日，9:00 触发）
- [x] 盘中扫描在交易日 9:33 正确触发
- [x] 非交易日自动跳过盘中扫描
- [x] 手动触发扫描正常工作
- [x] 指定日期回溯扫描正常工作

## CLI 入口 — Task 7

- [x] `python -m scanner scan` 命令正常执行（支持 --date 参数）
- [x] `python -m scanner serve` 命令正常启动定时服务（sync=9:00, scan=9:33）
- [x] `python -m scanner sync` 命令正常执行数据同步
- [x] `python -m scanner backtest` 命令正常执行回溯测试

## 集成测试 — Task 8

- [x] 手动触发完整扫描流程验证通过
- [x] 定时触发配置完成（crontab: 周一至周五 9:00 sync、9:33 scan）
- [x] 历史回溯扫描验证通过
- [x] 推送验证通过

## 代码质量

- [x] 所有代码符合 Google Python 编码规范
- [x] 类型注解覆盖公开 API
- [x] 关键模块有单元测试覆盖
