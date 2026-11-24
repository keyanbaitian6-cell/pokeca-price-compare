#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '../..');
const KIT_DIR = path.join(REPO_ROOT, 'freelance-kit');
const DEMO_DIR = path.join(REPO_ROOT, 'site/portfolio-demo');

const demoSandbox = { globalThis: null };
demoSandbox.globalThis = demoSandbox;
vm.runInNewContext(fs.readFileSync(path.join(DEMO_DIR, 'app.js'), 'utf8'), demoSandbox, {
  filename: 'site/portfolio-demo/app.js',
});
const demoApp = demoSandbox.ZeroRunDemo;

function walkFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkFiles(full));
    } else {
      results.push(full);
    }
  }
  return results;
}

// 1. Secret / Privacy / Forbidden content leakage scan
const forbiddenChecks = [
  { label: 'personal output spreadsheet ID', regex: /1N3mF4tIjuq8|lFLP8ZNysYI/i },
  { label: 'source spreadsheet ID', regex: /1uNtzhQBeiPm|4ecZAjBE15g/i },
  { label: 'personal Vercel updater domain', regex: /pokeca-price-update\.vercel\.app/i },
  { label: 'real store name (somurie)', regex: /買取ソムリエ|somurie/i },
  { label: 'real store name (runto)', regex: /\brunto\b|runto666/i },
  { label: 'real store name (collect)', regex: /コレクト|collect_sheet/i },
  { label: 'Rakuten ROOM reference', regex: /楽天\s*ROOM|rakuten\s*room/i },
  { label: 'private GitHub owner in public demo/kit', regex: /keyanbaitian6-cell/i },
];

const filesToScan = [...walkFiles(KIT_DIR), ...walkFiles(DEMO_DIR)].filter(
  (filePath) => path.resolve(filePath) !== path.resolve(__filename)
);

for (const filePath of filesToScan) {
  const content = fs.readFileSync(filePath, 'utf8');
  for (const check of forbiddenChecks) {
    assert.equal(
      check.regex.test(content),
      false,
      `Forbidden content (${check.label}) found in ${path.relative(REPO_ROOT, filePath)}`
    );
  }
}
console.log(`PASS: Privacy & constraint scan (${filesToScan.length} files clean)`);

// 2. Verify all relative markdown links in freelance-kit/ resolve to existing files
const mdFiles = walkFiles(KIT_DIR).filter((f) => f.endsWith('.md'));
const linkRe = /\[[^\]]+\]\(([^)]+)\)/g;
let linkCount = 0;
for (const mdFile of mdFiles) {
  const content = fs.readFileSync(mdFile, 'utf8');
  for (const match of content.matchAll(linkRe)) {
    const target = match[1].trim();
    if (/^(https?:|mailto:|#|\{\{)/i.test(target)) continue;
    const cleanTarget = target.split('#')[0];
    if (!cleanTarget) continue;
    const resolved = path.resolve(path.dirname(mdFile), cleanTarget);
    assert.equal(
      fs.existsSync(resolved),
      true,
      `Broken markdown link "${target}" in ${path.relative(REPO_ROOT, mdFile)}`
    );
    linkCount += 1;
  }
}
console.log(`PASS: Markdown link integrity (${linkCount} local links verified across ${mdFiles.length} docs)`);

// 3. Verify HTML element IDs referenced by app.js exist in index.html
const indexHtml = fs.readFileSync(path.join(DEMO_DIR, 'index.html'), 'utf8');
const appJs = fs.readFileSync(path.join(DEMO_DIR, 'app.js'), 'utf8');
const referencedIds = [...appJs.matchAll(/getElementById\(['"]([^'"]+)['"]\)/g)].map((m) => m[1]);
for (const id of new Set(referencedIds)) {
  assert.equal(
    new RegExp(`id=["']${id}["']`).test(indexHtml),
    true,
    `Missing id="${id}" in site/portfolio-demo/index.html`
  );
}
console.log(`PASS: DOM ID consistency (${new Set(referencedIds).size} element IDs matched)`);

// 4. Verify ROI calculator logic
const roi = demoApp.calculateRoi({
  minutesPerDay: 30,
  daysPerMonth: 22,
  hourlyWage: 1500,
  planCost: 30000,
});
assert.equal(roi.monthlyHours, 11.0);
assert.equal(roi.monthlySavings, 16500);
assert.equal(roi.annualSavings, 198000);
assert.equal(roi.paybackMonths, 1.8);
console.log('PASS: ROI calculator unit assertions');

// 5. Verify Quick Estimator tier matching & strict monotonicity
const lightEst = demoApp.calculateEstimate({
  sites: '1-2',
  tech: 'static',
  compare: 'list',
  optTrend: false,
  optMobile: false,
  optNotify: false,
  optSupport: false,
});
assert.equal(lightEst.minPrice, 15000);
assert.match(lightEst.planName, /ライト/);

const standardNoTrend = demoApp.calculateEstimate({
  sites: '3',
  tech: 'spa',
  compare: 'match',
  optTrend: false,
  optMobile: false,
  optNotify: false,
  optSupport: false,
});
const standardEst = demoApp.calculateEstimate({
  sites: '3',
  tech: 'spa',
  compare: 'match',
  optTrend: true,
  optMobile: false,
  optNotify: false,
  optSupport: false,
});
assert.equal(standardEst.minPrice, 30000);
assert.ok(standardNoTrend.minPrice < standardEst.minPrice, 'Removing trend option must lower price');
assert.match(standardEst.planName, /スタンダード/);

const customEst = demoApp.calculateEstimate({
  sites: '4-5',
  tech: 'spa',
  compare: 'match',
  optTrend: true,
  optMobile: true,
  optNotify: false,
  optSupport: false,
});
assert.equal(customEst.minPrice, 50000);
assert.match(customEst.planName, /カスタム/);
assert.ok(customEst.summaryText.includes('スマホ1タップ手動更新ページ'));
console.log('PASS: Quick estimator tier & monotonicity assertions');

// 6. Verify anonymized datasets, metrics calculation, and SVG sparklines
const datasets = demoApp.createInitialDatasets();
for (const [key, ds] of Object.entries(datasets)) {
  assert.ok(ds.items.length >= 5, `Dataset ${key} should have at least 5 items`);
  for (const item of ds.items) {
    const metrics = demoApp.computeItemMetrics(item, ds);
    assert.ok(metrics.bestPrice > 0, `${item.id} bestPrice must be positive`);
    assert.ok(metrics.spreadYen >= 0, `${item.id} spreadYen must be non-negative`);
    const svg = demoApp.buildSparklineSvg(item.history);
    assert.ok(svg.startsWith('<svg') && svg.includes('<polyline'), `${item.id} sparkline SVG invalid`);
  }
}
console.log('PASS: Anonymized datasets & SVG sparkline assertions');
console.log('ALL VERIFICATIONS PASSED');
