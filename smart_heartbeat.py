import os
import sys
import json
import re
import urllib.request
import urllib.error
import subprocess
import logging
import glob
import time
import shlex

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY_PATH = "/home/hoonsoropenclaw/.hermes/.minimax_api_key"
API_KEY = ""
try:
    with open(API_KEY_PATH, "r") as f:
        API_KEY = f.read().strip()
except Exception:
    pass
API_URL = "https://api.minimax.io/v1/token_plan/remains"

THRESHOLD_PERCENT = 5
PROJECTS_DIR = "/home/hoonsoropenclaw/.hermes/projects"
AGENT_MEMORY_DIR = "/home/hoonsoropenclaw/.hermes/agent_memory"
TOPIC_DEDUP_HOURS = 24  # 同 topic 24 小時內已完成 → 跳過

def get_topic_hash(topic: str) -> str:
    """Topic → 12 字 hash。穩定：同 topic 永遠同 hash，跨 session 可累積。"""
    import hashlib
    normalized = topic.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]

def get_or_create_work_dir(topic: str, idx: int = 0) -> str:
    """Topic-based 固定 work_dir。**核心修正**（教訓 39）：
    - 同 topic → 同一個 work_dir（累積成品、半成品、記憶）
    - 不同 idx（同一輪多個 topic） → 加 _1/_2 後綴避免衝突
    - 若已存在則不重建，保留歷史
    """
    topic_hash = get_topic_hash(topic)
    # 取 topic 前 16 字當 human-readable 前綴（方便 ls 時辨識）
    safe_topic_slug = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "_", topic)[:16]
    base = f"{PROJECTS_DIR}/learning_{safe_topic_slug}_{topic_hash}"
    work_dir = f"{base}_{idx}" if idx > 0 else base
    os.makedirs(work_dir, exist_ok=True)
    return work_dir

def get_memory_path(topic: str) -> str:
    """Topic → 固定 memory file 路徑。spawn 出的 session 必讀寫此檔。"""
    topic_hash = get_topic_hash(topic)
    return os.path.join(AGENT_MEMORY_DIR, f"{topic_hash}.md")

