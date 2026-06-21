# 移动端与微信网页适配 Todo

目标：让当前数据看板在手机浏览器，尤其是微信内置浏览器中可读、可点、可横滑、图表稳定显示。

优先处理主页面：

- `广东省考综合数据分析看板.html`

验证稳定后，再把通用做法同步到其它专题 HTML 页面。

## 0. 适配目标

- [ ] 优先支持微信内置浏览器竖屏访问。
- [ ] 重点检查宽度：360px、375px、390px、414px、430px。
- [ ] 页面整体不应出现横向滚动。
- [ ] 表格可以在表格容器内部横向滑动。
- [ ] 图表不能空白、压扁、截断或明显溢出。
- [ ] Tab、筛选器、按钮、弹窗在手机上都能正常点击。

## 1. Head 与微信基础适配

- [x] 将 viewport 改为：

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

- [x] 在全局 CSS 中加入：

```css
html {
  -webkit-text-size-adjust: 100%;
}
```

- [x] 给页面容器加入安全区兼容，避免 iPhone 刘海屏或微信底部区域遮挡：

```css
.container {
  padding-left: max(14px, env(safe-area-inset-left));
  padding-right: max(14px, env(safe-area-inset-right));
  padding-bottom: max(40px, env(safe-area-inset-bottom));
}
```

- [ ] 检查微信中 Google Fonts 是否加载失败或变慢。
- [ ] 检查 `https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js` 在微信中是否稳定加载。
- [ ] 如 CDN 不稳定，考虑把 ECharts 下载到本地，例如 `assets/echarts.min.js`。
- [ ] 对外分享时优先分享 `index.html`，避免直接分享中文文件名 URL。

## 2. 建立集中式移动端 CSS 补丁

- [x] 在主 HTML 的 `<style>` 末尾新增一个清晰区块：

```css
/* ===== Mobile / WeChat Adaptation ===== */
```

- [x] 保留现有 `@media (max-width: 768px)`，再补充：

```css
@media (max-width: 560px) { }
@media (max-width: 430px) { }
```

- [x] 移动端收紧 `.container`、`.hero`、`.sub-tab-content` 的 padding。
- [x] Hero 标题降低字号和行高。
- [x] Hero 副标题允许自然换行，不要依赖一整行展示。
- [x] `.stats-bar` 在手机上改为两列或单列。
- [x] `.status-dot` 在手机上改为普通流式位置，避免绝对定位遮挡内容。

## 3. 导航与 Tab

- [x] `.section-nav` 移动端改为横向滚动。
- [x] `.sub-tabs` 移动端改为横向滚动。
- [x] 给横向滚动容器增加：

```css
overflow-x: auto;
flex-wrap: nowrap;
-webkit-overflow-scrolling: touch;
scrollbar-width: none;
```

- [x] 给 `.section-btn`、`.sub-tab-btn` 增加：

```css
flex: 0 0 auto;
min-height: 40px;
```

- [ ] 检查每个 Tab 在 375px 宽度下是否仍然可点击。
- [x] Tab 切换后确认图表会重新 resize。

## 4. 筛选栏与表单控件

- [x] `.select-bar` 在移动端改为纵向或多行布局。
- [x] 移动端覆盖所有 `select`、`input`：

```css
.select-bar select,
.select-bar input {
  width: 100%;
  max-width: none !important;
  min-width: 0 !important;
}
```

- [x] 检查 HTML 中的内联样式，例如 `min-width:260px`、`max-width:280px`，确保移动端 CSS 能覆盖。
- [x] 多选框控件在手机上不要过高，必要时限制高度并允许内部滚动。
- [x] 对比专业的 chip 区域要能滚动，不能撑爆页面。

## 5. ECharts 图表容器

- [x] 移动端降低图表固定高度。
- [x] 建议补丁：

```css
@media (max-width: 560px) {
  .chart-box { height: clamp(300px, 86vw, 440px); }
  .chart-box-sm { height: clamp(280px, 78vw, 380px); }
  .chart-box-map { height: clamp(360px, 95vw, 480px); }
  .network-wrap { height: clamp(420px, 115vw, 560px); }
}
```

- [x] 地图、网络图在移动端优先减少标签显示。
- [x] 横向柱状排名图在移动端减少默认展示数量，或增加 `dataZoom`。
- [x] 移动端缩小 ECharts `grid.left`、`grid.right`、`grid.bottom`。
- [x] 移动端降低坐标轴字体，但不要低于 10px。
- [x] 移动端 tooltip 优先考虑点击触发，避免手指悬停不可用。

## 6. ECharts Resize 与微信 WebView

