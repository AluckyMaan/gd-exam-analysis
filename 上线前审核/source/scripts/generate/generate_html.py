"""Generate the complete civil engineering page with magazine layout + data narrative + motion + mobile + charts + branding."""
import json
d = json.load(open('tumu_data.json', encoding='utf-8'))
details = d['details']

items = []
for item in details:
    y=item["year"]; u=item["unit"].replace("\\","\\\\").replace('"','\\"')
    p=item["position"].replace("\\","\\\\").replace('"','\\"')
    n=item["recruits"]; c=item["city"].replace("\\","\\\\").replace('"','\\"')
    e=item["education"].replace("\\","\\\\").replace('"','\\"')
    f="true" if item["fresh_only"] else "false"
    ft=item.get("fresh_type","social")
    pr=item.get("prof_fields","").replace("\\","\\\\").replace('"','\\"').replace("\n"," ").replace("\r"," ")
    items.append(f'{{"y":"{y}","u":"{u}","p":"{p}","n":{n},"c":"{c}","e":"{e}","f":{f},"ft":"{ft}","pr":"{pr}"}}')
all_pos_js=f"var ALL_POSITIONS = [\n" + ",\n".join(items) + "\n];"

# Read JS from external file to simplify
with open('generate_html.py', encoding='utf-8') as f:
    pass  # placeholder

