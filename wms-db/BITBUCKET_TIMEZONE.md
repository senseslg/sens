# Bitbucket 金边时区配置（2026-10-23）

## 当前配置

按用户授权，将 `code.cambodianexpress.com` 的 Bitbucket Java 服务时区从 `Etc/UTC` 改为 `Asia/Phnom_Penh`（UTC+7），仅重启 `bitbucket` 容器。运行中 JVM 已核对 `user.timezone=Asia/Phnom_Penh`，新应用日志时间也变为 UTC+7；可用性验证结果见下方。

实例为 GCP `wms-db`，镜像 `bitbucket/bitbucket`，安装版本 4.0.2。宿主机原本就是 `Asia/Phnom_Penh`，本次未改宿主机时钟或容器 OS 时区；容器的 `date` 仍可显示 UTC，不等于 Java 设置失效。历史 Git 提交的原始时间信息及旧日志未改写。

## 修改与持久化

- 当前容器 `/opt/atlassian/bitbucket/bin/setenv.sh`：将 `JVM_SUPPORT_RECOMMENDED_ARGS` 从空值改为 `-Duser.timezone=Asia/Phnom_Penh`。保留其他 JVM 参数及原有脚本权限，普通容器重启保留该修改。
- 宿主机 `/home/daniel/containers/bitbucket/docker.sh`：在 `docker run` 参数中增加 `--env JAVA_OPTS=-Duser.timezone=Asia/Phnom_Penh`。以后通过该脚本重建容器会继续采用此时区；没有实际重建容器验证。
- 没有重新构建镜像；如改用其他创建方式，需显式携带同一 Java 参数，不能只依赖当前容器文件修改。
- 两份脚本均通过 `bash -n` 检查；重启前未发现活动 Git 进程。容器重启完成时间为 2026-10-23 20:53:00（UTC+7，Docker StartedAt 换算）。

## 备份与回滚

备份目录：`/home/daniel/containers/bitbucket/backups/timezone-20261023T135143Z`，目录权限 `700`。包含原始 `docker.sh`、`setenv.sh` 和摘要清单，文件权限 `600`；这是配置备份，不是仓库或数据库备份。

若本次配置导致问题，先恢复该目录中的 `setenv.sh` 到当前容器同一路径（保留目标文件原有属主和执行权限），恢复宿主机 `docker.sh` 内容，再检查脚本语法并仅重启 `bitbucket`。恢复后核对 JVM 时区、HTTP 和 Git SSH。未实际执行回滚演练；后续已有其他配置修改时，不直接覆盖整份旧备份，应只撤销此次时区参数。

## 本次验证

- 运行中 JVM：`user.timezone=Asia/Phnom_Penh`，启动后应用日志使用金边时间。
- 本机 `7990/status` 与公网 `https://code.cambodianexpress.com/status`：HTTP 200，`state=RUNNING`。
- 公网 `/login`：HTTP 200，返回 Bitbucket 页面。
- 公网 Git SSH 9200：返回 `SSH-2.0-SSHD-CORE-0.14.1-ATLASSIAN-01`。未执行实际仓库拉取或推送。
- 本次启动期间检查到 0 条 ERROR，存在 Marketplace/UPM 请求异常类提示，未阻止启动；不将其表述为所有插件外部连接正常。
- 重启后的普通服务验收已完成；容器重建与回滚路径仅做配置核对，未实际执行。

## 后续核对方法

1. `docker exec bitbucket jcmd 1 VM.system_properties` 的结果仅筛选 `user.timezone`，应为 `Asia/Phnom_Penh`；不要输出全部系统属性。
2. 检查本机 `http://127.0.0.1:7990/status` 与公网 `https://code.cambodianexpress.com/status`、登录页。
3. 检查 Git SSH 7999 端口的协议响应；需要时再以已授权账号对已有仓库做只读拉取验证。
4. 网页时间显示还需结合页面格式及 Git 提交自带时区判断，不将 HTTP `Date` 头的 GMT 视为应用时区未生效。

依据：[Atlassian 时区设置说明](https://support.atlassian.com/bitbucket-data-center/kb/timestamp-incorrect-in-bitbucket-server/)。此次是单服务配置变更，现有 Runbook 足以复用，未新增 Skill 或独立自动化脚本。
