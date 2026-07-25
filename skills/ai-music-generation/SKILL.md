---
name: ai-music-generation
description: |
  AI 音樂生成 umbrella — 從歌詞寫作到 Suno/HeartMuLa/MiniMax 等多平台的音樂 prompt 工程。
  **Class-level skill** — 涵蓋三個面向：(1) 歌詞寫作工藝（結構、韻律、情緒）、(2) Suno AI prompt 工程、(3) HeartMuLa 開源模型安裝與使用。
  **觸發**：寫歌、歌詞、歌曲創作、改編歌曲、parody、Suno prompt、HeartMuLa、AI 音樂生成。
version: 1.0.0
author: Hermes Agent (curator consolidation 2026-07-04)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [music, songwriting, suno, parody, lyrics, creative, ai-music-generation, heartmula, open-source, suno-alternative]
    triggers: [writing a song, song lyrics, music prompt, suno prompt, parody song, adapting a song, AI music generation, heartmula, open-source music, suno alternative]
---

# AI Music Generation — Class-Level Umbrella

完整 AI 音樂生成指南：從歌詞寫作到多平台 prompt 工程。

## 何時使用

**任一符合即載入**：
- 用戶要寫歌、改編歌曲、parody → 「歌詞寫作工藝」段
- 用戶要在 Suno 上生歌 → 「Suno prompt 工程」段
- 用戶想用開源 / 離線 / Suno 替代方案 → 「HeartMuLa 開源模型」段
- 整體「AI 音樂生成」任務 → 全部內容都在這

---

## 1. 歌詞寫作工藝（原 `songwriting-and-ai-music` 內容）

> 全部是 guideline，不是規則。藝術故意打破規則。對歌曲有幫助的就用、沒幫助的就跳過。

### 1.1 歌曲結構（選一個或自創）

常見骨架 — 混合、修改、或丟掉都可以：

```
ABABCB  Verse/Chorus/Verse/Chorus/Bridge/Chorus    (most pop/rock)
AABA    Verse/Verse/Bridge/Verse (refrain-based)    (jazz standards, ballads)
ABAB    Verse/Chorus alternating                    (simple, direct)
AAA     Verse/Verse/Verse (strophic, no chorus)     (folk, storytelling)
```

六大組件：
- **Intro** — 設定情緒、把聽眾拉進來
- **Verse** — 故事、細節、世界觀
- **Pre-Chorus** — 可選的張力累積
- **Chorus** — 情緒核心、大家記得的部分
- **Bridge** — 岔路、觀點或調性轉換
- **Outro** — 告別、可以呼應或顛覆前面

不需要全部。有些好歌就是一段持續演化的單一結構。結構服務情緒、不倒過來。

### 1.2 韻律、節拍、聲音

**RHYME TYPES**（由緊到鬆）：
- **Perfect**：lean/mean
- **Family**：crate/braid
- **Assonance**：had/glass（同韻母、不同結尾）
- **Consonance**：scene/when（不同韻母、相似結尾）
- **Near/slant**：暗示連結但不鎖死

混合使用。全部 perfect rhyme 會像兒歌、全部 slant rhyme 會顯懶。融合才是本體。

**INTERNAL RHYME**：行內韻、不是只在行尾押。
> "We pruned the lies from bleeding trees / Distilled the storm from entropy"
> — "lies/flies"、"trees/entropy" 創造內部回音

**METER**：重音 vs 非重音的節奏。
- 平行行的音節數一致有助於可唱性
- **重音**比總音節數重要
- 大聲念出來。如果卡到、節奏要改
- 故意破節拍可以創造強調或驚喜

### 1.3 情緒弧線與動態

把歌想成旅程、不是平路。

**ENERGY MAPPING**（粗略、非規定）：
```
Intro: 2-3  |  Verse: 5-6  |  Pre-Chorus: 7
Chorus: 8-9  |  Bridge: varies  |  Final Chorus: 9-10
```

最有效的動態技巧：**CONTRAST**。
- 嘶吼前的低語比單純嘶吼更狠
- 密集前的稀疏、快速前的慢、高前的低
- Drop 只在有 buildup 時有效
- 沉默也是樂器

> "Whisper to roar to whisper" — 從親密開始、堆到全力、再剝回脆弱。抒情、史詩、頌歌都適用。

### 1.4 寫歌詞

**SHOW, DON'T TELL**（通常）：
- ❌ "I was sad"（平淡）
- ✅ "Your hoodie's still on the hook by the door"（活的）

