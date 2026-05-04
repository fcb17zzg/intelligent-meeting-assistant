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

        <p style="margin-bottom: 12px; color: #606266">
          支持重复上传新音频。上传新文件后会覆盖该会议此前的转录与分析结果。
        </p>
        <AudioUploader
          :meeting-id="meeting.id"
          @upload-success="onAudioUploadSuccess"
          @upload-error="onAudioUploadError"
        />

        <!-- 已上传音频信息 -->
        <div v-if="meeting.audio_path" style="margin-top: 16px">
          <el-alert title="✓ 音频已上传" type="success" :closable="false" />
          <div style="margin-top: 16px">
            <p>
              <strong>文件:</strong> {{ audioFileName }}
            </p>
            <p v-if="meeting.duration">
              <strong>时长:</strong> {{ Number(meeting.duration).toFixed(1) }}秒
            </p>

            <!-- 转录进度 -->
            <div v-if="transcribing" style="margin-top: 16px">
              <p style="margin-bottom: 8px">🔄 正在转录中...</p>
              <el-progress :percentage="transcribeProgress" />
            </div>

            <!-- 转录完成 -->
            <div v-else-if="meeting.transcript_raw || meeting.transcript_formatted" style="margin-top: 16px">
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
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span>📄 会议摘要</span>
        </template>
        <SummaryDisplay
          :summary="displaySummary"
          :loading="summaryLoading"
          :transcription="transcriptionData"
          :meeting-id="meetingId"
          @refresh="loadSummary(true)"
          @update-notes="updateSummaryNotes"
          @update-summary="updateSummaryContent"
          @update-action-item="upsertActionItemFromSummary"
          @add-action-items="openBatchAddTaskDialog"
          @delete-action-items="deleteSelectedActionItems"
        />
      </el-card>

      <!-- 可视化控制 -->
      <el-card class="section-card" shadow="hover">
        <template #header>
          <span>📈 可视化</span>
        </template>

        <div style="display:flex; gap:12px; align-items:center">
          <el-button type="primary" :loading="vizLoading" @click="generateVisualization">
            生成会议报告
          </el-button>

          <span v-if="reportResult" style="color:#909399">已生成会议报告</span>
        </div>

        <div v-if="reportResult" class="viz-result-grid">
          <div class="viz-result-card viz-report-card">
            <div class="viz-result-title">会议报告</div>
            <div class="viz-result-path">{{ reportResult.description }}</div>
            <el-button text type="primary" @click="openVisualizationReport(reportResult.url)">
              打开 HTML
            </el-button>
          </div>
        </div>

      </el-card>

      <!-- 任务列表，获取 -->
      <el-card v-if="tasks && tasks.length > 0" class="section-card" shadow="hover">
        <template #header>
          <span>✅ 会议任务</span>
        </template>

        <el-alert
          v-if="reminderOverview.overdue_count > 0"
          :title="`有 ${reminderOverview.overdue_count} 项任务已逾期`"
          type="error"
          :closable="false"
          style="margin-bottom: 12px"
        />
        <el-alert
          v-else-if="reminderOverview.due_soon_count > 0"
          :title="`有 ${reminderOverview.due_soon_count} 项任务即将到期（48小时内）`"
          type="warning"
          :closable="false"
          style="margin-bottom: 12px"
        />

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
        <el-form-item label="状态" required>
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
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

    <el-dialog v-model="batchAddDialogVisible" title="批量加入任务系统" width="680px">
      <div v-if="batchAddTaskItems.length === 0">
        <el-empty description="暂无可添加行动项" />
      </div>
      <div v-else class="batch-add-list">
        <div v-for="(item, index) in batchAddTaskItems" :key="`batch-${index}`" class="batch-add-item">
          <el-form label-width="88px">
            <el-form-item label="任务标题">
              <el-input v-model="item.title" placeholder="请输入任务标题" />
            </el-form-item>
            <el-form-item label="任务描述">
              <el-input v-model="item.description" type="textarea" rows="2" />
            </el-form-item>
            <el-row :gutter="12">
              <el-col :xs="24" :md="8">
                <el-form-item label="负责人">
                  <el-input v-model="item.assignee_name" placeholder="可留空" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="截止日期">
                  <el-date-picker
                    v-model="item.due_date"
                    type="datetime"
                    placeholder="可留空"
                    format="YYYY年MM月DD日 HH:mm"
                    value-format="YYYY-MM-DDTHH:mm:ss"
                    clearable
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="优先级">
                  <el-select v-model="item.priority" style="width: 100%">
                    <el-option label="紧急" value="urgent" />
                    <el-option label="高" value="high" />
                    <el-option label="中" value="medium" />
                    <el-option label="低" value="low" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>

      <template #footer>
        <el-button @click="batchAddDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchAdding" @click="confirmBatchAddTasks">
          确认添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMeetingStore } from '@/stores/meetingStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/dateUtils'
