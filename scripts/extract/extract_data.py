import xlrd
import json
import re

# ===== 土木工程相关关键词 =====
# 涵盖具体专业和广东省考专业大类"规划建设类（01）"
TM_KEYWORDS = [
    # 土木工程具体专业/学科
    '土木工程', '土木类', '岩土工程', '结构工程', '市政工程',
    '桥梁与隧道工程', '土木水利', '市政工程类', '建设工程',
    '土建', '工民建', '建筑工程', '土木',
    # 广东省考专业大类：规划建设类（01）下含土木工程
    '规划建设类',
]

def matches_tumu(text):
    if not text or text.strip() == '':
        return False
    for kw in TM_KEYWORDS:
        if kw in text:
            return True
    return False

def safe_int(val):
    try:
        return int(float(val))
    except:
        return 0

def find_header_row(sheet, max_check=15):
    """Find the row that contains professional field headers."""
    for r in range(max_check):
        row_text = '|'.join([str(sheet.cell_value(r, c)) for c in range(sheet.ncols)])
        # Look for either 本科专业 or 研究生专业 indicators
        if '专业' in row_text and ('名称' in row_text or '代码' in row_text):
            return r
    return None

def extract_sheet_data(sheet, header_row):
    """Extract data from a single sheet by finding relevant columns."""
    if header_row is None:
        return []

    # Build column mapping
    col_map = {}
    for c in range(sheet.ncols):
        val = str(sheet.cell_value(header_row, c)).strip().replace('\n', '')
        col_map[val] = c

    # Map key columns
    recruit_col = None
    for name in ['录用人数']:
        if name in col_map:
            recruit_col = col_map[name]
            break

    prof_cols = []
    for name in ['研究生专业名称及代码', '本科专业名称及代码', '大专专业名称及代码',
                 '研究生专业\n名称及代码', '本科专业\n名称及代码', '大专专业\n名称及代码',
                 '研究生专业\n名称及代码', '本科专业\n名称及代码']:
        if name in col_map:
            prof_cols.append(col_map[name])

    fresh_col = None
    for name in ['是否限应届毕业生报考', '是否限应届\n毕业生报考']:
        if name in col_map:
            fresh_col = col_map[name]
            break

    # Education column
    edu_col = col_map.get('学历')

    city_col = col_map.get('考区')
    unit_col = col_map.get('招考单位') if '招考单位' in col_map else col_map.get('招录主管部门')
    pos_col = col_map.get('招考职位')
    pos_code_col = col_map.get('职位代码')

    if not all([recruit_col is not None, prof_cols, unit_col is not None]):
        return []

    records = []
    data_start = header_row + 1

    for r in range(data_start, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]

        # Skip meta rows
        if not any(row):
            continue
        first_cell = row[0] if len(row) > 0 else ''
        if '附件' in first_cell or '职位表' in first_cell or '报考' in first_cell or '配套' in first_cell:
            continue

        # Check professional fields
        prof_texts = []
        for pc in prof_cols:
            if pc < len(row):
                prof_texts.append(row[pc])

        if not any(matches_tumu(pt) for pt in prof_texts):
            continue

        recruit = safe_int(row[recruit_col]) if recruit_col < len(row) else 0

        fresh_only = False
        fresh_type = 'social'
        if fresh_col is not None and fresh_col < len(row):
            fv = row[fresh_col]
            if fv == '否':
                fresh_only = False
                fresh_type = 'social'
            elif fv == '是' or '应届毕业生' in fv:
                fresh_only = True
                fresh_type = 'fresh_any'
            elif '届' in fv and '毕业生' in fv:
                fresh_only = True
                fresh_type = 'fresh_current'

        city = row[city_col] if city_col is not None and city_col < len(row) else ''
        unit = row[unit_col] if unit_col < len(row) else ''
        position = row[pos_col] if pos_col is not None and pos_col < len(row) else ''
        pos_code = row[pos_code_col] if pos_code_col is not None and pos_code_col < len(row) else ''
        education = row[edu_col] if edu_col is not None and edu_col < len(row) else ''

        # Fix 省直 classification: provincial units often have 考区=广州 but unit name starts with 广东省
        if unit.startswith('广东省') and ('厅' in unit or '局' in unit or '委' in unit or '办' in unit):
            city = '省直'

        records.append({
            'unit': unit,
            'position': position,
            'position_code': pos_code,
            'recruits': recruit,
            'city': city,
            'education': education,
            'fresh_only': fresh_only,
            'fresh_type': fresh_type,
            'prof_fields': '; '.join(prof_texts),
        })

    return records


# ===== File configuration =====
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# List of (year, filename, sheet_override) where sheet_override=None means all sheets
files_to_process = []

