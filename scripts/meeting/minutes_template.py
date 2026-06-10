#!/usr/bin/env python3
"""
會議紀錄範本產生器 - 產生標準化的會議紀錄格式
支援輸出：Word (.docx)、Markdown (.md)、HTML (.html)、JSON (.json)
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class MinutesTemplate:
    """會議紀錄範本產生器"""
    
    def __init__(self, template_name: str = "standard"):
        self.template_name = template_name
        self.templates = {
            "standard": self._standard_template,
            "school": self._school_template,
            "formal": self._formal_template,
            "brief": self._brief_template,
        }
    
    def generate(self, meeting_data: Dict, output_path: str = None, format: str = "md") -> str:
        """
        產生會議紀錄
        
        Args:
            meeting_data: 會議資料字典
            output_path: 輸出檔案路徑
            format: 輸出格式（md, html, json）
        
        Returns:
            產生的會議紀錄內容
        """
        template_func = self.templates.get(self.template_name, self._standard_template)
        
        if format == "json":
            result = json.dumps(meeting_data, ensure_ascii=False, indent=2)
        elif format == "html":
            result = self._to_html(meeting_data, template_func)
        else:
            result = template_func(meeting_data)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"[✓] 會議紀錄已儲存: {output_path}")
        
        return result
    
    def _standard_template(self, data: Dict) -> str:
        """標準會議紀錄範本"""
        lines = []
        lines.append("# " + data.get("title", "會議紀錄"))
        lines.append("")
        lines.append(f"**會議時間：** {data.get('datetime', '未設定')}")
        lines.append(f"**會議地點：** {data.get('location', '未設定')}")
        lines.append(f"**主席：** {data.get('chair', '未設定')}")
        lines.append(f"**紀錄：** {data.get('secretary', '未設定')}")
        lines.append(f"**與會人員：** {data.get('attendees', '未設定')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 議程
        if data.get("agenda"):
            lines.append("## 📋 議程")
            lines.append("")
            for i, item in enumerate(data["agenda"], 1):
                lines.append(f"{i}. {item}")
            lines.append("")
        
        # 摘要
        if data.get("summary"):
            lines.append("## 📝 會議摘要")
            lines.append("")
            lines.append(data["summary"])
            lines.append("")
        
        # 討論事項
        if data.get("discussions"):
            lines.append("## 💬 討論事項")
            lines.append("")
            for disc in data["discussions"]:
                lines.append(f"### {disc.get('topic', '主題')}")
                lines.append(disc.get('content', ''))
                lines.append("")
        
        # 決議事項
        if data.get("decisions"):
            lines.append("## ✅ 決議事項")
            lines.append("")
            for i, decision in enumerate(data["decisions"], 1):
                lines.append(f"{i}. {decision}")
            lines.append("")
        
        # 待辦事項
        if data.get("action_items"):
            lines.append("## 📝 待辦事項")
            lines.append("")
            lines.append("| 事項 | 負責人 | 期限 | 狀態 |")
            lines.append("|------|--------|------|------|")
            for item in data["action_items"]:
                status = item.get('status', '🔄 進行中')
                lines.append(f"| {item.get('task', '')} | {item.get('assignee', '')} | {item.get('deadline', '')} | {status} |")
            lines.append("")
        
        # 下次會議
        if data.get("next_meeting"):
            lines.append("## 📅 下次會議")
            lines.append("")
            lines.append(data["next_meeting"])
            lines.append("")
        
        # 附件
        if data.get("attachments"):
            lines.append("## 📎 附件")
            lines.append("")
            for att in data["attachments"]:
                lines.append(f"- {att}")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*紀錄產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        return "\n".join(lines)
    
    def _school_template(self, data: Dict) -> str:
        """學校行政會議範本（符合台灣教育體制）"""
        lines = []
        lines.append("# " + data.get("title", "學校行政會議紀錄"))
        lines.append("")
        lines.append(f"**一、會議資料**")
        lines.append(f"| 項目 | 內容 |")
        lines.append(f"|------|------|")
        lines.append(f"| 會議名稱 | {data.get('title', '行政會議')} |")
        lines.append(f"| 會議時間 | {data.get('datetime', '')} |")
        lines.append(f"| 會議地點 | {data.get('location', '')} |")
        lines.append(f"| 主 席 | {data.get('chair', '')} |")
        lines.append(f"| 紀錄人員 | {data.get('secretary', '')} |")
        lines.append(f"| 出席人員 | {data.get('attendees', '')} |")
        lines.append("")
        
        # 報告事項
        if data.get("reports"):
            lines.append("**二、報告事項**")
            lines.append("")
            for i, report in enumerate(data["reports"], 1):
                lines.append(f"（{i}）{report.get('department', '單位')}：{report.get('content', '')}")
                lines.append("")
        
        # 討論提案
        if data.get("proposals"):
            lines.append("**三、討論提案**")
            lines.append("")
            for i, prop in enumerate(data["proposals"], 1):
                lines.append(f"**提案 {i}：{prop.get('title', '提案')}**")
                lines.append(f"{prop.get('description', '')}")
                lines.append(f"**決議：**{prop.get('decision', '通過')}")
                lines.append("")
        
        # 臨時動議
        if data.get("motions"):
            lines.append("**四、臨時動議**")
            lines.append("")
            for motion in data["motions"]:
                lines.append(f"- {motion}")
            lines.append("")
        
        # 主席結論
        if data.get("conclusion"):
            lines.append("**五、主席結論**")
            lines.append("")
            lines.append(data["conclusion"])
            lines.append("")
        
        # 待辦追蹤
        if data.get("action_items"):
            lines.append("**六、工作追蹤**")
            lines.append("")
            lines.append("| 編號 | 工作項目 | 承辦單位 | 完成期限 | 備註 |")
            lines.append("|------|----------|----------|--------|------|")
            for i, item in enumerate(data["action_items"], 1):
                lines.append(f"| {i} | {item.get('task', '')} | {item.get('department', '')} | {item.get('deadline', '')} | {item.get('note', '')} |")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*【本文由 AI 自動產生】產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        return "\n".join(lines)
    
    def _formal_template(self, data: Dict) -> str:
        """正式會議紀錄範本（公務機關適用）"""
        lines = []
        lines.append("# 會議紀錄")
        lines.append("")
        lines.append(f"**會議名稱：** {data.get('title', '')}")
        lines.append(f"**會議時間：** {data.get('datetime', '')}")
        lines.append(f"**會議地點：** {data.get('location', '')}")
        lines.append(f"**主 持 人：** {data.get('chair', '')}")
        lines.append(f"**記 錄 人：** {data.get('secretary', '')}")
        lines.append(f"**出席人員：** {data.get('attendees', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        if data.get("summary"):
            lines.append("## 壹、会议摘要")
            lines.append(data["summary"])
            lines.append("")
        
        if data.get("discussions"):
            lines.append("## 貳、討論事項及決議")
            lines.append("")
            for disc in data["discussions"]:
                lines.append(f"一、{disc.get('topic', '')}")
                lines.append(f"（一）案情說明：{disc.get('description', '')}")
                lines.append(f"（二）決議：{disc.get('decision', '')}")
                lines.append("")
        
        if data.get("action_items"):
            lines.append("## 參、追蹤事項")
            lines.append("")
            for item in data["action_items"]:
                lines.append(f"｜{item.get('task', '')}｜{item.get('assignee', '')}｜{item.get('deadline', '')}｜")
            lines.append("")
        
        lines.append("---")
        lines.append("*本紀錄由 AI 系統自動產生*")
        
        return "\n".join(lines)
    
    def _brief_template(self, data: Dict) -> str:
        """簡短會議紀錄（快速記錄）"""
        lines = []
        lines.append(f"# {data.get('title', '會議紀錄')} - {data.get('datetime', '')}")
        lines.append("")
        if data.get("summary"):
            lines.append(data["summary"])
            lines.append("")
        if data.get("decisions"):
            lines.append("**決議：** " + "；".join(data["decisions"]))
            lines.append("")
        if data.get("action_items"):
            lines.append("**待辨：**")
            for item in data["action_items"]:
                lines.append(f"- {item.get('task', '')} [{item.get('assignee', '')}]")
        return "\n".join(lines)
    
    def _to_html(self, data: Dict, template_func) -> str:
        """將會議紀錄轉換為 HTML"""
        md_content = template_func(data)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('title', '會議紀錄')}</title>
    <style>
        body {{ font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif; 
               max-width: 800px; margin: 40px auto; padding: 20px; 
               background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 8px;
                     box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #3498db; color: white; }}
        .meta {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .action-item {{ background: #e8f6f3; padding: 10px; margin: 10px 0; border-left: 4px solid #1abc9c; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 {data.get('title', '會議紀錄')}</h1>
        <div class="meta">
            <p><strong>📅 時間：</strong> {data.get('datetime', '')}</p>
            <p><strong>📍 地點：</strong> {data.get('location', '')}</p>
            <p><strong>👤 主席：</strong> {data.get('chair', '')}</p>
            <p><strong>📝 紀錄：</strong> {data.get('secretary', '')}</p>
            <p><strong>👥 與會：</strong> {data.get('attendees', '')}</p>
        </div>
        {self._md_to_html_basic(md_content)}
        <hr>
        <p style="color: #7f8c8d; font-size: 12px;">🤖 本文由 AI 自動產生 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
</body>
</html>"""
        return html
    
    def _md_to_html_basic(self, md: str) -> str:
        """簡單的 Markdown 到 HTML 轉換"""
        html = md
        html = html.replace("# ", "<h1>").replace("\n", "</h1>\n", 1)
        html = html.replace("## ", "<h2>").replace("\n##", "</h1>\n<h2")
        html = html.replace("### ", "<h3>").replace("\n###", "</h2>\n<h3")
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("\n\n", "</p><p>")
        return f"<div>{html}</div>"

