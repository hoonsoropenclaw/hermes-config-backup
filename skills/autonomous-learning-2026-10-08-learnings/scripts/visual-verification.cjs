#!/usr/bin/env node
// scripts/visual-verification.cjs
//
// 可重複跑的 Playwright 視覺驗證腳本：對一組 URL + role 截圖、量 boundingBox 確認
// 關鍵按鈕在 viewport 內、把結果輸出成 manifest.json。
//
// 用途：補「e2e toBeVisible() 通過但被 overflow:hidden 裁切」的盲點。SOP 來自
// autonomous-learning-2026-10-08-learnings pitfall #7 (day-2 2026-10-09)。
//
// 用法：
//   node scripts/visual-verification.cjs
//
// 客製：改頂端的 BASE_URL / VIEWPORT / ROUTES / CHECKPOINTS 即可。

const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:4173';
const OUT_DIR = process.env.OUT_DIR || './docs/visual-checks';
const VIEWPORT = { width: 1280, height: 720 };

// 待驗證的 route 與重要 testid。route 是 path，viewports/role 透過 ?as=<role> 預填
// （參考 day-1 / day-2 的 AuthContext ?as=role 慣例）。
const ROUTES = [
  { path: '/flows?as=employee', name: 'employee' },
  { path: '/flows?as=manager',  name: 'manager'  },
  { path: '/flows?as=principal',name: 'principal'},
];

// 必須出現在 viewport 內的關鍵 testid（每個 role 可能不同）。
const CHECKPOINTS = {
  employee:  ['flow-editor', 'btn-submit'],
  manager:   ['flow-editor', 'btn-add-manager', 'btn-approve-2'],
  principal: ['flow-editor', 'btn-approve-4'],
};

// 在 N100 環境，Playwright 預裝的 chromium 可能在以下任一路徑。
const CHROMIUM_CANDIDATES = [
  '/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',
  '/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1234/chrome-linux/chrome',
  '/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1223/chrome-linux/chrome',
];

(async () => {
  const exe = CHROMIUM_CANDIDATES.find((p) => fs.existsSync(p));
  if (!exe) {
    console.error('FATAL: 找不到 chromium，請跑 npx playwright install --with-deps chromium');
    process.exit(1);
  }
  console.log('chromium:', exe);

  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ executablePath: exe, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: VIEWPORT });
  const page = await ctx.newPage();
  const manifest = [];

  for (const route of ROUTES) {
    const url = `${BASE_URL}${route.path}`;
    const checkpointIds = CHECKPOINTS[route.name] || ['flow-editor'];
    console.log(`\n[${route.name}] ${url}`);

    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    // 1) 截圖
    const shotPath = path.join(OUT_DIR, `${route.name}.png`);
    await page.screenshot({ path: shotPath, fullPage: true });
    console.log('  shot:', shotPath);

    // 2) 量每個 checkpoint 的 boundingBox，確認在 viewport 內
    const checks = [];
    for (const testid of checkpointIds) {
      const loc = page.locator(`[data-testid="${testid}"]`).first();
      const exists = (await loc.count()) > 0;
      if (!exists) {
        checks.push({ testid, exists: false, in_viewport: false });
        continue;
      }
      const box = await loc.boundingBox();
      const inViewport =
        box &&
        box.y >= 0 &&
        box.y + box.height <= VIEWPORT.height &&
        box.x >= 0 &&
        box.x + box.width <= VIEWPORT.width;
      checks.push({
        testid,
        exists: true,
        in_viewport: inViewport,
        box: box ? { x: box.x, y: box.y, w: box.width, h: box.height } : null,
        viewport: VIEWPORT,
      });
      if (!inViewport) {
        console.log(`  ❌ [${testid}] 不在 viewport 內：`, box);
      } else {
        console.log(`  ✅ [${testid}] OK`);
      }
    }

    manifest.push({
      route: route.name,
      url,
      shot: shotPath,
      viewport: VIEWPORT,
      checks,
    });
  }

  await browser.close();

  const manifestPath = path.join(OUT_DIR, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log('\nmanifest:', manifestPath);

  // 3) 退出碼：有任何 not-in-viewport 就 fail（CI 可用）
  const failed = manifest.flatMap((m) => m.checks.filter((c) => c.in_viewport === false));
  if (failed.length > 0) {
    console.error(`\nFAIL: ${failed.length} 個關鍵 UI 元素不在 viewport 內`);
    process.exit(2);
  }
  console.log('\nALL CHECKPOINTS IN VIEWPORT ✅');
})();
