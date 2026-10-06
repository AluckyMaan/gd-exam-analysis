"""
广东省考全部专业招录数据提取脚本（通用版，不限关键词）
读取 2020-2026 全部 10 个职位表，提取每个职位的专业要求，
统计各专业招录人数、职位数、年份分布、城市分布、应届/社会比例、共现关系。

输出: data/all_majors_ranking.json
"""

import xlrd
import os
import re
import json
import copy
from collections import Counter, defaultdict

# 项目根目录 = 本文件的上两级（scripts/extract/ → scripts/ → 项目根）。
# 不要写死绝对路径：否则换机器或换目录后无法从干净检出复现。
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# ====== 基础工具 ======

def safe_int(val):
    try:
        return int(float(val))
    except:
        return 0

def find_header_row(sheet, max_check=20):
    for r in range(max_check):
        row_text = '|'.join([str(sheet.cell_value(r, c)).replace('\n', '').replace('\r', '') for c in range(sheet.ncols)])
        if '专业' in row_text and ('名称' in row_text or '代码' in row_text):
            return r
    # Fallback: look for header rows with typical column names
    for r in range(max_check):
        row_text = '|'.join([str(sheet.cell_value(r, c)).replace('\n', '').replace('\r', '') for c in range(sheet.ncols)])
        if '招录主管部门' in row_text or '招考单位' in row_text:
            return r
    return None

def get_fresh_type(fv):
    if not fv or fv.strip() == '' or fv == '否':
        return 'social'
    if re.search(r'\d+届', fv):
        return 'fresh_current'
    return 'fresh_any'

def standardize_city(unit, city):
    if unit.startswith('广东省') and ('厅' in unit or '局' in unit or '委' in unit or '办' in unit):
        return '省直'
    return city

# ====== 文件配置 ======

