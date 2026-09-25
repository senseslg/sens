#!/usr/bin/env python3
"""
CCSL 夜间定时任务健康检查（只读）

检查生产/UAT 每天凌晨的定时任务执行情况，全部通过 SSH + 日志只读取证：
  1. 自动集包   OrderJob.orderPackaging    cron 0 0 1 * * ?  (01:00)
       分支A OrderManager.autoCollectionPackages    (ship_type=2 集包 + status=1 拆包/到齐)
       分支B ParcelAutoCollectionManager (1688 自动集包)
       分支C EndCusAutoCollectionManager (子客户自动集包)
  2. 订单转运+TMS推送 OrderJob.orderTransport cron 0 0 2,3 * * ? (02:00/03:00)
       order_list.status 6 -> 7(成功)/99(失败)，推送 https://tms.cambodianexpress.com/api/public/v3/order/body-booking
  3. 失败单重推 OrderJob.resendFailToTms cron 0 0 13 * * ? (13:00)  status=99 -> 重推

用法示例：
  python3 check_scheduled_jobs.py                       # 生产，默认最近一个完整凌晨(今天或昨天)
  python3 check_scheduled_jobs.py --date 2026-09-03     # 指定服务器本地日期
  python3 check_scheduled_jobs.py --compare             # 同时扫描前一天作为基线对比
  python3 check_scheduled_jobs.py --env uat             # 检查 UAT
  python3 check_scheduled_jobs.py --no-probe            # 跳过 TMS 连通性探测

SSH 配置解析顺序（多设备可移植）：
  1) 环境变量 CCSL_SSH_CONFIG 指向的 ssh_config；
  2) 脚本同目录下的 ssh_config；
  3) 原运维目录 /Users/lingang/sens/sens-server/new-ccsl/ssh_config（本机兜底）。

只读安全边界：不写库、不部署、不重启；不打印凭据；远端日志大文件用单次
awk 全文件扫描(nohup+轮询)避免长 SSH 会话被掐断。
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SSH_HOST = "ccsl-new"


def _find_ssh_config():
    cand = os.environ.get("CCSL_SSH_CONFIG")
    if cand:
        return Path(cand)
    here = Path(__file__).resolve().parent
    for p in (here / "ssh_config", here.parent.parent / "ssh_config",
              Path("/Users/lingang/sens/sens-server/new-ccsl/ssh_config")):
        if p.is_file():
            return p
    return None


SSH_CONFIG = _find_ssh_config()

ENVS = {
    "prod": {
        "label": "生产",
        "log": "/home/engineer/prod/backend/ccsl-prod.log",
        "port": 8080,
        "tms": ["https://tms.cambodianexpress.com/", "https://otwms.cambodianexpress.com/"],
    },
    "uat": {
        "label": "UAT",
        "log": "/home/engineer/uat/backend/ccsl-uat.log",
        "port": 8081,
        "tms": ["https://tms-uat.cambodianexpress.com/", "https://otwms-uat.cambodianexpress.com/"],
    },
}

# 关注的凌晨小时（集包 01、转运 02/03、重推 13）
WATCH_HOURS = "00,01,02,03,04,13,14"

AWK_TEMPLATE = r"""
function cap(t, line) { captured[t, ++n[t]] = line }
BEGIN { want = D }
/^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}/ {
  d = substr($0, 1, 10)
  key = d " " substr($0, 12, 5)
}
key ~ "^" want " " {
  # ---- 每分钟计数（SQL 为无时间戳裸行，归到最近一条带时间戳日志）----
  if (/UPDATE order_list SET status = 7/)       cnt[key, "tms_ok"]++
  if (/UPDATE order_list SET status = 99/)      cnt[key, "tms_fail"]++
  if (/INSERT INTO order_list \(/)              cnt[key, "new_order"]++
  if (/UPDATE parcel_list SET shipment_code = '/) cnt[key, "assign_sc"]++
  if (/UPDATE parcel_list SET shipment_code = NULL/) cnt[key, "clear_sc"]++
  if (/UPDATE parcel_list SET shipment_code = null/) cnt[key, "clear_sc"]++
  if (/UPDATE order_list SET status = 3/)       cnt[key, "status3"]++
  # ---- 失败/状态标记（必须 ERROR 级，避免命中巨型 INFO 字典行）----
  if (/ ERROR /) {
    if (/自动集包job执行失败/)                cap("auto_fail_a", $0)
    if (/大件自动集包job执行失败/)            cap("auto_fail_b", $0)
    if (/子客户自动集包job执行失败/)          cap("auto_fail_c", $0)
    if (/推送TMS失败/)                        { cnt[key, "tms_push_fail"]++; cap("tms_push_fail", $0) }
    if (/创建集包订单失败/)                   cap("order_fail", $0)
    if (/Unexpected error occurred in scheduled task/) cap("sched_uncaught", $0)
    if (/OrderManager|OrderJob|ParcelAutoCollectionManager|EndCusAutoCollectionManager/) cnt[key, "job_error"]++
  }
  # ---- 分支 B/C 的开始/完成标记 ----
  if (/ParcelAutoCollectionManager/ && /开始执行1688自动集包/) cap("flow_b_start", $0)
  if (/ParcelAutoCollectionManager/ && /1688自动集包执行完成/) cap("flow_b_done", $0)
  if (/EndCusAutoCollectionManager/ && /开始执行子客户自动集包/) cap("flow_c_start", $0)
  if (/EndCusAutoCollectionManager/ && /子客户自动集包执行完成/) cap("flow_c_done", $0)
}
END {
  for (k in cnt) { split(k, p, SUBSEP); print "cnt|" p[1] "|" p[2] "|" cnt[k] }
  for (t in n) for (i = 1; i <= n[t]; i++) print "cap|" t "|" captured[t, i]
}
"""


def ssh_base(extra_opts=None):
    if SSH_CONFIG is None:
        raise RuntimeError(
            "未找到 ssh_config：请设置环境变量 CCSL_SSH_CONFIG 指向 ssh_config，"
            "或把 ssh_config 放到脚本同目录（多设备部署见 tools/ccsl-nightly-job-check/README.md）")
    opts = ["-F", str(SSH_CONFIG), "-o", "ConnectTimeout=30",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=60",
            "-o", "TCPKeepAlive=yes"]
    return ["ssh"] + opts + [SSH_HOST]


def run_remote(cmd, timeout=120):
    """执行单条远端只读命令；返回 (returncode, stdout, stderr)。"""
    proc = subprocess.run(ssh_base() + [cmd], capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def remote_cmd_ok(cmd, timeout=120):
    rc, out, err = run_remote(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"远端命令失败 rc={rc}\ncmd={cmd}\nerr={err[:800]}")
    return out


def remote_cmd_retry(cmd, tries=8, timeout=90):
    """ssh 瞬时断开（rc=255）等场景自动重试；用于轮询/取数这类短命令。"""
    last = None
    for attempt in range(tries):
        try:
            return remote_cmd_ok(cmd, timeout=timeout)
        except Exception as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(8)
    raise last


def upload_remote(remote_path, text, tries=6):
    """通过 ssh stdin 上传小文件到远端，带重试。"""
    last = None
    for attempt in range(tries):
        try:
            proc = subprocess.run(ssh_base() + ["cat > " + remote_path],
                                  input=text, text=True, capture_output=True, timeout=90)
            if proc.returncode != 0:
                raise RuntimeError(f"上传失败 rc={proc.returncode} err={proc.stderr[:300]}")
            return
        except Exception as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(8)
    raise last


def server_date():
    return remote_cmd_ok("date +%F").strip()


def server_time_hour():
    return int(remote_cmd_ok("date +%H").strip())


def log_span(log_path):
    """返回日志文件覆盖的时间范围（服务器本地）或 None。"""
    try:
        start = remote_cmd_ok(
            f"grep -a -m1 -E '^20[0-9]{{2}}-[0-9]{{2}}-[0-9]{{2}} [0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}' {log_path}"
        ).strip()[:19]
        end = remote_cmd_ok(
            f"tail -n 2000 {log_path} | grep -a -E '^20[0-9]{{2}}-[0-9]{{2}}-[0-9]{{2}} [0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}' | tail -1"
        ).strip()[:19]
        return start, end
    except Exception:
        return None


def scan_log(log_path, date):
    """
    单次 awk 全文件扫描（远端 nohup + 轮询，避免长 SSH 会话被掐断）。
    返回 (cnt_rows, cap_rows)：cnt 每行 "2026-09-03 02:03|tms_ok|12"，cap 每行 "auto_fail_a|完整日志行"。
    """
    remote_tmp = "/tmp/ccsl_job_check_%s" % os.getpid()
    awk_file = remote_tmp + ".awk"
    out_file = remote_tmp + ".out"

    try:
        upload_remote(awk_file, AWK_TEMPLATE)
        # 注意：nohup 后台启动后 ssh 会滞留约 60s 才返回（远端 shell 等待行为），
        # 因此启动命令超时放宽到 180s，pid 会先打印出来。
        start_cmd = (f"cd /tmp && nohup nice -n 10 awk -v D='{date}' -f {awk_file} {log_path} "
                     f"> {out_file} 2>&1 < /dev/null & echo $!")
        rc, out, err = run_remote(start_cmd, timeout=180)
        if rc != 0:
            raise RuntimeError("无法启动远端 awk 扫描: " + (err or out)[:400])
        pid = out.strip().splitlines()[-1].strip()

        deadline = time.time() + 1500  # 25 分钟上限
        while time.time() < deadline:
            time.sleep(25)
            alive = remote_cmd_retry(
                f"kill -0 {pid} 2>/dev/null && echo yes || echo no").strip()
            if alive != "yes":
                break
        else:
            run_remote(f"kill {pid} 2>/dev/null")
            raise RuntimeError("远端 awk 扫描超时（>25min）")

        out_text = remote_cmd_retry(f"cat {out_file}", tries=12, timeout=120)
        cnt_rows, cap_rows = [], []
        for line in out_text.splitlines():
            if line.startswith("cnt|"):
                _, minute, kind, n = line.split("|", 3)
                cnt_rows.append((minute[11:16], kind, int(n)))  # "2026-09-03 01:00" -> "01:00"
            elif line.startswith("cap|"):
                _, kind, text = line.split("|", 2)
                cap_rows.append((kind, text))
        return cnt_rows, cap_rows
    finally:
        try:
            run_remote(f"kill $(pgrep -f '{os.path.basename(awk_file)}' 2>/dev/null) 2>/dev/null; "
                       f"rm -f {awk_file} {out_file}", timeout=30)
        except Exception:
            pass


def probe_tms(env):
    if not ENVS[env].get("tms"):
        return []
    results = []
    for host in ENVS[env]["tms"]:
        out = remote_cmd_ok(
            f"curl -s -m 8 -o /dev/null -w '%{{http_code}} %{{time_connect}} %{{time_total}}' {host}"
        ).strip()
        results.append((host, out))
    return results


def summarize(env, date, rows, caps, baseline=None, probe=True):
    """rows: (minute "HH:MM", kind, n)；caps: (kind, line)。输出可读报告。"""
    def bucket_total(hh_start, hh_end, kind):
        total = 0
        for minute, k, n in rows:
            if k == kind and hh_start <= minute[:2] <= hh_end:
                total += n
        return total

    def window_minutes(hh_start, hh_end, kinds):
        got = set()
        for minute, k, n in rows:
            if k in kinds and hh_start <= minute[:2] <= hh_end:
                got.add(minute)
        return sorted(got)

    def caps_of(kind):
        return [t for k, t in caps if k == kind]

    def bl(metric):
        return baseline.get(metric) if baseline else None

    L = []
    L.append("=" * 78)
    L.append(f"CCSL 夜间定时任务检查  |  环境:{ENVS[env]['label']}({env})  |  日期:{date}（服务器本地时区）")
    L.append("=" * 78)

    # ---------- 自动集包 01:00 ----------
    L.append("\n[1] 自动集包  OrderJob.orderPackaging  cron 0 0 1 * * ?（01:00）")
    fa = caps_of("auto_fail_a")
    fb = caps_of("auto_fail_b")
    fc = caps_of("auto_fail_c")
    ofail = caps_of("order_fail")
    sched = caps_of("sched_uncaught")
    b_start = caps_of("flow_b_start")
    b_done = caps_of("flow_b_done")
    c_start = caps_of("flow_c_start")
    c_done = caps_of("flow_c_done")

    n_new = bucket_total("00", "01", "new_order")
    n_assign = bucket_total("00", "01", "assign_sc")
    n_status3 = bucket_total("00", "01", "status3")
    n_clear = bucket_total("00", "01", "clear_sc")

    if fa:
        verdict = "FAIL ❌"
        reason = f"分支A(主流程 OrderManager.autoCollectionPackages，含 ship_type=2 集包)中断，见下"
    elif fb or fc:
        verdict = "FAIL ❌"
        reason = f"分支B/C 失败：{fb[0][:120] if fb else ''} {fc[0][:120] if fc else ''}"
    else:
        if n_new == 0 and n_assign == 0 and n_status3 == 0:
            verdict = "INFO（未见集包产出，可能当日无待集包包裹，或任务未执行）"
        else:
            verdict = "OK ✅"
        marks = []
        marks.append("B 完成 " + b_done[0][11:19] if b_done else "B 未见完成标记（可能当日无 1688 集包数据）")
        marks.append("C 完成 " + c_done[0][11:19] if c_done else "C 未见完成标记")
        reason = "；".join(marks)

    L.append(f"  判定: {verdict}")
    L.append(f"  说明: {reason}")
    for t in (fa + fb + fc):
        L.append(f"     · {t[:220]}")
    L.append(f"  集包产出(00:00-01:59) 新建订单={n_new}  分配运单号={n_assign}  置status=3={n_status3}  拆包清空={n_clear}")
    if baseline:
        L.append(f"  对比前一天: 新建订单={bl('new_order')}  分配运单号={bl('assign_sc')}")
    m = window_minutes("00", "01", {"new_order", "assign_sc", "status3"})
    if m:
        L.append(f"  产出分钟: {m[0]} ~ {m[-1]}（共 {len(m)} 分钟有产出）")
        # 分时证据（00:50-01:20 细节）
        by_min = {}
        for mm, k2, n in rows:
            if "00:50" <= mm <= "01:20":
                by_min.setdefault(mm, {})[k2] = n
        detail = [f"{mm}[" + " ".join(f"{k2}:{v}" for k2, v in sorted(d.items()) if v > 0) + "]"
                  for mm, d in sorted(by_min.items())]
        L.append("  分时(00:50-01:20): " + "  ".join(detail[:16]))
    L.append(f"  分支B/C标记: 开始={[x[11:19] for x in b_start]} 完成={[x[11:19] for x in b_done]} | 子客户 开始={[x[11:19] for x in c_start]} 完成={[x[11:19] for x in c_done]}")

    # ---------- 转运 + TMS 02:00/03:00 ----------
    L.append("\n[2] 订单转运+TMS推送  OrderJob.orderTransport  cron 0 0 2,3 * * ?（02:00/03:00）")
    for hh, tag in (("02", "02:00 主批次"), ("03", "03:00 补批次")):
        ok = bucket_total(hh, hh, "tms_ok")
        fail = bucket_total(hh, hh, "tms_push_fail")
        up99 = bucket_total(hh, hh, "tms_fail")
        if ok == 0 and fail == 0:
            v = "WARN（该批次无任何产出/失败记录，可能无待转运订单）"
        else:
            v = f"status6→7 成功 {ok} 单" + (f"，推送失败 {fail} 单(status→99)" if fail else "")
        L.append(f"  {tag}: {v}")
        if baseline:
            L.append(f"          对比前一天: 成功 {bl('tms_ok_' + hh)} 失败 {bl('tms_fail_' + hh)}")
    # 分时证据（02/03 点 成功/失败 每分钟）
    ev = {}
    for mm, k2, n in rows:
        if k2 in ("tms_ok", "tms_fail") and mm[:2] in ("02", "03"):
            ev.setdefault(mm, {})[k2] = n
    if ev:
        parts = [f"{mm}[ok:{d.get('tms_ok', 0)} fail:{d.get('tms_fail', 0)}]"
                 for mm, d in sorted(ev.items())]
        L.append("  分时(02:00-03:59): " + "  ".join(parts)[:700])
    fails = caps_of("tms_push_fail")
    if fails:
        L.append(f"  推送失败明细（最多显示 8 条）:")
        for t in fails[:8]:
            L.append(f"     · {t[:200]}")
        if len(fails) > 8:
            L.append(f"     … 共 {len(fails)} 条失败，其余请查日志")

    # ---------- 13:00 重推 ----------
    r_ok = bucket_total("13", "13", "tms_ok")
    r_fail = bucket_total("13", "13", "tms_push_fail")
    L.append("\n[3] 失败单重推  OrderJob.resendFailToTms  cron 0 0 13 * * ?（13:00）")
    if r_ok == 0 and r_fail == 0:
        L.append("  13:00 窗口暂无记录（若查询日期的 13:00 尚未到来或无可重推单则正常）")
    else:
        L.append(f"  重推成功 {r_ok} 单，失败 {r_fail} 单")

    # ---------- 其它调度/订单异常（同日志日期，非上述主任务） ----------
    others = ofail + sched
    L.append("\n[4] 其它调度/订单异常（同日志日期，非上述主任务，供参考）")
    if others:
        for t in others[:10]:
            L.append(f"     · {t[:200]}")
        if len(others) > 10:
            L.append(f"     … 共 {len(others)} 条")
    else:
        L.append("  无")

    # ---------- TMS 连通性 ----------
    probes = probe_tms(env) if probe else []
    if probes:
        L.append("\n[5] TMS/OTWMS 连通性（当前探测，只读）")
        for host, res in probes:
            L.append(f"  {host} -> {res or '无响应/超时'}")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="CCSL 夜间定时任务健康检查（只读）")
    ap.add_argument("--date", help="服务器本地日期 YYYY-MM-DD（默认最近一个完整凌晨）")
    ap.add_argument("--env", choices=["prod", "uat"], default="prod")
    ap.add_argument("--compare", action="store_true", help="同时扫描前一天作为基线对比")
    ap.add_argument("--no-probe", action="store_true", help="跳过 TMS 连通性探测")
    args = ap.parse_args()

    env = ENVS[args.env]
    log_path = env["log"]

    # 连通性 + 日志范围
    try:
        today = server_date()
    except Exception as e:
        print(f"无法连接生产服务器（{e}）；请检查 ssh_config（见文件头「SSH 配置解析顺序」）与网络。", file=sys.stderr)
        return 2
    if args.date:
        date = args.date
    else:
        hour = server_time_hour()
        # 当天 04:00 前，最近完整凌晨仍属于前一天
        date = (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat() if hour < 4 else today

    span = log_span(log_path)
    if span:
        print(f"日志覆盖范围: {span[0]} ~ {span[1]}（{env['label']} {log_path}）", file=sys.stderr)
        if not (span[0][:10] <= date <= span[1][:10]):
            print(f"⚠️ 请求日期 {date} 不在日志覆盖范围内，结果可能不完整", file=sys.stderr)

    def scan(date):
        print(f"扫描 {date} …（大日志单次全扫约 2-5 分钟）", file=sys.stderr)
        return scan_log(log_path, date)

    rows, caps = scan(date)
    baseline = None
    if args.compare:
        prev = (datetime.date.fromisoformat(date) - datetime.timedelta(days=1)).isoformat()
        try:
            brows, _ = scan(prev)
            baseline = {}
            for minute, kind, n in brows:
                baseline[kind] = baseline.get(kind, 0) + n
            baseline["new_order"] = sum(n for m, k, n in brows if k == "new_order" and m[:2] <= "01")
            baseline["assign_sc"] = sum(n for m, k, n in brows if k == "assign_sc" and m[:2] <= "01")
            for hh in ("02", "03"):
                baseline["tms_ok_" + hh] = sum(n for m, k, n in brows if k == "tms_ok" and m[:2] == hh)
                baseline["tms_fail_" + hh] = sum(n for m, k, n in brows if k == "tms_push_fail" and m[:2] == hh)
        except Exception as e:
            print(f"基线扫描失败（忽略）: {e}", file=sys.stderr)

    print(summarize(args.env, date, rows, caps, baseline, probe=not args.no_probe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