HEADER = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省考 · 土木工程 / 规划建设类招录趋势</title>
<style>
:root{--navy:#16233a;--navy-light:#2a3f5e;--navy-mid:#7c8fa8;--gold:#b8952e;--gold-soft:#f5efdc;--gold-light:#faf6ed;--paper:#f7f5f0;--white:#fff;--border:#e3dfd6;--border-light:#edeae3;--text:#1e1e1e;--text-secondary:#6b6660;--text-tertiary:#9e9890;--positive:#2a6b4a;--positive-soft:#eaf1ec;--negative:#b8432a;--negative-soft:#f5e8e4;--radius:10px;--radius-sm:6px;--shadow:0 1px 3px rgba(0,0,0,0.05);--shadow-md:0 4px 12px rgba(0,0,0,0.06);--shadow-lg:0 8px 28px rgba(0,0,0,0.07);--sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;--serif:Georgia,"Songti SC","Noto Serif SC","Source Han Serif SC","SimSun",serif;--mono:"SF Mono",ui-monospace,"Cascadia Code","Consolas","JetBrains Mono",monospace}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:var(--sans);background:var(--paper);color:var(--text);line-height:1.5;-webkit-font-smoothing:antialiased;padding-bottom:80px}
.container{max-width:1080px;margin:0 auto;padding:0 20px}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes blink{0%,50%{opacity:1}51%,100%{opacity:0}}
.section{scroll-margin-top:60px}
.section-header{display:flex;align-items:center;gap:16px;margin-bottom:20px;padding-top:16px}
.section-number{font-family:var(--mono);font-size:14px;font-weight:600;color:var(--gold);letter-spacing:1px}
.section-line{flex:1;height:1px;background:linear-gradient(90deg,var(--gold),transparent)}
.section-line-left{flex:1;height:1px;background:linear-gradient(270deg,var(--gold),transparent)}
.section-title{font-family:var(--serif);font-size:20px;font-weight:600;color:var(--text);letter-spacing:0.5px}
.sticky-nav{position:sticky;top:0;z-index:100;background:rgba(247,245,240,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--border-light);padding:0 20px;display:flex;align-items:center;gap:4px;overflow-x:auto;margin-bottom:24px}
.sticky-nav::-webkit-scrollbar{display:none}
.sticky-nav a{text-decoration:none;color:var(--text-secondary);font-size:13px;font-weight:500;padding:10px 16px;white-space:nowrap;transition:color 0.2s;position:relative}
.sticky-nav a::after{content:"";position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:0;height:2px;background:var(--navy);transition:width 0.3s}
.sticky-nav a:hover,.sticky-nav a.active{color:var(--navy)}
.sticky-nav a.active::after{width:24px}
.app-bar{display:flex;align-items:center;justify-content:space-between;padding:18px 0;margin-bottom:4px}
.app-bar-brand{display:flex;align-items:center;gap:10px;font-family:var(--serif);font-size:19px;font-weight:600;color:var(--text);text-decoration:none}
.app-bar-brand svg{width:26px;height:26px;color:var(--navy)}
.app-bar-year{font-size:12px;color:var(--text-tertiary);border:1px solid var(--border);padding:4px 14px;border-radius:20px;font-weight:500;letter-spacing:0.5px}
.hero-wrap{background:var(--white);border-bottom:1px solid var(--border-light);margin-bottom:28px;position:relative;overflow:hidden}
.hero-wrap::before{content:"2020  2021  2022  2023  2024  2025  2026";position:absolute;right:-20px;top:50%;transform:translateY(-50%);font-family:var(--mono);font-size:clamp(60px,10vw,120px);font-weight:700;color:rgba(22,35,58,0.03);letter-spacing:8px;white-space:nowrap;pointer-events:none;line-height:1}
.hero{padding:40px 0 32px;position:relative;z-index:1}
.hero .hero-label{font-family:var(--mono);font-size:11px;color:var(--gold);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
.hero h1{font-family:var(--serif);font-size:42px;font-weight:600;color:var(--text);line-height:1.15;margin-bottom:12px;max-width:720px}
.hero h1 span{color:var(--navy)}
.hero .subtitle{font-size:14px;color:var(--text-tertiary);letter-spacing:0.3px}
.hero .subtitle .cursor{display:inline-block;width:1.5px;height:1em;background:var(--navy);vertical-align:text-bottom;animation:blink 1s step-end infinite}
.chip-group{display:flex;flex-wrap:wrap;gap:6px;margin-top:18px}
.chip{display:inline-flex;align-items:center;padding:4px 13px;border:1px solid var(--border);border-radius:5px;font-size:12px;font-weight:400;color:var(--text-secondary);background:var(--paper);transition:border-color 0.2s,color 0.2s}
.banner{display:flex;align-items:flex-start;gap:12px;background:var(--white);border-left:3px solid var(--gold);border-radius:var(--radius-sm);padding:14px 18px;margin-bottom:28px;font-size:13px;color:var(--text-secondary);line-height:1.7;box-shadow:var(--shadow)}
.banner svg{flex-shrink:0;width:18px;height:18px;color:var(--gold);margin-top:3px}
.banner strong{color:var(--text)}
.insight-bar{display:none;align-items:center;gap:12px;background:var(--gold-light);border-radius:var(--radius-sm);padding:12px 18px;margin-bottom:20px;font-size:13px;color:var(--text);line-height:1.6;border:1px solid var(--gold-soft)}
.insight-bar.visible{display:flex}
.insight-bar .insight-icon{flex-shrink:0;width:18px;height:18px;color:var(--gold)}
.filter-bar{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:20px;padding:10px 0}
.filter-label{font-size:13px;font-weight:500;color:var(--text-secondary);margin-right:8px}
.filter-btn{padding:6px 16px;border:1px solid var(--border);background:var(--white);border-radius:18px;cursor:pointer;font-size:12px;font-weight:500;font-family:var(--sans);color:var(--text-secondary);transition:all 0.2s;user-select:none}
.filter-btn:hover{border-color:var(--navy-mid);color:var(--navy)}
.filter-btn.active{background:var(--navy);color:#fff;border-color:var(--navy)}
.filter-info{margin-left:auto;font-size:12px;color:var(--text-tertiary)}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:28px}
.stat-card{background:var(--white);border-radius:var(--radius);padding:22px 18px;box-shadow:var(--shadow);text-align:center;position:relative;overflow:hidden;transition:box-shadow 0.3s,transform 0.25s}
.stat-card:hover{box-shadow:var(--shadow-md);transform:translateY(-2px)}
.stat-card .number{font-family:var(--mono);font-size:30px;font-weight:600;color:var(--navy);letter-spacing:-0.5px;line-height:1}
.stat-card .label{font-size:13px;font-weight:500;color:var(--text);margin-top:8px}
.stat-card .sub{font-size:11px;color:var(--text-tertiary);margin-top:2px}
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}
.chart-grid-donut{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}
.chart-card{background:var(--white);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow);transition:box-shadow 0.3s;position:relative}
.chart-card:hover{box-shadow:var(--shadow-md)}
.chart-card.full{grid-column:1/-1}
.chart-card .chart-title{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--text);margin-bottom:16px;letter-spacing:0.3px;text-transform:uppercase}
.chart-card .chart-title svg{width:16px;height:16px;color:var(--navy-mid);flex-shrink:0}
.chart-wrapper{position:relative;height:300px}
.chart-note{margin-top:8px;font-size:11px;color:var(--text-tertiary);text-align:center}
.data-table{background:var(--white);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin-bottom:28px}
.data-table .dt-header{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:0.3px;padding:20px 22px 12px}
.data-table .dt-header svg{width:16px;height:16px;color:var(--navy-mid)}
.data-table table{width:100%;border-collapse:collapse;font-size:13px}
.data-table th{padding:11px 18px;text-align:right;font-weight:600;color:var(--text-secondary);border-bottom:1.5px solid var(--border);font-size:11px;letter-spacing:0.5px;text-transform:uppercase;font-family:var(--mono);background:var(--paper)}
.data-table th:first-child{text-align:left;padding-left:22px}
.data-table th:last-child{padding-right:22px}
.data-table td{padding:11px 18px;text-align:right;border-bottom:1px solid var(--border-light);color:var(--text);font-variant-numeric:tabular-nums}
.data-table td:first-child{text-align:left;font-weight:600;padding-left:22px}
.data-table td:last-child{padding-right:22px}
.data-table tbody tr{transition:background 0.12s}
.data-table tbody tr:hover td{background:var(--gold-soft)}
.data-table tbody tr:last-child td{border-bottom:none}
.data-table .hl{display:inline-block;background:var(--gold-soft);color:var(--navy);padding:2px 10px;border-radius:4px;font-weight:600;font-family:var(--mono);font-size:13px}
.change-up{color:var(--positive);font-weight:500}
.change-down{color:var(--negative);font-weight:500}
.change-none{color:var(--text-tertiary)}
.heatmap-cell{display:inline-block;padding:2px 6px;border-radius:3px;font-weight:500;font-family:var(--mono);font-size:12px}
.year-tabs{display:flex;gap:6px;flex-wrap:wrap;padding:0 22px 14px}
.year-tab{padding:5px 15px;border:1px solid var(--border);background:var(--white);border-radius:18px;cursor:pointer;font-size:12px;font-weight:500;font-family:var(--sans);color:var(--text-secondary);transition:all 0.2s}
.year-tab:hover{border-color:var(--navy-mid);color:var(--navy)}
.year-tab.active{background:var(--navy);color:#fff;border-color:var(--navy)}
.tab-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:0 22px 16px}
.search-wrapper{position:relative;flex:1;min-width:200px}
.search-wrapper svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--text-tertiary);pointer-events:none}
.search-input{padding:7px 12px 7px 34px;border:1px solid var(--border);border-radius:18px;font-size:13px;font-family:var(--sans);color:var(--text);background:var(--paper);width:100%;transition:all 0.2s}
.search-input:focus{outline:none;border-color:var(--gold);background:var(--white);box-shadow:0 0 0 3px rgba(184,149,46,0.08)}
.search-input::placeholder{color:var(--text-tertiary)}
.result-count{font-size:12px;color:var(--text-tertiary);white-space:nowrap;margin-left:auto}
.pos-table-wrap{max-height:560px;overflow-y:auto;border-top:1px solid var(--border-light)}
.pos-table{width:100%;border-collapse:collapse;font-size:12px}
.pos-table thead{position:sticky;top:0;z-index:2}
.pos-table th{background:var(--paper);padding:9px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1.5px solid var(--border);font-size:11px;letter-spacing:0.3px;white-space:nowrap;font-family:var(--mono)}
.pos-table th.sortable{cursor:pointer}
.pos-table th.sortable:hover{color:var(--navy)}
.pos-table th.sortable::after{content:" \\2195";font-size:10px;opacity:0.3}
.pos-table th.sort-asc::after{content:" \\2191";opacity:1;color:var(--gold)}
.pos-table th.sort-desc::after{content:" \\2193";opacity:1;color:var(--gold)}
.pos-table td{padding:7px 12px;border-bottom:1px solid var(--border-light);vertical-align:top;color:var(--text)}
.pos-table tbody tr{transition:background 0.12s}
.pos-table tbody tr:hover td{background:var(--gold-soft)}
.tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600}
.tag-fresh{background:var(--positive-soft);color:var(--positive)}
.tag-social{background:var(--negative-soft);color:var(--negative)}
.tag-benke{background:var(--gold-soft);color:var(--navy)}
.tag-master{background:#ede9f6;color:#5b4d8b}
.tag-dazhuan{background:#fef3e4;color:#8b7a3a}
.pos-table .recruit-num{font-weight:700;color:var(--navy);font-size:13px;font-family:var(--mono)}
.footer{text-align:center;padding:28px;color:var(--text-tertiary);font-size:12px;border-top:1px solid var(--border-light);margin-top:48px}
.back-top{position:fixed;bottom:92px;right:24px;width:40px;height:40px;background:var(--white);color:var(--text-secondary);border:1px solid var(--border);border-radius:50%;cursor:pointer;box-shadow:var(--shadow);opacity:0;visibility:hidden;z-index:99;display:flex;align-items:center;justify-content:center;transition:all 0.25s}
.back-top.visible{opacity:1;visibility:visible}
.back-top:hover{transform:translateY(-2px);border-color:var(--navy);color:var(--navy);box-shadow:var(--shadow-md)}
.back-top svg{width:18px;height:18px}
@media(max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:769px){.mobile-only{display:none!important}}
@media(max-width:768px){
body{padding-bottom:64px}
.desktop-only{display:none!important}
.hero h1{font-size:28px}
.chart-grid,.chart-grid-donut{grid-template-columns:1fr}
.chart-wrapper{height:260px}
.data-table{overflow-x:auto}
.data-table table{font-size:12px}
.data-table th,.data-table td{padding:10px 14px}
.data-table th:first-child,.data-table td:first-child{padding-left:16px}
.data-table th:last-child,.data-table td:last-child{padding-right:16px}
.filter-info{width:100%;margin-left:0;text-align:right;font-size:11px}
.stat-card{padding:16px}
.stat-card .number{font-size:24px}
.sticky-nav{padding:0 12px;gap:2px}
.sticky-nav a{font-size:12px;padding:8px 12px}
.back-top{bottom:76px;right:12px;width:34px;height:34px}
.stats-grid{grid-template-columns:none;display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:4px}
.stats-grid::-webkit-scrollbar{display:none}
.stat-card{flex:0 0 160px;scroll-snap-align:start}
.mobile-nav{position:fixed;bottom:0;left:0;right:0;z-index:200;background:rgba(255,255,255,0.95);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-top:1px solid var(--border-light);display:flex;justify-content:space-around;padding:6px 0 env(safe-area-inset-bottom,6px)}
.mobile-nav a{text-decoration:none;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:10px;color:var(--text-tertiary);transition:color 0.2s;padding:4px 8px}
.mobile-nav a svg{width:20px;height:20px}
.mobile-nav a.active{color:var(--navy)}
}
@media(max-width:480px){
.hero{padding:24px 0 20px}
.hero h1{font-size:24px}
.container{padding:0 14px}
}
@media print{.sticky-nav,.back-top,.mobile-nav,.filter-bar{display:none!important}.hero-wrap{background:white!important;border:none!important}.hero-wrap::before{display:none}body{background:white;padding:0}.section{page-break-inside:avoid}}
</style>
</head>
<body>
<nav class="sticky-nav desktop-only" id="stickyNav">
<div class="container" style="display:flex;align-items:center;gap:4px;padding:0">
<a href="#section-overview" class="active">概览</a><a href="#section-trend">趋势</a><a href="#section-city">城市</a><a href="#section-edu">学历</a><a href="#section-data">数据</a>
</div></nav>
<nav class="mobile-nav mobile-only" id="mobileNav">
<a href="#section-overview"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg><span>概览</span></a>
<a href="#section-trend"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg><span>趋势</span></a>
<a href="#section-city"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="6" width="4" height="12" rx="1"/><rect x="10" y="4" width="4" height="14" rx="1"/><rect x="18" y="8" width="4" height="10" rx="1"/></svg><span>城市</span></a>
<a href="#section-edu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M12 3 3 8.5 12 14l9-5.5L12 3z"/><path d="M5 10.5v4l7 4 7-4v-4"/></svg><span>学历</span></a>
<a href="#section-data"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg><span>岗位</span></a>
</nav>
<div class="container"><div class="app-bar">
<a href="#" class="app-bar-brand"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20h20M6 20V8l4-4 4 4v12M10 20v-6h4v6M18 20V6l-2-2"/></svg>广东省考·招录趋势</a>
<span class="app-bar-year">2020–2026</span>
</div></div>
<div class="hero-wrap">
<div class="container"><div class="hero">
<div class="hero-label">招考数据报告</div>
<h1>土木工程 <span>/</span> 规划建设类招录趋势</h1>
<p class="subtitle" id="typewriterP" data-text="基于 2020–2026 年广东省公务员考试全部职位表数据，分析招录趋势与分布"></p>
<div class="chip-group">
<span class="chip">土木工程</span><span class="chip">土木类</span><span class="chip">规划建设类</span>
<span class="chip">岩土工程</span><span class="chip">结构工程</span><span class="chip">市政工程</span>
</div>
</div></div></div>
<div class="container">
<div class="banner">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v.01M12 12v4"/></svg>
<span>统计范围为专业要求包含 <strong>土木工程 / 土木类 / 规划建设类</strong> 等关键词的职位。涵盖县级以上机关、乡镇机关、公安、法院、检察院、监狱戒毒等全部系统。省直单位根据单位名称自动识别。</span>
</div>
<section id="section-overview" class="section">
<div class="section-header"><span class="section-number">01</span><span class="section-title">概览 — 招录总览</span><span class="section-line"></span></div>
<div class="insight-bar" id="insightBar">
<svg class="insight-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
<span id="insightText"></span>
</div>
<div class="filter-bar"><span class="filter-label">学历筛选</span>
<button class="filter-btn active" data-filter="all">全部</button>
<button class="filter-btn active" data-filter="benke">本科</button>
<button class="filter-btn active" data-filter="yanjiusheng">研究生</button>
<button class="filter-btn active" data-filter="dazhuan">大专</button>
<span class="filter-info" id="filterInfo"></span>
</div>
<div class="stats-grid" id="statsGrid"></div>
</section>
<section id="section-trend" class="section">
<div class="section-header"><span class="section-line-left"></span><span class="section-number">02</span><span class="section-title">趋势 — 招录变化</span><span class="section-line"></span></div>
<div class="chart-grid">
<div class="chart-card full"><div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>招录人数变化趋势</div><div class="chart-wrapper"><canvas id="trendChart"></canvas></div><div class="chart-note" id="trendNote"></div></div>
</div>
<div class="chart-grid-donut">
<div class="chart-card"><div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>应届 vs 社会 占比</div><div class="chart-wrapper" style="height:260px"><canvas id="donutChart"></canvas></div><div class="chart-note" id="donutNote"></div></div>
<div class="chart-card"><div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="4" height="12" rx="1"/><rect x="10" y="4" width="4" height="14" rx="1"/><rect x="18" y="8" width="4" height="10" rx="1"/></svg>应届 vs 社会 对比</div><div class="chart-wrapper"><canvas id="freshChart"></canvas></div></div>
</div>
</section>
<section id="section-city" class="section">
<div class="section-header"><span class="section-line-left"></span><span class="section-number">03</span><span class="section-title">城市 — 各地市分布</span><span class="section-line"></span></div>
<div class="chart-grid">
<div class="chart-card full"><div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="4" height="12" rx="1"/><rect x="10" y="4" width="4" height="14" rx="1"/><rect x="18" y="8" width="4" height="10" rx="1"/></svg>各城市（含省直）招录人数排名</div><div class="chart-wrapper" style="height:480px"><canvas id="cityChart"></canvas></div></div>
</div>
<div class="data-table"><div class="dt-header"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>城市 × 年份 招录热力图</div>
<table><thead><tr><th>城市</th><th>累计</th></tr></thead><tbody id="heatmapBody"></tbody></table></div>
</section>
<section id="section-edu" class="section">
<div class="section-header"><span class="section-line-left"></span><span class="section-number">04</span><span class="section-title">学历 — 层级结构</span><span class="section-line"></span></div>
<div class="chart-grid">
<div class="chart-card full"><div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 3 8.5 12 14l9-5.5L12 3z"/><path d="M5 10.5v4l7 4 7-4v-4"/></svg>各学历层级招录人数</div><div class="chart-wrapper"><canvas id="eduChart"></canvas></div><div class="chart-note" id="eduNote"></div></div>
</div>
</section>
<section id="section-data" class="section">
<div class="section-header"><span class="section-line-left"></span><span class="section-number">05</span><span class="section-title">数据 — 明细查询</span><span class="section-line"></span></div>
<div class="data-table"><div class="dt-header"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>历年数据明细</div>
<table><thead><tr><th>年份</th><th>职位数</th><th>招录人数</th><th>本科及以上</th><th>仅限研究生</th><th>应届</th><th>变化</th></tr></thead>
<tbody id="dataTableBody"></tbody></table></div>
<div class="data-table"><div class="dt-header"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>历年岗位明细</div>
<div class="tab-toolbar"><div class="year-tabs" id="yearTabs"></div>
<div class="search-wrapper"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>
<input class="search-input" id="posSearch" placeholder="搜索单位、职位、专业、城市..." /></div>
<span class="result-count" id="resultCount"></span></div>
<div class="pos-table-wrap"><table class="pos-table">
<thead><tr><th style="width:42px">年份</th><th style="width:56px">城市</th><th>招考单位</th><th>招考职位</th><th style="width:40px" class="sortable" data-sort="n">招录</th><th style="width:50px">学历</th><th style="width:40px">应届</th><th style="width:160px">专业要求</th></tr></thead>
<tbody id="posTableBody"></tbody></table></div></div>
</section>
</div>
<div class="footer"><div class="container">数据来源：广东省公务员考试录用管理系统 · 2020–2026</div></div>
<button class="back-top" id="backTop" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="回到顶部"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 15l-6-6-6 6"/></svg></button>
'''

JS_CODE = r"""
// ====== Chart defaults ======
(function(){
var font=getComputedStyle(document.documentElement).getPropertyValue('--sans').trim().split(',')[0];
Chart.defaults.font.family=font;
Chart.defaults.font.color='#6b6660';
Chart.defaults.plugins.tooltip.backgroundColor='rgba(255,255,255,0.97)';
Chart.defaults.plugins.tooltip.titleColor='#1e1e1e';
Chart.defaults.plugins.tooltip.bodyColor='#6b6660';
Chart.defaults.plugins.tooltip.borderColor='#e3dfd6';
Chart.defaults.plugins.tooltip.borderWidth=1;
Chart.defaults.plugins.tooltip.padding=12;
Chart.defaults.plugins.tooltip.cornerRadius=8;
Chart.defaults.plugins.tooltip.titleFont={weight:'600',size:13};
Chart.defaults.plugins.tooltip.bodyFont={size:12};
})();

function eduMatches(edu,f){
if(!edu||f==='all')return true;
var e=edu.replace(/\s/g,'');
if(f==='benke')return e.indexOf('本科')>=0;
if(f==='yanjiusheng')return e.indexOf('研究生')>=0||e.indexOf('硕士')>=0||e.indexOf('博士')>=0;
if(f==='dazhuan')return e.indexOf('大专')>=0;
return true;
}

function getFilteredData(filters){
var isAll=filters.indexOf('all')>=0||filters.length===0;
var pos=isAll?ALL_POSITIONS:ALL_POSITIONS.filter(function(p){return filters.some(function(f){return eduMatches(p.e,f);});});
var years={};
pos.forEach(function(p){
if(!years[p.y])years[p.y]={records:0,recruits:0,fresh:0};
years[p.y].records++;years[p.y].recruits+=p.n;if(p.f)years[p.y].fresh+=p.n;
});
var sy=Object.keys(years).sort(),summary={};
sy.forEach(function(y){var d=years[y];summary[y]={records:d.records,recruits:d.recruits,fresh:d.fresh,avg:Math.round(d.recruits/d.records*10)/10};});
var cities={};
pos.forEach(function(p){if(!cities[p.c])cities[p.c]={};if(!cities[p.c][p.y])cities[p.c][p.y]=0;cities[p.c][p.y]+=p.n;});
var edu={};
sy.forEach(function(y){edu[y]={};});
pos.forEach(function(p){
var e=p.e.replace(/\s/g,''),k;
if(e.indexOf('研究生')>=0||e.indexOf('硕士')>=0||e.indexOf('博士')>=0)k='研究生';
else if(e.indexOf('本科')>=0)k='本科以上';
else if(e.indexOf('大专')>=0)k='大专以上';
else k='其他';
if(!edu[p.y][k])edu[p.y][k]=0;edu[p.y][k]+=p.n;
});
return {years:sy,summary:summary,cities:cities,edu:edu,positions:pos};
}

var activeFilters=new Set(['all']),activeYearTab=null,posSortCol=null,posSortDir='desc',posSearchText='';
var trendChart,cityChart,freshChart,eduChart,donutChart;

function toggleFilter(btn){
var f=btn.dataset.filter;
if(f==='all'){
document.querySelectorAll('.filter-btn').forEach(function(b){b.classList.toggle('active',b.dataset.filter==='all');});
activeFilters=new Set(['all']);
}else{
btn.classList.toggle('active');
if(btn.classList.contains('active'))activeFilters.add(f);else activeFilters.delete(f);
var hs=false;activeFilters.forEach(function(x){if(x!=='all')hs=true;});
var ab=document.querySelector('[data-filter="all"]');
if(!hs){ab.classList.add('active');activeFilters.add('all');}else{ab.classList.remove('active');activeFilters.delete('all');}
}
updateAll();renderPositionTable();
}

function updateAll(){
var filters=[];activeFilters.forEach(function(f){if(f!=='all')filters.push(f);});
var data=getFilteredData(filters.length?filters:['all']);
var at=ALL_POSITIONS.reduce(function(s,p){return s+p.n;},0);
var ft=data.positions.reduce(function(s,p){return s+p.n;},0);
document.getElementById('filterInfo').textContent=filters.length?'筛选 '+data.positions.length+' 个职位 · 招录 '+ft+' 人':'全部数据 · '+at+' 人';
renderInsight(data);
renderStats(data);
renderTrend(data);
renderDonut(data);
renderFresh(data);
renderCity(data);
renderHeatmap(data);
renderEdu(data);
renderTable(data);
}

function renderInsight(data){
var sy=data.summary,yrs=data.years;
var bar=document.getElementById('insightBar');
if(yrs.length<2){bar.classList.remove('visible');return;}
var peakYr=yrs[0];yrs.forEach(function(y){if(sy[y].recruits>sy[peakYr].recruits)peakYr=y;});
var last=sy[yrs[yrs.length-1]],peak=sy[peakYr];
var diff=last.recruits-peak.recruits,pct=Math.round(Math.abs(diff)/peak.recruits*100);
var dir=diff>0?'增长了':'回落了';
bar.classList.add('visible');
var txt='<strong>'+yrs[yrs.length-1]+'年</strong> 招录 '+last.recruits+' 人，';
txt+=peakYr===yrs[yrs.length-1]?'创历史新高。':'较 '+peakYr+' 年峰值('+peak.recruits+' 人) '+dir+' 约 '+pct+'%。';
if(data.positions.length===ALL_POSITIONS.length)txt+=' 累计招录 '+ALL_POSITIONS.reduce(function(s,p){return s+p.n;},0).toLocaleString()+' 人。';
document.getElementById('insightText').innerHTML=txt;
}

function renderStats(data){
var sy=data.summary,yrs=data.years;
if(!yrs.length){document.getElementById('statsGrid').innerHTML='<div class="stat-card" style="grid-column:1/-1"><div class="number" style="font-size:18px">暂无数据</div></div>';return;}
var total=yrs.reduce(function(s,y){return s+sy[y].recruits;},0);
var peakYr=yrs[0];yrs.forEach(function(y){if(sy[y].recruits>sy[peakYr].recruits)peakYr=y;});
var g=yrs.length>1?((sy[yrs[yrs.length-1]].recruits-sy[yrs[0]].recruits)/sy[yrs[0]].recruits*100).toFixed(0):'0';
var pr=sy[yrs[yrs.length-1]].recruits>0?(sy[yrs[yrs.length-1]].recruits/sy[peakYr].recruits*100).toFixed(0):'0';
document.getElementById('statsGrid').innerHTML=
'<div class="stat-card"><div class="number">'+total.toLocaleString()+'</div><div class="label">累计招录</div><div class="sub">土木 / 规划建设类</div></div>'+
'<div class="stat-card"><div class="number">'+sy[peakYr].recruits.toLocaleString()+'</div><div class="label">'+peakYr+' 年峰值</div><div class="sub">历年最高招录</div></div>'+
'<div class="stat-card"><div class="number">'+pr+'%</div><div class="label">'+yrs[yrs.length-1]+' 年为峰值的</div><div class="sub">较峰值时期回落</div></div>'+
'<div class="stat-card"><div class="number">'+(g>='0'?'+ ':'')+g+'%</div><div class="label">总体增长</div><div class="sub">'+yrs[yrs.length-1]+' 对比 '+yrs[0]+'</div></div>';
}

function renderTrend(data){
if(trendChart)trendChart.destroy();
var yrs=data.years;if(!yrs.length)return;
var ctx=document.getElementById('trendChart').getContext('2d');
var peakVal=Math.max.apply(null,yrs.map(function(y){return data.summary[y].recruits;}));
var g=ctx.createLinearGradient(0,0,0,300);g.addColorStop(0,'rgba(22,35,58,0.08)');g.addColorStop(1,'rgba(22,35,58,0.01)');
trendChart=new Chart(ctx,{
type:'line',
data:{labels:yrs,datasets:[
{label:'招录人数',data:yrs.map(function(y){return data.summary[y].recruits;}),borderColor:'#16233a',backgroundColor:g,fill:true,tension:0.3,pointBackgroundColor:'#16233a',pointRadius:5,pointHoverRadius:7,borderWidth:2.5},
{label:'应届生',data:yrs.map(function(y){return data.summary[y].fresh;}),borderColor:'#b8952e',backgroundColor:'rgba(184,149,46,0.05)',fill:true,tension:0.3,pointBackgroundColor:'#b8952e',pointRadius:4,pointHoverRadius:6,borderWidth:2,borderDash:[6,4]}
]},
options:{
responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},
plugins:{
tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+ctx.parsed.y+' 人';}}},
legend:{labels:{usePointStyle:true,padding:20,pointStyleWidth:10,font:{size:11}}}
},
scales:{y:{beginAtZero:true,title:{display:true,text:'招录人数',color:'#9e9890',font:{size:11}},grid:{color:'rgba(227,223,214,0.4)'},ticks:{color:'#9e9890',font:{size:11}}},x:{grid:{display:false},ticks:{color:'#9e9890',font:{size:11}}}}
},
plugins:[{afterDraw:function(ch){
var ctx2=ch.ctx;if(!ch.data||!ch.data.labels)return;
var meta=ch.getDatasetMeta(0);if(!meta||!meta.data)return;
var peakIdx=0;meta.data.forEach(function(d,i){if(d.y<meta.data[peakIdx].y)peakIdx=i;});
var p=meta.data[peakIdx];
if(peakIdx===0||peakIdx===meta.data.length-1)return;
ctx2.save();
var label='峰值 '+ch.data.datasets[0].data[peakIdx];
ctx2.font='10px sans-serif';
var tw=ctx2.measureText(label).width;
ctx2.fillStyle='rgba(22,35,58,0.85)';
roundRect(ctx2,p.x-tw/2-6,p.y-28,tw+12,18,4);ctx2.fill();
ctx2.fillStyle='#fff';ctx2.font='bold 10px sans-serif';
ctx2.fillText(label,p.x,p.y-16);
ctx2.restore();
}}]
});
function roundRect(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.quadraticCurveTo(x+w,y,x+w,y+r);c.lineTo(x+w,y+h-r);c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);c.lineTo(x+r,y+h);c.quadraticCurveTo(x,y+h,x,y+h-r);c.lineTo(x,y+r);c.quadraticCurveTo(x,y,x+r,y);c.closePath();}
var sy=data.summary;
document.getElementById('trendNote').textContent='峰值出现在 '+yrs.reduce(function(a,b){return sy[a].recruits>sy[b].recruits?a:b;})+' 年，招录 '+Math.max.apply(null,yrs.map(function(y){return sy[y].recruits;}))+' 人。应届生招录最高年份为 '+yrs.reduce(function(a,b){return sy[a].fresh>sy[b].fresh?a:b;})+' 年。';
}

function renderDonut(data){
if(donutChart)donutChart.destroy();
var yrs=data.years;if(!yrs.length)return;
var total=data.positions.reduce(function(s,p){return s+p.n;},0);
var fresh=data.positions.reduce(function(s,p){return s+(p.f?p.n:0);},0);
var social=total-fresh;
var ctx=document.getElementById('donutChart').getContext('2d');
donutChart=new Chart(ctx,{type:'doughnut',data:{labels:['应届生','社会招录'],datasets:[{data:[fresh,social],backgroundColor:['#16233a','#b8952e'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'65%',plugins:{tooltip:{callbacks:{label:function(ctx){return ctx.label+': '+ctx.parsed.y+' 人 ('+Math.round(ctx.parsed.y/total*100)+'%)';}}},legend:{position:'bottom',labels:{usePointStyle:true,padding:16,pointStyleWidth:8,font:{size:11}}}}}});
document.getElementById('donutNote').textContent='应届生占 '+Math.round(fresh/total*100)+'%，社会招录占 '+Math.round(social/total*100)+'%。';
}

function renderFresh(data){
if(freshChart)freshChart.destroy();
var yrs=data.years;if(!yrs.length)return;
var ctx=document.getElementById('freshChart').getContext('2d');
freshChart=new Chart(ctx,{type:'bar',data:{labels:yrs,datasets:[{label:'招录人数',data:yrs.map(function(y){return data.summary[y].recruits;}),backgroundColor:'#16233a',borderRadius:6,barPercentage:0.65},{label:'应届',data:yrs.map(function(y){return data.summary[y].fresh;}),backgroundColor:'#b8952e',borderRadius:6,barPercentage:0.65}]},options:{responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},plugins:{tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+ctx.parsed.y+' 人';}}}},scales:{y:{beginAtZero:true,grid:{color:'rgba(227,223,214,0.4)'},ticks:{color:'#9e9890',font:{size:11}}},x:{grid:{display:false},ticks:{color:'#9e9890',font:{size:11}}}}}});
}

function renderCity(data){
if(cityChart)cityChart.destroy();
var cities=data.cities,yrs=data.years;
var sorted=Object.keys(cities).sort(function(a,b){var sa=0,sb=0;yrs.forEach(function(y){sa+=cities[a][y]||0;sb+=cities[b][y]||0;});return sb-sa;});
if(!sorted.length)return;
var totals=sorted.map(function(c){var t=0;yrs.forEach(function(y){t+=cities[c][y]||0;});return t;});
var maxVal=Math.max.apply(null,totals);
var medals={0:'🥇',1:'🥈',2:'🥉'};
var ctx=document.getElementById('cityChart').getContext('2d');
cityChart=new Chart(ctx,{type:'bar',data:{labels:sorted.map(function(c,i){return(medals[i]||'')+' '+c;}),datasets:[{label:'累计招录',data:totals,backgroundColor:sorted.map(function(c,i){var t=0.3+(1-i/sorted.length)*0.7;return c==='省直'?'rgba(124,143,168,'+t.toFixed(2)+')':'rgba(22,35,58,'+t.toFixed(2)+')';}),borderRadius:{topLeft:4,topRight:4,bottomLeft:0,bottomRight:0},barThickness:16}]},options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false},tooltip:{callbacks:{label:function(ctx){var parts=[];var c=ctx.rawLabel||ctx.label.replace(/^[🥇🥈🥉]\s/,'');yrs.forEach(function(y){if(cities[c]&&cities[c][y])parts.push(y+':'+cities[c][y]);});return'累计 '+ctx.parsed.x+' 人 | '+parts.join(' · ');}}}},scales:{x:{beginAtZero:true,max:maxVal*1.12,ticks:{font:{size:11},color:'#9e9890'},grid:{color:'rgba(227,223,214,0.4)'}},y:{grid:{display:false},ticks:{font:{size:12,weight:'500'},color:'#6b6660'}}}}});
}

function renderHeatmap(data){
var cities=data.cities,yrs=data.years,medals={0:'🥇',1:'🥈',2:'🥉'};
var sorted=Object.keys(cities).sort(function(a,b){var sa=0,sb=0;yrs.forEach(function(y){sa+=cities[a][y]||0;sb+=cities[b][y]||0;});return sb-sa;});
var allVals=[];sorted.forEach(function(c){yrs.forEach(function(y){if(cities[c][y])allVals.push(cities[c][y]);});});
var minV=Math.min.apply(null,allVals),maxV=Math.max.apply(null,allVals);
function hc(v){if(!v||maxV===minV)return'rgba(22,35,58,0.05)';var t=(v-minV)/(maxV-minV);return'rgba(22,35,58,'+(0.05+t*0.35).toFixed(2)+')';}
var html='<thead><tr><th>城市</th>';yrs.forEach(function(y){html+='<th style="text-align:center;font-size:10px">'+y+'</th>';});html+='<th style="text-align:center;font-size:10px">累计</th></tr></thead><tbody>';
sorted.forEach(function(c,i){
var total=0;yrs.forEach(function(y){total+=cities[c][y]||0;});
html+='<tr><td style="font-weight:600">'+(medals[i]||'')+' '+c+'</td>';
yrs.forEach(function(y){
var v=cities[c][y]||0;
html+='<td style="text-align:center;padding:8px 6px"><span class="heatmap-cell" style="background:'+hc(v)+';color:'+(v>=(minV+maxV)/2?'#fff':'var(--text)')+'">'+(v||'-')+'</span></td>';
});
html+='<td style="text-align:center;font-weight:600;font-family:var(--mono);color:var(--navy)">'+total+'</td></tr>';
});
html+='</tbody>';
document.getElementById('heatmapBody').innerHTML=html;
}

function renderEdu(data){
if(eduChart)eduChart.destroy();
var yrs=data.years;if(!yrs.length)return;
var benke=yrs.map(function(y){return(data.edu[y]['本科以上']||0)+(data.edu[y]['本科']||0);});
var yanjiusheng=yrs.map(function(y){return data.edu[y]['研究生']||0;});
var dazhuan=yrs.map(function(y){return data.edu[y]['大专以上']||0;});
var totals=yrs.map(function(y,i){return benke[i]+yanjiusheng[i]+dazhuan[i];});
var ctx=document.getElementById('eduChart').getContext('2d');
eduChart=new Chart(ctx,{type:'bar',data:{labels:yrs,datasets:[{label:'本科及以上',data:benke,backgroundColor:'#16233a',borderRadius:4},{label:'研究生',data:yanjiusheng,backgroundColor:'#7c8fa8',borderRadius:4},{label:'大专可报',data:dazhuan,backgroundColor:'#b8952e',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},plugins:{tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+ctx.parsed.y+' 人 ('+Math.round(ctx.parsed.y/totals[ctx.dataIndex]*100)+'%)';}}},legend:{labels:{usePointStyle:true,padding:20,pointStyleWidth:10,font:{size:11}}}},scales:{y:{beginAtZero:true,grid:{color:'rgba(227,223,214,0.4)'},ticks:{color:'#9e9890',font:{size:11}}},x:{grid:{display:false},ticks:{color:'#9e9890',font:{size:11}}}}}});
document.getElementById('eduNote').textContent='本科及以上仍是招录主体，但研究生比例从 '+yrs[0]+' 年的 '+yanjiusheng[0]+' 人升至 '+yrs[yrs.length-1]+' 年的 '+yanjiusheng[yanjiusheng.length-1]+' 人，增长趋势明显。';
}

function renderTable(data){
var tbody=document.getElementById('dataTableBody');
var yrs=data.years;
if(!yrs.length){tbody.innerHTML='<tr><td colspan="7" style="text-align:center;color:#9e9890;padding:20px">暂无数据</td></tr>';return;}
tbody.innerHTML=yrs.map(function(y,i){
var d=data.summary[y],prev=i>0?data.summary[yrs[i-1]]:null;
var ct='-',cc='change-none';
if(prev){var df=d.recruits-prev.recruits;ct=(df>0?'+':'')+df;cc=df>0?'change-up':df<0?'change-down':'change-none';}
var bk=(data.edu[y]['本科以上']||0)+(data.edu[y]['本科']||0);
var yjs=data.edu[y]['研究生']||0;
var fp=d.recruits>0?(d.fresh/d.recruits*100).toFixed(0):'0';
return '<tr><td><strong>'+y+'</strong></td><td>'+d.records+'</td><td><span class="hl">'+d.recruits+'</span></td><td>'+bk+'</td><td>'+yjs+'</td><td>'+d.fresh+' <span style="color:var(--text-tertiary);font-size:11px">('+fp+'%)</span></td><td class="'+cc+'">'+ct+'</td></tr>';
}).join('');
}

function getFilteredPositions(){
var filters=[];activeFilters.forEach(function(f){if(f!=='all')filters.push(f);});
var pos=filters.length?ALL_POSITIONS.filter(function(p){return filters.some(function(f){return eduMatches(p.e,f);});}):ALL_POSITIONS.slice();
if(activeYearTab)pos=pos.filter(function(p){return p.y===activeYearTab;});
if(posSearchText){var q=posSearchText.toLowerCase();pos=pos.filter(function(p){return p.u.toLowerCase().indexOf(q)>=0||p.p.toLowerCase().indexOf(q)>=0||p.pr.toLowerCase().indexOf(q)>=0||p.c.toLowerCase().indexOf(q)>=0;});}
if(posSortCol){pos.sort(function(a,b){var va=a[posSortCol],vb=b[posSortCol];if(posSortCol==='n'){va=a.n;vb=b.n;}if(typeof va==='string'){va=va.toLowerCase();vb=vb.toLowerCase();}return va<vb?(posSortDir==='asc'?-1:1):va>vb?(posSortDir==='asc'?1:-1):0;});}
return pos;
}

function getEduTag(e){
if(!e)return'';var edu=e.replace(/\s/g,'');
if(edu.indexOf('研究生')>=0||edu.indexOf('硕士')>=0||edu.indexOf('博士')>=0)return'<span class="tag tag-master">研究生</span>';
if(edu.indexOf('大专')>=0)return'<span class="tag tag-dazhuan">大专</span>';
if(edu.indexOf('本科')>=0)return'<span class="tag tag-benke">本科</span>';
return'<span class="tag tag-benke">'+e+'</span>';
}

function renderPositionTable(){
var pos=getFilteredPositions(),tn=pos.reduce(function(s,p){return s+p.n;},0);
document.getElementById('resultCount').textContent=pos.length+' 条 · 招录 '+tn+' 人';
var rows='';
pos.forEach(function(p){
var ft=p.f?'<span class="tag tag-fresh">应届</span>':'<span class="tag tag-social">社会</span>';
var et=getEduTag(p.e),cb=p.c==='省直'?'style="font-weight:600;color:var(--navy-mid)"':'';
rows+='<tr><td><strong>'+p.y+'</strong></td><td><span '+cb+'>'+p.c+'</span></td><td>'+p.u+'</td><td>'+p.p+'</td><td><span class="recruit-num">'+p.n+'</span></td><td>'+et+'</td><td>'+ft+'</td><td style="font-size:11px;color:var(--text-tertiary);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+p.pr.replace(/"/g,'&quot;')+'">'+p.pr+'</td></tr>';
});
document.getElementById('posTableBody').innerHTML=rows;
document.querySelectorAll('.pos-table th.sortable').forEach(function(th){
th.classList.remove('sort-asc','sort-desc');
if(th.dataset.sort===posSortCol)th.classList.add(posSortDir==='asc'?'sort-asc':'sort-desc');
});
}

function initYearTabs(){
var td=document.getElementById('yearTabs');
var ab=document.createElement('button');ab.className='year-tab active';ab.textContent='全部年份';
ab.onclick=function(){activeYearTab=null;updateYearTabStyles();renderPositionTable();};td.appendChild(ab);
var yrs=[];ALL_POSITIONS.forEach(function(p){if(yrs.indexOf(p.y)<0)yrs.push(p.y);});
yrs.sort().forEach(function(yr){
var btn=document.createElement('button');btn.className='year-tab';btn.textContent=yr+'年';
btn.onclick=function(){activeYearTab=yr;updateYearTabStyles();renderPositionTable();};td.appendChild(btn);
});
}

function updateYearTabStyles(){
document.querySelectorAll('.year-tab').forEach(function(btn){
btn.classList.toggle('active',(btn.textContent==='全部年份'&&activeYearTab===null)||btn.textContent===activeYearTab+'年');
});
}

// Scroll observer
(function(){
if(!window.IntersectionObserver)return;
var els=document.querySelectorAll('.section>.section-header, .stat-card, .chart-card, .data-table');
var obs=new IntersectionObserver(function(entries){
entries.forEach(function(entry){
if(entry.isIntersecting){entry.target.style.opacity='1';entry.target.style.transform='translateY(0)';obs.unobserve(entry.target);}
});
},{threshold:0.1});
els.forEach(function(el){el.style.opacity='0';el.style.transform='translateY(16px)';el.style.transition='opacity 0.5s ease, transform 0.5s ease';obs.observe(el);});
})();

// Nav scroll spy
function updateNav(){
var links=document.querySelectorAll('#stickyNav a, #mobileNav a');
var sections=['section-overview','section-trend','section-city','section-edu','section-data'];
var current='section-overview';
sections.forEach(function(id){var el=document.getElementById(id);if(el&&el.getBoundingClientRect().top<120)current=id;});
links.forEach(function(a){a.classList.toggle('active',a.getAttribute('href')==='#'+current);});
}

// Init
document.querySelectorAll('.filter-btn').forEach(function(b){b.addEventListener('click',function(){toggleFilter(b);});});
document.addEventListener('click',function(e){
var th=e.target.closest?e.target.closest('.pos-table th.sortable'):null;if(!th)return;
var col=th.dataset.sort;
if(posSortCol===col)posSortDir=posSortDir==='asc'?'desc':'asc';else{posSortCol=col;posSortDir='desc';}
renderPositionTable();
});
document.addEventListener('input',function(e){if(e.target.id==='posSearch'){posSearchText=e.target.value.trim();renderPositionTable();}});
window.addEventListener('scroll',function(){
var btn=document.getElementById('backTop');if(btn)btn.classList.toggle('visible',window.scrollY>400);
updateNav();
});
initYearTabs();updateAll();renderPositionTable();

// Typewriter
(function(){
var el=document.getElementById('typewriterP');if(!el)return;
var text=el.getAttribute('data-text')||'',i=0;
function type(){
if(i<=text.length){el.innerHTML=text.substring(0,i)+(i<text.length?'<span class="cursor"></span>':'');i++;setTimeout(type,45+Math.random()*35);}
else el.innerHTML=text+'<span class="cursor"></span>';
}
type();
})();
"""

output = HEADER + '\n<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>\n<script>\n' + all_pos_js + '\n' + JS_CODE + '\n</script>\n</body>\n</html>'

with open('广东省考土木招考趋势.html', 'w', encoding='utf-8') as f:
    f.write(output)

import os
s = os.path.getsize('广东省考土木招考趋势.html')
print(f"OK Generated: {s/1024:.0f} KB, {len(details)} positions")
