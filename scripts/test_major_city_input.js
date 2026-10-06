// 回归测试：「专业×地域」栏用输入框手打专业名 + 回车，图表/表格必须随之更新。
//
// 背景（本测试守护的 bug）：#majorSearch 曾经只绑了 oninput（刷候选）和 onchange（失焦才触发），
// 回车不做任何事；而且 updateMajorCity() 把 majorCurrent 放在取值优先级前面，而它只在点选
// 候选时才更新，于是手打的专业名永远被启动时注入的默认专业覆盖 —— 表现为「输入土木回车，表格不变」。
//
// 用法：node scripts/test_major_city_input.js [看板HTML路径]
// 不传路径时默认测根目录的 广东省考综合数据分析看板.html。
// 无浏览器可用时（Chromium 在受限沙箱内无法创建 mojo 通道）用自制 DOM/ECharts 桩真实执行看板 JS。
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const defaultHtml = path.join(__dirname, '..', '广东省考综合数据分析看板.html');
const htmlPath = process.argv[2] ? path.resolve(process.argv[2]) : defaultHtml;
const html = fs.readFileSync(htmlPath, 'utf8');

// ── 抽出内联脚本，并把数据变量声明与业务代码分离（同 上线前审核/scripts/sim_dashboard.js 的做法）──
const inline = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
const dataVars = ['RANKING', 'RAW_RANKING', 'CO_PAIRS', 'CITY_YEARLY', 'CITY_RANKING', 'CITY_EDUCATION',
  'CITY_FRESH', 'CITY_MAJOR_MATRIX', 'ALL_MAJORS', 'CITY_NAME_MAP', 'GD_GEOJSON', 'YEARS'];
const dataLines = [], codeLines = [];
for (const line of inline.split('\n')) {
  const m = line.match(/^\s*var ([A-Z_0-9]+) = /);
  if (m && dataVars.includes(m[1])) dataLines.push(line); else codeLines.push(line);
}
const prelude = dataLines.join('\n') + '\n';
const code = codeLines.join('\n');

