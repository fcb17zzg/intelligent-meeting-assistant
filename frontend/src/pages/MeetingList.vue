<template>
  <div class="meeting-list">
    <!-- 页面标题和操作 -->
    <div class="page-header">
      <h1>📋 会议管理</h1>
      <div class="header-actions">
        <el-input
          v-model="searchText"
          placeholder="搜索会议..."
          clearable
          style="width: 250px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="$router.push('/meetings/create')">
          ➕ 新建会议
        </el-button>
        <el-button v-if="!isBatchMode" @click="toggleBatchMode">
          多选
        </el-button>
        <template v-else>
          <el-button @click="toggleBatchMode">
            取消多选
          </el-button>
          <el-button
            type="danger"
            :disabled="selectedMeetingIds.length === 0"
            @click="batchDeleteMeetings"
          >
            批量删除（{{ selectedMeetingIds.length }}）
          </el-button>
        </template>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ meetingStore.totalMeetings }}</div>
            <div class="stat-label">总会议</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ meetingStore.pendingMeetings.length }}</div>
            <div class="stat-label">待处理</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ meetingStore.completedMeetings.length }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value progress">
              {{
                meetingStore.totalMeetings > 0
                  ? Math.round(
                      (meetingStore.completedMeetings.length / meetingStore.totalMeetings) * 100
                    )
                  : 0
              }}%
            </div>
            <div class="stat-label">完成率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 加载状态 -->
    <el-skeleton v-if="meetingStore.loading" :rows="5" animated />

    <!-- 会议卡片列表 -->
    <el-row v-else-if="filteredMeetings.length > 0" :gutter="20" class="meetings-row">
      <el-col v-for="meeting in filteredMeetings" :key="meeting.id" :xs="24" :sm="12" :md="8">
        <el-card
          class="meeting-card"
          :class="{ 'batch-mode': isBatchMode, 'is-selected': isMeetingSelected(meeting.id) }"
          shadow="hover"
          @click="handleCardClick(meeting.id)"
        >
          <div v-if="isBatchMode" class="select-indicator" @click.stop>
            <el-checkbox
              :model-value="isMeetingSelected(meeting.id)"
              @change="(checked) => toggleMeetingSelection(meeting.id, checked)"
            >
              选择
            </el-checkbox>
          </div>

          <!-- 卡片标题和状态 -->
          <div class="card-header">
            <h3 class="meeting-title">{{ meeting.title }}</h3>
            <el-tag :type="getMeetingStatusType(meeting.status)" effect="dark">
              {{ getMeetingStatusLabel(meeting.status) }}
            </el-tag>
          </div>

          <!-- 会议描述 -->
          <p v-if="meeting.description" class="meeting-description">
            {{ truncate(meeting.description, 80) }}
          </p>

          <!-- 会议信息 -->
          <div class="meeting-info">
            <div class="info-item">
              <span class="icon">📅</span>
              <span>{{ formatDate(meeting.created_at) }}</span>
            </div>
            <div v-if="meeting.duration" class="info-item">
              <span class="icon">⏱️</span>
              <span>{{ meeting.duration }}分钟</span>
            </div>
            <div v-if="meeting.participants" class="info-item">
              <span class="icon">👥</span>
              <span>{{ meeting.participants }}人</span>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="progress-wrapper">
            <el-progress
              :percentage="getMeetingProgress(meeting)"
              :format="(percentage) => percentage + '%'"
            />
          </div>

          <!-- 快速操作 -->
          <div class="card-actions">
            <el-button text type="primary" size="small" @click.stop="viewDetail(meeting.id)">
              📖 查看详情
            </el-button>
            <el-button
              v-if="!isBatchMode"
              text
              type="danger"
              size="small"
              @click.stop="deleteMeeting(meeting.id)"
            >
              🗑️ 删除
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 空状态 -->
    <el-empty v-else description="暂无会议数据">
      <el-button type="primary" @click="$router.push('/meetings/create')">
        创建第一个会议
      </el-button>
    </el-empty>

    <!-- 错误提示 -->
    <el-alert
      v-if="meetingStore.error"
      type="error"
      :title="meetingStore.error"
      closable
      @close="meetingStore.error = null"
      style="margin-top: 20px"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMeetingStore } from '@/stores/meetingStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { formatDate } from '@/utils/dateUtils'
import { useRouter } from 'vue-router'

const meetingStore = useMeetingStore()
const router = useRouter()
const searchText = ref('')
const isBatchMode = ref(false)
const selectedMeetingIds = ref([])

const filteredMeetings = computed(() => {
  if (!searchText.value) {
    return meetingStore.meetings
  }
  const query = searchText.value.toLowerCase()
  return meetingStore.meetings.filter(
    (m) =>
      m.title.toLowerCase().includes(query) ||
      (m.description && m.description.toLowerCase().includes(query))
  )
})

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

const getMeetingStatusLabel = (status) => {
  const normalizedStatus = normalizeMeetingStatus(status)
  const map = {
    scheduled: '已排期',
    in_progress: '进行中',
    completed: '已完成',
    archived: '已归档',
  }
  return map[normalizedStatus] || normalizedStatus
}

