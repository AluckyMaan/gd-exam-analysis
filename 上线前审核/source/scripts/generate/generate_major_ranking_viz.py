#!/usr/bin/env python3
"""
广东省考专业招录深度分析 — 可视化生成脚本
生成单页HTML，包含5个Tab模块的交互式数据看板
"""
import json, os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'all_majors_ranking.json')
OUTPUT_FILE = os.path.join(BASE_DIR, '广东省考专业招录深度分析.html')

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

ranking_js = json.dumps(data['ranking'], ensure_ascii=False)
raw_ranking_js = json.dumps(data.get('raw_ranking', data['ranking']), ensure_ascii=False)
co_pairs_js = json.dumps(data['co_occurrence_pairs'], ensure_ascii=False)

# Build small HTML fragments in Python
def make_dd_opts(items):
    return ''.join(
        f'<option value="{i}">{m["major"].replace("（旧版乡镇招考代码）", "（旧版"+m["code"]+"）") if m.get("type")=="township" and m.get("code") else m["major"]}{" ("+m["code"]+")" if m.get("code") and m.get("type")!="township" else ""}</option>'
        for i, m in enumerate(items)
    )

def make_trend_opts(items, sel=0):
    return ''.join(
        f'<option value={i}{" selected" if i==sel else ""}>{m["major"].replace("（旧版乡镇招考代码）", "（旧版"+m["code"]+"）") if m.get("type")=="township" and m.get("code") else m["major"]}{" ("+m["code"]+")" if m.get("code") and m.get("type")!="township" else ""}</option>'
        for i, m in enumerate(items)
    )

def make_chk(items, limit=20, ck=3):
    return ''.join(
        f'<div class="compare-item"><input type="checkbox" value={i} {"checked" if i<ck else ""} onchange="updateCompare()"><span>{m["major"].replace("（旧版乡镇招考代码）", "（旧版"+m["code"]+"）") if m.get("type")=="township" and m.get("code") else m["major"]}{" ("+m["code"]+")" if m.get("code") and m.get("type")!="township" else ""}</span></div>'
        for i,m in enumerate(items[:limit])
    )

dd_opts = make_dd_opts(data['top30'])
tr_opts = make_trend_opts(data['top30'][:15])
tr_opts_2 = make_trend_opts(data['top30'][:15], 4)
tr_opts_3 = make_trend_opts(data['top30'][:15], 6)
chk_html = make_chk(data['ranking'], 20, 3)

sum_pos = data['summary']['total_position_rows']
sum_maj = data['summary']['unique_majors_found']
total_ranked = len(data['ranking'])
top_recruit = data['top30'][0]['total_recruits']

