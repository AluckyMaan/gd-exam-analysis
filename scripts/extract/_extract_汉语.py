"""
汉语言相关专业招录数据提取脚本（由 make_viz.py 自动生成）
"""
import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from generate.gviz_common import *

KEYWORDS = [
    '汉语言文学',
    '汉语言',
    '汉语国际教育',
    '中国语言文学',
    '中国语言文学类',
    'B0501',
    '秘书学',
    '应用语言学',
    '古典文献学',
    '中国语言与文化',
]

def matches(text):
    if not text or text.strip() == '':
        return False
    for kw in KEYWORDS:
        if kw in text:
            return True
    return False

def extract_sheet_data(sheet, header_row):
    if header_row is None:
        return []
    col_map = build_col_map(sheet, header_row)
    recruit_col = find_col_in_map(col_map, RECRUIT_COL_NAMES)
    prof_cols = [col_map[n] for n in PROF_COL_NAMES if n in col_map]
    fresh_col = find_col_in_map(col_map, FRESH_COL_NAMES)
    edu_col = find_col_in_map(col_map, EDU_COL_NAMES)
    city_col = find_col_in_map(col_map, CITY_COL_NAMES)
    unit_col = find_col_in_map(col_map, UNIT_COL_NAMES)
    pos_col = find_col_in_map(col_map, POS_COL_NAMES)
    pos_code_col = find_col_in_map(col_map, POS_CODE_COL_NAMES)
    if not all([recruit_col is not None, prof_cols, unit_col is not None]):
        return []
    records = []
    for r in range(header_row + 1, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
        if not any(row):
            continue
        first_cell = row[0] if len(row) > 0 else ''
        if any(kw in first_cell for kw in ['附件', '职位表', '报考', '配套']):
            continue
        prof_texts = collect_prof_field_texts(row, prof_cols)
        if not any(matches(pt) for pt in prof_texts):
            continue
        recruit = safe_int(row[recruit_col]) if recruit_col < len(row) else 0
        fresh_only = False
        fresh_type = 'social'
        if fresh_col is not None and fresh_col < len(row):
            fv = row[fresh_col]
            fresh_only = (fv == '是') or ('\u5e94\u5c4a' in fv) or ('\u5c4a' in fv and '\u6bd5\u4e1a\u751f' in fv)
            fresh_type = get_fresh_type(fv)
        city = row[city_col] if city_col is not None and city_col < len(row) else ''
        unit = row[unit_col] if unit_col < len(row) else ''
        position = row[pos_col] if pos_col is not None and pos_col < len(row) else ''
        pos_code = row[pos_code_col] if pos_code_col is not None and pos_code_col < len(row) else ''
        education = row[edu_col] if edu_col is not None and edu_col < len(row) else ''
        city = standardize_city(unit, city)
        records.append({
            'unit': unit, 'position': position, 'position_code': pos_code,
            'recruits': recruit, 'city': city, 'education': education,
            'fresh_only': fresh_only, 'fresh_type': fresh_type,
            'prof_fields': '; '.join(prof_texts),
        })
    return records

base_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'data')
all_records = []
yearly_data = {}

for year, fpath in files_config(base_dir):
    if not os.path.exists(fpath):
        continue
    wb = xlrd.open_workbook(fpath)
    for sheet_idx in range(wb.nsheets):
        sheet = wb.sheet_by_index(sheet_idx)
        sheet_name = sheet.name
        header_row = find_header_row(sheet)
        if header_row is None:
            continue
        records = extract_sheet_data(sheet, header_row)
        if not records:
            continue
        if year not in yearly_data:
            yearly_data[year] = {
                'year': year, 'total_records': 0, 'total_recruits': 0,
                'fresh_records': 0, 'fresh_recruits': 0, 'fresh_current_recruits': 0,
            }
        yd = yearly_data[year]
        yd['total_records'] += len(records)
        yd['total_recruits'] += sum(r['recruits'] for r in records)
        fresh_recs = [r for r in records if r['fresh_only']]
        yd['fresh_records'] += len(fresh_recs)
        yd['fresh_recruits'] += sum(r['recruits'] for r in fresh_recs)
        yd['fresh_current_recruits'] += sum(r['recruits'] for r in records if r['fresh_type'] == 'fresh_current')
        for r in records:
            all_records.append({'year': year, 'sheet': sheet_name, **r})

city_summary = {}
edu_summary = {}
fresh_summary = {'social': {}, 'fresh_any': {}, 'fresh_current': {}}
for rec in all_records:
    city = rec.get('city', '') or '\u5176\u4ed6'
    yr = rec['year']
    city_summary.setdefault(city, {})
    city_summary[city][yr] = city_summary[city].get(yr, 0) + rec['recruits']
    edu = rec.get('education', '') or '\u5176\u4ed6'
    edu_summary.setdefault(edu, {})
    edu_summary[edu][yr] = edu_summary[edu].get(yr, 0) + rec['recruits']
    ft = rec.get('fresh_type', 'social')
    fresh_summary[ft][yr] = fresh_summary[ft].get(yr, 0) + rec['recruits']

yearly_summary = {}
for yr in sorted(yearly_data.keys()):
    d = yearly_data[yr]
    yearly_summary[yr] = {
        'year': yr, 'total_records': d['total_records'],
        'total_recruits': d['total_recruits'],
        'fresh_records': d['fresh_records'],
        'fresh_recruits': d['fresh_recruits'],
        'fresh_current_recruits': d['fresh_current_recruits'],
        'avg_per_position': round(d['total_recruits'] / d['total_records'], 1) if d['total_records'] > 0 else 0,
    }

output = {
    'yearly_summary': yearly_summary,
    'city_summary': city_summary,
    'edu_summary': edu_summary,
    'fresh_summary': fresh_summary,
    'details': all_records,
}

outpath = os.path.join(os.path.dirname(base_dir), 'data', '汉语_data.json')
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n\u6570\u636e\u5df2\u4fdd\u5b58\u5230 {outpath}（\u5171 {len(all_records)} \u6761\u8bb0\u5f55）')
