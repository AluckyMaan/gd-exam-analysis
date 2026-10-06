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
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

EXPECT = {
    'majors_rows': 74849,
    'majors_unique': 241,
    'majors_ranking_len': 242,
    'city_positions': 73353,
    'city_recruits': 101964,
    'city_prd_ratio': 45.0,
    'yearly': {'2020': 11871, '2021': 13309, '2022': 15422, '2023': 14857,
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

    tmp = tempfile.mkdtemp(prefix='clean-checkout-')
    work = os.path.join(tmp, 'repo')
    print('临时检出: %s' % work)
    try:
        # 用 git worktree 导出 HEAD，避免复制 100MB+ 的 .git
        rc, out = run(['git', 'worktree', 'add', '--detach', work, 'HEAD'], ROOT)
        if rc != 0:
            print('git worktree 失败：\n' + out[:800])
            return 2

        # 干净检出里没有生成物，正是要验证的状态
        check('检出中不含 data/city_data.json（确认是干净状态）',
              not os.path.exists(os.path.join(work, 'data', 'city_data.json')))
        check('检出中含原始 .xls 输入',
              len([f for f in os.listdir(os.path.join(work, 'data')) if f.endswith('.xls')]) >= 10,
              '%d 个 .xls' % len([f for f in os.listdir(os.path.join(work, 'data')) if f.endswith('.xls')]))

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

            # 步骤 3：生成看板（两次，验证确定性）
            rc3, out3 = run([PY, 'scripts/generate/generate_merged_viz.py'], work)
            check('scripts/generate/generate_merged_viz.py 在干净检出中运行成功', rc3 == 0,
                  '' if rc3 == 0 else (out3.strip().splitlines()[-1][:160] if out3.strip() else ''))
            if rc3 == 0:
                html = os.path.join(work, '广东省考综合数据分析看板.html')
                h1 = sha256(html)
                rc4, _ = run([PY, 'scripts/generate/generate_merged_viz.py'], work)
                h2 = sha256(html) if os.path.exists(html) else ''
                check('看板生成确定性（两次哈希一致）', h1 == h2, h1[:24])
                check('生成过程未依赖网络（使用本地地图缓存）',
                      '已加载本地地图缓存' in out3 or 'GeoJSON' not in out3,
                      [l for l in out3.splitlines() if '地图' in l][:1][0] if '地图' in out3 else '')
                text = open(html, encoding='utf-8').read()
                check('生成结果无模板占位符残留', not re.findall(r'__[A-Z_0-9]+__', text))
                check('生成结果引用本地 echarts（无 CDN）',
                      'assets/echarts.min.js' in text and 'jsdelivr' not in text)

        print()
        failed = [r for r in results if not r[1]]
        print('=' * 60)
        print('干净检出复现测试：%d 项，失败 %d 项' % (len(results), len(failed)))
        for n, p, d in failed:
            print('  FAIL %s %s' % (n, d))
        return 1 if failed else 0
    finally:
        run(['git', 'worktree', 'remove', '--force', work], ROOT)
        if args.keep:
            print('保留临时目录: %s' % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
