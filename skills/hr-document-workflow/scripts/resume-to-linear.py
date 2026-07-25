#!/usr/bin/env python3
"""
resume-to-linear.py — Parse PDF resume → extract candidate info → create Linear issue
Usage: python3.12 resume-to-linear.py <resume_pdf_path> [--dry-run]
Requires: pdfminer.six (python3.12), LINEAR_API_KEY in env
"""
import sys, os, re, argparse

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdfminer.six (python3.12)."""
    from pdfminer.high_level import extract_text
    return extract_text(pdf_path)

def extract_text_from_scanned_pdf(pdf_path: str) -> str:
    """OCR a scanned PDF using tesseract (system python3.11)."""
    import subprocess, tempfile, os
    # Convert PDF pages to images using pdftoppm (poppler-utils)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ['pdftoppm', '-r', '300', '-l', '1', pdf_path, f'{tmpdir}/page'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {result.stderr}")
        # OCR the first page image
        ocr_result = subprocess.run(
            ['tesseract', f'{tmpdir}/page-1.ppm', 'stdout', '-l', 'chi_tra+eng'],
            capture_output=True, text=True
        )
        if ocr_result.returncode != 0:
            raise RuntimeError(f"tesseract failed: {ocr_result.stderr}")
        return ocr_result.stdout

def parse_resume_text(text: str) -> dict:
    """Parse candidate info from resume text using regex patterns."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Name: usually first non-empty line or after "姓名" pattern
    name = None
    name_patterns = [
        r'姓名[：:]\s*(\S+)',
        r'^([A-Za-z\u4e00-\u9fff]{2,4})$',  # 2-4 char name at line start
    ]
    for line in lines[:5]:  # Check first 5 lines
        for pat in name_patterns:
            m = re.search(pat, line)
            if m:
                name = m.group(1) if m.lastindex else m.group(0)
                break
        if name:
            break
    
    # Email
    email = None
    email_m = re.search(r'[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}', text)
    if email_m:
        email = email_m.group(0)
    
    # Phone (Taiwan format)
    phone = None
    phone_m = re.search(r'(?:手機|電話|TEL|電話號碼)[：: ]*([0-9]{2}[- ]?[0-9]{4}[- ]?[0-9]{4}|[0-9]{10})', text)
    if phone_m:
        phone = phone_m.group(1)
    else:
        # Try bare 09xx format
        phone_m2 = re.search(r'(09[0-9]{2}[- ]?[0-9]{3}[- ]?[0-9]{3})', text)
        if phone_m2:
            phone = phone_m2.group(1)
    
    # Position (what they're applying for)
    position = None
    position_m = re.search(r'(?:應徵|申請|報名|投件)[：: ]*(.+?)(?:\n|$)', text)
    if position_m:
        position = position_m.group(1).strip()
    else:
        # Try to find department/subject
        dept_m = re.search(r'(?:科別|科目|處室|部門)[：: ]*(\S+)', text)
        if dept_m:
            position = dept_m.group(1)
    
    # Education
    education = []
    edu_keywords = ['大學', '學院', '碩士', '博士', '研究所', 'college', 'university', 'Master', 'PhD', 'Bachelor']
    for line in lines:
        if any(kw in line for kw in edu_keywords) and len(line) < 100:
            education.append(line.strip())
    
    return {
        'name': name or '未知',
        'email': email,
        'phone': phone,
        'position': position or '代理教師',
        'education': education[:3],  # Top 3 entries
        'raw_text': text[:500],  # First 500 chars for LLM review
    }

