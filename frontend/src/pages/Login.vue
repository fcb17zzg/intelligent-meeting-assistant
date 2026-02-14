<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>🎯 登录</h1>
        <p>智能会议助手系统</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username" label="">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password" label="">
          <el-input
            v-model="loginForm.password"
            placeholder="密码"
            prefix-icon="Lock"
            type="password"
            size="large"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>没有账户？<el-link type="primary" @click="goToRegister">立即注册</el-link></p>
      </div>

      <!-- 错误信息 -->
      <el-alert
        v-if="error"
        type="error"
        :title="error"
        closable
        style="margin-top: 20px"
        @close="error = null"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const loading = ref(false)
const error = ref(null)

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' },
  ],
}

/**
 * 处理登录
 */
const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    error.value = null

    try {
      await authStore.login({
        username: loginForm.username,
        password: loginForm.password,
      })

      ElMessage.success('登录成功')

      // 重定向到指定页面或首页
      const redirect = route.query.redirect || '/meetings'
      router.push(redirect)
    } catch (err) {
      console.error('登录失败:', err)
      error.value = err.message || err.detail || '登录失败，请检查用户名和密码'
    } finally {
      loading.value = false
    }
  })
}

/**
 * 跳转到注册页面
 */
const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped lang="scss">
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.5s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 30px;

  h1 {
    margin: 0 0 10px 0;
    font-size: 28px;
    color: #333;
  }

  p {
    margin: 0;
    color: #999;
    font-size: 14px;
  }
}

:deep(.el-form-item) {
  margin-bottom: 18px;

  &:last-of-type {
    margin-top: 30px;
  }
}

:deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

:deep(.el-button) {
  border: none;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;

  p {
    margin: 0;
    color: #666;
    font-size: 14px;

    :deep(.el-link) {
      margin-left: 5px;
    }
  }
}
</style>
