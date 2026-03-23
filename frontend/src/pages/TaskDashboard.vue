<template>
  <div class="task-dashboard">
    <div class="page-header">
      <div>
        <h1>任务管理中心</h1>
        <p>支持手动创建、行动项导入、进度标记与站内提醒。</p>
      </div>
      <el-button type="primary" @click="$router.push('/meetings')">查看会议</el-button>
    </div>

    <el-row :gutter="16" class="top-row">
      <el-col :xs="24" :lg="16">
        <el-card class="panel" shadow="hover">
          <template #header>
            <div class="panel-title">创建任务</div>
          </template>

          <el-form :model="createForm" label-width="90px">
            <el-row :gutter="12">
              <el-col :xs="24" :md="12">
                <el-form-item label="任务标题" required>
                  <el-input v-model="createForm.title" placeholder="例如：下周演示稿终版" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="优先级">
                  <el-select v-model="createForm.priority" style="width: 100%">
                    <el-option label="紧急" value="urgent" />
                    <el-option label="高" value="high" />
                    <el-option label="中" value="medium" />
                    <el-option label="低" value="low" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="任务描述">
              <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="可选" />
            </el-form-item>

            <el-row :gutter="12">
              <el-col :xs="24" :md="8">
                <el-form-item label="负责人">
                  <el-input v-model="createForm.assignee_name" placeholder="可留空" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="截止日期">
                  <el-date-picker
                    v-model="createForm.due_date"
                    type="datetime"
                    placeholder="可留空"
                    value-format="YYYY-MM-DDTHH:mm:ss"
                    clearable
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="关联会议">
                  <el-select v-model="createForm.meeting_id" placeholder="可选" clearable style="width: 100%">
                    <el-option
                      v-for="meeting in meetings"
                      :key="meeting.id"
                      :label="meeting.title"
                      :value="meeting.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <div class="form-actions">
              <el-button @click="resetCreateForm">重置</el-button>
              <el-button type="primary" :loading="creatingTask" @click="createTask">创建任务</el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="panel" shadow="hover">
          <template #header>
            <div class="panel-title">最近最紧急任务</div>
          </template>

          <el-empty v-if="urgentTasks.length === 0" description="暂无紧急任务" />
          <div v-else class="urgent-list">
            <div v-for="task in urgentTasks" :key="`urgent-${task.id}`" class="urgent-item">
              <div class="urgent-main">
                <span class="urgent-title">{{ task.title }}</span>
                <el-tag size="small" :type="priorityTagType(task.priority)">{{ priorityLabel(task.priority) }}</el-tag>
              </div>
              <div class="urgent-meta">
                <span>👤 {{ task.assignee_name || '待分配' }}</span>
                <span :class="{ danger: task.is_overdue, warning: task.is_due_soon }">
                  📅 {{ task.due_date ? formatDate(task.due_date) : '待设置' }}
                </span>
              </div>
              <div v-if="task.meeting_title" class="urgent-meeting">来源会议：{{ task.meeting_title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="top-row">
      <el-col :xs="24" :lg="10">
        <el-card class="panel" shadow="hover">
          <template #header>
            <div class="panel-title">从摘要行动项导入</div>
          </template>

          <el-space direction="vertical" style="width: 100%" fill>
            <el-select v-model="selectedMeetingId" placeholder="选择会议" style="width: 100%" @change="loadMeetingActionItems">
              <el-option v-for="meeting in meetings" :key="`source-${meeting.id}`" :label="meeting.title" :value="meeting.id" />
            </el-select>

            <el-empty v-if="selectedMeetingId && actionItems.length === 0" description="该会议暂无可导入行动项" />

            <div v-for="item in actionItems" :key="item.source_key" class="action-item-row">
              <div class="action-text">{{ item.description }}</div>
              <div class="action-meta">
                <span>👤 {{ item.assignee || '待分配' }}</span>
                <span>📅 {{ item.due_date ? formatDate(item.due_date) : '待设置' }}</span>
              </div>
              <el-button size="small" type="primary" plain @click="openImportDialog(item)">加入任务</el-button>
            </div>
          </el-space>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card class="panel" shadow="hover">
          <template #header>
            <div class="panel-title">站内提醒</div>
          </template>

          <el-alert
            :title="`逾期 ${reminders.overdue_count || 0} 项，48小时内到期 ${reminders.due_soon_count || 0} 项`"
            :type="(reminders.overdue_count || 0) > 0 ? 'error' : 'warning'"
            :closable="false"
          />

          <div class="reminder-columns">
            <div>
              <h4>已逾期</h4>
              <el-empty v-if="(reminders.overdue || []).length === 0" description="无" />
              <div v-for="task in reminders.overdue || []" :key="`od-${task.id}`" class="reminder-item">
                <span>{{ task.title }}</span>
                <span class="danger">{{ task.due_date ? formatDate(task.due_date) : '待设置' }}</span>
              </div>
            </div>
            <div>
              <h4>即将到期</h4>
              <el-empty v-if="(reminders.due_soon || []).length === 0" description="无" />
              <div v-for="task in reminders.due_soon || []" :key="`ds-${task.id}`" class="reminder-item">
                <span>{{ task.title }}</span>
                <span class="warning">{{ task.due_date ? formatDate(task.due_date) : '待设置' }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="panel" shadow="hover">
      <template #header>
        <div class="panel-title">全部任务</div>
      </template>
      <TaskList
        :tasks="tasks"
        @complete-task="completeTask"
        @update-task="updateTask"
        @delete-task="deleteTask"
      />
    </el-card>

    <el-dialog v-model="importDialogVisible" title="加入任务" width="520px">
      <el-form :model="importForm" label-width="90px">
        <el-form-item label="任务标题" required>
          <el-input v-model="importForm.title" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="importForm.description" type="textarea" rows="3" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="importForm.assignee_name" clearable placeholder="可留空" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker
            v-model="importForm.due_date"
            type="datetime"
            placeholder="可留空"
            value-format="YYYY-MM-DDTHH:mm:ss"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="importForm.priority" style="width: 100%">
            <el-option label="紧急" value="urgent" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importingTask" @click="confirmImportTask">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { meetingAPI, taskAPI } from '@/api'
import { formatDate } from '@/utils/dateUtils'
import TaskList from '@/components/TaskList.vue'

const meetings = ref([])
const meetingTitleMap = ref({})
const tasks = ref([])
const urgentTasks = ref([])
const reminders = ref({ overdue_count: 0, due_soon_count: 0, overdue: [], due_soon: [] })
const selectedMeetingId = ref(null)
const actionItems = ref([])

const creatingTask = ref(false)
const importingTask = ref(false)
const importDialogVisible = ref(false)

const createForm = ref({
  title: '',
  description: '',
  assignee_name: '',
  due_date: null,
  priority: 'medium',
  meeting_id: null,
})

const importForm = ref({
  title: '',
  description: '',
  assignee_name: '',
  due_date: null,
  priority: 'medium',
  meeting_id: null,
})

const priorityLabel = (priority) => {
  const map = { urgent: '紧急', high: '高', medium: '中', low: '低' }
  return map[priority] || '中'
}

const priorityTagType = (priority) => {
  const map = { urgent: 'danger', high: 'warning', medium: 'primary', low: 'info' }
  return map[priority] || 'primary'
}

const normalizeTask = (task) => ({
  ...task,
  completed: task.status === 'completed',
  assignee_name: task.assignee_name || task.assignee || '',
  meeting_title: task.meeting_title || meetingTitleMap.value[task.meeting_id] || '',
})

const loadMeetings = async () => {
  const response = await meetingAPI.getMeetings()
  const payload = response?.data || response || []
  meetings.value = Array.isArray(payload) ? payload : (payload.meetings || [])
  meetingTitleMap.value = meetings.value.reduce((acc, meeting) => {
    acc[meeting.id] = meeting.title
    return acc
  }, {})
}

const loadTasks = async () => {
  const response = await taskAPI.getTasks()
  const payload = response?.data || response || []
  const list = Array.isArray(payload) ? payload : (payload.tasks || [])
  tasks.value = list.map(normalizeTask)
}

const loadUrgentTasks = async () => {
  const response = await taskAPI.getUrgentTasks({ limit: 8 })
  const payload = response?.data || response || {}
  urgentTasks.value = (payload.items || []).map(normalizeTask)
}

const loadReminders = async () => {
  const response = await taskAPI.getReminders()
  reminders.value = response?.data || response || reminders.value
}

const loadMeetingActionItems = async (meetingId) => {
  if (!meetingId) {
    actionItems.value = []
    return
  }

  try {
    const response = await meetingAPI.getSummary(meetingId)
    const payload = response?.data || response || {}
    const source = Array.isArray(payload.action_items) ? payload.action_items : []
    actionItems.value = source
      .map((item, index) => ({
        source_key: `${meetingId}-${item?.id || index}`,
        meeting_id: Number(meetingId),
        description: String(item?.description || item?.text || '').trim(),
        assignee: item?.assignee ? String(item.assignee).trim() : '',
        due_date: item?.due_date || null,
        priority: item?.priority || 'medium',
      }))
      .filter((item) => item.description)
  } catch (error) {
    ElMessage.error('加载行动项失败')
    actionItems.value = []
  }
}

const resetCreateForm = () => {
  createForm.value = {
    title: '',
    description: '',
    assignee_name: '',
    due_date: null,
    priority: 'medium',
    meeting_id: null,
  }
}

const refreshAll = async () => {
  await Promise.all([loadTasks(), loadUrgentTasks(), loadReminders()])
}

const createTask = async () => {
  if (!String(createForm.value.title || '').trim()) {
    ElMessage.warning('请输入任务标题')
    return
  }

  const selectedMeeting = Number(createForm.value.meeting_id || selectedMeetingId.value || 0)
  if (!selectedMeeting) {
    ElMessage.warning('请先选择关联会议')
    return
  }

  creatingTask.value = true
  try {
    await taskAPI.createTask({
      meeting_id: selectedMeeting,
      title: String(createForm.value.title).trim(),
      description: String(createForm.value.description || '').trim() || null,
      assignee_name: String(createForm.value.assignee_name || '').trim() || null,
      due_date: createForm.value.due_date || null,
      priority: createForm.value.priority || 'medium',
    })
    ElMessage.success('任务已创建')
    resetCreateForm()
    await refreshAll()
  } catch (error) {
    ElMessage.error('创建任务失败')
  } finally {
    creatingTask.value = false
  }
}

const openImportDialog = (item) => {
  importForm.value = {
    title: item.description.slice(0, 80),
    description: item.description,
    assignee_name: item.assignee || '',
    due_date: item.due_date || null,
    priority: item.priority || 'medium',
    meeting_id: item.meeting_id,
  }
  importDialogVisible.value = true
}

const confirmImportTask = async () => {
  if (!String(importForm.value.title || '').trim()) {
    ElMessage.warning('任务标题不能为空')
    return
  }

  const selectedMeeting = Number(importForm.value.meeting_id || selectedMeetingId.value || 0)
  if (!selectedMeeting) {
    ElMessage.warning('缺少会议信息，无法导入')
    return
  }

  importingTask.value = true
  try {
    await taskAPI.createTask({
      meeting_id: selectedMeeting,
      title: String(importForm.value.title).trim(),
      description: String(importForm.value.description || '').trim() || null,
      assignee_name: String(importForm.value.assignee_name || '').trim() || null,
      due_date: importForm.value.due_date || null,
      priority: importForm.value.priority || 'medium',
    })
    ElMessage.success('行动项已加入任务')
    importDialogVisible.value = false
    await refreshAll()
  } catch (error) {
    ElMessage.error('导入任务失败')
  } finally {
    importingTask.value = false
  }
}

const completeTask = async (task) => {
  try {
    await taskAPI.updateTask(task.id, {
      status: task.completed ? 'completed' : 'pending',
    })
    await refreshAll()
  } catch (error) {
    ElMessage.error('更新任务状态失败')
  }
}

const updateTask = async (task) => {
  try {
    await taskAPI.updateTask(task.id, {
      title: task.title,
      description: task.description || null,
      assignee_name: String(task.assignee || task.assignee_name || '').trim() || null,
      due_date: task.due_date || null,
      priority: task.priority || 'medium',
      status: task.completed ? 'completed' : (task.status || 'pending'),
    })
    ElMessage.success('任务已更新')
    await refreshAll()
  } catch (error) {
    ElMessage.error('更新任务失败')
  }
}

const deleteTask = async (taskId) => {
  try {
    await taskAPI.deleteTask(taskId)
    ElMessage.success('任务已删除')
    await refreshAll()
  } catch (error) {
    ElMessage.error('删除任务失败')
  }
}

onMounted(async () => {
  try {
    await loadMeetings()
    await refreshAll()
  } catch (error) {
    ElMessage.error('初始化任务主页失败')
  }
})
</script>

<style scoped lang="scss">
.task-dashboard {
  padding: 12px 0;

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;

    h1 {
      margin: 0;
      font-size: 28px;
    }

    p {
      margin: 8px 0 0;
      color: #606266;
    }
  }

  .top-row {
    margin-bottom: 16px;
  }

  .panel {
    height: 100%;
  }

  .panel-title {
    font-weight: 600;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .urgent-list,
  .action-item-row {
    display: grid;
    gap: 8px;
  }

  .urgent-item {
    border: 1px solid #ebeef5;
    border-left: 3px solid #e6a23c;
    border-radius: 6px;
    padding: 10px;

    .urgent-main {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
    }

    .urgent-title {
      font-weight: 600;
      color: #303133;
    }

    .urgent-meta {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 12px;
      color: #606266;

      .danger {
        color: #f56c6c;
      }

      .warning {
        color: #e6a23c;
      }
    }

    .urgent-meeting {
      margin-top: 4px;
      font-size: 12px;
      color: #909399;
    }
  }

  .action-item-row {
    border: 1px solid #ebeef5;
    border-left: 3px solid #67c23a;
    border-radius: 6px;
    padding: 10px;
    margin-bottom: 10px;

    .action-text {
      font-weight: 500;
      color: #303133;
    }

    .action-meta {
      display: flex;
      gap: 12px;
      color: #909399;
      font-size: 12px;
    }
  }

  .reminder-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;

    h4 {
      margin: 0 0 8px;
      font-size: 14px;
    }

    .reminder-item {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #606266;
      background: #f5f7fa;
      padding: 8px;
      border-radius: 4px;
      margin-bottom: 6px;
    }

    .danger {
      color: #f56c6c;
    }

    .warning {
      color: #e6a23c;
    }
  }
}

@media (max-width: 992px) {
  .task-dashboard {
    .reminder-columns {
      grid-template-columns: 1fr;
    }
  }
}

.task-dashboard {
  .page-header {
    border-radius: 18px;
    padding: 18px 20px;
    background: linear-gradient(120deg, rgba(102, 126, 234, 0.14), rgba(79, 172, 254, 0.15));
    border: 1px solid rgba(136, 153, 240, 0.25);

    h1 {
      background: var(--grad-primary);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
  }

  .panel-title {
    position: relative;
    padding-left: 12px;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 2px;
      bottom: 2px;
      width: 4px;
      border-radius: 99px;
      background: var(--grad-primary);
    }
  }

  .urgent-item {
    transition: var(--transition-base);

    &:hover {
      box-shadow: 0 0 16px rgba(245, 87, 108, 0.4);
      transform: translateX(4px);
      border-left-color: #f5576c;
    }
  }

  .action-item-row {
    border-left-color: #2bc770;
    transition: var(--transition-base);

    &:hover {
      box-shadow: 0 0 16px rgba(67, 233, 123, 0.34);
      border-color: rgba(67, 233, 123, 0.45);
    }
  }

  .reminder-columns {
    h4 {
      display: flex;
      align-items: center;
      gap: 6px;

      &::before {
        content: '';
        width: 7px;
        height: 7px;
        border-radius: 50%;
      }
    }

    > div:first-child h4::before {
      background: #f5576c;
    }

    > div:last-child h4::before {
      background: #fa8231;
    }

    .reminder-item {
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.56);
      background: rgba(255, 255, 255, 0.62);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      transition: var(--transition-base);

      &:hover {
        background: rgba(255, 255, 255, 0.95);
      }
    }
  }
}
</style>

