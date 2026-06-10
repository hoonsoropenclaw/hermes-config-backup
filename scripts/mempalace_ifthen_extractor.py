#!/usr/bin/env python3
"""
MemPalace IF→THEN Pattern Auto-Extractor v1.0
自動從工作記錄中萃取 IF→THEN 經驗模式

功能：
1. 掃描 evolution/notes/ 中的學習報告
2. 使用正則表達式和關鍵詞匹配萃取 IF→THEN 模式
3. 自動存入 MemPalace
4. 支援批量處理和增量更新
"""

import re
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import sys

# ============ 配置 ============
WORKSPACE = Path.home() / ".openclaw" / "workspace"
NOTES_DIR = WORKSPACE / "evolution" / "notes"
OUTPUT_FILE = WORKSPACE / "evolution" / "notes" / "IF_THEN_EXTRACT_AUTO.md"
STATE_FILE = WORKSPACE / "evolution" / "notes" / ".ifthen_state.json"

# MemPalace API MCP 端點（通過文件系統介面）
MEMPALACE_WING = "learning_system"
MEMPALACE_ROOM = "if_then_experiences"

# ============ IF→THEN 模式定義 ============
# 領域關鍵詞映射
DOMAIN_PATTERNS = {
    "行政領域（Admin）": [
        "line bot", "line-bot", "學校行政", "學校通知", "行政", "公文",
        "docx", "word", "docuseal", "審批", "workflow", "请假", "行事曆"
    ],
    "瀏覽器自動化（Browser）": [
        "playwright", "puppeteer", "browser", "瀏覽器", "爬蟲", "scrap",
        "自動化登入", "截圖"
    ],
    "AI / Agent 系統": [
        "agent", "crewai", "langchain", "langgraph", "mcp", "ollama",
        "llm", "gpt", "claude", " autonomous"
    ],
    "金融領域（Finance）": [
        "stock", "股票", "期權", "option", "期貨", "future", "投資",
        "finance", "yfinance", "alpha vantage", "finnhub", "量化", "回測"
    ],
    "訊息平台（Messaging）": [
        "line", "discord", "telegram", "messenger", "通知", "push"
    ],
    "資料庫與後端": [
        "database", "sqlite", "postgresql", "mysql", "mongodb", "redis",
        "api", "fastapi", "flask", "async", "asyncio"
    ],
    "前端開發": [
        "react", "vue", "html", "css", "javascript", "typescript",
        "frontend", "ui", "ux", "antigravity"
    ],
    "系統架構": [
        "kubernetes", "docker", "ci/cd", "github actions", "devops",
        "microservice", "serverless", "部署"
    ]
}

# IF→THEN 萃取正則表達式
IF_THEN_PATTERNS = [
    # 標準 IF → THEN 格式
    (r'[Ii][Ff]\s*[→:]\s*(.{10,100}?)\s*[Tt][Hh][Ee][Nn]\s*[→:]\s*(.{10,200}?)', 'standard'),
    # "如果...就..." 格式
    (r'如果.{5,50}?[，,]\s*就.{10,200}?', 'chinese_if_then'),
    # "當...時，使用" 格式
    (r'當.{5,50}?[，,]\s*使用.{10,200}?', 'chinese_when_use'),
    # "情境：... 方案：..." 格式
    (r'情境[：:]\s*(.{10,100}?)\s*方案[：:]\s*(.{10,200}?)', 'scenario_solution'),
    # "遇到...問題，用..." 格式
    (r'遇到.{5,50}?\s*[,，]\s*用.{10,200}?', 'problem_solution'),
    # "使用...處理..." 格式
    (r'使用.{5,50}?\s*處理.{10,200}?', 'use_to_handle'),
]

# 工具/技術名稱萃取模式
TOOL_PATTERNS = [
    # 程式語言/框架
    (r'\b(Python|JavaScript|TypeScript|Go|Rust|Java|React|Vue|FastAPI|Flask|Django)\b', 'language_framework'),
    # 資料庫
    (r'\b(SQLite|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch)\b', 'database'),
    # 雲端服務
    (r'\b(AWS|Azure|GCP|Vercel|Netlify|Heroku)\b', 'cloud'),
    # AI/ML 工具
    (r'\b(OpenAI|Claude|GPT|Llama|Ollama|LangChain|CrewAI|MCP)\b', 'ai_ml'),
    # 特定工具
    (r'\b(line-bot-sdk|python-docx|pandas|numpy|playwright|puppeteer)\b', 'tool'),
]


