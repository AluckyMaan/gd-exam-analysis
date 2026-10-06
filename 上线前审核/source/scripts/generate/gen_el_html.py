#!/usr/bin/env python3
"""电子类省考数据 — HTML 可视化看板生成器"""
import json, os
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
d = json.load(open(os.path.join(BASE, 'data', 'electronics_data.json'), encoding='utf-8'))
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
    items.append(f'{{"y":"{y}","u":"{u}","p":"{p}","n":{n},"c":"{c}","e":"{e}","f":{f},"ft":"{ft}","pr":"{pr}"}}')
all_pos_js = "var ALL_POSITIONS = [\n" + ",\n".join(items) + "\n];"

ys = d['yearly_summary']
years_sorted = sorted(ys.keys())
year_labels = '","'.join(years_sorted)
total_recruits_arr = [str(ys[y]['total_recruits']) for y in years_sorted]
total_positions_arr = [str(ys[y]['total_records']) for y in years_sorted]

city_data = d['city_summary']
edu_data = d['edu_summary']
edu_keys = sorted(edu_data.keys())
edu_labels_js = '","'.join(edu_keys)
edu_totals_js = ','.join([str(sum(edu_data[k].values())) for k in edu_keys])

edu_colors = ['#0f2347', '#3875b6', '#5fa8c7', '#b8952e', '#7a8b9e']
edu_trend_datasets = []
for idx, k in enumerate(edu_keys):
    yearly_data = ','.join([str(edu_data[k].get(y, 0)) for y in years_sorted])
    edu_trend_datasets.append(f'{{label:"{k}",data:[{yearly_data}],backgroundColor:"{edu_colors[idx % len(edu_colors)]}",borderWidth:0}}')
edu_trend_js = '[' + ','.join(edu_trend_datasets) + ']'

fs = d['fresh_summary']
ts = sum(fs['social'].values())
ta = sum(fs['fresh_any'].values())
tc = sum(fs['fresh_current'].values())

first_total = ys[years_sorted[0]]['total_recruits']
last_total = ys[years_sorted[-1]]['total_recruits']
growth_pct = round((last_total - first_total) / first_total * 100)
peak_year = max(years_sorted, key=lambda y: ys[y]['total_recruits'])
peak_val = ys[peak_year]['total_recruits']
total_all = sum(ys[y]['total_recruits'] for y in years_sorted)
total_pos_all = sum(ys[y]['total_records'] for y in years_sorted)
city_data_json = json.dumps(city_data, ensure_ascii=False)

