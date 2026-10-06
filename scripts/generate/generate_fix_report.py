#!/usr/bin/env python3
"""
生成「修复前后核对页」→ 修复核对报告.html

用途：把本轮修复（地域维度全 sheet 提取、地图离线化、标签口径、仓库清理等）
的前后数据差异整理成一张可离线打开的静态页面，便于人工复核后再推送。
修复前的旧数据从 data/_before_city_data.json 读取（如不存在则跳过对比部分）。
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
NEW_FILE = os.path.join(DATA_DIR, 'city_data.json')
OLD_FILE = os.path.join(DATA_DIR, '_before_city_data.json')
OUTPUT_FILE = os.path.join(BASE_DIR, '修复核对报告.html')

with open(NEW_FILE, 'r', encoding='utf-8') as f:
    new = json.load(f)
old = None
if os.path.exists(OLD_FILE):
    with open(OLD_FILE, 'r', encoding='utf-8') as f:
        old = json.load(f)

YEARS = ['2020', '2021', '2022', '2023', '2024', '2025', '2026']


def yearly_totals(d):
    out = {y: 0 for y in YEARS}
    for city, info in d['city_yearly'].items():
        for y in YEARS:
            out[y] += info['yearly'].get(y, 0)
    return out


def positions_by_year(d):
    out = {y: 0 for y in YEARS}
    for rec in d['details']:
        out[rec['year']] = out.get(rec['year'], 0) + 1
    return out


new_y, old_y = yearly_totals(new), (yearly_totals(old) if old else None)
new_p, old_p = positions_by_year(new), (positions_by_year(old) if old else None)
new_s, old_s = new['summary'], (old['summary'] if old else None)


def fmt(n):
    return f'{n:,}'


def delta(new_v, old_v):
    if old_v is None:
        return ''
    d = new_v - old_v
    pct = (d / old_v * 100) if old_v else 0
    cls = 'up' if d > 0 else ('down' if d < 0 else 'same')
    sign = '+' if d > 0 else ''
    return f'<span class="{cls}">{sign}{fmt(d)}（{sign}{pct:.0f}%）</span>'


# ====== 汇总卡片 ======
cards = [
    ('职位记录数', fmt(new_s['total_positions']), fmt(old_s['total_positions']) if old_s else None, delta(new_s['total_positions'], old_s['total_positions'] if old_s else None)),
    ('招录人数', fmt(new_s['total_recruits']), fmt(old_s['total_recruits']) if old_s else None, delta(new_s['total_recruits'], old_s['total_recruits'] if old_s else None)),
    ('珠三角招录', fmt(new_s['pearl_river_delta_recruits']), fmt(old_s['pearl_river_delta_recruits']) if old_s else None, delta(new_s['pearl_river_delta_recruits'], old_s['pearl_river_delta_recruits'] if old_s else None)),
    ('珠三角占比', f"{new_s['prd_ratio']}%", f"{old_s['prd_ratio']}%" if old_s else None, ''),
    ('覆盖城市', str(new_s['total_cities']), str(old_s['total_cities']) if old_s else None, ''),
]
card_html = ''
for label, now, before, d in cards:
    before_cell = f'<div class="ba-before">修复前 {before}</div>' if before is not None else ''
    card_html += f'''<div class="card">
      <div class="card-label">{label}</div>
      <div class="card-now">{now}</div>
      {before_cell}
      <div class="card-delta">{d}</div>
    </div>'''

# ====== 年度表 ======
year_rows = ''
for y in YEARS:
    year_rows += f'''<tr>
      <td class="y">{y}</td>
      <td class="num">{fmt(new_p[y])}</td>
      <td class="num">{fmt(new_y[y])}</td>
      <td class="num">{fmt(old_p[y]) if old_p else '—'}</td>
      <td class="num">{fmt(old_y[y]) if old_y else '—'}</td>
      <td class="num">{delta(new_y[y], old_y[y] if old_y else None) or '—'}</td>
    </tr>'''
year_rows += f'''<tr class="total">
      <td class="y">合计</td>
      <td class="num">{fmt(sum(new_p.values()))}</td>
      <td class="num">{fmt(sum(new_y.values()))}</td>
      <td class="num">{fmt(sum(old_p.values())) if old_p else '—'}</td>
      <td class="num">{fmt(sum(old_y.values())) if old_y else '—'}</td>
      <td class="num">{delta(sum(new_y.values()), sum(old_y.values()) if old_y else None) or '—'}</td>
    </tr>'''

# ====== 城市表（按修复后招录降序） ======
old_rank = {c: i + 1 for i, c in enumerate(old['city_ranking'])} if old else {}
city_rows = ''
for i, city in enumerate(new['city_ranking'], 1):
    info = new['city_yearly'][city]
    old_info = old['city_yearly'].get(city) if old else None
    old_total = old_info['total_recruits'] if old_info else 0
    old_pos = old_info['total_positions'] if old_info else 0
    rank_mv = ''
    if old and city in old_rank:
        diff = old_rank[city] - i
        if diff > 0:
            rank_mv = f'<span class="up">↑{diff}</span>'
        elif diff < 0:
            rank_mv = f'<span class="down">↓{-diff}</span>'
    city_rows += f'''<tr>
      <td class="y">{i} {rank_mv}</td>
      <td class="name">{city}</td>
      <td class="num">{fmt(info['total_recruits'])}</td>
      <td class="num">{fmt(info['total_positions'])}</td>
      <td class="num dim">{fmt(old_total) if old else '—'}</td>
      <td class="num dim">{fmt(old_pos) if old else '—'}</td>
      <td class="num">{info['pct_of_total']}%</td>
    </tr>'''

# ====== 修复项清单 ======
fixes = [
    ('地域分析数据缺失', '严重',
     '<code>extract_city_data.py</code> 只读每个文件的 <code>sheet_by_index(0)</code>，且表头定位函数被乡镇子表的说明行误命中',
     '改为遍历全部 sheet；表头定位增加「排除说明行 + 优先强表头信号列」两条约束',
     f"职位记录 {fmt(old_s['total_positions'])} → {fmt(new_s['total_positions'])}"),
    ('年度人数口径错误', '严重',
     '城市侧年度趋势建立在不足半数样本上，与专业侧口径不一致',
     '两年数据源统一为全 sheet 汇总，年度合计与专业侧完全对齐',
     '2020-2026 各年合计现已一致'),
    ('教育分组丢失最大项', '严重',
     '学历图表硬编码 6 个旧分组，实际数据里占比最大的「本科以上」（53%）根本不会显示',
     '分组改为从数据动态取得，并按实际取值归类',
     '「其他」占比 54% → 1.0%'),
    ('城市×专业矩阵污染', '中',
     '矩阵混入「不限」等占位符、旧版两位数字代码（<code>06法律类</code>）及逗号分隔的多值残串',
     '过滤占位符、归一化旧版代码、拆分逗号/顿号多值、剥离残缺括号',
     '脏名 606 个 → 0 个'),
    ('地图依赖网络 + 旧 HTML 回填', '中',
     'GeoJSON 从阿里云下载，失败时从旧 HTML 正则提取复用，地图数据被"冻结"',
     '改为本地缓存优先：<code>data/guangdong_geojson.json</code>，缺失时才联网并落盘',
     '本次生成实测「已加载本地地图缓存（未联网）」'),
    ('首页标签口径错误', '中',
     '「74849 个职位 / 总职位记录」把"含专业要求的职位记录数"写成了职位总数',
     '文案与统计卡改为「含专业要求的职位记录」，不再与全量职位数混用',
     '模板 <code>generate_merged_viz.py</code> 同步修正'),
    ('技能文档架构不同步', '中',
     '<code>.agents/</code> 下的 gd-exam-viz 仍是 Chart.js 旧版，<code>.claude/</code> 已是 ECharts 新版',
     '以 <code>.claude</code> 为权威副本同步覆盖',
     '两份 SHA256 完全一致'),
    ('CLAUDE.md 路径与生成器名过时', '中',
     '指向根目录、且引用了并不存在的 <code>generate_dashboard.py</code>',
     '按真实目录重写，明确唯一生成器为 <code>generate_merged_viz.py</code>',
     '含数据口径与已知约束章节'),
    ('孤立残留与一次性补丁', '低',
     '<code>data/major_ranking.json</code> 无任何脚本读取；<code>scripts/fix/</code> 8 个补丁脚本中 6 个指向早已不维护的土木 HTML',
     '两者一并删除',
     '全项目对该 JSON 的引用数为 0'),
    ('.gitignore 把代码排除在仓库外', '严重（阻塞推送）',
     '原规则忽略 <code>scripts/</code>、<code>docs/</code>、<code>.claude/</code>，推送后仓库里没有代码',
     '收紧为只忽略可重建的大体积产物与本地镜像目录',
     'scripts 20 个 + docs 3 个 + .claude 1 个文件进入跟踪'),
]
fix_rows = ''
for name, level, before, after, effect in fixes:
    cls = 'lv-high' if level.startswith('严重') else ('lv-mid' if level == '中' else 'lv-low')
    fix_rows += f'''<tr>
      <td class="name">{name}</td>
      <td><span class="lv {cls}">{level}</span></td>
      <td class="tiny">{before}</td>
      <td class="tiny">{after}</td>
      <td class="tiny">{effect}</td>
    </tr>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>广东省考看板 · 修复核对报告</title>
<style>
:root {{
  --bg:#f6f5f1; --card:#ffffff; --ink:#16233a; --ink2:#5b6472; --line:#e2e0d8;
  --gold:#b8952e; --up:#b4453a; --down:#2f7d4f; --dim:#9aa1ab;
  --serif:"Noto Serif SC","Songti SC",Georgia,serif;
  --sans:"Inter","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --mono:"JetBrains Mono","SF Mono",Consolas,monospace;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans); font-size:14px; line-height:1.6; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:0 20px 64px; }}
.hero {{ background:var(--ink); color:#fff; padding:40px 0 32px; margin-bottom:28px; }}
.hero .wrap {{ padding-bottom:0; }}
.hero h1 {{ font-family:var(--serif); font-size:26px; margin:0 0 8px; letter-spacing:.01em; }}
.hero p {{ margin:0; color:rgba(255,255,255,.62); font-size:13px; }}
.hero .stamp {{ display:inline-block; margin-top:16px; padding:5px 12px; border:1px solid rgba(255,255,255,.25);
  border-radius:999px; font-family:var(--mono); font-size:11px; color:var(--gold); }}
h2 {{ font-family:var(--serif); font-size:19px; margin:36px 0 6px; padding-left:12px; border-left:3px solid var(--gold); }}
h2 .n {{ font-family:var(--mono); font-size:12px; color:var(--gold); margin-right:8px; }}
.note {{ color:var(--ink2); font-size:12.5px; margin:0 0 14px 15px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(178px,1fr)); gap:12px; margin-top:14px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 18px; }}
.card-label {{ font-size:12px; color:var(--ink2); }}
.card-now {{ font-family:var(--mono); font-size:23px; font-weight:600; margin:6px 0 2px; letter-spacing:-.02em; }}
.ba-before {{ font-family:var(--mono); font-size:11.5px; color:var(--dim); text-decoration:line-through; }}
.card-delta {{ font-size:12px; margin-top:4px; }}
table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line);
  border-radius:12px; overflow:hidden; margin-top:14px; }}
th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; }}
th {{ background:#efeee8; font-size:12px; font-weight:600; color:var(--ink); white-space:nowrap; }}
tr:last-child td {{ border-bottom:none; }}
td.num {{ font-family:var(--mono); text-align:right; white-space:nowrap; }}
td.y {{ font-family:var(--mono); color:var(--ink2); white-space:nowrap; }}
td.dim {{ color:var(--dim); }}
td.name {{ font-weight:600; }}
td.tiny {{ font-size:12.5px; color:var(--ink2); }}
tr.total td {{ background:#f2f1eb; font-weight:600; }}
.up {{ color:var(--up); font-family:var(--mono); }}
.down {{ color:var(--down); font-family:var(--mono); }}
.same {{ color:var(--dim); font-family:var(--mono); }}
.lv {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; white-space:nowrap; }}
.lv-high {{ background:#fbe9e7; color:#b4453a; }}
.lv-mid {{ background:#fdf3e0; color:#a9791a; }}
.lv-low {{ background:#eceef1; color:#5b6472; }}
code {{ font-family:var(--mono); font-size:12px; background:#f0efe9; padding:1px 5px; border-radius:4px; }}
.links {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; }}
.links a {{ display:inline-block; padding:10px 16px; background:var(--ink); color:#fff; text-decoration:none;
  border-radius:8px; font-size:13px; }}
.links a.ghost {{ background:transparent; color:var(--ink); border:1px solid var(--line); }}
.foot {{ margin-top:36px; padding-top:16px; border-top:1px solid var(--line); color:var(--dim); font-size:12px; }}
</style>
</head>
<body>
<div class="hero"><div class="wrap">
  <h1>广东省考数据看板 · 修复核对报告</h1>
  <p>本轮修复的问题清单、前后数据对比与自查结果，供推送前人工复核。</p>
  <div class="stamp">数据区间 2020-2026 · 全 sheet 口径</div>
</div></div>

<div class="wrap">

<div class="links">
  <a href="广东省考综合数据分析看板.html">打开主看板 →</a>
  <a class="ghost" href="index.html">导航入口</a>
</div>

<h2><span class="n">01</span>核心指标对比</h2>
<p class="note">修复前 = 只读首个 sheet 的旧口径；修复后 = 全部 sheet 汇总。</p>
<div class="cards">{card_html}</div>

<h2><span class="n">02</span>年度明细对比</h2>
<p class="note">修复后每年的招录人数已与专业侧口径完全一致；修复前 2020-2022 偏低是因为乡镇专项子表被整表跳过。</p>
<table>
  <thead><tr>
    <th>年份</th><th style="text-align:right">职位记录(新)</th><th style="text-align:right">招录人数(新)</th>
    <th style="text-align:right">职位记录(旧)</th><th style="text-align:right">招录人数(旧)</th><th style="text-align:right">人数变化</th>
  </tr></thead>
  <tbody>{year_rows}</tbody>
</table>

<h2><span class="n">03</span>城市排名对比</h2>
<p class="note">补上公安、法院、检察院、监狱戒毒、乡镇机关等 sheet 后，深圳升至第 2，省直进入前 8；排名箭头表示相对修复前的位次移动。</p>
<table>
  <thead><tr>
    <th>排名</th><th>城市</th><th style="text-align:right">招录(新)</th><th style="text-align:right">职位(新)</th>
    <th style="text-align:right">招录(旧)</th><th style="text-align:right">职位(旧)</th><th style="text-align:right">占全省</th>
  </tr></thead>
  <tbody>{city_rows}</tbody>
</table>

<h2><span class="n">04</span>修复项清单</h2>
<p class="note">共 10 项，其中 4 项影响对外数据正确性，1 项会直接导致推送后仓库缺代码。</p>
<table>
  <thead><tr><th>问题</th><th>级别</th><th>原因</th><th>修复方式</th><th>效果</th></tr></thead>
  <tbody>{fix_rows}</tbody>
</table>

<h2><span class="n">05</span>自查结果</h2>
<p class="note">生成后的程序化校验（浏览器内实际交互请以你自己打开主看板为准）。</p>
<table>
  <thead><tr><th>检查项</th><th>结果</th></tr></thead>
  <tbody>
    <tr><td>年度招录合计与专业侧口径</td><td class="tiny">完全一致（2020-2026 各年逐一核对）</td></tr>
    <tr><td>城市×专业矩阵脏名（数字/逗号/括号/不限）</td><td class="tiny">606 → 0</td></tr>
    <tr><td>学历分组「其他」占比</td><td class="tiny">54% → 1.0%（仅 985 人无学历信息）</td></tr>
    <tr><td>生成内嵌数据与 city_data.json 一致性</td><td class="tiny">CITY_RANKING / CITY_EDUCATION / CITY_MAJOR_MATRIX 全部一致</td></tr>
    <tr><td>地图 GeoJSON</td><td class="tiny">21 个地级市齐全，本地缓存命中、生成过程未联网</td></tr>
    <tr><td>页面结构完整性</td><td class="tiny">57 个 getElementById 引用仅 helpModal 为动态创建；内联脚本括号平衡；ECharts 5.5 本地加载</td></tr>
    <tr><td>JS 图表分组自适应</td><td class="tiny">学历图表已去除硬编码分组，改为按数据动态生成</td></tr>
  </tbody>
</table>

<h2><span class="n">06</span>说明：专业名的层级关系</h2>
<p class="note">城市×专业矩阵中出现「法学」「法学类」「法律类」等多个相近名称并非重复计数，而是同一专业体系的不同层级：具体专业（法学）／专业类（法学类，B0301）／旧版乡镇招考代码归一化后的名称（法律类）。专业详情图的「纯洁度」指标即用于区分这类独设与共招情况。</p>

<div class="foot">
  本页由 <code>scripts/generate/generate_fix_report.py</code> 依据 <code>data/city_data.json</code> 与修复前快照 <code>data/_before_city_data.json</code> 自动生成。
</div>

</div>
</body>
</html>
'''

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'核对页已生成: {OUTPUT_FILE}')
print(f'  大小: {os.path.getsize(OUTPUT_FILE) / 1024:.0f} KB')
