#!/usr/bin/env python3
"""
广东省考综合数据分析看板 — 合并生成脚本
整合专业热度分析和地域维度分析为单一页面，两级Tab导航。
"""
import json, os, urllib.request, html as _html

# 项目根目录 = 本文件的上两级（scripts/generate/ → scripts/ → 项目根）。
# 不要写死绝对路径：否则换机器或换目录后无法从干净检出复现。
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MAJOR_DATA_FILE = os.path.join(BASE_DIR, 'data', 'all_majors_ranking.json')
CITY_DATA_FILE = os.path.join(BASE_DIR, 'data', 'city_data.json')
OUTPUT_FILE = os.path.join(BASE_DIR, '广东省考综合数据分析看板.html')

# ====== 加载数据 ======
with open(MAJOR_DATA_FILE, 'r', encoding='utf-8') as f:
    major_data = json.load(f)
with open(CITY_DATA_FILE, 'r', encoding='utf-8') as f:
    city_data = json.load(f)

# ====== 加载广东地图 GeoJSON ======
# 本地缓存优先：只要 data/guangdong_geojson.json 存在，生成过程就完全离线，
# 不再依赖网络，也不会从旧 HTML 里"冻结"地图数据。首次生成或刷新地图时，
# 删除该缓存文件再跑一次即可重新下载。
GD_GEOJSON_URL = 'https://geo.datav.aliyun.com/areas_v3/bound/440000_full.json'
GD_GEOJSON_CACHE = os.path.join(BASE_DIR, 'data', 'guangdong_geojson.json')
GD_GEOJSON = None

