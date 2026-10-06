"""Generate the electronics engineering page with editorial treasury layout + data narrative + charts."""
import json
import os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
d = json.load(open(os.path.join(_BASE, 'data', 'electronics_data.json'), encoding='utf-8'))
details = d['details']

items = []
for item in details:
    y = item["year"]
    u = item["unit"].replace("\\", "\\\\").replace('"', '\\"')
    p = item["position"].replace("\\", "\\\\").replace('"', '\\"')
    n = item["recruits"]
    c = item["city"].replace("\\", "\\\\").replace('"', '\\"')
    e = item["education"].replace("\\", "\\\\").replace('"', '\\"')
    f = "true" if item["fresh_only"] else "false"
    ft = item.get("fresh_type", "social")
    pr = item.get("prof_fields", "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    items.append(
        f'{{"y":"{y}","u":"{u}","p":"{p}","n":{n},"c":"{c}","e":"{e}","f":{f},"ft":"{ft}","pr":"{pr}"}}'
    )
all_pos_js = "var ALL_POSITIONS = [\n" + ",\n".join(items) + "\n];"

ys = d['yearly_summary']
years_sorted = sorted(ys.keys())

# Precompute all data arrays
year_labels = '","'.join(years_sorted)
total_recruits_arr = [str(ys[y]['total_recruits']) for y in years_sorted]
total_positions_arr = [str(ys[y]['total_records']) for y in years_sorted]
fresh_recruits_arr = [str(ys[y]['fresh_recruits']) for y in years_sorted]
fresh_current_arr = [str(ys[y]['fresh_current_recruits']) for y in years_sorted]

# City data
city_data = d['city_summary']
cities_sorted = sorted(city_data.items(), key=lambda x: sum(x[1].values()), reverse=True)
city_names_js = '","'.join([c for c, _ in cities_sorted])
city_totals_js = ','.join([str(sum(v.values())) for _, v in cities_sorted])

# Education data - precompute yearly breakdown
edu_data = d['edu_summary']
edu_keys = sorted(edu_data.keys())
edu_labels_js = '","'.join(edu_keys)
edu_totals_js = ','.join([str(sum(edu_data[k].values())) for k in edu_keys])

# Education trend data (year by year, stacked)
edu_trend_datasets = []
edu_colors = ['#0f2347', '#3875b6', '#5fa8c7', '#b8952e', '#7a8b9e']
for idx, k in enumerate(edu_keys):
    yearly_data = ','.join([str(edu_data[k].get(y, 0)) for y in years_sorted])
    edu_trend_datasets.append(
        f'{{label:"{k}",data:[{yearly_data}],backgroundColor:"{edu_colors[idx % len(edu_colors)]}",borderWidth:0}}'
    )
edu_trend_js = '[' + ','.join(edu_trend_datasets) + ']'

# Fresh type summary
fs = d['fresh_summary']
total_social = sum(fs['social'].values())
total_fresh_any = sum(fs['fresh_any'].values())
total_fresh_current = sum(fs['fresh_current'].values())

# Key metrics
first_year = years_sorted[0]
last_year = years_sorted[-1]
first_total = ys[first_year]['total_recruits']
last_total = ys[last_year]['total_recruits']
growth_pct = round((last_total - first_total) / first_total * 100)
peak_year = max(years_sorted, key=lambda y: ys[y]['total_recruits'])
peak_val = ys[peak_year]['total_recruits']
total_all = sum(ys[y]['total_recruits'] for y in years_sorted)
total_pos_all = sum(ys[y]['total_records'] for y in years_sorted)

# City heatmap data
import json as _json
city_data_json = _json.dumps(city_data, ensure_ascii=False)

