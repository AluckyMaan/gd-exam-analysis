// 小红书发布图生成器（2027 版）——「直接出图」，不是看板截图。
//
// 用 data/*.json 实时算出数字，渲染 6 张 1080×1440 的竖版海报（3:4），
// 再用本机 Edge 的 CDP 逐张截取（零 npm 依赖，和 e2e 同一套思路）。
//
// 用法：
//   node scripts/generate_xhs_cards.mjs            # 输出到 xhs_publish_materials/2027/
//   node scripts/generate_xhs_cards.mjs --out DIR  # 自定义输出目录
//
// 说明：数字全部来自数据源，不写死任何统计值；文案与图表会随数据更新自动变化。
import { spawn, spawnSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, '..');
const outIdx = process.argv.indexOf('--out');
const outDir = path.resolve(outIdx >= 0 ? process.argv[outIdx + 1] : path.join(root, 'xhs_publish_materials', '2027'));
const PORT = 9337;
const CARD_W = 1080;
const CARD_H = 1440;

const CANDIDATES = [
  process.env.EDGE_PATH,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/microsoft-edge', '/usr/bin/google-chrome', '/usr/bin/chromium',
].filter(Boolean);
const browser = CANDIDATES.find((p) => existsSync(p));
if (!browser) { console.log('SKIP: 未找到 Chromium 系浏览器（可用 EDGE_PATH 指定）'); process.exit(0); }
if (typeof WebSocket !== 'function') { console.log('SKIP: 当前 Node 无内置 WebSocket（需 Node 22+）'); process.exit(0); }

// ── 数据 ──
const cityData = JSON.parse(readFileSync(path.join(root, 'data', 'city_data.json'), 'utf8'));
const majorData = JSON.parse(readFileSync(path.join(root, 'data', 'all_majors_ranking.json'), 'utf8'));

const numFmt = (v) => Math.round(v).toLocaleString('zh-CN');
const pct = (v, digits = 1) => (Math.round(v * 10 ** digits) / 10 ** digits).toFixed(digits);
const signed = (v) => (v > 0 ? '+' : '') + numFmt(v);
const signPct = (v) => (v > 0 ? '+' : '') + pct(v) + '%';

const yearlyTotals = {};
for (const entry of Object.values(cityData.city_yearly || {})) {
  for (const [y, v] of Object.entries(entry.yearly || {})) yearlyTotals[y] = (yearlyTotals[y] || 0) + v;
}
const years = Object.keys(yearlyTotals).sort();
const latest = years[years.length - 1];
const prev = years[years.length - 2];
const ySeries = years.map((y) => [y, yearlyTotals[y]]);
const latestTotal = yearlyTotals[latest];
const prevTotal = yearlyTotals[prev];
const totalDelta = latestTotal - prevTotal;
const totalPct = (totalDelta / prevTotal) * 100;

const struct = (cityData.yearly_structure || {})[latest] || {};
const structPrev = (cityData.yearly_structure || {})[prev] || {};
const edu = struct.education || {};
const fresh = struct.fresh || {};
const regions = struct.regions || {};
const freshRatio = ((fresh.fresh_any || 0) + (fresh.fresh_current || 0)) / struct.recruits * 100;
const freshRatioPrev = ((structPrev.fresh.fresh_any || 0) + (structPrev.fresh.fresh_current || 0)) / structPrev.recruits * 100;
const researchRatio = (edu['研究生'] || 0) / struct.recruits * 100;
const researchRatioPrev = (structPrev.education['研究生'] || 0) / structPrev.recruits * 100;
const prdRatio = (regions.prd || 0) / struct.recruits * 100;
const nonPrdRatio = (regions.non_prd || 0) / struct.recruits * 100;
const provinceRatio = (regions.province || 0) / struct.recruits * 100;
const positions = struct.positions;

const highEdu = (edu['研究生'] || 0) + (edu['本科以上'] || 0);
const highEduRatio = highEdu / struct.recruits * 100;
const bachelorRatio = (edu['本科'] || 0) / struct.recruits * 100;
const belowCollege = Math.max(0, struct.recruits - highEdu - (edu['本科'] || 0));

