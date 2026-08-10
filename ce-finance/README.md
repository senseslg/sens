# ce-finance

CE 财务与账目管理子项目，用于统一维护账目范围、账户索引、收支分类、应收应付、对账、月结和财务行动项。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：目标、范围、当前状态和行动项。
2. [ACCOUNT_CATALOG.md](ACCOUNT_CATALOG.md)：账户、主体、币种和用途索引。
3. [RECORDING_RULES.md](RECORDING_RULES.md)：账目字段、分类、凭证和校验规则。
4. [SMS_REIMBURSEMENT_RULES.md](SMS_REIMBURSEMENT_RULES.md)：Plasgate 相邻充值周期报销的输入、计算和中英文模板。
5. [MONTHLY_CLOSE_RUNBOOK.md](MONTHLY_CLOSE_RUNBOOK.md)：月度对账与关账流程。
6. [ROADMAP.md](ROADMAP.md)：分阶段建设计划。

## 当前状态

- 状态：`proposed`
- 建立日期：`2026-07-22`
- 已确认：该子项目主要用于管理账目内容。
- 已建立：Plasgate 短信平台按实际充值周期发生的报销文案和计算规则。
- 待确认：管理主体、账户范围、币种、起始期间、现有数据来源和负责人。

## 数据边界

- Markdown 文件保存规则、索引、摘要、决定和行动项。
- 逐笔流水达到一定规模后，应使用结构化表格或财务系统，不在说明文档中无限追加。
- 不记录完整银行卡号、网银账号、密码、验证码、Token、身份证件号或未脱敏的付款凭证。
- 金额记录必须保留币种、日期、业务主体、分类、对方、凭证状态和核对状态。
- 本项目用于内部工作管理，不替代持牌会计师、审计师或税务专业意见。
