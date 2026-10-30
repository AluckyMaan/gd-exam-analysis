# 广东省考职位数据分析看板

把广东省 2020-2027 年考试录用公务员职位表（`.xls`）提取成 JSON，再生成**单页多 Tab 交互式数据看板**。

**在线看板**：https://aluckymaan.github.io/gd-exam-analysis/
**主交付物**：根目录 `广东省考综合数据分析看板.html`
**数据规模**：83,060 条职位记录（12 份职位表 / 67 张 sheet 全覆盖）· 招录 115,658 人 · 252 个专业 · 22 个城市 · 2020-2027
**协议**：MIT（见 `LICENSE`）

---

## 看板结构

三个一级导航：

| 一级导航 | 内容 |
| --- | --- |
| 专业热度分析 | 洞察总览 / Top30 排名 / 专业详情 / 关联网络 / 趋势总览 / 综合对比 |
| 地域维度分析 | 城市洞察 / 地图总览 / 城市排名 / 年度趋势 / 应往届·学历 / 专业×地域 / 城市对比 |
| **2027 年度变化** | 变化总览 / 专业变化 / 城市变化 —— 只对比最新一年与上一年：规模、应届结构、学历门槛、区域重心，以及专业与城市的增减 Top 榜 |

> 「年度变化」页的年度轴由 `generate_merged_viz.py` 的 `ALL_YEARS` 单一来源驱动；以后 2028 年数据入库时改这一处 + 两个提取脚本即可，页面的最新年份标题、KPI、图表会自动跟随。

---

## 快速开始

```bash
git clone git@github.com:AluckyMaan/gd-exam-analysis.git
cd gd-exam-analysis

pip install -r requirements.txt      # 唯一依赖：xlrd（读 .xls）
```

clone 完成后**即可直接打开看板**：所有数据、图表库、脚本都已随仓库发布，不需要先跑任何提取脚本。

```bash
# 验证环境是否可用（25 项断言，全 PASS 即正常；地图 GeoJSON 已随仓库分发，全程离线）
python scripts/test_clean_checkout.py
```

---

## 常用命令

| 目的 | 命令 |
| --- | --- |
| **改完代码后重新生成看板** | `python scripts/generate/generate_merged_viz.py` |
| 从原始 `.xls` 重算专业侧数据 | `python scripts/extract/extract_all_majors.py` |
| 从原始 `.xls` 重算地域侧数据 | `python scripts/extract/extract_city_data.py` |
| 端到端复现验证（推荐每次改动后跑） | `python scripts/test_clean_checkout.py` |
| 数据不变量 + HTML 内嵌一致性校验 | `python 上线前审核/scripts/collect_evidence.py` |
| 内联 JS 语法校验（需 Node.js） | `node scripts/qa_syntax_check.js .` |
| 重新生成另一份单专业看板 | `python scripts/generate/make_viz.py --major "材料类" --keywords "材料,高分子"` |
| 重新生成修复核对页 | `python scripts/generate/generate_fix_report.py` |
| 重新生成小红书发布图（2027 版 6 张） | `node scripts/generate_xhs_cards.mjs` |

**完整重建顺序**（从零开始，约 1-2 分钟）：

```bash
python scripts/extract/extract_all_majors.py   # → data/all_majors_ranking.json
python scripts/extract/extract_city_data.py    # → data/city_data.json
python scripts/generate/generate_merged_viz.py # → 广东省考综合数据分析看板.html
```

---

## 目录结构

```
├─ 广东省考综合数据分析看板.html   ← 主交付物（双击即可打开）
├─ index.html                     ← 导航入口（跳转到主看板）
├─ assets/echarts.min.js          ← 本地 ECharts 5.5，无 CDN 依赖
├─ data/                          ← 13 个原始 .xls + 提取出的 JSON
│   ├─ *.xls                      原始职位表与专业参考目录（数据来源）
│   ├─ all_majors_ranking.json    专业侧提取产物（242 个专业的多维指标）
│   └─ city_data.json             地域侧提取产物（22 城 × 逐年 × 专业矩阵）
├─ scripts/
│   ├─ extract/                   提取脚本：.xls → JSON
│   ├─ generate/                  生成脚本：JSON → HTML
│   ├─ test_clean_checkout.py     端到端复现测试（git worktree + 全量断言）
│   └─ qa_syntax_check.js         内联 JS 语法校验（需 Node.js）
├─ 修复核对报告.html              历史修复的前后数据对比与清单
├─ 上线前审核/                     上线前证据包（改动日志、可复跑校验、源文件副本）
├─ xhs_publish_materials/         小红书发布图与文案
├─ docs/                          历史设计与计划文档
└─ CLAUDE.md                      项目约定与「数据口径与已知约束」（重要，改动前先读）
```

