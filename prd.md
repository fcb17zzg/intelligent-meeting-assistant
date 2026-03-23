## 智能会议助手前端 UI 改造方案

 Context

 当前前端界面功能完整但视觉简陋，使用基础 Element Plus
 组件、平淡的白色卡片和轻阴影。用户希望升级为渐变高级感风格（Glassmorphism +
 紫蓝渐变色系），保留顶部导航栏结构，改造全部 4 个核心页面。

 设计方向

 - Glassmorphism：半透明背景 + backdrop-filter: blur() + 白色毛玻璃边框
 - 渐变色系：紫蓝主渐变 (#667eea → #764ba2)，配以青/绿/橙/红辅助渐变
 - 微交互：hover 卡片抬起发光、数字入场动画、导航激活下划线动画
 - 圆角大化：12-20px 大圆角
 - 层次阴影：精细阴影体系区分深度

 改造文件

 ┌───────────────────┬──────────────────────────────────────┬──────────────────────────┐
 │       文件        │                 路径                 │         改动类型         │
 ├───────────────────┼──────────────────────────────────────┼──────────────────────────┤
 │ main.scss         │ frontend/src/styles/main.scss        │ 全面重写 - 设计系统基础  │
 ├───────────────────┼──────────────────────────────────────┼──────────────────────────┤
 │ App.vue           │ frontend/src/App.vue                 │ 模板 + 样式双重修改      │
 ├───────────────────┼──────────────────────────────────────┼──────────────────────────┤
 │ MeetingList.vue   │ frontend/src/pages/MeetingList.vue   │ 模板微调 + 样式重写      │
 ├───────────────────┼──────────────────────────────────────┼──────────────────────────┤
 │ MeetingDetail.vue │ frontend/src/pages/MeetingDetail.vue │ 仅追加样式（无模板改动） │
 ├───────────────────┼──────────────────────────────────────┼──────────────────────────┤
 │ TaskDashboard.vue │ frontend/src/pages/TaskDashboard.vue │ 仅追加样式（无模板改动） │
 └───────────────────┴──────────────────────────────────────┴──────────────────────────┘

 ---
 实施步骤

 Step 1：main.scss — 全局设计系统

 建立 CSS 变量体系 + 全局 Element Plus 覆盖 + 动画 keyframes：

 CSS 变量（在 :root 中）：
 --grad-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
 --grad-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
 --grad-warning: linear-gradient(135deg, #fa8231 0%, #f7b731 100%);
 --grad-danger:  linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
 --grad-stat-1 ~ --grad-stat-4  /* 4 个统计卡片专属渐变 */

 --glass-bg: rgba(255, 255, 255, 0.75);
 --glass-bg-light: rgba(255, 255, 255, 0.92);
 --glass-border: 1px solid rgba(255, 255, 255, 0.55);
 --glass-blur: blur(12px);

 --shadow-card: 0 8px 32px rgba(31, 38, 135, 0.12);
 --shadow-hover: 0 16px 48px rgba(102, 126, 234, 0.28);

 --color-bg-page: #f0f2ff;  /* 浅紫灰背景，替换原 #f5f7fa */
 --color-text-primary: #1a1a2e;
 --color-text-secondary: #5a6a85;
 --transition-base: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

 覆盖 Element Plus CSS 变量（无需 !important）：
 :root {
   --el-color-primary: #667eea;
   --el-border-radius-base: 8px;
 }

 全局 Element Plus 组件覆盖：
 - .el-button--primary：渐变背景 + hover 抬起发光
 - .el-card：玻璃态圆角卡片（全局基础）
 - .el-tag--dark.*：各状态渐变色 tag
 - .el-input__wrapper：玻璃态输入框
 - .el-dialog：毛玻璃弹窗
 - .el-progress-bar__inner：渐变进度条

 动画 keyframes：countUp, fadeInUp, fadeInScale（用于统计卡片和页面入场）

 ---
 Step 2：App.vue — 顶部导航升级

 模板调整（小改）：
 1. Logo 区域拆分为 .logo-icon-wrap（圆角方块图标）+ .logo-text（标题 + 英文副标题）
 2. 导航右侧加用户信息区：import { useAuthStore } 并展示 el-avatar + 用户名（已登录时）
 3. header 内加 .header-glow-line div（底部光线分割线）

 样式改造（全面重写 scoped style）：
 - header 高度 66px，保留紫蓝渐变，增加 ::before 径向光晕覆盖层
 - .header-glow-line：白色渐变分割线（居中高亮）
 - Logo 图标圆角方块：background: rgba(255,255,255,0.22) + border: 1px solid rgba(255,255,255,0.4)
 - .logo-sub：英文小字，追加品牌副标题
 - 导航链接激活态：渐变下划线动画（::after + scaleX 动画）替代原来的背景色激活

 ---
 Step 3：MeetingList.vue — 会议列表页全面升级

 模板调整（关键改动）：
 1. 页面标题改为渐变文字 + 英文 badge（.page-title-badge）
 2. 搜索框外套 .search-wrap（用于胶囊圆角覆盖）
 3. 4 个统计卡片的 el-col 添加 .stat-col-1/2/3/4 class（注入不同渐变）
 4. 每个统计卡片内添加 .stat-icon div（emoji 图标）
 5. 会议卡片 :class 绑定新增 status-completed、status-in-progress、status-archived（复用已有 normalizeMeetingStatus
 函数，无新逻辑）

 样式改造（关键效果）：
 - 统计卡片：4 个卡片分别用 4 种渐变背景（彩色渐变卡片），白色文字，右上角装饰圆，入场延迟动画（0.0s / 0.1s / 0.2s /
 0.3s）
 - 页面标题：-webkit-background-clip: text 渐变文字
 - 会议卡片：::before 左侧 3px 状态色条（随状态颜色变化），hover 触发 translateY(-6px) scale(1.01) + 紫色光晕阴影

 ---
 Step 4：MeetingDetail.vue — 会议详情页提升（仅样式追加）

 无模板改动，在 <style scoped> 尾部追加：
 - .back-btn：胶囊圆角描边样式，hover 向左位移
 - .section-card：覆盖为玻璃态，左侧 4px 渐变色条（用 nth-child(1~5) 分别赋紫/橙/青/粉/红）
 - 覆盖 .el-alert--success/error/warning：渐变色半透明背景替代纯色
 - .batch-add-item 对话框：渐变背景 hover 效果

 ---
 Step 5：TaskDashboard.vue — 任务管理页提升（仅样式追加）

 无模板改动，在 <style scoped> 尾部追加：
 - .page-header：渐变浅色横幅背景，标题渐变文字
 - .panel-title：::before 左侧渐变竖条装饰
 - .urgent-item：hover 时红色发光 box-shadow: 0 0 16px rgba(245,87,108,0.4) + 向右位移
 - .action-item-row：绿色边框 + hover 绿色发光
 - .reminder-columns h4：圆点颜色区分逾期（红）vs 即将到期（橙）
 - .reminder-item：玻璃态背景 + hover 白色背景切换

 ---
 验证方法

 1. 启动前端开发服务器：cd frontend && npm run dev（端口 3000）
 2. 访问 http://localhost:3000，依次检查：
   - 顶部导航：渐变背景、Logo 图标方块、导航激活下划线、底部光线
   - 会议列表页：4 色统计卡片（紫/青/绿/橙）、卡片 hover 抬起发光、搜索框胶囊
   - 会议详情页：返回按钮圆角、各 section 卡片左侧彩色边框
   - 任务管理页：页面标题横幅、紧急任务红色发光、提醒区域样式
 3. 功能验收：搜索、新建会议、删除、批量选择、转录、任务创建等核心流程正常
 4. 响应式：缩小到 768px 以下，检查移动端适配

 注意事项

 - backdrop-filter 需同时加 -webkit-backdrop-filter（Safari 兼容）
 - Element Plus 组件样式覆盖优先使用 CSS 变量覆盖（:root 内）；确需用 !important 时仅用于 scoped 块中 :deep() 选择器
 - 统计卡片的渐变背景需用 !important 覆盖全局 el-card 的玻璃态背景
 - 可选：在 index.html 中引入 Inter 字体（Google Fonts CDN）提升字体质感