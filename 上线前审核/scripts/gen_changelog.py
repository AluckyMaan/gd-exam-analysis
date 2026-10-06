#!/usr/bin/env python3
"""
生成「改动日志.md」与「git-history.txt」→ 上线前审核/

由 git 历史自动汇总，避免手写日志与提交记录不一致。
用法：python 上线前审核/scripts/gen_changelog.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(PKG_DIR)

BASE = 'origin/main'          # 推送基线
HEAD = 'HEAD'


def git(*args):
    return subprocess.run(['git', '-C', ROOT, '-c', 'core.quotepath=false'] + list(args),
                          capture_output=True, text=True, encoding='utf-8').stdout.strip()


def main():
    commits = git('log', '--reverse', '--format=%h|%ad|%s', '--date=format:%Y-%m-%d %H:%M',
                  f'{BASE}..{HEAD}').splitlines()
    if not commits:
        print('没有相对基线的新提交')
        return 1

    lines = []
    lines.append('# 改动日志（自动生成）\n')
    lines.append(f'- 生成方式：`git log {BASE}..{HEAD}`，由 `上线前审核/scripts/gen_changelog.py` 汇总\n')
    lines.append(f'- 基线提交：`{git("rev-parse", "--short", BASE)}`　目标提交：`{git("rev-parse", "--short", HEAD)}`\n')
    lines.append(f'- 提交数量：{len(commits)}\n')
    stat = git('diff', '--shortstat', f'{BASE}..{HEAD}')
    lines.append(f'- 净改动规模：{stat}\n')
    lines.append('\n---\n\n## 逐提交明细\n')

    for i, row in enumerate(commits, 1):
        h, date, subject = row.split('|', 2)
        body = git('log', '-1', '--format=%b', h)
        files = [f for f in git('show', '--name-status', '--format=', h).splitlines() if f.strip()]
        lines.append(f'### {i}. `{h}` {subject}\n')
        lines.append(f'*时间：{date}*\n')
        if body.strip():
            lines.append('说明：\n')
            for para in [p.strip() for p in body.split('\n') if p.strip()]:
                lines.append(f'- {para}\n')
            lines.append('')
        added = [f for f in files if f.startswith('A\t')]
        modified = [f for f in files if f.startswith('M\t')]
        deleted = [f for f in files if f.startswith('D\t')]
        lines.append(f'改动文件：新增 {len(added)}、修改 {len(modified)}、删除 {len(deleted)}\n')
        for label, group in [('新增', added), ('修改', modified), ('删除', deleted)]:
            if not group:
                continue
            lines.append(f'\n<details><summary>{label}（{len(group)}）</summary>\n')
            for f in group[:60]:
                lines.append(f'- `{f.split(chr(9), 1)[1]}`')
            if len(group) > 60:
                lines.append(f'- …（其余 {len(group) - 60} 个见 git-history.txt）')
            lines.append('\n</details>\n')
        lines.append('\n')

    lines.append('---\n\n## 净改动文件清单（相对基线）\n')
    lines.append('```\n')
    lines.append(git('diff', '--stat', f'{BASE}..{HEAD}'))
    lines.append('\n```\n')

    with open(os.path.join(PKG_DIR, '改动日志.md'), 'w', encoding='utf-8') as f:
        f.write(''.join(lines))

    raw = git('log', '--reverse', '--stat', '--format=commit %h%nDate:   %ad%nSubject: %s%n',
              '--date=iso', f'{BASE}..{HEAD}')
    with open(os.path.join(PKG_DIR, 'git-history.txt'), 'w', encoding='utf-8') as f:
        f.write(raw + '\n')

    print('已生成 改动日志.md 与 git-history.txt')
    print(f'  提交数 {len(commits)}｜{stat}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
