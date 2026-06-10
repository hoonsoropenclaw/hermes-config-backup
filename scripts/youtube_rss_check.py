#!/usr/bin/env python3
"""
YouTube 新影片抓取 + 字幕摘要 + Obsidian 輸出
==================================================

完整 pipeline：
1. 從 RSS 抓頻道新影片（不需 OAuth）
2. 抓每支影片的 auto-gen 字幕（不需登入）
3. 餵給 LLM（本地 ollama qwen2.5:1.5b 或外部 API）做摘要
4. 輸出結構化 Markdown 筆記到 Obsidian vault（含封面圖）
5. 自動同步到 RAG 索引

**特性**：
- 不需瀏覽器、不需登入（N100 headless 友善）
- 字幕抓失敗時 graceful degradation（只寫 metadata）
- 支援 LLM 切換：本地 ollama / Gemini API / OpenAI API
- 自動把輸出資料夾加進 RAG 索引

**用法**：
    # 預設：用本地 qwen2.5:1.5b 摘要 + 過去 24 小時
    python3 youtube_rss_check.py --hours 24 --output ~/AutoLearningKnowledge/youtube/

    # 用 Gemini API 摘要
    python3 youtube_rss_check.py --llm gemini --hours 24

    # 不用 LLM（只寫 metadata）
    python3 youtube_rss_check.py --no-llm

    # 完整流程（含 RAG 索引）
    python3 youtube_rss_check.py --hours 24 --index-rag

**環境**：
- Python 3.11+ (需要 youtube-transcript-api、ollama Python client、requests)
- ollama 已跑（qwen2.5:1.5b 模型已 pull）
- 或設定 GEMINI_API_KEY env var

**更新日期**：2026-06-07（加上字幕抓取 + LLM 摘要 pipeline）
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# ────────────────────────────────────────
# 常數
# ────────────────────────────────────────
SECRETS_FILE = os.path.expanduser("~/.local/share/hermes/secrets/youtube_client.json")
CHANNELS_FILE = os.path.expanduser("~/.hermes/youtube_channels.json")
OBSIDIAN_VAULT = os.path.expanduser("~/AutoLearningKnowledge/youtube")
RAG_MAIN_PY = os.path.expanduser("~/.hermes/rag/rag_system/main.py")
PYTHON312 = "/usr/bin/python3.12"
OLLAMA_MODEL = "qwen2.5:1.5b"
GEMINI_MODEL = "gemini-2.0-flash-exp"

# ────────────────────────────────────────
# RSS 抓取
# ────────────────────────────────────────

def fetch_rss(channel_id, timeout=8):
    url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.content if resp.status_code == 200 else None
    except Exception as e:
        print(f"  ⚠️  RSS 抓 {channel_id} 失敗: {e}")
        return None


def parse_atom(xml_bytes):
    import xml.etree.ElementTree as ET
    ATOM = '{http://www.w3.org/2005/Atom}'
    try:
        root = ET.fromstring(xml_bytes)
    except:
        return []
    entries = []
    for entry in root.findall(f'{ATOM}entry'):
        title_el = entry.find(f'{ATOM}title')
        link_el = entry.find(f'{ATOM}link')
        pub_el = entry.find(f'{ATOM}published')

        title = title_el.text if title_el is not None else '?'
        link = link_el.attrib.get('href', '?') if link_el is not None else '?'
        pub = pub_el.text if pub_el is not None else ''

        m = re.search(r'v=([A-Za-z0-9_-]+)', link)
        video_id = m.group(1) if m else ''

        entries.append({
            'title': title,
            'link': link,
            'published': pub,
            'video_id': video_id,
        })
    return entries


# ────────────────────────────────────────
# 字幕抓取
# ────────────────────────────────────────

def fetch_transcript(video_id, languages=None):
    """抓影片字幕。失敗回 None。
    languages 預設 ['zh-Hant', 'zh-Hans', 'en']
    """
    if languages is None:
        languages = ['zh-Hant', 'zh-Hans', 'en']
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        return transcript
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        return None
    except Exception as e:
        # 包含所有其他例外（網路、JSON 解析等）
        return None


def transcript_to_text(transcript):
    """把 FetchedTranscript 物件轉成純文字"""
    return ' '.join([snippet.text for snippet in transcript])


def transcript_with_timestamps(transcript, max_chars=8000):
    """保留時間戳的字幕（給 LLM 看的版本）"""
    lines = []
    total = 0
    for snippet in transcript:
        ts = int(snippet.start)
        mm, ss = divmod(ts, 60)
        line = f"[{mm:02d}:{ss:02d}] {snippet.text}"
        if total + len(line) > max_chars:
            lines.append(f"... (省略 {len(transcript) - len(lines)} 段)")
            break
        lines.append(line)
        total += len(line)
    return '\n'.join(lines)


# ────────────────────────────────────────
# LLM 摘要
# ────────────────────────────────────────

def summarize_with_ollama(text, title="", model=OLLAMA_MODEL):
    """用本地 ollama 摘要"""
    import urllib.request

    # 截斷到合理長度（qwen2.5:1.5b 輸入上限約 8K）
    text = text[:6000]

    prompt = f"""你是 YouTube 影片摘要助手。請根據以下影片字幕（可能含時間軸）製作結構化 Markdown 筆記。

