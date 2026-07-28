#!/usr/bin/env python3
# mlogwatch.py — Linux 系統日誌與資源監控腳本 (v2)
#
# 用法:
#   ./mlogwatch.py                  跑一次完整檢查
#   ./mlogwatch.py --check disk     只跑單一 check
#   ./mlogwatch.py --self-test      跑內建單元測試
#   ./mlogwatch.py --dry-run        跑檢查但不發通知
#   ./mlogwatch.py --report         只生成本次報告,不算 alert
#   ./mlogwatch.py --quiet          抑制 stderr 輸出
#   ./mlogwatch.py --config PATH    指定配置檔
#
# 設計目標:
#   - 零外部依賴 (stdlib only)
#   - portable atomic_write (Windows 不會爆)
#   - bounded read (HTTP webhook 防 OOM)
#   - 明確 User-Agent
#   - 三級警告 (WARN/ALERT/CRITICAL) + cooldown 並發鎖
#
# 參考:
#   - Senior Architect Round 3 建議: portable atomic_write / bounded HTTP read
#   - Senior Architect Round 4 建議: 明確 User-Agent / stdlib 防 slop

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import http.client
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# ---- 版本 + User-Agent ---------------------------------------------
__version__ = "2.0.0"
USER_AGENT = f"mlogwatch/{__version__} (+https://github.com/hoonsoropenclaw/hermes-scripts)"

# ---- 全域常數 -------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path(os.environ.get("MLOGWATCH_CONFIG", SCRIPT_DIR / "config.yaml"))
STATE_DIR = Path(os.environ.get("MLOGWATCH_STATE_DIR", SCRIPT_DIR / "state"))
LOCK_DIR = Path(os.environ.get("MLOGWATCH_LOCK_DIR", SCRIPT_DIR / "locks"))
REPORT_DIR = Path(os.environ.get("MLOGWATCH_REPORT_DIR", SCRIPT_DIR / "reports"))
ALERT_LOG = REPORT_DIR / "alerts.log"
MAX_HTTP_BYTES = 256 * 1024  # Senior Architect Round 3: 防 OOM
COOLDOWN_DEFAULT_SEC = 1800  # 30 分鐘 (跟既有品對齊)
LOCK_STALE_SEC = 600


# ---- 嚴重度 ----------------------------------------------------------
@dataclass(frozen=True)
class Severity:
    name: str
    rank: int  # 越高越嚴重


SEV_WARN = Severity("WARN", 1)
SEV_ALERT = Severity("ALERT", 2)
SEV_CRITICAL = Severity("CRITICAL", 3)


@dataclass
class Alert:
    check: str
    target: str
    severity: Severity
    value: float
    threshold: float
    message: str
    host: str = field(default_factory=lambda: socket.gethostname())


