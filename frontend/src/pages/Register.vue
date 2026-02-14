<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>📝 注册账户</h1>
        <p>加入智能会议助手系统</p>
      </div>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username" label="">
          <el-input
            v-model="registerForm.username"
            placeholder="用户名 (3-20个字符)"
            prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="email" label="">
          <el-input
            v-model="registerForm.email"
            placeholder="邮箱地址"
            prefix-icon="Message"
            type="email"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="full_name" label="">
          <el-input
            v-model="registerForm.full_name"
            placeholder="全名 (可选)"
            prefix-icon="Document"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password" label="">
          <el-input
            v-model="registerForm.password"
            placeholder="密码 (至少6个字符)"
            prefix-icon="Lock"
            type="password"
            size="large"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item prop="confirmPassword" label="">
          <el-input
            v-model="registerForm.confirmPassword"
            placeholder="确认密码"
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
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <p>已有账户？<el-link type="primary" @click="goToLogin">直接登录</el-link></p>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const registerFormRef = ref(null)
const loading = ref(false)
const error = ref(null)

const registerForm = reactive({
  username: '',
  email: '',
  full_name: '',
  password: '',
  confirmPassword: '',
})

// 自定义验证器
const validatePassword = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请输入密码'))
  } else if (value.length < 6) {
    callback(new Error('密码至少6个字符'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const validateConfirmPassword = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度3-20个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

/**
 * 处理注册
 */
const handleRegister = async () => {
  if (!registerFormRef.value) return

  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    error.value = null

    try {
      await authStore.register({
        username: registerForm.username,
        email: registerForm.email,
        full_name: registerForm.full_name || undefined,
        password: registerForm.password,
      })

      ElMessage.success('注册成功，请登录')

      // 跳转到登录页面
      router.push({
        name: 'Login',
        query: { username: registerForm.username },
      })
    } catch (err) {
      console.error('注册失败:', err)
      if (err.detail) {
        error.value = err.detail
      } else if (err.message) {
        error.value = err.message
      } else {
        error.value = '注册失败，请稍后重试'
      }
    } finally {
      loading.value = false
    }
  })
}

/**
 * 跳转到登录页面
 */
const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped lang="scss">
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 480px;
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

.register-header {
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

.register-footer {
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