HTML = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省考 · 电子信息类招录趋势</title>
<style>
:root{{--navy:#0f2347;--navy-light:#1a3a6e;--navy-mid:#3875b6;--teal:#2e8b8b;--teal-soft:#e6f0f2;--gold:#b8952e;--gold-soft:#f5efdc;--gold-light:#faf6ed;--paper:#f7f5f0;--white:#fff;--border:#e3dfd6;--border-light:#edeae3;--text:#1e1e1e;--text-secondary:#6b6660;--text-tertiary:#9e9890;--positive:#2a6b4a;--positive-soft:#eaf1ec;--negative:#b8432a;--negative-soft:#f5e8e4;--radius:10px;--radius-sm:6px;--shadow:0 1px 3px rgba(0,0,0,0.05);--shadow-md:0 4px 12px rgba(0,0,0,0.06);--shadow-lg:0 8px 28px rgba(0,0,0,0.07);--sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;--serif:Georgia,"Songti SC","Noto Serif SC","Source Han Serif SC","SimSun",serif;--mono:"SF Mono",ui-monospace,"Cascadia Code","Consolas","JetBrains Mono",monospace}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--sans);background:var(--paper);color:var(--text);line-height:1.5;-webkit-font-smoothing:antialiased;padding-bottom:80px}}
.container{{max-width:1080px;margin:0 auto;padding:0 20px}}
/* Reading progress bar */
#progressBar{{position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,var(--gold),var(--navy));z-index:999;width:0%;transition:width 0.15s ease-out}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade-in{{animation:fadeUp 0.5s ease-out forwards}}
@keyframes blink{{0%,50%{{opacity:1}}51%,100%{{opacity:0}}}}
.section{{scroll-margin-top:60px}}
.section-header{{display:flex;align-items:center;gap:16px;margin-bottom:20px;padding-top:16px}}
.section-number{{font-family:var(--mono);font-size:14px;font-weight:600;color:var(--gold);letter-spacing:1px}}
.section-line{{flex:1;height:1px;background:linear-gradient(90deg,var(--gold),transparent)}}
.section-title{{font-family:var(--serif);font-size:20px;font-weight:600;color:var(--text);letter-spacing:0.5px}}
.sticky-nav{{position:sticky;top:0;z-index:100;background:rgba(247,245,240,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--border-light);padding:0 20px;display:flex;align-items:center;gap:4px;overflow-x:auto;margin-bottom:24px}}
.sticky-nav::-webkit-scrollbar{{display:none}}
.sticky-nav a{{text-decoration:none;color:var(--text-secondary);font-size:13px;font-weight:500;padding:10px 16px;white-space:nowrap;transition:color 0.2s;position:relative}}
.sticky-nav a::after{{content:"";position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:0;height:2px;background:var(--navy);transition:width 0.3s}}
.sticky-nav a:hover,.sticky-nav a.active{{color:var(--navy)}}
.sticky-nav a.active::after{{width:24px}}
/* Floating year filter bar */
.float-year-bar{{position:fixed;top:50px;left:50%;transform:translateX(-50%);z-index:99;display:flex;align-items:center;gap:4px;background:rgba(247,245,240,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border:1px solid var(--border);border-radius:28px;padding:6px 16px;box-shadow:var(--shadow-md);white-space:nowrap}}
.float-year-label{{font-size:11px;color:var(--text-tertiary);margin-right:4px;letter-spacing:0.5px}}
.float-year-btn{{padding:4px 12px;border:1px solid transparent;background:transparent;border-radius:16px;cursor:pointer;font-size:12px;font-weight:500;font-family:var(--sans);color:var(--text-secondary);transition:all 0.2s}}
.float-year-btn:hover{{border-color:var(--navy-mid);color:var(--navy)}}
.float-year-btn.active{{background:var(--navy);color:#fff;border-color:var(--navy)}}
.float-year-info{{font-size:11px;color:var(--text-tertiary);margin-left:6px;padding-left:8px;border-left:1px solid var(--border)}}
.app-bar{{display:flex;align-items:center;justify-content:space-between;padding:18px 0;margin-bottom:4px}}
.app-bar-brand{{display:flex;align-items:center;gap:10px;font-family:var(--serif);font-size:19px;font-weight:600;color:var(--text);text-decoration:none}}
.app-bar-brand svg{{width:26px;height:26px;color:var(--navy-mid)}}
.app-bar-year{{font-size:12px;color:var(--text-tertiary);border:1px solid var(--border);padding:4px 14px;border-radius:20px;font-weight:500;letter-spacing:0.5px}}
.hero-wrap{{background:var(--white);border-bottom:1px solid var(--border-light);margin-bottom:28px;position:relative;overflow:hidden}}
.hero-wrap::before{{content:"\\7535\\5b50  \\4fe1\\606f  \\62db\\5f55";position:absolute;right:-20px;top:50%;transform:translateY(-50%);font-family:var(--serif);font-size:clamp(80px,14vw,160px);font-weight:700;color:rgba(15,35,71,0.03);letter-spacing:16px;white-space:nowrap;pointer-events:none;line-height:1}}
.hero{{padding:40px 0 32px;position:relative;z-index:1}}
.hero .hero-label{{font-family:var(--mono);font-size:11px;color:var(--gold);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}}
.hero h1{{font-family:var(--serif);font-size:42px;font-weight:600;color:var(--text);line-height:1.15;margin-bottom:12px;max-width:720px}}
.hero h1 span{{color:var(--navy)}}
.hero .subtitle{{font-size:14px;color:var(--text-tertiary);letter-spacing:0.3px}}
.hero .subtitle .cursor{{display:inline-block;width:1.5px;height:1em;background:var(--navy);vertical-align:text-bottom;animation:blink 1s step-end infinite}}
.chip-group{{display:flex;flex-wrap:wrap;gap:6px;margin-top:18px}}
.chip{{display:inline-flex;align-items:center;padding:4px 13px;border:1px solid var(--border);border-radius:5px;font-size:12px;font-weight:400;color:var(--text-secondary);background:var(--paper);transition:border-color 0.2s,color 0.2s}}
.banner{{display:flex;align-items:flex-start;gap:12px;background:var(--white);border-left:3px solid var(--gold);border-radius:var(--radius-sm);padding:14px 18px;margin:20px 0;font-size:13px;color:var(--text-secondary);line-height:1.7;box-shadow:var(--shadow)}}
.banner svg{{flex-shrink:0;width:18px;height:18px;color:var(--gold);margin-top:3px}}
.banner strong{{color:var(--text)}}
.filter-bar{{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:20px;padding:10px 0}}
.filter-label{{font-size:13px;font-weight:500;color:var(--text-secondary);margin-right:8px}}
.filter-btn{{padding:6px 16px;border:1px solid var(--border);background:var(--white);border-radius:18px;cursor:pointer;font-size:12px;font-weight:500;font-family:var(--sans);color:var(--text-secondary);transition:all 0.2s;user-select:none}}
.filter-btn:hover{{border-color:var(--navy-mid);color:var(--navy)}}
.filter-btn.active{{background:var(--navy);color:#fff;border-color:var(--navy)}}
.filter-info{{margin-left:auto;font-size:12px;color:var(--text-tertiary)}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:28px}}
.stat-card{{background:var(--white);border-radius:var(--radius);padding:22px 18px;box-shadow:var(--shadow);text-align:center;position:relative;overflow:hidden;transition:box-shadow 0.3s,transform 0.25s}}
.stat-card:hover{{box-shadow:var(--shadow-md)}}
.stat-card .number{{font-family:var(--mono);font-size:30px;font-weight:600;color:var(--navy);letter-spacing:-0.5px;line-height:1}}
.stat-card .label{{font-size:13px;font-weight:500;color:var(--text);margin-top:8px}}
.stat-card .sub{{font-size:11px;color:var(--text-tertiary);margin-top:2px}}
.chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}}
.chart-card{{background:var(--white);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow);transition:box-shadow 0.3s;position:relative}}
.chart-card:hover{{box-shadow:var(--shadow-md)}}
.chart-card.full{{grid-column:1/-1}}
.chart-card .chart-title{{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--text);margin-bottom:16px;letter-spacing:0.3px;text-transform:uppercase}}
.chart-card .chart-title svg{{width:16px;height:16px;color:var(--navy-mid);flex-shrink:0}}
.chart-wrapper{{position:relative;height:300px}}
#cityChartWrapper{{height:600px}}
.chart-note{{margin-top:8px;font-size:11px;color:var(--text-tertiary);text-align:center}}
.data-table{{background:var(--white);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin-bottom:28px}}
.data-table .dt-header{{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:0.3px;padding:20px 22px 12px}}
.data-table .dt-header svg{{width:16px;height:16px;color:var(--navy-mid)}}
.data-table table{{width:100%;border-collapse:collapse;font-size:13px}}
.data-table th{{padding:11px 18px;text-align:right;font-weight:600;color:var(--text-secondary);border-bottom:1.5px solid var(--border);font-size:11px;letter-spacing:0.5px;text-transform:uppercase;font-family:var(--mono);background:var(--paper)}}
.data-table th:first-child{{text-align:left;padding-left:22px}}
.data-table th:last-child{{padding-right:22px}}
.data-table td{{padding:11px 18px;text-align:right;border-bottom:1px solid var(--border-light);color:var(--text);font-variant-numeric:tabular-nums}}
.data-table td:first-child{{text-align:left;font-weight:600;padding-left:22px}}
.data-table td:last-child{{padding-right:22px}}
.data-table tbody tr{{transition:background 0.12s}}
.data-table tbody tr:hover td{{background:var(--gold-soft)}}
.data-table tbody tr:last-child td{{border-bottom:none}}
.data-table .hl{{display:inline-block;background:var(--gold-soft);color:var(--navy);padding:2px 10px;border-radius:4px;font-weight:600;font-family:var(--mono);font-size:13px}}
.change-up{{color:var(--positive);font-weight:500}}
.change-down{{color:var(--negative);font-weight:500}}
.change-none{{color:var(--text-tertiary)}}
.heatmap-cell{{display:inline-block;padding:2px 6px;border-radius:3px;font-weight:500;font-family:var(--mono);font-size:12px}}
.year-tabs{{display:flex;gap:6px;flex-wrap:wrap;padding:0 22px 14px}}
.year-tab{{padding:5px 15px;border:1px solid var(--border);background:var(--white);border-radius:18px;cursor:pointer;font-size:12px;font-weight:500;font-family:var(--sans);color:var(--text-secondary);transition:all 0.2s}}
.year-tab:hover{{border-color:var(--navy-mid);color:var(--navy)}}
.year-tab.active{{background:var(--navy);color:#fff;border-color:var(--navy)}}
.tab-toolbar{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:0 22px 16px}}
.search-wrapper{{position:relative;flex:1;min-width:200px}}
.search-wrapper svg{{position:absolute;left:12px;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--text-tertiary);pointer-events:none}}
.search-input{{padding:7px 12px 7px 34px;border:1px solid var(--border);border-radius:18px;font-size:13px;font-family:var(--sans);color:var(--text);background:var(--paper);width:100%;transition:all 0.2s}}
.search-input:focus{{outline:none;border-color:var(--gold);background:var(--white);box-shadow:0 0 0 3px rgba(184,149,46,0.08)}}
.search-input::placeholder{{color:var(--text-tertiary)}}
.result-count{{font-size:12px;color:var(--text-tertiary);white-space:nowrap;margin-left:auto}}
.pos-table-wrap{{max-height:560px;overflow-y:auto;border-top:1px solid var(--border-light)}}
.pos-table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:12px}}
.pos-table thead{{position:sticky;top:0;z-index:2}}
.pos-table th{{background:var(--paper);padding:9px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1.5px solid var(--border);font-size:11px;font-family:var(--sans)}}
.pos-table th:nth-child(5){{text-align:right}}
.pos-table th.sortable{{cursor:pointer}}
.pos-table th.sortable:hover{{color:var(--navy)}}
.pos-table th.sortable::after{{content:" \\2195";font-size:10px;opacity:0.3}}
.pos-table th.sort-asc::after{{content:" \\2191";opacity:1;color:var(--gold)}}
.pos-table th.sort-desc::after{{content:" \\2193";opacity:1;color:var(--gold)}}
.pos-table th:nth-child(1),.pos-table td:nth-child(1){{width:8%}}
.pos-table th:nth-child(2),.pos-table td:nth-child(2){{width:8%}}
.pos-table th:nth-child(3),.pos-table td:nth-child(3){{width:22%}}
.pos-table th:nth-child(4),.pos-table td:nth-child(4){{width:32%}}
.pos-table th:nth-child(5),.pos-table td:nth-child(5){{width:7%;text-align:right}}
.pos-table th:nth-child(6),.pos-table td:nth-child(6){{width:12%}}
.pos-table th:nth-child(7),.pos-table td:nth-child(7){{width:11%}}
.pos-table td{{padding:7px 12px;border-bottom:1px solid var(--border-light);vertical-align:top;color:var(--text)}}
.pos-table td:nth-child(1),.pos-table td:nth-child(2){{white-space:nowrap}}
.pos-table td:nth-child(3),.pos-table td:nth-child(4){{word-break:break-all}}
.pos-table tbody tr{{transition:background 0.12s}}
.pos-table tbody tr:hover td{{background:var(--gold-soft)}}
.tag{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600}}
.tag-fresh{{background:var(--positive-soft);color:var(--positive)}}
.tag-social{{background:var(--negative-soft);color:var(--negative)}}
.tag-benke{{background:var(--gold-soft);color:var(--navy)}}
.tag-master{{background:#ede9f6;color:#5b4d8b}}
.tag-dazhuan{{background:#fef3e4;color:#8b7a3a}}
.pos-table .recruit-num{{font-weight:700;color:var(--navy);font-size:13px;font-family:var(--mono)}}
.footer{{text-align:center;padding:28px;color:var(--text-tertiary);font-size:12px;border-top:1px solid var(--border-light);margin-top:48px}}
.back-top{{position:fixed;bottom:92px;right:24px;width:40px;height:40px;background:var(--white);color:var(--text-secondary);border:1px solid var(--border);border-radius:50%;cursor:pointer;box-shadow:var(--shadow);opacity:0;visibility:hidden;z-index:99;display:flex;align-items:center;justify-content:center;transition:all 0.25s}}
.back-top.visible{{opacity:1;visibility:visible}}
.back-top:hover{{transform:translateY(-2px);border-color:var(--navy);color:var(--navy);box-shadow:var(--shadow-md)}}
.back-top svg{{width:18px;height:18px}}
@media(max-width:900px){{.stats-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(min-width:769px){{.mobile-only{{display:none!important}}}}
@media(max-width:768px){{
body{{padding-bottom:64px}}
.desktop-only{{display:none!important}}
.hero h1{{font-size:28px}}
.chart-grid{{grid-template-columns:1fr}}
.chart-wrapper{{height:260px}}
#cityChartWrapper{{height:400px}}
.data-table{{overflow-x:auto}}
.data-table table{{font-size:12px}}
.data-table th,.data-table td{{padding:10px 14px}}
.data-table th:first-child,.data-table td:first-child{{padding-left:16px}}
.data-table th:last-child,.data-table td:last-child{{padding-right:16px}}
.stat-card{{padding:16px}}
.stat-card .number{{font-size:24px}}
.sticky-nav{{padding:0 12px;gap:2px}}
.sticky-nav a{{font-size:12px;padding:8px 12px}}
.float-year-bar{{top:44px;padding:5px 12px;gap:3px;border-radius:24px}}
.float-year-btn{{font-size:11px;padding:3px 9px}}
.float-year-label{{display:none}}
}}
</style>
</head>
<body>
<div id="progressBar"></div>

<div class="sticky-nav">
  <a href="#overview" class="active">概览</a>
  <a href="#trend">招录趋势</a>
  <a href="#city">城市分布</a>
  <a href="#education">学历与应届</a>
  <a href="#positions">岗位明细</a>
</div>

<div class="float-year-bar" id="floatYearBar">
  <span class="float-year-label">年份</span>
  <button class="float-year-btn active" data-year="all" title="全部年份 · 共 {total_all} 人">全部</button>
  {''.join(f'<button class="float-year-btn" data-year="{y}" title="{y}年 · 共 {ys[y]["total_recruits"]} 人">{y}</button>' for y in years_sorted)}
  <span class="float-year-info" id="yearFilterInfo">全部 · {total_all} 人</span>
</div>

<div class="hero-wrap">
  <div class="container">
    <div class="app-bar">
      <a class="app-bar-brand" href="#">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 15v4c0 1.1.9 2 2 2h14a2 2 0 0 0 2-2v-4"/><polyline points="10 3 2 11 6 11 6 19 12 19 12 13 16 13 16 19 22 19 22 11 17 11"/></svg>
        广东省考电子信息类
      </a>
      <span class="app-bar-year">2020-2026</span>
    </div>
    <div class="hero">
      <div class="hero-label">Guangdong Provincial Exam</div>
      <h1><span>电子信息类</span> 及相关专业<br>招录趋势分析报告</h1>
      <div class="subtitle">涵盖 B0807 电子信息类 · A0809 电子科学与技术 · A0810 信息与通信工程 · A0840 电子信息（专硕）<span class="cursor"></span></div>
      <div class="chip-group">
        <span class="chip">电子信息工程</span>
        <span class="chip">电子科学与技术</span>
        <span class="chip">通信工程</span>
        <span class="chip">微电子科学与工程</span>
        <span class="chip">光电信息科学与工程</span>
        <span class="chip">集成电路设计与集成系统</span>
        <span class="chip">人工智能</span>
        <span class="chip">电子信息科学与技术</span>
        <span class="chip">应用电子技术</span>
      </div>
    </div>
  </div>
</div>

<div class="container">

<div class="banner" id="overview">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  <div>本报告分析 <strong>2020-2026 年广东省考</strong>中 <strong>电子信息类（B0807）</strong> 及相关专业的招录数据。涵盖本科电子信息类全部 20 个专业（电子信息工程、电子科学与技术、通信工程、微电子、光电信息、集成电路等），以及研究生层次的电子科学与技术（A0809）、信息与通信工程（A0810）和电子信息专业硕士（A0840）。共收录 <strong>{total_pos_all} 个职位</strong>，<strong>{total_all} 个招录名额</strong>，是省考中招录规模最大的专业类别之一。</div>
</div>

<div class="section" id="insights">
  <div class="section-header">
    <span class="section-number">01</span>
    <div class="section-line"></div>
    <span class="section-title">核心发现</span>
  </div>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="number">{total_all}</div>
      <div class="label">总招录人数</div>
      <div class="sub">2020-2026 合计</div>
    </div>
    <div class="stat-card">
      <div class="number">{total_pos_all}</div>
      <div class="label">总职位数</div>
      <div class="sub">7 年累计</div>
    </div>
    <div class="stat-card">
      <div class="number">{growth_pct}%</div>
      <div class="label">招录增长</div>
      <div class="sub">{first_year} → {last_year}</div>
    </div>
    <div class="stat-card">
      <div class="number">{peak_year}</div>
      <div class="label">招录峰值年</div>
      <div class="sub">{peak_val} 人</div>
    </div>
  </div>
</div>

<div class="section" id="trend">
  <div class="section-header">
    <span class="section-number">02</span>
    <div class="section-line"></div>
    <span class="section-title">招录趋势</span>
  </div>
  <div class="chart-card full" style="margin-bottom:16px">
    <div class="chart-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      历年招录人数与职位数
    </div>
    <div class="chart-wrapper"><canvas id="trendChart"></canvas></div>
    <div class="chart-note">电子信息类招录规模持续扩大，7 年间增长 {growth_pct}%，2025 年达到峰值 {peak_val} 人</div>
  </div>

  <div class="chart-grid">
    <div class="chart-card">
      <div class="chart-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
        应届 vs 社会人员
      </div>
      <div class="chart-wrapper"><canvas id="freshChart"></canvas></div>
      <div class="chart-note">当年应届（2023-2026）共 {total_fresh_current} 人，社会人员共 {total_social} 人</div>
      <div style="display:flex;align-items:flex-start;gap:8px;background:var(--teal-soft);border-radius:6px;padding:10px 14px;margin-top:10px;font-size:12px;color:var(--text-secondary);line-height:1.6">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;flex-shrink:0;margin-top:2px;color:var(--navy-mid)"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        <div><strong>电子信息类岗位特征</strong>：招录规模在省考所有专业类别中位居前列。2023 年起引入"当年应届"分类，不限应届的社会岗位仍占较大比例，为往届生提供了大量机会。</div>
      </div>
    </div>
    <div class="chart-card">
      <div class="chart-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        学历分布（总计）
      </div>
      <div class="chart-wrapper"><canvas id="eduChart"></canvas></div>
      <div class="chart-note">本科以上和研究生学历占比逐年提高，研究生需求增长显著</div>
    </div>
  </div>
</div>

<div class="section" id="city">
  <div class="section-header">
    <span class="section-number">03</span>
    <div class="section-line"></div>
    <span class="section-title">城市分布</span>
  </div>
  <div class="chart-card full" style="margin-bottom:16px">
    <div class="chart-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
      各城市招录分布（按年份堆叠）
    </div>
    <div class="chart-wrapper" id="cityChartWrapper"><canvas id="cityChart"></canvas></div>
    <div class="chart-note">每个城市按年份分色堆叠，鼠标悬停可查看每年招录明细。珠三角城市需求最为旺盛。</div>
  </div>

  <div class="chart-card full">
    <div class="chart-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
      城市 × 年份 热度矩阵
    </div>
    <div class="year-tabs" id="heatYearTabs" style="padding:0 0 12px 0"></div>
    <div class="chart-wrapper" style="height:auto;min-height:320px;overflow-x:auto">
      <table id="cityHeatTable" style="width:100%;border-collapse:collapse;font-size:13px"></table>
    </div>
    <div class="chart-note">色阶越深表示该年该城市招录人数越多。点击年份标签可筛选查看单年数据。</div>
  </div>
</div>

<div class="section" id="education">
  <div class="section-header">
    <span class="section-number">04</span>
    <div class="section-line"></div>
    <span class="section-title">学历与应届</span>
  </div>
  <div class="chart-card full" style="margin-bottom:16px">
    <div class="chart-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 14l9-5-9-5-9 5 9 5z"/><path d="M12 14l6.16-3.42a6.08 6.08 0 0 1 2.19 1.07"/><path d="M12 14l-6.16-3.42a6.08 6.08 0 0 0-2.19 1.07"/><path d="M12 14v5"/></svg>
      学历层次逐年变化
    </div>
    <div class="chart-wrapper"><canvas id="eduTrendChart"></canvas></div>
    <div class="chart-note">研究生学历需求从 2020 年的 19 人增长至 2026 年的 443 人，增幅超过 20 倍</div>
  </div>
</div>

<div class="section" id="positions">
  <div class="section-header">
    <span class="section-number">05</span>
    <div class="section-line"></div>
    <span class="section-title">岗位明细</span>
  </div>
  <div class="data-table">
    <div class="dt-header">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      可检索职位明细表
    </div>
    <div class="tab-toolbar">
      <div class="year-tabs" id="yearTabs"></div>
    </div>
    <div class="tab-toolbar">
      <div class="search-wrapper">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input class="search-input" id="posSearch" placeholder="搜索单位、职位、专业…" autocomplete="off">
      </div>
      <span class="result-count" id="resultCount"></span>
    </div>
    <div class="pos-table-wrap">
      <table class="pos-table">
        <thead>
          <tr>
            <th class="sortable" data-key="y">年份</th>
            <th class="sortable" data-key="c">考区</th>
            <th class="sortable" data-key="u">招考单位</th>
            <th class="sortable" data-key="p">招考职位</th>
            <th class="sortable" data-key="n" style="text-align:right">人数</th>
            <th class="sortable" data-key="e">学历</th>
            <th class="sortable" data-key="ft">类别</th>
          </tr>
        </thead>
        <tbody id="posTableBody"></tbody>
      </table>
    </div>
  </div>
</div>

</div>

<div class="footer">
  <p>数据来源：广东省 2020-2026 年考试录用公务员职位表 &nbsp;·&nbsp; 专业范围：B0807 电子信息类 + A0809 电子科学与技术 + A0810 信息与通信工程 + A0840 电子信息（专硕）</p>
  <p style="margin-top:4px">分析工具：gd-exam-viz · 可视化设计：Editorial Treasury 风格</p>
</div>

<button class="back-top" id="backTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" aria-label="返回顶部">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
</button>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script>
{all_pos_js}

// ====== Data Arrays ======
const YEARS = ["{year_labels}"];
const TOTAL_RECRUITS = [{','.join(total_recruits_arr)}];
const TOTAL_POSITIONS = [{','.join(total_positions_arr)}];
const FRESH_RECRUITS = [{','.join(fresh_recruits_arr)}];
const FRESH_CURRENT = [{','.join(fresh_current_arr)}];
const EDU_LABELS = ["{edu_labels_js}"];
const EDU_VALUES = [{edu_totals_js}];
const EDU_TREND_DATA = {edu_trend_js};
const CITY_NAMES = ["{city_names_js}"];
const CITY_TOTALS = [{city_totals_js}];
const CITY_DATA = {city_data_json};

// ====== Common Chart Config ======
Chart.defaults.font.family = "'SF Pro Text','PingFang SC','Microsoft YaHei',sans-serif";
Chart.defaults.color = '#6b6660';

function baseOpts() {{
  return {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 16 }} }},
      tooltip: {{ backgroundColor: '#fff', titleColor: '#1e1e1e', bodyColor: '#6b6660', borderColor: '#e3dfd6', borderWidth: 1, padding: 12, cornerRadius: 6 }}
    }},
    scales: {{
      y: {{ beginAtZero: true, grid: {{ color: 'rgba(0,0,0,0.04)' }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }};
}}

// ====== 1. Trend Chart ======
window.trendChart = new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: YEARS,
    datasets: [
      {{
        label: '招录人数',
        data: TOTAL_RECRUITS,
        borderColor: '#0f2347',
        backgroundColor: 'rgba(15,35,71,0.08)',
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#0f2347',
        pointRadius: 4,
        pointHoverRadius: 6,
        borderWidth: 2.5,
      }},
      {{
        label: '职位数',
        data: TOTAL_POSITIONS,
        borderColor: '#3875b6',
        backgroundColor: 'rgba(56,117,182,0.05)',
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#3875b6',
        pointRadius: 4,
        pointHoverRadius: 6,
        borderWidth: 2,
        borderDash: [5,3],
      }}
    ]
  }},
  options: baseOpts()
}});

