---
name: stdlib-production-tool-pattern
description: "Pure-stdlib Linux ops tool pattern — no psutil, no requests, no third-party deps. For building production-grade monitoring/automation agents that run on N100/homelab/air-gapped boxes. D3: delivers working tool with tests."
version: 1.0.0
author: hermes
platforms: [linux]
metadata:
  hermes:
    tags: [stdlib, linux, ops, production, n100, monitoring]
    triggers: [linux-monitor, system-automation, homelab-ops, air-gapped]
    proof_sessions: [20260726_044008_36e7d0, 20260728_080012_febe57]
    cycle: 551
---

# stdlib Production Tool Pattern

## When to Use

**Trigger conditions** (any):
- User asks for Linux system monitoring, automation, log analysis
- Target: N100 / homelab / air-gapped / minimal-container (no pip)
- Similar scope: "read /proc → evaluate → emit output"

**Skip** when:
- Cross-platform Windows/macOS required (use psutil)
- Complex network protocols needed (use requests/aiohttp)
- User already has a preferred dep stack

## Pattern Architecture

```
bin/
  tool.py          # CLI orchestrator: argparse + signal handlers + exit codes
  tool_core.py     # Pure functions: collectors + evaluators (NO I/O side effects)
  tool_config.py   # Config loader + strict schema validator
  tool_sink.py     # Alert/log sink (file NDJSON + stderr fallback)
src/toolname/     # if package structure needed
  __init__.py
  core.py
  config.py
  sink.py
  run.py
tests/
  test_unit.py     # pure functions with mocks
  test_config.py   # config validation
  test_sink.py     # file writer + fallback
  test_smoke.py    # end-to-end CLI subprocess
docs/
  ARCHITECTURE.md
  USAGE.md
README.md
examples/
  strict.json
```

## Core Principles

### 1. stdlib Only — Never pip install

Linux exposes everything via `/proc`, `/sys`, `/dev`:

| Needed | stdlib Source |
|--------|--------------|
| CPU % | `/proc/stat` two-sample delta (0.5s gap) |
| Memory | `/proc/meminfo` |
| Load avg | `/proc/loadavg` |
| Disk | `os.statvfs()` or `df -PB1` |
| Processes | `ps -eo pid,user,pcpu,pmem,comm` |
| Log lines | `re` on `tail` output or `journalctl` |
| Auth failures | `re` on `/var/log/auth.log` |
| Network | `/proc/net/dev` |
| Time | `datetime` (not `arrow`, not `pendulum`) |
| HTTP webhook | `urllib.request` |
| Config | `json` (or `yaml` if PyYAML is acceptable) |

**Never**: `psutil`, `requests`, `click`, `typer`, `rich`, `pandas`

### 2. Pure Functions + Thin Orchestrator

Every collector/evaluator is a **pure function**: same inputs → same outputs, zero I/O side effects.

```python
# GOOD — pure
def sample_cpu(proc_root: str = "/proc") -> float:
    t0 = _read_cpu_times(proc_root)
    time.sleep(0.5)
    t1 = _read_cpu_times(proc_root)
    return _compute_pct(t0, t1)

# BAD — hidden I/O in "helper"
def get_cpu():  # what does this touch? Mystery.
    return _helper()  # don't do this
```

The **orchestrator** (`run.py`) is thin (~150-200 lines): it composes core + config + sink into CLI commands. No business logic lives there.

### 3. Append-Only NDJSON for Alerts/Logs

Why NDJSON over SQLite / single JSON / CSV:
- Each line is self-contained → safe to `tail -f | jq`
- Truncation-safe: crash leaves previous lines intact
- Schema evolves per-line (backward-compatible field additions)
- Pipe-friendly: vector, fluentd, logstash all consume NDJSON natively
- No migrations, no locking, no connection strings

```python
def emit_alert(alert: Alert, path: str):
    line = json.dumps(asdict(alert), default=str) + "\n"
    with atomic_append(path) as f:
        f.write(line)
```

### 4. Strict Config Validation — Fail Loud

Config typos are silent production bugs. Strict validator raises on unknown keys:

```python
VALID_THRESHOLD_KEYS = {
    "load1_warn", "load1_crit",
    "mem_used_pct_warn", "mem_used_pct_crit",
    # ...
}

def validate_config(cfg: dict) -> None:
    for key in cfg.get("thresholds", {}):
        if key not in VALID_THRESHOLD_KEYS:
            raise ConfigError(f"Unknown threshold key: {key!r}")
```

**Deep-merge partial overrides** so user only setting `load1_warn` keeps all other defaults:

```python
def deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result
```

### 5. Incremental Log Scanning (Rotation-Safe)

```python
def scan_log_file(path: str, patterns: list[re.Pattern], since_offset: int):
    with open(path, errors="replace") as f:
        f.seek(since_offset)
        matches = []
        for line in f:
            for pat in patterns:
                if pat.search(line):
                    matches.append(line)
        new_offset = f.tell()
    # Detect rotation: file shrank
    size = os.path.getsize(path)
    if new_offset > size:
        new_offset = 0  # rotated, start from beginning
    return matches, new_offset
```

