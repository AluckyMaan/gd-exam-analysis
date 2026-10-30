# 广东省考职位数据分析看板项目

## 项目概述
把广东省考试录用公务员职位表（`.xls`）提取成 JSON 中间产物，再生成**单页多 Tab 交互式数据看板**。
主交付物是根目录下的 **`广东省考综合数据分析看板.html`**：原生 JS + 本地 ECharts 5.5，纯静态、无构建、双击即可打开。

根目录另有若干单专业/单维度历史看板（土木、电子信息、海洋工程、汉语言、材料、地域维度、专业深度分析等），
属于早期独立产物，只保留不再作为主维护目标。

## 真实目录结构
```
广东20-27年广东省考职位表/
├─ data/                          14 个原始 .xls + JSON 中间产物
├─ assets/echarts.min.js          本地 ECharts 5.5（离线可用）
├─ scripts/
│  ├─ extract/                    数据提取脚本（.xls → JSON）
│  ├─ generate/                   看板生成脚本（JSON → HTML）
│  ├─ generate_xhs_cards.mjs      小红书发布图生成器（6 张 1080×1440，CDP 出图，零 npm 依赖）
│  └─ capture_xhs_materials.mjs   旧版发布图截取脚本（playwright，仅存档）
├─ docs/superpowers/              plans + specs（历史设计与计划文档）
├─ xhs_publish_materials/         小红书发布图：2027/ 6 张（最新）+ 根目录 9 张历史截图 + README
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
| `xhs_publish_materials/2027/README.md` | **最新**小红书发布图（6 张）+ 标题/正文文案 |
| `scripts/generate_xhs_cards.mjs` | 小红书发布图生成器：读 `data/*.json` 实时算数 → 渲染 6 张 1080×1440 → Edge CDP 出图 |
| `xhs_publish_materials/README.md` | 历史 9 张截图清单（2026-07-20，数字已过时） |

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
- **字体**：Noto Serif SC（标题）+ Inter（正文）+ JetBrains Mono（数字），均已补全系统中文字体回退栈；Google Fonts 仅作渐进增强，断网/被墙时自动回退
- **配色**：浅色画布 + 海军蓝主色 + 琥珀强调；语义色只有红涨绿跌；CSS 变量系统（详见 skills）

## 视觉基线（v4，2026-10-25）

主看板在 2026-10-25 做了一次视觉系统收口（计划见 docs/superpowers/plans/2026-10-25-dashboard-visual-system-v4.md）：

- **页面骨架**：浅色画布 #f3f4f2 + 深色 hero + 单层白卡片；内容区不再套白色大面板，子 Tab 吸顶；桌面 hero 约 105px，首屏内容起点约 258px（1440×900）。
- **字号**：12（图例/注释）/ 14（正文与表格）/ 16（卡片标题）/ 20–22（区块标题）/ 32（页头）；图表轴 ≥12，数据标签 ≥11。
- **数字**：全量走 formatNumber / formatPercent（百分比固定 1 位小数）；表格文本列左对齐、数值列右对齐，数字 tabular-nums。
- **颜色**：语义色只有红涨 #dc2626 / 绿跌 #047857，且必须带 ▲▼ 或文字；分类色最多 6 个（#1e3a5f / #2563eb / #b45309 / #0f766e / #7c3aed / #be123c）；珠三角=#1e3a5f、非珠=#b45309、省直=#64748b。
- **图表**：不用纯装饰性渐变（名次/年份不再映射成色相）；长标签截断到 16 字、完整名放 tooltip；地图标签 12px + 白描边 + labelLayout.hideOverlap。
- **关联网络**：全局 12 个专业放射环布局 + 右侧读数栏（最强关联 Top5）；聚焦模式为中心 + Top10 邻居（移动端 8/6）；点击节点切换、侧栏可返回全局；移动端只标注 3 个节点，完整名单在侧栏列表。
- **可访问性**：Tab 有 role=tablist/tab/tabpanel + aria-selected；help 按钮为 button；洞察卡可聚焦并支持 Enter/Space；新增 @media print。
- **已移除**：SVG 波浪背景、body 径向渐变、卡片阴影/backdrop-filter（浮层除外）。

改动必须落在 scripts/generate/generate_merged_viz.py 的 HTML 模板里，再重新生成；**不要直接编辑根目录 HTML**。

## 年度变化页（2027 数据入库时新增）

- **定位**：一级导航第三个 Tab「最新年份 年度变化」，只回答「最新一年 vs 上一年变了什么」，不重复首页的多年趋势图。
- **三个二级 Tab**：① 变化总览（4 个 KPI + 年度规模图 + 结构三线 + 年度总表 + 3 张结构洞察卡）；② 专业变化（增/减 Top8 发散条形 + Top20 表 + 新增/消失专业 chip）；③ 城市变化（22 城发散条形 + 全量表 + 珠三角/非珠/省直结构 chip）。
- **视觉**：沿用仓库的 v4 视觉基线（深色 hero + 白卡片 + navy #1e3a5f 主系列 + amber #a16207 强调；发散条形用红涨 #dc2626 / 绿跌 #059669），不注册额外 ECharts 主题；组件复用 `.overview-shell / .overview-head / .exec-summary / .metric / .insight-card / .data-table`。
- **年度轴唯一来源**：`generate_merged_viz.py` 的 `ALL_YEARS`（派生 `LATEST_YEAR` / `PREV_YEAR`，并注入 `STATS.years` 与 JS 的 `YEARS`）。**新增年份时改这里 + 两个提取脚本 + 测试基线**，不要在 JS/HTML 里再硬编码年份。
- **结构数据**：`city_data.json` 的 `yearly_structure`（逐年 学历分组 / 应届三分 / 珠三角·非珠·省直），由 `extract_city_data.py` 用 `normalize_education` 生成，口径与地域 Tab 完全一致。
- **口径**：规模一律逐职位聚合；专业变化用「专业出现次数」并标注不可相加；结构差异用百分点（pp），规模差异用人数与百分比；红涨绿跌 + ▲▼；空数据必须走空状态文案。
- **增长率统一口径**：近三年（当前 2025–2027）年均 vs 前三年（2020–2022）年均，由 JS 的 `GROWTH_RECENT` / `GROWTH_EARLY` 与提取脚本的同名窗口共同决定；地图、城市排名、城市详情共用 `calcYearWindowGrowth()`。

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

### 5. 颜色必须编码信息
- 名次/年份不再映射成色相或明度渐变（v4 起主看板排名柱、年份柱均为单色）。
- 区分维度用分类色（最多 6 个）或语义色（红涨绿跌），并保证图形对比度 ≥3:1。
- 纯装饰渐变只允许出现在 hero 等非数据区域。

### 6. ECharts 配置
- `setOption({...}, true)` — 使用 notMerge
- grid left ≥ 50, bottom ≥ 30, axisLabel fontSize ≥ 12
- 分组模式地图需要 `delete option.visualMap`

### 7. 表格优化
`white-space: nowrap`, `max-height: 600px`, sticky th, text-overflow: ellipsis

## 数据口径与已知约束
- **⚠️ 禁止把各专业的数量相加**：同一职位若在专业列写了 N 个专业，会在各专业名下**重复计入**。`sum(RANKING[].total_recruits)` = 264,947，`sum(RANKING[].total_positions)` = 188,339 —— 都**没有现实对应物**（分别是真实值的 2.29 / 2.27 倍）。**首页展示规模一律用地域侧逐职位聚合的真实值**：职位数 `STATS.positions` = **83,060**、招录人数 `STATS.recruits` = **115,658**（由生成器注入 `var STATS`）。专业侧保留现状（竞争指数/纯洁度已表达共招），但在页面上必须写明"专业数值不可相加"。若要做"Top3 占比"这类比例，分母要么用真实职位数，要么明确标注为"专业出现次数"，不得用膨胀值。
- **83060 的口径**：83060 = **全部 sheet 的职位记录数**，也是**含专业要求**的职位记录数 —— 两侧现已相等（专业侧 `summary.total_position_rows` = 地域侧 `summary.total_positions` = 83060）。历史差异：地域侧曾是 73353，因为 2023 附件1 被漏读 1496 行（见下条）。注意 83060 仍**不等于**全省招考人数（招录总人数为 **115658**）。
- **职位表拆份结构**：2020-2023 年官方把职位表**拆成两份**（公告附件1 = 沿海经济带东西两翼及北部生态发展区乡镇机关；附件2 = 县级以上机关和珠三角地区乡镇机关），**两份都要读**；2024 年起合并为一份（附件1 内含 6 个 sheet）。`files_config()` 按「年份 + 附件序号 + 关键词候选」在 `data/` 里实际查找，不再写死文件名。
- **⚠️ 静默漏表的教训**：`files_config()` 曾把 2023 附件1 写成「…2023年**招录**公务员职位表.xls」，而官网实际文件名是「…2023年**考试录用**公务员职位表.xls」（2021 及更早用"招录"，2022-2023 用"考试录用"，逐年在变）。原实现用 `os.path.exists()` 判断、对不上就 `continue`，**不报错不提示**，导致 2023 少统计 3401 人（14857→应为 18258）、珠三角占比虚高到 45.0%（实际 43.5%）。现在找不到会打印 `[WARN]`，且 `resolve_job_tables()` 会报告"像是职位表却未被认领"的文件。**改动文件匹配逻辑后务必跑 `scripts/test_clean_checkout.py`**（含 4 条漏表断言）。
- **数据范围：只看省考**（业主明确的口径决定）。本看板统计**广东省考试录用公务员（省考）统一招考**的职位，**直接取自省公务员主管部门发布的官方附件**（`data/*.xls` 即官网下载原件）。**不含**选调优秀大学毕业生、急需紧缺专业公务员、定向港澳选拔等**另行发布**的招录计划。
- **⚠️ 不要拿"公告计划招考总数"当基准校验本看板**（业主明确指示）。当年的公告总数口径更宽，把选调生等并行计划一起报，因此 2020-2022 年本看板合计会低于该总数（2020 少 437、2021 少 399、2022 少 379）；2023–2026 年两者一致（18258 / 17307 / 17419 / 11779 逐年精确吻合）；2027 年职位表合计 **10293** 人（新数据，公告口径待核对）。**这不是数据缺失**：2020-2022 已做逐行审计，6 份文件 / 33 个 sheet / 28,181 行**零跳过、零遗漏**（见 `scripts/audit_2020_2022.py`），且目录中"像是职位表却未被读取"的文件为 0。**不要去补那几份选调生表**——除非业主改口径。
- **年度招考人数口径**：以**全部 sheet 汇总**为准（县级以上机关 + 珠三角乡镇 + 东西两翼/北部生态发展区乡镇机关等所有表都要计入），不得只用单一 sheet 汇总。逐年合计：11871 / 13309 / 15422 / 18258 / 17307 / 17419 / 11779 / 10293（合计 115658）。
- **表头行定位**：`find_header_row()` 会排除以「报考条件/配套措施/附件」开头的说明行，并优先选择含「录用人数/招考单位/招录主管部门/职位代码/考区」等强表头信号的行。乡镇子表（本市/本县大专以上、专项人员）的说明行正文里含"应届硕士…"字样，历史上会被误判为表头，导致整张子表提取为空 —— 修改该函数时必须保留这两条约束。
- **地域维度**：地域（城市）维度数据同样来自全部 sheet；学历分组从数据动态取得（`getEduLabels()`），不要再在图表里硬编码分组列表。
- **地图 GeoJSON**：优先使用本地缓存 `data/guangdong_geojson.json`、离线可重建；缺失时才联网并把结果落盘。需要刷新地图时删掉缓存文件再跑一次。该缓存（205 KB）**已纳入版本控制**：全新克隆即可离线复现，`test_clean_checkout.py` 的「生成过程未依赖网络」断言因此稳定通过（历史上它被 ignore，导致全新克隆首跑必有一项失败）。
- **已删除、不要重新引入**：`data/major_ranking.json`（旧口径孤立残留：10 文件 / 71296 行 / 1550 专业，无任何看板或生成器读取）；`scripts/fix/`（8 个一次性源码字符串替换补丁，其中 6 个指向早已不维护的土木 HTML）。
- **跨层次同名专业不折进专科大类（2027-10-30 起）**：同一个专业名可能同时出现在研究生（A）/本科（B）/专科（C）目录（如「审计」=A1206+C120203、「商务英语」=B050262+C050301）。归并大类的键是**名称**，因此「首见代码」可能来自 2020 年乡镇表的专科代码，把本科/研究生岗位折进专科大类 —— 2027 年就曾把 399 人的 审计(A1206) 折进「财务会计类」，让它看起来是该年最大涨幅专业。现规则：若某名称的代码同时含 A/B 和 C，且算出的父级是 C 开头大类，则**不归并、保留为独立条目**，展示代码改用该名称下出现最多的代码。当前生效 5 个：审计 / 商务英语 / 社区矫正 / 国际商务 / 临床工程技术（专业条目 247 → 252）。改这条规则会同时改变多个大类的历史数值，需重跑提取并复核 `ranking` 长度与 `test_clean_checkout.py` 基线。
- **`服务基层/退役士兵专岗`（code=`SPECIAL-SR`）**：由 `extract_all_majors.py` **脚本内确定性构造**，识别规则为「其他要求」含 `服务基层项目人员和退役大学生士兵` 的职位，加上 2020-2022 的乡镇「专项人员」表。⚠️ 该条目**历史上靠人工改 JSON 注入**，重跑提取即丢失、且因文件曾被 `.gitignore` 忽略而从 git 看不出丢失（已发生一次事故）。**不要再手工改 JSON**；如需调整口径，改脚本并同步更新 `data/all_majors_ranking.json`。当前脚本口径为 2103 职位 / 3845 人（2027 年新增 228 职位 / 404 人），与原人工 patch（1828 / 3346）的差异来自 2020-2023 的识别规则，待业务确认。展示名已去掉「不限专业：」前缀（2026-10-25），数据口径不变。
- **仓库忽略规则**：`.gitignore` 忽略 `__pycache__/`、`.agents/`、`.superpowers/`、`*.pdf`、`*.prev`、`*.ref`、`.clean-checkout-test/`，以及 `data/_before_city_data.json`（本地对比快照）。**`data/all_majors_ranking.json`、`data/city_data.json` 与 `data/guangdong_geojson.json` 有意纳入版本控制** —— 看板内嵌数据必须与它们一致，且它们的存在是本项目「可复现、可审核」的前提（见上一条事故）。`scripts/`、`docs/`、`.claude/` 正常纳入版本控制。
- **可复现性验证**：`scripts/test_clean_checkout.py` 用 `git worktree` 导出当前 HEAD 到干净检出，在其中跑完整管线并核对 25 项断言（含深比对、整条流水线逐字节确定性、以及 4 条"防漏表"断言）。改动提取/生成脚本后请务必跑一次。
- **看板行为验证（两层，缺一不可）**：① `node scripts/test_major_city_input.js` —— 自制 DOM/ECharts 桩执行看板真实内联 JS，快、无需浏览器，能抓 JS 逻辑与接线；**但它没有 CSS 级联、也没有真实输入管线**，所以 `style.display=''`、`mousedown/change` 时序、输入法组合态这类问题它一律看不见（曾因此漏掉"候选面板 CSS 默认 display:none + 内联置空 → 真实浏览器里下拉永不出现"，桩里全绿）。② `node scripts/e2e_major_city.mjs` —— 用 Chrome DevTools Protocol 驱动本机已装的 Edge（**零 npm 依赖**，Node 22+ 自带 WebSocket/fetch），真实键鼠 + 真实 computed style/布局盒 + 逐屏截图 + 页面异常捕获。**改看板 HTML/CSS/内联 JS 后跑 ②**；环境不具备（无浏览器 / CDP 起不来 / Node<22）会打印 `SKIP` 并以 0 退出，可安全进 CI。**前提：沙箱不得限制浏览器的进程间通信 —— 文件策略需为 `danger-full-access`；受限模式下 Chromium 会 `mojo ... 拒绝访问` 直接 FATAL。**
- **禁止硬编码绝对路径**：所有脚本的项目根目录必须由 `__file__` 推导（`os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))`；`.mjs` 用 `fileURLToPath(import.meta.url)`）。历史上多个脚本写死 `C:/Users/YANG/Desktop/...`，导致无法在其它机器或干净检出复现。**非项目依赖的第三方模块（如 `scripts/capture_xhs_materials.mjs` 用的 playwright）不得写死本机路径**：按「环境变量（如 `GD_EXAM_PLAYWRIGHT`）→ 项目/上层 `node_modules`」的顺序解析，解析失败要打印可执行的安装指引。
- 提取脚本解析 `.xls` 依赖 `xlrd`；不要改动 `data/*.xls` 原始文件。
