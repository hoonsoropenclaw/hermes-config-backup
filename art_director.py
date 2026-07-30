import sys
import os
import json
import base64
import urllib.request
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY_PATH = "/home/hoonsoropenclaw/.hermes/.gemini_api_key"
AESTHETIC_CATALOG = "/home/hoonsoropenclaw/.hermes/data_repo/skills/AESTHETIC_CATALOG.md"

def get_api_key():
    if not os.path.exists(API_KEY_PATH):
        logging.error("Gemini API Key not found. Please create ~/.hermes/.gemini_api_key")
        return None
    with open(API_KEY_PATH, "r") as f:
        return f.read().strip()

def take_screenshot(html_path, screenshot_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        # Use file:// protocol to load local html
        abs_path = os.path.abspath(html_path)
        page.goto(f"file://{abs_path}")
        # Wait a bit for fonts/animations to settle
        page.wait_for_timeout(1000)
        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()

def review_with_gemini(api_key, screenshot_path):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    with open(screenshot_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        
    payload = {
        "contents": [{
            "parts": [
                {"text": "You are a world-class UI/UX Art Director. Analyze this webpage screenshot for aesthetics, modern design practices (e.g. glassmorphism, rounded corners, drop shadows, visual hierarchy, typography, whitespace). Score it from 0 to 100. Return ONLY a valid JSON object matching this schema: {\"score\": 85, \"critique\": \"Your detailed critique here in Traditional Chinese\"} Do not use markdown backticks in output."},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": encoded_string
                    }
                }
            ]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode('utf-8'), method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            text_resp = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean markdown block if present
            if text_resp.startswith("```json"):
                text_resp = text_resp[7:]
            if text_resp.startswith("```"):
                text_resp = text_resp[3:]
            if text_resp.endswith("```"):
                text_resp = text_resp[:-3]
                
            return json.loads(text_resp.strip())
    except Exception as e:
        logging.error(f"Gemini API request failed: {e}")
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 art_director.py <html_path> <log_md_path>")
        sys.exit(1)
        
    html_path = sys.argv[1]
    log_md_path = sys.argv[2]
    
    if not os.path.exists(html_path):
        logging.info("No web_output.html found for this task. Skipping Art Director review.")
        sys.exit(0)
        
    api_key = get_api_key()
    if not api_key:
        sys.exit(1)
        
    screenshot_path = html_path.replace(".html", ".jpg")
    logging.info(f"Taking screenshot of {html_path}...")
    take_screenshot(html_path, screenshot_path)
    
    logging.info("Sending screenshot to Gemini Art Director...")
    review = review_with_gemini(api_key, screenshot_path)
    
    if not review:
        sys.exit(1)
        
    score = review.get("score", 0)
    critique = review.get("critique", "無評語")
    
    logging.info(f"Art Director Score: {score}")
    
    # Append critique to the task's markdown file
    if os.path.exists(log_md_path):
        with open(log_md_path, "a", encoding="utf-8") as f:
            f.write("\n\n## 🎨 藝術總監視覺審查 (Art Director Review)\n")
            f.write(f"- **美學分數**: {score}/100\n")
            f.write(f"- **總監評語**: {critique}\n")
            
    # Append to catalog if score is excellent
    if score >= 80:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        catalog_entry = (
            f"\n\n### 黃金美學樣板 (Score: {score})\n"
            f"> {critique}\n"
            f"```html\n{html_content}\n```\n"
        )
        
        os.makedirs(os.path.dirname(AESTHETIC_CATALOG), exist_ok=True)
        with open(AESTHETIC_CATALOG, "a", encoding="utf-8") as f:
            f.write(catalog_entry)
            
        logging.info("Score is >= 80! Appended to AESTHETIC_CATALOG.md")

if __name__ == "__main__":
    main()
