#!/usr/bin/env python3
"""萃取出所有無盡學習專案的記憶精華"""
import os
import re
from pathlib import Path
from collections import defaultdict
import json

PROJECTS_DIR = Path("/home/hoonsoropenclaw/.hermes/evolution/endless_mode/projects")
OUTPUT_FILE = Path("/home/hoonsoropenclaw/.hermes/evolution/EL_ALL_EXTRACT.md")

def get_memory_files():
    """取得所有 memory.md 檔案"""
    memory_files = []
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir():
            memory_file = d / "memory.md"
            if memory_file.exists():
                memory_files.append((d.name, memory_file))
    return sorted(memory_files)

def extract_key_info(project_name, content):
    """從專案記憶中萃取關鍵資訊"""
    info = {
        "project": project_name,
        "domain": extract_domain(project_name),
        "topics": extract_topics(content),
        "code_snippets": extract_code_snippets(content),
        "key_findings": extract_key_findings(content),
        "tools_mentioned": extract_tools(content),
        "lines": len(content.split('\n'))
    }
    return info

def extract_domain(project_name):
    """從專案名稱萃取領域"""
    name_lower = project_name.lower()
    if any(x in name_lower for x in ['admin', 'hr', 'school', 'workflow', 'document', 'docx', 'doc']):
        return "admin"
    elif any(x in name_lower for x in ['code', 'api', 'python', 'async']):
        return "code"
    elif any(x in name_lower for x in ['finance', 'stock', 'option', 'trading', 'portfolio']):
        return "finance"
    elif any(x in name_lower for x in ['web', 'react', 'ui', 'frontend']):
        return "web"
    elif any(x in name_lower for x in ['system', 'mcp', 'agent', 'subagent']):
        return "system"
    elif any(x in name_lower for x in ['browser', 'scrape', 'playwright']):
        return "browser"
    elif any(x in name_lower for x in ['line', 'messaging', 'bot', 'notification']):
        return "messaging"
    elif any(x in name_lower for x in ['travel', 'weather', 'transit']):
        return "lifestyle"
    else:
        return "other"

def extract_topics(content):
    """萃取主題關鍵字"""
    topics = set()
    # 關鍵技術模式
    patterns = [
        r'(?i)(python|javascript|typescript|rust|go|java)\b',
        r'(?i)(fastapi|flask|django|express|nextjs|react|vue)\b',
        r'(?i)(mcp|agent|subagent|automation|workflow)\b',
        r'(?i)(api|rest|graphql|websocket|http)\b',
        r'(?i)(async|await|concurrent|parallel)\b',
        r'(?i)(database|postgresql|mysql|mongodb|redis)\b',
        r'(?i)(docker|kubernetes|cloud|aws|vercel)\b',
        r'(?i)(line|slack|discord|telegram|notification)\b',
        r'(?i)(ai|llm|gpt|claude|rag|embedding)\b',
        r'(?i)(scraping|crawler|parser|html|beautifulsoup)\b',
    ]
    for p in patterns:
        matches = re.findall(p, content)
        topics.update(matches)
    return list(topics)[:20]  # 限制數量

def extract_code_snippets(content):
    """萃取程式碼片段"""
    snippets = []
    # 尋找 ```python, ```bash, ```javascript 等代码块
    pattern = r'```(?:\w+)?\n(.{10,200}?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    for m in matches[:5]:  # 每個專案最多5個片段
        snippets.append(m.strip()[:150])
    return snippets

def extract_key_findings(content):
    """萃取關鍵發現"""
    findings = []
    # 尋找 ### 或 ## 標題
    pattern = r'(?:^#{1,3}\s+(.+)$)'
    matches = re.findall(pattern, content, re.MULTILINE)
    for m in matches[:10]:
        if len(m) > 10 and len(m) < 100:
            findings.append(m.strip())
    return findings

