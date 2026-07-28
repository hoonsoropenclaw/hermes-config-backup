#!/usr/bin/env bash
# logwatcher.sh — Linux 系統日誌與資源監控腳本
# 用法:
#   ./logwatcher.sh                跑一次完整檢查
#   ./logwatcher.sh --check disk   單獨跑某個 check
#   ./logwatcher.sh --self-test    跑內建單元測試
#   ./logwatcher.sh --dry-run      跑檢查但不發通知
#   ./logwatcher.sh --report       只生成本次報告檔, 不算 alert
#   ./logwatcher.sh --quiet        抑制 stderr 輸出
#   ./logwatcher.sh --config PATH  指定配置檔
set -u
set -o pipefail

# ===== 內建常數 =====
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
# 允許環境變數覆蓋路徑（測試 / 多實例用）
CONFIG_FILE="${LOGWATCHER_CONFIG:-${SCRIPT_DIR}/config.yaml}"
STATE_DIR="${LOGWATCHER_STATE_DIR:-${SCRIPT_DIR}/state}"
LOCK_DIR="${LOGWATCHER_LOCK_DIR:-${SCRIPT_DIR}/locks}"
REPORT_DIR="${LOGWATCHER_REPORT_DIR:-${SCRIPT_DIR}/reports}"
ALERT_LOG_DEFAULT="${REPORT_DIR}/alerts.log"
TIMESTAMP="$(date +'%Y-%m-%dT%H:%M:%S%z')"
EPOCH="$(date +%s)"
HOSTNAME_SHORT="$(hostname -s 2>/dev/null || hostname)"

# 預設旗標
MODE_RUN=0
MODE_SELF_TEST=0
MODE_DRY_RUN=0
MODE_REPORT_ONLY=0
QUIET=0
ONLY_CHECK=""

