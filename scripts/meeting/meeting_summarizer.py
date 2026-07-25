#!/usr/bin/env python3
"""
會議摘要生成器 - 使用 LLM API 生成會議紀錄摘要
功能：從文字稿自動識別發言人、討論主題、決策事項、行動項目
"""

import os
import sys
import json
import re
from typing import List, Dict, Optional
from datetime import datetime

# 嘗試使用 Litellm（統一的 LLM 呼叫介面）
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# 直接使用 OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class MeetingSummarizer:
    """會議摘要生成器"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key) if self.api_key and OPENAI_AVAILABLE else None
    
    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """呼叫 LLM API"""
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        elif LITELLM_AVAILABLE:
            return litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            ).choices[0].message.content
        else:
            print("[警告] 無法連線 LLM API")
            return ""
    
    def summarize_meeting(self, transcription: str, meeting_info: Dict = None) -> Dict:
        """
        生成會議摘要
        
        Args:
            transcription: 會議文字稿
            meeting_info: 會議資訊（標題、時間、與會者等）
        
        Returns:
            包含摘要各部分的字典
        """
        meeting_info = meeting_info or {}
        
        system_prompt = """你是一個專業的會議紀錄分析師。請根據提供的會議文字稿，生成結構化的會議紀錄。

請以 JSON 格式輸出，包含以下欄位：
{
    "summary": "會議摘要（100-200字）",
    "topics_discussed": ["議題1", "議題2", ...],
    "decisions": ["決策1", "決策2", ...],
    "action_items": [
        {"task": "任務描述", "assignee": "負責人", "deadline": "期限"}
    ],
    "questions_raised": ["問題1", "問題2", ...],
    "next_meeting": "下次會議相關資訊（如有）"
}

請確保輸出是有效的 JSON 格式，不要包含額外的說明文字。"""
        
        context = f"""會議標題：{meeting_info.get('title', '未命名會議')}
會議時間：{meeting_info.get('datetime', datetime.now().strftime('%Y-%m-%d %H:%M'))}
與會人員：{meeting_info.get('attendees', '未提供')}

會議文字稿：
{transcription}"""
        
        result_text = self._call_llm(system_prompt, context)
        
        # 解析 JSON
        try:
            result = json.loads(result_text)
            return result
        except json.JSONDecodeError:
            # 嘗試提取 JSON 部分
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {
                "summary": result_text[:500],
                "topics_discussed": [],
                "decisions": [],
                "action_items": [],
                "questions_raised": [],
                "next_meeting": ""
            }
    
    def identify_speakers(self, transcription: str, num_speakers: int = None) -> List[Dict]:
        """
        識別發言人並分析發言統計
        
        Args:
            transcription: 會議文字稿
            num_speakers: 預期發言人數（可選）
        
        Returns:
            發言人統計列表
        """
        system_prompt = f"""請分析以下會議文字稿，識別發言人並統計發言次數和內容。

請以 JSON 格式輸出：
{{
    "speakers": [
        {{"name": "發言人A", "turns": 5, "total_words": 300, "topics": ["主題1", "主題2"]}},
        ...
    ],
    "conversation_flow": ["發言人A", "發言人B", "發言人A", ...]
}}

{'預期發言人人數：' + str(num_speakers) if num_speakers else ''}

請確保輸出是有效的 JSON 格式。"""
        
        result_text = self._call_llm(system_prompt, transcription)
        
        try:
            result = json.loads(result_text)
            return result.get("speakers", [])
        except:
            return []
    
    def extract_key_points(self, transcription: str, num_points: int = 5) -> List[str]:
        """提取關鍵要點"""
        system_prompt = f"""請從以下會議文字稿中提取 {num_points} 個最重要的關鍵要點。

請以 JSON 格式輸出：
{{
    "key_points": ["要點1", "要點2", "要點3", "要點4", "要點5"]
}}"""
        
        result_text = self._call_llm(system_prompt, transcription)
        
        try:
            result = json.loads(result_text)
            return result.get("key_points", [])
        except:
            return []

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="會議摘要生成器")
    parser.add_argument("transcript", help="會議文字稿檔案路徑")
    parser.add_argument("-o", "--output", help="輸出檔案路徑")
    parser.add_argument("--title", help="會議標題")
    parser.add_argument("--datetime", help="會議時間")
    parser.add_argument("--attendees", help="與會人員（用逗號分隔）")
    parser.add_argument("-m", "--model", default="gpt-4o-mini", help="使用的模型")
    
    args = parser.parse_args()
    
    # 讀取文字稿
    with open(args.transcript, "r", encoding="utf-8") as f:
        transcription = f.read()
    
    # 準備會議資訊
    meeting_info = {
        "title": args.title or "未命名會議",
        "datetime": args.datetime or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "attendees": args.attendees or "未提供"
    }
    
    # 生成摘要
    summarizer = MeetingSummarizer(model=args.model)
    
    print("[*] 正在分析會議內容...")
    result = summarizer.summarize_meeting(transcription, meeting_info)
    
    # 輸出結果
    print("\n" + "="*50)
    print("📋 會議摘要")
    print("="*50)
    print(f"\n{result.get('summary', '無法生成摘要')}")
    
    if result.get("topics_discussed"):
        print("\n📌 討論議題：")
        for i, topic in enumerate(result["topics_discussed"], 1):
            print(f"   {i}. {topic}")
    
    if result.get("decisions"):
        print("\n✅ 決議事項：")
        for i, decision in enumerate(result["decisions"], 1):
            print(f"   {i}. {decision}")
    
    if result.get("action_items"):
        print("\n📝 待辦事項：")
        for item in result["action_items"]:
            assignee = item.get("assignee", "未指定")
            deadline = item.get("deadline", "無期限")
            print(f"   • {item.get('task')} [{assignee}] {deadline}")
    
    # 儲存結果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n[✓] 結果已儲存: {args.output}")

if __name__ == "__main__":
    main()