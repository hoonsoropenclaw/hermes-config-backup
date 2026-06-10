# cache/youtube/

YouTube 抓取工具用的「純公開資料」快取。

## 內容

- `channels.json` — 訂閱頻道清單（id + title），可從 YouTube 公開 RSS 重建
- 8 個頻道（2026-06-07 抓的）

## 為什麼在 cache/

- 不是 hermes 系統檔（不像 `state.db` / `*.cache.json` 那樣 hardcode 根目錄）
- 是「自建的 YouTube 抓取工具」產出
- 純公開資料，無 secret 性質，不需加密
- 用 `cache/` 子目錄收容，避免散在根目錄

## 寫入端

- `~/.hermes/scripts/youtube_oauth.py`（refresh channels 時寫入）
- `~/.hermes/scripts/youtube_rss_check.py`（讀）
- `~/.hermes/scripts/youtube_obsidian_build.py`（讀）

## rebuild

如果 channels.json 掉了：
1. 跑 `python3 ~/.hermes/scripts/youtube_oauth.py --refresh-channels`
2. 從 OAuth token 重新拉訂閱清單
3. 寫回 cache/youtube/channels.json
