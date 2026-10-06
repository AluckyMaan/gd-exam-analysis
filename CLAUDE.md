# 广东省考职位数据分析看板项目

## 项目概述
把广东省考试录用公务员职位表（`.xls`）提取成 JSON 中间产物，再生成**单页多 Tab 交互式数据看板**。
主交付物是根目录下的 **`广东省考综合数据分析看板.html`**：原生 JS + 本地 ECharts 5.5，纯静态、无构建、双击即可打开。

根目录另有若干单专业/单维度历史看板（土木、电子信息、海洋工程、汉语言、材料、地域维度、专业深度分析等），
属于早期独立产物，只保留不再作为主维护目标。

## 真实目录结构
```
广东20-26年广东省考职位表/
├─ data/                          12 个原始 .xls + JSON 中间产物
├─ assets/echarts.min.js          本地 ECharts 5.5（离线可用）
├─ scripts/
│  ├─ extract/                    数据提取脚本（.xls → JSON）
│  ├─ generate/                   看板生成脚本（JSON → HTML）
│  └─ capture_xhs_materials.mjs   小红书发布图截取脚本
├─ docs/superpowers/              plans + specs（历史设计与计划文档）
├─ xhs_publish_materials/         小红书发布图 9 张 + README.md
├─ .claude/skills/gd-exam-viz/SKILL.md   权威技能文档（ECharts 版，最新，已纳入版本控制）
├─ .agents/skills/gd-exam-viz/SKILL.md   本机镜像副本（同一内容，已被 .gitignore 忽略）
├─ CLAUDE.md
├─ index.html                     导航入口
└─ 广东省考综合数据分析看板.html   ← 主交付物
```

## 核心文件
| 文件 | 作用 |
| --- | --- |
| `scripts/generate/generate_merged_viz.py` | **唯一**主看板生成器 → 根目录 `广东省考综合数据分析看板.html` |
| `scripts/extract/extract_all_majors.py` | 数据源生成器 1：全专业排名 → `data/all_majors_ranking.json` |
| `scripts/extract/extract_city_data.py` | 数据源生成器 2：地域维度 → `data/city_data.json` |
| `scripts/generate/gviz_common.py` | 公共模块（提取/工具函数，被 `make_viz.py` 等生成器引用） |
| `scripts/generate/make_viz.py` | 统一 CLI 入口：一键「提取 + 生成」，支持自定义专业关键词与配色 |
| `scripts/generate/generate_major_ranking_viz.py`、`generate_city_html.py`、`generate_html.py`、`generate_viz_html.py`、`generate_汉语言_html.py`、`generate_electronics_html.py`、`generate_electronics_html_standalone.py`、`generate_ocean_html.py`、`gen_el_html.py`、`gen_data.py` | 各单专业/单维度历史生成器（分别读取 `data/all_majors_ranking.json` 或 `data/city_data.json`） |
| `scripts/extract/extract_cailiao.py`、`extract_electronics.py`、`extract_ocean.py`、`extract_data.py`、`_extract_汉语.py` | 各单专业历史提取脚本 |
| `assets/echarts.min.js` | 本地 ECharts 5.5，无 CDN 依赖 |
| `.claude/skills/gd-exam-viz/SKILL.md` | 完整技能文档（权威、最新，ECharts 架构） |
| `xhs_publish_materials/README.md` | 小红书发布图片清单与文案 |

## 数据管线
```
data/*.xls
   ├─ scripts/extract/extract_all_majors.py ─→ data/all_majors_ranking.json
   └─ scripts/extract/extract_city_data.py  ─→ data/city_data.json
                       ↓
        scripts/generate/generate_merged_viz.py
                       ↓
            广东省考综合数据分析看板.html
```
一行图：`xls → all_majors_ranking.json + city_data.json → generate_merged_viz.py → 广东省考综合数据分析看板.html`

## 技术栈
- **图表**：ECharts 5.5（非 Chart.js），通过本地 `assets/echarts.min.js` 引入，离线可用
- **形态**：纯静态单页，HTML + 内联 CSS/JS，无构建步骤、无 npm 依赖，浏览器直接打开
- **字体**：Noto Serif SC（标题）+ Inter（正文）+ JetBrains Mono（数字）
- **配色**：CSS 变量系统（详见 skills）