### 6. SIGTERM-Graceful Daemon

```python
def main():
    signal.signal(signal.SIGTERM, _handle_sigterm)
    running = True
    while running:
        try:
            tick()
            time.sleep(INTERVAL)
        except SIGTERM:
            running = False
    print("[tool] draining...")  # visible in journalctl
    drain()
    print("[tool] stopped")
```

Max interrupt latency = `INTERVAL` (default 60s, use 1s for faster response).

### 7. Atomic Writes (No Torn State)

```python
import tempfile, os, json

def atomic_write(path: str, data: dict) -> None:
    dir_ = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(dir=dir_, mode="w", delete=False) as tf:
        json.dump(data, tf, default=str)
        tf.flush()
        os.fsync(tf.fileno())
        os.chmod(tf.name, 0o600)
    os.replace(tf.name, path)  # atomic on POSIX
```

## Exit Code Contract

| Code | Meaning | Use case |
|------|---------|----------|
| 0 | OK — no alerts | cron / timer healthy |
| 1 | WARN — warning threshold breached | optional: treat as warning |
| 2 | CRIT — critical threshold breached | optional: treat as critical |
| 10 | Alerts fired (one-shot check) | cron action without parsing stdout |
| 3 | Internal error / config error | immediate human attention |

Codes 0/1/2 are standard. `10` is intentionally large to avoid collision with `1` (generic error) or `130` (SIGINT).

## Permission Lockdown (CWE-276)

```python
import os
os.umask(0o077)  # at startup — all files inherit this mask

def atomic_write(path, data):
    # ... write to tmp ...
    os.chmod(tmp_path, 0o600)  # defense-in-depth
    os.replace(tmp_path, path)
    os.chmod(path, 0o600)     # repair if widened by parent
```

## Testing Strategy

| Layer | Type | Mocks |
|-------|------|-------|
| Collectors (sample_*) | Unit | Mock `/proc/*` files |
| Evaluators (threshold logic) | Unit | In-memory dataclasses |
| Config validator | Unit | JSON strings |
| Sink (file writer) | Unit | `NamedTemporaryFile` |
| End-to-end CLI | Smoke | `subprocess.run` |

Wall-clock assertions prove concurrency:
```python
async def test_parallel():
    t0 = time.time()
    await asyncio.gather(task_a(), task_b(), task_c())
    elapsed = time.time() - t0
    assert elapsed < 0.6  # serial would be ~0.9
```

## What This Pattern Does NOT Do

- **No remote alerting** (Slack/email) — webhook is the universal adapter
- **No metric persistence** (Prometheus/InfluxDB) — pipe NDJSON to vector
- **No systemd journal native** — reads `/var/log/syslog` (works everywhere)
- **No auto-remediation** — alert fires, human decides

## Build Lessons (L3 from sysmon)

### Lesson 1: Threshold dict keys must match the lookup key
```python
# BAD — thresholds have "warn"/"crit" keys but lookup uses "warning"/"critical"
thresholds = {"cpu_pct": {"warn": 80.0, "crit": 95.0}}
# in evaluator:
if level == "critical":  # "critical" vs "crit" — silent KeyError
    key = "crit"
# FIX: explicit mapping
_lookup = {"warning": "warn", "critical": "crit"}
key = _lookup[level]
```

### Lesson 2: `Alerter.log(level, msg, **fields)` — `level` kwarg collision
```python
# BAD — runner calls alerter.log(level=severity, ...) but level is positional
def log(self, level: str, msg: str, **fields):
    record = {"level": level, "message": msg, **fields}  # level overwritten
# FIX: rename field to alert_level
record = {"alert_level": level, "message": msg, **fields}
```

### Lesson 3: `atomic_write` must tolerate empty files
```python
# BAD — mktemp creates empty file, json.loads("") raises
state = json.loads(Path(path).read_text())
# FIX:
text = Path(path).read_text().strip()
if not text:
    return {}
state = json.loads(text)
```

### Lesson 4: stdlib `df -PB1` is cross-distro cleanest
```bash
df -h      # rounds, GNU-specific columns
df -PB1    # POSIX, bytes, no rounding
```

## Verification Commands

```bash
# Full test suite
python3 -m unittest discover -s tests -p "test_*.py" -v

# End-to-end smoke
./bin/tool.sh --once
echo "exit=$?"

# Force low threshold test
TMPDIR=$(mktemp -d)
cat > $TMPDIR/test.json <<EOF
{"resources": {"interval_seconds": 60, "thresholds": {"load1_warn": 0.01}}}
EOF
./bin/tool.sh --config $TMPDIR/test.json --once
```

## References

- sysmon project: `~/.hermes/projects/learning_1785012006_2/code_workspace/sysmon-tool/` (49 tests, 2222 lines)
- asyncio variant: `~/.hermes/projects/learning_1785196806_6/sysmon/` (13 tests, v0.1.0)
- Proof sessions: `session:cli/20260726_044008_36e7d0`, `session:cli/20260728_080012_febe57`
