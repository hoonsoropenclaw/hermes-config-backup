# Todo App 5-Round 對比實驗(2026-06-11~12)

> 完整實驗數據,給未來 agent 看「派遣 vs 單獨寫」的真實 trade-off。
> 對應 `SKILL.md` 的「Model Selection: M3 vs M2.7 Sub-Agents」段。

## 實驗設計

- **任務**:Todo App(Next.js 14 + TypeScript + in-memory DB + 4 個檔:`lib/types.ts` / `lib/db.ts` / `app/page.tsx` / `app/api/todos/route.ts`)
- **任務規模**:M 型(2-3 ticket,多檔 + 簡單介面)
- **基準架構圖**:`~/reverse-engineering/todo-app/reverse-arch.md`(5 視角)
- **5 個 round**:同樣任務、5 種執行方式對比

## 5 Round 結果

| Round | 方式 | Sub-agent Model | 整合問題 | 整合時間 | 總耗時 | 程式碼品質 |
|-------|------|-----------------|---------|---------|--------|-----------|
| **R1** | 單獨寫(1 個人 1 條龍) | (M3,1 個人) | 0 | 0 | 161s | ⭐⭐⭐⭐⭐ |
| **R2** | 派遣,粗糙 ticket | **M2.7** | **2 個大**(export 形式不一致) | 71s | 180-200s | ⭐⭐⭐ |
| **R2b** | 派遣,粗糙 ticket | **M3** | 1 個小(1 個 catch lint) | 30s | 270s | ⭐⭐⭐⭐ |
| **R3** | 派遣,改進 ticket(6 條 coding 規範) | **M2.7** | 2 個小(函式簽名) | 60s | 605s(失真) | ⭐⭐⭐⭐ |
| **R3b** | 派遣,改進 ticket(6 條 coding 規範) | **M3** | **0** | 0 | **180s** | ⭐⭐⭐⭐⭐ |

## 5 個關鍵發現

### 發現 1:平行寫不會省 wall time,只會省主 session context

```
R1:131s(1 個人連續寫)
R2:180s(平行 109s + 整合 71s)
R3:605s(平行 545s + 整合 60s,時間失真)
R3b:180s(平行 180s + 整合 0s)
```

**真正省的不是 wall time,是主 session 的 context 占用時間**。在 R2/R3/R3b,主 session 只在「派遣 + 整合」時占用 context,中間平行時間可以做別的事。

### 發現 2:整合成本隨 sub-agent 數量增加

- R1:1 個人 → 0 整合
- R2:3 個 sub-agent → 2 個大整合問題
- R3b:3 個 sub-agent + 6 條規範 → 0 個整合問題

**整合成本 ≈ (介面不一致點數) × (修齊所需時間)**。子代理越多、ticket 規格越不明確、不一致點越多。

### 發現 3:規範對「格式問題」有效,對「語意問題」無效

| 問題類型 | 範例 | 規範化難度 |
|---------|------|----------|
| **格式問題** | 引號、import/export 形式、catch 寫法 | ✅ 易規範化(6 條夠用) |
| **語意問題** | 函式簽名、回傳型、命名 | ⚠️ 要寫精確 API spec(寫進 reverse-arch 視角 2) |

R3 跟 R3b 的 6 條規範完全解決了「格式問題」,但「語意問題」(函式簽名)還是要靠 reverse-arch 升級成「精確 API 規格」才能解。

### 發現 4:sub-agent 會犯「自己寫不會犯」的錯

- 寫 `import db from '@/lib/db'` 預期 default export(自己寫時會看自己 export 的是 named)
- 寫 `catch { setError(e.message) }` 沒 e 變數(自己寫會 `catch (e) { console.error(e); ... }`)
- 寫 `db.list()` 沒參數(自己寫會記得規格)

**根因**:sub-agent 寫 route.ts 時 **沒看到** lib/db.ts 寫了什麼 — 兩個 context 切斷。**自己寫時有「跨檔連貫記憶」**,這是 sub-agent 沒有的。

### 發現 5:ticket 規格的明確度直接決定品質

| Ticket 粒度 | 整合問題 | 修齊時間 |
|------------|---------|---------|
| 「寫 Todo App 的 lib/db.ts」 | 多個(export、簽名、行為) | 60-90s |
| 「寫 lib/db.ts,**用 export const db 物件、list 接受 filter: FilterType、回傳 Todo[]**」 | 少 | 0-30s |

