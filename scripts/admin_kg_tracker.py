#!/usr/bin/env python3
"""
行政決策知識圖譜自動追蹤系統
Admin Decision Knowledge Graph Auto-Tracker

功能：
1. 自動掃描 LINE 對話記錄，提取行政決策
2. 將決策添加到 MemPalace 知識圖譜
3. 建立決策 → 背景 → 結果 的追蹤鏈
4. 生成 if_then 經驗規則

使用方式：
    python3 admin_kg_tracker.py scan      # 掃描並提取決策
    python3 admin_kg_tracker.py add <text> # 手動添加決策
    python3 admin_kg_tracker.py query <entity> # 查詢實體
    python3 admin_kg_tracker.py rules      # 生成 if_then 規則
"""

import os
import re
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

# ============================================================================
# 配置
# ============================================================================
WORKSPACE = Path.home() / ".openclaw" / "workspace"
LINE_LOGS_DIR = WORKSPACE / "line_logs"
MEMORY_DIR = WORKSPACE / "memory"
KG_DB = str(Path.home() / ".mempalace" / "knowledge_graph.sqlite3")
OUTPUT_DIR = WORKSPACE / "mempalace_sync" / "admin_kg"

# 決策關鍵詞
DECISION_KEYWORDS = [
    "決定", " Decision", "確認", "核准", "通過",
    "採用", "選用", "批准", "同意", "通過",
    "最終", "結果是", "那就", "好吧", "OK",
    "沒問題", "可以", "就這樣"
]

# 行政類型關鍵詞
ADMIN_TYPES = {
    "请假": ["请假", "休假", "排假", "請假"],
    "人事": ["人事", "人員", "聘用", "離職", "異動"],
    "會議": ["會議", "meeting", "開會", "討論"],
    "採購": ["採購", "購買", "招標", "報價"],
    "活動": ["活動", "event", "校慶", "典禮"],
    "表單": ["表單", "文件", "報表", "資料"],
}

# 創建輸出目錄
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# 數據類型
# ============================================================================
@dataclass
class AdminDecision:
    """行政決策結構"""
    id: str
    timestamp: str
    decision_text: str
    admin_type: str
    context: str
    outcome: str
    persons_involved: List[str]
    importance: int  # 1-5
    source: str
    if_then_rule: str = ""

@dataclass
class KGTriple:
    """知識圖譜三元組"""
    subject: str
    predicate: str
    obj: str
    valid_from: str
    created_at: str

# ============================================================================
# 決策提取器
# ============================================================================
class DecisionExtractor:
    """從各種來源提取行政決策"""
    
    def __init__(self):
        self.decision_keywords = DECISION_KEYWORDS
        self.admin_types = ADMIN_TYPES
    
    def extract_from_text(self, text: str, source: str = "unknown") -> List[AdminDecision]:
        """從文字中提取決策"""
        decisions = []
        lines = text.split('\n')
        
        current_context = []
        current_type = "一般"
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 檢測是否是決策行
            is_decision = any(kw in line for kw in self.decision_keywords)
            
            # 檢測行政類型
            detected_type = self._detect_admin_type(line)
            if detected_type:
                current_type = detected_type
            
            if is_decision:
                # 提取相關上下文（前後各2行）
                start_idx = max(0, i - 2)
                end_idx = min(len(lines), i + 3)
                context = '\n'.join(lines[start_idx:end_idx])
                
                # 提取涉及人員
                persons = self._extract_persons(line + context)
                
                # 估計重要性
                importance = self._estimate_importance(line, context)
                
                decision = AdminDecision(
                    id=f"dec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}",
                    timestamp=datetime.now().isoformat(),
                    decision_text=line,
                    admin_type=current_type,
                    context=context,
                    outcome="",  # 待後續追蹤
                    persons_involved=persons,
                    importance=importance,
                    source=source
                )
                
                decisions.append(decision)
        
        return decisions
    
    def _detect_admin_type(self, text: str) -> Optional[str]:
        """檢測行政類型"""
        text_lower = text.lower()
        
        for admin_type, keywords in self.admin_types.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return admin_type
        return None
    
    def _extract_persons(self, text: str) -> List[str]:
        """提取涉及人員（簡單正則匹配）"""
        # 匹配常見人員提及
        patterns = [
            r'@[a-zA-Z0-9_]+',  # @mentions
            r'[A-Z][a-z]+',      # 英文名字
            r'老師',              # 老師
            r'主任',              # 主任
            r'組長',              # 組長
        ]
        
        persons = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            persons.extend(matches[:3])  # 限制數量
        
        return list(set(persons))[:5]  # 去重，最多5人
    
    def _estimate_importance(self, decision: str, context: str) -> int:
        """估計決策重要性"""
        importance = 3  # 默認中等
        
        # 高重要性指標
        high_importance = ["全校", "緊急", "重要", "年度", " budget", "請假"]
        for kw in high_importance:
            if kw in decision or kw in context:
                importance = max(importance, 4)
        
        # 檢查是否有後果描述
        if any(w in context for w in ["將", "會", "必須", "should", "must"]):
            importance = max(importance, 4)
        
        return min(importance, 5)

