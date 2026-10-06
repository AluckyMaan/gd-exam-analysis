// 真实浏览器端到端测试：「专业×地域」栏
//
// 为什么需要它：DOM/ECharts 桩（scripts/test_major_city_input.js）没有 CSS 级联，也没有真实输入管线，
// 因此看不见两类问题 ——
//   ① CSS 与内联样式冲突（例：.mcs-panel 的 CSS 默认 display:none，而 JS 用 style.display='' 去"显示"，
//      置空等于删掉内联值，面板永远不出现。桩里这一行看起来完全正常，测试全绿）；
//   ② 真实事件序列（mousedown/change 的先后、输入法组合态、真实键盘与鼠标）。
// 本脚本用 Chrome DevTools Protocol 驱动**已安装的 Edge**（无 npm 依赖：Node 22+ 自带 WebSocket 与 fetch）。
//
// 用法：
//   node scripts/e2e_major_city.mjs [看板HTML路径] [--out 截图目录] [--headful]
// 退出码：0 = 全部通过或环境不具备（打印 SKIP）；1 = 有断言失败。
import { spawn, spawnSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { existsSync, mkdirSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

// ── 参数 ──
const argv = process.argv.slice(2);
const headful = argv.includes('--headful');
const outIdx = argv.indexOf('--out');
// 必须绝对路径：Edge 对相对的 --user-data-dir 解析基准不是我们的工作目录，会直接起不来
const outDir = path.resolve(outIdx >= 0 ? argv[outIdx + 1] : path.join(tmpdir(), 'gd-exam-e2e'));
// 位置参数 = 除选项及其取值之外的第一个（否则会把 --out 的取值当成看板路径）
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--out') { i++; continue; }
  if (argv[i].startsWith('--')) continue;
  positional.push(argv[i]);
}
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const board = path.resolve(positional[0] || path.join(scriptDir, '..', '广东省考综合数据分析看板.html'));
const PORT = 9333;

const CANDIDATES = [
  process.env.EDGE_PATH,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/microsoft-edge', '/usr/bin/google-chrome', '/usr/bin/chromium',
].filter(Boolean);
const browser = CANDIDATES.find((p) => existsSync(p));

function skip(msg) { console.log('SKIP: ' + msg); process.exit(0); }
if (!existsSync(board) || !statSync(board).isFile()) skip('看板文件不存在或不是文件: ' + board);
if (!browser) skip('未找到 Chromium 系浏览器（可用 EDGE_PATH 指定）');
if (typeof WebSocket !== 'function') skip('当前 Node 无内置 WebSocket（需 Node 22+）');

mkdirSync(outDir, { recursive: true });
const profile = path.join(outDir, 'profile');
const proc = spawn(browser, [
  headful ? '--headless=old' : '--headless=new',
  '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
  '--allow-file-access-from-files', '--hide-scrollbars',
  `--user-data-dir=${profile}`, `--remote-debugging-port=${PORT}`, 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });
// 收集浏览器 stderr：启动失败时才有线索可查（GUI 进程的 stdout 抓不到，stderr 可以）
let errTail = '';
proc.stderr?.on('data', (d) => { errTail = (errTail + d.toString()).slice(-1500); });

let cleaned = false;
let browserWs = null;      // browser 级 WS 连接（只用于 Browser.close）
// 关浏览器要"先 CDP 后杀树"：Edge 的启动器会把工作交给真正的浏览器进程后自行退出，
// 于是 kill(launcher) 或 taskkill /PID launcher 都可能落空（实测会残留 20+ 个 msedge）。
// 先通过 browser 级 WS 发 Browser.close 让浏览器自己收尾，再补 taskkill 兜底。
const cleanup = () => {
  if (cleaned) return; cleaned = true;
  try { browserWs?.send(JSON.stringify({ id: 99999, method: 'Browser.close' })); } catch { /* ignore */ }
  try {
    if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(proc.pid), '/T', '/F'], { stdio: 'ignore' });
    else process.kill(-proc.pid, 'SIGKILL');
  } catch { /* ignore */ }
};
process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(130); });

let pass = 0, fail = 0;
const lines = [];
const ok = (cond, msg) => { if (cond) { pass++; lines.push('  PASS ' + msg); } else { fail++; lines.push('  FAIL ' + msg); } };
const info = (msg) => lines.push('  info ' + msg);