# ===== 工具函式 =====
log_info()  { [[ ${QUIET} -eq 1 ]] || printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_err()   { printf '[ERROR] %s\n' "$*" >&2; }
die()       { log_err "$*"; exit 1; }

# 確保目錄存在
mkdir -p "$STATE_DIR" "$LOCK_DIR" "$REPORT_DIR"

# ===== YAML 解析器（最小集合, 支援 nested block, flow mapping, flow list）=====
yaml_get() {
    # 用法: yaml_get <key.path>
    local key_path="$1"
    python3 - "$CONFIG_FILE" "$key_path" <<'PYEOF'
import sys, re
cfg_path, key_path = sys.argv[1], sys.argv[2]
parts = key_path.split('.')
with open(cfg_path, 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.splitlines()

def strip_comment(line):
    in_str = False; quote = None; out = []
    for ch in line:
        if not in_str and ch == '#':
            break
        if ch in '"\'':
            if not in_str: in_str = True; quote = ch
            elif quote == ch: in_str = False
        out.append(ch)
    return ''.join(out).rstrip()

def parse_flow_object(s):
    s = s.strip()
    if not (s.startswith('{') and s.endswith('}')):
        return None
    inner = s[1:-1].strip()
    if not inner:
        return {}
    result = {}
    depth = 0; in_str = False; quote = None; cur = []; items = []
    for ch in inner:
        if not in_str:
            if ch in '"\'':
                in_str = True; quote = ch; cur.append(ch)
            elif ch in '[{(':
                depth += 1; cur.append(ch)
            elif ch in ']})':
                depth -= 1; cur.append(ch)
            elif ch == ',' and depth == 0:
                items.append(''.join(cur).strip()); cur = []
            else:
                cur.append(ch)
        else:
            cur.append(ch)
            if ch == quote:
                in_str = False
    if cur:
        items.append(''.join(cur).strip())
    for item in items:
        if ':' not in item:
            continue
        k, v = item.split(':', 1)
        k = k.strip()
        v = v.strip()
        if v.startswith('[') and v.endswith(']'):
            inner_list = v[1:-1]
            v = [x.strip().strip('"').strip("'") for x in inner_list.split(',') if x.strip()]
        elif v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        result[k] = v
    return result

def parse_flow_list(s):
    s = s.strip()
    if not (s.startswith('[') and s.endswith(']')):
        return None
    inner = s[1:-1].strip()
    if not inner:
        return []
    result = []
    depth = 0; in_str = False; quote = None; cur = []
    for ch in inner:
        if not in_str:
            if ch in '"\'':
                in_str = True; quote = ch; cur.append(ch)
            elif ch in '[{(':
                depth += 1; cur.append(ch)
            elif ch in ']})':
                depth -= 1; cur.append(ch)
            elif ch == ',' and depth == 0:
                result.append(''.join(cur).strip()); cur = []
            else:
                cur.append(ch)
        else:
            cur.append(ch)
            if ch == quote:
                in_str = False
    if cur:
        result.append(''.join(cur).strip())
    cleaned = []
    for x in result:
        x = x.strip()
        if x.startswith('"') and x.endswith('"'):
            x = x[1:-1]
        elif x.startswith("'") and x.endswith("'"):
            x = x[1:-1]
        cleaned.append(x)
    return cleaned

def find_node(lines):
    stack = []
    current = {}
    parent_stack = [current]
    for raw in lines:
        line = strip_comment(raw)
        if not line.strip():
            continue
        m = re.match(r'^(\s*)(- )?([^:]+):\s*(.*)', line)
        if not m:
            continue
        indent = len(m.group(1))
        is_list_item = m.group(2) is not None
        key = m.group(3).strip()
        val = m.group(4).strip()
        if is_list_item:
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
            parent_stack.pop()
        if val.startswith('{') and val.endswith('}'):
            obj = parse_flow_object(val)
            if obj is not None:
                parent_stack[-1][key] = obj
                continue
        if val.startswith('[') and val.endswith(']'):
            lst = parse_flow_list(val)
            if lst is not None:
                parent_stack[-1][key] = lst
                continue
        if val == '':
            node = {}
            stack.append((indent, key))
            parent_stack[-1][key] = node
            parent_stack.append(node)
        else:
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            parent_stack[-1][key] = val
    return current

def lookup(node, parts):
    for p in parts:
        if isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return None
    return node

cfg = find_node(lines)
val = lookup(cfg, parts)
if val is None:
    sys.exit(0)
if isinstance(val, bool):
    print('true' if val else 'false')
elif isinstance(val, list):
    print('\n'.join(str(x) for x in val))
elif isinstance(val, dict):
    for k, v in val.items():
        print(f'{k}={v}')
else:
    print(val)
PYEOF
}

yaml_get_or_default() {
    local val
    val="$(yaml_get "$1" 2>/dev/null || true)"
    if [[ -z "$val" ]]; then
        printf '%s' "$2"
    else
        printf '%s' "$val"
    fi
}

yaml_get_list() {
    # 取出 list 全部（每行一個）
    # 支援 nested: 沿 parts[] 逐層深入, 最後一層若是 list 取 list
    python3 - "$CONFIG_FILE" "$1" <<'PYEOF'
import sys, re
cfg_path, key_path = sys.argv[1], sys.argv[2]
parts = key_path.split('.')
with open(cfg_path, 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.splitlines()
def strip_comment(line):
    in_str = False; quote = None; out = []
    for ch in line:
        if not in_str and ch == '#':
            break
        if ch in '"\'':
            if not in_str: in_str = True; quote = ch
            elif quote == ch: in_str = False
        out.append(ch)
    return ''.join(out).rstrip()

# 沿 parts 逐層深入找 leaf 區塊
cur_indent = -1
target_indent = -1
from_line = 0

top_key = parts[0]
for i, raw in enumerate(lines):
    line = strip_comment(raw)
    if not line.strip():
        continue
    m = re.match(r'^(\s*)([^:]+):', line)
    if m and m.group(2).strip() == top_key and len(m.group(1)) == 0:
        from_line = i + 1
        target_indent = 0
        cur_indent = 0
        break

for depth in range(1, len(parts)):
    sub_key = parts[depth]
    found = False
    i = from_line
    while i < len(lines):
        line = strip_comment(lines[i])
        if not line.strip():
            i += 1; continue
        m = re.match(r'^(\s*)([^:]+):\s*(.*)', line)
        if not m:
            i += 1; continue
        indent = len(m.group(1))
        if indent <= cur_indent:
            sys.exit(0)
        if m.group(2).strip() == sub_key and indent == cur_indent + 2:
            from_line = i + 1
            target_indent = indent
            cur_indent = indent
            found = True
            break
        i += 1
    if not found:
        sys.exit(0)

out = []
for i in range(from_line, len(lines)):
    line = strip_comment(lines[i])
    if not line.strip():
        continue
    mlist = re.match(r'^(\s*)- (.+)$', line)
    if mlist:
        if len(mlist.group(1)) <= target_indent:
            break
        val = mlist.group(2).strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        if val:
            out.append(val)
        continue
    m = re.match(r'^(\s*)([^:]+):\s*(.*)', line)
    if not m:
        continue
    indent = len(m.group(1))
    if indent <= target_indent:
        break

for v in out:
    print(v)
PYEOF
}

# ===== 鎖定 =====
acquire_lock() {
    local lock_file="${LOCK_DIR}/watcher.lock"
    if [[ -e "$lock_file" ]]; then
        local pid mtime age
        pid="$(cat "$lock_file" 2>/dev/null || echo 0)"
        mtime="$(stat -c %Y "$lock_file" 2>/dev/null || echo 0)"
        age=$(( EPOCH - mtime ))
        if kill -0 "$pid" 2>/dev/null && [[ $age -lt 600 ]]; then
            log_warn "另一個 watcher 正在執行 (pid ${pid}, age ${age}s), 跳過本次"
            exit 0
        else
            log_info "移除 stale lock (pid ${pid}, age ${age}s)"
            rm -f "$lock_file"
        fi
    fi
    echo "$$" > "$lock_file"
    trap 'rm -f "${LOCK_DIR}/watcher.lock"' EXIT
}

# ===== 通知 =====
declare -a ALERTS_BUFFER=()

emit_alert() {
    # emit_alert <level> <check> <target> <message>
    local level="$1" check="$2" target="$3" msg="$4"
    local alerts_log
    alerts_log="$(yaml_get_or_default 'notification.alerts_log' "$ALERT_LOG_DEFAULT")"
    local line="${TIMESTAMP}|${level}|${HOSTNAME_SHORT}|${check}|${target}|${msg}"
    ALERTS_BUFFER+=("$line")

    # 抑制冷卻
    local cooldown
    cooldown="$(yaml_get_or_default 'notification.cooldown_minutes' 30)"
    local stamp_key="${check}::${target}::${level}"
    local stamp="${STATE_DIR}/stamp.$(echo "$stamp_key" | tr -c 'A-Za-z0-9._-' '_')"
    if [[ -e "$stamp" ]]; then
        local last
        last="$(stat -c %Y "$stamp" 2>/dev/null || echo 0)"
        if [[ $(( EPOCH - last )) -lt $(( cooldown * 60 )) ]]; then
            log_info "[suppressed] ${level} ${check} ${target} (cooldown ${cooldown}m)"
            return
        fi
    fi
    touch "$stamp"

    # 寫入 alerts log
    if [[ ${MODE_DRY_RUN} -eq 0 ]]; then
        printf '%s\n' "$line" >> "$alerts_log"
    fi

    # stderr
    if [[ "$(yaml_get_or_default 'notification.stderr' true)" == "true" ]]; then
        printf '[%s] %s\n' "$level" "$msg" >&2
    fi

    # 通知通道
    if [[ ${MODE_DRY_RUN} -eq 0 ]]; then
        send_webhook "$level" "$check" "$target" "$msg"
        send_telegram "$level" "$check" "$target" "$msg"
    fi
}

send_webhook() {
    local level="$1" check="$2" target="$3" msg="$4"
    local url
    url="$(yaml_get_or_default 'notification.webhook_url' '')"
    [[ -z "$url" ]] && return

    local timeout
    timeout="$(yaml_get_or_default 'notification.webhook_timeout_sec' 5)"
    local payload
    payload=$(printf '{"host":"%s","level":"%s","check":"%s","target":"%s","message":"%s","ts":"%s"}' \
        "$HOSTNAME_SHORT" "$level" "$check" "$target" "$msg" "$TIMESTAMP")

    timeout "$timeout" python3 - "$url" "$payload" <<'PYEOF' 2>/dev/null || log_warn "webhook failed"
import sys, urllib.request
url, payload = sys.argv[1], sys.argv[2]
try:
    req = urllib.request.Request(url, data=payload.encode('utf-8'),
        headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=5) as r:
        pass
except Exception as e:
    print(f"webhook error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

send_telegram() {
    local level="$1" check="$2" target="$3" msg="$4"
    [[ -z "${TG_BOT_TOKEN:-}" ]] && return
    [[ -z "${TG_CHAT_ID:-}" ]] && return

    local text
    text=$(printf '[%s] %s on %s\n%s' "$level" "$check" "$HOSTNAME_SHORT" "$msg")
    timeout 5 python3 - "$TG_BOT_TOKEN" "$TG_CHAT_ID" "$text" <<'PYEOF' 2>/dev/null || log_warn "telegram failed"
import sys, urllib.request, urllib.parse
token, chat_id, text = sys.argv[1], sys.argv[2], sys.argv[3]
url = f"https://api.telegram.org/bot{token}/sendMessage"
data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text}).encode()
try:
    req = urllib.request.Request(url, data=data, method='POST')
    with urllib.request.urlopen(req, timeout=5) as r:
        pass
except Exception as e:
    print(f"tg error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ===== Check: 磁碟 =====
check_disk() {
    log_info "check_disk ..."
    local warn_p alert_p crit_p
    warn_p="$(yaml_get_or_default 'resources.disk.warn_percent' 80)"
    alert_p="$(yaml_get_or_default 'resources.disk.alert_percent' 90)"
    crit_p="$(yaml_get_or_default 'resources.disk.critical_percent' 95)"

    # 拿排除清單（內建 fallback, 總是排除常見虛擬 fs）
    local exclude_fs exclude_mount
    exclude_fs="$(yaml_get_list 'resources.disk.exclude_fs_types' | paste -sd '|' -)"
    exclude_mount="$(yaml_get_list 'resources.disk.exclude_mount_prefixes' | paste -sd '|' -)"
    local default_fs='tmpfs|devtmpfs|overlay|squashfs|proc|sysfs|cgroup|cgroup2|efivarfs|autofs|ramfs|debugfs|tracefs|configfs|fusectl|hugetlbfs|mqueue|pstore|bpf|binfmt_misc|fuse.gvfsd-fuse'
    local default_mount='^/snap$|^/run$|^/sys$|^/proc$|^/dev$'
    [[ -z "$exclude_fs" ]] && exclude_fs="$default_fs" || exclude_fs="${exclude_fs}|${default_fs}"
    [[ -z "$exclude_mount" ]] && exclude_mount="$default_mount" || exclude_mount="${exclude_mount}|${default_mount}"

    while IFS= read -r line; do
        [[ "$line" =~ ^Filesystem ]] && continue
        local fs size used avail pcent target fstype
        read -r fs size used avail pcent target <<< "$line"
        [[ -z "$target" ]] && continue
        if [[ "$target" =~ $exclude_mount ]]; then continue; fi
        fstype="$(grep -F " $target " /proc/mounts 2>/dev/null | awk '{print $3}' | head -1)"
        if [[ -z "$fstype" ]]; then continue; fi
        if [[ "$fstype" =~ $exclude_fs ]]; then continue; fi
        pcent="${pcent%\%}"
        if ! [[ "$pcent" =~ ^[0-9]+$ ]]; then continue; fi
        if [[ $pcent -ge $crit_p ]]; then
            emit_alert "CRITICAL" "disk" "$target" "disk ${target} (${fs}) at ${pcent}% (>=${crit_p}%)"
        elif [[ $pcent -ge $alert_p ]]; then
            emit_alert "ALERT" "disk" "$target" "disk ${target} (${fs}) at ${pcent}% (>=${alert_p}%)"
        elif [[ $pcent -ge $warn_p ]]; then
            emit_alert "WARN" "disk" "$target" "disk ${target} (${fs}) at ${pcent}% (>=${warn_p}%)"
        else
            log_info "  disk ${target}: ${pcent}% OK"
        fi
    done < <(df --output=source,size,used,avail,pcent,target 2>/dev/null | tail -n +2)
}

# ===== Check: inode =====
check_inode() {
    log_info "check_inode ..."
    local warn_p alert_p crit_p
    warn_p="$(yaml_get_or_default 'resources.inode.warn_percent' 70)"
    alert_p="$(yaml_get_or_default 'resources.inode.alert_percent' 85)"
    crit_p="$(yaml_get_or_default 'resources.inode.critical_percent' 93)"

    while IFS= read -r line; do
        [[ "$line" =~ ^Filesystem ]] && continue
        read -r fs inodes iused ifree ipcent target <<< "$line"
        [[ -z "$target" ]] && continue
        [[ "$target" == "/dev" ]] && continue
        ipcent="${ipcent%\%}"
        [[ -z "$ipcent" || "$ipcent" == "-" ]] && continue
        if ! [[ "$ipcent" =~ ^[0-9]+$ ]]; then continue; fi
        if [[ $ipcent -ge $crit_p ]]; then
            emit_alert "CRITICAL" "inode" "$target" "inode ${target} at ${ipcent}% (>=${crit_p}%)"
        elif [[ $ipcent -ge $alert_p ]]; then
            emit_alert "ALERT" "inode" "$target" "inode ${target} at ${ipcent}% (>=${alert_p}%)"
        elif [[ $ipcent -ge $warn_p ]]; then
            emit_alert "WARN" "inode" "$target" "inode ${target} at ${ipcent}% (>=${warn_p}%)"
        else
            log_info "  inode ${target}: ${ipcent}% OK"
        fi
    done < <(df -i --output=source,inodes,iused,ifree,ipcent,target 2>/dev/null | tail -n +2)
}

# ===== Check: 記憶體 =====
check_memory() {
    log_info "check_memory ..."
    local warn_p alert_p crit_p
    warn_p="$(yaml_get_or_default 'resources.memory.warn_percent' 75)"
    alert_p="$(yaml_get_or_default 'resources.memory.alert_percent' 88)"
    crit_p="$(yaml_get_or_default 'resources.memory.critical_percent' 95)"

    local mem_total mem_avail
    mem_total=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
    mem_avail=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
    if [[ -z "$mem_total" || -z "$mem_avail" ]]; then
        log_warn "  memory: cannot read /proc/meminfo"
        return
    fi
    local used_kb=$(( mem_total - mem_avail ))
    local pcent=$(( used_kb * 100 / mem_total ))
    local total_mb=$(( mem_total / 1024 ))
    local used_mb=$(( used_kb / 1024 ))
    if [[ $pcent -ge $crit_p ]]; then
        emit_alert "CRITICAL" "memory" "system" "memory ${used_mb}MB/${total_mb}MB = ${pcent}% (>=${crit_p}%)"
    elif [[ $pcent -ge $alert_p ]]; then
        emit_alert "ALERT" "memory" "system" "memory ${used_mb}MB/${total_mb}MB = ${pcent}% (>=${alert_p}%)"
    elif [[ $pcent -ge $warn_p ]]; then
        emit_alert "WARN" "memory" "system" "memory ${used_mb}MB/${total_mb}MB = ${pcent}% (>=${warn_p}%)"
    else
        log_info "  memory ${used_mb}MB/${total_mb}MB = ${pcent}% OK"
    fi
}

# ===== Check: SWAP =====
check_swap() {
    log_info "check_swap ..."
    local warn_p alert_p crit_p
    warn_p="$(yaml_get_or_default 'resources.swap.warn_percent' 30)"
    alert_p="$(yaml_get_or_default 'resources.swap.alert_percent' 60)"
    crit_p="$(yaml_get_or_default 'resources.swap.critical_percent' 85)"

    local swap_total swap_free
    swap_total=$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)
    swap_free=$(awk '/^SwapFree:/ {print $2}' /proc/meminfo)
    if [[ -z "$swap_total" || "$swap_total" == "0" ]]; then
        log_info "  swap: no swap configured"
        return
    fi
    local used=$(( swap_total - swap_free ))
    local pcent=$(( used * 100 / swap_total ))
    if [[ $pcent -ge $crit_p ]]; then
        emit_alert "CRITICAL" "swap" "system" "swap ${pcent}% (>=${crit_p}%)"
    elif [[ $pcent -ge $alert_p ]]; then
        emit_alert "ALERT" "swap" "system" "swap ${pcent}% (>=${alert_p}%)"
    elif [[ $pcent -ge $warn_p ]]; then
        emit_alert "WARN" "swap" "system" "swap ${pcent}% (>=${warn_p}%)"
    else
        log_info "  swap ${pcent}% OK"
    fi
}

# ===== Check: CPU load =====
check_load() {
    log_info "check_load ..."
    local warn_r alert_r crit_r
    warn_r="$(yaml_get_or_default 'resources.load.warn_ratio' 1.5)"
    alert_r="$(yaml_get_or_default 'resources.load.alert_ratio' 2.5)"
    crit_r="$(yaml_get_or_default 'resources.load.critical_ratio' 4.0)"
    local cores
    cores=$(nproc 2>/dev/null || echo 1)
    local load1
    load1=$(awk '{print $1}' /proc/loadavg)
    # ratio 用 python 算（避免 bash 不支援浮點）
    local ratio r_thousand
    ratio=$(python3 -c "print(f'{$load1/$cores:.2f}')")
    r_thousand=$(python3 -c "print(int(float('$load1') * 1000 / $cores))")
    local crit_t alert_t warn_t
    crit_t=$(python3 -c "print(int(float('${crit_r}') * 1000))")
    alert_t=$(python3 -c "print(int(float('${alert_r}') * 1000))")
    warn_t=$(python3 -c "print(int(float('${warn_r}') * 1000))")
    if [[ $r_thousand -ge $crit_t ]]; then
        emit_alert "CRITICAL" "load" "1m" "loadavg1 ${load1} / ${cores} cores = ${ratio}x (>=${crit_r}x)"
    elif [[ $r_thousand -ge $alert_t ]]; then
        emit_alert "ALERT" "load" "1m" "loadavg1 ${load1} / ${cores} cores = ${ratio}x (>=${alert_r}x)"
    elif [[ $r_thousand -ge $warn_t ]]; then
        emit_alert "WARN" "load" "1m" "loadavg1 ${load1} / ${cores} cores = ${ratio}x (>=${warn_r}x)"
    else
        log_info "  load ${load1} / ${cores} = ${ratio}x OK"
    fi
}

# ===== Check: 系統日誌 =====
check_logs() {
    log_info "check_logs ..."
    local window
    window="$(yaml_get_or_default 'window_minutes' 10)"

    local k_count=0 a_count=0 s_count=0

    local log_text=""
    if command -v journalctl >/dev/null 2>&1; then
        log_text=$(journalctl --since "-${window} min" --no-pager 2>/dev/null || true)
    fi
    if [[ -z "$log_text" ]] && [[ -r /var/log/syslog ]]; then
        log_text=$(tail -c 200000 /var/log/syslog 2>/dev/null || true)
    fi
    if [[ -z "$log_text" ]]; then
        log_warn "  logs: 無法取得系統日誌"
        return
    fi

    local k_patterns auth_patterns s_patterns
    k_patterns=$(yaml_get_list 'logs.kernel_error_patterns')
    auth_patterns=$(yaml_get_list 'logs.auth_failure_patterns')
    s_patterns=$(yaml_get_list 'logs.service_failure_patterns')

    local k_thr a_thr s_thr
    k_thr="$(yaml_get_or_default 'logs.thresholds.kernel_error_count' 1)"
    a_thr="$(yaml_get_or_default 'logs.thresholds.auth_failure_count' 10)"
    s_thr="$(yaml_get_or_default 'logs.thresholds.service_failure_count' 3)"

    while IFS= read -r pat; do
        [[ -z "$pat" ]] && continue
        local n
        n=$(grep -cE "$pat" <<<"$log_text" 2>/dev/null)
        n="${n%%$'\n'*}"  # 取第一行
        [[ -z "$n" ]] && n=0
        k_count=$(( k_count + n ))
    done <<< "$k_patterns"

    while IFS= read -r pat; do
        [[ -z "$pat" ]] && continue
        local n
        n=$(grep -cE "$pat" <<<"$log_text" 2>/dev/null)
        n="${n%%$'\n'*}"
        [[ -z "$n" ]] && n=0
        a_count=$(( a_count + n ))
    done <<< "$auth_patterns"

    while IFS= read -r pat; do
        [[ -z "$pat" ]] && continue
        local n
        n=$(grep -cE "$pat" <<<"$log_text" 2>/dev/null)
        n="${n%%$'\n'*}"
        [[ -z "$n" ]] && n=0
        s_count=$(( s_count + n ))
    done <<< "$s_patterns"

    log_info "  logs: kernel_err=${k_count} auth_fail=${a_count} service_fail=${s_count} (window=${window}m)"

    if [[ $k_count -ge $k_thr ]]; then
        emit_alert "CRITICAL" "kernel_error" "system" "kernel errors ${k_count} ≥ ${k_thr} in ${window}m"
    fi
    if [[ $a_count -ge $a_thr ]]; then
        emit_alert "ALERT" "auth_failure" "system" "auth failures ${a_count} ≥ ${a_thr} in ${window}m"
    fi
    if [[ $s_count -ge $s_thr ]]; then
        emit_alert "ALERT" "service_failure" "system" "service failures ${s_count} ≥ ${s_thr} in ${window}m"
    fi
}

# ===== 報告 =====
write_report() {
    local report_file="${REPORT_DIR}/report-$(date +%Y%m%d-%H%M%S).txt"
    {
        echo "logwatcher report — ${TIMESTAMP}"
        echo "host: ${HOSTNAME_SHORT}"
        echo "mode: ${MODE_RUN}${MODE_DRY_RUN:+ (dry-run)}${MODE_REPORT_ONLY:+ (report-only)}"
        echo "---"
        echo "load_avg: $(awk '{print $1, $2, $3}' /proc/loadavg)"
        echo "cores: $(nproc)"
        echo "uptime: $(uptime -p 2>/dev/null || awk '{print $1}' /proc/uptime)"
        echo "---"
        echo "df -h:"
        df -h --output=source,size,used,avail,pcent,target 2>/dev/null | head -20
        echo "---"
        echo "free -h:"
        free -h 2>/dev/null
        echo "---"
        echo "alerts emitted this run: ${#ALERTS_BUFFER[@]}"
        if [[ ${#ALERTS_BUFFER[@]} -gt 0 ]]; then
            printf '%s\n' "${ALERTS_BUFFER[@]}"
        fi
    } > "$report_file"
    log_info "report written: $report_file"
}

# ===== 自我測試 =====
run_self_test() {
    log_info "=== self-test begin ==="
    local fails=0

    local v
    v="$(yaml_get 'resources.disk.warn_percent')"
    if [[ "$v" == "80" ]]; then
        log_info "  ✓ yaml_get scalar"
    else
        log_err "  ✗ yaml_get scalar got: '$v'"; fails=$((fails+1))
    fi

    local l_count
    l_count=$(yaml_get_list 'logs.kernel_error_patterns' | wc -l)
    if [[ $l_count -ge 5 ]]; then
        log_info "  ✓ yaml_get_list (${l_count} items)"
    else
        log_err "  ✗ yaml_get_list got: ${l_count}"; fails=$((fails+1))
    fi

    v="$(yaml_get 'nonexistent.key' 2>/dev/null || true)"
    if [[ -z "$v" ]]; then
        log_info "  ✓ yaml_get missing key returns empty"
    else
        log_err "  ✗ yaml_get missing key got: '$v'"; fails=$((fails+1))
    fi

    # 測試 flow object 解析
    v="$(yaml_get 'behavior.lock_timeout_sec' 2>/dev/null || true)"
    if [[ "$v" == "600" ]]; then
        log_info "  ✓ yaml_get flow mapping"
    else
        log_err "  ✗ yaml_get flow mapping got: '$v'"; fails=$((fails+1))
    fi

    if [[ -r /proc/meminfo ]]; then
        log_info "  ✓ /proc/meminfo readable"
    else
        log_err "  ✗ /proc/meminfo not readable"; fails=$((fails+1))
    fi

    if df -h / >/dev/null 2>&1; then
        log_info "  ✓ df works"
    else
        log_err "  ✗ df failed"; fails=$((fails+1))
    fi

    local stamp="${STATE_DIR}/test.stamp"
    touch "$stamp"
    if [[ -e "$stamp" ]]; then
        rm -f "$stamp"
        log_info "  ✓ stamp file mechanism"
    else
        log_err "  ✗ stamp file failed"; fails=$((fails+1))
    fi

    local lock="${LOCK_DIR}/test.lock"
    echo "$$" > "$lock"
    if [[ -e "$lock" ]]; then
        rm -f "$lock"
        log_info "  ✓ lock file mechanism"
    else
        log_err "  ✗ lock file failed"; fails=$((fails+1))
    fi

    # 跑所有 check 不能 crash
    local c
    for c in disk inode memory swap load logs; do
        if check_${c} 2>/dev/null; then
            log_info "  ✓ check_${c} runs"
        else
            log_err "  ✗ check_${c} crashed"; fails=$((fails+1))
        fi
    done
    ALERTS_BUFFER=()

    log_info "=== self-test done: ${fails} failure(s) ==="
    if [[ $fails -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# ===== 維護 =====
cleanup_old() {
    log_info "cleanup_old ..."
    local a_ret s_ret r_ret
    a_ret="$(yaml_get_or_default 'maintenance.alerts_retention_days' 30)"
    s_ret="$(yaml_get_or_default 'maintenance.state_retention_days' 7)"
    r_ret="$(yaml_get_or_default 'maintenance.report_retention_days' 14)"
    local alerts_log
    alerts_log="$(yaml_get_or_default 'notification.alerts_log' "$ALERT_LOG_DEFAULT")"

    if [[ -f "$alerts_log" ]]; then
        find "$(dirname "$alerts_log")" -maxdepth 1 -name 'alerts.log.*' -mtime +${a_ret} -delete 2>/dev/null || true
    fi
    find "$STATE_DIR" -maxdepth 1 -name 'stamp.*' -mtime +${s_ret} -delete 2>/dev/null || true
    find "$REPORT_DIR" -maxdepth 1 -name 'report-*.txt' -mtime +${r_ret} -delete 2>/dev/null || true
    log_info "  cleanup done"
}

# ===== 參數解析 =====
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)    ONLY_CHECK="${2:-}"; shift 2 ;;
        --self-test) MODE_SELF_TEST=1; shift ;;
        --dry-run)  MODE_DRY_RUN=1; shift ;;
        --report)   MODE_REPORT_ONLY=1; shift ;;
        --quiet|-q) QUIET=1; shift ;;
        --config)   CONFIG_FILE="${2:-}"; shift 2 ;;
        --help|-h)
            cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Options:
  --check NAME        單獨跑某個 check (disk|inode|memory|swap|load|logs|cleanup)
  --dry-run           跑檢查但不發通知
  --report            只生成本次報告檔
  --quiet, -q         抑制 stderr 輸出
  --config PATH       指定配置檔
  --self-test         跑內建單元測試
  --help, -h          顯示此說明
EOF
            exit 0
            ;;
        *) log_err "unknown option: $1"; exit 2 ;;
    esac
done

if [[ $MODE_SELF_TEST -eq 1 ]]; then
    run_self_test
fi

# ===== Main =====
MODE_RUN=1

[[ -f "$CONFIG_FILE" ]] || die "config not found: $CONFIG_FILE"

enabled="$(yaml_get_or_default 'enabled' true)"
if [[ "$enabled" != "true" ]]; then
    log_warn "disabled in config (enabled: ${enabled}), exit"
    exit 0
fi

acquire_lock

declare -a CHECKS
if [[ -n "$ONLY_CHECK" ]]; then
    CHECKS=( "$ONLY_CHECK" )
else
    CHECKS=( logs disk inode memory swap load )
fi

for c in "${CHECKS[@]}"; do
    fn="check_${c}"
    if declare -f "$fn" >/dev/null; then
        if [[ "$(yaml_get_or_default 'behavior.keep_going_on_error' true)" == "true" ]]; then
            "$fn" || log_err "  ${c} failed, continuing"
        else
            "$fn" || die "${c} failed"
        fi
    elif [[ "$c" == "cleanup" ]]; then
        cleanup_old
    else
        log_err "  unknown check: $c"
    fi
done

cleanup_old

write_report

log_info "done. alerts emitted: ${#ALERTS_BUFFER[@]}"
if [[ ${#ALERTS_BUFFER[@]} -gt 0 ]]; then
    exit 2
else
    exit 0
fi