def load_cached_geojson():
    """读取本地 GeoJSON 缓存"""
    if not os.path.exists(GD_GEOJSON_CACHE):
        return None
    try:
        with open(GD_GEOJSON_CACHE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data and data.get('features'):
            return data
    except Exception as e:
        print(f'  本地地图缓存损坏，忽略: {e}')
    return None

def save_cached_geojson(data):
    """把下载到的 GeoJSON 写入本地缓存，供后续离线生成使用"""
    try:
        os.makedirs(os.path.dirname(GD_GEOJSON_CACHE), exist_ok=True)
        with open(GD_GEOJSON_CACHE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f'  已写入本地地图缓存: {os.path.relpath(GD_GEOJSON_CACHE, BASE_DIR)}')
    except Exception as e:
        print(f'  地图缓存写入失败（不影响本次生成）: {e}')

def load_existing_geojson():
    """最后兜底：从已生成的旧 HTML 中提取内嵌地图（仅在无本地缓存且离线时使用）"""
    if not os.path.exists(OUTPUT_FILE):
        return None
    marker = 'var GD_GEOJSON = '
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return None
    start = text.find(marker)
    if start < 0:
        return None
    literal_start = start + len(marker)
    if text.startswith('null', literal_start):
        return None
    open_index = text.find('{', literal_start)
    if open_index < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(open_index, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[open_index:i + 1])
    return None

# 加载顺序：本地缓存 → 联网下载（成功后落盘）→ 旧 HTML 兜底
GD_GEOJSON = load_cached_geojson()
if GD_GEOJSON:
    print(f'已加载本地地图缓存: {os.path.relpath(GD_GEOJSON_CACHE, BASE_DIR)}（离线生成，未联网）')
else:
    try:
        print('无本地地图缓存，正在下载广东地图GeoJSON...')
        req = urllib.request.Request(GD_GEOJSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            GD_GEOJSON = json.loads(resp.read().decode('utf-8'))
        print('  OK')
        save_cached_geojson(GD_GEOJSON)
    except Exception as e:
        print(f'  GeoJSON下载失败: {e}')
        GD_GEOJSON = load_existing_geojson()
        if GD_GEOJSON:
            print('  [降级] 已复用现有HTML中的广东地图GeoJSON，建议恢复网络后删除缓存文件重新生成')

# ====== 准备JS数据 ======
# 专业分析数据
ranking_js = json.dumps(major_data['ranking'], ensure_ascii=False)
raw_ranking_js = json.dumps(major_data.get('raw_ranking', major_data['ranking']), ensure_ascii=False)
co_pairs_js = json.dumps(major_data['co_occurrence_pairs'], ensure_ascii=False)
major_summary = major_data['summary']

# 地域分析数据
city_yearly_js = json.dumps(city_data['city_yearly'], ensure_ascii=False)
city_ranking_js = json.dumps(city_data['city_ranking'], ensure_ascii=False)
city_education_js = json.dumps(city_data['city_education'], ensure_ascii=False)
city_fresh_js = json.dumps(city_data['city_fresh'], ensure_ascii=False)
city_major_matrix_js = json.dumps(city_data['city_major_matrix'], ensure_ascii=False)
city_summary = city_data['summary']
gd_geojson_js = json.dumps(GD_GEOJSON, ensure_ascii=False) if GD_GEOJSON else 'null'

# 城市名映射
city_name_map = {}
if GD_GEOJSON and 'features' in GD_GEOJSON:
    for feat in GD_GEOJSON['features']:
        name = feat['properties']['name']
        mapped = name.replace('市', '')
        if mapped:
            city_name_map[mapped] = name
city_name_map_js = json.dumps(city_name_map, ensure_ascii=False)

# 专业列表（地域Tab中用）
all_majors_set = set()
for c, majors in city_data['city_major_matrix'].items():
    for m in majors:
        all_majors_set.add(m)
FOCUS_MAJOR_NAMES = [
    '生物科学类',
    '图书情报与档案管理类',
    '动物医学类',
    '兽医学',
]
all_majors_sorted = sorted(all_majors_set)
all_majors = [m for m in FOCUS_MAJOR_NAMES if m in all_majors_set]
all_majors.extend([m for m in all_majors_sorted if m not in set(all_majors)])
all_majors_js = json.dumps(all_majors, ensure_ascii=False)

# 专业×地域页的默认专业：取矩阵中招录人数最多的专业，
# 保证用户一进这个 Tab 就有数据可看（ALL_MAJORS[0] 可能是招录极少的专业）。
_major_total = {}
for _city, _majors in city_data['city_major_matrix'].items():
    for _m, _n in _majors.items():
        _major_total[_m] = _major_total.get(_m, 0) + _n
default_major = max(_major_total, key=_major_total.get) if _major_total else ''

# ====== HTML生成辅助 ======
ranking_index_by_major = {m['major']: i for i, m in enumerate(major_data['ranking'])}

def major_label(m):
    base = m["major"].replace("（旧版乡镇招考代码）", "（旧版"+m["code"]+"）") if m.get("type")=="township" and m.get("code") else m["major"]
    return base + (" ("+m["code"]+")" if m.get("code") and m.get("type")!="township" else "")

def with_focus_majors(items):
    seen = {m['major'] for m in items}
    expanded = list(items)
    for name in FOCUS_MAJOR_NAMES:
        if name in seen:
            continue
        idx = ranking_index_by_major.get(name)
        if idx is not None:
            expanded.append(major_data['ranking'][idx])
            seen.add(name)
    return expanded

def make_dd_opts(items):
    return ''.join(
        f'<option value="{ranking_index_by_major[m["major"]]}">{major_label(m)}</option>'
        for m in items
    )

def make_trend_opts(items, sel=0):
    selected_major = items[sel]['major'] if 0 <= sel < len(items) else items[0]['major']
    return ''.join(
        f'<option value={ranking_index_by_major[m["major"]]}{" selected" if m["major"]==selected_major else ""}>{major_label(m)}</option>'
        for m in items
    )

def make_chk(items, limit=20, ck=0):
    return ''.join(
        f'<div class="compare-item"><input type="checkbox" value={ranking_index_by_major[m["major"]]} {"checked" if i<ck else ""} onchange="updateCompare()"><span>{major_label(m)}</span></div>'
        for i,m in enumerate(with_focus_majors(items[:limit]))
    )

dd_opts = make_dd_opts(with_focus_majors(major_data['top30']))
trend_items = with_focus_majors(major_data['top30'][:15])
tr_opts = make_trend_opts(trend_items)
tr_opts_2 = make_trend_opts(trend_items, 4)
tr_opts_3 = make_trend_opts(trend_items, 6)
chk_html = make_chk(major_data['ranking'], 20, 3)

sum_pos = major_summary['total_position_rows']
sum_maj = major_summary['unique_majors_found']
total_ranked = len(major_data['ranking'])
top_recruit = major_data['top30'][0]['total_recruits']

# ====== 完整HTML ======
html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>广东省考综合数据分析看板 (2020-2026)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Serif+SC:wght@600;700&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
<script src="assets/echarts.min.js?v=5.5.0"></script>
<style>
:root {
  --page-bg: #0a0e17;
  --card-bg: #FFFFFF;
  --card-bg-glass: rgba(255,255,255,0.75);
  --border: #D4D4D0;
  --fill-warm: #F2F0EA;
  --font-serif: "Noto Serif SC","Source Han Serif SC","STSong",serif;
  --font-sans: "Inter","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
  --font-mono: "JetBrains Mono","SF Mono","Fira Code",monospace;

  /* -- Ink neutral palette -- */
  --ink-50: #f8fafc;
  --ink-100: #f1f5f9;
  --ink-200: #e2e8f0;
  --ink-300: #cbd5e1;
  --ink-400: #94a3b8;
  --ink-500: #64748b;
  --ink-600: #475569;
  --ink-700: #334155;
  --ink-800: #1e293b;
  --ink-900: #0f172a;
  --ink-950: #020617;

  /* -- Blue palette -- */
  --blue-50: #eff6ff;
  --blue-100: #dbeafe;
  --blue-200: #bfdbfe;
  --blue-300: #93c5fd;
  --blue-400: #60a5fa;
  --blue-500: #3b82f6;
  --blue-600: #2563eb;
  --blue-700: #1d4ed8;
  --blue-800: #1e3a5f;
  --blue-900: #16345a;

  /* -- Accent -- */
  --amber-50: #fffbeb;
  --amber-100: #fef3c7;
  --amber-400: #fbbf24;
  --amber-500: #f59e0b;
  --amber-600: #d97706;
  --green-500: #10b981;
  --green-600: #059669;
  --red-500: #ef4444;
  --red-600: #dc2626;

  /* -- Surface tokens -- */
  --surface-card: #ffffff;
  --surface-elevated: rgba(255,255,255,0.92);
  --surface-subtle: var(--ink-50);
  --surface-warm: #f2f0ea;

  /* -- Radii -- */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 18px;

  /* -- Shadows -- */
  --shadow-sm: 0 1px 2px rgba(15,23,42,0.04);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
  --shadow-lg: 0 16px 44px rgba(15,23,42,0.1);

  /* -- Premium visual system -- */
  --premium-surface: rgba(255,255,255,0.82);
  --premium-surface-strong: rgba(255,255,255,0.94);
  --premium-line: rgba(148,163,184,0.22);
  --premium-line-strong: rgba(100,116,139,0.28);
  --premium-shadow: 0 18px 45px rgba(15,23,42,0.08);
  --premium-shadow-soft: 0 8px 24px rgba(15,23,42,0.055);
  --premium-radius: 16px;
  --premium-radius-sm: 12px;
  --premium-blur: blur(18px);

  /* -- Legacy aliases (point to tokens) -- */
  --text-primary: var(--ink-900);
  --text-secondary: var(--ink-600);
  --text-tertiary: var(--ink-400);
  --accent-blue: var(--blue-800);
  --accent-amber: var(--amber-600);
  --accent-sky: var(--blue-500);
  --glass-border: rgba(0,0,0,0.08);
  --glass-shadow: var(--shadow-md);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:var(--font-sans); background:var(--page-bg); color:var(--text-primary); font-size:15px; line-height:1.65; -webkit-font-smoothing:antialiased; min-height:100vh; }

/* ===== SVG Wave Background ===== */
#wave-bg { position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:-1; pointer-events:none; overflow:hidden; opacity:0.55; }
#wave-bg svg { width:100%; height:100%; }

/* ===== Container ===== */
.container { max-width:1280px; margin:0 auto; padding:32px 28px; position:relative; z-index:1; backdrop-filter:blur(2px); }

/* ===== Hero ===== */
.hero { background:linear-gradient(135deg, #0f1a2e 0%, #1a3050 40%, #1E3A5F 100%); border-radius:12px; padding:36px 40px 32px; margin-bottom:28px; position:relative; overflow:hidden; border:1px solid rgba(255,255,255,0.06); box-shadow:0 4px 40px rgba(30,58,95,0.3); }
.hero::before { content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:radial-gradient(ellipse at 30% 20%, rgba(59,130,246,0.08) 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, rgba(217,119,6,0.05) 0%, transparent 50%); pointer-events:none; }
.hero h1 { font-family:var(--font-serif); font-size:clamp(1.4rem, 3.5vw, 2rem); font-weight:700; color:#fff; text-align:center; letter-spacing:0.04em; margin-bottom:4px; position:relative; }
.hero h1 .help-btn { display:inline-block; width:24px; height:24px; line-height:24px; text-align:center; border-radius:50%; background:rgba(255,255,255,0.12); color:#fff; font-size:14px; font-weight:600; cursor:pointer; margin-left:10px; vertical-align:middle; transition:all 0.2s; }
.hero h1 .help-btn:hover { background:rgba(255,255,255,0.25); transform:scale(1.1); }
.hero-subtitle { text-align:center; color:rgba(255,255,255,0.55); font-size:13px; margin-bottom:24px; letter-spacing:0.02em; position:relative; }
.stats-bar { display:flex; justify-content:center; gap:10px; flex-wrap:wrap; position:relative; }
.stat-item { text-align:center; background:rgba(255,255,255,0.07); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); border-radius:10px; padding:14px 22px; min-width:110px; border:1px solid rgba(255,255,255,0.08); transition:all 0.25s ease; }
.stat-item:hover { background:rgba(255,255,255,0.12); transform:translateY(-2px); border-color:rgba(255,255,255,0.18); }
.stat-num { font-family:var(--font-mono); font-size:clamp(1.1rem, 2.5vw, 1.6rem); font-weight:600; color:#fff; letter-spacing:-0.02em; }
.stat-label { font-size:12px; color:rgba(255,255,255,0.55); margin-top:2px; font-weight:400; }

/* ===== Status Ping ===== */
.status-dot { display:inline-flex; align-items:center; gap:6px; color:rgba(255,255,255,0.5); font-size:11px; position:absolute; bottom:10px; right:16px; }
.status-dot .ping { width:7px; height:7px; border-radius:50%; background:#22c55e; position:relative; }
.status-dot .ping::before { content:''; position:absolute; inset:-3px; border-radius:50%; background:#22c55e; animation:ping 2s cubic-bezier(0,0,0.2,1) infinite; opacity:0.4; }
@keyframes ping { 75%,100% { transform:scale(2); opacity:0; } }
.section-nav { display:flex; gap:4px; margin-bottom:0; border-bottom:1px solid var(--border); padding-bottom:0; }
.section-btn { padding:12px 24px; text-align:center; cursor:pointer; font-size:14px; font-weight:500; color:var(--text-secondary); border:none; background:transparent; position:relative; transition:all 0.2s; }
.section-btn:hover { color:var(--accent-sky); background:rgba(59,130,246,0.04); }
.section-btn.active { color:var(--accent-sky); font-weight:600; }
.section-btn.active::after { content:""; position:absolute; bottom:-1px; left:20%; width:60%; height:2px; background:var(--accent-sky); border-radius:1px; }
.sub-tabs { display:flex; gap:0; margin-bottom:0; border-bottom:1px solid var(--border); flex-wrap:wrap; }
.sub-tab-btn { padding:10px 20px; text-align:center; cursor:pointer; font-size:13px; font-weight:500; color:var(--text-secondary); border:none; background:transparent; position:relative; transition:all 0.2s; }
.sub-tab-btn:hover { color:var(--accent-sky); background:rgba(59,130,246,0.04); }
.sub-tab-btn.active { color:var(--accent-sky); font-weight:600; }
.sub-tab-btn.active::after { content:""; position:absolute; bottom:-1px; left:15%; width:70%; height:2px; background:var(--accent-sky); border-radius:1px; }
.sub-tab-content { display:none; background:var(--card-bg); border:1px solid var(--border); border-top:none; border-radius:0 0 10px 10px; padding:24px; min-height:400px; box-shadow:var(--glass-shadow); }
.sub-tab-content.active { display:block; }
.section-content { display:none; }
.section-content.active { display:block; }
.chart-box { width:100%; height:500px; }
.chart-box-sm { width:100%; height:350px; }
.chart-box-map { width:100%; height:560px; }
.network-wrap { width:100%; height:680px; background:var(--card-bg); border:1px solid var(--border); border-radius:10px; overflow:hidden; box-shadow:var(--glass-shadow); }
#networkChart { width:100%; height:580px; }
.select-bar { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:16px; }
.select-bar label { font-weight:500; color:var(--text-secondary); font-size:13px; }
.select-bar select, .select-bar input { padding:6px 12px; border:1px solid var(--border); border-radius:6px; font-size:13px; color:var(--text-primary); background:#fff; transition:all 0.15s; }
.select-bar select:focus, .select-bar input:focus { outline:none; border-color:var(--accent-sky); box-shadow:0 0 0 3px rgba(59,130,246,0.12); }
/* 专业搜索控件：1500+ 专业名无法用原生 select 查找，改为输入框 + 候选列表 */
.mcs-wrap { position:relative; flex:1; min-width:170px; max-width:280px; }
.mcs-wrap input { width:100%; }
.mcs-panel { display:none; position:absolute; z-index:120; top:calc(100% + 4px); left:0; right:0;
  max-height:264px; overflow-y:auto; background:#fff; border:1px solid var(--border);
  border-radius:8px; box-shadow:0 14px 34px rgba(15,23,42,0.14); padding:4px; }
.mcs-item { padding:7px 10px; border-radius:6px; font-size:13px; cursor:pointer; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
.mcs-item:hover { background:var(--fill-warm); }
.mcs-empty, .mcs-more { padding:8px 10px; font-size:12px; color:var(--text-tertiary); }
.table-wrap { overflow-x:auto; overflow-y:auto; margin-top:12px; max-height:600px; border-radius:8px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { background:var(--fill-warm); color:var(--accent-blue); padding:10px 8px; text-align:center; font-weight:600; border-bottom:1px solid var(--border); position:sticky; top:0; }
td { padding:8px 6px; text-align:center; border-bottom:1px solid rgba(0,0,0,0.04); white-space:nowrap; }
tr:hover td { background:var(--fill-warm); }
.table-wrap td:first-child, .table-wrap th:first-child { padding-left:12px; }
.table-wrap td:nth-child(2) { max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
th { white-space:nowrap; }
.rank-num { font-weight:600; }
.top3 { color:var(--accent-amber); }
.top5 { color:var(--accent-sky); }
.metrics { display:flex; gap:12px; flex-wrap:wrap; margin:12px 0; }
.metric { flex:1; min-width:130px; background:var(--fill-warm); border-radius:8px; padding:12px 14px; text-align:center; }
.metric-val { font-size:clamp(0.95rem, 1.8vw, 1.25rem); font-weight:700; color:var(--accent-blue); font-family:var(--font-mono); }
.metric-label { font-size:12px; color:var(--text-tertiary); margin-top:2px; }
.up { color:var(--red-600); font-weight:500; } .down { color:var(--green-600); font-weight:500; } .flat { color:var(--ink-400); }
.data-table { width:100%; border-collapse:separate; border-spacing:0; font-size:13px; table-layout:fixed; }
.data-table th { background:var(--fill-warm); color:var(--accent-blue); padding:12px 8px; text-align:center; font-weight:600; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:6; white-space:nowrap; box-shadow:0 1px 0 var(--border), 0 8px 18px rgba(15,23,42,0.06); }
.data-table td { padding:12px 8px; text-align:center; border-bottom:1px solid rgba(0,0,0,0.04); white-space:normal; line-height:1.35; vertical-align:middle; background:#fff; }
.data-table th:nth-child(1), .data-table td:nth-child(1) { width:6%; }
.data-table th:nth-child(2), .data-table td:nth-child(2) { width:21%; }
.data-table th:nth-child(3), .data-table td:nth-child(3) { width:12%; }
.data-table th:nth-child(4), .data-table td:nth-child(4) { width:10%; }
.data-table th:nth-child(5), .data-table td:nth-child(5) { width:10%; }
.data-table th:nth-child(6), .data-table td:nth-child(6) { width:10%; }
.data-table th:nth-child(7), .data-table td:nth-child(7) { width:11%; }
.data-table th:nth-child(8), .data-table td:nth-child(8) { width:10%; }
.data-table th:nth-child(9), .data-table td:nth-child(9) { width:10%; }
.data-table tbody tr:hover td { background:var(--fill-warm); }
.rank-pill { display:inline-block; min-width:22px; padding:2px 7px; border-radius:10px; font-size:11px; font-weight:600; text-align:center; font-family:var(--font-mono); border:none; }
.rank-pill.top1 { background:var(--amber-400); color:#1a1a1a; } .rank-pill.top3 { background:var(--amber-100); color:var(--ink-800); } .rank-pill.top5 { background:#fde68a; color:var(--ink-600); } .rank-pill.normal { background:var(--surface-subtle); color:var(--ink-500); }
.trend-text { font-size:11px; font-weight:500; font-family:var(--font-mono); padding:1px 6px; border-radius:4px; border:none; }
.trend-text.up { color:var(--red-600); background:rgba(220,38,38,0.08); } .trend-text.down { color:var(--green-600); background:rgba(5,150,105,0.08); } .trend-text.flat { color:var(--ink-400); background:rgba(0,0,0,0.04); }
.mini-bar-wrap { display:block; width:min(112px, 100%); height:8px; margin:6px auto 0; padding:0 2px; }
.mini-bar { width:100%; height:100%; border-radius:999px; background:var(--fill-warm); position:relative; overflow:hidden; }
.mini-bar .fill { position:absolute; bottom:0; left:0; height:100%; border-radius:999px; transition:width 0.3s; }
.mini-bar .fill.high { background:var(--blue-800); } .mini-bar .fill.mid { background:var(--blue-500); } .mini-bar .fill.low { background:var(--blue-200); }
.detail-panel { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.detail-full { grid-column:1/-1; }
@media (max-width:768px) { .detail-panel { grid-template-columns:1fr; } }

/* ===== Consistent container spacing ===== */
.metrics + .detail-panel,
.detail-panel + .detail-panel {
  margin-top: 20px;
}
.tags { display:flex; gap:5px; flex-wrap:wrap; margin:4px 0; }
.tag {
  background: var(--surface-subtle);
  padding: 2px 9px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--ink-600);
  border: none;
}
.tag.highlight { background:var(--blue-800); color:#fff; }
.tag-township { background:var(--amber-50); color:#92400e; padding:2px 8px; border-radius:6px; font-size:10px; font-weight:500; white-space:nowrap; }
.township-suffix { font-size:0.55em; opacity:0.9; white-space:nowrap; }

/* ===== Premium panel base ===== */
.premium-panel {
  border: 1px solid var(--premium-line);
  border-radius: var(--premium-radius);
  background: linear-gradient(145deg, var(--premium-surface-strong), rgba(248,250,252,0.86));
  box-shadow: var(--premium-shadow);
  backdrop-filter: var(--premium-blur);
  -webkit-backdrop-filter: var(--premium-blur);
  overflow: hidden;
}

.city-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .03em;
  background: var(--blue-50);
  color: var(--blue-700);
}

/* ===== Chart headline ===== */
.chart-headline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px 0;
}
.chart-title {
  margin-top: 2px;
  color: var(--blue-900);
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 800;
}
.chart-hint {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15,23,42,0.05);
  color: var(--ink-500);
  font-family: var(--font-mono);
  font-size: 12px;
}
.compare-chart-panel {
  padding-bottom: 8px;
}

.compare-grid { display:flex; flex-wrap:wrap; gap:8px; max-height:172px; overflow-y:auto; padding:14px; border:1px solid var(--premium-line); border-radius:var(--premium-radius); background:rgba(255,255,255,0.72); box-shadow:inset 0 1px 0 rgba(255,255,255,0.86); }
.compare-item { position:relative; display:inline-flex; }
.compare-item input { position:absolute; opacity:0; pointer-events:none; }
.compare-item span { display:inline-flex; align-items:center; min-height:34px; padding:7px 12px; border:1px solid rgba(148,163,184,0.28); border-radius:999px; background:rgba(255,255,255,0.76); color:var(--ink-700); font-size:12px; font-weight:600; letter-spacing:0; cursor:pointer; transition:transform .16s ease,border-color .16s ease,background .16s ease,box-shadow .16s ease; }
.compare-item span:hover { transform:translateY(-1px); border-color:rgba(59,130,246,0.38); box-shadow:var(--premium-shadow-soft); }
.compare-item input:checked+span { border-color:rgba(59,130,246,0.5); background:linear-gradient(135deg,rgba(59,130,246,0.15),rgba(255,255,255,0.92)); color:var(--blue-900); box-shadow:0 8px 20px rgba(37,99,235,0.10); }
.compare-item input:checked+span::before { content:""; display:inline-block; width:7px; height:7px; margin-right:7px; border-radius:999px; background:var(--accent-sky); box-shadow:0 0 0 4px rgba(59,130,246,0.12); flex-shrink:0; }
.compare-selector-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }
.eyebrow { color:var(--accent-sky); font-size:11px; font-weight:800; letter-spacing:.13em; }
.selector-title { margin-top:2px; color:var(--blue-900); font-family:var(--font-serif); font-size:16px; font-weight:800; }
.selector-meta { padding:6px 10px; border-radius:999px; background:rgba(30,58,95,0.08); color:var(--blue-800); font-size:12px; font-weight:700; }
.compare-charts-layout { display:grid; grid-template-columns:minmax(0,1.14fr) minmax(390px,.86fr); gap:20px; align-items:stretch; margin-top:16px; }
#comparePanel > .compare-selector-head,
#comparePanel > .compare-grid {
  margin-bottom: 16px;
}
.compare-main { min-height:520px; }
.compare-score-panel { min-height:520px; padding:18px; border:1px solid var(--premium-line); border-radius:var(--premium-radius); background:linear-gradient(145deg, var(--premium-surface-strong), rgba(248,250,252,0.88)); box-shadow:var(--premium-shadow); display:grid; gap:14px; align-content:start; overflow:hidden; }
.score-panel-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding-bottom:10px; border-bottom:1px solid var(--premium-line); }
.score-panel-kicker { font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--accent-blue); font-weight:700; margin-bottom:4px; }
.score-panel-title { font-family:var(--font-serif); color:var(--blue-900); font-size:17px; font-weight:700; }
.score-panel-note { color:var(--ink-500); font-size:12px; line-height:1.6; max-width:260px; }
.score-personas { display:grid; grid-template-columns:repeat(auto-fit,minmax(128px,1fr)); gap:10px; }
.score-major-card,
.score-metric-block {
  border: 1px solid rgba(148,163,184,0.16);
  background: rgba(255,255,255,0.66);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
}
.score-major-card { position:relative; padding:12px; border-radius:var(--premium-radius-sm); overflow:hidden; }
.score-metric-block { padding:14px; border-radius:var(--premium-radius-sm); }
.score-major-card:before { content:""; position:absolute; left:0; top:0; width:4px; height:100%; background:var(--score-color,#3b82f6); }
.score-major-name { font-size:13px; font-weight:700; color:var(--blue-900); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-left:4px; }
.score-major-meta { margin-top:8px; display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:11px; color:var(--ink-500); }
.score-major-meta b { display:block; color:var(--blue-800); font-family:var(--font-mono); font-size:13px; font-weight:700; }
.score-matrix { display:grid; gap:10px; }
.score-metric-head { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:10px; }
.score-metric-head b { display:block; color:var(--blue-900); font-size:13px; }
.score-metric-head span { display:block; margin-top:2px; color:var(--ink-500); font-size:11px; }
.score-best-chip { flex:0 0 auto; max-width:150px; padding:4px 8px; border-radius:999px; background:rgba(30,58,95,0.08); color:var(--blue-800); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.score-bars { display:grid; gap:8px; }
.score-bar-row { display:grid; grid-template-columns:minmax(68px,92px) minmax(80px,1fr) minmax(54px,auto); align-items:center; gap:8px; }
.score-name { color:var(--ink-600); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.score-track { height:8px; border-radius:999px; background:rgba(148,163,184,0.18); overflow:hidden; }
.score-track i { display:block; height:100%; border-radius:inherit; background:var(--score-color,#3b82f6); box-shadow:0 0 14px rgba(59,130,246,0.22); }
.score-value { color:var(--blue-900); font-family:var(--font-mono); font-size:11px; font-weight:700; text-align:right; white-space:nowrap; }
.score-empty { min-height:460px; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; color:var(--ink-500); }
.score-empty h3 { color:var(--blue-900); font-family:var(--font-serif); font-size:17px; margin-bottom:8px; }
.score-empty p { font-size:12px; line-height:1.7; max-width:260px; }
@media (max-width:900px) { .compare-charts-layout { grid-template-columns:1fr; gap:16px; } .compare-main, .compare-score-panel { min-height:420px; } .score-bar-row { grid-template-columns:minmax(76px,110px) 1fr minmax(56px,auto); } }
.sub-select-wrap { margin-left:auto; display:none; align-items:center; gap:8px; }
.sub-select-wrap select { min-width:200px; max-width:300px; }
.help-btn-sm { display:inline-block; width:20px; height:20px; line-height:20px; text-align:center; border-radius:50%; background:var(--accent-blue); color:#fff; font-size:11px; font-weight:600; cursor:pointer; margin-left:6px; user-select:none; transition:all 0.2s; }
.help-btn-sm:hover { opacity:0.85; transform:scale(1.1); }
.modal-overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); backdrop-filter:blur(4px); -webkit-backdrop-filter:blur(4px); z-index:1000; }
.modal-overlay.show { display:flex; align-items:center; justify-content:center; animation:fadeIn 0.2s ease; }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
.modal-content { background:var(--card-bg); border-radius:12px; padding:24px 28px; max-width:540px; width:90%; max-height:80vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,0.2); position:relative; border:1px solid var(--border); animation:slideUp 0.25s ease; }
@keyframes slideUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
.modal-close { position:absolute; top:10px; right:14px; font-size:22px; cursor:pointer; color:var(--text-tertiary); border:none; background:none; line-height:1; transition:color 0.15s; }
.modal-close:hover { color:var(--text-primary); }
.modal-content h3 { margin-bottom:14px; color:var(--blue-800); font-size:15px; font-family:var(--font-serif); }
.modal-term { margin-bottom:10px; padding:10px 14px; background:var(--surface-subtle); border-radius:8px; border-left:3px solid var(--blue-500); }
.modal-term .t { font-weight:600; color:var(--blue-800); display:block; margin-bottom:2px; }
.modal-term .d { font-size:12px; color:var(--ink-600); line-height:1.5; }
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
@media (max-width:768px) { .two-col { grid-template-columns:1fr; } }
.legend-tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; margin:2px; }
.prd-tag { background:var(--blue-100); color:var(--blue-900); }
.non-prd-tag { background:#f8d7da; color:#721c24; }
.province-tag { background:var(--blue-100); color:var(--blue-900); }
.city-detail-card { display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:var(--card-bg); border-radius:12px; padding:24px; box-shadow:0 20px 60px rgba(0,0,0,0.2); z-index:1000; max-width:480px; width:90%; max-height:80vh; overflow-y:auto; border:1px solid var(--border); animation:slideUp 0.25s ease; }
.city-detail-card.show { display:block; }
.city-detail-card h3 { color:var(--blue-800); margin-bottom:10px; border-bottom:1px solid var(--border); padding-bottom:8px; font-size:15px; font-family:var(--font-serif); }
.city-detail-card .close-btn { position:absolute; top:10px; right:14px; font-size:22px; cursor:pointer; color:var(--text-tertiary); border:none; background:none; }
.city-detail-card .detail-metrics { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:12px 0; }
.city-detail-card .dm-item { background:var(--fill-warm); padding:10px; border-radius:8px; text-align:center; }
.city-detail-card .dm-val { font-size:18px; font-weight:700; color:var(--accent-blue); font-family:var(--font-mono); }
.city-detail-card .dm-label { font-size:11px; color:var(--text-tertiary); }
.major-check-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:4px; max-height:240px; overflow-y:auto; padding:8px; background:var(--fill-warm); border-radius:8px; font-size:12px; border:1px solid var(--border); }
.overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:999; }
.overlay.show { display:block; }
/* ===== Premium dashboard component layer ===== */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: -2;
  pointer-events: none;
  background:
    radial-gradient(circle at 18% 18%, rgba(59,130,246,0.18), transparent 30%),
    radial-gradient(circle at 78% 10%, rgba(217,119,6,0.12), transparent 26%),
    linear-gradient(180deg, rgba(15,23,42,0.1), rgba(2,6,23,0.28));
}

.container {
  padding-bottom: 64px;
}

.section-nav {
  position: sticky;
  top: 14px;
  z-index: 30;
  gap: 8px;
  padding: 8px;
  margin-bottom: 0;
  border: 1px solid rgba(255,255,255,0.16);
  border-bottom: 1px solid rgba(255,255,255,0.1);
  border-radius: 18px 18px 0 0;
  background: linear-gradient(135deg, rgba(15,23,42,0.86), rgba(30,58,95,0.62));
  box-shadow: 0 24px 70px rgba(2,6,23,0.32), inset 0 1px 0 rgba(255,255,255,0.14);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
}

.section-btn {
  border-radius: 12px;
  color: rgba(226,232,240,0.78);
  letter-spacing: 0.02em;
}

.section-btn:hover {
  color: #fff;
  background: rgba(255,255,255,0.08);
}

.section-btn.active {
  color: #fff;
  background: linear-gradient(135deg, rgba(59,130,246,0.86), rgba(30,58,95,0.9));
  box-shadow: 0 10px 28px rgba(59,130,246,0.28), inset 0 1px 0 rgba(255,255,255,0.22);
}

.section-btn.active::after,
.sub-tab-btn.active::after {
  display: none;
}

.section-content.active {
  padding: 18px;
  border: 1px solid rgba(255,255,255,0.14);
  border-top: 0;
  border-radius: 0 0 22px 22px;
  background: var(--surface-elevated);
  box-shadow: 0 34px 90px rgba(2,6,23,0.36), inset 0 1px 0 rgba(255,255,255,0.74);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  animation: panelIn 0.28s ease-out both;
}

.sub-tabs {
  gap: 6px;
  padding: 6px;
  margin-bottom: 16px;
  border: 1px solid rgba(30,58,95,0.1);
  border-radius: 16px;
  background: var(--surface-subtle);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.sub-tab-btn {
  border-radius: 12px;
  color: var(--ink-600);
  letter-spacing: 0.01em;
}

.sub-tab-btn:hover {
  color: var(--blue-800);
  background: var(--blue-50);
}

.sub-tab-btn.active {
  color: var(--ink-900);
  background: var(--surface-card);
  box-shadow: 0 10px 24px rgba(30,58,95,0.13), inset 0 1px 0 rgba(255,255,255,0.9);
}

.sub-tab-content {
  border: 1px solid rgba(30,58,95,0.12);
  border-radius: 18px;
  background: var(--surface-elevated);
  box-shadow: 0 22px 52px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.9);
}

.sub-tab-content.active {
  animation: panelIn 0.26s ease-out both;
}

.select-bar {
  padding: 10px 12px;
  border: 1px solid rgba(30,58,95,0.1);
  border-radius: 14px;
  background: var(--surface-subtle);
}

.select-bar + .viz-panel,
.select-bar + .chart-box,
.select-bar + .chart-box-sm,
.select-bar + .chart-box-map,
.select-bar + .table-wrap {
  margin-top: 16px;
}

.select-bar select,
.select-bar input {
  border-color: rgba(30,58,95,0.14);
  border-radius: 10px;
  background: var(--surface-card);
}

.chart-box,
.chart-box-sm,
.chart-box-map,
.network-wrap {
  border: 1px solid rgba(30,58,95,0.1);
  border-radius: 16px;
  background: var(--surface-card);
  box-shadow: 0 16px 44px rgba(15,23,42,0.1), inset 0 1px 0 rgba(255,255,255,0.88);
  overflow: hidden;
}

/* ===== Viz Panel & Viz Head ===== */
.viz-panel {
  margin-bottom: 20px;
}

/* ===== Consistent section spacing ===== */
.section-content.active .sub-tab-content + .sub-tab-content {
  margin-top: 20px;
}
.sub-tab-content .viz-panel:last-child,
.sub-tab-content .table-wrap:last-child {
  margin-bottom: 0;
}
.chart-box + .table-wrap,
.chart-box-sm + .table-wrap,
.chart-box-map + .table-wrap {
  margin-top: 18px;
}
.viz-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 0 2px;
}
.viz-head-title {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 700;
  color: var(--blue-800);
}
.viz-head-desc {
  font-size: 12px;
  color: var(--ink-500);
  margin-left: 12px;
  flex: 1;
}
.viz-head-metric {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--amber-600);
  white-space: nowrap;
}

.chart-box:hover,
.chart-box-sm:hover,
.chart-box-map:hover,
.network-wrap:hover,
.table-wrap:hover {
  border-color: rgba(59,130,246,0.24);
  box-shadow: 0 22px 58px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.9);
}

.table-wrap {
  border: 1px solid rgba(30,58,95,0.1);
  border-radius: 16px;
  background: var(--surface-card);
  box-shadow: 0 14px 36px rgba(15,23,42,0.08);
}

.table-wrap table {
  border-collapse: separate;
  border-spacing: 0;
}

th {
  background: var(--surface-subtle);
  color: var(--blue-900);
  border-bottom: 1px solid rgba(30,58,95,0.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
}

td {
  border-bottom: 1px solid rgba(30,58,95,0.06);
}

tr:hover td {
  background: var(--blue-50);
}

.metric,
.compare-grid,
.city-detail-card .dm-item {
  border: 1px solid rgba(30,58,95,0.08);
  background: var(--surface-subtle);
}

.tag,
.legend-tag {
  border: none;
}

@keyframes panelIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .container { padding: 20px 14px 40px; }
  .section-nav { position: static; border-radius: 16px 16px 0 0; }
  .section-content.active { padding: 12px; border-radius: 0 0 18px 18px; }
  .sub-tabs { overflow-x: auto; flex-wrap: nowrap; }
  .sub-tab-btn { flex: 0 0 auto; padding: 9px 14px; }
  .sub-tab-content { padding: 16px; }
}
/* ===== Insight overview components ===== */
.overview-shell {
  display: grid;
  gap: 22px;
}

.overview-head {
  display: flex;
  justify-content: space-between;
  gap: 28px;
  align-items: flex-end;
  padding: 4px 2px 8px;
}

.overview-kicker {
  color: var(--blue-500);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  margin-bottom: 5px;
}

.overview-head h2 {
  color: var(--ink-900);
  font-family: var(--font-serif);
  font-size: clamp(1.35rem, 2.5vw, 2rem);
  line-height: 1.2;
}

.overview-head p {
  max-width: 480px;
  color: var(--ink-500);
  font-size: 13px;
  text-align: right;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.insight-card {
  position: relative;
  min-height: 172px;
  padding: 18px;
  border: 1px solid rgba(30,58,95,0.12);
  border-radius: 18px;
  background: var(--surface-elevated);
  box-shadow: 0 18px 42px rgba(15,23,42,0.1), inset 0 1px 0 rgba(255,255,255,0.92);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}

.insight-card:hover {
  transform: translateY(-3px);
  border-color: rgba(59,130,246,0.32);
  box-shadow: 0 26px 60px rgba(15,23,42,0.16), inset 0 1px 0 rgba(255,255,255,0.94);
}

.insight-card::after {
  content: '';
  position: absolute;
  inset: auto -20% -45% 30%;
  height: 110px;
  background: radial-gradient(circle, rgba(217,119,6,0.16), transparent 62%);
}

.insight-label {
  color: var(--ink-500);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.insight-value {
  margin-top: 10px;
  color: var(--ink-900);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.18;
}

.insight-meta {
  margin-top: 8px;
  color: var(--ink-600);
  font-size: 12px;
}

.insight-list {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 5px;
  margin-top: 14px;
}

.insight-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--ink-700);
  font-size: 12px;
}

.insight-row b {
  color: var(--ink-900);
  font-weight: 700;
}

.overview-split {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 14px;
}

.matrix-card,
.narrative-card {
  border: 1px solid rgba(30,58,95,0.12);
  border-radius: 18px;
  background: var(--surface-elevated);
  box-shadow: 0 16px 42px rgba(15,23,42,0.09), inset 0 1px 0 rgba(255,255,255,0.9);
  padding: 18px;
}

.mini-title {
  color: var(--ink-900);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.05em;
  margin-bottom: 14px;
}

.strategy-matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.matrix-quadrant {
  min-height: 150px;
  padding: 14px;
  border: 1px solid rgba(30,58,95,0.08);
  border-radius: 14px;
  background: var(--surface-subtle);
}

.matrix-quadrant h4 {
  color: var(--blue-900);
  font-size: 13px;
  margin-bottom: 8px;
}

.matrix-chip,
.tier-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  margin: 3px 3px 0 0;
  padding: 4px 8px;
  border-radius: 8px;
  background: var(--blue-50);
  color: var(--blue-800);
  font-size: 12px;
  white-space: nowrap;
  border: none;
}

.narrative-card h3 {
  color: var(--ink-900);
  font-family: var(--font-serif);
  font-size: 20px;
  margin-bottom: 12px;
}

.narrative-card p {
  color: var(--ink-600);
  font-size: 13px;
  line-height: 1.75;
  margin-bottom: 12px;
}

.action-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  color: var(--blue-800);
  background: var(--blue-50);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  border: none;
}

/* ===== Executive summary strip ===== */
.exec-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  padding: 18px 20px;
  border: 1px solid rgba(30,58,95,0.12);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(15,23,42,0.96), rgba(30,58,95,0.86)),
    radial-gradient(circle at 90% 10%, rgba(217,119,6,0.26), transparent 38%);
  box-shadow: 0 22px 56px rgba(15,23,42,0.22), inset 0 1px 0 rgba(255,255,255,0.12);
}

.exec-summary h3 {
  margin: 0 0 6px;
  color: #fff;
  font-family: var(--font-serif);
  font-size: clamp(1.05rem, 2vw, 1.45rem);
  line-height: 1.35;
}

.exec-summary p {
  margin: 0;
  color: rgba(226,232,240,0.72);
  font-size: 13px;
  line-height: 1.7;
}

.exec-summary .summary-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 86px;
  padding: 8px 12px;
  border-radius: 999px;
  color: #f8fafc;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.16);
  font-family: var(--font-mono);
  font-size: 12px;
}

.path-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.path-card {
  padding: 13px 14px;
  border-radius: 15px;
  border: 1px solid rgba(30,58,95,0.1);
  background: var(--surface-elevated);
  color: var(--ink-700);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.path-card:hover {
  transform: translateY(-2px);
  border-color: rgba(59,130,246,0.32);
  box-shadow: 0 16px 34px rgba(15,23,42,0.12);
}

.path-card b {
  display: block;
  color: var(--ink-900);
  font-size: 13px;
  margin-bottom: 4px;
}

.path-card span {
  display: block;
  color: var(--ink-500);
  font-size: 12px;
  line-height: 1.55;
}

@media (max-width: 980px) {
  .exec-summary { grid-template-columns: 1fr; }
  .path-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .path-grid { grid-template-columns: 1fr; }
}

.tier-list {
  display: grid;
  gap: 10px;
}

.tier-row {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 12px;
  align-items: start;
  padding: 12px;
  border-radius: 14px;
  background: var(--surface-subtle);
  border: 1px solid rgba(30,58,95,0.08);
}

.tier-name {
  color: var(--blue-900);
  font-size: 12px;
  font-weight: 800;
}

.tier-meta {
  margin-top: 4px;
  color: var(--ink-500);
  font-size: 11px;
  line-height: 1.35;
}

.tier-cities {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
@media (max-width: 980px) {
  .insight-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .overview-split { grid-template-columns: 1fr; }
  .overview-head { display: block; }
  .overview-head p { text-align: left; margin-top: 8px; }
}

@media (max-width: 560px) {
  .insight-grid,
  .strategy-matrix { grid-template-columns: 1fr; }
}
/* ===== Mobile / WeChat Adaptation ===== */
html {
  -webkit-text-size-adjust: 100%;
}
.container {
  padding-left: max(28px, env(safe-area-inset-left));
  padding-right: max(28px, env(safe-area-inset-right));
  padding-bottom: max(64px, env(safe-area-inset-bottom));
}
@media (max-width: 768px) {
  .hero { padding:24px 18px 20px; }
  .hero h1 { font-size:clamp(1.15rem,4.5vw,1.5rem); }
  .hero-subtitle { font-size:11px; line-height:1.5; white-space:normal; margin-bottom:16px; }
  .stats-bar { gap:6px; }
  .stat-item { padding:10px 14px; min-width:80px; }
  .stat-num { font-size:clamp(0.95rem,3vw,1.2rem); }
  .section-btn { padding:10px 14px; font-size:13px; }
  .section-nav { overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
  .section-nav::-webkit-scrollbar { display:none; }
  .section-btn { flex:0 0 auto; }
  .compare-grid { max-height:220px; }
  .compare-item span { padding:6px 10px; font-size:11px; min-height:36px; }
  .overview-split { grid-template-columns:1fr; }
  .overview-head { display:block; }
  .overview-head p { text-align:left; margin-top:8px; max-width:none; }
  .modal-content { width:calc(100vw - 24px); max-height:calc(100dvh - 40px); padding:20px 16px; }
  .city-detail-card { width:calc(100vw - 24px); max-height:calc(100dvh - 40px); }
  .city-detail-card .close-btn,
  .modal-close { width:44px; height:44px; font-size:28px; }
  .table-wrap { -webkit-overflow-scrolling:touch; }
  .table-wrap table,
  .data-table { min-width:720px; }
  #wave-bg { opacity:0.25; }
}
@media (max-width: 560px) {
  .container { padding:14px 10px 40px; }
  .hero { padding:18px 14px 16px; margin-bottom:16px; }
  .hero h1 { font-size:clamp(1.05rem,5vw,1.25rem); letter-spacing:0.02em; }
  .hero h1 .help-btn { width:22px; height:22px; line-height:22px; font-size:12px; margin-left:6px; }
  .hero-subtitle { font-size:10px; margin-bottom:12px; }
  .stats-bar { gap:4px; }
  .stat-item { padding:8px 10px; min-width:60px; border-radius:8px; }
  .stat-num { font-size:clamp(0.85rem,3.5vw,1rem); }
  .stat-label { font-size:10px; }
  .status-dot { position:static; margin-top:8px; justify-content:center; }
  .section-nav { position:static; border-radius:14px 14px 0 0; padding:6px; overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
  .section-nav::-webkit-scrollbar { display:none; }
  .section-content.active { padding:10px; }
  .section-btn { padding:8px 12px; font-size:12px; min-height:40px; border-radius:10px; flex:0 0 auto; }
  .sub-tabs { overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
  .sub-tabs::-webkit-scrollbar { display:none; }
  .sub-tab-btn { flex:0 0 auto; padding:9px 12px; font-size:12px; min-height:40px; }
  .sub-tab-content { padding:12px; min-height:auto; border-radius:0 0 14px 14px; }
  .select-bar { flex-direction:column; align-items:stretch; gap:8px; padding:12px; }
  .select-bar select,
  .select-bar input { width:100%; max-width:none !important; min-width:0 !important; box-sizing:border-box; font-size:12px; padding:5px 10px; }
  .select-bar label { font-size:12px; }
  .mcs-wrap { width:100%; max-width:none; min-width:0; }
  .mcs-panel { max-height:200px; }
  .sub-select-wrap { margin-left:0; width:100%; }
  .sub-select-wrap select { min-width:0; width:100%; }
  .compare-grid { max-height:200px; padding:10px; gap:6px; }
  .compare-item span { font-size:11px; min-height:34px; padding:6px 10px; }
  .compare-charts-layout { grid-template-columns:1fr; gap:14px; }
  .compare-main,
  .compare-score-panel { min-height:360px; }
  .chart-box { height:clamp(300px,80vw,400px); }
  .chart-box-sm { height:clamp(260px,72vw,340px); }
  .chart-box-map { height:clamp(340px,90vw,440px); }
  .network-wrap { height:clamp(380px,105vw,500px); }
  #networkChart { height:100%; }
  .overview-split { grid-template-columns:1fr; }
  .insight-grid { grid-template-columns:1fr; }
  .insight-card { min-height:140px; padding:14px; }
  .insight-value { font-size:20px; }
  .strategy-matrix { grid-template-columns:1fr; }
  .exec-summary { grid-template-columns:1fr; }
  .path-grid { grid-template-columns:1fr; }
  .overview-head p { font-size:12px; }
  .detail-panel { grid-template-columns:1fr; }
  .two-col { grid-template-columns:1fr; }
  .metrics { gap:8px; }
  .metric { min-width:100px; padding:10px; }
  .major-check-grid { grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); max-height:180px; }
  .score-personas { grid-template-columns:1fr; }
  .score-panel-note { max-width:none; }
  .city-detail-card .detail-metrics { grid-template-columns:1fr 1fr; }
  .table-wrap { max-height:400px; overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .table-wrap table,
  .data-table { min-width:720px; }
  .modal-content { width:calc(100vw - 16px); padding:18px 14px; border-radius:10px; }
  .modal-term { padding:8px 12px; }
  .city-detail-card { padding:18px; }
  .stat-item { backdrop-filter:none; -webkit-backdrop-filter:none; }
  .section-nav { backdrop-filter:blur(10px) saturate(120%); -webkit-backdrop-filter:blur(10px) saturate(120%); }
  #wave-bg { opacity:0.12; }
}
@media (max-width: 430px) {
  .container { padding:10px 8px 32px; }
  .hero h1 { font-size:clamp(0.95rem,5.5vw,1.1rem); }
  .hero-subtitle { font-size:9px; }
  .stat-item { padding:6px 8px; min-width:52px; }
  .stat-num { font-size:clamp(0.75rem,4vw,0.9rem); }
  .stat-label { font-size:9px; }
  .section-btn { font-size:11px; padding:6px 10px; }
  .sub-tab-btn { font-size:11px; padding:8px 10px; min-height:36px; }
  .sub-tab-content { padding:10px; }
  .chart-box { height:clamp(260px,78vw,360px); }
  .chart-box-sm { height:clamp(220px,68vw,300px); }
  .chart-box-map { height:clamp(300px,88vw,400px); }
  .network-wrap { height:clamp(340px,100vw,460px); }
  .select-bar { padding:10px; }
  .select-bar select,
  .select-bar input { font-size:12px; padding:5px 10px; }
  .viz-head { flex-wrap:wrap; gap:4px; }
  .viz-head-title { font-size:14px; }
  .viz-head-desc { font-size:11px; margin-left:0; width:100%; }
}
@media (prefers-reduced-motion: reduce) {
  *,*::before,*::after { animation-duration:0.01ms !important; animation-iteration-count:1 !important; transition-duration:0.01ms !important; }
  #wave-bg { display:none; }
}
</style>
</head>
<body>
<div id="wave-bg"><svg id="wave-svg"></svg></div>
<div class="container">

<div class="hero">
<h1>广东省公务员招录 · 综合数据分析看板 <span class="help-btn" onclick="showHelp()">?</span></h1>
<p class="hero-subtitle">数据来源：广东省 2020-2026 年考试录用公务员职位表 &nbsp;|&nbsp; 共 __SUM_POS__ 条含专业要求的职位记录，覆盖 __SUM_MAJ__ 个专业 · __TOTAL_CITIES__ 个城市</p>

<div class="stats-bar" id="statsBar">
  <div class="stat-item"><div class="stat-num">__TOTAL_RANKED__</div><div class="stat-label">统计专业数</div></div>
  <div class="stat-item"><div class="stat-num">__SUM_POS__</div><div class="stat-label">含专业要求职位</div></div>
  <div class="stat-item"><div class="stat-num">__TOTAL_CITIES__</div><div class="stat-label">覆盖城市</div></div>
  <div class="stat-item"><div class="stat-num">2020-2026</div><div class="stat-label">数据跨度</div></div>
  <div class="stat-item"><div class="stat-num">__TOP_RECRUIT__</div><div class="stat-label">榜首专业招录</div></div>
</div>
<div class="status-dot"><span class="ping"></span>数据更新至 2026</div>
</div>

<!-- 一级导航 -->
<div class="section-nav">
  <button class="section-btn active" data-section="section1" onclick="switchSection('section1')">专业热度分析</button>
  <button class="section-btn" data-section="section2" onclick="switchSection('section2')">地域维度分析</button>
</div>

<!-- ==================== 专业热度分析区域 ==================== -->
<div class="section-content active" id="section1">
<div class="sub-tabs">
  <button class="sub-tab-btn active" data-subtab="m-tab0" onclick="switchSubTab('m-tab0',this)">洞察总览</button>
  <button class="sub-tab-btn" data-subtab="m-tab1" onclick="switchSubTab('m-tab1',this)">Top30排名</button>
  <button class="sub-tab-btn" data-subtab="m-tab2" onclick="switchSubTab('m-tab2',this)">专业详情</button>
  <button class="sub-tab-btn" data-subtab="m-tab3" onclick="switchSubTab('m-tab3',this)">关联网络</button>
  <button class="sub-tab-btn" data-subtab="m-tab4" onclick="switchSubTab('m-tab4',this)">趋势总览</button>
  <button class="sub-tab-btn" data-subtab="m-tab5" onclick="switchSubTab('m-tab5',this)">综合对比</button>
</div>

<!-- 专业 Tab0: 洞察总览 -->
<div class="sub-tab-content active" id="m-tab0">
  <div class="overview-shell">
    <div class="overview-head">
      <div>
        <p class="overview-kicker">MAJOR INTELLIGENCE</p>
        <h2>先看结论，再下钻专业</h2>
      </div>
      <p>把 __TOTAL_RANKED__ 个专业压缩成规模、增速、应届友好、专业开放度四条决策线索。点击卡片可直接进入对应分析。</p>
    </div>
    <div class="exec-summary" id="majorExecSummary"></div>
    <div class="premium-panel" style="padding:6px;"><div class="path-grid" id="majorPathGrid"></div></div>
    <div class="insight-grid" id="majorInsightGrid"></div>
    <div class="overview-split">
      <div class="matrix-card">
        <div class="mini-title">专业策略矩阵</div>
        <div id="majorStrategyMatrix" class="strategy-matrix"></div>
      </div>
      <div class="narrative-card" id="majorNarrative"></div>
    </div>
  </div>
</div>

<!-- 专业 Tab1: Top30排名 -->
<div class="sub-tab-content" id="m-tab1">
  <div class="select-bar">
    <label>显示：</label>
    <select id="rankMode" onchange="switchRankMode()">
      <option value="recruits">按招录总人数</option>
      <option value="positions">按职位总数</option>
      <option value="purity">按纯洁度</option>
      <option value="growth">按增长率</option>
    </select>
    <input type="text" id="rankSearch" placeholder="搜索专业..." oninput="filterRankTable()" style="flex:1;max-width:220px;">
    <span id="rankCount" style="color:var(--ink-400);font-size:12px;"></span>
  </div>
  <div class="viz-panel">
    <div id="rankChartHead"></div>
    <div class="premium-panel" style="padding:4px;">
      <div class="chart-box" id="rankChart" style="height:420px;"></div>
    </div>
  </div>
  <div class="premium-panel" style="padding:2px;margin-top:12px;"><div class="table-wrap" id="rankTableWrap"></div></div>
  <div style="margin-top:24px;border-top:1px solid var(--ink-200);padding-top:18px;">
    <h3 style="margin:0 0 6px;color:var(--blue-800);font-size:14px;">📉 招录最少 Top30 专业</h3>
    <p style="margin:0 0 12px;color:var(--ink-400);font-size:12px;">按2020-2026年累计招录人数从少到多排序</p>
    <div class="chart-box-sm" id="lowRankChart"></div>
    <div class="table-wrap" id="lowRankTableWrap"></div>
  </div>
</div>

<!-- 专业 Tab2: 专业详情 -->
<div class="sub-tab-content" id="m-tab2">
  <div class="select-bar">
    <label>选择专业：</label>
    <select id="detailSelect" onchange="switchDetail()" style="min-width:260px;">
      __DD_OPTS__
    </select>
    <span class="help-btn-sm" onclick="showDetailHelp()">?</span>
    <div class="sub-select-wrap" id="detailSubSelect">
      <label>细分专业：</label>
      <select id="subDetailSelect" onchange="switchDetail()"></select>
    </div>
  </div>
  <div class="metrics" id="detailMetrics"></div>
  <div class="detail-panel">
    <div class="chart-box-sm" id="detailTrendChart"></div>
    <div class="chart-box-sm" id="detailDistChart"></div>
    <div class="detail-full chart-box-sm" id="detailEduChart"></div>
    <div class="detail-full" id="detailCoTable"></div>
  </div>
</div>

<!-- 专业 Tab3: 关联网络 -->
<div class="sub-tab-content" id="m-tab3">
  <div class="select-bar">
    <label>中心专业：</label>
    <select id="networkSelect" onchange="initNetwork(this.value === 'global' ? 'global' : RANKING[parseInt(this.value)].major)" style="min-width:260px;">
      __NETWORK_DD_OPTS__
    </select>
    <span style="font-size:12px;color:var(--ink-400);">默认显示全局关系；选择专业后只显示该专业的直接关联项</span>
  </div>
  <div class="network-wrap" id="networkChart"></div>
</div>

<!-- 专业 Tab4: 趋势总览 -->
<div class="sub-tab-content" id="m-tab4">
  <div class="two-col">
    <div>
      <h3 style="color:var(--blue-800);margin-bottom:8px;font-size:14px;">📈 招录人数趋势</h3>
      <select id="trendSelect1" onchange="switchTrend()" style="margin-bottom:8px;padding:4px 8px;border:1px solid var(--ink-200);border-radius:6px;">__TR_OPTS__</select>
      <div class="chart-box-sm" id="trendChart1"></div>
    </div>
    <div>
      <h3 style="color:var(--blue-800);margin-bottom:8px;font-size:14px;">📊 应届占比趋势</h3>
      <select id="trendSelect2" onchange="switchTrend()" style="margin-bottom:8px;padding:4px 8px;border:1px solid var(--ink-200);border-radius:6px;">__TR_OPTS_2__</select>
      <div class="chart-box-sm" id="trendChart2"></div>
    </div>
  </div>
  <div style="margin-top:12px;">
    <h3 style="color:var(--blue-800);margin-bottom:8px;font-size:14px;">📊 各专业应届比例对比</h3>
    <select id="trendSelect3" onchange="switchTrend()" style="margin-bottom:8px;padding:4px 8px;border:1px solid var(--ink-200);border-radius:6px;">__TR_OPTS_3__</select>
    <div class="chart-box-sm" id="trendChart3"></div>
  </div>
</div>

<!-- 专业 Tab5: 综合对比 -->
<div class="sub-tab-content" id="m-tab5">
  <div id="comparePanel">
    <div class="compare-selector-head">
      <div>
        <div class="eyebrow">SELECT MAJORS</div>
        <div class="selector-title">选择对比专业</div>
      </div>
      <div class="selector-meta" id="compareSelectedCount">已选 3</div>
    </div>
    <div class="compare-grid" id="compareGrid">__CHK_HTML__</div>
    <div class="compare-charts-layout">
      <div class="premium-panel compare-chart-panel">
        <div class="chart-headline">
          <div>
            <div class="eyebrow">TREND</div>
            <div class="chart-title">年度招录趋势</div>
          </div>
          <div class="chart-hint">2020-2026</div>
        </div>
        <div class="chart-box compare-main" id="compareChart"></div>
      </div>
      <div class="compare-score-panel" id="compareScorePanel"></div>
    </div>
  </div>
</div>
</div><!-- /section1 -->

<!-- ==================== 地域维度分析区域 ==================== -->
<div class="section-content" id="section2">
<div class="sub-tabs">
  <button class="sub-tab-btn active" data-subtab="c-tab0" onclick="switchSubTab('c-tab0',this)">城市洞察</button>
  <button class="sub-tab-btn" data-subtab="c-tab1" onclick="switchSubTab('c-tab1',this)">🗺️ 地图总览</button>
  <button class="sub-tab-btn" data-subtab="c-tab2" onclick="switchSubTab('c-tab2',this)">📊 城市排名</button>
  <button class="sub-tab-btn" data-subtab="c-tab3" onclick="switchSubTab('c-tab3',this)">📈 年度趋势</button>
  <button class="sub-tab-btn" data-subtab="c-tab4" onclick="switchSubTab('c-tab4',this)">🎓 应往届·学历</button>
  <button class="sub-tab-btn" data-subtab="c-tab5" onclick="switchSubTab('c-tab5',this)">🎯 专业×地域</button>
  <button class="sub-tab-btn" data-subtab="c-tab6" onclick="switchSubTab('c-tab6',this)">📋 城市对比</button>
</div>

<!-- 地域 Tab0: 城市洞察 -->
<div class="sub-tab-content active" id="c-tab0">
  <div class="overview-shell">
    <div class="overview-head">
      <div>
        <p class="overview-kicker">CITY INTELLIGENCE</p>
        <h2>先判断城市格局，再看地图分布</h2>
      </div>
      <p>把 __TOTAL_CITIES__ 个城市归纳为规模中心、增长弹性、应届友好和专业集中度，帮助快速判断地区机会。</p>
    </div>
    <div class="exec-summary" id="cityExecSummary"></div>
    <div class="premium-panel" style="padding:6px;"><div class="path-grid" id="cityPathGrid"></div></div>
    <div class="insight-grid" id="cityInsightGrid"></div>
    <div class="overview-split">
      <div class="matrix-card">
        <div class="mini-title">城市机会阶梯</div>
        <div id="cityTierList" class="tier-list"></div>
      </div>
      <div class="narrative-card" id="cityNarrative"></div>
    </div>
  </div>
</div>

<!-- 地域 Tab1: 地图 -->
<div class="sub-tab-content" id="c-tab1">
  <div class="select-bar">
    <label>显示模式：</label>
    <select id="mapMode" onchange="switchMapMode()">
      <option value="total">绝对招录人数</option>
      <option value="density">每职位招录比</option>
      <option value="growth">招录增长率</option>
    </select>
    <label>分组：</label>
    <select id="mapGroup" onchange="switchMapGroup()">
      <option value="none">无</option>
      <option value="prd">珠三角 vs 非珠</option>
    </select>
    <span style="margin-left:auto;font-size:11px;color:var(--ink-400);">
      <span class="legend-tag prd-tag">珠三角</span>
      <span class="legend-tag non-prd-tag">非珠三角</span>
    </span>
  </div>
  <div class="viz-panel">
    <div id="mapChartHead"></div>
    <div class="chart-box-map" id="mapChart"></div>
  </div>
</div>

<!-- 地域 Tab2: 城市排名 -->
<div class="sub-tab-content" id="c-tab2">
  <div class="select-bar">
    <label>排序：</label>
    <select id="cityRankMode" onchange="switchCityRankMode()">
      <option value="recruits">按招录人数</option>
      <option value="positions">按职位数</option>
      <option value="growth">按增长率</option>
      <option value="fresh">按应届占比</option>
    </select>
    <input type="text" id="cityRankSearch" placeholder="搜索城市..." oninput="filterCityRankTable()" style="flex:1;max-width:180px;">
    <span id="cityRankCount" style="color:var(--ink-400);font-size:12px;"></span>
  </div>
  <div class="viz-panel">
    <div id="cityRankChartHead"></div>
    <div class="premium-panel" style="padding:4px;">
      <div class="chart-box" id="cityRankChart" style="height:420px;"></div>
    </div>
  </div>
  <div class="premium-panel" style="padding:2px;margin-top:12px;"><div class="table-wrap" id="cityRankTableWrap"></div></div>
</div>

<!-- 地域 Tab3: 年度趋势 -->
<div class="sub-tab-content" id="c-tab3">
  <div class="select-bar">
    <label>城市选择：</label>
    <select id="trendCitySelect" multiple style="min-width:220px;height:90px;" onchange="updateCityTrend()">
    </select>
    <button onclick="selectDefaultCities()" style="padding:3px 8px;border:1px solid var(--ink-200);border-radius:4px;background:var(--surface-card);cursor:pointer;font-size:11px;">默认 Top6</button>
    <button onclick="selectAllCities()" style="padding:3px 8px;border:1px solid var(--ink-200);border-radius:4px;background:var(--surface-card);cursor:pointer;font-size:11px;">全选</button>
    <span style="font-size:11px;color:var(--ink-400);margin-left:8px;">按住 Ctrl 多选，最多 8 个</span>
  </div>
  <div class="viz-panel">
    <div id="cityTrendChartHead"></div>
    <div class="chart-box" id="cityTrendChart"></div>
  </div>
  <div class="table-wrap" id="cityTrendTableWrap"></div>
</div>

<!-- 地域 Tab4: 应往届 × 学历 -->
<div class="sub-tab-content" id="c-tab4">
  <div class="two-col">
    <div>
      <h3 style="color:var(--blue-800);margin-bottom:8px;font-size:14px;">🎓 各城市应往届分布</h3>
      <div class="chart-box-sm" id="freshChart"></div>
    </div>
    <div>
      <h3 style="color:var(--blue-800);margin-bottom:8px;font-size:14px;">📚 各城市学历分布</h3>
      <div class="chart-box-sm" id="eduChart"></div>
    </div>
  </div>
  <div style="margin-top:16px;border-top:1px solid var(--ink-200);padding-top:12px;">
    <div class="select-bar">
      <label>查看城市详情：</label>
      <select id="freshEduCity" onchange="updateFreshEduDetail()"></select>
    </div>
    <div class="two-col">
      <div class="chart-box-sm" id="freshDetailChart"></div>
      <div class="chart-box-sm" id="eduDetailChart"></div>
    </div>
  </div>
</div>

<!-- 地域 Tab5: 专业×地域 -->
<div class="sub-tab-content" id="c-tab5">
  <div class="select-bar">
    <label>视图：</label>
    <select id="majorCityView" onchange="switchMajorCityView()">
      <option value="major_to_city">按专业看城市分布</option>
      <option value="city_to_major">按城市看热门专业</option>
    </select>
    <input type="hidden" id="majorDefault" value="__DEFAULT_MAJOR__">
    <div class="mcs-wrap" id="majorSearchWrap">
      <input type="text" id="majorSearch" placeholder="输入专业名搜索…" autocomplete="off"
             oninput="filterMajorOptions()" onfocus="filterMajorOptions()" onchange="updateMajorCity()">
      <div class="mcs-panel" id="majorOptions"></div>
    </div>
    <select id="citySelect" onchange="updateMajorCity()" style="flex:1;max-width:180px;display:none;"></select>
  </div>
  <div class="chart-box" id="majorCityChart"></div>
  <div class="table-wrap" id="majorCityTableWrap"></div>
</div>

<!-- 地域 Tab6: 城市对比 -->
<div class="sub-tab-content" id="c-tab6">
  <div class="select-bar">
    <label>选择城市（2-4个）：</label>
    <select id="compareCities" multiple style="min-width:220px;height:100px;" onchange="updateCityCompare()">
    </select>
    <button onclick="selectCompareCities()" style="padding:3px 8px;border:1px solid var(--ink-200);border-radius:4px;background:var(--surface-card);cursor:pointer;font-size:11px;">广州vs深圳</button>
    <span style="font-size:11px;color:var(--ink-400);margin-left:8px;">按住 Ctrl 选择</span>
  </div>
  <div id="compareContent"></div>
</div>

</div><!-- /section2 -->

</div><!-- /container -->

<div class="overlay" id="helpOverlay" onclick="hideHelp()"></div>
<div class="city-detail-card" id="cityDetailCard">
  <button class="close-btn" onclick="hideCityDetail()">&times;</button>
  <div id="cityDetailContent"></div>
</div>

<script>
// ====== 数据注入（专业分析）======
var RANKING = __RANKING_JS__;
var RAW_RANKING = __RAW_RANKING_JS__;
var CO_PAIRS = __CO_PAIRS_JS__;

// ====== 数据注入（地域分析）======
var CITY_YEARLY = __CITY_YEARLY_JS__;
var CITY_RANKING = __CITY_RANKING_JS__;
var CITY_EDUCATION = __CITY_EDUCATION_JS__;
var CITY_FRESH = __CITY_FRESH_JS__;
var CITY_MAJOR_MATRIX = __CITY_MAJOR_MATRIX_JS__;
var GD_GEOJSON = __GD_GEOJSON_JS__;
var CITY_NAME_MAP = __CITY_NAME_MAP_JS__;
var ALL_MAJORS = __ALL_MAJORS_JS__;

var PRD_CITIES = ['广州','深圳','珠海','佛山','东莞','中山','惠州','江门','肇庆'];
var YEARS = ['2020','2021','2022','2023','2024','2025','2026'];
var COLORS = ['#1a3c6e','#2a5c9e','#3a7cce','#5a9cee','#8abcf5','#b0d4f8','#d0e4fc'];

function formatPercent(value) {
  return Math.round((value || 0) * 10) / 10;
}

// ====== 洞察总览：派生叙事层 ======
function formatNumber(n) {
  return (n || 0).toLocaleString('zh-CN');
}

function escHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}

function insightRows(items, valueFn) {
  return items.map(function(item) {
    return '<div class="insight-row"><span>' + escHtml(item.name) + '</span><b>' + escHtml(valueFn(item)) + '</b></div>';
  }).join('');
}

function insightCard(action, label, value, meta, rows) {
  return '<div class="insight-card" data-action="' + action + '">' +
    '<div class="insight-label">' + label + '</div>' +
    '<div class="insight-value">' + value + '</div>' +
    '<div class="insight-meta">' + meta + '</div>' +
    '<div class="insight-list">' + rows + '</div>' +
    '</div>';
}

function majorItems(list) {
  return list.map(function(m) { return { name: m.major + (m.code ? ' ' + m.code : ''), raw: m }; });
}

function activateSubTab(tabId) {
  var btn = document.querySelector('[data-subtab="' + tabId + '"]');
  if (btn) switchSubTab(tabId, btn);
}

function jumpMajorDetail(index) {
  var sel = document.getElementById('detailSelect');
  if (sel) sel.value = String(index || 0);
  activateSubTab('m-tab2');
  setTimeout(switchDetail, 120);
}

function jumpMajorRank(mode) {
  var sel = document.getElementById('rankMode');
  if (sel) sel.value = mode;
  activateSubTab('m-tab1');
  setTimeout(switchRankMode, 120);
}

function jumpCityRank(mode) {
  var sel = document.getElementById('cityRankMode');
  if (sel) sel.value = mode;
  activateSubTab('c-tab2');
  setTimeout(switchCityRankMode, 120);
}

function jumpCityDetail(city) {
  activateSubTab('c-tab1');
  setTimeout(function() { showCityDetail(city); }, 220);
}

function renderMajorOverview() {
  var grid = document.getElementById('majorInsightGrid');
  if (!grid || !Array.isArray(RANKING) || !RANKING.length) return;
  var scale = RANKING.slice().sort(function(a,b) { return b.total_recruits - a.total_recruits; }).slice(0, 3);
  var growth = RANKING.filter(function(m) { return m.total_recruits >= 300; }).sort(function(a,b) { return (b.growth_rate||0) - (a.growth_rate||0); }).slice(0, 3);
  var fresh = RANKING.filter(function(m) { return m.total_recruits >= 300; }).sort(function(a,b) { return (b.fresh_ratio||0) - (a.fresh_ratio||0); }).slice(0, 3);
  var compound = RANKING.filter(function(m) { return m.total_recruits >= 500; }).sort(function(a,b) { return (b.competition_index||0) - (a.competition_index||0); }).slice(0, 3);

  grid.innerHTML = [
    insightCard('major-scale', '规模重心', escHtml(scale[0].major), formatNumber(scale[0].total_recruits) + ' 人 · Top1', insightRows(majorItems(scale), function(item) { return formatNumber(item.raw.total_recruits); })),
    insightCard('major-growth', '需求上行', escHtml(growth[0].major), '+' + formatPercent(growth[0].growth_rate) + '% 增长率', insightRows(majorItems(growth), function(item) { return '+' + formatPercent(item.raw.growth_rate) + '%'; })),
    insightCard('major-fresh', '应届友好', escHtml(fresh[0].major), formatPercent(fresh[0].fresh_ratio) + '% 应届占比', insightRows(majorItems(fresh), function(item) { return formatPercent(item.raw.fresh_ratio) + '%'; })),
    insightCard('major-compound', '复合共招', escHtml(compound[0].major), (compound[0].competition_index || 0) + ' 竞争指数', insightRows(majorItems(compound), function(item) { return item.raw.competition_index || 0; }))
  ].join('');

  var actions = {
    'major-scale': function() { jumpMajorRank('recruits'); },
    'major-growth': function() { jumpMajorRank('growth'); },
    'major-fresh': function() { jumpMajorDetail(RANKING.indexOf(fresh[0])); },
    'major-compound': function() { jumpMajorDetail(RANKING.indexOf(compound[0])); }
  };
  grid.querySelectorAll('.insight-card').forEach(function(card) {
    card.addEventListener('click', function() { actions[card.dataset.action](); });
  });

  var buckets = [
    { title: '高规模 × 高增长', items: RANKING.filter(function(m) { return m.total_recruits >= 3000 && (m.growth_rate||0) >= 50; }).slice(0, 6) },
    { title: '高规模 × 稳定盘', items: RANKING.filter(function(m) { return m.total_recruits >= 5000 && (m.growth_rate||0) < 50; }).slice(0, 6) },
    { title: '小规模 × 快速上行', items: RANKING.filter(function(m) { return m.total_recruits < 2000 && (m.growth_rate||0) >= 100; }).slice(0, 6) },
    { title: '跨专业复合岗位', items: compound.concat(RANKING.filter(function(m) { return (m.competition_index||0) >= 2.2; }).slice(0, 3)).slice(0, 6) }
  ];
  document.getElementById('majorStrategyMatrix').innerHTML = buckets.map(function(bucket) {
    return '<div class="matrix-quadrant"><h4>' + bucket.title + '</h4>' + bucket.items.map(function(m) {
      return '<button class="matrix-chip" onclick="jumpMajorDetail(' + RANKING.indexOf(m) + ')">' + escHtml(m.major) + '<span>' + formatNumber(m.total_recruits) + '</span></button>';
    }).join('') + '</div>';
  }).join('');

  // -- Executive Summary --
  var majorTotal = RANKING.reduce(function(s,m) { return s + (m.total_recruits || 0); }, 0);
  var scaleTop3 = scale.reduce(function(s,m) { return s + (m.total_recruits || 0); }, 0);
  var top3Share = majorTotal ? Math.round(scaleTop3 / majorTotal * 1000) / 10 : 0;
  var topGrowth = growth[0];
  document.getElementById('majorExecSummary').innerHTML =
    '<div><h3>专业机会呈现"头部集中 + 理工复合上行"的结构</h3>' +
    '<p>Top3 专业合计占全部专业招录口径约 ' + top3Share + '%；' +
    escHtml(topGrowth.major) + ' 等增长赛道提示近年岗位需求正在重分配。</p></div>' +
    '<div class="summary-badge">' + formatNumber(majorTotal) + ' 人</div>';

  document.getElementById('majorPathGrid').innerHTML = [
    '<button class="path-card" onclick="jumpMajorRank(\'recruits\')"><b>想稳妥选岗</b><span>先看规模重心和长期高频专业。</span></button>',
    '<button class="path-card" onclick="jumpMajorDetail(' + RANKING.indexOf(fresh[0]) + ')"><b>想应届友好</b><span>优先查看应届占比和学历结构。</span></button>',
    '<button class="path-card" onclick="jumpMajorRank(\'growth\')"><b>想找上升赛道</b><span>按增长率排序，识别扩招专业。</span></button>',
    '<button class="path-card" onclick="jumpMajorDetail(' + RANKING.indexOf(compound[0]) + ')"><b>想避开拥挤</b><span>看复合共招，寻找可替代入口。</span></button>'
  ].join('');

  var topShare = Math.round(scale.slice(0, 3).reduce(function(s,m) { return s + m.total_recruits; }, 0) / RANKING.reduce(function(s,m) { return s + m.total_recruits; }, 0) * 1000) / 10;
  document.getElementById('majorNarrative').innerHTML = '<h3>读法建议</h3>' +
    '<p>专业侧可以先按四个问题阅读：哪里规模最大、哪里还在增长、哪里更照顾应届、哪里经常接受复合专业。Top3 专业合计约占全部专业招录口径的 ' + topShare + '%，规模集中度很高。</p>' +
    '<p>如果目标是稳妥选岗，优先看"规模重心"和"应届友好"；如果目标是避开拥挤赛道，则从"小规模 × 快速上行"和"复合共招"里找更细的机会。</p>' +
    '<button class="action-link" onclick="jumpMajorRank(\'recruits\')">进入完整专业排名</button>';
}

function renderCityOverview() {
  var grid = document.getElementById('cityInsightGrid');
  if (!grid || !Array.isArray(CITY_RANKING) || !CITY_RANKING.length) return;
  var cities = CITY_RANKING.slice();
  var scale = cities.slice().sort(function(a,b) { return CITY_YEARLY[b].total_recruits - CITY_YEARLY[a].total_recruits; }).slice(0, 3);
  var growth = cities.slice().sort(function(a,b) { return calcCityGrowth(b) - calcCityGrowth(a); }).slice(0, 3);
  var fresh = cities.slice().sort(function(a,b) { return calcCityFreshRatio(b) - calcCityFreshRatio(a); }).slice(0, 3);
  var density = cities.slice().sort(function(a,b) {
    return (CITY_YEARLY[b].total_recruits / Math.max(CITY_YEARLY[b].total_positions, 1)) - (CITY_YEARLY[a].total_recruits / Math.max(CITY_YEARLY[a].total_positions, 1));
  }).slice(0, 3);

  function cityItem(c) { return { name: c, raw: CITY_YEARLY[c] }; }
  grid.innerHTML = [
    insightCard('city-scale', '规模中心', escHtml(scale[0]), formatNumber(CITY_YEARLY[scale[0]].total_recruits) + ' 人', insightRows(scale.map(cityItem), function(item) { return formatNumber(item.raw.total_recruits); })),
    insightCard('city-growth', '增长弹性', escHtml(growth[0]), calcCityGrowth(growth[0]) + '% 增长率', insightRows(growth.map(cityItem), function(item) { return calcCityGrowth(item.name) + '%'; })),
    insightCard('city-fresh', '应届友好', escHtml(fresh[0]), calcCityFreshRatio(fresh[0]) + '% 应届占比', insightRows(fresh.map(cityItem), function(item) { return calcCityFreshRatio(item.name) + '%'; })),
    insightCard('city-density', '岗位密度', escHtml(density[0]), Math.round(CITY_YEARLY[density[0]].total_recruits / Math.max(CITY_YEARLY[density[0]].total_positions, 1) * 10) / 10 + ' 人/岗', insightRows(density.map(cityItem), function(item) { return Math.round(item.raw.total_recruits / Math.max(item.raw.total_positions, 1) * 10) / 10; }))
  ].join('');

  var actions = {
    'city-scale': function() { jumpCityRank('recruits'); },
    'city-growth': function() { jumpCityRank('growth'); },
    'city-fresh': function() { jumpCityRank('fresh'); },
    'city-density': function() { var sel = document.getElementById('mapMode'); if (sel) sel.value = 'density'; activateSubTab('c-tab1'); setTimeout(switchMapMode, 120); }
  };
  grid.querySelectorAll('.insight-card').forEach(function(card) {
    card.addEventListener('click', function() { actions[card.dataset.action](); });
  });

  var prdAll = cities.filter(function(c) { return getCityGroup(c) === 'prd'; });
  var nonPrdAll = cities.filter(function(c) { return getCityGroup(c) === 'non-prd'; });
  var specialAll = cities.filter(function(c) { return getCityGroup(c) === 'province'; });
  function sortCityList(list) {
    return list.slice().sort(function(a,b) { return CITY_YEARLY[b].total_recruits - CITY_YEARLY[a].total_recruits; });
  }
  function tierMeta(list) {
    var total = list.reduce(function(s,c) { return s + (CITY_YEARLY[c].total_recruits || 0); }, 0);
    var allTotal = cities.reduce(function(s,c) { return s + (CITY_YEARLY[c].total_recruits || 0); }, 0);
    var share = allTotal ? Math.round(total / allTotal * 1000) / 10 : 0;
    return list.length + '城 · ' + formatNumber(total) + '人 · ' + share + '%';
  }
  document.getElementById('cityTierList').innerHTML = [
    { name: '珠三角主轴', meta: tierMeta(prdAll), items: sortCityList(prdAll).slice(0, 6) },
    { name: '非珠三角腹地', meta: tierMeta(nonPrdAll), items: sortCityList(nonPrdAll).slice(0, 8) },
    { name: '省直岗位', meta: tierMeta(specialAll), items: sortCityList(specialAll) }
  ].map(function(tier) {
    return '<div class="tier-row"><div><div class="tier-name">' + tier.name + '</div><div class="tier-meta">' + tier.meta + '</div></div><div class="tier-cities">' + tier.items.map(function(c) {
      return '<button class="tier-chip" onclick="jumpCityDetail(\'' + escHtml(c) + '\')">' + escHtml(c) + '<span>' + formatNumber(CITY_YEARLY[c].total_recruits) + '</span></button>';
    }).join('') + '</div></div>';
  }).join('');

  // -- City Executive Summary --
  var allCities = CITY_RANKING.slice();
  var cityTotal = allCities.reduce(function(s,c) { return s + (CITY_YEARLY[c].total_recruits || 0); }, 0);
  var scaleTop3 = scale.reduce(function(s,c) { return s + (CITY_YEARLY[c].total_recruits || 0); }, 0);
  var scaleShare = cityTotal ? Math.round(scaleTop3 / cityTotal * 1000) / 10 : 0;
  document.getElementById('cityExecSummary').innerHTML =
    '<div><h3>城市机会呈现"规模中心明确 + 非珠三角承接强"的格局</h3>' +
    '<p>规模前三城市合计约占全省招录 ' + scaleShare + '%；同时非珠三角城市仍提供大量岗位池，适合和增长弹性一起判断。</p></div>' +
    '<div class="summary-badge">' + formatNumber(cityTotal) + ' 人</div>';

  document.getElementById('cityPathGrid').innerHTML = [
    '<button class="path-card" onclick="jumpCityRank(\'recruits\')"><b>看岗位池大小</b><span>按总招录人数判断城市规模。</span></button>',
    '<button class="path-card" onclick="jumpCityRank(\'growth\')"><b>看增长弹性</b><span>找近年扩招更明显的城市。</span></button>',
    '<button class="path-card" onclick="jumpCityRank(\'fresh\')"><b>看应届友好</b><span>按应届占比筛选报考环境。</span></button>',
    '<button class="path-card" onclick="activateSubTab(\'c-tab5\')"><b>看专业落点</b><span>按专业反查城市分布。</span></button>'
  ].join('');

  var top5Share = Math.round(scale.concat(cities.slice().filter(function(c) { return scale.indexOf(c) < 0; }).slice(0, 2)).reduce(function(s,c) { return s + CITY_YEARLY[c].total_recruits; }, 0) / cities.reduce(function(s,c) { return s + CITY_YEARLY[c].total_recruits; }, 0) * 1000) / 10;
  document.getElementById('cityNarrative').innerHTML = '<h3>读法建议</h3>' +
    '<p>地域侧先分两层看：第一层是广州、湛江等规模中心，决定岗位池大小；第二层是惠州、珠海等结构性指标，决定应届或密度机会。</p>' +
    '<p>招录规模前五城市合计约占全省 ' + top5Share + '%。如果只看总量容易错过增长弹性，所以建议先点"增长弹性"和"应届友好"，再回到地图看空间分布。</p>' +
    '<button class="action-link" onclick="jumpCityRank(\'recruits\')">进入城市排名</button>';
}

function rankPill(index) {
  var cls = 'rank-pill normal';
  var label = '' + (index + 1);
  if (index === 0) { cls = 'rank-pill top1'; }
  else if (index < 3) { cls = 'rank-pill top3'; }
  else if (index < 5) { cls = 'rank-pill top5'; }
  return '<span class="' + cls + '">' + label + '</span>';
}

function trendText(value) {
  if (value === undefined || value === null || isNaN(value)) return '<span class="trend-text flat">-</span>';
  var v = Math.round(value * 10) / 10;
  var absV = Math.abs(v);
  if (v > 0) return '<span class="trend-text up">&#9650;' + absV + '%</span>';
  if (v < 0) return '<span class="trend-text down">&#9660;' + absV + '%</span>';
  return '<span class="trend-text flat">0%</span>';
}

function miniBar(value, maxValue) {
  if (!maxValue) return '<div class="mini-bar-wrap"><div class="mini-bar"><div class="fill low" style="width:0%"></div></div></div>';
  var pct = Math.max(1, Math.round(value / maxValue * 100));
  if (pct > 100) pct = 100;
  var cls = pct > 66 ? 'high' : (pct > 33 ? 'mid' : 'low');
  return '<div class="mini-bar-wrap"><div class="mini-bar"><div class="fill ' + cls + '" style="width:' + pct + '%"></div></div></div>';
}

// ====== Chart Section Header Helper ======
function renderVizHead(title, desc, metric) {
  return '<div class="viz-head">' +
    '<span class="viz-head-title">' + title + '</span>' +
    '<span class="viz-head-desc">' + desc + '</span>' +
    '<span class="viz-head-metric">' + metric + '</span>' +
    '</div>';
}

function getYearEntry(yearly, year) {
  var item = yearly && yearly[year];
  if (typeof item === 'number') return { recruits: item, positions: 0, fresh_recruits: 0 };
  return item || { recruits: 0, positions: 0, fresh_recruits: 0 };
}
function getYearRecruits(yearly, year) {
  return getYearEntry(yearly, year).recruits || 0;
}
function getYearFreshRecruits(yearly, year) {
  return getYearEntry(yearly, year).fresh_recruits || 0;
}
function getYearFreshRatio(yearly, year) {
  var total = getYearRecruits(yearly, year);
  var fresh = getYearFreshRecruits(yearly, year);
  return total > 0 ? Math.round(fresh / total * 1000) / 10 : 0;
}

// ====== 一级导航切换 ======
function switchSection(sectionId) {
  document.querySelectorAll('.section-btn').forEach(function(b) { b.classList.remove('active'); });
  document.querySelectorAll('.section-content').forEach(function(c) { c.classList.remove('active'); });
  var sectionBtn = document.querySelector('.section-btn[data-section="'+sectionId+'"]');
  if (sectionBtn) sectionBtn.classList.add('active');
  var sectionEl = document.getElementById(sectionId);
  if (sectionEl) sectionEl.classList.add('active');
  // 激活该区域第一个subtab
  var firstTab = document.querySelector('#' + sectionId + ' .sub-tab-btn');
  if (firstTab) switchSubTab(firstTab.dataset.subtab, firstTab);
  setTimeout(resizeAll, 150);
}

// ====== 二级Tab切换 ======
function switchSubTab(tabId, btn) {
  if (!btn) btn = document.querySelector('[data-subtab="'+tabId+'"]');
  if (!btn) return;
  var parent = btn.closest('.section-content') || document;
  parent.querySelectorAll('.sub-tab-btn').forEach(function(b) { b.classList.remove('active'); });
  parent.querySelectorAll('.sub-tab-content').forEach(function(c) { c.classList.remove('active'); });
  btn.classList.add('active');
  var el = document.getElementById(tabId);
  if (el) el.classList.add('active');
  setTimeout(resizeAll, 100);
  // 图表在隐藏容器中初始化后仅 resize() 不足以触发完整重绘，
  // 需重新调用对应渲染函数以重新计算布局（地图投影、力导向、坐标轴等）
  var needsRefresh = {
    'm-tab0': 'renderMajorOverview',
    'm-tab1': 'refreshRankTab',
    'm-tab2': 'switchDetail',
    'm-tab3': 'initNetwork',
    'm-tab4': 'switchTrend',
    'm-tab5': 'updateCompare',
    'c-tab0': 'renderCityOverview',
    'c-tab1': 'switchMapMode',
    'c-tab2': 'switchCityRankMode',
    'c-tab3': 'updateCityTrend',
    'c-tab4': 'renderFreshEduOverview',
    'c-tab5': 'updateMajorCity',
    'c-tab6': 'updateCityCompare'
  };
  if (needsRefresh[tabId] && typeof window[needsRefresh[tabId]] === 'function') {
    setTimeout(function() { window[needsRefresh[tabId]](); }, 300);
  }
}

// Top30 排名 Tab 首次显示时的重绘入口：容器在隐藏状态下初始化，尺寸为 0，
// 需要重新 switchRankMode/renderLowRank 让坐标轴与柱子按真实宽度重算。
function refreshRankTab() {
  switchRankMode();
  renderLowRank();
}

function resizeAll() {
  var charts = document.querySelectorAll('.chart-box, .chart-box-sm, .chart-box-map, .network-wrap');
  charts.forEach(function(el) {
    var inst = echarts.getInstanceByDom(el);
    if (inst) inst.resize();
  });
}
// ====== 帮助弹窗（专业）======
function showHelp() {
  var html = '<div class="modal-overlay show" id="helpModalInner" onclick="if(event.target==this)hideHelp()"><div class="modal-content"><button class="modal-close" onclick="hideHelp()">&times;</button><h3>📖 指标说明</h3>';
  html += '<div class="modal-term"><span class="t">🔵 纯洁度</span><span class="d">该专业独占岗位的比例。100% = 该专业出现时都是单独招录；0% = 每次都和其他专业一同招录。</span></div>';
  html += '<div class="modal-term"><span class="t">🟠 竞争指数</span><span class="d">该专业出现时，同一岗位平均还有几个其他专业同时招录。</span></div>';
  html += '<div class="modal-term"><span class="t">🟢 关联专业 / 关联率</span><span class="d">经常和该专业出现在同一岗位要求里的其他专业。</span></div>';
  html += '<div class="modal-term"><span class="t">📈 增长率</span><span class="d">(2024-2026 年均 − 2020-2022 年均) / 基准。正数表示需求上升。</span></div>';
  html += '<div class="modal-term"><span class="t">🎓 应届占比</span><span class="d">限应届毕业生报考的岗位招录人数比例。</span></div>';
  html += '<div class="modal-term"><span class="t">🏷️ 旧版乡镇招考代码</span><span class="d">来自乡镇职位自定分类代码体系，2024年后停止使用。</span></div>';
  html += '<div class="modal-term"><span class="t">🔢 两个"职位数"的区别</span><span class="d">专业侧 74,849 = <b>含专业要求</b>的职位记录数（用于专业排名，不要求每个职位都写明专业）；地域侧 73,353 = 全部 sheet 的职位记录数（含"专业不限"的职位）。两者统计对象不同，因此不相等，页面内不做混用。</span></div>';
  html += '<div class="modal-term"><span class="t">📚 学历分组</span><span class="d">"本科以上"与"本科"是两档并列的最低学历门槛，互不重叠；"其他"为源表未标注学历的记录（约 1%）。</span></div>';
  html += '<div class="modal-term"><span class="t">🗺️ 关于省直</span><span class="d">"省直"是省级机关汇总口径，不是地级市，因此不出现在地图上，仅参与排名与对比。</span></div>';
  html += '</div></div></div>';
  var div = document.createElement('div'); div.innerHTML = html;
  div.id = 'helpModal'; document.body.appendChild(div);
}
function hideHelp() { var el = document.getElementById('helpModal'); if (el) el.remove(); }

function showDetailHelp() { showHelp(); }

// ====== 专业分析：排名模式切换 ======
var rankChart = null, lowRankChart = null;
function initMajorCharts() {
  rankChart = echarts.init(document.getElementById('rankChart'));
  lowRankChart = echarts.init(document.getElementById('lowRankChart'));
  switchRankMode();
  renderLowRank();
}
initMajorCharts();

function getRankData(mode) {
  var items = RANKING.slice();
  if (mode === 'recruits') items.sort(function(a,b) { return b.total_recruits - a.total_recruits; });
  else if (mode === 'positions') items.sort(function(a,b) { return b.total_positions - a.total_positions; });
  else if (mode === 'purity') items.sort(function(a,b) { return (b.purity||0) - (a.purity||0); });
  else if (mode === 'growth') items.sort(function(a,b) { return (b.growth_rate||0) - (a.growth_rate||0); });
  return items;
}

function switchRankMode() {
  var mode = document.getElementById('rankMode').value;
  var rankHeadMap = {
    recruits: ['专业招录 Top30', '按 2020-2026 年累计招录人数排序，观察岗位池规模。', '招录人数'],
    positions: ['专业职位 Top30', '按职位记录数排序，观察岗位出现频率。', '职位数'],
    purity: ['专业纯洁度 Top30', '纯洁度越高，越常以单一专业独占岗位。', '纯洁度'],
    growth: ['专业增长 Top30', '按近年增长率排序，观察扩招赛道。', '增长率']
  };
  document.getElementById('rankChartHead').innerHTML = renderVizHead(rankHeadMap[mode][0], rankHeadMap[mode][1], rankHeadMap[mode][2]);
  var sorted = getRankData(mode);
  var top30 = sorted.slice(0, 30);
  var names = top30.map(function(m) {
    var label = m.major;
    if (m.type === 'township') label = label.replace('（旧版乡镇招考代码）', '（旧版'+(m.code||'')+'）');
    else if (m.code) label += ' ('+m.code+')';
    return label;
  });
  var vals = top30.map(function(m) {
    if (mode === 'recruits') return m.total_recruits;
    if (mode === 'positions') return m.total_positions;
    if (mode === 'purity') return formatPercent(m.purity);
    if (mode === 'growth') return Math.round((m.growth_rate||0)*10)/10;
    return 0;
  });
  var suffix = mode === 'purity' ? '%' : (mode === 'growth' ? '%' : '');

  rankChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
    grid: { left: 180, right: 50, top: 15, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: names.reverse(), axisLabel: {fontSize:10, interval:0} },
    series: [{ type: 'bar', data: vals.reverse(), barMaxWidth: 18, label: { show: true, position: 'right', fontSize: 10, formatter: function(p) { return p.value + suffix; } }, itemStyle: { color: function(p) { var i = p.dataIndex; var t = i / 29; return 'hsl(' + Math.round(30 + t * 200) + ', 65%, ' + Math.round(58 - t * 20) + '%)'; } } }]
  }, true);

  // 表格
  var maxRecruits = top30.length > 0 ? top30[0].total_recruits : 1;
  var th = '<table class="data-table"><thead><tr><th>#</th><th>专业</th><th>招录人数</th><th>职位数</th><th>纯洁度</th><th>竞争指数</th><th>增长率</th><th>应届占比</th><th>学历</th></tr></thead><tbody>';
  top30.forEach(function(m, i) {
    var eduStr = m.education_distribution ? Object.entries(m.education_distribution).sort(function(a,b){return b[1]-a[1]}).map(function(e){return e[0]}).slice(0,2).join('、') : '-';
    th += '<tr>' +
      '<td>' + rankPill(i) + '</td>' +
      '<td style="text-align:left;font-weight:600;">' + names[29-i] + '</td>' +
      '<td>' + m.total_recruits + '<div style="margin-top:2px;">' + miniBar(m.total_recruits, maxRecruits) + '</div></td>' +
      '<td>' + m.total_positions + '</td>' +
      '<td>' + formatPercent(m.purity) + '%</td>' +
      '<td>' + (m.competition_index||'-') + '</td>' +
      '<td>' + trendText(m.growth_rate) + '</td>' +
      '<td>' + formatPercent(m.fresh_ratio) + '%</td>' +
      '<td style="font-size:11px;">' + eduStr + '</td>' +
      '</tr>';
  });
  th += '</tbody></table>';
  document.getElementById('rankTableWrap').innerHTML = th;
  document.getElementById('rankCount').textContent = '共 ' + RANKING.length + ' 个专业';
}

function renderLowRank() {
  var sorted = RANKING.slice().sort(function(a,b) { return a.total_recruits - b.total_recruits; });
  var low30 = sorted.slice(0, 30);
  var names = low30.map(function(m) { return m.major + (m.code ? ' ('+m.code+')' : ''); }).reverse();
  var vals = low30.map(function(m) { return m.total_recruits; }).reverse();
  lowRankChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
    grid: { left: 180, right: 30, top: 10, bottom: 30 },
    xAxis: { type: 'value' }, yAxis: { type: 'category', data: names, axisLabel: {fontSize:10, interval:0} },
    series: [{ type: 'bar', data: vals, barMaxWidth: 18, label: { show: true, position: 'right', fontSize: 10 }, itemStyle: {color: function(p) { var i = p.dataIndex; var t = i / 29; return 'hsl(' + Math.round(210 + t * 40) + ', 45%, ' + Math.round(55 - t * 12) + '%)'; } } }]
  }, true);
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
  document.getElementById('rankCount').textContent = '显示 ' + count + ' / ' + RANKING.length + ' 个专业';
}

// ====== 专业分析：详情 ======
var detailTrendChart = null, detailDistChart = null, detailEduChart = null;
function initDetail() {
  detailTrendChart = echarts.init(document.getElementById('detailTrendChart'));
  detailDistChart = echarts.init(document.getElementById('detailDistChart'));
  detailEduChart = echarts.init(document.getElementById('detailEduChart'));
  switchDetail();
}
initDetail();

function switchDetail() {
  var idx = parseInt(document.getElementById('detailSelect').value);
  if (isNaN(idx)) idx = 0;
  var major = RANKING[idx];
  if (!major) return;
  var yearly = major.yearly || {};
  var cities = major.city_top || {};
  var edu = major.education_distribution || {};

  document.getElementById('detailMetrics').innerHTML =
    '<div class="metric"><div class="metric-val">' + major.total_recruits + '</div><div class="metric-label">总招录人数</div></div>' +
    '<div class="metric"><div class="metric-val">' + major.total_positions + '</div><div class="metric-label">职位数</div></div>' +
    '<div class="metric"><div class="metric-val">' + formatPercent(major.purity) + '%</div><div class="metric-label">纯洁度</div></div>' +
    '<div class="metric"><div class="metric-val ' + ((major.growth_rate||0)>0?'up':'down') + '">' + Math.round((major.growth_rate||0)*100)/100 + '%</div><div class="metric-label">增长率</div></div>';

  detailTrendChart.setOption({
    tooltip: { trigger: 'axis' }, grid: { left: 40, right: 10, top: 15, bottom: 20 },
    xAxis: { type: 'category', data: YEARS },
    yAxis: { type: 'value', name: '招录人数' },
    series: [{ type: 'line', smooth: true, data: YEARS.map(function(y) { return getYearRecruits(yearly, y); }), areaStyle: {color:'#e8edf5'}, lineStyle: {color:'#1a3c6e',width:2}, symbol: 'circle', symbolSize: 6 }]
  }, true);

  var cityArr = Object.entries(cities).sort(function(a,b) { return b[1]-a[1]; }).slice(0, 10);
  detailDistChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} }, grid: { left: 60, right: 10, top: 10, bottom: 20 },
    xAxis: { type: 'value' }, yAxis: { type: 'category', data: cityArr.map(function(c) { return c[0]; }).reverse(), axisLabel: {fontSize:10} },
    series: [{ type: 'bar', data: cityArr.map(function(c) { return c[1]; }).reverse(), barMaxWidth: 18, itemStyle: {color: function(p) { return ['#1a3c6e','#2a5c9e','#3a7cce','#5a9cee','#8abcf5','#b0d4f8'][p.dataIndex % 6]; }}, label: { show: true, position: 'right', fontSize: 10 } }]
  }, true);

  var eduArr = Object.entries(edu).filter(function(e) { return e[1] > 0; });
  detailEduChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['30%', '60%'], label: { formatter: '{b}: {d}%' }, data: eduArr.map(function(e) { return {name: e[0], value: e[1]}; }) }]
  }, true);

  // 关联专业表格
  var co = major.top_co_occurrences || [];
  if (co.length > 0) {
    var th = '<table><thead><tr><th>关联专业</th><th>共同招录人数</th><th>关联率</th></tr></thead><tbody>';
    co.slice(0, 15).forEach(function(c) {
      th += '<tr><td style="text-align:left;">' + (c.major||c.majors) + '</td><td>' + (c.recruits||c.count) + '</td><td>' + Math.round((c.recruits||c.count)/major.total_recruits*1000)/10 + '%</td></tr>';
    });
    th += '</tbody></table>';
    document.getElementById('detailCoTable').innerHTML = '<h4 style="color:var(--blue-800);margin:8px 0;">🔗 关联专业 Top15</h4>' + th;
  } else {
    document.getElementById('detailCoTable').innerHTML = '<div style="padding:14px;color:var(--ink-400);text-align:center;">该专业暂无直接关联专业</div>';
  }
}

