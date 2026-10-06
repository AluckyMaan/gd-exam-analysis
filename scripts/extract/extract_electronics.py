"""
电子信息类及相关专业招录数据提取脚本。
依据《广东省2026年考试录用公务员专业参考目录》B0807 电子信息类 + A0809/A0810/A0840 研究生层次。
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gviz_common import *

# ===== 专业关键词列表 =====
ELECTRONICS_KEYWORDS = [
    # B0807 电子信息类（本科核心）
    '电子信息类', 'B0807',
    '电子信息工程', 'B080701',
    '电子科学与技术', 'B080702',
    '通信工程', 'B080703',
    '微电子科学与工程', 'B080704',
    '光电信息科学与工程', 'B080705',
    '信息工程', 'B080706',
    '广播电视工程', 'B080707',
    '水声工程', 'B080708',
    '电子封装技术', 'B080709',
    '集成电路设计与集成系统', 'B080710',
    '医学信息工程', 'B080711',
    '电磁场与无线技术', 'B080712',
    '电波传播与天线', 'B080713',
    '电子信息科学与技术', 'B080714',
    '电信工程及管理', 'B080715',
    '应用电子技术教育', 'B080716',
    '人工智能', 'B080717',
    '海洋信息工程', 'B080718',
    '柔性电子学', 'B080719',
    '智能测控工程', 'B080720',
    # A0809 电子科学与技术（研究生）
    '电子科学与技术', 'A0809',
    '物理电子学', 'A080901',
    '电路与系统', 'A080902',
    '微电子学与固体电子学', 'A080903',
    '电磁场与微波技术', 'A080904',
    # A0810 信息与通信工程（研究生）
    '信息与通信工程', 'A0810',
    '通信与信息系统', 'A081001',
    '信号与信息处理', 'A081002',
    # A0840 电子信息（专业硕士）
    '电子信息', 'A0840',
    '新一代电子信息技术', 'A084001',
    '通信工程硕士', 'A084002', '集成电路工程', 'A084003',
    '光电信息工程', 'A084008',
    '人工智能硕士', 'A084010',
    # C0811 电子信息类（大专）
    '电子信息类', 'C0811',
    '电子信息工程技术', 'C081101',
    '应用电子技术', 'C081102',
    '微电子技术', 'C081103',
    '智能产品开发', 'C081104',
    # 通用/大类
    '电子信息',
    '电子工程',
    '电子技术',
    '应用电子',
    '微电子',
    '光电信息',
]


def matches_electronics(text):
    if not text or text.strip() == '':
        return False
    for kw in ELECTRONICS_KEYWORDS:
        if kw in text:
            return True
    return False


def extract_sheet_data(sheet, header_row):
    """提取单 sheet 中符合电子信息工程关键词的职位数据"""
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
    data_start = header_row + 1

    for r in range(data_start, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
        if not any(row):
            continue
        first_cell = row[0] if len(row) > 0 else ''
        if any(kw in first_cell for kw in ['附件', '职位表', '报考', '配套']):
            continue

        prof_texts = collect_prof_field_texts(row, prof_cols)
        if not any(matches_electronics(pt) for pt in prof_texts):
            continue

        recruit = safe_int(row[recruit_col]) if recruit_col < len(row) else 0

        fresh_only = False
        fresh_type = 'social'
        if fresh_col is not None and fresh_col < len(row):
            fv = row[fresh_col]
            fresh_only = (fv == '是') or ('应届' in fv)
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


# ====== 主流程 ======
base_dir = 'c:/Users/YANG/Desktop/广东20-26年广东省考职位表'
all_records = []
yearly_data = {}

for year, fpath in files_config(base_dir):
    if not os.path.exists(fpath):
        print(f'  文件不存在: {os.path.basename(fpath)}')
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
                'fresh_records': 0, 'fresh_recruits': 0,
                'fresh_current_recruits': 0, 'sheets': {},
            }

        yd = yearly_data[year]
        if sheet_name not in yd['sheets']:
            yd['sheets'][sheet_name] = {'records': 0, 'recruits': 0}

        yd['total_records'] += len(records)
        yd['total_recruits'] += sum(r['recruits'] for r in records)
        yd['sheets'][sheet_name]['records'] += len(records)
        yd['sheets'][sheet_name]['recruits'] += sum(r['recruits'] for r in records)

        fresh_recs = [r for r in records if r['fresh_only']]
        yd['fresh_records'] += len(fresh_recs)
        yd['fresh_recruits'] += sum(r['recruits'] for r in fresh_recs)
        yd['fresh_current_recruits'] += sum(r['recruits'] for r in records if r['fresh_type'] == 'fresh_current')

        for r in records:
            all_records.append({'year': year, 'sheet': sheet_name, **r})

    print(f'{year}: {yd["total_records"]} pos, {yd["total_recruits"]} recruits')

# === 汇总输出 ===
city_summary = {}
edu_summary = {}
fresh_summary = {'social': {}, 'fresh_any': {}, 'fresh_current': {}}

for rec in all_records:
    city = rec.get('city', '') or '其他'
    yr = rec['year']
    city_summary.setdefault(city, {})
    city_summary[city][yr] = city_summary[city].get(yr, 0) + rec['recruits']

    edu = rec.get('education', '') or '其他'
    edu_summary.setdefault(edu, {})
    edu_summary[edu][yr] = edu_summary[edu].get(yr, 0) + rec['recruits']

    ft = rec.get('fresh_type', 'social')
    fresh_summary[ft][yr] = fresh_summary[ft].get(yr, 0) + rec['recruits']

yearly_summary = {}
for yr in sorted(yearly_data.keys()):
    d = yearly_data[yr]
    yearly_summary[yr] = {
        'year': yr,
        'total_records': d['total_records'],
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

outpath = f'{base_dir}/electronics_data.json'
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n数据已保存到 electronics_data.json（共 {len(all_records)} 条记录）')
