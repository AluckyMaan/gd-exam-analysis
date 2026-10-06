#!/usr/bin/env python3
"""
广东省考职位数据可视化生成器 — 统一入口
一键提取 + 生成 HTML 看板，支持自定义专业关键词和配色。

用法:
  # 查看所有选项
  python make_viz.py --help

  # 基本用法（交互式输入专业名）
  python make_viz.py

  # 完整参数模式
  python make_viz.py ^
      --major "计算机类" ^
      --keywords "计算机,软件工程,人工智能,计算机类,B0809" ^
      --color "#1a3a5c" ^
      --desc "涵盖计算机类（B0809）、软件工程、人工智能等相关专业"

  # 仅提取数据（不生成 HTML）
  python make_viz.py --major "计算机类" --keywords "计算机" --extract-only

依赖: gviz_common.py (公共模块), xlrd
"""

import argparse
import json
import os
import sys
import tempfile
import textwrap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    parser = argparse.ArgumentParser(
        description='广东省考职位数据可视化生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            使用示例:
              python make_viz.py
              python make_viz.py --major "材料类" --keywords "材料,高分子,金属" --color "#4a2a5a"
              python make_viz.py --extract-only
        """),
    )
    parser.add_argument('--major', '-m', help='专业名称（如：海洋工程、计算机类）')
    parser.add_argument('--keywords', '-k', help='关键词列表，逗号分隔')
    parser.add_argument('--color', '-c', help='主题主色（十六进制，如 #0f2b4a）')
    parser.add_argument('--gold', help='强调色（十六进制，默认 #b8952e）')
    parser.add_argument('--desc', help='专业描述（显示在 Hero 区）')
    parser.add_argument('--extract-only', action='store_true', help='仅提取数据，不生成 HTML')
    parser.add_argument('--output', '-o', help='输出 JSON 文件名（不含路径）')
    parser.add_argument('--html', help='输出 HTML 文件名（不含路径）')
    return parser.parse_args()


def interactive_input():
    """交互式输入专业信息"""
    print('=' * 50)
    print('广东省考职位可视化生成器')
    print('=' * 50)
    major = input('专业名称（如：海洋工程）: ').strip()
    if not major:
        print('专业名称不能为空')
        sys.exit(1)

    keywords_raw = input('专业关键词（逗号分隔，如：海洋工程,船舶,轮机）: ').strip()
    keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]
    if not keywords:
        print('关键词不能为空')
        sys.exit(1)

    color = input('主题主色（直接回车使用默认 #0f2b4a）: ').strip() or '#0f2b4a'
    desc_raw = input('专业描述（直接回车自动生成）: ').strip()

    return {
        'major': major,
        'keywords': keywords,
        'color': color,
        'gold': '#b8952e',
        'desc': desc_raw or f'涵盖 {major} 及相关专业招录趋势分析',
    }


def make_extract_script(config):
    """动态生成提取脚本内容"""
    kw_list = '\n    '.join(f"'{kw}'," for kw in config['keywords'])
    major = config['major']
    tag = major[:2]  # 取前两字作为标识

    return f'''"""
{major}相关专业招录数据提取脚本（由 make_viz.py 自动生成）
"""
import json
import os
import sys
sys.path.insert(0, r"{BASE_DIR}")
from gviz_common import *

KEYWORDS = [
    {kw_list}
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
            fresh_only = (fv == '是') or ('\\u5e94\\u5c4a' in fv) or ('\\u5c4a' in fv and '\\u6bd5\\u4e1a\\u751f' in fv)
            fresh_type = get_fresh_type(fv)
        city = row[city_col] if city_col is not None and city_col < len(row) else ''
        unit = row[unit_col] if unit_col < len(row) else ''
        position = row[pos_col] if pos_col is not None and pos_col < len(row) else ''
        pos_code = row[pos_code_col] if pos_code_col is not None and pos_code_col < len(row) else ''
        education = row[edu_col] if edu_col is not None and edu_col < len(row) else ''
        city = standardize_city(unit, city)
        records.append({{
            'unit': unit, 'position': position, 'position_code': pos_code,
            'recruits': recruit, 'city': city, 'education': education,
            'fresh_only': fresh_only, 'fresh_type': fresh_type,
            'prof_fields': '; '.join(prof_texts),
        }})
    return records

base_dir = r"{BASE_DIR}"
all_records = []
yearly_data = {{}}

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
            yearly_data[year] = {{
                'year': year, 'total_records': 0, 'total_recruits': 0,
                'fresh_records': 0, 'fresh_recruits': 0, 'fresh_current_recruits': 0,
            }}
        yd = yearly_data[year]
        yd['total_records'] += len(records)
        yd['total_recruits'] += sum(r['recruits'] for r in records)
        fresh_recs = [r for r in records if r['fresh_only']]
        yd['fresh_records'] += len(fresh_recs)
        yd['fresh_recruits'] += sum(r['recruits'] for r in fresh_recs)
        yd['fresh_current_recruits'] += sum(r['recruits'] for r in records if r['fresh_type'] == 'fresh_current')
        for r in records:
            all_records.append({{'year': year, 'sheet': sheet_name, **r}})

city_summary = {{}}
edu_summary = {{}}
fresh_summary = {{'social': {{}}, 'fresh_any': {{}}, 'fresh_current': {{}}}}
for rec in all_records:
    city = rec.get('city', '') or '\\u5176\\u4ed6'
    yr = rec['year']
    city_summary.setdefault(city, {{}})
    city_summary[city][yr] = city_summary[city].get(yr, 0) + rec['recruits']
    edu = rec.get('education', '') or '\\u5176\\u4ed6'
    edu_summary.setdefault(edu, {{}})
    edu_summary[edu][yr] = edu_summary[edu].get(yr, 0) + rec['recruits']
    ft = rec.get('fresh_type', 'social')
    fresh_summary[ft][yr] = fresh_summary[ft].get(yr, 0) + rec['recruits']

yearly_summary = {{}}
for yr in sorted(yearly_data.keys()):
    d = yearly_data[yr]
    yearly_summary[yr] = {{
        'year': yr, 'total_records': d['total_records'],
        'total_recruits': d['total_recruits'],
        'fresh_records': d['fresh_records'],
        'fresh_recruits': d['fresh_recruits'],
        'fresh_current_recruits': d['fresh_current_recruits'],
        'avg_per_position': round(d['total_recruits'] / d['total_records'], 1) if d['total_records'] > 0 else 0,
    }}

output = {{
    'yearly_summary': yearly_summary,
    'city_summary': city_summary,
    'edu_summary': edu_summary,
    'fresh_summary': fresh_summary,
    'details': all_records,
}}

outpath = os.path.join(base_dir, '{config["output"] or tag + "_data.json"}')
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\\n\\u6570\\u636e\\u5df2\\u4fdd\\u5b58\\u5230 {{outpath}}（\\u5171 {{len(all_records)}} \\u6761\\u8bb0\\u5f55）')
'''


def run_extract(config):
    """生成并运行提取脚本"""
    script_content = make_extract_script(config)

    # 写入临时文件运行
    tag = config['major'][:2]
    script_path = os.path.join(BASE_DIR, f'_extract_{tag}.py')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    print(f'  提取脚本已生成: {os.path.basename(script_path)}')
    print('  正在提取数据...')

    import subprocess
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        capture_output=True, text=True, timeout=300,
    )

    if result.returncode != 0:
        print('  提取失败:', result.stderr[:500])
        return None

    # 解析输出
    for line in result.stdout.split('\n'):
        if '数据已保存' in line or '202' in line[:4]:
            print(f'  {line}')

    return result.stdout


def generate_html_summary(config, extract_output):
    """输出 HTML 生成指引（不直接生成，指向 generate_xxx_html.py 模式）"""
    tag = config['major'][:2]
    json_file = config.get('output') or f'{tag}_data.json'

    print()
    print('=' * 50)
    print('✅ 数据提取完成！')
    print('=' * 50)
    print(f'  JSON 文件: {json_file}')
    print()
    print('下一步：生成 HTML 可视化看板')
    print('─' * 40)
    print(f'参考已有模板修改 generate_ocean_html.py：')
    print(f'  1. 复制为 generate_{tag}_html.py')
    print(f'  2. 修改数据源为 \"{json_file}\"')
    print(f'  3. 修改标题/描述/颜色')
    print(f'  4. 运行 python generate_{tag}_html.py')
    print()
    print('常用配色参考：')
    print(f'  {config["major"]}: {config["color"]}')


def main():
    args = parse_args()

    # 获取配置
    if args.major:
        config = {
            'major': args.major,
            'keywords': [k.strip() for k in args.keywords.split(',')] if args.keywords else [args.major],
            'color': args.color or '#0f2b4a',
            'gold': args.gold or '#b8952e',
            'desc': args.desc or f'涵盖 {args.major} 及相关专业招录趋势分析',
            'output': args.output,
            'html': args.html,
        }
    else:
        config = interactive_input()

    if not config.get('output'):
        config['output'] = f'{config["major"][:2]}_data.json'

    # 提取数据
    result = run_extract(config)
    if result is None:
        sys.exit(1)

    # HTML 生成指引
    if not args.extract_only:
        generate_html_summary(config, result)


if __name__ == '__main__':
    main()