// ====== 专业分析：趋势 ======
var trendCharts = {};
function initTrends() {
  ['trendChart1','trendChart2','trendChart3'].forEach(function(id) { trendCharts[id] = echarts.init(document.getElementById(id)); });
  switchTrend();
}
initTrends();

function switchTrend() {
  [0,1,2].forEach(function(i) {
    var sel = document.getElementById('trendSelect' + (i+1));
    var idx = parseInt(sel ? sel.value : 0);
    var major = RANKING[idx];
    if (!major) return;
    var yearly = major.yearly || {};
    var id = 'trendChart' + (i+1);
    var isFresh = (i === 2);
    var cht = trendCharts[id];
    if (!cht) return;

    if (i === 2) {
      // 应届比例对比: 显示多个专业的应届率
      var majors3 = [RANKING[idx], RANKING[Math.min(idx+1, RANKING.length-1)], RANKING[Math.min(idx+2, RANKING.length-1)]];
      var series3 = majors3.map(function(m, mi) {
        var my = m.yearly || {};
        return { name: m.major, type: 'line', smooth: true, data: YEARS.map(function(y) { return getYearFreshRatio(my, y); }), lineStyle: {width:2} };
      });
      cht.setOption({
        tooltip: { trigger: 'axis', formatter: function(ps) { var h = '<b>'+ps[0].axisValue+'</b>'; ps.forEach(function(p) { h += '<br/>'+p.seriesName+': '+p.value+'%'; }); return h; } },
        legend: { data: majors3.map(function(m) { return m.major; }), bottom: 0, type: 'scroll', pageIconSize: 8 },
        grid: { left: 50, right: 20, top: 10, bottom: 40 },
        xAxis: { type: 'category', data: YEARS }, yAxis: { type: 'value', name: '应届占比 %' },
        series: series3, color: ['#1a3c6e','#e74c3c','#27ae60']
      }, true);
    } else {
      cht.setOption({
        tooltip: { trigger: 'axis' }, grid: { left: 40, right: 10, top: 10, bottom: 20 },
        xAxis: { type: 'category', data: YEARS },
        yAxis: { type: 'value', name: i === 0 ? '招录人数' : '应届占比 %' },
        series: [{ type: 'line', smooth: true, data: i === 0 ? YEARS.map(function(y) { return getYearRecruits(yearly, y); }) : YEARS.map(function(y) { return getYearFreshRatio(yearly, y); }), areaStyle: {color:'#e8edf5'}, lineStyle: {color:'#1a3c6e',width:2}, symbol: 'circle', symbolSize: 5 }]
      }, true);
    }
  });
}

