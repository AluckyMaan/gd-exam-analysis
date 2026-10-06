"""
海洋工程类及相关专业招录数据提取脚本。
依赖 gviz_common 公共模块。
"""
import json
import os
from gviz_common import *

# ===== 专业关键词列表 =====
OCEAN_KEYWORDS = [
    # B0820 海洋工程类（本科核心）
    '海洋工程类', 'B0820',
    '船舶与海洋工程', 'B082001',
    '海洋工程与技术', 'B082002',
    '海洋资源开发技术', 'B082003',
    '海洋机器人', 'B082004',
    '智慧海洋技术', 'B082005',
    # A0824 船舶与海洋工程（研究生）
    '船舶与海洋结构物设计制造', 'A082401',
    '轮机工程', 'A082402',
    '水声工程', 'A082403',
    '海洋工程硕士', 'A084403',
    '船舶工程硕士', 'A084605',
    # 跨大类紧密相关
    '海洋科学类', 'B0707',
    '海洋技术', 'B070702',
    '海洋资源与环境', 'B070703',
    '海洋信息工程', 'B080718',
    '航海技术', 'B081903',
    '船舶电子电气工程', 'B081908',
    '海洋油气工程', 'B081606',
    '港口航道与海岸工程', 'B081203',
    '港口、海岸及近海工程', 'A081505',
    '土木、水利与海洋工程', 'B081109',
    '海洋渔业科学与技术', 'B090602',
    '海洋药学', 'B101007',
    # 专科
    '船舶工程技术', 'C084501',
    '海洋工程技术', 'C084507',
    '船舶机械工程技术', 'C084502',
    '船舶电气工程技术', 'C084503',
    # 大类编号
    '13船舶',
]


def matches_ocean(text):
    if not text or text.strip() == '':
        return False
    for kw in OCEAN_KEYWORDS:
        if kw in text:
            return True
    return False


def extract_sheet_data(sheet, header_row):
    """提取单 sheet 中符合海洋工程关键词的职位数据"""
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
        if not any(matches_ocean(pt) for pt in prof_texts):
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
# 项目根 = 上两级；files_config() 需要的是含 .xls 的 data 目录
base_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'data')
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

outpath = f'{base_dir}/ocean_data.json'
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n数据已保存到 ocean_data.json（共 {len(all_records)} 条记录）')