@dataclass
class IfThenPattern:
    """IF→THEN 模式結構"""
    if_situation: str
    then_solution: str
    domain: str
    source_file: str
    extracted_at: str
    confidence: float  # 0.0 - 1.0
    
    def to_markdown_row(self) -> str:
        return f"| {self.if_situation} | {self.then_solution} | {self.domain} | {self.source_file} |"
    
    def to_aaak_format(self) -> str:
        return f"If → {self.if_situation}\nIF: {self.if_situation}\nTHEN: {self.then_solution}\nSOURCE: {self.source_file}"


class IfThenExtractor:
    """IF→THEN 模式萃取器"""
    
    def __init__(self):
        self.patterns: List[IfThenPattern] = []
        self.stats = {
            "files_scanned": 0,
            "patterns_found": 0,
            "by_domain": {}
        }
        
    def load_processed_files(self) -> set:
        """載入已處理的檔案列表"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    return set(state.get("processed_files", []))
            except:
                pass
        return set()
    
    def save_processed_files(self, files: set):
        """保存已處理的檔案列表"""
        state = {
            "processed_files": list(files),
            "last_updated": datetime.now().isoformat()
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def detect_domain(self, text: str) -> str:
        """根據文本內容檢測所屬領域"""
        text_lower = text.lower()
        scores = {}
        
        for domain, keywords in DOMAIN_PATTERNS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[domain] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "其他領域"
    
    def extract_patterns_from_text(self, text: str, source_file: str) -> List[IfThenPattern]:
        """從文本中萃取 IF→THEN 模式"""
        patterns = []
        
        for regex, pattern_type in IF_THEN_PATTERNS:
            matches = re.finditer(regex, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    if pattern_type == 'standard':
                        if_situation = match.group(1).strip()
                        then_solution = match.group(2).strip()
                    elif pattern_type in ['chinese_if_then', 'chinese_when_use']:
                        # 處理中文格式
                        full_match = match.group(0)
                        parts = re.split(r'[,，]', full_match)
                        if len(parts) >= 2:
                            if_situation = parts[0].strip()
                            then_solution = ','.join(parts[1:]).strip()
                        else:
                            continue
                    elif pattern_type == 'scenario_solution':
                        if_situation = match.group(1).strip()
                        then_solution = match.group(2).strip()
                    elif pattern_type in ['problem_solution', 'use_to_handle']:
                        full_match = match.group(0)
                        parts = re.split(r'[,，]', full_match)
                        if len(parts) >= 2:
                            if_situation = parts[0].strip()
                            then_solution = ','.join(parts[1:]).strip()
                        else:
                            continue
                    else:
                        continue
                    
                    # 過濾太短或無意義的匹配
                    if len(if_situation) < 10 or len(then_solution) < 10:
                        continue
                    if len(if_situation) > 200 or len(then_solution) > 300:
                        continue
                    
                    # 檢測領域
                    combined_text = if_situation + then_solution
                    domain = self.detect_domain(combined_text)
                    
                    # 計算置信度
                    confidence = self._calculate_confidence(if_situation, then_solution, pattern_type)
                    
                    pattern = IfThenPattern(
                        if_situation=self._clean_text(if_situation),
                        then_solution=self._clean_text(then_solution),
                        domain=domain,
                        source_file=source_file,
                        extracted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        confidence=confidence
                    )
                    patterns.append(pattern)
                    
                except Exception as e:
                    continue
        
        return patterns
    
    def _calculate_confidence(self, if_part: str, then_part: str, pattern_type: str) -> float:
        """計算萃取置信度"""
        confidence = 0.5  # 基礎置信度
        
        # 標準格式置信度更高
        if pattern_type == 'standard':
            confidence += 0.2
        
        # 包含工具名稱置信度更高
        tool_indicators = ['使用', '用', '透過', '透过', 'via', 'using', 'with']
        if any(ind in then_part for ind in tool_indicators):
            confidence += 0.1
        
        # 包含具體技術名稱
        tech_mentioned = False
        for _, tool_type in TOOL_PATTERNS:
            if re.search(r'\b[A-Z][a-z]+|[A-Z]{2,}\b', then_part):
                tech_mentioned = True
                break
        if tech_mentioned:
            confidence += 0.1
        
        # 過長的 IF 部分降低置信度
        if len(if_part) > 100:
            confidence -= 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多餘空白
        text = re.sub(r'\s+', ' ', text)
        # 移除 Markdown 鏈接但保留文字
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # 移除代碼標記
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text.strip()
    
    def extract_tools_from_text(self, text: str) -> List[str]:
        """萃取文本中的工具/技術名稱"""
        tools = set()
        for regex, tool_type in TOOL_PATTERNS:
            matches = re.findall(regex, text)
            tools.update(matches)
        return list(tools)
    
    def scan_notes_directory(self, incremental: bool = True) -> List[IfThenPattern]:
        """掃描 notes 目錄萃取模式"""
        processed_files = self.load_processed_files() if incremental else set()
        all_patterns = []
        
        # 獲取所有 markdown 文件
        md_files = list(NOTES_DIR.glob("*.md"))
        
        for md_file in md_files:
            # 跳過狀態文件
            if md_file.name.startswith('.'):
                continue
            # 跳過已處理的（增量模式）
            if incremental and md_file.name in processed_files:
                continue
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.stats["files_scanned"] += 1
                patterns = self.extract_patterns_from_text(content, md_file.name)
                
                # 去重（基於 IF 部分相似度）
                existing_if = {p.if_situation[:50] for p in all_patterns}
                for p in patterns:
                    if p.if_situation[:50] not in existing_if:
                        all_patterns.append(p)
                        self.stats["patterns_found"] += 1
                        
                        # 更新領域統計
                        domain = p.domain
                        self.stats["by_domain"][domain] = self.stats["by_domain"].get(domain, 0) + 1
                
                processed_files.add(md_file.name)
                
            except Exception as e:
                print(f"Error processing {md_file.name}: {e}", file=sys.stderr)
        
        self.save_processed_files(processed_files)
        self.patterns = all_patterns
        return all_patterns
    
    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式的萃取報告"""
        # 按領域分組
        by_domain = {}
        for p in self.patterns:
            if p.domain not in by_domain:
                by_domain[p.domain] = []
            by_domain[p.domain].append(p)
        
        # 按置信度排序
        for domain in by_domain:
            by_domain[domain].sort(key=lambda x: x.confidence, reverse=True)
        
        lines = [
            "# IF→THEN 經驗萃取（自動萃取）",
            "",
            f"## 萃取資訊",
            f"- 萃取時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 掃描檔案數：{self.stats['files_scanned']}",
            f"- 萃取模式數：{self.stats['patterns_found']}",
            f"- 增量更新：是",
            "",
            "---",
            ""
        ]
        
        # 按領域輸出
        for domain in sorted(by_domain.keys()):
            patterns = by_domain[domain]
            lines.append(f"## {domain}（{len(patterns)} 個模式）")
            lines.append("")
            lines.append("| IF 情境 | THEN 解決方案 | 來源 | 置信度 |")
            lines.append("|---------|--------------|------|--------|")
            
            for p in patterns[:20]:  # 每領域最多顯示20個
                conf_icon = "⭐" * int(p.confidence * 5) if p.confidence >= 0.6 else "☆" * int(p.confidence * 5)
                lines.append(f"| {p.if_situation[:80]} | {p.then_solution[:100]} | {p.source_file} | {conf_icon} |")
            
            lines.append("")
        
        # 工具/技術統計
        all_tools = set()
        for p in self.patterns:
            tools = self.extract_tools_from_text(p.then_solution)
            all_tools.update(tools)
        
        lines.append("---")
        lines.append("")
        lines.append("## 萃取的工具/技術統計")
        lines.append("")
        tools_list = sorted(all_tools)
        lines.append(", ".join(tools_list[:50]))
        if len(tools_list) > 50:
            lines.append(f"... 還有 {len(tools_list) - 50} 個")
        
        return "\n".join(lines)
    
    def save_report(self):
        """保存萃取報告"""
        report = self.generate_markdown_report()
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 報告已保存至：{OUTPUT_FILE}")
        print(f"   萃取 {self.stats['patterns_found']} 個 IF→THEN 模式")
    
    def get_patterns_for_mempalace(self) -> List[str]:
        """獲取可用於存入 MemPalace 的 AAAK 格式"""
        return [p.to_aaak_format() for p in self.patterns if p.confidence >= 0.6]


def main():
    """主函數"""
    print("🚀 MemPalace IF→THEN Pattern Auto-Extractor")
    print("=" * 50)
    
    extractor = IfThenExtractor()
    
    # 增量掃描
    print("\n📂 開始掃描 notes 目錄...")
    patterns = extractor.scan_notes_directory(incremental=True)
    
    print(f"\n📊 萃取統計：")
    print(f"   掃描檔案：{extractor.stats['files_scanned']}")
    print(f"   萃取模式：{extractor.stats['patterns_found']}")
    print(f"\n   按領域統計：")
    for domain, count in sorted(extractor.stats['by_domain'].items(), key=lambda x: -x[1]):
        print(f"     {domain}: {count}")
    
    # 保存報告
    extractor.save_report()
    
    # 顯示可用於 MemPalace 的模式
    mp_patterns = extractor.get_patterns_for_mempalace()
    print(f"\n📦 可存入 MemPalace 的高置信度模式：{len(mp_patterns)}")
    
    return extractor


if __name__ == "__main__":
    main()
