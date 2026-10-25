#!/usr/bin/env python3
"""
2020-2022 职位提取完整性审计

对 grep 三年（6 份文件）逐 sheet、逐行追踪：源表里每一行数据的去向必须可交代。
输出：每 sheet 的 总行数 / 提取数 / 各跳过原因计数 + 全局合计与守恒校验。

用法：python scripts/audit_2020_2022.py
"""
import os
import sys
from collections import Counter, defaultdict

import xlrd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from generate.gviz_common import (find_header_row, build_col_map, get_col,
                                  RECRUIT_COL_NAMES, CITY_COL_NAMES, UNIT_COL_NAMES,
                                  POS_COL_NAMES, resolve_job_tables)

DATA = os.path.join(ROOT, 'data')
YEARS = ['2020', '2021', '2022']

# 与 extract_city_data.py 保持一致的跳过规则
META_PREFIX = ['附件', '职位表', '报考', '配套', '说明']


def audit():
    resolved, _, _ = resolve_job_tables(DATA)
    files = [(y, fn) for y, fn in resolved if y in YEARS]

    grand = Counter()
    print('=' * 78)
    print('审计范围：2020-2022 共 %d 份文件' % len(files))
    print('=' * 78)

    for year, fn in files:
        wb = xlrd.open_workbook(os.path.join(DATA, fn))
        print('\n■ %s  %s' % (year, fn))
        print('  文件含 %d 个 sheet' % wb.nsheets)
        for si in range(wb.nsheets):
            sh = wb.sheet_by_index(si)
            hr = find_header_row(sh)
            if hr is None:
                print('    [%d] %-18s 无表头 → 整表跳过' % (si, sh.name))
                grand['no_header'] += 1
                continue
            cm = build_col_map(sh, hr)
            rc = get_col(cm, RECRUIT_COL_NAMES)
            cc = get_col(cm, CITY_COL_NAMES)
            uc = get_col(cm, UNIT_COL_NAMES)
            pc = get_col(cm, POS_COL_NAMES)

            stat = Counter()
            detail = []
            for r in range(hr + 1, sh.nrows):
                row = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
                stat['raw_rows'] += 1
                if not any(row):
                    stat['skip_empty'] += 1
                    continue
                first = row[0] if row else ''
                if any(k in first for k in META_PREFIX):
                    stat['skip_meta'] += 1
                    continue
                # 录用人数
                v = row[rc] if (rc is not None and rc < len(row)) else ''
                try:
                    n = int(float(v))
                except Exception:
                    stat['skip_bad_recruit'] += 1
                    if len(detail) < 3:
                        detail.append('人数无法解析: %r' % v)
                    continue
                if n <= 0:
                    stat['skip_zero_recruit'] += 1
                    continue
                # 城市
                city = row[cc] if (cc is not None and cc < len(row)) else ''
                unit = row[uc] if (uc is not None and uc < len(row)) else ''
                if not city:
                    stat['skip_no_city'] += 1
                    if len(detail) < 6:
                        detail.append('无考区: 单位=%r 职位=%r 人数=%d'
                                      % (unit[:26], (row[pc][:20] if pc is not None and pc < len(row) else ''), n))
                    continue
                stat['extracted'] += 1
                stat['people'] += n

            print('    [%d] %-18s hr=%-2s 总行=%-5d 提取=%-5d(人=%-6d) 跳过: 空行=%-4d 说明行=%-4d 人数<=0=%-3d 无考区=%-3d 人数异常=%d'
                  % (si, sh.name, hr, stat['raw_rows'], stat['extracted'], stat['people'],
                     stat['skip_empty'], stat['skip_meta'], stat['skip_zero_recruit'],
                     stat['skip_no_city'], stat['skip_bad_recruit']))
            for d in detail:
                print('         · %s' % d)
            for k, v in stat.items():
                grand[k] += v
            grand['sheets'] += 1

    print('\n' + '=' * 78)
    print('全局合计')
    print('=' * 78)
    print('  sheet 总数            : %d' % grand['sheets'])
    print('  源表数据行总数        : %d' % grand['raw_rows'])
    print('  提取入库行数          : %d' % grand['extracted'])
    print('  提取入库招录人数      : %d' % grand['people'])
    print('  跳过：空行            : %d' % grand['skip_empty'])
    print('  跳过：说明/标题行     : %d' % grand['skip_meta'])
    print('  跳过：录用人数<=0     : %d' % grand['skip_zero_recruit'])
    print('  跳过：无考区          : %d' % grand['skip_no_city'])
    print('  跳过：人数无法解析    : %d' % grand['skip_bad_recruit'])
    tot_skip = (grand['skip_empty'] + grand['skip_meta'] + grand['skip_zero_recruit']
                + grand['skip_no_city'] + grand['skip_bad_recruit'])
    print('  跳过合计              : %d' % tot_skip)
    print('  守恒校验 提取+跳过 == 总行 : %s (%d + %d = %d)'
          % ('PASS' if grand['extracted'] + tot_skip == grand['raw_rows'] else '**FAIL**',
             grand['extracted'], tot_skip, grand['raw_rows']))

    # 与已生成的 JSON 对照
    import json
    city = json.load(open(os.path.join(DATA, 'city_data.json'), encoding='utf-8'))
    for y in YEARS:
        rows = sum(1 for r in city['details'] if r['year'] == y)
        ppl = sum(r['recruits'] for r in city['details'] if r['year'] == y)
        print('  JSON 中 %s 年: 行=%d 人=%d' % (y, rows, ppl))
    return 0


if __name__ == '__main__':
    sys.exit(audit())
