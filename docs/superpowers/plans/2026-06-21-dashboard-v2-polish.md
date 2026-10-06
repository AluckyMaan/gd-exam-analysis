# Dashboard V2 Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `广东省考综合数据分析看板.html` from a chart collection into a decision-oriented, premium data product.

**Architecture:** Keep the current single-file HTML architecture and existing embedded data objects. Add a thin presentation layer: design tokens, reusable dashboard section headers, richer overview narratives, and enhanced table renderers. Do not change source data extraction or metric definitions.

**Tech Stack:** Plain HTML/CSS/JavaScript, ECharts 5.5.0, embedded JSON data, static local HTML.

---

## Files

- Modify: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html`
- Verify: browser preview through `index.html` or direct HTML open
- Optional backup: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html.bak`

## Implementation Notes

- Preserve all existing data objects: `RANKING`, `CITY_YEARLY`, `CITY_RANKING`, `CITY_FRESH`, `CITY_EDUCATION`, `CITY_MAJOR_MATRIX`.
- Preserve current tab ids: `m-tab0` to `m-tab5`, `c-tab0` to `c-tab6`.
- Keep all rendering functions globally available because inline `onclick` handlers call them.
- After every JavaScript edit, run the syntax check command in Task 5.
- Avoid adding new external dependencies.

---

### Task 1: Executive Dashboard Narrative

**Files:**
- Modify: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html`

**Goal:** Make `洞察总览` and `城市洞察` read like an executive dashboard: one headline conclusion, four decision cards, and clear next-step actions.

- [ ] **Step 1: Add CSS for the executive summary strip**

Add this inside `<style>`, near the existing overview component CSS:

```css
.exec-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  padding: 18px 20px;
  border: 1px solid rgba(30,58,95,0.12);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(15,23,42,0.96), rgba(30,58,95,0.86)),
    radial-gradient(circle at 90% 10%, rgba(217,119,6,0.26), transparent 38%);
  box-shadow: 0 22px 56px rgba(15,23,42,0.22), inset 0 1px 0 rgba(255,255,255,0.12);
}

.exec-summary h3 {
  margin: 0 0 6px;
  color: #fff;
  font-family: var(--font-serif);
  font-size: clamp(1.05rem, 2vw, 1.45rem);
  line-height: 1.35;
}

.exec-summary p {
  margin: 0;
  color: rgba(226,232,240,0.72);
  font-size: 13px;
  line-height: 1.7;
}

.exec-summary .summary-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 86px;
  padding: 8px 12px;
  border-radius: 999px;
  color: #f8fafc;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.16);
  font-family: var(--font-mono);
  font-size: 12px;
}

.path-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.path-card {
  padding: 13px 14px;
  border-radius: 15px;
  border: 1px solid rgba(30,58,95,0.1);
  background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.9));
  color: #334155;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.path-card:hover {
  transform: translateY(-2px);
  border-color: rgba(59,130,246,0.32);
  box-shadow: 0 16px 34px rgba(15,23,42,0.12);
}

.path-card b {
  display: block;
  color: #0f172a;
  font-size: 13px;
  margin-bottom: 4px;
}