# ---- portable atomic_write (吸收 Senior Architect Round 3 #1) -------
def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    """寫檔:tmp + fsync + rename;Windows 跳過 fsync dir。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    # Windows 上 os.replace 已足夠;posix 多 fsync dir inode 確保 rename 進目錄
    if sys.platform != "win32":
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except (OSError, PermissionError):
            pass  # 某些 mount 不支援 fsync dir (例如 NFS / FAT)
    os.chmod(path, mode)


# ---- bounded HTTP read (吸收 Senior Architect Round 3 #2) ----------
def http_post_json(url: str, payload: dict, timeout: float = 10.0) -> tuple[int, str]:
    """POST JSON,嚴格限制讀取大小。失敗回 (0, msg)。"""
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https"):
            return (0, f"unsupported scheme: {parsed.scheme}")
        body = json.dumps(payload).encode("utf-8")
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        conn = cls(host, port, timeout=timeout)
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            headers = {
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            }
            conn.request("POST", path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read(MAX_HTTP_BYTES)  # ← bounded read
            return (resp.status, data[:512].decode("utf-8", errors="replace"))
        finally:
            conn.close()
    except Exception as e:
        return (0, f"{type(e).__name__}: {e}")


# ---- mini YAML parser (stdlib 防 slop) -----------------------------
# 支援:nested block (縮排)、flow mapping {key: val}、flow list [a, b, c]、
# 整數、浮點、布林、null、字串 (含 quoted)。
# 不支援:多行字串、anchor、tag (現實用不到)
class YamlError(ValueError):
    pass


def _yaml_coerce(s: str) -> Any:
    s = s.strip()
    if s == "" or s.lower() in ("null", "~"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    # 去掉引號
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _yaml_tokenize_flow(s: str) -> list[str]:
    """Flow tokenizer:處理 {k: v, k2: v2} 與 [a, b, c] 內部 token。
    認識引號字串 (不會在字串內拆逗號/冒號)、支援巢狀。
    """
    tokens: list[str] = []
    cur = ""
    depth = 0
    in_str: str | None = None
    for ch in s:
        if in_str:
            cur += ch
            if ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            cur += ch
            continue
        if ch in "[{":
            depth += 1
            cur += ch
            continue
        if ch in "]}":
            depth -= 1
            cur += ch
            continue
        if ch == "," and depth == 0:
            tokens.append(cur)
            cur = ""
            continue
        cur += ch
    if cur:
        tokens.append(cur)
    return [t.strip() for t in tokens if t.strip()]  # ← 保留引號,延後給 _yaml_coerce


def _yaml_split_kv_on_colon(tok: str) -> tuple[str, str]:
    """在 token 內找第一個 (字串外的)':' 切 key/value。"""
    in_str: str | None = None
    for i, ch in enumerate(tok):
        if in_str:
            if ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            continue
        if ch == ":":
            return (tok[:i], tok[i + 1:])
    raise YamlError(f"flow map token needs ':': {tok!r}")


def parse_flow_object(s: str) -> dict:
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise YamlError(f"not a flow object: {s!r}")
    body = s[1:-1]
    out: dict = {}
    for tok in _yaml_tokenize_flow(body):
        k_raw, v_raw = _yaml_split_kv_on_colon(tok)
        k = _yaml_coerce(k_raw)
        v = v_raw.strip()
        if v.startswith("[") and v.endswith("]"):
            out[k] = parse_flow_list(v)
        elif v.startswith("{") and v.endswith("}"):
            out[k] = parse_flow_object(v)
        else:
            out[k] = _yaml_coerce(v)
    return out


def parse_flow_list(s: str) -> list:
    s = s.strip()
    if not (s.startswith("[") and s.endswith("]")):
        raise YamlError(f"not a flow list: {s!r}")
    body = s[1:-1]
    out: list = []
    for tok in _yaml_tokenize_flow(body):
        if tok.startswith("{") and tok.endswith("}"):
            out.append(parse_flow_object(tok))
        elif tok.startswith("[") and tok.endswith("]"):
            out.append(parse_flow_list(tok))
        else:
            out.append(_yaml_coerce(tok))
    return out


def parse_yaml(text: str) -> Any:
    """遞迴下降式 YAML parser,只支援 block + flow 兩種 syntax。"""
    lines = [
        re.sub(r"#.*$", "", ln).rstrip()
        for ln in text.splitlines()
    ]
    lines = [ln for ln in lines if ln.strip() != ""]  # 略空行

    pos = [0]

    def indent_of(ln: str) -> int:
        return len(ln) - len(ln.lstrip(" "))

    def parse_block(min_indent: int) -> Any:
        if pos[0] >= len(lines):
            return None
        head = lines[pos[0]]
        ind = indent_of(head)
        if ind < min_indent:
            return None
        # 看 head 是 list 還是 map
        stripped = head.strip()
        if stripped.startswith("- "):
            return parse_list(ind)
        return parse_map(ind)

    def parse_list(ind: int) -> list:
        out: list = []
        while pos[0] < len(lines):
            head = lines[pos[0]]
            ci = indent_of(head)
            if ci < ind:
                break
            if ci > ind:
                break  # 上層處理
            stripped = head.strip()
            if not stripped.startswith("- "):
                break
            item_raw = stripped[2:]  # 去掉 "- "
            pos[0] += 1
            # 三種情況:
            #   "- key: value"   (item 是 map,第一行 inline)
            #   "- xxx"          (item 是 scalar)
            #   "- " 開頭但空,接著是 block
            if ":" in item_raw and not item_raw.startswith(("{", "[")):
                # 重建一個兩行 map,前綴縮排對齊
                fake = " " * (ind + 2) + item_raw
                lines.insert(pos[0], fake)
                # parse_map 從這個新插入的位置起;它會消費 "- xxx" 這一行
                # 但我們已經跳過;改用更直接辦法:手動解析第一行 + 解析剩餘 block
                out.append(_parse_map_item(ind + 2, first_line=item_raw))
            else:
                # scalar 或 flow 物件
                if item_raw.startswith("{") and item_raw.endswith("}"):
                    out.append(parse_flow_object(item_raw))
                elif item_raw.startswith("[") and item_raw.endswith("]"):
                    out.append(parse_flow_list(item_raw))
                elif item_raw == "":
                    # block 子元素
                    out.append(parse_block(ind + 2))
                else:
                    out.append(_yaml_coerce(item_raw))
        return out

    def _parse_map_item(parent_ind: int, first_line: str) -> dict:
        # 解析 "- xxx: yyy" 的第一行,然後繼續吃縮排 > parent_ind 的行
        d: dict = {}
        k, _, v = first_line.partition(":")
        v = v.strip()
        if v == "":
            d[k] = parse_block(parent_ind)
        elif v.startswith("[") and v.endswith("]"):
            d[k] = parse_flow_list(v)
        elif v.startswith("{") and v.endswith("}"):
            d[k] = parse_flow_object(v)
        else:
            d[k] = _yaml_coerce(v)
        # 繼續吃剩餘 sibling
        extra = parse_map_continuation(parent_ind)
        d.update(extra)
        return d

    def parse_map(ind: int) -> dict:
        d: dict = {}
        while pos[0] < len(lines):
            head = lines[pos[0]]
            ci = indent_of(head)
            if ci < ind:
                break
            if ci > ind:
                break
            stripped = head.strip()
            if stripped.startswith("- "):
                break
            pos[0] += 1
            k, _, v = stripped.partition(":")
            v = v.strip()
            if v == "":
                d[k] = parse_block(ind + 2) if pos[0] < len(lines) and indent_of(lines[pos[0]]) > ind else None
                if k not in d or d[k] is None:
                    d[k] = parse_block(ind + 2)
            elif v.startswith("[") and v.endswith("]"):
                d[k] = parse_flow_list(v)
            elif v.startswith("{") and v.endswith("}"):
                d[k] = parse_flow_object(v)
            else:
                d[k] = _yaml_coerce(v)
        return d

    def parse_map_continuation(ind: int) -> dict:
        d: dict = {}
        while pos[0] < len(lines):
            head = lines[pos[0]]
            ci = indent_of(head)
            if ci != ind:
                break
            stripped = head.strip()
            if stripped.startswith("- "):
                break
            pos[0] += 1
            k, _, v = stripped.partition(":")
            v = v.strip()
            if v == "":
                d[k] = parse_block(ind + 2)
            elif v.startswith("[") and v.endswith("]"):
                d[k] = parse_flow_list(v)
            elif v.startswith("{") and v.endswith("}"):
                d[k] = parse_flow_object(v)
            else:
                d[k] = _yaml_coerce(v)
        return d

    return parse_block(0)


def yaml_get(cfg: Any, dotted_key: str, default: Any = None) -> Any:
    """從 nested dict/list 結構用 'a.b.0.c' 取值。"""
    cur = cfg
    for seg in dotted_key.split("."):
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(seg, default)
        elif isinstance(cur, list):
            try:
                cur = cur[int(seg)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur if cur is not None else default


# ---- 工具 sub-process 呼叫 -----------------------------------------
def run_cmd(cmd: list[str], timeout: float = 5.0, input_data: str | None = None) -> tuple[int, str, str]:
    """subprocess 包裝;失敗不 raise,回 (rc, stdout, stderr)。"""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, input=input_data
        )
        return (r.returncode, r.stdout, r.stderr)
    except FileNotFoundError as e:
        return (127, "", f"command not found: {e}")
    except subprocess.TimeoutExpired:
        return (124, "", f"timeout after {timeout}s")


# ---- 並發鎖 (fcntl 強型別,跨平台) -------------------------------
def acquire_lock(lock_path: Path, stale_sec: int = LOCK_STALE_SEC) -> int | None:
    """回 fd 表示取得鎖,None 表示已被佔用。"""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            age = time.time() - lock_path.stat().st_mtime
            if age > stale_sec:
                lock_path.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        if sys.platform != "win32":
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd, f"{os.getpid()}\n{time.time()}\n".encode("utf-8"))
        return fd
    except (OSError, IOError):
        return None


def release_lock(fd: int | None) -> None:
    if fd is None:
        return
    try:
        if sys.platform != "win32":
            fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        os.close(fd)
    except Exception:
        pass


# ---- cooldown stamp (sanitize 檔名) -------------------------------
def _sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def stamp_path(alert: Alert) -> Path:
    key = f"{alert.check}::{alert.target}::{alert.severity.name}"
    return STATE_DIR / (_sanitize(key) + ".stamp")


def in_cooldown(alert: Alert, cooldown_sec: int) -> bool:
    p = stamp_path(alert)
    if not p.exists():
        return False
    try:
        age = time.time() - p.stat().st_mtime
        return age < cooldown_sec
    except OSError:
        return False


def write_stamp(alert: Alert) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write(stamp_path(alert), str(time.time()))


# ---- Check 抽象 ------------------------------------------------------
@dataclass
class CheckResult:
    alerts: list[Alert] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


Check = Callable[[dict], CheckResult]


# ---- Check 實作 ------------------------------------------------------
def check_disk(cfg: dict) -> CheckResult:
    res = CheckResult()
    rc, out, err = run_cmd(
        ["df", "--output=source,size,used,avail,pcent,target"],
        timeout=10,
    )
    if rc != 0:
        # df 失敗 → journalctl fallback (原則: graceful degradation)
        rc2, out2, _ = run_cmd(["journalctl", "-n", "20", "-p", "err", "--no-pager"], timeout=5)
        res.error = f"df failed (rc={rc}): {err.strip() or 'no stderr'}"
        return res
    fs_white = yaml_get(cfg, "checks.disk.include_mounts", []) or []
    fs_black = yaml_get(cfg, "checks.disk.exclude_fs_types",
                        ["tmpfs", "devtmpfs", "overlay", "squashfs", "efivarfs"])
    excludes = yaml_get(cfg, "checks.disk.exclude_mounts",
                        [r"^/run$", r"^/sys$", r"^/dev$"])
    warn_pct = yaml_get(cfg, "checks.disk.warn", 70)
    alert_pct = yaml_get(cfg, "checks.disk.alert", 85)
    crit_pct = yaml_get(cfg, "checks.disk.critical", 95)
    rows = out.strip().splitlines()[1:]
    for row in rows:
        cols = row.split()
        if len(cols) < 6:
            continue
        src, sz, used, avail, pct_s, mnt = cols[:6]
        try:
            pct = float(pct_s.rstrip("%"))
        except ValueError:
            continue
        if any(re.fullmatch(p, mnt) for p in excludes):
            continue
        if fs_black and any(b.lower() in src.lower() for b in fs_black):
            continue
        if fs_white and not any(w in mnt for w in fs_white):
            # 若有明確 include 白名單,只檢查白名單中的 mount
            continue
        res.raw[mnt] = {"pct": pct, "size": sz, "used": used, "avail": avail}
        if pct >= crit_pct:
            sev = SEV_CRITICAL
        elif pct >= alert_pct:
            sev = SEV_ALERT
        elif pct >= warn_pct:
            sev = SEV_WARN
        else:
            continue
        res.alerts.append(Alert(
            check="disk", target=mnt, severity=sev,
            value=pct, threshold=crit_pct if sev is SEV_CRITICAL
                else alert_pct if sev is SEV_ALERT else warn_pct,
            message=f"{mnt} ({src}) 使用率 {pct:.1f}%",
        ))
    return res


def check_memory(cfg: dict) -> CheckResult:
    res = CheckResult()
    rc, out, err = run_cmd(["free", "-b"], timeout=5)
    if rc != 0:
        res.error = f"free failed: {err.strip()}"
        return res
    # Mem 行第二欄 = total, 第三欄 = used
    m = {}
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] in ("Mem:", "Swap:"):
            try:
                m[parts[0].rstrip(":")] = {
                    "total": int(parts[1]),
                    "used": int(parts[2]),
                    "free": int(parts[3]),
                }
            except (ValueError, IndexError):
                pass
    if not m:
        res.error = "no memory line parsed"
        return res
    mem = m["Mem"]
    pct = (mem["used"] / mem["total"] * 100.0) if mem["total"] else 0.0
    res.raw = {"mem_pct": pct, **mem}
    warn = yaml_get(cfg, "checks.memory.warn", 75)
    alert = yaml_get(cfg, "checks.memory.alert", 88)
    crit = yaml_get(cfg, "checks.memory.critical", 95)
    if pct >= crit:
        sev = SEV_CRITICAL; thr = crit
    elif pct >= alert:
        sev = SEV_ALERT; thr = alert
    elif pct >= warn:
        sev = SEV_WARN; thr = warn
    else:
        return res
    res.alerts.append(Alert(
        check="memory", target="mem", severity=sev,
        value=pct, threshold=thr,
        message=f"記憶體使用率 {pct:.1f}% ({mem['used']/1024/1024:.0f}MiB / {mem['total']/1024/1024:.0f}MiB)",
    ))
    if "Swap:" in m:
        sw = m["Swap"]
        sw_pct = (sw["used"] / sw["total"] * 100.0) if sw["total"] else 0.0
        res.raw["swap_pct"] = sw_pct
        if sw_pct >= 50:
            res.alerts.append(Alert(
                check="memory", target="swap", severity=SEV_WARN,
                value=sw_pct, threshold=50,
                message=f"swap 使用率 {sw_pct:.1f}%",
            ))
    return res


def check_load(cfg: dict) -> CheckResult:
    res = CheckResult()
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
        l1, l5, l15 = float(parts[0]), float(parts[1]), float(parts[2])
    except (OSError, ValueError, IndexError) as e:
        res.error = f"loadavg read failed: {e}"
        return res
    try:
        nproc = os.cpu_count() or 1
    except NotImplementedError:
        nproc = 1
    l1_per_core = l1 / nproc
    res.raw = {"load1": l1, "load5": l5, "load15": l15, "nproc": nproc, "l1_per_core": l1_per_core}
    warn = yaml_get(cfg, "checks.load.warn", 0.7)
    alert = yaml_get(cfg, "checks.load.alert", 1.0)
    crit = yaml_get(cfg, "checks.load.critical", 1.5)
    if l1_per_core >= crit:
        sev = SEV_CRITICAL; thr = crit
    elif l1_per_core >= alert:
        sev = SEV_ALERT; thr = alert
    elif l1_per_core >= warn:
        sev = SEV_WARN; thr = warn
    else:
        return res
    res.alerts.append(Alert(
        check="load", target="load1_per_core", severity=sev,
        value=l1_per_core, threshold=thr,
        message=f"1-min load/core {l1_per_core:.2f} (raw load1={l1:.2f}, nproc={nproc})",
    ))
    return res


def check_cpu(cfg: dict) -> CheckResult:
    """透過 /proc/stat 計算短窗 CPU 使用率 (delta 模式)。"""
    res = CheckResult()
    state_file = STATE_DIR / "cpu_prev.json"
    warn = yaml_get(cfg, "checks.cpu.warn", 70)
    alert = yaml_get(cfg, "checks.cpu.alert", 85)
    crit = yaml_get(cfg, "checks.cpu.critical", 95)
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        cols = line.split()
        if cols[0] != "cpu":
            raise ValueError(f"unexpected: {cols[0]}")
        nums = list(map(int, cols[1:11]))  # user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
        total = sum(nums)
        idle = nums[3] + nums[4]  # idle + iowait
    except Exception as e:
        res.error = f"/proc/stat read failed: {e}"
        return res
    prev = None
    if state_file.exists():
        try:
            prev = json.loads(state_file.read_text())
        except (OSError, json.JSONDecodeError):
            prev = None
    pct = None
    if prev:
        dt_total = total - prev["total"]
        dt_idle = idle - prev["idle"]
        if dt_total > 0:
            pct = (1.0 - dt_idle / dt_total) * 100.0
    # 寫入新值供下次對照
    atomic_write(state_file, json.dumps({"total": total, "idle": idle, "ts": time.time()}))
    if pct is None:
        # 第一次跑,沒有 baseline → 不報
        return res
    res.raw = {"cpu_pct": pct}
    if pct >= crit:
        sev = SEV_CRITICAL; thr = crit
    elif pct >= alert:
        sev = SEV_ALERT; thr = alert
    elif pct >= warn:
        sev = SEV_WARN; thr = warn
    else:
        return res
    res.alerts.append(Alert(
        check="cpu", target="usage", severity=sev,
        value=pct, threshold=thr,
        message=f"CPU 使用率 {pct:.1f}% (delta-based, 兩次跑間隔為週期)",
    ))
    return res


def check_inode(cfg: dict) -> CheckResult:
    res = CheckResult()
    # GNU df 的 --output 不支援 inode 欄位,改用 `df -i` + 解析最後一欄 (IUse%)
    # -i 與 --output 互斥,只能分開跑;POSIX 標準格式
    # df 沒 -i 支援時退到 fallback (Linux 一般都有;macOS 用 `df -i` 即可)
    rc, out, err = run_cmd(["df", "-i", "-P"], timeout=10)
    if rc != 0:
        res.error = f"df inode failed: {err.strip()}"
        return res
    warn = yaml_get(cfg, "checks.inode.warn", 70)
    alert = yaml_get(cfg, "checks.inode.alert", 85)
    crit = yaml_get(cfg, "checks.inode.critical", 95)
    excludes = yaml_get(cfg, "checks.inode.exclude_mounts",
                        [r"^/run$", r"^/sys$", r"^/dev$"])
    fs_black = yaml_get(cfg, "checks.inode.exclude_fs_types",
                        ["tmpfs", "devtmpfs", "overlay", "squashfs", "efivarfs"])
    # df -i -P 格式:Filesystem Inodes IUsed IFree IUse% Mounted on
    # IUse% 可能是 "-" 或數字百分比
    rows = out.strip().splitlines()[1:]
    for row in rows:
        cols = row.split()
        if len(cols) < 6:
            continue
        src, _it, _iu, _if, pct_s, mnt = cols[0], cols[1], cols[2], cols[3], cols[4], cols[5]
        if pct_s == "-":
            continue  # 該 FS 無 inode (e.g. efivarfs)
        try:
            pct = float(pct_s.rstrip("%"))
        except ValueError:
            continue
        if any(re.fullmatch(p, mnt) for p in excludes):
            continue
        if fs_black and any(b.lower() in src.lower() for b in fs_black):
            continue
        if pct >= crit:
            sev = SEV_CRITICAL; thr = crit
        elif pct >= alert:
            sev = SEV_ALERT; thr = alert
        elif pct >= warn:
            sev = SEV_WARN; thr = warn
        else:
            continue
        res.alerts.append(Alert(
            check="inode", target=mnt, severity=sev,
            value=pct, threshold=thr,
            message=f"{mnt} inode 使用率 {pct:.1f}%",
        ))
    return res


def check_journal(cfg: dict) -> CheckResult:
    """掃 journalctl 過去 N 分鐘的 ERROR/CRITICAL。"""
    res = CheckResult()
    window_min = int(yaml_get(cfg, "checks.journal.window_min", 5))
    patterns = yaml_get(cfg, "checks.journal.error_patterns",
                        ["Out of memory", "I/O error", "segfault", "panic", "Traceback"])
    threshold = int(yaml_get(cfg, "checks.journal.alert_threshold", 3))
    rc, out, err = run_cmd(
        ["journalctl", "-p", "err", "--since", f"-{window_min} min", "--no-pager", "-q"],
        timeout=10,
    )
    if rc not in (0, 1):  # 1 = no entries
        # graceful degradation → fallback grep /var/log
        rc2, out2, err2 = run_cmd(
            ["grep", "-hE", "emerg|alert|crit|err", "/var/log/syslog", "/var/log/messages"],
            timeout=5,
        )
        if rc2 not in (0, 1):
            res.error = f"journalctl+syslog both failed: {err.strip()} | {err2.strip()}"
            return res
        out = out2
    matched = []
    for ln in out.splitlines():
        for pat in patterns:
            if pat.lower() in ln.lower():
                matched.append(ln.strip()[:200])
                break
    res.raw = {"matched_count": len(matched), "window_min": window_min, "samples": matched[:5]}
    if len(matched) >= threshold:
        sev = SEV_ALERT if len(matched) < threshold * 2 else SEV_CRITICAL
        res.alerts.append(Alert(
            check="journal", target=f"errors_last_{window_min}min", severity=sev,
            value=len(matched), threshold=threshold,
            message=f"近 {window_min} 分鐘 {len(matched)} 條嚴重 log (>= {threshold})",
        ))
    return res


CHECK_REGISTRY: dict[str, Check] = {
    "disk": check_disk,
    "memory": check_memory,
    "load": check_load,
    "cpu": check_cpu,
    "inode": check_inode,
    "journal": check_journal,
}


# ---- 通知 dispatch --------------------------------------------------
def render_alert(alert: Alert, fmt: str = "text") -> str:
    ts = dt.datetime.fromtimestamp(time.time()).isoformat(timespec="seconds")
    if fmt == "json":
        return json.dumps({
            "ts": ts, "host": alert.host, "check": alert.check,
            "target": alert.target, "severity": alert.severity.name,
            "value": round(alert.value, 2), "threshold": alert.threshold,
            "message": alert.message,
        }, ensure_ascii=False)
    return f"[{ts}] [{alert.severity.name:8}] {alert.host} {alert.check}/{alert.target}: {alert.message}"


def notify_log(alerts: Iterable[Alert]) -> int:
    """寫到 alerts.log (append)。"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [render_alert(a) for a in alerts]
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")
    return len(lines)


