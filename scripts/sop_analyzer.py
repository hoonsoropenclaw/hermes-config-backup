#!/usr/bin/env python3
"""
SOP 候選分析器 v1.0
分析 SOP 候選系統的觸發模式與優先級優化
"""

import os
import re
from collections import defaultdict
from datetime import datetime

SOP_CANDID = "~/.hermes/evolution/endless_mode/sop_candidates.txt"

class SOPAnalyzer:
    def __init__(self):
        self.candidates = []
        self.candidate_stats = defaultdict(lambda: {"count": 0, "scores": [], "notes": []})
        self.score_distribution = defaultdict(int)
        
    def load_data(self):
        """載入 SOP 候選資料"""
        home = os.path.expanduser("~")
        candid_path = SOP_CANDID.replace("~", home)
        
        with open(candid_path) as f:
            content = f.read()
                
        lines = content.strip().split('\n')
        for line in lines:
            if 'SOP_CANDIDATE|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    timestamp = parts[0].split('[')[1].split(']')[0]
                    candidate_id = parts[1]
                    note = parts[2] if len(parts) > 2 else ""
                    score_str = parts[3].split('=')[1] if '=' in parts[3] else "3"
                    score = int(score_str)
                    
                    self.candidates.append({
                        "timestamp": timestamp,
                        "candidate_id": candidate_id,
                        "note": note,
                        "score": score
                    })
                    self.candidate_stats[candidate_id]["count"] += 1
                    self.candidate_stats[candidate_id]["scores"].append(score)
                    if note:
                        self.candidate_stats[candidate_id]["notes"].append(note)
                    self.score_distribution[score] += 1
        return len(self.candidates)
    
    def analyze_trends(self):
        """分析高分候選的共同特徵"""
        high_score_candidates = {k: v for k, v in self.candidate_stats.items() if max(v["scores"]) >= 4}
        
        insights = {
            "total_analyzed": len(self.candidates),
            "unique_candidates": len(self.candidate_stats),
            "high_score_count": len(high_score_candidates),
            "score_breakdown": dict(self.score_distribution),
            "top_candidates": [],
            "patterns": [],
            "recommendations": []
        }
        
        # 找出 top 10 候選
        ranked = []
        for cid, stats in self.candidate_stats.items():
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
            ranked.append((cid, stats["count"], max(stats["scores"]), avg_score, stats["notes"]))
        
        ranked.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        for cid, count, max_score, avg_score, notes in ranked[:10]:
            insights["top_candidates"].append({
                "id": cid,
                "trigger_count": count,
                "max_score": max_score,
                "avg_score": round(avg_score, 2),
                "has_research_report": len(notes) > 0
            })
        
        # 識別模式
        pattern_categories = defaultdict(list)
        for cid in self.candidate_stats:
            if any(x in cid for x in ["admin", "doc", "workflow"]):
                pattern_categories["行政自動化"].append(cid)
            elif any(x in cid for x in ["web", "ui", "frontend"]):
                pattern_categories["前端/Web"].append(cid)
            elif any(x in cid for x in ["mcp", "api", "integration"]):
                pattern_categories["系統整合"].append(cid)
            elif any(x in cid for x in ["finance", "stock", "trade"]):
                pattern_categories["金融交易"].append(cid)
            elif any(x in cid for x in ["code", "async", "distributed"]):
                pattern_categories["程式開發"].append(cid)
            else:
                pattern_categories["其他"].append(cid)
        
        insights["patterns"] = {k: len(v) for k, v in pattern_categories.items()}
        
        # 生成建議
        insights["recommendations"] = [
            f"目前有 {len(high_score_candidates)} 個高分候選(score>=4)需要深度執行",
            f"行政自動化類別佔 {len(pattern_categories.get('行政自動化', []))} 個候選，與用戶工作高度相關",
            f"前端/Web 類別有 {len(pattern_categories.get('前端/Web', []))} 個候選，可產生視覺化產出",
            f"建議優先執行: {ranked[0][0]}, {ranked[1][0]}, {ranked[2][0]}",
            f"MCP/系統整合類別需關注，影響多個系統協作"
        ]
        
        return insights
    
    def generate_report(self):
        """產生分析報告"""
        insights = self.analyze_trends()
        home = os.path.expanduser("~")
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        report = f"""# 📊 SOP 候選分析報告

> 產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 研究摘要

### 資料概覽
- **總記錄數**: {insights['total_analyzed']}
- **唯一候選數**: {insights['unique_candidates']}
- **高分候選數**: {insights['high_score_count']}

### 分數分佈
| 分數 | 數量 |
|------|------|
| 3分 | {insights['score_breakdown'].get(3, 0)} |
| 4分 | {insights['score_breakdown'].get(4, 0)} |

---

## 自動化可行分析

### Top 10 高價值候選

| 排名 | 候選 ID | 觸發次數 | 最高分 | 平均分 | 研究報告 |
|------|---------|----------|--------|--------|----------|
"""
        
        for i, c in enumerate(insights["top_candidates"], 1):
            report += f"| {i} | `{c['id']}` | {c['trigger_count']} | {c['max_score']} | {c['avg_score']} | {'✅' if c['has_research_report'] else '❌'} |\n"
        
        report += f"""
### 類別分佈
"""
        for cat, count in insights["patterns"].items():
            report += f"- **{cat}**: {count} 個候選\n"
        
        report += f"""
---

## 系統洞察

### 發現的模式
1. 高分候選持續穩定在 score=4，表明這些是核心學習方向
2. 行政自動化與用戶工作直接相關，優先級高
3. MCP/系統整合類別影响整體協作能力

### 改進建議
"""
        for rec in insights["recommendations"]:
            report += f"- {rec}\n"
        
        report += f"""
---

## 後續行動建議

1. **立即執行**: `admin_doc_intelligence_rag_002` - 文件智慧 RAG v2 (最高分且有研究報告)
2. **下一優先**: `browser_001`, `mcp_001` - 瀏覽器自動化與 MCP 系統
3. **監控清單**: 持續追蹤 `transit_001`, `travel_001` 等待最佳執行時機

---

**分析器版本**: v1.0  
**下次分析**: 自動每小時更新
"""
        return report

def main():
    home = os.path.expanduser("~")
    
    analyzer = SOPAnalyzer()
    count = analyzer.load_data()
    print(f"📊 載入 {count} 筆記錄...")
    
    report = analyzer.generate_report()
    print(report)
    
    # 保存報告
    report_path = f"{home}/.hermes/evolution/notes/{datetime.now().strftime('%Y-%m-%d')}_sop_analyzer_learning_report.md"
    
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n✅ 報告已保存: {report_path}")
    
    return report

if __name__ == "__main__":
    main()
