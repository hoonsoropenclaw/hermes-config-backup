# Daily Learning Plan Skill

## 目的
生成每日學習計畫的JSON格式清單，用於網頁界面展示和n8n自動化執行。

## 使用方式
當使用者要求生成每日學習計畫時，輸出以下格式的JSON：

```json
{
  "date": "YYYY-MM-DD",
  "main_tasks": [
    { "id": "m1", "task": "任務描述", "status": "pending" },
    { "id": "m2", "task": "任務描述", "status": "pending" }
  ],
  "sub_tasks": [
    { "id": "s1", "task": "任務描述", "status": "pending" }
  ]
}
```

## 規則
1. 只輸出JSON，不包含任何其他文字
2. 日期格式為YYYY-MM-DD
3. 任務ID格式：主任務為m1, m2, m3...，次要任務為s1, s2, s3...
4. 初始狀態一律為"pending"
5. 根據當天情況合理分配3-5個主任務和2-4個次要任務
6. 任務內容應涵蓋：技能學習、效率優化、工具掌握、知識擴展等方向

## 範例輸出
```json
{
  "date": "2026-03-22",
  "main_tasks": [
    { "id": "m1", "task": "學習n8n Webhook API整合", "status": "pending" },
    { "id": "m2", "task": "優化OpenClaw記憶檢索效率", "status": "pending" },
    { "id": "m3", "task": "研究Docker容器資源優化", "status": "pending" }
  ],
  "sub_tasks": [
    { "id": "s1", "task": "更新技能文件格式", "status": "pending" },
    { "id": "s2", "task": "測試新的token節省策略", "status": "pending" }
  ]
}
```