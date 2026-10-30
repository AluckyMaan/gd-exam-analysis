#!/usr/bin/env python3
"""
「物流管理与工程类（B1206）」招录分析页生成器
------------------------------------------------
读取 data/wuliu_data.json 与 data/all_majors_ranking.json，
生成单文件离线报告：根目录《物流管理与工程类招录分析.html》。

用法：
    python scripts/generate/generate_wuliu_html.py

设计遵循主看板 v5「数据年鉴」视觉系统（纸白 / 墨黑 / 铜金 / 发丝线），
图表使用本地 assets/echarts.min.js（相对路径，双击即可打开）。
"""

import json
import os
import sys
from datetime import date

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUT_PATH = os.path.join(BASE_DIR, '物流管理与工程类招录分析.html')

MAJOR = '物流管理与工程类'
CODE = 'B1206'
PRD = {'广州', '深圳', '珠海', '佛山', '东莞', '中山', '惠州', '江门', '肇庆'}


def fmt(n):
    return f'{n:,}'


def pct(a, b):
    return round(a / b * 100, 1) if b else 0.0


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def load():
    with open(os.path.join(DATA_DIR, 'wuliu_data.json'), encoding='utf-8') as f:
        data = json.load(f)
    with open(os.path.join(DATA_DIR, 'all_majors_ranking.json'), encoding='utf-8') as f:
        ranking = json.load(f)['ranking']
    return data, ranking


def build_units_table(units, total):
    rows = []
    for i, u in enumerate(units[:20], 1):
        rows.append(
            '<tr>'
            f'<td class="num muted">{i:02d}</td>'
            f'<td><b>{esc(u["unit"])}</b></td>'
            f'<td>{esc(u["city"])}</td>'
            f'<td>{esc(u["system"])}</td>'
            f'<td class="num">{u["positions"]}</td>'
            f'<td class="num"><b>{u["recruits"]}</b></td>'
            f'<td class="num muted">{pct(u["recruits"], total):.1f}%</td>'
            '</tr>'
        )
    return '\n'.join(rows)


def build_peer_table(ranking, names):
    by = {m['major']: m for m in ranking}
    rows = []
    for name in names:
        m = by.get(name)
        if not m:
            continue
        cls = ' class="hl"' if name == MAJOR else ''
        rows.append(
            f'<tr{cls}>'
            f'<td><b>{esc(name)}</b><span class="code">{esc(m.get("code") or "")}</span></td>'
            f'<td class="num">{fmt(m["total_recruits"])}</td>'
            f'<td class="num">{fmt(m["total_positions"])}</td>'
            f'<td class="num">#{m["rank"]}</td>'
            f'<td class="num">{m["purity"]:.1f}%</td>'
            f'<td class="num">{m["competition_index"]:.2f}</td>'
            f'<td class="num">{m["fresh_ratio"]:.1f}%</td>'
            f'<td class="num">{m["growth_rate"]:+.1f}%</td>'
            '</tr>'
        )
    return '\n'.join(rows)


def build_eng_table(ranking):
    eng = [m for m in ranking if '工程' in m['major'] and m.get('code')]
    eng.sort(key=lambda x: -x['total_recruits'])
    rows = []
    for m in eng[:15]:
        cls = ' class="hl"' if m['major'] == MAJOR else ''
        rows.append(
            f'<tr{cls}>'
            f'<td><b>{esc(m["major"])}</b><span class="code">{esc(m["code"])}</span></td>'
            f'<td class="num">{fmt(m["total_recruits"])}</td>'
            f'<td class="num">{fmt(m["total_positions"])}</td>'
            f'<td class="num">#{m["rank"]}</td>'
            f'<td class="num">{m["purity"]:.1f}%</td>'
            f'<td class="num">{m["competition_index"]:.2f}</td>'
            f'<td class="num">{m["growth_rate"]:+.1f}%</td>'
            '</tr>'
        )
    return '\n'.join(rows)


