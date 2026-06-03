# Checklist

## 接口切换

- [x] client.py: get_concept_popularity 使用 p03793 + hyfl 参数
- [x] client.py: get_board_stocks 使用 p03794 + hyfl 参数
- [x] sync.py: 字段解析使用 p03793_* / p03794_* 字段名

## 接口验证

- [x] p03793 接口返回数据正确（257 个行业名称、热度、变化率）
- [x] p03794 接口返回数据正确（845 只股票代码、涨跌幅）
- [x] 完整回溯 20260602 验证通过（1172 只个股 + 77 个行业 + 34 只强势）
