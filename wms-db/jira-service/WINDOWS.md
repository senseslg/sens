# Windows 本机调用 Jira 服务

适用本机：`D:\sens_apps\sens\wms-db\jira-service`，2026-11-19 验证。
本文件只补充 Windows 步骤；原 macOS 启动、接口规范继续见 [RUNBOOK.md](RUNBOOK.md)。

## 启动（PowerShell）

```powershell
Set-Location D:\sens_apps\sens\wms-db\jira-service
$env:PYTHONIOENCODING = 'utf-8'
python -m pip install -r requirements.txt
# 已有配置不要覆盖；只有首次使用且没有配置时运行：python setup_local.py
python run.py
```

服务仅监听 `127.0.0.1:8765`。保持启动终端，另开终端调用；停止用 Ctrl+C。
无需管理员启动；若配置 ACL 拒绝访问，使用该文件已授权的本机用户，不扩大权限绕过检查。
配置默认为脚本目录下 `.local/config.json`，不依赖当前目录，保存现有 Jira 凭据和本地服务密钥。
不同设备配置可用 `$env:JIRA_SERVICE_CONFIG='C:\私有目录\config.json'` 指定独立文件；不要把凭据复制进版本库。

Windows 用 NTFS ACL 检查，允许所有者/当前用户、SYSTEM、Administrators 及 OWNER RIGHTS 读取，拒绝其它读取主体。
已有 ACL 不自动改写，新建配置由初始化脚本设置私有 ACL。macOS/Linux 仍检查配置 600、目录 700。
配置支持 UTF-8 及 BOM；`private_config.py` 是启动和导出的共用入口。
Windows PowerShell 5.1 检查进程使用系统模块路径，避免继承 PowerShell 7 的 PSModulePath 后 Get-Acl 加载失败。
`tzdata` 仅在 Windows 安装，供金边等 IANA 时区报表使用。

## 只读认证与查询

另开 PowerShell 并进入相同目录。脚本不打印配置或请求头：

```powershell
@'
import json, urllib.request
from private_config import load_private_config
key = load_private_config()['JIRA_SERVICE_API_KEY']
def call(path, body=None, idem=None):
    headers = {'X-API-Key': key, 'Content-Type': 'application/json'}
    if idem:
        headers['Idempotency-Key'] = idem
    req = urllib.request.Request('http://127.0.0.1:8765' + path,
        data=None if body is None else json.dumps(body).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)
print(call('/health'))
print(call('/projects'))
result = call('/requirements/query', {
    'jql': 'key = CCSL-2859', 'limit': 1, 'fields': ['summary', 'status', 'assignee']})
for issue in result['issues']:
    fields = issue['fields']
    print(issue['key'], fields['summary'], fields['status']['name'],
          (fields.get('assignee') or {}).get('name'))
'@ | python -
```

`/health` 只说明本地配置齐备，`/projects` 或查询成功才证明 Jira 真实连通。
不读取浏览器 Cookie，不打印密码、密钥、Authorization，不把完整业务响应或客户明细放入 Git。
网络失败不关闭 TLS 校验，不改用 HTTP 访问 Jira。

## 创建任务

先查重，再读 `GET /projects/CCSL/metadata?issue_type_id=10300` 确认类型、必填字段和模块 ID。
2026-11-19 核对 CCSL 任务类型 10300、后端 java 模块 11505、reporter 必填；后续以实时元数据为准。
复用上面脚本的 `call` 函数，在同一脚本中加入以下内容；没有授权时只预检查：

```python
body = {
    'project': 'CCSL', 'issue_type_id': '10300',
    'summary': '替换为实际标题', 'description': '替换为实际说明与验收条件',
    'assignee': 'sens',
    'extra_fields': {'reporter': {'name': 'sens'}, 'components': [{'id': '11505'}]},
    'dry_run': True,
}
preview = call('/requirements', body)
assert preview['submitted'] is False
# 获得本次建单授权后才执行以下两行。新任务用新键，同次重试保留键和正文。
# body['dry_run'] = False
# created = call('/requirements', body, idem='替换为该逻辑请求的唯一键')
```

成功后保存任务号，用 `/requirements/query` 读回核对标题、经办人、模块和状态。
超时/unknown 不得换键重发，先查询 Jira；已有任务号不得重复创建。
拿到任务号后再开关联分支，分支和提交信息带任务号。
关闭/不做按 Runbook 先读取工作流并 dry_run，需用户授权具体任务与原因。

## 导出与验证

```powershell
python export_report.py --month 2026-09
python -m unittest discover -s tests -v
```

导出默认当前用户 `~/Downloads`，Windows 为 `C:\Users\<用户>\Downloads`；
可用 `--output` 指定新文件，拒绝覆盖已有文件。
macOS 原默认 `/Users/lingang/Downloads` 及原调用步骤保留，未替换为 Windows 路径。

验证：Windows 服务启动、真实 sens 认证、CCSL 创建预检查、幂等创建 CCSL-2859 并读回经办人 sens 均通过。
23 项配置/导出/服务隔离测试通过，测试不访问真实 Jira。未改写现有凭据或 ACL，未部署到共享服务器。