// ====== 专业分析：对比 ======
var compareChart = null;
function initCompare() {
  compareChart = echarts.init(document.getElementById('compareChart'));
  updateCompare();
}
initCompare();

function updateCompare() {
  var checked = document.querySelectorAll('#compareGrid input:checked');
  var indices = Array.from(checked).map(function(cb) { return parseInt(cb.value); });
  var selected = indices.map(function(i) { return RANKING[i]; }).filter(function(m) { return m; });
  var countEl = document.getElementById('compareSelectedCount');
  if (countEl) countEl.textContent = '已选 ' + selected.length;
  if (!selected.length) {
    compareChart.clear();
    compareChart.setOption({
      title: {
        text: '请选择要对比的专业',
        subtext: '勾选上方专业后显示招录趋势曲线',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#1a3c6e', fontSize: 16 },
        subtextStyle: { color: '#94a3b8', fontSize: 12 }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    }, true);
    updateScorePanel([]);
    return;
  }
  var series = selected.map(function(m) {
    var my = m.yearly || {};
    return { name: m.major, type: 'line', smooth: true, data: YEARS.map(function(y) { return getYearRecruits(my, y); }), lineStyle: {width:2}, symbol: 'circle', symbolSize: 5 };
  });
  compareChart.setOption({
    color: ['#1e3a5f', '#3b82f6', '#10b981', '#d97706', '#8b5cf6', '#ef4444', '#0f766e', '#7c3aed'],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: 'rgba(148,163,184,0.24)',
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: '#1e293b', fontSize: 12 },
      extraCssText: 'box-shadow:0 14px 30px rgba(15,23,42,.12);border-radius:12px;'
    },
    legend: {
      data: selected.map(function(m) { return m.major; }),
      bottom: 4,
      type: 'scroll',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#475569', fontSize: 12 },
      pageIconSize: 8
    },
    grid: { left: 54, right: 24, top: 36, bottom: 46 },
    xAxis: {
      type: 'category',
      data: YEARS,
      axisLine: { lineStyle: { color: 'rgba(148,163,184,0.45)' } },
      axisTick: { lineStyle: { color: 'rgba(148,163,184,0.35)' } },
      axisLabel: { color: '#64748b', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '',
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.22)' } },
      axisLabel: { color: '#64748b', fontSize: 12 }
    },
    series: series
  }, true);
  updateScorePanel(selected);
  setTimeout(resizeAll, 50);
}

