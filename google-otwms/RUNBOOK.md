# Google OTWMS Runbook

## 参数

- Project：`cambodian-express`
- Zone：`asia-southeast1-a`
- SSH user：`senseslg`
- Production instance pattern：`otwms-group-*`
- UAT instance：`otwms-uat`

## 生产实例发现

生产实例属于 Managed Instance Group，连接前先查询当前活动实例：

```bash
gcloud compute instances list \
  --project=cambodian-express \
  --filter="name~'^otwms-group-'" \
  --format="table(name,zone.basename(),status)"
```

确认目标实例处于预期状态后，将查询结果中的实例名用于 SSH。来源快照中的实例是 `otwms-group-5dbm`：

```bash
gcloud compute ssh senseslg@otwms-group-5dbm \
  --project=cambodian-express \
  --zone=asia-southeast1-a
```

如果 MIG 已重建实例，必须替换上面的实例名。

## UAT SSH

显式指定远程用户，避免 GCloud CLI 使用本机用户名 `lingang`：

```bash
gcloud compute ssh senseslg@otwms-uat \
  --project=cambodian-express \
  --zone=asia-southeast1-a
```

失败时运行诊断：

```bash
gcloud compute ssh senseslg@otwms-uat \
  --project=cambodian-express \
  --zone=asia-southeast1-a \
  --troubleshoot
```

如果返回 `Permission denied (publickey,...)`，不要先处理磁盘或重启实例，按 [SSH_TROUBLESHOOTING.md](SSH_TROUBLESHOOTING.md) 检查远程用户、GCloud 身份、SSH Key、Metadata 和 OS Login。

## 只读巡检清单

登录后依次确认：

1. 根磁盘容量和使用率。
2. 根目录主要空间占用。
3. Java 进程是否存在、是否符合预期。
4. 是否存在 deleted file handle。
5. `/home/daniel/bladex.log` 与 `/home/daniel/nohup.out` 的大小和增长情况。
6. 应用是否可以正常响应。

常用只读检查：

```bash
df -h /
du -sh /home/daniel/bladex.log /home/daniel/nohup.out
ps -ef | grep '[j]ava'
lsof +L1
```

部分系统上的 `lsof` 可能需要提升权限；只在获准后使用相应权限。

## 磁盘告警处理原则

先收集证据：

- `df -h` 当前使用率。
- 两个主要日志文件的当前大小。
- Java 进程状态。
- deleted file handle 情况。
- 应用可用性。

来源事故中采用的处理顺序是：停止 Java 写入、清理主要日志、重启应用。该流程会中断服务，不能作为无确认的自动操作。

## 恢复验证

任何修复完成后至少验证：

- [ ] 根磁盘空间已经恢复到安全范围。
- [ ] Java 正常运行。
- [ ] 没有异常 deleted file handle。
- [ ] 主要日志文件大小合理，且增长速度可解释。
- [ ] 应用启动并通过业务可用性检查。
- [ ] 记录处理时间、执行人、前后状态和异常情况。

## 自动巡检工具

来源摘要提到 `check_gcloud_otwms_disk.py v1.0.0`，但本次建档时未在 `/Users/lingang/Downloads` 找到该脚本，因此这里只记录功能和规划，不声称脚本已经纳入当前仓库。详情见 [ROADMAP.md](ROADMAP.md)。