// ====== 2. Fresh/Social Donut ======
window.freshChart = new Chart(document.getElementById('freshChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['社会人员', '往届应届/择业期', '当年应届'],
    datasets: [{{
      data: [{total_social}, {total_fresh_any}, {total_fresh_current}],
      backgroundColor: ['#b8432a', '#b8952e', '#2e8b8b'],
      borderWidth: 0,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 14 }} }},
      tooltip: {{
        callbacks: {{
          label: function(ctx) {{ return ctx.label + ': ' + ctx.parsed + ' 人'; }}
        }}
      }}
    }},
    cutout: '55%',
  }}
}});

// ====== 3. Education Donut ======
window.eduChart = new Chart(document.getElementById('eduChart'), {{
  type: 'doughnut',
  data: {{
    labels: EDU_LABELS,
    datasets: [{{
      data: EDU_VALUES,
      backgroundColor: ['#0f2347', '#3875b6', '#5fa8c7', '#b8952e', '#7a8b9e'],
      borderWidth: 0,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 14 }} }},
      tooltip: {{
        callbacks: {{
          label: function(ctx) {{ return ctx.label + ': ' + ctx.parsed + ' 人'; }}
        }}
      }}
    }},
    cutout: '55%',
  }}
}});
// ====== Year filter for charts ======
var EDU_KEYS = EDU_LABELS;

