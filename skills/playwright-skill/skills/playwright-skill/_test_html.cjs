
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 800 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('file:///home/hoonsoropenclaw/.hermes/projects/learning_1785751215_8/web_output.html');
  await page.waitForTimeout(500);

  // 量各預設的 FPS
  const results = {};
  for (const t of ['fire','explosion','firework','snow','smoke','magic']) {
    await page.click(`button.preset[data-type="${t}"]`);
    await page.waitForTimeout(50);
    // 量 1.5 秒
    const measure = await page.evaluate(async () => {
      const fpsChip = document.getElementById('hud-fps');
      const startVal = fpsChip.textContent;
      await new Promise(r => setTimeout(r, 1500));
      const endVal = fpsChip.textContent;
      const s = window.__sim;
      const alive = s.Particle.pool.filter(p => !p.dead).length;
      return { start: startVal, end: endVal, alive };
    });
    results[t] = measure;
  }

  // 量互動期間 FPS
  const cv = await page.$('canvas#view');
  const box = await cv.boundingBox();
  await page.click('button.preset[data-type="fire"]');
  await page.waitForTimeout(200);
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.7);
  await page.mouse.down();
  const dragMeasure = await page.evaluate(async () => {
    const fpsChip = document.getElementById('hud-fps');
    await new Promise(r => setTimeout(r, 1200));
    return { end: fpsChip.textContent };
  });
  await page.mouse.up();

  // 量右鍵衝擊波
  await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.5, { button: 'right' });
  await page.waitForTimeout(800);
  await page.screenshot({ path: '/tmp/shot3_after_shockwave.png' });
  const finalState = await page.evaluate(() => {
    const s = window.__sim;
    const alive = s.Particle.pool.filter(p => !p.dead).length;
    return { alive, balls: s.balls.length, poolSize: s.Particle.pool.length };
  });

  await browser.close();
  console.log(JSON.stringify({ errors, results, dragMeasure, finalState }, null, 2));
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
