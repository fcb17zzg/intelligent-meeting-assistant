<template>
  <div class="user-menu">
    <!-- 未登录状态 -->
    <template v-if="!authStore.isAuthenticated">
      <el-button type="primary" @click="goToLogin">登录</el-button>
      <el-button @click="goToRegister">注册</el-button>
    </template>

    <!-- 已登录状态 -->
    <template v-else>
      <el-dropdown>
        <div class="user-info">
          <el-avatar :size="36" icon="User" />
          <span class="username">{{ authStore.user?.username }}</span>
          <el-icon class="is-icon"><arrow-down /></el-icon>
        </div>

        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item icon="User" @click="goToProfile">
              个人资料
            </el-dropdown-item>

            <!-- 管理员菜单 -->
            <template v-if="authStore.isAdmin">
              <el-divider margin="10px 0" />
              <el-dropdown-item icon="Management" @click="goToUserManagement">
                用户管理
              </el-dropdown-item>
            </template>

            <el-divider margin="10px 0" />
            <el-dropdown-item icon="SwitchButton" @click="handleLogout">
              登出
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </template>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

/**
 * 跳转到登录页面
 */
const goToLogin = () => {
  router.push('/login')
}

/**
 * 跳转到注册页面
 */
const goToRegister = () => {
  router.push('/register')
}

/**
 * 跳转到个人资料页面
 */
const goToProfile = () => {
  router.push('/profile')
}

/**
 * 跳转到用户管理页面
 */
const goToUserManagement = () => {
  router.push('/admin/users')
}

/**
 * 处理登出
 */
const handleLogout = () => {
  authStore.logout()
  ElMessage.success('已登出')
  router.push('/login')
}
</script>

<style scoped lang="scss">
.user-menu {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;

  &:hover {
    background-color: #f0f0f0;
  }
}

.username {
  color: #333;
  font-size: 14px;
  font-weight: 500;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.el-dropdown-menu) {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

:deep(.el-dropdown-menu__item) {
  padding: 10px 16px;

  &:hover {
    background-color: #f5f7fa;
  }
}
</style>
