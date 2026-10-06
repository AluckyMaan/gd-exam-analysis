# 上线前审核包

本目录是广东省考数据看板**上线（推送到 GitHub）前的自包含交付物与证据包**，供另一位 agent 独立复核。

- **审核对象**：`广东省考综合数据分析看板.html`（主交付物）
- **待推送基线**：`origin/main`（= 提交 `db77980`）→ `HEAD`，共 **5 个提交**
- **生成时间**：2026-07-28
- **生成环境**：Windows / Python 3.12（xlrd）／ Node v24；**沙箱内无法启动浏览器**，故浏览器渲染未经自动化验证（见文末「已知局限」）

---

## 1. 复核者应先建立的独立事实

不要直接采信本包的任何结论。建议先自己算出下面 4 个数字，再与 `evidence.json` 比对：

| 待独立求证的量 | 怎么算 | 期望值 |
| --- | --- | --- |
| 2020-2026 全省招录人数 | 遍历 `data/*.xls` 的**全部 sheet**，对「录用人数 > 0」的行求和 | 11871 / 13309 / 15422 / 14857 / 17307 / 17419 / 11779，合计 **101,964** |
| 地域侧招录总人数 | 累加 `data/city_data.json` 的 `city_yearly[*].yearly` | **101,964**（应与上一条逐年、总计都完全相等） |
| 地域侧职位记录数 | `city_data.json` 的 `summary.total_positions` | **73,353** |
| 专业侧「含专业要求职位数」 | `all_majors_ranking.json` 的 `summary.total_position_rows` | **74,849**（≠ 上一条，口径不同，说明见 §5） |

**关键自洽点**：上表前两行必须**逐年、总计都完全相等**（101,964）。这正是本轮修复的核心 —— 修复前地域侧只有 46,765，与专业侧口径对不上。若复核者的独立求和与 `city_data.json` 出现任何年度差异，即说明地域侧提取仍有漏表。

> 计数口径提示：求和时应只统计「录用人数 > 0」的**数据行**，并排除表头、标题行与说明行。各源文件的表头位置不同（0-4 行不等），且乡镇子表的说明行正文里含"应届硕士、博士研究生…"字样，容易被误当成表头 —— 这正是原代码踩的坑（见 §4-B）。

---

## 2. 目录结构

```
上线前审核/
├─ README.md                        ← 本文件
├─ 广东省考综合数据分析看板.html      ← 主交付物（与项目根目录同名文件一致；双击即可打开）
├─ assets/echarts.min.js            ← 上述 HTML 依赖的本地图表库（保证副本可独立打开）
├─ 修复核对报告.html                 ← 18 项修复清单 + 前后数据对比 + 自查结果
├─ 改动日志.md                       ← 由 git 历史自动生成，逐提交明细
├─ git-history.txt                   ← git log --stat 原始输出（完整文件清单）
├─ evidence.json                     ← 机器可读的全部断言与实测值（含文件 SHA256）
├─ inline-script.js                  ← 从看板 HTML 抽出的内联脚本，供独立语法校验
├─ scripts/
│  ├─ collect_evidence.py           ← 重算全部数据不变量（仅标准库）
│  ├─ gen_changelog.py              ← 由 git 历史重新生成改动日志
│  └─ qa_syntax_check.js            ← Node 侧：编译校验 + 12 项机器核对
└─ source/                           ← 本轮改动过的源文件副本（权威版本在项目根目录）
   ├─ scripts/extract/extract_city_data.py     ★ 核心修复
   ├─ scripts/generate/generate_merged_viz.py  ★ 核心修复（含 HTML 模板）
   ├─ scripts/generate/gviz_common.py          ★ 表头定位修复
   ├─ CLAUDE.md、.gitignore、.claude/skills/...  文档与仓库规则
   └─ …（完整清单见 改动日志.md）
```

`source/` 是**副本**（不含两份 HTML 与 `data/*.json`），权威版本在项目根目录。若两者不一致，以 git 提交为准。

---

## 3. 复跑校验（3 条命令）

```bash
# ① 数据不变量 + HTML 内嵌一致性（18 + 11 项断言）
python 上线前审核/scripts/collect_evidence.py

# ② 内联脚本语法（只编译不执行）+ 机器核对
node 上线前审核/scripts/qa_syntax_check.js .          # 在项目根目录执行

# ③ 产物是否可复现（可选：会覆盖看板 HTML，注意先备份）
python scripts/generate/generate_merged_viz.py         # 需 data/ 下两个 JSON 存在
```

- ① 应输出 **18 项数据不变量 + 11 项 HTML 校验全部 PASS**，并打印修复前后对比（职位 38,099 → 73,353）
- ② 应输出 `SYNTAX OK`（约 221 万字符）与 12 项 `PASS`
- ③ 重新生成后看板 HTML 的 **SHA256 应与 `evidence.json` 的 `paths.看板 HTML.sha256` 一致**（生成过程确定性，地图走本地缓存不联网）

---

## 4. 本轮改了什么（按严重度）

完整清单见 `修复核对报告.html` 的「04 修复项清单」（18 项）。最需要复核的是这 5 条：

### 🔴 A. 地域维度只覆盖 54% 数据（数据正确性）
`scripts/extract/extract_city_data.py` 原先只读 `wb.sheet_by_index(0)`，而每个源文件有 4-7 个 sheet（公安/法院/检察院/监狱戒毒/乡镇机关/珠三角乡镇/乡镇专项子表）。修复后遍历全部 sheet。

**复核方法**：对比 `evidence.json` 的 `before_after`。旧快照在 `data/_before_city_data.json`。