function updateScorePanel(selected) {
  var panel = document.getElementById('compareScorePanel');
  if (!panel) return;
  selected = selected || [];
  if (!selected.length) {
    panel.innerHTML = '<div class="score-empty"><h3>请选择专业</h3><p>勾选上方专业后，这里会生成更适合横向判断的指标对比矩阵。</p></div>';
    return;
  }
  var colors = ['#1e3a5f', '#3b82f6', '#10b981', '#d97706', '#8b5cf6', '#ef4444', '#0f766e', '#7c3aed'];
  var maxRecruit = Math.max.apply(null, selected.map(function(m) { return m.total_recruits || 0; })) || 1;
  var maxGrowth = Math.max(40, Math.max.apply(null, selected.map(function(m) { return Math.max(0, m.growth_rate || 0); })) || 0);
  function percentValue(v) { return formatPercent(v); }
  function growthText(v) { return (v > 0 ? '+' : '') + formatPercent(v) + '%'; }
  function widthFor(value, max) {
    if (!max || value <= 0) return 4;
    return Math.max(6, Math.min(100, Math.round(value / max * 100)));
  }
  var metrics = [
    { label:'招录规模', desc:'累计招录人数', max:maxRecruit, value:function(m){ return m.total_recruits || 0; }, widthValue:function(m){ return m.total_recruits || 0; }, format:function(v){ return formatNumber(v) + '人'; } },
    { label:'纯洁度', desc:'专业独占岗位比例', max:100, value:function(m){ return percentValue(m.purity); }, widthValue:function(m){ return percentValue(m.purity); }, format:function(v){ return formatPercent(v) + '%'; } },
    { label:'增长率', desc:'近年扩张强度', max:maxGrowth, value:function(m){ return m.growth_rate || 0; }, widthValue:function(m){ return Math.max(0, m.growth_rate || 0); }, format:growthText },
    { label:'应届占比', desc:'应届友好程度', max:100, value:function(m){ return percentValue(m.fresh_ratio); }, widthValue:function(m){ return percentValue(m.fresh_ratio); }, format:function(v){ return formatPercent(v) + '%'; } }
  ];
  var cards = selected.map(function(m, i) {
    var color = colors[i % colors.length];
    return '<div class="score-major-card" style="--score-color:' + color + '">' +
      '<div class="score-major-name" title="' + escHtml(m.major) + '">' + escHtml(m.major) + '</div>' +
      '<div class="score-major-meta"><span><b>' + formatNumber(m.total_recruits || 0) + '</b>招录</span><span><b>' + growthText(m.growth_rate || 0) + '</b>增长</span><span><b>' + formatPercent(m.fresh_ratio) + '%</b>应届</span><span><b>' + formatPercent(m.purity) + '%</b>纯度</span></div>' +
    '</div>';
  }).join('');
  var matrix = metrics.map(function(metric) {
    var best = selected.slice().sort(function(a, b) { return metric.value(b) - metric.value(a); })[0];
    var rows = selected.map(function(m, i) {
      var color = colors[i % colors.length];
      var value = metric.value(m);
      var w = widthFor(metric.widthValue(m), metric.max);
      return '<div class="score-bar-row" style="--score-color:' + color + '">' +
        '<span class="score-name" title="' + escHtml(m.major) + '">' + escHtml(m.major) + '</span>' +
        '<span class="score-track"><i style="width:' + w + '%"></i></span>' +
        '<strong class="score-value">' + metric.format(value) + '</strong>' +
      '</div>';
    }).join('');
    return '<div class="score-metric-block">' +
      '<div class="score-metric-head"><div><b>' + metric.label + '</b><span>' + metric.desc + '</span></div><em class="score-best-chip" title="' + escHtml(best.major) + '">领先：' + escHtml(best.major) + '</em></div>' +
      '<div class="score-bars">' + rows + '</div>' +
    '</div>';
  }).join('');
  panel.innerHTML = '<div class="score-panel-head"><div><div class="score-panel-kicker">COMPARISON</div><div class="score-panel-title">专业竞争力侧写</div></div><p class="score-panel-note">多维度指标对比矩阵，可直观判断各专业的相对优势和特征差异。</p></div><div class="score-personas">' + cards + '</div><div class="score-matrix">' + matrix + '</div>';
}

