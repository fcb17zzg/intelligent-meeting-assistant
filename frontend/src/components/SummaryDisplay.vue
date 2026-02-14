<template>
  <div class="summary-display">
    <!-- 加载状态 -->
    <el-skeleton v-if="loading" :rows="5" animated />

    <!-- 摘要内容 -->
    <div v-else-if="summary" class="summary-content">
      <!-- 会议信息 -->
      <div class="summary-header">
        <h3>{{ summary.title || '会议摘要' }}</h3>
        <div class="summary-meta">
          <el-tag v-if="summary.duration" type="info">
            ⏱️ {{ formatDuration(summary.duration) }}
          </el-tag>
          <el-tag v-if="summary.created_at" type="warning">
            📅 {{ formatDate(summary.created_at) }}
          </el-tag>
          <el-tag v-if="summary.speaker_count">
            👥 {{ summary.speaker_count }} 位发言人
          </el-tag>
        </div>
      </div>

      <!-- 主要内容摘要 -->
      <div v-if="summary.summary_text" class="summary-section">
        <h4>📝 会议纪要</h4>
        <div class="summary-text">
          {{ summary.summary_text }}
        </div>
      </div>

      <!-- 关键议题 -->
      <div v-if="summary.key_topics && summary.key_topics.length" class="summary-section">
        <h4>🎯 关键议题</h4>
        <ul class="topics-list">
          <li v-for="(topic, index) in summary.key_topics" :key="index">
            {{ topic }}
          </li>
        </ul>
      </div>

      <!-- 重点突出 -->
      <div
        v-if="summary.highlights && summary.highlights.length"
        class="summary-section"
      >
        <h4>⭐ 重点突出</h4>
        <div class="highlights-list">
          <div v-for="(highlight, index) in summary.highlights" :key="index" class="highlight-item">
            <span class="highlight-mark">•</span>
            {{ highlight }}
          </div>
        </div>
      </div>

      <!-- 行动项 -->
      <div
        v-if="summary.action_items && summary.action_items.length"
        class="summary-section"
      >
        <h4>✅ 行动项</h4>
        <div class="action-items-list">
          <div v-for="(item, index) in summary.action_items" :key="index" class="action-item">
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
        v-if="summary.speaker_stats && Object.keys(summary.speaker_stats).length"
        class="summary-section"
      >
        <h4>🎤 发言人统计</h4>
        <div class="speaker-stats">
          <div
            v-for="(count, speaker) in summary.speaker_stats"
            :key="speaker"
            class="speaker-stat"
          >
            <div class="speaker-name">{{ speaker }}</div>
            <el-progress
              :percentage="calculatePercentage(count, summary.speaker_stats)"
              :color="getProgressColor(count, summary.speaker_stats)"
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
        <el-button v-if="!editingNotes" @click="editingNotes = true">
          ✏️ 编辑笔记
        </el-button>
      </div>

      <!-- 额外笔记 -->
      <div class="summary-section">
        <h4>📌 笔记</h4>
        <div v-if="!editingNotes" class="notes-display">
          <p v-if="summary.notes">{{ summary.notes }}</p>
          <p v-else style="color: #909399">暂无笔记</p>
        </div>
        <div v-else class="notes-edit">
          <el-input
            v-model="summary.notes"
            type="textarea"
            rows="4"
            placeholder="添加笔记..."
          />
          <div style="margin-top: 12px; display: flex; gap: 8px">
            <el-button type="primary" @click="saveNotes">保存</el-button>
            <el-button @click="editingNotes = false">取消</el-button>
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
})

const emit = defineEmits(['update-notes', 'refresh'])

const editingNotes = ref(false)
const localLoading = ref(false)
const localSummary = ref(null)

const displayedSummary = computed(() => props.summary || localSummary.value)

// 当收到转录数据时自动触发 NLP 分析和摘要生成
watch(
  () => props.transcription,
  async (newVal) => {
    if (!newVal) return
    try {
      localLoading.value = true

      const segments = newVal.segments || []
      const fullText = newVal.text || segments.map((s) => s.text || '').join(' ')

      // 并行请求：处理转录（实体/关键词/句子级分析）与摘要
      const [processedResp, summaryResp] = await Promise.all([
        nlpAnalysisService.processTranscript(segments, newVal.language || 'zh'),
        nlpAnalysisService.generateSummary(fullText, 'medium', newVal.language || 'zh'),
      ])

      // 合成本地 summary 结构，尽量兼容模板字段
      localSummary.value = {
        title: newVal.file_name || '会议摘要',
        duration: newVal.duration || null,
        created_at: newVal.transcription_time || newVal.created_at || null,
        speaker_count: processedResp.segments ? processedResp.segments.length : (newVal.speaker_count || 0),
        summary_text: summaryResp.summary || summaryResp.summary_text || '',
        key_topics: processedResp.segments ? [] : [],
        highlights: [],
        action_items: [],
        speaker_stats: {},
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
        if (proc && proc.segments) {
          const stats = {}
          proc.segments.forEach((s) => {
            const sp = s.speaker || 'Unknown'
            stats[sp] = (stats[sp] || 0) + 1
          })
          localSummary.value.speaker_stats = stats
        }
        if (proc && proc.segments) {
          // 从 processed segments 中提取简单 key topics（占位）
          localSummary.value.key_topics = (proc.segments.slice(0, 5) || []).map((s) => s.text?.slice(0, 30) || '')
        }
      } catch (e) {
        // ignore
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

const saveNotes = () => {
  emit('update-notes', props.summary.notes)
  editingNotes.value = false
  ElMessage.success('笔记已保存')
}

const refreshSummary = () => {
  emit('refresh')
}

const updateActionItem = (item) => {
  emit('update-action-item', item)
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