// 专业增/减（专业侧数值 = 该专业出现次数，不可相加）
const getY = (m, y) => {
  const v = (m.yearly || {})[y];
  if (typeof v === 'number') return v;
  return (v && v.recruits) || 0;
};
const majorRows = majorData.ranking.map((m) => ({
  name: m.major, code: m.code, type: m.type, raw: m,
  cur: getY(m, latest), prev: getY(m, prev),
}));
majorRows.forEach((r) => { r.delta = r.cur - r.prev; r.pct = r.prev ? (r.delta / r.prev) * 100 : null; });
const majorGain = majorRows.filter((r) => r.delta > 0).sort((a, b) => b.delta - a.delta).slice(0, 6);
const majorLoss = majorRows.filter((r) => r.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 6);
const majorTop = majorRows.slice().sort((a, b) => b.cur - a.cur).slice(0, 10);
const majorAdded = majorRows.filter((r) => r.cur > 0 && r.prev === 0).sort((a, b) => b.cur - a.cur).slice(0, 8);
const majorDropped = majorRows.filter((r) => r.prev > 0 && r.cur === 0).sort((a, b) => b.prev - a.prev).slice(0, 8);
const recentYears = years.slice(-3);
const majorTop3Trend = majorRows.slice().sort((a, b) => b.cur - a.cur).slice(0, 3).map((r) => ({
  name: r.name, values: recentYears.map((y) => getY(r.raw, y)),
}));

// 城市增/减
const cityRows = Object.keys(cityData.city_yearly || {}).map((c) => {
  const info = cityData.city_yearly[c];
  const cur = (info.yearly || {})[latest] || 0;
  const pv = (info.yearly || {})[prev] || 0;
  return { city: c, cur, prev: pv, delta: cur - pv };
});
const cityGain = cityRows.filter((r) => r.delta > 0).sort((a, b) => b.delta - a.delta);
const cityTop5 = cityRows.slice().sort((a, b) => b.cur - a.cur).slice(0, 5);
const cityLoss = cityRows.filter((r) => r.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 8);

// ── 文案里用到的结论（随数据变化）──
const trendWord = totalDelta < 0 ? '继续收缩' : '回升';
const coverTitle = `${latest} 招录<br><span class="gold">${trendWord}</span>`;

// ── 通用小组件 ──
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));

function barRows(rows, { max, color, formatter, showPct = false }) {
  const cap = max || Math.max(1, ...rows.map((r) => Math.abs(r.value)));
  return rows.map((r, i) => {
    const w = Math.max(3, Math.round((Math.abs(r.value) / cap) * 100));
    return `<div class="bar-row">
      <div class="bar-rank">${i + 1}</div>
      <div class="bar-name">${esc(r.name)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${w}%;background:${color}"></div></div>
      <div class="bar-val" style="color:${color}">${formatter(r)}${showPct && r.pct !== null && r.pct !== undefined ? `<span class="pct">${signPct(r.pct)}</span>` : ''}</div>
    </div>`;
  }).join('');
}

// 封面趋势图（SVG）
const chartW = 860, chartH = 356, padL = 84, padB = 42, padT = 44;
const plotW = chartW - padL - 16, plotH = chartH - padB - padT;
const maxV = Math.max(...ySeries.map(([, v]) => v));
const minV = 0;
const barW = Math.min(64, Math.round(plotW / ySeries.length * 0.46));
const svgBars = ySeries.map(([y, v], i) => {
  const x = padL + (plotW / ySeries.length) * (i + 0.5);
  const h = Math.round((v - minV) / (maxV - minV) * plotH);
  const yTop = padT + plotH - h;
  const isLast = i === ySeries.length - 1;
  const fill = isLast ? '#c1a05a' : '#2c3a58';
  return `<rect x="${x - barW / 2}" y="${yTop}" width="${barW}" height="${h}" rx="4" fill="${fill}"/>
    <text x="${x}" y="${yTop - 14}" text-anchor="middle" font-size="20" fill="#2a3247" font-family="Consolas, monospace">${numFmt(v)}</text>
    <text x="${x}" y="${chartH - 10}" text-anchor="middle" font-size="19" fill="#6a7285">${y}</text>`;
}).join('');
const svgGrid = [0, 6000, 12000, 18000].map((g) => {
  const y = padT + plotH - Math.round((g - minV) / (maxV - minV) * plotH);
  return `<line x1="${padL}" y1="${y}" x2="${chartW - 8}" y2="${y}" stroke="#ddd6c6" stroke-width="1.5"/>
    <text x="${padL - 12}" y="${y + 6}" text-anchor="end" font-size="16" fill="#8b909c" font-family="Consolas, monospace">${numFmt(g)}</text>`;
}).join('');

