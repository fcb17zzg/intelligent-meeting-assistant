<template>
  <div id="app" class="app-container">
    <!-- 头部导航 -->
    <header class="app-header">
      <div class="header-glow-line" />
      <div class="layout-container">
        <div class="header-content">
          <div class="logo">
            <div class="logo-text">
              <h1>智能会议助手</h1>
              <span class="logo-sub">Meeting Intelligence Studio</span>
            </div>
          </div>
          <nav class="nav-menu">
            <RouterLink to="/dashboard" class="nav-item">任务主页</RouterLink>
            <RouterLink to="/meetings" class="nav-item">会议管理</RouterLink>
            <RouterLink to="/help" class="nav-item">帮助</RouterLink>
          </nav>

          <div v-if="authStore.isAuthenticated" class="user-info">
            <el-avatar :size="34" class="user-avatar">
              {{ userInitial }}
            </el-avatar>
            <span class="user-name">{{ authStore.user?.username || authStore.user?.email || '用户' }}</span>
          </div>
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
import { computed } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()

const userInitial = computed(() => {
  const rawName = String(authStore.user?.username || authStore.user?.email || 'U')
  return rawName.charAt(0).toUpperCase()
})
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: transparent;
}

.app-header {
  background: var(--grad-primary);
  color: white;
  height: 66px;
  display: flex;
  align-items: center;
  box-shadow: 0 10px 28px rgba(52, 36, 107, 0.3);
  position: sticky;
  top: 0;
  z-index: 100;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    width: 380px;
    height: 180px;
    top: -80px;
    right: 12%;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.36) 0%, rgba(255, 255, 255, 0) 70%);
    pointer-events: none;
  }

  .header-glow-line {
    position: absolute;
    left: 50%;
    bottom: 0;
    transform: translateX(-50%);
    width: min(760px, 82vw);
    height: 2px;
    background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.96), rgba(255, 255, 255, 0));
  }

  .header-content {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 28px;
    position: relative;
    z-index: 1;

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 260px;

      .logo-text {
        h1 {
          font-size: 20px;
          font-weight: 800;
          margin: 0;
          line-height: 1.1;
          letter-spacing: 0.6px;
        }

        .logo-sub {
          display: block;
          margin-top: 2px;
          font-size: 11px;
          letter-spacing: 1.25px;
          text-transform: uppercase;
          opacity: 0.82;
        }
      }
    }

    .nav-menu {
      display: flex;
      gap: 26px;
      align-items: center;
      flex: 1;

      .nav-item {
        color: white;
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: var(--transition-base);
        padding: 6px 2px;
        position: relative;

        &::after {
          content: '';
          position: absolute;
          left: 0;
          right: 0;
          bottom: -7px;
          height: 3px;
          border-radius: 99px;
          background: linear-gradient(90deg, rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 1));
          transform: scaleX(0);
          transform-origin: left;
          transition: transform 0.3s ease;
        }

        &:hover::after,
        &.router-link-active::after {
          transform: scaleX(1);
        }

        &:hover,
        &.router-link-active {
          opacity: 1;
        }
      }
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 4px 8px 4px 4px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.14);
      border: 1px solid rgba(255, 255, 255, 0.28);

      .user-avatar {
        background: rgba(255, 255, 255, 0.3);
        color: #fff;
        font-weight: 700;
      }

      .user-name {
        font-size: 13px;
        font-weight: 600;
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

.app-main {
  flex: 1;
  padding: 32px 0 40px;
}

.layout-container {
  width: 100%;
  margin: 0;
  padding: 0 24px;
}

.app-footer {
  background-color: #1b1d2e;
  color: #b4bbd0;
  padding: 20px 0;
  text-align: center;
  border-top: 1px solid rgba(230, 236, 255, 0.12);

  p {
    margin: 0;
    font-size: 12px;
  }
}

@media (max-width: 768px) {
  .app-header {
    height: auto;
    min-height: 66px;
    padding: 10px 0;

    .header-content {
      flex-wrap: wrap;
      gap: 12px;

      .logo {
        min-width: unset;

        .logo-text h1 {
          font-size: 18px;
        }
      }

      .nav-menu {
        order: 3;
        width: 100%;
        justify-content: space-between;
        gap: 10px;

        .nav-item {
          font-size: 13px;
        }
      }

      .user-info {
        margin-left: auto;
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