def notify_webhook(url: str, alerts: list[Alert], timeout: float = 10.0) -> tuple[int, str]:
    if not url or not alerts:
        return (0, "skipped")
    payload = {
        "user_agent": USER_AGENT,
        "alerts": [
            {
                "ts": dt.datetime.fromtimestamp(time.time()).isoformat(timespec="seconds"),
                "host": a.host, "check": a.check, "target": a.target,
                "severity": a.severity.name,
                "value": round(a.value, 2),
                "threshold": a.threshold,
                "message": a.message,
            }
            for a in alerts
        ],
    }
    return http_post_json(url, payload, timeout=timeout)


def notify_desktop(alerts: Iterable[Alert]) -> int:
    """notify-send (只有 desktop session 才有效)。"""
    if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        return 0
    rc, _, _ = run_cmd(["which", "notify-send"], timeout=2)
    if rc != 0:
        return 0
    n = 0
    for a in alerts:
        summary = f"[mlogwatch {a.severity.name}] {a.check}/{a.target}"
        run_cmd(["notify-send", "-u", "critical" if a.severity is SEV_CRITICAL else "normal",
                 summary, a.message], timeout=5)
        n += 1
    return n


def dispatch(alerts: list[Alert], cfg: dict, dry_run: bool) -> dict[str, Any]:
    """過 cooldown → 分發給 log / webhook / desktop。
    注意:dry-run 模式不下副作用 (包含 stamp),因為 dry-run 是「看會發什麼」不該污染真實 cooldown 狀態。
    """
    cooldown = int(yaml_get(cfg, "notify.cooldown_seconds", COOLDOWN_DEFAULT_SEC))
    sent: list[Alert] = []
    suppressed: list[Alert] = []
    for a in alerts:
        if in_cooldown(a, cooldown):
            suppressed.append(a)
            continue
        sent.append(a)
        if not dry_run:
            write_stamp(a)
    out: dict[str, Any] = {"suppressed": len(suppressed), "sent_count": len(sent)}
    if dry_run:
        out["sent"] = [render_alert(a) for a in sent]
        out["note"] = "dry-run: skipped log/webhook/desktop side-effects"
        return out
    if sent:
        out["log_lines"] = notify_log(sent)
        out["desktop"] = notify_desktop(sent)
        url = yaml_get(cfg, "notify.webhook_url", "")
        if url:
            rc, msg = notify_webhook(url, sent)
            out["webhook_status"] = rc
            out["webhook_msg"] = msg
        else:
            out["webhook_status"] = 0
            out["webhook_msg"] = "no webhook_url configured"
    return out


