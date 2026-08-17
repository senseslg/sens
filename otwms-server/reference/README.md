# OTWMS Server Reference

本目录保存 OTWMS 后端中经过验证、可复用但尚未登记为项目 Skill 的诊断方法。

| 文件 | 用途 |
|---|---|
| [xxl-job-source-tracing.md](xxl-job-source-tracing.md) | 从 XXL-JOB 失败记录追踪到执行器、JAR、源码仓库和 Jenkins Job |
| [mysql-large-in-query.md](mysql-large-in-query.md) | 只读诊断大型 `IN` 查询的索引计划、optimizer 内存和语句超时 |

当同一流程再次出现且步骤保持稳定时，再评估登记到根目录 `SKILL.md`；只有重复命令已验证并适合安全自动化时才生成 `scripts/*.py`。
