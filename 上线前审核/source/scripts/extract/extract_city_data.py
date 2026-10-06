"""
广东省考地域维度数据提取脚本
从原始 .xls 职位表中提取城市维度数据，按城市聚合招录情况。
输出: data/city_data.json
"""
import sys
import os
import json
import re
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from generate.gviz_common import (
    files_config, find_header_row, build_col_map, get_fresh_type,
    safe_int, standardize_city, collect_prof_field_texts, get_col,
    PROF_COL_NAMES, FRESH_COL_NAMES, RECRUIT_COL_NAMES,
    UNIT_COL_NAMES, POS_COL_NAMES, CITY_COL_NAMES, EDU_COL_NAMES,
)
import xlrd

# 项目根目录 = 本文件的上两级（scripts/extract/ → scripts/ → 项目根）。
# 不要写死绝对路径：否则换机器或换目录后无法从干净检出复现。
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'city_data.json')

# ====== 数据提取 ======

# 乡镇专项子表没有「学历」列，学历门槛写在 sheet 名上（如「本市大专以上」）。
# 这里把 sheet 名映射为学历层次，避免这些记录在学历结构里全部落到「其他」。
SHEET_NAME_EDUCATION = {
    '优秀本科以上毕业生': '本科以上',
    '本市大专以上': '大专以上',
    '本县大专以上': '大专以上',
}

# 非专业名的占位符，构建 城市×专业 矩阵时必须排除
NO_MAJOR_LIMIT_TOKENS = {
    '不限', '专业不限', '不限专业', '无限制',
}

# 旧版（2020-2022 乡镇表）分类名 → 去数字前缀后的写法。
# 仅当去前缀后仍与新版名不一致时才需要在这里列出；未列出的直接去前缀。
LEGACY_MAJOR_FIX = {
    '能源和动力类': '能源动力类',
}

# 学历原始取值 → 标准分组。
# 原始表实际只会出现「本科以上 / 本科 / 研究生 / 大专以上 / 大专、本科 / 大专 / 空」，
# 旧版分组表只列了 5 个精确值，导致占比最大的「本科以上」全部落入「其他」。
EDU_GROUP_RULES = [
    ('研究生', '研究生'),
    ('本科以上', '本科以上'),
    ('大专、本科', '大专或本科'),
    ('大专以上', '大专以上'),
    ('本科', '本科'),
    ('大专', '大专'),
]

EDU_GROUPS = ['研究生', '本科以上', '本科', '大专以上', '大专', '大专或本科']


def normalize_education(raw_value):
    """把原始学历文本归入标准分组，无法识别的返回 '其他'"""
    v = str(raw_value or '').strip()
    if not v:
        return '其他'
    for key, group in EDU_GROUP_RULES:
        if key in v:
            return group
    return '其他'





def sheet_name_education(sheet_name):
    """当 sheet 无学历列时，按 sheet 名推断学历层次"""
    for key, edu in SHEET_NAME_EDUCATION.items():
        if key in sheet_name:
            return edu
    return ''


