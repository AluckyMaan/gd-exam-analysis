// 行为仿真：无法启动浏览器时，用自制 DOM/ECharts 桩真实执行看板 JS，抓运行时异常。
// 用法：node scripts/sim_dashboard.js <看板HTML路径>
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const htmlPath = process.argv[2];
if (!htmlPath) { console.error('用法: node sim_dashboard.js <看板HTML路径>'); process.exit(2); }
const html = fs.readFileSync(htmlPath, 'utf8');

// ── 从内联脚本里抽出数据变量声明行，注入沙箱（等价于浏览器里 script 执行时的全局）──
const inline = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
const dataVars = ['RANKING', 'RAW_RANKING', 'CO_PAIRS', 'CITY_YEARLY', 'CITY_RANKING',
  'CITY_EDUCATION', 'CITY_FRESH', 'CITY_MAJOR_MATRIX', 'ALL_MAJORS', 'CITY_NAME_MAP', 'GD_GEOJSON', 'YEARS'];
const dataLines = [];
const codeLines = [];
for (const line of inline.split('\n')) {
  const m = line.match(/^\s*var ([A-Z_0-9]+) = /);
  if (m && dataVars.includes(m[1])) dataLines.push(line);
  else codeLines.push(line);
}
const prelude = dataLines.join('\n') + '\n';
const code = codeLines.join('\n');
const missingData = dataVars.filter(v => !dataLines.some(l => l.startsWith('var ' + v + ' ')));
if (missingData.length) console.log('  [sim] 未抽到数据变量:', missingData.join(', '));

// ── DOM 桩 ──
const errors = [];
const echartsCalls = [];
let elSeq = 0;
function makeEl(id, tag) {
  const cls = new Set();
  const el = {
    __id: id || ('anon' + (++elSeq)), tagName: (tag || 'DIV').toUpperCase(),
    children: [], attributes: {}, style: {}, dataset: {},
    value: '', textContent: '', innerHTML: '',
    clientWidth: 1200, clientHeight: 480, offsetWidth: 1200, offsetHeight: 480,
    classList: {
      add: (...c) => c.forEach(x => cls.add(x)),
      remove: (...c) => c.forEach(x => cls.delete(x)),
      contains: (c) => cls.has(c),
      toggle: (c) => (cls.has(c) ? cls.delete(c) : cls.add(c)),
    },
    _cls: cls,
    get className() { return [...cls].join(' '); },
    set className(v) { cls.clear(); String(v).split(/\s+/).filter(Boolean).forEach(x => cls.add(x)); },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); return c; },
    remove() {},
    setAttribute(k, v) { this.attributes[k] = v; },
    getAttribute(k) { return this.attributes[k]; },
    addEventListener() {}, removeEventListener() {},
    querySelector(sel) { return queryAll(this, sel)[0] || null; },
    querySelectorAll(sel) { return queryAll(this, sel); },
    contains() { return false; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 1200, height: 480 }; },
    focus() {}, blur() {}, click() {},
    getContext() { return {}; },
    forEach(cb) { this.children.forEach(cb); },
    closest() { return null; },
  };
  return el;
}

const idRegistry = new Map();

function parseStaticIds(h) {
  for (const m of h.matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const id = m[1];
    const tag = (m[0].match(/^<(\w+)/) || [, 'div'])[1];
    const el = makeEl(id, tag);
    const cm = m[0].match(/class="([^"]*)"/);
    if (cm) el.className = cm[1];
    // select：解析 option，并让 value 取 selected 项或第一项（模拟浏览器默认行为）
    if (el.tagName === 'SELECT') {
      const block = h.slice(m.index, h.indexOf('</select>', m.index) + 9);
      const opts = [...block.matchAll(/<option[^>]*value="([^"]*)"([^>]*)>([\s\S]*?)<\/option>/g)]
        .map(o => ({ value: o[1], selected: /\bselected\b/.test(o[2]), text: o[3].trim() }));
      el.options = opts;
      const sel = opts.filter(o => o.selected);
      el.selectedOptions = sel;
      el.multiple = /multiple/.test(m[0]);
      el.value = (sel[0] || opts[0] || { value: '' }).value;
      // 支持 sel.options 赋值式伪数组访问
      opts.forEach((o, i) => { el[i] = o; });
      el.length = opts.length;
    }
    idRegistry.set(id, el);
  }
}