def main():
    data, ranking = load()
    s = data['summary']
    yearly = data['yearly']
    positions = data['positions']
    total = s['total_recruits']
    total_pos = s['total_positions']

    peak = max(yearly, key=lambda y: y['recruits'])
    last = yearly[-1]
    prev = yearly[-2]
    early_avg = sum(y['recruits'] for y in yearly[:3]) / 3
    recent_avg = sum(y['recruits'] for y in yearly[-3:]) / 3
    growth = (recent_avg - early_avg) / early_avg * 100
    yoy = (last['recruits'] - prev['recruits']) / prev['recruits'] * 100
    prov_yoy = (last['province_recruits'] - prev['province_recruits']) / prev['province_recruits'] * 100

    top_city = data['city'][0]
    y26 = [p for p in positions if p['year'] == '2026']
    y26_top = {}
    for p in y26:
        y26_top[p['city']] = y26_top.get(p['city'], 0) + p['recruits']
    y26_top = sorted(y26_top.items(), key=lambda x: -x[1])[:2]

    fresh_cur = s['fresh_ratio']
    social_ratio = 100 - fresh_cur
    edu_map = {e['edu']: e for e in data['education']}
    edu_bk_up = edu_map.get('本科以上', {'recruits': 0, 'positions': 0})
    edu_bk = edu_map.get('本科', {'recruits': 0, 'positions': 0})
    edu_dz = sum(e['recruits'] for e in data['education'] if e['edu'].startswith('大专'))

    systems = data['system']
    police = next((x for x in systems if x['system'] == '公安'), {'recruits': 0, 'positions': 0})

    peers = ['法学类', '工商管理类', '公共管理类', '管理科学与工程类',
             '交通运输类', '电子商务类', '旅游管理类', MAJOR, '工业工程类']

    # 图表数据（保持与 JSON 一致）
    chart = {
        'years': [y['year'] for y in yearly],
        'recruits': [y['recruits'] for y in yearly],
        'positions': [y['positions'] for y in yearly],
        'share': [y['share_recruits'] for y in yearly],
        'freshCurrent': [y['fresh_current_recruits'] for y in yearly],
        'freshAny': [y['fresh_recruits'] - y['fresh_current_recruits'] for y in yearly],
        'social': [y['social_recruits'] for y in yearly],
        'city': [[c['city'], c['recruits'], c['positions'], c['city'] in PRD] for c in data['city'][:15]],
        'system': [[x['system'], x['recruits'], x['positions']] for x in systems],
        'edu': [['本科以上', edu_bk_up['recruits']], ['本科', edu_bk['recruits']], ['大专', edu_dz]],
        'co': [[c['major'], c['recruits'], c['co_rate']] for c in data['cooccurrence']],
        'subs': [[x['name'], x['positions'], x['recruits'], x['type']] for x in data['submajors']],
        'province': [[y['year'], y['province_recruits'], y['province_positions']] for y in yearly],
    }

    summary_html = f'''
      <p><b>规模中等偏小，七年累计 472 人。</b>物流管理与工程类在 2020—2026 年广东省考中共出现
      <b>{total}</b> 人 / <b>{total_pos}</b> 个职位，占全省同期招录 {fmt(s['province_total_recruits'])} 人的
      <b>{pct(total, s['province_total_recruits'])}%</b>，在 {s['all_majors_count']} 个专业中排第
      <b>{s['rank_in_all_majors']}</b> 位。</p>
      <p><b>总量上行、2026 回落。</b>招录人数从 2020 年的 {yearly[0]['recruits']} 人升至 {peak['year']} 年的
      <b>{peak['recruits']}</b> 人峰值，2026 年回落至 <b>{last['recruits']}</b> 人（同比 {yoy:+.1f}%）；
      同期全省招录同比 {prov_yoy:+.1f}%，该专业占全省比例仍为 <b>{last['share_recruits']}%</b>，基本持平。</p>
      <p><b>岗位以机关综合岗为主，公安是第三大去向。</b>县以上机关 {systems[0]['recruits']} 人
      （{pct(systems[0]['recruits'], total)}%）、乡镇机关 {next(x for x in systems if x['system'] == '乡镇机关')['recruits']} 人、
      公安 {police['recruits']} 人（{pct(police['recruits'], total)}%）、监狱戒毒 {next(x for x in systems if x['system'] == '监狱戒毒')['recruits']} 人。
      22 个城市全覆盖，{top_city['city']}以 {top_city['recruits']} 人居首。</p>
      <p><b>“共招”是竞争的关键。</b>354 个职位中仅 {round(total_pos * s['purity'] / 100)} 个（{s['purity']}%）只招物流类专业，
      {100 - s['purity']:.1f}% 的职位同时接受其他专业，平均每个职位并列 <b>{s['competition_index']}</b> 个其他专业，
      最常见的同岗专业是工商管理类、管理科学与工程类、公共管理类。</p>
    '''

    units_table = build_units_table(data['units'], total)
    peer_table = build_peer_table(ranking, peers)
    eng_table = build_eng_table(ranking)

    kpis = f'''
      <div class="kpi"><b>{fmt(total)}</b><span>累计招录 · 人</span><em>2020—2026 全部职位表</em></div>
      <div class="kpi"><b>{fmt(total_pos)}</b><span>职位数 · 个</span><em>平均每职位 {s['avg_recruits_per_pos']} 人</em></div>
      <div class="kpi"><b>{s['city_coverage']}</b><span>覆盖城市</span><em>全省 {s['city_coverage']}/22 市</em></div>
      <div class="kpi"><b>{pct(total, s['province_total_recruits'])}%</b><span>占全省招录</span><em>全省合计 {fmt(s['province_total_recruits'])} 人</em></div>
    '''

    micro = f'''
      <div class="micro"><b>#{s['rank_in_all_majors']} / {s['all_majors_count']}</b><span>全专业招录排名</span></div>
      <div class="micro"><b>{s['competition_index']}</b><span>平均并列其他专业数</span></div>
      <div class="micro"><b>{s['purity']}%</b><span>仅招物流类的职位占比</span></div>
      <div class="micro"><b>{fresh_cur}%</b><span>应届可报比例</span></div>
    '''

    today = date.today().strftime('%Y-%m-%d')

    html = TEMPLATE
    replacements = {
        '@@KPI@@': kpis,
        '@@MICRO@@': micro,
        '@@SUMMARY@@': summary_html,
        '@@UNITS@@': units_table,
        '@@PEERS@@': peer_table,
        '@@ENG@@': eng_table,
        '@@DATA@@': json.dumps(chart, ensure_ascii=False, separators=(',', ':')),
        '@@POSITIONS@@': json.dumps([
            {
                'y': p['year'], 'c': p['city'], 's': p['system'], 'u': p['unit'],
                'p': p['position'], 'n': p['recruits'], 'e': p['education'],
                'f': p['fresh_type'], 't': p['prof'][:220],
            } for p in positions
        ], ensure_ascii=False, separators=(',', ':')),
        '@@TODAY@@': today,
        '@@N@@': str(total),
        '@@NP@@': str(total_pos),
        '@@RANK@@': str(s['rank_in_all_majors']),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'已生成: {OUT_PATH}  ({len(html) / 1024:.0f} KB)')
    print(f'  累计 {total} 人 / {total_pos} 职位 / {s["city_coverage"]} 城市 / 排名 #{s["rank_in_all_majors"]}')


TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>物流管理与工程类（B1206）省考招录分析 · 广东 2020—2026</title>
<style>
:root{
  --paper:#F3F1EA; --paper2:#EDE9DE; --card:#FBF9F3;
  --ink:#101418; --ink2:#2A2F36; --muted:#6C7076; --faint:#8A8D91;
  --hair:#D9D4C7; --rule:#DCD7CA; --brand:#0C1520; --copper:#A0622F;
  --data:#16222E; --data2:#42505C; --sand:#C9C4B6; --up:#9A3B26; --down:#3F6B4F;
  --sans:"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box}
html{background:var(--paper)}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.75;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
::selection{background:rgba(160,98,47,.18)}
.wrap{max-width:1200px;margin:0 auto;padding:0 32px 72px}

/* masthead */
.masthead{background:var(--brand);color:#F6F4EE}
.masthead-inner{max-width:1200px;margin:0 auto;padding:0 32px;min-height:84px;display:flex;align-items:center;gap:14px}
.mark{width:30px;height:30px;border:1px solid rgba(246,244,238,.5);display:grid;place-items:center;font-size:13px;font-weight:700;flex:none;line-height:1}
.brand{display:flex;flex-direction:column;gap:3px;min-width:0}
.brand b{font-size:15px;font-weight:600;letter-spacing:.06em;white-space:nowrap}
.brand small{font-size:9.5px;letter-spacing:.2em;color:rgba(246,244,238,.5);font-weight:500;white-space:nowrap}
.masthead .meta{margin-left:auto;display:flex;gap:26px;font-size:11px;letter-spacing:.12em;color:rgba(246,244,238,.62);white-space:nowrap}
.masthead .meta b{color:#F6F4EE;font-weight:600}

/* hero */
.hero{padding:56px 0 0;border-bottom:1px solid var(--hair)}
.eyebrow{display:flex;align-items:center;gap:10px;margin:0 0 20px;font-size:10.5px;letter-spacing:.22em;color:var(--copper);font-weight:600;text-transform:uppercase}
.eyebrow::before{content:"";width:18px;height:2px;background:var(--copper);display:block;flex:none}
h1{font-size:46px;line-height:1.16;font-weight:700;letter-spacing:-.015em;margin:0 0 16px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1 .code{font-size:15px;font-weight:500;letter-spacing:.12em;color:var(--copper);border:1px solid var(--hair);padding:3px 8px;border-radius:3px;transform:translateY(-4px)}
.sub{max-width:800px;color:var(--muted);font-size:15px;line-height:1.75;margin:0}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--hair);margin-top:38px;padding:26px 0 0}
.kpi{border-left:1px solid var(--hair);padding:0 26px;min-width:0}
.kpi:first-child{border-left:0;padding-left:0}
.kpi b{display:block;font-size:44px;line-height:1;font-weight:600;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi span{display:block;margin-top:10px;font-size:11px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase}
.kpi em{display:block;margin-top:6px;font-style:normal;font-size:12px;color:var(--faint)}
.microstats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--hair);margin-top:26px}
.micro{padding:18px 26px;border-left:1px solid var(--hair)}
.micro:first-child{border-left:0;padding-left:0}
.micro b{display:block;font-size:19px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.micro span{display:block;margin-top:4px;font-size:11.5px;color:var(--muted);letter-spacing:.04em}

/* sections */
.section{margin-top:56px}
.kicker{display:flex;align-items:center;gap:10px;font-size:10.5px;letter-spacing:.22em;color:var(--copper);font-weight:600;text-transform:uppercase}
.kicker::before{content:"";width:18px;height:2px;background:var(--copper);display:block;flex:none}
h2{font-size:28px;line-height:1.3;font-weight:700;letter-spacing:-.01em;margin:10px 0 0}
.lead{color:var(--muted);font-size:13.5px;line-height:1.8;margin:8px 0 22px;max-width:860px}
.summary{border-left:2px solid var(--copper);padding:2px 0 2px 20px;margin:42px 0 0}
.summary p{margin:0 0 12px;font-size:13.5px;line-height:1.85;color:var(--ink2)}
.summary p:last-child{margin-bottom:0}
.summary b{color:var(--ink);font-weight:650}

.grid{display:grid;gap:18px}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.g23{grid-template-columns:1.6fr 1fr}
.card{background:var(--card);border:1px solid var(--hair);border-radius:4px;padding:22px 24px;min-width:0}
.card h3{font-size:15px;font-weight:650;margin:0 0 4px;letter-spacing:.01em}
.card .cap{font-size:12px;color:var(--muted);margin:0 0 14px;line-height:1.6}
.chart{height:320px}
.chart-sm{height:250px}

/* insight strip */
.insights{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--hair);border-bottom:1px solid var(--hair);margin-top:20px}
.insight{padding:18px 22px;border-left:1px solid var(--hair)}
.insight:first-child{border-left:0;padding-left:0}
.insight b{display:block;font-size:12px;letter-spacing:.08em;color:var(--copper);margin-bottom:6px}
.insight p{margin:0;font-size:13.5px;line-height:1.75;color:var(--ink2)}
.insight .big{font-size:23px;font-weight:600;letter-spacing:-.01em;color:var(--ink);font-variant-numeric:tabular-nums}

/* chips */
.chips{display:flex;gap:14px;align-items:center;font-size:11.5px;color:var(--muted);margin:0 0 8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:6px}
.swatch{width:9px;height:9px;border-radius:2px;display:inline-block}

/* tables */
.tablewrap{overflow:auto;max-height:560px;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{position:sticky;top:0;z-index:2;background:var(--card);text-align:left;font-weight:600;color:var(--muted);border-bottom:1px solid var(--hair);padding:10px 12px;white-space:nowrap;font-size:11.5px;letter-spacing:.06em}
td{padding:9px 12px;border-bottom:1px solid #E7E2D6;vertical-align:top;line-height:1.6}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.nw{white-space:nowrap}
td.pos{min-width:170px;max-width:250px}
td.muted{color:var(--faint)}
tr:hover td{background:#F6F3EA}
tr.hl td{background:#F4EDE3}
tr.hl:hover td{background:#F0E6D8}
.pos-table{table-layout:fixed;min-width:1000px}
.pos-table th:nth-child(1),.pos-table td:nth-child(1){width:56px}
.pos-table th:nth-child(2),.pos-table td:nth-child(2){width:66px}
.pos-table th:nth-child(3),.pos-table td:nth-child(3){width:86px}
.pos-table th:nth-child(4),.pos-table td:nth-child(4){width:180px;overflow-wrap:anywhere}
.pos-table th:nth-child(5),.pos-table td:nth-child(5){width:196px;overflow-wrap:anywhere}
.pos-table th:nth-child(6),.pos-table td:nth-child(6){width:48px}
.pos-table th:nth-child(7),.pos-table td:nth-child(7){width:78px}
.pos-table th:nth-child(8),.pos-table td:nth-child(8){width:92px}
.pos-table th:nth-child(9),.pos-table td:nth-child(9){overflow:hidden}
.code{display:inline-block;margin-left:7px;font-size:10.5px;letter-spacing:.08em;color:var(--faint);border:1px solid var(--hair);border-radius:2px;padding:0 4px;vertical-align:1px}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border:1px solid var(--hair);border-radius:2px;color:var(--muted);white-space:nowrap;background:#F7F4EC}
.tag.prd{border-color:#B9C2CB;color:#1E3A4F}
.tag.non{border-color:#DCC3AE;color:#8A4B22}

/* filters */
.filters{display:flex;gap:12px;align-items:center;margin:0 0 12px;flex-wrap:wrap}
.filters input,.filters select{font-family:var(--sans);font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--hair);border-radius:3px;padding:8px 11px;outline:none;min-height:38px}
.filters input{width:260px;max-width:100%}
.filters input:focus,.filters select:focus{border-color:var(--copper);box-shadow:0 0 0 2px rgba(160,98,47,.12)}
.count{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.count b{color:var(--ink)}

/* footnote */
.foot{margin-top:64px;border-top:1px solid var(--hair);padding-top:22px;font-size:12px;color:var(--muted);line-height:1.8}
.foot p{margin:0 0 6px}
.foot b{color:var(--ink2)}
details{border-top:1px solid var(--hair);padding:16px 0 0;margin-top:22px}
summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--ink2);outline:none}
summary:hover{color:var(--copper)}
details .body{font-size:12.5px;color:var(--muted);line-height:1.85;margin-top:10px;max-width:900px}
details .body b{color:var(--ink2)}
.up{color:var(--up)} .down{color:var(--down)}

@media (max-width:980px){
  .wrap{padding:0 20px 56px}
  h1{font-size:32px}
  .kpis{grid-template-columns:1fr 1fr;row-gap:24px}
  .kpi:nth-child(3){border-left:0;padding-left:0}
  .microstats{grid-template-columns:1fr 1fr;row-gap:14px}
  .micro:nth-child(3){border-left:0;padding-left:0}
  .g2,.g3,.g23{grid-template-columns:1fr}
  .insights{grid-template-columns:1fr}
  .insight{border-left:0;padding-left:0;border-top:1px solid var(--hair)}
  .insight:first-child{border-top:0}
  .masthead-inner{min-height:64px;flex-wrap:wrap;padding-top:10px;padding-bottom:10px}
  .masthead .meta{margin-left:0;width:100%;gap:14px;font-size:10px;flex-wrap:wrap;white-space:normal;row-gap:4px}
  .masthead .meta span{white-space:nowrap}
  .masthead .meta span:nth-child(3){display:none}
  h2{font-size:24px}
  .chart{height:280px}
  .filters input{width:100%}
}
@media print{
  body{background:#fff}
  .masthead{background:#101418}
  .card{break-inside:avoid}
  .tablewrap{max-height:none;overflow:visible}
  th{position:static}
}
</style>
</head>
<body>
<header class="masthead">
  <div class="masthead-inner">
    <div class="mark">粤</div>
    <div class="brand">
      <b>广东省考职位数据</b>
      <small>DATA ANNUAL · 专业招录分析</small>
    </div>
    <div class="meta">
      <span>数据范围 <b>2020—2026</b></span>
      <span>11 份职位表</span>
      <span>74,849 条职位记录</span>
      <span>生成于 <b>@@TODAY@@</b></span>
    </div>
  </div>
</header>

<main class="wrap">
  <section class="hero">
    <div class="eyebrow">专业招录分析 · Logistics Management &amp; Engineering</div>
    <h1>物流管理与工程类<span class="code">B1206</span></h1>
    <p class="sub">广东省考试录用公务员（省考）统一招考职位表中，专业要求含「物流管理与工程类」及其下辖的物流管理、物流工程、供应链管理、采购管理的全部职位。不含选调生、急需紧缺专业等另行发布的招录计划。</p>
    <div class="kpis">@@KPI@@</div>
    <div class="microstats">@@MICRO@@</div>
  </section>

  <section class="summary">@@SUMMARY@@</section>

  <section class="section">
    <div class="kicker">01 · 规模与趋势</div>
    <h2>七年招录规模：从 35 人走到 107 人，再回落到 58 人</h2>
    <p class="lead">2020—2024 年稳步上行，2025 年达到峰值；2026 年随全省招录大盘同步收缩。由于分母也在收缩，该专业占全省招录的比例并未明显下滑，稳定在 0.5% 左右。</p>

    <div class="card">
      <h3>逐年招录人数与职位数</h3>
      <p class="cap">柱：招录人数（人）；线：职位数（个）。悬停查看占全省招录比例。</p>
      <div id="trendChart" class="chart"></div>
    </div>

    <div class="insights">
      <div class="insight">
        <b>峰值 · 2025</b>
        <p><span class="big">107</span> 人 / 76 个职位，为七年最高。</p>
      </div>
      <div class="insight">
        <b>2026 同比</b>
        <p><span class="big">-45.8%</span>，58 人；同期全省招录 -32.4%。</p>
      </div>
      <div class="insight">
        <b>三年均值变化</b>
        <p><span class="big">+86.5%</span>，2024—26 均值 82.7 人 vs 2020—22 均值 44.3 人。</p>
      </div>
    </div>

    <div class="card" style="margin-top:18px">
      <h3>同门类参照：在管理类与邻近专业中的位置</h3>
      <p class="cap">按七年累计招录人数排序。“纯度”指仅招该专业类的职位占比；“竞争指数”指平均每个职位并列的其他专业数；“增长”为 2024—26 均值相对 2020—22 均值。</p>
      <div class="tablewrap" style="max-height:420px">
        <table>
          <thead><tr><th>专业类</th><th class="num">招录人数</th><th class="num">职位数</th><th class="num">全省排名</th><th class="num">纯度</th><th class="num">竞争指数</th><th class="num">应届占比</th><th class="num">增长</th></tr></thead>
          <tbody>@@PEERS@@</tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="kicker">02 · 地域分布</div>
    <h2>22 市全覆盖，江门、广州、肇庆领跑</h2>
    <p class="lead">珠三角九市合计 214 人（45.3%），非珠三角 258 人（54.7%）。与全省大盘“珠三角略低于非珠”的结构一致，物流类岗位没有明显向核心城市集中。</p>

    <div class="grid g23">
      <div class="card">
        <h3>城市招录人数 Top 15</h3>
        <p class="cap">悬停查看职位数与人均招录。</p>
        <div class="chips">
          <span class="chip"><i class="swatch" style="background:#16222E"></i>珠三角</span>
          <span class="chip"><i class="swatch" style="background:#A0622F"></i>非珠三角</span>
        </div>
        <div id="cityChart" class="chart" style="height:380px"></div>
      </div>
      <div class="card">
        <h3>区域结构</h3>
        <p class="cap">按招录人数占比。</p>
        <div id="prdChart" class="chart-sm" style="height:250px"></div>
        <div class="insights" style="grid-template-columns:1fr;border-bottom:0;margin-top:8px">
          <div class="insight" style="border-left:0;padding-left:0">
            <b>2026 年最新分布</b>
            <p>梅州、河源各 7 人并列第一；广州 5 人、江门 4 人、肇庆 4 人。珠三角九市 19 人（32.8%），非珠三角 39 人（67.2%），当年岗位进一步向非珠地区倾斜。</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="kicker">03 · 系统与门槛</div>
    <h2>县以上机关近半，公安系统是第三大去向</h2>
    <p class="lead">学历门槛高度集中于本科：本科以上与本科合计占 98.1%，大专仅 9 人；应届可报比例 39.0%，六成岗位面向社会人员。</p>

    <div class="grid g3">
      <div class="card">
        <h3>招录系统</h3>
        <p class="cap">按招录人数（人）。</p>
        <div id="systemChart" class="chart-sm"></div>
      </div>
      <div class="card">
        <h3>学历要求</h3>
        <p class="cap">按招录人数（人）。</p>
        <div id="eduChart" class="chart-sm"></div>
      </div>
      <div class="card">
        <h3>应届门槛</h3>
        <p class="cap">逐年招录人数构成（人）。</p>
        <div id="freshChart" class="chart-sm"></div>
      </div>
    </div>

    <div class="insights">
      <div class="insight">
        <b>机关结构</b>
        <p>县以上机关 208 人（44.1%）、乡镇机关 131 人（27.8%）、公安 103 人（21.8%）、监狱戒毒 30 人（6.4%）。</p>
      </div>
      <div class="insight">
        <b>学历结构</b>
        <p>本科以上 261 人（55.3%）、本科 202 人（42.8%）、大专 9 人（1.9%）；无“研究生及以上”单独门槛岗位。</p>
      </div>
      <div class="insight">
        <b>应届结构</b>
        <p>社会人员 288 人（61.0%）、应届 184 人（39.0%），其中当年应届 34 人（7.2%）。</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="kicker">04 · 竞争结构</div>
    <h2>86% 的职位是“共招岗”，物流类很少单独设岗</h2>
    <p class="lead">这是物流类岗位最重要的特征：绝大多数职位把物流专业与管理、交通、电商等专业并列，报考时的实际竞争对手来自多个专业。以下“共现”统计的是同一职位中与物流类同时出现的其他专业（按招录人数加权）。</p>

    <div class="grid g2">
      <div class="card">
        <h3>最常见的同岗专业 Top 5</h3>
        <p class="cap">柱：共现职位的招录人数；标签：共现率（占物流类全部招录人数的比例）。</p>
        <div id="coChart" class="chart"></div>
      </div>
      <div class="card">
        <h3>专业写法构成</h3>
        <p class="cap">职位专业栏出现该写法的职位数；同一职位可同时出现“专业类 + 具体专业”，故合计大于 354。</p>
        <div id="subChart" class="chart"></div>
      </div>
    </div>

    <div class="insights">
      <div class="insight">
        <b>纯度 13.6%</b>
        <p>354 个职位中仅 48 个只招物流类专业，306 个与其他专业共招。</p>
      </div>
      <div class="insight">
        <b>并列 3.09 个专业</b>
        <p>平均每个职位除物流类外还接受 3.09 个其他专业，竞争面较宽。</p>
      </div>
      <div class="insight">
        <b>“类”比“具体专业”更常见</b>
        <p>252 个职位写“物流管理与工程类”，83 个写“物流管理”，39 个写“物流工程”，采购管理 12 个、供应链管理 8 个。</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="kicker">05 · 主要招录单位</div>
    <h2>监狱系统与公安系统贡献了最多的岗位</h2>
    <p class="lead">按七年累计招录人数排序。广东省监狱管理局以 30 人 / 22 个职位居首，公安系统单位在榜单中占据多数；市场监管、交通运输、乡镇政府也是常见招录方。</p>

    <div class="card">
      <div class="tablewrap" style="max-height:620px">
        <table>
          <thead><tr><th class="num">#</th><th>招考单位</th><th>城市</th><th>系统</th><th class="num">职位数</th><th class="num">招录人数</th><th class="num">占本类</th></tr></thead>
          <tbody>@@UNITS@@</tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="kicker">06 · 职位明细</div>
    <h2>354 个职位全量可检索</h2>
    <p class="lead">支持按单位、职位、城市或专业文字搜索，并可按年份筛选。表中“专业要求”保留原始写法，过长部分已截断，鼠标悬停可看全文。</p>

    <div class="card">
      <div class="filters">
        <input id="q" type="search" placeholder="搜索单位 / 职位 / 城市 / 专业…" aria-label="搜索职位">
        <select id="yearSel" aria-label="按年份筛选">
          <option value="">全部年份</option>
        </select>
        <span class="count" id="cnt"></span>
      </div>
      <div class="tablewrap" style="max-height:640px">
        <table class="pos-table">
          <thead><tr><th>年份</th><th>城市</th><th>系统</th><th>招考单位</th><th>职位</th><th class="num">人数</th><th>学历</th><th>应届</th><th>专业要求</th></tr></thead>
          <tbody id="posBody"></tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="kicker">07 · 附：工程相关专业类参照</div>
    <h2>名称含“工程”的专业类招录概览</h2>
    <p class="lead">若你关注的是更广义的“工程类”专业，可参考下表：242 个专业中名称含“工程”的专业类按累计招录人数排序（前 15）。注意：同一职位可能同时列出多个专业，各行不可相加。</p>

    <div class="card">
      <div class="tablewrap" style="max-height:520px">
        <table>
          <thead><tr><th>专业类</th><th class="num">招录人数</th><th class="num">职位数</th><th class="num">全省排名</th><th class="num">纯度</th><th class="num">竞争指数</th><th class="num">增长</th></tr></thead>
          <tbody>@@ENG@@</tbody>
        </table>
      </div>
    </div>
  </section>

  <div class="foot">
    <p><b>数据口径</b>：统计范围为广东省考试录用公务员（省考）统一招考的官方职位表附件，2020—2023 年每年两份（附件1 乡镇机关 + 附件2 县级以上机关及珠三角乡镇），2024—2026 年每年一份；共 11 份文件、74,849 条职位记录、招录 105,365 人。</p>
    <p><b>专业匹配</b>：专业栏文本命中“物流管理与工程类 / 物流管理 / 物流工程 / 供应链管理 / 采购管理”，并排除“政府采购管理”与研究生层次（如“物流工程硕士”“物流工程与管理硕士”）。本科专业类 B1206 共 472 人 / 354 个职位；另有专科“物流类（C1209）”单独职位 1 个（1 人）未计入。</p>
    <p><b>不可相加</b>：同一职位可同时列出多个专业，专业侧数值会重复计入，不能跨专业相加；“占全省”比例以逐职位聚合的全省真实值（105,365 人）为分母。</p>
    <p><b>其他</b>：不含选调优秀大学毕业生、急需紧缺专业公务员、定向港澳选拔等另行发布的招录计划；2026 年数据为当年省考职位表，后续如有补录不在统计内。</p>
    <details>
      <summary>为什么 2026 年只有 58 人？与全省大盘对照</summary>
      <div class="body">
        2026 年广东省考职位表合计招录 <b>11,779 人</b>，较 2025 年的 <b>17,419 人</b>下降 <b>32.4%</b>，是七年中降幅最大的一年。物流管理与工程类同期从 107 人降至 58 人（-45.8%），降幅大于大盘，但由于基数小，占全省比例仅从 0.61% 微降至 0.49%，仍处于历史区间内。单年波动不宜直接解读为专业需求转弱。
      </div>
    </details>
  </div>
</main>

<script src="assets/echarts.min.js"></script>
<script>
var DATA = @@DATA@@;
var POSITIONS = @@POSITIONS@@;

var GDV5_THEME = {
  color: ['#16222E','#A0622F','#5B6A76','#8C7A5B','#3F6B4F','#9A3B26'],
  backgroundColor: 'transparent',
  textStyle: { fontFamily: '"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif', color: '#2A2F36', fontSize: 12 },
  legend: { textStyle: { color: '#6C7076', fontSize: 11 }, itemWidth: 8, itemHeight: 8, icon: 'circle' },
  tooltip: { backgroundColor: '#FBF9F3', borderColor: '#D9D4C7', borderWidth: 1, padding: [10, 12],
    textStyle: { color: '#2A2F36', fontSize: 12 },
    extraCssText: 'box-shadow:0 8px 24px rgba(16,20,24,.08);border-radius:4px;' },
  categoryAxis: { axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false },
    axisLabel: { color: '#6C7076', fontSize: 11 }, nameTextStyle: { color: '#6C7076' } },
  valueAxis: { axisLine: { show: false }, axisTick: { show: false },
    splitLine: { lineStyle: { color: '#DCD7CA' } }, axisLabel: { color: '#6C7076', fontSize: 11 },
    nameTextStyle: { color: '#6C7076' } }
};
if (window.echarts && typeof echarts.registerTheme === 'function') { echarts.registerTheme('gdv5', GDV5_THEME); }
if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  GDV5_THEME.animation = false;
}

function initChart(id) {
  var el = document.getElementById(id);
  if (!el || !window.echarts) { return null; }
  return echarts.init(el, 'gdv5');
}

function num(n) { return Number(n || 0).toLocaleString('zh-CN'); }

/* ---------- 趋势 ---------- */
function renderTrend() {
  var c = initChart('trendChart'); if (!c) { return; }
  c.setOption({
    grid: { left: 54, right: 22, top: 46, bottom: 34 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: function (ps) {
        var i = ps[0].dataIndex;
        return '<b>' + DATA.years[i] + ' 年</b><br>' +
          '招录人数：<b>' + num(DATA.recruits[i]) + '</b> 人<br>' +
          '职位数：<b>' + num(DATA.positions[i]) + '</b> 个<br>' +
          '占全省招录：<b>' + DATA.share[i].toFixed(2) + '%</b>';
      }
    },
    legend: { right: 0, top: 0, data: ['招录人数', '职位数'] },
    xAxis: { type: 'category', data: DATA.years },
    yAxis: { type: 'value', name: '人 / 个', nameGap: 18, splitNumber: 4 },
    series: [
      {
        name: '招录人数', type: 'bar', barWidth: '44%',
        data: DATA.recruits.map(function (v, i) {
          return { value: v, itemStyle: { color: i === 5 ? '#A0622F' : '#16222E' } };
        }),
        label: { show: true, position: 'top', fontSize: 11, color: '#2A2F36', formatter: '{c}' },
        itemStyle: { borderRadius: [2, 2, 0, 0] }
      },
      {
        name: '职位数', type: 'line', data: DATA.positions,
        symbol: 'circle', symbolSize: 6, lineStyle: { width: 2, color: '#A0622F' },
        itemStyle: { color: '#A0622F' }
      }
    ]
  }, true);
  c.resize();
}

/* ---------- 城市 ---------- */
function renderCity() {
  var c = initChart('cityChart'); if (!c) { return; }
  var rows = DATA.city.slice().reverse();
  var names = rows.map(function (r) { return r[0]; });
  var vals = rows.map(function (r) {
    return { value: r[1], itemStyle: { color: r[3] ? '#16222E' : '#A0622F' } };
  });
  c.setOption({
    grid: { left: 52, right: 40, top: 10, bottom: 24 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: function (ps) {
        var i = ps[0].dataIndex;
        var r = rows[i];
        return '<b>' + r[0] + '</b><br>招录人数：<b>' + num(r[1]) + '</b> 人<br>职位数：<b>' + num(r[2]) + '</b> 个<br>类型：' + (r[3] ? '珠三角' : '非珠三角');
      }
    },
    xAxis: { type: 'value', splitNumber: 3 },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 12, color: '#2A2F36' } },
    series: [{
      type: 'bar', data: vals, barWidth: '58%',
      label: { show: true, position: 'right', fontSize: 11, color: '#2A2F36', formatter: '{c}' }
    }]
  }, true);
  c.resize();
}

/* ---------- 珠三角 / 非珠 ---------- */
function renderPrd() {
  var c = initChart('prdChart'); if (!c) { return; }
  var prd = 214, non = 258;
  c.setOption({
    grid: { left: 10, right: 12, top: 10, bottom: 10 },
    tooltip: { trigger: 'item', formatter: '{b}：{c} 人（{d}%）' },
    legend: { bottom: 0, itemWidth: 8, itemHeight: 8, icon: 'circle' },
    series: [{
      type: 'pie', radius: ['58%', '80%'], center: ['50%', '46%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#FBF9F3', borderWidth: 3 },
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 11, color: '#2A2F36', lineHeight: 16 },
      data: [
        { name: '珠三角', value: prd, itemStyle: { color: '#16222E' } },
        { name: '非珠三角', value: non, itemStyle: { color: '#A0622F' } }
      ]
    }]
  }, true);
  c.resize();
}

/* ---------- 系统 ---------- */
function renderSystem() {
  var c = initChart('systemChart'); if (!c) { return; }
  var rows = DATA.system.slice().reverse();
  c.setOption({
    grid: { left: 92, right: 40, top: 24, bottom: 24 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: function (ps) {
        var i = ps[0].dataIndex; var r = rows[i];
        return '<b>' + r[0] + '</b><br>招录：<b>' + r[1] + '</b> 人<br>职位：<b>' + r[2] + '</b> 个';
      }
    },
    xAxis: { type: 'value', splitNumber: 3 },
    yAxis: { type: 'category', data: rows.map(function (r) { return r[0]; }), axisLabel: { fontSize: 12, color: '#2A2F36' } },
    series: [{
      type: 'bar', barWidth: '52%',
      data: rows.map(function (r) { return { value: r[1], itemStyle: { color: r[0] === '公安' ? '#A0622F' : '#16222E' } }; }),
      label: { show: true, position: 'right', fontSize: 11, color: '#2A2F36', formatter: '{c}' }
    }]
  }, true);
  c.resize();
}

/* ---------- 学历 ---------- */
function renderEdu() {
  var c = initChart('eduChart'); if (!c) { return; }
  var rows = DATA.edu.slice().reverse();
  c.setOption({
    grid: { left: 62, right: 44, top: 8, bottom: 22 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', splitNumber: 3 },
    yAxis: { type: 'category', data: rows.map(function (r) { return r[0]; }), axisLabel: { fontSize: 12, color: '#2A2F36' } },
    series: [{
      type: 'bar', barWidth: '52%', data: rows.map(function (r) { return r[1]; }),
      itemStyle: { color: '#16222E' },
      label: { show: true, position: 'right', fontSize: 11, color: '#2A2F36', formatter: '{c}' }
    }]
  }, true);
  c.resize();
}

/* ---------- 应届 ---------- */
function renderFresh() {
  var c = initChart('freshChart'); if (!c) { return; }
  c.setOption({
    grid: { left: 44, right: 14, top: 34, bottom: 26 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, right: 0, itemWidth: 8, itemHeight: 8, icon: 'circle' },
    xAxis: { type: 'category', data: DATA.years },
    yAxis: { type: 'value', splitNumber: 3 },
    series: [
      { name: '当年应届', type: 'bar', stack: 'f', data: DATA.freshCurrent, itemStyle: { color: '#A0622F' }, barWidth: '48%' },
      { name: '应届/择业期', type: 'bar', stack: 'f', data: DATA.freshAny, itemStyle: { color: '#42505C' } },
      { name: '社会人员', type: 'bar', stack: 'f', data: DATA.social, itemStyle: { color: '#C9C4B6' } }
    ]
  }, true);
  c.resize();
}

/* ---------- 共现 ---------- */
function renderCo() {
  var c = initChart('coChart'); if (!c) { return; }
  var rows = DATA.co;
  c.setOption({
    grid: { left: 54, right: 20, top: 34, bottom: 46 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: function (ps) {
        var i = ps[0].dataIndex; var r = rows[i];
        return '<b>' + r[0] + '</b><br>共现职位招录：<b>' + r[1] + '</b> 人<br>共现率：<b>' + r[2] + '%</b>';
      }
    },
    xAxis: { type: 'category', data: rows.map(function (r) { return r[0]; }),
      axisLabel: { interval: 0, fontSize: 11, color: '#6C7076' } },
    yAxis: { type: 'value', name: '人', nameGap: 16, splitNumber: 3 },
    series: [{
      type: 'bar', barWidth: '46%', data: rows.map(function (r) { return r[1]; }),
      itemStyle: { color: '#A0622F', borderRadius: [2, 2, 0, 0] },
      label: { show: true, position: 'top', fontSize: 11, color: '#2A2F36',
        formatter: function (p) { return rows[p.dataIndex][2] + '%'; } }
    }]
  }, true);
  c.resize();
}

/* ---------- 专业写法 ---------- */
function renderSub() {
  var c = initChart('subChart'); if (!c) { return; }
  var rows = DATA.subs;
  c.setOption({
    grid: { left: 54, right: 20, top: 34, bottom: 74 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: function (ps) {
        var i = ps[0].dataIndex; var r = rows[i];
        return '<b>' + r[0] + '</b>（' + r[3] + '）<br>职位数：<b>' + r[1] + '</b> 个<br>涉及招录：<b>' + r[2] + '</b> 人';
      }
    },
    xAxis: { type: 'category', data: rows.map(function (r) { return r[0]; }),
      axisLabel: { interval: 0, fontSize: 10.5, color: '#6C7076',
        formatter: function (v) { return v.length > 6 ? v.slice(0, 5) + '\n' + v.slice(5) : v; } } },
    yAxis: { type: 'value', name: '职位', nameGap: 16, splitNumber: 3 },
    series: [{
      type: 'bar', barWidth: '46%', data: rows.map(function (r) { return r[1]; }),
      itemStyle: { color: '#16222E', borderRadius: [2, 2, 0, 0] },
      label: { show: true, position: 'top', fontSize: 11, color: '#2A2F36' }
    }]
  }, true);
  c.resize();
}

/* ---------- 职位明细 ---------- */
var FRESH_LABEL = { fresh_current: '当年应届', fresh_any: '应届/择业期', social: '不限应届' };
var yearSel = document.getElementById('yearSel');
var qInput = document.getElementById('q');
var cntEl = document.getElementById('cnt');
var tbody = document.getElementById('posBody');

(function initYears() {
  var ys = DATA.years.slice().reverse();
  ys.forEach(function (y) {
    var o = document.createElement('option');
    o.value = y; o.textContent = y + ' 年';
    yearSel.appendChild(o);
  });
})();

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, function (ch) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch];
  });
}

