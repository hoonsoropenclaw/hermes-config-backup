import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
from datetime import datetime

API_KEY_PATH = "/home/hoonsoropenclaw/.hermes/.minimax_api_key"
API_KEY = ""
try:
    with open(API_KEY_PATH, "r") as f:
        API_KEY = f.read().strip()
except Exception:
    pass
API_URL = "https://api.minimax.io/v1/text/chatcompletion_v2"
LOG_FILE = "/home/hoonsoropenclaw/.hermes/learning_output.log"
OUTPUT_FILE = "/home/hoonsoropenclaw/.hermes/data_repo/data.json"

def read_latest_logs():
    if not os.path.exists(LOG_FILE):
        return "No logs found yet."
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(size - 50000, 0)) # Read more logs to catch concurrent runs
        return f.read()

def read_ongoing_tasks():
    try:
        result = subprocess.run("ps aux | grep '[h]ermes chat'", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error reading ongoing tasks: {e}")
        return ""

def read_existing_mindmap_raw():
    if not os.path.exists(OUTPUT_FILE):
        return None
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("mindmap", {})
    except Exception as e:
        print(f"Error reading existing mindmap: {e}")
        return None

def merge_properties(old_node, new_node):
    if not old_node or not new_node:
        return
    if "url" in old_node and "url" not in new_node:
        new_node["url"] = old_node["url"]
    
    old_children = {child.get("name", ""): child for child in old_node.get("children", [])}
    for new_child in new_node.get("children", []):
        name = new_child.get("name", "")
        if name in old_children:
            merge_properties(old_children[name], new_child)

def extract_mindmap_json(log_text, ongoing_text, existing_raw):
    existing_json_text = json.dumps(existing_raw, ensure_ascii=False, indent=2) if existing_raw else None

    if existing_json_text:
        base_context = f"【現有心智圖 JSON 結構】：\n{existing_json_text}\n\n請基於上述現有結構進行更新。嚴禁刪除現有的學習節點，只能追加新節點或更新狀態與連結。"
    else:
        base_context = """【預設學習藍圖】（總工程師指定的高價值領域）：
1. 人工智慧代理 (AI Agents)
   - 多智能體協作 (Multi-Agent Sync)
   - MCP 工具整合 (MCP Integration)
   - 知識庫檢索 (RAG System)
2. 全端網頁開發 (Full-Stack Web)
   - React 狀態管理 (React State)
   - FastAPI 非同步處理 (FastAPI Async)
   - Serverless 部署架構 (Vercel Deploy)
3. 維運與自動化 (DevOps & Automation)
   - Linux 系統安全維護 (Linux Security)
   - 背景排程與監控 (Cron & Monitoring)
   - GitHub Actions 自動化 (CI/CD Pipeline)"""

    prompt = f"""
請閱讀以下的學習日誌，並更新心智圖狀態。
將結果轉換為嚴格的 JSON 格式。請只輸出 JSON，不要輸出 Markdown 標記（如 ```json）。

{base_context}

【更新規則】：
1. 比對日誌，若某項預設技能已在日誌中被實作或學習，請將其保留，且不加狀態（預設即為已完成）。
2. 若某項預設技能尚未被學習，請務必保留它，並在該節點加上 `"status": "planned"`。
3. 若日誌中出現了不包含在現有結構中的**高價值**技能，你可以將它做為新節點加入（狀態預設為已完成）。
4. 所有的 name 必須採用「中文 (English)」的雙語格式，例如 "自動化腳本 (Automation Script)"。
5. 【重要】下方有「目前正在執行中的任務清單 (Ongoing Tasks)」。請仔細比對，如果某個技能正在該清單中被執行，請將該節點加上 `"status": "ongoing"`，這會優先於 planned 狀態。
6. 【提取連結】：若日誌片段中包含 `[Project URL]: https://...` 或是 GitHub 網址，請將該網址作為 `"url"` 屬性，加入到對應技能的節點資料中。
7. 【結構穩定】：若有傳入現有結構，請保持層級結構不變，只做微調與新增。

目前正在執行中的任務清單 (Ongoing Tasks)：
{ongoing_text}

學習日誌片段：
{log_text}
"""
    
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": "You are a data extractor. Output ONLY valid JSON without markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8192
    }
    
    req = urllib.request.Request(API_URL, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }, data=json.dumps(payload).encode('utf-8'))
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content'].strip()
            if content.startswith("```json"):
                content = content.replace("```json\n", "")
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None

def main():
    print("Reading logs...")
    log_text = read_latest_logs()
    
    print("Reading ongoing tasks...")
    ongoing_text = read_ongoing_tasks()
    
    print("Reading existing mindmap...")
    existing_raw = read_existing_mindmap_raw()
    
    print("Extracting mindmap data...")
    mindmap_data = extract_mindmap_json(log_text, ongoing_text, existing_raw)
    
    if mindmap_data:
        if existing_raw:
            print("Merging existing properties (URLs) to prevent LLM amnesia...")
            merge_properties(existing_raw, mindmap_data)

        final_json = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mindmap": mindmap_data
        }
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)
        print(f"Successfully updated {OUTPUT_FILE}")
        
        # Git Commit and Push
        try:
            repo_dir = os.path.dirname(OUTPUT_FILE)
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"Auto-update: {final_json['last_updated']}"], cwd=repo_dir, check=True)
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            print("Successfully pushed to GitHub repository.")
        except Exception as e:
            print(f"Git push failed: {e}")
    else:
        print("Failed to extract valid JSON.")

if __name__ == "__main__":
    main()
