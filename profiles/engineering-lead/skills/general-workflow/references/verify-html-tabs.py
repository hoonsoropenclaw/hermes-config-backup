#!/usr/bin/env python3
"""
verify-html-tabs.py — 驗證多 tab HTML 結構的腳本

用途：當用 innerHTML 注入架構的網站（如 hermes-status-site 的 loadTab）
做多檔修改時，驗證：
1. 整檔 div 平衡
2. 標記的內容（如 status-footer）是否在 tab-content innerHTML 內
3. 不在 tab-content 內的元素清單（可能是 patch 漏掉的）

用法：
  python3 verify-html-tabs.py <tabs_dir> <expected_selector> [<expected_selector> ...]

範例：
  python3 verify-html-tabs.py ~/hermes-status-site/tabs status-footer
  python3 verify-html-tabs.py ~/hermes-status-site/tabs status-footer related-sites
"""

import re
import sys
import os
from html.parser import HTMLParser


class DivBalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            self.stack.append(self.getpos())

    def handle_endtag(self, tag):
        if tag == 'div':
            if not self.stack:
                self.errors.append(f"Unexpected </div> at line {self.getpos()[0]}")
            else:
                self.stack.pop()


def find_tab_content_inner(content):
    """找 <div id="tab-content"> 對應的 innerHTML 範圍"""
    tab_open = content.find('<div id="tab-content"')
    if tab_open < 0:
        tab_open = content.find('<div id="tab-content>')
    if tab_open < 0:
        return None, None

    # 跳過 <div id="tab-content" 自己
    inner_start = content.find('>', tab_open) + 1

    # 用 stack 找對應的 closing </div>
    pos = inner_start
    depth = 1
    div_pat = re.compile(r'<div[\s>]')
    close_pat = re.compile(r'</div>')
    while depth > 0:
        next_open = div_pat.search(content, pos)
        next_close = close_pat.search(content, pos)
        if not next_close:
            return inner_start, len(content)
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
    return inner_start, pos - len('</div>')


def check_tab(path, selectors):
    name = os.path.basename(path)
    content = open(path).read()
    content_clean = re.sub(r'<script[\s\S]*?</script>', '', content)
    content_clean = re.sub(r'<style[\s\S]*?</style>', '', content_clean)

    # 1. div balance
    checker = DivBalanceChecker()
    checker.feed(content_clean)
    balanced = (len(checker.stack) == 0 and len(checker.errors) == 0)
    unclosed = [(s[0]) for s in checker.stack]

    # 2. tab-content 範圍
    inner_start, inner_end = find_tab_content_inner(content)
    inner_html = content[inner_start:inner_end] if inner_start is not None else ''

    # 3. selectors in tab-content
    selector_status = {}
    for sel in selectors:
        in_inner = sel in inner_html
        in_full = sel in content
        selector_status[sel] = {
            'in_tab_content': in_inner,
            'in_full_file': in_full,
            'ok': in_inner,
        }

    return {
        'name': name,
        'balanced': balanced,
        'unclosed_lines': unclosed,
        'errors': checker.errors,
        'selectors': selector_status,
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    tabs_dir = sys.argv[1]
    selectors = sys.argv[2:]

    if not os.path.isdir(tabs_dir):
        print(f"ERROR: {tabs_dir} is not a directory")
        sys.exit(1)

    all_ok = True
    print(f"\n=== Verifying {tabs_dir} ===\n")

    for tab in sorted(os.listdir(tabs_dir)):
        if not tab.endswith('.html'):
            continue
        path = os.path.join(tabs_dir, tab)
        result = check_tab(path, selectors)

        bal_flag = '✓' if result['balanced'] else '✗'
        print(f"  {bal_flag} {result['name']:25s}", end='')

        for sel, status in result['selectors'].items():
            sel_flag = '✓' if status['ok'] else '✗'
            print(f"  {sel_flag} {sel}", end='')
            if not status['ok']:
                all_ok = False
        print()

        if not result['balanced']:
            print(f"      → unclosed: {result['unclosed_lines']} · errors: {result['errors'][:2]}")
            all_ok = False

    print()
    if all_ok:
        print("✅ ALL OK — div balance + selectors all inside tab-content")
        sys.exit(0)
    else:
        print("✗ ISSUES FOUND — fix before deploying")
        sys.exit(1)


if __name__ == '__main__':
    main()