import { taskAPI } from '@/api'
import AudioUploader from '@/components/AudioUploader.vue'
import SummaryDisplay from '@/components/SummaryDisplay.vue'
import TaskList from '@/components/TaskList.vue'
import visualizationService from '@/services/visualizationService'

const route = useRoute()
const router = useRouter()
const meetingStore = useMeetingStore()

const meeting = computed(() => meetingStore.currentMeeting)
const summary = ref(null)
const tasks = ref([])
const showEditDialog = ref(false)
const editForm = ref({})
const transcribing = ref(false)
const transcribeProgress = ref(0)
const summaryLoading = ref(false)
const transcriptionData = ref(null)
const reportResult = ref(null)
const vizLoading = ref(false)
const batchAddDialogVisible = ref(false)
const batchAddTaskItems = ref([])
const batchAdding = ref(false)
const reminderOverview = ref({
  due_soon_count: 0,
  overdue_count: 0,
  due_soon: [],
  overdue: [],
})

const parseKeyTopics = (raw) => {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed : []
    } catch (_) {
      return []
    }
  }
  return []
}

const normalizeTopicLabel = (topic) => {
  if (topic && typeof topic === 'object') {
    return String(topic.name || topic.topic || topic.label || '').trim()
  }
  return String(topic || '').trim()
}

const buildSummaryFallback = (meetingData) => {
  if (!meetingData) return null
  const summaryText = String(meetingData.summary || '').trim()
  const topics = parseKeyTopics(meetingData.key_topics)
  if (!summaryText && topics.length === 0) return null
  return {
    meeting_id: meetingData.id,
    title: meetingData.title || '会议摘要',
    summary: summaryText,
    summary_text: summaryText,
    summary_type: meetingData.summary_type || 'extractive',
    key_topics: topics,
    decisions: [],
    open_issues: [],
    action_items: [],
    speaker_stats: {},
    duration: meetingData.duration,
    created_at: meetingData.created_at,
    notes: '',
  }
}

const displaySummary = computed(() => {
  if (summary.value) return summary.value
  return buildSummaryFallback(meetingStore.currentMeeting)
})

const meetingId = route.params.id
const audioFileName = computed(() => {
  const fullPath = String(meeting.value?.audio_path || '').trim()
  if (!fullPath) return ''
  const normalized = fullPath.replace(/\\/g, '/')
  return normalized.split('/').pop() || fullPath
})

const statusOptions = [
  { value: 'scheduled', label: '已排期' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'archived', label: '已归档' },
]

const normalizeMeetingStatus = (status) => {
  const legacyMap = {
    draft: 'scheduled',
    pending: 'scheduled',
    processing: 'in_progress',
    transcribed: 'in_progress',
    analyzed: 'completed',
  }
  return legacyMap[status] || status
}

const getStatusLabel = (status) => {
  const normalizedStatus = normalizeMeetingStatus(status)
  const map = {
    scheduled: '已排期',
    in_progress: '进行中',
    completed: '已完成',
    archived: '已归档',
  }
  return map[normalizedStatus] || normalizedStatus
}

