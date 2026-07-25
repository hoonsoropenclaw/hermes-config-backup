# 瀏覽器自動化 / Playwright / Headless Browser 相關踩雷

> 觸發:任何瀏覽器自動化、Playwright 腳本、headless browser、CDP 連線
> 建立時間: 2026-06-05
> 條目數: 3

---

### Playwright headless 環境需要先 pip install playwright + playwright install chromium
**發現時間**: 2026-05-30
**觸發情境**: 第一次跑 Playwright QA 腳本驗證網站
**症狀**: `playwright._impl._api_types.Error: Executable doesn't exist at /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome`
**根因**: Playwright Python 套件裝了,但瀏覽器 binary 沒裝
**解法**:
```bash
pip install playwright
playwright install chromium    # 裝 chromium binary
# 或裝 firefox / webkit
playwright install firefox
```
**預防**: 環境初始化 SOP 必加這兩步
**相關條目**: 無

---

### Camofox watchdog 未部署導致瀏覽器長期掉線（2026-06-06）
**發現時間**: 2026-06-06
**觸發情境**: 日常 cron 檢查發現 `browserConnected: false`，但 Docker container 還在跑（API server alive, browser process dead）
**症狀**: `curl http://localhost:9377/health` 回 `browserConnected: false`，但 `docker ps` 顯示 container 還在運行；所有自動化任務靜默失敗
**根因**: `camofox-watchdog.sh` 腳本存在於 `~/.hermes/skills/browser/camofox/scripts/` 但**從未加入 crontab**，導致瀏覽器引擎斷線後無自動復線機制
**解法**:
```bash
# 立刻重啟瀏覽器引擎
docker restart camofox-browser
sleep 10 && curl -s http://localhost:9377/health

# 部署 watchdog 到 cron（每分鐘檢查）
(crontab -l 2>/dev/null | grep -v camofox-watchdog; echo "* * * * * /home/hoonsoropenclaw/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh >> /tmp/camofox-watchdog.log 2>&1") | crontab -
```
**預防**: SKILL.md 裡有 watchdog script ≠ 自動生效。Skill author 必須同時確認：script 存在 AND cron 已部署。兩者缺一就是漏洞。
**If→Then**: **If** `hermes cron list` 顯示某個 cron job error 且該 job 有對應的 watchdog script **Then** 立即檢查 script 是否在 crontab 中，確認 cron 部署狀態而非只確認 script 檔案存在
**相關條目**: [[hermes-internal#hermes cron edit --script 對 no_agent jobs 的 Bug]]

---

### noVNC 黑畫面 = 沒按 Connect，autoconnect URL 才能自動連（2026-06-07）
**發現時間**: 2026-06-07
**觸發情境**: 從 Windows SSH tunnel 連到 N100 的 noVNC（port 6080），打開 `http://localhost:6080/vnc.html` 看到**純深灰色無內容畫面**
**症狀**:
- noVNC 介面有載入（網址列顯示 `vnc.html`）
- 畫面是純灰色，**沒有 VNC 內容渲染**（沒看到桌面、沒看到 Firefox）
- 沒看到 noVNC 預設的「Connect」對話框（被自動關閉？或現代 noVNC 行為改變）
**根因**:
- noVNC **預設行為**是要求使用者手動輸入 host/port 並按 Connect
- 即使 VNC server 活著（x11vnc 跑在 5900、Xvfb 跑在 :1738），noVNC 沒發起 WebSocket 連線就不會 render
- 從 Windows 看就是「黑畫面」——其實是「noVNC 沒跟 VNC 握手」
- **這不是 VNC server 死了**：可以從 N100 內部 `bash -c "exec 3<>/dev/tcp/127.0.0.1/5900"` 測試，TCP 連得上
**解法**:
1. **用 autoconnect URL 參數**（**最簡單**）：
```
http://localhost:6080/vnc.html?autoconnect=true&host=localhost&port=5900&resize=scale
```
或用 `vnc_lite.html`：
```
http://localhost:6080/vnc_lite.html?autoconnect=true&resize=scale
```
開啟就會自動連 VNC、立刻看到桌面

2. **手動按 Connect**（如果 autoconnect URL 失敗）：
   - noVNC 介面左上或中間會有「Settings」齒輪 → 輸入 `host=localhost&port=5900`
   - 按 **Connect** 按鈕

3. **驗證 VNC server 活著**（先排除後端死掉）：
```bash
ss -tlnp | grep 5900                          # port 5900 LISTEN
ps aux | grep -E "x11vnc|Xvfb" | grep -v grep # process 活著
docker exec camofox-browser bash -c "exec 3<>/dev/tcp/127.0.0.1/5900"  # container 內 TCP 通
```
**預防**:
- 任何「noVNC 看到黑畫面」的回報，**第一步先打 autoconnect URL**，不要假設 VNC 死了
- 寫教學文件時，**永遠給 autoconnect URL**（不要只給 `vnc.html` 沒參數的版本）
- 部署 noVNC 的 websockify 時，**優先用 `vnc_lite.html` + autoconnect 參數**組合（最穩）
**If→Then**:
- **If** 從 Windows SSH tunnel 連 N100 noVNC 看到黑畫面  **Then** 立刻把 URL 改成 `vnc.html?autoconnect=true&host=localhost&port=5900`，**不要**先懷疑 VNC server 死了
- **If** autoconnect URL 還是不行  **Then** 才懷疑 websockify 跟 VNC 連線問題，檢查 websockify 啟動參數（`/usr/share/novnc` 路徑、`127.0.0.1:6080` 跟 `127.0.0.1:5900`）
- **If** VNC 需要密碼  **Then** URL 加 `&password=<密碼>` 參數，或檢查 x11vnc 啟動有沒有 `-nopw`
**相關條目**: 本 skill 的「Camofox watchdog 未部署」 + [[secrets-and-env#OAuth client 被刪除 → refresh_token 立刻失效]]

---

## 跨分類關聯

- 瀏覽器跑 gpg / 加密 → [[gpg-encryption]]
- Vercel 部署前瀏覽器實測 → [[vercel-deployment#Vercel 部署區分「新建專案」vs「更新現有」]]


---

### N100 預設沒裝 vision LLM、browser_vision 會回 "No LLM provider configured"(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 想自己用 browser_vision 看 status site 截圖驗證視覺
**症狀**:
- `browser_vision` 報 `Error analyzing image: No LLM provider configured for task=vision provider=auto. Run: hermes setup`
- 圖片有下載到 `~/.hermes/browser_screenshots/`(看截圖檔案存在),但**沒人分析**
- 想視覺驗證只能靠子代理瀏覽器或自己手動眼睛看

**根因**:
- Hermes 預設沒裝 vision model(像 gpt-4-vision、Claude 3 vision)
- `browser_vision` 工具會自動 fallback 到 auxiliary vision model,但要 LLM provider 設定
- N100 headless 環境通常不會預裝(省資源、不是 desktop use case)

**修法**:
1. **設定 hermes vision provider**:
   ```bash
   hermes setup
   # 選 vision 設定、輸入 API key
   ```
   但會吃 API 額度

2. **不要自己 browser_vision、改派子代理**:
   - 子代理有 vision LLM 設定(因為它有獨立的 provider config)
   - 給子代理截圖、它自己 browser_vision 評
   - 回傳文字評分給主 session

3. **手動看截圖檔**:
   - `ls ~/.hermes/browser_screenshots/`
   - 把 PNG 讀到 vision 工具(用 `vision_analyze(image_url=...)`)

**If** → **Then** 規則:
- **If** 主 session 要視覺驗證 **Then** 派有 vision 的子代理、給它截圖任務
- **If** 只想確認「畫面長怎樣」 **Then** 讀截圖檔到 `vision_analyze`(支援本地檔)
- **If** browser_vision 報 provider 錯誤 **Then** 不要糾結、跳到子代理方案
- **If** 評估 portal 作品 / 網站視覺 **Then** 走 portal-judge-agent skill,讓 portal-judge-agent 處理 vision

**已驗證**:
- 2026-06-07 評 status site 時主 session browser_vision 報 provider 錯誤
- 改派 portal-judge-agent 子代理、子代理自己用 browser_vision 成功
- 子代理回報文字結果(7.3/10 → 7.7/10)給主 session 整合