.path-card span {
  display: block;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

@media (max-width: 980px) {
  .exec-summary { grid-template-columns: 1fr; }
  .path-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .path-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 2: Add summary containers in `m-tab0`**

Inside `<div class="overview-shell">` for `m-tab0`, place this after `.overview-head` and before `#majorInsightGrid`:

```html
<div class="exec-summary" id="majorExecSummary"></div>
<div class="path-grid" id="majorPathGrid"></div>
```

- [ ] **Step 3: Add summary containers in `c-tab0`**

Inside `<div class="overview-shell">` for `c-tab0`, place this after `.overview-head` and before `#cityInsightGrid`:

```html
<div class="exec-summary" id="cityExecSummary"></div>
<div class="path-grid" id="cityPathGrid"></div>
```

- [ ] **Step 4: Extend `renderMajorOverview()`**

Inside `renderMajorOverview()`, after the `grid.innerHTML = [...]` block and before card click binding, add:

```js
  var majorTotal = RANKING.reduce(function(s,m) { return s + (m.total_recruits || 0); }, 0);
  var top3Total = scale.reduce(function(s,m) { return s + (m.total_recruits || 0); }, 0);
  var top3Share = majorTotal ? Math.round(top3Total / majorTotal * 1000) / 10 : 0;
  var topGrowth = growth[0];
  document.getElementById('majorExecSummary').innerHTML =
    '<div><h3>专业机会呈现“头部集中 + 理工复合上行”的结构</h3>' +
    '<p>Top3 专业合计占全部专业招录口径约 ' + top3Share + '%；' +
    escHtml(topGrowth.major) + ' 等增长赛道提示近年岗位需求正在重分配。</p></div>' +
    '<div class="summary-badge">' + formatNumber(majorTotal) + ' 人</div>';

  document.getElementById('majorPathGrid').innerHTML = [
    '<button class="path-card" onclick="jumpMajorRank(\\'recruits\\')"><b>想稳妥选岗</b><span>先看规模重心和长期高频专业。</span></button>',
    '<button class="path-card" onclick="jumpMajorDetail(' + RANKING.indexOf(fresh[0]) + ')"><b>想应届友好</b><span>优先查看应届占比和学历结构。</span></button>',
    '<button class="path-card" onclick="jumpMajorRank(\\'growth\\')"><b>想找上升赛道</b><span>按增长率排序，识别扩招专业。</span></button>',
    '<button class="path-card" onclick="jumpMajorDetail(' + RANKING.indexOf(compound[0]) + ')"><b>想避开拥挤</b><span>看复合共招，寻找可替代入口。</span></button>'
  ].join('');
```

- [ ] **Step 5: Extend `renderCityOverview()`**

Inside `renderCityOverview()`, after the `grid.innerHTML = [...]` block and before `var actions = { ... }`, add:

```js
  var cityTotal = cities.reduce(function(s,c) { return s + (CITY_YEARLY[c].total_recruits || 0); }, 0);
  var scaleTop3 = scale.reduce(function(s,c) { return s + (CITY_YEARLY[c].total_recruits || 0); }, 0);
  var scaleShare = cityTotal ? Math.round(scaleTop3 / cityTotal * 1000) / 10 : 0;
  document.getElementById('cityExecSummary').innerHTML =
    '<div><h3>城市机会呈现“规模中心明确 + 非珠三角承接强”的格局</h3>' +
    '<p>规模前三城市合计约占全省招录 ' + scaleShare + '%；同时非珠三角城市仍提供大量岗位池，适合和增长弹性一起判断。</p></div>' +
    '<div class="summary-badge">' + formatNumber(cityTotal) + ' 人</div>';

  document.getElementById('cityPathGrid').innerHTML = [
    '<button class="path-card" onclick="jumpCityRank(\\'recruits\\')"><b>看岗位池大小</b><span>按总招录人数判断城市规模。</span></button>',
    '<button class="path-card" onclick="jumpCityRank(\\'growth\\')"><b>看增长弹性</b><span>找近年扩招更明显的城市。</span></button>',
    '<button class="path-card" onclick="jumpCityRank(\\'fresh\\')"><b>看应届友好</b><span>按应届占比筛选报考环境。</span></button>',
    '<button class="path-card" onclick="activateSubTab(\\'c-tab5\\')"><b>看专业落点</b><span>按专业反查城市分布。</span></button>'
  ].join('');
```

- [ ] **Step 6: Verify**

Run:

```powershell
node -e "const fs=require('fs');const vm=require('vm');const html=fs.readFileSync('广东省考综合数据分析看板.html','utf8');const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);scripts.forEach((s,i)=>{try{new vm.Script(s);console.log('script',i,'ok')}catch(e){console.error('script',i,'ERR',e.message); process.exitCode=1}});"
```

Expected:

```text
script 0 ok
script 1 ok
```

---

### Task 2: Chart Section Headers

**Files:**
- Modify: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html`

**Goal:** Every major chart should explain what it shows, what metric is active, and where the user can drill down.

- [ ] **Step 1: Add reusable chart header CSS**

Add near the chart CSS:

```css
.viz-panel {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.viz-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  padding: 4px 2px 0;
}

.viz-title {
  color: #0f172a;
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 700;
  line-height: 1.25;
}

.viz-subtitle {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.viz-badge {
  flex: 0 0 auto;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(59,130,246,0.18);
  color: #1e3a5f;
  background: rgba(59,130,246,0.08);
  font-size: 11px;
  font-weight: 700;
}
```

- [ ] **Step 2: Add header helper function**

Place this before `switchRankMode()`:

```js
function renderVizHead(title, subtitle, badge) {
  return '<div class="viz-head"><div><div class="viz-title">' + title + '</div>' +
    '<div class="viz-subtitle">' + subtitle + '</div></div>' +
    '<div class="viz-badge">' + badge + '</div></div>';
}
```

- [ ] **Step 3: Wrap professional rank chart**

In `m-tab1`, replace:

```html
<div class="chart-box" id="rankChart"></div>
```

with:

```html
<div class="viz-panel">
  <div id="rankChartHead"></div>
  <div class="chart-box" id="rankChart"></div>
</div>
```

In `switchRankMode()`, after `var mode = document.getElementById('rankMode').value;`, add:

```js
  var rankHeadMap = {
    recruits: ['专业招录 Top30', '按 2020-2026 年累计招录人数排序，观察岗位池规模。', '招录人数'],
    positions: ['专业职位 Top30', '按职位记录数排序，观察岗位出现频率。', '职位数'],
    purity: ['专业纯洁度 Top30', '纯洁度越高，越常以单一专业独占岗位。', '纯洁度'],
    growth: ['专业增长 Top30', '按近年增长率排序，观察扩招赛道。', '增长率']
  };
  document.getElementById('rankChartHead').innerHTML = renderVizHead(rankHeadMap[mode][0], rankHeadMap[mode][1], rankHeadMap[mode][2]);
```

- [ ] **Step 4: Wrap city rank chart**

In `c-tab2`, replace:

```html
<div class="chart-box" id="cityRankChart"></div>
```

with:

```html
<div class="viz-panel">
  <div id="cityRankChartHead"></div>
  <div class="chart-box" id="cityRankChart"></div>
</div>
```

In `switchCityRankMode()`, after `var mode = document.getElementById('cityRankMode').value;`, add:

```js
  var cityHeadMap = {
    recruits: ['城市招录规模排名', '按累计招录人数排序，识别岗位池最大的城市。', '招录人数'],
    positions: ['城市职位频率排名', '按职位记录数排序，识别岗位出现频率。', '职位数'],
    growth: ['城市增长弹性排名', '按增长率排序，识别近年扩招更明显的城市。', '增长率'],
    fresh: ['城市应届友好排名', '按应届占比排序，辅助判断应届报考环境。', '应届占比']
  };
  document.getElementById('cityRankChartHead').innerHTML = renderVizHead(cityHeadMap[mode][0], cityHeadMap[mode][1], cityHeadMap[mode][2]);
```

- [ ] **Step 5: Add static headers for map and trend panels**

For `#mapChart`, wrap it with:

```html
<div class="viz-panel">
  <div class="viz-head">
    <div>
      <div class="viz-title">广东城市空间分布</div>
      <div class="viz-subtitle">按城市口径展示招录规模、岗位密度或增长率；点击城市查看详情。</div>
    </div>
    <div class="viz-badge">地图视图</div>
  </div>
  <div class="chart-box-map" id="mapChart"></div>
</div>
```

For `#cityTrendChart`, wrap it with:

```html
<div class="viz-panel">
  <div class="viz-head">
    <div>
      <div class="viz-title">城市年度趋势</div>
      <div class="viz-subtitle">最多同时对比 8 个城市，观察 2020-2026 年招录曲线。</div>
    </div>
    <div class="viz-badge">年度走势</div>
  </div>
  <div class="chart-box" id="cityTrendChart"></div>
</div>
```

- [ ] **Step 6: Verify**

Open `index.html` locally. Check:

- `Top30排名` tab has a chart title and metric badge.
- Changing `显示` select updates the badge.
- `城市排名` tab has a chart title and metric badge.
- Map and city trend panels have clear titles.

---

### Task 3: Ranking Tables as Data Product Tables

**Files:**
- Modify: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html`

**Goal:** Upgrade professional and city tables from plain grids into readable ranked data products.

- [ ] **Step 1: Add table polish CSS**

Add near table CSS:

```css
.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.data-table th {
  font-size: 12px;
  letter-spacing: 0.02em;
}

.rank-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 24px;
  border-radius: 999px;
  color: #1e3a5f;
  background: rgba(59,130,246,0.08);
  font-family: var(--font-mono);
  font-weight: 700;
}

.rank-pill.top {
  color: #7c4a03;
  background: linear-gradient(180deg, #fff7db, #f8df91);
}

.entity-cell {
  text-align: left;
  white-space: normal;
}

.entity-main {
  color: #0f172a;
  font-weight: 700;
}

.entity-sub {
  margin-top: 2px;
  color: #64748b;
  font-size: 11px;
}

.trend-up,
.trend-down {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
}

.trend-up { color: #b45309; }
.trend-down { color: #0f766e; }

.mini-bar {
  position: relative;
  min-width: 86px;
  height: 8px;
  border-radius: 999px;
  background: rgba(30,58,95,0.08);
  overflow: hidden;
}

.mini-bar span {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--w);
  border-radius: inherit;
  background: linear-gradient(90deg, #8abcf5, #3b82f6);
}

.metric-stack {
  display: inline-grid;
  justify-items: end;
  gap: 3px;
}

.metric-stack small {
  color: #64748b;
  font-size: 11px;
}
```

- [ ] **Step 2: Add helper functions**

Place before `switchRankMode()`:

```js
function rankPill(index) {
  return '<span class="rank-pill ' + (index < 3 ? 'top' : '') + '">' + (index + 1) + '</span>';
}

function trendText(value) {
  var rounded = Math.round((value || 0) * 10) / 10;
  var cls = rounded >= 0 ? 'trend-up' : 'trend-down';
  var arrow = rounded >= 0 ? '↑' : '↓';
  return '<span class="' + cls + '">' + arrow + ' ' + Math.abs(rounded) + '%</span>';
}

function miniBar(value) {
  var v = Math.max(0, Math.min(100, Math.round((value || 0) * 10) / 10));
  return '<div class="metric-stack"><span>' + v + '%</span><div class="mini-bar" style="--w:' + v + '%"><span></span></div></div>';
}
```

- [ ] **Step 3: Upgrade professional rank table HTML**

In `switchRankMode()`, replace the table header string with:

```js
  var th = '<table class="data-table"><thead><tr><th>#</th><th>专业</th><th>招录</th><th>职位</th><th>纯洁度</th><th>竞争</th><th>增长</th><th>应届</th><th>学历</th></tr></thead><tbody>';
```

Replace each row construction with:

```js
    var edu = m.education_distribution ? Object.entries(m.education_distribution).sort(function(a,b){return b[1]-a[1]}).map(function(e){return e[0]}).slice(0,2).join('、') : '-';
    var entitySub = (m.code ? m.code : (m.type === 'township' ? '旧版乡镇代码' : '标准专业')) + ' · 覆盖 ' + (m.city_coverage || '-') + ' 城';
    th += '<tr><td>' + rankPill(i) + '</td>' +
      '<td class="entity-cell"><div class="entity-main">' + names[29-i] + '</div><div class="entity-sub">' + entitySub + '</div></td>' +
      '<td><strong>' + formatNumber(m.total_recruits) + '</strong></td>' +
      '<td>' + formatNumber(m.total_positions) + '</td>' +
      '<td>' + miniBar(m.purity) + '</td>' +
      '<td>' + (m.competition_index || '-') + '</td>' +
      '<td>' + trendText(m.growth_rate || 0) + '</td>' +
      '<td>' + miniBar(m.fresh_ratio) + '</td>' +
      '<td>' + edu + '</td></tr>';
```

- [ ] **Step 4: Upgrade city rank table HTML**

In `switchCityRankMode()`, replace the table header string with:

```js
  var th = '<table class="data-table"><thead><tr><th>#</th><th>城市</th><th>分区</th><th>招录</th><th>职位</th><th>增长</th><th>应届</th><th>占比</th></tr></thead><tbody>';
```

Replace each row construction with:

```js
    var groupText = g === 'prd' ? '珠三角' : (g === 'province' ? '省直' : '非珠三角');
    th += '<tr><td>' + rankPill(i) + '</td>' +
      '<td class="entity-cell"><div class="entity-main">' + c + '</div><div class="entity-sub">' + groupText + ' · ' + formatNumber(info.total_recruits) + ' 人</div></td>' +
      '<td>' + groupText + '</td>' +
      '<td><strong>' + formatNumber(info.total_recruits) + '</strong></td>' +
      '<td>' + formatNumber(info.total_positions) + '</td>' +
      '<td>' + trendText(calcCityGrowth(c)) + '</td>' +
      '<td>' + miniBar(calcCityFreshRatio(c)) + '</td>' +
      '<td>' + info.pct_of_total + '%</td></tr>';
```

- [ ] **Step 5: Verify**

Check:

- Professional table top 3 ranks use gold pills.
- Growth values show arrows.
- Fresh ratio and purity show mini bars.
- City table shows readable city group and mini bars.
- Search functions still work for professional and city tables.

---

### Task 4: Visual System Consolidation

**Files:**
- Modify: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html`

**Goal:** Consolidate colors, shadows, borders, and spacing so the full dashboard feels intentional.

- [ ] **Step 1: Expand design tokens in `:root`**

Add these variables inside `:root`:

```css
  --ink-950: #0a0e17;
  --ink-900: #0f172a;
  --ink-800: #16233a;
  --ink-700: #1E3A5F;
  --blue-500: #3b82f6;
  --blue-100: #dbeafe;
  --gold-500: #D97706;
  --gold-100: #fef3c7;
  --paper-50: #f8fafc;
  --paper-100: #eef5ff;
  --line-soft: rgba(30,58,95,0.12);
  --line-strong: rgba(59,130,246,0.28);
  --shadow-card: 0 18px 46px rgba(15,23,42,0.11);
  --shadow-card-hover: 0 24px 62px rgba(15,23,42,0.16);
```

- [ ] **Step 2: Normalize core card surfaces**

Update these existing selectors to use the tokens:

```css
.sub-tab-content,
.matrix-card,
.narrative-card,
.chart-box,
.chart-box-sm,
.chart-box-map,
.network-wrap,
.table-wrap {
  border-color: var(--line-soft);
  box-shadow: var(--shadow-card), inset 0 1px 0 rgba(255,255,255,0.88);
}

.chart-box:hover,
.chart-box-sm:hover,
.chart-box-map:hover,
.network-wrap:hover,
.table-wrap:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-card-hover), inset 0 1px 0 rgba(255,255,255,0.9);
}
```

- [ ] **Step 3: Reduce visual noise in tags and chips**

Update `.tag`, `.legend-tag`, `.matrix-chip`, `.tier-chip`:

```css
.tag,
.legend-tag,
.matrix-chip,
.tier-chip {
  border-color: rgba(30,58,95,0.1);
  background: rgba(59,130,246,0.07);
  color: #1e3a5f;
}
```

Keep `.prd-tag`, `.non-prd-tag`, `.province-tag` as semantic exceptions.

- [ ] **Step 4: Add consistent section spacing**

Add:

```css
.overview-shell,
.sub-tab-content,
.viz-panel {
  scroll-margin-top: 90px;
}

.two-col > div,
#comparePanel,
#compareContent {
  min-width: 0;
}
```

- [ ] **Step 5: Verify visually**

Check:

- No section looks like a nested card inside another heavy card.
- The dashboard uses mostly navy, blue, white, and small gold accents.
- Tags are quieter than primary insight cards.
- Hover states are visible but not flashy.

---

### Task 5: Regression and Review Checklist

**Files:**
- Verify: `C:\Users\YANG\Desktop\广东20-26年广东省考职位表\广东省考综合数据分析看板.html`

- [ ] **Step 1: JavaScript syntax check**

Run:

```powershell
node -e "const fs=require('fs');const vm=require('vm');const html=fs.readFileSync('广东省考综合数据分析看板.html','utf8');const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);scripts.forEach((s,i)=>{try{new vm.Script(s);console.log('script',i,'ok')}catch(e){console.error('script',i,'ERR',e.message); process.exitCode=1}});"
```

Expected:

```text
script 0 ok
script 1 ok
```

- [ ] **Step 2: Simulated overview render check**

Run:

```powershell
$code = @'
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync('广东省考综合数据分析看板.html','utf8');
const script = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
const elements = new Map();
function makeEl(id='') {
  const el = { id, style:{}, children:[], options:[], selectedOptions:[], value:'', textContent:'', _innerHTML:'', appendChild(child){ this.children.push(child); if (child && 'value' in child) this.options.push(child); return child; }, remove(){}, addEventListener(){}, setAttribute(){}, getBoundingClientRect(){ return { width:800, height:400, top:0, left:0 }; }, querySelectorAll(){ return []; }, querySelector(){ return null; }, classList:{ add(){}, remove(){} } };
  Object.defineProperty(el, 'innerHTML', { get(){ return this._innerHTML; }, set(v){ this._innerHTML = String(v); } });
  return el;
}
const document = { body: makeEl('body'), getElementById(id){ if (id === 'wave-svg') return null; if (!elements.has(id)) elements.set(id, makeEl(id)); return elements.get(id); }, querySelector(){ return makeEl('query'); }, querySelectorAll(){ return []; }, createElement(tag){ return makeEl(tag); }, createElementNS(ns, tag){ return makeEl(tag); }, addEventListener(){} };
const context = { console, document, window:{ addEventListener(){}, innerWidth:1280, innerHeight:720 }, setTimeout(fn){ if (typeof fn === 'function') fn(); return 0; }, requestAnimationFrame(){ return 0; }, echarts:{ init(){ return { setOption(){}, resize(){}, clear(){}, off(){}, on(){} }; }, getInstanceByDom(){ return null; }, registerMap(){} }, getComputedStyle(){ return { display:'block' }; }, event:null };
context.window = Object.assign(context.window, context);
vm.createContext(context);
vm.runInContext(script, context, { timeout: 10000 });
const major = elements.get('majorInsightGrid')?._innerHTML || '';
const city = elements.get('cityTierList')?._innerHTML || '';
console.log(JSON.stringify({
  majorInsight: major.includes('规模重心'),
  cityNonPrd: city.includes('非珠三角腹地') && city.includes('湛江'),
  hasExecutiveSummary: (elements.get('majorExecSummary')?._innerHTML || '').includes('专业机会')
}));
'@
node -e $code
```

Expected:

```text
{"majorInsight":true,"cityNonPrd":true,"hasExecutiveSummary":true}
```

- [ ] **Step 3: Manual browser review**

Open `index.html` or `广东省考综合数据分析看板.html` and check:

- First viewport: hero, sticky nav, and dashboard content align with no overlap.
- `洞察总览`: executive summary, path cards, insight cards, strategy matrix all render.
- `城市洞察`: non-Pearl River Delta group shows cities and group summary.
- `Top30排名`: switching mode updates chart and table.
- `城市排名`: switching mode updates chart and table.
- `地图总览`: map still renders and city click opens detail modal.
- `综合对比`: checkbox interactions still update charts.

- [ ] **Step 4: Diff review before asking Codex**

Run:

```powershell
git diff --check -- "广东省考综合数据分析看板.html"
git diff --stat -- "广东省考综合数据分析看板.html"
```

Expected:

```text
git diff --check has no errors
Only 广东省考综合数据分析看板.html changed for this work
```

---

## Self-Review

- Spec coverage: all four approved directions are covered by Tasks 1-4.
- Placeholder scan: no `TBD`, `TODO`, or vague implementation-only steps remain.
- Type consistency: all referenced functions are existing globals or defined in this plan: `renderVizHead`, `rankPill`, `trendText`, `miniBar`.
- Risk note: this plan keeps the single-file structure because the current dashboard is generated/static and already works that way.

