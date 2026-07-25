# mmx-cli Speech/TTS 踩坑彙整 (2026-06-17 驗證)

本檔收錄「從 hermes session 透過 `mmx-cli` 跑 speech synthesis (TTS)」會踩到的雷。

---

## 1. `mmx` 不在 PATH,要用 `npx -y mmx-cli`

**症狀**: 直接跑 `mmx auth status` 或 `mmx speech synthesize` → `command not found`。

**根因**: `mmx-cli` 全域安裝在 `/home/hoonsoropenclaw/.npm-global/lib`，不在系統 PATH。

**正確用法**: 永遠用 `npx -y mmx-cli <command>`。

---

## 2. API key 讀取：不能用 `awk` / `grep` 對 key 名做 regex

**症狀**:
```bash
# 這樣會失敗（awk regex 吃到 `***`）
KEY=$(awk -F= '/^MINIMAX_API_KEY=*** {print $2}' ~/.hermes/.env)
# awk: ... ^ unterminated regexp

# 第一次成功後，後續调用失败（credential 被 cache/汙染）
npx -y mmx-cli speech synthesize ... --api-key "$KEY" --quiet
# {"error": {"code": 3, "message": "No credentials found."}}
```

**根因**: `***` 是赫米斯 token 遮蔽關鍵字，awk/regex 對它的處理導致 pattern 失效。

**正確做法**: 用 Python 讀 key，避免 shell regex。

```python
import subprocess
from pathlib import Path

env_path = Path.home() / '.hermes/.env'
key = None
for line in open(env_path):
    if line.startswith('MINIMAX_API_KEY=***        key = line.strip().split('=', 1)[1]
        break

# 每次新的 subprocess.run call 都用 list 格式，--api-key 作為独立元素
args = ['npx', '-y', 'mmx-cli', 'speech', 'synthesize',
        '--text', 'Hello world',
        '--out', '/tmp/tts.mp3',
        '--api-key', key,  # ← 分開作 list 元素
        '--quiet']
r = subprocess.run(args, capture_output=True, text=True, timeout=60)
```

**驗證**: 每次跑完 `ls -la /tmp/tts_*.mp3` 確認檔案存在且 > 50KB。

---

## 3. API key flag 首次成功後後續失败（credential 狀態問題）

**症狀**: 第一個 TTS call 成功（exit 0，檔案正常），但第二個相同 call 失敗（code 3: No credentials）。

**根因**: 疑似 npx/mmx 在同一 shell session 內部的 credential 解析狀態被汙染（可能是 `***` mask 殘留影響了 mmx 內部狀態）。

**繞法**: 每次 TTS call 用乾淨的 Python subprocess，**不要**在同一次 `execute_code` 裡串聯多個 TTS call，中間夾其他工具會導致 credential 狀態不一致。

```python
# 每次 TTS 生成用獨立的 subprocess.run
def tts_once(text, out_path, voice=None):
    import subprocess
    from pathlib import Path
    key = next((l.split('=',1)[1].strip()
                for l in open(Path.home()/.hermes/.env)
                if l.startswith('MINIMAX_API_KEY=***    args = ['npx', '-y', 'mmx-cli', 'speech', 'synthesize',
                '--text', text, '--out', str(out_path),
                '--api-key', key, '--quiet']
    if voice:
        args.extend(['--voice', voice])
    r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return r
```

**驗證**: TTS 每次生成後立即 `ls -la <out_path>` 確認檔案大小 > 50KB。

---

## 4. `speech synthesize` 可用的 voice 選項

**已驗證可用的 voice**:
- `English_expressive_narrator`（預設，exit 0，檔案 65-77KB for ~10s audio）
- `Male_calm_Narrative`（exit 0，檔案正常）

**不存在的 voice**（未測試但可預期）:
- `English_British_Narrator` — 需要自己列舉

**建議**: 先用 `--voice default` 確認 wired，再用指定 voice。

---

## 5. `speech synthesize` 基本參數

| 參數 | 說明 |
|------|------|
| `--text` | 要轉語音的文字（max 10k chars） |
| `--voice` | voice ID（可用 `mmx speech list-voices` 查） |
| `--speed` | 速度倍率 |
| `--format` | 輸出格式（預設 mp3） |
| `--sample-rate` | 採樣率（預設 32000） |
| `--out` | 輸出檔案路徑 |
| `--api-key` | 必填，用 Python subprocess 不要用 shell variable |
| `--quiet` | 抑制 progress output，stdout 只出檔案路徑 |

**預設輸出格式**: MPEG ADTS, layer III, 128 kbps, 32 kHz, Monaural（MP3）。

---

## 6. `text_to_speech` tool（Hermes 原生）vs `mmx speech synthesize` 選擇

- **Hermes `text_to_speech` tool**: 走內建 provider（MiniMax），**不需要**手動傳 key。適合快速語音轉換、voice memo。
- **`mmx speech synthesize`**: 可控制 voice/speed/format，適合需要特定 voice 或高品質輸出的場景。

**If** 使用者只是說「把這段文字轉語音」→ 用 Hermes 原生 `text_to_speech` tool。
**If** 使用者要指定特定 voice / speed / format → 用 `mmx speech synthesize` + Python subprocess 模式。

---

## If→Then 經驗

**If** 要從 hermes session 跑 TTS (speech synthesis) **Then** 用 Python subprocess + `npx -y mmx-cli speech synthesize`，key 用 `chr()` 構造字串讀取，避免 awk/grep regex 吃到 `***`。
