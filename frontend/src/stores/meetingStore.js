import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { meetingAPI } from '@/api'

export const useMeetingStore = defineStore('meeting', () => {
  // 状态
  const meetings = ref([])
  const currentMeeting = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 计算属性
  const totalMeetings = computed(() => meetings.value.length)
  const completedMeetings = computed(() =>
    meetings.value.filter((m) => m.status === 'completed')
  )
  const pendingMeetings = computed(() =>
    meetings.value.filter((m) => m.status === 'pending')
  )

  // 方法
  const fetchMeetings = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await meetingAPI.getMeetings()
      meetings.value = response.data || response
    } catch (err) {
      error.value = err.message || '获取会议列表失败'
      console.error('Fetch meetings error:', err)
    } finally {
      loading.value = false
    }
  }

  const fetchMeetingDetail = async (meetingId) => {
    loading.value = true
    error.value = null
    try {
      const response = await meetingAPI.getMeetingDetail(meetingId)
      currentMeeting.value = response.data || response
      return currentMeeting.value
    } catch (err) {
      error.value = err.message || '获取会议详情失败'
      console.error('Fetch meeting detail error:', err)
    } finally {
      loading.value = false
    }
  }

  const createMeeting = async (meetingData) => {
    loading.value = true
    error.value = null
    try {
      const response = await meetingAPI.createMeeting(meetingData)
      const newMeeting = response.data || response
      meetings.value.push(newMeeting)
      return newMeeting
    } catch (err) {
      error.value = err.message || '创建会议失败'
      console.error('Create meeting error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateMeeting = async (meetingId, meetingData) => {
    loading.value = true
    error.value = null
    try {
      const response = await meetingAPI.updateMeeting(meetingId, meetingData)
      const updated = response.data || response
      const index = meetings.value.findIndex((m) => m.id === meetingId)
      if (index !== -1) {
        meetings.value[index] = updated
      }
      if (currentMeeting.value?.id === meetingId) {
        currentMeeting.value = updated
      }
      return updated
    } catch (err) {
      error.value = err.message || '更新会议失败'
      console.error('Update meeting error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteMeeting = async (meetingId) => {
    loading.value = true
    error.value = null
    try {
      await meetingAPI.deleteMeeting(meetingId)
      meetings.value = meetings.value.filter((m) => m.id !== meetingId)
      if (currentMeeting.value?.id === meetingId) {
        currentMeeting.value = null
      }
    } catch (err) {
      error.value = err.message || '删除会议失败'
      console.error('Delete meeting error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const uploadAudio = async (meetingId, file) => {
    loading.value = true
    error.value = null
    try {
      const response = await meetingAPI.uploadAudio(meetingId, file)
      return response.data || response
    } catch (err) {
      error.value = err.message || '上传音频失败'
      console.error('Upload audio error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const transcribeMeeting = async (meetingId) => {
    loading.value = true
    error.value = null
    try {
      const response = await meetingAPI.transcribeMeeting(meetingId)
      return response.data || response
    } catch (err) {
      error.value = err.message || '转录失败'
      console.error('Transcribe error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const getSummary = async (meetingId) => {
    try {
      const response = await meetingAPI.getSummary(meetingId)
      return response.data || response
    } catch (err) {
      error.value = err.message || '获取摘要失败'
      console.error('Get summary error:', err)
      throw err
    }
  }

  const getTasks = async (meetingId) => {
    try {
      const response = await meetingAPI.getTasks(meetingId)
      return response.data || response
    } catch (err) {
      error.value = err.message || '获取任务列表失败'
      console.error('Get tasks error:', err)
      throw err
    }
  }

  return {
    // 状态
    meetings,
    currentMeeting,
    loading,
    error,
    // 计算属性
    totalMeetings,
    completedMeetings,
    pendingMeetings,
    // 方法
    fetchMeetings,
    fetchMeetingDetail,
    createMeeting,
    updateMeeting,
    deleteMeeting,
    uploadAudio,
    transcribeMeeting,
    getSummary,
    getTasks,
  }
})