影片標題：{title}

要求：
1. 用繁體中文
2. 結構：## 影片重點 / ## 詳細內容（3-5 個重點帶時間戳）/ ## 我的行動建議
3. 簡潔（總長 300-500 字）
4. 如果字幕很技術性，重點放在「這影片在解決什麼問題、用什麼方法」

字幕：
{text}

請直接輸出 Markdown（不要前言）："""

    try:
        req = urllib.request.Request(
            'http://localhost:11434/api/generate',
            data=json.dumps({
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3, 'num_predict': 1024},
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get('response', '').strip()
    except Exception as e:
        return f"❌ ollama 摘要失敗: {e}"


def summarize_with_gemini(text, title="", model=GEMINI_MODEL):
    """用 Gemini API 摘要"""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return "❌ 沒設 GEMINI_API_KEY / GOOGLE_API_KEY 環境變數"

    text = text[:12000]  # Gemini 支援更長

    prompt = f"""你是 YouTube 影片摘要助手。請根據以下影片字幕（可能含時間軸）製作結構化 Markdown 筆記。

影片標題：{title}

要求：
1. 用繁體中文
2. 結構：## 影片重點 / ## 詳細內容（3-5 個重點帶時間戳）/ ## 我的行動建議
3. 簡潔（總長 300-500 字）
4. 如果字幕很技術性，重點放在「這影片在解決什麼問題、用什麼方法」
5. 標出影片中**提到的關鍵工具/指令/設定**（如果有）

字幕：
{text}

請直接輸出 Markdown（不要前言）："""

    try:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
        resp = requests.post(
            url,
            json={
                'contents': [{'parts': [{'text': prompt}]}],
                'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 2048},
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return f"❌ Gemini 摘要失敗: {e}"


# ────────────────────────────────────────
# Obsidian 輸出
# ────────────────────────────────────────

def slugify(s):
    """產生安全檔名"""
    s = re.sub(r'[\\/:*?"<>|]', '-', s)
    s = re.sub(r'\s+', '-', s)
    return s[:80]


def make_obsidian_note(channel, video, transcript, summary, output_dir):
    """產生 Obsidian 格式 .md 檔"""
    title = video['title']
    video_id = video['video_id']
    pub = video['published']
    link = video['link']
    today = datetime.now().strftime('%Y-%m-%d')

    has_transcript = transcript is not None
    has_summary = summary and not summary.startswith('❌')

    # 封面圖
    cover = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    cover_hq = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    # 處理 title 跳脫（f-string 不能用 backslash，預先處理）
    safe_title = title.replace('"', '\\"')

    # 字幕區塊
    transcript_section = ""
    if has_transcript:
        ts_text = transcript_with_timestamps(transcript, max_chars=4000)
        transcript_section = f"""

## 📝 原始字幕（含時間戳）

> 完整字幕存於 `{video_id}.srt`（如需要可另外存檔）

```
{ts_text}
```
"""
    else:
        transcript_section = """

## 📝 原始字幕

> ⚠️ **此影片沒有可抓取的字幕**（可能是 Shorts、影片擁有者關閉、或無 auto-generated CC）
> 標題與 metadata 已記錄，內容需要手動觀看補充
"""

    # 摘要區塊
    summary_section = ""
    if has_summary:
        summary_section = f"\n## 🤖 AI 摘要（{('Gemini' if 'Gemini' in str(type(summary)) else '本地 qwen2.5') }）\n\n{summary}\n"
    elif not has_transcript:
        summary_section = "\n## 🤖 AI 摘要\n\n> 跳過（無字幕）\n"

    # Frontmatter（先組好字串，避免 f-string 內 backslash/quote 限制）
    status_value = 'complete' if has_summary else ('partial' if has_transcript else 'metadata-only')
    frontmatter = (
        '---\n'
        f'title: "{safe_title}"\n'
        f'channel: {channel}\n'
        f'published: {pub}\n'
        f'video_id: {video_id}\n'
        f'link: {link}\n'
        'tags: [youtube, video]\n'
        f'date_captured: {today}\n'
        f'has_transcript: {has_transcript}\n'
        f'has_summary: {has_summary}\n'
        f'status: {status_value}\n'
        '---\n\n'
    )

    # 完整內容
    content = f"""{frontmatter}# {title}

![{title}]({cover})

**頻道**：{channel}
**發布**：{pub}
**連結**：[{link}]({link})

## 📊 元資訊

| 欄位 | 值 |
|------|-----|
| 影片 ID | `{video_id}` |
| 頻道 | {channel} |
| 發布時間 | {pub} |
| 原始連結 | [{link}]({link}) |
| 高畫質封面 | ![封面]({cover}) |
| 縮圖 (HQ) | ![HQ]({cover_hq}) |
| 有字幕 | {'✅' if has_transcript else '❌'} |
| 有 AI 摘要 | {'✅' if has_summary else '❌'}
{summary_section}{transcript_section}
## 我的筆記

