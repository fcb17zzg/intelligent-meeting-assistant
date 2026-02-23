<template>
  <div class="summary-display">
    <!-- 加载状态 -->
    <el-skeleton v-if="loading" :rows="5" animated />

    <!-- 摘要内容 -->
    <div v-else-if="displayedSummary" class="summary-content">
      <!-- 会议信息 -->
      <div class="summary-header">
        <h3>{{ displayedSummary.title || '会议摘要' }}</h3>
        <div class="summary-meta">
          <el-tag v-if="displayedSummary.duration" type="info">
            ⏱️ {{ formatDuration(displayedSummary.duration) }}
          </el-tag>
          <el-tag v-if="displayedSummary.created_at" type="warning">
            📅 {{ formatDate(displayedSummary.created_at) }}
          </el-tag>
          <el-tag v-if="displayedSummary.speaker_count">
            👥 {{ displayedSummary.speaker_count }} 位发言人
          </el-tag>
        </div>
      </div>

      <!-- 主要内容摘要 -->
      <div v-if="displayedSummary.summary_text" class="summary-section">
        <h4>📝 会议纪要</h4>
        <div class="summary-text">
          {{ displayedSummary.summary_text }}
        </div>
      </div>

      <!-- 关键议题 -->
      <div v-if="displayedSummary.key_topics && displayedSummary.key_topics.length" class="summary-section">
        <h4>🎯 关键议题</h4>
        <ul class="topics-list">
          <li v-for="(topic, index) in displayedSummary.key_topics" :key="index">
            {{ topic }}
          </li>
        </ul>
      </div>

      <!-- 重点突出 -->
      <div
        v-if="displayedSummary.highlights && displayedSummary.highlights.length"
        class="summary-section"
      >
        <h4>⭐ 重点突出</h4>
        <div class="highlights-list">
          <div v-for="(highlight, index) in displayedSummary.highlights" :key="index" class="highlight-item">
            <span class="highlight-mark">•</span>
            {{ highlight }}
          </div>
        </div>
      </div>

      <!-- 行动项 -->
      <div
        v-if="displayedSummary.action_items && displayedSummary.action_items.length"
        class="summary-section"
      >
        <h4>✅ 行动项</h4>
        <div class="action-items-list">
          <div v-for="(item, index) in displayedSummary.action_items" :key="index" class="action-item">
            <el-checkbox v-model="item.completed" @change="updateActionItem(item)">
              {{ item.text }}
            </el-checkbox>
            <span v-if="item.assignee" class="assignee">(负责人: {{ item.assignee }})</span>
            <span v-if="item.due_date" class="due-date">期限: {{ formatDate(item.due_date) }}</span>
          </div>
        </div>
      </div>

      <!-- 发言人统计 -->
      <div
        v-if="displayedSummary.speaker_stats && Object.keys(displayedSummary.speaker_stats).length"
        class="summary-section"
      >
        <h4>🎤 发言人统计</h4>
        <div class="speaker-stats">
          <div
            v-for="(count, speaker) in displayedSummary.speaker_stats"
            :key="speaker"
            class="speaker-stat"
          >
            <div class="speaker-name">{{ speaker }}</div>
            <el-progress
              :percentage="calculatePercentage(count, displayedSummary.speaker_stats)"
              :color="getProgressColor(count, displayedSummary.speaker_stats)"
              :show-text="true"
            />
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="summary-actions">
        <el-button type="primary" @click="exportSummary">
          📥 导出摘要
        </el-button>
        <el-button @click="refreshSummary">
          🔄 刷新
        </el-button>
        <el-button v-if="!editingNotes" @click="startEditNotes">
          ✏️ 编辑笔记
        </el-button>
      </div>

      <!-- 额外笔记 -->
      <div class="summary-section">
        <h4>📌 笔记</h4>
        <div v-if="!editingNotes" class="notes-display">
          <p v-if="displayedSummary.notes">{{ displayedSummary.notes }}</p>
          <p v-else style="color: #909399">暂无笔记</p>
        </div>
        <div v-else class="notes-edit">
          <el-input
            v-model="editableNotes"
            type="textarea"
            rows="4"
            placeholder="添加笔记..."
          />
          <div style="margin-top: 12px; display: flex; gap: 8px">
            <el-button type="primary" @click="saveNotes">保存</el-button>
            <el-button @click="cancelEditNotes">取消</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-else description="暂无摘要数据" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { formatDate, formatDuration } from '@/utils/dateUtils'