def extract_tools(content):
    """萃取提到的工具/庫"""
    tools = set()
    # 常見工具模式
    tool_patterns = [
        r'(?i)(playwright|puppeteer|selenium|beautifulsoup|scrapy)\b',
        r'(?i)(fastapi|flask|django|express|nextjs)\b',
        r'(?i)(openai|anthropic|claude|gemini|llama)\b',
        r'(?i)(docker|kubernetes|nginx|apache)\b',
        r'(?i)(postgresql|mysql|mongodb|redis|elasticsearch)\b',
        r'(?i)(github|gitlab|vercel|netlify|aws)\b',
        r'(?i)(line|slack|discord|telegram|whatsapp)\b',
        r'(?i)(n8n|zapier|make|ifttt)\b',
        r'(?i)(mcp|crewai|langchain|langgraph)\b',
    ]
    for p in tool_patterns:
        matches = re.findall(p, content)
        tools.update(matches)
    return list(tools)[:15]

def generate_report(all_info):
    """生成萃取報告"""
    report = []
    report.append("# 無盡學習系統 - 全部萃取精華\n")
    report.append(f"**萃取時間**: 2026-05-28\n")
    report.append(f"**專案總數**: {len(all_info)}\n")
    
    # 按領域分組
    by_domain = defaultdict(list)
    for info in all_info:
        by_domain[info['domain']].append(info)
    
    # 領域統計
    report.append("\n## 📊 領域分佈\n")
    report.append("| 領域 | 專案數 |")
    report.append("|------|--------|")
    for domain in sorted(by_domain.keys(), key=lambda x: -len(by_domain[x])):
        report.append(f"| {domain} | {len(by_domain[domain])} |")
    
    # 各領域詳情
    for domain in sorted(by_domain.keys()):
        projects = by_domain[domain]
        report.append(f"\n## 🔹 {domain.upper()} 領域 ({len(projects)}個專案)\n")
        
        # 彙總工具
        all_tools = set()
        all_topics = set()
        for p in projects:
            all_tools.update(p['tools_mentioned'])
            all_topics.update(p['topics'])
        
        report.append(f"**涵蓋技術**: {', '.join(sorted(all_topics)[:15])}\n")
        report.append(f"**相關工具**: {', '.join(sorted(all_tools)[:20])}\n")
        report.append("\n### 專案清單\n")
        
        for p in projects[:30]:  # 每領域最多30個
            report.append(f"- **{p['project']}** ({p['lines']}行)")
            if p['key_findings']:
                report.append(f"  - 關鍵: {' | '.join(p['key_findings'][:3])}")
        if len(projects) > 30:
            report.append(f"- ... 還有 {len(projects)-30} 個專案")
    
    # 全域熱門技術
    report.append("\n## 🌍 全域熱門技術統計\n")
    tool_count = defaultdict(int)
    topic_count = defaultdict(int)
    for info in all_info:
        for t in info['tools_mentioned']:
            tool_count[t.lower()] += 1
        for t in info['topics']:
            topic_count[t.lower()] += 1
    
    report.append("\n### 最常見工具/庫 Top 20\n")
    for tool, count in sorted(tool_count.items(), key=lambda x: -x[1])[:20]:
        report.append(f"- {tool}: {count}個專案")
    
    report.append("\n### 最常見主題 Top 20\n")
    for topic, count in sorted(topic_count.items(), key=lambda x: -x[1])[:20]:
        report.append(f"- {topic}: {count}個專案")
    
    return "\n".join(report)

def main():
    print("開始萃取所有專案記憶...")
    
    memory_files = get_memory_files()
    print(f"找到 {len(memory_files)} 個專案記憶檔案")
    
    all_info = []
    for i, (name, path) in enumerate(memory_files):
        if (i+1) % 10 == 0:
            print(f"處理中: {i+1}/{len(memory_files)}")
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            info = extract_key_info(name, content)
            all_info.append(info)
        except Exception as e:
            print(f"Error processing {name}: {e}")
    
    # 生成報告
    report = generate_report(all_info)
    OUTPUT_FILE.write_text(report, encoding='utf-8')
    print(f"\n✅ 萃取完成！報告已儲存至: {OUTPUT_FILE}")
    print(f"摘要: {len(all_info)} 個專案已處理")

if __name__ == "__main__":
    main()