template = """
<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>广东省考 · 电子信息类招录趋势</title>
<style>
:root{--navy:#0f2347;--navy-light:#1a3a6e;--navy-mid:#3875b6;--teal:#2e8b8b;--teal-soft:#e6f0f2;--gold:#b8952e;--gold-soft:#f5efdc;--paper:#f7f5f0;--white:#fff;--border:#e3dfd6;--text:#1e1e1e;--text-secondary:#6b6660;--text-tertiary:#9e9890;--positive:#2a6b4a;--positive-soft:#eaf1ec;--negative:#b8432a;--negative-soft:#f5e8e4;--radius:10px;--radius-sm:6px;--shadow:0 1px 3px rgba(0,0,0,0.05);--shadow-md:0 4px 12px rgba(0,0,0,0.06);--sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;--serif:Georgia,"Songti SC","Noto Serif SC","Source Han Serif SC","SimSun",serif;--mono:"SF Mono",ui-monospace,"Cascadia Code","Consolas","JetBrains Mono",monospace}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);background:var(--paper);color:var(--text);line-height:1.5;padding-bottom:80px}
.container{max-width:1080px;margin:0 auto;padding:0 20px}
#progressBar{position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,var(--gold),var(--navy));z-index:999;width:0%;transition:width 0.15s ease-out}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.fade-in{animation:fadeUp 0.5s ease-out forwards}
.sticky-nav{position:sticky;top:0;z-index:100;background:rgba(247,245,240,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:0 20px;display:flex;gap:4px;overflow-x:auto;margin-bottom:24px}
.sticky-nav a{text-decoration:none;color:var(--text-secondary);font-size:13px;font-weight:500;padding:10px 16px;white-space:nowrap}
.sticky-nav a:hover,.sticky-nav a.active{color:var(--navy)}
.float-year-bar{position:fixed;top:50px;left:50%;transform:translateX(-50%);z-index:99;display:flex;gap:4px;background:rgba(247,245,240,0.92);backdrop-filter:blur(12px);border:1px solid var(--border);border-radius:28px;padding:6px 16px;box-shadow:var(--shadow-md)}
.float-year-btn{padding:4px 12px;border:1px solid transparent;background:transparent;border-radius:16px;cursor:pointer;font-size:12px;color:var(--text-secondary)}
.float-year-btn.active{background:var(--navy);color:#fff;border-color:var(--navy)}
.float-year-info{font-size:11px;color:var(--text-tertiary);margin-left:6px;padding-left:8px;border-left:1px solid var(--border)}
.app-bar{display:flex;align-items:center;justify-content:space-between;padding:18px 0}
.app-bar-brand{display:flex;align-items:center;gap:10px;font-family:var(--serif);font-size:19px;font-weight:600;color:var(--text);text-decoration:none}
.app-bar-year{font-size:12px;color:var(--text-tertiary);border:1px solid var(--border);padding:4px 14px;border-radius:20px}
.hero-wrap{background:var(--white);border-bottom:1px solid var(--border);margin-bottom:28px;position:relative;overflow:hidden}
.hero{padding:40px 0 32px}
.hero h1{font-family:var(--serif);font-size:42px;font-weight:600;line-height:1.15;margin-bottom:12px}
.hero h1 span{color:var(--navy)}
.chip-group{display:flex;flex-wrap:wrap;gap:6px;margin-top:18px}
.chip{display:inline-flex;padding:4px 13px;border:1px solid var(--border);border-radius:5px;font-size:12px;color:var(--text-secondary);background:var(--paper)}
.banner{display:flex;align-items:flex-start;gap:12px;background:var(--white);border-left:3px solid var(--gold);border-radius:var(--radius-sm);padding:14px 18px;margin:20px 0;font-size:13px;color:var(--text-secondary);line-height:1.7;box-shadow:var(--shadow)}
.section-header{display:flex;align-items:center;gap:16px;margin-bottom:20px;padding-top:16px}
.section-number{font-family:var(--mono);font-size:14px;font-weight:600;color:var(--gold)}
.section-line{flex:1;height:1px;background:linear-gradient(90deg,var(--gold),transparent)}
.section-title{font-family:var(--serif);font-size:20px;font-weight:600}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:28px}
.stat-card{background:var(--white);border-radius:var(--radius);padding:22px 18px;box-shadow:var(--shadow);text-align:center}
.stat-card .number{font-family:var(--mono);font-size:30px;font-weight:600;color:var(--navy)}
.stat-card .label{font-size:13px;font-weight:500;margin-top:8px}
.stat-card .sub{font-size:11px;color:var(--text-tertiary);margin-top:2px}
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}
.chart-card{background:var(--white);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow)}
.chart-card.full{grid-column:1/-1}
.chart-card .chart-title{font-size:13px;font-weight:600;margin-bottom:16px}
.chart-wrapper{position:relative;height:300px;width:100%}
#cityChartWrapper{height:600px}
.chart-note{margin-top:8px;font-size:11px;color:var(--text-tertiary);text-align:center}
.data-table{background:var(--white);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin-bottom:28px}
.data-table .dt-header{font-size:13px;font-weight:600;padding:20px 22px 12px}
.year-tabs{display:flex;gap:6px;flex-wrap:wrap;padding:0 22px 14px}
.year-tab{padding:5px 15px;border:1px solid var(--border);background:var(--white);border-radius:18px;cursor:pointer;font-size:12px;color:var(--text-secondary)}
.year-tab.active{background:var(--navy);color:#fff;border-color:var(--navy)}
.tab-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:0 22px 16px}
.search-input{padding:7px 12px;border:1px solid var(--border);border-radius:18px;font-size:13px;font-family:var(--sans);width:100%}
.pos-table-wrap{max-height:560px;overflow-y:auto;border-top:1px solid var(--border)}
.pos-table{width:100%;table-layout:fixed;border-collapse:collapse;font-size:12px}
.pos-table thead{position:sticky;top:0;z-index:2}
.pos-table th{background:var(--paper);padding:9px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1.5px solid var(--border);font-size:11px}
.pos-table td{padding:7px 12px;border-bottom:1px solid var(--border)}
.pos-table tbody tr:hover td{background:var(--gold-soft)}
.tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600}
.tag-fresh{background:var(--positive-soft);color:var(--positive)}
.tag-social{background:var(--negative-soft);color:var(--negative)}
.footer{text-align:center;padding:28px;color:var(--text-tertiary);font-size:12px;border-top:1px solid var(--border);margin-top:48px}
.back-top{position:fixed;bottom:92px;right:24px;width:40px;height:40px;background:var(--white);border:1px solid var(--border);border-radius:50%;cursor:pointer;opacity:0;visibility:hidden;z-index:99}
.back-top.visible{opacity:1;visibility:visible}
@media(max-width:768px){.hero h1{font-size:28px}.stats-grid{grid-template-columns:repeat(2,1fr)}.chart-grid{grid-template-columns:1fr}}
</style></head><body>
<div id="progressBar"></div>
<div class="sticky-nav"><a href="#overview">概览</a><a href="#trend">招录趋势</a><a href="#city">城市分布</a><a href="#education">学历与应届</a><a href="#positions">岗位明细</a></div>
<div class="float-year-bar" id="floatYearBar">
<span class="float-year-info" id="yearFilterInfo">全部 · <SCRIPT>document.write(""" + str(total_all) + """)</SCRIPT> 人</span></div>
<div class="hero-wrap"><div class="container"><div class="app-bar"><span class="app-bar-brand">广东省考电子信息类</span><span class="app-bar-year">2020-2026</span></div>
<div class="hero"><h1><span>电子信息类</span> 及相关专业<br>招录趋势分析报告</h1>
<div class="chip-group"><span class="chip">电子信息工程</span><span class="chip">电子科学与技术</span><span class="chip">通信工程</span><span class="chip">微电子</span><span class="chip">光电信息</span><span class="chip">集成电路</span><span class="chip">人工智能</span><span class="chip">电子信息科学与技术</span><span class="chip">应用电子技术</span></div>
</div></div></div>
<div class="container">
<div class="banner" id="overview">本报告分析 <strong>2020-2026 年广东省考</strong>中 <strong>电子信息类（B0807）</strong> 及相关专业的招录数据。共收录 <strong>"""+str(total_pos_all)+""" 个职位</strong>，<strong>"""+str(total_all)+""" 个招录名额</strong>，是省考中招录规模最大的专业类别之一。</div>
<div class="section"><div class="section-header"><span class="section-number">01</span><div class="section-line"></div><span class="section-title">核心发现</span></div>
<div class="stats-grid">
<div class="stat-card"><div class="number">"""+str(total_all)+"""</div><div class="label">总招录人数</div><div class="sub">2020-2026 合计</div></div>
<div class="stat-card"><div class="number">"""+str(total_pos_all)+"""</div><div class="label">总职位数</div><div class="sub">7 年累计</div></div>
<div class="stat-card"><div class="number">"""+str(growth_pct)+"""%</div><div class="label">招录增长</div><div class="sub">"""+years_sorted[0]+""" → """+years_sorted[-1]+"""</div></div>
<div class="stat-card"><div class="number">"""+peak_year+"""</div><div class="label">招录峰值年</div><div class="sub">"""+str(peak_val)+""" 人</div></div>
</div></div>
<div class="section" id="trend"><div class="section-header"><span class="section-number">02</span><div class="section-line"></div><span class="section-title">招录趋势</span></div>
<div class="chart-card full" style="margin-bottom:16px"><div class="chart-title">历年招录人数与职位数</div>
<div class="chart-wrapper"><canvas id="trendChart"></canvas></div>
<div class="chart-note">电子信息类招录规模持续扩大，"""+str(growth_pct)+"""% 增长</div></div>
<div class="chart-grid">
<div class="chart-card"><div class="chart-title">应届 vs 社会人员</div><div class="chart-wrapper"><canvas id="freshChart"></canvas></div><div class="chart-note">当年应届（2023-2026）共 """+str(tc)+""" 人，社会人员共 """+str(ts)+""" 人</div></div>
<div class="chart-card"><div class="chart-title">学历分布</div><div class="chart-wrapper"><canvas id="eduChart"></canvas></div><div class="chart-note">本科以上为主体，研究生需求增长显著</div></div>
</div></div>
<div class="section" id="city"><div class="section-header"><span class="section-number">03</span><div class="section-line"></div><span class="section-title">城市分布</span></div>
<div class="chart-card full" style="margin-bottom:16px"><div class="chart-title">各城市招录分布</div><div class="chart-wrapper" id="cityChartWrapper"><canvas id="cityChart"></canvas></div><div class="chart-note">珠三角城市需求最为旺盛</div></div>
<div class="chart-card full"><div class="chart-title">城市 × 年份 热度矩阵</div>
<div class="year-tabs" id="heatYearTabs"></div>
<div class="chart-wrapper" style="height:auto;min-height:320px;overflow-x:auto"><table id="cityHeatTable" style="width:100%;border-collapse:collapse;font-size:13px"></table></div></div></div>
<div class="section" id="education"><div class="section-header"><span class="section-number">04</span><div class="section-line"></div><span class="section-title">学历</span></div>
<div class="chart-card full"><div class="chart-title">学历层次逐年变化</div><div class="chart-wrapper"><canvas id="eduTrendChart"></canvas></div><div class="chart-note">研究生从 """+str(edu_data.get('研究生',{}).get('2020',0))+"""→""" +str(edu_data.get('研究生',{}).get('2026',0))+""" 人</div></div></div>
<div class="section" id="positions"><div class="section-header"><span class="section-number">05</span><div class="section-line"></div><span class="section-title">岗位明细</span></div>
<div class="data-table"><div class="dt-header">可检索职位明细表</div>
<div class="tab-toolbar"><div class="year-tabs" id="yearTabs"></div></div>
<div class="tab-toolbar"><input class="search-input" id="posSearch" placeholder="搜索单位、职位、专业…"></div>
<div class="pos-table-wrap"><table class="pos-table"><thead><tr><th data-key="y">年份</th><th data-key="c">考区</th><th data-key="u">单位</th><th data-key="p">职位</th><th data-key="n">人数</th><th data-key="e">学历</th><th data-key="ft">类别</th></tr></thead><tbody id="posTableBody"></tbody></table></div></div></div>
</div>
<div class="footer"><p>数据来源：广东省 2020-2026 年考试录用公务员职位表</p></div>
<button class="back-top" id="backTop"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg></button>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script>
"""+ all_pos_js +"""
const YEARS = ["""+','.join(f'"{y}"' for y in years_sorted)+"""];
const TR = ["""+','.join(total_recruits_arr)+"""];
const TP = ["""+','.join(total_positions_arr)+"""];
const EL = ["""+','.join(f'"{e}"' for e in edu_keys)+"""];
const EV = ["""+edu_totals_js+"""];
const ETD = """+edu_trend_js+""";
const CD = """+city_data_json+""";
Chart.defaults.font.family = "'SF Pro Text','PingFang SC','Microsoft YaHei',sans-serif";
new Chart(document.getElementById('trendChart'),{type:'line',data:{labels:YEARS,datasets:[{label:'招录人数',data:TR,borderColor:'#0f2347',backgroundColor:'rgba(15,35,71,0.08)',fill:true,tension:0.3},{label:'职位数',data:TP,borderColor:'#3875b6',borderDash:[5,3],borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false}});
new Chart(document.getElementById('freshChart'),{type:'doughnut',data:{labels:['社会人员','往届应届','当年应届'],datasets:[{data:["""+str(ts)+","+str(ta)+","+str(tc)+"""],backgroundColor:['#b8432a','#b8952e','#2e8b8b'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'55%'}});
new Chart(document.getElementById('eduChart'),{type:'doughnut',data:{labels:EL,datasets:[{data:EV,backgroundColor:['#0f2347','#3875b6','#5fa8c7','#b8952e','#7a8b9e'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'55%'}});
var cities=Object.keys(CD).sort(function(a,b){var ta=0,tb=0;YEARS.forEach(function(y){ta+=CD[a][y]||0;tb+=CD[b][y]||0;});return tb-ta;});
var yc=['#c4d7e8','#a8c4df','#8bb1d5','#6e9ecc','#528bc2','#3578b9','#0f2347'];
new Chart(document.getElementById('cityChart'),{type:'bar',data:{labels:cities,datasets:YEARS.map(function(y,i){return{label:y+'年',data:cities.map(function(c){return CD[c][y]||0;}),backgroundColor:yc[i%yc.length]};})},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,scales:{x:{stacked:true,beginAtZero:true},y:{stacked:true}}}});
new Chart(document.getElementById('eduTrendChart'),{type:'bar',data:{labels:YEARS,datasets:ETD},options:{responsive:true,maintainAspectRatio:false,scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true}}}});
(function(){var y=YEARS;var ac=cities;var hy='all';var maxV=[];ac.forEach(function(c){y.forEach(function(yy){maxV.push(CD[c][yy]||0);});});maxV=Math.max.apply(null,maxV)||1;
function rHT(){var sy=hy==='all'?y:[hy];var mv=[];ac.forEach(function(c){sy.forEach(function(yy){mv.push(CD[c][yy]||0);});});mv=Math.max.apply(null,mv)||1;
var h='<thead><tr><th style="padding:8px 12px;text-align:left;font-weight:600;font-size:12px;border-bottom:1px solid #edeae3">城市</th>';sy.forEach(function(yy){h+='<th style="padding:8px 10px;text-align:right;font-size:12px;border-bottom:1px solid #edeae3">'+yy+'</th>';});h+='<th style="padding:10px 14px;text-align:right;font-size:12px;border-bottom:1px solid #edeae3">累计</th></tr></thead><tbody>';
ac.forEach(function(c){var t=0;h+='<tr><td style="padding:8px 12px;font-weight:600;white-space:nowrap;border-bottom:1px solid #edeae3;font-size:13px">'+c+'</td>';sy.forEach(function(yy){var v=CD[c][yy]||0;t+=v;var r=mv>0?v/mv:0;var bg="rgba(15,35,71,"+(0.05+r*0.58)+")";h+='<td style="text-align:right;padding:8px 10px;border-bottom:1px solid #edeae3"><span style="background:'+bg+';color:'+(v>0?'#0f2347':'#c0bbb5')+';font-weight:'+(v>0?'600':'400')+';padding:3px 8px;border-radius:3px;font-size:13px">'+v+'</span></td>';});h+='<td style="text-align:right;padding:8px 14px;font-weight:700;border-bottom:1px solid #edeae3;color:#0f2347;font-size:13px">'+t+'</td></tr>';});
document.getElementById('cityHeatTable').innerHTML=h;}
var c=document.getElementById('heatYearTabs');var b=document.createElement('button');b.className='year-tab active';b.textContent='全部';b.dataset.year='all';c.appendChild(b);
y.forEach(function(yy){var b=document.createElement('button');b.className='year-tab';b.textContent=yy;b.dataset.year=yy;c.appendChild(b);});
c.addEventListener('click',function(e){if(e.target.classList.contains('year-tab')){c.querySelectorAll('.year-tab').forEach(function(t){t.classList.remove('active');});e.target.classList.add('active');hy=e.target.dataset.year;rHT();}});rHT();})();
(function(){var all=ALL_POSITIONS,cy='all',st='';
function gF(){var l=cy==='all'?all:all.filter(function(p){return p.y===cy;});if(st){var s=st.toLowerCase();l=l.filter(function(p){return p.u.toLowerCase().indexOf(s)>=0||p.p.toLowerCase().indexOf(s)>=0||p.pr.toLowerCase().indexOf(s)>=0;});}return l;}
function rP(){var l=gF();document.getElementById('posTableBody').innerHTML=l.map(function(p){var fl={social:'社会',fresh_any:'往届',fresh_current:'当年应届'}[p.ft]||p.ft;return '<tr><td>'+p.y+'</td><td>'+p.c+'</td><td>'+p.u+'</td><td>'+p.p+'</td><td>'+p.n+'</td><td>'+p.e+'</td><td>'+fl+'</td></tr>';}).join('');}
var c=document.getElementById('yearTabs');var b=document.createElement('button');b.className='year-tab active';b.textContent='全部';b.dataset.year='all';c.appendChild(b);
YEARS.forEach(function(yy){var b=document.createElement('button');b.className='year-tab';b.textContent=yy;b.dataset.year=yy;c.appendChild(b);});
c.addEventListener('click',function(e){if(e.target.classList.contains('year-tab')){c.querySelectorAll('.year-tab').forEach(function(t){t.classList.remove('active');});e.target.classList.add('active');cy=e.target.dataset.year;rP();}});
document.getElementById('posSearch').addEventListener('input',function(e){st=e.target.value;rP();});rP();})();
window.addEventListener('scroll',function(){var y=window.scrollY;var h=document.documentElement.scrollHeight-window.innerHeight;document.getElementById('progressBar').style.width=(y/h*100).toFixed(1)+'%';document.getElementById('backTop').classList.toggle('visible',y>400);});
</script></body></html>"""

html = template.replace('<SCRIPT>', '').replace('</SCRIPT>', '')  # Safety cleanup

outpath = os.path.join(BASE, '广东省考电子信息类招录趋势.html')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'HTML generated: {len(html)} bytes, {len(details)} records')