import nlpAnalysisService from '@/services/nlpAnalysisService'
import { meetingAPI } from '@/api/index'

const props = defineProps({
  summary: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  transcription: {
    type: Object,
    default: null,
  },
  meetingId: {
    type: [Number, String],
    default: null,
  },
})

const emit = defineEmits(['update-notes', 'refresh'])

const editingNotes = ref(false)
const localLoading = ref(false)
const localSummary = ref(null)
const editableNotes = ref('')

const displayedSummary = computed(() => {
  const remote = props.summary || null
  const local = localSummary.value || null

  const normalizedRemote = remote
    ? {
        ...remote,
        summary_text: remote.summary_text || remote.summary || '',
        title: remote.title || '会议摘要',
      }
    : null

  const localHasContent = !!(
    local &&
    (
      (local.summary_text && String(local.summary_text).trim()) ||
      (local.notes && String(local.notes).trim()) ||
      (Array.isArray(local.key_topics) && local.key_topics.length > 0) ||
      (Array.isArray(local.highlights) && local.highlights.length > 0) ||
      (Array.isArray(local.action_items) && local.action_items.length > 0)
    )
  )

  if (localHasContent) {
    return {
      ...(normalizedRemote || {}),
      ...local,
    }
  }

  return normalizedRemote || local
})

// 当收到转录数据时自动触发 NLP 分析和摘要生成
watch(
  () => props.transcription,
  async (newVal) => {
    if (!newVal) return
    try {
      localLoading.value = true

      const segments = newVal.segments || []
      const segmentsText = segments
        .map((s) => (s && s.text ? String(s.text).trim() : ''))
        .filter((t) => t)
        .join(' ')
      const textFromResult = newVal.text ? String(newVal.text).trim() : ''
      const fullText = textFromResult || segmentsText

      // 空文本短路：无有效文本时跳过摘要接口，避免无效请求
      const summaryPromise = fullText
        ? nlpAnalysisService.generateSummary(fullText, 'medium', newVal.language || 'zh')
        : Promise.resolve({ summary: '' })

      // 并行请求：处理转录（实体/关键词/句子级分析）与摘要
      const [processedResp, summaryResp] = await Promise.all([
        nlpAnalysisService.processTranscript(segments, newVal.language || 'zh'),
        summaryPromise,
      ])

      const processedSegments = Array.isArray(processedResp?.segments) ? processedResp.segments : []
      const processedSpeakerStats = processedResp?.speaker_stats && typeof processedResp.speaker_stats === 'object'
        ? processedResp.speaker_stats
        : {}
      const processedKeyTopics = Array.isArray(processedResp?.key_topics)
        ? processedResp.key_topics.filter((topic) => String(topic || '').trim())
        : []

      // 合成本地 summary 结构，尽量兼容模板字段
      localSummary.value = {
        title: newVal.file_name || '会议摘要',
        duration: newVal.duration || null,
        created_at: newVal.transcription_time || newVal.created_at || null,
        speaker_count:
          Object.keys(processedSpeakerStats).length ||
          new Set(processedSegments.map((seg) => seg?.speaker || 'Unknown')).size ||
          (newVal.speaker_count || 0),
        summary_text: (
          (summaryResp.summary && String(summaryResp.summary).trim()) ||
          (summaryResp.summary_text && String(summaryResp.summary_text).trim()) ||
          ''
        ),
        key_topics: processedKeyTopics,
        highlights: [],
        action_items: [],
        speaker_stats: processedSpeakerStats,
        notes: '',
        // 原始分析数据
        _nlp: {
          processed: processedResp,
          summary: summaryResp,
        },
      }

      // 如果 processTranscript 返回 processed segments，尝试构建简单 speaker_stats 和 key_topics
      try {
        const proc = processedResp
        if (proc && proc.segments && !Object.keys(localSummary.value.speaker_stats || {}).length) {
          const stats = {}
          proc.segments.forEach((s) => {
            const sp = s.speaker || 'Unknown'
            stats[sp] = (stats[sp] || 0) + 1
          })
          localSummary.value.speaker_stats = stats
        }
        if (proc && proc.segments && (!localSummary.value.key_topics || !localSummary.value.key_topics.length)) {
          const fallbackTopics = (proc.segments.slice(0, 5) || [])
            .map((s) => s.text?.slice(0, 30) || '')
            .filter((t) => t)
          localSummary.value.key_topics = fallbackTopics
        }
      } catch (e) {
        // ignore
      }

      // 保存摘要到后端
      if (props.meetingId && localSummary.value.summary_text) {
        try {
          await saveSummaryToBackend(localSummary.value)
        } catch (saveErr) {
          console.error('保存摘要失败:', saveErr)
          // 继续显示摘要，即使保存失败
        }
      }

    } catch (err) {
      ElMessage.error('自动分析失败：' + (err.message || err))
    } finally {
      localLoading.value = false
    }
  },
  { immediate: true }
)

