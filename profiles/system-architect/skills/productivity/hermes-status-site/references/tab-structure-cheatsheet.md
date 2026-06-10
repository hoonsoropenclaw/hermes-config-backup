# Tab 結構速查表（2026-06-06 建立）

快速對照 11 個 tab 的結構差異，省下未來 session 重新探索的時間。

## 速查表

| tab 檔名 | 結尾 anchor | 是否有 `<script>` | 是否有 `<body></html>` | 結構備註 |
|----------|------------|-------------------|----------------------|----------|
| `overview.html` | 4-space `</div></body></html>` | ❌ | ✅ | 最大、最複雜；已加 related-sites section |
| `memory.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準 |
| `delegation.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準（pre-existing 開合不平衡）|
| `tools.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準（pre-existing 開合不平衡）|
| `skills.html` | `</script></body></html>` | ✅（inline skill-count script）| ✅ | 內有 inline script；**`loadTab` 不會執行**（已記錄為 known bug）|
| `soul.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準 |
| `md-files.html` | `</div>` only | ❌ | ❌ | 最特殊，由 `loadTab` 注入；`js/md-files.js` 從 `assets/md-files.json` 載入 |
| `scheduler.html` | 0-space `</div></body></html>` | ❌ | ✅ | 0-space 結尾（其他都 4-space）|
| `learning.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準（pre-existing 開合不平衡）|
| `system-info.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準（pre-existing 開合不平衡）|
| `dashboard.html` | 4-space `</div></body></html>` | ❌ | ✅ | 標準 |

## 各 tab 的已知問題

### 4 個 tab 有 pre-existing `</div>` 不平衡（**不是 bug，是設計遺漏**）
- `delegation.html`：69 open / 68 close（diff +1）
- `learning.html`：44 open / 43 close（diff +1）
- `system-info.html`：41 open / 40 close（diff +1）
- `tools.html`：73 open / 72 close（diff +1）

**根因**：這 4 個檔案的 `<div id="tab-content">` 開了但**沒對應的 `</div>` 關閉**。`loadTab` 用 `querySelector('#tab-content').innerHTML` 取內容，所以缺少 closing 反而是「不影響載入」 — 但用 HTML parser 嚴格驗證會 fail。

**處理原則**：
- ✅ 跨 tab 套用 footer / banner / 相關站等元素時，這 4 個檔案可以照樣套
- ❌ 不要去「修」這個不平衡（會動到別人的程式碼，不在任務範圍）
- ✅ 驗證「我的新元素在不在 `#tab-content` 內」時用 regex 找對應 closing，不要用 HTML parser

### `skills.html` 有已知 bug
- 切到 skills tab 後 `skill-count` 永遠顯示「共 0 個技能」
- 原因：inline script 在 `loadTab` 注入時不會被執行
- 49 個 `.skill-row` 元素其實有渲染出來，只是 `document.getElementById('skill-count').textContent = '共 49 個技能'` 這行 JS 沒跑
- 修法（未做）：把 skill-count 改成 inline 數字（Python 預算）或用 `window.*` 從 index.html 注入

## 跨 tab 套用時的 anchor 速查

### 標準 4-space `</div></body></html>`（7 個 tab）
```
    </div>
</body>
</html>
```
**適用**：dashboard, delegation, learning, memory, soul, system-info, tools
**patch 範例**：
```python
old = "    </div>\n</body>\n</html>"
new = "    <!-- My Footer -->\n    <div>...</div>\n</div>\n</body>\n</html>"
```

### 0-space `</div></body></html>`（1 個 tab）
```
</div>
</body>
</html>
```
**適用**：scheduler
**注意**：這個 0-space closing 是 `#tab-content` 真正的關閉（4-space 是關 section）

### `</script></body></html>`（1 個 tab）
```
</script>
</body>
</html>
```
**適用**：skills
**注意**：footer 要插在 `</div></script>` 之間還是 `</script></body>` 之間？要看你想 footer 跟著 tab 內容還是跟著頁面

### `</div>` only（1 個 tab）
```
</div>
```
**適用**：md-files
**注意**：這個檔案**沒有** `</body></html>` 結尾；`loadTab` 會 strip 掉 wrapper，所以不需要
**patch 範例**（插在 `</div>` 之前）：
```python
# anchor 找 `└── config.yaml        # 主設定檔</div>\n    </div>\n</div>` 確保唯一
```

### overview.html（自定結構）
- 因為**已有 related-sites section**（2026-06-06 加的），再加新元素時要小心
- 最保險：**整個 read_file + write_file 重寫**（不要 patch 累積）

## 驗證 SOP（套用後必跑）

```python
import re, os

base = "/home/hoonsoropenclaw/permanent-projects/hermes-status-site/tabs"

def find_tab_content_inner(path):
    """找 #tab-content 開合之間的內容"""
    content = open(path).read()
    tab_open = content.find('<div id="tab-content"')
    if tab_open < 0:
        return None
    pos, depth = content.find('>', tab_open) + 1, 1
    while depth > 0:
        no = re.search(r'<div[\s>]', content[pos:])
        nc = content.find('</div>', pos)
        if nc < 0:
            return None
        if no and pos + no.start() < nc:
            depth += 1
            pos = pos + no.end()
        else:
            depth -= 1
            pos = nc + 6
    return content[content.find('>', tab_open)+1:pos-6]

for tab in sorted(os.listdir(base)):
    if not tab.endswith('.html'): continue
    inner = find_tab_content_inner(os.path.join(base, tab))
    has_footer = inner and 'status-footer' in inner
    print(f"  {'✓' if has_footer else '✗'} {tab:20s} footer in tab-content: {has_footer}")
```

## 歷史 commit 對照

| commit | 內容 | 教訓 |
|--------|------|------|
| `e4c3e17` | feat: add related-sites section + footer to all tabs | 11 個 tab 跨套用，發現 anchor 差 1 space 就匹配錯區段 |
| `96f0055` | feat: remove Raphael dashboard link | 批次刪除 14 處用 Python batch 處理比逐個 patch 快 10x |
| `0155096` | fix: replace JS-generated radar with inline SVG | loadTab innerHTML 不跑 script 的坑（雷達圖）|
| `16c3cbf` | feat: add capability radar chart | 初次踩雷達圖的 innerHTML 坑 |
