<template>
  <div class="meeting-list">
    <!-- 页面标题和操作 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h1>会议管理中心</h1>
        <span class="page-title-badge">Command Room</span>
      </div>
      <div class="header-actions">
        <div class="search-wrap">
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
        </div>
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
      <el-col :xs="24" :sm="12" :md="6" class="stat-col-1">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-value">{{ meetingStore.totalMeetings }}</div>
            <div class="stat-label">总会议</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="stat-col-2">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon">⏳</div>
            <div class="stat-value">{{ meetingStore.pendingMeetings.length }}</div>
            <div class="stat-label">待处理</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="stat-col-3">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-value">{{ meetingStore.completedMeetings.length }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="stat-col-4">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon">🚀</div>
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
          :class="[
            {
              'batch-mode': isBatchMode,
              'is-selected': isMeetingSelected(meeting.id)
            },
            getMeetingCardStatusClass(meeting.status)
          ]"
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
            <el-tag :type="getMeetingStatusType(meeting.status)" effect="plain" :class="getMeetingTagClass(meeting.status)">
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
            <el-button text type="primary" size="small" class="detail-btn" @click.stop="viewDetail(meeting.id)">
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
    scheduled: 'primary',
    in_progress: 'warning',
    completed: 'success',
    archived: 'danger',
  }
  return map[normalizedStatus] || 'info'
}

const getMeetingTagClass = (status) => {
  const normalizedStatus = normalizeMeetingStatus(status)
  if (normalizedStatus === 'completed') return 'tag-completed'
  if (normalizedStatus === 'scheduled') return 'tag-scheduled'
  return ''
}

const getMeetingCardStatusClass = (status) => {
  const normalizedStatus = normalizeMeetingStatus(status)
  if (normalizedStatus === 'completed') return 'status-completed'
  if (normalizedStatus === 'in_progress') return 'status-in-progress'
  if (normalizedStatus === 'archived') return 'status-archived'
  return 'status-scheduled'
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

onMounted(() => {
  meetingStore.fetchMeetings()
})
</script>

<style scoped lang="scss">
.meeting-list {
  padding: 16px 0;
  animation: fadeInUp 0.5s ease;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28px;
    gap: 20px;

    .page-title-wrap {
      display: flex;
      align-items: center;
      gap: 12px;

      h1 {
        margin: 0;
        min-width: 220px;
        font-size: 30px;
        line-height: 1.1;
        font-weight: 800;
        background: var(--grad-primary);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }

      .page-title-badge {
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #4e5ebc;
        background: rgba(102, 126, 234, 0.14);
        border: 1px solid rgba(102, 126, 234, 0.2);
      }
    }

    .header-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: flex-end;
      flex: 1;

      .search-wrap {
        border-radius: 999px;
        padding: 4px;
        background: linear-gradient(130deg, rgba(102, 126, 234, 0.2), rgba(79, 172, 254, 0.18));
      }
    }
  }

  .stats-row {
    margin-bottom: 30px;

    > [class*='stat-col-'] {
      animation: fadeInScale 0.45s ease both;
    }

    .stat-col-1 { animation-delay: 0s; }
    .stat-col-2 { animation-delay: 0.1s; }
    .stat-col-3 { animation-delay: 0.2s; }
    .stat-col-4 { animation-delay: 0.3s; }

    :deep(.el-card) {
      border: none;
      overflow: hidden;
      color: #fff;

      .el-card__body {
        position: relative;
        z-index: 1;
      }

      &::before {
        content: '';
        position: absolute;
        top: -44px;
        right: -32px;
        width: 108px;
        height: 108px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
      }
    }

    .stat-col-1 :deep(.el-card) { background: var(--grad-stat-1) !important; }
    .stat-col-2 :deep(.el-card) { background: var(--grad-stat-2) !important; }
    .stat-col-3 :deep(.el-card) { background: var(--grad-stat-3) !important; }
    .stat-col-4 :deep(.el-card) { background: var(--grad-stat-4) !important; }

    .stat-card {
      text-align: left;

      .stat-icon {
        font-size: 18px;
        margin-bottom: 8px;
        opacity: 0.95;
      }

      .stat-value {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 8px;
        animation: countUp 0.45s ease;

        &.progress {
          color: #fff;
        }
      }

      .stat-label {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.88);
      }
    }
  }

  .meetings-row {
    margin-bottom: 30px;
  }

  .meeting-card {
    cursor: pointer;
    transition: var(--transition-base);
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: #7a87d7;
    }

    &.status-completed::before {
      background: linear-gradient(180deg, #43e97b 0%, #2cd3b4 100%);
    }

    &.status-in-progress::before {
      background: linear-gradient(180deg, #f6d365 0%, #fda085 100%);
    }

    &.status-archived::before {
      background: linear-gradient(180deg, #f093fb 0%, #f5576c 100%);
    }

    &.status-scheduled::before {
      background: linear-gradient(180deg, #4f8bff 0%, #2d73ff 100%);
    }

    &:hover {
      box-shadow: 0 20px 44px rgba(102, 126, 234, 0.28);
      transform: translateY(-6px) scale(1.01);

      :deep(.card-header) {
        .meeting-title {
          color: #5568d8;
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
        font-weight: 700;
        color: #303133;
        transition: color 0.3s;
        flex: 1;
        word-break: break-word;
      }

      :deep(.el-tag) {
        flex-shrink: 0;
      }

      :deep(.el-tag.tag-completed) {
        color: #1f9d50;
        border-color: rgba(31, 157, 80, 0.45);
        background: rgba(31, 157, 80, 0.12);
      }

      :deep(.el-tag.tag-scheduled) {
        color: #2d73ff;
        border-color: rgba(45, 115, 255, 0.45);
        background: rgba(45, 115, 255, 0.12);
      }
    }

    .meeting-description {
      margin: 0 0 12px;
      font-size: 13px;
      color: #5f6580;
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      line-clamp: 2;
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
      border-top: 1px solid rgba(120, 132, 198, 0.14);
      margin-top: auto;

      :deep(.detail-btn) {
        --el-button-text-color: #ffffff;
        color: #ffffff;
      }
    }

    &.batch-mode {
      cursor: pointer;
    }

    &.is-selected {
      border: 1px solid #667eea;
      box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
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

      .page-title-wrap {
        justify-content: space-between;

        h1 {
          min-width: unset;
          font-size: 24px;
        }
      }

      .header-actions {
        justify-content: stretch;

        .search-wrap {
          width: 100%;
        }

        :deep(input) {
          width: 100% !important;
        }
      }
    }
  }
}
</style>
