#!/usr/bin/env python3
"""
MemPalace KG Auto-Expander v1.0
自動擴展知識圖譜的實體和關係

功能：
1. 掃描專案目錄，自動識別技術棧
2. 從學習報告中萃取實體和關係
3. 生成 KG 事實三元組
4. 批量存入 MemPalace
"""

import re
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from collections import defaultdict
import sys

# ============ 配置 ============
WORKSPACE = Path.home() / ".openclaw" / "workspace"
NOTES_DIR = WORKSPACE / "evolution" / "notes"
PROJECTS_DIR = WORKSPACE / "evolution" / "endless_mode" / "projects"
OUTPUT_FILE = WORKSPACE / "evolution" / "notes" / "KG_AUTO_EXTRACT.md"

# 關係類型定義
RELATION_TYPES = {
    # 技術關係
    "uses": ["使用", "uses", "utilizes", "employs"],
    "enables": ["使能", "enables", "allows", "facilitates"],
    "depends_on": ["依賴", "depends_on", "requires", "needs"],
    "works_with": ["配合", "works_with", "integrates_with", "combines"],
    
    # 領域關係
    "domain": ["領域", "domain", "area", "field"],
    "solves": ["解決", "solves", "handles", "manages"],
    "produces": ["產生", "produces", "creates", "generates"],
    
    # 組織關係
    "belongs_to": ["屬於", "belongs_to", "part_of"],
    "implements": ["實現", "implements", "realizes"],
    "completes": ["完成", "completes", "finishes"],
}

# 實體類型關鍵詞
ENTITY_TYPE_KEYWORDS = {
    "Framework": ["FastAPI", "Flask", "Django", "React", "Vue", "LangChain", "CrewAI", "LangGraph", "Next.js"],
    "Language": ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "SQL"],
    "Database": ["SQLite", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch"],
    "Cloud": ["AWS", "Azure", "GCP", "Vercel", "Netlify", "Heroku", "Docker", "Kubernetes"],
    "AI_ML": ["OpenAI", "Claude", "GPT", "Llama", "Ollama", "Gemini", "LLaVA"],
    "Tool": ["Playwright", "Puppeteer", "LINE Bot SDK", "python-docx", "pandas"],
    "Platform": ["LINE", "Discord", "Telegram", "GitHub", "Google Calendar"],
}


@dataclass
class Entity:
    """實體結構"""
    name: str
    entity_type: str
    sources: List[str]
    first_seen: str
    
    def to_triple_subject(self) -> str:
        return self.name


@dataclass
class Relationship:
    """關係結構"""
    subject: str
    predicate: str
    object: str
    relation_type: str
    confidence: float
    source: str
    
    def to_kg_format(self) -> str:
        return f"({self.subject}) --[{self.predicate}]--> ({self.object})"