## 关键修复模式（必须遵守）

### 1. 数据访问安全
```javascript
// ✅ 嵌套对象逐层判空
var yr = yearly[y]; return yr ? yr.recruits : 0;
```

### 2. 隐藏容器重绘
- Tab 切换用 `needsRefresh + setTimeout(fn, 300)` 延迟刷新
- 每个渲染函数中 `cht.resize()` 在 `setOption` 前后各调一次

### 3. resizeAll 选择器
```javascript
// ✅ 基于 class，而非 [id$=Chart]
document.querySelectorAll('.chart-box, .chart-box-sm, .chart-box-map, .network-wrap')
```

### 4. 空状态处理
所有动态图表必须处理 0 项选择的空状态（显示提示文字）。

### 5. HSL 渐变色替代硬编码
```javascript
color: function(p) { var t = p.dataIndex / maxItems; return `hsl(${30+t*200}, 65%, ${58-t*20}%)`; }
```

### 6. ECharts 配置
- `setOption({...}, true)` — 使用 notMerge
- grid left ≥ 50, bottom ≥ 30, axisLabel fontSize ≥ 12
- 分组模式地图需要 `delete option.visualMap`

### 7. 表格优化
`white-space: nowrap`, `max-height: 600px`, sticky th, text-overflow: ellipsis

## 数据口径与已知约束
- **74849 的口径**：74849 = **含专业要求**的职位记录数，**不是**全省招考人数，也不等于全量职位数（地域侧全 sheet 口径的职位记录为 **73353**）。凡在文案/图例中出现该数字，必须写明是「含专业要求的职位记录数」，不得写成「职位数」「招录人数」，也不要与地域侧的职位数混在同一句里。
- **年度招考人数口径**：以**全部 sheet 汇总**为准（县级以上机关 + 珠三角乡镇 + 东西两翼/北部生态发展区乡镇机关等所有表都要计入），不得只用单一 sheet 汇总。2020-2026 各年合计已与专业侧完全对齐。
- **表头行定位**：`find_header_row()` 会排除以「报考条件/配套措施/附件」开头的说明行，并优先选择含「录用人数/招考单位/招录主管部门/职位代码/考区」等强表头信号的行。乡镇子表（本市/本县大专以上、专项人员）的说明行正文里含"应届硕士…"字样，历史上会被误判为表头，导致整张子表提取为空 —— 修改该函数时必须保留这两条约束。
- **地域维度**：地域（城市）维度数据同样来自全部 sheet；学历分组从数据动态取得（`getEduLabels()`），不要再在图表里硬编码分组列表。
- **地图 GeoJSON**：优先使用本地缓存 `data/guangdong_geojson.json`、离线可重建；缺失时才联网并把结果落盘。需要刷新地图时删掉缓存文件再跑一次。
- **已删除、不要重新引入**：`data/major_ranking.json`（旧口径孤立残留：10 文件 / 71296 行 / 1550 专业，无任何看板或生成器读取）；`scripts/fix/`（8 个一次性源码字符串替换补丁，其中 6 个指向早已不维护的土木 HTML）。
- **仓库忽略规则**：`.gitignore` 忽略可重建的大体积产物（`data/all_majors_ranking.json`、`data/city_data.json`、`data/guangdong_geojson.json`、`data/_before_city_data.json`）、`__pycache__/`、`.agents/`、`.superpowers/`、`*.pdf`。`scripts/`、`docs/`、`.claude/` **正常纳入版本控制**（早期规则曾把这三者忽略，导致推送后仓库里没有代码，已修正）。注意这三者原本不在仓库中时，需 `git add -f` 才能纳入。
- **路径约定**：`generate_merged_viz.py`、`extract_all_majors.py`、`extract_city_data.py` 内 `BASE_DIR` 为硬编码绝对路径，迁移目录后需同步修改。
- 提取脚本解析 `.xls` 依赖 `xlrd`；不要改动 `data/*.xls` 原始文件。