**但有時候** "I give my life" 簡單直白的講反而是力量。

**THE HOOK**：大家記得、哼、複誦的那句。
- 通常是 title 或核心 phrase
- melody + lyric + emotion 對齊時效果最好
- 放在最痛的位置（常常是 chorus 的第一/最後一行）

**PROSODY** — 歌詞和音樂互相支持：
- 穩定感受（解決、平靜）配穩定 melody、perfect rhyme、解決和弦
- 不穩定感受（渴望、懷疑）配遊走 melody、near-rhyme、不解決和弦
- Verse melody 通常低、chorus 走高
- 但服務歌曲的話可以顛倒

**避免**（除非故意）：
- 自動駕駛的陳腔濫調（"heart of gold" 沒賦予就寫）
- 為了押韻強迫字序（"Yoda-speak"）
- 每段一樣的能量（平的動態）
- 把初稿當神聖 — 修改就是創造

### 1.5 Parody 與改編

**THE SKELETON**：先 map 原曲的結構。
- 每行數音節
- 標記押韻格式（ABAB, AABB 等）
- 哪些音節是 STRESSED
- 哪裡有 held/sustained notes

**FITTING NEW WORDS**：
- 對齊原曲相同節拍的重音音節
- 總音節可以 ±1-2 非重音
- 在長音上嘗試對齊原曲的 VOWEL SOUND
  - 原曲 hold "LOOOVE" 用 "oo" 母音，"FOOOD" 比 "LIFE" 更合
- 關鍵位置的單音節替換保持節奏（Crime → Code, Snake → Noose）
- 對著原曲唱新詞 — 卡到就改

**CONCEPT**：
- 概念要夠強才能撐整首歌
- 從 title/hook 開始往外擴
- 先大量生成 raw material（雙關、phrase、意象），再挑最好的塞進結構
- 如果某個位置需要特定一句，反推押韻格式往回設計

**KEEP SOME ORIGINALS**：留幾句原曲或結構可以增加辨識度、讓觀眾感覺連結。

---

## 2. Suno AI Prompt 工程

### 2.1 Style/Genre 描述欄

**FORMULA**（可調整）：
```
Genre + Mood + Era + Instruments + Vocal Style + Production + Dynamics
```

**範例**：
```
❌ "sad rock song"
✅ "Cinematic orchestral spy thriller, 1960s Cold War era, smoky
    sultry female vocalist, big band jazz, brass section with
    trumpets and french horns, sweeping strings, minor key,
    vintage analog warmth"
```

**描述旅程、不要只列類型**：
```
"Begins as a haunting whisper over sparse piano. Gradually layers
in muted brass. Builds through the chorus with full orchestra.
Second verse erupts with raw belting intensity. Outro strips back
to a lone piano and a fragile whisper fading to silence."
```

**TIPS**：
- V4.5+ Style field 支援最多 1,000 字 — 用滿
- **不要寫藝名或商標**。描述聲音而不是歌手。
  - "1960s Cold War spy thriller brass" 而非 "James Bond style"
  - "90s grunge" 而非 "Nirvana-style"
- 有偏好的話指定 BPM 跟 key
- 用 Exclude Styles 欄寫你不想要的
- 意想不到的類型組合可能是寶藏：「bossa nova trap」、「Appalachian gothic」、「chiptune jazz」
- 建立 vocal PERSONA、不只是性別：
  - "A weathered torch singer with a smoky alto, slight rasp, who starts vulnerable and builds to devastating power"

### 2.2 Metatags（歌詞欄內 `[brackets]`）

**STRUCTURE**：
```
[Intro] [Verse] [Verse 1] [Pre-Chorus] [Chorus]
[Post-Chorus] [Hook] [Bridge] [Interlude]
[Instrumental] [Instrumental Break] [Guitar Solo]
[Breakdown] [Build-up] [Outro] [Silence] [End]
```

**VOCAL PERFORMANCE**：
```
[Whispered] [Spoken Word] [Belted] [Falsetto] [Powerful]
[Soulful] [Raspy] [Breathy] [Smooth] [Gritty]
[Staccato] [Legato] [Vibrato] [Melismatic]
[Harmonies] [Choir] [Harmonized Chorus]
```

**DYNAMICS**：
```
[High Energy] [Low Energy] [Building Energy] [Explosive]
[Emotional Climax] [Gradual swell] [Orchestral swell]
[Quiet arrangement] [Falling tension] [Slow Down]
```

**GENDER**：`[Female Vocals]` `[Male Vocals]`

