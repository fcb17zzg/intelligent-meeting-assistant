# 前端项目启动和开发指南

## 🎯 项目概述

这是智能会议助手系统的前端项目，提供现代化的Web界面来管理会议、上传音频、展示转录结果和任务管理。

## 📋 功能清单

### ✅ 完成的功能

- [x] **会议管理模块**
  - 会议列表展示（卡片布局）
  - 创建新会议
  - 会议详情查看
  - 编辑会议信息
  - 删除会议
  - 搜索和筛选
  - 统计数据概览

- [x] **音频处理模块**
  - 拖拽上传音频
  - 文件验证（格式、大小）
  - 上传进度显示
  - 支持多种音频格式

- [x] **转录和分析模块**
  - 开始转录功能
  - 转录进度显示
  - 转录完成提示

- [x] **摘要展示模块**
  - 会议纪要显示
  - 关键议题列表
  - 重点突出标记
  - 行动项管理
  - 发言人统计
  - 摘要导出
  - 笔记编辑

- [x] **任务管理模块**
  - 任务列表显示
  - 任务统计概览
  - 优先级标记
  - 任务筛选和排序
  - 标记完成/未完成
  - 编辑任务
  - 删除任务
  - 截止日期管理

- [x] **UI/UX 组件**
  - 响应式布局
  - Element Plus UI 框架
  - 现代化设计风格
  - 加载等待状态
  - 错误提示
  - 空状态提示

## 🚀 快速开始

### 第一步：安装 Node.js

确保你的系统已安装 Node.js (版本 14+)

```bash
node --version
npm --version
```

### 第二步：进入前端目录

```bash
cd h:\study\graduate_paper\auto-meeting-assistent\frontend
```

### 第三步：安装依赖

```bash
npm install
```

这将安装所有必要的 npm 包。

### 第四步：启动开发服务器

```bash
npm run dev
```

应用会在 `http://localhost:3000` 启动。

## 💻 开发工作流

### 修改前端代码

1. 在 `src/` 目录下修改 Vue 组件
2. Vite 会自动检测文件变化并热更新
3. 浏览器会自动刷新

### 常用命令

```bash
# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint
```

## 🔌 后端集成

### 确保后端运⁺行

在另一个终端中启动后端服务：

```bash
cd h:\study\graduate_paper\auto-meeting-assistent
python -m uvicorn app:app --reload
```

后端将在 `http://localhost:8000` 运行

### 配置 API 地址

#### 方式 1: 修改 vite.config.js (推荐)

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // 修改这里
      changeOrigin: true,
    },
  },
},
```

#### 方式 2: 环境变量

创建 `.env.local` 文件：

```
VITE_API_URL=http://localhost:8000/api
```

## 🗂️ 项目结构说明

```
frontend/
├── src/
│   ├── api/               # API 调用层
│   │   ├── client.js      # Axios 配置
│   │   └── index.js       # API 方法
│   ├── components/        # 可复用组件
│   │   ├── AudioUploader.vue
│   │   ├── SummaryDisplay.vue
│   │   └── TaskList.vue
│   ├── pages/             # 页面组件
│   │   ├── MeetingList.vue   # 主页 - 会议列表
│   │   ├── MeetingDetail.vue # 详情页 - 完整会议信息
│   │   └── CreateMeeting.vue # 创建页 - 新建会议
│   ├── router/            # 路由配置
│   ├── stores/            # 状态管理 (Pinia)
│   ├── styles/            # 全局样式
│   ├── utils/             # 工具函数
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── package.json           # 依赖配置
├── vite.config.js         # Vite 配置
└── index.html             # HTML 入口
```

## 🎨 主要页面

### 1. 会议列表页 (`/meetings`)
- 显示所有会议卡片
- 搜索和统计概览
- 创建新会议按钮
- 快速访问会议详情

### 2. 创建会议页 (`/meetings/create`)
- 表单填写会议信息
- 标题、描述、时长等
- 表单验证和提交

### 3. 会议详情页 (`/meetings/:id`)
- 会议基本信息
- 音频上传和转录
- 摘要显示
- 任务列表
- 编辑和删除操作

## 📱 响应式设计

所有页面都支持移动设备：
- 手机 (< 768px)
- 平板 (768px - 1024px)
- 桌面 (> 1024px)

## 🔐 认证准备

项目已预留认证支持：

```javascript
// src/api/client.js
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

## 🧪 测试数据

### 创建一个测试会议

1. 点击"新建会议"
2. 填写信息：
   - 标题: "测试会议"
   - 描述: "这是一个测试"
   - 时长: 60
   - 参与人数: 5

3. 点击"创建会议"
4. 上传测试音频
5. 开始转录

## 🐛 调试技巧

### 在浏览器中查看 API 响应

打开浏览器开发者工具 (F12)：

1. 点击 "Network" 标签
2. 执行会议相关操作
3. 查看请求和响应

### 查看应用状态

使用 Vue DevTools 浏览器扩展：
- 检查组件树
- 查看 Pinia 店铺状态

## 📚 学习资源

- [Vue 3 官方教程](https://vuejs.org/guide/introduction.html)
- [Element Plus 组件库](https://element-plus.org/zh-CN/)
- [Vite 用户指南](https://vitejs.dev/guide/)
- [Axios 文档](https://axios-http.com/)
- [Pinia 文档](https://pinia.vuejs.org/)

## 🤔 常见问题

### Q: 页面打不开怎么办？
A: 检查：
1. 开发服务器是否运行 (`npm run dev`)
2. 浏览器地址是否为 `http://localhost:3000`
3. 控制台是否有错误信息

### Q: API 请求失败怎么办？
A: 检查：
1. 后端服务是否运行
2. `vite.config.js` 中的 proxy 配置
3. CORS 设置是否正确

### Q: 样式显示不对怎么办？
A: 尝试：
1. 清空浏览器缓存 (Ctrl+Shift+Delete)
2. 重新启动开发服务器
3. 检查浏览器控制台是否有错误

## ✨ 后续拓展

可以考虑的功能扩展：

- [ ] 用户登录和认证
- [ ] 用户个人中心
- [ ] 会议评论功能
- [ ] 会议共享功能
- [ ] 实时协作编辑
- [ ] 音/视频通话
- [ ] 暗色模式
- [ ] 国际化语言支持
- [ ] 离线支持
- [ ] PWA 支持

## 📧 需要帮助？

如遇到问题，请：

1. 检查浏览器控制台错误消息
2. 查看网络请求 (DevTools > Network)
3. 检查后端日志
4. 参考相关文档

---

**开发者提示**: 使用 `npm run dev` 在开发模式下工作，这样可以享受热模块更新（HMR）的快速开发体验。

**预期**：该前端项目完全兼容后端 FastAPI，可即刻投入使用！
