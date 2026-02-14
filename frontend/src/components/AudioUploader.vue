<template>
  <div class="audio-uploader">
    <div
      class="upload-area"
      :class="{ 'drag-over': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept="audio/*,.wav,.mp3,.m4a,.ogg"
        @change="handleFileSelect"
        style="display: none"
      />

      <div class="upload-content">
        <el-icon class="upload-icon">
          <DocumentAdd />
        </el-icon>
        <p class="upload-title">点击或拖拽上传音频文件</p>
        <p class="upload-hint">支持 WAV、MP3、M4A、OGG 等格式</p>
        <el-button type="primary" @click="$refs.fileInput.click()">
          选择文件
        </el-button>
      </div>
    </div>

    <!-- 上传进度 -->
    <div v-if="uploading" class="upload-progress">
      <el-progress :percentage="uploadProgress" :format="progressFormat" />
      <p class="progress-text">正在上传中...</p>
    </div>

    <!-- 已上传文件 -->
    <div v-if="selectedFile" class="selected-file">
      <div class="file-info">
        <el-icon><DocumentCopy /></el-icon>
        <div class="file-details">
          <p class="file-name">{{ selectedFile.name }}</p>
          <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
        </div>
      </div>
      <el-button v-if="!uploading" type="danger" text @click="clearFile">
        删除
      </el-button>
    </div>

    <!-- 错误信息 -->
    <div v-if="errorMessage" class="error-message">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ errorMessage }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, DocumentCopy, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  meetingId: {
    type: [String, Number],
    required: true,
  },
})

const emit = defineEmits(['upload-success', 'upload-error', 'file-selected'])

import meetingProcessingService from '../services/meetingProcessingService'

const fileInput = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const errorMessage = ref('')

const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB
const ALLOWED_TYPES = [
  'audio/mpeg',
  'audio/wav',
  'audio/m4a',
  'audio/ogg',
  'audio/webm',
]

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const progressFormat = (percentage) => {
  return `${Math.round(percentage)}%`
}

const validateFile = (file) => {
  errorMessage.value = ''

  if (!file) {
    errorMessage.value = '请选择一个文件'
    return false
  }

  if (file.size > MAX_FILE_SIZE) {
    errorMessage.value = `文件大小不能超过 ${formatFileSize(MAX_FILE_SIZE)}`
    return false
  }

  if (!ALLOWED_TYPES.includes(file.type)) {
    errorMessage.value = '仅支持音频文件格式'
    return false
  }

  return true
}

const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (validateFile(file)) {
    selectedFile.value = file
    emit('file-selected', file)
  }
}

const handleDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files?.[0]
  if (validateFile(file)) {
    selectedFile.value = file
    emit('file-selected', file)
  }
}

const clearFile = () => {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  errorMessage.value = ''
  uploadProgress.value = 0
}

const uploadFile = async () => {
  if (!selectedFile.value) {
    ElMessage.error('请先选择文件')
    return false
  }

  uploading.value = true
  uploadProgress.value = 0
  errorMessage.value = ''

  try {
    // 使用综合处理服务：上传 -> 转录 -> NLP -> 可视化（可选）
    const result = await meetingProcessingService.processMeeting(selectedFile.value, {
      language: 'auto',
      enableDiarization: true,
      enableNLPAnalysis: true,
      enableVisualization: false,
      meetingId: props.meetingId || 0,
    })

    uploading.value = false
    uploadProgress.value = 100

    if (result && result.status === 'success') {
      ElMessage.success('处理完成')
      emit('upload-success', result)
      clearFile()
      return true
    } else {
      const msg = result?.error || '处理失败'
      errorMessage.value = msg
      emit('upload-error', msg)
      return false
    }
  } catch (err) {
    uploading.value = false
    errorMessage.value = '上传或处理出错：' + (err.message || err)
    emit('upload-error', err.message || err)
    return false
  }
}

defineExpose({
  uploadFile,
  clearFile,
  selectedFile,
})
</script>

<style scoped lang="scss">
.audio-uploader {
  width: 100%;
}

.upload-area {
  border: 2px dashed #e0e0e0;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: #fafafa;

  &:hover {
    border-color: #409eff;
    background-color: #f0f9ff;
  }

  &.drag-over {
    border-color: #409eff;
    background-color: #f0f9ff;
    box-shadow: 0 0 12px rgba(64, 158, 255, 0.3);
  }

  .upload-content {
    .upload-icon {
      font-size: 48px;
      color: #409eff;
      margin-bottom: 12px;
    }

    .upload-title {
      font-size: 16px;
      font-weight: 500;
      color: #303133;
      margin: 12px 0 8px;
    }

    .upload-hint {
      font-size: 12px;
      color: #909399;
      margin: 0 0 20px;
    }
  }
}

.upload-progress {
  margin-top: 20px;
  padding: 20px;
  background-color: #f0f9ff;
  border-radius: 8px;

  .progress-text {
    margin-top: 12px;
    text-align: center;
    color: #409eff;
    font-size: 14px;
  }
}

.selected-file {
  margin-top: 20px;
  padding: 16px;
  background-color: #f0f9ff;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #c6e2ff;

  .file-info {
    display: flex;
    align-items: center;
    gap: 12px;

    :deep(.el-icon) {
      font-size: 24px;
      color: #409eff;
    }

    .file-details {
      text-align: left;

      .file-name {
        margin: 0;
        font-size: 14px;
        font-weight: 500;
        color: #303133;
        word-break: break-all;
      }

      .file-size {
        margin: 4px 0 0;
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

.error-message {
  margin-top: 16px;
  padding: 12px 16px;
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  color: #f56c6c;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;

  :deep(.el-icon) {
    flex-shrink: 0;
  }
}
</style>