// ── DOM 桩 ──
let elSeq = 0;
function makeEl(id, tag) {
  const cls = new Set();
  return {
    __id: id || ('anon' + (++elSeq)), tagName: (tag || 'DIV').toUpperCase(),
    children: [], parentNode: null, attributes: {}, style: {}, dataset: {}, value: '', textContent: '', innerHTML: '',
    options: [], selectedOptions: [],
    clientWidth: 1200, clientHeight: 480, offsetWidth: 1200, offsetHeight: 480,
    classList: {
      add: (...c) => c.forEach(x => cls.add(x)), remove: (...c) => c.forEach(x => cls.delete(x)),
      contains: (c) => cls.has(c), toggle: (c) => (cls.has(c) ? cls.delete(c) : cls.add(c)),
    },
    _cls: cls,
    get className() { return [...cls].join(' '); },
    set className(v) { cls.clear(); String(v).split(/\s+/).filter(Boolean).forEach(x => cls.add(x)); },
    appendChild(c) {
      if (c.parentNode) c.parentNode.children = c.parentNode.children.filter(x => x !== c);
      c.parentNode = this;
      this.children.push(c);
      // 动态 new Option 后要维护 options/selectedOptions，否则看板里的
      // Array.from(sel.options) / Array.from(sel.selectedOptions) 会拿到 undefined
      if (this.tagName === 'SELECT' && c.tagName === 'OPTION') {
        if (c.value === '' && c.textContent) c.value = c.textContent;
        this.options.push(c);
        if (c.selected) this.selectedOptions.push(c);
        if (!this.value) this.value = c.value;
      }
      return c;
    },
    removeChild(c) { this.children = this.children.filter(x => x !== c); return c; },
    remove() {}, setAttribute(k, v) { this.attributes[k] = v; }, getAttribute(k) { return this.attributes[k]; },
    addEventListener() {}, removeEventListener() {},
    querySelector(sel) { return queryAll(sel)[0] || null; }, querySelectorAll(sel) { return queryAll(sel); },
    // 真实 contains：沿 parentNode 上溯（桩里只对断言用到的嵌套显式建了父子关系）
    contains(node) {
      for (var n = node; n; n = n.parentNode) { if (n === this) return true; }
      return false;
    }, getBoundingClientRect() { return { left: 0, top: 0, width: 1200, height: 480 }; },
    focus() {}, blur() {}, click() {}, getContext() { return {}; },
    forEach(cb) { this.children.forEach(cb); }, closest() { return null; },
  };
}
const idRegistry = new Map();
for (const m of html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)) {
  const el = makeEl(m[1], (m[0].match(/^<(\w+)/) || [, 'div'])[1]);
  const cm = m[0].match(/class="([^"]*)"/); if (cm) el.className = cm[1];
  const dm = m[0].match(/data-subtab="([^"]*)"/); if (dm) el.dataset.subtab = dm[1];
  const vm2 = m[0].match(/\bvalue="([^"]*)"/); if (vm2) el.value = vm2[1];   // 关键：hidden input #majorDefault 的值
  if (el.tagName === 'SELECT') {
    const block = html.slice(m.index, html.indexOf('</select>', m.index) + 9);
    const opts = [...block.matchAll(/<option[^>]*value="([^"]*)"([^>]*)>([\s\S]*?)<\/option>/g)]
      .map(o => ({ value: o[1], selected: /\bselected\b/.test(o[2]), text: o[3].trim() }));
    el.options = opts; el.multiple = /multiple/.test(m[0]);
    el.selectedOptions = opts.filter(o => o.selected);
    el.value = (el.selectedOptions[0] || opts[0] || { value: '' }).value;
  }
  idRegistry.set(m[1], el);
}
function queryAll(sel) {
  const text = String(sel).trim(), all = [...idRegistry.values()];
  if (text.startsWith('#')) { const e = idRegistry.get(text.slice(1).split(/\s+/)[0]); return e ? [e] : []; }
  if (text.includes('input:checked')) return all.filter(e => e.tagName === 'INPUT' && e.checked === true);
  if (text.startsWith('.')) { const c = text.slice(1).split(/[\s,]+/)[0]; return all.filter(e => e._cls.has(c)); }
  return all.filter(e => e.tagName === text.toUpperCase());
}
// 记录 document 上的监听器：看板"点击空白处收起候选面板"用的是 document click，
// 桩里必须能真的派发它，否则这条交互等于没测（本次把候选项的 onclick 改成 onmousedown，
// 最需要防守的正是它与外部点击的配合）。
const docListeners = {};
const documentStub = {
  getElementById: (id) => idRegistry.get(id) || null,
  querySelector: (s) => queryAll(s)[0] || null,
  querySelectorAll: (s) => queryAll(s),
  createElement: (t) => makeEl(null, t), createElementNS: (ns, t) => makeEl(null, t),
  addEventListener(type, fn) { (docListeners[type] = docListeners[type] || []).push(fn); },
  removeEventListener() {},
  body: makeEl('body'), documentElement: makeEl('html'), readyState: 'complete',
};
function dispatchDocument(type, target) {
  (docListeners[type] || []).forEach(fn => fn({ target }));
  return (docListeners[type] || []).length;
}
// 静态 HTML 里 #majorOptions 嵌套在 #majorSearchWrap 内，但上面的 id 注册表是扁平的。
// 这里先从 HTML 源码核对这层嵌套确实存在，**核对通过才**补父子关系：
// 否则就是"桩手工捏造关系、测试再自证"，#majorOptions 被挪出 wrap 时测试仍会通过。
// 判据：wrap 的 id 与 panel 的 id 之间不应出现会关闭 wrap 的 </div>。
const _wrapEl = idRegistry.get('majorSearchWrap'), _panelEl = idRegistry.get('majorOptions');
const _wrapIdx = html.indexOf('id="majorSearchWrap"'), _panelIdx = html.indexOf('id="majorOptions"');
const PANEL_NESTED_IN_WRAP = _wrapIdx >= 0 && _panelIdx > _wrapIdx && !/<\/div>/.test(html.slice(_wrapIdx, _panelIdx));
if (PANEL_NESTED_IN_WRAP && _wrapEl && _panelEl) _panelEl.parentNode = _wrapEl;