**寫 ticket 的成本也算進去** — 改進版 ticket 我寫了 3 倍長度,但只省 30-60s 整合,**M3 時代淨小賺,M2.7 時代淨小虧**。

## 環境陷阱(實驗中踩到)

### 陷阱 1:`/tmp` 不可靠,prompt 必放永久路徑

**症狀**:實驗中用 `/tmp/round-3b-worker-*.txt` 存 prompt,被系統清掉(2-3 小時後自動清),後續 background sub-agent 跑失敗但 main session 還以為 prompt 在。

**修法**:`mkdir -p <exp-dir>/prompts/`,所有 prompt 永久存。

### 陷阱 2:`hermes chat -q` 配 `| tee` 會「Input is not a terminal」→ Goodbye

**症狀**:
```bash
hermes chat -m MiniMax-M3 -q "$PROMPT" --cli --quiet --yolo --accept-hooks 2>&1 | tee worker.log
```
→ 60 秒內 Goodbye,log 只有 7.7KB banner 文字、沒有 prompt 處理。

**根因**:`tee` 接管 stdin,跟 `hermes chat -q` 的 prompt 衝突。

**修法**:用 `>` redirect 寫檔,不用 `| tee`:
```bash
hermes chat -m MiniMax-M3 -q "$PROMPT" --cli --quiet --yolo --accept-hooks 2>&1 > worker.log
```

### 陷阱 3:`terminal(background=true)` 啟動但目錄沒建 → 失敗但 exit_code=0

**症狀**:目錄不存在時,background process 內的 `tee` / `redirect` 失敗,但 `terminal(background=true)` 立即 detach、return exit_code=0 → main session 不知道失敗。

**修法**:啟動 background process **之前** 先 `mkdir -p` 目錄並驗證。

### 陷阱 4:`execute_code` 5 分鐘 timeout 不夠跑 sub-agent

**症狀**:用 `execute_code` 內 `subprocess.Popen` 啟動 3 個 sub-agent 並 `process.communicate(timeout=600)`,5 分鐘後 `execute_code` 自身 timeout 殺掉整個 script → 連 sub-agent 一起死。

**修法**:
- **不要**在 `execute_code` 內用 `subprocess.communicate` 等 sub-agent
- **改用** `terminal(background=true, notify_on_complete=true)` 啟動,sub-agent 自己跑、main session 主動 `ls` 監聽
- 或者 `process.wait(timeout=...)` 拆成多個 `terminal()` call

### 陷阱 5:2>&1 > 的順序會丟 stderr

**症狀**:`hermes chat ... 2>&1 > worker.log` 的 stderr 跑到 terminal(主 session 看到一堆輸出),worker.log 只有 stdout。

**修法**:正確順序 `> worker.log 2>&1`(先 redirect stdout 到 log、再 redirect stderr 到「當前 stdout」也就是 log)。

## 對 engineering-lead persona 的具體建議

從實驗結論,建議補進 `~/.hermes/profiles/engineering-lead/persona.md`:

1. **Step 1 評估任務規模** → 決定是否派遣(S 型不派遣、M 型看 model、L 型鼓勵)
2. **Step 2 寫 ticket 時** 必含 API 規格表(函式簽名 + 回傳型 + 命名)
3. **Step 3 派遣後** 必跑「整合 SOP」(build + typecheck + lint)
4. **若 model = M3** → 鼓勵派遣(S 型除外)
5. **若 model = M2.7** → S/M 型單獨寫、L 型才派遣

## 完整檔案

```
~/reverse-engineering/todo-app/
├── reverse-arch.md                       # 基準架構圖
├── exp-1-3-compare.md                    # 第一次對比報告
├── exp-2-m3-compare.md                   # 第二次對比報告(含 M3 結論)
├── round-1-solo/RESULT.md                # R1 詳細
├── round-2-parallel/RESULT.md            # R2 詳細(M2.7 派遣粗糙)
├── round-2b-parallel-m3/RESULT.md        # R2b 詳細(M3 派遣粗糙)
├── round-3-parallel/RESULT.md            # R3 詳細(M2.7 派遣改進)
└── round-3b-parallel-m3/RESULT.md        # R3b 詳細(M3 派遣改進)
```