# ============================================================================
# 知識圖譜管理器
# ============================================================================
class AdminKGManager:
    """行政知識圖譜管理器"""
    
    def __init__(self, db_path: str = KG_DB):
        self.db_path = db_path
        self._ensure_connection()
    
    def _ensure_connection(self):
        """確保資料庫連接"""
        if not os.path.exists(self.db_path):
            print(f"⚠️ KG DB 不存在: {self.db_path}")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 檢查表結構
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'kg_%'
            """)
            tables = [r[0] for r in cursor.fetchall()]
            
            if not tables:
                print(f"⚠️ KG DB 沒有 kg_ 表")
                self.conn = None
            else:
                self.conn = conn
                
        except Exception as e:
            print(f"❌ KG DB 連接失敗: {e}")
            self.conn = None
    
    def add_triple(self, subject: str, predicate: str, obj: str, 
                   valid_from: str = None) -> bool:
        """添加三元組到 KG"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO kg_triples (subject, predicate, object, valid_from, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (subject, predicate, obj, 
                  valid_from or datetime.now().strftime("%Y-%m-%d"),
                  datetime.now().isoformat()))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 添加三元組失敗: {e}")
            return False
    
    def query(self, entity: str, depth: int = 1) -> List[KGTriple]:
        """查詢實體關係"""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT subject, predicate, object, valid_from, created_at
                FROM kg_triples 
                WHERE subject = ? OR object = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (entity, entity))
            
            results = []
            for r in cursor.fetchall():
                results.append(KGTriple(
                    subject=r[0], predicate=r[1], obj=r[2],
                    valid_from=r[3] or "", created_at=r[4]
                ))
            
            return results
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
            return []
    
    def add_decision_to_kg(self, decision: AdminDecision) -> bool:
        """將決策添加到 KG"""
        if not self.conn:
            return False
        
        success = True
        
        # 添加主決策三元組
        self.add_triple(
            "行政系統",
            f"做出{dimension}",
            decision.decision_text[:100]
        )
        
        # 添加類型關係
        self.add_triple(
            decision.decision_text[:50],
            "是",
            f"{decision.admin_type}類型"
        )
        
        # 添加涉及人員
        for person in decision.persons_involved[:3]:
            self.add_triple(
                decision.decision_text[:50],
                "涉及",
                person
            )
        
        # 添加時間關係
        self.add_triple(
            decision.decision_text[:50],
            "記錄於",
            decision.timestamp[:10]
        )
        
        return success

