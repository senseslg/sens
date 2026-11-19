"""Private local configuration: POSIX mode checks or Windows ACL checks."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def config_path():
    return Path(os.environ.get("JIRA_SERVICE_CONFIG", ROOT / ".local" / "config.json"))


def windows_acl(path):
    # Pass the path as environment data, never interpolate it into PowerShell code.
    env = dict(os.environ, JIRA_CONFIG_ACL_PATH=str(path.resolve()))
    # PowerShell 7 can leave an incompatible PSModulePath for Windows PowerShell 5.1.
    env["PSModulePath"] = str(Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "Modules")
    script = "$ErrorActionPreference='Stop'; $a=Get-Acl -LiteralPath $env:JIRA_CONFIG_ACL_PATH; " + \
        "@{owner=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value; " + \
        "current=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; " + \
        "protected=$a.AreAccessRulesProtected; rules=@($a.GetAccessRules($true,$true," + \
        "[System.Security.Principal.SecurityIdentifier]) | ForEach-Object { " + \
        "@{sid=$_.IdentityReference.Value; allow=($_.AccessControlType -eq 'Allow'); " + \
        "rights=[int64]$_.FileSystemRights}})} | ConvertTo-Json -Depth 4 -Compress"
    try:
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                env=env, capture_output=True, check=True, text=True, encoding="utf-8")
        return json.loads(result.stdout.lstrip("\ufeff"))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise ValueError("无法检查Windows配置ACL，拒绝读取凭据") from error


def validate_windows_acl(acl):
    trusted = {acl["owner"], acl["current"], "S-1-5-18", "S-1-5-32-544", "S-1-3-4"}
    # ReadData/ListDirectory bit; fail closed for every other allow principal.
    if any(rule["allow"] and rule["rights"] & 1 and rule["sid"] not in trusted
           for rule in acl.get("rules", [])):
        raise ValueError("配置ACL允许其他用户读取，请限制为文件所有者、当前用户、SYSTEM及Administrators")


def assert_private_file(path):
    if os.name == "nt":
        validate_windows_acl(windows_acl(path))
    elif path.stat().st_mode & 0o077:
        raise ValueError("配置权限过宽，请执行chmod 600")


def protect_private_path(path):
    if os.name != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    acl = windows_acl(path)
    permission = "(OI)(CI)(F)" if path.is_dir() else "(F)"
    # Used only for newly created paths, never rewrite an existing user's ACL.
    grants = [f"*{sid}:{permission}" for sid in (acl["current"], "S-1-5-18", "S-1-5-32-544")]
    try:
        subprocess.run(["icacls.exe", str(path), "/inheritance:r", "/grant:r", *grants],
                       capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("无法设置私有Windows ACL") from error
    assert_private_file(path)


def load_private_config(path=None):
    path = Path(path) if path is not None else config_path()
    if not path.exists():
        return {}
    assert_private_file(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("配置必须为JSON对象")
    return data


def load_environment():
    config = load_private_config()
    for name in ("JIRA_BASE_URL", "JIRA_SERVICE_API_KEY", "JIRA_USERNAME", "JIRA_PASSWORD"):
        if config.get(name):
            os.environ.setdefault(name, config[name])
