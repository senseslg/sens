# Google Cloud 控制台检查手册

本文件仅记录 `2026-09-17` 已在 Chrome 控制台核实的入口和只读步骤。页面显示会变化，操作前先确认右上角项目为 `Cambodian Express` / `cambodian-express`。

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
