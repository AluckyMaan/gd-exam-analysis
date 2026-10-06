// 只做语法编译校验，不执行页面脚本：从生成的 HTML 中抽出内联 <script>，用 new Function 编译。
const fs = require('fs');
const path = require('path');

const root = process.argv[2] || process.cwd();
const htmlPath = path.join(root, '广东省考综合数据分析看板.html');
const html = fs.readFileSync(htmlPath, 'utf8');

const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const src = blocks.join('\n');
console.log('内联 script 块数 =', blocks.length, '总长度 =', src.length);

let failed = 0;
try {
  new Function(src); // 仅编译
  console.log('SYNTAX OK');
} catch (e) {
  failed = 1;
  console.log('SYNTAX ERROR:', e.name + ':', e.message);
  // 用 vm.Script 拿到带行号的定位
  try {
    const vm = require('vm');
    new vm.Script(src, { filename: 'inline.js' });
  } catch (e2) {
    console.log('vm.Script:', e2.stack ? e2.stack.split('\n').slice(0, 4).join('\n') : e2.message);
  }
}

// 顺便做几项机器核对
const checks = [];
const count = (re) => (src.match(re) || []).length;
checks.push(['initOpeningViews 有调用', /initOpeningViews\(\);/.test(src)]);
checks.push(['echartsFor 助手存在', /function echartsFor/.test(src)]);
checks.push(['echartsFor 使用 >=3 次', count(/echartsFor\(/g) >= 3]);
checks.push(['无裸 cityData.reverse()', !/cityData\.reverse\(\)/.test(src)]);
checks.push(['needsRefresh 含 m-tab1', /'m-tab1':\s*'refreshRankTab'/.test(src)]);
checks.push(['refreshRankTab 已定义', /function refreshRankTab/.test(src)]);
checks.push(['calcCityGrowth 判空', /var cy = \(entry && entry\.yearly\) \|\| \{\};/.test(src)]);
checks.push(['无外部 CDN (jsdelivr/unpkg)', !/jsdelivr|unpkg|bootcdn/.test(html)]);
checks.push(['本地 echarts 引用', /src="assets\/echarts\.min\.js/.test(html)]);
checks.push(['无模板占位符残留', !/__[A-Z_0-9]+__/.test(html)]);

// needsRefresh 引用的函数是否都存在
const mapMatch = src.match(/var needsRefresh = \{([\s\S]*?)\};/);
if (mapMatch) {
  const pairs = [...mapMatch[1].matchAll(/'([^']+)':\s*'([^']+)'/g)];
  const missing = pairs.filter(([, , fn]) => !new RegExp('function\\s+' + fn + '\\s*\\(').test(src));
  checks.push(['needsRefresh ' + pairs.length + ' 项函数齐全', missing.length === 0]);
  if (missing.length) console.log('  缺失:', missing.map(p => p[2]));
}

// 裸 .yearly[ 访问（前后文无判空变量）
const bareYearly = [...src.matchAll(/[^.\w](\w+)\.yearly\[/g)].filter(m => {
  const before = src.slice(Math.max(0, m.index - 100), m.index);
  return !/iy|cy|yearly \|\||\|\| \{\}/.test(before);
});
checks.push(['无裸 .yearly[ 访问', bareYearly.length === 0]);
if (bareYearly.length) console.log('  裸访问:', bareYearly.map(m => m[0]).join(', '));

console.log('\n机器核对：');
for (const [name, pass] of checks) console.log('  ' + (pass ? 'PASS' : '**FAIL**') + '  ' + name);

process.exit(failed || checks.some(c => !c[1]) ? 1 : 0);
