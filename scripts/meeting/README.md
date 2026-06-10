# 會議紀錄 AI 生成系統

## 📁 腳本說明

| 檔案 | 功能 |
|------|------|
| `audio_transcriber.py` | 音訊轉文字（支援 Whisper API / 本地模型） |
| `meeting_summarizer.py` | AI 摘要生成（發言人分析、決策追蹤） |
| `minutes_template.py` | 會議紀錄範本（Markdown / HTML / JSON） |
| `meeting_minutes_generator.py` | 整合主腳本（完整流程） |

## 🚀 使用方式

### 1. 音訊轉文字（獨立使用）

```bash
# 本地 Whisper 模型（需安裝：pip install openai-whisper）
python audio_transcriber.py recording.mp3 -o transcript.txt

# 使用 OpenAI Whisper API
export OPENAI_API_KEY="your-key"
export WHISPER_API_MODE="1"
python audio_transcriber.py recording.mp3 -o transcript.txt -m whisper-1
```

### 2. AI 摘要生成（獨立使用）

```bash
export OPENAI_API_KEY="your-key"
python meeting_summarizer.py transcript.txt -o summary.json \
    --title "校務會議" --datetime "2026-05-26 14:00" \
    --attendees "校長,主任,組長"
```

### 3. 產生會議紀錄範本

```bash
# 標準格式
python minutes_template.py -o minutes.md --template standard

# 學校行政格式（台灣教育體制適用）
python minutes_template.py -o school_minutes.md --template school

# 公務機關正式格式
python minutes_template.py -o formal_minutes.md --template formal

# 快速簡短格式
python minutes_template.py -o brief_minutes.md --template brief

# 產生範例
python minutes_template.py --sample -o sample.md
```

### 4. 完整流程（整合）

```bash
export OPENAI_API_KEY="your-key"
python meeting_minutes_generator.py recording.mp3 \
    --title "111學年度校務會議" \
    --datetime "2026-05-26 14:00" \
    --location "會議室A" \
    --chair "校長 張大明" \
    --attendees "各處室主任,年級組長" \
    -o ./output
```

## 📋 會議紀錄範本格式

### 標準格式 (standard)
- 包含：議程、摘要、討論事項、決議事項、待辨事項、下次會議

### 學校行政格式 (school) - 台灣教育體制
- 報告事項（各處室）
- 討論提案
- 臨時動議
- 主席結論
- 工作追蹤表格

### 正式格式 (formal) - 公務機關
- 壹、會議摘要
- 貳、討論事項及決議
- 叁、追蹤事項

### 簡短格式 (brief)
- 快速會議記錄

## 🔧 安裝需求

```bash
# Whisper（本地模型）
pip install openai-whisper

# OpenAI SDK
pip install openai

# 或使用 LiteLLM（統一的 LLM 介面）
pip install litellm
```

## 📊 輸出格式

```
output/
├── transcript_20260526_143000.txt   # 文字稿
├── meeting_20260526_143000.md       # 會議紀錄 (Markdown)
├── meeting_20260526_143000.html     # 會議紀錄 (HTML)
└── meeting_20260526_143000.json     # 完整資料 (JSON)
```

## 💡 擴展建議

1. **LINE Bot 整合**：將會議紀錄自動發送到 LINE 群組
2. **Google Docs 整合**：直接匯出到 Google 文件
3. **行事曆整合**：自動建立下次會議提醒
4. **多發言人識別**：使用 speaker diarization 技術
5. **即時轉錄**：結合即時語音辨識 API