# Read the HTML template
template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省考专业招录深度分析（2020-2026）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif; background:#f5f7fa; color:#333; }
.container { max-width:1400px; margin:0 auto; padding:20px; }
h1 { text-align:center; font-size:28px; color:#1a3c6e; padding:25px 0 5px; }
.subtitle { text-align:center; color:#666; font-size:14px; margin-bottom:20px; }
.stats-bar { display:flex; justify-content:center; gap:40px; margin:15px 0 25px; flex-wrap:wrap; }
.stat-item { text-align:center; background:#fff; border-radius:10px; padding:15px 30px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.stat-num { font-size:28px; font-weight:700; color:#1a3c6e; }
.stat-label { font-size:13px; color:#888; margin-top:3px; }
.tabs { display:flex; gap:0; margin-bottom:0; background:#fff; border-radius:10px 10px 0 0; box-shadow:0 1px 3px rgba(0,0,0,0.06); overflow:hidden; }
.tab-btn { flex:1; padding:14px 10px; text-align:center; cursor:pointer; font-size:14px; font-weight:500; color:#666; border:none; background:transparent; transition:all 0.2s; position:relative; }
.tab-btn:hover { background:#f0f4ff; color:#1a3c6e; }
.tab-btn.active { color:#1a3c6e; font-weight:600; }
.tab-btn.active::after { content: ""; position:absolute; bottom:0; left:20%; width:60%; height:3px; background:#1a3c6e; border-radius:3px 3px 0 0; }
.tab-content { display:none; background:#fff; border-radius:0 0 10px 10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); min-height:500px; }
.tab-content.active { display:block; }
.chart-box { width:100%; height:520px; }
.chart-box-sm { width:100%; height:380px; }
.chart-box-full { width:100%; height:520px; }
.network-wrap { width:100%; height:600px; }
.table-wrap { overflow-x:auto; margin-top:15px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { background:#f0f4ff; color:#1a3c6e; padding:10px 8px; text-align:center; font-weight:600; border-bottom:2px solid #d0d9e8; position:sticky; top:0; }
td { padding:8px; text-align:center; border-bottom:1px solid #eee; }
tr:hover td { background:#f8faff; }
.rank-num { font-weight:600; }
.top3 { color:#e67e22; }
.top5 { color:#2980b9; }
.select-bar { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:15px; }
.select-bar label { font-weight:500; color:#555; }
.select-bar select, .select-bar input { padding:6px 12px; border:1px solid #d0d5dd; border-radius:6px; font-size:13px; }
.sub-select-wrap { margin-left:auto; display:none; align-items:center; gap:8px; }
.sub-select-wrap select { min-width:220px; max-width:320px; }
.metrics { display:flex; gap:15px; flex-wrap:wrap; margin:15px 0; }
.metric { flex:1; min-width:140px; background:#f8faff; border-radius:8px; padding:12px 16px; text-align:center; }
.metric-val { font-size:22px; font-weight:700; color:#1a3c6e; }
.metric-label { font-size:12px; color:#888; margin-top:2px; }
.up { color:#e74c3c; } .down { color:#27ae60; } .flat { color:#888; }
.detail-panel { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
.detail-full { grid-column:1/-1; }
@media (max-width:768px) { .detail-panel { grid-template-columns:1fr; } }
.tags { display:flex; gap:6px; flex-wrap:wrap; margin:5px 0; }
.tag { background:#e8edf5; padding:3px 10px; border-radius:12px; font-size:12px; color:#555; }
.tag.highlight { background:#1a3c6e; color:#fff; }
.tag-township { background:#fff3e0; color:#e65100; border:1px solid #ffcc80; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:500; white-space:nowrap; }
.township-suffix { font-size:0.55em; opacity:0.9; white-space:nowrap; }
#networkChart { width:100%; height:600px; }
.compare-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:6px; max-height:300px; overflow-y:auto; padding:10px; background:#f8faff; border-radius:8px; }
.compare-item { display:flex; align-items:center; gap:5px; font-size:13px; }
.compare-item input { cursor:pointer; }
.help-btn { display:inline-block; width:22px; height:22px; line-height:22px; text-align:center; border-radius:50%; background:#1a3c6e; color:#fff; font-size:13px; font-weight:700; cursor:pointer; margin-left:8px; vertical-align:middle; position:relative; top:-1px; user-select:none; }
.help-btn:hover { background:#2a5c9e; }
.modal-overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.4); z-index:1000; }
.modal-overlay.show { display:flex; align-items:center; justify-content:center; }
.modal-content { background:#fff; border-radius:12px; padding:25px 30px; max-width:560px; width:90%; max-height:80vh; overflow-y:auto; box-shadow:0 10px 40px rgba(0,0,0,0.2); position:relative; }
.modal-close { position:absolute; top:10px; right:14px; font-size:22px; cursor:pointer; color:#888; border:none; background:none; line-height:1; }
.modal-close:hover { color:#333; }
.modal-content h3 { margin-bottom:16px; color:#1a3c6e; font-size:16px; }
.modal-term { margin-bottom:12px; padding:10px 14px; background:#f8faff; border-radius:8px; border-left:3px solid #1a3c6e; }
.modal-term .t { font-weight:600; color:#1a3c6e; display:block; margin-bottom:3px; }
.modal-term .d { font-size:13px; color:#555; line-height:1.5; }
</style>
</head>
<body>
<div class="container">
<h1>广东省公务员招录 · 专业热度深度分析 <span class="help-btn" onclick="showHelp()">?</span></h1>
<p class="subtitle">数据来源：广东省2020-2026年考试录用公务员职位表 | 共覆盖 __SUM_POS__ 个职位、__SUM_MAJ__ 个专业</p>

<div class="modal-overlay" id="helpModal" onclick="if(event.target==this)hideHelp()">
  <div class="modal-content">
    <button class="modal-close" onclick="hideHelp()">&times;</button>
    <h3>📖 指标说明</h3>
    <div class="modal-term"><span class="t">🔵 纯洁度</span><span class="d">该专业独占岗位的比例。100% = 该专业出现时都是单独招录；0% = 每次都和其他专业一同招录。</span></div>
    <div class="modal-term"><span class="t">🟠 竞争指数</span><span class="d">该专业出现时，同一岗位平均还有几个其他专业同时招录。数值越大，说明该岗位的潜在竞争者越多。</span></div>
    <div class="modal-term"><span class="t">🟢 关联专业 / 关联率</span><span class="d">经常和该专业出现在同一岗位要求里的其他专业。关联率 = 两者共同出现的招录人数 / 该专业总招录人数 × 100%。</span></div>
    <div class="modal-term"><span class="t">📈 增长率</span><span class="d">(2024-2026 年均招录人数 − 2020-2022 年均招录人数) / 基准。正数表示近年需求上升，负数表示下降。</span></div>
    <div class="modal-term"><span class="t">🎓 应届占比</span><span class="d">该专业限应届毕业生报考的岗位招录人数，占该专业总招录人数的比例。</span></div>
    <div class="modal-term"><span class="t">🏷️ 旧版乡镇招考代码</span><span class="d">标有"旧版乡镇招考代码"的专业来自2020-2023年广东省考乡镇职位自定的分类代码体系（如"01规划建设类""03法律类"），与标准学科专业目录不同，2024年后已停止使用。</span></div>
    <div class="modal-term"><span class="t">📋 专业代码</span><span class="d">专业名称后括号内的代码（如 A0301、B0301）来自教育部专业目录或广东省考自定分类编号，用于精确定位专业归属。</span></div>
  </div>
</div>

<div class="stats-bar">
  <div class="stat-item"><div class="stat-num">__TOTAL_RANKED__</div><div class="stat-label">统计专业数</div></div>
  <div class="stat-item"><div class="stat-num">__SUM_POS__</div><div class="stat-label">总职位记录</div></div>
  <div class="stat-item"><div class="stat-num">2020-2026</div><div class="stat-label">数据跨度</div></div>
  <div class="stat-item"><div class="stat-num">__TOP_RECRUIT__</div><div class="stat-label">榜首招录总人数</div></div>
</div>

<div class="tabs" id="tabHeaders">
  <button class="tab-btn active" data-tab="tab1">Top30排名</button>
  <button class="tab-btn" data-tab="tab2">专业详情</button>
  <button class="tab-btn" data-tab="tab3">🔗 关联网络</button>
  <button class="tab-btn" data-tab="tab4">趋势总览</button>
  <button class="tab-btn" data-tab="tab5">综合对比</button>
</div>

<!-- Tab1 -->
<div class="tab-content active" id="tab1">
  <div class="select-bar">
    <label>显示：</label>
    <select id="rankMode" onchange="switchRankMode()">
      <option value="recruits">按招录总人数</option>
      <option value="positions">按职位总数</option>
      <option value="purity">按纯洁度</option>
      <option value="growth">按增长率</option>
    </select>
    <input type="text" id="rankSearch" placeholder="搜索专业..." oninput="filterRankTable()" style="flex:1;max-width:250px;">
    <span id="rankCount" style="color:#888;font-size:13px;"></span>
  </div>
  <div class="chart-box" id="rankChart"></div>
  <div class="table-wrap" id="rankTableWrap"></div>
  <div style="margin-top:28px;border-top:1px solid var(--border);padding-top:22px;">
    <h3 style="margin:0 0 8px;color:var(--primary);">招录最少 Top30 专业</h3>
    <p style="margin:0 0 14px;color:#888;font-size:13px;">按2020-2026年累计招录人数从少到多排序，用来观察低频、冷门或目录边缘专业。</p>
    <div class="chart-box" id="lowRankChart"></div>
    <div class="table-wrap" id="lowRankTableWrap"></div>
  </div>
</div>

<!-- Tab2 -->
<div class="tab-content" id="tab2">
  <div class="select-bar">
    <label>选择专业：</label>
    <select id="detailSelect" onchange="showDetail()">
      __DD_OPTS__
    </select>
    <span class="sub-select-wrap" id="subMajorWrap">
      <label>子专业：</label>
      <select id="subMajorSelect" onchange="showDetail(false)">
        <option value="">大类汇总</option>
      </select>
    </span>
  </div>
  <div id="detailContent"></div>
</div>

<!-- Tab3 -->
<div class="tab-content" id="tab3">
  <div class="select-bar">
    <label>显示专业数：</label>
    <select id="networkNodes" onchange="buildNetwork()">
      <option value="30">Top30</option>
      <option value="50" selected>Top50</option>
      <option value="80">Top80</option>
    </select>
    <label style="margin-left:15px;">最低关联阈值：</label>
    <select id="networkThreshold" onchange="buildNetwork()">
      <option value="100">>=100人</option>
      <option value="200" selected>>=200人</option>
      <option value="500">>=500人</option>
    </select>
  </div>
  <div class="network-wrap" id="networkChart"></div>
  <p style="text-align:center;color:#888;font-size:12px;">节点大小 = 招录人数，连线粗细 = 关联强度，拖动可交互</p>
</div>

<!-- Tab4 -->
<div class="tab-content" id="tab4">
  <div class="select-bar">
    <label>视图：</label>
    <select id="trendView" onchange="switchTrendView()">
      <option value="grow">增长最快 Top20</option>
      <option value="decline">下降最快 Top20</option>
      <option value="custom">自定义对比</option>
    </select>
    <div id="customSelectArea" style="display:none;flex:1;gap:8px;">
      <select id="trendMajor1" onchange="drawTrendLines()">__TR_OPTS__</select>
      <select id="trendMajor2" onchange="drawTrendLines()">__TR_OPTS2__</select>
      <select id="trendMajor3" onchange="drawTrendLines()">__TR_OPTS3__</select>
    </div>
  </div>
  <div id="trendChart" class="chart-box-full"></div>
  <div id="trendTable" style="margin-top:15px;"></div>
</div>

<!-- Tab5 -->
<div class="tab-content" id="tab5">
  <div class="select-bar">
    <label>选择对比专业（最多5个）：</label>
  </div>
  <div class="compare-grid" id="compareCheckboxes">
    __CHK_HTML__
  </div>
  <div style="margin-top:15px;display:flex;gap:15px;flex-wrap:wrap;">
    <div style="flex:1;min-width:300px;"><div id="radarChart" class="chart-box-sm"></div><div id="radarEmpty" style="display:none;padding:60px 20px;text-align:center;color:#888;height:380px;line-height:260px;font-size:15px;">请至少选择 2 个专业进行对比</div></div>
    <div style="flex:1;min-width:300px;"><div id="compareBarChart" class="chart-box-sm"></div></div>
  </div>
  <div id="compareTable" style="margin-top:15px;"></div>
</div>

</div>

<script>
var RANKING = __RANKING_JS__;
var RAW_RANKING = __RAW_RANKING_JS__;
var TOP30 = RANKING.slice(0, 30);
var LOW30 = RANKING.slice().sort(function(a,b){
  if (a.total_recruits !== b.total_recruits) return a.total_recruits - b.total_recruits;
  return a.total_positions - b.total_positions;
}).slice(0, 30);
var CO_PAIRS = __CO_PAIRS_JS__;
var RAW_BY_MAJOR = {};
function fmtMajor(name) {
  var suffix = "\uff08\u65e7\u7248\u4e61\u9547\u62db\u8003\u4ee3\u7801\uff09";
  if (name.indexOf(suffix) > -1) {
    var main = name.replace(suffix, "");
    return main + '<span class="township-suffix">' + suffix + '</span>';
  }
  return name;
}
function shortMajor(name, code) {
  // For township entries, show compact plain-text version
  var suffix = "\uff08\u65e7\u7248\u4e61\u9547\u62db\u8003\u4ee3\u7801\uff09";
  if (name.indexOf(suffix) > -1) {
    var main = name.replace(suffix, "");
    if (code) { return main + '(' + code + ')'; }
    return main;
  }
  return name;
}function resizeVisibleCharts() {
  setTimeout(function() {
    try {
      document.querySelectorAll('.tab-content.active [id]').forEach(function(el) {
        var inst = echarts.getInstanceByDom(el);
        if (inst) inst.resize();
      });
    } catch(e) {}
  }, 50);
}

document.querySelectorAll('.tab-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    this.classList.add('active');
    var tabId = this.dataset.tab;
    document.getElementById(tabId).classList.add('active');

    // Lazy-init each tab on first visit
    if (tabId == 'tab1') { initRankChart(); filterRankTable(); initLowRankChart(); renderLowRankTable(); }
    if (tabId == 'tab2') { if (!tabInited.tab2) { tabInited.tab2 = true; } setTimeout(function() { showDetail(); }, 50); }
    if (tabId == 'tab3') { if (!tabInited.tab3) { tabInited.tab3 = true; setTimeout(buildNetwork, 200); } resizeVisibleCharts(); }
    if (tabId == 'tab4') { if (!tabInited.tab4) { tabInited.tab4 = true; } setTimeout(setupTrendView, 100); }
    if (tabId == 'tab5') { if (!tabInited.tab5) { tabInited.tab5 = true; } setTimeout(updateCompare, 100); }

    resizeVisibleCharts();
  });
});

// Window resize handler
window.addEventListener('resize', function() {
  try {
    document.querySelectorAll('[id]').forEach(function(el) {
      var inst = echarts.getInstanceByDom(el);
      if (inst) inst.resize();
    });
  } catch(e) {}
});

// ====== Tab1: Top30 ======
var rankChart = null;
var lowRankChart = null;
function switchRankMode() { initRankChart(); filterRankTable(); initLowRankChart(); renderLowRankTable(); }

function initRankChart() {
  var mode = document.getElementById('rankMode').value;
  var sorted = [...TOP30];
  var km = {recruits:'total_recruits',positions:'total_positions',purity:'purity',growth:'growth_rate'};
  var key = km[mode] || 'total_recruits';
  sorted.sort(function(a,b){return b[key]-a[key]});

    var names = sorted.map(function(m){return shortMajor(m.major, m.code);});
  var vals = sorted.map(function(m){return m[key]});
  var unit = {recruits:'招录总人数',positions:'职位总数',purity:'纯洁度(%)',growth:'增长率(%)'}[mode];

  // Gradient color: top items (rank 1) darkest, bottom items (rank 30) lightest
  function barColor(idx, total) {
    var t = idx / Math.max(total - 1, 1);  // 0 at idx=0 (last place), 1 at idx=last (first place)
    // Interpolate from light (#deebf7 = rgb(222,235,247)) to dark (#08306b = rgb(8,48,107))
    var r = Math.round(222 + (8 - 222) * t);
    var g = Math.round(235 + (48 - 235) * t);
    var b = Math.round(247 + (107 - 247) * t);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  var opt = {
    title: { text: '广东省考专业招录 Top30 ('+unit+')', left:'center', textStyle:{fontSize:16} },
    tooltip: { trigger:'axis', axisPointer:{type:'shadow'},
      formatter: function(params) {
        var i = params[0].dataIndex;
        var m = sorted[sorted.length-1-i];
        var dn = shortMajor(m.major, m.code);
        var sub = '';
        if (m.merged_from && m.merged_from.length > 0) {
          sub = '<br/><span style=\"font-size:12px;color:#888;\">包含: '+m.merged_from.slice(0,8).join(', ')+(m.merged_from.length>8?'<br/>等'+m.merged_from.length+'个子专业':'')+'</span>';
        }
        return '<b>'+dn+'</b><br/>招录: '+m.total_recruits+'人 | 职位: '+m.total_positions+'个<br/>纯洁度: '+m.purity+'% | 增长率: '+m.growth_rate+'%<br/>应届占比: '+m.fresh_ratio+'%'+sub;
      }
    },
    grid: { left:160, right:'12%', top:'12%', bottom:'5%' },
    xAxis: { type:'value', name: unit, axisLabel:{fontSize:11} },
    yAxis: { type:'category', data: [...names].reverse(), axisLabel:{fontSize:12, interval:0}, axisLine:{show:false}, axisTick:{show:false} },
    series: [{
      type:'bar',
      data: [...vals].reverse().map(function(v,i){ return {value:v, itemStyle:{color:barColor(i, vals.length)}}; }),
      barMaxWidth: 20,
      label: { show:true, position:'right', formatter:function(p){return p.value+(mode=='purity'?'%':(mode=='growth'?'%':''));}, fontSize:10 }
    }]
  };
  if (!rankChart) rankChart = echarts.init(document.getElementById('rankChart'));
  rankChart.setOption(opt);
  rankChart.on('click', function(params) {
    var i = sorted.length - 1 - params.dataIndex;
    var m = sorted[i];
    var idx = RANKING.indexOf(m);
    if (idx >= 0) { document.getElementById('detailSelect').value = idx; document.querySelectorAll('.tab-btn')[1].click(); }
  });
}

function filterRankTable() {
  var q = document.getElementById('rankSearch').value.trim().toLowerCase();
  var mode = document.getElementById('rankMode').value;
  var km = {recruits:'total_recruits',positions:'total_positions',purity:'purity',growth:'growth_rate'};
  var key = km[mode] || 'total_recruits';
  var sorted = [...TOP30].sort(function(a,b){return b[key]-a[key]});
  var filtered = q ? sorted.filter(function(m){return m.major.toLowerCase().indexOf(q)>=0}) : sorted;
  document.getElementById('rankCount').textContent = '显示 '+filtered.length+'/'+sorted.length+' 个专业';

  var html = '<table><thead><tr><th title="按招录总人数从高到低排序">排名</th><th>专业名称</th><th title="2020-2026年该专业累计招录总人数">招录总人数</th><th title="要求该专业的职位总数">职位总数</th><th title="总招录人数÷7年">年均</th><th title="该专业独占的职位比例。越高说明专属岗位越多">纯洁度</th><th title="该专业出现时同岗平均还有几个其他专业">竞争指数</th><th title="(2024-2026均招录-2020-2022均招录)÷基准">增长率</th><th title="限应届报考的岗位招录人数占比">应届占比</th></tr></thead><tbody>';
  filtered.forEach(function(m) {
    var tcl = m.growth_rate > 10 ? 'up' : (m.growth_rate < -10 ? 'down' : 'flat');
    var rcl = m.rank <= 3 ? 'top3' : (m.rank <= 10 ? 'top5' : '');
    var avg = Math.round(m.total_recruits/7);
    html += '<tr><td class="rank-num '+rcl+'">'+m.rank+'</td><td><a href="javascript:void(0)" onclick="goToDetail('+RANKING.indexOf(m)+')" title="'+(m.merged_from?m.major+' 包含: '+m.merged_from.join(', '):m.major)+'">'+m.major+'</a>'+(m.code?'&nbsp;<span style="color:#999;font-size:11px;">'+m.code+'</span>':'')+(m.type=='township'?' <span class="tag-township">乡镇</span>':'')+(m.merged_from&&m.merged_from.length>0?' <span style="color:#888;font-size:11px;cursor:help;" title="'+m.merged_from.join(', ')+'">(+'+m.merged_from.length+'专业)</span>':'')+'</td><td>'+m.total_recruits+'</td><td>'+m.total_positions+'</td><td>'+avg+'</td><td>'+m.purity+'%</td><td>'+m.competition_index+'</td><td class="'+tcl+'">'+(m.growth_rate>0?'+':'')+m.growth_rate+'%</td><td>'+m.fresh_ratio+'%</td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('rankTableWrap').innerHTML = html;
}

function initLowRankChart() {
  var sorted = LOW30.slice().sort(function(a,b){
    if (a.total_recruits !== b.total_recruits) return a.total_recruits - b.total_recruits;
    return a.total_positions - b.total_positions;
  });
  var names = sorted.map(function(m){return shortMajor(m.major, m.code);});
  var vals = sorted.map(function(m){return m.total_recruits});

  function barColor(idx, total) {
    var t = idx / Math.max(total - 1, 1);
    var r = Math.round(247 + (184 - 247) * t);
    var g = Math.round(245 + (149 - 245) * t);
    var b = Math.round(240 + (46 - 240) * t);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  var opt = {
    title: { text: '招录最少 Top30 专业（累计招录人数）', left:'center', textStyle:{fontSize:16} },
    tooltip: { trigger:'axis', axisPointer:{type:'shadow'},
      formatter: function(params) {
        var i = params[0].dataIndex;
        var m = sorted[sorted.length-1-i];
        var dn = shortMajor(m.major, m.code);
        return '<b>'+dn+'</b><br/>招录: '+m.total_recruits+'人 | 职位: '+m.total_positions+'个<br/>纯洁度: '+m.purity+'% | 增长率: '+m.growth_rate+'%<br/>应届占比: '+m.fresh_ratio+'%';
      }
    },
    grid: { left:190, right:'12%', top:'12%', bottom:'5%' },
    xAxis: { type:'value', name:'招录总人数', axisLabel:{fontSize:11} },
    yAxis: { type:'category', data:[...names].reverse(), axisLabel:{fontSize:12, interval:0}, axisLine:{show:false}, axisTick:{show:false} },
    series: [{
      type:'bar',
      data: [...vals].reverse().map(function(v,i){ return {value:v, itemStyle:{color:barColor(i, vals.length)}}; }),
      barMaxWidth: 20,
      label: { show:true, position:'right', fontSize:10 }
    }]
  };
  if (!lowRankChart) lowRankChart = echarts.init(document.getElementById('lowRankChart'));
  lowRankChart.setOption(opt);
  lowRankChart.off('click');
  lowRankChart.on('click', function(params) {
    var i = sorted.length - 1 - params.dataIndex;
    var m = sorted[i];
    var idx = RANKING.indexOf(m);
    if (idx >= 0) { document.getElementById('detailSelect').value = idx; document.querySelectorAll('.tab-btn')[1].click(); }
  });
}

function renderLowRankTable() {
  var sorted = LOW30.slice().sort(function(a,b){
    if (a.total_recruits !== b.total_recruits) return a.total_recruits - b.total_recruits;
    return a.total_positions - b.total_positions;
  });
  var html = '<table><thead><tr><th title="在总排名中的名次">总排名</th><th>专业名称</th><th title="2020-2026年该专业累计招录总人数">招录总人数</th><th title="要求该专业的职位总数">职位总数</th><th title="总招录人数÷7年">年均</th><th title="该专业独占的职位比例。越高说明专属岗位越多">纯洁度</th><th title="该专业出现时同岗平均还有几个其他专业">竞争指数</th><th title="(2024-2026均招录-2020-2022均招录)÷基准">增长率</th><th title="限应届报考的岗位招录人数占比">应届占比</th></tr></thead><tbody>';
  sorted.forEach(function(m) {
    var tcl = m.growth_rate > 10 ? 'up' : (m.growth_rate < -10 ? 'down' : 'flat');
    var avg = Math.round(m.total_recruits/7);
    html += '<tr><td class="rank-num">'+m.rank+'</td><td><a href="javascript:void(0)" onclick="goToDetail('+RANKING.indexOf(m)+')" title="'+(m.merged_from?m.major+' 包含: '+m.merged_from.join(', '):m.major)+'">'+m.major+'</a>'+(m.code?'&nbsp;<span style="color:#999;font-size:11px;">'+m.code+'</span>':'')+(m.type=='township'?' <span class="tag-township">乡镇</span>':'')+(m.merged_from&&m.merged_from.length>0?' <span style="color:#888;font-size:11px;cursor:help;" title="'+m.merged_from.join(', ')+'">(+'+m.merged_from.length+'专业)</span>':'')+'</td><td>'+m.total_recruits+'</td><td>'+m.total_positions+'</td><td>'+avg+'</td><td>'+m.purity+'%</td><td>'+m.competition_index+'</td><td class="'+tcl+'">'+(m.growth_rate>0?'+':'')+m.growth_rate+'%</td><td>'+m.fresh_ratio+'%</td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('lowRankTableWrap').innerHTML = html;
}

function goToDetail(idx) {
  if (idx<0) return;
  var sel = document.getElementById('detailSelect');
  if (sel) sel.value = idx;
  // Click Tab2 - tab switch handler will call showDetail with 50ms delay
  var tabs = document.querySelectorAll('.tab-btn');
  if (tabs[1]) tabs[1].click();
}

// ====== Tab2: 详情 ======
function syncSubMajorSelect(parentMajor, resetSub) {
  var wrap = document.getElementById('subMajorWrap');
  var sel = document.getElementById('subMajorSelect');
  if (!wrap || !sel) return null;
  var subItems = (parentMajor.merged_from || [])
    .map(function(name) { return RAW_BY_MAJOR[name]; })
    .filter(function(m) { return !!m; })
    .sort(function(a, b) { return b.total_recruits - a.total_recruits; });
  if (subItems.length === 0) {
    wrap.style.display = 'none';
    sel.innerHTML = '<option value="">大类汇总</option>';
    return null;
  }
  var previous = resetSub === false ? sel.value : '';
  var html = '<option value="">大类汇总：'+parentMajor.major+'</option>';
  subItems.forEach(function(s) {
    var label = s.code ? s.major + ' (' + s.code + ')' : s.major;
    html += '<option value="'+s.major+'">'+label+' · '+s.total_recruits+'人</option>';
  });
  sel.innerHTML = html;
  if (previous && subItems.some(function(s) { return s.major === previous; })) {
    sel.value = previous;
  } else {
    sel.value = '';
  }
  wrap.style.display = 'inline-flex';
  return sel.value ? RAW_BY_MAJOR[sel.value] : null;
}

function findMajorInfo(name) {
  return RANKING.find(function(r){return r.major == name;}) || RAW_BY_MAJOR[name];
}

function showDetail(resetSub) {
  var idx = parseInt(document.getElementById('detailSelect').value);
  var parentMajor = RANKING[idx];
  if (!parentMajor) return;
  var subMajor = syncSubMajorSelect(parentMajor, resetSub);
  var m = subMajor || parentMajor;
  var viewingSub = !!subMajor;
  var years = ['2020','2021','2022','2023','2024','2025','2026'];
  var yd = years.map(function(y){return {year:y, r:m.yearly[y].recruits, p:m.yearly[y].positions};});

  var html = '';
  if (viewingSub) {
    html += '<p><b>当前视图：</b><span class="tag highlight">'+fmtMajor(m.major)+'</span> 子专业详情，所属大类为 <span class="tag">'+fmtMajor(parentMajor.major)+'</span>。</p>';
  }
  html += '<div class="metrics">'
    + '<div class="metric"><div class="metric-val">'+m.total_recruits+'</div><div class="metric-label">招录总人数</div></div>'
    + '<div class="metric"><div class="metric-val">'+m.purity+'%</div><div class="metric-label">纯洁度(独占比)</div></div>'
    + '<div class="metric"><div class="metric-val">'+m.competition_index+'</div><div class="metric-label">竞争指数</div></div>'
    + '<div class="metric"><div class="metric-val">'+(m.growth_rate>0?'+':'')+m.growth_rate+'%</div><div class="metric-label">增长率</div></div>'
    + '<div class="metric"><div class="metric-val">'+m.fresh_ratio+'%</div><div class="metric-label">应届占比</div></div>'
    + '<div class="metric"><div class="metric-val">'+m.city_coverage+'</div><div class="metric-label">覆盖考区</div></div></div>';
  html += '<p><b>独占/共享：</b>'+m.alone_positions+'个职位独占，'+m.shared_positions+'个职位共享';
  if (m.code) { html += ' &nbsp;|&nbsp; <b>代码：</b>'+m.code; }
  if (m.type == 'township') {
    html += ' &nbsp;|&nbsp; <span class="tag-township">旧版乡镇招考代码</span> 该专业来自2020-2023年广东省考乡镇职位自定的分类代码体系（如"01规划建设类""06法律类"），与标准学科专业目录不同，2024年后已停止使用。';
  }
  if (!viewingSub && parentMajor.merged_from && parentMajor.merged_from.length > 0) {
    html += '</p><p><b>📦 包含的子专业（'+parentMajor.merged_from.length+'个）：</b></p><div class="tags">';
    parentMajor.merged_from.forEach(function(s){html += '<span class="tag">'+fmtMajor(s)+'</span>';});
    html += '</div>';
  } else {
    html += '</p>';
  }

  html += '<div class="detail-panel">';
  html += '<div><div id="detailTrend" style="height:280px;"></div></div>';
  html += '<div><div id="detailCooccur" style="height:280px;"></div></div>';
  html += '<div><div id="detailCity" style="height:280px;"></div></div>';
  html += '<div><div id="detailYearBar" style="height:280px;"></div></div></div>';

  var eduKeys = Object.keys(m.education_distribution || {});
  if (eduKeys.length > 0) {
    eduKeys.sort(function(a,b){return m.education_distribution[b]-m.education_distribution[a]});
    html += '<div class="detail-full"><p><b>学历分布：</b></p><div class="tags">';
    eduKeys.forEach(function(k){html += '<span class="tag">'+k+': '+m.education_distribution[k]+'</span>';});
    html += '</div></div>';
  }

  if (m.top_co_occurrences && m.top_co_occurrences.length > 0) {
    html += '<div class="detail-full"><p><b>关联专业 Top5：</b></p><div class="tags">';
    m.top_co_occurrences.forEach(function(co){
      // Check if this associated major has merged_from in the ranking
      var assoc = findMajorInfo(co.major);
      var subInfo = '';
      if (assoc && assoc.merged_from && assoc.merged_from.length > 0) {
        subInfo = ' ('+assoc.merged_from.slice(0,3).join(', ')+(assoc.merged_from.length>3?'…':'')+')';
      }
      html += '<span class="tag highlight" title="'+co.major+subInfo+'">'+co.major+' ('+co.co_rate+'%)</span>';
    });
    html += '</div></div>';
  }

  document.getElementById('detailContent').innerHTML = html;

  // 延迟渲染确保DOM布局完成后再init ECharts
  setTimeout(function() {
    // Trend line
    var t1 = document.getElementById('detailTrend');
    if (t1) {
      var tc = echarts.init(t1);
      tc.setOption({
        title:{text:'年份趋势',textStyle:{fontSize:13},left:'center'},
        tooltip:{trigger:'axis'}, grid:{left:'12%',right:'5%',top:'20%',bottom:'12%'},
        xAxis:{type:'category',data:years},
        yAxis:{type:'value',name:'招录人数'},
        series:[{type:'line',data:yd.map(function(d){return d.r;}),smooth:true,lineStyle:{width:3,color:'#1a3c6e'},
          areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(26,60,110,0.3)'},{offset:1,color:'rgba(26,60,110,0.02)'}])}}]
      });
    }

    // Co-occurrence
    if (m.top_co_occurrences && m.top_co_occurrences.length > 0) {
      var t2 = document.getElementById('detailCooccur');
      if (t2) {
        var cc = echarts.init(t2);
        cc.setOption({
          title:{text:'关联专业 Top5',textStyle:{fontSize:13},left:'center'},
          tooltip:{trigger:'axis',formatter:function(p){
            var nm = p[0].name;
            var assoc = findMajorInfo(nm);
            var info = assoc && assoc.merged_from ? ' 包含' + assoc.merged_from.length + '个子专业' : '';
            return nm+'<br/>关联率: '+p[0].value+'%'+info;
          }},
          grid:{left:'15%',right:'5%',top:'20%',bottom:'12%'},
          yAxis:{type:'category',data:m.top_co_occurrences.map(function(c){return c.major;}).reverse()},
          xAxis:{type:'value',name:'关联率(%)',max:100},
          series:[{type:'bar',data:m.top_co_occurrences.map(function(c){return c.co_rate;}).reverse().map(function(v){return{value:v,itemStyle:{color:'#4292c6'}};}),label:{show:true,position:'right',formatter:function(p){return p.value+'%';}}}]
        });
      }
    }

    // City
    var cities = Object.entries(m.city_top||{}).sort(function(a,b){return b[1]-a[1];}).slice(0,8);
    if (cities.length > 0) {
      var t3 = document.getElementById('detailCity');
      if (t3) {
        var ct = echarts.init(t3);
        ct.setOption({
          title:{text:'城市分布 Top8',textStyle:{fontSize:13},left:'center'},
          tooltip:{trigger:'axis'}, grid:{left:'12%',right:'5%',top:'20%',bottom:'12%'},
          yAxis:{type:'category',data:cities.map(function(c){return c[0];}).reverse()},
          xAxis:{type:'value',name:'招录人数'},
          series:[{type:'bar',data:cities.map(function(c){return c[1];}).reverse().map(function(v){return{value:v,itemStyle:{color:'#6baed6'}};}),label:{show:true,position:'right'}}]
        });
      }
    }

    // Year bar
    var t4 = document.getElementById('detailYearBar');
    if (t4) {
      var yb = echarts.init(t4);
      yb.setOption({
        title:{text:'各年职位数',textStyle:{fontSize:13},left:'center'},
        tooltip:{trigger:'axis'}, grid:{left:'12%',right:'5%',top:'20%',bottom:'12%'},
        xAxis:{type:'category',data:years},
        yAxis:{type:'value',name:'职位数'},
        series:[{type:'bar',data:yd.map(function(d){return d.p;}),itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#4292c6'},{offset:1,color:'#9ecae1'}])}}]
      });
    }
  }, 100);
}

// ====== Tab3: 关联网络 ======
var networkChart = null;
function buildNetwork() {
  var maxN = parseInt(document.getElementById('networkNodes').value);
  var minW = parseInt(document.getElementById('networkThreshold').value);
  var tms = RANKING.slice(0, maxN);
  var tn = new Set(tms.map(function(m){return m.major;}));

  var nodes = tms.map(function(m){return {id:m.major, name:shortMajor(m.major, m.code), symbolSize:Math.max(5,Math.min(40,Math.sqrt(m.total_recruits)*0.6)), value:m.total_recruits};});
  var edges = [];
  var seen = new Set();
  CO_PAIRS.forEach(function(p) {
    var a=p.majors[0], b=p.majors[1];
    if (!tn.has(a)||!tn.has(b)) return;
    if (p.recruits < minW) return;
    var key = a<b ? a+':'+b : b+':'+a;
    if (seen.has(key)) return;
    seen.add(key);
    edges.push({source:a, target:b, value:p.recruits, lineStyle:{width:Math.max(1,Math.min(8,p.recruits/300))}});
  });

  if (!networkChart) networkChart = echarts.init(document.getElementById('networkChart'));
  networkChart.setOption({
    title:{text:'专业关联网络(Top'+maxN+', 关联>='+minW+'人)',left:'center',textStyle:{fontSize:15}},
    tooltip:{formatter:function(p){return p.data.value?p.data.name+'<br/>关联: '+p.data.value+'人':p.name+'<br/>招录: '+p.data.value+'人';}},
    series:[{
      type:'graph', layout:'force', roam:true, draggable:true, focusNodeAdjacency:true,
      edgeSymbol:['none','none'], edgeLabel:{show:false},
      force:{repulsion:300, edgeLength:[50,200], gravity:0.1, friction:0.1},
      data:nodes, edges:edges,
      label:{show:true, position:'right', fontSize:10},
      lineStyle:{color:'source', opacity:0.3, curveness:0.3},
      emphasis:{focus:'adjacency', lineStyle:{width:5}}
    }]
  });
}

// ====== Tab4: 趋势 ======
function setupTrendView() { switchTrendView(); }

function switchTrendView() {
  var v = document.getElementById('trendView').value;
  var a = document.getElementById('customSelectArea');
  a.style.display = (v=='custom')?'inline-flex':'none';
  // Chart init is inside drawGrowthChart/drawTrendLines with setTimeout
  if (v=='grow') drawGrowthChart(true);
  else if (v=='decline') drawGrowthChart(false);
  else drawTrendLines();
}

function drawGrowthChart(isGrow) {
  var sorted = [...RANKING].filter(function(m){return m.total_recruits>=100;}).sort(function(a,b){return isGrow?b.growth_rate-a.growth_rate:a.growth_rate-b.growth_rate;});
  var topN = sorted.slice(0,20);

  setTimeout(function() {
    var el = document.getElementById('trendChart');
    if (!el) return;
    var tc = echarts.init(el);
    tc.setOption({
      title:{text:isGrow?'增长最快 Top20':'下降最快 Top20',left:'center',textStyle:{fontSize:15}},
      tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:function(p){
        var i=p[0].dataIndex; var m=topN[i];
        return '<b>'+shortMajor(m.major, m.code)+'</b><br/>增长率: '+(m.growth_rate>0?'+':'')+m.growth_rate+'%<br/>招录: '+m.total_recruits+'人 | 职位: '+m.total_positions+'个';
      }},
      grid:{left:'18%',right:'10%',top:'15%',bottom:'5%'},
      xAxis:{type:'value',name:'增长率(%)',axisLabel:{formatter:function(v){return v+'%';}}},
      yAxis:{type:'category',data:topN.map(function(m){return m.major;}).reverse(),axisLabel:{fontSize:11}},
      series:[{type:'bar',data:topN.map(function(m){return m.growth_rate;}).reverse().map(function(v){return{value:v,itemStyle:{color:v>=0?'#e74c3c':'#27ae60'}};}),label:{show:true,position:'right',formatter:function(p){return p.value+'%';}}}]
    });
  }, 80);

  var html = '<table><thead><tr><th>专业</th><th title="(2024-2026均招录-2020-2022均招录)÷基准">增长率</th><th title="2020-2026年总招录人数">招录总人数</th><th>2020</th><th>2022</th><th>2024</th><th>2026</th></tr></thead><tbody>';
  topN.forEach(function(m){
    html += '<tr><td>'+m.major+'</td><td class="'+(m.growth_rate>=0?'up':'down')+'">'+(m.growth_rate>0?'+':'')+m.growth_rate+'%</td><td>'+m.total_recruits+'</td><td>'+(m.yearly['2020'].recruits||0)+'</td><td>'+(m.yearly['2022'].recruits||0)+'</td><td>'+(m.yearly['2024'].recruits||0)+'</td><td>'+(m.yearly['2026'].recruits||0)+'</td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('trendTable').innerHTML = html;
}

function drawTrendLines() {
  var ids = [parseInt(document.getElementById('trendMajor1').value), parseInt(document.getElementById('trendMajor2').value), parseInt(document.getElementById('trendMajor3').value)];
  var majors = ids.map(function(i){return RANKING[i];}).filter(function(m){return m;});
  var years = ['2020','2021','2022','2023','2024','2025','2026'];
  var colors = ['#e74c3c','#2980b9','#27ae60'];

  setTimeout(function() {
    var el = document.getElementById('trendChart');
    if (!el) return;
    var tc = echarts.init(el);
    tc.setOption({
      title:{text:'多专业招录趋势对比',left:'center',textStyle:{fontSize:15}},
      tooltip:{trigger:'axis'}, legend:{top:'10%',left:'center'},
      grid:{left:'12%',right:'5%',top:'25%',bottom:'12%'},
      xAxis:{type:'category',data:years},
      yAxis:{type:'value',name:'招录人数'},
      series:majors.map(function(m,i){return {type:'line',name:shortMajor(m.major, m.code),smooth:true,lineStyle:{width:3,color:colors[i]},data:years.map(function(y){return m.yearly[y].recruits;})};})
    });
  }, 80);
  document.getElementById('trendTable').innerHTML = '';
}

// ====== Tab5: 对比 ======
function updateCompare() {
  var cbs = document.querySelectorAll('#compareCheckboxes input:checked');
  var selected = [];
  cbs.forEach(function(cb){selected.push(RANKING[parseInt(cb.value)]);});
  if (selected.length < 2) {
    document.getElementById('radarChart').style.display = 'none';
    document.getElementById('radarEmpty').style.display = 'block';
    return;
  }
  document.getElementById('radarChart').style.display = 'block';
  document.getElementById('radarEmpty').style.display = 'none';
  if (selected.length > 5) selected = selected.slice(0,5);

  var dims = ['total_recruits','purity','growth_rate','fresh_ratio','city_coverage'];
  var dlb = ['招录总人数','纯洁度','增长率','应届占比','城市覆盖'];
  var indicators = dims.map(function(d,i){
    var vals = selected.map(function(m){return m[d];});
    if (d=='growth_rate') vals = vals.map(function(v){return Math.min(300,Math.max(-100,v));});
    return {name:dlb[i], max:(Math.max.apply(null,vals)*1.3||1)};
  });

  var colors = ['#e74c3c','#2980b9','#27ae60','#f39c12','#8e44ad'];

  setTimeout(function() {
    // Radar chart
    var r1 = document.getElementById('radarChart');
    if (r1) {
      var rc = echarts.init(r1);
      rc.setOption({
        title:{text:'多维度雷达对比',textStyle:{fontSize:13},left:'center'},
        legend:{data:selected.map(function(m){return m.major;}),bottom:0,left:'center'},
        radar:{indicator:indicators,center:['50%','45%'],radius:'65%'},
        series:[{type:'radar',data:selected.map(function(m,i){
          var v = dims.map(function(d){var x=m[d]; if(d=='growth_rate')x=Math.min(300,Math.max(-100,x)); return x;});
          return {value:v,name:m.major,itemStyle:{color:colors[i%5]},lineStyle:{color:colors[i%5]}};
        })}]
      });
    }

    // Bar comparison
    var r2 = document.getElementById('compareBarChart');
    if (r2) {
      var bc = echarts.init(r2);
      bc.setOption({
        title:{text:'招录人数与纯洁度',textStyle:{fontSize:13},left:'center'},
        tooltip:{trigger:'axis'}, grid:{left:'12%',right:'5%',top:'18%',bottom:'18%'},
        legend:{data:['招录总人数','纯洁度(%)','应届占比(%)'],bottom:0,left:'center'},
        xAxis:{type:'category',data:selected.map(function(m){return shortMajor(m.major, m.code);})},
        yAxis:{type:'value'},
        series:[
          {type:'bar',name:'招录总人数',data:selected.map(function(m,i){return{value:m.total_recruits,itemStyle:{color:colors[i%5]}};}),barMaxWidth:30},
          {type:'bar',name:'纯洁度(%)',data:selected.map(function(m,i){return{value:m.purity,itemStyle:{color:colors[(i+1)%5]}};}),barMaxWidth:30},
          {type:'bar',name:'应届占比(%)',data:selected.map(function(m,i){return{value:m.fresh_ratio,itemStyle:{color:colors[(i+2)%5]}};}),barMaxWidth:30}
        ]
      });
    }
  }, 80);

  var html = '<table><thead><tr><th>指标</th>'+selected.map(function(m){return '<th>'+fmtMajor(m.major)+'</th>';}).join('')+'</tr></thead><tbody>';
  var rows = [
    ['招录总人数', selected.map(function(m){return m.total_recruits;})],
    ['职位总数', selected.map(function(m){return m.total_positions;})],
    ['纯洁度(%)', selected.map(function(m){return m.purity+'%';})],
    ['增长率(%)', selected.map(function(m){return (m.growth_rate>0?'+':'')+m.growth_rate+'%';})],
    ['应届占比(%)', selected.map(function(m){return m.fresh_ratio+'%';})],
    ['竞争指数', selected.map(function(m){return m.competition_index;})],
    ['覆盖考区', selected.map(function(m){return m.city_coverage;})],
  ];
  rows.forEach(function(row){html += '<tr><td><b>'+row[0]+'</b></td>'+row[1].map(function(v){return '<td>'+v+'</td>';}).join('')+'</tr>';});
  html += '</tbody></table>';
  document.getElementById('compareTable').innerHTML = html;
}

// ====== 指标说明弹窗 ======
function showHelp() { document.getElementById('helpModal').classList.add('show'); }
function hideHelp() { document.getElementById('helpModal').classList.remove('show'); }

// ====== Init (only visible Tab1, rest lazy-loaded on click) ======
window.onload = function() {
  initRankChart();
  filterRankTable();
  initLowRankChart();
  renderLowRankTable();
};
</script>
</body>
</html>"""

# Replace placeholders
html = template
html = html.replace('__RANKING_JS__', ranking_js)
html = html.replace('__RAW_RANKING_JS__', raw_ranking_js)
html = html.replace('__CO_PAIRS_JS__', co_pairs_js)
html = html.replace('__SUM_POS__', str(sum_pos))
html = html.replace('__SUM_MAJ__', str(sum_maj))
html = html.replace('__TOTAL_RANKED__', str(total_ranked))
html = html.replace('__TOP_RECRUIT__', str(top_recruit))
html = html.replace('__DD_OPTS__', dd_opts)
html = html.replace('__TR_OPTS__', tr_opts)
html = html.replace('__TR_OPTS2__', tr_opts_2)
html = html.replace('__TR_OPTS3__', tr_opts_3)
html = html.replace('__CHK_HTML__', chk_html)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'已生成: {OUTPUT_FILE}')
print(f'文件大小: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.1f} MB')