const getStatusType = (status) => {
  const normalizedStatus = normalizeMeetingStatus(status)
  const map = {
    scheduled: 'info',
    in_progress: 'warning',
    completed: 'success',
    archived: 'danger',
  }
  return map[normalizedStatus] || 'info'
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
      editForm.value = {
        ...meetingStore.currentMeeting,
        status: normalizeMeetingStatus(meetingStore.currentMeeting.status),
      }
      if (!summary.value) {
        summary.value = buildSummaryFallback(meetingStore.currentMeeting)
      }
    }
  } catch (error) {
    ElMessage.error('加载会议详情失败')
  }
}

const loadSummary = async (refreshAnalysis = false, allowActionRetry = true) => {
  summaryLoading.value = true
  try {
    const result = await meetingStore.getSummary(meetingId, {
      refresh_analysis: refreshAnalysis,
    })
    summary.value = result

    const hasActionItems = Array.isArray(result?.action_items) && result.action_items.length > 0
    const hasTranscript = Boolean(
      meetingStore.currentMeeting?.transcript_formatted || meetingStore.currentMeeting?.transcript_raw
    )
    if (!refreshAnalysis && allowActionRetry && hasTranscript && !hasActionItems) {
      await loadSummary(true, false)
      return
    }
  } catch (error) {
    console.log('获取摘要:', error)
    summary.value = summary.value || buildSummaryFallback(meetingStore.currentMeeting)
  } finally {
    summaryLoading.value = false
  }
}

const generateVisualization = async () => {
  if (!meeting.value && !summary.value && !transcriptionData.value) {
    ElMessage.error('没有可用的数据用于生成会议报告')
    return
  }

  vizLoading.value = true
  reportResult.value = null

  try {
    const sourceMeeting = meeting.value || meetingStore.currentMeeting || {}
    const summaryData = displaySummary.value || summary.value || {}
    const transcriptText = String(
      meeting.value?.transcript_formatted ||
        meeting.value?.transcript_raw ||
        transcriptionData.value?.transcript_formatted ||
        transcriptionData.value?.transcript_raw ||
        ''
    ).trim()

    const summaryTopics = Array.isArray(summaryData.key_topics)
      ? summaryData.key_topics.map((item) => normalizeTopicLabel(item)).filter((item) => item)
      : parseKeyTopics(sourceMeeting.key_topics).map((item) => normalizeTopicLabel(item)).filter((item) => item)

    const summaryHighlights = Array.isArray(summaryData.highlights)
      ? summaryData.highlights.map((item) => String(item || '').trim()).filter((item) => item)
      : []

    const mergedTopicLabels = [...summaryTopics, ...summaryHighlights].filter(
      (item, index, arr) => arr.indexOf(item) === index
    )

    const reportKeyTopics = mergedTopicLabels.map((label) => ({
      name: label,
      topic: label,
      description: label,
      keywords: [],
    }))

    const insights = {
      meeting_id: Number(meetingId),
      summary: String(summaryData.summary_text || summaryData.summary || sourceMeeting.summary || '').trim(),
      action_items: Array.isArray(summaryData.action_items)
        ? summaryData.action_items.map((item) => ({
            id: item?.id,
            task: String(item?.task || item?.description || item?.text || '').trim(),
            description: String(item?.description || item?.text || item?.task || '').trim(),
            assignee: item?.assignee || item?.assignee_name || '',
            due_date: item?.due_date || null,
            priority: item?.priority || 'medium',
          }))
        : [],
      key_topics: reportKeyTopics,
      highlights: summaryHighlights,
      decisions: Array.isArray(summaryData.decisions) ? summaryData.decisions : [],
      open_issues: Array.isArray(summaryData.open_issues) ? summaryData.open_issues : [],
      transcript_excerpt: transcriptText ? transcriptText.slice(0, 1200) : '',
      transcript_full_excerpt: transcriptText,
    }

    const meetingData = {
      id: sourceMeeting.id,
      title: sourceMeeting.title || '会议报告',
      date: sourceMeeting.date || sourceMeeting.created_at || '',
      created_at: sourceMeeting.created_at || '',
      duration: sourceMeeting.duration || '',
      participants: Array.isArray(sourceMeeting.participants)
        ? sourceMeeting.participants
        : String(sourceMeeting.participants || sourceMeeting.participants_count || '')
            .split(',')
            .map((item) => String(item).trim())
            .filter(Boolean),
      description: sourceMeeting.description || '',
      status: sourceMeeting.status || '',
      transcript_formatted: sourceMeeting.transcript_formatted || transcriptText,
      transcript_raw: sourceMeeting.transcript_raw || transcriptText,
      summary: insights.summary,
    }

    const res = await visualizationService.generateReport(
      meetingData,
      insights,
      'html',
      `会议报告_${String(meetingData.title).replace(/[\\/:*?"<>|]/g, '_')}`
    )

    reportResult.value = {
      url: visualizationService.resolveVisualizationUrl(res?.file_url || res?.file_path),
      description: res?.file_path ? String(res.file_path).replace(/\\/g, '/') : '已生成会议报告',
    }
    ElMessage.success('会议报告生成完成')
  } catch (err) {
    ElMessage.error('会议报告生成失败：' + (err.message || err))
  } finally {
    vizLoading.value = false
  }
}