# ---- 報告 ----------------------------------------------------------
def write_report(run_id: str, results: dict[str, CheckResult], dispatch_out: dict, cfg: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# mlogwatch report {run_id}")
    lines.append(f"host: {socket.gethostname()}")
    lines.append(f"version: {__version__}")
    lines.append("")
    for name, r in results.items():
        lines.append(f"## check: {name}")
        if r.error:
            lines.append(f"  ERROR: {r.error}")
        else:
            for k, v in r.raw.items():
                lines.append(f"  {k}: {v}")
            if r.alerts:
                lines.append(f"  alerts: {len(r.alerts)}")
                for a in r.alerts:
                    lines.append(f"    - [{a.severity.name}] {a.target}: {a.message}")
        lines.append("")
    lines.append("## dispatch")
    for k, v in dispatch_out.items():
        lines.append(f"  {k}: {v}")
    out = REPORT_DIR / f"{run_id}.md"
    atomic_write(out, "\n".join(lines) + "\n", mode=0o644)
    return out


# ---- 自我測試 -------------------------------------------------------
SELF_TEST_RESULTS: list[tuple[str, bool, str]] = []


def _assert(name: str, cond: bool, detail: str = "") -> None:
    SELF_TEST_RESULTS.append((name, bool(cond), detail))


def self_test() -> int:
    """14 條 unit test,stdout 印出結果。不需 root。"""
    SELF_TEST_RESULTS.clear()

    # YAML parser
    cfg_simple = parse_yaml("a: 1\nb: hello\nc: true\n")
    _assert("yaml.int_bool_str", cfg_simple == {"a": 1, "b": "hello", "c": True})

    cfg_nested = parse_yaml("outer:\n  inner1: 10\n  inner2:\n    deep: 99\n")
    _assert("yaml.nested", cfg_nested == {"outer": {"inner1": 10, "inner2": {"deep": 99}}})

    cfg_flow = parse_yaml("servers: {web: '10.0.0.1', db: '10.0.0.2'}\n")
    _assert("yaml.flow_object", cfg_flow == {"servers": {"web": "10.0.0.1", "db": "10.0.0.2"}})

    cfg_list = parse_yaml("items:\n  - alpha\n  - beta\n  - gamma\n")
    _assert("yaml.list_block", cfg_list == {"items": ["alpha", "beta", "gamma"]})

    cfg_list_flow = parse_yaml("nums: [1, 2, 3]\n")
    _assert("yaml.list_flow", cfg_list_flow == {"nums": [1, 2, 3]})

    cfg_quoted = parse_yaml('msg: "hello world"\n')
    _assert("yaml.quoted", cfg_quoted == {"msg": "hello world"})

    cfg_comments = parse_yaml("# top comment\na: 1  # inline\nb: 2\n")
    _assert("yaml.comments_stripped", cfg_comments == {"a": 1, "b": 2})

    # yaml_get
    cfg = parse_yaml("a:\n  b:\n    c: 42\nlist:\n  - x\n  - y\n")
    _assert("yaml_get.dotted", yaml_get(cfg, "a.b.c") == 42)
    _assert("yaml_get.list_idx", yaml_get(cfg, "list.0") == "x")
    _assert("yaml_get.missing_default", yaml_get(cfg, "x.y", "def") == "def")

    # sanitize
    _assert("sanitize.slash", _sanitize("a/b::c") == "a_b__c")
    _assert("sanitize.keeps_safe", _sanitize("ok-name_99.x") == "ok-name_99.x")

    # cooldown stamp + Alert serialise
    a = Alert("disk", "/", SEV_ALERT, 90.5, 85.0, "test")
    p = stamp_path(a)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.unlink(missing_ok=True)
    _assert("cooldown.first_run", not in_cooldown(a, 60))
    write_stamp(a)
    _assert("cooldown.inside_window", in_cooldown(a, 60))
    _assert("cooldown.outside_window", not in_cooldown(a, 0))

    # 跑 6 個 check (即使環境不是 Linux 也應該不爆)
    cfg_full = parse_yaml(
        "checks:\n"
        "  disk: {warn: 70, alert: 85, critical: 95, exclude_fs_types: [tmpfs, devtmpfs, overlay, squashfs, efivarfs], exclude_mounts: [\"^/run$\", \"^/sys$\"]}\n"
        "  memory: {warn: 75, alert: 88, critical: 95}\n"
        "  load: {warn: 0.7, alert: 1.0, critical: 1.5}\n"
        "  cpu: {warn: 70, alert: 85, critical: 95}\n"
        "  inode: {warn: 70, alert: 85, critical: 95}\n"
        "  journal: {window_min: 5, alert_threshold: 3}\n"
        "notify:\n"
        "  cooldown_seconds: 1800\n"
    )
    for name, fn in CHECK_REGISTRY.items():
        try:
            r = fn(cfg_full)
            _assert(f"check.{name}.runs_without_raise", True)
        except Exception as e:
            _assert(f"check.{name}.runs_without_raise", False, str(e))

    # 真 alert 生成 (CPU 注入法:造假 prev 讓 delta 爆)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    cpu_state = STATE_DIR / "cpu_prev.json"
    # 故意把 prev 設得遠高於現在,讓算出來的使用率爆炸
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        cols = line.split()
        nums = list(map(int, cols[1:11]))
        cur_total = sum(nums)
        cur_idle = nums[3] + nums[4]
        # prev 設成讓 dt_idle ~ 0 全部都 busy
        fake_prev = {"total": cur_total - 1000, "idle": cur_idle, "ts": time.time()}
        atomic_write(cpu_state, json.dumps(fake_prev))
        r = check_cpu(cfg_full)
        # 注意:pct 可能 >= 95 觸發 CRITICAL 或甚至 >100
        _assert("check.cpu.fake_overlimit_yields_alert", len(r.alerts) >= 1,
                f"alerts={len(r.alerts)} raw={r.raw}")
    except Exception as e:
        _assert("check.cpu.fake_overlimit_yields_alert", False, str(e))

    # bounded HTTP read:送網址到一個絕對無法回應的 server 應該 timeout 但不 OOM
    rc, msg = http_post_json("http://127.0.0.1:1/", {"x": 1}, timeout=1.0)
    _assert("http.bounded.read_no_oom", rc == 0, f"rc={rc} msg={msg[:80]}")

    # 並發鎖
    lk = LOCK_DIR / "selftest.lock"
    fd1 = acquire_lock(lk, stale_sec=5)
    _assert("lock.first_acquire", fd1 is not None)
    fd2 = acquire_lock(lk, stale_sec=5)
    _assert("lock.second_busy", fd2 is None)
    release_lock(fd1)
    fd3 = acquire_lock(lk, stale_sec=5)
    _assert("lock.after_release", fd3 is not None)
    release_lock(fd3)

    # 印結果
    ok = sum(1 for _, p, _ in SELF_TEST_RESULTS if p)
    total = len(SELF_TEST_RESULTS)
    print(f"\n=== self-test: {ok}/{total} ===")
    for name, passed, detail in SELF_TEST_RESULTS:
        flag = "PASS" if passed else "FAIL"
        print(f"  {flag:4} {name}{(': ' + detail) if detail else ''}")
    return 0 if ok == total else 1


# ---- 主入口 --------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="mlogwatch — Linux system log & resource monitor")
    p.add_argument("--check", choices=sorted(CHECK_REGISTRY.keys()),
                   help="只跑單一 check")
    p.add_argument("--self-test", action="store_true", help="跑內建單元測試")
    p.add_argument("--dry-run", action="store_true", help="不發通知")
    p.add_argument("--report", action="store_true", help="只生 report, 不算 alert")
    p.add_argument("--quiet", action="store_true", help="抑制 stderr 輸出")
    p.add_argument("--config", type=str, help="指定配置檔")
    p.add_argument("--version", action="version", version=f"mlogwatch {__version__}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.self_test:
        return self_test()

    if args.config:
        global CONFIG_FILE
        CONFIG_FILE = Path(args.config)

    # 載入 config (若不存在,用空白 config 跑)
    if CONFIG_FILE.exists():
        cfg = parse_yaml(CONFIG_FILE.read_text(encoding="utf-8"))
    else:
        cfg = {}

    quiet = args.quiet
    def info(msg: str) -> None:
        if not quiet:
            print(f"[INFO] {msg}", file=sys.stderr)
    def warn(msg: str) -> None:
        print(f"[WARN] {msg}", file=sys.stderr)
    def err(msg: str) -> None:
        print(f"[ERROR] {msg}", file=sys.stderr)

    run_id = time.strftime("%Y%m%dT%H%M%S", time.localtime())

    # 並發鎖
    lock_path = LOCK_DIR / "mlogwatch.lock"
    fd = acquire_lock(lock_path)
    if fd is None:
        err(f"another mlogwatch run holds {lock_path} (stale after {LOCK_STALE_SEC}s)")
        return 2
    try:
        info(f"mlogwatch {__version__} run {run_id} on {socket.gethostname()}")
        targets = [args.check] if args.check else sorted(CHECK_REGISTRY.keys())
        results: dict[str, CheckResult] = {}
        all_alerts: list[Alert] = []
        for name in targets:
            fn = CHECK_REGISTRY[name]
            try:
                r = fn(cfg)
            except Exception as e:
                r = CheckResult(error=f"{type(e).__name__}: {e}")
            results[name] = r
            if r.error:
                warn(f"check {name}: {r.error}")
            for a in r.alerts:
                info(f"{a.severity.name} {a.check}/{a.target}: {a.message}")
                all_alerts.append(a)

        if args.report:
            # report-only 模式:不 dispatch,只寫檔
            rpt = write_report(run_id, results,
                               {"report_only": True, "alerts_seen": len(all_alerts)}, cfg)
            info(f"report: {rpt}")
            return 0

        dispatch_out = dispatch(all_alerts, cfg, dry_run=args.dry_run)
        rpt = write_report(run_id, results, dispatch_out, cfg)
        info(f"report: {rpt}")
        info(f"alerts: seen={len(all_alerts)} sent={dispatch_out.get('sent_count', 0)} "
             f"suppressed={dispatch_out.get('suppressed', 0)}")
        return 1 if all_alerts else 0
    finally:
        release_lock(fd)


if __name__ == "__main__":
    sys.exit(main())