// ── ECharts 桩：记录每个容器的 setOption/clear，供断言检查图表是否真的重绘 ──
const chartCalls = new Map();
function rec(id, fn, opt) {
  if (!chartCalls.has(id)) chartCalls.set(id, []);
  chartCalls.get(id).push({ fn, opt });
}
function makeChartStub(id) {
  return {
    __id: id, setOption: (opt) => rec(id, 'setOption', opt), resize: () => rec(id, 'resize'),
    clear: () => rec(id, 'clear'), dispose() {}, on() {}, off() {}, getOption: () => ({}), isDisposed: () => false,
  };
}
const echartsStub = {
  init: (arg) => makeChartStub(arg && arg.__id ? arg.__id : 'NULL_ARG'),
  getInstanceByDom: (arg) => (arg ? makeChartStub(arg.__id) : null),
  registerMap() {}, graphic: {}, connect() {}, dispose() {}, version: '5.5.0-sim',
};
function lastSet(id) {
  const c = (chartCalls.get(id) || []).filter(x => x.fn === 'setOption');
  return c.length ? c[c.length - 1].opt : null;
}

const errors = [];
const sandbox = {
  console: { log() {}, warn: (...a) => errors.push('js warn: ' + a.join(' ')), error: (...a) => errors.push('js error: ' + a.join(' ')) },
  document: documentStub, window: {}, navigator: { userAgent: 'sim' }, location: { href: 'file:///sim' },
  echarts: echartsStub,
  setTimeout: (fn) => { try { fn(); } catch (e) { errors.push('setTimeout: ' + e.message); } return 0; },
  clearTimeout() {}, setInterval: () => 0, clearInterval() {}, requestAnimationFrame: () => 0, cancelAnimationFrame() {},
  addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }),
  IntersectionObserver: class { observe() {} unobserve() {} disconnect() {} },
  ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
  performance: { now: () => 0 },
  Math, JSON, Date, Object, Array, String, Number, Boolean, RegExp, Error, parseInt, parseFloat, isNaN,
  encodeURIComponent, decodeURIComponent,
};
sandbox.window = sandbox; sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
try {
  vm.runInContext(prelude + '\n' + code, ctx, { filename: 'dashboard-inline.js', timeout: 30000 });
} catch (e) {
  errors.push('执行期异常: ' + e.name + ': ' + e.message);
}
// 沙箱自身的执行期问题先打出来（否则会表现为后续断言莫名失败）
if (errors.length) console.log('[harness] 沙箱执行期异常: ' + errors.join(' | '));
function ev(expr) { return vm.runInContext(expr, ctx); }          // 求值

// ── 断言框架 ──
let pass = 0, fail = 0;
const lines = [];
function ok(cond, msg) { if (cond) { pass++; lines.push('  PASS ' + msg); } else { fail++; lines.push('  FAIL ' + msg); } }
function info(msg) { lines.push('  info ' + msg); }

