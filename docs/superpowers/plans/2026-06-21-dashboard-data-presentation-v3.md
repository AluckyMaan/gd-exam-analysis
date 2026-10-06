# Dashboard Premium Visual Coordination Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the dashboard feel like one coherent premium data product by harmonizing selection controls, chart surfaces, comparison cards, spacing, typography, and color rhythm.

**Architecture:** Keep the current page structure and data logic. Focus this iteration on visual system, component consistency, and premium interaction polish. Do not introduce new data modules unless they directly improve visual hierarchy.

**Tech Stack:** Static HTML, CSS custom properties, vanilla JavaScript, ECharts.

---

## Design Diagnosis

当前页面的问题不是“功能不够”，而是视觉语言混杂：

- 顶部 tab 已经有高级玻璃质感。
- 右侧矩阵已经接近高级数据卡片。
- 左侧 ECharts 仍像默认统计图。
- 上方勾选框仍像原生表单，和下面两个高级卡片完全不搭。
- 页面缺少统一的“边界、阴影、圆角、留白、标题系统”。

下一版不要大幅改数据逻辑，重点是把所有内容区统一成同一套审美：**冷白玻璃、深蓝墨色、轻边框、低饱和强调色、克制阴影、组件化标签**。

## Visual North Star

参考方向：Linear / Vercel Analytics / Stripe Dashboard / 21st.dev Cards。整体关键词：

- Premium, not flashy
- Soft glass, not heavy card
- Data editorial, not admin table
- Quiet contrast, not colorful chart wall
- Selection chips, not raw checkboxes
- Insight panels, not isolated charts

## Task 1: Establish A Unified Premium Surface System

**Files:**
- Modify: `广东省考综合数据分析看板.html` CSS style block.

- [ ] **Step 1: Define one shared surface language**

Add or normalize these tokens. The important part is not the exact name, but that all cards, selectors, charts, and panels reuse the same values.

```css
:root {
  --premium-surface: rgba(255,255,255,0.82);
  --premium-surface-strong: rgba(255,255,255,0.94);
  --premium-line: rgba(148,163,184,0.22);
  --premium-line-strong: rgba(100,116,139,0.28);
  --premium-shadow: 0 18px 45px rgba(15,23,42,0.08);
  --premium-shadow-soft: 0 8px 24px rgba(15,23,42,0.055);
  --premium-radius: 16px;
  --premium-radius-sm: 12px;
  --premium-blur: blur(18px);
}
```

- [ ] **Step 2: Create one base class for all content blocks**

```css
.premium-panel {
  border: 1px solid var(--premium-line);
  border-radius: var(--premium-radius);
  background: linear-gradient(145deg, var(--premium-surface-strong), rgba(248,250,252,0.86));
  box-shadow: var(--premium-shadow);
  backdrop-filter: var(--premium-blur);
  -webkit-backdrop-filter: var(--premium-blur);
  overflow: hidden;
}
```

**Design rule:** Any major content area should feel like this same material. If a module still has plain white background, old grey border, or native control styling, it will look unfinished.

## Task 2: Redesign The Compare Selector As A Premium Filter Bar

**Files:**
- Modify: CSS for `.compare-grid`, `.compare-item`, `.compare-item input`, `.compare-item span`.
- Modify: HTML around `#compareGrid`.

### Target Look

The selector should look like a refined tag picker, not a form. Think “facet filters in a premium SaaS dashboard”.

- Container: translucent white, subtle border, same radius as right matrix.
- Items: pill chips.
- Selected: blue-tinted chip with small dot or left glow.
- Hover: slight lift, not dramatic.
- Density: compact but breathable.
- No visible native checkbox.

- [ ] **Step 1: Replace checkbox visuals with chips**

