# Tasks

- [x] Task 0: 接口预验证（前置任务）
  - [x] 0.1 用户提供 refresh_token，验证 Token 获取接口连通性
  - [x] 0.2 验证 data_pool(p03797) 概念人气明细接口，确认返回字段格式（列式数组）
  - [x] 0.3 验证 data_pool(p03798) 板块热门成分股接口，确认返回字段格式（列式数组）
  - [x] 0.4 验证 cmd_history_quotation 接口（日K线：获取昨收价和近5日OHLCV）
  - [x] 0.5 验证 high_frequency 接口（开盘 5 分钟 K 线），确认 LB 需 `calculate: {"LB": "5"}` 参数
  - [x] 0.6 验证 get_trade_dates 接口（交易日判断），确认返回 `tables.time` 字典格式
  - [x] 0.7 整理验证结果，更新验证清单文档

- [x] Task 1: 项目基础结构搭建
  - [x] 1.1 创建项目目录结构（scanner 包、config、tests、Docs）
  - [x] 1.2 创建 requirements.txt（requests, apscheduler, pyyaml 等依赖）
  - [x] 1.3 创建配置文件模板（config.yaml.template）和环境变量模板（.env.example）
  - [x] 1.4 创建 .gitignore（排除 .env、data/、config/config.yaml 等敏感文件）

- [x] Task 2: ifind API 数据采集模块
  - [x] 2.1 封装 ifind HTTP 客户端 IfindClient（Token 管理、鉴权、速率限制 0.1s 间隔、错误处理）
  - [x] 2.2 实现概念人气明细接口 get_concept_popularity（p03797：functionpara 用 date/tjzq）
  - [x] 2.3 实现板块热门成分股接口 get_board_stocks（p03798：functionpara 用 date/hy/tjzq）
  - [x] 2.4 实现历史日K线接口 get_history_quotation（cmd_history_quotation：近5日OHLCV）
  - [x] 2.5 实现开盘 5 分钟 K 线接口 get_high_frequency（含 calculate 参数支持 LB 量比）
  - [x] 2.6 实现交易日判断接口 get_trade_dates
  - [x] 2.7 实现列式数组转行式解析 _extract_table_rows（兼容 data_pool / history / high_frequency）
  - [ ] 2.8 编写接口调用单元测试（基于 Task 0 验证结果 mock 数据）

- [x] Task 3: SQLite 数据存储模块
  - [x] 3.1 设计并创建数据库表结构（6 张表：concept_popularity、board_stock_relation、kline_daily、kline_1min、stock_daily_scan、board_daily_scan）
  - [x] 3.2 实现 upsert 和 query 接口（支持 INSERT OR REPLACE）
  - [x] 3.3 实现每日数据同步编排逻辑：
    - 获取全部概念人气（p03797）→ 按热度 Top20 + 变化率 Top20 合并去重得热门板块
    - 逐板块获取成分股（p03798）→ 按涨跌幅 Top30、剔除 ST 股 → 合并去重得观察股池
    - 批量获取日K线（cmd_history_quotation）和 1 分钟 K 线（high_frequency）
    - 全部写入 SQLite
  - [ ] 3.4 实现 scan_result 表的写入和查询接口（stock_daily_scan、board_daily_scan）

- [ ] Task 4: 多因子综合评分引擎
  - [ ] 4.1 实现昨收价获取（从 kline_daily 表查询 T-1 日 close）
  - [ ] 4.2 实现涨幅因子（(最后 close - 昨收) / 昨收 × 100%）
  - [ ] 4.3 实现实体涨幅因子（(最后 close - 第1根 open) / 第1根 open × 100%）
  - [ ] 4.4 实现成交额因子（5 根 K 线 amount 求和）
  - [ ] 4.5 实现量比因子（从 kline_1min 获取最后一根 K 线的 LB 值）
  - [ ] 4.6 实现加权综合评分公式（权重可配置：涨幅 0.25、实体涨幅 0.30、成交额 0.20、量比 0.25）
  - [ ] 4.7 实现强势个股标记（涨幅 > 7% 或实体涨幅 > 5% 标记为"强势"）
  - [ ] 4.8 实现概念板块评分（板块强势得分 = 强势个股占比 × 60% + 板块平均得分 × 40%）
  - [ ] 4.9 实现评分结果写入 scan_result 表（stock_daily_scan、board_daily_scan）
  - [ ] 4.10 编写评分引擎单元测试

- [ ] Task 5: 结果推送模块
  - [ ] 5.1 实现企业微信 webhook 推送（文本格式）
  - [ ] 5.2 设计扫描报告模板（Top 5 强势板块：板块名、得分、强势个股数；Top 10 强势个股：股票名、代码、得分、关键指标）
  - [ ] 5.3 实现推送失败日志记录（不阻塞主流程）

- [ ] Task 6: 扫描调度器
  - [ ] 6.1 实现每日同步编排（含非交易日，如每日 20:00 触发：p03797 → p03798 → kline_daily → kline_1min → SQLite）
  - [ ] 6.2 实现盘中扫描编排（仅交易日 9:36 触发：trade_dates 判断 → history_quotation → high_frequency → 评分 → push）
  - [ ] 6.3 实现交易日判断逻辑（调用 get_trade_dates，非交易日跳过盘中扫描）
  - [ ] 6.4 支持手动触发和指定日期回溯扫描

- [ ] Task 7: CLI 命令行入口
  - [ ] 7.1 实现 `scan` 命令（立即触发盘中扫描，支持 --date 参数回溯）
  - [ ] 7.2 实现 `serve` 命令（启动 APScheduler 定时服务，等待 9:36 自动触发）
  - [ ] 7.3 实现 `sync` 命令（手动触发数据同步，不执行评分）

- [ ] Task 8: 端到端集成测试
  - [ ] 8.1 手动触发完整扫描流程验证（scan 命令）
  - [ ] 8.2 定时触发验证（serve 命令）
  - [ ] 8.3 历史回溯扫描验证（scan --date YYYYMMDD）
  - [ ] 8.4 推送验证（webhook 推送成功）

# Task Dependencies

- [Task 1] depends on [Task 0]（接口验证通过后再搭建项目）
- [Task 2] depends on [Task 1]（需要项目结构和配置文件）
- [Task 3] depends on [Task 2]（需要接口数据格式确认）
- [Task 4] depends on [Task 2, Task 3]（需要接口数据和 kline_daily 表）
- [Task 5] depends on [Task 1]（推送模块可独立开发）
- [Task 6] depends on [Task 2, Task 3, Task 4, Task 5]（编排所有模块）
- [Task 7] depends on [Task 6]（CLI 入口调用调度器）
- [Task 8] depends on [Task 7]（集成测试需要完整系统）

# Parallelizable Work

- Task 2.8（单元测试）可与其他任务并行
- Task 4（评分引擎）和 Task 5（推送模块）可并行开发