**ATMOSPHERE**：
```
[Melancholic] [Euphoric] [Nostalgic] [Aggressive]
[Dreamy] [Intimate] [Dark Atmosphere]
```

**SFX**：`[Vinyl Crackle]` `[Rain]` `[Applause]` `[Static]` `[Thunder]`

Style 欄 跟 歌詞欄 都放 tag 加強效果。每段 5-8 個 tag 上限 — 太多會混淆 AI。不要自相矛盾（[Calm] + [Aggressive] 在同一段）。

### 2.3 Custom Mode

- 認真做一定要 Custom Mode（Style + Lyrics 分開）
- Lyrics 欄上限 ~3,000 字（~40-60 行）
- 一定要加 structural tags — 沒有時 Suno 預設會是平的 verse/chorus/verse、沒有情緒弧

### 2.4 Phonetic Tricks for AI Singers

AI vocalists 不會「讀」、只會「發音」。幫助它們：

**PHONETIC RESPELLING**：
- 照聲音拼："through" → "thru"
- 專有名詞失敗率最高 — 提早測
- "Nous" → "Noose"（強制正確發音）
- 連字號引導音節："Re-search"、"bio-engineering"

**DELIVERY CONTROL**：
- 全大寫 = 大聲、激烈
- 母音延長："lo-o-o-ove" = sustained/melisma
- 省略號："I... need... you" = dramatic pauses
- 連字號拉伸："ne-e-ed" = emotional stretch

**必做**：
- 拼出數字："24/7" → "twenty four seven"
- 間隔縮寫："AI" → "A I" 或 "A-I"
- 在短 30 秒片段測試專有名詞 / 不尋常字
- 一旦生成、發音就烤進去了 — 修正要在歌詞階段

### 2.5 Workflow

1. 先寫概念/hook — 情緒核心是什麼？
2. 改編的話、map 原曲結構（音節、韻、重音）
3. 生成 raw material — 在結構化前自由 brainstorm
4. 把 lyrics 草稿塞進結構
5. 大聲唸/唱 — 抓卡到的地方、修節奏
6. 寫 Suno style description — 畫出動態旅程
7. 在 lyrics 加 metatags 引導表演
8. 至少生 3-5 個變化 — 把它們當錄音 takes
9. 挑最好的、用 Extend/Continue 在有潛力的段落加長
10. 意外的好東西就留著

**預期**：~3-5 次生成才會有 1 個好結果。修改是常態。Extension 時 style 可能漂移 — 重新聲明 genre/mood。

---

## 3. HeartMuLa 開源模型（原 `heartmula` 內容）

> HeartMuLa 是 Apache-2.0 開源音樂 foundation model 系列，從 lyrics + tags 生成音樂，多語言支援。完整 Suno 替代品。包含：
> - **HeartMuLa** — 音樂語言模型（3B/7B）從 lyrics + tags 生成
> - **HeartCodec** — 12.5Hz 音樂 codec、高保真重建
> - **HeartTranscriptor** — Whisper-based lyrics transcription
> - **HeartCLAP** — 音頻-文字對齊模型

### 3.1 硬體需求

- **Minimum**：8GB VRAM + `--lazy_load true`（依序載入/卸載模型）
- **Recommended**：16GB+ VRAM 舒服用單 GPU
- **Multi-GPU**：`--mula_device cuda:0 --codec_device cuda:1` 切兩 GPU
- 3B 模型 lazy_load 峰值 ~6.2GB VRAM

### 3.2 安裝步驟

```bash
# 1. Clone
cd ~/
git clone https://github.com/HeartMuLa/heartlib.git
cd heartlib

# 2. venv（需要 Python 3.10）
uv venv --python 3.10 .venv
. .venv/bin/activate
uv pip install -e .

# 3. 修依賴衝突（2026-02 必要）
uv pip install --upgrade datasets
uv pip install --upgrade transformers

# 4. Patch source code（transformers 5.x 必要）

# Patch 1 - RoPE cache fix in src/heartlib/heartmula/modeling_heartmula.py
# 在 HeartMuLa 類的 setup_caches 方法，在 reset_caches try/except 後、with device: 前：
for module in self.modules():
    if isinstance(module, Llama3ScaledRoPE) and not module.is_cache_built:
        module.rope_init()
        module.to(device)

# Patch 2 - HeartCodec loading fix in src/heartlib/pipelines/music_generation.py
# 所有 HeartCodec.from_pretrained() calls 加 ignore_mismatched_sizes=True

# 5. 下載 checkpoints
hf download --local-dir './ckpt' 'HeartMuLa/HeartMuLaGen'
hf download --local-dir './ckpt/HeartMuLa-oss-3B' 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'
hf download --local-dir './ckpt/HeartCodec-oss' 'HeartMuLa/HeartCodec-oss-20260123'
```