def create_linear_issue(candidate: dict, dry_run: bool = False) -> dict:
    """Create a Linear issue for the candidate via GraphQL API."""
    import requests
    
    api_key = os.getenv('LINEAR_API_KEY')
    if not api_key:
        raise RuntimeError("LINEAR_API_KEY not set in environment")
    
    # First, find the HR team
    query = """
    query {
        teams(first: 10) {
            nodes { id name }
        }
    }
    """
    r = requests.post(
        'https://api.linear.app/graphql',
        headers={'Authorization': api_key, 'Content-Type': 'application/json'},
        json={'query': query}
    )
    if not r.ok:
        raise RuntimeError(f"Linear API error: {r.status_code} {r.text}")
    
    data = r.json()
    teams = data.get('data', {}).get('teams', {}).get('nodes', [])
    if not teams:
        raise RuntimeError("No Linear teams found")
    
    team_id = teams[0]['id']  # Use first team
    
    # Build issue title and body
    name = candidate['name']
    position = candidate['position']
    body_parts = [f"## 候選人資料 Candidate Information"]
    body_parts.append(f"- **姓名**: {name}")
    if candidate.get('email'):
        body_parts.append(f"- **Email**: {candidate['email']}")
    if candidate.get('phone'):
        body_parts.append(f"- **電話**: {candidate['phone']}")
    body_parts.append(f"- **應徵職位**: {position}")
    if candidate.get('education'):
        body_parts.append(f"- **學歷**: {'; '.join(candidate['education'])}")
    body_parts.append(f"\n## 原始履歷（前500字）")
    body_parts.append(f"```\n{candidate.get('raw_text', '')}\n```")
    body_parts.append(f"\n---\n*此候選人追蹤 issue 由赫米斯自動建立（resume-to-linear.py）*")
    
    mutation = """
    mutation CreateIssue($title: String!, $body: String, $teamId: String!) {
        issueCreate(input: {title: $title, body: $body, teamId: $teamId}) {
            success
            issue { id identifier title url }
        }
    }
    """
    variables = {
        'title': f'【應徵】{name} - {position}',
        'body': '\n'.join(body_parts),
        'teamId': team_id
    }
    
    if dry_run:
        return {'dry_run': True, 'variables': variables, 'team_id': team_id}
    
    r = requests.post(
        'https://api.linear.app/graphql',
        headers={'Authorization': api_key, 'Content-Type': 'application/json'},
        json={'query': mutation, 'variables': variables}
    )
    if not r.ok:
        raise RuntimeError(f"Linear issue create failed: {r.status_code} {r.text}")
    
    result = r.json()
    if result.get('errors'):
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    
    issue = result['data']['issueCreate']['issue']
    return {
        'success': True,
        'issue_id': issue['id'],
        'issue_identifier': issue['identifier'],
        'issue_url': issue['url']
    }

def main():
    parser = argparse.ArgumentParser(description='Parse PDF resume → create Linear issue')
    parser.add_argument('resume_pdf', help='Path to resume PDF file')
    parser.add_argument('--dry-run', action='store_true', help='Parse only, do not create Linear issue')
    parser.add_argument('--force-ocr', action='store_true', help='Force OCR even if text layer exists')
    args = parser.parse_args()
    
    if not os.path.exists(args.resume_pdf):
        print(f"❌ File not found: {args.resume_pdf}", file=sys.stderr)
        sys.exit(1)
    
    print(f"📄 Reading: {args.resume_pdf}")
    
    # Try text extraction first
    try:
        text = extract_text_from_pdf(args.resume_pdf)
        text_len = len(text.strip())
        print(f"   Text layer found ({text_len} chars)")
        if text_len < 50 or args.force_ocr:
            print("   → Text too short, falling back to OCR...")
            text = extract_text_from_scanned_pdf(args.resume_pdf)
    except Exception as e:
        print(f"   → Text extraction failed ({e}), trying OCR...")
        text = extract_text_from_scanned_pdf(args.resume_pdf)
    
    print(f"   Parsed text ({len(text.strip())} chars)")
    
    # Parse candidate info
    candidate = parse_resume_text(text)
    print(f"\n👤 Candidate: {candidate['name']}")
    print(f"   Position: {candidate['position']}")
    print(f"   Email: {candidate.get('email') or 'N/A'}")
    print(f"   Phone: {candidate.get('phone') or 'N/A'}")
    if candidate.get('education'):
        print(f"   Education: {candidate['education'][0]}")
    
    if args.dry_run:
        print("\n🔍 Dry run — skipping Linear issue creation")
        sys.exit(0)
    
    print("\n📋 Creating Linear issue...")
    result = create_linear_issue(candidate, dry_run=False)
    print(f"✅ Linear issue created!")
    print(f"   ID: {result['issue_identifier']}")
    print(f"   URL: {result['issue_url']}")

if __name__ == '__main__':
    main()
