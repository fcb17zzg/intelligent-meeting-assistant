<template>
  <div id="app" class="app-container">
    <!-- 头部导航 -->
    <header class="app-header">
      <div class="layout-container">
        <div class="header-content">
          <div class="logo">
            <h1>🎤 智能会议助手</h1>
          </div>
          <nav class="nav-menu">
            <RouterLink to="/dashboard" class="nav-item">任务主页</RouterLink>
            <RouterLink to="/meetings" class="nav-item">会议管理</RouterLink>
            <a href="#" class="nav-item">帮助</a>
          </nav>
        </div>
      </div>
    </header>

    <!-- 主容容器 -->
    <main class="app-main">
      <div class="layout-container">
        <RouterView />
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="app-footer">
      <div class="layout-container">
        <p>&copy; 2024 智能会议助手系统。保留所有权利。</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 0;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .logo {
      h1 {
        font-size: 28px;
        font-weight: 600;
        margin: 0;
        letter-spacing: 1px;
      }
    }

    .nav-menu {
      display: flex;
      gap: 30px;
      align-items: center;

      .nav-item {
        color: white;
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
        padding: 8px 12px;
        border-radius: 4px;

        &:hover,
        &.router-link-active {
          background-color: rgba(255, 255, 255, 0.2);
        }
      }
    }
  }
}

.app-main {
  flex: 1;
  padding: 40px 0;
}

.layout-container {
  width: 100%;
  margin: 0;
  padding: 0 24px;
}

.app-footer {
  background-color: #25252b;
  color: #999;
  padding: 20px 0;
  text-align: center;
  border-top: 1px solid #e6e6e6;

  p {
    margin: 0;
    font-size: 12px;
  }
}

@media (max-width: 768px) {
  .app-header {
    .header-content {
      flex-direction: column;
      gap: 20px;

      .logo h1 {
        font-size: 24px;
      }

      .nav-menu {
        gap: 15px;
      }
    }
  }

  .app-main {
    padding: 20px 0;
  }

  .layout-container {
    padding: 0 12px;
  }
}
</style>
