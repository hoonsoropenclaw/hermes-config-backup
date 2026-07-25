# Script Writing: Heredoc + Pipe Nesting Bugs

## 2026-06-18: `school-bulletin-system/scripts/deploy.sh` line 22

**Symptom**: `bash -n deploy.sh` → `unexpected EOF while looking for matching '('`

**Root Cause**: Compound command substitution with pipeline inside `$(...)` that mixed HTTP header quoting with shell redirects:

```bash
# BROKEN — the `2>/dev/null |` gets interpreted as part of the HTTP header string
STATUS=$(curl -s "https://api.vercel.com/v13/deployments?teamId=__dev&project=school-bulletin" \
  -H "Authorization: Bearer *** 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['deployments'][0]['status'])" \
  2>/dev/null || echo "pending")
```

**Fix**: Decompose into two separate commands — capture first, then process:

```bash
# Step 1: capture curl output to variable (no nesting)
CURL_OUT=$(curl -s "https://api.vercel.com/v13/deployments?teamId=__dev&project=school-bulletin" \
  -H "Authorization: Bearer *** 2>/dev/null)

# Step 2: pipe variable to python (separate command, no quoting conflict)
STATUS=$(echo "$CURL_OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('deployments'):
    print(d['deployments'][0]['status'])
else:
    print('pending')
" 2>/dev/null || echo "pending")
```

**Verification**:
```bash
bash -n deploy.sh   # must exit 0
# Then test the pipeline in isolation:
echo '{"deployments": [{"status": "ready"}]}' | python3 -c "import sys,json; print(json.load(sys.stdin)['deployments'][0]['status'])"
```

**Prevention**: 
- `bash -n script.sh` before committing/running any script
- Avoid nesting `$(...)` inside `$(...)` 
- Split compound pipelines into capture-then-process steps

**Lesson**: When writing scripts via `cat > file << 'ENDOFFILE'`, write the entire heredoc content in one block. When the script needs a curl-then-python pipeline, always use the two-step variable approach.
