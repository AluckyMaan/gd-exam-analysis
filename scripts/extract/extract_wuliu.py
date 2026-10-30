#!/usr/bin/env python3
"""
「物流管理与工程类（B1206）」招录数据提取脚本
--------------------------------------------------
从 data/*.xls 省级职位表中筛出专业要求含「物流」的职位，输出
data/wuliu_data.json，供 generate_wuliu_html.py 生成分析报告。

口径与 extract_all_majors.py 保持一致：
  * 2020-2023 每年两份附件（附件1 乡镇 + 附件2 县以上及珠三角乡镇）都要读；
  * 省直单位按单位名归一化（广东省 + 厅/局/委/办 → 省直）；
  * 应届分类沿用 gviz_common.get_fresh_type；
  * 专业匹配为「专业列文本包含 物流」，因此同时覆盖
    物流管理与工程类（B1206）、物流管理（B120601）、物流工程（B120602）、
    物流类（C1209）等写法，同一职位只计一次。

项目根目录由 __file__ 推导，不写死绝对路径。
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict

import xlrd

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from generate.gviz_common import (  # noqa: E402
    build_col_map,
    collect_prof_field_texts,
    files_config,
    find_col_in_map,
    find_header_row,
    get_fresh_type,
    safe_int,
    standardize_city,
    CITY_COL_NAMES,
    EDU_COL_NAMES,
    FRESH_COL_NAMES,
    POS_CODE_COL_NAMES,
    POS_COL_NAMES,
    PROF_COL_NAMES,
    RECRUIT_COL_NAMES,
    UNIT_COL_NAMES,
)

# 物流管理与工程类（B1206）下辖：物流管理 B120601、物流工程 B120602、
# 供应链管理 B120603、采购管理 B120604；另含专科物流类 C1209。
# 注意：'政府采购管理' 含子串『采购管理』，必须排除；'…硕士/博士』为研究生层次，
# 不属于本科专业类 B1206，与 extract_all_majors.py 的口径一致，予以排除。
MATCH_PATTERNS = [
    ('物流管理与工程类', 'B1206', '专业类', r'物流管理与工程类'),
    ('物流管理', 'B120601', '具体专业', r'物流管理(?!与工程类)'),
    ('物流工程', 'B120602', '具体专业', r'物流工程'),
    ('供应链管理', 'B120603', '具体专业', r'供应链管理'),
    ('采购管理', 'B120604', '具体专业', r'(?<!政府)采购管理'),
]

# 专科层次「物流类（C1209）」不属于本科专业类 B1206，单独计数、不计入主口径。
C1209_PATTERN = r'(?<!政府)物流类'
C1209_ONLY = {'positions': 0, 'recruits': 0}

MASTER_TAIL = ('硕士', '博士')


# 职位表 sheet → 招录系统
SYSTEM_MAP = {
    '县以上机关': '县以上机关',
    '审计': '审计',
    '公安': '公安',
    '法院': '法院',
    '检察院': '检察院',
    '监狱戒毒': '监狱戒毒',
    '珠三角乡镇': '乡镇机关',
    '乡镇机关': '乡镇机关',
    '优秀本科以上毕业生': '乡镇机关',
    '本市大专以上': '乡镇机关',
    '本县大专以上': '乡镇机关',
    '大专以上': '乡镇机关',
    '专项人员': '乡镇机关',
}

def has_nonmaster(text, pattern):
    """pattern 命中且其后 6 字内不是『硕士/博士』（研究生层次不算 B1206 本科专业类）"""
    for m in re.finditer(pattern, text):
        if not any(t in text[m.end():m.end() + 6] for t in MASTER_TAIL):
            return True
    return False


def detect_subs(text):
    """返回该专业文本命中的本科/专科专业名（'类'与'具体专业'可同时出现）"""
    return [name for name, _, _, pat in MATCH_PATTERNS if has_nonmaster(text, pat)]


def extract_sheet(sheet, year):
    """返回 (matched_records, all_records_count, all_recruits)"""
    header_row = find_header_row(sheet)
    if header_row is None:
        return [], 0, 0, {'positions': 0, 'recruits': 0}

    col_map = build_col_map(sheet, header_row)
    recruit_col = find_col_in_map(col_map, RECRUIT_COL_NAMES)
    prof_cols = [col_map[n] for n in PROF_COL_NAMES if n in col_map]
    unit_col = find_col_in_map(col_map, UNIT_COL_NAMES)
    if recruit_col is None or unit_col is None:
        return [], 0, 0, {'positions': 0, 'recruits': 0}

    fresh_col = find_col_in_map(col_map, FRESH_COL_NAMES)
    edu_col = find_col_in_map(col_map, EDU_COL_NAMES)
    city_col = find_col_in_map(col_map, CITY_COL_NAMES)
    pos_col = find_col_in_map(col_map, POS_COL_NAMES)
    code_col = find_col_in_map(col_map, POS_CODE_COL_NAMES)

    matched = []
    total_rows = 0
    total_recruits = 0
    c1209 = {'positions': 0, 'recruits': 0}
    system = SYSTEM_MAP.get(sheet.name, sheet.name)

    for r in range(header_row + 1, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
        if not any(row):
            continue
        first = row[0] if row else ''
        if any(kw in first for kw in ('附件', '职位表', '报考', '配套', '说明')):
            continue

        recruits = safe_int(row[recruit_col]) if recruit_col < len(row) else 0
        total_rows += 1
        total_recruits += recruits

        prof_texts = collect_prof_field_texts(row, prof_cols)
        prof_joined = ' ; '.join(t for t in prof_texts if t)
        subs = detect_subs(prof_joined)
        if not subs:
            if has_nonmaster(prof_joined, C1209_PATTERN):
                c1209['positions'] += 1
                c1209['recruits'] += recruits
            continue

        unit = row[unit_col] if unit_col < len(row) else ''
        city = row[city_col] if city_col is not None and city_col < len(row) else ''
        education = row[edu_col] if edu_col is not None and edu_col < len(row) else ''
        fv = row[fresh_col] if fresh_col is not None and fresh_col < len(row) else ''
        position = row[pos_col] if pos_col is not None and pos_col < len(row) else ''
        pos_code = row[code_col] if code_col is not None and code_col < len(row) else ''

        matched.append({
            'year': year,
            'system': system,
            'sheet': sheet.name,
            'unit': unit,
            'position': position,
            'position_code': pos_code,
            'city': standardize_city(unit, city),
            'education': education or '未注明',
            'fresh_raw': fv,
            'fresh_type': get_fresh_type(fv),
            'recruits': recruits,
            'prof': prof_joined,
            'subs': subs,
        })

    return matched, total_rows, total_recruits, c1209


def pct(a, b):
    return round(a / b * 100, 1) if b else 0.0


def main():
    files = files_config(os.path.join(BASE_DIR, 'data'))
    print(f'找到 {len(files)} 个职位表文件')

    records = []
    province_yearly = {}
    c1209_total = {'positions': 0, 'recruits': 0}
    for year, fpath in files:
        wb = xlrd.open_workbook(fpath)
        y_rows = y_recruits = 0
        for si in range(wb.nsheets):
            sheet = wb.sheet_by_index(si)
            got, rows, recruits, extra = extract_sheet(sheet, year)
            c1209_total['positions'] += extra['positions']
            c1209_total['recruits'] += extra['recruits']
            y_rows += rows
            y_recruits += recruits
            records.extend(got)
        if year not in province_yearly:
            province_yearly[year] = {'positions': 0, 'recruits': 0}
        province_yearly[year]['positions'] += y_rows
        province_yearly[year]['recruits'] += y_recruits
        print(f'  {year}: 本文件 {y_rows} 职位 / {y_recruits} 人；'
              f'累计物流命中 {sum(1 for r in records if r["year"] == year)} 条')

    print(f'\n共命中 {len(records)} 条职位记录')

    yearly = defaultdict(lambda: {'positions': 0, 'recruits': 0, 'fresh_recruits': 0,
                                  'social_recruits': 0, 'fresh_current_recruits': 0})
    city = defaultdict(lambda: {'positions': 0, 'recruits': 0})
    edu = Counter()
    edu_recruits = Counter()
    system = defaultdict(lambda: {'positions': 0, 'recruits': 0})
    fresh = defaultdict(int)
    unit_stats = defaultdict(lambda: {'positions': 0, 'recruits': 0, 'city': '', 'system': ''})
    sub_stats = defaultdict(lambda: {'positions': 0, 'recruits': 0, 'type': '',
                                     'code': '', 'yearly': defaultdict(int)})
    sub_by_year = defaultdict(lambda: defaultdict(int))
    unit_yearly = defaultdict(lambda: defaultdict(int))

    for rec in records:
        y = rec['year']
        n = rec['recruits']
        dy = yearly[y]
        dy['positions'] += 1
        dy['recruits'] += n
        if rec['fresh_type'] == 'social':
            dy['social_recruits'] += n
        else:
            dy['fresh_recruits'] += n
        if rec['fresh_type'] == 'fresh_current':
            dy['fresh_current_recruits'] += n

        city[rec['city']]['positions'] += 1
        city[rec['city']]['recruits'] += n

        edu[rec['education']] += 1
        edu_recruits[rec['education']] += n

        system[rec['system']]['positions'] += 1
        system[rec['system']]['recruits'] += n

        fresh[rec['fresh_type']] += n

        u = unit_stats[rec['unit']]
        u['positions'] += 1
        u['recruits'] += n
        u['city'] = rec['city']
        u['system'] = rec['system']
        unit_yearly[rec['unit']][y] += n

        for name in rec['subs']:
            info = next(s for s in MATCH_PATTERNS if s[0] == name)
            st = sub_stats[name]
            st['positions'] += 1
            st['recruits'] += n
            st['type'] = info[2]
            st['code'] = info[1]
            sub_by_year[name][y] += n

    total_recruits = sum(r['recruits'] for r in records)
    total_positions = len(records)

    # ---- 与权威产物交叉校验 ----
    ref_path = os.path.join(BASE_DIR, 'data', 'all_majors_ranking.json')
    ref = None
    if os.path.exists(ref_path):
        ref_data = json.load(open(ref_path, encoding='utf-8'))
        ref = next((m for m in ref_data['ranking'] if m['major'] == '物流管理与工程类'), None)

    # 共现专业（取自权威产物，其专业名解析比本脚本的字符串匹配更准确）
    cooccurrence = ref['top_co_occurrences'] if ref else []

    # 按年排序
    years = sorted(yearly)
    yearly_out = []
    for y in years:
        dy = yearly[y]
        prov = province_yearly.get(y, {'recruits': 0, 'positions': 0})
        yearly_out.append({
            'year': y,
            'positions': dy['positions'],
            'recruits': dy['recruits'],
            'fresh_recruits': dy['fresh_recruits'],
            'social_recruits': dy['social_recruits'],
            'fresh_current_recruits': dy['fresh_current_recruits'],
            'province_positions': prov['positions'],
            'province_recruits': prov['recruits'],
            'share_recruits': pct(dy['recruits'], prov['recruits']),
            'share_positions': pct(dy['positions'], prov['positions']),
        })

    city_out = sorted(
        ({'city': k, **v} for k, v in city.items()),
        key=lambda x: (-x['recruits'], -x['positions']),
    )
    prd = {'广州', '深圳', '珠海', '佛山', '东莞', '中山', '惠州', '江门', '肇庆'}
    prd_recruits = sum(c['recruits'] for c in city_out if c['city'] in prd)
    nonprd_recruits = total_recruits - prd_recruits

    edu_out = sorted(
        ({'edu': k, 'positions': v, 'recruits': edu_recruits[k]} for k, v in edu.items()),
        key=lambda x: -x['positions'],
    )
    system_out = sorted(
        ({'system': k, **v} for k, v in system.items()),
        key=lambda x: -x['recruits'],
    )
    units_out = sorted(
        ({'unit': k, **v, 'yearly': dict(unit_yearly[k])} for k, v in unit_stats.items()),
        key=lambda x: (-x['recruits'], -x['positions']),
    )
    subs_out = sorted(
        ({'name': k, 'code': v['code'], 'type': v['type'],
          'positions': v['positions'], 'recruits': v['recruits'],
          'yearly': {str(yy): nn for yy, nn in sorted(sub_by_year[k].items())}}
         for k, v in sub_stats.items()),
        key=lambda x: -x['positions'],
    )

    positions_out = sorted(
        records,
        key=lambda r: (-r['recruits'], r['year'], r['city'], r['unit']),
    )

    out = {
        'meta': {
            'major': '物流管理与工程类',
            'code': 'B1206',
            'scope': '广东省考试录用公务员（省考）统一招考职位表，2020-2026',
            'keyword': '物流管理与工程类（B1206）及其下辖专业',
            'c1209_only': c1209_total,
            'source_files': len(files),
            'total_position_rows': sum(v['positions'] for v in province_yearly.values()),
            'note': '同一职位可能同时列出多个专业，专业侧数值不可跨专业相加。',
        },
        'summary': {
            'total_recruits': total_recruits,
            'total_positions': total_positions,
            'avg_recruits_per_pos': round(total_recruits / total_positions, 1) if total_positions else 0,
            'city_coverage': len(city_out),
            'fresh_ratio': pct(fresh.get('fresh_current', 0) + fresh.get('fresh_any', 0), total_recruits),
            'prd_recruits': prd_recruits,
            'prd_ratio': pct(prd_recruits, total_recruits),
            'non_prd_recruits': nonprd_recruits,
            'rank_in_all_majors': ref['rank'] if ref else None,
            'all_majors_count': len(ref_data['ranking']) if ref else None,
            'purity': ref['purity'] if ref else None,
            'competition_index': ref['competition_index'] if ref else None,
            'growth_rate': ref['growth_rate'] if ref else None,
            'province_total_recruits': sum(v['recruits'] for v in province_yearly.values()),
            'province_total_positions': sum(v['positions'] for v in province_yearly.values()),
            'share_recruits_all': pct(total_recruits, sum(v['recruits'] for v in province_yearly.values())),
        },
        'yearly': yearly_out,
        'city': city_out,
        'education': edu_out,
        'system': system_out,
        'fresh': {
            'fresh_current': fresh.get('fresh_current', 0),
            'fresh_any': fresh.get('fresh_any', 0),
            'social': fresh.get('social', 0),
        },
        'units': units_out,
        'positions': positions_out,
        'submajors': subs_out,
        'cooccurrence': cooccurrence,
    }

    out_path = os.path.join(BASE_DIR, 'data', 'wuliu_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f'\n数据已保存: {out_path}')
    print(f'合计 {total_recruits} 人 / {total_positions} 个职位 / {len(city_out)} 个城市')
    if ref:
        ok = (ref['total_recruits'] == total_recruits and ref['total_positions'] == total_positions)
        print(f'交叉校验: 权威产物 {ref["total_recruits"]} 人 / {ref["total_positions"]} 职位 -> '
              f'{"一致" if ok else "不一致（请检查匹配口径）"}')
    print('\n逐年：')
    for item in yearly_out:
        print(f'  {item["year"]}: {item["recruits"]:>4} 人 / {item["positions"]:>3} 职位 '
              f'(占全省 {item["share_recruits"]}%)')


if __name__ == '__main__':
    main()
