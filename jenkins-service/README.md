# jenkins-service

公司 Jenkins 的位置、访问方式和只读查询脚本。核实日期：2026-11-19。

## 基础信息

| 项 | 值 |
|---|---|
| 网页 | `https://jenkins.cambodianexpress.com`（用户本人登录；agent 需要时经 Chrome 访问） |
| 所在主机 | GCP `wms-db`（项目 `cambodian-express`，区域 `asia-southeast1-a`），无公网 IP |
| 运行方式 | Docker 容器 `jenkins`，容器内 8080 → 宿主机 `127.0.0.1:8081`，Nginx 反代域名 |
| 数据卷 | 宿主机 `/home/daniel/containers/jenkins/jenkins`（容器内 `/var/jenkins_home`） |
| 同机服务 | Jira、Bitbucket、XXL-JOB、YApi 等，见 [wms-db](../wms-db/README.md) |

不在 CCSL 主应用服务器上：那台机器只接收 Jenkins 上传的产物并由 `deploy.sh` 启动。

## CCSL 任务

| 任务路径 | 用途 |
|---|---|
| `ccsl/uat/ccsl-backend-uat` | 后端 qa → UAT（`/home/engineer/uat/backend/ccsl-uat.jar`） |
| `ccsl/uat/ccsl-frontend-uat` | 管理后台前端 qa → UAT |
| `ccsl/uat/ccsl-webapp-uat` | webapp UAT |
| `ccsl/prod/ccsl-backend-prod` / `ccsl-frontend-prod` / `ccsl-webapp-prod` | 生产 |
| `ccsl/prod/i18n` | 国际化 |

其他文件夹：`APP`、`AppTranslation`、`mall`、`otwms`、`TMS`、`restart-tms`、`toucha`。

后端构建（Maven）会编译测试代码（`testCompile`），但跳过运行测试（`Tests are skipped`）：测试代码编译不过也会导致构建失败。

单个构建在数据卷中的位置：`jobs/ccsl/jobs/uat/jobs/ccsl-backend-uat/builds/<编号>/`，`build.xml` 含结果，`log` 为控制台输出。

## 只读查询

```bash
cd ~/sens/jenkins-service/scripts
python3 jenkins_builds.py jobs                                          # CCSL 任务列表
python3 jenkins_builds.py list --job ccsl/uat/ccsl-backend-uat -n 5     # 最近构建结果与时间
python3 jenkins_builds.py log  --job ccsl/uat/ccsl-backend-uat --build 2345   # 关键行
python3 jenkins_builds.py log  --job ccsl/uat/ccsl-backend-uat --build 2345 --tail 80
```

- 脚本经 `gcloud compute ssh wms-db --tunnel-through-iap` 登录，用 `sudo -n` 读文件；不调用 Jenkins API，不触发或取消构建。
- 关键行包括触发人、检出提交、提交说明、`[ERROR]`、`BUILD SUCCESS/FAILURE`、`Finished:`。
- 输出会去掉 Jenkins 注解（`ha://…`）和颜色码，含 password/token/secret 等字样的行替换为 `[已隐藏疑似敏感行]`。
- 列表中结果为 `RUNNING` 表示 `build.xml` 尚无结果（运行中或异常中止）。

## 排查部署是否生效

1. 用 `list` 看对应任务在合并之后有没有新构建、结果是什么。
2. 失败时用 `log` 看检出的提交和报错；成功时再用 CCSL 发版检查确认服务器产物时间。
3. 前后端是两个任务，需要分别确认。

## 边界

- 只读。构建、重启、改任务配置、清理数据卷都由用户在 Jenkins 页面操作，或经明确授权。
- 不读取或输出 `credentials.xml`、`secrets/`、任务 `config.xml` 中的凭据，不复制完整日志到文档。
- IAP 登录失败时停止排查原因，不要换参数反复重试。

## 记录

- 2026-11-19：后端 UAT #2345 失败，原因是 qa 上 CCSL-2859 测试类 `ParcelAutoCollectionDatabaseUatTest` 中 `assertEquals(int, Integer)` 编译歧义（`testCompile` 阶段），不是 Git 合并冲突；前端 UAT 当天 10:02 后无新构建。
