<template>
  <div class="create-meeting">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>🆕 创建新会议</h1>
      <p>填写以下信息创建一个新的会议，之后可以上传音频进行转录和分析</p>
    </div>

    <!-- 创建表单 -->
    <el-card shadow="hover">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        label-position="top"
      >
        <!-- 会议标题 -->
        <el-form-item prop="title" label="会议标题">
          <el-input
            v-model="formData.title"
            placeholder="请输入会议标题"
            clearable
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <!-- 会议描述 -->
        <el-form-item prop="description" label="会议描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            placeholder="请输入会议描述（可选）"
            rows="4"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item prop="status" label="会议状态">
          <el-select v-model="formData.status" style="width: 100%">
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <!-- 两列布局 -->
        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <!-- 会议时长 -->
            <el-form-item prop="duration" label="会议时长（分钟）">
              <el-input-number
                v-model="formData.duration"
                :min="0"
                :max="1440"
                placeholder="可选，会议时长"
                controls-position="right"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :md="12">
            <!-- 参与人数 -->
            <el-form-item prop="participants" label="参与人数">
              <el-input-number
                v-model="formData.participants"
                :min="1"
                :max="1000"
                placeholder="可选，参与人数"
                controls-position="right"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 会议地点 -->
        <el-form-item prop="location" label="会议地点">
          <el-input
            v-model="formData.location"
            placeholder="请输入会议地点（可选）"
            clearable
          />
        </el-form-item>

        <!-- 主持人 -->
        <el-form-item prop="organizer" label="主持人">
          <el-input
            v-model="formData.organizer"
            placeholder="请输入主持人名称（可选）"
            clearable
          />
        </el-form-item>

        <!-- 参与者 -->
        <el-form-item prop="participants_list" label="参与者">
          <el-input
            v-model="formData.participants_list"
            type="textarea"
            placeholder="请输入参与者姓名，多个用英文逗号分隔（可选）"
            rows="3"
          />
        </el-form-item>

        <!-- 提交按钮 -->
        <el-form-item>
          <el-button type="primary" size="large" @click="submitForm" :loading="submitting">
            🚀 创建会议
          </el-button>
          <el-button size="large" @click="resetForm">
            🔄 重置表单
          </el-button>
          <el-button size="large" @click="$router.back()">
            × 返回
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 提示信息 -->
      <el-alert
        type="info"
        :closable="false"
        style="margin-top: 20px"
        title="💡 提示"
        description="创建会议后，你可以上传音频文件，系统将自动进行转录、分析和提取任务。"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useMeetingStore } from '@/stores/meetingStore'

const router = useRouter()
const meetingStore = useMeetingStore()
const formRef = ref(null)
const submitting = ref(false)

const statusOptions = [
  { value: 'scheduled', label: '已排期' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'archived', label: '已归档' },
]

const formData = ref({
  title: '',
  description: '',
  status: 'scheduled',
  duration: null,
  participants: null,
  location: '',
  organizer: '',
  participants_list: '',
})

const rules = {
  title: [
    { required: true, message: '请输入会议标题', trigger: 'blur' },
    { min: 2, max: 100, message: '标题长度为2-100个字符', trigger: 'blur' },
  ],
  description: [{ max: 500, message: '描述长度不能超过500个字符', trigger: 'blur' }],
  duration: [
    { type: 'number', max: 1440, message: '请输入0-1440之间的数字（分钟）', trigger: 'blur' },
  ],
  participants: [{ type: 'number', message: '请输入有效的数字', trigger: 'blur' }],
}

const submitForm = async () => {
  if (!formRef.value) return

  // 验证表单
  try {
    await formRef.value.validate()
  } catch (error) {
    ElMessage.error('请填写必填项')
    return
  }

  submitting.value = true

  try {
    // 构建提交数据
    const submitData = {
      title: formData.value.title,
      description: formData.value.description || null,
      start_time: new Date().toISOString(), // 自动设置为当前时间
      status: formData.value.status || 'scheduled',
      duration: formData.value.duration || null,
      participants: formData.value.participants || null,
      location: formData.value.location || null,
      organizer: formData.value.organizer || null,
    }

    // 调用API创建会议
    const result = await meetingStore.createMeeting(submitData)

    ElMessage.success('会议创建成功')

    // 跳转到会议详情页
    setTimeout(() => {
      router.push(`/meetings/${result.id}`)
    }, 500)
  } catch (error) {
    ElMessage.error('创建失败：' + (error.message || error))
    console.error('Create meeting error:', error)
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  formRef.value?.resetFields()
}
</script>

<style scoped lang="scss">
.create-meeting {
  padding: 20px 0;
  max-width: 800px;
  margin: 0 auto;

  .page-header {
    margin-bottom: 30px;

    h1 {
      margin: 0 0 12px;
      font-size: 28px;
      color: #303133;
    }

    p {
      margin: 0;
      font-size: 14px;
      color: #606266;
      line-height: 1.6;
    }
  }

  :deep(.el-card) {
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    .el-form {
      padding-top: 20px;

      .el-form-item {
        margin-bottom: 24px;
      }

      .el-form-item__label {
        font-weight: 500;
        margin-bottom: 8px;
      }
    }

    .el-button-group {
      display: flex;
      gap: 12px;

      .el-button {
        flex: 1;
      }
    }
  }

  :deep(.el-alert) {
    border-radius: 4px;
  }
}

@media (max-width: 768px) {
  .create-meeting {
    :deep(.el-form-item__label) {
      display: block;
      margin-bottom: 8px;
    }

    :deep(.el-form-item) {
      margin-bottom: 20px;
    }
  }
}
</style>