def is_topic_recently_completed(topic: str, hours: int = TOPIC_DEDUP_HOURS) -> bool:
    """檢查 memory file 的『完成狀態』是否在 N 小時內標記為完成。
    用於 spawn gate：避免重複做同樣的事。
    """
    mem_path = get_memory_path(topic)
    if not os.path.exists(mem_path):
        return False
    try:
        with open(mem_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 找「最後更新」時間 + 「完成階段」
        m_update = re.search(r"最後更新[：:]\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})", content)
        m_stage = re.search(r"完成階段[：:]\s*(\d)", content)
        if not m_update or not m_stage:
            return False
        from datetime import datetime, timedelta
        last_update = datetime.strptime(m_update.group(1).replace("T", " "), "%Y-%m-%d %H:%M")
        stage = int(m_stage.group(1))
        # stage 2=完成 / 3=timeout，且在 hours 小時內 → 視為 recently completed
        if stage in (2, 3) and (datetime.now() - last_update) < timedelta(hours=hours):
            return True
        return False
    except Exception as e:
        logging.warning(f"[is_topic_recently_completed] {mem_path} parse error: {e}")
        return False

def _scan_recent_completed_topics(hours: int = TOPIC_DEDUP_HOURS) -> list:
    """掃描 agent_memory/ 目錄，找出 N 小時內『完成』的 topic 清單。
    回傳 topic 字串（從 memory file 的 title 解析）。
    給 Strategist prompt 當 dedup 上下文。
    """
    completed = []
    if not os.path.exists(AGENT_MEMORY_DIR):
        return completed
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=hours)
    for fname in os.listdir(AGENT_MEMORY_DIR):
        if not fname.endswith(".md") or fname == "README.md":
            continue
        fpath = os.path.join(AGENT_MEMORY_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            m_update = re.search(r"最後更新[：:]\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})", content)
            m_stage = re.search(r"完成階段[：:]\s*(\d)", content)
            m_title = re.search(r"#\s*任務[：:]\s*(.+)", content)
            if not (m_update and m_stage and m_title):
                continue
            last_update = datetime.strptime(m_update.group(1).replace("T", " "), "%Y-%m-%d %H:%M")
            stage = int(m_stage.group(1))
            title = m_title.group(1).strip()
            if stage in (2, 3) and last_update >= cutoff:
                completed.append(title)
        except Exception as e:
            logging.warning(f"[_scan_recent_completed_topics] {fpath} parse error: {e}")
    return completed

def check_budget():
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }
    req = urllib.request.Request(API_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            interval_pct = 100
            weekly_pct = 100
            for model_rem in data.get('model_remains', []):
                if model_rem.get('model_name') == 'general':
                    interval_pct = model_rem.get('current_interval_remaining_percent', 100)
                    weekly_pct = model_rem.get('current_weekly_remaining_percent', 100)
                    break
            
            return interval_pct, weekly_pct, 60
    except Exception as e:
        logging.error(f"Failed to check budget: {e}")
        # Default to safe values if API fails
        return 100, 100, 300

def get_context_and_history():
    context = ""
    past_topics = []
    
    try:
        feedback_path = "/home/hoonsoropenclaw/.hermes/architect_feedback.md"
        if os.path.exists(feedback_path):
            with open(feedback_path, 'r', encoding='utf-8') as f:
                context = f.read()[:1000] # truncate to avoid huge prompts
    except:
        pass
        
    try:
        logs_path = "/home/hoonsoropenclaw/.hermes/data_repo/skills/SKILL_CATALOG.md"
        if os.path.exists(logs_path):
            with open(logs_path, 'r', encoding='utf-8') as f:
                logs = f.read()
                past_topics.append(logs)
    except:
        pass
        
    return context, list(set(past_topics))

def get_resume_tasks(available_slots):
    """Scan for projects that have a .timeout marker."""
    resume_tasks = []
    search_pattern = os.path.join(PROJECTS_DIR, "learning_*", ".timeout")
    for timeout_file in glob.glob(search_pattern):
        work_dir = os.path.dirname(timeout_file)
        task_info_path = os.path.join(work_dir, "task_info.json")
        if os.path.exists(task_info_path):
            try:
                with open(task_info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    resume_tasks.append({
                        "work_dir": work_dir,
                        "topic": info.get('topic', 'Unknown Topic'),
                        "id": info.get('id', os.path.basename(work_dir))
                    })
            except Exception as e:
                logging.error(f"Error reading {task_info_path}: {e}")
    
    # Sort to prioritize older tasks
    resume_tasks.sort(key=lambda x: x['id'])
    
    # Limit to available slots
    return resume_tasks[:available_slots]

def get_llm_strategy(interval_pct, minutes_left, running_count, slots_already_taken_by_resume, recent_completed_topics=None):
    context, past_topics = get_context_and_history()
    past_topics_str = ", ".join(past_topics) if past_topics else "無"
    recent_completed_str = ", ".join(recent_completed_topics) if recent_completed_topics else "無"
    
    # [ANTI-LOOP ENHANCEMENT] Read data.json to extract permanently mastered topics
    mastered_topics = []
    try:
        data_path = "/home/hoonsoropenclaw/.hermes/data_repo/data.json"
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                import json
                mindmap_data = json.load(f)
                
                def extract_names(node):
                    if isinstance(node, dict):
                        if 'name' in node and node['name']:
                            mastered_topics.append(node['name'])
                        if 'children' in node:
                            for c in node['children']:
                                extract_names(c)
                    elif isinstance(node, list):
                        for c in node:
                            extract_names(c)
                            
                extract_names(mindmap_data.get('mindmap', {}))
    except Exception as e:
        logging.error(f"Failed to read data.json for anti-loop: {e}")
        
    mastered_str = ", ".join(set(mastered_topics)) if mastered_topics else "無"
    
    domains_str = ""
    try:
        domains_path = "/home/hoonsoropenclaw/.hermes/learning_domains.txt"
        if os.path.exists(domains_path):
            with open(domains_path, 'r', encoding='utf-8') as f:
                domains_str = f.read()
    except Exception:
        pass
    if not domains_str:
        domains_str = "1. Web Platforms\n2. Desktop/OS Automation\n3. API Integrations\n4. Multimedia & Games"
    
    # Fallback default strategy
    fallback = {"target_new_tasks": 1, "max_running_count": 2, "novel_topics": ["開發一個高效能的 FastAPI 非同步框架模版"]}
    url = "https://api.minimax.io/v1/text/chatcompletion_v2"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        prompt = (
            f"You are the N100 Core AI Strategist. Your job is to decide how many NEW 'hermes chat' tasks to launch right now. "
            f"Note: There are already {slots_already_taken_by_resume} tasks being automatically resumed from timeout. "
            f"Current state:\n"
            f"- Interval Quota Remaining: {interval_pct:.2f}%\n"
            f"- Minutes until interval resets: {minutes_left:.1f} mins\n"
            f"- Currently running hermes processes: {running_count}\n\n"
            # === 教訓 39 修正：「燒 token」改成「聰明用 token」 ===
            f"Rules (EFFICIENCY-FIRST, NOT BURN-FIRST):\n"
            f"1. If quota > 90%, you should still be productive but NOT waste tokens. Launch moderate (target_new_tasks=2 to 4, max_running_count=3). Quality over quantity.\n"
            f"2. If quota > 50% and time < 150 mins, steady pace (target_new_tasks=1 to 3, max_running_count=2).\n"
            f"3. If time < 60 mins and quota > 30%, wrap-up mode (target_new_tasks=0 to 1, max_running_count=1).\n"
            f"4. If quota < 15%, throttle down (target_new_tasks=0 or 1, max_running_count=1).\n"
            f"5. CRITICAL: The system already filters out topics completed in the past 24 hours (see 'recent_completed_topics'). DO NOT generate topics that overlap with these.\n\n"
            # === 修正結束 ===
            f"Output ONLY a raw JSON object (NO markdown formatting, NO backticks) with exactly these keys:\n"
            f"{{\"target_new_tasks\": <int>, \"max_running_count\": <int>, \"novel_topics\": [\"topic1\", \"topic2\", ...]}}\n"
            f"You MUST generate `target_new_tasks` number of extremely creative, challenging, and NON-REPETITIVE software engineering topics in `novel_topics` (Traditional Chinese).\n\n"
            f"CRITICAL RULES FOR TOPIC GENERATION:\n"
            f"- Here is the agent's current Skill Catalog (what he already knows): {past_topics_str}\n"
            f"- DO NOT generate tasks that can be fully solved by existing skills. The task MUST require learning at least one NEW micro-skill, while combining it with existing skills for reinforcement.\n"
            f"- RECENTLY COMPLETED TOPICS (avoid regenerating these within 24h): {recent_completed_str}\n"
            f"- PERMANENTLY MASTERED TOPICS (Already on the mindmap): {mastered_str}\n"
            f"  -> CRITICAL RULE: You MUST NOT generate these exact topics again, nor any basic tutorials for them. HOWEVER, you are highly encouraged to generate ADVANCED, EXPERT-LEVEL, or DEEP-DIVE topics that build upon these mastered foundations (e.g., if 'Playwright Basics' is mastered, you can generate 'Playwright Cluster Distributed Testing').\n"
            f"- Align the topics with the user's role and goals based on this context: {context}\n"
            f"- The goal is to train the AI to become a highly capable executive assistant, workflow automator, and creative technologist for the user's daily life and work.\n" \
            f"- Specifically, the topics MUST heavily focus on these domains: \n" \
            f"{domains_str}\n" \
            f"- If you evaluate that the agent has already mastered the core skills of all 4 domains based on the Skill Catalog, generate EXACTLY ONE topic in novel_topics: '向總工程師發送系統級報告：四大核心領域的基礎微技能庫已建置完畢，請求總工程師審閱目前的心智圖，並指示下一階段的拓展領域。'"
        )
        
        payload = {
            "model": "MiniMax-Text-01",
            "messages": [
                {"role": "system", "content": "You are a JSON-only configuration bot."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode('utf-8'), method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            content = data['choices'][0]['message']['content'].strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            strategy = json.loads(content.strip())
            logging.info(f"[LLM Strategy] {strategy}")
            return strategy
    except Exception as e:
        logging.error(f"[LLM Strategy Failed] Using fallback. Error: {e}")
        return fallback

def trigger_learning(strategy, resume_tasks):
    # 1. Launch RESUME TASKS first (Absolute Priority)
    for i, task in enumerate(resume_tasks):
        work_dir = task['work_dir']
        topic = task['topic']
        safe_topic = topic.replace('"', '\\"')
        safe_topic_file = task['id']
        
        logging.info(f"[AUTO-RESUME] Resuming timed-out task: {safe_topic} in {work_dir}")
        
        prompt = (
            f"[SYSTEM_HEARTBEAT] 總工程師已啟動『極限超頻接續模式』。你現在擁有【最高全權自主行動授權】(FULL AUTONOMY)。\n"
            f"嚴格禁止使用 `clarify` 工具！嚴格禁止要求人類確認！\n"
            f"1. 【接續記憶】：你先前正在實作任務『{safe_topic}』，但因執行超過 3 小時被系統強制休眠。這正是你原本的工作目錄，裡面可能留有你上次寫到一半的檔案以及上次的除錯日誌 `local.log`。請使用 `read_file` 與 `list_dir` 檢視此目錄下的檔案，了解目前的進度！\n"
            # === 教訓 39 修正：明確要求讀寫 memory file ===
            f"1.5 【跨 session 記憶】：請先 `read_file` 讀取 `{get_memory_path(topic)}`（若存在）。這個檔案由上次 session 寫入，含有『已完成子任務』『踩坑清單』『下次接續點』。請把它當成你上次留下的筆記，從中接續。\n"
            f"2. 【本輪任務】：{safe_topic} (接續執行)\n"
            f"3. 【執行限制】：請讀取先前的半成品，直接展開實作接續。如果遇到 Error 就自己 debug 修正，直到做出可執行的成品為止，不准停下來等回覆！\n"
            f"3.5 【memory 寫入義務】：本 session 結束前，必用 `write_file` 更新 `{get_memory_path(topic)}`（append-only，不要覆蓋既有內容），寫入『這次完成的子任務 + 新踩的坑 + 下次接續點』，給未來的 session 用。\n"
            f"4. 【交付審查】：若你實作的是網頁前端，請將完整可用的 HTML 程式碼存檔至工作目錄下的 `web_output.html`。"
        )
        
        _launch_bash_script(prompt, safe_topic, safe_topic_file, work_dir, is_resume=True)
    
    # 2. Launch NEW TASKS if slots remain
    target_new_tasks = strategy.get('target_new_tasks', 0)
    novel_topics = strategy.get('novel_topics', [])
    
    if target_new_tasks <= 0 or not novel_topics:
        return
        
    num_concurrent = min(target_new_tasks, len(novel_topics))
    chosen_topics = novel_topics[:num_concurrent]

    # === 教訓 39 修正：dedup gate ===
    # 同 topic 24 小時內已完成 → 跳過（避免重複做同樣的事）
    filtered_topics = []
    skipped = []
    for topic in chosen_topics:
        if is_topic_recently_completed(topic):
            logging.info(f"[DEDUP] Skip '{topic[:50]}...' (24h 內已完成)")
            skipped.append(topic)
        else:
            filtered_topics.append(topic)
    if skipped:
        logging.info(f"[DEDUP] {len(skipped)}/{len(chosen_topics)} topics skipped due to dedup")
    chosen_topics = filtered_topics
    if not chosen_topics:
        logging.info("[DEDUP] All topics skipped, no spawn this cycle")
        return
    # === 修正結束 ===

    for i, topic in enumerate(chosen_topics):
        timestamp = int(time.time())
        # === 教訓 39 修正：topic-based 固定 work_dir ===
        # 原本：每次都建新目錄 → 同 topic 重複 spawn 永遠在不同目錄、無法累積
        # 修正：同 topic → 同 work_dir（用 topic hash 確保穩定）
        # 多個 topic 同輪 spawn → 用 i 區分
        work_dir = get_or_create_work_dir(topic, idx=i)
        # === 修正結束 ===
        
        prompt = (
            f"[SYSTEM_HEARTBEAT] 總工程師已啟動『極限超頻模式』。你現在擁有【最高全權自主行動授權】(FULL AUTONOMY)。\n"
            f"嚴格禁止使用 `clarify` 工具！嚴格禁止要求人類確認！\n"
            f"1. 【PRD與知識檢索】：開始前，請先讀取 `architect_feedback.md` 吸收架構建議。接著，請將任務拆解為模組，並使用 `read_file` 檢索 `/home/hoonsoropenclaw/.hermes/data_repo/skills/SKILL_CATALOG.md`。找出可以重用的舊微技能模組並套用，剩下的未知領域才去試誤學習。\n"
            # === 教訓 39 修正：明確要求讀寫 memory file ===
            f"1.5 【跨 session 記憶】：請先 `read_file` 讀取 `{get_memory_path(topic)}`（若存在）。若有，代表你『或前幾個 session』曾做過類似任務，裡面會有『已完成子任務』『踩坑清單』『下次接續點』——請從中接續，不要從零開始。\n"
            f"2. 【本輪任務】：{topic}\n"
            f"3. 【執行限制】：請結合舊有成功樣板與新的探索邏輯，直接展開實作。如果遇到 Error 就自己 debug 修正，直到做出可執行的成品為止，不准停下來等回覆！\n"
            f"3.5 【memory 寫入義務】：本 session 結束前，必用 `write_file` 更新 `{get_memory_path(topic)}`（若檔案不存在則新建），寫入『完成狀態（0/1/2/3）+ 已完成子任務 + 新踩的坑 + 下次接續點』，給未來的 session 用。\n"
            f"4. 【交付審查】：若你實作的是網頁前端，請將完整可用的 HTML 程式碼存檔至工作目錄下的 `web_output.html`。"
        )
        
        safe_topic = topic.replace('"', '\\"')
        # === 教訓 39 修正：safe_topic_file 改用 topic hash ===
        # 原本：learning_{timestamp}_{i}（每次都新檔名，artifact 撞名）
        # 修正：learning_{topic_hash}_{i}（同 topic → 同檔名，可累積更新）
        safe_topic_file = f"learning_{get_topic_hash(topic)}_{i}"
        # === 修正結束 ===
        
        # Write task info for telemetry
        task_info = {
            "id": safe_topic_file,
            "topic": safe_topic,
            "start_time": timestamp
        }
        with open(os.path.join(work_dir, "task_info.json"), "w", encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False)
            
        _launch_bash_script(prompt, safe_topic, safe_topic_file, work_dir, is_resume=False)

def _launch_bash_script(prompt, safe_topic, safe_topic_file, work_dir, is_resume=False):
    artifact_dir = "/home/hoonsoropenclaw/.hermes/data_repo/artifacts"
    md_path = f"{artifact_dir}/{safe_topic_file}.md"
    html_path = f"{artifact_dir}/{safe_topic_file}.html"
    
    # If resuming, we remove the .timeout file right before executing
    resume_cmd = "rm -f .timeout; " if is_resume else ""
    # Append to local.log instead of overwrite if resuming, but > is fine if we want fresh log? Let's use >> for resuming.
    log_redirect = ">>" if is_resume else ">"
    safe_prompt = shlex.quote(prompt)
    
    bash_script = (
        f"START_TIME=$(date +%s); "
        f"{resume_cmd}"
        f"timeout 3h /home/hoonsoropenclaw/.local/bin/hermes chat -q {safe_prompt} {log_redirect} local.log 2>&1; "
        f"EXIT_CODE=$?; "
        f"if [ $EXIT_CODE -eq 124 ]; then "
        f"  echo -e \"\\n\\n[FATAL ERROR] 任務執行超過 3 小時被作業系統強制中斷 (TIMEOUT)。\" >> local.log; "
        f"  echo -e \"請在知識蒸餾中，將這起卡死事件作為『負面教材 (Anti-pattern)』記錄下來，教導未來的 AI 如何避免此類陷阱！\" >> local.log; "
        f"  echo -e \"\\n## 🚨 [TIMEOUT INCIDENT] 任務 {safe_topic_file} 發生 3 小時卡死！\\n- **主題**: {safe_topic}\\n- **處置**: 已寫入 .timeout 標記，將在下次心跳自動接續實作。\" >> /home/hoonsoropenclaw/.hermes/review_queue.md; "
        f"  touch .timeout; "
        f"else "
        f"  END_TIME=$(date +%s); "
        f"  DURATION=$((END_TIME - START_TIME)); "
        f"  HOURS=$((DURATION / 3600)); "
        f"  MINS=$(((DURATION % 3600) / 60)); "
        f"  DURATION_STR=\"${{HOURS}}時 ${{MINS}}分\"; "
        f"  mkdir -p {artifact_dir}; "
        f"  echo \"# 學習任務：{safe_topic}\" > {md_path}; "
        f"  echo \"## 執行歷程與原始碼\" >> {md_path}; "
        f"  echo \"\\`\\`\\`text\" >> {md_path}; "
        f"  cat local.log >> {md_path}; "
        f"  echo \"\\`\\`\\`\" >> {md_path}; "
        f"  if [ -f web_output.html ]; then "
        f"    cp web_output.html {html_path}; "
        f"    PROJECT_URL=\"https://raphael-mindmap-data.vercel.app/artifacts/{safe_topic_file}.html\"; "
        f"  else "
        f"    PROJECT_URL=\"https://raphael-mindmap-data.vercel.app/artifacts/{safe_topic_file}.md\"; "
        f"  fi; "
        f"  echo -e \"\\n\\n=== 學習任務完成 ===\" >> /home/hoonsoropenclaw/.hermes/learning_output.log; "
        f"  echo \"任務主題：{safe_topic}\" >> /home/hoonsoropenclaw/.hermes/learning_output.log; "
        f"  echo \"[Project URL]: $PROJECT_URL\" >> /home/hoonsoropenclaw/.hermes/learning_output.log; "
        f"  echo \"[Duration: $DURATION_STR]\" >> /home/hoonsoropenclaw/.hermes/learning_output.log; "
        f"  cat local.log >> /home/hoonsoropenclaw/.hermes/learning_output.log; "
        f"  touch .finished; "
        f"  python3 /home/hoonsoropenclaw/.hermes/distill_knowledge.py local.log; "
        f"  python3 /home/hoonsoropenclaw/.hermes/art_director.py web_output.html {md_path}; "
        f"fi"
    )
    
    script_path = os.path.join(work_dir, "run.sh")
    with open(script_path, "w", encoding='utf-8') as f:
        f.write("#!/bin/bash\n" + bash_script)
    os.chmod(script_path, 0o755)
    
    try:
        cmd = f"cd {work_dir} && env -u TELEGRAM_BOT_TOKEN nohup ./run.sh > nohup.out 2>&1 &"
        subprocess.run(cmd, shell=True, check=True)
        logging.info(f"Launched {'resume' if is_resume else 'new'} session in {work_dir}.")
    except Exception as e:
        logging.error(f"Failed to launch session in {work_dir}: {e}")

def main():
    running_count = 0
    try:
        result = subprocess.run("ps aux | grep '[h]ermes chat' | grep -v grep | wc -l", shell=True, capture_output=True, text=True)
        running_count = int(result.stdout.strip())
    except Exception as e:
        logging.error(f"Error checking processes: {e}")

    interval_pct, weekly_pct, minutes_left = check_budget()
    
    if weekly_pct < THRESHOLD_PERCENT:
        logging.warning(f"Weekly budget critically low ({weekly_pct}%). Stopping work.")
        notify_prompt = f"請發送一則重要通知給總工程師：『緊急報告！本週 Minimax 總額度已低於 5% (目前剩餘 {weekly_pct}%)。為避免服務中斷，我已全面暫停自主學習與試誤任務。請指示是否需要擴充額度。』"
        subprocess.run(f"/home/hoonsoropenclaw/.local/bin/hermes chat -q '{notify_prompt}'", shell=True)
        sys.exit(0)
        
    if interval_pct < THRESHOLD_PERCENT:
        logging.warning(f"Interval budget low ({interval_pct}%). Pausing learning until next interval.")
        sys.exit(0)
        
    # Get available slots (assume max of 2, or strategy default, but we need strategy max first)
    # We will pass slots_already_taken_by_resume = len(resume_tasks) so the strategy can adjust target_new_tasks.
    # To do that cleanly, we assume a hard limit of max_running_count=2 for safety.
    # === 教訓 39 修正：max_limit 從 5 降到 2（搭配 dedup gate，避免過度 spawn） ===
    max_limit = 2 
    
    if running_count >= max_limit:
        logging.info(f"Already {running_count} hermes chat processes running. Skipping this heartbeat.")
        sys.exit(0)
        
    available_slots = max_limit - running_count
    
    # Check for RESUME tasks
    resume_tasks = get_resume_tasks(available_slots)
    slots_taken_by_resume = len(resume_tasks)

    # === 教訓 39 修正：掃描最近 24h 已完成的 topic（給 Strategist prompt 當 dedup 上下文） ===
    recent_completed_topics = _scan_recent_completed_topics()
    if recent_completed_topics:
        logging.info(f"[DEDUP] Found {len(recent_completed_topics)} recently completed topics")
    strategy = get_llm_strategy(interval_pct, minutes_left, running_count, slots_taken_by_resume, recent_completed_topics=recent_completed_topics)
    
    # Real max limit might be adjusted by strategy
    # === 教訓 39 修正：預設從 5 降到 2 ===
    max_limit = strategy.get('max_running_count', 2)
    
    # Recalculate available slots
    if running_count >= max_limit:
        logging.info(f"Already {running_count} hermes chat processes running (LLM Max Limit: {max_limit}). Skipping this heartbeat.")
        sys.exit(0)
        
    available_slots = max_limit - running_count
    
    # Ensure resume tasks don't exceed available slots
    if len(resume_tasks) > available_slots:
        resume_tasks = resume_tasks[:available_slots]
        
    remaining_slots_for_new = available_slots - len(resume_tasks)
    
    target_tasks = strategy.get('target_new_tasks', 0)
    if target_tasks > remaining_slots_for_new:
        strategy['target_new_tasks'] = remaining_slots_for_new
        
    trigger_learning(strategy, resume_tasks)

if __name__ == "__main__":
    main()