try {
  // ── 等 CDP 端口 ──
  let ver = null;
  for (let i = 0; i < 80 && !ver; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) ver = await r.json(); } catch { /* retry */ }
    if (!ver) await sleep(250);
  }
  if (!ver) {
    console.log('浏览器 stderr 末尾（诊断用）:\n' + (errTail || '  (无输出)'));
    skip('CDP 端口未就绪（浏览器无法在当前环境启动）: ' + browser + '\n  profile: ' + profile + '\n  若为沙箱限制，请放宽后再跑；若是端口占用，先关掉残留的 msedge 进程');
  }
  info('浏览器: ' + ver.Browser + '（' + browser + '）');
  try {
    browserWs = new WebSocket(ver.webSocketDebuggerUrl);
    await new Promise((res, rej) => { browserWs.onopen = res; browserWs.onerror = rej; });
  } catch { browserWs = null; }

  const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let seq = 0; const pending = new Map(); const exceptions = []; const consoleErrors = [];
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params?.exceptionDetails?.exception?.description || m.params?.exceptionDetails?.text);
    if (m.method === 'Runtime.consoleAPICalled' && m.params?.type === 'error') consoleErrors.push((m.params.args || []).map((a) => a.value ?? a.description).join(' '));
  };
  const send = (method, params = {}) => new Promise((res) => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
  const evalIn = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.result?.exceptionDetails) throw new Error('页面求值异常: ' + (r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text) + '\n  表达式: ' + expression.slice(0, 120));
    return r.result?.result?.value;
  };
  const shot = async (name) => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    if (!r.result?.data) return null;
    const p = path.join(outDir, name + '.png');
    writeFileSync(p, Buffer.from(r.result.data, 'base64'));
    return p;
  };
  const key = async (k, code, vk) => {
    for (const type of ['keyDown', 'keyUp']) {
      await send('Input.dispatchKeyEvent', { type, key: k, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk });
    }
  };
  const clickEl = async (selector) => {
    const rect = await evalIn(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
      const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height }; })()`);
    if (!rect || rect.w === 0 || rect.h === 0) return null;
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rect.x, y: rect.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rect.x, y: rect.y, button: 'left', clickCount: 1 });
    return rect;
  };
  const typeInto = async (text) => {
    await evalIn("document.getElementById('majorSearch').focus()");
    await evalIn("document.getElementById('majorSearch').value = ''");   // 清空（等价于全选删除）
    await evalIn("document.getElementById('majorSearch').dispatchEvent(new Event('input',{bubbles:true}))");
    for (const ch of text) await send('Input.insertText', { text: ch });
  };
  // 面板"是否真的可见"：结合计算样式与布局盒（这才是有 CSS 级联的判断）
  const panelState = async () => evalIn(`(() => {
    const p = document.getElementById('majorOptions');
    const cs = getComputedStyle(p); const r = p.getBoundingClientRect();
    return { display: cs.display, visibility: cs.visibility, height: Math.round(r.height),
             items: p.querySelectorAll('.mcs-item').length, text: (p.textContent || '').slice(0, 40) };
  })()`);
  const tableState = async () => evalIn(`(() => {
    const rows = [...document.querySelectorAll('#majorCityTableWrap tbody tr')];
    return { count: rows.length, first: rows[0] ? rows[0].innerText.replace(/\\s+/g, ' ').trim() : '' };
  })()`);
  const chartState = async () => evalIn(`(() => {
    const o = echarts.getInstanceByDom(document.getElementById('majorCityChart')).getOption();
    return { title: o.title && o.title[0] ? String(o.title[0].text || '') : '',
             axis: o.yAxis && o.yAxis[0] && o.yAxis[0].data ? o.yAxis[0].data.length : 0 };
  })()`);
  const expectCities = (major) => evalIn(`(() => { const a = [];
    for (const c in CITY_MAJOR_MATRIX) { const n = CITY_MAJOR_MATRIX[c][${JSON.stringify(major)}] || 0; if (n > 0) a.push([c, n]); }
    a.sort((x, y) => y[1] - x[1]); return { count: a.length, top: a[0] ? a[0][0] + '/' + a[0][1] : '-' }; })()`);

  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: pathToFileURL(board).href });
  for (let i = 0; i < 60; i++) {
    const ready = await evalIn("typeof switchSection === 'function' && !!window.echarts").catch(() => false);
    if (ready) break;
    await sleep(250);
  }
  await sleep(600);

  // ═══ 1. 页面本身 ═══
  const loaded = await evalIn("JSON.stringify({ majors: ALL_MAJORS.length, charts: typeof echarts, ec: echarts.version, rows: document.querySelectorAll('#majorCityTableWrap tbody tr').length })");
  info('页面状态: ' + loaded);
  const st = JSON.parse(loaded);
  ok(st.majors === 1580, '看板载入：ALL_MAJORS = ' + st.majors + ' 条');
  ok(String(st.ec).startsWith('5'), '本地 ECharts 已加载（v' + st.ec + '，无 CDN 依赖）');
  ok(st.rows > 0, '首屏 ' + st.rows + ' 行的表格已渲染（不是空白页）');

  // ═══ 2. 切到「专业×地域」 ═══
  await evalIn("switchSection('section2')");
  await evalIn("switchSubTab('c-tab5', document.querySelector('[data-subtab=\"c-tab5\"]'))");
  await sleep(700);
  const visible = await evalIn(`(() => { const r = document.getElementById('majorCityChart').getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height), tab: document.getElementById('c-tab5').classList.contains('active') }; })()`);
  info('图表容器: ' + JSON.stringify(visible));
  ok(visible.tab && visible.w > 300 && visible.h > 200, '「专业×地域」栏已展开且图表容器有真实尺寸（' + visible.w + '×' + visible.h + '）');
  const shot0 = await shot('e2e-0-tab5-default');

  // ═══ 3. 输入半截专业名 → 候选下拉必须真的可见（CSS 级联下的判断）═══
  await typeInto('电子');
  await sleep(400);
  const p1 = await panelState();
  const expElec = await evalIn("ALL_MAJORS.filter(function(m){return m.toLowerCase().indexOf('电子')>=0;}).length");
  info('输入「电子」后候选面板: ' + JSON.stringify(p1) + '；数据源匹配 ' + expElec + ' 个');
  ok(p1.display !== 'none' && p1.visibility !== 'hidden' && p1.height > 0,
     '★真实浏览器里候选面板可见（computed display=' + p1.display + '，高度 ' + p1.height + 'px）');
  ok(p1.items > 0 && p1.items === Math.min(60, expElec), '★候选列表渲染出 ' + p1.items + ' 条匹配项');
  ok(/电子/.test(p1.text), '候选内容确实是匹配「电子」的专业');
  const shot1 = await shot('e2e-1-dropdown-electron');

  // ═══ 4. 回车提交半截名 → 明确提示（且候选仍在，可继续挑）═══
  await key('Enter', 'Enter', 13);
  await sleep(500);
  const c1 = await chartState(); const p2 = await panelState();
  info('回车后: 图表标题=' + JSON.stringify(c1.title) + '，面板 display=' + p2.display + '/' + p2.height + 'px');
  ok(c1.title.indexOf('未找到专业') === 0, '回车提交非精确名 → 给出「未找到专业」提示（不再静默无反应）');
  ok(p2.display !== 'none' && p2.height > 0, '提示的同时候选面板保持可见，用户可直接点选');
  const shot2 = await shot('e2e-2-enter-partial');

  // ═══ 5. 真实鼠标点选候选项 → 图表与表格切换到该专业 ═══
  const picked = await evalIn("document.querySelector('#majorOptions .mcs-item').textContent.trim()");
  const clicked = await clickEl('#majorOptions .mcs-item');
  await sleep(600);
  const t1 = await tableState(); const exp1 = await expectCities(picked); const inp1 = await evalIn("document.getElementById('majorSearch').value");
  info('点选「' + picked + '」→ 表格 ' + t1.count + ' 行，首位 ' + t1.first + '；数据源 ' + exp1.count + ' 个城市，首位 ' + exp1.top);
  ok(clicked !== null, '候选项可被真实鼠标命中（' + (clicked ? Math.round(clicked.w) + '×' + Math.round(clicked.h) + 'px' : '不可点击') + '）');
  ok(inp1 === picked, '点选后输入框回写为规范专业名「' + inp1 + '」');
  ok(t1.count === exp1.count && exp1.count > 0, '表格行数与数据源一致（' + t1.count + ' 行）');
  ok(t1.first.indexOf(exp1.top.split('/')[0]) >= 0, '表格首位城市与数据源首位一致（' + exp1.top + '）');
  const shot3 = await shot('e2e-3-after-pick');

  // ═══ 6. 用户最初报告的场景：手打「土木」+ 回车 ═══
  const before = await tableState();
  await typeInto('土木');
  await key('Enter', 'Enter', 13);
  await sleep(600);
  const t2 = await tableState(); const exp2 = await expectCities('土木'); const c2 = await chartState();
  info('手打「土木」+回车 → 表格 ' + t2.count + ' 行，首位 ' + t2.first + '；数据源 ' + exp2.count + ' 个城市，首位 ' + exp2.top + '；图表轴 ' + c2.axis + ' 项');
  ok(t2.count === exp2.count && exp2.count > 0, '★回车后表格确实切到「土木」（' + t2.count + ' 行，此前 ' + before.count + ' 行）');
  ok(t2.first.indexOf(exp2.top.split('/')[0]) >= 0, '★表格首位与数据源首位一致（' + exp2.top + '）');
  ok(c2.axis === exp2.count, '★图表坐标轴城市数与表格一致（' + c2.axis + '）');
  ok(c2.title === '', '图表处于正常数据态（无空状态标题）');
  const shot4 = await shot('e2e-4-tumu-enter');

  // ═══ 7. 全程无页面异常 ═══
  ok(exceptions.length === 0, '页面无未捕获异常' + (exceptions.length ? ' → ' + exceptions.slice(0, 3).join(' | ') : ''));
  ok(consoleErrors.length === 0, '控制台无 error 级输出' + (consoleErrors.length ? ' → ' + consoleErrors.slice(0, 3).join(' | ') : ''));
  info('截图: ' + [shot0, shot1, shot2, shot3, shot4].filter(Boolean).join(' , '));
} catch (e) {
  fail++;
  lines.push('  FAIL 测试异常: ' + e.message);
}

console.log('='.repeat(72));
console.log('真实浏览器 E2E：「专业×地域」输入/候选/回车（CDP 驱动 Edge）');
console.log('='.repeat(72));
lines.forEach((l) => console.log(l));
console.log('-'.repeat(72));
console.log('  合计: ' + pass + ' 项通过, ' + fail + ' 项失败');
cleanup();
process.exit(fail ? 1 : 0);
