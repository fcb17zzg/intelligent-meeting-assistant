<template>
  <div class="task-list">
    <!-- 统计概览 -->
    <div class="task-stats">
      <el-card shadow="hover">
        <template #header>
          <div class="card-header">
            <span>📊 任务概览</span>
          </div>
        </template>

        <el-row :gutter="20">
          <el-col :xs="24" :sm="12" :md="6">
            <div class="stat-item">
              <div class="stat-number">{{ totalTasks }}</div>
              <div class="stat-label">总任务数</div>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="stat-item active">
              <div class="stat-number">{{ pendingTasks }}</div>
              <div class="stat-label">待完成</div>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="stat-item completed">
              <div class="stat-number">{{ completedTasks }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="stat-item">
              <div class="stat-number">
                {{ totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0
                }}%
              </div>
              <div class="stat-label">完成率</div>
            </div>
          </el-col>
        </el-row>

        <!-- 进度条 -->
        <el-progress
          :percentage="totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0"
          :color="getProgressColor"
        />
      </el-card>
    </div>

    <!-- 筛选和排序 -->
    <div class="task-filters">
      <el-button-group>
        <el-button
          :type="filter === 'all' ? 'primary' : 'default'"
          @click="filter = 'all'"
        >
          全部
        </el-button>
        <el-button
          :type="filter === 'pending' ? 'primary' : 'default'"
          @click="filter = 'pending'"
        >
          待完成
        </el-button>
        <el-button
          :type="filter === 'completed' ? 'primary' : 'default'"
          @click="filter = 'completed'"
        >
          已完成
        </el-button>
      </el-button-group>

      <el-select v-model="sortBy" placeholder="排序方式" style="width: 150px">
        <el-option label="创建时间（新）" value="newest" />
        <el-option label="创建时间（旧）" value="oldest" />
        <el-option label="优先级（高）" value="priority" />
        <el-option label="期限（近）" value="due-date" />
      </el-select>
    </div>

    <!-- 任务列表 -->
    <div v-if="filteredTasks.length > 0" class="tasks-grid">
      <div v-for="task in filteredTasks" :key="task.id" class="task-card">
        <div class="task-header">
          <el-checkbox v-model="task.completed" @change="toggleTask(task)">
            <span class="task-title" :class="{ completed: task.completed }">
              {{ task.title }}
            </span>
          </el-checkbox>

          <div v-if="task.priority" class="priority-badge" :class="task.priority">
            {{ getPriorityLabel(task.priority) }}
          </div>
        </div>

        <div v-if="task.description" class="task-description">
          {{ task.description }}
        </div>

        <div class="task-meta">
          <span v-if="task.assignee" class="meta-item">
            👤 {{ task.assignee }}
          </span>
          <span v-if="task.due_date" class="meta-item" :class="getDueDateClass(task.due_date)">
            📅 {{ formatDate(task.due_date) }}
          </span>
          <span v-if="task.meeting_title" class="meta-item meeting">
            📌 {{ task.meeting_title }}
          </span>
        </div>

        <div class="task-actions">
          <el-button text type="primary" size="small" @click="editTask(task)">
            编辑
          </el-button>
          <el-button text type="danger" size="small" @click="deleteTask(task.id)">
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <el-empty :description="`暂无${getFilterLabel()}任务`" />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑任务" width="500px">
      <el-form :model="editingTask">
        <el-form-item label="任务标题" required>
          <el-input v-model="editingTask.title" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="editingTask.description" type="textarea" rows="3" />
        </el-form-item>

        <el-form-item label="优先级">
          <el-select v-model="editingTask.priority">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>

        <el-form-item label="负责人">
          <el-input v-model="editingTask.assignee" />
        </el-form-item>

        <el-form-item label="期限">
          <el-date-picker
            v-model="editingTask.due_date"
            type="datetime"
            placeholder="选择截止时间"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/dateUtils'

const props = defineProps({
  tasks: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update-task', 'delete-task', 'complete-task'])

const filter = ref('all')
const sortBy = ref('newest')
const editDialogVisible = ref(false)
const editingTask = ref({})

const totalTasks = computed(() => props.tasks.length)
const completedTasks = computed(() => props.tasks.filter((t) => t.completed).length)
const pendingTasks = computed(() => props.tasks.filter((t) => !t.completed).length)

const filteredTasks = computed(() => {
  let result = [...props.tasks]

  // 按状态筛选
  if (filter.value === 'pending') {
    result = result.filter((t) => !t.completed)
  } else if (filter.value === 'completed') {
    result = result.filter((t) => t.completed)
  }

  // 排序
  switch (sortBy.value) {
    case 'oldest':
      result.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      break
    case 'priority':
      const priorityMap = { high: 3, medium: 2, low: 1 }
      result.sort((a, b) => (priorityMap[b.priority] || 0) - (priorityMap[a.priority] || 0))
      break
    case 'due-date':
      result.sort((a, b) => new Date(a.due_date || Infinity) - new Date(b.due_date || Infinity))
      break
    case 'newest':
    default:
      result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  }

  return result
})

const getProgressColor = (percentage) => {
  if (percentage >= 80) return '#67c23a'
  if (percentage >= 50) return '#409eff'
  return '#e6a23c'
}

const getPriorityLabel = (priority) => {
  const map = { high: '高', medium: '中', low: '低' }
  return map[priority] || priority
}

const getDueDateClass = (dueDate) => {
  if (!dueDate) return ''
  const due = new Date(dueDate)
  const now = new Date()
  const daysLeft = Math.floor((due - now) / (1000 * 60 * 60 * 24))

  if (daysLeft < 0) return 'overdue'
  if (daysLeft <= 3) return 'urgent'
  return 'normal'
}

const getFilterLabel = () => {
  const map = { all: '', pending: '待完成', completed: '已完成' }
  return map[filter.value] || ''
}

const toggleTask = (task) => {
  emit('complete-task', task)
}

const editTask = (task) => {
  editingTask.value = { ...task }
  editDialogVisible.value = true
}

const saveEdit = () => {
  emit('update-task', editingTask.value)
  editDialogVisible.value = false
  ElMessage.success('任务已更新')
}

const deleteTask = (taskId) => {
  ElMessageBox.confirm('确定删除此任务？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      emit('delete-task', taskId)
      ElMessage.success('任务已删除')
    })
    .catch(() => {})
}
</script>

<style scoped lang="scss">
.task-list {
  width: 100%;
}

.task-stats {
  margin-bottom: 24px;

  :deep(.el-card) {
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 600;
      font-size: 16px;
    }
  }

  .stat-item {
    text-align: center;
    padding: 16px;
    border-radius: 8px;
    background-color: #f5f7fa;

    .stat-number {
      font-size: 32px;
      font-weight: 700;
      color: #303133;
      margin-bottom: 8px;
    }

    .stat-label {
      font-size: 14px;
      color: #909399;
    }

    &.active {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;

      .stat-number,
      .stat-label {
        color: white;
      }
    }

    &.completed {
      background-color: #f0f9ff;

      .stat-number {
        color: #67c23a;
      }
    }
  }

  :deep(.el-progress) {
    margin-top: 16px;
  }
}

.task-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;

  :deep(.el-button-group) {
    flex-wrap: wrap;
  }
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.task-card {
  background: white;
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.15);
    border-color: #409eff;
  }

  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
    gap: 12px;

    :deep(.el-checkbox) {
      flex: 1;
    }

    .task-title {
      font-weight: 500;
      font-size: 15px;
      color: #303133;

      &.completed {
        text-decoration: line-through;
        color: #909399;
      }
    }

    .priority-badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;

      &.high {
        background-color: #fef0f0;
        color: #f56c6c;
      }

      &.medium {
        background-color: #fdf6ec;
        color: #e6a23c;
      }

      &.low {
        background-color: #f0f9ff;
        color: #409eff;
      }
    }
  }

  .task-description {
    font-size: 13px;
    color: #606266;
    margin-bottom: 12px;
    line-height: 1.5;
    background-color: #f5f7fa;
    padding: 8px 12px;
    border-radius: 4px;
  }

  .task-meta {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
    font-size: 12px;

    .meta-item {
      color: #606266;

      &.overdue {
        color: #f56c6c;
        font-weight: 600;
      }

      &.urgent {
        color: #e6a23c;
        font-weight: 600;
      }

      &.meeting {
        color: #409eff;
      }
    }
  }

  .task-actions {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;
  }
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
}
</style>