def get_files():
    """返回 [(year, filepath), ...] 列表"""
    files = [
        ('2020', os.path.join(BASE_DIR, 'data', '附件2：广东省县级以上机关和珠三角地区乡镇机关2020年招录公务员职位表.xls')),
        ('2020', os.path.join(BASE_DIR, 'data', '附件1：广东省东西两翼地区和北部生态发展区乡镇机关2020年招录公务员职位表.xls')),
        ('2021', os.path.join(BASE_DIR, 'data', '附件2：广东省县级以上机关和珠三角地区乡镇机关2021年招录公务员职位表.xls')),
        ('2021', os.path.join(BASE_DIR, 'data', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2021年招录公务员职位表.xls')),
        ('2022', os.path.join(BASE_DIR, 'data', '附件2：广东省县级以上机关和珠三角地区乡镇机关2022年考试录用公务员职位表.xls')),
        ('2022', os.path.join(BASE_DIR, 'data', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2022年考试录用公务员职位表.xls')),
        ('2023', os.path.join(BASE_DIR, 'data', '附件2：广东省县级以上机关和珠三角地区乡镇机关2023年考试录用公务员职位表.xls')),
        ('2023', os.path.join(BASE_DIR, 'data', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2023年考试录用公务员职位表.xls')),
        ('2024', os.path.join(BASE_DIR, 'data', '附件1：广东省2024年考试录用公务员职位表.xls')),
        ('2025', os.path.join(BASE_DIR, 'data', '附件1：广东省2025年考试录用公务员职位表.xls')),
        ('2026', os.path.join(BASE_DIR, 'data', '附件1：广东省2026年考试录用公务员职位表.xls')),
    ]
    # Verify files exist
    valid = []
    for year, fp in files:
        if os.path.exists(fp):
            valid.append((year, fp))
        else:
            print(f'  [WARN] 文件不存在，跳过: {fp}')
    return valid


# ====== 专业目录映射 ======

def extract_code_name(text):
    """Parse entries like 土木类（B0811） or 土木类(B0811)."""
    if not text:
        return None
    text = str(text).strip().replace('\n', '')
    m = re.search(r'(.+?)[（(]([A-Z]\d+)[）)]', text)
    if not m:
        return None
    return m.group(2).strip(), m.group(1).strip()

def get_catalog_file():
    data_dir = os.path.join(BASE_DIR, 'data')
    candidates = []
    for fn in os.listdir(data_dir):
        if fn.endswith('.xls') and '专业参考目录' in fn:
            candidates.append(os.path.join(data_dir, fn))
    if not candidates:
        return None
    candidates.sort(key=lambda p: ('2026' not in os.path.basename(p), os.path.basename(p)))
    return candidates[0]

def build_catalog_parent_map():
    """
    Return {code: (parent_code, parent_name)} from the official reference catalog.
    This maps graduate A-level disciplines/specialties to their aligned B-level
    undergraduate category when the catalog places them on the same row block.
    """
    fpath = get_catalog_file()
    if not fpath:
        return {}
    try:
        wb = xlrd.open_workbook(fpath)
    except Exception as e:
        print(f'  [WARN] 专业参考目录打开失败，跳过跨层级合并: {e}')
        return {}

    # Sheet 1: 学科对应具体专业目录
    sheet = wb.sheet_by_index(1)
    code_parent = {}
    a_disc_parents = defaultdict(set)
    a_disc_without_parent = set()
    last_a_code = None
    for r in range(4, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
        a_disc = (row[1], row[2]) if len(row) > 2 and row[1] and row[2] else None
        b_disc = (row[7], row[8]) if len(row) > 8 and row[7] and row[8] else None
        if a_disc and b_disc:
            a_disc_parents[a_disc[0]].add(b_disc)
        elif a_disc:
            if a_disc[0] != last_a_code:
                a_disc_without_parent.add(a_disc[0])
        if a_disc:
            last_a_code = a_disc[0]

    current_a_parent = None
    current_b = None
    current_c = None

    for r in range(4, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]

        a_disc = (row[1], row[2]) if len(row) > 2 and row[1] and row[2] else None
        a_spec = (row[3], row[4]) if len(row) > 4 and row[3] and row[4] else None
        b_disc = (row[7], row[8]) if len(row) > 8 and row[7] and row[8] else None
        b_spec = (row[9], row[10]) if len(row) > 10 and row[9] and row[10] else None
        c_disc = (row[13], row[14]) if len(row) > 14 and row[13] and row[14] else None
        c_spec = (row[15], row[16]) if len(row) > 16 and row[15] and row[16] else None

        if b_disc:
            current_b = b_disc
            if not a_disc:
                current_a_parent = None
        if a_disc:
            current_a_parent = current_b if b_disc else None
        if c_disc:
            current_c = c_disc

        if current_b:
            parent = current_b
            if b_spec and b_spec[0] != parent[0]:
                code_parent[b_spec[0]] = parent
        if current_a_parent:
            parent = current_a_parent
            for item in (a_disc, a_spec):
                if item and item[0] != parent[0]:
                    code_parent[item[0]] = parent
        if current_c:
            parent = current_c
            if c_spec and c_spec[0] != parent[0]:
                code_parent[c_spec[0]] = parent

    for a_code, parents in a_disc_parents.items():
        if len(parents) != 1 or a_code in a_disc_without_parent:
            code_parent.pop(a_code, None)

    supplemental = {
        # These relationships are stated in the professional-category catalog
        # but are not aligned row-by-row in the detailed catalog sheet.
        'A0402': ('B0712', '心理学类'),
        'A0810': ('B0807', '电子信息类'),
        'A0833': ('B0810', '建筑类'),
        'A0834': ('B0810', '建筑类'),
        'A0840': ('B0807', '电子信息类'),
        # Applied economics is too broad to merge as A0202, but its concrete
        # graduate specialties can be split into the corresponding B categories.
        'A020201': ('B0201', '经济学类'),
        'A020202': ('B0201', '经济学类'),
        'A020203': ('B0202', '财政学类'),
        'A020204': ('B0203', '金融学类'),
        'A020205': ('B0201', '经济学类'),
        'A020206': ('B0204', '经济与贸易类'),
        'A020207': ('B0201', '经济学类'),
        'A020208': ('B0711', '统计学类'),
        'A020209': ('B0201', '经济学类'),
        'A020210': ('B0201', '经济学类'),
        'A020211': ('B0203', '金融学类'),
    }
    code_parent.update(supplemental)

    return code_parent


# ====== 专业名称解析 ======

# Filter: skip non-major entries like "不限" and "不限专业"
SKIP_NAMES = {'不限', '不限专业', '无限制', '专业不限', '不限专业类', '不限学历'}

def extract_major_names(text):
    """
    从专业字段文本中提取独立的专业名称列表。

    文本格式示例：
    "法学(A0301),社会学(A0302),公安学(A0303)"
    "01规划建设类, 02装备制造类"
    "计算机科学与技术(A0812)"
    "法学(A0301); 法学(B0301)"  (不同学历层次用;分隔)
    "不限"

    返回: list of {name, type, code}
      type='standard'  → 标准专业目录中的专业名称（如"法学"）
      type='township'  → 乡镇职位分类代码（如"规划建设类"来自"01规划建设类"）
      code             → 专业代码（如"A0301"）或 None
    """
    if not text or text.strip() == '':
        return [{'name': '不限专业', 'type': 'unrestricted', 'code': None}]

    result = []

    # Step 1: 按 ; 分割不同学历层次
    segments = re.split(r'[;；]', text)

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # Step 2: 按 , 分割单个专业条目
        items = re.split(r'[,，]', seg)

        for item in items:
            item = item.strip()
            if not item:
                continue

            # 格式1: "专业名称(专业代码)" → 标准专业
            m = re.match(r'([一-鿿A-Za-zα-ω]+[一-鿿A-Za-zα-ω]*)\(([A-Za-z0-9]+)\)', item)
            if m:
                name = m.group(1).strip()
                code = m.group(2)
                if len(name) >= 2 and not re.match(r'^[\dA-Za-z]+$', name) and name not in SKIP_NAMES:
                    result.append({'name': name, 'type': 'standard', 'code': code})
                continue

            # 格式2: "01规划建设类" → 乡镇分类代码（数字开头+专业名）
            # 标记为"旧版乡镇招考代码"以区别于标准学科专业目录
            m = re.match(r'(\d+)([一-鿿A-Za-z]+[一-鿿A-Za-z]*)', item)
            if m:
                code = m.group(1)
                name = m.group(2).strip()
                if len(name) >= 2 and name not in SKIP_NAMES:
                    result.append({'name': name + '（旧版乡镇招考代码）', 'type': 'township', 'code': code})
                continue

            # 格式3: 纯中文专业名（无代码）→ 标准专业
            m = re.match(r'([一-鿿]+)', item)
            if m:
                name = m.group(1).strip()
                if len(name) >= 2 and name not in SKIP_NAMES:
                    result.append({'name': name, 'type': 'standard', 'code': None})

    # 全部解析后仍无结果 → 检查是否全为“不限”类关键词
    if not result and text.strip():
        text_stripped = text.strip()
        parts = [p.strip() for p in re.split(r'[;；、，,\s]+', text_stripped) if p.strip()]
        if parts and all(p in SKIP_NAMES for p in parts):
            return [{'name': '不限专业', 'type': 'unrestricted', 'code': None}]

    return result


# ====== 职位数据提取 ======

def extract_sheet(sheet):
    """从单个 sheet 提取所有职位数据，返回记录列表"""
    header_row = find_header_row(sheet)
    if header_row is None:
        return []

    # Build column map
    col_map = {}
    for c in range(sheet.ncols):
        val = str(sheet.cell_value(header_row, c)).strip().replace('\n', '')
        col_map[val] = c

    # Find key columns
    recruit_col = col_map.get('录用人数')

    prof_cols = []
    for name in ['研究生专业名称及代码', '本科专业名称及代码', '大专专业名称及代码',
                 '研究生专业\n名称及代码', '本科专业\n名称及代码', '大专专业\n名称及代码']:
        if name in col_map:
            prof_cols.append(col_map[name])

    fresh_col = col_map.get('是否限应届毕业生报考')
    if fresh_col is None:
        fresh_col = col_map.get('是否限应届\n毕业生报考')
    edu_col = col_map.get('学历')
    city_col = col_map.get('考区')
    unit_col = col_map.get('招考单位')
    if unit_col is None:
        unit_col = col_map.get('招录主管部门')
    pos_col = col_map.get('招考职位')
    pos_code_col = col_map.get('职位代码')
    other_col = col_map.get('其他要求')

    if recruit_col is None or unit_col is None:
        return []

    # 「服务基层项目人员和退役大学生士兵」专门职位：单独归为一类，不参与专业排名。
    # 识别方式（两条都要，缺一会漏）：①「其他要求」列含该标识；
    # ② sheet 本身是乡镇专项人员表（2020-2022 的「专项人员」sheet，无「其他要求」列）。
    SPECIAL_MARKER = '服务基层项目人员和退役大学生士兵'
    SPECIAL_SHEET = '专项人员'

    # Check if this sheet has professional-restriction columns
    has_restricted_majors = bool(prof_cols)

    records = []
    data_start = header_row + 1

    for r in range(data_start, sheet.nrows):
        row = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]

        # Skip empty rows and meta rows
        if not any(row):
            continue
        first_cell = row[0] if len(row) > 0 else ''
        if any(kw in first_cell for kw in ['附件', '职位表', '报考', '配套', '说明']):
            continue

        # Professional fields
        prof_texts = []
        for pc in prof_cols:
            if pc < len(row) and row[pc]:
                prof_texts.append(row[pc])
        combined_prof = '; '.join(prof_texts)

        # Extract major names (returns list of {name, type})
        major_items = extract_major_names(combined_prof)
        if not major_items:
            continue

        # Deduplicate by name (同一专业在研究生/本科列都可能出现)
        seen_names = set()
        deduped_items = []
        for item in major_items:
            if item['name'] not in seen_names:
                seen_names.add(item['name'])
                deduped_items.append(item)
        major_items = deduped_items

        major_names = [m['name'] for m in major_items]
        major_types = {m['name']: m['type'] for m in major_items}
        major_codes = {}  # name -> first found code
        for m in major_items:
            if m['name'] not in major_codes and m.get('code'):
                major_codes[m['name']] = m['code']

        recruits = safe_int(row[recruit_col]) if recruit_col < len(row) else 0

        # Fresh graduate
        fresh_only = False
        fresh_type = 'social'
        if fresh_col is not None and fresh_col < len(row):
            fv = row[fresh_col]
            fresh_type = get_fresh_type(fv)
            fresh_only = fresh_type != 'social'

        city = row[city_col] if city_col is not None and city_col < len(row) else ''
        unit = row[unit_col] if unit_col < len(row) else ''
        position = row[pos_col] if pos_col is not None and pos_col < len(row) else ''
        pos_code = row[pos_code_col] if pos_code_col is not None and pos_code_col < len(row) else ''
        education = row[edu_col] if edu_col is not None and edu_col < len(row) else ''
        city = standardize_city(unit, city)

        other_val = row[other_col] if other_col is not None and other_col < len(row) else ''
        is_special = (SPECIAL_MARKER in other_val) or (SPECIAL_SHEET in sheet.name)

        records.append({
            'majors': list(major_names),
            'major_types': major_types,
            'major_codes': major_codes,
            'recruits': recruits,
            'year': None,  # set later
            'city': city,
            'unit': unit,
            'position': position,
            'pos_code': pos_code,
            'education': education,
            'fresh_only': fresh_only,
            'fresh_type': fresh_type,
            'is_special': is_special,
        })

    return records


# ====== 主流程 ======

def main():
    files = get_files()
    print(f'找到 {len(files)} 个文件')

    all_records = []

    for year, fpath in files:
        try:
            wb = xlrd.open_workbook(fpath)
        except Exception as e:
            print(f'  [ERR] 打开失败 {os.path.basename(fpath)}: {e}')
            continue

        total = 0
        for si in range(wb.nsheets):
            sheet = wb.sheet_by_index(si)
            records = extract_sheet(sheet)
            for rec in records:
                rec['year'] = year
                rec['sheet'] = f'{os.path.basename(fpath)}/{sheet.name}'
                all_records.append(rec)
            total += len(records)

        print(f'  {year}: {total} 条记录 ({os.path.basename(fpath)[:25]}...)')

    print(f'\n共提取 {len(all_records)} 条职位记录')

    # ====== 按专业名聚合 ======

    # major_buckets: major_name -> list of record indices
    major_buckets = defaultdict(list)
    major_total_recruits = Counter()
    major_total_positions = Counter()
    major_yearly_recruits = defaultdict(lambda: Counter())
    major_yearly_positions = defaultdict(lambda: Counter())
    major_city_recruits = defaultdict(lambda: Counter())
    major_fresh_recruits = Counter()
    major_social_recruits = Counter()
    major_edu_counter = defaultdict(lambda: Counter())  # education level distribution

    # For purity: count how many times a major appears alone vs with others
    major_alone_count = Counter()  # major appears as the ONLY major in a position
    major_total_appearances = Counter()

    # For co-occurrence: (major_a, major_b) -> count
    cooccur_counts = Counter()

    # Track type (standard vs township) for each major
    major_type_detection = defaultdict(set)
    major_code_map = {}  # major -> first found code

    for idx, rec in enumerate(all_records):
        majors = rec['majors']
        major_types = rec.get('major_types', {})
        major_codes = rec.get('major_codes', {})
        recruits = rec['recruits']
        year = rec['year']
        city = rec['city']
        edu = rec['education']
        is_fresh = rec['fresh_only']

        for m in majors:
            major_total_recruits[m] += recruits
            major_total_positions[m] += 1
            major_total_appearances[m] += 1
            major_yearly_recruits[m][year] += recruits
            major_yearly_positions[m][year] += 1
            major_city_recruits[m][city] += recruits
            if is_fresh:
                major_fresh_recruits[m] += recruits
            else:
                major_social_recruits[m] += recruits
            if edu:
                major_edu_counter[m][edu] += 1

        # Track type per major
        for m_name, m_type in major_types.items():
            major_type_detection[m_name].add(m_type)
        # Track first code found for each major
        for m_name, m_code in major_codes.items():
            if m_name not in major_code_map and m_code:
                major_code_map[m_name] = m_code

        # Purity: if only one major, mark it as "alone"
        if len(majors) == 1:
            major_alone_count[majors[0]] += 1

        # Co-occurrence: pairwise
        majors_sorted = sorted(set(majors))
        for i in range(len(majors_sorted)):
            for j in range(i+1, len(majors_sorted)):
                pair = tuple(sorted([majors_sorted[i], majors_sorted[j]]))
                cooccur_counts[pair] += recruits  # weight by recruits

    # === Filter and build ranking ===

    # Skip master-level entries (they should not be separate ranking items)
    MASTER_SUFFIXES = ('硕士', '博士')
    MIN_POSITIONS = 3

    def build_ranking(records, merge_map=None):
        """Aggregate metrics, applying merge_map before per-position de-duplication."""
        merge_map = merge_map or {}
        total_recruits = Counter()
        total_positions = Counter()
        yearly_recruits = defaultdict(lambda: Counter())
        yearly_positions = defaultdict(lambda: Counter())
        yearly_fresh_recruits = defaultdict(lambda: Counter())
        city_recruits = defaultdict(lambda: Counter())
        fresh_recruits = Counter()
        edu_counter = defaultdict(lambda: Counter())
        alone_count = Counter()
        appearances = Counter()
        other_major_counts = Counter()
        co_counts = Counter()
        type_detection = defaultdict(set)
        code_map = {}

        for rec in records:
            mapped_items = []
            seen = set()
            for name in rec['majors']:
                if any(name.endswith(s) for s in MASTER_SUFFIXES):
                    continue
                mapped = merge_map.get(name, name)
                if mapped in seen:
                    continue
                seen.add(mapped)
                mapped_items.append(mapped)

                original_type = rec.get('major_types', {}).get(name, 'standard')
                type_detection[mapped].add(original_type)
                if mapped not in code_map:
                    code_map[mapped] = major_code_map.get(mapped) or rec.get('major_codes', {}).get(name)

            if not mapped_items:
                continue

            recruits = rec['recruits']
            year = rec['year']
            for name in mapped_items:
                total_recruits[name] += recruits
                total_positions[name] += 1
                appearances[name] += 1
                yearly_recruits[name][year] += recruits
                yearly_positions[name][year] += 1
                if rec['fresh_only']:
                    yearly_fresh_recruits[name][year] += recruits
                city_recruits[name][rec['city']] += recruits
                if rec['fresh_only']:
                    fresh_recruits[name] += recruits
                if rec['education']:
                    edu_counter[name][rec['education']] += 1

            if len(mapped_items) == 1:
                alone_count[mapped_items[0]] += 1
            for name in mapped_items:
                other_major_counts[name] += len(mapped_items) - 1

            majors_sorted = sorted(mapped_items)
            for i in range(len(majors_sorted)):
                for j in range(i + 1, len(majors_sorted)):
                    co_counts[(majors_sorted[i], majors_sorted[j])] += recruits

        ranked = []
        for name, total_pos in total_positions.items():
            if total_pos < MIN_POSITIONS:
                continue

            total_rec = total_recruits[name]
            total_app = appearances[name]
            yearly = {
                y: {
                    'recruits': yearly_recruits[name].get(y, 0),
                    'positions': yearly_positions[name].get(y, 0),
                    'fresh_recruits': yearly_fresh_recruits[name].get(y, 0),
                }
                for y in ['2020', '2021', '2022', '2023', '2024', '2025', '2026']
            }
            recent_years = [y for y in ['2024', '2025', '2026'] if yearly_recruits[name].get(y, 0) > 0]
            early_years = [y for y in ['2020', '2021', '2022'] if yearly_recruits[name].get(y, 0) > 0]
            recent = sum(yearly_recruits[name].get(y, 0) for y in ['2024', '2025', '2026']) / max(1, len(recent_years))
            early = sum(yearly_recruits[name].get(y, 0) for y in ['2020', '2021', '2022']) / max(1, len(early_years))
            growth_rate = round((recent - early) / early * 100, 1) if early > 0 else 0
            m_types = type_detection.get(name, {'standard'})
            maj_type = 'township' if 'township' in m_types else 'standard'
            ranked.append({
                'major': name,
                'code': code_map.get(name),
                'type': maj_type,
                'total_recruits': total_rec,
                'total_positions': total_pos,
                'avg_recruits_per_pos': round(total_rec / total_pos, 1) if total_pos > 0 else 0,
                'purity': round(alone_count.get(name, 0) / total_app * 100, 1) if total_app > 0 else 0,
                'alone_positions': alone_count.get(name, 0),
                'shared_positions': total_app - alone_count.get(name, 0),
                'competition_index': round(other_major_counts[name] / total_app, 2) if total_app > 0 else 0,
                'growth_rate': growth_rate,
                'fresh_ratio': round(fresh_recruits.get(name, 0) / total_rec * 100, 1) if total_rec > 0 else 0,
                'city_coverage': len(city_recruits[name]),
                'yearly': yearly,
                'city_top': dict(city_recruits[name].most_common()),
                'education_distribution': dict(edu_counter[name].most_common(10)),
                'top_co_occurrences': [],
            })

        ranked.sort(key=lambda x: -x['total_recruits'])
        return ranked, co_counts

    def assign_ranks(ranked):
        ranked.sort(key=lambda x: -x['total_recruits'])
        rank = 1
        prev_recruits = None
        for i, m in enumerate(ranked):
            if prev_recruits is not None and m['total_recruits'] < prev_recruits:
                rank = i + 1
            m['rank'] = rank
            prev_recruits = m['total_recruits']

    def attach_top_cooccurrences(ranked, co_counts):
        keep_names = set(m['major'] for m in ranked)
        by_major = defaultdict(lambda: defaultdict(int))
        for (a, b), cnt in co_counts.items():
            if a not in keep_names or b not in keep_names:
                continue
            by_major[a][b] += cnt
            by_major[b][a] += cnt
        for m in ranked:
            total = m['total_recruits']
            pairs = sorted(by_major.get(m['major'], {}).items(), key=lambda x: -x[1])
            m['top_co_occurrences'] = [
                {'major': other, 'recruits': cnt,
                 'co_rate': round(cnt / total * 100, 1) if total > 0 else 0}
                for other, cnt in pairs[:5]
            ]

    ranked_majors, cooccur_counts = build_ranking(all_records)
    assign_ranks(ranked_majors)
    attach_top_cooccurrences(ranked_majors, cooccur_counts)
    raw_ranked_majors = copy.deepcopy(ranked_majors)

    # ====== Merge: 按代码层级将子专业归入大类 ======
    # 规则：
    #   B030101(法学) → B0301(法学类)  子代码→父代码
    #   A0301(法学/研) → B0301(法学类)  A头→B头同级
    #   无对应父代码的保持原样

    # Build code→name lookup (prefer broader/category names)
    code_to_name = {}
    # First pass: collect all name variants per code
    code_name_variants = defaultdict(set)
    for m in ranked_majors:
        c = m.get('code')
        if c and m.get('type') == 'standard':
            code_name_variants[c].add(m['major'])
    # Second pass: pick the best name for each code
    for code, names in code_name_variants.items():
        # Prefer name ending with 类, then longest name, then first alphabetically
        category = [n for n in names if n.endswith('类')]
        if category:
            code_to_name[code] = sorted(category, key=len, reverse=True)[0]
        else:
            code_to_name[code] = sorted(names, key=len, reverse=True)[0]

    catalog_parent_map = build_catalog_parent_map()
    catalog_parent_codes = {}
    for code, name in catalog_parent_map.values():
        old = catalog_parent_codes.get(name)
        if old is None or (old.startswith('C') and code.startswith(('A', 'B'))) or (old.startswith('A') and code.startswith('B')):
            catalog_parent_codes[name] = code

    # Determine merge targets: child_name → parent_name
    merge_map = {}
    for m in ranked_majors:
        code = m.get('code')
        if not code or m.get('type') != 'standard':
            continue
        parent = catalog_parent_map.get(code)
        if not parent and code.startswith('A'):
            for end in range(len(code) - 1, 1, -1):
                parent = catalog_parent_map.get(code[:end])
                if parent:
                    break
        if not parent and len(code) >= 6 and code[0] in ('B', 'C'):
            pc = code[0] + code[1:5]  # B030101 → B0301
            if pc in code_to_name and pc != code:
                parent = (pc, code_to_name[pc])
        if parent and parent[1] != m['major']:
            merge_map[m['major']] = parent[1]

    merged_from_lookup = defaultdict(list)
    for source, target in merge_map.items():
        merged_from_lookup[target].append(source)

    if merge_map:
        ranked_majors, cooccur_counts = build_ranking(all_records, merge_map)
        for m in ranked_majors:
            if m['major'] in catalog_parent_codes:
                m['code'] = catalog_parent_codes[m['major']]
            if m['major'] in merged_from_lookup:
                m['merged_from'] = sorted(set(merged_from_lookup[m['major']]))

    # Sort by total_recruits descending
    assign_ranks(ranked_majors)

    # Top 30（最终排序在下方追加「服务基层/退役士兵专岗」后重算，见 special 段）
    top30 = ranked_majors[:30]

    # Summary stats
    total_positions_scanned = len(all_records)
    unique_majors = len(ranked_majors)

    # ====== Build co-occurrence pairs ======
    keep_names = set(m['major'] for m in ranked_majors)
    merged_pair_counts = defaultdict(int)
    for (a, b), cnt in cooccur_counts.items():
        if a == b:
            continue
        if a not in keep_names or b not in keep_names:
            continue
        key = (a, b) if a < b else (b, a)
        merged_pair_counts[key] += cnt

    cooccurrence_list = [
        {'majors': [a, b], 'recruits': cnt}
        for (a, b), cnt in sorted(merged_pair_counts.items(), key=lambda x: -x[1])[:200]
    ]

    attach_top_cooccurrences(ranked_majors, cooccur_counts)

    # ====== 单独归集「不限专业：服务基层/退役士兵专岗」======
    # 背景：这一类职位不限定专业（源表专业列为空），原先靠人工往 JSON 里补一条
    # code=SPECIAL-SR 的条目，脚本重跑即丢失（且当时该 JSON 被 .gitignore 忽略，
    # 从 git 完全看不出丢失）。现改为脚本内确定性构造，指标定义与其它条目一致。
    special_records = [rec for rec in all_records if rec.get('is_special')]
    if special_records:
        sp_recruits = sum(r['recruits'] for r in special_records)
        sp_positions = len(special_records)
        sp_yearly = {
            y: {
                'recruits': sum(r['recruits'] for r in special_records if r['year'] == y),
                'positions': sum(1 for r in special_records if r['year'] == y),
                'fresh_recruits': 0,
            }
            for y in ['2020', '2021', '2022', '2023', '2024', '2025', '2026']
        }
        sp_city = Counter()
        for r in special_records:
            sp_city[r['city']] += r['recruits']
        sp_edu = Counter()
        for r in special_records:
            sp_edu[r['education'] or '旧表专项人员表未列学历'] += 1
        recent = sum(sp_yearly[y]['recruits'] for y in ['2024', '2025', '2026']) / 3
        early = sum(sp_yearly[y]['recruits'] for y in ['2020', '2021', '2022']) / 3
        ranked_majors.append({
            'major': '不限专业：服务基层/退役士兵专岗',
            'code': 'SPECIAL-SR',
            'type': 'special',
            'total_recruits': sp_recruits,
            'total_positions': sp_positions,
            'avg_recruits_per_pos': round(sp_recruits / sp_positions, 1) if sp_positions else 0,
            'purity': 100.0,          # 该类职位不与其他专业共招
            'alone_positions': sp_positions,
            'shared_positions': 0,
            'competition_index': 0.0,
            'growth_rate': round((recent - early) / early * 100, 1) if early > 0 else 0,
            'fresh_ratio': 0.0,       # 该类职位不限应届
            'city_coverage': len(sp_city),
            'yearly': sp_yearly,
            'city_top': dict(sp_city.most_common()),
            'education_distribution': dict(sp_edu.most_common(10)),
            'top_co_occurrences': [],
            'rank': 0,
        })
        assign_ranks(ranked_majors)
        top30 = ranked_majors[:30]
        unique_majors = len(ranked_majors)
        print(f'  [special] 服务基层/退役士兵专岗: {sp_positions} 个职位 / {sp_recruits} 人')

    output = {
        'summary': {
            'total_files_scanned': len(files),
            'total_position_rows': total_positions_scanned,
            'unique_majors_found': unique_majors,
            'note': '同一职位可能同时包含多个专业名称（如大类+具体专业），总数不互斥。'
        },
        'ranking': ranked_majors,
        'raw_ranking': raw_ranked_majors,
        'top30': top30,
        'co_occurrence_pairs': cooccurrence_list,
    }

    out_path = os.path.join(BASE_DIR, 'data', 'all_majors_ranking.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n数据已保存到 {out_path}')
    print(f'总记录数: {total_positions_scanned}')
    print(f'唯一专业数: {unique_majors}')
    print(f'\n=== Top 10 专业 ===')
    print(f'{"排名":<4} {"专业名称":<20} {"招录人数":<10} {"职位数":<8} {"纯洁度":<8} {"竞争指数":<10}')
    for m in top30[:10]:
        print(f'{m["rank"]:<4} {m["major"]:<20} {m["total_recruits"]:<10} {m["total_positions"]:<8} {m["purity"]:<7}% {m["competition_index"]:<10}')


if __name__ == '__main__':
    main()

