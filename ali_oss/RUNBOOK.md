# RUNBOOK

本机验证过的命令。不写凭证，只写路径。

## OSS API 脚本 `scripts/oss.py`

纯 Python 标准库（3.11 已测），OSS V1 签名，macOS 自动加载系统 CA。输出 JSON；退出码 `0` 成功 · `1` 本地错误 · `2` OSS 返回错误 · `3` 写操作被拦截（dry-run/未确认）。

### 凭据

1. 已建专用 RAM 用户 `ali-oss-ops`（仅 OpenAPI，只读 `AliyunOSSReadOnlyAccess`）。需要写时再按桶追加自定义策略；轮换时新建 AccessKey 后禁用旧的。
2. 写入 `ali_oss/.local/credentials.json`，权限 0600（目录 0700），已 gitignore：
   ```json
   {"access_key_id": "REPLACE_WITH_REAL_VALUE", "access_key_secret": "REPLACE_WITH_REAL_VALUE", "region": "cn-hongkong"}
   ```
   也可用 `--credentials <路径>` 或环境变量 `ALI_OSS_CREDENTIALS`。可加 `security_token` 使用 STS。
   控制台导出的 AccessKey CSV 可直接导入（不显示 Secret）：`python3 scripts/oss.py import-csv <csv> --delete-csv`。
3. 不借用 `power-application-user`（证书/CDN 专用）。

### 命令

```bash
cd /Users/lingang/sens/ali_oss
python3 scripts/oss.py check                         # 只校验本地凭据文件，不联网
python3 scripts/oss.py buckets                       # Bucket 列表
python3 scripts/oss.py info uat-ccsl                 # 基本信息/ACL/版本控制
python3 scripts/oss.py stat uat-ccsl                 # 容量与对象数
python3 scripts/oss.py config uat-ccsl referer       # acl|referer|cors|lifecycle|logging|versioning
python3 scripts/oss.py ls uat-ccsl --prefix img/ --max-keys 20 --delimiter /
python3 scripts/oss.py head uat-ccsl img/a.png
python3 scripts/oss.py download uat-ccsl img/a.png /tmp/a.png
python3 scripts/oss.py sign-url uat-ccsl img/a.png --expires 600   # 本地计算，不联网
# 写操作：默认 dry-run；--apply 才执行；生产桶还需 --confirm-bucket <同名>
python3 scripts/oss.py upload uat-ccsl test/x.txt ./x.txt [--acl private] [--apply]
python3 scripts/oss.py delete uat-ccsl test/x.txt [--apply]               # 单个对象，不可恢复
python3 scripts/oss.py put-bucket-acl uat-ccsl private [--apply]
```

受保护桶（`PROTECTED_BUCKETS`）：`cambodianexpress-ccsl`、`ccsl-mallgogo`、`ceccsl`、`uat-mallgogo`。

### Python 调用

```python
import sys; sys.path.insert(0, '/Users/lingang/sens/ali_oss/scripts')
from oss import OssClient, OssError
c = OssClient.from_file()                 # 或 OssClient.from_file('/path/creds.json')
c.list_objects('uat-ccsl', prefix='img/', max_keys=20)
c.presign_url('uat-ccsl', 'img/a.png', expires=600)
```

库方法不带 dry-run 保护；其他业务调用写方法前须自行取得授权。

### 验证

```bash
python3 -m unittest discover -s tests      # 10 项离线测试，2026-11-27 通过
```

真实 API（2026-11-27，`ali-oss-ops` 只读）：`check`、`buckets`（7 个桶与控制台一致）、`info`、`stat`、`config referer/logging`、`ls` 均成功。写命令未真实执行（账号只读，会返回 `AccessDenied`）。签名错误返回 `SignatureDoesNotMatch`。

## Devices

### macOS（本机）

- 采集日期：2026-11-27 · Python 3.11.1 · 未安装 `oss2`，脚本不依赖。
