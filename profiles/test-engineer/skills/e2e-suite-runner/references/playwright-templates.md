# Playwright E2E 範本集

## 基本 E2E 結構

```typescript
import { test, expect } from '@playwright/test';

test.describe('Sprint <N>: <feature name>', () => {
  test('happy path: <scenario>', async ({ page }) => {
    // Given: <precondition>
    await page.goto('http://localhost:3000/...');
    
    // When: <action>
    await page.click('[data-testid="..."]');
    
    // Then: <assertion>
    await expect(page.locator('...')).toBeVisible();
  });
  
  test('error path: <scenario>', async ({ page }) => {
    // Given
    await page.goto('...');
    
    // When: 故意觸發錯誤
    await page.fill('[data-testid="email"]', 'invalid-email');
    await page.click('[data-testid="submit"]');
    
    // Then: 應該顯示錯誤訊息
    await expect(page.locator('[data-testid="error"]')).toContainText('...');
  });
});
```

## 常見元件選擇器

| 用途 | selector | 為什麼 |
|------|----------|--------|
| 輸入框 | `input[data-testid="email"]` | 用 data-testid 不用 CSS class |
| 按鈕 | `button[data-testid="submit"]` | 同上 |
| 連結 | `a[data-testid="nav-home"]` | 同上 |
| 錯誤訊息 | `[data-testid="error-message"]` | 同上 |
| 載入中 | `[data-testid="loading-spinner"]` | 用 .toBeHidden() 等消失 |
| 確認 modal | `[data-testid="confirm-modal"]` | 通常會自動出現 |

## 等待元素的方式

| 方式 | 用法 | 為什麼 |
|------|------|------|
| `await expect(locator).toBeVisible()` | 等元素出現 | 自動等、避免 race condition |
| `await expect(locator).toHaveText('...')` | 等元素有特定文字 | 自動等 |
| `await expect(locator).toBeHidden()` | 等元素消失 | 自動等 |
| `await page.waitForURL('...')` | 等 URL 改變 | 自動等 |
| ❌ `await page.waitForTimeout(5000)` | 等 5 秒 | **不要**用、超慢、flaky |

## 失敗時 debug

```typescript
test('sprint-1 login', async ({ page }) => {
  test.slow();  // 給 2x 時間
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err));
  page.on('requestfailed', req => console.log('REQ FAIL:', req.url(), req.failure()?.errorText));
  
  // ... test code ...
});
```

**`page.on` 是黃金**：失敗時 console / page error / network error 都有。

## CI 整合（GitHub Actions）

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: docker compose up -d  # 起 test env
      - run: npx playwright test  # 跑 E2E
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
      - run: docker compose down --volumes
```

## 範本：登入流程

```typescript
test('login with valid credentials', async ({ page }) => {
  // Given: User is on login page
  await page.goto('http://localhost:3000/login');
  
  // When: User submits valid credentials
  await page.fill('[data-testid="email-input"]', 'test@example.com');
  await page.fill('[data-testid="password-input"]', 'TestPassword123!');
  await page.click('[data-testid="submit-button"]');
  
  // Then: User is redirected to dashboard
  await expect(page).toHaveURL(/.*\/dashboard/);
  await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
});
```

## 範本：CRUD 操作

```typescript
test('create post', async ({ page }) => {
  // Given: User is logged in
  await page.goto('http://localhost:3000/posts/new');
  
  // When: User creates a post
  await page.fill('[data-testid="title"]', 'Test Post');
  await page.fill('[data-testid="content"]', 'Lorem ipsum...');
  await page.click('[data-testid="save-button"]');
  
  // Then: Post appears in list
  await expect(page.locator('text=Test Post')).toBeVisible();
});

test('edit post', async ({ page }) => {
  // ... 編輯
});

test('delete post', async ({ page }) => {
  // ... 刪除
  await page.click('[data-testid="confirm-delete"]');
  await expect(page.locator('text=Test Post')).toBeHidden();
});
```

## 範本：API 整合測試

```typescript
test('API returns user data on login', async ({ request }) => {
  const response = await request.post('http://localhost:8000/api/auth/login', {
    data: {
      email: 'test@example.com',
      password: 'TestPassword123!',
    },
  });
  
  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(data).toHaveProperty('token');
  expect(data.user.email).toBe('test@example.com');
});
```

_Last updated: 2026-06-11（e2e-suite-runner 附錄）_