// 表格解析与期望值（期望值直接从页面内嵌数据算出，不硬编码）
function tableRows() {
  const wrap = documentStub.getElementById('majorCityTableWrap');
  const re = /<tr><td>(\d+)<\/td><td><strong>([^<]+)<\/strong><\/td><td>([^<]*)<\/td><td>(\d+)<\/td><td>([\d.]+)%<\/td><\/tr>/g;
  const out = []; let m;
  while ((m = re.exec(wrap.innerHTML)) !== null) out.push({ rank: +m[1], city: m[2], group: m[3], recruits: +m[4], pct: +m[5] });
  return out;
}
// 「按城市看热门专业」视图是 4 列表格（#/专业/招录/占比），与上面的 5 列结构不同
function tableRowsCityView() {
  const wrap = documentStub.getElementById('majorCityTableWrap');
  const re = /<tr><td>(\d+)<\/td><td><strong>([^<]+)<\/strong><\/td><td>(\d+)<\/td><td>([\d.]+)%<\/td><\/tr>/g;
  const out = []; let m;
  while ((m = re.exec(wrap.innerHTML)) !== null) out.push({ rank: +m[1], name: m[2], recruits: +m[3], pct: +m[4] });
  return out;
}
// setOption 的原始入参里 yAxis 是对象，getOption() 才会规范成数组，两种都要兼容
function axisOf(opt) {
  if (!opt || !opt.yAxis) return null;
  const y = Array.isArray(opt.yAxis) ? opt.yAxis[0] : opt.yAxis;
  return y && y.data ? y.data : null;
}
function titleOf(opt) { return opt && opt.title && opt.title.text ? String(opt.title.text) : ''; }
function expected(major) {
  const matrix = ev('CITY_MAJOR_MATRIX'), arr = [];
  for (const c in matrix) { const n = matrix[c][major] || 0; if (n > 0) arr.push({ city: c, n }); }
  arr.sort((a, b) => b.n - a.n);
  return arr;
}
const cityNames = (rows) => rows.map(r => r.city);
const sameList = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 还原真实交互：改值 → 触发 input → 触发回车 keydown
function typeAndEnter(v) {
  documentStub.getElementById('majorSearch').value = v;
  ev('filterMajorOptions()');
  if (ev('typeof onMajorSearchKeydown') === 'function') {
    vm.runInContext("onMajorSearchKeydown({ key: 'Enter', keyCode: 13, preventDefault: function(){} })", ctx);
  }
}
function setSearchValue(v) { documentStub.getElementById('majorSearch').value = v; ev('filterMajorOptions()'); }

