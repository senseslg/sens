# bitbucket-service

通过 REST API **只读**查询公司 Bitbucket（`https://code.cambodianexpress.com`，4.0.2，部署在 wms-db）。脚本只发 GET 请求，不创建、合并、删除或改权限。

## 当前状态

- 2026-11-28 建立。不登录也能访问的接口已经通了；登录后的接口要等用户填好密码才能验证。
- 账号：`sens`（用户决定）。sens 是系统管理员，所以能用管理员接口（`users`、`groups`），脚本本身仍然只读。

## 凭据

- Bitbucket 4.0.2 **没有个人访问令牌**，只能用账号加密码。
- 凭据放在 `.local/config.json`：Git 不跟踪，权限 600，用 `init` 生成。
- 密码由用户本人填写，不写进文档，也不贴到聊天里。
- 也可以用环境变量 `BITBUCKET_USERNAME` / `BITBUCKET_PASSWORD` 提供。
- 密码连续输错几次会触发验证码，脚本接口也会跟着失败。这时先用浏览器登录一次解除。

## 用法（macOS）

```bash
cd ~/sens/wms-db/bitbucket-service/scripts
python3 bitbucket_api.py init                     # 生成 .local/config.json，再手动填密码
python3 bitbucket_api.py check                    # 连通性与认证
python3 bitbucket_api.py projects
python3 bitbucket_api.py repos --project CCSL
python3 bitbucket_api.py branches --repo CCSL/<仓库> --filter qa
python3 bitbucket_api.py commits  --repo CCSL/<仓库> --branch qa -n 10
python3 bitbucket_api.py contains --repo CCSL/<仓库> --commit <提交号>   # 这个提交在哪些分支上
python3 bitbucket_api.py prs      --repo CCSL/<仓库> --state MERGED
python3 bitbucket_api.py users                    # 启用账号；--all 包含停用账号
python3 bitbucket_api.py groups
python3 bitbucket_api.py perms    --project CCSL [--repo <仓库>]
python3 bitbucket_api.py whitelist --allow sens,BRIAN,ceck,daniel.zhou,huzw,longmh,milf,yuth,jenkins
```

- 每个子命令都可以加 `--json`。
- 退出码：0 成功；1 请求失败，或白名单检查发现多余账号；2 参数或配置错误。
- 只用 Python 标准库，始终校验 HTTPS 证书：本机 Python 没有 CA 证书时，依次改用 certifi、`/etc/ssl/cert.pem`。

## 边界

- 写操作（创建或合并 PR、改权限、删分支）不在本脚本里。真要做时另外加，默认只预览，并经用户确认。
- 用户来自 Jira：要停用账号，在 Jira 里操作；目录同步只能在网页上点，见 [RUNBOOK：账号停用](../RUNBOOK.md#jira--bitbucket-账号停用)。
- 数据库只读核对，见 [账号清理记录](../BITBUCKET_USER_CLEANUP_2026-11-28.md)。
