/**
 * 综合会议处理服务
 * 整合音频处理、NLP分析和可视化
 */
import audioProcessingService from './audioProcessingService'
import nlpAnalysisService from './nlpAnalysisService'
import visualizationService from './visualizationService'

export const meetingProcessingService = {
  /**
   * 处理完整的会议流程
   * 1. 上传音频
   * 2. 转录音频
   * 3. 分析NLP
   * 4. 生成可视化
   * 
   * @param {File} audioFile - 音频文件
   * @param {Object} options - 处理选项
   * @returns {Promise}
   */
  async processMeeting(audioFile, options = {}) {
    const {
      language = 'auto',
      enableDiarization = true,
      enableNLPAnalysis = true,
      enableVisualization = true,
      meetingId = null,
    } = options

    try {
      // 步骤1: 上传音频
      console.log('步骤1: 上传音频文件...')
      const uploadResult = await audioProcessingService.uploadAudio(
        audioFile,
        language,
        enableDiarization
      )

      if (uploadResult.status !== 'uploaded') {
        throw new Error('音频上传失败')
      }

      const fileId = uploadResult.file_id

      // 步骤2: 转录音频
      console.log('步骤2: 转录音频...')
      const transcriptionResult = await audioProcessingService.transcribeAudio(
        fileId,
        language,
        enableDiarization
      )

      if (transcriptionResult.status !== 'completed') {
        throw new Error('音频转录失败')
      }

      const segments = transcriptionResult.segments || []
      const transcriptionText = transcriptionResult.text || ''

      let nlpResults = null
      if (enableNLPAnalysis) {
        // 步骤3: 进行NLP分析
        console.log('步骤3: 进行NLP分析...')

        // 并行执行多个NLP分析
        const [
          entitiesResult,
          keywordsResult,
          sentimentResult,
          topicsResult,
          transcriptProcessingResult,
        ] = await Promise.all([
          nlpAnalysisService.extractEntities(transcriptionText, language),
          nlpAnalysisService.extractKeywords(transcriptionText, 10, language),
          nlpAnalysisService.analyzeSentiment([transcriptionText], language),
          nlpAnalysisService.analyzeTopics([transcriptionText], language, 5),
          nlpAnalysisService.processTranscript(segments, language),
        ])

        nlpResults = {
          entities: entitiesResult.entities || [],
          keywords: keywordsResult.keywords || [],
          sentiment: sentimentResult.sentiments ? sentimentResult.sentiments[0] : null,
          topics: topicsResult.topics || [],
          processedSegments: transcriptProcessingResult.segments || [],
        }
      }

      const insights = {
        entities: nlpResults?.entities || [],
        keywords: nlpResults?.keywords || [],
        sentiment: nlpResults?.sentiment || null,
        topics: nlpResults?.topics || [],
        processedSegments: nlpResults?.processedSegments || segments,
      }

      let visualizationResults = null
      if (enableVisualization) {
        // 步骤4: 生成可视化
        console.log('步骤4: 生成可视化...')

        visualizationResults = await visualizationService.generateAllCharts(
          insights,
          meetingId || 0
        )
      }

      return {
        status: 'success',
        fileId,
        transcription: {
          text: transcriptionText,
          segments,
          language,
        },
        nlpAnalysis: nlpResults,
        visualization: visualizationResults,
        insights,
      }
    } catch (error) {
      console.error('会议处理失败:', error)
      return {
        status: 'error',
        error: error.message || '未知错误',
      }
    }
  },

  /**
   * 批量处理多个会议
   * @param {Array<File>} audioFiles - 音频文件数组
   * @param {Object} options - 处理选项
   * @returns {Promise}
   */
  async processMeetingBatch(audioFiles, options = {}) {
    const results = []

    for (let i = 0; i < audioFiles.length; i++) {
      const file = audioFiles[i]
      console.log(`处理会议 ${i + 1}/${audioFiles.length}: ${file.name}`)

      try {
        const result = await this.processMeeting(file, options)
        results.push({
          fileName: file.name,
          ...result,
        })
      } catch (error) {
        results.push({
          fileName: file.name,
          status: 'error',
          error: error.message,
        })
      }
    }

    return {
      status: 'completed',
      total: audioFiles.length,
      successful: results.filter((r) => r.status === 'success').length,
      failed: results.filter((r) => r.status === 'error').length,
      results,
    }
  },

  /**
   * 从现有的转录生成洞见和可视化
   * @param {Array<Object>} segments - 转录分段
   * @param {Object} options - 处理选项
   * @returns {Promise}
   */
  async generateInsightsFromTranscript(segments, options = {}) {
    const { language = 'zh', meetingId = null } = options

    try {
      console.log('从转录生成洞见...')

      const fullText = segments
        .map((s) => (s.text ? s.text : ''))
        .join(' ')

      // 并行执行NLP分析
      const [
        entitiesResult,
        keywordsResult,
        sentimentResult,
        topicsResult,
        transcriptProcessingResult,
      ] = await Promise.all([
        nlpAnalysisService.extractEntities(fullText, language),
        nlpAnalysisService.extractKeywords(fullText, 10, language),
        nlpAnalysisService.analyzeSentiment([fullText], language),
        nlpAnalysisService.analyzeTopics([fullText], language, 5),
        nlpAnalysisService.processTranscript(segments, language),
      ])

      const insights = {
        entities: entitiesResult.entities || [],
        keywords: keywordsResult.keywords || [],
        sentiment: sentimentResult.sentiments ? sentimentResult.sentiments[0] : null,
        topics: topicsResult.topics || [],
        processedSegments: transcriptProcessingResult.segments || segments,
      }

      // 生成可视化
      const visualizationResults = await visualizationService.generateAllCharts(
        insights,
        meetingId || 0
      )

      return {
        status: 'success',
        insights,
        visualization: visualizationResults,
      }
    } catch (error) {
      console.error('生成洞见失败:', error)
      return {
        status: 'error',
        error: error.message,
      }
    }
  },

  /**
   * 预处理音频
   * @param {string} fileId - 文件ID
   * @param {Object} options - 预处理选项
   * @returns {Promise}
   */
  async preprocessAudio(fileId, options = {}) {
    const { normalize = true, denoise = true, sampleRate = 16000 } = options

    try {
      return await audioProcessingService.preprocessAudio(
        fileId,
        normalize,
        denoise,
        sampleRate
      )
    } catch (error) {
      console.error('音频预处理失败:', error)
      throw error
    }
  },
}

export default meetingProcessingService