### 3.3 GPU / CUDA

預設用 CUDA（`--mula_device cuda --codec_device cuda`）。

- 內建 `torch==2.4.1` 已含 CUDA 12.1
- `torchtune` 可能顯示 `0.4.0+cpu` — 這只是 package metadata，仍走 CUDA via PyTorch
- 驗證 GPU 有用：看 "CUDA memory" log（如 "CUDA memory before unloading: 6.20 GB"）
- **沒 GPU？** 用 `--mula_device cpu --codec_device cpu`，但**極慢**（30-60+ 分鐘一首、GPU 約 4 分鐘）。CPU 模式也要 ~12GB+ RAM。沒有 NVIDIA GPU 建議用 Google Colab T4 免費層、Lambda Labs、或 https://heartmula.github.io/ 線上 demo

### 3.4 基本使用

```bash
cd heartlib
. .venv/bin/activate
python ./examples/run_music_generation.py \
  --model_path=./ckpt \
  --version="3B" \
  --lyrics="./assets/lyrics.txt" \
  --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" \
  --lazy_load true
```

**Tags**（逗號分隔、無空格）：
```
piano,happy,wedding,synthesizer,romantic
rock,energetic,guitar,drums,male-vocal
```

**Lyrics**（用 bracket structural tags）：
```
[Intro]
[Verse]
Your lyrics here...
[Chorus]
Chorus lyrics...
[Bridge]
Bridge lyrics...
[Outro]
```

### 3.5 關鍵參數

| 參數 | 預設 | 說明 |
|------|------|------|
| `--max_audio_length_ms` | 240000 | 最長長度（240s = 4 min） |
| `--topk` | 50 | Top-k sampling |
| `--temperature` | 1.0 | Sampling temperature |
| `--cfg_scale` | 1.5 | Classifier-free guidance scale |
| `--lazy_load` | false | 依序載入/卸載模型（省 VRAM） |
| `--mula_dtype` | bfloat16 | HeartMuLa dtype（bf16 推薦） |
| `--codec_dtype` | float32 | HeartCodec dtype（fp32 推薦、保持品質） |

### 3.6 效能

- RTF (Real-Time Factor) ≈ 1.0 — 4 分鐘的歌約 4 分鐘生成
- 輸出：MP3, 48kHz stereo, 128kbps

### 3.7 Pitfalls

1. **HeartCodec 不要用 bf16** — 會降音質。用 fp32（預設）
2. **Tags 可能被忽略** — 已知 issue（#90）。Lyrics 通常主導；試 tag 順序
3. **macOS 沒有 Triton** — GPU 加速只支援 Linux/CUDA
4. **RTX 5080 不相容** — upstream issues 報告
5. 依賴 pin 衝突需要手動升級 跟 patch（如上）

---

## 4. 平台比較與選擇指南

| 需求 | 平台 |
|------|------|
| 快速、雲端、不想架設本地 | **Suno**（付費、商業友善） |
| 想開源、離線、不想付費、GPU | **HeartMuLa** |
| 只想寫歌詞、不生音樂 | 本 skill 的歌詞工藝段就夠 |
| MiniMax 用戶、想用戶 API | `mmx-cli` skill 的 music generate 命令 |

---

## 5. 教訓（從實戰累積）

- Style field 描述動態 ARC 比列 genre 清單重要得多。"Whisper to roar to whisper" 給 Suno 一張表演地圖
- Parody 留幾句原曲會增加辨識度跟情緒重量 — 觀眾感覺原曲的幽靈
- Bridge 是可以變形意象的位置。用主題的 metaphor 換掉原曲的具體 reference、保留情緒功能（反思、轉折、啟示）
- Hook/tag 位置的單音節替換是保持節奏同時換意義的最乾淨方式
- Style field 寫的 vocal persona 比任何單獨 metatag 影響都大
- 不要被規則束縛。如果某句破節拍但更狠、就留。感覺才是重點。craft serves art

---

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-07-04 | curator 整合：`songwriting-and-ai-music`（歌詞工藝 + Suno prompt）+ `heartmula`（HeartMuLa 開源模型）合併為一個 class-level umbrella skill。原本兩個 skill 歸檔。 |