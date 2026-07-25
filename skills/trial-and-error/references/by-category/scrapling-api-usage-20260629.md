# scrapling API 用法更新（2026-06-29 新增）

## 缺口背景

scrapling SKILL.md（mtime 2026-06-14）記錄的 API 用法與 v0.4.8 實際行為不符：

### 錯誤用法（文檔中的寫法）
```python
from scrapling.fetchers import Fetcher, StealthyFetcher

# 錯誤：configure() 不等於 Fetcher 實例
F = Fetcher.configure()  # 返回 None！
resp = F.get(url)        # AttributeError: 'NoneType' object has no attribute 'get'

# 錯誤：直接當 classmethod 呼叫
p = Fetcher.fetch(url)   # AttributeError: type object 'Fetcher' has no attribute 'fetch'
```

### 正確用法（v0.4.8 實測）
```python
from scrapling.fetchers import Fetcher

# 正確：直接實例化（不需 configure）
f = Fetcher()
resp = f.get("https://example.com")
print(resp.css("h1::text").get())  # ✅ 輸出：Example Domain

# configure() 是用來設定全域 parser 參數，不是取得 Fetcher 實例
Fetcher.configure(adaptive=False)  # 設定全域參數
```

### 為什麼文檔是錯的
- `configure()` 是 **classmethod** 用来设定 parser 全域参数（`adaptive`、`storage` 等）
- `configure()` **不返回 Fetcher 实例**，返回 `None`（在 v0.4.8）
- 正確模式：**直接 `Fetcher()` 实例化后调用 `.get()` / `.post()`**

## If→Then

**If** scrapling `Fetcher.configure()` 返回 `None` **Then** 不要用 `configure()` 当 Fetcher 实例化，改用 `Fetcher()` 直接实例化

**If** 需要設定 parser 參數（adaptive 等） **Then** `Fetcher.configure(adaptive=True)` 設定的是全域參數，不是取得實例

## 驗證命令
```bash
python3.12 -c "from scrapling.fetchers import Fetcher; f=Fetcher(); r=f.get('https://example.com'); print(r.css('h1::text').get())"
# 預期輸出：Example Domain
```

## 相關條目
- [[browser-automation#scrapling-API-v0.4.8]]
