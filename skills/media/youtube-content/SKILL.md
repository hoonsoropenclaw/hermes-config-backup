---
name: youtube-content
description: "YouTube transcripts to summaries, threads, blogs."
platforms: [linux, macos, windows]
---

# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

```bash
pip install youtube-transcript-api
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Workflow

1. **Fetch** the transcript using the helper script with `--text-only --timestamps`.
2. **Validate**: confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript. If still empty, tell the user the video likely has transcripts disabled.
3. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
4. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
5. **Verify**: re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.

## Limitations & Known Gotchas

- **YouTube RSS feeds ARE STILL ALIVE (verified 2026-06-07)** — earlier versions of this skill claimed they were discontinued in 2025; **this is WRONG**. The URL `https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxx` still returns 200 with a valid Atom feed (latest ~15 videos per channel). This is the **fastest way to check a specific channel's new videos without OAuth or any tokens**. Example verified working 2026-06:
  ```bash
  curl "https://www.youtube.com/feeds/videos.xml?channel_id=UCATnB3v_NkTTd9iD_4W2A-g"
  # Returns 200 + Atom XML with 泛科學院's latest 15 videos
  ```
  Use RSS when the user wants "what's new on channel X". Skip the entire OAuth flow in that case.
- **YouTube Data API v3 requires OAuth for user-specific data** (subscriptions, watch history, playlists, "my channel"): Unlike most Google APIs, YouTube Data API does not support API key auth for these endpoints. You need:
  - `client_id` + `client_secret` from Google Cloud Console
  - A valid `refresh_token` (obtained via OAuth flow)
  - Use the refresh token to obtain short-lived `access_token` before each API call
  - **Hermes's actual token location**: `~/.hermes/youtube_tokens.json` (mode 600). The `~/.openclaw/workspace/youtube_tokens.json` path mentioned in older versions of this skill is **wrong for this user** — that's OpenClaw (拉斐爾) on the same N100, not Hermes. Don't read/write there.
  - **For headless N100**: Use Device Code Flow (TV and limited-input devices client type) — full recipe in `browser:camofox` SKILL.md "OAuth on N100 Headless — Complete Recipe" section. Successfully tested 2026-06-07.
- **YouTube OAuth scopes — which work with Device Code Flow**: `youtube.readonly`, `openid`, `email`, `profile` are OK. `subscriptions.readonly` and `youtube.force-ssl` are NOT supported by Device Code Flow (Google returns 400 `invalid_scope`). For "get user's subscriptions" via Device Code Flow, use just `youtube.readonly` — `subscriptions.list` works with that scope.
- **Browser tool (Camofox) session**: The Hermes browser tool uses Camofox. Session cookies are stored in `~/.camofox-docker/profiles/{profile_id}/storage-state.json`. To log into YouTube via browser:
  1. Navigate to `https://accounts.google.com/v3/signin/identifier` and sign in manually
  2. Or import cookies from another browser session into the Camofox storage-state.json file
  3. Navigate to YouTube after cookies are set; check for the avatar in the banner to confirm login
  4. Alternative: use `agent-browser` CLI (installed at `~/.hermes/hermes-agent/node_modules/.bin/agent-browser`) with `agent-browser state load` command
- **Camofox profile path**: `~/.camofox-docker/profiles/8da9bc670425101e670f0e6b89eb99e1/storage-state.json` (profile may vary)
- **YouTube cookies are domain-specific**: A critical distinction — cookies exported from Chrome for `.google.com` do NOT grant access to YouTube. YouTube uses its own session cookies (`LOGIN_INFO`) set only on `.youtube.com`. When exporting cookies for YouTube access:
  1. Export cookies specifically for the `youtube.com` domain (not just `.google.com`)
  2. Or export `.google.com` + `.youtube.com` separately and merge
  3. A full YouTube login session requires both Google auth cookies AND YouTube-specific session tokens
  4. Generic Google cookies (SID, HSID, SSID, SAPISID, etc.) authenticate to Google services but NOT to YouTube's subscription/history endpoints without YouTube-specific tokens
- **Camofox + agent-browser both available**: Two browser automation paths — Camofox (Hermes native, `browser_navigate`/`browser_snapshot`) and agent-browser CLI (`~/.hermes/hermes-agent/node_modules/.bin/agent-browser`). Camofox is default; agent-browser can be invoked via `terminal` for operations like `state load`.
- **Transcript availability**: `youtube-transcript-api` works for videos with subtitles. It does NOT work on live streams or videos with transcripts disabled.

## Error Handling

- **Transcript disabled**: tell the user; suggest they check if subtitles are available on the video page.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing**: run `pip install youtube-transcript-api` and retry.
