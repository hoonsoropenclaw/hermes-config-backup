#!/usr/bin/env python3
"""
會議紀錄 AI 生成系統 - 主整合腳本
功能：錄音 → 轉文字 → AI 摘要 → 產生會議紀錄

使用流程：
    1. audio_transcriber.py  - 錄音轉文字（Whisper）
    2. meeting_summarizer.py - AI 分析摘要
    3. minutes_template.py   - 產生紀錄檔案
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# 匯入子模組
from audio_transcriber import transcribe
from meeting_summarizer import MeetingSummarizer
from minutes_template import MinutesTemplate

class MeetingMinutesGenerator:
    """會議紀錄 AI 生成系統"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.summarizer = MeetingSummarizer(api_key=self.api_key, model=self.model)
        self.template = MinutesTemplate()
    
    def process_audio(self, audio_path: str, language: str = "zh") -> dict:
        """處理音訊檔案"""
        print(f"[*] 處理音訊: {audio_path}")
        result = transcribe(
            audio_path=audio_path,
            output_path=None,
            language=language
        )
        return result
    
    def process_full(self, audio_path: str, meeting_info: dict = None, 
                     output_dir: str = "./output") -> dict:
        """
        完整處理流程：音訊 → 轉文字 → 摘要 → 會議紀錄
        
        Args:
            audio_path: 音訊檔案路徑
            meeting_info: 會議資訊
            output_dir: 輸出目錄
        
        Returns:
            處理結果字典
        """
        meeting_info = meeting_info or {}
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Step 1: 音訊轉文字
        print("\n" + "="*50)
        print("Step 1: 音訊轉文字")
        print("="*50)
        transcription_result = self.process_audio(audio_path)
        
        if not transcription_result["text"]:
            return {"error": "轉換失敗", "step": "transcription"}
        
        # 儲存文字稿
        transcript_path = output_dir / f"transcript_{timestamp}.txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcription_result["text"])
        print(f"[✓] 文字稿已儲存: {transcript_path}")
        
        # Step 2: AI 摘要生成
        print("\n" + "="*50)
        print("Step 2: AI 摘要生成")
        print("="*50)
        summary_result = self.summarizer.summarize_meeting(
            transcription_result["text"],
            meeting_info
        )
        
        # Step 3: 產生會議紀錄
        print("\n" + "="*50)
        print("Step 3: 產生會議紀錄")
        print("="*50)
        
        # 合併資料
        meeting_data = {
            **meeting_info,
            "summary": summary_result.get("summary", ""),
            "topics_discussed": summary_result.get("topics_discussed", []),
            "decisions": summary_result.get("decisions", []),
            "action_items": summary_result.get("action_items", []),
            "questions_raised": summary_result.get("questions_raised", []),
            "next_meeting": summary_result.get("next_meeting", ""),
            "transcript_path": str(transcript_path)
        }
        
        # 產生各格式檔案
        base_name = f"meeting_{timestamp}"
        
        # Markdown 格式
        md_path = output_dir / f"{base_name}.md"
        self.template.generate(meeting_data, str(md_path), "md")
        
        # HTML 格式
        html_path = output_dir / f"{base_name}.html"
        self.template.generate(meeting_data, str(html_path), "html")
        
        # JSON 格式（完整資料）
        json_path = output_dir / f"{base_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "meeting_info": meeting_info,
                "summary": summary_result,
                "transcript": transcription_result["text"],
                "segments": transcription_result.get("segments", []),
                "generated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n[✓] 所有檔案已產生：")
        print(f"    📝 文字稿: {transcript_path}")
        print(f"    📋 會議紀錄(MD): {md_path}")
        print(f"    🌐 會議紀錄(HTML): {html_path}")
        print(f"    📊 完整資料(JSON): {json_path}")
        
        return {
            "success": True,
            "transcript_path": str(transcript_path),
            "minutes_md": str(md_path),
            "minutes_html": str(html_path),
            "minutes_json": str(json_path),
            "summary": summary_result
        }

def main():
    parser = argparse.ArgumentParser(
        description="會議紀錄 AI 生成系統 - 錄音 → 轉文字 → AI 摘要 → 會議紀錄"
    )
    parser.add_argument("audio", help="音訊檔案路徑")
    parser.add_argument("-o", "--output", default="./output", help="輸出目錄")
    parser.add_argument("-m", "--model", default="gpt-4o-mini", help="使用的模型")
    parser.add_argument("-l", "--language", default="zh", help="語言")
    parser.add_argument("--title", help="會議標題")
    parser.add_argument("--datetime", help="會議時間")
    parser.add_argument("--location", help="會議地點")
    parser.add_argument("--chair", help="主席")
    parser.add_argument("--attendees", help="與會人員")
    
    args = parser.parse_args()
    
    # 組裝會議資訊
    meeting_info = {
        "title": args.title or "會議紀錄",
        "datetime": args.datetime or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "location": args.location or "",
        "chair": args.chair or "",
        "attendees": args.attendees or ""
    }
    
    # 執行完整流程
    generator = MeetingMinutesGenerator(model=args.model)
    
    print("🎙️  會議紀錄 AI 生成系統")
    print("="*50)
    result = generator.process_full(
        audio_path=args.audio,
        meeting_info=meeting_info,
        output_dir=args.output
    )
    
    if result.get("success"):
        print("\n✅ 處理完成！")
    else:
        print(f"\n❌ 處理失敗: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()