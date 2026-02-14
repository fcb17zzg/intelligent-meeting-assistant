import client from './client'

// ==================== 会议相关API ====================
export const meetingAPI = {
  // 获取会议列表
  getMeetings(params = {}) {
    return client.get('/meetings', { params })
  },

  // 获取会议详情
  getMeetingDetail(meetingId) {
    return client.get(`/meetings/${meetingId}`)
  },

  // 创建会议
  createMeeting(data) {
    return client.post('/meetings', data)
  },

  // 更新会议
  updateMeeting(meetingId, data) {
    return client.put(`/meetings/${meetingId}`, data)
  },

  // 删除会议
  deleteMeeting(meetingId) {
    return client.delete(`/meetings/${meetingId}`)
  },

  // 上传音频
  uploadAudio(meetingId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return client.post(`/meetings/${meetingId}/upload-audio`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 开始转录
  transcribeMeeting(meetingId) {
    return client.post(`/meetings/${meetingId}/transcribe`)
  },

  // 获取转录结果
  getTranscript(meetingId) {
    return client.get(`/meetings/${meetingId}/transcript`)
  },

  // 获取摘要
  getSummary(meetingId) {
    return client.get(`/meetings/${meetingId}/summary`)
  },

  // 获取任务列表
  getTasks(meetingId) {
    return client.get(`/meetings/${meetingId}/tasks`)
  },
}

// ==================== 任务相关API ====================
export const taskAPI = {
  // 获取所有任务
  getTasks(params = {}) {
    return client.get('/tasks', { params })
  },

  // 获取任务详情
  getTaskDetail(taskId) {
    return client.get(`/tasks/${taskId}`)
  },

  // 创建任务
  createTask(data) {
    return client.post('/tasks', data)
  },

  // 更新任务状态
  updateTask(taskId, data) {
    return client.put(`/tasks/${taskId}`, data)
  },

  // 删除任务
  deleteTask(taskId) {
    return client.delete(`/tasks/${taskId}`)
  },

  // 标记任务完成
  completeTask(taskId) {
    return client.patch(`/tasks/${taskId}/complete`)
  },
}

// ==================== 用户相关API ====================
export const userAPI = {
  // 获取用户列表
  getUsers() {
    return client.get('/users')
  },

  // 获取用户详情
  getUserDetail(userId) {
    return client.get(`/users/${userId}`)
  },

  // 创建用户
  createUser(data) {
    return client.post('/users', data)
  },

  // 更新用户
  updateUser(userId, data) {
    return client.put(`/users/${userId}`, data)
  },

  // 删除用户
  deleteUser(userId) {
    return client.delete(`/users/${userId}`)
  },
}