```css
.compare-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 172px;
  overflow-y: auto;
  padding: 14px;
  border: 1px solid var(--premium-line);
  border-radius: var(--premium-radius);
  background: rgba(255,255,255,0.72);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.86);
}

.compare-item {
  position: relative;
}

.compare-item input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.compare-item span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 7px 12px;
  border: 1px solid rgba(148,163,184,0.28);
  border-radius: 999px;
  background: rgba(255,255,255,0.76);
  color: var(--ink-700);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
  cursor: pointer;
  transition: transform .16s ease, border-color .16s ease, background .16s ease, box-shadow .16s ease;
}

.compare-item span:hover {
  transform: translateY(-1px);
  border-color: rgba(59,130,246,0.38);
  box-shadow: var(--premium-shadow-soft);
}

.compare-item input:checked + span {
  border-color: rgba(59,130,246,0.5);
  background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(255,255,255,0.92));
  color: var(--blue-900);
  box-shadow: 0 8px 20px rgba(37,99,235,0.10);
}

.compare-item input:checked + span::before {
  content: "";
  width: 7px;
  height: 7px;
  margin-right: 7px;
  border-radius: 999px;
  background: var(--accent-sky);
  box-shadow: 0 0 0 4px rgba(59,130,246,0.12);
}
```

- [ ] **Step 2: Add a small selector header**

Above `#compareGrid`, add a header so the selector does not float like a random form block.

```html
<div class="compare-selector-head">
  <div>
    <div class="eyebrow">SELECT MAJORS</div>
    <div class="selector-title">选择对比专业</div>
  </div>
  <div class="selector-meta" id="compareSelectedCount">已选 3</div>
</div>
```

CSS:

```css
.compare-selector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.eyebrow {
  color: var(--accent-sky);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .13em;
}

.selector-title {
  margin-top: 2px;
  color: var(--blue-900);
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 800;
}

.selector-meta {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(30,58,95,0.08);
  color: var(--blue-800);
  font-size: 12px;
  font-weight: 700;
}
```

**Acceptance:** 勾选区和右侧矩阵看起来像同一个设计系统，不再像浏览器默认表单。

## Task 3: Make The ECharts Line Chart Feel Custom, Not Default

**Files:**
- Modify: CSS around `.chart-box`, `.compare-main`.
- Modify: `compareChart.setOption()`.

### Target Look

左侧图表现在最大的问题是“默认 ECharts 味太重”。要做三件事：

- 图表外层变成和右侧一致的 premium panel。
- 图表内网格线更淡，坐标轴更轻。
- 折线颜色和右侧卡片颜色保持一致。

- [ ] **Step 1: Wrap chart with visual header**

```html
<div class="premium-panel compare-chart-panel">
  <div class="chart-headline">
    <div>
      <div class="eyebrow">TREND</div>
      <div class="chart-title">年度招录趋势</div>
    </div>
    <div class="chart-hint">2020-2026</div>
  </div>
  <div class="chart-box compare-main" id="compareChart"></div>
</div>
```

CSS:

```css
.chart-headline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px 0;
}

.chart-title {
  margin-top: 2px;
  color: var(--blue-900);
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 800;
}

.chart-hint {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15,23,42,0.05);
  color: var(--ink-500);
  font-family: var(--font-mono);
  font-size: 12px;
}
```

- [ ] **Step 2: Soften ECharts axes and grid**

In `compareChart.setOption()`, use this visual direction:

```javascript
color: ['#1e3a5f', '#3b82f6', '#10b981', '#d97706', '#8b5cf6', '#ef4444'],
grid: { left: 54, right: 24, top: 36, bottom: 46 },
xAxis: {
  type: 'category',
  data: YEARS,
  axisLine: { lineStyle: { color: 'rgba(148,163,184,0.45)' } },
  axisTick: { lineStyle: { color: 'rgba(148,163,184,0.35)' } },
  axisLabel: { color: '#64748b', fontSize: 12 }
},
yAxis: {
  type: 'value',
  name: '',
  splitLine: { lineStyle: { color: 'rgba(148,163,184,0.22)' } },
  axisLabel: { color: '#64748b', fontSize: 12 }
},
legend: {
  bottom: 4,
  type: 'scroll',
  icon: 'circle',
  itemWidth: 8,
  itemHeight: 8,
  textStyle: { color: '#475569', fontSize: 12 }
}
```

- [ ] **Step 3: Polish tooltip**

Tooltip 应该像右侧卡片，而不是默认白框。

```javascript
tooltip: {
  trigger: 'axis',
  backgroundColor: 'rgba(255,255,255,0.96)',
  borderColor: 'rgba(148,163,184,0.24)',
  borderWidth: 1,
  padding: [10, 12],
  textStyle: { color: '#1e293b', fontSize: 12 },
  extraCssText: 'box-shadow:0 14px 30px rgba(15,23,42,.12);border-radius:12px;'
}
```