# ============================================================================
# If-Then 規則生成器
# ============================================================================
class IfThenRuleGenerator:
    """生成 if_then 經驗規則"""
    
    def __init__(self):
        self.rules = []
    
    def generate_from_decision(self, decision: AdminDecision) -> str:
        """從決策生成 if_then 規則"""
        # 根據決策類型生成規則模板
        rule = ""
        
        if decision.admin_type == "请假":
            rule = self._generate_leave_rule(decision)
        elif decision.admin_type == "會議":
            rule = self._generate_meeting_rule(decision)
        elif decision.admin_type == "人事":
            rule = self._generate_hr_rule(decision)
        elif decision.admin_type == "採購":
            rule = self._generate_purchase_rule(decision)
        else:
            rule = self._generate_general_rule(decision)
        
        return rule
    
    def _generate_leave_rule(self, decision: AdminDecision) -> str:
        """生成請假規則"""
        return f"""
IF [請假申請] AND [原因包含：{', '.join(decision.persons_involved[:2])}]
THEN [審核流程：{decision.outcome or '待追蹤'}]
CONTEXT: {decision.context[:100]}
"""
    
    def _generate_meeting_rule(self, decision: AdminDecision) -> str:
        """生成會議規則"""
        return f"""
IF [召開會議] AND [議題包含：{', '.join(decision.persons_involved[:2])}]
THEN [會議結論：{decision.decision_text[:80]}]
CONTEXT: {decision.context[:100]}
"""
    
    def _generate_hr_rule(self, decision: AdminDecision) -> str:
        """生成人事規則"""
        return f"""
IF [人事異動] AND [人員：{', '.join(decision.persons_involved[:2])}]
THEN [處理方式：{decision.decision_text[:80]}]
"""
    
    def _generate_purchase_rule(self, decision: AdminDecision) -> str:
        """生成採購規則"""
        return f"""
IF [採購需求] AND [預算相關]
THEN [審核結果：{decision.decision_text[:80]}]
"""
    
    def _generate_general_rule(self, decision: AdminDecision) -> str:
        """生成一般規則"""
        return f"""
IF [行政決策] AND [類型：{decision.admin_type}]
THEN [結論：{decision.decision_text[:80]}]
"""
    
    def save_rules(self, rules: List[str], output_path: str):
        """保存規則到檔案"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# If-Then 行政經驗規則\n")
            f.write(f"# 生成時間：{datetime.now().isoformat()}\n")
            f.write("# ===================\n\n")
            
            for i, rule in enumerate(rules, 1):
                f.write(f"## 規則 {i}\n")
                f.write(rule)
                f.write("\n" + "="*50 + "\n\n")

# ============================================================================
# 主程式
# ============================================================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="行政決策 KG 自動追蹤系統"
    )
    parser.add_argument(
        "--action", "-a",
        choices=["scan", "add", "query", "rules", "stats"],
        default="stats",
        help="操作"
    )
    parser.add_argument("--text", "-t", help="決策文字")
    parser.add_argument("--entity", "-e", help="查詢實體")
    parser.add_argument("--source", "-s", default="manual", help="來源")
    parser.add_argument("--type", default="一般", help="決策類型")
    
    args = parser.parse_args()
    
    extractor = DecisionExtractor()
    kg_manager = AdminKGManager()
    rule_gen = IfThenRuleGenerator()
    
    if args.action == "stats":
        print("📊 行政決策 KG 追蹤系統狀態")
        print("=" * 50)
        
        # KG 狀態
        if os.path.exists(KG_DB):
            print(f"✅ KG 資料庫：已連接")
            print(f"   路徑：{KG_DB}")
            
            # 查詢一些統計
            try:
                conn = sqlite3.connect(KG_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM kg_triples")
                count = cursor.fetchone()[0]
                print(f"   三元組數量：{count}")
                conn.close()
            except:
                pass
        else:
            print(f"❌ KG 資料庫：未找到")
        
        print(f"\n📁 輸出目錄：{OUTPUT_DIR}")
        print(f"\n🔑 決策關鍵詞：{len(DECISION_KEYWORDS)} 個")
        print(f"📂 行政類型：{len(ADMIN_TYPES)} 種")
        
        # 最近的規則檔案
        rules_file = os.path.join(OUTPUT_DIR, "if_then_rules.md")
        if os.path.exists(rules_file):
            import stat
            st = os.stat(rules_file)
            mtime = datetime.fromtimestamp(st.st_mtime).isoformat()
            print(f"\n📜 If-Then 規則檔案：存在（{mtime}）")
    
    elif args.action == "scan":
        print("🔍 掃描行政決策...")
        
        all_decisions = []
        
        # 掃描 LINE 日誌
        if LINE_LOGS_DIR.exists():
            for log_file in sorted(LINE_LOGS_DIR.glob("*.json"))[-5:]:  # 最近5個
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 提取訊息文字
                    if isinstance(data, list):
                        for msg in data:
                            if isinstance(msg, dict) and 'text' in msg:
                                decisions = extractor.extract_from_text(
                                    msg['text'], 
                                    f"line:{log_file.name}"
                                )
                                all_decisions.extend(decisions)
                except Exception as e:
                    print(f"⚠️ 讀取 {log_file} 失敗: {e}")
        
        # 掃描每日記憶
        if MEMORY_DIR.exists():
            for mem_file in sorted(MEMORY_DIR.glob("*.md"))[-5:]:
                try:
                    content = mem_file.read_text(encoding='utf-8')
                    decisions = extractor.extract_from_text(
                        content,
                        f"memory:{mem_file.name}"
                    )
                    all_decisions.extend(decisions)
                except Exception as e:
                    print(f"⚠️ 讀取 {mem_file} 失敗: {e}")
        
        print(f"✅ 找到 {len(all_decisions)} 個潛在決策")
        
        # 添加到 KG 並生成規則
        rules = []
        for dec in all_decisions:
            kg_manager.add_decision_to_kg(dec)
            rule = rule_gen.generate_from_decision(dec)
            rules.append(rule)
        
        # 保存規則
        if rules:
            rules_file = os.path.join(OUTPUT_DIR, "if_then_rules.md")
            rule_gen.save_rules(rules, rules_file)
            print(f"✅ 保存 {len(rules)} 條 if_then 規則到 {rules_file}")
    
    elif args.action == "add":
        if not args.text:
            print("❌ 需要 --text 參數")
            return
        
        print(f"➕ 添加決策：{args.text[:50]}...")
        
        decisions = extractor.extract_from_text(args.text, args.source)
        
        if decisions:
            for dec in decisions:
                dec.admin_type = args.type
                kg_manager.add_decision_to_kg(dec)
                rule = rule_gen.generate_from_decision(dec)
                print(f"✅ 已添加並生成規則：{rule[:100]}...")
            
            # 保存規則
            rules_file = os.path.join(OUTPUT_DIR, "if_then_rules.md")
            with open(rules_file, 'a', encoding='utf-8') as f:
                f.write(f"\n## 新規則 - {datetime.now().isoformat()}\n")
                f.write(rule_gen.generate_from_decision(decisions[0]))
            print(f"✅ 規則已保存")
        else:
            print("⚠️ 未提取到決策")
    
    elif args.action == "query":
        if not args.entity:
            print("❌ 需要 --entity 參數")
            return
        
        print(f"🔍 查詢實體：{args.entity}")
        
        triples = kg_manager.query(args.entity)
        
        if triples:
            print(f"\n找到 {len(triples)} 條關係：")
            for t in triples[:10]:
                print(f"  {t.subject} --[{t.predicate}]--> {t.obj}")
        else:
            print("未找到關係")
    
    elif args.action == "rules":
        rules_file = os.path.join(OUTPUT_DIR, "if_then_rules.md")
        
        if os.path.exists(rules_file):
            print(f"📜 If-Then 規則檔案：{rules_file}")
            print("-" * 50)
            print(open(rules_file, encoding='utf-8').read()[:2000])
        else:
            print("⚠️ 規則檔案不存在，請先執行 scan")

if __name__ == "__main__":
    main()
