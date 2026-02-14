<template>
  <div class="meeting-detail">
    <!-- 返回按钮 -->
    <el-button class="back-btn" @click="$router.back()">
      ← 返回
    </el-button>

    <!-- 加载状态 -->
    <el-skeleton v-if="meetingStore.loading" :rows="8" animated />

    <!-- 会议详情内容 -->
    <div v-else-if="meeting" class="detail-container">
      <!-- 会议基本信息 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>📌 会议信息</span>
            <el-button-group>
              <el-button type="primary" plain size="small" @click="showEditDialog = true">
                ✏️ 编辑
              </el-button>
              <el-button type="danger" plain size="small" @click="deleteMeeting">
                🗑️ 删除
              </el-button>
            </el-button-group>
          </div>
        </template>

        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form label-width="100px" label-position="left">
              <el-form-item label="会议标题">
                <span>{{ meeting.title }}</span>
              </el-form-item>
              <el-form-item label="创建时间">
                <span>{{ formatDate(meeting.created_at) }}</span>
              </el-form-item>
              <el-form-item label="状态">
                <el-tag :type="getStatusType(meeting.status)">
                  {{ getStatusLabel(meeting.status) }}
                </el-tag>
              </el-form-item>
            </el-form>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form label-width="100px" label-position="left">
              <el-form-item label="时长">
                <span>{{ meeting.duration || '未设置' }}分钟</span>
              </el-form-item>
              <el-form-item label="参与人数">
                <span>{{ meeting.participants || '未设置' }}人</span>
              </el-form-item>
              <el-form-item label="描述">
                <span>{{ meeting.description || '无' }}</span>
              </el-form-item>
            </el-form>
          </el-col>
        </el-row>
      </el-card>

      <!-- 音频处理区域 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span>🎤 音频处理</span>
        </template>

        <!-- 如果还没上传音频，显示上传组件 -->
        <div v-if="!meeting.audio_path">
          <p style="margin-bottom: 20px; color: #606266">
            请上传会议音频文件，系统将自动进行转录和分析
          </p>
          <AudioUploader
            :meeting-id="meeting.id"
            @upload-success="onAudioUploadSuccess"
            @upload-error="onAudioUploadError"
          />
        </div>

        <!-- 已上传音频信息 -->
        <div v-else>
          <el-alert title="✓ 音频已上传" type="success" :closable="false" />
          <div style="margin-top: 16px">
            <p>
              <strong>文件:</strong> {{ meeting.audio_filename }}
            </p>
            <p v-if="meeting.audio_duration">
              <strong>时长:</strong> {{ meeting.audio_duration }}秒
            </p>

            <!-- 转录进度 -->
            <div v-if="transcribing" style="margin-top: 16px">
              <p style="margin-bottom: 8px">🔄 正在转录中...</p>
              <el-progress :percentage="transcribeProgress" />
            </div>

            <!-- 转录完成 -->
            <div v-else-if="meeting.transcript_status === 'completed'" style="margin-top: 16px">
              <el-alert
                title="✓ 转录已完成"
                type="success"
                :closable="false"
                style="margin-bottom: 12px"
              />
            </div>

            <!-- 开始转录按钮 -->
            <div v-else style="margin-top: 16px">
              <el-button type="primary" @click="startTranscribe" :loading="transcribing">
                🚀 开始转录
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 摘要展示 -->
      <el-card v-if="summary" class="section-card" shadow="hover">
        <template #header>
          <span>📄 会议摘要</span>
        </template>
        <SummaryDisplay
          :summary="summary"
          :loading="summaryLoading"
          :transcription="transcriptionData"
          @refresh="loadSummary"
          @update-notes="updateSummaryNotes"
        />
      </el-card>

      <!-- 可视化控制 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span>📈 可视化</span>
        </template>

        <div style="display:flex; gap:12px; align-items:center">
          <el-button type="primary" :loading="vizLoading" @click="generateVisualization">
            生成可视化图表
          </el-button>

          <el-button v-if="visualizationResults" @click="() => {}">查看结果（控制台）</el-button>
          <span v-if="visualizationResults" style="color:#909399">已生成图表数据</span>
        </div>

      </el-card>

      <!-- 任务列表，获取 -->
      <el-card v-if="tasks && tasks.length > 0" class="section-card" shadow="hover">
        <template #header>
          <span>✅ 会议任务</span>
        </template>
        <TaskList
          :tasks="tasks"
          @complete-task="completeTask"
          @update-task="updateTask"
          @delete-task="deleteTask"
        />
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-empty v-else description="会议不存在或已被删除" />

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑会议" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="会议标题" required>
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" rows="4" />
        </el-form-item>
        <el-form-item label="时长（分钟）">
          <el-input-number v-model="editForm.duration" :min="0" />
        </el-form-item>
        <el-form-item label="参与人数">
          <el-input-number v-model="editForm.participants" :min="1" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMeetingStore } from '@/stores/meetingStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/dateUtils'
import AudioUploader from '@/components/AudioUploader.vue'
import SummaryDisplay from '@/components/SummaryDisplay.vue'
import TaskList from '@/components/TaskList.vue'
import visualizationService from '@/services/visualizationService'

const route = useRoute()
const router = useRouter()
const meetingStore = useMeetingStore()