function queryAll(root, sel) {
  // 仅支持本仿真需要的选择器：#id、.class、tag、以及带 input:checked 的组合
  const text = String(sel).trim();
  let out = [];
  const all = [...idRegistry.values()];
  if (text.startsWith('#')) {
    const id = text.slice(1).split(/\s+/)[0];
    const el = idRegistry.get(id);
    if (el) out = [el];
  } else if (text.includes('input:checked')) {
    // '#compareGrid input:checked' —— 从注册表里取标记为 checked 的复选框桩
    out = [...idRegistry.values()].filter(e => e.tagName === 'INPUT' && e.checked === true);
  } else if (text.startsWith('.')) {
    const c = text.slice(1).split(/[\s,]+/)[0];
    out = all.filter(e => e._cls.has(c));
  } else {
    out = all.filter(e => e.tagName === text.toUpperCase());
  }
  return out;
}

parseStaticIds(html);

// 动态创建的复选框：initCompare 之外，chip 的 input 是静态 HTML 里的，需单独注册
function registerCheckboxes(h) {
  const grid = idRegistry.get('compareGrid') || makeEl('compareGrid');
  idRegistry.set('compareGrid', grid);
  const re = /<input type="checkbox" value=(\d+)([^>]*)>/g;
  let m, i = 0;
  while ((m = re.exec(h)) !== null) {
    const cb = makeEl('cb' + (++i), 'input');
    cb.value = m[1];
    cb.checked = /checked/.test(m[2]);
    grid.appendChild(cb);
    idRegistry.set(cb.__id, cb);          // 必须登记，否则 querySelectorAll('input:checked') 找不到
  }
  return grid.children.length;
}

const chipCount = registerCheckboxes(html);

const documentStub = {
  getElementById(id) { return idRegistry.get(id) || null; },
  querySelector(sel) { return queryAll(null, sel)[0] || null; },
  querySelectorAll(sel) { return queryAll(null, sel); },
  createElement(tag) { return makeEl(null, tag); },
  createElementNS(ns, tag) { return makeEl(null, tag); },
  addEventListener() {}, removeEventListener() {},
  body: makeEl('body'), documentElement: makeEl('html'),
  readyState: 'complete',
};

// ── ECharts 桩：记录每次调用参数，专门抓 init 参数是否合法 ──
function makeChartStub(id) {
  return {
    __id: id,
    setOption(opt) { echartsCalls.push({ id, fn: 'setOption', opt }); },
    resize() { echartsCalls.push({ id, fn: 'resize' }); },
    clear() { echartsCalls.push({ id, fn: 'clear' }); },
    dispose() {}, on() {}, off() {}, getOption() { return {}; },
    isDisposed() { return false; },
  };
}
const initLog = [];
const echartsStub = {
  init(arg) {
    const domEl = (arg && typeof arg === 'object') ? arg : null;
    initLog.push({ argType: typeof arg, argId: domEl ? domEl.__id : null, argIsNull: arg === null || arg === undefined });
    return makeChartStub(domEl ? domEl.__id : 'NULL_ARG');
  },
  getInstanceByDom(arg) { return arg ? makeChartStub(arg.__id) : null; },
  registerMap() {}, graphic: {}, connect() {}, dispose() {},
  version: '5.5.0-sim',
};