function renderTable() {
  var q = (qInput.value || '').trim().toLowerCase();
  var y = yearSel.value;
  var out = [];
  var shown = 0;
  for (var i = 0; i < POSITIONS.length; i++) {
    var p = POSITIONS[i];
    if (y && p.y !== y) { continue; }
    var hay = (p.y + ' ' + p.c + ' ' + p.s + ' ' + p.u + ' ' + p.p + ' ' + p.e + ' ' + p.t).toLowerCase();
    if (q && hay.indexOf(q) === -1) { continue; }
    var cityTag = (p.c === '广州' || p.c === '深圳' || p.c === '珠海' || p.c === '佛山' || p.c === '东莞' || p.c === '中山' || p.c === '惠州' || p.c === '江门' || p.c === '肇庆')
      ? '<span class="tag prd">' + esc(p.c) + '</span>'
      : '<span class="tag non">' + esc(p.c) + '</span>';
    out.push('<tr>' +
      '<td class="num nw">' + esc(p.y) + '</td>' +
      '<td class="nw">' + cityTag + '</td>' +
      '<td class="nw">' + esc(p.s) + '</td>' +
      '<td>' + esc(p.u) + '</td>' +
      '<td class="pos">' + esc(p.p) + '</td>' +
      '<td class="num"><b>' + p.n + '</b></td>' +
      '<td class="nw">' + esc(p.e) + '</td>' +
      '<td class="nw">' + (FRESH_LABEL[p.f] || esc(p.f)) + '</td>' +
      '<td title="' + esc(p.t) + '"><span class="trunc">' + esc(p.t) + '</span></td>' +
      '</tr>');
    shown++;
  }
  tbody.innerHTML = out.join('');
  cntEl.innerHTML = '显示 <b>' + shown + '</b> / ' + POSITIONS.length + ' 个职位';
}

qInput.addEventListener('input', renderTable);
yearSel.addEventListener('change', renderTable);

/* 专业要求列截断 */
var style = document.createElement('style');
style.textContent = '.trunc{display:inline-block;max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;vertical-align:bottom;color:#6C7076}';
document.head.appendChild(style);

/* ---------- 启动 ---------- */
renderTrend();
renderCity();
renderPrd();
renderSystem();
renderEdu();
renderFresh();
renderCo();
renderSub();
renderTable();

var charts = [];
['trendChart','cityChart','prdChart','systemChart','eduChart','freshChart','coChart','subChart'].forEach(function (id) {
  var inst = echarts.getInstanceByDom(document.getElementById(id));
  if (inst) { charts.push(inst); }
});
var rt = null;
window.addEventListener('resize', function () {
  if (rt) { clearTimeout(rt); }
  rt = setTimeout(function () {
    charts.forEach(function (c) { c.resize(); });
  }, 120);
});
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
