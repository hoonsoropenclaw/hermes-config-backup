
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 800 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('file:///home/hoonsoropenclaw/.hermes/projects/learning_1785751215_8/web_output.html');
  await page.waitForTimeout(400);
  // 點三個預設 + 鍵盤按鍵
  await page.keyboard.press('1');  // fire
  await page.waitForTimeout(150);
  await page.keyboard.press('2');  // explosion
  await page.waitForTimeout(150);
  await page.keyboard.press('3');  // firework
  await page.waitForTimeout(150);
  await page.keyboard.press('g');  // 反重力
  await page.waitForTimeout(150);
  await page.keyboard.press(' ');  // 暫停
  await page.waitForTimeout(150);
  await page.keyboard.press(' ');  // 取消暫停
  await page.keyboard.press('r');  // reset
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/tmp/shot_final.png' });
  await browser.close();
  console.log(JSON.stringify({ errors, finalScreenshot: 'OK' }));
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
