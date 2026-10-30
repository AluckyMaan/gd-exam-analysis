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
- 2024-2027：一个合并文件（2027 起同样为单文件 6 个 sheet）
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
│ 一级导航：专业热度 │ 地域维度 │ 年度变化   │
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

### 排名柱状图（v4：单色 + 12px 轴）

~~~javascript
series: [{
  type: 'bar',
  data: vals.reverse(),
  barMaxWidth: 13,                       // 30 行 / 760px 时约 13–16px
  label: { show: true, position: 'right', fontSize: 11, color: '#475569' },
  itemStyle: { color: '#1e3a5f' }        // 单一色：颜色不编码名次
}]
~~~

**原则：** 名次已由排序和排名 pill 表达，不要再把名次映射成色相/明度渐变；
颜色只表达分类（区域/学历）或语义（增长/下降）。长专业名用
axisLabel.formatter 截断到 16 字 + …，完整名放 tooltip。

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
  label: { show: true, fontSize: 12, color: '#1e3a5f', textBorderColor: '#fff', textBorderWidth: 2 },
  labelLayout: { hideOverlap: true },     // 珠三角小市标签不互相压住
  data: mapData,
  itemStyle: { borderColor: '#fff', borderWidth: 1 },
  emphasis: { itemStyle: { areaColor: '#2a5c9e' } }
}]
```

#### 分组着色模式（珠三角/非珠三角/省直）

```javascript
var isGroupMode = group === 'prd';
var groupColors = { prd: '#1e3a5f', 'non-prd': '#b45309', province: '#64748b' };

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
.down { color: #047857; font-weight: 500; }
```

### 8. f-string 与 JS 花括号冲突
JS 代码中的 `{}` 在 Python f-string 中必须双写为 `{{}}`。**建议**：将大段 JS 代码作为 `r"""..."""` 原始字符串，只将简单变量用 f-string 嵌入。

```python
JS_CODE = r"""
document.getElementById('test').textContent = '${value}';
"""  # $ 不会被 f-string 干扰
```

## 设计系统（v4 视觉基线，2026-10-25）

### 页面骨架
- 浅色画布 + 深色 hero + 单层白卡片：页面底色 #f3f4f2；hero 是全页唯一的深色块；
  内容区不再套“白色大面板”，图表/表格各自是一张卡片。
- 层级上限 3 层：页面 → 卡片 →（图表 canvas）。premium-panel 内的图表去掉内层边框。
- 导航：一级 bar 为浅色 sticky 胶囊条；二级子 Tab 吸顶在导航下方，激活项为白色 pill。
- 阴影只用于浮层（下拉/弹窗）；卡片用 1px 线 + 白底，不用阴影和 backdrop-filter。
- 已移除 SVG 波浪背景与 body::before 径向渐变（省 GPU，避免深色外框）。

### CSS 变量
~~~css
:root {
  --page-bg: #f3f4f2;
  --line: #e2e6ec;
  --ink-400: #64748b;   /* 辅助文字，白底 4.76:1 */
  --ink-500: #475569;
  --ink-600: #334155;
  --accent-sky: #1d4ed8;
  --accent-amber: #a16207;
  --green-600: #047857;
  --font-serif: "Noto Serif SC","Source Han Serif SC","Source Han Serif CN","Noto Serif CJK SC","Songti SC","STSong","SimSun",serif;
  --font-sans: "Inter","PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,-apple-system,"Segoe UI",sans-serif;
  --font-mono: "JetBrains Mono",ui-monospace,"Cascadia Mono","SF Mono",Consolas,monospace;
  --fs-caption: 12px; --fs-body: 14px; --fs-title: 16px;
  --radius-card: 12px; --radius-control: 8px;
}
button, select, input, textarea { font: inherit; }   /* 表单控件必须继承字体 */
~~~

### 字号与排版
- 五级：12（只给图例/注释）/ 14（正文与表格）/ 16（卡片标题）/ 20–22（区块标题）/ 32（页头）。
- 图表轴 axisLabel ≥ 12；数据标签 ≥ 11；表格正文 14、表头 13。
- 数字：font-variant-numeric: tabular-nums；表格文本列左对齐、数值列右对齐。
- 全量数字走 formatNumber()；百分比统一 formatPercent()（固定 1 位小数）。
- 6 个 emoji 小标题已改为 .panel-title（左侧 3px 竖线 + 单位 span），全页只用两套标题体系。

### 配色规则
- 主色海军蓝 #1e3a5f，强调琥珀 #a16207，中性灰阶 ink-50…900。
- 语义色只有两个：红 #dc2626 增长、绿 #047857 下降；必须同时带 ▲/▼ 或“扩招/收缩”文字。
- 分类色最多 6 个：#1e3a5f / #2563eb / #b45309 / #0f766e / #7c3aed / #be123c。
- 珠三角=#1e3a5f，非珠=#b45309，省直=#64748b（不要再用绿/红表示区域）。
- 地图连续色阶：#eef3fb → #8abcf5 → #1e3a5f。
- 小字对比度：白底 ≥ 4.5:1；图形/线 ≥ 3:1。已知达标值：ink-400 4.76、白 72% on 海军蓝 6.81、amber 4.92、green 5.48。

### 字体加载
- 看板 head 保留 Google Fonts 作为渐进增强；断网或字体被墙时回退到系统中文衬线/无衬线
  （SimSun/Songti、PingFang/微软雅黑），因此 CSS 必须写全回退栈。
- 不依赖未安装字体做布局关键尺寸（字号/行高/列宽都用 px）。

### Hero（v4）
~~~html
<div class="hero">
  <div class="hero-copy">
    <h1>标题 <button class="help-btn" type="button" onclick="showHelp()" aria-label="指标说明">?</button></h1>
    <p class="hero-subtitle">数据来源 + 口径</p>
  </div>
  <div class="stats-bar"> <!-- 4 个真指标，桌面 1 行、移动 2×2 --> </div>
</div>
~~~
~~~css
.hero { display:grid; grid-template-columns:minmax(0,1fr) minmax(400px,540px);
        align-items:center; gap:24px; padding:16px 24px; border-radius:14px;
        background:linear-gradient(135deg,#12233d,#1e3a5f 62%,#24466f); }
.stats-bar { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:6px; }
~~~
- 桌面 hero 高度约 105px，首屏内容起点约 258px（1440×900）。
- KPI 只放真指标（招录人数 / 职位数 / 专业数 / 城市数），不要放“数据跨度”或“榜首专业”。

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
- [ ] 表格 14px；文本列左对齐、数值列右对齐；数字 tabular-nums
- [ ] 响应式布局 grid + media query；1440/390px 无横向溢出
- [ ] 颜色必须编码信息（分类/语义），不做纯装饰渐变
- [ ] 小字对比度 ≥ 4.5:1（白底），图形 ≥ 3:1
- [ ] 页面层级 ≤ 3 层（页面 → 卡片 → 图表）
- [ ] 数字格式化走 formatNumber/formatPercent，不裸拼
- [ ] Tab 有 role=tablist/tab/tabpanel 与 aria-selected；自定义可点卡片可键盘触发
- [ ] select 值有防御性 parseInt + isNaN 检查

### ECharts 特有
- [ ] `display:none` 容器初始化的图表需延迟渲染
- [ ] map 分组模式需 `delete option.visualMap`（不显示色阶图例）
- [ ] resize() 在 setOption 前后各调一次