const openVisualizationReport = (url) => {
  if (!url) {
    ElMessage.warning('未找到可打开的图表文件')
    return
  }

  window.open(url, '_blank', 'noopener,noreferrer')
}

const loadTasks = async () => {
  try {
    const result = await meetingStore.getTasks(meetingId)
    const raw = Array.isArray(result) ? result : result.data || []
    tasks.value = raw.map((task) => ({
      ...task,
      completed: task.status === 'completed',
      assignee: task.assignee || null,
      assignee_name: task.assignee_name || task.assignee || null,
    }))
    await loadTaskReminders()
  } catch (error) {
    console.log('获取任务列表:', error)
  }
}

const loadTaskReminders = async () => {
  try {
    const response = await taskAPI.getReminders({ meeting_id: Number(meetingId) })
    reminderOverview.value = response?.data || response || reminderOverview.value
  } catch (error) {
    console.log('获取任务提醒失败:', error)
  }
}

const saveEdit = async () => {
  try {
    const payload = {
      ...editForm.value,
      status: normalizeMeetingStatus(editForm.value.status || 'scheduled'),
    }
    await meetingStore.updateMeeting(meetingId, payload)
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
  try {
    await taskAPI.updateTask(task.id, {
      status: task.completed ? 'completed' : 'pending',
    })
    ElMessage.success(`任务已${task.completed ? '标记完成' : '标记未完成'}`)
    await loadTasks()
  } catch (error) {
    ElMessage.error('更新任务状态失败')
  }
}

const updateTask = async (task) => {
  try {
    const dueDateValue = task.due_date
      ? (task.due_date instanceof Date ? task.due_date.toISOString() : String(task.due_date))
      : null

    await taskAPI.updateTask(task.id, {
      title: task.title,
      description: task.description,
      due_date: dueDateValue,
      priority: task.priority || 'medium',
      status: task.completed ? 'completed' : (task.status || 'pending'),
      assignee_name: task.assignee || task.assignee_name || null,
    })
    ElMessage.success('任务已更新')
    await loadTasks()
  } catch (error) {
    ElMessage.error('更新任务失败')
  }
}

const deleteTask = async (taskId) => {
  try {
    await taskAPI.deleteTask(taskId)
    tasks.value = tasks.value.filter((t) => t.id !== taskId)
    ElMessage.success('任务已删除')
  } catch (error) {
    ElMessage.error('删除任务失败')
  }
}

const updateSummaryNotes = (notes) => {
  ElMessage.success('笔记已保存')
}

const updateSummaryContent = async (payload) => {
  const summaryText = String(payload?.summary_text || payload?.summary || '').trim()
  const keyTopics = Array.isArray(payload?.key_topics)
    ? payload.key_topics
        .map((topic) => {
          if (topic && typeof topic === 'object') {
            return String(topic?.name || '').trim()
          }
          return String(topic || '').trim()
        })
        .filter((topic) => topic)
    : []
  const highlights = Array.isArray(payload?.highlights)
    ? payload.highlights
        .map((highlight) => String(highlight || '').trim())
        .filter((highlight) => highlight)
    : []
  const mergedTopics = [...highlights, ...keyTopics].filter(
    (topic, index, arr) => arr.indexOf(topic) === index
  )

  await meetingStore.updateMeeting(meetingId, {
    summary: summaryText,
    key_topics: JSON.stringify(mergedTopics),
  })

  if (summary.value) {
    summary.value = {
      ...summary.value,
      summary_text: summaryText,
      summary: summaryText,
      key_topics: mergedTopics,
      highlights,
    }
  }
}

const upsertActionItemFromSummary = async (item) => {
  try {
    const description = String(item?.description || item?.text || '').trim()
    if (!description) {
      ElMessage.warning('行动项描述不能为空')
      return
    }

    const dueDateValue = item?.due_date ? String(item.due_date) : null
    const assigneeName = item?.assignee ? String(item.assignee).trim() : null

    // 先更新页面上的摘要行动项显示，避免用户感知“保存后没变化”。
    if (summary.value && Array.isArray(summary.value.action_items)) {
      const idx = summary.value.action_items.findIndex((x) => String(x?.id) === String(item?.id))
      if (idx >= 0) {
        summary.value.action_items[idx] = {
          ...summary.value.action_items[idx],
          description,
          text: description,
          assignee: assigneeName,
          due_date: dueDateValue,
        }
      }
    }

    const numericId = Number(item?.id)
    const existingTask = Number.isFinite(numericId)
      ? tasks.value.find((t) => Number(t.id) === numericId)
      : null

    if (existingTask) {
      await taskAPI.updateTask(existingTask.id, {
        title: description.slice(0, 80),
        description,
        assignee_name: assigneeName,
        due_date: dueDateValue,
      })
    } else {
      await taskAPI.createTask({
        meeting_id: Number(meetingId),
        title: description.slice(0, 80),
        description,
        assignee_name: assigneeName,
        due_date: dueDateValue,
        priority: item?.priority || 'medium',
      })
    }

    ElMessage.success('行动项已保存，可在任务列表继续编辑')
    await loadTasks()
  } catch (error) {
    ElMessage.error('保存行动项失败')
  }
}

const openBatchAddTaskDialog = (items) => {
  const source = Array.isArray(items) ? items : []
  if (!source.length) {
    ElMessage.warning('请先选择行动项')
    return
  }

  batchAddTaskItems.value = source.map((item, index) => ({
    title: String(item?.title || '').trim() || `任务${index + 1}`,
    description: String(item?.description || item?.text || '').trim(),
    assignee_name: item?.assignee ? String(item.assignee).trim() : '',
    due_date: item?.due_date || null,
    priority: item?.priority || 'medium',
  }))
  batchAddDialogVisible.value = true
}

const confirmBatchAddTasks = async () => {
  const validItems = batchAddTaskItems.value.filter((item) => String(item.description || '').trim())
  if (!validItems.length) {
    ElMessage.warning('至少需要一个有效行动项')
    return
  }

  batchAdding.value = true
  try {
    for (const item of validItems) {
      const title = String(item.title || '').trim() || '任务'
      await taskAPI.createTask({
        meeting_id: Number(meetingId),
        title,
        description: String(item.description || '').trim(),
        assignee_name: String(item.assignee_name || '').trim() || null,
        due_date: item.due_date || null,
        priority: item.priority || 'medium',
      })
    }
    ElMessage.success(`已添加 ${validItems.length} 项任务`)
    batchAddDialogVisible.value = false
    batchAddTaskItems.value = []
    await Promise.all([loadTasks(), loadSummary(false, false)])
  } catch (error) {
    ElMessage.error('批量添加任务失败')
  } finally {
    batchAdding.value = false
  }
}

const deleteSelectedActionItems = async (items) => {
  const selectedItems = Array.isArray(items) ? items : []
  if (!selectedItems.length) {
    ElMessage.warning('请先选择行动项')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedItems.length} 个行动项吗？`,
      '批量删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch (_) {
    return
  }

  try {
    const selectedIdSet = new Set(
      selectedItems
        .map((item) => Number(item?.id))
        .filter((id) => Number.isFinite(id))
    )

    let deletedCount = 0
    for (const id of selectedIdSet) {
      const task = tasks.value.find((taskItem) => Number(taskItem.id) === id)
      if (!task) continue
      await taskAPI.deleteTask(id)
      deletedCount += 1
    }

    if (summary.value && Array.isArray(summary.value.action_items)) {
      const descriptionSet = new Set(
        selectedItems
          .map((item) => String(item?.description || item?.text || '').trim())
          .filter((text) => text)
      )
      summary.value.action_items = summary.value.action_items.filter((item) => {
        const numericId = Number(item?.id)
        const desc = String(item?.description || item?.text || '').trim()
        if (Number.isFinite(numericId) && selectedIdSet.has(numericId)) return false
        if (desc && descriptionSet.has(desc)) return false
        return true
      })
    }

    await loadTasks()
    ElMessage.success(
      deletedCount > 0
        ? `已删除 ${deletedCount} 个任务，并从摘要移除选中行动项`
        : '已从当前摘要移除选中行动项'
    )
  } catch (error) {
    ElMessage.error('批量删除行动项失败')
  }
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
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
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

.viz-result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.viz-result-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
  border: 1px solid #dbeafe;
}

.viz-result-title {
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 6px;
}

.viz-result-path {
  color: #64748b;
  font-size: 12px;
  margin-bottom: 10px;
  word-break: break-all;
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

.meeting-detail {
  .back-btn {
    border-radius: 999px;
    border: 1px solid rgba(102, 126, 234, 0.4);
    background: rgba(255, 255, 255, 0.82);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.16);
    transition: var(--transition-base);

    &:hover {
      transform: translateX(-4px);
      border-color: rgba(118, 75, 162, 0.55);
      box-shadow: 0 14px 24px rgba(102, 126, 234, 0.24);
    }
  }

  .section-card {
    position: relative;
    overflow: hidden;
    border-radius: 18px;
    border: var(--glass-border);
    background: var(--glass-bg);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: var(--grad-primary);
    }

    &:nth-of-type(1)::before {
      background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }

    &:nth-of-type(2)::before {
      background: linear-gradient(180deg, #fa8231 0%, #f7b731 100%);
    }

    &:nth-of-type(3)::before {
      background: linear-gradient(180deg, #4facfe 0%, #00f2fe 100%);
    }

    &:nth-of-type(4)::before {
      background: linear-gradient(180deg, #f093fb 0%, #f5576c 100%);
    }

    &:nth-of-type(5)::before {
      background: linear-gradient(180deg, #ff758c 0%, #ff7eb3 100%);
    }
  }

  :deep(.el-alert--success) {
    border: none;
    background: linear-gradient(135deg, rgba(67, 233, 123, 0.24), rgba(56, 249, 215, 0.2));
  }

  :deep(.el-alert--error) {
    border: none;
    background: linear-gradient(135deg, rgba(245, 87, 108, 0.22), rgba(240, 147, 251, 0.2));
  }

  :deep(.el-alert--warning) {
    border: none;
    background: linear-gradient(135deg, rgba(250, 130, 49, 0.22), rgba(247, 183, 49, 0.2));
  }

  .batch-add-item {
    border-radius: 14px;
    border: 1px solid rgba(149, 162, 230, 0.25);
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.84), rgba(241, 244, 255, 0.88));
    transition: var(--transition-base);

    &:hover {
      border-color: rgba(112, 129, 230, 0.4);
      box-shadow: 0 16px 28px rgba(102, 126, 234, 0.16);
      transform: translateY(-2px);
    }
  }
}
</style>