function updateYearCharts(year) {{
  var filtered = year === 'all' ? ALL_POSITIONS : ALL_POSITIONS.filter(function(p) {{ return p.y === year; }});
  var totalPeople = filtered.reduce(function(s,p) {{ return s + p.n; }}, 0);
  document.getElementById('yearFilterInfo').textContent = (year === 'all' ? '全部' : year) + ' · ' + totalPeople + ' 人';

  var social = filtered.filter(function(p) {{ return p.ft === 'social'; }}).reduce(function(s,p) {{ return s + p.n; }}, 0);
  var freshAny = filtered.filter(function(p) {{ return p.ft === 'fresh_any'; }}).reduce(function(s,p) {{ return s + p.n; }}, 0);
  var freshCurrent = filtered.filter(function(p) {{ return p.ft === 'fresh_current'; }}).reduce(function(s,p) {{ return s + p.n; }}, 0);
  window.freshChart.data.datasets[0].data = [social, freshAny, freshCurrent];
  window.freshChart.update();

  var eduCounts = {{}};
  EDU_KEYS.forEach(function(k) {{ eduCounts[k] = 0; }});
  filtered.forEach(function(p) {{ if (eduCounts[p.e] !== undefined) eduCounts[p.e] += p.n; }});
  window.eduChart.data.datasets[0].data = EDU_KEYS.map(function(k) {{ return eduCounts[k]; }});
  window.eduChart.update();

  // Update chart notes
  var yearLabel = year === 'all' ? '2020-2026' : year;
  var notes = document.querySelectorAll('.chart-note');
  notes[1].textContent = yearLabel + ' · 当年应届 ' + freshCurrent + ' 人，社会人员 ' + social + ' 人';
  notes[2].textContent = yearLabel + ' · 本科以上和研究生为主体，共 ' + (totalPeople - (eduCounts['大专以上']||0)) + ' 人';

  var positions = filtered.length;
  animateCounter(document.querySelectorAll('.stat-card .number')[0], totalPeople);
  animateCounter(document.querySelectorAll('.stat-card .number')[1], positions);
}}

