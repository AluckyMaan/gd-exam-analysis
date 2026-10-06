import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire('file:///C:/Users/YANG/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright/package.json');
const { chromium } = require('playwright');

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');
const outDir = join(root, 'xhs_publish_materials');
const dashboard = join(root, '广东省考综合数据分析看板.html');

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1080, height: 1440 }, deviceScaleFactor: 1 });

async function dashboardReady() {
  await page.waitForLoadState('load');
  await page.waitForTimeout(1400);
}

async function saveViewport(name) {
  await page.screenshot({ path: join(outDir, name), fullPage: false });
}

async function clickTab(selector) {
  await page.locator(selector).click();
  await page.waitForTimeout(1200);
}

const yearly = [
  ['2020', 5941],
  ['2021', 6509],
  ['2022', 7886],
  ['2023', 6900],
  ['2024', 6752],
  ['2025', 7047],
  ['2026', 5730],
];

const coverHtml = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    width: 1080px;
    height: 1440px;
    font-family: "Noto Serif SC", "Microsoft YaHei", sans-serif;
    background: #f6f1e8;
    color: #172033;
  }
  .page {
    height: 100%;
    padding: 84px 82px;
    background:
      linear-gradient(180deg, rgba(23,32,51,.94), rgba(23,32,51,.88) 39%, rgba(246,241,232,1) 39%),
      radial-gradient(circle at 85% 12%, rgba(191,153,76,.25), transparent 28%);
  }
  .eyebrow { color: #d9bd74; font-size: 30px; letter-spacing: .12em; margin-bottom: 22px; }
  h1 { color: #fff; font-size: 86px; line-height: 1.06; margin: 0; letter-spacing: 0; }
  .sub { color: rgba(255,255,255,.78); font-size: 34px; line-height: 1.55; margin-top: 30px; max-width: 850px; }
  .panel {
    margin-top: 94px;
    background: #fffaf0;
    border: 1px solid rgba(23,32,51,.12);
    border-radius: 6px;
    padding: 44px 48px 38px;
    box-shadow: 0 24px 60px rgba(23,32,51,.13);
  }
  .panel h2 { margin: 0 0 12px; font-size: 42px; line-height: 1.22; color: #172033; }
  .note { font-size: 25px; color: #5d6473; line-height: 1.55; margin-bottom: 22px; }
  .chart { width: 100%; height: 360px; display: block; }
  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 26px; }
  .stat { border-left: 4px solid #b99243; background: rgba(185,146,67,.08); padding: 18px 18px; }
  .num { font-family: Georgia, serif; font-size: 39px; font-weight: 700; color: #172033; }
  .label { font-size: 21px; color: #687083; margin-top: 4px; }
  .footer { margin-top: 30px; font-size: 25px; color: #172033; font-weight: 700; }
  .url { margin-top: 8px; font-size: 24px; color: #5d6473; font-family: Arial, sans-serif; }
</style>
</head>
<body>
<main class="page">
  <div class="eyebrow">广东省考职位数据看板</div>
  <h1>近年招录<br>不是一路扩招</h1>
  <div class="sub">2020-2022 快速上升，2023-2025 进入高位平台，2026 明显回落。选岗不能只看总量，更要看专业和城市结构。</div>
  <section class="panel">
    <h2>2020-2026 全省招录人数趋势</h2>
    <div class="note">单位：人。基于广东省考职位表按城市口径汇总。</div>
    <svg class="chart" viewBox="0 0 900 360" aria-label="年度招录趋势折线图">
      <defs>
        <linearGradient id="area" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#b99243" stop-opacity=".36"/>
          <stop offset="100%" stop-color="#b99243" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <line x1="52" y1="300" x2="860" y2="300" stroke="#d8d1c4" stroke-width="2"/>
      <line x1="52" y1="58" x2="52" y2="300" stroke="#d8d1c4" stroke-width="2"/>
      <path d="M 70 230 L 195 189 L 320 70 L 445 164 L 570 174 L 695 151 L 820 248" fill="none" stroke="#172033" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M 70 230 L 195 189 L 320 70 L 445 164 L 570 174 L 695 151 L 820 248 L 820 300 L 70 300 Z" fill="url(#area)"/>
      ${yearly.map(([y, v], i) => {
        const xs = [70,195,320,445,570,695,820];
        const ys = [230,189,70,164,174,151,248];
        return `<circle cx="${xs[i]}" cy="${ys[i]}" r="9" fill="#b99243"/><text x="${xs[i]}" y="${ys[i]-22}" text-anchor="middle" font-size="24" font-family="Arial" fill="#172033">${v}</text><text x="${xs[i]}" y="336" text-anchor="middle" font-size="23" font-family="Arial" fill="#687083">${y}</text>`;
      }).join('')}
    </svg>
    <div class="stats">
      <div class="stat"><div class="num">7886</div><div class="label">2022 达到阶段峰值</div></div>
      <div class="stat"><div class="num">约 6.9k</div><div class="label">2023-2025 高位波动</div></div>
      <div class="stat"><div class="num">5730</div><div class="label">2026 总量回落</div></div>
    </div>
    <div class="footer">点进网页，看你的专业和城市机会</div>
    <div class="url">aluckymaan.github.io/gd-exam-analysis/</div>
  </section>
</main>
</body>
</html>`;

await page.setContent(coverHtml, { waitUntil: 'load' });
await saveViewport('01_cover_recent_trend.png');

await page.goto(pathToFileURL(dashboard).href);
await dashboardReady();
await saveViewport('02_dashboard_overview.png');

await clickTab('[data-subtab="m-tab4"]');
await saveViewport('03_major_recent_trends.png');

await clickTab('[data-subtab="m-tab1"]');
await saveViewport('04_major_top30_ranking.png');

await clickTab(`button[onclick="switchSection('section2')"]`);
await saveViewport('05_city_insights.png');

await clickTab('[data-subtab="c-tab3"]');
await saveViewport('06_city_yearly_trend.png');

await clickTab('[data-subtab="c-tab4"]');
await saveViewport('07_fresh_education.png');

await browser.close();
await writeFile(join(outDir, 'README.md'), [
  '# 小红书发布图片材料',
  '',
  '01_cover_recent_trend.png - 封面结论图，主打近年来招录趋势变化。',
  '02_dashboard_overview.png - 网页首页和总览数据。',
  '03_major_recent_trends.png - 专业趋势总览。',
  '04_major_top30_ranking.png - 专业 Top30 排名。',
  '05_city_insights.png - 城市格局洞察。',
  '06_city_yearly_trend.png - 城市年度趋势。',
  '07_fresh_education.png - 应往届与学历分布。',
  '',
  '建议发布顺序：01 -> 03 -> 04 -> 05 -> 07 -> 02。',
].join('\n'), 'utf8');

console.log(`Saved materials to ${outDir}`);
