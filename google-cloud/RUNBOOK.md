# Google Cloud 控制台检查手册

本文件仅记录 `2026-09-17` 已在 Chrome 控制台核实的入口和只读步骤。页面显示会变化，操作前先确认右上角项目为 `Cambodian Express` / `cambodian-express`。

## 2026-10-24 成本只读复核

更多控制台入口见 [成本清单](COST_OPTIMIZATION_CHECKLIST_2026-10-24.md#2-入口索引)。已验证的复查命令：

```bash
python3 google-cloud/scripts/cloud_cost_audit.py --project cambodian-express --days 30 --output /private/tmp/gcp-cost-audit.json
```

需已有 gcloud 登录与读取资源/监控权限。脚本只读，凭据不落盘；使用 certifi 或系统受信任 CA，保持 TLS 校验。退出 0=完成，2=部分失败，1=执行失败；输出 JSON 内每项错误须检查。CPU *_peak 用小时采样最大值，其余利用率用小时均值；缺失内存/旧实例覆盖不完整时，不据低 CPU 自动降配。

对象年龄汇总使用现有 Insights 数据集的 [只读 SQL](scripts/storage_age_summary.sql)，运行前核对数据集和冻结日期，并做 BigQuery dry-run/设置 maximum_bytes_billed；不扫描文件内容或创建删除任务。2026-10-24 实际查询计费扫描约 542 MiB（SELECT），不是 dry-run 所示约 49.6 GB 上界。

## 已核实入口

| 目的 | 控制台入口 |
|---|---|
| 项目主页与项目编号 | [Welcome](https://console.cloud.google.com/welcome?project=cambodian-express) |
| Compute Engine 资源总览 | [Overview](https://console.cloud.google.com/compute/overview?project=cambodian-express) |
| VM 当前状态与所在区域 | [VM instances](https://console.cloud.google.com/compute/instances?project=cambodian-express) |
| 托管/非托管实例组与成员数 | [Instance groups](https://console.cloud.google.com/compute/instanceGroups/list?project=cambodian-express) |

## 只读检查

1. 在项目主页核对显示名、项目 ID 和项目编号；切换项目后重新核对。
2. 在 Compute Engine 总览读取 VM、实例组、磁盘、快照和映像的当前数量，注明采集时间。
3. 在 VM 列表核对目标名称、区域、状态和实例组归属。托管实例组的活动 VM 需每次重新发现。
4. 在实例组列表核对成员数、模板、自动扩缩容状态及关联后端。出现警告时先确认业务预期。
5. 需要判断服务是否正常时，转到对应子项目验证 SSH、端口、日志和应用；VM 的 `Running` 状态不足以作出该结论。

如果需要 CLI，先核实当前账号、项目和区域；本目录暂不把未验证的 CLI 命令作为固定操作流程。
