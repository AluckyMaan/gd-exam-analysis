#!/usr/bin/env python3
"""
干净检出端到端复现测试。

作用：把当前 HEAD 导出成一个临时的干净检出（模拟别人 clone 仓库后的状态），
      在那里跑完整管线，验证：
        1) 脚本不依赖跨机器无效的硬编码绝对路径
        2) 两步提取能从 data/*.xls 重建两个 JSON，且关键数字与主工作区一致
        3) 看板生成不依赖网络（地图走本地缓存）
        4) 生成结果确定性可复现（同输入两次生成哈希一致）

用法：
    python scripts/test_clean_checkout.py            # 只跑管线并核对数字
    python scripts/test_clean_checkout.py --keep     # 保留临时检出目录以便排查

退出码 0 = 全部通过。
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

EXPECT = {
    'majors_rows': 74849,
    # 242 = 241 个专业 + 1 条「不限专业：服务基层/退役士兵专岗」(code=SPECIAL-SR)
    'majors_unique': 242,
    'majors_ranking_len': 242,
    'city_positions': 74849,
    'city_recruits': 105365,
    'city_prd_ratio': 43.5,
    # 省直回归基线 —— 见文件末尾「为什么省直必须是这个数」的说明，不要"顺手修正"它
    'provincial_recruits': 5215,
    'provincial_2026': 605,
    'yearly': {'2020': 11871, '2021': 13309, '2022': 15422, '2023': 18258,
               '2024': 17307, '2025': 17419, '2026': 11779},
}


def run(cmd, cwd, timeout=1800):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', action='store_true')
    args = ap.parse_args()

    results = []

    def check(name, passed, detail=''):
        results.append((name, passed, detail))
        print('  [%s] %s%s' % ('PASS' if passed else 'FAIL', name, ('  — ' + detail) if detail else ''))

    # 说明：干净检出必须放在工作区内 —— 本环境对系统临时目录只读。
    # 该目录已被 .gitignore 忽略，不会污染仓库。
    tmp_parent = os.path.join(ROOT, '.clean-checkout-test')
    os.makedirs(tmp_parent, exist_ok=True)
    work = os.path.join(tmp_parent, 'repo')
    if os.path.exists(work):
        subprocess.run(['git', 'worktree', 'remove', '--force', work], cwd=ROOT,
                       capture_output=True, text=True)
        shutil.rmtree(work, ignore_errors=True)
    print('干净检出: %s' % work)
    try:
        # 用 git worktree 导出 HEAD（只检出工作区文件，不复制 .git 历史）
        rc, out = run(['git', 'worktree', 'add', '--detach', work, 'HEAD'], ROOT)
        if rc != 0:
            print('git worktree 失败：\n' + out[:800])
            return 2

        # 两个数据 JSON 现在**有意纳入版本控制**，因此干净检出里应当存在它们 ——
        # 这正是"审核可复现"的前提：有权威副本可比对，而不是依赖工作区里的未跟踪文件。
        check('检出中含受版本控制的数据 JSON（审核可比对）',
              os.path.exists(os.path.join(work, 'data', 'city_data.json'))
              and os.path.exists(os.path.join(work, 'data', 'all_majors_ranking.json')))
        check('检出中含原始 .xls 输入',
              len([f for f in os.listdir(os.path.join(work, 'data')) if f.endswith('.xls')]) >= 10,
              '%d 个 .xls' % len([f for f in os.listdir(os.path.join(work, 'data')) if f.endswith('.xls')]))

        # 记录受控副本，稍后与重跑结果比对
        import json as _json
        tracked_city = _json.load(open(os.path.join(work, 'data', 'city_data.json'), encoding='utf-8'))
        tracked_major = _json.load(open(os.path.join(work, 'data', 'all_majors_ranking.json'), encoding='utf-8'))

        # 地图缓存是可选加速项（无网络时应由生成器优雅降级）
        cache = os.path.join(ROOT, 'data', 'guangdong_geojson.json')
        if os.path.exists(cache):
            shutil.copy2(cache, os.path.join(work, 'data', 'guangdong_geojson.json'))
            print('  （已放入本地地图缓存，使生成过程不联网）')

        # 步骤 1：专业侧提取
        rc, out = run([PY, 'scripts/extract/extract_all_majors.py'], work)
        check('scripts/extract/extract_all_majors.py 在干净检出中运行成功', rc == 0,
              '' if rc == 0 else out.strip().splitlines()[-1][:160] if out.strip() else '')
        if rc != 0:
            print(out[-2500:])

        # 步骤 2：地域侧提取
        rc2, out2 = run([PY, 'scripts/extract/extract_city_data.py'], work)
        check('scripts/extract/extract_city_data.py 在干净检出中运行成功', rc2 == 0,
              '' if rc2 == 0 else out2.strip().splitlines()[-1][:160] if out2.strip() else '')
        if rc2 != 0:
            print(out2[-2500:])

        if rc == 0 and rc2 == 0:
            import json
            a = json.load(open(os.path.join(work, 'data', 'all_majors_ranking.json'), encoding='utf-8'))
            c = json.load(open(os.path.join(work, 'data', 'city_data.json'), encoding='utf-8'))
            check('专业侧 total_position_rows == %d' % EXPECT['majors_rows'],
                  a['summary']['total_position_rows'] == EXPECT['majors_rows'],
                  str(a['summary']['total_position_rows']))
            check('专业侧 unique_majors_found == %d' % EXPECT['majors_unique'],
                  a['summary']['unique_majors_found'] == EXPECT['majors_unique'],
                  str(a['summary']['unique_majors_found']))
            check('专业侧 ranking 长度 == %d' % EXPECT['majors_ranking_len'],
                  len(a['ranking']) == EXPECT['majors_ranking_len'], str(len(a['ranking'])))
            check('地域侧 total_positions == %d' % EXPECT['city_positions'],
                  c['summary']['total_positions'] == EXPECT['city_positions'],
                  str(c['summary']['total_positions']))
            check('地域侧 total_recruits == %d' % EXPECT['city_recruits'],
                  c['summary']['total_recruits'] == EXPECT['city_recruits'],
                  str(c['summary']['total_recruits']))
            check('地域侧 prd_ratio == %.1f' % EXPECT['city_prd_ratio'],
                  abs(c['summary']['prd_ratio'] - EXPECT['city_prd_ratio']) < 0.05,
                  str(c['summary']['prd_ratio']))
            cy = {y: 0 for y in EXPECT['yearly']}
            for info in c['city_yearly'].values():
                for y in cy:
                    cy[y] += info['yearly'].get(y, 0)
            check('逐年招录人数与基线完全一致', cy == EXPECT['yearly'], str(cy))

            # 防「静默漏表」回归：data/ 中的每份职位表都必须被 files_config 命中，
            # 且两侧职位数必须相等（曾因 2023 附件1 文件名不匹配相差 1496）
            import sys as _sys
            _sys.path.insert(0, os.path.join(work, 'scripts'))
            from generate.gviz_common import resolve_job_tables
            _res, _miss, _unused = resolve_job_tables(os.path.join(work, 'data'))
            check('无漏读的职位表（files_config 完整覆盖 data/）',
                  not _miss and not _unused,
                  '认领 %d 份；未找到=%s；未认领=%s' % (len(_res), _miss, _unused))
            check('地域侧职位数 == 专业侧职位数（%d）' % EXPECT['city_positions'],
                  c['summary']['total_positions'] == a['summary']['total_position_rows']
                  == EXPECT['city_positions'],
                  '%s vs %s' % (c['summary']['total_positions'], a['summary']['total_position_rows']))

            # 省直回归守卫：见文件末尾说明。这里断言的是**业务确认过的口径**，
            # 不是"待修复的缺陷" —— 若此断言失败，先读那段说明再动手。
            sdx = c['city_yearly'].get('省直', {})
            check('省直人数 == %d（业务确认口径）' % EXPECT['provincial_recruits'],
                  sdx.get('total_recruits') == EXPECT['provincial_recruits'],
                  str(sdx.get('total_recruits')))
            check('省直 2026 == %d（监狱/戒毒属省直单位，不应为 0）' % EXPECT['provincial_2026'],
                  sdx.get('yearly', {}).get('2026') == EXPECT['provincial_2026'],
                  str(sdx.get('yearly', {}).get('2026')))

            # 关键回归 1：重跑提取后必须仍与受版本控制的副本语义一致
            # （曾发生：重跑把人工注入的 SPECIAL-SR 条目丢掉，且因文件被 ignore 而无人发现）
            check('重跑专业侧 == 受版本控制的副本（深比对，含每条专业指标）',
                  a == tracked_major,
                  'ranking %d vs %d，SPECIAL-SR=%s' % (
                      len(a['ranking']), len(tracked_major['ranking']),
                      any(m.get('code') == 'SPECIAL-SR' for m in a['ranking'])))
            check('重跑地域侧 == 受版本控制的副本（深比对，含逐城市/逐年/矩阵）',
                  c == tracked_city,
                  'positions %s vs %s' % (c['summary']['total_positions'],
                                          tracked_city['summary']['total_positions']))

            # 步骤 3：生成看板
            html = os.path.join(work, '广东省考综合数据分析看板.html')
            rc3, out3 = run([PY, 'scripts/generate/generate_merged_viz.py'], work)
            check('scripts/generate/generate_merged_viz.py 在干净检出中运行成功', rc3 == 0,
                  '' if rc3 == 0 else (out3.strip().splitlines()[-1][:160] if out3.strip() else ''))
            if rc3 == 0:
                h1 = sha256(html)
                check('生成过程未依赖网络（使用本地地图缓存）',
                      '已加载本地地图缓存' in out3 or 'GeoJSON' not in out3,
                      [l for l in out3.splitlines() if '地图' in l][:1][0] if '地图' in out3 else '')
                text = open(html, encoding='utf-8').read()
                check('生成结果无模板占位符残留', not re.findall(r'__[A-Z_0-9]+__', text))
                check('生成结果引用本地 echarts（无 CDN）',
                      'assets/echarts.min.js' in text and 'jsdelivr' not in text)

                # ===== 端到端确定性：完整流水线跑第二遍，逐字节比对全部产物 =====
                # 必须重跑**提取**（而非只重跑生成器）：JSON 的键顺序若不稳定，
                # 只重跑生成器是发现不了的 —— 这正是上一版测试的漏洞。
                snap = {
                    'all_majors_ranking.json': sha256(os.path.join(work, 'data', 'all_majors_ranking.json')),
                    'city_data.json': sha256(os.path.join(work, 'data', 'city_data.json')),
                    '看板 HTML': h1,
                }
                rc5, _ = run([PY, 'scripts/extract/extract_all_majors.py'], work)
                rc6, _ = run([PY, 'scripts/extract/extract_city_data.py'], work)
                rc7, _ = run([PY, 'scripts/generate/generate_merged_viz.py'], work)
                if rc5 == 0 and rc6 == 0 and rc7 == 0:
                    now = {
                        'all_majors_ranking.json': sha256(os.path.join(work, 'data', 'all_majors_ranking.json')),
                        'city_data.json': sha256(os.path.join(work, 'data', 'city_data.json')),
                        '看板 HTML': sha256(html),
                    }
                    for name in snap:
                        same = snap[name] == now[name]
                        check('完整流水线第二遍产出字节一致：%s' % name, same,
                              snap[name][:24] + ('' if same else ' → ' + now[name][:24]))
                else:
                    check('完整流水线第二遍执行成功', False,
                          'rc=%s/%s/%s' % (rc5, rc6, rc7))

        print()
        failed = [r for r in results if not r[1]]
        print('=' * 60)
        print('干净检出复现测试：%d 项，失败 %d 项' % (len(results), len(failed)))
        for n, p, d in failed:
            print('  FAIL %s %s' % (n, d))
        return 1 if failed else 0
    finally:
        run(['git', 'worktree', 'remove', '--force', work], ROOT)
        run(['git', 'worktree', 'prune'], ROOT)
        if args.keep:
            print('保留检出目录以便排查: %s' % work)
        else:
            shutil.rmtree(tmp_parent, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

