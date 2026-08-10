# SMS Reimbursement Rules

用于生成 Plasgate 短信平台预充值费用的中英文报销说明。短信服务用于客户端注册、登录和忘记密码等验证码场景。

支付周期不按自然月固定发生：当前充值余额使用完或接近用完后才再次支付。因此分析口径是“本次支付/充值周期与上一次支付记录对比”，月份只作为记录标签，不使用自然月环比。

本文件只规定报销文案和计算口径；正式入账仍须遵守 [`RECORDING_RULES.md`](RECORDING_RULES.md)，并以平台账单、发票、充值记录和审批结果为依据。

## 每次报销输入

必填：

- 本次与上一次支付/充值的日期或记录标签。
- 本次与上一次充值周期的短信总量。
- 本次与上一次支付/充值金额（USD）。

按需填写：

- 上一次充值日期和充值金额。
- 本次与上一次充值周期的开始、结束日期。
- 是否在周期天数明确时展示日均短信量与费用。
- 原始发票是否直接交给财务。

## 计算与校验

| 指标 | 公式 | 输出精度 |
|---|---|---|
| 平均单条费用 | 本次周期费用 ÷ 本次周期短信总量 | 4 位小数 |
| 每日平均短信量 | 本次周期短信总量 ÷ 本次周期实际天数 | 整数 |
| 每日平均费用 | 本次支付金额 ÷ 本次周期实际天数 | 2 位小数 |
| 短信量较上次变化 | （本次量 − 上次量）÷ 上次量 × 100% | 1–2 位小数 |
| 费用较上次变化 | （本次金额 − 上次金额）÷ 上次金额 × 100% | 1–2 位小数 |
| 单条费用较上次变化 | （本次单价 − 上次单价）÷ 上次单价 × 100% | 1–2 位小数 |

规则：

- 报销费用保留 2 位小数，币种固定写为 `USD` 或 `$`，同一文案内保持一致；原始数据可以保留更多小数用于计算。
- 平均单价与“总费用 ÷ 总量”不一致时，以重新计算结果为准。
- 只有充值周期起止日期明确时才计算日均值，不用月份天数代替实际使用天数。
- 默认比较相邻两次实际支付/充值记录，即使两次记录不属于连续自然月。
- 上一次记录的分母为 0 或数据缺失时，不计算百分比，改写为“无可比基数”或“数据待补”。
- 增长写“增加约 X%”，下降写“减少约 X%”；差异处于已批准的微小阈值内可写“基本保持稳定”。未批准阈值前不得自行定义。
- 英文若只要求语法修正，不增加中文原文没有的信息。
- 计算结果用于报销说明，不替代账单核对、审批或会计入账。

## 中文简版模板

```text
充值短信服务平台 Plasgate，用于支持客户端注册、登录、忘记密码等验证码短信。

本次（{本次记录标签}）短信总量为 {本次短信量} 条，
报销费用约为 ${本次费用}，
平均单条短信费用约为 ${本次平均单价}。

对比上一次支付记录（{上次记录标签}：{上次短信量} 条，${上次费用}，平均单条约 ${上次平均单价}）：
- 短信量{增加/减少}约 {短信量变化}%
- 费用{增加/减少}约 {费用变化}%
- 平均单条费用{增加/减少}约 {单价变化}% / 基本保持稳定
```

需要说明充值时追加：

```text
预充值消费，上一次充值日期为 {YYYY 年 MM 月 DD 日}，金额为 {金额} 美金。
```

## English template

```text
Apply for reimbursement for the prepaid SMS service provided by Plasgate ({current record label}).

The total SMS volume for this recharge cycle was {current volume} messages,
with a total cost of USD {current cost},
and an average cost per message of approximately USD {current unit cost}.

Compared with the previous payment record ({previous record label}: {previous volume} messages, USD {previous cost},
average cost per message approximately USD {previous unit cost}),
SMS volume increased/decreased by approximately {volume change}%,
total cost increased/decreased by approximately {cost change}%,
and the average cost per message increased/decreased by approximately {unit-cost change}% / remained stable.
```

按需追加：

```text
Previous recharge date: {Mon. D, YYYY}; amount: USD {amount}.
The original invoice will be sent directly to Finance.
```

只有实际安排已确认时，才保留发票递交说明。

## 详细版模板

```text
本次充值周期每日短信量平均为 {每日平均短信量} 条，平均单条短信费用约为 ${平均单价}，
短信费用约为 ${每日平均费用} / 天、${本次费用} / 本周期；对比上一次支付记录，短信量{增加/减少}约 {短信量变化}%。
```

如用于正式财务说明，可同时补充费用和平均单价较上次的变化。周期日期不完整时不使用详细版。

## 报销与入账检查

- [ ] 平台用量期间与本次充值周期一致。
- [ ] 短信总量、费用和币种可追溯到平台账单。
- [ ] 充值日期和金额可追溯到付款或充值记录。
- [ ] 平均值、实际周期天数和较上次变化已重新计算。
- [ ] 发票、账单及审批状态已经记录。
- [ ] 预充值余额与本次周期实际消耗分开记录，未把未消耗余额直接计入本期费用。
- [ ] 缺失凭证或数据差异已进入待办清单。

## 来源

- 2026-07-22：根据用户提供的《短信平台报销文案规则整理》建立；仅提炼长期有效规则，不导入示例金额或未确认账目。
- 2026-07-22：根据实际支付方式改为按相邻充值周期比较，不再默认使用自然月环比。
