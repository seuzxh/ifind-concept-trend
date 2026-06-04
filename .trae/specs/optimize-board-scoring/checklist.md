* [x] scorer.py `_score_boards` 使用 Top 50 个股反推板块评分

* [x] board\_score 公式 = top50\_count × 10 + top50\_avg\_score × 0.5

* [x] top50\_count = 0 的板块被过滤

* [x] 新增字段 top50\_count、top50\_avg\_score、top50\_avg\_change、board\_avg\_change 写入 board\_daily\_scan

* [x] 推送报告 Top 5 板块标题显示 top50\_count 和 board\_avg\_change

* [x] 推送报告板块内成分股按涨幅降序展示 Top 5

* [x] 回测摘要和 CLI 输出适配新字段

* [x] 回测 0520-0602 全部成功，结果符合预期