# === 2020 ===
files_to_process.append(('2020', '附件2：广东省县级以上机关和珠三角地区乡镇机关2020年招录公务员职位表.xls'))
files_to_process.append(('2020', '附件1：广东省东西两翼地区和北部生态发展区乡镇机关2020年招录公务员职位表.xls'))

# === 2021 ===
files_to_process.append(('2021', '附件2：广东省县级以上机关和珠三角地区乡镇机关2021年招录公务员职位表.xls'))
files_to_process.append(('2021', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2021年招录公务员职位表.xls'))

# === 2022 ===
files_to_process.append(('2022', '附件2：广东省县级以上机关和珠三角地区乡镇机关2022年考试录用公务员职位表.xls'))
files_to_process.append(('2022', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2022年考试录用公务员职位表.xls'))

# === 2023 ===
files_to_process.append(('2023', '附件2：广东省县级以上机关和珠三角地区乡镇机关2023年考试录用公务员职位表.xls'))
files_to_process.append(('2023', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2023年考试录用公务员职位表.xls'))

# === 2024, 2025, 2026 ===
files_to_process.append(('2024', '附件1：广东省2024年考试录用公务员职位表.xls'))
files_to_process.append(('2025', '附件1：广东省2025年考试录用公务员职位表.xls'))
files_to_process.append(('2026', '附件1：广东省2026年考试录用公务员职位表.xls'))


all_records = []
yearly_data = {}

for year, fname in files_to_process:
    wb = xlrd.open_workbook(os.path.join(base_dir, 'data', fname))

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
                'year': year,
                'total_records': 0,
                'total_recruits': 0,
                'fresh_records': 0,
                'fresh_recruits': 0,
                'sheets': {}
            }

        if sheet_name not in yearly_data[year]['sheets']:
            yearly_data[year]['sheets'][sheet_name] = {'records': 0, 'recruits': 0}

        yearly_data[year]['total_records'] += len(records)
        yearly_data[year]['total_recruits'] += sum(r['recruits'] for r in records)
        yearly_data[year]['sheets'][sheet_name]['records'] += len(records)
        yearly_data[year]['sheets'][sheet_name]['recruits'] += sum(r['recruits'] for r in records)

        fresh_recs = [r for r in records if r['fresh_only']]
        yearly_data[year]['fresh_records'] += len(fresh_recs)
        yearly_data[year]['fresh_recruits'] += sum(r['recruits'] for r in fresh_recs)

        for r in records:
            all_records.append({
                'year': year,
                'sheet': sheet_name,
                **r
            })

    print(f'{year} ({fname[:20]}...): total={yearly_data[year]["total_records"]} pos, {yearly_data[year]["total_recruits"]} recruits')
    for sname, sdata in yearly_data[year]['sheets'].items():
        print(f'  [{sname}]: {sdata["records"]} pos, {sdata["recruits"]} recruits')


# === Print Summary ===
print('\n' + '='*60)
print('历年土木工程/规划建设类招录汇总')
print('='*60)
print(f'{"年份":<6} {"职位数":<8} {"招录人数":<10} {"应届招录":<10} {"每岗平均":<10}')
for yr in sorted(yearly_data.keys()):
    d = yearly_data[yr]
    avg = round(d['total_recruits'] / d['total_records'], 1) if d['total_records'] > 0 else 0
    print(f'{yr:<6} {d["total_records"]:<8} {d["total_recruits"]:<10} {d["fresh_recruits"]:<10} {avg:<10}')

# City breakdown
city_summary = {}
for rec in all_records:
    city = rec.get('city', '') or '其他'
    yr = rec['year']
    if city not in city_summary:
        city_summary[city] = {}
    city_summary[city][yr] = city_summary[city].get(yr, 0) + rec['recruits']

print('\n=== 城市分布 ===')
for city in sorted(city_summary.keys()):
    totals = city_summary[city]
    total = sum(totals.values())
    print(f'{city}: {total} ({totals})')

# === Save output ===
yearly_summary = {}
for yr in sorted(yearly_data.keys()):
    d = yearly_data[yr]
    yearly_summary[yr] = {
        'year': yr,
        'total_records': d['total_records'],
        'total_recruits': d['total_recruits'],
        'fresh_records': d['fresh_records'],
        'fresh_recruits': d['fresh_recruits'],
        'avg_per_position': round(d['total_recruits'] / d['total_records'], 1) if d['total_records'] > 0 else 0,
    }

output = {
    'yearly_summary': yearly_summary,
    'city_summary': {k: v for k, v in city_summary.items()},
    'details': all_records
}

with open(f'{base_dir}/tumu_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n数据已保存到 tumu_data.json（共 {len(all_records)} 条记录）')