document.querySelectorAll('.float-year-btn').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.float-year-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    this.classList.add('active');
    var year = this.dataset.year;
    updateYearCharts(year);
    // Also trigger heat table and position table tabs to sync
    document.querySelectorAll('.year-tab').forEach(function(tab) {{
      if (tab.dataset.year === year) {{
        tab.click();
      }}
    }});
  }});
}});

// ====== 4. City Stacked Bar Chart ======
(function() {{
  var years = YEARS;
  var cities = Object.keys(CITY_DATA).sort(function(a,b) {{
    var ta = 0, tb = 0;
    years.forEach(function(y) {{ ta += CITY_DATA[a][y] || 0; tb += CITY_DATA[b][y] || 0; }});
    return tb - ta;
  }});

  var yearColors = ['#c4d7e8','#a8c4df','#8bb1d5','#6e9ecc','#528bc2','#3578b9','#0f2347'];

  var datasets = years.map(function(y, i) {{
    return {{
      label: y + '年',
      data: cities.map(function(c) {{ return CITY_DATA[c][y] || 0; }}),
      backgroundColor: yearColors[i % yearColors.length],
      borderColor: '#fff',
      borderWidth: 0.5,
    }};
  }});

  var cityChart = new Chart(document.getElementById('cityChart'), {{
    type: 'bar',
    data: {{ labels: cities, datasets: datasets }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      interaction: {{ mode: 'point', intersect: false }},
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 14, boxWidth: 12, font: {{ size: 11 }} }} }},
        tooltip: {{
          mode: 'point',
          backgroundColor: '#fff',
          titleColor: '#1e1e1e',
          bodyColor: '#6b6660',
          borderColor: '#e3dfd6',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 6,
          callbacks: {{
            title: function(items) {{
              var city = items[0].label;
              var total = 0;
              years.forEach(function(y) {{ total += CITY_DATA[city][y] || 0; }});
              return city + ' · 共 ' + total + ' 人';
            }}
          }}
        }}
      }},
      scales: {{
        x: {{ stacked: true, beginAtZero: true, grid: {{ color: 'rgba(0,0,0,0.04)' }}, title: {{ display: true, text: '招录人数', color: '#9e9890', font: {{ size: 11 }} }} }},
        y: {{ stacked: true, grid: {{ display: false }}, ticks: {{ autoSkip: false, font: {{ size: 11, weight: '500' }} }} }}
      }}
    }}
  }});
}})();

