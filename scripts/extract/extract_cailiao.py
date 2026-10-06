import xlrd
import json
import re

# ===== 材料类相关关键词 =====
# 涵盖材料科学与工程、材料类及相关具体专业
CL_KEYWORDS = [
    # 材料类大类和学科
    '材料类', '材料科学与工程',
    # 研究生专业
    '材料物理与化学', '材料学', '材料加工工程',
    # 本科具体专业
    '材料物理', '材料化学', '金属材料工程', '无机非金属材料工程',
    '高分子材料与工程', '复合材料与工程', '粉体材料科学与工程',
    '宝石及材料工艺学', '焊接技术与工程', '功能材料',
    '纳米材料与技术', '新能源材料与器件', '材料设计科学与工程',
    '复合材料成型工程', '智能材料与结构', '光电信息材料与器件',
    '生物材料',
    # 专业硕士 / 交叉学科
    '材料工程', '材料与化工',
]

def matches_cailiao(text):
    if not text or text.strip() == '':
        return False
    for kw in CL_KEYWORDS:
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

        if not any(row):
            continue
        first_cell = row[0] if len(row) > 0 else ''
        if '附件' in first_cell or '职位表' in first_cell or '报考' in first_cell or '配套' in first_cell:
            continue

        prof_texts = []
        for pc in prof_cols:
            if pc < len(row):
                prof_texts.append(row[pc])

        if not any(matches_cailiao(pt) for pt in prof_texts):
            continue

        recruit = safe_int(row[recruit_col]) if recruit_col < len(row) else 0

        fresh_only = False
        if fresh_col is not None and fresh_col < len(row):
            fv = row[fresh_col]
            fresh_only = (fv == '是') or ('应届' in fv) or ('届' in fv and '毕业生' in fv)

        city = row[city_col] if city_col is not None and city_col < len(row) else ''
        unit = row[unit_col] if unit_col < len(row) else ''
        position = row[pos_col] if pos_col is not None and pos_col < len(row) else ''
        pos_code = row[pos_code_col] if pos_code_col is not None and pos_code_col < len(row) else ''
        education = row[edu_col] if edu_col is not None and edu_col < len(row) else ''

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
            'prof_fields': '; '.join(prof_texts),
        })

    return records


# ===== File configuration =====
base_dir = 'c:/Users/YANG/Desktop/广东20-26年广东省考职位表'

files_to_process = []

files_to_process.append(('2020', '附件2：广东省县级以上机关和珠三角地区乡镇机关2020年招录公务员职位表.xls'))
files_to_process.append(('2020', '附件1：广东省东西两翼地区和北部生态发展区乡镇机关2020年招录公务员职位表.xls'))

files_to_process.append(('2021', '附件2：广东省县级以上机关和珠三角地区乡镇机关2021年招录公务员职位表.xls'))
files_to_process.append(('2021', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2021年招录公务员职位表.xls'))

files_to_process.append(('2022', '附件2：广东省县级以上机关和珠三角地区乡镇机关2022年考试录用公务员职位表.xls'))
files_to_process.append(('2022', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2022年考试录用公务员职位表.xls'))

files_to_process.append(('2023', '附件2：广东省县级以上机关和珠三角地区乡镇机关2023年考试录用公务员职位表.xls'))
files_to_process.append(('2023', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2023年考试录用公务员职位表.xls'))

files_to_process.append(('2024', '附件1：广东省2024年考试录用公务员职位表.xls'))
files_to_process.append(('2025', '附件1：广东省2025年考试录用公务员职位表.xls'))
files_to_process.append(('2026', '附件1：广东省2026年考试录用公务员职位表.xls'))


all_records = []
yearly_data = {}

for year, fname in files_to_process:
    wb = xlrd.open_workbook(f'{base_dir}/{fname}')

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

    print(f'{year}: total={yearly_data[year]["total_records"]} pos, {yearly_data[year]["total_recruits"]} recruits')
    for sname, sdata in yearly_data[year]['sheets'].items():
        print(f'  [{sname}]: {sdata["records"]} pos, {sdata["recruits"]} recruits')


# === Print Summary ===
print('\n' + '='*60)
print('历年材料类招录汇总')
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

with open(f'{base_dir}/cailiao_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n数据已保存到 cailiao_data.json（共 {len(all_records)} 条记录）')
