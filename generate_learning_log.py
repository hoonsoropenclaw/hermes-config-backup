import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import glob
from datetime import datetime, timedelta

API_KEY_PATH = "/home/hoonsoropenclaw/.hermes/.minimax_api_key"
API_KEY = ""
try:
    with open(API_KEY_PATH, "r") as f:
        API_KEY = f.read().strip()
except Exception:
    pass
API_URL = "https://api.minimax.io/v1/text/chatcompletion_v2"
LOG_FILE = "/home/hoonsoropenclaw/.hermes/learning_output.log"
OUTPUT_FILE = "/home/hoonsoropenclaw/.hermes/data_repo/learning_logs.json"
DATA_JSON_FILE = "/home/hoonsoropenclaw/.hermes/data_repo/data.json"
PROJECTS_DIR = "/home/hoonsoropenclaw/.hermes/projects"

def get_completed_topics():
    topics = []
    if os.path.exists(DATA_JSON_FILE):
        try:
            with open(DATA_JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            def extract_names(node):
                if node.get('name'):
                    topics.append(node['name'])
                for child in node.get('children', []):
                    extract_names(child)
            
            if 'mindmap' in data:
                extract_names(data['mindmap'])
        except Exception as e:
            print(f"Error reading completed topics: {e}")
    return list(set(topics))

def get_ongoing_tasks():
    ongoing = []
    search_pattern = os.path.join(PROJECTS_DIR, "learning_*", "task_info.json")
    for info_file in glob.glob(search_pattern):
        work_dir = os.path.dirname(info_file)
        if not os.path.exists(os.path.join(work_dir, ".finished")):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    
                start_time = info.get('start_time', 0)
                duration_sec = int(datetime.now().timestamp()) - start_time
                hours = duration_sec // 3600
                mins = (duration_sec % 3600) // 60
                info['running_time'] = f"{hours}小時 {mins}分"
                ongoing.append(info)
            except Exception as e:
                pass
    return ongoing

def read_recent_logs(lines_to_read=2000):
    if not os.path.exists(LOG_FILE):
        return ""
    try:
        # We'll just read the tail of the log
        result = subprocess.run(f"tail -n {lines_to_read} {LOG_FILE}", shell=True, capture_output=True, text=True, errors='replace')
        return result.stdout
    except Exception as e:
        print(f"Error reading logs: {e}")
        return ""

def summarize_logs(log_text, completed_topics):
    if not log_text.strip():
        return None

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    past_topics_str = ", ".join(completed_topics[:100]) # limit context size
    
    prompt = (
        f"請分析以下拉斐爾 (Raphael) 最近的學習日誌內容與正在執行的任務。\n"
        f"請你扮演冷靜客觀的監理官，判斷拉斐爾在剛才的行為模式。\n"
        f"【安全防護護欄 Guardrails 規則】：\n"
        f"1. 如果日誌顯示他在解決同樣的錯誤（例如不斷報錯、不斷修正卻失敗），請將 is_looping 設為 true。\n"
        f"2. 失憶警告 (amnesia_warning)：對比他正在學習/剛學完的主題，是否與以下『已精通主題』高度重複？若是，請設為 true。\n"
        f"   已精通主題：{past_topics_str}\n"
        f"3. 未反饋警告 (missing_feedback)：若日誌中顯示任務『已完成』，但拉斐爾完全沒有呼叫 `@學習` 指令或修改技能庫來反饋經驗（你可以自行判斷該次任務重要性，若很瑣碎可忽略不報警），請設為 true。\n"
        f"4. 固著警告 (repeated_error_warning)：若拉斐爾調用了已知的錯誤技能庫，卻一再犯相同的錯誤超過兩次，請設為 true。\n\n"
        f"請輸出嚴格的 JSON 格式（不要加上 markdown backticks），包含以下欄位：\n"
        f" - time_period (字串，例如 '{current_time} 前後')\n"
        f" - tasks_executed (陣列，描述他剛完成的任務主題。若是日誌中顯示[Duration: ...]請一併附註耗時)\n"
        f" - errors_encountered (陣列，描述他遇到了哪些主要錯誤)\n"
        f" - is_looping (布林值)\n"
        f" - amnesia_warning (布林值)\n"
        f" - missing_feedback (布林值)\n"
        f" - repeated_error_warning (布林值)\n"
        f" - evaluation (字串，簡短評價他的表現及建議)\n\n"
        f"近期日誌片段：\n{log_text[-15000:]}"  # Prevent prompt injection/overflow
    )
    
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": "You are a JSON-only data summarizer. Output raw JSON without any markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    req = urllib.request.Request(API_URL, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }, data=json.dumps(payload).encode('utf-8'))
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            content = data['choices'][0]['message']['content'].strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            summary = json.loads(content.strip())
            summary["timestamp"] = datetime.now().isoformat()
            return summary
    except Exception as e:
        print(f"LLM Summarization failed: {e}")
        return None

def main():
    print("Reading recent learning logs...")
    log_text = read_recent_logs()
    
    print("Gathering context for guardrails...")
    completed_topics = get_completed_topics()
    ongoing_tasks = get_ongoing_tasks()
    
    print("Generating LLM summary...")
    summary = summarize_logs(log_text, completed_topics)
    
    if summary:
        summary["ongoing_tasks"] = ongoing_tasks
        print("Summary generated:", json.dumps(summary, ensure_ascii=False))
        
        # Load existing logs
        logs_data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    logs_data = json.load(f)
            except Exception:
                pass
                
        # Append new summary (keep max 100 to avoid bloat)
        logs_data.insert(0, summary)
        logs_data = logs_data[:100]
        
        # Save back
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=4)
            
        print(f"Successfully updated {OUTPUT_FILE}")
        
        # Git Push
        try:
            repo_dir = os.path.dirname(OUTPUT_FILE)
            subprocess.run(["git", "add", OUTPUT_FILE], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"docs: update learning log {summary['timestamp']}"], cwd=repo_dir, check=True)
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            print("Successfully pushed learning logs to GitHub.")
        except Exception as e:
            print(f"Git push failed: {e}")
    else:
        print("Failed to generate summary.")

if __name__ == "__main__":
    main()
