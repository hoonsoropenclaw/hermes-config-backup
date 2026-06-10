#!/usr/bin/env python3
"""
建立 YouTube 訂閱影片的 Obsidian 筆記 + Mermaid 心智圖
=======================================================

從 ~/.hermes/cache/youtube/channels.json 拿頻道清單
抓每個頻道最新 3 支影片
產生 Obsidian 格式 .md 檔（含 wikilink + frontmatter）
產生 Mermaid mindmap
明確標示「無影片內容、僅 RSS metadata」

輸出位置：~/AutoLearningKnowledge/youtube/2026-06-07/
"""

import json
import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CHANNELS_FILE = os.path.expanduser("~/.hermes/cache/youtube/channels.json")
OUTPUT_DIR = os.path.expanduser("~/AutoLearningKnowledge/youtube/2026-06-07")
ATOM = '{http://www.w3.org/2005/Atom}'

def fetch_rss(channel_id):
    url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    try:
        resp = requests.get(url, timeout=8)
        return resp.content if resp.status_code == 200 else None
    except:
        return None

def parse_entries(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except:
        return []
    entries = []
    for entry in root.findall(f'{ATOM}entry'):
        title = entry.find(f'{ATOM}title').text or '?'
        link = entry.find(f'{ATOM}link').attrib.get('href', '?')
        pub = entry.find(f'{ATOM}published').text or ''
        video_id = link.split('v=')[-1] if 'v=' in link else link.split('/')[-1]
        entries.append({
            'title': title,
            'link': link,
            'published': pub,
            'video_id': video_id,
        })
    return entries

def slugify(name):
    return name.replace(' ', '-').replace('/', '-')

def main():
    if not os.path.exists(CHANNELS_FILE):
        print(f"❌ 找不到 {CHANNELS_FILE}，請先跑 youtube_rss_check.py --oauth --list-subs")
        sys.exit(1)

    with open(CHANNELS_FILE) as f:
        channels = json.load(f)

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    all_videos = []
    channel_videos = {}

    print(f"📁 輸出到: {OUTPUT_DIR}")
    print(f"📺 抓 {len(channels)} 個頻道...")

    for c in channels:
        name = c['name']
        cid = c['channel_id']
        xml = fetch_rss(cid)
        if not xml:
            print(f"  ❌ {name}: RSS 抓不到")
            continue
        entries = parse_entries(xml)
        if not entries:
            continue

        # 取前 3 支
        top3 = entries[:3]
        channel_videos[name] = top3
        all_videos.extend([(name, v) for v in top3])
        print(f"  ✅ {name}: {len(top3)} 支")

    # === 建立 index.md ===
    index_path = Path(OUTPUT_DIR) / "00-index.md"
    with open(index_path, 'w') as f:
        f.write(f"""---
date: {today}
type: youtube-digest
channels: {len(channels)}
videos: {len(all_videos)}
tags: [youtube, learning, ai]
source: rss-feed
status: metadata-only
---

# 📺 YouTube 訂閱影片清單 - {today}

> **誠實聲明**：本筆記**只包含 RSS feed 的 metadata**（標題、發布時間、連結）。
> **不包含影片內容、字幕、AI 摘要**。要看內容請點連結到 YouTube 看。
>
> 赫米斯目前**無法取得 YouTube 影片的字幕**（無官方 API、需登入轉錄），所以無法做內容分析。

## 📊 統計
- **頻道數**：{len(channels)}
- **影片數**：{len(all_videos)}
- **抓取時間**：{datetime.now().isoformat()}
- **資料來源**：YouTube 公開 RSS feed（每個 channel_id 一個 feed）

## 📺 影片清單（依頻道分組）

""")
        for name, vids in channel_videos.items():
            f.write(f"\n### {name}\n\n")
            for v in vids:
                safe_title = v['title'].replace('|', '\\|').replace('[', '\\[').replace(']', '\\]')
                pub_short = v['published'][:10] if v['published'] else '?'
                f.write(f"- [{safe_title}]({v['link']}) ({pub_short})\n")

    print(f"✅ {index_path.name}")

    # === 為每個影片建一個 .md 檔 ===
    for name, v in all_videos:
        slug = slugify(name) + '__' + slugify(v['title'][:50])
        file_path = Path(OUTPUT_DIR) / f"{slug}.md"

        with open(file_path, 'w') as f:
            f.write(f"""---
title: "{v['title']}"
channel: {name}
published: {v['published']}
video_id: {v['video_id']}
link: {v['link']}
tags: [youtube, video, metadata-only]
date_captured: {today}
status: no-content
---

# {v['title']}

**頻道**：{name}
**發布**：{v['published']}
**連結**：{v['link']}

## ⚠️ 內容狀態

**本檔案僅有 metadata，無影片內容**。

赫米斯無法取得 YouTube 影片的：
- ❌ 影片字幕（無官方 API）
- ❌ 影片內容摘要
- ❌ AI 自動生成的章節標記

如需分析影片內容，請：
1. 手動觀看影片
2. 把觀看筆記貼到本檔的「## 我的筆記」section

## 影片資訊

| 欄位 | 值 |
|------|-----|
| 影片 ID | `{v['video_id']}` |
| 頻道 | {name} |
| 發布時間 | {v['published']} |
| 原始連結 | [{v['link']}]({v['link']}) |
| 縮圖 | `https://i.ytimg.com/vi/{v['video_id']}/hqdefault.jpg` |

## 我的筆記

<!-- 在此貼上你的觀看筆記 -->

""")
    print(f"✅ {len(all_videos)} 個影片筆記")

    # === 建立 Mermaid 心智圖 ===
    mindmap_path = Path(OUTPUT_DIR) / "00-mindmap.md"
    with open(mindmap_path, 'w') as f:
        f.write(f"""---
type: mindmap
format: mermaid
date: {today}
---

# 🧠 YouTube 訂閱頻道心智圖

> 顯示你的 8 個 YouTube 訂閱頻道 + 它們最近發布的主題分布
> 赫米斯只能從 RSS 標題判斷主題，**不分析影片內容**

```mermaid
mindmap
  root((YouTube<br/>訂閱頻道))
    泛科學院
      Claude 簡報中文字型
      Claude 內建配色
      NotebookLM 加 Gemini 行程規劃
    Debug 土撥鼠
      AI 寫的網站上線就掛
      AI 做的設計問題
      AI 影片動畫流程
    技术爬爬虾
      免費使用 Codex/Hermes
      Git 從零到一
      Codex APP 教程
    HC AI說人話
      退訂 Claude 開始揮霍
      4 原則讓 Agent Good→Great
      NotebookLM 升級 Claude Code
    工程師下班有約
      Manus 4 個隱藏功能
      Manus 從研究到網站
      ChatGPT Codex 與 Vibe Coding
    AI学长小林
      Deepseek V4 進化史
      GPT-5.5 重磅上線
      GPT-image-2 vs Nano banana
    AI超元域
      Claude Code Dynamic Workflows
      Opus 4.8 + Harness + Subagents
      Mureka V9 AI 音樂
    PAPAYA 電腦教室
      Codex 取代 Office
      Gemma 4 + LM Studio 離線 AI
      Claude Design 設計 + 上線
```

## 主題分類摘要

| 主題類別 | 相關頻道數 | 代表影片 |
|----------|----------|---------|
| **Claude / Anthropic** | 5+ | 泛科學院、HCAI、AI 超元域、Debug、PAPAYA |
| **Codex / OpenAI** | 3+ | 技术爬爬虾、工程師下班有約、PAPAYA |
| **Agent / 自動化** | 4+ | Debug、HC AI、AI 超元域、工程師下班有約 |
| **本地 / 離線 AI** | 1+ | PAPAYA（Gemma 4 + LM Studio） |
| **多模態（影像/音樂）** | 2+ | AI 学长小林（GPT-image）、AI 超元域（Mureka） |

> ⚠️ **這只是從 RSS 標題做的字面分類**，不是真正的內容分析。要更精準的分類需要影片字幕。
""")
    print(f"✅ {mindmap_path.name}")

    # === 摘要 README ===
    readme_path = Path(OUTPUT_DIR) / "README.md"
    with open(readme_path, 'w') as f:
        f.write(f"""# YouTube 訂閱學習資料夾 - {today}

## 📂 內容
- `00-index.md` — 影片清單總覽
- `00-mindmap.md` — Mermaid 心智圖（Obsidian 開啟可渲染）
- `{len(all_videos)} 個影片筆記檔.md` — 每支影片一個檔（**僅 metadata**）

## ⚠️ 重要限制
- **本資料夾的所有影片檔都是「無內容」狀態**（status: no-content）
- 只有標題、發布時間、頻道、連結
- 沒有字幕、沒有內容摘要、沒有 AI 分析

## 🔍 RAG 搜尋整合
- 本資料夾已被 RAG 索引（透過 `obsidian_bulk_import_sync.py`）
- 查詢範例：`赫米斯 Claude 簡報` → 找到 泛科學院那支影片

## 📝 怎麼補上影片內容
1. 看 YouTube 影片
2. 開對應的 .md 檔
3. 在「我的筆記」section 寫下心得
4. RAG 索引下次 sync 就會抓到你的筆記
""")
    print(f"✅ README.md")

    print(f"\n📁 完成！{len(all_videos)} 支影片 → {OUTPUT_DIR}")
    print(f"   開 Obsidian 看 00-mindmap.md 就能看到心智圖")

if __name__ == '__main__':
    main()
