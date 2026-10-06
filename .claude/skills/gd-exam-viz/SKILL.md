---
name: gd-exam-viz
description: 广东省考职位数据分析可视化 — 从 Excel 职位表到交互式数据看板（ECharts）。支持全专业排名、多维对比、地域分析、网络图。触发关键词：省考、职位表、招录趋势、公务员数据可视化、ECharts看板
---

# 广东省考职位数据分析可视化技能

将 `.xls` 格式的广东省公务员考试职位表转换为交互式数据看板的完整工作流。当前代码已演进为 **ECharts + 多Tab综合看板** 架构。

## 工作流程概览

```
① 确定专业范围（专业参考目录）→ 定义专业代码
    ↓
② 数据提取（extract_all_majors.py → all_majors_ranking.json）
    ↓
③ 看板生成（generate_dashboard.py → 广东省考综合数据分析看板.html）
```

## 第一步：数据提取 (extract_all_majors.py)

### 源文件格式
- 2020-2023：两个文件（县级以上机关 + 东西两翼乡镇机关）
- 2024-2026：一个合并文件
- 列名：`是否限应届毕业生报考`、`学历`、`考区`、`招考单位`、`录用人数`、`专业名称(代码)` 等

### 应届毕业生分类逻辑

```python
# 从 2023 年起，"是否限应届毕业生报考"列的值有三种可能：
# 1. "否" → social（社会可报）
# 2. "应届毕业生" → fresh_any（往届应届/择业期）
# 3. "202X届高校毕业生" → fresh_current（当年应届）

if fv == '否':
    fresh_type = 'social'
elif '应届毕业生' in fv:
    if re.search(r'\d+届', fv):       # 含年份数字的"2024届"
        fresh_type = 'fresh_current'
    else:                              # 仅"应届毕业生"
        fresh_type = 'fresh_any'
```

> **注意**：2020-2022 年乡镇机关表不含该列，fresh_type 默认 social。
> **陷阱**：不能用 `'届' in fv` 判断，因为"应届毕业生"也含"届"字。

### 城市归一化

```python
if unit.startswith('广东省') and ('厅' in unit or '局' in unit):
    city = '省直'
```

### 输出数据格式 (all_majors_ranking.json)

每个专业条目结构：
```json
{
  "major": "法学类 (B0301)",
  "total_recruits": 15000,
  "total_positions": 5000,
  "growth_rate": -0.05,
  "fresh_ratio": 0.35,
  "purity": 0.85,
  "competition_index": 12.5,
  "city_coverage": 21,
  "education_distribution": {"本科": 12000, "研究生": 2000, "大专": 1000},
  "yearly": {
    "2020": {"recruits": 2000, "positions": 700},
    "2021": {"recruits": 2200, "positions": 750}
  }
}
```

## 第二步：ECharts 综合看板生成

### 架构模式：单页多 Tab

```
┌─────────────────────────────────────────┐
│ Hero 区域（深蓝底色 + 6 个核心指标）     │
├─────────────────────────────────────────┤
│ 一级导航：专业分析 │ 地域分析 │ 数据源     │
├─────────────────────────────────────────┤
│ 二级 Tab（每个 section 下 N 个 sub-tab）  │
│ 专业分析：排名 → 详情 → 趋势 → 对比       │
│ 地域分析：地图 → 堆叠 → 教育 → 专业×地域   │
└─────────────────────────────────────────┘
```

### 初始化流程

```javascript
// ====== 全局变量 ======
var RANKING = [...];          // 所有专业排名数据
var YEARS = ['2020','2021',...];
var SECTION_NAMES = [...];    // 一级导航
var SUB_TABS = {...};         // 二级Tab配置
var cityData = {...};         // 按城市聚合

// ====== 图表实例变量 ======
var rankingChart = null, lowRankChart = null, cityRankChart = null;
var networkChart = null, mapChart = null;
var trendCharts = {};         // 趋势总览三个图表用对象存储
var compareChart = null, radarChart = null;
var eduChart = null;

// ====== 初始化 ======
function initAll() {
  rankingChart = echarts.init(document.getElementById('rankingChart'));
  lowRankChart = echarts.init(document.getElementById('lowRankChart'));
  // ... 所有图表实例化
  switchSection('section1');  // 默认显示第一个 section
}
```