const meeting = meetingStore.currentMeeting
const summary = ref(null)
const tasks = ref([])
const showEditDialog = ref(false)
const editForm = ref({})
const transcribing = ref(false)
const transcribeProgress = ref(0)
const summaryLoading = ref(false)
const transcriptionData = ref(null)
const visualizationResults = ref(null)
const vizLoading = ref(false)

const meetingId = route.params.id

const getStatusLabel = (status) => {
  const map = {
    draft: '草稿',
    processing: '处理中',
    completed: '已完成',
    transcribed: '已转录',
    analyzed: '已分析',
  }
  return map[status] || status
}

const getStatusType = (status) => {
  const map = {
    draft: 'info',
    processing: 'warning',
    completed: 'success',
    transcribed: 'primary',
    analyzed: 'success',
  }
  return map[status] || 'info'
}

const onAudioUploadSuccess = (response) => {
  ElMessage.success('音频上传成功')
  // response 可能为 meetingProcessingService.processMeeting 的结果
  // 如果包含 transcription，则传给 SummaryDisplay
  transcriptionData.value = response?.transcription || response
  // 刷新会议详情/摘要/任务
  loadMeetingDetail()
  loadSummary()
  loadTasks()
}

const onAudioUploadError = (error) => {
  ElMessage.error('音频上传失败：' + error)
}

const startTranscribe = async () => {
  transcribing.value = true
  transcribeProgress.value = 0

  try {
    const interval = setInterval(() => {
      transcribeProgress.value += Math.random() * 30
      if (transcribeProgress.value > 90) {
        transcribeProgress.value = 90
      }
    }, 500)

    await meetingStore.transcribeMeeting(meetingId)

    clearInterval(interval)
    transcribeProgress.value = 100
    ElMessage.success('转录完成')

    setTimeout(() => {
      transcribing.value = false
      loadMeetingDetail()
      loadSummary()
      loadTasks()
    }, 1000)
  } catch (error) {
    transcribing.value = false
    ElMessage.error('转录失败：' + error)
  }
}

const loadMeetingDetail = async () => {
  try {
    await meetingStore.fetchMeetingDetail(meetingId)
    if (meetingStore.currentMeeting) {
      editForm.value = { ...meetingStore.currentMeeting }
    }
  } catch (error) {
    ElMessage.error('加载会议详情失败')
  }
}

const loadSummary = async () => {
  summaryLoading.value = true
  try {
    const result = await meetingStore.getSummary(meetingId)
    summary.value = result
  } catch (error) {
    console.log('获取摘要:', error)
  } finally {
    summaryLoading.value = false
  }
}

const generateVisualization = async () => {
  if (!summary.value && !transcriptionData.value) {
    ElMessage.error('没有可用的洞见数据用于生成可视化')
    return
  }

  vizLoading.value = true
  visualizationResults.value = null

  try {
    // 构造insights：优先使用 summary._nlp，如果不存在则使用 transcriptionData
    const insights = summary.value?._nlp || { processed: transcriptionData.value } || {}

    const res = await visualizationService.generateAllCharts(insights, Number(meetingId))
    visualizationResults.value = res
    ElMessage.success('可视化生成完成')
  } catch (err) {
    ElMessage.error('可视化生成失败：' + (err.message || err))
  } finally {
    vizLoading.value = false
  }
}

const loadTasks = async () => {
  try {
    const result = await meetingStore.getTasks(meetingId)
    tasks.value = Array.isArray(result) ? result : result.data || []
  } catch (error) {
    console.log('获取任务列表:', error)
  }
}

const saveEdit = async () => {
  try {
    await meetingStore.updateMeeting(meetingId, editForm.value)
    showEditDialog.value = false
    ElMessage.success('会议已更新')
  } catch (error) {
    ElMessage.error('更新失败：' + error)
  }
}

const deleteMeeting = () => {
  ElMessageBox.confirm('确定删除此会议？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await meetingStore.deleteMeeting(meetingId)
        ElMessage.success('会议已删除')
        router.push('/meetings')
      } catch (error) {
        ElMessage.error('删除失败：' + error)
      }
    })
    .catch(() => {})
}

const completeTask = async (task) => {
  ElMessage.success(`任务已${task.completed ? '标记完成' : '标记未完成'}`)
}

const updateTask = async (task) => {
  ElMessage.success('任务已更新')
}

const deleteTask = async (taskId) => {
  tasks.value = tasks.value.filter((t) => t.id !== taskId)
}

const updateSummaryNotes = (notes) => {
  ElMessage.success('笔记已保存')
}

const back = () => {
  router.back()
}

// 页面加载时获取详情
onMounted(() => {
  loadMeetingDetail()
  loadSummary()
  loadTasks()
})
</script>

<style scoped lang="scss">
.meeting-detail {
  padding: 20px 0;

  .back-btn {
    margin-bottom: 20px;
  }

  .detail-container {
    max-width: 1200px;
  }

  .section-card {
    margin-bottom: 20px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    :deep(.el-card__header) {
      border-bottom: 2px solid #f0f0f0;
      padding: 16px;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      }
    }

    :deep(.el-card__body) {
      padding: 24px;
    }
  }

  :deep(.el-form) {
    .el-form-item {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

@media (max-width: 768px) {
  .meeting-detail {
    .section-card {
      :deep(.el-card__body) {
        padding: 16px;
      }
    }
  }
}
</style>