const calculatePercentage = (count, stats) => {
  const total = Object.values(stats).reduce((a, b) => a + b, 0)
  return Math.round((count / total) * 100)
}

const getProgressColor = (value, stats) => {
  const percentage = calculatePercentage(value, stats)
  if (percentage > 60) return '#67c23a'
  if (percentage > 30) return '#409eff'
  return '#e6a23c'
}

const exportSummary = () => {
  const s = displayedSummary.value
  if (!s) {
    ElMessage.error('没有可导出的摘要')
    return
  }

  const content = generateSummaryText()
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `meeting-summary-${new Date().getTime()}.txt`
  link.click()
  URL.revokeObjectURL(link.href)
}

const generateSummaryText = () => {
  const s = displayedSummary.value
  let text = ''

  text += `会议摘要\n`
  text += `${'='.repeat(50)}\n\n`

  if (s.title) text += `标题: ${s.title}\n`
  if (s.duration) text += `时长: ${formatDuration(s.duration)}\n`
  if (s.created_at) text += `日期: ${formatDate(s.created_at)}\n`
  if (s.speaker_count) text += `发言人: ${s.speaker_count}位\n\n`

  if (s.summary_text) {
    text += `会议纪要\n${'-'.repeat(30)}\n${s.summary_text}\n\n`
  }

  if (s.key_topics && s.key_topics.length) {
    text += `关键议题\n${'-'.repeat(30)}\n`
    s.key_topics.forEach((t) => (text += `• ${t}\n`))
    text += '\n'
  }

  if (s.action_items && s.action_items.length) {
    text += `行动项\n${'-'.repeat(30)}\n`
    s.action_items.forEach((item) => {
      text += `${item.completed ? '✓' : '○'} ${item.text}`
      if (item.assignee) text += ` (${item.assignee})`
      if (item.due_date) text += ` [${formatDate(item.due_date)}]`
      text += '\n'
    })
    text += '\n'
  }

  if (s.notes) {
    text += `笔记\n${'-'.repeat(30)}\n${s.notes}\n`
  }

  return text
}

const ensureLocalSummary = () => {
  if (localSummary.value) return

  const remote = props.summary || {}
  localSummary.value = {
    ...remote,
    summary_text: remote.summary_text || remote.summary || '',
    title: remote.title || '会议摘要',
    notes: remote.notes || '',
  }
}

