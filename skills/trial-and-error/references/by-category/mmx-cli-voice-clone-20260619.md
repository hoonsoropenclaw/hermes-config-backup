# MMX-CLI Voice Clone — 缺口識別 (2026-06-19)

## 缺口分級：D2（識別 + 原理理解）

**Why D2 not D3**: voice clone 需要上傳音頻 sample（由用戶提供），本 cycle 無法獨立完成 D3 全流程。

## 狀態：mmx-cli 無 voice clone 子命令

`mmx-cli` speech 子命令只有：
- `speech synthesize` — 基本 TTS（已 document）
- `speech generate` — 基本 TTS（alias）
- `speech voices` — 列出可用 voice ID

**缺少**：`voice-clone`、`voice_upload`、`file-upload` 等子命令。

Voice clone 必須走 MiniMax API 直接呼叫。

---

## Voice Cloning API 原理（從 platform.minimax.io 文件學習）

### 流程（三步）

**Step 1: 上傳音頻 sample**
- Endpoint: `POST /v1/files/upload`
- 格式: mp3, m4a, wav
- 時長: 10 秒 ~ 5 分鐘
- 大小: ≤ 20 MB
- 取得 `file_id`（integer）

**Step 2: Clone 聲音**
- Endpoint: `POST /v1/voice_clone`
- 必需欄位:
  - `file_id`: 上一步取得的 ID
  - `voice_id`: 自訂名稱（8-256 字，英文開頭，含 `-`_）
  - `model`: `speech-2.8-hd`（推薦）
- 選用:
  - `clone_prompt`: 含 `prompt_audio`（<8s sample）+ `prompt_text`（轉寫）
  - `accuracy`: 相似度閾值（default 0.7）
  - `need_noise_reduction`: 降噪
  - `need_volume_normalization`: 音量標準化
- 回應: 含 `demo_audio` URL（可預覽）

**Step 3: 使用 Clone 的聲音合成**
- `POST /v1/t2a_v2`（t2a = text to audio）
- `voice_id` 欄位填入 Step 2 的自訂名稱

### ⚠️ 重要限制

- **7 天過期**: cloned voice 7 天未使用會被系統刪除
- **唯一性**: `voice_id` 不可重複
- **clone_prompt 強烈建議**: 不提供則準確度低，容易音色漂移
- **付費**: 依據 `usage_characters` 計費（T2A pricing）

---

## 現有 mmx-cli speech 驗證結果（2026-06-19）

### 已驗證可用
- `Chinese (Mandarin)_News_Anchor` — exit 0, 127KB for ~15 Chinese chars ✅
- `English_expressive_narrator` — exit 0, 已知可用
- 完整 voice list: 50+ voices，含 8 個 Chinese (Mandarin) voices

### mmx-cli 語法（已更新）
```bash
# 永遠用 npx -y mmx-cli，勿直接 mmx（不在 PATH）
npx -y mmx-cli speech voices --api-key "$KEY" --quiet
npx -y mmx-cli speech synthesize \
  --text "您好，面試通知。" \
  --voice "Chinese (Mandarin)_News_Anchor" \
  --out /tmp/tts.mp3 \
  --api-key "$KEY" --quiet
```

---

## 學校 HR 應用場景

若用戶需要語音面試通知（候選人聽而非讀）：
1. **基本 TTS 即可滿足**：`Chinese (Mandarin)_News_Anchor` 或 `Chinese (Mandarin)_Reliable_Executive`
2. **進階需求（自訂音色）**: 需要用戶提供錄音 sample → 上傳 → clone → 使用
3. **替代方案**: 若只需要通知訊息，直接用 Hermes `text_to_speech` tool（更簡單）

---

## If→Then

**If** 用戶需要語音面試通知且要求特定音色 **Then** 先嘗試內建 `Chinese (Mandarin)_News_Anchor`，若用戶堅持自訂音色再走 voice clone API

**If** 需要語音 clone 但 mmx-cli 沒有 `voice-clone` 子命令 **Then** 需直接呼叫 MiniMax REST API:
1. `POST /v1/files/upload` → 拿 `file_id`
2. `POST /v1/voice_clone` → 拿 `voice_id`
3. `POST /v1/t2a_v2` → 合成音頻
4. ⚠️ 警告用戶：cloned voice 7 天過期

---

## 待驗證（需要用戶提供音頻 sample）

- 上傳音頻 sample 到 MiniMax API 是否需要特殊格式轉換
- Chinese voice clone 效果（英文語料 clone 成中文語音是否音色保持）
- 學校 HR 情境下語音通知 vs 文字通知的實際需求強度