try {
  // ═══ 0. 静态接线：输入框必须真的绑上回车与提交函数 ═══
  info('被测文件: ' + htmlPath);
  // 取出 <input id="majorSearch" ...> 这一个完整标签，断言属性确实在同一个标签内
  // （不能用宽松的"id 之后 N 个字符内出现"式正则，否则可能跨标签误判为通过）
  const inputTag = (html.match(/<input[^>]*\bid="majorSearch"[^>]*>/) || [''])[0];
  ok(inputTag !== '', '能定位到 #majorSearch 的 <input> 标签');
  ok(/onkeydown="onMajorSearchKeydown\(event\)"/.test(inputTag), '输入框已绑定 onkeydown 回车处理（同一标签内）');
  ok(/onchange="commitMajorInput\(\)"/.test(inputTag), '输入框 onchange 已指向 commitMajorInput()');
  ok(!/onchange="updateMajorCity\(\)"/.test(inputTag), '不再使用旧的 onchange="updateMajorCity()" 接线');
  ok(/oninput="filterMajorOptions\(\)"/.test(inputTag), 'oninput 仍保留候选列表过滤');
  ok(/onmousedown="selectMajorOption\(/.test(html), '候选项目用 onmousedown 选中（保证先于输入框 change 触发）');
  ok(ev('typeof onMajorSearchKeydown') === 'function' && ev('typeof commitMajorInput') === 'function'
     && ev('typeof resolveMajorName') === 'function' && ev('typeof showMajorEmptyState') === 'function',
     '回车/提交/归一化/空状态 四个函数都已定义');

  // ═══ 1. 首屏默认（应显示 #majorDefault 指定的专业） ═══
  const defMajor = documentStub.getElementById('majorDefault').value;
  const base = tableRows();
  info('默认专业 = ' + defMajor + '；初始表格 ' + base.length + ' 行，首位 = ' + (base[0] ? base[0].city + '/' + base[0].recruits : '-'));
  ok(base.length > 0 && sameList(cityNames(base), cityNames(expected(defMajor))), '首屏按默认专业「' + defMajor + '」渲染');

  // ═══ 2. 核心场景：手打「土木」+ 回车 ═══
  typeAndEnter('土木');
  const got = tableRows(), exp = expected('土木');
  info('回车「土木」后 ' + got.length + ' 行，首位 = ' + (got[0] ? got[0].city + '/' + got[0].recruits : '-')
       + '；数据源首位 = ' + (exp[0] ? exp[0].city + '/' + exp[0].n : '-'));
  ok(got.length > 0, '回车后表格非空');
  ok(sameList(cityNames(got), cityNames(exp)), '表格城市顺序与内嵌数据源完全一致');
  ok(got.reduce((s, r) => s + r.recruits, 0) === exp.reduce((s, e) => s + e.n, 0), '招录合计与数据源一致');
  ok(!sameList(cityNames(got), cityNames(base)), '★表格确实随「土木」改变（不再停留在默认专业）');
  const opt = lastSet('majorCityChart');
  const axis = axisOf(opt);
  ok(axis && sameList(axis, cityNames(exp).slice().reverse()), '★图表坐标轴同步更新为「土木」（反转顺序正确、未错位）');
  ok(documentStub.getElementById('majorSearch').value === '土木', '输入框保留专业名「土木」');
  ok(got.every(r => r.pct === Math.round(r.recruits / exp.reduce((s, e) => s + e.n, 0) * 1000) / 10), '占比列数值与数据源自洽');

  // ═══ 2c. 未提交的半截输入不得污染被动刷新路径（切 Tab / 切视图 → updateMajorCity）═══
  // 用户打「土」往往只是为了筛候选、并不点选；此时切走再切回（needsRefresh 或切视图）
  // 应当回到"最近一次确认"的专业，而不是把图表清空成"未找到专业「土」"。
  const confirmed = cityNames(tableRows());
  setSearchValue('土');                                  // 未回车、未失焦，仅筛候选
  ev('updateMajorCity()');                               // 被动刷新走的就是这个入口
  const passiveOpt = lastSet('majorCityChart');
  info('未提交的「土」被动刷新后 ' + tableRows().length + ' 行，图表标题 = ' + JSON.stringify(titleOf(passiveOpt)));
  ok(sameList(cityNames(tableRows()), confirmed), '★未提交的半截输入在被动刷新时回退到最近确认的专业（不清空图表）');
  ok(titleOf(passiveOpt).indexOf('未找到') < 0, '被动刷新不会显示「未找到」空状态');

  // ═══ 3. 未匹配：必须给提示，不能静默 ═══
  typeAndEnter('土木工程类');
  const optBad = lastSet('majorCityChart');
  const badTitle = optBad && optBad.title && optBad.title.text ? String(optBad.title.text) : '';
  info('未匹配时表格 ' + tableRows().length + ' 行，图表标题 = ' + JSON.stringify(badTitle));
  ok(tableRows().length === 0, '未匹配时表格清空');
  ok(badTitle.indexOf('未找到专业') === 0, '★未匹配时图表显示「未找到专业」提示（旧版是静默无反应）');

  // ═══ 4. 失焦（change → commitMajorInput）路径 ═══
  setSearchValue('土木类');
  if (ev('typeof commitMajorInput') === 'function') vm.runInContext('commitMajorInput()', ctx);
  const g3 = tableRows(), e3 = expected('土木类');
  ok(g3.length > 0 && sameList(cityNames(g3), cityNames(e3)), '失焦(change) 同样能切换到「土木类」');

  // ═══ 5. 点选候选路径未被破坏 ═══
  ev("selectMajorOption('建筑类')");
  const g4 = tableRows(), e4 = expected('建筑类');
  ok(g4.length > 0 && sameList(cityNames(g4), cityNames(e4)), '点选下拉候选仍正常（建筑类）');

  // ═══ 5b. 真实事件顺序：输入半截 → 点候选(onmousedown) → 输入框随之失焦 change ═══
  // 这是把 onclick 换成 onmousedown 的原因：mousedown 先执行会把规范名写回输入框，
  // 随后的 change 读到的就是合法值，不会先闪一下「未找到」再被纠正。
  setSearchValue('土木工');                        // 半截、非精确匹配
  ev("selectMajorOption('土木工程')");             // 候选项 onmousedown 的处理函数
  if (ev('typeof commitMajorInput') === 'function') vm.runInContext('commitMajorInput()', ctx);  // 随后的 change
  const g5 = tableRows(), e5 = expected('土木工程'), opt5 = lastSet('majorCityChart');
  ok(documentStub.getElementById('majorSearch').value === '土木工程', '点选候选后输入框被回写为规范专业名');
  ok(sameList(cityNames(g5), cityNames(e5)), '半截输入 + 点选候选后最终停在所选专业（土木工程）');
  // 显式断言"画的是数据图"：不能因为"没有 title"就蒙混通过（原写法在 opt5 为 null 时会恒真）
  ok(axisOf(opt5) !== null && sameList(axisOf(opt5), cityNames(e5).slice().reverse()) && titleOf(opt5) === '',
     '点选候选后图表是正常数据图（有坐标轴数据、无空状态标题）');

  // ═══ 5c. 候选面板与"点击空白处收起"的配合（onmousedown 改造后最需防守的交互）═══
  // 看板用 document 上的 click 监听 + wrap.contains(e.target) 判断是否收起面板。
  // 桩里必须真实派发这个监听器，否则这条逻辑等于没测。
  const panelEl = documentStub.getElementById('majorOptions');
  setSearchValue('土木');
  info('document 上的 click 监听器数量 = ' + (docListeners['click'] || []).length);
  // 注意：filterMajorOptions() 展开面板时写的是 ''，桩初始 display 为 undefined，
  // 所以这里必须断言 === ''（只断言 !== 'none' 会近似恒真）
  ok(panelEl.style.display === '', '输入后候选面板展开');
  ok(PANEL_NESTED_IN_WRAP, '#majorOptions 在 HTML 源码里嵌于 #majorSearchWrap 内（桩的父子关系来自源码核对，非手工捏造）');
  dispatchDocument('click', documentStub.createElement('div'));            // 点在 wrap 之外
  ok(panelEl.style.display === 'none', '点击面板外（wrap 之外）收起候选面板');
  setSearchValue('土木');
  // 把"监听器确实被派发过"并入断言，让这条断言局部自足（否则监听器压根没跑也会通过）
  ok(dispatchDocument('click', panelEl) >= 1 && panelEl.style.display !== 'none', '点击候选面板内部不会误收起');

  // ═══ 6. 专业名归一化 ═══
  if (ev('typeof resolveMajorName') === 'function') {
    ev("ALL_MAJORS.push('TEST-MBA')");
    ok(ev("resolveMajorName('test-mba')") === 'TEST-MBA', '大小写兜底：test-mba → TEST-MBA');
    ev('ALL_MAJORS.pop()');
    ok(ev("resolveMajorName('土木')") === '土木', '精确命中：土木 → 土木');
    ok(ev("resolveMajorName('不存在的专业')") === '', '未命中返回空串（交由调用方给提示）');
    ok(ev("resolveMajorName(' 土木 ')") === '土木', '归一化内部也 trim（容忍首尾空格）');
  } else {
    ok(false, 'resolveMajorName 未定义'); ok(false, 'resolveMajorName 未定义'); ok(false, 'resolveMajorName 未定义');
  }
  // 带空格粘贴 → 回车仍需命中（真实输入法/复制粘贴常见）
  typeAndEnter('  土木  ');
  ok(documentStub.getElementById('majorSearch').value === '土木' && sameList(cityNames(tableRows()), cityNames(expected('土木'))),
     '粘贴「  土木  」回车后正常命中并回写规范名');

  // ═══ 7. 空输入 ═══
  typeAndEnter('');
  const optEmpty = lastSet('majorCityChart');
  const emptyTitle = optEmpty && optEmpty.title && optEmpty.title.text ? String(optEmpty.title.text) : '';
  ok(emptyTitle.indexOf('请输入专业名') === 0 && tableRows().length === 0, '空输入回车给出「请输入专业名」提示');

  // ═══ 7b. 输入法组合期间的回车不能被当成"提交搜索" ═══
  // 中文用户敲「tumu」→ 候选框打开 → 回车确认「土木」；这一下 Enter 必须被放行，
  // 否则会在候选字落进输入框之前就去查，误报"未找到专业"。
  setSearchValue('建筑类');
  if (ev('typeof commitMajorInput') === 'function') vm.runInContext('commitMajorInput()', ctx);
  const beforeIme = cityNames(tableRows());
  documentStub.getElementById('majorSearch').value = 'tumu';   // 模拟输入法组合中的拼音
  if (ev('typeof onMajorSearchKeydown') === 'function') {
    vm.runInContext("onMajorSearchKeydown({ key: 'Enter', keyCode: 229, isComposing: true, preventDefault: function(){ throw new Error('组合期间不应 preventDefault'); } })", ctx);
  }
  ok(sameList(cityNames(tableRows()), beforeIme), '输入法组合期间的回车被放行，不提交搜索、不改动图表');
  ok(documentStub.getElementById('majorSearch').value === 'tumu', '组合期间的输入内容原样保留（交给输入法处理）');

  // ═══ 8. 另一个视图不受影响 ═══
  documentStub.getElementById('majorCityView').value = 'city_to_major';
  ev('switchMajorCityView()');
  documentStub.getElementById('citySelect').value = '广州';
  ev('updateMajorCity()');
  const cityRows = tableRowsCityView();
  const gzTop = Object.entries(ev("CITY_MAJOR_MATRIX['广州']")).sort((a, b) => b[1] - a[1])[0];
  const gzMajorCount = Object.keys(ev("CITY_MAJOR_MATRIX['广州']")).length;
  const topN = Math.min(20, gzMajorCount);          // Top N 由数据量推导，不写死字面量
  info('「按城市看热门专业」广州 Top' + topN + ' 首行 = ' + (cityRows[0] ? cityRows[0].name + '/' + cityRows[0].recruits : '-')
       + '；数据源首位 = ' + gzTop[0] + '/' + gzTop[1]);
  ok(cityRows.length === topN, '「按城市看热门专业」视图仍正常（广州共 ' + gzMajorCount + ' 个专业，显示 Top' + topN + '，实际 ' + cityRows.length + ' 行）');
  ok(cityRows.length > 0 && cityRows[0].name === gzTop[0] && cityRows[0].recruits === gzTop[1], '该视图首行为数据源中广州招录最多的专业');

  // ═══ 9. 切回后输入框仍生效（needsRefresh 走的就是 updateMajorCity） ═══
  documentStub.getElementById('majorCityView').value = 'major_to_city';
  ev('switchMajorCityView()');
  typeAndEnter('土木');
  const g9 = tableRows();
  ok(g9.length > 0 && sameList(cityNames(g9), cityNames(expected('土木'))), '切回「按专业看城市分布」后「土木」仍正常');

  // ═══ 10. 无运行期异常 ═══
  ok(errors.length === 0, '看板 JS 在仿真中无运行期异常' + (errors.length ? ' → ' + errors.slice(0, 4).join(' | ') : ''));
} catch (e) {
  fail++;
  lines.push('  FAIL 测试自身异常: ' + e.name + ': ' + e.message + ' @ ' + String(e.stack).split('\n')[1]);
}

// ═══ 已知未被本测试覆盖的路径（勿把它们当作"已验证"来依赖）═══
// 这两条都属防御性代码，界面流程进不去，靠变异测试也抓不到（审查者 M6/M8 两个变体均存活）：
//   1) showMajorEmptyState() 中"图表实例不存在(majorCityChart===null)时仍清空表格"——
//      正常运行中 initMajorCityTab() 先建实例再渲染，该状态不可达；
//   2) updateMajorCity() 里的未匹配保险网分支——commitMajorInput() 未匹配时已提前 return，
//      只有直接调用全局函数 selectMajorOption('不存在的专业') 之类的外部路径才会命中。

console.log('='.repeat(72));
console.log('「专业×地域」输入专业名 + 回车 行为回归测试');
console.log('='.repeat(72));
lines.forEach(l => console.log(l));
console.log('-'.repeat(72));
console.log('  合计: ' + pass + ' 项通过, ' + fail + ' 项失败');
process.exit(fail ? 1 : 0);
