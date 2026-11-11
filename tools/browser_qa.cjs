/* Optional browser QA: npm install --prefix .qa-tools playwright @axe-core/playwright */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
function dependency(name) {
  try { return require(name); }
  catch { return require(path.join(process.env.VERDANT_QA_MODULES || path.resolve('.qa-tools/node_modules'), name)); }
}
const { chromium, firefox, webkit } = dependency('playwright');
const AxeBuilder = dependency('@axe-core/playwright').default;
const base = process.env.VERDANT_QA_URL || 'http://127.0.0.1:8501';
const output = path.resolve(process.env.VERDANT_QA_OUTPUT || 'dist/browser-qa');
const screenshots = path.resolve('docs/screenshots');
fs.mkdirSync(output, { recursive: true });
fs.mkdirSync(screenshots, { recursive: true });
const results = [];

async function audit(page, label) {
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  const violations = axe.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) }));
  fs.writeFileSync(path.join(output, `${label}-axe.json`), JSON.stringify(violations, null, 2));
  return violations;
}
async function main() {
  const engine = process.env.VERDANT_QA_ENGINE || 'chromium';
  const browserType = { chromium, firefox, webkit }[engine];
  assert(browserType, 'Choose chromium, firefox or webkit');
  const browser = await browserType.launch({ headless: true,
    ...(engine === 'chromium' && process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH, args: ['--no-sandbox'] } : {}) });
  try {
    for (const [name, width, height] of [['desktop', 1440, 1000], ['tablet', 820, 1180], ['mobile', 390, 844], ['small-mobile', 320, 740]]) {
      const context = await browser.newContext({ viewport: { width, height }, reducedMotion: name.includes('mobile') ? 'reduce' : 'no-preference' });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.goto(base);
      await page.locator('.vc-allocation').waitFor({ timeout: 60000 });
      assert.equal(await page.locator('#conviction-with-a-paper-trail').count(), 1, 'Skip-link destination must exist');
      if (name.includes('mobile')) assert.equal(await page.locator('.vc-hero').evaluate(e => getComputedStyle(e).animationName), 'none');
      await page.getByRole('button', { name: 'Review this mandate', exact: true }).click();
      await page.getByText(/Decision #\d+ recorded/).waitFor({ timeout: 60000 });
      assert.equal(await page.getByTestId('stException').count(), 0);
      await page.keyboard.press('Tab');
      const keyboardFocus = await page.evaluate(() => document.activeElement !== document.body);
      assert(keyboardFocus, 'Keyboard focus must move to an interactive element');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert(!overflow, `${name}: page overflows horizontally`);
      const boardroomViolations = await audit(page, `${engine}-${name}-boardroom`);
      await page.locator('.vc-hero').scrollIntoViewIfNeeded();
      if (['desktop', 'mobile'].includes(name)) await page.screenshot({ path: path.join(screenshots, `boardroom-${name}.png`) });
      await page.getByText('Risk Lab', { exact: true }).click();
      await page.getByText('C02 — Rare-event stress', { exact: true }).waitFor({ timeout: 60000 });
      await page.getByText('Decision economics · C13', { exact: true }).click();
      await page.getByRole('cell', { name: '4920', exact: true }).waitFor({ timeout: 60000 });
      const c13Violations = await audit(page, `${engine}-${name}-c13`);
      await page.getByText('C13 — Decision economics', { exact: true }).scrollIntoViewIfNeeded();
      if (['desktop', 'mobile'].includes(name)) {
        await page.screenshot({ path: path.join(screenshots, `c13-${name}.png`) });
        await page.getByText('Held-out confusion matrix — optimized policy', { exact: true }).scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(screenshots, `c13-results-${name}.png`) });
      }
      await page.getByRole('spinbutton', { name: 'Financial loss per missed positive (USD)' }).fill('50000');
      await page.getByRole('button', { name: 'Optimize economic threshold', exact: true }).click();
      await page.getByRole('cell', { name: 'FN: $50,000.00', exact: true }).waitFor({ timeout: 60000 });
      await page.getByTestId('stStatusWidget').waitFor({ state: 'hidden', timeout: 60000 });
      await page.getByText('Economic assumptions, split methodology and complete evidence', { exact: true }).click();
      const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download C13 audit ($100 audit / $50000 missed)', exact: true }).click()]);
      const downloaded = path.join(output, `${engine}-${name}-c13.json`);
      await download.saveAs(downloaded);
      assert.equal(JSON.parse(fs.readFileSync(downloaded)).cost_matrix_usd.fn, 50000);
      await page.getByText('Market intelligence', { exact: true }).click();
      await page.getByRole('heading', { name: 'Market intelligence', exact: true }).waitFor();
      await page.getByText('Audit trail', { exact: true }).click();
      await page.getByRole('heading', { name: 'Decision audit trail', exact: true }).waitFor();
      assert.equal(await page.getByTestId('stException').count(), 0);
      results.push({ engine, viewport: name, width, keyboardFocus, overflow, errors, boardroomViolations, c13Violations });
      assert.equal(errors.length, 0, errors.join('\n'));
      await context.close();
    }
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(output, `${engine}-results.json`), JSON.stringify(results, null, 2));
  }
  const count = results.flatMap(r => [...r.boardroomViolations, ...r.c13Violations]).length;
  process.stdout.write(JSON.stringify({ engine, viewports: results.length, accessibilityViolations: count }) + '\n');
  assert.equal(count, 0, 'Accessibility findings require remediation or explicit triage in QA_REPORT.md');
}
main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
