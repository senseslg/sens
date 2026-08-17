# MySQL 大型 IN 查询诊断

## 当前结论

字段已有索引不代表超大 `IN` 一定使用索引。MySQL 可能因 `range_optimizer_max_mem_size` 不足而跳过范围优化，退化为全表扫描。

## 安全检查顺序

1. 统计参数数量，不输出业务值。
2. 用 `information_schema.TABLES` 获取估算行数、数据量和索引量。
3. 用 `SHOW INDEX` 确认过滤列及联合索引顺序。
4. 使用少量虚构值执行 `EXPLAIN`，确认基础计划。
5. 用与事故相同数量的虚构值执行 `EXPLAIN`，随后立即执行 `SHOW WARNINGS`。
6. 核对 `@@global.max_execution_time`、`@@session.max_execution_time` 和 `@@range_optimizer_max_mem_size`。
7. 用多个批量级别的虚构值对比计划变化，不执行真实业务 SELECT。

## 关键判定

以下组合可以确认 optimizer 内存导致的计划退化：

- 小批量为 `type=range` 且选择目标索引。
- 大批量变为 `type=ALL`、`key=NULL`。
- `SHOW WARNINGS` 出现错误码 3170，并说明 `range_optimizer_max_mem_size` 被超过。
- 查询失败时间与 `max_execution_time` 一致，错误码为 3024。

## 修复优先级

1. 应用层去重并分批查询，合并结果。
2. 大规模长期需求可评估临时表或批量表连接方案。
3. optimizer 内存和语句超时只作为受控应急调整，并评估全局资源影响。

不要因已有超时就直接增加超时时间，也不要在未看执行计划前重复执行相同生产查询。