const getMeetingStatusType = (status) => {
  const normalizedStatus = normalizeMeetingStatus(status)
  const map = {
    scheduled: 'info',
    in_progress: 'warning',
    completed: 'success',
    archived: 'danger',
  }
  return map[normalizedStatus] || 'info'
}

const getMeetingProgress = (meeting) => {
  const status = normalizeMeetingStatus(meeting.status)
  if (status === 'completed') return 100
  if (status === 'archived') return 100
  if (status === 'in_progress') return 60
  if (status === 'scheduled') return 20
  return 20
}

const truncate = (text, length) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

const viewDetail = (meetingId) => {
  router.push(`/meetings/${meetingId}`)
}

const isMeetingSelected = (meetingId) => {
  return selectedMeetingIds.value.includes(Number(meetingId))
}

const toggleMeetingSelection = (meetingId, checked) => {
  const normalizedId = Number(meetingId)
  if (checked) {
    if (!selectedMeetingIds.value.includes(normalizedId)) {
      selectedMeetingIds.value.push(normalizedId)
    }
  } else {
    selectedMeetingIds.value = selectedMeetingIds.value.filter((id) => id !== normalizedId)
  }
}

const handleCardClick = (meetingId) => {
  if (!isBatchMode.value) {
    router.push(`/meetings/${meetingId}`)
    return
  }
  const selected = isMeetingSelected(meetingId)
  toggleMeetingSelection(meetingId, !selected)
}

const toggleBatchMode = () => {
  isBatchMode.value = !isBatchMode.value
  if (!isBatchMode.value) {
    selectedMeetingIds.value = []
  }
}

const deleteMeeting = (meetingId) => {
  const meeting = meetingStore.meetings.find((m) => m.id === meetingId)
  ElMessageBox.confirm(`确定删除会议"${meeting?.title}"?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await meetingStore.deleteMeeting(meetingId)
        ElMessage.success('会议已删除')
      } catch (error) {
        ElMessage.error('删除失败：' + error)
      }
    })
    .catch(() => {})
}

const batchDeleteMeetings = () => {
  if (selectedMeetingIds.value.length === 0) {
    return
  }

  ElMessageBox.confirm(`确定批量删除 ${selectedMeetingIds.value.length} 个会议吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await meetingStore.deleteMeetings(selectedMeetingIds.value)
        ElMessage.success(`已删除 ${selectedMeetingIds.value.length} 个会议`)
        selectedMeetingIds.value = []
        isBatchMode.value = false
      } catch (error) {
        ElMessage.error('批量删除失败：' + error)
      }
    })
    .catch(() => {})
}

// 页面加载时获取会议列表
onMounted(() => {
  meetingStore.fetchMeetings()
})
</script>

<style scoped lang="scss">
.meeting-list {
  padding: 20px 0;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    gap: 20px;

    h1 {
      margin: 0;
      font-size: 28px;
      color: #303133;
      min-width: 200px;
    }

    .header-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: flex-end;
      flex: 1;
    }
  }

  .stats-row {
    margin-bottom: 30px;

    :deep(.el-card) {
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15) !important;
      }
    }

    .stat-card {
      text-align: center;

      .stat-value {
        font-size: 32px;
        font-weight: 700;
        color: #409eff;
        margin-bottom: 8px;

        &.progress {
          color: #67c23a;
        }
      }

      .stat-label {
        font-size: 14px;
        color: #909399;
      }
    }
  }

  .meetings-row {
    margin-bottom: 30px;
  }

  .meeting-card {
    cursor: pointer;
    transition: all 0.3s ease;
    height: 100%;
    display: flex;
    flex-direction: column;

    &:hover {
      box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
      transform: translateY(-4px);

      :deep(.card-header) {
        .meeting-title {
          color: #409eff;
        }
      }
    }

    :deep(.el-card__body) {
      padding: 16px;
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      gap: 8px;

      .meeting-title {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #303133;
        transition: color 0.3s;
        flex: 1;
        word-break: break-word;
      }

      :deep(.el-tag) {
        flex-shrink: 0;
      }
    }

    .meeting-description {
      margin: 0 0 12px;
      font-size: 13px;
      color: #606266;
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .meeting-info {
      margin-bottom: 12px;

      .info-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #606266;
        margin-bottom: 4px;

        .icon {
          display: inline-block;
        }
      }
    }

    .progress-wrapper {
      margin: 12px 0;
      flex: 1;
      display: flex;
      align-items: flex-end;
    }

    .card-actions {
      display: flex;
      gap: 8px;
      padding-top: 12px;
      border-top: 1px solid #f0f0f0;
      margin-top: auto;
    }

    &.batch-mode {
      cursor: pointer;
    }

    &.is-selected {
      border: 1px solid #409eff;
      box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
    }

    .select-indicator {
      margin-bottom: 8px;
    }
  }
}

@media (max-width: 768px) {
  .meeting-list {
    .page-header {
      flex-direction: column;
      align-items: stretch;

      h1 {
        margin-bottom: 12px;
      }

      .header-actions {
        justify-content: stretch;

        :deep(input) {
          width: 100% !important;
        }
      }
    }
  }
}
</style>