---

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

生成器会把数据以 `var XXX = {...}` 形式内嵌进 HTML（单文件、离线可用）。因此
**`data/*.json` 与看板 HTML 必须保持一致** —— 只改脚本不重新生成，页面不会变。

---

## 使用这些数据前必须知道的口径

1. **数据范围：只看省考**。统计广东省考试录用公务员（省考）统一招考的职位表，**直接取自省公务员主管部门发布的官方附件**（`data/*.xls` 即官网原件）。**不含**选调优秀大学毕业生、急需紧缺专业公务员、定向港澳选拔等另行发布的招录计划。
   > 注意：不要用当年公告的"计划招考总数"来校验本看板 —— 公告口径更宽（把选调生等并行计划一起报），故 2020-2022 年本看板低于该总数（少 437 / 399 / 379），2023 年起两者一致。2020-2022 的提取已逐行审计：**28,181 行零跳过、零遗漏**（`scripts/audit_2020_2022.py`）。
2. **职位数 83,060 / 招录人数 115,658**。83,060 是全部 sheet 的职位记录数，专业侧与地域侧已相等；115,658 是全部职位的招录人数合计（按年：11871 / 13309 / 15422 / **18258** / 17307 / 17419 / 11779 / 10293）。
3. **每份职位表的每个 sheet 都要读**。同一文件内含县以上机关、公安、法院、检察院、监狱戒毒、乡镇机关等多个 sheet；2020-2023 还是**两份文件**（附件1 乡镇 + 附件2 县以上及珠三角乡镇），少读任何一份都会少统计。只读第 1 个 sheet 会漏掉约 46% 的数据。
4. **省直口径**：源表「考区」列在不同年份填报口径不同（2020-2023 对省属监狱/戒毒职位填"省直"，2024 起填监狱**实际所在地**）。因此城市归属按**单位名**归一化（"广东省 + 厅/局/委/办" → 省直），而不是直接采信"考区"。**省直 2024-2027 不是 0**（2026 年为 605 人、2027 年为 381 人）—— 改动此处前请先读 `CLAUDE.md` 与 `scripts/test_clean_checkout.py` 末尾的说明。
5. **「服务基层/退役士兵专岗」**（code=`SPECIAL-SR`）由脚本确定性构造，并已纳入版本控制。不要手工改 JSON —— 历史上手工注入过该条目，重跑提取即丢失且无法从 git 发现。
6. **历史看板**（土木、电子信息、海洋工程、汉语言、材料、地域维度、专业深度分析）是早期独立产物，仅存档、不再维护。

---

## 环境要求

| 项 | 要求 |
| --- | --- |
| Python | 3.8+（开发环境为 3.12） |
| 第三方库 | 仅 `xlrd>=2.0`（见 `requirements.txt`） |
| Node.js | 可选：`qa_syntax_check.js`、`test_major_city_input.js`、`e2e_major_city.mjs` 需要（E2E 需 Node 22+，浏览器用本机 Edge） |
| 操作系统 | 无平台限制（脚本内不写死绝对路径，项目根目录由 `__file__` 推导） |
| 网络 | 默认**不需要**：地图 GeoJSON 已随仓库分发（`data/guangdong_geojson.json`）。只有主动删掉该缓存、想从上游刷新地图时才需要联网 |

---

## 已知限制

- **浏览器渲染的自动化覆盖范围有限**：`node scripts/e2e_major_city.mjs`（CDP 驱动本机 Edge，零 npm 依赖）已覆盖「专业×地域」的真实键鼠输入、候选面板真实可见性与桌面/移动布局，并捕获页面异常与控制台 error。其余 Tab 的视觉效果仍需人工打开看板确认（重点：首屏、「应往届·学历」）。
- `xhs_publish_materials/` 下有两套图：`2027/`（最新，6 张 1080×1440 竖版海报，由 `node scripts/generate_xhs_cards.mjs` 从 `data/*.json` 实时生成，零 npm 依赖，需要本机 Edge）与根目录 9 张 2026-07-20 的历史截图（数字已过时，仅存档）。旧的 playwright 版脚本 `scripts/capture_xhs_materials.mjs` 仍保留，但已不是推荐路径。
- 仅 `data/_before_city_data.json`（生成修复核对页用的历史快照）被 `.gitignore` 忽略、不随仓库分发；它不影响看板的生成与打开。地图缓存 `data/guangdong_geojson.json` 已纳入版本控制（保证全新克隆离线可复现）。