// ====== 专业分析：关联网络 ======
var networkChart = null;
var currentNetworkMajor = null;
function getMajorByName(name) {
  return RANKING.find(function(m) { return m.major === name; }) || null;
}
function getNetworkLinks(centerName) {
  var links = [];
  var seen = new Set();
  CO_PAIRS.forEach(function(p) {
    var majors = p.majors || p.major;
    if (!Array.isArray(majors) || majors.length < 2) return;
    var a = majors[0], b = majors[1];
    if (a !== centerName && b !== centerName) return;
    var other = a === centerName ? b : a;
    var key = [centerName, other].sort().join('|||');
    if (seen.has(key)) return;
    seen.add(key);
    links.push({ source: centerName, target: other, value: p.recruits || p.count || 0 });
  });
  return links.sort(function(a, b) { return b.value - a.value; }).slice(0, 18);
}
function setNetworkSelect(centerName) {
  var sel = document.getElementById('networkSelect');
  if (!sel) return;
  if (!centerName || centerName === 'global') { sel.value = 'global'; return; }
  var idx = RANKING.findIndex(function(m) { return m.major === centerName; });
  if (idx >= 0) sel.value = String(idx);
}
function buildGlobalNetwork() {
  var nodeMap = {};
  var topMajors = RANKING.slice(0, 20).map(function(m) { return m.major; });
  var topSet = new Set(topMajors);
  topMajors.forEach(function(name) {
    var info = getMajorByName(name) || { total_recruits: 0 };
    nodeMap[name] = {
      name: name,
      value: info.total_recruits || 0,
      symbolSize: Math.max(18, Math.min(62, (info.total_recruits || 0) / 180)),
      itemStyle: { color: '#1a3c6e' }
    };
  });
  var edges = [];
  var seen = new Set();
  CO_PAIRS.forEach(function(p) {
    var majors = p.majors || p.major;
    if (!Array.isArray(majors) || majors.length < 2) return;
    var a = majors[0], b = majors[1];
    if (!topSet.has(a) && !topSet.has(b)) return;
    var key = [a, b].sort().join('|||');
    if (seen.has(key)) return;
    seen.add(key);
    if (!nodeMap[a]) nodeMap[a] = { name: a, value: p.recruits || p.count || 0, symbolSize: 14, itemStyle: { color: '#8abcf5' } };
    if (!nodeMap[b]) nodeMap[b] = { name: b, value: p.recruits || p.count || 0, symbolSize: 14, itemStyle: { color: '#8abcf5' } };
    edges.push({ source: a, target: b, value: p.recruits || p.count || 0 });
  });
  edges = edges.sort(function(a, b) { return b.value - a.value; }).slice(0, 90);
  return { nodes: Object.values(nodeMap), edges: edges };
}
function renderNetwork(nodes, edges, title, subtext, centerName) {
  networkChart.setOption({
    title: {
      text: title,
      subtext: subtext,
      left: 16,
      top: 12,
      textStyle: { color: '#1a3c6e', fontSize: 15 },
      subtextStyle: { color: '#888', fontSize: 12 }
    },
    tooltip: {
      formatter: function(p) {
        if (p.dataType === 'edge') return p.data.source + ' ↔ ' + p.data.target + '<br/>共同招录: ' + p.data.value + ' 人';
        var m = getMajorByName(p.name);
        if (centerName && p.name !== centerName) return '<strong>' + p.name + '</strong><br/>与 ' + centerName + ' 共同招录: ' + p.value + ' 人';
        return '<strong>' + p.name + '</strong><br/>总招录: ' + (m ? m.total_recruits : p.value || 0) + ' 人';
      }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      top: 70,
      roam: true,
      draggable: true,
      force: { repulsion: centerName ? 520 : 360, gravity: 0.08, edgeLength: centerName ? [90, 180] : [60, 160] },
      data: nodes,
      edges: edges.map(function(link) {
        return {
          source: link.source,
          target: link.target,
          value: link.value,
          lineStyle: { width: Math.max(1, Math.min(7, link.value / 500)), curveness: 0.16, opacity: 0.68, color: '#9aa9bf' },
          label: { show: centerName && link.value >= 1000, formatter: link.value + '人', color: '#666', fontSize: 10 }
        };
      }),
      edgeLabel: { show: false },
      label: { show: true, fontSize: 10, color: '#222' },
      emphasis: { focus: 'adjacency', label: { fontSize: 13, fontWeight: 600 } }
    }]
  }, true);
}
function initNetwork(centerName) {
  var el = document.getElementById('networkChart');
  if (!el) return;
  networkChart = echarts.getInstanceByDom(el) || echarts.init(el);
  if (!centerName) centerName = currentNetworkMajor || 'global';
  if (centerName === 'global') {
    currentNetworkMajor = null;
    setNetworkSelect('global');
    var global = buildGlobalNetwork();
    renderNetwork(global.nodes, global.edges, '全局关联网络', '显示 Top20 专业及其高频共现关系；点击节点可聚焦该专业', null);
  } else {
    currentNetworkMajor = centerName;
    setNetworkSelect(centerName);
    var center = getMajorByName(centerName) || { major: centerName, total_recruits: 0 };
    var links = getNetworkLinks(centerName);
    var nodes = [{
      name: centerName,
      value: center.total_recruits || 0,
      symbolSize: Math.max(38, Math.min(76, (center.total_recruits || 0) / 120)),
      itemStyle: { color: '#1a3c6e' },
      label: { fontSize: 13, fontWeight: 600 }
    }];
    links.forEach(function(link, i) {
      nodes.push({
        name: link.target,
        value: link.value,
        symbolSize: Math.max(20, Math.min(52, link.value / 70)),
        itemStyle: { color: COLORS[(i + 2) % COLORS.length] }
      });
    });
    renderNetwork(nodes, links, centerName + ' 关联网络', links.length ? '仅显示直接关联专业；点击任一节点切换中心专业' : '暂无关联专业', centerName);
  }
  networkChart.off('click');
  networkChart.on('click', function(params) {
    if (params.dataType === 'node' && params.name) initNetwork(params.name);
  });
}
initNetwork('global');


