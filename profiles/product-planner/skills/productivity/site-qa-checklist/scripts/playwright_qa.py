#!/usr/bin/env python3
"""
hermes-status-site Playwright QA 測試
測試目標：Tab 切換、DOM 結構完整性、Console 錯誤檢測

使用方式：
  python3 playwright_qa.py [url]
  # url 預設為 http://localhost:8765/

Exit code: 0 = 通過, 1 = 有問題
"""
import asyncio
import sys
import json
from playwright.async_api import async_playwright

TABS = [
    'overview', 'memory', 'delegation', 'tools', 'skills',
    'soul', 'mdfiles', 'scheduler', 'learning', 'sysinfo', 'dashboard'
]

async def run_qa(url: str) -> dict:
    results = {
        'url': url,
        'tabs': {},
        'console_errors': [],
        'dom_issues': [],
        'passed': True
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 攔截 console errors
        def on_console(msg):
            if msg.type == 'error':
                results['console_errors'].append({'type': 'error', 'text': msg.text})

        def on_pageerror(err):
            results['console_errors'].append({'type': 'pageerror', 'text': str(err)})

        page.on('console', on_console)
        page.on('pageerror', on_pageerror)

        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            results['dom_issues'].append(f'導航失敗: {e}')
            results['passed'] = False
            await browser.close()
            return results

        # 測試每個 Tab 切換
        for tab_name in TABS:
            tab_id = f'tab-{tab_name}'
            tab_content = page.locator(f'#{tab_id}')
            tab_btn = page.locator(f'[data-tab="{tab_name}"]')

            # 檢查 Tab 內容元素存在
            content_exists = await tab_content.count() > 0
            btn_exists = await tab_btn.count() > 0

            if not content_exists:
                results['dom_issues'].append(f'缺少 tab content: #{tab_id}')
                results['tabs'][tab_name] = '❌ 缺少 content 元素'
                results['passed'] = False
                continue

            # 點擊 Tab 按鈕
            if btn_exists:
                await tab_btn.click()
                await page.wait_for_timeout(300)
            else:
                # 嘗試用 onclick 方式找按鈕
                all_btns = page.locator('.tab-btn')
                count = await all_btns.count()
                clicked = False
                for i in range(count):
                    btn = all_btns.nth(i)
                    onclick = await btn.get_attribute('onclick') or ''
                    if f"showTab('{tab_name}')" in onclick or f'showTab("{tab_name}")' in onclick:
                        await btn.click()
                        await page.wait_for_timeout(300)
                        clicked = True
                        break
                if not clicked:
                    results['dom_issues'].append(f'找不到 tab 按鈕: {tab_name}')
                    results['tabs'][tab_name] = '❌ 找不到按鈕'
                    results['passed'] = False
                    continue

            # 檢查內容是否顯示
            display = await tab_content.evaluate('el => getComputedStyle(el).display')
            inner_len = await tab_content.evaluate('el => el.innerText.length')

            if display == 'none':
                results['tabs'][tab_name] = f'❌ display={display}, chars={inner_len}'
                results['passed'] = False
            elif inner_len == 0:
                results['tabs'][tab_name] = f'⚠️ display={display}, chars=0 (空白內容)'
            else:
                results['tabs'][tab_name] = f'✅ display={display}, chars={inner_len}'

        # 檢查 HTML 結構（</html> 後不應有內容）
        html_content = await page.content()
        html_end = html_content.rfind('</html>')
        if html_end != -1:
            after_html = html_content[html_end + len('</html>'):].strip()
            if after_html:
                results['dom_issues'].append(f'</html> 後有多餘內容: {after_html[:200]}')
                results['passed'] = False

        # 檢查是否有未閉合的 div
        div_open = html_content.count('<div')
        div_close = html_content.count('</div>')
        if div_open != div_close:
            results['dom_issues'].append(f'DOM 結構問題: <div> 數量={div_open}, </div> 數量={div_close}')
            results['passed'] = False

        await browser.close()
        return results


if __name__ == '__main__':
    test_url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
    result = asyncio.run(run_qa(test_url))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['passed'] and not result['dom_issues'] else 1)
