# Tasks

- [ ] Task 1: 更新 `scanner/client.py` 接口调用
  - [ ] 1.1 `get_concept_popularity`: p03797 → p03793，新增 hyfl 参数，字段名更新
  - [ ] 1.2 `get_board_stocks`: p03798 → p03794，新增 hyfl 参数，字段名更新
- [ ] Task 2: 更新 `scanner/sync.py` 字段解析
  - [ ] 2.1 `sync_concept_popularity`: p03797_f001/f009/f010 → p03793_f001/f009/f010
  - [ ] 2.2 `sync_board_stocks`: p03798_f012/f016 → p03794_f012/f016
- [ ] Task 3: 验证接口调用
  - [ ] 3.1 调用 p03793 验证返回数据格式和字段
  - [ ] 3.2 调用 p03794 验证返回数据格式和字段
  - [ ] 3.3 运行完整回溯验证（至少 1 个交易日）
  - [ ] 3.4 提交代码

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