// =================== 地域分析 ===================

// ====== 地域：地图 ======
var mapChart = null;
function initMap() {
  if (!GD_GEOJSON || !GD_GEOJSON.features) {
    document.getElementById('mapChart').innerHTML = '<div style="text-align:center;padding:80px 20px;color:var(--ink-400);">⚠️ 地图数据加载失败，请刷新</div>';
    return;
  }
  mapChart = echarts.init(document.getElementById('mapChart'));
  echarts.registerMap('guangdong', GD_GEOJSON);
  switchMapMode();
}
initMap();

function getMapData(mode) {
  var mapData = [];
  if (!GD_GEOJSON || !GD_GEOJSON.features) return mapData;
  GD_GEOJSON.features.forEach(function(feat) {
    var geoName = feat.properties.name;
    var cityName = null;
    for (var cn in CITY_NAME_MAP) { if (CITY_NAME_MAP[cn] === geoName) { cityName = cn; break; } }
    if (!cityName) cityName = geoName.replace('市', '');
    var info = CITY_YEARLY[cityName];
    var val = 0;
    if (info) {
      if (mode === 'total') val = info.total_recruits;
      else if (mode === 'density') val = info.total_recruits / Math.max(info.total_positions, 1);
      else if (mode === 'growth') { var iy = info.yearly || {}; var early = (((iy['2020']||0)+(iy['2021']||0)+(iy['2022']||0))/3); var late = (((iy['2023']||0)+(iy['2024']||0)+(iy['2025']||0)+(iy['2026']||0))/4); val = early > 0 ? Math.round((late-early)/early*1000)/10 : 0; }
    }
    mapData.push({name: geoName, value: val, cityName: cityName, info: info});
  });
  return mapData;
}

function calcCityGrowth(city) {
  // 逐层判空：缺少该城市或缺少 yearly 时返回 0，避免抛 TypeError 把整个 Tab 打断
  var entry = CITY_YEARLY[city];
  var cy = (entry && entry.yearly) || {};
  var early = ((cy['2020']||0)+(cy['2021']||0)+(cy['2022']||0))/3;
  var late = ((cy['2023']||0)+(cy['2024']||0)+(cy['2025']||0)+(cy['2026']||0))/4;
  return early > 0 ? Math.round((late-early)/early*1000)/10 : (late > 0 ? 100 : 0);
}

function calcCityFreshRatio(city) {
  var f = CITY_FRESH[city] || {};
  var fresh = (f.fresh_any||0) + (f.fresh_current||0);
  var total = fresh + (f.social||0);
  return total > 0 ? Math.round(fresh/total*1000)/10 : 0;
}

function getCityGroup(city) {
  if (city === '省直') return 'province';
  return PRD_CITIES.indexOf(city) >= 0 ? 'prd' : 'non-prd';
}

function switchMapMode() {
  if (!mapChart) return;
  var mode = document.getElementById('mapMode').value;
  var group = document.getElementById('mapGroup').value;
  var mapData = getMapData(mode);
  var values = mapData.filter(function(d) { return d.value > 0; }).map(function(d) { return d.value; });
  values.sort(function(a,b) { return a-b; });
  var visualMax = values.length > 0 ? values[Math.floor(values.length * 0.95)] : 1;

  var isGroupMode = group === 'prd';
  var groupColors = { prd: '#4a9e5c', 'non-prd': '#c97878', province: '#3a7cce' };
  var groupLabels = { prd: '珠三角', 'non-prd': '非珠三角', province: '省直' };
  var option = {
    tooltip: { trigger: 'item', formatter: function(params) {
      var d = params.data;
      if (!d || !d.info) return params.name;
      var g = getCityGroup(d.cityName);
      var groupText = isGroupMode ? '<br/>区域: '+groupLabels[g] : '';
      return '<strong>'+d.cityName+'</strong>'+groupText+'<br/>总招录: '+d.info.total_recruits+' 人<br/>职位数: '+d.info.total_positions+'<br/>增长率: '+calcCityGrowth(d.cityName)+'%<br/>应届占比: '+calcCityFreshRatio(d.cityName)+'%';
    }},
    visualMap: isGroupMode ? undefined : { min: 0, max: visualMax, text:['高','低'], left:'left', bottom:20, inRange: {color:['#e8edf5','#8abcf5','#1a3c6e']}, calculable: true },
    series: [{
      type: 'map', map: 'guangdong', roam: true, label: { show: true, fontSize: 10 },
      data: mapData, itemStyle: { borderColor: '#fff', borderWidth: 1 },
      emphasis: { label: { fontSize: 13, fontWeight:'bold' }, itemStyle: { areaColor: '#2a5c9e' } }
    }]
  };
  if (isGroupMode) {
    option.series[0].data = mapData.map(function(d) {
      var g = d.cityName ? getCityGroup(d.cityName) : 'non-prd';
      return Object.assign({}, d, {
        value: g === 'prd' ? 1 : (g === 'province' ? 3 : 2),
        itemStyle: {areaColor: groupColors[g], opacity: 0.82, borderColor:'#fff', borderWidth:1}
      });
    });
    delete option.visualMap;
  }
  mapChart.setOption(option, true);
  mapChart.off('click');
  mapChart.on('click', function(params) {
    var d = params.data;
    if (d && d.cityName && d.info) showCityDetail(d.cityName);
  });
}
function switchMapGroup() { switchMapMode(); }

function showCityDetail(city) {
  var info = CITY_YEARLY[city];
  if (!info) return;
  var edu = CITY_EDUCATION[city] || {};
  var fresh = CITY_FRESH[city] || {};
  var totalFresh = (fresh.fresh_any||0)+(fresh.fresh_current||0);
  var totalF = totalFresh+(fresh.social||0);
  var growth = calcCityGrowth(city);
  var freshR = calcCityFreshRatio(city);
  var majorsInCity = CITY_MAJOR_MATRIX[city] || {};
  var topMajors = Object.entries(majorsInCity).sort(function(a,b) { return b[1]-a[1]; }).slice(0,5);
  var g = getCityGroup(city);
  var html = '<h3>🏙️ '+city+' <span style="font-size:12px;font-weight:400;color:var(--ink-400);">'+(g==='prd'?'(珠三角)':(g==='province'?'(省级)':'(非珠)'))+'</span></h3>';
  html += '<div class="detail-metrics">';
  html += '<div class="dm-item"><div class="dm-val">'+info.total_recruits+'</div><div class="dm-label">总招录</div></div>';
  html += '<div class="dm-item"><div class="dm-val">'+info.total_positions+'</div><div class="dm-label">职位数</div></div>';
  html += '<div class="dm-item"><div class="dm-val '+(growth>0?'up':'down')+'">'+growth+'%</div><div class="dm-label">增长率</div></div>';
  html += '<div class="dm-item"><div class="dm-val">'+freshR+'%</div><div class="dm-label">应届占比</div></div></div>';
  html += '<div style="height:90px;" id="miniTrend'+city.replace(/\s/g,'')+'"></div>';
  html += '<div style="margin:6px 0;"><strong style="font-size:12px;">热门专业 Top5：</strong> ';
  topMajors.forEach(function(item) {
    html += '<span style="background:#e8edf5;padding:2px 8px;border-radius:10px;font-size:11px;margin:1px;">'+item[0]+': '+item[1]+'</span>';
  });
  html += '</div>';
  document.getElementById('cityDetailContent').innerHTML = html;
  document.getElementById('cityDetailCard').classList.add('show');
  document.getElementById('helpOverlay').classList.add('show');
  setTimeout(function() {
    var el = document.getElementById('miniTrend'+city.replace(/\s/g,''));
    if (!el) return;
    var mini = echarts.getInstanceByDom(el) || echarts.init(el);
    var iy = info.yearly || {};
    mini.setOption({ grid:{left:'3%',right:'3%',top:10,bottom:10}, xAxis:{type:'category',data:YEARS,axisLabel:{fontSize:8}}, yAxis:{type:'value',splitLine:{lineStyle:{type:'dashed',opacity:0.3}}}, series:[{type:'line',data:YEARS.map(function(y){return iy[y]||0;}),smooth:true,lineStyle:{color:'#1a3c6e'},areaStyle:{color:'#e8edf5'}}], tooltip:{trigger:'axis'} });
  }, 50);
}
function hideCityDetail() {
  document.getElementById('cityDetailCard').classList.remove('show');
  document.getElementById('helpOverlay').classList.remove('show');
}

// ====== 地域：城市排名 ======
var cityRankChart = null;
function initCityRank() {
  cityRankChart = echarts.init(document.getElementById('cityRankChart'));
  switchCityRankMode();
}
initCityRank();

function switchCityRankMode() {
  var mode = document.getElementById('cityRankMode').value;
  var cityHeadMap = {
    recruits: ['城市招录 Top22', '按 2020-2026 年累计招录人数排序，观察岗位池规模。', '招录人数'],
    positions: ['城市职位 Top22', '按职位记录数排序，观察岗位出现频率。', '职位数'],
    growth: ['城市增长 Top22', '按近年增长率排序，观察扩招城市。', '增长率'],
    fresh: ['城市应届 Top22', '按应届占比排序，观察对应届生友好的城市。', '应届占比']
  };
  document.getElementById('cityRankChartHead').innerHTML = renderVizHead(cityHeadMap[mode][0], cityHeadMap[mode][1], cityHeadMap[mode][2]);
  var sorted = CITY_RANKING.slice();
  if (mode === 'recruits') sorted.sort(function(a,b) { return (CITY_YEARLY[b].total_recruits||0) - (CITY_YEARLY[a].total_recruits||0); });
  else if (mode === 'positions') sorted.sort(function(a,b) { return (CITY_YEARLY[b].total_positions||0) - (CITY_YEARLY[a].total_positions||0); });
  else if (mode === 'growth') sorted.sort(function(a,b) { return calcCityGrowth(b) - calcCityGrowth(a); });
  else if (mode === 'fresh') sorted.sort(function(a,b) { return calcCityFreshRatio(b) - calcCityFreshRatio(a); });
  var names = sorted.map(function(c) { var g=getCityGroup(c); return c+(g==='prd'?' ★':''); });
  var values = sorted.map(function(c) { if(mode==='recruits') return CITY_YEARLY[c].total_recruits; if(mode==='positions') return CITY_YEARLY[c].total_positions; if(mode==='growth') return calcCityGrowth(c); if(mode==='fresh') return calcCityFreshRatio(c); return 0; });
  cityRankChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} },
    grid: { left: 80, right: 50, top: 15, bottom: 30 },
    xAxis: { type: 'value' }, yAxis: { type: 'category', data: names.reverse(), axisLabel: {fontSize:11} },
    series: [{ type: 'bar', data: values.reverse().map(function(v,i) { var city = sorted[sorted.length-1-i]; var g=getCityGroup(city); return {value:v, itemStyle:{color: function(p) { var i = p.dataIndex; var t = i / Math.max(1, sorted.length-1); return 'hsl(' + Math.round(40 + t * 190) + ', 60%, ' + Math.round(52 - t * 12) + '%)'; } }}; }), barMaxWidth: 22, label: { show:true, position:'right', fontSize:10, formatter: function(p){return p.value +((mode==='growth'||mode==='fresh')?'%':'');} } }]
  }, true);
  var maxRecruits = sorted.length > 0 ? (CITY_YEARLY[sorted[0]].total_recruits||0) : 1;
  var th = '<table class="data-table"><thead><tr><th>#</th><th>城市</th><th>分区</th><th>招录人数</th><th>职位数</th><th>增长率</th><th>应届占比</th><th>占全省比</th></tr></thead><tbody>';
  sorted.forEach(function(c,i) {
    var info = CITY_YEARLY[c]; var g=getCityGroup(c);
    th += '<tr>' +
      '<td>' + rankPill(i) + '</td>' +
      '<td style="text-align:left;font-weight:600;">' + c + '</td>' +
      '<td>' + (g==='prd'?'<span class="city-badge">珠三角</span>':(g==='province'?'<span class="city-badge">省直</span>':'<span class="city-badge">非珠</span>')) + '</td>' +
      '<td>' + info.total_recruits + '<div style="margin-top:2px;">' + miniBar(info.total_recruits, maxRecruits) + '</div></td>' +
      '<td>' + info.total_positions + '</td>' +
      '<td>' + trendText(calcCityGrowth(c)) + '</td>' +
      '<td>' + calcCityFreshRatio(c) + '%</td>' +
      '<td>' + info.pct_of_total + '%</td>' +
      '</tr>';
  });
  th += '</tbody></table>';
  document.getElementById('cityRankTableWrap').innerHTML = th;
  document.getElementById('cityRankCount').textContent = '共 '+sorted.length+' 个城市';
}

function filterCityRankTable() {
  var q = document.getElementById('cityRankSearch').value;
  var rows = document.querySelectorAll('#cityRankTableWrap table tbody tr');
  var count = 0;
  rows.forEach(function(r) { var match = r.cells[1].textContent.indexOf(q) >= 0; r.style.display = match?'': 'none'; if(match) count++; });
  document.getElementById('cityRankCount').textContent = '显示 '+count+' / '+CITY_RANKING.length+' 个城市';
}

// ====== 地域：年度趋势 ======
var cityTrendChart = null;
function initCityTrend() {
  var sel = document.getElementById('trendCitySelect');
  CITY_RANKING.forEach(function(c) { var opt = document.createElement('option'); opt.value=c; opt.textContent=c; sel.appendChild(opt); });
  cityTrendChart = echarts.init(document.getElementById('cityTrendChart'));
  selectDefaultCities();
}
initCityTrend();

function selectDefaultCities() {
  var sel = document.getElementById('trendCitySelect');
  var defaults = ['广州','深圳','省直','佛山','东莞','惠州'].filter(function(c) { return CITY_YEARLY[c]; });
  Array.from(sel.options).forEach(function(opt) { opt.selected = defaults.indexOf(opt.value) >= 0; });
  updateCityTrend();
}
function selectAllCities() {
  var sel = document.getElementById('trendCitySelect');
  Array.from(sel.options).forEach(function(opt) { opt.selected = true; });
  updateCityTrend();
}
function updateCityTrend() {
  var sel = document.getElementById('trendCitySelect');
  var picked = Array.from(sel.selectedOptions).map(function(o) { return o.value; });
  var selected = picked.slice(0, 8);
  if (selected.length === 0) selected = ['广州'];
  var series = [];
  selected.forEach(function(city) {
    var info = CITY_YEARLY[city]; if (!info) return;
    var iy = info.yearly || {};
    series.push({ name: city, type: 'line', smooth: true, data: YEARS.map(function(y) { return iy[y]||0; }), lineStyle: {width:2.5}, symbolSize: 5 });
  });
  // 多选上限 8 条曲线，但"全选"按钮会把 22 个城市都选上；这里显式说明被截断，
  // 避免图形只画 8 条而用户以为看到了全部。
  var head = document.getElementById('cityTrendChartHead');
  if (head) {
    head.innerHTML = picked.length > selected.length
      ? renderVizHead('城市年度趋势', '已选 ' + picked.length + ' 个城市，图形仅显示前 8 个', '2020-2026')
      : renderVizHead('城市年度趋势', '各城市历年招录人数变化', '2020-2026');
  }
  cityTrendChart.setOption({
    tooltip: { trigger: 'axis' }, legend: { bottom: 0, type: 'scroll', pageIconSize: 8 },
    grid: { left: 50, right: 20, top: 15, bottom: 40 },
    xAxis: { type: 'category', data: YEARS, axisLabel: {fontSize:11} }, yAxis: { type: 'value', name: '招录人数' },
    series: series, color: ['#1a3c6e','#e74c3c','#27ae60','#e67e22','#8e44ad','#2ecc71','#f39c12','#2980b9']
  }, true);
  var growthRanks = selected.map(function(c) { return {city:c, growth:calcCityGrowth(c)}; }).sort(function(a,b) { return b.growth - a.growth; });
  var th = '<table><thead><tr><th>城市</th><th>年均增长率</th>'+YEARS.map(function(y){return '<th>'+y+'</th>';}).join('')+'</tr></thead><tbody>';
  growthRanks.forEach(function(item) {
    var info = CITY_YEARLY[item.city];
    var iy = (info && info.yearly) || {};
    th += '<tr><td><strong>'+item.city+'</strong></td><td class="'+(item.growth>0?'up':'down')+'">'+item.growth+'%</td>'+YEARS.map(function(y){return '<td>'+(iy[y]||0)+'</td>';}).join('')+'</tr>';
  });
  th += '</tbody></table>';
  document.getElementById('cityTrendTableWrap').innerHTML = th;
}

// ====== 地域：应往届 × 学历 ======
// 复用已存在的 ECharts 实例：部分容器在详情面板里被反复重绘，
// 直接 echarts.init 会触发 "already initialized" 警告并可能残留旧状态。
function echartsFor(id) {
  var el = document.getElementById(id);
  if (!el) return null;
  return echarts.getInstanceByDom(el) || echarts.init(el);
}

// 学历分组助手：从 CITY_EDUCATION 实际出现的键动态取分组，
// 保证数据侧新增/调整分组时图表不会静默丢数据。
var EDU_LABEL_ORDER = ['研究生','本科以上','本科','大专以上','大专','大专或本科','其他'];
var EDU_COLOR_MAP = {
  '研究生':'#1a3c6e','本科以上':'#4a9e5c','本科':'#2f7d4f',
  '大专以上':'#8abcf5','大专':'#c97878','大专或本科':'#e67e22','其他':'#c9c9c9'
};
var EDU_COLOR_FALLBACK = ['#1a3c6e','#4a9e5c','#2f7d4f','#8abcf5','#c97878','#e67e22','#c9c9c9'];
function getEduLabels() {
  var seen = {};
  Object.keys(CITY_EDUCATION || {}).forEach(function(c) {
    Object.keys(CITY_EDUCATION[c] || {}).forEach(function(k) { seen[k] = true; });
  });
  var ordered = EDU_LABEL_ORDER.filter(function(k) { return seen[k]; });
  Object.keys(seen).forEach(function(k) { if (ordered.indexOf(k) < 0) ordered.push(k); });
  return ordered;
}
function getEduColors(labels) {
  var out = {};
  labels.forEach(function(l, i) { out[l] = EDU_COLOR_MAP[l] || EDU_COLOR_FALLBACK[i % EDU_COLOR_FALLBACK.length]; });
  return out;
}
var freshChart = null, eduChart = null;
function initFreshEdu() {
  freshChart = echarts.init(document.getElementById('freshChart'));
  eduChart = echarts.init(document.getElementById('eduChart'));
  var sel = document.getElementById('freshEduCity');
  CITY_RANKING.forEach(function(c) { var opt = document.createElement('option'); opt.value=c; opt.textContent=c; sel.appendChild(opt); });
  renderFreshEduOverview();
  updateFreshEduDetail();
}
initFreshEdu();