### Tab 切换核心函数

```javascript
function switchSubTab(tabId, btn) {
  // 1. 隐藏所有 sub-tab
  document.querySelectorAll('.sub-tab-content').forEach(function(el) {
    el.classList.remove('active');
  });
  // 2. 显示目标 tab
  var el = document.getElementById(tabId);
  if (el) el.classList.add('active');
  // 3. 触发 resize（容器尺寸变化后 ECharts 需要 resize）
  setTimeout(resizeAll, 100);
  // 4. 隐藏容器中的图表需要强制刷新（关键修复！）
  var needsRefresh = {
    'm-tab4': 'switchTrend',
    'm-tab5': 'updateCompare',
    'c-tab3': 'updateCityTrend',
    'c-tab4': 'renderFreshEduOverview',
    'c-tab5': 'updateMajorCity',
    'c-tab6': 'updateCityCompare'
  };
  if (needsRefresh[tabId] && typeof window[needsRefresh[tabId]] === 'function') {
    setTimeout(function() { window[needsRefresh[tabId]](); }, 300);
  }
}

function resizeAll() {
  // 使用 class 选择器，而非 [id$=Chart]（后者会遗漏某些图表）
  document.querySelectorAll('.chart-box, .chart-box-sm, .chart-box-map, .network-wrap')
    .forEach(function(el) {
      var inst = echarts.getInstanceByDom(el);
      if (inst) inst.resize();
    });
}
```

### 图表渲染通用模式

```javascript
function renderExampleChart() {
  var cht = echarts.getInstanceByDom(document.getElementById('exampleChart'));
  if (!cht) return;
  cht.resize();  // 必须！确保容器已挂载
  cht.setOption({
    // ... 图表配置
    grid: { left: 60, right: 30, top: 20, bottom: 40 },  // 留足边距
    xAxis: { axisLabel: {fontSize: 12} },  // 字体不可过小
    yAxis: { nameTextStyle: {fontSize: 12} }
  }, true);  // 第二个参数 true = notMerge
  cht.resize();  // setOption 后再 resize 一次（更可靠）
}
```

## 核心 ECharts 图表模式

### 排名柱状图（HSL 渐变色）

```javascript
series: [{
  type: 'bar',
  data: vals.reverse(),
  barMaxWidth: 18,
  label: { show: true, position: 'right', fontSize: 10 },
  itemStyle: {
    color: function(p) {
      var i = p.dataIndex;
      var t = i / maxItems;  // 归一化到 0→1
      return 'hsl(' + Math.round(30 + t * 200) + ', 65%, ' + Math.round(58 - t * 20) + '%)';
    }
  }
}]
```

**参数指南：** `hsl(30→230, 65%, 58→38%)` = 琥珀→蓝色渐变，从亮到暗。

### 折线图（趋势）

```javascript
series: [{
  type: 'line',
  smooth: true,
  data: YEARS.map(function(y) {
    var yr = yearly[y];
    return yr ? yr.recruits : 0;  // 逐层判空！
  }),
  areaStyle: { color: '#e8edf5' },
  lineStyle: { color: '#1a3c6e', width: 3 },
  symbol: 'circle',
  symbolSize: 8
}]
```

### 雷达图（多维度对比）

```javascript
radarChart.setOption({
  radar: {
    indicator: [
      { name: '招录规模', max: maxVal * 1.2 },
      { name: '纯洁度', max: 100 },
      { name: '增长率', max: Math.max(100, maxGrowth * 2) },
      { name: '应届占比', max: 100 },
    ]
  },
  series: [{
    type: 'radar',
    radius: '68%',
    center: ['50%', '48%'],
    areaStyle: { opacity: 0.08 },
    data: selected.map(function(m) { return {
      name: m.major,
      value: [m.total_recruits, formatPercent(m.purity), growth, formatPercent(m.fresh_ratio)]
    };})
  }]
}, true);
```

