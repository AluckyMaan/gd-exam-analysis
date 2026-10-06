"""
广东省考职位数据提取公共模块 (gviz-common)
提供表头查找、列映射、应届分类、文件配置等共享功能。
"""

import xlrd
import os
import re

# ====== 基础工具函数 ======

def safe_int(val):
    """安全转整数，失败返回0"""
    try:
        return int(float(val))
    except:
        return 0


META_ROW_PREFIXES = ('附件', '报考条件', '配套措施', '说明', '职位表')

# 强表头信号列名：出现其中之一基本可确认该行是真正的表头
HEADER_STRONG_KEYS = ('录用人数', '招考单位', '招录主管部门', '职位代码', '考区')

def _is_meta_row(row_text):
    """判断该行是否为说明/元信息行（不能当表头）"""
    first = row_text.split('|')[0].strip()
    return any(first.startswith(p) for p in META_ROW_PREFIXES)


def find_header_row(sheet, max_check=20):
    """找到真正的表头行。

    历史上这里只用「专业 + 名称/代码」匹配，会被乡镇子表的说明行误命中：
    说明行首列是「报考条件」，正文里含"应届硕士、博士研究生…"以及"专业不限"，
    导致表头行被定位到说明行，整个 sheet 提取为空。因此增加两条约束：
      1) 首列为「报考条件/配套措施/附件」等元信息行一律排除；
      2) 优先选择同时含强表头信号列（录用人数/招考单位/考区…）的行。
    """
    candidates = []
    for r in range(max_check):
        row_text = '|'.join(
            str(sheet.cell_value(r, c)).replace('\n', '').replace('\r', '')
            for c in range(sheet.ncols)
        )
        if _is_meta_row(row_text):
            continue
        has_prof = '专业' in row_text and ('名称' in row_text or '代码' in row_text)
        strong = sum(1 for k in HEADER_STRONG_KEYS if k in row_text)
        if has_prof:
            candidates.append((3 + strong, r))
        elif strong >= 2:
            candidates.append((strong, r))
    if candidates:
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][1]
    # 最后兜底：任意含「专业」的行
    for r in range(max_check):
        row_text = '|'.join(
            str(sheet.cell_value(r, c)).replace('\n', '').replace('\r', '')
            for c in range(sheet.ncols)
        )
        if _is_meta_row(row_text):
            continue
        if '专业' in row_text:
            return r
    return None


def get_fresh_type(fv):
    """
    应届类型分类
    - '否' / 空 → social（社会人员）
    - '202X届高校毕业生'（带年份数字） → fresh_current（当年应届）
    - '应届毕业生' / '是'（无具体年份）→ fresh_any（往届应届/择业期）
    """
    import re
    if not fv or fv.strip() == '' or fv == '否':
        return 'social'
    # 包含年份数字 + 届，如 "2023届高校毕业生"、"2024届"
    if re.search(r'\d+届', fv):
        return 'fresh_current'
    # 其他含"应届"或"是"的，属于往届/择业期
    return 'fresh_any'


def find_col_in_map(col_map, names):
    """在列映射中按名称列表查找列号，返回第一个匹配"""
    for name in names:
        if name in col_map:
            return col_map[name]
    return None


def norm_key(text):
    """归一化列名：去掉所有空白/换行符，便于跨 sheet 稳定匹配。

    各年份职位表的表头写法不一致（如 '研究生专业\\n名称及代码' vs
    '研究生专业名称及代码'），归一化后再查表可避免漏列。
    """
    return re.sub(r'\s+', '', str(text))


def normalized_col_map(sheet, header_row):
    """构建「归一化列名 → 列号」的映射（推荐用于新增脚本）"""
    return {norm_key(sheet.cell_value(header_row, c)): c for c in range(sheet.ncols)}


def get_col(col_map, names):
    """按名称列表查列号，精确匹配失败时退化为归一化匹配"""
    hit = find_col_in_map(col_map, names)
    if hit is not None:
        return hit
    normalized = {norm_key(k): v for k, v in col_map.items()}
    for name in names:
        key = norm_key(name)
        if key in normalized:
            return normalized[key]
    return None


# ====== 职位表文件配置 ======

def files_config(base_dir):
    """
    返回 (year, filepath) 列表，按年份从旧到新排列
    """
    files = [
        # 2020
        ('2020', '附件2：广东省县级以上机关和珠三角地区乡镇机关2020年招录公务员职位表.xls'),
        ('2020', '附件1：广东省东西两翼地区和北部生态发展区乡镇机关2020年招录公务员职位表.xls'),
        # 2021
        ('2021', '附件2：广东省县级以上机关和珠三角地区乡镇机关2021年招录公务员职位表.xls'),
        ('2021', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2021年招录公务员职位表.xls'),
        # 2022
        ('2022', '附件2：广东省县级以上机关和珠三角地区乡镇机关2022年考试录用公务员职位表.xls'),
        ('2022', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2022年考试录用公务员职位表.xls'),
        # 2023
        ('2023', '附件2：广东省县级以上机关和珠三角地区乡镇机关2023年考试录用公务员职位表.xls'),
        ('2023', '附件1：广东省沿海经济带东西两翼地区和北部生态发展区乡镇机关2023年招录公务员职位表.xls'),
        # 2024-2026 合并文件
        ('2024', '附件1：广东省2024年考试录用公务员职位表.xls'),
        ('2025', '附件1：广东省2025年考试录用公务员职位表.xls'),
        ('2026', '附件1：广东省2026年考试录用公务员职位表.xls'),
    ]
    return [(year, os.path.join(base_dir, fname)) for year, fname in files]


# ====== 列映射构建 ======

def build_col_map(sheet, header_row):
    """构建列名→列号的映射，自动处理换行符"""
    col_map = {}
    for c in range(sheet.ncols):
        val = str(sheet.cell_value(header_row, c)).strip().replace('\n', '')
        col_map[val] = c
    return col_map


def collect_prof_field_texts(row, prof_cols):
    """收集专业列文本，返回合并后的字符串列表"""
    texts = []
    for pc in prof_cols:
        if pc < len(row):
            texts.append(row[pc])
    return texts


# ====== 标准化城市名 ======

def standardize_city(unit, city):
    """省直单位归一化为'省直'"""
    if unit.startswith('广东省') and ('厅' in unit or '局' in unit or '委' in unit or '办' in unit):
        return '省直'
    return city


# ====== 专业列名 ======

PROF_COL_NAMES = [
    '研究生专业名称及代码', '本科专业名称及代码', '大专专业名称及代码',
    '研究生专业\n名称及代码', '本科专业\n名称及代码', '大专专业\n名称及代码',
]

FRESH_COL_NAMES = [
    '是否限应届毕业生报考', '是否限应届\n毕业生报考',
]

RECRUIT_COL_NAMES = ['录用人数']

UNIT_COL_NAMES = ['招考单位', '招录主管部门']
POS_COL_NAMES = ['招考职位']

POS_CODE_COL_NAMES = ['职位代码']

CITY_COL_NAMES = ['考区']

EDU_COL_NAMES = ['学历']