// ====== 5. Edu Trend (Stacked Bar) ======
window.eduTrendChart = new Chart(document.getElementById('eduTrendChart'), {{
  type: 'bar',
  data: {{
    labels: YEARS,
    datasets: EDU_TREND_DATA,
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 14 }} }},
      tooltip: {{ mode: 'index', intersect: false, backgroundColor: '#fff', titleColor: '#1e1e1e', bodyColor: '#6b6660', borderColor: '#e3dfd6', borderWidth: 1, padding: 10, cornerRadius: 6 }}
    }},
    scales: {{
      x: {{ stacked: true, grid: {{ display: false }} }},
      y: {{ stacked: true, beginAtZero: true, grid: {{ color: 'rgba(0,0,0,0.04)' }} }}
    }}
  }}
}});

// ====== 6. City Heat Table with Year Tabs ======
(function() {{
  var years = YEARS;
  var allCities = Object.keys(CITY_DATA).sort(function(a,b) {{
    var ta = 0, tb = 0;
    years.forEach(function(y) {{ ta += CITY_DATA[a][y] || 0; tb += CITY_DATA[b][y] || 0; }});
    return tb - ta;
  }});
  var allVals = [];
  allCities.forEach(function(c) {{
    years.forEach(function(y) {{ allVals.push(CITY_DATA[c][y] || 0); }});
  }});
  var maxValAll = Math.max.apply(null, allVals) || 1;

  var heatYear = 'all';

  function renderHeatTable() {{
    var showYears = heatYear === 'all' ? years : [heatYear];
    var cities = allCities;
    var vals = [];
    cities.forEach(function(c) {{
      showYears.forEach(function(y) {{ vals.push(CITY_DATA[c][y] || 0); }});
    }});
    var maxVal = Math.max.apply(null, vals) || 1;

    var html = '<thead><tr><th>城市</th>';
    showYears.forEach(function(y) {{ html += '<th style="text-align:right;padding:8px 10px;font-size:12px">' + y + '</th>'; }});
    html += '<th style="text-align:right;padding:10px 14px;font-size:12px">累计</th></tr></thead><tbody>';

    cities.forEach(function(c) {{
      var total = 0;
      var row = '<tr><td style="padding:8px 12px;font-weight:600;white-space:nowrap;border-bottom:1px solid #edeae3;font-size:13px">' + c + '</td>';
      showYears.forEach(function(y) {{
        var v = CITY_DATA[c][y] || 0;
        total += v;
        var ratio = maxVal > 0 ? v / maxVal : 0;
        var intensity = 0.05 + ratio * 0.58;
        var bg = 'rgba(15,35,71,' + intensity + ')';
        var textColor = v > 0 ? '#0f2347' : '#c0bbb5';
        row += '<td style="text-align:right;padding:8px 10px;border-bottom:1px solid #edeae3"><span class="heatmap-cell" style="background:' + bg + ';color:' + textColor + ';font-weight:' + (v > 0 ? '600' : '400') + ';font-size:13px;padding:3px 8px">' + v + '</span></td>';
      }});
      row += '<td style="text-align:right;padding:8px 14px;font-weight:700;border-bottom:1px solid #edeae3;font-family:var(--mono);color:#0f2347;font-size:13px">' + total + '</td></tr>';
      html += row;
    }});

    html += '</tbody>';
    document.getElementById('cityHeatTable').innerHTML = html;
  }}

  // Build year tabs
  (function() {{
    var container = document.getElementById('heatYearTabs');
    var btn = document.createElement('button');
    btn.className = 'year-tab active';
    btn.textContent = '全部年份';
    btn.dataset.year = 'all';
    container.appendChild(btn);
    years.forEach(function(y) {{
      var btn = document.createElement('button');
      btn.className = 'year-tab';
      btn.textContent = y;
      btn.dataset.year = y;
      container.appendChild(btn);
    }});
    container.addEventListener('click', function(e) {{
      if (e.target.classList.contains('year-tab')) {{
        container.querySelectorAll('.year-tab').forEach(function(t) {{ t.classList.remove('active'); }});
        e.target.classList.add('active');
        heatYear = e.target.dataset.year;
        renderHeatTable();
      }}
    }});
  }})();

  renderHeatTable();
}})();