def extract_sheet_records(sheet, year):
    """提取单个 sheet 的职位记录。

    各 sheet 的表头位置与列顺序都不同（如「监狱戒毒」无「考区」列、
    「本市大专以上」等乡镇子表无「是否限应届毕业生报考」列），
    因此列映射必须逐 sheet 重建，缺失列按缺省值处理。
    """
    hr = find_header_row(sheet)
    if hr is None:
        return []

    col_map = build_col_map(sheet, hr)
    recruit_col = get_col(col_map, RECRUIT_COL_NAMES)
    city_col = get_col(col_map, CITY_COL_NAMES)
    unit_col = get_col(col_map, UNIT_COL_NAMES)
    if recruit_col is None or (city_col is None and unit_col is None):
        return []

    prof_cols = [col_map[n] for n in PROF_COL_NAMES if n in col_map]
    fresh_col = get_col(col_map, FRESH_COL_NAMES)
    edu_col = get_col(col_map, EDU_COL_NAMES)
    pos_col = get_col(col_map, POS_COL_NAMES)

    def cell(row, col):
        if col is None or col >= len(row):
            return ''
        return row[col]

    records = []
    for r in range(hr + 1, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
        if not any(row):
            continue
        first_cell = row[0] if row else ''
        if any(kw in first_cell for kw in ['附件', '职位表', '报考', '配套', '说明']):
            continue

        recruits = safe_int(cell(row, recruit_col))
        if recruits <= 0:
            continue

        unit_val = cell(row, unit_col)
        city = standardize_city(unit_val, cell(row, city_col))
        if not city:
            continue

        education = cell(row, edu_col) or sheet_name_education(sheet.name)
        records.append({
            'year': year,
            'city': city,
            'recruits': recruits,
            'education': education,
            'fresh_type': get_fresh_type(cell(row, fresh_col)),
            'unit': unit_val,
            'position': cell(row, pos_col),
            'prof_fields': collect_prof_field_texts(row, prof_cols) if prof_cols else [],
        })
    return records


def extract_all_records():
    """遍历所有职位表文件的**全部 sheet**，提取每条记录的城市维度数据。

    历史缺陷：本函数曾只读取 wb.sheet_by_index(0)，导致 2024-2026 年
    丢失公安/法院/检察院/监狱戒毒/乡镇机关等 sheet，2020-2023 年丢失
    审计/公安/法院/检察院/监狱戒毒/珠三角乡镇及乡镇子表，累计漏掉约
    46% 的职位记录。现改为逐 sheet 提取。
    """
    all_records = []
    files = files_config(DATA_DIR)

    for year, fpath in files:
        if not os.path.exists(fpath):
            print(f'  [跳过] 文件不存在: {os.path.basename(fpath)}')
            continue
        fname = os.path.basename(fpath)
        try:
            wb = xlrd.open_workbook(fpath)
        except Exception as e:
            print(f'  [错误] 无法打开 {fname}: {e}')
            continue

        file_count = 0
        for si in range(wb.nsheets):
            sheet = wb.sheet_by_index(si)
            records = extract_sheet_records(sheet, year)
            if not records:
                continue
            all_records.extend(records)
            file_count += len(records)
            print(f'    [sheet] {sheet.name}: {len(records)} 条')
        print(f'  [OK] {fname[:40]} ({year}): 合计 {file_count} 条记录')

    return all_records


def normalize_legacy_major(name):
    """归一化 2020-2022 旧版乡镇招考专业代码。

    那几年的乡镇职位表用「01规划建设类」「06法律类」这类两位数字前缀的旧分类名，
    与新版专业目录名称（如「法律类」）指同一类专业。不归一化会让同一个专业在
    城市×专业矩阵里分裂成两个条目。
    """
    m = re.match(r'^(\d{2})([\u4e00-\u9fa5]+)$', name)
    if not m:
        return name
    bare = m.group(2)
    return LEGACY_MAJOR_FIX.get(bare, bare)


def parse_majors(prof_texts):
    """从专业要求文本中解析出专业名称列表。

    - 「不限」「专业不限」不是专业名，只是"无专业限制"的占位符，需过滤；
    - 旧版两位数字前缀代码（06法律类）需归一化为新版名（法律类）；
    - 同一字段内可能出现逗号分隔的多值（"06法律类, 08中文传播类"），需拆分。
    """
    majors = set()
    for text in prof_texts:
        if not text:
            continue
        # 按分号、换行、中英文逗号、顿号分割
        parts = re.split(r'[;；\n,，、]', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 尝试提取 "专业名(代码)" 格式；源表里存在括号不成对的情况
            # （如 "人力资源管理）"），因此再剥掉名称尾部残留的括号/标点
            m = re.match(r'([^（(]+)[（(]', part)
            name = (m.group(1) if m else part).strip()
            name = re.sub(r'[）)】\]、,，;；\s]+$', '', name).strip()
            if not name or name in NO_MAJOR_LIMIT_TOKENS or '不限' in name:
                continue
            majors.add(normalize_legacy_major(name))
    return majors


def build_city_major_matrix(all_records):
    """构建城市×专业招录矩阵 {城市: {专业: 招录人数}}"""
    matrix = defaultdict(lambda: defaultdict(int))
    city_major_positions = defaultdict(lambda: defaultdict(int))  # 职位数
    for rec in all_records:
        if not rec['prof_fields']:
            continue
        majors = parse_majors(rec['prof_fields'])
        for m in majors:
            matrix[rec['city']][m] += rec['recruits']
            city_major_positions[rec['city']][m] += 1
    # 转回普通 dict
    result = {}
    for city, majors in matrix.items():
        result[city] = dict(sorted(majors.items(), key=lambda x: -x[1]))
    return result


def aggregate_city_data(all_records):
    """按城市+年度聚合数据"""
    # 基础聚合
    city_year = defaultdict(lambda: defaultdict(int))
    city_edu = defaultdict(lambda: defaultdict(int))
    city_fresh = defaultdict(lambda: defaultdict(int))
    city_records = defaultdict(list)
    total_recruits = 0
    total_positions = 0

    for rec in all_records:
        c = rec['city']
        y = rec['year']
        city_year[c][y] += rec['recruits']
        city_edu[c][rec['education']] += rec['recruits']

        # 累计招录人数（每个record是一条职位记录）
        # recruits 字段已经是该职位的招录人数
        total_recruits += rec['recruits']
        total_positions += 1

        city_fresh[c][rec['fresh_type']] += rec['recruits']
        city_records[c].append(rec)

    # 构建输出
    prd_cities = ['广州', '深圳', '珠海', '佛山', '东莞', '中山', '惠州', '江门', '肇庆']
    all_cities = sorted(city_year.keys(), key=lambda c: -sum(city_year[c].values()))

    city_yearly = {}
    for c in all_cities:
        yearly = {}
        for y in ['2020', '2021', '2022', '2023', '2024', '2025', '2026']:
            yearly[y] = city_year[c].get(y, 0)
        total_c = sum(city_year[c].values())
        city_yearly[c] = {
            'total_recruits': total_c,
            'total_positions': len(city_records[c]),
            'yearly': yearly,
            'pct_of_total': round(total_c / total_recruits * 100, 1) if total_recruits else 0,
        }

    city_education = {}
    for c in all_cities:
        city_education[c] = dict(city_edu[c])

    city_fresh_out = {}
    for c in all_cities:
        city_fresh_out[c] = dict(city_fresh[c])

    prd_recruits = sum(city_yearly[c]['total_recruits'] for c in prd_cities if c in city_yearly)

    # 教育层次标准化分组：用 normalize_education 归类每个原始取值，
    # 未识别的（含空值）才计入「其他」，避免占比最大的「本科以上」被误归入「其他」。
    city_edu_grouped = {}
    for c in all_cities:
        grouped = {eg: 0 for eg in EDU_GROUPS}
        grouped['其他'] = 0
        for raw_edu, cnt in city_education.get(c, {}).items():
            grouped[normalize_education(raw_edu)] += cnt
        if not grouped['其他']:
            grouped.pop('其他')
        city_edu_grouped[c] = grouped

    result = {
        'summary': {
            'total_cities': len(all_cities),
            'total_recruits': total_recruits,
            'total_positions': total_positions,
            'pearl_river_delta_recruits': prd_recruits,
            'non_prd_recruits': total_recruits - prd_recruits,
            'prd_cities': prd_cities,
            'prd_ratio': round(prd_recruits / total_recruits * 100, 1) if total_recruits else 0,
        },
        'city_yearly': city_yearly,
        'city_education_raw': city_education,
        'city_education': city_edu_grouped,
        'city_fresh': city_fresh_out,
        'city_ranking': [c for c in all_cities],
        'details': all_records,
    }

    return result


def main():
    print('=== 广东省考地域维度数据提取 ===')
    print('[1/3] 提取所有职位记录...')
    all_records = extract_all_records()
    print(f'  共提取 {len(all_records)} 条记录')

    print('[2/3] 按城市聚合数据...')
    city_data = aggregate_city_data(all_records)

    print('[2b/3] 构建专业×城市矩阵...')
    matrix = build_city_major_matrix(all_records)
    city_data['city_major_matrix'] = matrix

    print('[3/3] 保存到文件...')
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(city_data, f, ensure_ascii=False, indent=2)
    print(f'  输出: {OUTPUT_FILE}')
    print(f'  Summary: {json.dumps(city_data["summary"], ensure_ascii=False)}')


if __name__ == '__main__':
    main()
