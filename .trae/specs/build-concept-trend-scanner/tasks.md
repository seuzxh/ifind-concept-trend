# Tasks

- [ ] Task 0: 接口预验证（前置任务）
  - [x] 0.1 用户提供 refresh_token，验证 Token 获取接口连通性
  - [ ] 0.2 验证 data_pool(p03797) 概念人气明细接口，确认返回字段格式
  - [ ] 0.3 验证 data_pool(p03798) 板块热门成分股接口，确认返回字段格式
  - [ ] 0.4 验证 cmd_history_quotation 接口（日K线：获取昨收价和近5日OHLCV）
  - [ ] 0.5 验证 high_frequency 接口（开盘 5 分钟 K 线：09:30~09:35），确认 indicators 含 LB 量比
  - [ ] 0.6 验证 get_trade_dates 接口（交易日判断）
  - [ ] 0.7 整理验证结果，确认每个接口的返回数据格式

- [x] Task 1: 项目基础结构搭建
  - [x] 1.1 创建项目目录结构（scanner 包、config、tests）
  - [x] 1.2 创建 requirements.txt（requests, apscheduler, pyyaml 等依赖）
  - [x] 1.3 创建配置文件模板（config.yaml：API 地址、refresh_token、阈值参数、webhook URL）

- [x] Task 2: ifind API 数据采集模块
  - [x] 2.1 封装 ifind HTTP 客户端（Token 管理、鉴权、请求重试、错误处理）
  - [x] 2.2 实现概念人气明细接口（data_pool p03797：自选热度、自选热度变化率）
  - [x] 2.3 实现板块热门成分股接口（data_pool p03798：交易代码、涨跌幅）
  - [x] 2.4 实现历史日K线接口（cmd_history_quotation：近5日OHLCV，获取昨收价）
  - [x] 2.5 实现开盘 5 分钟 K 线接口（high_frequency：OHLCV + changeRatio + LB 量比）
  - [x] 2.6 实现交易日判断接口（get_trade_dates）
  - [ ] 2.7 编写接口调用单元测试（基于 Task 0 验证结果 mock 数据）

- [x] Task 3: SQLite 数据存储模块
  - [x] 3.1 设计并创建数据库表结构（详见 SQLite 设计文档，含 kline_daily 表）
  - [x] 3.2 实现数据写入和查询接口
  - [x] 3.3 实现每日数据同步逻辑（人气数据每日同步，含非交易日）

- [ ] Task 4: 多因子综合评分引擎
  - [ ] 4.1 实现昨收价获取（从 cmd_history_quotation 日K线的 T-1 日 close）
  - [ ] 4.2 实现涨幅因子（(最后close - 昨收) / 昨收）
  - [ ] 4.3 实现实体涨幅因子（(最后close - 第1根open) / 第1根open）
  - [ ] 4.4 实现成交额因子（5 根 K 线 amount 求和）
  - [ ] 4.5 实现量比因子（LB 指标直接获取）
  - [ ] 4.6 实现加权综合评分公式（权重可配置）
  - [ ] 4.7 实现概念板块评分（基于成份股得分聚合）
  - [ ] 4.8 编写评分引擎单元测试

- [ ] Task 5: 结果推送模块
  - [ ] 5.1 实现企业微信 webhook 推送
  - [ ] 5.2 设计文本格式扫描报告模板（Top 5 板块 + Top 10 个股）
  - [ ] 5.3 实现推送失败日志记录

- [ ] Task 6: 扫描调度器
  - [ ] 6.1 实现人气数据每日同步调度（含非交易日，每日固定时间触发）
  - [ ] 6.2 实现盘中扫描流程编排（日K获取昨收 → high_frequency 采集 → 评分 → 推送，仅交易日 9:36 触发）
  - [ ] 6.3 实现交易日判断逻辑（调用 get_trade_dates）

- [ ] Task 7: CLI 命令行入口
  - [ ] 7.1 实现 `scan` 命令（立即扫描）
  - [ ] 7.2 实现 `serve` 命令（启动定时服务）
  - [ ] 7.3 实现 `sync` 命令（手动数据同步）

- [ ] Task 8: 端到端集成测试
  - [ ] 8.1 手动触发完整扫描流程验证
  - [ ] 8.2 定时触发验证
  - [ ] 8.3 历史回溯扫描验证

# Task Dependencies

- [Task 1] depends on [Task 0]（接口验证通过后再搭建项目）
- [Task 2] depends on [Task 1]（需要项目结构和配置文件）
- [Task 3] depends on [Task 2]（需要接口数据格式确认）
- [Task 4] depends on [Task 2]（需要接口数据格式确认，评分引擎可并行开发）
- [Task 5] depends on [Task 1]（推送模块可独立开发）
- [Task 6] depends on [Task 2, Task 3, Task 4, Task 5]（编排所有模块）
- [Task 7] depends on [Task 6]（CLI 入口调用调度器）
- [Task 8] depends on [Task 7]（集成测试需要完整系统）

# Parallelizable Work

- Task 2（数据采集）和 Task 4（评分引擎）可并行开发
- Task 5（推送模块）可与其他模块并行开发