// 结构堆叠条
function stackedBar(segments) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  return `<div class="stack">${segments.map((s) => `<div class="stack-seg" style="width:${(s.value / total) * 100}%;background:${s.color}"></div>`).join('')}</div>
    <div class="legend">${segments.map((s) => `<span class="legend-item"><i style="background:${s.color}"></i>${s.label} <b>${pct((s.value / total) * 100)}%</b></span>`).join('')}</div>`;
}

const bgCard = '#f6f2e9';
const navy = '#16223a';
const ink = '#1b2436';
const muted = '#6a7285';
const gold = '#b99243';
const red = '#c8453a';
const green = '#2f8a68';

const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{width:${CARD_W}px;background:#e6e0d2;font-family:"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;color:${ink};-webkit-font-smoothing:antialiased}
  .card{width:${CARD_W}px;height:${CARD_H}px;position:relative;overflow:hidden;padding:78px 72px;background:${bgCard}}
  .card + .card{margin-top:0}
  .num-tag{position:absolute;right:60px;top:52px;font:600 24px/1 Consolas,monospace;color:rgba(27,36,54,.28);letter-spacing:.1em}
  .eyebrow{font-size:23px;letter-spacing:.22em;color:${gold};font-weight:700}
  h1{font-size:82px;line-height:1.12;font-weight:800;letter-spacing:-.01em;margin-top:26px}
  h1 .gold,.gold{color:${gold}}
  h2{font-size:56px;line-height:1.18;font-weight:800;letter-spacing:-.01em;margin-top:16px}
  h3{font-size:30px;font-weight:800;margin-bottom:16px}
  .sub{font-size:29px;line-height:1.62;color:rgba(255,255,255,.82);margin-top:26px}
  .sub b{color:#fff}
  .note{font-size:20px;line-height:1.6;color:${muted}}
  .dark{background:radial-gradient(circle at 82% 4%, rgba(193,160,90,.28), transparent 42%), linear-gradient(160deg,#141c2e,#1d2942 62%,#16223a);color:#fff}
  .panel{background:#fbf7ee;border:1px solid rgba(22,34,58,.12);border-radius:10px;box-shadow:0 22px 54px rgba(22,34,58,.16);padding:34px 36px}
  .panel-title{font-size:26px;font-weight:800;color:${navy};margin-bottom:6px}
  .panel-sub{font-size:20px;color:${muted};margin-bottom:14px}
  .cover-chart{margin-top:36px}
  .stats3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:26px}
  .stat3{border-left:5px solid ${gold};padding:10px 14px;background:rgba(185,146,67,.07)}
  .stat3 .v{font:700 40px/1.1 Georgia,serif;color:${navy}}
  .stat3 .l{font-size:19px;color:${muted};margin-top:6px}
  .foot{position:absolute;left:72px;right:72px;bottom:56px;font-size:22px;color:rgba(255,255,255,.6);letter-spacing:.02em}
  .kpi{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:40px}
  .kpi-item{background:#fbf7ee;border:1px solid rgba(22,34,58,.12);border-radius:10px;padding:26px 28px}
  .kpi-item .k{font-size:21px;color:${muted};letter-spacing:.06em}
  .kpi-item .v{font:700 58px/1.05 Georgia,serif;margin-top:10px;color:${navy}}
  .kpi-item .v small{font-size:26px;font-family:"PingFang SC","Microsoft YaHei",sans-serif;font-weight:600;margin-left:4px}
  .d-bad{color:${red}} .d-good{color:${green}}
  .kpi-item .d{font-size:21px;margin-top:10px;font-weight:700}
  .block{margin-top:34px}
  .stack{display:flex;height:34px;border-radius:6px;overflow:hidden;background:#e8e2d4}
  .stack-seg{height:100%}
  .legend{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:12px}
  .legend-item{font-size:20px;color:${muted}}
  .legend-item i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:7px;vertical-align:-1px}
  .legend-item b{color:${ink};font-family:Consolas,monospace}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:34px}
  .col-head{font-size:26px;font-weight:800;margin-bottom:18px;display:flex;justify-content:space-between;align-items:baseline}
  .col-head span{font-size:19px;color:${muted};font-weight:500}
  .bar-row{display:flex;align-items:center;gap:12px;margin-bottom:17px;height:34px}
  .bar-rank{width:20px;font:700 18px/1 Consolas,monospace;color:#b9b3a4;text-align:right}
  .bar-name{width:186px;font-size:21px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .bar-track{flex:1;height:16px;border-radius:8px;background:#e8e2d4;overflow:hidden}
  .bar-fill{height:100%;border-radius:8px}
  .bar-val{width:92px;text-align:right;font:700 21px/1 Consolas,monospace}
  .bar-val .pct{display:block;font-size:14px;color:${muted};font-weight:500;margin-top:2px}
  .list-big .bar-row{height:44px;margin-bottom:20px}
  .list-big .bar-name{width:230px;font-size:26px}
  .list-big .bar-track{height:20px}
  .list-big .bar-val{width:104px;font-size:26px}
  .divider{height:1px;background:rgba(22,34,58,.12);margin:30px 0}
  .q-list{counter-reset:q;margin-top:34px}
  .q{display:flex;gap:20px;align-items:flex-start;margin-bottom:28px}
  .q .qn{counter-increment:q;flex:0 0 54px;height:54px;border-radius:50%;background:${navy};color:#fff;font:700 24px/54px Georgia,serif;text-align:center}
  .q .qn::before{content:counter(q)}
  .q .qt{font-size:29px;line-height:1.5;font-weight:700}
  .q .qd{font-size:21px;line-height:1.5;color:${muted};margin-top:6px}
  .url-box{margin-top:30px;background:${navy};color:#fff;border-radius:10px;padding:28px 32px}
  .url-box .u{font:600 27px/1.4 Consolas,monospace;color:#f0e6cf;word-break:break-all}
  .url-box .t{font-size:19px;color:rgba(255,255,255,.6);margin-bottom:8px;letter-spacing:.1em}
  .pill{display:inline-block;padding:6px 14px;border-radius:999px;background:rgba(185,146,67,.16);color:#8a6b24;font-size:20px;font-weight:700;margin-right:8px}
  .callout{margin-top:30px;background:${navy};color:#fff;border-radius:10px;padding:28px 32px;font-size:27px;line-height:1.55;font-weight:700}
  .callout em{font-style:normal;color:#e6c987}
  .dark .num-tag{color:rgba(255,255,255,.38)}
  .teaser{margin-top:34px}
  .teaser .t{display:flex;align-items:baseline;gap:14px;font-size:26px;line-height:1.5;color:rgba(255,255,255,.86);margin-bottom:14px}
  .teaser .t i{flex:0 0 10px;height:10px;border-radius:50%;background:#c1a05a;display:inline-block}
  .teaser .t b{color:#fff}
  .cmp{background:#fbf7ee;border:1px solid rgba(22,34,58,.12);border-radius:10px;padding:8px 26px;margin-top:12px}
  .cmp-row{display:grid;grid-template-columns:1.4fr .8fr 40px .8fr 1fr;align-items:center;gap:8px;padding:18px 0;border-bottom:1px solid rgba(22,34,58,.09);font-size:24px}
  .cmp-row:last-child{border-bottom:0}
  .cmp-row .k{font-weight:700}
  .cmp-row .v{font-family:Consolas,monospace;color:#6a7285;text-align:right}
  .cmp-row .arrow{color:#b9b3a4;text-align:center}
  .cmp-row .v2{font-family:Consolas,monospace;color:#16223a;font-weight:700;text-align:right}
  .cmp-row .e{text-align:right;font-size:21px;font-weight:700}
  .chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
  .chip{border:1px solid rgba(22,34,58,.16);background:#fbf7ee;border-radius:8px;padding:9px 14px;font-size:20px;font-weight:600}
  .chip b{font-family:Consolas,monospace;margin-left:8px}
  .chip.up b{color:#c8453a} .chip.down b{color:#2f8a68}
  .tags{display:flex;flex-wrap:wrap;gap:10px;margin-top:26px}
  .tag{font-size:20px;color:#8a6b24;background:rgba(185,146,67,.14);border-radius:6px;padding:8px 14px;font-weight:700}
</style>
</head>
<body>

<!-- 01 封面 -->
<section class="card dark" id="c1">
  <div class="num-tag">01 / 06</div>
  <div class="eyebrow">广东省考 · ${years[0]}—${latest}</div>
  <h1>${latest} 招录<br><span class="gold">${trendWord}</span></h1>
  <p class="sub">全省计划招录 <b>${numFmt(latestTotal)}</b> 人、<b>${numFmt(positions)}</b> 个职位，<br>较 ${prev} 年${totalDelta < 0 ? '减少' : '增加'} <b>${numFmt(Math.abs(totalDelta))}</b> 人（${signPct(totalPct)}）。</p>
  <div class="panel cover-chart">
    <div class="panel-title">${years[0]}—${latest} 全省招录人数趋势</div>
    <div class="panel-sub">单位：人 · 官方职位表全 sheet 逐职位汇总</div>
    <svg width="${chartW}" height="${chartH}" viewBox="0 0 ${chartW} ${chartH}" style="width:100%;height:auto;display:block">
      ${svgGrid}
      ${svgBars}
    </svg>
    <div class="stats3">
      <div class="stat3"><div class="v">${numFmt(Math.max(...ySeries.map(([, v]) => v)))}</div><div class="l">${ySeries.find(([, v]) => v === Math.max(...ySeries.map(([, v2]) => v2)))[0]} 年峰值</div></div>
      <div class="stat3"><div class="v">${numFmt(prevTotal)}</div><div class="l">${prev} 年</div></div>
      <div class="stat3"><div class="v">${numFmt(latestTotal)}</div><div class="l">${latest} 年（较峰值 ${signPct((latestTotal / Math.max(...ySeries.map(([, v]) => v)) - 1) * 100)}）</div></div>
    </div>
  </div>
  <div class="teaser">
    <div class="t"><i></i>应届岗位占比 <b>${pct(freshRatio)}%</b>，较 ${prev} 年 ${freshRatio >= freshRatioPrev ? '+' : ''}${pct(freshRatio - freshRatioPrev)}pp</div>
    <div class="t"><i></i>研究生门槛 <b>${pct(researchRatio)}%</b>，首次突破两成</div>
    <div class="t"><i></i>22 个城市/地区里，只有 <b>${cityGain.map((r) => r.city).join('、')}</b> 正增长</div>
  </div>
  <div class="foot">往下看：谁在逆势扩招，谁在收缩 →</div>
</section>

<!-- 02 年度变化 -->
<section class="card" id="c2">
  <div class="num-tag">02 / 06</div>
  <div class="eyebrow">${latest} vs ${prev}</div>
  <h2>总量收缩，<br>门槛在抬高</h2>
  <div class="kpi">
    <div class="kpi-item"><div class="k">计划招录人数</div><div class="v">${numFmt(latestTotal)}<small>人</small></div><div class="d d-bad">▼ ${numFmt(Math.abs(totalDelta))}（${pct(totalPct)}%）</div></div>
    <div class="kpi-item"><div class="k">职位数</div><div class="v">${numFmt(positions)}<small>个</small></div><div class="d d-bad">▼ ${numFmt(Math.abs(structPrev.positions - positions))}（${pct((positions - structPrev.positions) / structPrev.positions * 100)}%）</div></div>
    <div class="kpi-item"><div class="k">应届岗位占比</div><div class="v">${pct(freshRatio)}<small>%</small></div><div class="d ${freshRatio >= freshRatioPrev ? 'd-bad' : 'd-good'}">${freshRatio >= freshRatioPrev ? '▲' : '▼'} ${pct(Math.abs(freshRatio - freshRatioPrev))}pp</div></div>
    <div class="kpi-item"><div class="k">研究生门槛占比</div><div class="v">${pct(researchRatio)}<small>%</small></div><div class="d ${researchRatio >= researchRatioPrev ? 'd-bad' : 'd-good'}">${researchRatio >= researchRatioPrev ? '▲' : '▼'} ${pct(Math.abs(researchRatio - researchRatioPrev))}pp</div></div>
  </div>
  <div class="block">
    <h3>区域结构（按招录人数）</h3>
    ${stackedBar([
      { label: '珠三角', value: regions.prd || 0, color: '#2c3a58' },
      { label: '非珠三角', value: regions.non_prd || 0, color: '#8a6b2f' },
      { label: '省直', value: regions.province || 0, color: '#9aa1ad' },
    ])}
  </div>
  <div class="block">
    <h3>学历门槛（按招录人数）</h3>
    ${stackedBar([
      { label: '研究生', value: edu['研究生'] || 0, color: '#2c3a58' },
      { label: '本科以上', value: edu['本科以上'] || 0, color: '#4a5c82' },
      { label: '本科', value: edu['本科'] || 0, color: '#8a6b2f' },
      { label: '大专及以下', value: belowCollege, color: '#9aa1ad' },
    ])}
  </div>
  <div class="block">
    <h3>同口径对比（${prev} → ${latest}）</h3>
    <div class="cmp">
      <div class="cmp-row"><span class="k">应届岗位占比</span><span class="v">${pct(freshRatioPrev)}%</span><span class="arrow">→</span><span class="v2">${pct(freshRatio)}%</span><span class="e ${freshRatio >= freshRatioPrev ? 'd-bad' : 'd-good'}">${freshRatio >= freshRatioPrev ? '▲' : '▼'}${pct(Math.abs(freshRatio - freshRatioPrev))}pp</span></div>
      <div class="cmp-row"><span class="k">研究生门槛占比</span><span class="v">${pct(researchRatioPrev)}%</span><span class="arrow">→</span><span class="v2">${pct(researchRatio)}%</span><span class="e ${researchRatio >= researchRatioPrev ? 'd-bad' : 'd-good'}">${researchRatio >= researchRatioPrev ? '▲' : '▼'}${pct(Math.abs(researchRatio - researchRatioPrev))}pp</span></div>
      <div class="cmp-row"><span class="k">珠三角占比</span><span class="v">${pct(structPrev.regions.prd / structPrev.recruits * 100)}%</span><span class="arrow">→</span><span class="v2">${pct(prdRatio)}%</span><span class="e">${Math.abs(prdRatio - structPrev.regions.prd / structPrev.recruits * 100) < 0.05 ? '持平' : (prdRatio > structPrev.regions.prd / structPrev.recruits * 100 ? '▲' : '▼') + pct(Math.abs(prdRatio - structPrev.regions.prd / structPrev.recruits * 100)) + 'pp'}</span></div>
      <div class="cmp-row"><span class="k">省直占比</span><span class="v">${pct(structPrev.regions.province / structPrev.recruits * 100)}%</span><span class="arrow">→</span><span class="v2">${pct(provinceRatio)}%</span><span class="e d-good">▼${pct(Math.abs(structPrev.regions.province / structPrev.recruits * 100 - provinceRatio))}pp</span></div>
    </div>
  </div>
</section>

<!-- 03 专业变化 -->
<section class="card" id="c3">
  <div class="num-tag">03 / 06</div>
  <div class="eyebrow">专业冷暖 · ${latest}</div>
  <h2>谁在逆势扩招，<br>谁在收缩</h2>
  <div class="cols">
    <div>
      <div class="col-head">增招 Top6 <span>按人数差</span></div>
      ${barRows(majorGain.map((r) => ({ name: r.name, value: r.delta })), { max: Math.max(...majorGain.map((r) => r.delta)), color: red, formatter: (r) => signed(r.value) })}
    </div>
    <div>
      <div class="col-head">减招 Top6 <span>按人数差</span></div>
      ${barRows(majorLoss.map((r) => ({ name: r.name, value: r.delta })), { max: Math.max(...majorLoss.map((r) => -r.delta)), color: green, formatter: (r) => signed(r.value) })}
    </div>
  </div>
  <div class="callout">大盘专业在收缩：<em>法学类 −251、不限专业 −205、工商管理类 −184</em>；<br>逆势扩张的是 <em>${esc(majorGain[0].name)} ${signed(majorGain[0].delta)}、${esc(majorGain[1].name)} ${signed(majorGain[1].delta)}</em> 这类细分方向。</div>
  <div class="block" style="margin-top:26px">
    <h3>${latest} 新增专业条目 <span style="font-weight:500;color:${muted};font-size:20px">（${prev} 年为 0）</span></h3>
    <div class="chips">${majorAdded.map((r) => `<span class="chip up">${esc(r.name)}<b>+${numFmt(r.cur)}</b></span>`).join('')}</div>
    <h3 style="margin-top:26px">${latest} 消失专业条目 <span style="font-weight:500;color:${muted};font-size:20px">（${latest} 年为 0）</span></h3>
    <div class="chips">${majorDropped.length ? majorDropped.map((r) => `<span class="chip down">${esc(r.name)}<b>−${numFmt(r.prev)}</b></span>`).join('') : '<span class="chip">无</span>'}</div>
  </div>
  <p class="note" style="margin-top:24px">专业数值 = 该专业在职位要求中出现的招录人数；同一职位挂多个专业会重复计入，<b>不可相加</b>。</p>
</section>

<!-- 04 城市变化 -->
<section class="card" id="c4">
  <div class="num-tag">04 / 06</div>
  <div class="eyebrow">城市冷暖 · ${latest}</div>
  <h2>只剩 2 个城市<br>还在正增长</h2>
  <div class="cols" style="grid-template-columns:1fr;gap:0">
    <div>
      <div class="col-head">正增长 <span>共 ${cityGain.length} 个</span></div>
      ${barRows(cityGain.map((r) => ({ name: r.city, value: r.delta })), { max: Math.max(1, ...cityGain.map((r) => r.delta)), color: red, formatter: (r) => signed(r.value) })}
      <div class="col-head" style="margin-top:26px">收缩 Top8 <span>按减少人数</span></div>
      ${barRows(cityLoss.map((r) => ({ name: r.city, value: r.delta })), { max: Math.max(1, ...cityLoss.map((r) => -r.delta)), color: green, formatter: (r) => signed(r.value) })}
    </div>
  </div>
  <div class="divider"></div>
  <div class="block">
    <h3>${latest} 招录人数 Top5 城市</h3>
    <div class="chips">${cityTop5.map((r, i) => `<span class="chip">${i + 1}. ${r.city}<b>${numFmt(r.cur)}</b></span>`).join('')}</div>
  </div>
  <p class="note" style="margin-top:24px">全省 22 个城市/地区中，仅 <b>${cityGain.map((r) => r.city).join('、')}</b> 正增长；珠三角仍占 ${pct(prdRatio)}%，<br>但省直、深圳、汕头等岗位池收缩最明显。</p>
  <div class="callout" style="margin-top:26px">选城市：先看岗位池是在扩还是在缩，<br>再看自己的专业在该市到底有没有岗。</div>
</section>

<!-- 05 专业 Top10 -->
<section class="card" id="c5">
  <div class="num-tag">05 / 06</div>
  <div class="eyebrow">${latest} 专业招录 Top10</div>
  <h2>热门专业格局</h2>
  <div class="list-big" style="margin-top:44px">
    ${barRows(majorTop.map((r) => ({ name: r.name, value: r.cur })), { max: majorTop[0].cur, color: '#2c3a58', formatter: (r) => numFmt(r.value) })}
  </div>
  <div class="callout">前 3 名（<em>${esc(majorTop[0].name)} / ${esc(majorTop[1].name)} / ${esc(majorTop[2].name)}</em>）合计 ${numFmt(majorTop[0].cur + majorTop[1].cur + majorTop[2].cur)} 人次，<br>占 Top10 总量的 ${pct((majorTop[0].cur + majorTop[1].cur + majorTop[2].cur) / majorTop.reduce((s, r) => s + r.cur, 0) * 100)}%。</div>
  <div class="block">
    <h3>Top3 近三年走势（${recentYears.join(' → ')}）</h3>
    <div class="chips">${majorTop3Trend.map((r) => `<span class="chip">${esc(r.name)}<b>${r.values.map((v) => numFmt(v)).join(' → ')}</b></span>`).join('')}</div>
  </div>
  <p class="note" style="margin-top:24px">看板共统计 ${majorData.ranking.length} 个专业条目；专业数值不可相加，<br>排名表达的是「岗位要求里出现得多不多」，不是岗位数占比。</p>
</section>

<!-- 06 选岗建议 -->
<section class="card" id="c6">
  <div class="num-tag">06 / 06</div>
  <div class="eyebrow">选岗方法</div>
  <h2>别只看总人数，<br>按这 4 个问题下钻</h2>
  <div class="q-list">
    <div class="q"><div class="qn"></div><div><div class="qt">你的专业，近三年是在扩招还是收缩？</div><div class="qd">看专业年度变化，避免踩在持续收缩的赛道上。</div></div></div>
    <div class="q"><div class="qn"></div><div><div class="qt">这个专业在哪些城市岗位更多？</div><div class="qd">同一个专业，珠三角与非珠三角的岗位池差异很大。</div></div></div>
    <div class="q"><div class="qn"></div><div><div class="qt">应届占比高不高？</div><div class="qd">应届友好度直接决定社会人员能报的岗位比例。</div></div></div>
    <div class="q"><div class="qn"></div><div><div class="qt">岗位是不是经常「多专业共招」？</div><div class="qd">共招越多，竞争面越宽，需要看纯洁度和竞争指数。</div></div></div>
  </div>
  <div class="url-box">
    <div class="t">交互式看板 · 2020-${latest} 全量数据</div>
    <div class="u">aluckymaan.github.io/gd-exam-analysis/</div>
  </div>
  <div class="callout" style="margin-top:26px">先看结构，再定城市，<br>最后才比岗位。</div>
  <div class="tags">${['#广东省考', '#广东公务员', '#公务员选岗', '#应届生考公', '#省考职位表'].map((t) => `<span class="tag">${t}</span>`).join('')}</div>
  <p class="note" style="margin-top:22px">数据来源：广东省考试录用公务员（省考）官方职位表附件，2020-${latest} 共 ${years.length} 年；<br>不含选调生、急需紧缺专业等另行发布的招录计划。</p>
</section>

</body>
</html>`;

const tmpHtml = path.join(tmpdir(), `gd-xhs-cards-${process.pid}.html`);
writeFileSync(tmpHtml, html, 'utf8');
mkdirSync(outDir, { recursive: true });

// ── 启动 Edge（CDP）──
const profile = path.join(tmpdir(), `gd-xhs-profile-${process.pid}`);
const proc = spawn(browser, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
  '--hide-scrollbars', '--force-device-scale-factor=1',
  `--user-data-dir=${profile}`, `--remote-debugging-port=${PORT}`, 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });
let errTail = '';
proc.stderr?.on('data', (d) => { errTail = (errTail + d.toString()).slice(-1200); });

let cleaned = false;
const cleanup = () => {
  if (cleaned) return; cleaned = true;
  try {
    if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(proc.pid), '/T', '/F'], { stdio: 'ignore' });
    else process.kill(-proc.pid, 'SIGKILL');
  } catch { /* ignore */ }
};
process.on('exit', cleanup);

let ver = null;
for (let i = 0; i < 80 && !ver; i++) {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) ver = await r.json(); } catch { /* retry */ }
  if (!ver) await sleep(250);
}
if (!ver) {
  console.log('SKIP: CDP 端口未就绪（浏览器无法启动）\n' + (errTail || ''));
  cleanup(); process.exit(0);
}
const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let seq = 0; const pending = new Map();
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: CARD_W, height: CARD_H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: pathToFileURL(tmpHtml).href });
await sleep(900);
await send('Runtime.evaluate', { expression: 'document.fonts && document.fonts.ready', awaitPromise: true });
await sleep(300);

const files = ['01_cover', '02_year_change', '03_major_delta', '04_city_delta', '05_major_top10', '06_guide'];
for (let i = 0; i < files.length; i++) {
  const r = await send('Page.captureScreenshot', {
    format: 'png',
    clip: { x: 0, y: i * CARD_H, width: CARD_W, height: CARD_H, scale: 1 },
    captureBeyondViewport: true,
  });
  if (!r.result?.data) throw new Error('截图失败: ' + files[i]);
  const out = path.join(outDir, files[i] + '.png');
  writeFileSync(out, Buffer.from(r.result.data, 'base64'));
  console.log('saved', path.relative(root, out));
}

// 收尾：先让浏览器自己关，再杀进程树；临时文件删除失败不影响结果
try { ws.send(JSON.stringify({ id: 99999, method: 'Browser.close' })); await sleep(600); } catch { /* ignore */ }
cleanup();
try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }
try { rmSync(tmpHtml, { force: true }); } catch { /* ignore */ }
console.log(`\n已生成 ${files.length} 张 1080×1440 发布图：${outDir}`);
