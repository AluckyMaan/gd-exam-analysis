import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');
const outDir = join(root, 'xhs_publish_materials');
const dashboard = join(root, '广东省考综合数据分析看板.html');

// Playwright 不是本项目依赖（项目坚持零 npm 依赖），此处不写死任何本机绝对路径。
// 解析顺序：① 环境变量 GD_EXAM_PLAYWRIGHT（指向 playwright 包目录或其 package.json）
//           ② 项目内/上层 node_modules（npm i -D playwright 后由 Node 自行解析）
// 都找不到时给出可执行的安装指引，而不是抛 ENOENT 堆栈。
function loadPlaywright() {
  const bases = [];
  if (process.env.GD_EXAM_PLAYWRIGHT) {
    const p = resolve(process.env.GD_EXAM_PLAYWRIGHT);
    bases.push(p.endsWith('.json') ? p : join(p, 'package.json'));
  }
  bases.push(import.meta.url);
  for (const base of bases) {
    try {
      return createRequire(base)('playwright');
    } catch (_) {
      /* 换下一个来源 */
    }
  }
  throw new Error([
    '未找到 playwright（本项目不把它作为依赖）。任选一种方式提供：',
    '  a) 在项目根执行:  npm i -D playwright && npx playwright install chromium',
    '  b) 复用它处已安装的副本:  设置环境变量 GD_EXAM_PLAYWRIGHT=<playwright 包目录>',
  ].join('\n'));
}

const { chromium } = loadPlaywright();

await mkdir(outDir, { recursive: true });

// ── 封面数字全部由数据源实时计算，不写死任何统计值（历史上这里写死过修复前的旧口径）──
const cityData = JSON.parse(readFileSync(join(root, 'data', 'city_data.json'), 'utf8'));
const yearlyTotals = {};
for (const entry of Object.values(cityData.city_yearly || {})) {
  for (const [y, v] of Object.entries(entry.yearly || {})) {
    yearlyTotals[y] = (yearlyTotals[y] || 0) + v;
  }
}
const years = Object.keys(yearlyTotals).sort();
const yearly = years.map((y) => [y, yearlyTotals[y]]);
if (yearly.length < 2) {
  throw new Error('data/city_data.json 未能解析出足够年度数据，无法生成封面趋势图');
}

const values = yearly.map(([, v]) => v);
const peakValue = Math.max(...values);
const peakYear = yearly[values.indexOf(peakValue)][0];
const lastYear = years[years.length - 1];
const lastValue = values[values.length - 1];
const plateauValues = yearly.filter(([y]) => y >= '2023' && y <= '2025').map(([, v]) => v);
const plateauAvg = plateauValues.length
  ? Math.round(plateauValues.reduce((a, b) => a + b, 0) / plateauValues.length)
  : null;
const trendText = peakYear === lastYear
  ? `${years[0]}-${lastYear} 持续上升。选岗不能只看总量，更要看专业和城市结构。`
  : `${years[0]}-${peakYear} 持续上升，其后高位波动，${lastYear} 回落至 ${lastValue} 人。选岗不能只看总量，更要看专业和城市结构。`;

// 折线图的像素坐标由数值等比例映射，避免图形与数字脱节
const xs = values.map((_, i) => Math.round(70 + i * (750 / Math.max(1, values.length - 1))));
const yTop = 58;
const yBase = 300;
const vMin = Math.min(...values);
const scale = (yBase - 18 - (yTop + 30)) / Math.max(1, peakValue - vMin);
const ys = values.map((v) => Math.round(yBase - 18 - (v - vMin) * scale));
const linePath = 'M ' + xs.map((x, i) => `${x} ${ys[i]}`).join(' L ');
const areaPath = `${linePath} L ${xs[xs.length - 1]} ${yBase} L ${xs[0]} ${yBase} Z`;

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
  <div class="sub">${trendText}</div>
  <section class="panel">
    <h2>${years[0]}-${lastYear} 全省招录人数趋势</h2>
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
      <path d="${linePath}" fill="none" stroke="#172033" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="${areaPath}" fill="url(#area)"/>
      ${yearly.map(([y, v], i) => {
        return `<circle cx="${xs[i]}" cy="${ys[i]}" r="9" fill="#b99243"/><text x="${xs[i]}" y="${ys[i] - 22}" text-anchor="middle" font-size="24" font-family="Arial" fill="#172033">${v}</text><text x="${xs[i]}" y="336" text-anchor="middle" font-size="23" font-family="Arial" fill="#687083">${y}</text>`;
      }).join('')}
    </svg>
    <div class="stats">
      <div class="stat"><div class="num">${peakValue}</div><div class="label">${peakYear} 达到峰值</div></div>
      <div class="stat"><div class="num">${plateauAvg === null ? '—' : `约 ${(plateauAvg / 1000).toFixed(1)}k`}</div><div class="label">2023-2025 高位平台（均值）</div></div>
      <div class="stat"><div class="num">${lastValue}</div><div class="label">${lastYear} 总量回落</div></div>
    </div>
    <div class="footer">点进网页，看你的专业和城市机会</div>
    <div class="url">aluckymaan.github.io/gd-exam-analysis/</div>
  </section>
</main>
</body>
</html>`;

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

// 文件名与数量必须与 xhs_publish_materials/ 现有 9 张发布图一一对应，
// 重截时是「原位替换」而不是另存一堆新文件。
// 注意：本脚本**不覆盖** xhs_publish_materials/README.md —— 那份文件含手写的标题与正文文案。
await page.setContent(coverHtml, { waitUntil: 'load' });
await saveViewport('01_cover_recent_trend.png');

await page.goto(pathToFileURL(dashboard).href);
await dashboardReady();
await saveViewport('02_dashboard_overview.png');            // 洞察总览

await clickTab('[data-subtab="m-tab4"]');
await saveViewport('03_major_recent_trends.png');           // 趋势总览

await clickTab('[data-subtab="m-tab1"]');
await saveViewport('04_major_top30_ranking.png');           // Top30 排名

await clickTab('[data-subtab="m-tab5"]');
await saveViewport('05_major_comparison.png');              // 综合对比

await clickTab(`button[onclick="switchSection('section2')"]`);
await saveViewport('06_city_insights.png');                 // 城市洞察（section2 默认页）

await clickTab('[data-subtab="c-tab5"]');
await saveViewport('07_city_major_distribution.png');       // 专业×地域

await clickTab('[data-subtab="c-tab3"]');
await saveViewport('08_city_yearly_trend.png');             // 城市年度趋势

await clickTab('[data-subtab="c-tab4"]');
await saveViewport('09_fresh_education.png');               // 应往届·学历

await browser.close();

console.log(`Saved 9 materials to ${outDir}`);
