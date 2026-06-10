#!/usr/bin/env python3
"""
音訊轉文字腳本 - 使用 OpenAI Whisper API
功能：將錄音檔案轉換為文字稿
支援格式：mp3, mp4, m4a, wav, webm, ogg
"""

import os
import sys
import argparse
import json
from pathlib import Path

# 嘗試使用 openai-whisper (本地端)
try:
    import whisper
    WHISPER_MODE = "local"
    print("[✓] 使用本地 Whisper 模型")
except ImportError:
    WHISPER_MODE = "api"
    print("[✓] 將使用 OpenAI Whisper API")

# OpenAI Whisper API 模式
USE_OPENAI_API = os.getenv("OPENAI_API_KEY") and os.getenv("WHISPER_API_MODE") == "1"

def transcribe_with_api(audio_path: str, model: str = "whisper-1", language: str = "zh") -> dict:
    """使用 OpenAI Whisper API 轉換"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        
        return {
            "text": response.text,
            "segments": [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in response.segments
            ] if hasattr(response, "segments") else []
        }
    except Exception as e:
        print(f"[錯誤] API 轉換失敗: {e}")
        return {"text": "", "segments": []}

def transcribe_with_local(audio_path: str, model_name: str = "base", language: str = "zh") -> dict:
    """使用本地 Whisper 模型轉換"""
    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(audio_path, language=language)
        
        return {
            "text": result["text"],
            "segments": [
                {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
                for seg in result["segments"]
            ]
        }
    except Exception as e:
        print(f"[錯誤] 本地轉換失敗: {e}")
        return {"text": "", "segments": []}

def transcribe(audio_path: str, output_path: str = None, model: str = "base", 
               language: str = "zh", save_json: bool = True) -> dict:
    """
    將音訊檔案轉換為文字
    
    Args:
        audio_path: 音訊檔案路徑
        output_path: 輸出文字檔路徑（可選）
        model: 模型大小（tiny, base, small, medium, large）
        language: 語言代碼（zh, en, ja 等）
        save_json: 是否儲存詳細 JSON
    
    Returns:
        包含 text 和 segments 的字典
    """
    if not os.path.exists(audio_path):
        print(f"[錯誤] 檔案不存在: {audio_path}")
        return {"text": "", "segments": []}
    
    print(f"[*] 開始轉換: {audio_path}")
    
    # 選擇轉換方式
    if USE_OPENAI_API and WHISPER_MODE == "api":
        result = transcribe_with_api(audio_path, language=language)
    else:
        result = transcribe_with_local(audio_path, model, language)
    
    if result["text"]:
        print(f"[✓] 轉換完成，共 {len(result['text'])} 字")
        
        # 儲存純文字
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result["text"])
            print(f"[✓] 文字已儲存: {output_path}")
        
        # 儲存詳細 JSON
        if save_json:
            json_path = output_path.replace(".txt", ".json") if output_path else audio_path + ".json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[✓] 詳細資料已儲存: {json_path}")
        
        return result
    else:
        print("[錯誤] 轉換失敗")
        return {"text": "", "segments": []}

def main():
    parser = argparse.ArgumentParser(description="Whisper 音訊轉文字工具")
    parser.add_argument("audio", help="音訊檔案路徑")
    parser.add_argument("-o", "--output", help="輸出文字檔路徑")
    parser.add_argument("-m", "--model", default="base", 
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="本地模型大小（預設: base）")
    parser.add_argument("-l", "--language", default="zh", help="語言代碼（預設: zh）")
    parser.add_argument("--no-json", action="store_true", help="不儲存 JSON")
    
    args = parser.parse_args()
    
    result = transcribe(
        audio_path=args.audio,
        output_path=args.output,
        model=args.model,
        language=args.language,
        save_json=not args.no_json
    )
    
    if result["text"]:
        print("\n=== 轉換結果 ===")
        print(result["text"][:500] + "..." if len(result["text"]) > 500 else result["text"])

if __name__ == "__main__":
    main()