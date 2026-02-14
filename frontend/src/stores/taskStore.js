import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskAPI } from '@/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const loading = ref(false)
  const error = ref(null)

  const completedTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'completed')
  )
  const pendingTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'pending')
  )

  const fetchTasks = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await taskAPI.getTasks(params)
      tasks.value = response.data || response
    } catch (err) {
      error.value = err.message || '获取任务失败'
      console.error('Fetch tasks error:', err)
    } finally {
      loading.value = false
    }
  }

  const updateTask = async (taskId, data) => {
    try {
      const response = await taskAPI.updateTask(taskId, data)
      const updated = response.data || response
      const index = tasks.value.findIndex((t) => t.id === taskId)
      if (index !== -1) {
        tasks.value[index] = updated
      }
      return updated
    } catch (err) {
      error.value = err.message || '更新任务失败'
      throw err
    }
  }

  const completeTask = async (taskId) => {
    try {
      const response = await taskAPI.completeTask(taskId)
      const updated = response.data || response
      const index = tasks.value.findIndex((t) => t.id === taskId)
      if (index !== -1) {
        tasks.value[index] = updated
      }
      return updated
    } catch (err) {
      error.value = err.message || '完成任务失败'
      throw err
    }
  }

  return {
    tasks,
    loading,
    error,
    completedTasks,
    pendingTasks,
    fetchTasks,
    updateTask,
    completeTask,
  }
})
