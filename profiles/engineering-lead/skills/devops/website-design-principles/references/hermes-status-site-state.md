# hermes-status-site 重構後現況

## 最終架構
```
hermes-status-site/
├── index.html          89行  ← 乾淨 shell
├── css/styles.css      298行
├── js/app.js           23行  ← loadTab() 在這裡
└── tabs/
    ├── overview.html
    ├── memory.html
    ├── delegation.html
    ├── tools.html
    ├── skills.html      227行  ← 技能統計要插入這裡
    ├── soul.html
    ├── md-files.html
    ├── scheduler.html
    ├── learning.html
    ├── system-info.html
    └── dashboard.html
```

## loadTab() 路徑對照
```javascript
async function loadTab(tabName) {
    const response = await fetch(`tabs/${tabName}.html`);
    // data-tab="mdfiles" → tabs/md-files.html
    // data-tab="sysinfo"  → tabs/system-info.html
    // data-tab="skills"   → tabs/skills.html
}
```

## 下一步
1. 將 `<!-- SKILL_STATS_MARKER -->` 寫入 `tabs/skills.html`
2. 重寫 `~/.hermes/scripts/skill_usage_stats.py` 針對獨立檔案插入
3. 設定 cron 每小時執行
4. 部署到 Vercel

## 備份位置
`hermes-status-site.bak.20260601234854/`（原始 2936 行 index.html）