function renderFreshEduOverview() {
  var cities = CITY_RANKING.slice(0, 15);
  var fData = {social: [], fresh_any: [], fresh_current: []};
  cities.forEach(function(c) { var f = CITY_FRESH[c]||{}; fData.social.push(f.social||0); fData.fresh_any.push(f.fresh_any||0); fData.fresh_current.push(f.fresh_current||0); });
  freshChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} }, legend: { data: ['社会人员','往届应届','当年应届'], bottom: 0 },
    grid: { left: 40, right: 15, top: 10, bottom: 50 }, xAxis: { type:'category', data: cities, axisLabel: {rotate:25, fontSize:9} }, yAxis: { type:'value', name:'招录人数' },
    series: [
      { name:'社会人员', type:'bar', stack:'fresh', data:fData.social, itemStyle:{color:'#c97878'} },
      { name:'往届应届', type:'bar', stack:'fresh', data:fData.fresh_any, itemStyle:{color:'#8abcf5'} },
      { name:'当年应届', type:'bar', stack:'fresh', data:fData.fresh_current, itemStyle:{color:'#4a9e5c'} }
    ]
  }, true);
  // 学历分组从实际数据动态取得：分组体系变化（如新增「本科以上」）时图表自动跟随，
  // 不再因硬编码标签而丢弃占比最大的分组。
  var eduLabels = getEduLabels();
  var eduColors = getEduColors(eduLabels);
  var eData = {}; eduLabels.forEach(function(l) { eData[l] = []; });
  cities.forEach(function(c) { var e = CITY_EDUCATION[c]||{}; eduLabels.forEach(function(l) { eData[l].push(e[l]||0); }); });
  var shownEdu = eduLabels.filter(function(l){return eData[l].some(function(v){return v>0;});});
  eduChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} }, legend: { data: shownEdu, bottom: 0 },
    grid: { left: 40, right: 15, top: 10, bottom: 50 }, xAxis: { type:'category', data: cities, axisLabel: {rotate:25, fontSize:9} }, yAxis: { type:'value', name:'招录人数' },
    series: shownEdu.map(function(l) { return {name:l,type:'bar',stack:'edu',data:eData[l],itemStyle:{color:eduColors[l]}}; })
  }, true);
}

function updateFreshEduDetail() {
  var city = document.getElementById('freshEduCity').value;
  if (!city || !CITY_YEARLY[city]) return;
  var f = CITY_FRESH[city]||{};
  var mini1 = echartsFor('freshDetailChart');
  if (!mini1) return;
  mini1.setOption({ tooltip: {trigger:'item'}, series:[{type:'pie', radius:['30%','60%'], label:{formatter:'{b}: {d}%'}, data:[{value:f.social||0, name:'社会', itemStyle:{color:'#c97878'}}, {value:f.fresh_any||0, name:'往届应届', itemStyle:{color:'#8abcf5'}}, {value:f.fresh_current||0, name:'当年应届', itemStyle:{color:'#4a9e5c'}}].filter(function(d){return d.value>0;}) }] }, true);
  var e = CITY_EDUCATION[city]||{};
  var mini2 = echartsFor('eduDetailChart');
  if (!mini2) return;
  var eduLabels = getEduLabels().filter(function(l) { return (e[l]||0) > 0; });
  var pieColors = getEduColors(eduLabels);
  mini2.setOption({ tooltip: {trigger:'item'}, series:[{type:'pie', radius:['30%','60%'], label:{formatter:'{b}: {d}%'}, data:eduLabels.map(function(l){return {value:e[l]||0, name:l, itemStyle:{color:pieColors[l]}};}) }] }, true);
}

// ====== 地域：专业×地域 ======
// 城市×专业矩阵有 1500+ 个专业名，普通 <select> 无法查找，
// 因此改为「输入框 + 可筛选候选列表」；下拉候选最多渲染 MAX_MAJOR_OPTIONS 条。
var majorCityChart = null;
var majorCurrent = '';
var MAX_MAJOR_OPTIONS = 60;

function filterMajorOptions() {
  var input = document.getElementById('majorSearch');
  var panel = document.getElementById('majorOptions');
  if (!input || !panel) return;
  var q = (input.value || '').trim().toLowerCase();
  var hits = q ? ALL_MAJORS.filter(function(m) { return m.toLowerCase().indexOf(q) >= 0; }) : ALL_MAJORS;
  var shown = hits.slice(0, MAX_MAJOR_OPTIONS);
  var html = shown.map(function(m) {
    return '<div class="mcs-item" onclick="selectMajorOption(\'' + m.replace(/'/g, "\\'") + '\')">' + escHtml(m) + '</div>';
  }).join('');
  if (!hits.length) html = '<div class="mcs-empty">未找到匹配的专业</div>';
  else if (hits.length > shown.length) html += '<div class="mcs-more">共 ' + hits.length + ' 个匹配，继续输入以缩小范围</div>';
  panel.innerHTML = html;
  panel.style.display = '';
}

function selectMajorOption(name) {
  majorCurrent = name;
  var input = document.getElementById('majorSearch');
  if (input) input.value = name;
  var panel = document.getElementById('majorOptions');
  if (panel) panel.style.display = 'none';
  updateMajorCity();
}

function initMajorCityTab() {
  // 默认专业由生成器写入 #majorDefault（取矩阵中招录最多的专业，保证首屏有数据）
  var def = document.getElementById('majorDefault');
  majorCurrent = (def && def.value) || ALL_MAJORS[0] || '';
  var input = document.getElementById('majorSearch');
  if (input) input.value = majorCurrent;
  var citySel = document.getElementById('citySelect');
  CITY_RANKING.forEach(function(c) { var opt = document.createElement('option'); opt.value=c; opt.textContent=c; citySel.appendChild(opt); });
  majorCityChart = echarts.init(document.getElementById('majorCityChart'));
  updateMajorCity();
}
initMajorCityTab();

// 点击空白处收起候选列表
document.addEventListener('click', function(e) {
  var wrap = document.getElementById('majorSearchWrap');
  var panel = document.getElementById('majorOptions');
  if (wrap && panel && !wrap.contains(e.target)) panel.style.display = 'none';
});

function switchMajorCityView() {
  var view = document.getElementById('majorCityView').value;
  document.getElementById('majorSearchWrap').style.display = view === 'major_to_city' ? '' : 'none';
  document.getElementById('citySelect').style.display = view === 'city_to_major' ? '' : 'none';
  var panel = document.getElementById('majorOptions');
  if (panel) panel.style.display = 'none';
  updateMajorCity();
}

function updateMajorCity() {
  var view = document.getElementById('majorCityView').value;
  if (view === 'major_to_city') {
    var major = majorCurrent || document.getElementById('majorSearch').value.trim();
    if (!major) return;
    if (ALL_MAJORS.indexOf(major) < 0) return;   // 输入了未匹配的专业名时不更新图表
    var cityData = [];
    for (var city in CITY_MAJOR_MATRIX) { var n = CITY_MAJOR_MATRIX[city][major]||0; if (n>0) cityData.push({city:city, recruits:n}); }
    cityData.sort(function(a,b) { return b.recruits - a.recruits; });
    if (!cityData.length) {
      majorCityChart.clear();
      majorCityChart.setOption({ title: { text: '该专业在各城市均无招录记录', left:'center', top:'middle', textStyle:{color:'#64748b',fontSize:14} }, series: [] }, true);
      document.getElementById('majorCityTableWrap').innerHTML = '';
      return;
    }
    // 注意：reverse() 会原地反转数组。此处必须用 slice().reverse() 提供副本，
    // 否则坐标轴标签与柱子数据会被反转不同次数而错位。
    var axisCities = cityData.map(function(d){ return d.city; }).slice().reverse();
    var barData = cityData.slice().reverse().map(function(d){ return {value:d.recruits, itemStyle:{color:getCityGroup(d.city)==='prd'?'#4a9e5c':(getCityGroup(d.city)==='province'?'#3a7cce':'#c97878')}}; });
    majorCityChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} }, grid: { left: 70, right: 40, top: 15, bottom: 30 },
      xAxis: { type:'value', name:'招录人数' }, yAxis: { type:'category', data:axisCities, axisLabel:{fontSize:10} },
      series: [{ type:'bar', data:barData, label:{show:true,position:'right',fontSize:10}, barMaxWidth:22 }]
    }, true);
    var total = cityData.reduce(function(s,d){return s+d.recruits;},0);
    var th = '<table><thead><tr><th>#</th><th>城市</th><th>分区</th><th>招录</th><th>占比</th></tr></thead><tbody>';
    cityData.forEach(function(d,i) { var g=getCityGroup(d.city); th += '<tr><td>'+(i+1)+'</td><td><strong>'+d.city+'</strong></td><td>'+(g==='prd'?'珠三角':(g==='province'?'省直':'非珠'))+'</td><td>'+d.recruits+'</td><td>'+Math.round(d.recruits/total*1000)/10+'%</td></tr>'; });
    th += '</tbody></table>';
    document.getElementById('majorCityTableWrap').innerHTML = th;
  } else {
    var city = document.getElementById('citySelect').value;
    if (!city) return;
    var majors = CITY_MAJOR_MATRIX[city]||{};
    var majorsArr = Object.entries(majors).sort(function(a,b){return b[1]-a[1];}).slice(0,20);
    var total = majorsArr.reduce(function(s,d){return s+d[1];},0);
    majorCityChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: {type:'shadow'} }, grid: { left: 120, right: 40, top: 15, bottom: 30 },
      xAxis: { type:'value', name:'招录人数' }, yAxis: { type:'category', data:majorsArr.map(function(d){return d[0];}).reverse(), axisLabel:{fontSize:9} },
      series: [{ type:'bar', data:majorsArr.map(function(d){return d[1];}).reverse(), label:{show:true,position:'right',fontSize:9}, barMaxWidth:18, itemStyle:{color:'#1a3c6e'} }]
    }, true);
    var th = '<table><thead><tr><th>#</th><th>专业</th><th>招录</th><th>占比</th></tr></thead><tbody>';
    majorsArr.forEach(function(d,i) { th += '<tr><td>'+(i+1)+'</td><td><strong>'+d[0]+'</strong></td><td>'+d[1]+'</td><td>'+Math.round(d[1]/total*1000)/10+'%</td></tr>'; });
    th += '</tbody></table>';
    document.getElementById('majorCityTableWrap').innerHTML = th;
  }
}

// ====== 地域：城市对比 ======
function initCityCompare() {
  var sel = document.getElementById('compareCities');
  CITY_RANKING.forEach(function(c) { var opt = document.createElement('option'); opt.value=c; opt.textContent=c; sel.appendChild(opt); });
  selectCompareCities();
}
initCityCompare();

// 首屏的两个「洞察总览」是各自一级 Tab 的默认页，容器都是空 div 且只能由 JS 填充。
// 它们此前只被 needsRefresh 引用、没有任何初始调用，导致首屏一片空白，
// 必须手动点一次"已经处于激活状态"的 Tab 才出内容。这里补上初始化。
function initOpeningViews() {
  if (typeof renderMajorOverview === 'function') renderMajorOverview();
  if (typeof renderCityOverview === 'function') renderCityOverview();
}
initOpeningViews();

function selectCompareCities() {
  var sel = document.getElementById('compareCities');
  var defaults = ['广州','深圳'].filter(function(c) { return CITY_YEARLY[c]; });
  Array.from(sel.options).forEach(function(opt) { opt.selected = defaults.indexOf(opt.value) >= 0; });
  updateCityCompare();
}

function updateCityCompare() {
  var sel = document.getElementById('compareCities');
  var selected = Array.from(sel.selectedOptions).map(function(o) { return o.value; }).slice(0, 4);
  if (selected.length < 2) selected = ['广州','深圳'];
  var html = '<div class="two-col" style="margin-bottom:12px;">';
  selected.forEach(function(city) {
    var info = CITY_YEARLY[city]; if (!info) return;
    var g = getCityGroup(city); var fresh = CITY_FRESH[city]||{};
    var growth = calcCityGrowth(city); var freshR = calcCityFreshRatio(city);
    var top5 = Object.entries(CITY_MAJOR_MATRIX[city]||{}).sort(function(a,b){return b[1]-a[1];}).slice(0,5);
    html += '<div style="background:#f8faff;border-radius:10px;padding:12px;">';
    html += '<h3 style="color:var(--blue-800);margin-bottom:6px;">'+city+' <span style="font-size:11px;font-weight:400;color:var(--ink-400);">'+(g==='prd'?'珠三角':(g==='province'?'省直':'非珠'))+'</span></h3>';
    html += '<div class="detail-metrics" style="margin:4px 0;">';
    html += '<div class="dm-item"><div class="dm-val">'+info.total_recruits+'</div><div class="dm-label">总招录</div></div>';
    html += '<div class="dm-item"><div class="dm-val '+(growth>0?'up':'down')+'">'+growth+'%</div><div class="dm-label">增长率</div></div>';
    html += '<div class="dm-item"><div class="dm-val">'+freshR+'%</div><div class="dm-label">应届占比</div></div>';
    html += '<div class="dm-item"><div class="dm-val">'+info.pct_of_total+'%</div><div class="dm-label">占全省比</div></div>';
    html += '</div>';
    html += '<div style="height:100px;" id="cityCmpTrend'+city.replace(/\s/g,'')+'"></div>';
    html += '<div style="margin-top:4px;"><strong style="font-size:10px;">热门专业：</strong> ';
    top5.forEach(function(item) { html += '<span style="background:#e8edf5;padding:1px 5px;border-radius:6px;font-size:10px;margin:1px;">'+item[0]+'</span>'; });
    html += '</div></div>';
  });
  html += '</div>';
  document.getElementById('compareContent').innerHTML = html;
  setTimeout(function() {
    selected.forEach(function(city) {
      var el = document.getElementById('cityCmpTrend'+city.replace(/\s/g,''));
      if (!el) return;
      var mini = echarts.getInstanceByDom(el) || echarts.init(el);
      var info = CITY_YEARLY[city];
      var iy = (info && info.yearly) || {};
      mini.setOption({ grid:{left:'5%',right:'3%',top:10,bottom:10}, xAxis:{type:'category',data:YEARS,axisLabel:{fontSize:7}}, yAxis:{type:'value',splitLine:{lineStyle:{type:'dashed',opacity:0.3}},show:false}, series:[{type:'line',data:YEARS.map(function(y){return iy[y]||0;}),smooth:true,lineStyle:{color:'#1a3c6e',width:2},areaStyle:{color:'#e8edf5'},symbol:'circle',symbolSize:3}] });
    });
  }, 50);
}

// ====== 窗口resize ======
window.addEventListener('resize', resizeAll);

// ====== Mobile / WeChat 增强 Resize ======
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', function() {
    setTimeout(resizeAll, 120);
  });
}
window.addEventListener('orientationchange', function() {
  setTimeout(resizeAll, 300);
});

// ====== Mobile 工具函数 ======
function isMobileWidth() { return window.innerWidth < 560; }
function isMobileLarge() { return window.innerWidth < 768; }
function mobileGridLeft() { return window.innerWidth < 430 ? 130 : (window.innerWidth < 560 ? 150 : 180); }

// ====== SVG Wave Background ======
(function() {
  var svg = document.getElementById('wave-svg');
  if (!svg) return;
  var isMobile = window.innerWidth < 560;
  var GAP = isMobile ? 20 : 10, lines = [], paths = [], time = 0;
  var mouse = { x: -10000, y: 0, sx: -10000, sy: 0, v: 0, vs: 0, a: 0, set: false };
  function init() {
    var w = window.innerWidth, h = window.innerHeight;
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    var totalLines = Math.ceil((w + 200) / GAP);
    var totalPoints = Math.ceil((h + 30) / GAP);
    var xStart = (w - GAP * totalLines) / 2;
    var yStart = (h - GAP * totalPoints) / 2;
    paths.forEach(function(p) { p.remove(); });
    lines = []; paths = [];
    for (var i = 0; i < totalLines; i++) {
      var pts = [];
      for (var j = 0; j < totalPoints; j++) {
        pts.push({ x: xStart + GAP * i, y: yStart + GAP * j, wave: 0, cursor: 0 });
      }
      lines.push(pts);
      var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', 'rgba(148,163,184,0.25)');
      path.setAttribute('stroke-width', '1');
      svg.appendChild(path);
      paths.push(path);
    }
  }
  function animate() {
    time++;
    for (var i = 0; i < lines.length; i++) {
      var pts = lines[i];
      for (var j = 0; j < pts.length; j++) {
        var p = pts[j];
        p.wave = Math.sin(p.y * 0.004 + time * 0.002 + i * 0.5) * 18
               + Math.sin(p.y * 0.008 + time * 0.003 + i * 0.9) * 10
               + Math.sin(p.y * 0.015 + time * 0.005 + i * 1.3) * 5;
        var dx = p.x - mouse.x, dy = p.y - mouse.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) p.cursor += ((120 - dist) / 120 * 25 - p.cursor) * 0.08;
        else p.cursor *= 0.92;
      }
    }
    for (var i = 0; i < paths.length; i++) {
      var pts = lines[i];
      var d = '';
      for (var j = 0; j < pts.length; j++) {
        var p = pts[j];
        var x = p.x + p.wave + p.cursor;
        d += (j === 0 ? 'M' : 'L') + ' ' + x.toFixed(1) + ' ' + p.y.toFixed(1);
      }
      paths[i].setAttribute('d', d);
    }
    requestAnimationFrame(animate);
  }
  init();
  animate();
  window.addEventListener('resize', function() { init(); });
  document.addEventListener('mousemove', function(e) {
    var rect = svg.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
    if (!mouse.set) { mouse.sx = mouse.x; mouse.sy = mouse.y; mouse.set = true; }
  });
})();
</script>
</body>
</html>
"""

# ====== 替换占位符 ======
html = html.replace('__RANKING_JS__', ranking_js)
html = html.replace('__RAW_RANKING_JS__', raw_ranking_js)
html = html.replace('__CO_PAIRS_JS__', co_pairs_js)
html = html.replace('__CITY_YEARLY_JS__', city_yearly_js)
html = html.replace('__CITY_RANKING_JS__', city_ranking_js)
html = html.replace('__CITY_EDUCATION_JS__', city_education_js)
html = html.replace('__CITY_FRESH_JS__', city_fresh_js)
html = html.replace('__CITY_MAJOR_MATRIX_JS__', city_major_matrix_js)
html = html.replace('__GD_GEOJSON_JS__', gd_geojson_js)
html = html.replace('__CITY_NAME_MAP_JS__', city_name_map_js)
html = html.replace('__ALL_MAJORS_JS__', all_majors_js)
html = html.replace('__DEFAULT_MAJOR__', _html.escape(default_major, quote=True))
html = html.replace('__SUM_POS__', str(sum_pos))
html = html.replace('__SUM_MAJ__', str(sum_maj))
html = html.replace('__TOTAL_RANKED__', str(total_ranked))
html = html.replace('__TOP_RECRUIT__', str(top_recruit))
html = html.replace('__TOTAL_CITIES__', str(city_summary['total_cities']))
html = html.replace('__NETWORK_DD_OPTS__', '<option value="global">全局关系</option>' + dd_opts)
html = html.replace('__DD_OPTS__', dd_opts)
html = html.replace('__TR_OPTS__', tr_opts)
html = html.replace('__TR_OPTS_2__', tr_opts_2)
html = html.replace('__TR_OPTS_3__', tr_opts_3)
html = html.replace('__CHK_HTML__', chk_html)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'合并完成: {OUTPUT_FILE}')
print(f'  文件大小: {os.path.getsize(OUTPUT_FILE) / 1024:.0f} KB')