- [x] 保留现有 `resizeAll()`。
- [x] 确认 `window.addEventListener('resize', resizeAll)` 已存在。
- [x] 增加横竖屏切换监听：

```javascript
window.addEventListener('orientationchange', function() {
  setTimeout(resizeAll, 300);
});
```

- [x] 增加微信地址栏变化兼容：

```javascript
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', function() {
    setTimeout(resizeAll, 120);
  });
}
```

- [ ] 可选：为图表容器加 `ResizeObserver`，容器尺寸变化时自动 resize。
- [x] Tab 切换后继续延迟执行 `resizeAll()`，至少延迟 100-300ms。
- [x] 如果某个图表在隐藏 Tab 中初始化后仍空白，在该 Tab 激活时重新执行对应 render 函数。

## 7. 表格移动端策略

- [x] 宽表不要强行塞进屏幕，保留横向滚动。
- [x] 给 `.table-wrap` 增加：

```css
overflow-x: auto;
-webkit-overflow-scrolling: touch;
```

- [x] 给主要数据表设置移动端最小宽度：

```css
@media (max-width: 560px) {
  .table-wrap table, .data-table { min-width: 720px; }
}
```

- [x] 排名表、城市表这类宽表继续保留 sticky 表头。
- [ ] 检查表头 sticky 在微信中是否遮挡内容。
- [x] 确认横滑只发生在表格容器内，不带动整个页面横滑。
- [ ] 如果少列表格只有 3-5 列，可后续再考虑改成卡片式展示。

## 8. 弹窗与浮层

- [x] 移动端调整 `.modal-content`：

```css
@media (max-width: 560px) {
  .modal-content {
    width: calc(100vw - 24px);
    max-height: calc(100dvh - 40px);
    padding: 20px 16px;
  }
}
```

- [x] 城市详情弹窗同样使用 `100dvh` 限制高度。
- [x] 弹窗内部允许滚动。
- [x] 关闭按钮点击区域至少 40px。
- [ ] 打开弹窗时检查背景页面是否误滚动。

## 9. 性能与视觉降级

- [x] 移动端关闭或降低背景 wave SVG 的复杂度。
- [x] 移动端减少大面积 `backdrop-filter`、`blur`、重阴影。
- [x] 非当前 Tab 的复杂图表尽量延迟初始化。
- [x] 地图和网络图移动端减少动画。
- [x] 加入减少动画兼容：

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

## 10. 微信真机测试

- [ ] 用微信打开本地部署或线上页面，而不是只看桌面浏览器。
- [ ] iPhone 微信至少测一次。
- [ ] Android 微信至少测一次。
- [ ] 检查首次进入页面图表是否正常。
- [ ] 检查切换一级 Tab 后图表是否正常。
- [ ] 检查切换二级 Tab 后图表是否正常。
- [ ] 检查微信地址栏收起/展开后图表是否变形。
- [ ] 检查横竖屏切换后图表是否重新适配。
- [ ] 检查返回页面后是否出现图表空白。
- [ ] 检查表格横向滑动是否顺滑。
- [ ] 检查弹窗是否能完整阅读并关闭。

## 11. 缓存与发布

- [ ] 发布前给 HTML 或资源 URL 加版本号，避免微信缓存旧文件。
- [ ] 如果 ECharts 本地化，资源引用加版本：

```html
<script src="assets/echarts.min.js?v=mobile-1"></script>
```

- [ ] 修改完成后，用无痕浏览器和微信各重新打开一次。
- [ ] 如果微信仍显示旧页面，尝试改 URL 参数，例如：

```text
index.html?v=mobile-1
```

## 12. 建议执行顺序

- [x] 第一步：只做集中式移动端 CSS 补丁。
- [x] 第二步：处理导航、筛选栏、表格横滑。
- [x] 第三步：处理 ECharts 高度、option 与 resize。
- [x] 第四步：处理弹窗和微信安全区。
- [ ] 第五步：微信真机测试并记录问题。
- [ ] 第六步：把稳定补丁同步到其它 HTML 页面。

## 13. 最终验收标准

- [ ] 375px 宽度下页面整体无横向滚动。
- [ ] 首屏标题、统计卡片、导航都正常显示。
- [ ] 所有一级 Tab 可点击。
- [ ] 所有二级 Tab 可横滑并可点击。
- [ ] 每个图表都能显示，不空白。
- [ ] 每个宽表都能在表格区域内横滑。
- [ ] 弹窗不超出屏幕。
- [ ] 微信内置浏览器中字体、ECharts、地图全部正常加载。
- [ ] 横竖屏切换后布局和图表仍正常。