class KGExpander:
    """知識圖譜自動擴展器"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.stats = {
            "entities_found": 0,
            "relationships_found": 0,
            "files_scanned": 0,
            "by_type": defaultdict(int)
        }
        
    def _detect_entity_type(self, name: str) -> str:
        """檢測實體類型"""
        for etype, keywords in ENTITY_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in name.lower():
                    return etype
        return "Unknown"
    
    def _detect_relation_type(self, text: str) -> Optional[str]:
        """檢測關係類型"""
        text_lower = text.lower()
        for rtype, keywords in RELATION_TYPES.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return rtype
        return None
    
    def _extract_entities_from_text(self, text: str, source: str) -> List[Entity]:
        """從文本中萃取實體"""
        entities = []
        seen_names = set()
        
        # 使用 Entity_TYPE_KEYWORDS 萃取
        for etype, keywords in ENTITY_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text.lower() and kw not in seen_names:
                    # 驗證是否真正出現
                    pattern = rf'\b{re.escape(kw)}\b'
                    if re.search(pattern, text, re.IGNORECASE):
                        entity = Entity(
                            name=kw,
                            entity_type=etype,
                            sources=[source],
                            first_seen=datetime.now().strftime("%Y-%m-%d")
                        )
                        entities.append(entity)
                        seen_names.add(kw)
                        self.entities[kw] = entity
                        self.stats["entities_found"] += 1
                        self.stats["by_type"][etype] += 1
        
        return entities
    
    def _extract_relationships_from_text(self, text: str, source: str) -> List[Relationship]:
        """從文本中萃取關係"""
        relationships = []
        
        # 遍歷所有實體對
        entity_names = list(self.entities.keys())
        
        for i, entity1 in enumerate(entity_names):
            for entity2 in entity_names[i+1:]:
                # 檢查兩個實體是否在文本中同時出現且距離較近
                pattern = rf'{re.escape(entity1)}.{5,100}?{re.escape(entity2)}'
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                if matches:
                    # 檢測關係類型
                    relation_type = self._detect_relation_type(text)
                    if relation_type:
                        # 計算置信度
                        distance = len(matches[0])
                        confidence = min(1.0, 50 / distance) if distance > 50 else 1.0
                        
                        rel = Relationship(
                            subject=entity1,
                            predicate=relation_type,
                            object=entity2,
                            relation_type=relation_type,
                            confidence=confidence,
                            source=source
                        )
                        relationships.append(rel)
                        self.relationships.append(rel)
                        self.stats["relationships_found"] += 1
        
        return relationships
    
    def _infer_relationships(self):
        """推斷隱含關係"""
        # 基於類型的推断
        type_hierarchies = {
            "Language": {
                "uses": ["Framework", "Tool"],
                "depends_on": ["Database"],
            },
            "Framework": {
                "uses": ["Tool"],
                "enables": ["Platform"],
            },
            "AI_ML": {
                "uses": ["Cloud"],
                "enables": ["Framework"],
            }
        }
        
        for entity in self.entities.values():
            if entity.entity_type in type_hierarchies:
                hierarchies = type_hierarchies[entity.entity_type]
                for relation, target_types in hierarchies.items():
                    for target_type in target_types:
                        for other_entity in self.entities.values():
                            if other_entity.entity_type == target_type:
                                # 檢查是否已存在
                                exists = any(
                                    r.subject == entity.name and 
                                    r.object == other_entity.name and 
                                    r.predicate == relation
                                    for r in self.relationships
                                )
                                if not exists:
                                    rel = Relationship(
                                        subject=entity.name,
                                        predicate=relation,
                                        object=other_entity.name,
                                        relation_type=relation,
                                        confidence=0.6,  # 推斷的置信度較低
                                        source="inferred"
                                    )
                                    self.relationships.append(rel)
    
    def scan_projects(self) -> Dict[str, List[str]]:
        """掃描專案目錄，識別技術棧"""
        tech_stack = defaultdict(list)
        
        # 掃描 projects 目錄
        if PROJECTS_DIR.exists():
            for item in PROJECTS_DIR.iterdir():
                if item.is_dir():
                    project_name = item.name
                    techs = self._scan_project_dir(item)
                    if techs:
                        tech_stack[project_name] = techs
        
        return tech_stack
    
    def _scan_project_dir(self, project_dir: Path) -> List[str]:
        """掃描單個專案目錄"""
        techs = []
        
        # 讀取 progress.md 獲取技術棧資訊
        progress_file = project_dir / "progress.md"
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 萃取實體
                self._extract_entities_from_text(content, progress_file.name)
                
                # 萃取技術名稱
                for etype, keywords in ENTITY_TYPE_KEYWORDS.items():
                    for kw in keywords:
                        if kw.lower() in content.lower():
                            techs.append(kw)
                            
            except Exception as e:
                print(f"Error reading {progress_file}: {e}", file=sys.stderr)
        
        # 掃描 Python 文件
        for py_file in project_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._extract_entities_from_text(content, py_file.name)
            except:
                pass
        
        # 掃描 JavaScript 文件
        for js_file in project_dir.rglob("*.js"):
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._extract_entities_from_text(content, js_file.name)
            except:
                pass
        
        return list(set(techs))
    
    def scan_notes(self) -> int:
        """掃描 notes 目錄"""
        files_processed = 0
        
        for md_file in NOTES_DIR.glob("*.md"):
            if md_file.name.startswith('.'):
                continue
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self._extract_entities_from_text(content, md_file.name)
                self._extract_relationships_from_text(content, md_file.name)
                files_processed += 1
                self.stats["files_scanned"] += 1
                
            except Exception as e:
                print(f"Error processing {md_file.name}: {e}", file=sys.stderr)
        
        return files_processed
    
    def generate_report(self) -> str:
        """生成 KG 擴展報告"""
        lines = [
            "# 知識圖譜自動擴展報告",
            "",
            f"## 擴展資訊",
            f"- 擴展時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 掃描檔案：{self.stats['files_scanned']}",
            f"- 發現實體：{self.stats['entities_found']}",
            f"- 發現關係：{self.stats['relationships_found']}",
            "",
            "---",
            "",
            "## 實體統計（按類型）",
            ""
        ]
        
        # 按類型分組
        by_type = defaultdict(list)
        for entity in self.entities.values():
            by_type[entity.entity_type].append(entity.name)
        
        for etype in sorted(by_type.keys()):
            names = sorted(by_type[etype])
            lines.append(f"### {etype} ({len(names)})")
            lines.append(", ".join(names))
            lines.append("")
        
        # 關係列表
        lines.append("---")
        lines.append("")
        lines.append("## 關係三元組")
        lines.append("")
        
        # 按關係類型分組
        by_rel_type = defaultdict(list)
        for rel in self.relationships:
            by_rel_type[rel.relation_type].append(rel)
        
        for rtype in sorted(by_rel_type.keys()):
            rels = by_rel_type[rtype]
            lines.append(f"### {rtype} ({len(rels)})")
            lines.append("")
            
            for rel in rels[:15]:  # 每類最多顯示15個
                lines.append(f"- ({rel.subject}) --[{rel.predicate}]--> ({rel.object})")
            if len(rels) > 15:
                lines.append(f"- ... 還有 {len(rels) - 15} 個")
            lines.append("")
        
        # 高置信度關係（用於 MemPalace）
        high_conf = [r for r in self.relationships if r.confidence >= 0.7]
        lines.append("---")
        lines.append("")
        lines.append(f"## 高置信度關係（用於 MemPalace KG）共 {len(high_conf)} 個")
        lines.append("")
        
        for rel in sorted(high_conf, key=lambda x: -x.confidence)[:20]:
            lines.append(f"- **{rel.subject}** `{rel.predicate}` **{rel.object}**")
        
        return "\n".join(lines)
    
    def save_report(self):
        """保存報告"""
        report = self.generate_report()
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ KG 擴展報告已保存至：{OUTPUT_FILE}")
        print(f"   發現 {self.stats['entities_found']} 個實體")
        print(f"   發現 {self.stats['relationships_found']} 個關係")
    
    def get_kg_triples_for_mempalace(self) -> List[Dict]:
        """獲取可用於存入 MemPalace KG 的三元組"""
        triples = []
        for rel in self.relationships:
            if rel.confidence >= 0.6 and rel.source != "inferred":
                triples.append({
                    "subject": rel.subject,
                    "predicate": rel.predicate,
                    "object": rel.object,
                    "confidence": rel.confidence,
                    "source": rel.source
                })
        return triples
    
    def get_entities_for_mempalace(self) -> List[Dict]:
        """獲取可用於存入 MemPalace 的實體"""
        entities = []
        for entity in self.entities.values():
            entities.append({
                "name": entity.name,
                "type": entity.entity_type,
                "sources": entity.sources
            })
        return entities


def main():
    """主函數"""
    print("🚀 MemPalace KG Auto-Expander")
    print("=" * 50)
    
    expander = KGExpander()
    
    # 掃描專案目錄
    print("\n📂 掃描專案目錄...")
    tech_stack = expander.scan_projects()
    print(f"   掃描 {len(tech_stack)} 個專案")
    
    # 掃描 notes 目錄
    print("\n📂 掃描 notes 目錄...")
    files = expander.scan_notes()
    print(f"   處理 {files} 個檔案")
    
    # 推斷關係
    print("\n🧠 推斷隱含關係...")
    expander._infer_relationships()
    
    print(f"\n📊 擴展統計：")
    print(f"   發現實體：{expander.stats['entities_found']}")
    print(f"   發現關係：{expander.stats['relationships_found']}")
    print(f"\n   按類型統計：")
    for etype, count in sorted(expander.stats['by_type'].items(), key=lambda x: -x[1]):
        print(f"     {etype}: {count}")
    
    # 保存報告
    expander.save_report()
    
    # 顯示可用於 MemPalace 的資料
    kg_triples = expander.get_kg_triples_for_mempalace()
    print(f"\n📦 可存入 MemPalace KG 的三元組：{len(kg_triples)}")
    
    return expander


if __name__ == "__main__":
    main()
