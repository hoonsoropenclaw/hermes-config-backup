# URL → D2 Architecture Diagram Pipeline

**驗證狀態**：2026-06-13 實測成功（python3.12 + playwright → D2 → 24723 bytes SVG）

## 工具鏈
`python3.12 + playwright`（fetch + analyze） → `/tmp/d2`（render SVG）

## 安裝 D2（若尚未安裝）

```bash
# 從 GitHub releases 直接下載（不走 pip）
curl -fsSL "https://api.github.com/repos/terrastruct/d2/releases/latest" | \
  python3 -c "import sys,json; r=json.load(sys.stdin); \
  [print(a['browser_download_url']) for a in r['assets'] if 'linux-amd64' in a['name'].lower()]"

curl -fsSL "https://github.com/terrastruct/d2/releases/download/v0.7.1/d2-v0.7.1-linux-amd64.tar.gz" \
  -o /tmp/d2.tar.gz && tar xzf /tmp/d2.tar.gz -C /tmp
cp /tmp/d2-v0.7.1-linux-amd64/bin/d2 /tmp/d2 && chmod +x /tmp/d2
/tmp/d2 version  # 驗證
```

## 腳本：`/tmp/url_to_d2.py`

```python
#!/usr/bin/env python3
"""URL to D2 Architecture Diagram"""
import asyncio, subprocess, sys
from playwright.async_api import async_playwright

D2_PATH = "/tmp/d2"

def escape_d2(s):
    """All D2 labels with : " {} # must be quoted and internal " escaped."""
    if not s: return '""'
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{s}"'

async def fetch_page_structure(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        resp = await page.goto(url, timeout=20000)
        structure = await page.evaluate("""
() => {
    const r = { title: document.title, status: %d, sections: [], links: [], scripts: [] };
    for (const c of Array.from(document.body.children).slice(0, 6)) {
        const sec = { tag: c.tagName, id: c.id||null, children: [] };
        for (const s of Array.from(c.children).slice(0, 4)) {
            const t = (s.innerText||'').substring(0,50).replace(/\\n/g,' ').trim();
            sec.children.push({tag: s.tagName, textPreview: t.substring(0,40)});
        }
        r.sections.push(sec);
    }
    r.links = Array.from(document.querySelectorAll('a[href]')).slice(0,5)
        .map(a=>({href:a.href, text:(a.innerText||'').substring(0,40)}));
    r.scripts = Array.from(document.querySelectorAll('script[src]')).slice(0,5)
        .map(s=>s.src.split('/').pop());
    return r;
}
        """ % resp.status)
        await browser.close()
        return structure

def structure_to_d2(url, structure):
    lines = [
        f"# {structure['title']}", f"# {url}", "",
        'Browser: Browser { shape: rectangle; style.fill: "#E3F2FD" }',
        f"Page: {escape_d2(structure['title'])} {{ shape: rectangle; style.fill: \"#FFFDE7\" }}", ""
    ]
    if structure.get('sections'):
        lines.append("Sections: Sections {")
        for i, sec in enumerate(structure['sections']):
            label = f'{sec["tag"]}#{sec["id"]}' if sec['id'] else sec['tag']
            lines.append(f'  S{i}: {escape_d2(label)} {{ shape: rectangle; style.fill: \"#F3E5F5\" }}')
            for j, child in enumerate(sec.get('children', [])[:3]):
                lines.append(f'    C{j}: {escape_d2(child["tag"]+": "+(child.get("textPreview","")[:35]))} {{ }}')
        lines.append('}')
    if structure.get('links'):
        lines.extend(['', 'ExternalLinks: ExternalLinks {'])
        for i, link in enumerate(structure['links'][:4]):
            lines.append(f'  L{i}: {escape_d2(link["text"])} {{ href: {escape_d2(link["href"])} }}')
        lines.append('}')
    lines.extend(['', 'Browser -> Page: "HTTP GET"', ''])
    return '\n'.join(lines)

async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://httpbin.org/html"
    out_d2 = sys.argv[2] if len(sys.argv) > 2 else "/tmp/output.d2"
    out_svg = out_d2.replace('.d2', '.svg')
    print(f"Fetching {url}...")
    structure = await fetch_page_structure(url)
    print(f"Title: {structure['title']} | Sections: {len(structure['sections'])}")
    d2 = structure_to_d2(url, structure)
    with open(out_d2, 'w') as f: f.write(d2)
    print(f"D2 saved: {out_d2}")
    r = subprocess.run([D2_PATH, out_d2, out_svg], capture_output=True, text=True)
    if r.returncode == 0:
        from os.path import getsize
        print(f"SVG rendered: {out_svg} ({getsize(out_svg)} bytes)")
    else:
        print(f"D2 error: {r.stderr}")

if __name__ == '__main__': asyncio.run(main())
```

**使用**：`python3.12 /tmp/url_to_d2.py "https://example.com" /tmp/example.d2`

## 常見錯誤

| 錯誤 | 原因 | 修復 |
|------|------|------|
| `"unexpected text after double quoted string"` | label 含 `:` 未 escape | 所有 label 透過 `escape_d2()` |
| `unknown shorthand flag: -f` | D2 v0.7.1 用 positional args | `d2 input.d2 output.svg` |
| `ModuleNotFoundError: playwright` | python3 路徑錯 | 用 `python3.12` |

## 驗證 SVG

```python
from xml.etree import ElementTree as ET
ET.parse('/tmp/output.svg')  # 無異常 = 有效
```
