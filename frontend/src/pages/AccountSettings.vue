<template>
  <div class="account-settings">
    <div class="page-header">
      <h1>账户管理</h1>
      <p>可修改邮箱、姓名和密码。用户名用于登录，当前不支持修改。</p>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-title">基本信息</div>
          </template>

          <el-form label-width="88px" :model="profileForm">
            <el-form-item label="用户名">
              <el-input v-model="profileForm.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="profileForm.full_name" placeholder="可选" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存信息</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-title">修改密码</div>
          </template>

          <el-form label-width="96px" :model="passwordForm">
            <el-form-item label="旧密码">
              <el-input v-model="passwordForm.currentPassword" type="password" show-password placeholder="请输入当前密码" />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="至少6位" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="再次输入" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingPassword" @click="changePassword">更新密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()

const profileForm = reactive({
  username: '',
  email: '',
  full_name: '',
})

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const savingProfile = ref(false)
const savingPassword = ref(false)

watch(
  () => authStore.user,
  (user) => {
    profileForm.username = user?.username || ''
    profileForm.email = user?.email || ''
    profileForm.full_name = user?.full_name || ''
  },
  { immediate: true }
)

const saveProfile = async () => {
  if (!authStore.user?.id) return
  if (!String(profileForm.email || '').trim()) {
    ElMessage.warning('邮箱不能为空')
    return
  }

  try {
    savingProfile.value = true
    await authStore.updateUserInfo(authStore.user.id, {
      email: String(profileForm.email).trim(),
      full_name: String(profileForm.full_name || '').trim() || null,
    })
    await authStore.fetchCurrentUser()
    ElMessage.success('账户信息已更新')
  } catch (error) {
    ElMessage.error(error?.message || '更新账户信息失败')
  } finally {
    savingProfile.value = false
  }
}

const changePassword = async () => {
  if (!authStore.user?.id) return

  const currentPassword = String(passwordForm.currentPassword || '').trim()
  const newPassword = String(passwordForm.newPassword || '').trim()
  const confirmPassword = String(passwordForm.confirmPassword || '').trim()

  if (!currentPassword) {
    ElMessage.warning('请输入旧密码')
    return
  }

  if (newPassword.length < 6) {
    ElMessage.warning('新密码至少需要6位')
    return
  }
  if (newPassword !== confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  try {
    savingPassword.value = true
    await authStore.updateUserInfo(authStore.user.id, {
      current_password: currentPassword,
      password: newPassword,
    })
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    ElMessage.success('密码已更新')
  } catch (error) {
    ElMessage.error(error?.message || '更新密码失败')
  } finally {
    savingPassword.value = false
  }
}
</script>

<style scoped lang="scss">
.account-settings {
  padding: 12px 0;

  .page-header {
    margin-bottom: 18px;
    border-radius: 16px;
    padding: 18px 20px;
    background: linear-gradient(120deg, rgba(102, 126, 234, 0.16), rgba(79, 172, 254, 0.14));
    border: 1px solid rgba(136, 153, 240, 0.25);

    h1 {
      margin: 0;
      font-size: 28px;
      background: var(--grad-primary);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }

    p {
      margin: 8px 0 0;
      color: #4f5f86;
    }
  }

  .card-title {
    font-weight: 700;
    color: #34476b;
  }
}
</style>