### 🔴 B. 表头行定位被说明行误命中（隐藏更深的一层根因）
`gviz_common.py` 的 `find_header_row()` 原先用「含『专业』且含『名称/代码』」判断，会被乡镇子表的说明行命中 —— 该行正文含"2020年应届硕士、博士研究生…"，导致 2020-2022 的 `本市大专以上 / 本县大专以上 / 专项人员` 三张子表**整表提取为空**。

**复核方法**：查看 `data/附件1：广东省东西两翼地区和北部生态发展区乡镇机关2020年招录公务员职位表.xls`，其 sheet[1]（本市大专以上）的第 1 行是说明行、第 3 行才是真表头；用旧逻辑 `find_header_row` 会返回 1，用新逻辑应返回 3。

### 🔴 C. ECharts 从 CDN 加载 → 离线/被墙时整站图表打不开
模板原先引用 `cdn.jsdelivr.net`，已改回本地 `assets/echarts.min.js`（同版本 5.5.0）。

**复核方法**：`grep -n "echarts" 广东省考综合数据分析看板.html`，确认只有 `assets/echarts.min.js`，无 CDN。同时确认仓库内存在 `assets/echarts.min.js`（约 1MB）。

### 🔴 D. 两个默认首屏完全不渲染
`renderMajorOverview()` / `renderCityOverview()` 原先**只被 `needsRefresh` 引用、无任何调用点**，而它们对应的 `m-tab0`（专业「洞察总览」）与 `c-tab0`（「城市洞察」）正是两个一级 Tab 的默认页 → 首屏空白。

**复核方法**：在 `inline-script.js` 中搜索 `renderMajorOverview`，确认存在 `initOpeningViews()` 调用它；并在浏览器打开看板确认首屏直接有内容。

### ⚠️ E. 一条被推翻的审查结论（请勿据此修改）
上一轮独立审查报告曾提出「S2：8 个专业在城市矩阵全为 0，点进去必然空图」，并给出 `不限专业 rank 2 / 14,435 人 / 0 城` 等数字。**经实测不成立**：

- `ALL_MAJORS` 中「所有城市都为 0」的专业数为 **0**（矩阵只存 `n>0` 的键，这类项在结构上无法存在）
- `不限专业`、`（旧版乡镇招考代码）` 等**不在**城市矩阵中（构建矩阵时已过滤占位符与旧代码）
- 该审查误将**专业侧排名**的数字当成了城市矩阵的键

`collect_evidence.py` 中已加入对应断言（「矩阵每个专业名至少命中 1 个城市（不存在全零项）」）。若复核者认同原结论，请先复现出「全零专业」再行动。

---

## 5. 口径说明（容易误判为 bug 的三处）

1. **74,849 ≠ 73,353**：前者=含专业要求的职位记录数（专业侧，用于专业排名）；后者=全部 sheet 的职位记录数（地域侧，含"专业不限"职位）。两者统计对象不同，页面内未混用，帮助弹窗已说明。
2. **「法学 / 法学类 / 法律类」并存**：分别是具体专业 / 专业类（B0301）/ 旧版乡镇代码归一化后的名称，属同一体系的不同层级，非重复计数（专业详情图的「纯洁度」即区分独设与共招）。
3. **「本科以上」与「本科」**：两档并列的最低学历门槛，互不重叠；「其他」为源表未标注学历的记录（约 1.0%）。

---

## 6. 已知局限（请重点人工确认）

| 项 | 状态 |
| --- | --- |
| 浏览器内实际渲染 | **未自动验证**（沙箱内 Edge 无法启动子进程）。请人工打开看板，重点看：首屏是否直接有内容、「应往届·学历」Tab、「专业×地域」Tab |
| `xhs_publish_materials/` 9 张配图 | **已过时**：仍是旧城市数据（深圳未升至第 2、珠三角占比仍是 37.9%），发布前需重截。本次未纳入审核包的 source 副本 |
| Google Fonts | 仍是唯一外部依赖（3 处），CSS 已配 `PingFang SC` / `Microsoft YaHei` / `STSong` 中文回退，被阻断仅字形降级 |
| 渲染函数 `resize()` | 13 个渲染函数未逐个补 `resize()`，依赖 Tab 切换后 100ms 的 `resizeAll()` 兜底（实测可用，属结构技术债，本次有意未改） |
| `scripts/fix/` 与 `data/major_ranking.json` | 已删除。前者是 8 个一次性补丁（6 个指向已废弃的土木 HTML），后者无任何脚本引用。删除记录见 `改动日志.md` |
| 3 个大 JSON 移出 git 跟踪 | `all_majors_ranking.json`、`city_data.json`、`guangdong_geojson.json` 已在 `.gitignore` 中（可重建产物）。磁盘文件保留；若线上 Pages 需直接取用，需加回跟踪 |

---

## 7. 给复核者的建议顺序

1. 跑 `collect_evidence.py`，确认 18+11 项断言与 `evidence.json` 一致
2. 跑 `qa_syntax_check.js`，确认 `SYNTAX OK`
3. 用 `inline-script.js` 搜索 §4 的 A-D 四处修复是否真实存在（而非只是文档声称）
4. 读 `source/scripts/extract/extract_city_data.py` 与 `source/scripts/generate/gviz_common.py`，确认多 sheet 遍历与表头判定逻辑
5. 在浏览器打开看板，人工确认首屏与两个被改动的 Tab
6. 如与结论不符，以 `evidence.json` 的实测值与 git 提交为准，并记录差异

**待推送命令**（复核通过后执行）：
```bash
git push -u origin main
```
