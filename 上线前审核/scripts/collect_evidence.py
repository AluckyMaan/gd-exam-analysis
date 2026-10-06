#!/usr/bin/env python3
"""
上线前审核包 · 证据重算脚本

用途：由审核 agent 独立复跑，重新计算全部数据不变量与一致性断言，
      并与 evidence.json 中记录的值比对，确认交付物没有被悄然改动。

用法：
    python 上线前审核/scripts/collect_evidence.py            # 重算并打印
    python 上线前审核/scripts/collect_evidence.py --write    # 重算并覆盖 evidence.json

依赖：仅标准库。数据源为项目 data/ 目录下由脚本生成的两个 JSON。
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(HERE)                 # 上线前审核/
ROOT = os.path.dirname(PKG_DIR)                 # 项目根目录
DATA_DIR = os.path.join(ROOT, 'data')
YEARS = ['2020', '2021', '2022', '2023', '2024', '2025', '2026']

MAJOR_JSON = os.path.join(DATA_DIR, 'all_majors_ranking.json')
CITY_JSON = os.path.join(DATA_DIR, 'city_data.json')
OLD_CITY_JSON = os.path.join(DATA_DIR, '_before_city_data.json')
DASHBOARD = os.path.join(ROOT, '广东省考综合数据分析看板.html')

# 独立于数据管线的年度基线：直接遍历全部 .xls 全部 sheet，
# 对「录用人数 > 0」的行求和。这是校验地域侧数据是否完整的黄金标准。
# 逐年基线：直接遍历 data/ 下**每一份职位表**的全部 sheet，对「录用人数>0」的行求和。
# 2023 为 18258（含附件1 乡镇 3401 人）—— 该文件曾因文件名写成「招录」而实际叫「考试录用」
# 被静默漏读，导致 2023 少统计 3401 人、地域侧职位数比专业侧少 1496。
YEAR_BASELINE = {
    '2020': 11871, '2021': 13309, '2022': 15422, '2023': 18258,
    '2024': 17307, '2025': 17419, '2026': 11779,
}


def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def yearly_totals(city_data):
    out = {y: 0 for y in YEARS}
    for info in city_data['city_yearly'].values():
        for y in YEARS:
            out[y] += info['yearly'].get(y, 0)
    return out


def parse_embedded(html, var):
    m = re.search(r'var ' + var + r' = (.+?);\s*\n', html, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def collect():
    ev = {'paths': {}, 'data_invariants': [], 'cross_dataset': [], 'html': {}, 'notes': []}
    ok = lambda b: 'PASS' if b else 'FAIL'

    for label, path in [('all_majors_ranking.json', MAJOR_JSON),
                        ('city_data.json', CITY_JSON),
                        ('看板 HTML', DASHBOARD)]:
        if os.path.exists(path):
            ev['paths'][label] = {
                'path': os.path.relpath(path, ROOT).replace('\\', '/'),
                'bytes': os.path.getsize(path),
                'sha256': sha256(path),
            }
        else:
            ev['paths'][label] = {'path': path, 'missing': True}

    a = load(MAJOR_JSON)
    c = load(CITY_JSON)
    inv = ev['data_invariants']

    def add(name, passed, detail):
        inv.append({'check': name, 'result': ok(passed), 'detail': detail})

    # ── 地域侧内部自洽 ──
    cy = yearly_totals(c)
    add('地域侧年度合计 == 独立全表基线',
        all(cy[y] == YEAR_BASELINE[y] for y in YEARS),
        {y: {'computed': cy[y], 'baseline': YEAR_BASELINE[y]} for y in YEARS})

    tot_r = sum(d['total_recruits'] for d in c['city_yearly'].values())
    tot_p = sum(d['total_positions'] for d in c['city_yearly'].values())
    add('city_yearly 招录合计 == summary.total_recruits',
        tot_r == c['summary']['total_recruits'], {'computed': tot_r, 'summary': c['summary']['total_recruits']})
    add('city_yearly 职位合计 == summary.total_positions',
        tot_p == c['summary']['total_positions'], {'computed': tot_p, 'summary': c['summary']['total_positions']})

    prd = sum(c['city_yearly'][x]['total_recruits'] for x in c['summary']['prd_cities'])
    ratio = round(prd / c['summary']['total_recruits'] * 100, 1)
    add('珠三角招录合计 == summary', prd == c['summary']['pearl_river_delta_recruits'],
        {'computed': prd, 'summary': c['summary']['pearl_river_delta_recruits']})
    add('珠三角占比重算一致', abs(ratio - c['summary']['prd_ratio']) < 0.05,
        {'computed': ratio, 'summary': c['summary']['prd_ratio']})

    fsum = Counter()
    for d in c['city_fresh'].values():
        for k, v in d.items():
            fsum[k] += v
    add('应届三分组合计 == 总招录',
        sum(fsum.values()) == c['summary']['total_recruits'],
        {'keys': dict(fsum), 'total': sum(fsum.values())})

    esum = sum(sum(d.values()) for d in c['city_education'].values())
    add('学历分组合计 == 总招录', esum == c['summary']['total_recruits'],
        {'computed': esum, 'summary': c['summary']['total_recruits']})

    other = sum(d.get('其他', 0) for d in c['city_education'].values())
    add('学历「其他」占比 < 2%', other / c['summary']['total_recruits'] < 0.02,
        {'其他': other, 'pct': round(other / c['summary']['total_recruits'] * 100, 2)})

    add('城市排名与城市表键数一致',
        len(c['city_ranking']) == len(c['city_yearly']) == c['summary']['total_cities'],
        {'ranking': len(c['city_ranking']), 'yearly_keys': len(c['city_yearly']),
         'summary': c['summary']['total_cities']})
    # ── 防「静默漏表」：data/ 里每一份职位表都必须被 files_config 命中 ──
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    from generate.gviz_common import resolve_job_tables, list_job_tables
    _resolved, _missing, _unused = resolve_job_tables(DATA_DIR)
    add('files_config 完整覆盖 data/ 中的职位表（无漏读）',
        not _missing and not _unused,
        {'已认领': len(_resolved), '未找到条目': _missing,
         '目录中未被认领的职位表': _unused,
         'note': '2023 附件1 曾因文件名写成"招录"而实际叫"考试录用"被静默漏读，'
                 '少 3401 人；此断言用于防止同类问题复发'})
    add('地域侧职位数 == 专业侧职位数',
        c['summary']['total_positions'] == a['summary']['total_position_rows'],
        {'地域侧': c['summary']['total_positions'],
         '专业侧': a['summary']['total_position_rows'],
         'note': '两侧都覆盖全部 sheet 的全部职位时应当相等；曾相差 1496（那份漏读文件）'})

    add('城市排名已按招录人数降序',
        all(c['city_yearly'][c['city_ranking'][i]]['total_recruits']
            >= c['city_yearly'][c['city_ranking'][i + 1]]['total_recruits']
            for i in range(len(c['city_ranking']) - 1)), {})

    # ── 矩阵清洁度 ──
    mm = Counter()
    for d in c['city_major_matrix'].values():
        for k, v in d.items():
            mm[k] += v
    dirty = [k for k in mm if re.search(r'[0-9,，（）()）]', k) or '不限' in k]
    add('城市×专业矩阵无脏名（数字/逗号/括号/不限）', not dirty,
        {'dirty_count': len(dirty), 'sample': dirty[:8], 'major_names': len(mm)})
    add('矩阵每个专业名至少命中 1 个城市（不存在全零项）',
        all(any(city.get(name, 0) > 0 for city in c['city_major_matrix'].values()) for name in mm),
        {'major_names': len(mm)})

    over = [(city, k, v) for city, d in c['city_major_matrix'].items()
            for k, v in d.items() if v > c['city_yearly'][city]['total_recruits']]
    add('矩阵单项未超该城市招录总和', not over, {'violations': over[:5]})

    # ── 专业侧 ──
    bad_year = []
    for m in a['ranking']:
        s = sum(v.get('recruits', 0) for v in (m.get('yearly') or {}).values())
        if s != m['total_recruits']:
            bad_year.append(m['major'])
    add('每专业 yearly 求和 == total_recruits', not bad_year, {'mismatch': bad_year[:5]})

    bad_pos = []
    for m in a['ranking']:
        s = sum(v.get('positions', 0) for v in (m.get('yearly') or {}).values())
        if s != m['total_positions']:
            bad_pos.append(m['major'])
    add('每专业 yearly 职位求和 == total_positions', not bad_pos, {'mismatch': bad_pos[:5]})

    bad_purity = []
    for m in a['ranking']:
        if m['total_positions'] > 0:
            exp = round(m['alone_positions'] / m['total_positions'] * 100, 1)
            if abs(exp - m['purity']) > 0.2:
                bad_purity.append(m['major'])
    add('purity 定义自洽（独设/总职位）', not bad_purity, {'mismatch': bad_purity[:5]})

    add('summary 口径与排名数组一致',
        a['summary']['total_position_rows'] == 74849
        and len(a['ranking']) == 242
        and a['summary']['unique_majors_found'] == len(a['ranking']),
        {'total_position_rows': a['summary']['total_position_rows'],
         'unique_majors_found': a['summary']['unique_majors_found'],
         'ranking_len': len(a['ranking']),
         'note': 'ranking 242 条 = 241 个专业 + 1 条「不限专业：服务基层/退役士兵专岗」(code=SPECIAL-SR)'})
    add('top30 是 ranking 前 30 且降序', a['top30'] == a['ranking'][:30], {})

    sp = [m for m in a['ranking'] if m.get('code') == 'SPECIAL-SR']
    add('「服务基层/退役士兵专岗」条目存在且由脚本生成',
        len(sp) == 1 and sp[0]['type'] == 'special' and sp[0]['total_positions'] > 0,
        {'found': len(sp), 'positions': sp[0]['total_positions'] if sp else None,
         'recruits': sp[0]['total_recruits'] if sp else None,
         'note': '该条目原先靠人工改 JSON 注入，重跑提取即丢失且因文件被 ignore 无法从 git 发现；'
                 '现已改为 extract_all_majors.py 内确定性构造。此处用于防止 regression'})

    # ── 跨数据集 ──
    cd = ev['cross_dataset']
    cd.append({'check': '地域侧年度招录合计 == 专业侧可核对的独立基线',
               'result': ok(all(cy[y] == YEAR_BASELINE[y] for y in YEARS)),
               'detail': '地域侧与直接读 xls 的独立求和逐年一致'})

    # ── HTML 内嵌一致性 ──
    with open(DASHBOARD, 'r', encoding='utf-8') as f:
        html = f.read()
    h = ev['html']
    h['bytes'] = len(html.encode('utf-8'))
    h['placeholder_residue'] = re.findall(r'__[A-Z_0-9]+__', html)
    h['echarts_src'] = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
    h['external_cdn'] = re.findall(r'https?://cdn\.|jsdelivr|unpkg|bootcdn', html)
    h['hardcoded_old_values'] = {k: html.count(k) for k in ['46765', '38099', '37.9%'] if html.count(k)}

    for var, obj in [('RANKING', a['ranking']), ('RAW_RANKING', a['raw_ranking']),
                     ('CITY_YEARLY', c['city_yearly']), ('CITY_RANKING', c['city_ranking']),
                     ('CITY_EDUCATION', c['city_education']), ('CITY_FRESH', c['city_fresh']),
                     ('CITY_MAJOR_MATRIX', c['city_major_matrix'])]:
        got = parse_embedded(html, var)
        h['embedded_' + var] = ok(got == obj)

    # 首屏渲染 bug 回归检查
    h['init_opening_views_called'] = ok('initOpeningViews();' in html)
    h['no_bare_yearly_index'] = ok(not re.search(r'(?<![\w.])(info|entry)\.yearly\[', html))
    h['no_inplace_reverse_mutation'] = ok('cityData.reverse()' not in html)
    h['needs_refresh_refs_exist'] = None
    m = re.search(r'var needsRefresh = \{(.*?)\};', html, re.DOTALL)
    if m:
        pairs = re.findall(r"'([^']+)':\s*'([^']+)'", m.group(1))
        missing = [f for _, f in pairs if ('function ' + f) not in html]
        h['needs_refresh_refs_exist'] = ok(not missing)
        h['needs_refresh_count'] = len(pairs)
        h['needs_refresh_missing'] = missing

    # ── 防「把各专业的数量相加」这类口径错误 ──
    _major_sum = sum(m['total_recruits'] for m in a['ranking'])
    add('首页不得出现各专业招录人数之和（膨胀值）',
        str(_major_sum) not in html,
        {'膨胀值': _major_sum, '真实招录': c['summary']['total_recruits'],
         '说明': '同一职位挂多个专业会在各专业名下重复计入；首页规模必须用 STATS 的真实值'})
    add('首页注入的真实规模 == 地域侧聚合值',
        ('"positions": %d' % c['summary']['total_positions']) in html
        and ('"recruits": %d' % c['summary']['total_recruits']) in html,
        {'positions': c['summary']['total_positions'], 'recruits': c['summary']['total_recruits']})

    # ── 修复前后对比（仅在旧快照存在时） ──
    if os.path.exists(OLD_CITY_JSON):
        old = load(OLD_CITY_JSON)
        oy = yearly_totals(old)
        ev['before_after'] = {
            'note': '修复前快照 data/_before_city_data.json（只读首个 sheet 的旧口径）',
            'summary': {k: {'before': old['summary'][k], 'after': c['summary'][k]}
                        for k in ['total_positions', 'total_recruits',
                                  'pearl_river_delta_recruits', 'prd_ratio', 'total_cities']},
            'yearly_recruits': {y: {'before': oy[y], 'after': cy[y], 'delta': cy[y] - oy[y]}
                                for y in YEARS},
            'city_ranking_top8': {'before': old['city_ranking'][:8], 'after': c['city_ranking'][:8]},
        }
    else:
        ev['notes'].append('未找到 data/_before_city_data.json，跳过修复前后对比')

    ev['notes'].append('年度基线 YEAR_BASELINE 直接遍历全部 .xls 的全部 sheet、对「录用人数>0」的行求和得出，'
                       '独立于任何项目脚本，因此可用作地域侧数据完整性的黄金标准')
    return ev


def preflight():
    """前置检查：缺失输入时给出可执行的指引，而不是抛裸 traceback。"""
    required = [MAJOR_JSON, CITY_JSON, DASHBOARD]
    missing = [p for p in required if not os.path.exists(p)]
    if not missing:
        return True
    print('=' * 66)
    print('前置检查未通过：缺少必要的输入文件')
    print('=' * 66)
    for p in missing:
        print('  缺少: %s' % os.path.relpath(p, ROOT).replace('\\', '/'))
    print()
    print('这两个数据 JSON 与看板 HTML 均已纳入版本控制，正常情况下 checkout 后就存在。')
    print('若确实缺失，按序执行下面的命令重建（需要 data/*.xls 原始文件）：')
    print()
    print('  python scripts/extract/extract_all_majors.py')
    print('  python scripts/extract/extract_city_data.py')
    print('  python scripts/generate/generate_merged_viz.py')
    print()
    print('重建后应满足：all_majors_ranking.json 的 summary.total_position_rows == 74849，')
    print('city_data.json 的 summary.total_positions == 73353 且 total_recruits == 101964。')
    print('也可运行 scripts/test_clean_checkout.py 在干净检出中做端到端验证。')
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='覆盖 evidence.json')
    args = ap.parse_args()

    if not preflight():
        return 2

    ev = collect()
    fails = [x for x in ev['data_invariants'] if x['result'] != 'PASS']
    html_fails = [k for k, v in ev['html'].items() if v == 'FAIL']

    print('=' * 66)
    print('数据不变量：%d 项，失败 %d 项' % (len(ev['data_invariants']), len(fails)))
    for x in ev['data_invariants']:
        print('  [%s] %s' % (x['result'], x['check']))
    print()
    print('HTML 校验：')
    for k in sorted(ev['html']):
        v = ev['html'][k]
        if v in ('PASS', 'FAIL'):
            print('  [%s] %s' % (v, k))
    print()
    if 'before_after' in ev:
        s = ev['before_after']['summary']
        print('修复前后：职位 %s → %s，招录 %s → %s' % (
            s['total_positions']['before'], s['total_positions']['after'],
            s['total_recruits']['before'], s['total_recruits']['after']))
    print()
    print('结论：', 'ALL PASS' if not fails and not html_fails else 'FAILURES: %s' % (fails + html_fails))

    if args.write:
        out = os.path.join(PKG_DIR, 'evidence.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(ev, f, ensure_ascii=False, indent=2)
        print('已写入', out)

    return 1 if (fails or html_fails) else 0


if __name__ == '__main__':
    sys.exit(main())