def create_sample_data() -> Dict:
    """建立範例會議資料"""
    return {
        "title": "111學年度第2學期校務會議",
        "datetime": "2026-05-26 14:00",
        "location": "會議室A",
        "chair": "校長 張大明",
        "secretary": "人事室主任 李小美",
        "attendees": "各處室主任、年級組長、教師會代表",
        "agenda": [
            "上次會議決議執行情形追蹤",
            "113年度預算編列檢討",
            "校舍改建工程進度報告",
            "暑期營隊規劃討論",
            "其他臨時動議"
        ],
        "summary": "本次會議主要針對上學期各項工作進行追蹤，並討論113年度預算規劃及校舍改建工程進度。會中達成多項決議，將於下次會議追蹤執行情形。",
        "discussions": [
            {
                "topic": "校舍改建工程",
                "description": "新建教學大樓預計於今年8月完工，目前進度正常。",
                "decision": "請總務處持續督導工程進度，並於每月校務會議提出報告。"
            },
            {
                "topic": "暑期營隊規劃",
                "description": "規劃辦理英語夏令營、程式設計營等活動。",
                "decision": "原則同意，請教務處與學務處協調師資及場地。"
            }
        ],
        "decisions": [
            "通過113年度預算編列原則",
            "校舍改建工程維持原進度",
            "暑期營隊授權相關處室辦理"
        ],
        "action_items": [
            {"task": "完成113年度預算最後核定", "assignee": "主計室", "deadline": "2026-06-15", "status": "🔄 進行中"},
            {"task": "英語夏令營招生簡章", "assignee": "教務處", "deadline": "2026-06-01", "status": "🔄 進行中"},
            {"task": "校舍改建工程督導", "assignee": "總務處", "deadline": "每月報告", "status": "🔄 進行中"}
        ],
        "next_meeting": "2026年6月15日 14:00 會議室A",
        "attachments": ["113年度預算書草案.pdf", "校舍改建工程進度報告.pdf"]
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="會議紀錄範本產生器")
    parser.add_argument("-o", "--output", help="輸出檔案路徑")
    parser.add_argument("-f", "--format", default="md", choices=["md", "html", "json"],
                       help="輸出格式（預設: md）")
    parser.add_argument("-t", "--template", default="standard",
                       choices=["standard", "school", "formal", "brief"],
                       help="範本類型")
    parser.add_argument("--title", help="會議標題")
    parser.add_argument("--datetime", help="會議時間")
    parser.add_argument("--location", help="會議地點")
    parser.add_argument("--chair", help="主席")
    parser.add_argument("--secretary", help="紀錄")
    parser.add_argument("--attendees", help="與會人員")
    parser.add_argument("--sample", action="store_true", help="產生範例資料")
    
    args = parser.parse_args()
    
    if args.sample:
        data = create_sample_data()
        print("[*] 產生範例會議資料")
    else:
        data = {
            "title": args.title or "會議紀錄",
            "datetime": args.datetime or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "location": args.location or "",
            "chair": args.chair or "",
            "secretary": args.secretary or "",
            "attendees": args.attendees or "",
        }
    
    # 產生會議紀錄
    generator = MinutesTemplate(template_name=args.template)
    result = generator.generate(data, args.output, args.format)
    
    if not args.output:
        print("\n" + "="*50)
        print("📋 會議紀錄預覽")
        print("="*50)
        print(result[:2000] + "..." if len(result) > 2000 else result)

if __name__ == "__main__":
    main()