const startEditNotes = () => {
  editableNotes.value = displayedSummary.value?.notes || ''
  editingNotes.value = true
}

const cancelEditNotes = () => {
  editableNotes.value = displayedSummary.value?.notes || ''
  editingNotes.value = false
}

const saveNotes = () => {
  ensureLocalSummary()
  localSummary.value.notes = editableNotes.value || ''
  emit('update-notes', localSummary.value.notes)
  editingNotes.value = false
  ElMessage.success('笔记已保存')
}

const refreshSummary = () => {
  emit('refresh')
}

const updateActionItem = (item) => {
  emit('update-action-item', item)
}

/**
 * 保存摘要到后端
 */
const saveSummaryToBackend = async (summary) => {
  if (!props.meetingId) {
    console.log('未提供 meetingId，跳过摘要保存')
    return
  }

  try {
    const updateData = {
      summary: summary.summary_text || summary.summary || '',
      key_topics: JSON.stringify(summary.key_topics || []),
      summary_type: 'abstractive',
    }

    await meetingAPI.updateMeeting(props.meetingId, updateData)
    console.log('摘要已保存到后端')
  } catch (err) {
    console.error('保存摘要到后端失败:', err)
    throw err
  }
}
</script>

<style scoped lang="scss">
.summary-display {
  background: white;
  border-radius: 8px;
  padding: 24px;

  .summary-header {
    margin-bottom: 24px;
    border-bottom: 2px solid #f0f0f0;
    padding-bottom: 16px;

    h3 {
      margin: 0 0 12px;
      font-size: 24px;
      color: #303133;
    }

    .summary-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
  }

  .summary-section {
    margin-bottom: 24px;

    h4 {
      margin: 0 0 12px;
      font-size: 16px;
      color: #303133;
      font-weight: 600;
    }
  }

  .summary-text {
    background-color: #f5f7fa;
    padding: 16px;
    border-radius: 4px;
    line-height: 1.6;
    color: #606266;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .topics-list {
    list-style: none;
    padding: 0;
    margin: 0;

    li {
      padding: 8px 12px;
      background-color: #f5f7fa;
      border-left: 3px solid #409eff;
      margin-bottom: 8px;
      border-radius: 0 4px 4px 0;
    }
  }

  .highlights-list {
    display: grid;
    gap: 8px;

    .highlight-item {
      padding: 12px;
      background-color: #fdf6ec;
      border-left: 3px solid #e6a23c;
      border-radius: 0 4px 4px 0;
      display: flex;
      align-items: flex-start;
      gap: 8px;

      .highlight-mark {
        color: #e6a23c;
        font-weight: bold;
      }
    }
  }

  .action-items-list {
    display: grid;
    gap: 12px;

    .action-item {
      padding: 12px;
      background-color: #f0f9ff;
      border-left: 3px solid #67c23a;
      border-radius: 0 4px 4px 0;
      display: flex;
      flex-direction: column;
      gap: 4px;

      :deep(.el-checkbox) {
        margin-bottom: 4px;
      }

      .assignee,
      .due-date {
        font-size: 12px;
        color: #909399;
        margin-left: 20px;
      }
    }
  }

  .speaker-stats {
    display: grid;
    gap: 16px;

    .speaker-stat {
      .speaker-name {
        margin-bottom: 8px;
        font-weight: 500;
        color: #303133;
      }
    }
  }

  .summary-actions {
    display: flex;
    gap: 12px;
    margin: 24px 0;
    padding: 16px 0;
    border-top: 1px solid #f0f0f0;
    border-bottom: 1px solid #f0f0f0;
  }

  .notes-display {
    background-color: #f5f7fa;
    padding: 16px;
    border-radius: 4px;
    line-height: 1.6;
    color: #606266;

    p {
      margin: 0;
    }
  }

  .notes-edit {
    width: 100%;
  }
}
</style>
