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
- **⚠️ 禁止把各专业的数量相加**：同一职位若在专业列写了 N 个专业，会在各专业名下**重复计入**。`sum(RANKING[].total_recruits)` = 236,473，`sum(RANKING[].total_positions)` = 165,940 —— 都**没有现实对应物**（分别是真实值的 2.24 / 2.22 倍）。**首页展示规模一律用地域侧逐职位聚合的真实值**：职位数 `STATS.positions` = **74,849**、招录人数 `STATS.recruits` = **105,365**（由生成器注入 `var STATS`）。专业侧保留现状（竞争指数/纯洁度已表达共招），但在页面上必须写明"专业数值不可相加"。若要做"Top3 占比"这类比例，分母要么用真实职位数，要么明确标注为"专业出现次数"，不得用膨胀值。
- **74849 的口径**：74849 = **全部 sheet 的职位记录数**，也是**含专业要求**的职位记录数 —— 两侧现已相等（专业侧 `summary.total_position_rows` = 地域侧 `summary.total_positions` = 74849）。历史差异：地域侧曾是 73353，因为 2023 附件1 被漏读 1496 行（见下条）。注意 74849 仍**不等于**全省招考人数（招录总人数为 **105365**）。
- **职位表拆份结构**：2020-2023 年官方把职位表**拆成两份**（公告附件1 = 沿海经济带东西两翼及北部生态发展区乡镇机关；附件2 = 县级以上机关和珠三角地区乡镇机关），**两份都要读**；2024 年起合并为一份（附件1 内含 6 个 sheet）。`files_config()` 按「年份 + 附件序号 + 关键词候选」在 `data/` 里实际查找，不再写死文件名。
- **⚠️ 静默漏表的教训**：`files_config()` 曾把 2023 附件1 写成「…2023年**招录**公务员职位表.xls」，而官网实际文件名是「…2023年**考试录用**公务员职位表.xls」（2021 及更早用"招录"，2022-2023 用"考试录用"，逐年在变）。原实现用 `os.path.exists()` 判断、对不上就 `continue`，**不报错不提示**，导致 2023 少统计 3401 人（14857→应为 18258）、珠三角占比虚高到 45.0%（实际 43.5%）。现在找不到会打印 `[WARN]`，且 `resolve_job_tables()` 会报告"像是职位表却未被认领"的文件。**改动文件匹配逻辑后务必跑 `scripts/test_clean_checkout.py`**（含 4 条漏表断言）。
- **数据范围：只看省考**（业主明确的口径决定）。本看板统计**广东省考试录用公务员（省考）统一招考**的职位，**直接取自省公务员主管部门发布的官方附件**（`data/*.xls` 即官网下载原件）。**不含**选调优秀大学毕业生、急需紧缺专业公务员、定向港澳选拔等**另行发布**的招录计划。
- **⚠️ 不要拿"公告计划招考总数"当基准校验本看板**（业主明确指示）。当年的公告总数口径更宽，把选调生等并行计划一起报，因此 2020-2022 年本看板合计会低于该总数（2020 少 437、2021 少 399、2022 少 379）；2023 年起两者一致（18258 / 17307 / 17419 / 11779 逐年精确吻合）。**这不是数据缺失**：2020-2022 已做逐行审计，6 份文件 / 33 个 sheet / 28,181 行**零跳过、零遗漏**（见 `scripts/audit_2020_2022.py`），且目录中"像是职位表却未被读取"的文件为 0。**不要去补那几份选调生表**——除非业主改口径。
- **年度招考人数口径**：以**全部 sheet 汇总**为准（县级以上机关 + 珠三角乡镇 + 东西两翼/北部生态发展区乡镇机关等所有表都要计入），不得只用单一 sheet 汇总。逐年合计：11871 / 13309 / 15422 / 18258 / 17307 / 17419 / 11779（合计 105365）。
- **表头行定位**：`find_header_row()` 会排除以「报考条件/配套措施/附件」开头的说明行，并优先选择含「录用人数/招考单位/招录主管部门/职位代码/考区」等强表头信号的行。乡镇子表（本市/本县大专以上、专项人员）的说明行正文里含"应届硕士…"字样，历史上会被误判为表头，导致整张子表提取为空 —— 修改该函数时必须保留这两条约束。
- **地域维度**：地域（城市）维度数据同样来自全部 sheet；学历分组从数据动态取得（`getEduLabels()`），不要再在图表里硬编码分组列表。
- **地图 GeoJSON**：优先使用本地缓存 `data/guangdong_geojson.json`、离线可重建；缺失时才联网并把结果落盘。需要刷新地图时删掉缓存文件再跑一次。
- **已删除、不要重新引入**：`data/major_ranking.json`（旧口径孤立残留：10 文件 / 71296 行 / 1550 专业，无任何看板或生成器读取）；`scripts/fix/`（8 个一次性源码字符串替换补丁，其中 6 个指向早已不维护的土木 HTML）。
- **`不限专业：服务基层/退役士兵专岗`（code=`SPECIAL-SR`）**：由 `extract_all_majors.py` **脚本内确定性构造**，识别规则为「其他要求」含 `服务基层项目人员和退役大学生士兵` 的职位，加上 2020-2022 的乡镇「专项人员」表。⚠️ 该条目**历史上靠人工改 JSON 注入**，重跑提取即丢失、且因文件曾被 `.gitignore` 忽略而从 git 看不出丢失（已发生一次事故）。**不要再手工改 JSON**；如需调整口径，改脚本并同步更新 `data/all_majors_ranking.json`。当前脚本口径为 1875 职位 / 3441 人，与原人工 patch（1828 / 3346）相差 47 职位 / 95 人，差异集中在 2020-2023，待业务确认。
- **仓库忽略规则**：`.gitignore` 忽略 `__pycache__/`、`.agents/`、`.superpowers/`、`*.pdf`、`*.prev`、`*.ref`、`.clean-checkout-test/`，以及 `data/guangdong_geojson.json`（纯缓存）与 `data/_before_city_data.json`（本地对比快照）。**`data/all_majors_ranking.json` 与 `data/city_data.json` 有意纳入版本控制** —— 看板内嵌数据必须与它们一致，且它们的存在是本项目「可复现、可审核」的前提（见上一条事故）。`scripts/`、`docs/`、`.claude/` 正常纳入版本控制。
- **可复现性验证**：`scripts/test_clean_checkout.py` 用 `git worktree` 导出当前 HEAD 到干净检出，在其中跑完整管线并核对 24 项断言（含深比对、整条流水线逐字节确定性、以及 4 条"防漏表"断言）。改动提取/生成脚本后请务必跑一次。
- **看板行为验证（两层，缺一不可）**：① `node scripts/test_major_city_input.js` —— 自制 DOM/ECharts 桩执行看板真实内联 JS，快、无需浏览器，能抓 JS 逻辑与接线；**但它没有 CSS 级联、也没有真实输入管线**，所以 `style.display=''`、`mousedown/change` 时序、输入法组合态这类问题它一律看不见（曾因此漏掉"候选面板 CSS 默认 display:none + 内联置空 → 真实浏览器里下拉永不出现"，桩里全绿）。② `node scripts/e2e_major_city.mjs` —— 用 Chrome DevTools Protocol 驱动本机已装的 Edge（**零 npm 依赖**，Node 22+ 自带 WebSocket/fetch），真实键鼠 + 真实 computed style/布局盒 + 逐屏截图 + 页面异常捕获。**改看板 HTML/CSS/内联 JS 后跑 ②**；环境不具备（无浏览器 / CDP 起不来 / Node<22）会打印 `SKIP` 并以 0 退出，可安全进 CI。**前提：沙箱不得限制浏览器的进程间通信 —— 文件策略需为 `danger-full-access`；受限模式下 Chromium 会 `mojo ... 拒绝访问` 直接 FATAL。**
- **禁止硬编码绝对路径**：所有脚本的项目根目录必须由 `__file__` 推导（`os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))`）。历史上多个脚本写死 `C:/Users/YANG/Desktop/...`，导致无法在其它机器或干净检出复现。
- 提取脚本解析 `.xls` 依赖 `xlrd`；不要改动 `data/*.xls` 原始文件。
