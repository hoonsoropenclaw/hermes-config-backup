# 新增踩雷條目 — 標準格式

複製下面的模板,填入後存到 `references/by-category/<分類>.md`。

```markdown
### [簡短標題,描述症狀或工具名]
**發現時間**: 2026-XX-XX
**觸發情境**: <什麼任務下踩到,一句話>
**症狀**: <具體錯誤訊息、命令列輸出、或觀察到的異常>
**根因**: <為什麼會這樣壞,寫機制不寫表面>
**解法**: <具體指令/步驟,可直接 copy-paste 執行>
**預防**: <未來怎麼避開,寫進 SKILL/工具的哪個地方>
**相關條目**: <連結到其他 by-category 內的條目,用 [[gpg-encryption#條目標題]] 格式>
```

## 填寫範例

```markdown
### Python sandbox 把 token 遮罩成 *** 導致字串截斷
**發現時間**: 2026-06-05
**觸發情境**: 寫 `f"Bearer {token}"` 跑 GitHub API,Python 程式碼被解析時 token 直接被替換成 `***`,字串被截斷、SyntaxError
**症狀**: `SyntaxError: unterminated string literal (detected at line N)`
**根因**: hermes Python sandbox 在 AST/解析階段掃程式碼,把 `ghp_*` / `vcp_*` 等 token pattern 直接替換成 `***`,導致 Python 解析器以為字串提前結束
**解法**: 
- 改用串接:`headers={"Authorization": "Bearer " + token}`
- 或從檔案讀取:`token = open(path).read().strip()`
- 或用 `os.environ.get("GH_TOKEN")` 拿環境變數
**預防**: 任何 token 字串都不直寫在 Python 程式碼字串內,一律走環境變數或檔案
**相關條目**: [[secrets-and-env#替代 token 加密佈局]]
```

## 注意事項

1. **症狀要可被搜尋**:寫具體的錯誤訊息、命令、API 端點、log 內容
2. **根因不要寫成「就是這樣」**:要解釋機制
3. **解法要可執行**:給指令碼或具體步驟,不只給原則
4. **預防要落地**:寫進 SKILL 哪個段落、寫進 SOP 哪一步
5. **標題用症狀 + 工具名**:不要用「X 壞了」這種籠統標題