// ====== 7. Position Table ======
(function() {{
  var all = ALL_POSITIONS;
  var currentYear = 'all';
  var sortKey = null;
  var sortDir = 1;
  var searchTerm = '';

  function getFiltered() {{
    var list = currentYear === 'all' ? all : all.filter(function(p) {{ return p.y === currentYear; }});
    if (searchTerm) {{
      var st = searchTerm.toLowerCase();
      list = list.filter(function(p) {{ return p.u.toLowerCase().indexOf(st)>=0 || p.p.toLowerCase().indexOf(st)>=0 || p.pr.toLowerCase().indexOf(st)>=0 || p.c.indexOf(st)>=0; }});
    }}
    return list;
  }}

  function render() {{
    var list = getFiltered();
    if (sortKey) {{
      list.sort(function(a,b) {{
        var va = a[sortKey], vb = b[sortKey];
        if (sortKey === 'n') {{ va = +va; vb = +vb; }}
        return va < vb ? -sortDir : va > vb ? sortDir : 0;
      }});
    }}
    var html = '';
    list.forEach(function(p) {{
      var ftLabel = {{'social':'社会','fresh_any':'往届','fresh_current':'当年应届'}}[p.ft] || p.ft;
      var ftClass = {{'social':'tag-social','fresh_any':'tag-fresh','fresh_current':'tag-fresh'}}[p.ft] || '';
      html += '<tr><td>' + p.y + '</td><td>' + p.c + '</td><td>' + p.u + '</td><td>' + p.p + '</td><td style="text-align:right;font-weight:700">' + p.n + '</td><td>' + p.e + '</td><td><span class="tag ' + ftClass + '">' + ftLabel + '</span></td></tr>';
    }});
    document.getElementById('posTableBody').innerHTML = html;
    document.getElementById('resultCount').textContent = '共 ' + list.length + ' 个职位';
  }}

  // Year tabs
  (function() {{
    var container = document.getElementById('yearTabs');
    var btn = document.createElement('button');
    btn.className = 'year-tab active';
    btn.textContent = '全部年份';
    btn.dataset.year = 'all';
    container.appendChild(btn);
    YEARS.forEach(function(y) {{
      var btn = document.createElement('button');
      btn.className = 'year-tab';
      btn.textContent = y;
      btn.dataset.year = y;
      container.appendChild(btn);
    }});
    container.addEventListener('click', function(e) {{
      if (e.target.classList.contains('year-tab')) {{
        container.querySelectorAll('.year-tab').forEach(function(t) {{ t.classList.remove('active'); }});
        e.target.classList.add('active');
        currentYear = e.target.dataset.year;
        render();
      }}
    }});
  }})();

  // Search
  document.getElementById('posSearch').addEventListener('input', function(e) {{
    searchTerm = e.target.value;
    render();
  }});

  // Sort
  document.querySelectorAll('.sortable').forEach(function(th) {{
    th.addEventListener('click', function() {{
      var key = this.dataset.key;
      if (sortKey === key) {{ sortDir *= -1; }} else {{ sortKey = key; sortDir = 1; }}
      document.querySelectorAll('.sortable').forEach(function(t) {{ t.classList.remove('sort-asc','sort-desc'); }});
      this.classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
      render();
    }});
  }});

  render();
}})();

