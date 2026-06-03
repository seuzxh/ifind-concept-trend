# Checklist

## 接口切换

- [ ] client.py: get_concept_popularity 使用 p03793 + hyfl 参数
- [ ] client.py: get_board_stocks 使用 p03794 + hyfl 参数
- [ ] sync.py: 字段解析使用 p03793_* / p03794_* 字段名

## 接口验证

- [ ] p03793 接口返回数据正确（行业名称、热度、变化率）
- [ ] p03794 接口返回数据正确（股票代码、涨跌幅）
- [ ] 完整回溯至少 1 个交易日验证通过