### 地图（广东）

```javascript
series: [{
  type: 'map',
  map: 'guangdong',  // ECharts 注册的地图名
  roam: true,
  label: { show: true, fontSize: 10 },
  data: mapData,
  itemStyle: { borderColor: '#fff', borderWidth: 1 },
  emphasis: { itemStyle: { areaColor: '#2a5c9e' } }
}]
```

#### 分组着色模式（珠三角/非珠三角/省直）

```javascript
var isGroupMode = group === 'prd';
var groupColors = { prd: '#4a9e5c', 'non-prd': '#c97878', province: '#3a7cce' };

if (isGroupMode) {
  option.series[0].data = mapData.map(function(d) {
    var g = getCityGroup(d.cityName);
    return Object.assign({}, d, {
      value: g === 'prd' ? 1 : (g === 'province' ? 3 : 2),
      itemStyle: { areaColor: groupColors[g], opacity: 0.82 }
    });
  });
  delete option.visualMap;  // 分组模式去掉 visualMap
}
```

### 并排双图布局

```css
.compare-charts-layout {
  display: grid;
  grid-template-columns: 7fr 3fr;
  gap: 16px;
  align-items: stretch;
}
.compare-main { min-height: 520px; }
.compare-radar { min-height: 520px; }
@media (max-width: 900px) {
  .compare-charts-layout { grid-template-columns: 1fr; }
  .compare-main, .compare-radar { min-height: 420px; }
}
```

## 已知陷阱与修复模式

### 1. 数据对象访问安全
```javascript
// ❌ 错误
YEARS.map(y => yearly[y]||0)

// ✅ 正确
YEARS.map(function(y) { var yr = yearly[y]; return yr ? yr.recruits : 0; })
```

### 2. display:none 容器中 ECharts 不渲染
- **现象**：隐藏 Tab 中的图表显示空白
- **根因**：ECharts 在 display:none 容器中初始化尺寸为 0
- **修复**：
  1. Tab 切换时用 `needsRefresh` 映射表延迟调用渲染函数
  2. 每个渲染函数中 `cht.resize()` 在 `setOption` 前后各调一次
  3. `setTimeout(fn, 300)` 确保容器已变为可见

### 3. resizeAll 选择器
```javascript
// ❌ 错误：漏掉 ID 不以 Chart 结尾的图表
document.querySelectorAll('[id$=Chart]')

// ✅ 正确：基于 class 名称选择
document.querySelectorAll('.chart-box, .chart-box-sm, .chart-box-map, .network-wrap')
```

### 4. 空状态
始终为图表添加无数据时的占位提示：
```javascript
if (!selected.length) {
  chart.clear();
  chart.setOption({
    title: {
      text: '请选择数据',
      subtext: '勾选上方选项后显示',
      left: 'center', top: 'middle',
      textStyle: { color: '#1a3c6e', fontSize: 16 },
      subtextStyle: { color: '#888', fontSize: 12 }
    },
    series: []
  }, true);
  return;
}
```

### 5. 防御性输入
```javascript
var idx = parseInt(document.getElementById('detailSelect').value);
if (isNaN(idx)) idx = 0;  // 兜底
```

### 6. 数据源字段映射
实际数据的 key 名可能与假设不一致，用 lookup table 显式映射：
```javascript
var eduKeys = { '研究生':'研究生', '本科':'本科', '本科及以上':'其他', ... };
eduLabels.forEach(function(l) {
  eData[l].push(e[eduKeys[l]]||0);  // 通过映射取值
});
```