// ====== Sticky Nav Active ======
(function() {{
  var nav = document.querySelector('.sticky-nav');
  var links = nav.querySelectorAll('a');
  var sections = [];
  links.forEach(function(a) {{
    var id = a.getAttribute('href').slice(1);
    sections.push(document.getElementById(id));
  }});
  window.addEventListener('scroll', function() {{
    var top = window.scrollY + 100;
    var active = 0;
    sections.forEach(function(s, i) {{
      if (s && s.offsetTop <= top) active = i;
    }});
    links.forEach(function(a, i) {{
      a.classList.toggle('active', i === active);
    }});
    var docH = document.documentElement.scrollHeight - window.innerHeight;
    document.getElementById('progressBar').style.width = (window.scrollY / docH * 100).toFixed(1) + '%';
    document.getElementById('backTop').classList.toggle('visible', window.scrollY > 400);
  }});
}})();

// ====== Fade Up Animation ======
(function() {{
  var els = document.querySelectorAll('.stat-card, .chart-card, .data-table, .banner');
  var observer = new IntersectionObserver(function(entries) {{
    entries.forEach(function(entry) {{
      if (entry.isIntersecting) {{
        entry.target.classList.remove('fade-in');
        void entry.target.offsetWidth;
        entry.target.classList.add('fade-in');
      }} else {{
        entry.target.classList.remove('fade-in');
      }}
    }});
  }}, {{ threshold: 0.15 }});
  els.forEach(function(el) {{ el.style.opacity = '0'; observer.observe(el); }});
}})();

// ====== Number Counter Animation ======
function animateCounter(el, target, duration) {{
  if (!el) return;
  var start = parseInt(el.textContent.replace(/[^0-9]/g, '')) || 0;
  var diff = target - start;
  if (diff === 0) return;
  duration = duration || 600;
  var startTime = null;
  function step(timestamp) {{
    if (!startTime) startTime = timestamp;
    var progress = Math.min((timestamp - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - progress, 3);
    var current = Math.round(start + diff * eased);
    el.textContent = current;
    if (progress < 1) {{
      requestAnimationFrame(step);
    }} else {{
      el.textContent = target;
    }}
  }}
  requestAnimationFrame(step);
}}

// ====== 3D Tilt Effect on Card Hover ======
(function() {{
  var tiltEls = document.querySelectorAll('.stat-card, .chart-card, .data-table');
  tiltEls.forEach(function(el) {{
    el.style.transition = 'transform 0.15s ease-out, box-shadow 0.25s ease-out';
    el.style.transformStyle = 'preserve-3d';
    el.style.willChange = 'transform';
    el.addEventListener('mouseenter', function() {{
      el.style.transition = 'transform 0.06s ease-out, box-shadow 0.2s ease-out';
    }});
    el.addEventListener('mousemove', function(e) {{
      var rect = el.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      var centerX = rect.width / 2;
      var centerY = rect.height / 2;
      var rotateY = ((x - centerX) / centerX) * 10;
      var rotateX = ((centerY - y) / centerY) * 10;
      el.style.transform = 'perspective(400px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) scale(1.02)';
      el.style.boxShadow = '0 12px 32px rgba(0,0,0,0.1)';
    }});
    el.addEventListener('mouseleave', function() {{
      el.style.transition = 'transform 0.4s ease-out, box-shadow 0.4s ease-out';
      el.style.transform = 'perspective(400px) rotateX(0deg) rotateY(0deg) scale(1)';
      el.style.boxShadow = '';
    }});
  }});
}})();

// Initial counter animation on page load
setTimeout(function() {{
  var nums = document.querySelectorAll('.stat-card .number');
  if (nums.length >= 4) {{
    animateCounter(nums[0], parseInt(nums[0].textContent), 800);
    animateCounter(nums[1], parseInt(nums[1].textContent), 800);
    animateCounter(nums[2], parseInt(nums[2].textContent), 600);
    animateCounter(nums[3], parseInt(nums[3].textContent), 600);
  }}
}}, 400);

console.log('电子信息类招录趋势看板已加载, 共 ' + ALL_POSITIONS.length + ' 条记录');
</script>
</body>
</html>
'''

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
outpath = os.path.join(_BASE, '广东省考电子信息类招录趋势.html')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f'HTML 已生成！文件大小: {len(HTML)} 字节')
