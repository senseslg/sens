# TMS Reference

经过本次故障验证、可迁移但尚未形成项目 Skill 的方法：

| 文件 | 用途 |
|---|---|
| [http-readiness-vs-tcp-health.md](http-readiness-vs-tcp-health.md) | 区分端口可连接、HTTP 就绪和业务可用；避免 Jenkins/负载均衡假阳性 |

仅当流程重复出现、步骤稳定且自动化风险可控时，再考虑登记到根目录 `SKILL.md` 或生成默认只读的脚本。