**Acceptance:** 左侧图表即使还是折线图，也不再像默认图库截图，而像定制 dashboard 组件。

## Task 4: Align Right Matrix With Left Chart

**Files:**
- Modify: `.compare-score-panel`, `.score-panel-head`, `.score-major-card`, `.score-metric-block`.

### Target Look

右侧已经不错，但要和左侧更统一：

- 圆角一致：16px 外层、12px 内层。
- 阴影一致：不要右侧更重、左侧更轻。
- 标题系统一致：eyebrow + serif title + small chip。
- 内部卡片减少边框噪音，多用留白和左侧色条。

- [ ] **Step 1: Normalize panel material**

```css
.compare-score-panel {
  min-height: 520px;
  padding: 18px;
  border: 1px solid var(--premium-line);
  border-radius: var(--premium-radius);
  background: linear-gradient(145deg, var(--premium-surface-strong), rgba(248,250,252,0.88));
  box-shadow: var(--premium-shadow);
  display: grid;
  gap: 14px;
  align-content: start;
  overflow: hidden;
}
```

- [ ] **Step 2: Reduce internal border contrast**

```css
.score-major-card,
.score-metric-block {
  border: 1px solid rgba(148,163,184,0.16);
  background: rgba(255,255,255,0.66);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
}
```

- [ ] **Step 3: Use same section naming as chart**

Change `Comparison Matrix` to `PROFILE` or `COMPARISON` if you want a less technical feel.

Recommended copy:

```text
COMPARISON
专业竞争力侧写
```

**Acceptance:** 左右两侧像同一产品里的两张兄弟卡片，而不是“图表 + 另一个组件”。

## Task 5: Harmonize Spacing And Layout Rhythm

**Files:**
- Modify: `.compare-charts-layout`, `.compare-main`, `.compare-score-panel`, `.sub-tab-content` if needed.

- [ ] **Step 1: Use equal gutters**

```css
.compare-charts-layout {
  display: grid;
  grid-template-columns: minmax(0,1.14fr) minmax(390px,.86fr);
  gap: 20px;
  align-items: stretch;
  margin-top: 16px;
}
```

- [ ] **Step 2: Make selector-to-chart spacing intentional**

```css
#comparePanel > .compare-selector-shell,
#comparePanel > .compare-grid {
  margin-bottom: 16px;
}
```

If you add a selector shell, use:

```css
.compare-selector-shell {
  padding: 16px;
  margin-bottom: 16px;
}
```

- [ ] **Step 3: Avoid excessive height mismatch**

Left and right should align at the top and feel balanced. If right panel is longer than left chart, let the page scroll naturally; do not squeeze right metrics until text becomes cramped.

**Acceptance:** 第一屏看起来像完整的设计稿，而不是不同组件拼接。

## Task 6: Apply The Same Aesthetic To Other Data Areas Later

Do this only after 综合对比稳定。

- [ ] **Top30 排名**

Keep the data table, but wrap chart and table in the same `premium-panel` style. Table header should use soft background and sticky shadow. Mini bars should use the same color tokens as comparison matrix.

- [ ] **城市排名**

Use the same card material. For city group labels, use small rounded badges instead of plain text: `珠三角`、`非珠`、`省直`.

- [ ] **洞察总览**

Use the same eyebrow/title/card system. This makes the whole page feel designed, not just one tab.

## Final Visual QA Checklist

- [ ] 原生 checkbox 不再可见。
- [ ] 勾选 chip、左图表、右矩阵的圆角一致。
- [ ] 左图表背景和右矩阵背景属于同一种材质。
- [ ] 图表 tooltip 不像默认 ECharts。
- [ ] 颜色数量控制在 5-6 个核心色以内。
- [ ] 页面没有突兀灰边框、强黑文字、默认控件。
- [ ] 第一屏截图时，顶部 tab、选择器、图表、矩阵都像同一个高级产品。
- [ ] 移动端/窄屏时上下堆叠，chip 不溢出。

## Recommended Execution Order

1. 先改勾选框为 chip，这是最明显的不协调点。
2. 再改左侧折线图外层和 ECharts 样式。
3. 再微调右侧矩阵，使左右统一。
4. 最后把同一套视觉迁移到 Top30 和城市排名。

这版的原则：**少改结构，多改质感；少加功能，多做统一。**