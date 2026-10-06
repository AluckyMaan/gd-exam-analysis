#!/usr/bin/env python3
"""
广东省考地域维度深度分析 — 可视化生成脚本
生成单页HTML，包含6个Tab模块的交互式地域分析看板。
"""
import json, os, urllib.request, sys

BASE_DIR = 'C:/Users/YANG/Desktop/广东20-26年广东省考职位表'
DATA_FILE = os.path.join(BASE_DIR, 'data', 'city_data.json')
OUTPUT_FILE = os.path.join(BASE_DIR, '广东省考地域维度深度分析.html')

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# ====== 加载广东地图 GeoJSON ======
GD_GEOJSON_URL = 'https://geo.datav.aliyun.com/areas_v3/bound/440000_full.json'
GD_GEOJSON = None
try:
    print('正在下载广东地图GeoJSON...')
    req = urllib.request.Request(GD_GEOJSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        GD_GEOJSON = json.loads(resp.read().decode('utf-8'))
    print('  下载成功')
except Exception as e:
    print(f'  下载失败: {e}')
    # 备用方案：使用精简的手动GeoJSON
    GD_GEOJSON = None

# 城市名前缀映射（GeoJSON中的名称可能带"市"后缀）
def map_city_name(geojson_name):
    """将GeoJSON中的城市名映射到职位表中的名称"""
    name = geojson_name.replace('市', '').replace('省直辖县级行政区划', '省直')
    if name == '广东':  # 省级
        return None
    return name

# ====== 准备 JavaScript 数据 ======
city_yearly_js = json.dumps(data['city_yearly'], ensure_ascii=False)
city_ranking_js = json.dumps(data['city_ranking'], ensure_ascii=False)
city_education_js = json.dumps(data['city_education'], ensure_ascii=False)
city_fresh_js = json.dumps(data['city_fresh'], ensure_ascii=False)
city_major_matrix_js = json.dumps(data['city_major_matrix'], ensure_ascii=False)
summary_js = json.dumps(data['summary'], ensure_ascii=False)
gd_geojson_js = json.dumps(GD_GEOJSON, ensure_ascii=False) if GD_GEOJSON else 'null'

# 城市名映射（用于地图显示）
city_name_map = {}
if GD_GEOJSON and 'features' in GD_GEOJSON:
    for feat in GD_GEOJSON['features']:
        name = feat['properties']['name']
        mapped = map_city_name(name)
        if mapped:
            city_name_map[mapped] = name  # 职位表名 → GeoJSON名

city_name_map_js = json.dumps(city_name_map, ensure_ascii=False)

# 构建所有专业列表（用于Tab5下拉框）
all_majors_set = set()
for city, majors in data['city_major_matrix'].items():
    for m in majors:
        all_majors_set.add(m)
all_majors = sorted(all_majors_set)
all_majors_js = json.dumps(all_majors, ensure_ascii=False)

# 合并专业用于排名（按总招录数降序）
major_totals = {}
for city, majors in data['city_major_matrix'].items():
    for m, n in majors.items():
        major_totals[m] = major_totals.get(m, 0) + n
major_ranking = sorted(major_totals.items(), key=lambda x: -x[1])

# ====== HTML 模板 ======
template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省考地域维度深度分析（2020-2026）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif; background:#f5f7fa; color:#333; }
.container { max-width:1400px; margin:0 auto; padding:20px; }
h1 { text-align:center; font-size:28px; color:#1a3c6e; padding:25px 0 5px; }
h1 .help-btn { display:inline-block; width:22px; height:22px; line-height:22px; text-align:center; border-radius:50%; background:#1a3c6e; color:#fff; font-size:13px; font-weight:700; cursor:pointer; margin-left:8px; vertical-align:middle; position:relative; top:-3px; user-select:none; }
h1 .help-btn:hover { background:#2a5c9e; }
.subtitle { text-align:center; color:#666; font-size:14px; margin-bottom:20px; }
.stats-bar { display:flex; justify-content:center; gap:40px; margin:15px 0 25px; flex-wrap:wrap; }
.stat-item { text-align:center; background:#fff; border-radius:10px; padding:15px 30px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.stat-num { font-size:28px; font-weight:700; color:#1a3c6e; }
.stat-label { font-size:13px; color:#888; margin-top:3px; }
.tabs { display:flex; margin-bottom:0; background:#fff; border-radius:10px 10px 0 0; box-shadow:0 1px 3px rgba(0,0,0,0.06); overflow:hidden; flex-wrap:wrap; }
.tab-btn { flex:1; padding:14px 10px; text-align:center; cursor:pointer; font-size:14px; font-weight:500; color:#666; border:none; background:transparent; transition:all 0.2s; position:relative; min-width:80px; }
.tab-btn:hover { background:#f0f4ff; color:#1a3c6e; }
.tab-btn.active { color:#1a3c6e; font-weight:600; }
.tab-btn.active::after { content: ""; position:absolute; bottom:0; left:20%; width:60%; height:3px; background:#1a3c6e; border-radius:3px 3px 0 0; }
.tab-content { display:none; background:#fff; border-radius:0 0 10px 10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); min-height:500px; }
.tab-content.active { display:block; }
.chart-box { width:100%; height:520px; }
.chart-box-sm { width:100%; height:380px; }
.chart-box-map { width:100%; height:600px; }
.select-bar { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:15px; }
.select-bar label { font-weight:500; color:#555; }
.select-bar select, .select-bar input { padding:6px 12px; border:1px solid #d0d5dd; border-radius:6px; font-size:13px; }
.table-wrap { overflow-x:auto; margin-top:15px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { background:#f0f4ff; color:#1a3c6e; padding:10px 8px; text-align:center; font-weight:600; border-bottom:2px solid #d0d9e8; position:sticky; top:0; }
td { padding:8px; text-align:center; border-bottom:1px solid #eee; }
tr:hover td { background:#f8faff; }
.metrics { display:flex; gap:15px; flex-wrap:wrap; margin:15px 0; }
.metric { flex:1; min-width:140px; background:#f8faff; border-radius:8px; padding:12px 16px; text-align:center; }
.metric-val { font-size:22px; font-weight:700; color:#1a3c6e; }
.metric-label { font-size:12px; color:#888; margin-top:2px; }
.up { color:#e74c3c; } .down { color:#27ae60; }
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
@media (max-width:768px) { .two-col { grid-template-columns:1fr; } }
.legend-tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; margin:2px; }
.prd-tag { background:#d4edda; color:#155724; }
.non-prd-tag { background:#f8d7da; color:#721c24; }
.province-tag { background:#cce5ff; color:#004085; }
.city-detail-card { display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:#fff; border-radius:12px; padding:25px; box-shadow:0 10px 40px rgba(0,0,0,0.2); z-index:1000; max-width:500px; width:90%; max-height:80vh; overflow-y:auto; }
.city-detail-card.show { display:block; }
.city-detail-card h3 { color:#1a3c6e; margin-bottom:12px; border-bottom:2px solid #f0f4ff; padding-bottom:8px; }
.city-detail-card .close-btn { position:absolute; top:10px; right:14px; font-size:22px; cursor:pointer; color:#888; border:none; background:none; }
.city-detail-card .detail-metrics { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:12px 0; }
.city-detail-card .dm-item { background:#f8faff; padding:10px; border-radius:8px; text-align:center; }
.city-detail-card .dm-val { font-size:20px; font-weight:700; color:#1a3c6e; }
.city-detail-card .dm-label { font-size:11px; color:#888; }
.major-check-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:4px; max-height:250px; overflow-y:auto; padding:8px; background:#f8faff; border-radius:8px; font-size:12px; }
.major-check-item { display:flex; align-items:center; gap:4px; }
.overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.4); z-index:999; }
.overlay.show { display:block; }
</style>
</head>
<body>
<div class="container">
<h1>🌏 广东省公务员招录 · 地域维度深度分析 <span class="help-btn" onclick="showHelp()">?</span></h1>
<p class="subtitle" id="pageSubtitle">数据来源：广东省2020-2026年考试录用公务员职位表 | 共 __TOTAL_RECRUITS__ 个招录名额、__TOTAL_CITIES__ 个城市</p>

<div class="stats-bar" id="statsBar">
  <div class="stat-item"><div class="stat-num">__TOTAL_CITIES__</div><div class="stat-label">覆盖城市/地区</div></div>
  <div class="stat-item"><div class="stat-num">__TOTAL_RECRUITS__</div><div class="stat-label">总招录人数</div></div>
  <div class="stat-item"><div class="stat-num">__PRD_RATIO__%</div><div class="stat-label">珠三角占比</div></div>
  <div class="stat-item"><div class="stat-num">2020-2026</div><div class="stat-label">数据跨度</div></div>
</div>

<div class="tabs" id="tabHeaders">
  <button class="tab-btn active" data-tab="tab1">🗺️ 地图总览</button>
  <button class="tab-btn" data-tab="tab2">📊 城市排名</button>
  <button class="tab-btn" data-tab="tab3">📈 年度趋势</button>
  <button class="tab-btn" data-tab="tab4">🎓 应往届·学历</button>
  <button class="tab-btn" data-tab="tab5">🎯 专业×地域</button>
  <button class="tab-btn" data-tab="tab6">📋 城市对比</button>
</div>

<!-- Tab 1: 地图总览 -->
<div class="tab-content active" id="tab1">
  <div class="select-bar">
    <label>显示模式：</label>
    <select id="mapMode" onchange="switchMapMode()">
      <option value="total">绝对招录人数</option>
      <option value="density">每万人招录比</option>
      <option value="growth">招录增长率</option>
    </select>
    <label>分组：</label>
    <select id="mapGroup" onchange="switchMapGroup()">
      <option value="none">无</option>
      <option value="prd">珠三角 vs 非珠</option>
    </select>
    <span style="margin-left:auto;font-size:12px;color:#888;">
      <span class="legend-tag prd-tag">珠三角</span>
      <span class="legend-tag non-prd-tag">非珠三角</span>
      <span class="legend-tag province-tag">省直</span>
    </span>
  </div>
  <div class="chart-box-map" id="mapChart"></div>
  <div id="mapClickDetail" style="margin-top:10px;display:none;">
    <div style="background:#f8faff;border-radius:8px;padding:15px;" id="mapClickContent"></div>
  </div>
</div>

<!-- Tab 2: 城市排名 -->
<div class="tab-content" id="tab2">
  <div class="select-bar">
    <label>排序：</label>
    <select id="rankMode" onchange="switchRankMode()">
      <option value="recruits">按招录人数</option>
      <option value="positions">按职位数</option>
      <option value="growth">按增长率</option>
      <option value="fresh">按应届占比</option>
    </select>
    <input type="text" id="rankSearch" placeholder="搜索城市..." oninput="filterRankTable()" style="flex:1;max-width:200px;">
    <span id="rankCount" style="color:#888;font-size:13px;"></span>
  </div>
  <div class="chart-box" id="rankChart"></div>
  <div class="table-wrap" id="rankTableWrap"></div>
</div>

<!-- Tab 3: 年度趋势 -->
<div class="tab-content" id="tab3">
  <div class="select-bar">
    <label>城市选择：</label>
    <select id="trendCitySelect" multiple style="min-width:240px;height:100px;" onchange="updateTrend()">
    </select>
    <button onclick="selectDefaultCities()" style="padding:4px 10px;border:1px solid #d0d5dd;border-radius:4px;background:#fff;cursor:pointer;font-size:12px;">默认 Top6</button>
    <button onclick="selectAllCities()" style="padding:4px 10px;border:1px solid #d0d5dd;border-radius:4px;background:#fff;cursor:pointer;font-size:12px;">全选</button>
    <span style="font-size:12px;color:#888;margin-left:10px;">按住 Ctrl 多选，最多 8 个</span>
  </div>
  <div class="chart-box" id="trendChart"></div>
  <div class="table-wrap" id="trendTableWrap"></div>
</div>

<!-- Tab 4: 应往届 × 学历 -->
<div class="tab-content" id="tab4">
  <div class="two-col">
    <div>
      <h3 style="color:#1a3c6e;margin-bottom:10px;font-size:15px;">🎓 各城市应往届分布</h3>
      <div class="chart-box-sm" id="freshChart"></div>
    </div>
    <div>
      <h3 style="color:#1a3c6e;margin-bottom:10px;font-size:15px;">📚 各城市学历分布</h3>
      <div class="chart-box-sm" id="eduChart"></div>
    </div>
  </div>
  <div style="margin-top:20px;border-top:1px solid #eee;padding-top:15px;">
    <div class="select-bar">
      <label>查看城市详情：</label>
      <select id="freshEduCity" onchange="updateFreshEduDetail()">
      </select>
    </div>
    <div class="two-col">
      <div class="chart-box-sm" id="freshDetailChart"></div>
      <div class="chart-box-sm" id="eduDetailChart"></div>
    </div>
  </div>
</div>

<!-- Tab 5: 专业×地域 -->
<div class="tab-content" id="tab5">
  <div class="select-bar">
    <label>视图：</label>
    <select id="majorCityView" onchange="switchMajorCityView()">
      <option value="major_to_city">按专业看城市分布</option>
      <option value="city_to_major">按城市看热门专业</option>
    </select>
    <select id="majorSelect" onchange="updateMajorCity()" style="flex:1;max-width:300px;">
    </select>
    <select id="citySelect" onchange="updateMajorCity()" style="flex:1;max-width:200px;display:none;">
    </select>
  </div>
  <div class="chart-box" id="majorCityChart"></div>
  <div class="table-wrap" id="majorCityTableWrap"></div>
</div>

<!-- Tab 6: 城市对比 -->
<div class="tab-content" id="tab6">
  <div class="select-bar">
    <label>选择城市（2-4个）：</label>
    <select id="compareCities" multiple style="min-width:250px;height:120px;" onchange="updateCompare()">
    </select>
    <button onclick="selectCompareCities()" style="padding:4px 10px;border:1px solid #d0d5dd;border-radius:4px;background:#fff;cursor:pointer;font-size:12px;">对比广州vs深圳</button>
    <span style="font-size:12px;color:#888;margin-left:10px;">按住 Ctrl 选择</span>
  </div>
  <div id="compareContent"></div>
</div>

</div><!-- /container -->

<div class="overlay" id="helpOverlay" onclick="hideHelp()"></div>
<div class="city-detail-card" id="cityDetailCard">
  <button class="close-btn" onclick="hideCityDetail()">&times;</button>
  <div id="cityDetailContent"></div>
</div>

<script>
// ====== 数据注入 ======
var CITY_YEARLY = __CITY_YEARLY_JS__;
var CITY_RANKING = __CITY_RANKING_JS__;
var CITY_EDUCATION = __CITY_EDUCATION_JS__;
var CITY_FRESH = __CITY_FRESH_JS__;
var CITY_MAJOR_MATRIX = __CITY_MAJOR_MATRIX_JS__;
var SUMMARY = __SUMMARY_JS__;
var GD_GEOJSON = __GD_GEOJSON_JS__;
var CITY_NAME_MAP = __CITY_NAME_MAP_JS__;
var ALL_MAJORS = __ALL_MAJORS_JS__;

// 珠三角定义
var PRD_CITIES = ['广州','深圳','珠海','佛山','东莞','中山','惠州','江门','肇庆'];
var YEARS = ['2020','2021','2022','2023','2024','2025','2026'];
var COLORS = ['#1a3c6e','#2a5c9e','#3a7cce','#5a9cee','#8abcf5','#b0d4f8','#d0e4fc'];

// Tab切换
document.querySelectorAll('.tab-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    this.classList.add('active');
    document.getElementById(this.dataset.tab).classList.add('active');
    // 触发各图表的resize
    setTimeout(function() {
      var charts = document.querySelectorAll('[id$=Chart]');
      charts.forEach(function(el) {
        var inst = echarts.getInstanceByDom(el);
        if (inst) inst.resize();
      });
    }, 100);
  });
});

// ====== 帮助弹窗 ======
function showHelp() {
  var html = '<div class="overlay show" id="helpOverlay2" onclick="hideHelp()"></div>';
  html += '<div class="city-detail-card show" style="max-width:600px;">';
  html += '<button class="close-btn" onclick="hideHelp()">&times;</button>';
  html += '<h3>📖 指标说明</h3>';
  html += '<div style="margin:10px 0;padding:10px 14px;background:#f8faff;border-radius:8px;border-left:3px solid #1a3c6e;">';
  html += '<strong style="color:#1a3c6e;">🏙️ 招录人数</strong><p style="font-size:13px;color:#555;margin-top:3px;">该城市所有职位的录用人数总和。广东省考部分职位招录多人，因此总招录人数 > 职位总数。</p></div>';
  html += '<div style="margin:10px 0;padding:10px 14px;background:#f8faff;border-radius:8px;border-left:3px solid #2a5c9e;">';
  html += '<strong style="color:#1a3c6e;">📈 招录增长率</strong><p style="font-size:13px;color:#555;margin-top:3px;">(2024-2026 年均招录人数 − 2020-2022 年均招录人数) / 基准。正数表示近年需求上升。</p></div>';
  html += '<div style="margin:10px 0;padding:10px 14px;background:#f8faff;border-radius:8px;border-left:3px solid #3a7cce;">';
  html += '<strong style="color:#1a3c6e;">🎓 应届占比</strong><p style="font-size:13px;color:#555;margin-top:3px;">限应届毕业生报考职位的招录人数占该城市总招录人数的比例。</p></div>';
  html += '<div style="margin:10px 0;padding:10px 14px;background:#f8faff;border-radius:8px;border-left:3px solid #5a9cee;">';
  html += '<strong style="color:#1a3c6e;">🗺️ 珠三角 vs 非珠</strong><p style="font-size:13px;color:#555;margin-top:3px;">珠三角9市：广州、深圳、珠海、佛山、东莞、中山、惠州、江门、肇庆。非珠三角12市：其余地级市。省直单独归类。</p></div>';
  html += '</div>';
  var div = document.createElement('div');
  div.innerHTML = html;
  div.id = 'helpModal';
  document.body.appendChild(div);
}
function hideHelp() {
  var el = document.getElementById('helpModal');
  if (el) el.remove();
  var el2 = document.getElementById('helpOverlay2');
  if (el2) el2.remove();
}

// ====== 工具函数 ======
function calcGrowth(city) {
  var cy = CITY_YEARLY[city].yearly;
  var early = (parseInt(cy['2020']||0) + parseInt(cy['2021']||0) + parseInt(cy['2022']||0)) / 3;
  var late = (parseInt(cy['2023']||0) + parseInt(cy['2024']||0) + parseInt(cy['2025']||0) + parseInt(cy['2026']||0)) / 4;
  if (early === 0) return late > 0 ? 100 : 0;
  return Math.round((late - early) / early * 1000) / 10;
}

function calcFreshRatio(city) {
  var f = CITY_FRESH[city] || {};
  var fresh = (parseInt(f.fresh_any||0) + parseInt(f.fresh_current||0));
  var total = fresh + parseInt(f.social||0);
  return total > 0 ? Math.round(fresh / total * 1000) / 10 : 0;
}

function getCityGroup(city) {
  if (city === '省直') return 'province';
  return PRD_CITIES.indexOf(city) >= 0 ? 'prd' : 'non-prd';
}

// ====== Tab 1: 地图总览 ======
var mapChart = null;
function initMap() {
  if (!GD_GEOJSON || !GD_GEOJSON.features) {
    document.getElementById('mapChart').innerHTML = '<div style="text-align:center;padding:100px 20px;color:#888;">⚠️ 广东地图数据加载失败，请检查网络连接后刷新页面</div>';
    return;
  }
  mapChart = echarts.init(document.getElementById('mapChart'));
  echarts.registerMap('guangdong', GD_GEOJSON);
  switchMapMode();
}
initMap();

function getMapData(mode) {
  var mapData = [];
  GD_GEOJSON.features.forEach(function(feat) {
    var geoName = feat.properties.name;
    var cityName = null;
    for (var cn in CITY_NAME_MAP) {
      if (CITY_NAME_MAP[cn] === geoName) { cityName = cn; break; }
    }
    if (!cityName) {
      cityName = geoName.replace('市', '');
    }
    var info = CITY_YEARLY[cityName];
    var val = 0;
    if (info) {
      if (mode === 'total') val = info.total_recruits;
      else if (mode === 'density') val = Math.round(info.total_recruits / info.total_positions * 100) / 100;
      else if (mode === 'growth') val = calcGrowth(cityName);
    }
    mapData.push({name: geoName, value: val, cityName: cityName, info: info});
  });
  return mapData;
}

function switchMapMode() {
  if (!mapChart) return;
  var mode = document.getElementById('mapMode').value;
  var group = document.getElementById('mapGroup').value;
  var mapData = getMapData(mode);

  var seriesName = mode === 'total' ? '总招录人数' : (mode === 'density' ? '平均每职位招录人数' : '增长率(%)');
  var visualMin = 0, visualMax = null;
  var values = mapData.filter(function(d) { return d.value > 0; }).map(function(d) { return d.value; });
  if (values.length > 0) {
    values.sort(function(a,b) { return a-b; });
    visualMax = values[Math.floor(values.length * 0.95)];
    if (visualMax === 0) visualMax = 1;
  } else { visualMax = 1; }

  var option = {
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        var d = params.data;
        if (!d || !d.info) return params.name + '<br/>暂无数据';
        var html = '<strong>' + d.cityName + '</strong><br/>';
        html += '总招录: ' + d.info.total_recruits + ' 人<br/>';
        html += '职位数: ' + d.info.total_positions + '<br/>';
        html += '增长率: ' + calcGrowth(d.cityName) + '%<br/>';
        html += '应届占比: ' + calcFreshRatio(d.cityName) + '%<br/>';
        html += '<span style="color:#999;font-size:12px;">点击查看详情</span>';
        return html;
      }
    },
    visualMap: {
      min: mode === 'growth' ? -100 : visualMin,
      max: mode === 'growth' ? 100 : visualMax,
      text: ['高','低'],
      left: 'left',
      bottom: 20,
      inRange: mode === 'growth' ? {color: ['#27ae60','#fef0d9','#e74c3c']} : {color: ['#e8edf5','#8abcf5','#1a3c6e']},
      calculable: true
    },
    series: [{
      type: 'map',
      map: 'guangdong',
      roam: true,
      selectedMode: false,
      label: { show: true, fontSize: 10 },
      data: mapData,
      itemStyle: { borderColor: '#fff', borderWidth: 1 },
      emphasis: { label: { fontSize: 13, fontWeight: 'bold' }, itemStyle: { areaColor: '#2a5c9e' } },
    }]
  };

  // 分组着色
  if (group === 'prd') {
    option.series[0].data = mapData.map(function(d) {
      var g = d.cityName ? getCityGroup(d.cityName) : 'non-prd';
      var c = g === 'prd' ? '#4a9e5c' : (g === 'province' ? '#3a7cce' : '#c97878');
      return Object.assign({}, d, {itemStyle: {areaColor: c, opacity: 0.6}});
    });
    option.visualMap.show = false;
  } else {
    option.visualMap.show = true;
  }

  mapChart.setOption(option, true);
  mapChart.off('click');
  mapChart.on('click', function(params) {
    var d = params.data;
    if (d && d.cityName && d.info) showCityDetail(d.cityName);
  });
}

function switchMapGroup() { switchMapMode(); }

// ====== 城市详情弹窗 ======
function showCityDetail(city) {
  var info = CITY_YEARLY[city];
  if (!info) return;
  var edu = CITY_EDUCATION[city] || {};
  var fresh = CITY_FRESH[city] || {};
  var totalFresh = (parseInt(fresh.fresh_any||0) + parseInt(fresh.fresh_current||0));
  var totalSocial = parseInt(fresh.social||0);
  var totalF = totalFresh + totalSocial;
  var growth = calcGrowth(city);
  var freshR = calcFreshRatio(city);
  var majorsInCity = CITY_MAJOR_MATRIX[city] || {};
  var topMajors = Object.entries(majorsInCity).sort(function(a,b) { return b[1]-a[1]; }).slice(0, 5);

  var html = '<h3>🏙️ ' + city + ' <span style="font-size:13px;font-weight:400;color:#888;">';
  var group = getCityGroup(city);
  if (group === 'prd') html += '(珠三角)';
  else if (group === 'province') html += '(省级机关)';
  else html += '(非珠三角)';
  html += '</span></h3>';

  html += '<div class="detail-metrics">';
  html += '<div class="dm-item"><div class="dm-val">' + info.total_recruits + '</div><div class="dm-label">总招录人数</div></div>';
  html += '<div class="dm-item"><div class="dm-val">' + info.total_positions + '</div><div class="dm-label">职位数</div></div>';
  html += '<div class="dm-item"><div class="dm-val ' + (growth > 0 ? 'up' : 'down') + '">' + growth + '%</div><div class="dm-label">增长率</div></div>';
  html += '<div class="dm-item"><div class="dm-val">' + freshR + '%</div><div class="dm-label">应届占比</div></div>';
  html += '</div>';

  html += '<div style="margin:10px 0;"><strong style="font-size:13px;">年度趋势：</strong><br/>';
  html += '<div style="height:100px;" id="miniTrend' + city.replace(/\s/g,'') + '"></div></div>';

  html += '<div style="margin:8px 0;"><strong style="font-size:13px;">热门招录专业 Top 5：</strong></div>';
  html += '<div style="display:flex;flex-wrap:wrap;gap:4px;">';
  topMajors.forEach(function(item) {
    html += '<span style="background:#e8edf5;padding:3px 10px;border-radius:12px;font-size:12px;">' + item[0] + ': ' + item[1] + '</span>';
  });
  html += '</div>';

  document.getElementById('cityDetailContent').innerHTML = html;
  document.getElementById('cityDetailCard').classList.add('show');
  document.getElementById('helpOverlay').classList.add('show');

  // 渲染迷你趋势图
  setTimeout(function() {
    var el = document.getElementById('miniTrend' + city.replace(/\s/g,''));
    if (!el) return;
    var mini = echarts.init(el);
    var yearly = info.yearly;
    mini.setOption({
      grid: { left: '3%', right: '3%', top: 10, bottom: 10 },
      xAxis: { type: 'category', data: YEARS, axisLabel: {fontSize:9} },
      yAxis: { type: 'value', splitLine: {lineStyle:{type:'dashed',opacity:0.3}} },
      series: [{ type: 'line', data: YEARS.map(function(y) { return yearly[y]||0; }), smooth: true, lineStyle: {color:'#1a3c6e'}, areaStyle: {color:'#e8edf5'} }],
      tooltip: { trigger: 'axis' },
    });
  }, 50);
}

function hideCityDetail() {
  document.getElementById('cityDetailCard').classList.remove('show');
  document.getElementById('helpOverlay').classList.remove('show');
}

// ====== Tab 2: 城市排名 ======
var rankChart = null;
function initRank() {
  rankChart = echarts.init(document.getElementById('rankChart'));
  switchRankMode();
}
initRank();

function switchRankMode() {
  var mode = document.getElementById('rankMode').value;
  var sorted = CITY_RANKING.slice();
  if (mode === 'recruits') sorted.sort(function(a,b) { return (CITY_YEARLY[b].total_recruits||0) - (CITY_YEARLY[a].total_recruits||0); });
  else if (mode === 'positions') sorted.sort(function(a,b) { return (CITY_YEARLY[b].total_positions||0) - (CITY_YEARLY[a].total_positions||0); });
  else if (mode === 'growth') sorted.sort(function(a,b) { return calcGrowth(b) - calcGrowth(a); });
  else if (mode === 'fresh') sorted.sort(function(a,b) { return calcFreshRatio(b) - calcFreshRatio(a); });

  var names = sorted.map(function(c) {
    var g = getCityGroup(c);
    return c + (g === 'prd' ? ' ★' : '');
  });
  var values = sorted.map(function(c) {
    if (mode === 'recruits') return CITY_YEARLY[c].total_recruits;
    if (mode === 'positions') return CITY_YEARLY[c].total_positions;
    if (mode === 'growth') return calcGrowth(c);
    if (mode === 'fresh') return calcFreshRatio(c);
    return 0;
  });

  var option = {
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
    grid: { left: 100, right: 50, top: 20, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: names.reverse(), axisLabel: {fontSize:11} },
    series: [{
      type: 'bar',
      data: values.reverse().map(function(v, i) {
        var city = sorted[sorted.length - 1 - i];
        var g = getCityGroup(city);
        return { value: v, itemStyle: { color: g === 'prd' ? '#4a9e5c' : (g === 'province' ? '#3a7cce' : '#c97878') } };
      }),
      barMaxWidth: 24,
      label: { show: true, position: 'right', fontSize: 11, formatter: function(p) { return p.value + (mode === 'growth' ? '%' : (mode === 'fresh' ? '%' : '')); } }
    }]
  };
  rankChart.setOption(option, true);

  // 表格
  var tableHtml = '<table><thead><tr><th>排名</th><th>城市</th><th>分区</th><th>招录人数</th><th>职位数</th><th>增长率</th><th>应届占比</th><th>占全省比</th></tr></thead><tbody>';
  sorted.forEach(function(c, i) {
    var info = CITY_YEARLY[c];
    var g = getCityGroup(c);
    var gLabel = g === 'prd' ? '珠三角' : (g === 'province' ? '省直' : '非珠');
    tableHtml += '<tr><td>' + (i+1) + '</td><td><strong>' + c + '</strong></td><td>' + gLabel + '</td><td>' + info.total_recruits + '</td><td>' + info.total_positions + '</td><td class="' + (calcGrowth(c) > 0 ? 'up' : 'down') + '">' + calcGrowth(c) + '%</td><td>' + calcFreshRatio(c) + '%</td><td>' + info.pct_of_total + '%</td></tr>';
  });
  tableHtml += '</tbody></table>';
  document.getElementById('rankTableWrap').innerHTML = tableHtml;
  document.getElementById('rankCount').textContent = '共 ' + sorted.length + ' 个城市';
}

function filterRankTable() {
  var q = document.getElementById('rankSearch').value;
  var rows = document.querySelectorAll('#rankTableWrap table tbody tr');
  var count = 0;
  rows.forEach(function(r) {
    var match = r.cells[1].textContent.indexOf(q) >= 0;
    r.style.display = match ? '' : 'none';
    if (match) count++;
  });
  document.getElementById('rankCount').textContent = '显示 ' + count + ' / ' + CITY_RANKING.length + ' 个城市';
}

// ====== Tab 3: 年度趋势 ======
var trendChart = null;
function initTrend() {
  var sel = document.getElementById('trendCitySelect');
  CITY_RANKING.forEach(function(c) {
    var opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  });
  trendChart = echarts.init(document.getElementById('trendChart'));
  selectDefaultCities();
}
initTrend();

function selectDefaultCities() {
  var sel = document.getElementById('trendCitySelect');
  var defaults = ['广州','深圳','省直','佛山','东莞','惠州'].filter(function(c) { return CITY_YEARLY[c]; });
  Array.from(sel.options).forEach(function(opt) {
    opt.selected = defaults.indexOf(opt.value) >= 0;
  });
  updateTrend();
}

function selectAllCities() {
  var sel = document.getElementById('trendCitySelect');
  Array.from(sel.options).forEach(function(opt) { opt.selected = true; });
  updateTrend();
}

function updateTrend() {
  var sel = document.getElementById('trendCitySelect');
  var selected = Array.from(sel.selectedOptions).map(function(o) { return o.value; }).slice(0, 8);
  if (selected.length === 0) { selected = ['广州']; }

  var series = [];
  var colorIdx = 0;
  selected.forEach(function(city) {
    var info = CITY_YEARLY[city];
    if (!info) return;
    series.push({
      name: city,
      type: 'line',
      smooth: true,
      data: YEARS.map(function(y) { return info.yearly[y] || 0; }),
      lineStyle: { width: 2.5 },
      symbolSize: 6,
    });
  });

  var option = {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, type: 'scroll', pageIconSize: 10 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: YEARS, axisLabel: {fontSize:12} },
    yAxis: { type: 'value', name: '招录人数' },
    series: series,
    color: ['#1a3c6e','#e74c3c','#27ae60','#e67e22','#8e44ad','#2ecc71','#f39c12','#2980b9'],
  };
  trendChart.setOption(option, true);

  // 增长率表
  var growthRanks = selected.map(function(c) { return {city: c, growth: calcGrowth(c)}; });
  growthRanks.sort(function(a,b) { return b.growth - a.growth; });
  var th = '<table><thead><tr><th>城市</th><th>年均增长率</th><th>2020</th><th>2021</th><th>2022</th><th>2023</th><th>2024</th><th>2025</th><th>2026</th></tr></thead><tbody>';
  growthRanks.forEach(function(item) {
    var info = CITY_YEARLY[item.city];
    th += '<tr><td><strong>' + item.city + '</strong></td><td class="' + (item.growth > 0 ? 'up' : 'down') + '">' + item.growth + '%</td>';
    YEARS.forEach(function(y) { th += '<td>' + (info.yearly[y]||0) + '</td>'; });
    th += '</tr>';
  });
  th += '</tbody></table>';
  document.getElementById('trendTableWrap').innerHTML = th;
}

// ====== Tab 4: 应往届 × 学历 ======
var freshChart = null, eduChart = null;
function initFreshEdu() {
  freshChart = echarts.init(document.getElementById('freshChart'));
  eduChart = echarts.init(document.getElementById('eduChart'));

  // 城市选择下拉
  var sel = document.getElementById('freshEduCity');
  CITY_RANKING.forEach(function(c) {
    var opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  });

  renderFreshEduOverview();
  updateFreshEduDetail();
}
initFreshEdu();

function renderFreshEduOverview() {
  var cities = CITY_RANKING.slice(0, 15);
  var freshData = {
    social: [], fresh_any: [], fresh_current: []
  };
  cities.forEach(function(c) {
    var f = CITY_FRESH[c] || {};
    freshData.social.push(parseInt(f.social||0));
    freshData.fresh_any.push(parseInt(f.fresh_any||0));
    freshData.fresh_current.push(parseInt(f.fresh_current||0));
  });

  freshChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
    legend: { data: ['社会人员','往届应届','当年应届'], bottom: 0 },
    grid: { left: 40, right: 20, top: 10, bottom: 50 },
    xAxis: { type: 'category', data: cities, axisLabel: {rotate:30, fontSize:10} },
    yAxis: { type: 'value', name: '招录人数' },
    series: [
      { name: '社会人员', type: 'bar', stack: 'fresh', data: freshData.social, itemStyle: {color:'#c97878'} },
      { name: '往届应届', type: 'bar', stack: 'fresh', data: freshData.fresh_any, itemStyle: {color:'#8abcf5'} },
      { name: '当年应届', type: 'bar', stack: 'fresh', data: freshData.fresh_current, itemStyle: {color:'#4a9e5c'} },
    ]
  }, true);

  var eduLabels = ['研究生','本科','大专','大专以上','大专或本科','其他'];
  var eduColors = {'研究生':'#1a3c6e','本科':'#4a9e5c','大专':'#c97878','大专以上':'#8abcf5','大专或本科':'#e67e22','其他':'#ccc'};
  var eduData = {};
  eduLabels.forEach(function(l) { eduData[l] = []; });
  cities.forEach(function(c) {
    var edu = CITY_EDUCATION[c] || {};
    eduLabels.forEach(function(l) { eduData[l].push(parseInt(edu[l]||0)); });
  });

  eduChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
    legend: { data: eduLabels.filter(function(l) { return eduData[l].some(function(v) { return v>0; }); }), bottom: 0 },
    grid: { left: 40, right: 20, top: 10, bottom: 50 },
    xAxis: { type: 'category', data: cities, axisLabel: {rotate:30, fontSize:10} },
    yAxis: { type: 'value', name: '招录人数' },
    series: eduLabels.filter(function(l) { return eduData[l].some(function(v) { return v>0; }); }).map(function(l) {
      return { name: l, type: 'bar', stack: 'edu', data: eduData[l], itemStyle: {color: eduColors[l]} };
    })
  }, true);
}

function updateFreshEduDetail() {
  var city = document.getElementById('freshEduCity').value;
  if (!city || !CITY_YEARLY[city]) return;

  var f = CITY_FRESH[city] || {};
  var freshMini = echarts.init(document.getElementById('freshDetailChart'));
  freshMini.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['30%', '60%'],
      label: { formatter: '{b}: {d}%' },
      data: [
        { value: parseInt(f.social||0), name: '社会人员' , itemStyle: {color:'#c97878'}},
        { value: parseInt(f.fresh_any||0), name: '往届应届', itemStyle: {color:'#8abcf5'} },
        { value: parseInt(f.fresh_current||0), name: '当年应届', itemStyle: {color:'#4a9e5c'} },
      ].filter(function(d) { return d.value > 0; })
    }]
  }, true);

  var e = CITY_EDUCATION[city] || {};
  var eduMini = echarts.init(document.getElementById('eduDetailChart'));
  var eduLabels = ['研究生','本科','大专','大专以上','大专或本科','其他'];
  eduMini.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['30%', '60%'],
      label: { formatter: '{b}: {d}%' },
      data: eduLabels.filter(function(l) { return parseInt(e[l]||0) > 0; }).map(function(l) {
        return { value: parseInt(e[l]||0), name: l };
      })
    }]
  }, true);
}

// ====== Tab 5: 专业×地域 ======
var majorCityChart = null;
function initMajorCity() {
  var sel = document.getElementById('majorSelect');
  ALL_MAJORS.forEach(function(m, i) {
    var opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    if (i < 1) opt.selected = true;
    sel.appendChild(opt);
  });
  var citySel = document.getElementById('citySelect');
  CITY_RANKING.forEach(function(c) {
    var opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    citySel.appendChild(opt);
  });
  majorCityChart = echarts.init(document.getElementById('majorCityChart'));
  updateMajorCity();
}
initMajorCity();

function switchMajorCityView() {
  var view = document.getElementById('majorCityView').value;
  document.getElementById('majorSelect').style.display = view === 'major_to_city' ? '' : 'none';
  document.getElementById('citySelect').style.display = view === 'city_to_major' ? '' : 'none';
  updateMajorCity();
}

function updateMajorCity() {
  var view = document.getElementById('majorCityView').value;
  if (view === 'major_to_city') {
    var major = document.getElementById('majorSelect').value;
    if (!major) return;
    var cityData = [];
    for (var city in CITY_MAJOR_MATRIX) {
      var n = CITY_MAJOR_MATRIX[city][major] || 0;
      if (n > 0) cityData.push({city: city, recruits: n});
    }
    cityData.sort(function(a,b) { return b.recruits - a.recruits; });

    var option = {
      tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
      grid: { left: 80, right: 50, top: 20, bottom: 30 },
      xAxis: { type: 'value', name: '招录人数' },
      yAxis: { type: 'category', data: cityData.map(function(d) { return d.city; }).reverse(), axisLabel: {fontSize:11} },
      series: [{
        type: 'bar',
        data: cityData.map(function(d,i) {
          return { value: d.recruits, itemStyle: { color: getCityGroup(d.city) === 'prd' ? '#4a9e5c' : (getCityGroup(d.city)==='province'?'#3a7cce':'#c97878') } };
        }).reverse(),
        label: { show: true, position: 'right', fontSize: 11 },
        barMaxWidth: 24,
      }]
    };
    majorCityChart.setOption(option, true);

    // 表格
    var th = '<table><thead><tr><th>排名</th><th>城市</th><th>分区</th><th>招录人数</th><th>占比</th></tr></thead><tbody>';
    var total = cityData.reduce(function(s,d) { return s + d.recruits; }, 0);
    cityData.forEach(function(d, i) {
      var g = getCityGroup(d.city);
      th += '<tr><td>' + (i+1) + '</td><td><strong>' + d.city + '</strong></td><td>' + (g==='prd'?'珠三角':(g==='province'?'省直':'非珠')) + '</td><td>' + d.recruits + '</td><td>' + Math.round(d.recruits/total*1000)/10 + '%</td></tr>';
    });
    th += '</tbody></table>';
    document.getElementById('majorCityTableWrap').innerHTML = th;
  } else {
    var city = document.getElementById('citySelect').value;
    if (!city) return;
    var majors = CITY_MAJOR_MATRIX[city] || {};
    var majorsArr = Object.entries(majors).sort(function(a,b) { return b[1]-a[1]; }).slice(0, 20);
    var total = majorsArr.reduce(function(s,d) { return s + d[1]; }, 0);

    var option = {
      tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
      grid: { left: 120, right: 50, top: 20, bottom: 30 },
      xAxis: { type: 'value', name: '招录人数' },
      yAxis: { type: 'category', data: majorsArr.map(function(d) { return d[0]; }).reverse(), axisLabel: {fontSize:10} },
      series: [{
        type: 'bar',
        data: majorsArr.map(function(d) { return d[1]; }).reverse(),
        label: { show: true, position: 'right', fontSize: 10 },
        barMaxWidth: 20,
        itemStyle: {color: '#1a3c6e'},
      }]
    };
    majorCityChart.setOption(option, true);

    var th = '<table><thead><tr><th>排名</th><th>专业</th><th>招录人数</th><th>占比</th></tr></thead><tbody>';
    majorsArr.forEach(function(d, i) {
      th += '<tr><td>' + (i+1) + '</td><td><strong>' + d[0] + '</strong></td><td>' + d[1] + '</td><td>' + Math.round(d[1]/total*1000)/10 + '%</td></tr>';
    });
    th += '</tbody></table>';
    document.getElementById('majorCityTableWrap').innerHTML = th;
  }
}

// ====== Tab 6: 城市对比 ======
function initCompare() {
  var sel = document.getElementById('compareCities');
  CITY_RANKING.forEach(function(c) {
    var opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  });
  selectCompareCities();
}
initCompare();

function selectCompareCities() {
  var sel = document.getElementById('compareCities');
  var defaults = ['广州','深圳'].filter(function(c) { return CITY_YEARLY[c]; });
  Array.from(sel.options).forEach(function(opt) {
    opt.selected = defaults.indexOf(opt.value) >= 0;
  });
  updateCompare();
}

function updateCompare() {
  var sel = document.getElementById('compareCities');
  var selected = Array.from(sel.selectedOptions).map(function(o) { return o.value; }).slice(0, 4);
  if (selected.length < 2) { selected = ['广州','深圳']; }

  var html = '<div class="two-col" style="margin-bottom:15px;">';
  selected.forEach(function(city) {
    var info = CITY_YEARLY[city];
    if (!info) return;
    var g = getCityGroup(city);
    var fresh = CITY_FRESH[city] || {};
    var totalF = (parseInt(fresh.fresh_any||0) + parseInt(fresh.fresh_current||0));
    var totalAll = totalF + parseInt(fresh.social||0);
    var edu = CITY_EDUCATION[city] || {};
    var growth = calcGrowth(city);
    var freshR = calcFreshRatio(city);
    var majorsInCity = CITY_MAJOR_MATRIX[city] || {};
    var top5 = Object.entries(majorsInCity).sort(function(a,b) { return b[1]-a[1]; }).slice(0, 5);

    html += '<div style="background:#f8faff;border-radius:10px;padding:15px;">';
    html += '<h3 style="color:#1a3c6e;margin-bottom:8px;">' + city + ' <span style="font-size:12px;font-weight:400;color:#888;">' + (g==='prd'?'珠三角':(g==='province'?'省直':'非珠')) + '</span></h3>';
    html += '<div class="detail-metrics" style="margin:5px 0;">';
    html += '<div class="dm-item"><div class="dm-val">' + info.total_recruits + '</div><div class="dm-label">总招录</div></div>';
    html += '<div class="dm-item"><div class="dm-val" class="' + (growth>0?'up':'down') + '">' + growth + '%</div><div class="dm-label">增长率</div></div>';
    html += '<div class="dm-item"><div class="dm-val">' + freshR + '%</div><div class="dm-label">应届占比</div></div>';
    html += '<div class="dm-item"><div class="dm-val">' + info.pct_of_total + '%</div><div class="dm-label">占全省比</div></div>';
    html += '</div>';
    html += '<div style="height:120px;" id="compareTrend' + city.replace(/\s/g,'') + '"></div>';
    html += '<div style="margin-top:6px;"><strong style="font-size:11px;">热门专业：</strong> ';
    top5.forEach(function(item, idx) {
      html += '<span style="background:#e8edf5;padding:1px 6px;border-radius:8px;font-size:11px;margin:1px;">' + item[0] + '</span>';
    });
    html += '</div></div>';
  });
  html += '</div>';
  document.getElementById('compareContent').innerHTML = html;

  // 渲染每个城市的趋势
  setTimeout(function() {
    selected.forEach(function(city) {
      var el = document.getElementById('compareTrend' + city.replace(/\s/g,''));
      if (!el) return;
      var mini = echarts.init(el);
      var info = CITY_YEARLY[city];
      mini.setOption({
        grid: { left: '5%', right: '3%', top: 10, bottom: 10 },
        xAxis: { type: 'category', data: YEARS, axisLabel: {fontSize:8} },
        yAxis: { type: 'value', splitLine: {lineStyle:{type:'dashed',opacity:0.3}}, show: false },
        series: [{ type: 'line', data: YEARS.map(function(y) { return info.yearly[y]||0; }), smooth: true, lineStyle: {color:'#1a3c6e', width:2}, areaStyle: {color:'#e8edf5'}, symbol: 'circle', symbolSize: 4 }],
        tooltip: { trigger: 'axis' },
      });
    });
  }, 50);
}

// ====== 窗口resize ======
window.addEventListener('resize', function() {
  var charts = document.querySelectorAll('[id$=Chart]');
  charts.forEach(function(el) {
    var inst = echarts.getInstanceByDom(el);
    if (inst) inst.resize();
  });
});
</script>
</body>
</html>
"""

# ====== 替换占位符 ======
summary = data['summary']
template = template.replace('__CITY_YEARLY_JS__', city_yearly_js)
template = template.replace('__CITY_RANKING_JS__', city_ranking_js)
template = template.replace('__CITY_EDUCATION_JS__', city_education_js)
template = template.replace('__CITY_FRESH_JS__', city_fresh_js)
template = template.replace('__CITY_MAJOR_MATRIX_JS__', city_major_matrix_js)
template = template.replace('__SUMMARY_JS__', summary_js)
template = template.replace('__GD_GEOJSON_JS__', gd_geojson_js)
template = template.replace('__CITY_NAME_MAP_JS__', city_name_map_js)
template = template.replace('__ALL_MAJORS_JS__', all_majors_js)
template = template.replace('__TOTAL_CITIES__', str(summary['total_cities']))
template = template.replace('__TOTAL_RECRUITS__', str(summary['total_recruits']))
template = template.replace('__PRD_RATIO__', str(summary['prd_ratio']))

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(template)

print(f'生成完成: {OUTPUT_FILE}')
print(f'  文件大小: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.1f} MB')