const sandbox = {
  console: { log: (...a) => {}, warn: (...a) => console.log('  [js warn]', ...a), error: (...a) => console.log('  [js error]', ...a) },
  document: documentStub,
  window: {}, navigator: { userAgent: 'sim' }, location: { href: 'file:///sim' },
  echarts: echartsStub,
  setTimeout: (fn) => { try { fn(); } catch (e) { errors.push('setTimeout: ' + e.message); } return 0; },
  clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  requestAnimationFrame: () => 0, cancelAnimationFrame() {},
  addEventListener() {}, removeEventListener() {},
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  IntersectionObserver: class { observe() {} unobserve() {} disconnect() {} },
  ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
  performance: { now: () => 0 },
  Math, JSON, Date, Object, Array, String, Number, Boolean, RegExp, Error, parseInt, parseFloat, isNaN, encodeURIComponent, decodeURIComponent,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
let compileOk = true;
try {
  new vm.Script(code, { filename: 'dashboard-inline.js' });
} catch (e) {
  compileOk = false;
  console.log('编译失败:', e.message);
}
if (compileOk) {
  try {
    vm.runInContext(prelude + '\n' + code, ctx, { filename: 'dashboard-inline.js', timeout: 20000 });
  } catch (e) {
    errors.push('执行期异常: ' + (e && e.name) + ': ' + (e && e.message));
    if (e && e.stack) errors.push('  栈: ' + e.stack.split('\n').slice(0, 4).join(' | '));
  }
}

// ── 报告 ──
console.log('='.repeat(70));
console.log('仿真结果');
console.log('='.repeat(70));
console.log('  静态 id 数          :', idRegistry.size);
console.log('  对比专业复选框数    :', chipCount, '（已勾选', [...idRegistry.values()].filter(e => e.tagName === 'INPUT' && e.checked).length, '）');
console.log('  echarts.init 调用次数:', initLog.length);
const badInit = initLog.filter(x => x.argIsNull);
console.log('  其中参数为空的 init  :', badInit.length, badInit.length ? '← 会导致 getElementById 返回 null 后报错/不渲染' : '');
console.log('  运行期异常数        :', errors.length);
for (const e of errors) console.log('    ! ' + e);

// 关键：确认 chip 的 onchange 目标函数是否存在且可调用
const fnNames = ['updateCompare', 'updateScorePanel', 'initCompare', 'renderMajorOverview', 'switchSubTab', 'resizeAll'];
console.log('\n  关键函数是否存在于沙箱:');
for (const f of fnNames) {
  let t = 'undefined';
  try { t = vm.runInContext('typeof ' + f, ctx); } catch (e) { t = 'err:' + e.message; }
  console.log('    %s %s', t === 'function' ? 'OK ' : 'MISS', f.padEnd(22) + ' (typeof=' + t + ')');
}

// 更贴近真实的"点击 chip"仿真：把一个复选框切成选中，再触发 onchange 指向的函数
console.log('\n  模拟点击 chip（勾选一个专业 → 触发 updateCompare）:');
const boxes = [...idRegistry.values()].filter(e => e.tagName === 'INPUT' && e.value !== '' && e.__id.startsWith('cb'));
if (boxes.length) {
  const target = boxes[3];                    // 挑一个初始未勾选的
  target.checked = true;
  const before = echartsCalls.length;
  try {
    vm.runInContext('updateCompare()', ctx, { timeout: 10000 });
    const opt = echartsCalls.slice(before).find(c => c.fn === 'setOption');
    const seriesN = opt && opt.opt && opt.opt.series ? opt.opt.series.length : 0;
    console.log('    勾选 value=%s → 调用成功；图表 series 数 = %d', target.value, seriesN);
    const cnt = idRegistry.get('compareSelectedCount');
    console.log('    「已选」文案 = %s', cnt ? JSON.stringify(cnt.textContent) : '(未找到元素)');
  } catch (e) {
    console.log('    **抛异常**: %s: %s', e.name, e.message);
  }
} else {
  console.log('    未找到复选框桩，跳过');
}
process.exit(errors.length || badInit.length ? 1 : 0);