### 7. 表格展示优化
```css
.table-wrap { overflow-x: auto; overflow-y: auto; max-height: 600px; }
td { white-space: nowrap; }
th { white-space: nowrap; position: sticky; top: 0; }
td:nth-child(2) { max-width: 260px; overflow: hidden; text-overflow: ellipsis; }
.up { color: #DC2626; font-weight: 500; }
.down { color: #059669; font-weight: 500; }
```

### 8. f-string 与 JS 花括号冲突
JS 代码中的 `{}` 在 Python f-string 中必须双写为 `{{}}`。**建议**：将大段 JS 代码作为 `r"""..."""` 原始字符串，只将简单变量用 f-string 嵌入。

```python
JS_CODE = r"""
document.getElementById('test').textContent = '${value}';
"""  # $ 不会被 f-string 干扰
```

## 设计系统

### CSS 变量（统一管理）

```css
:root {
  --page-bg: #FAFAF8;
  --card-bg: #FFFFFF;
  --border: #E8E8E2;
  --text-primary: #1A1A1A;
  --text-secondary: #4A4A4A;
  --text-tertiary: #787878;
  --accent-blue: #1E3A5F;
  --accent-amber: #D97706;
  --accent-sky: #2563EB;
  --fill-warm: #F2F0EA;
  --font-serif: "Noto Serif SC","Source Han Serif SC","STSong",serif;
  --font-sans: "Inter","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-mono: "JetBrains Mono","SF Mono","Fira Code",monospace;
}
```

### 三字体系统
- **标题**：Noto Serif SC（衬线，正式感）
- **正文**：Inter + PingFang SC（无衬线，易读）
- **数据**：JetBrains Mono（等宽，数字对齐）

### Hero 区域
```html
<div class="hero">
  <h1>标题<button class="help-btn" onclick="showHelp()">?</button></h1>
  <div class="hero-subtitle">数据范围说明</div>
  <div class="stats-bar">
    <div class="stat-item">
      <div class="stat-num">15000</div>
      <div class="stat-label">总招录</div>
    </div>
    <!-- 更多指标... -->
  </div>
</div>
```

### Hero CSS
```css
.hero { background: var(--accent-blue); border-radius: 10px; padding: 32px 40px 28px; margin-bottom: 28px; }
.hero h1 { font-family: var(--font-serif); font-size: 28px; color: #fff; text-align: center; }
.stat-item { background: rgba(255,255,255,0.08); backdrop-filter: blur(4px); border-radius: 8px; padding: 14px 24px; }
.stat-num { font-family: var(--font-mono); font-size: 26px; color: #fff; }
```

## 代码审查清单

当 review 或编写 ECharts 数据看板代码时，检查以下要点：

### 数据层
- [ ] 嵌套对象访问有逐层判空（`a?.b?.c` 或 `var x = a; if (x) return x.b;`）
- [ ] flat 字段（如 `fresh_ratio`）与 nested 字段（如 `yearly[y].recruits`）区分清晰
- [ ] 数据字段名通过 lookup table 映射，不硬编码假设

### 图表层
- [ ] resizeAll 基于 class 选择器
- [ ] `setOption({...}, true)` 使用 notMerge
- [ ] 隐藏容器图表有延迟刷新机制（needsRefresh）
- [ ] 空状态有友好提示
- [ ] grid 边距充裕（left ≥ 50, bottom ≥ 30）
- [ ] axisLabel fontSize ≥ 12

### UI 层
- [ ] CSS 变量管理颜色，无硬编码色值
- [ ] 表格有 `white-space: nowrap` 和 `max-height`
- [ ] 响应式布局 grid + media query
- [ ] 渐变色用 HSL 动态计算，非硬编码分段
- [ ] select 值有防御性 parseInt + isNaN 检查

### ECharts 特有
- [ ] `display:none` 容器初始化的图表需延迟渲染
- [ ] map 分组模式需 `delete option.visualMap`（不显示色阶图例）
- [ ] resize() 在 setOption 前后各调一次