<!-- 在此貼上你的觀看筆記 -->

## 參考連結

- 原始影片：{link}
- 高畫質封面：{cover}
- 頻道 RSS：`https://www.youtube.com/feeds/videos.xml?channel_id=...`
"""
    return content


# ────────────────────────────────────────
# RAG 索引
# ────────────────────────────────────────

def index_to_rag(md_file):
    """把單個 .md 加進 RAG 索引"""
    try:
        result = subprocess.run(
            [PYTHON312, RAG_MAIN_PY, 'add', md_file],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except Exception as e:
        return False


# ────────────────────────────────────────
# 主流程
# ────────────────────────────────────────

def get_channels(args):
    if args.channels_file:
        with open(args.channels_file) as f:
            return json.load(f)
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE) as f:
            return json.load(f)
    print(f"❌ 找不到頻道清單，請跑 --oauth 拿訂閱")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='YouTube RSS + 字幕 + LLM 摘要 + Obsidian 輸出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--hours', type=int, help='只處理過去 N 小時的新影片')
    parser.add_argument('--max', type=int, default=3, help='每頻道最多處理幾支')
    parser.add_argument('--channels-file', help='本地頻道清單 JSON')
    parser.add_argument('--output', default=OBSIDIAN_VAULT, help='Obsidian 輸出目錄')
    parser.add_argument('--llm', choices=['ollama', 'gemini', 'none'], default='none', help='LLM 選擇（預設 none：只抓字幕不摘要，要摘要要手動加 --llm）')
    parser.add_argument('--no-llm', action='store_true', help='跳過 LLM 摘要（只用字幕）')
    parser.add_argument('--index-rag', action='store_true', help='把輸出加進 RAG 索引')
    parser.add_argument('--limit', type=int, default=3, help='測試用：只跑前 N 支')
    args = parser.parse_args()

    if args.no_llm:
        args.llm = 'none'

    # 1. 拿頻道
    channels = get_channels(args)
    print(f"📺 {len(channels)} 個頻道")

    # 2. 抓新影片
    cutoff = None
    if args.hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    all_videos = []
    for c in channels:
        name = c.get('name', '?')
        cid = c.get('channel_id', '?')
        xml = fetch_rss(cid)
        if not xml:
            continue
        entries = parse_atom(xml)
        # 時間過濾
        if cutoff:
            fresh = []
            for e in entries:
                if not e['published']:
                    continue
                try:
                    dt = datetime.fromisoformat(e['published'].replace('Z', '+00:00'))
                    if dt >= cutoff:
                        fresh.append(e)
                except:
                    fresh.append(e)  # parse 失敗保留
            entries = fresh
        for e in entries[:args.max]:
            e['channel'] = name
            all_videos.append(e)

    # 測試模式：限前 N 支
    if args.limit and len(all_videos) > args.limit:
        print(f"⚠️  測試模式：只跑前 {args.limit} 支（總共 {len(all_videos)} 支）")
        all_videos = all_videos[:args.limit]

    print(f"🔍 要處理 {len(all_videos)} 支影片")

    if not all_videos:
        print("📭 沒有新影片")
        return

    # 3. 抓字幕 + 摘要 + 寫檔
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.path.join(args.output, today)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    print(f"📁 輸出到: {output_dir}")

    success = 0
    failed = 0

    for v in all_videos:
        title = v['title']
        video_id = v['video_id']
        channel = v['channel']
        print(f"\n--- {channel}: {title[:50]}... ---")

        # 抓字幕
        transcript = None
        if video_id:
            transcript = fetch_transcript(video_id)
            if transcript:
                print(f"  ✅ 字幕: {len(transcript)} 段")
            else:
                print(f"  ⚠️  無字幕")

        # LLM 摘要
        summary = None
        if args.llm != 'none' and transcript:
            text = transcript_to_text(transcript)
            if args.llm == 'gemini':
                print(f"  🤖 Gemini 摘要中...")
                summary = summarize_with_gemini(text, title=title)
            else:
                print(f"  🤖 ollama 摘要中...")
                summary = summarize_with_ollama(text, title=title)
            if summary and not summary.startswith('❌'):
                print(f"  ✅ 摘要: {len(summary)} 字")
            else:
                print(f"  ⚠️  摘要失敗: {summary[:100] if summary else 'None'}")

        # 寫 .md
        content = make_obsidian_note(channel, v, transcript, summary, output_dir)
        slug = slugify(f"{channel}__{title}")
        md_file = os.path.join(output_dir, f"{slug}.md")
        with open(md_file, 'w') as f:
            f.write(content)
        print(f"  💾 {os.path.basename(md_file)}")
        success += 1

        # RAG 索引
        if args.index_rag:
            if index_to_rag(md_file):
                print(f"  📥 RAG indexed")
            else:
                print(f"  ⚠️  RAG index 失敗")

    print(f"\n{'=' * 60}")
    print(f"✅ 完成: {success} 支影片 → {output_dir}")
    if args.index_rag:
        print(f"   全部已加入 RAG 索引")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
