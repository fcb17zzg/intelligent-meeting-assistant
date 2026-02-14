/**
 * NLP分析服务
 * 提供自然语言处理的API
 */
import client from '../api/client'

export const nlpAnalysisService = {
  /**
   * 提取命名实体
   * @param {string} text - 输入文本
   * @param {string} language - 语言代码
   * @param {Array<string>} entityTypes - 实体类型列表
   * @returns {Promise}
   */
  async extractEntities(text, language = 'zh', entityTypes = null) {
    return client.post('/nlp/extract-entities', {
      text,
      language,
      entity_types: entityTypes,
    })
  },

  /**
   * 提取关键词
   * @param {string} text - 输入文本
   * @param {number} topK - 返回的关键词数量
   * @param {string} language - 语言代码
   * @param {string} method - 提取方法
   * @returns {Promise}
   */
  async extractKeywords(text, topK = 10, language = 'zh', method = 'keybert') {
    return client.post('/nlp/extract-keywords', {
      text,
      top_k: topK,
      language,
      method,
    })
  },

  /**
   * 分析情感
   * @param {Array<string>} texts - 文本列表
   * @param {string} language - 语言代码
   * @returns {Promise}
   */
  async analyzeSentiment(texts, language = 'zh') {
    return client.post('/nlp/analyze-sentiment', {
      texts,
      language,
    })
  },

  /**
   * 进行主题分析
   * @param {Array<string>} documents - 文档列表
   * @param {string} language - 语言代码
   * @param {number} numTopics - 主题数量
   * @returns {Promise}
   */
  async analyzeTopics(documents, language = 'zh', numTopics = 5) {
    return client.post('/nlp/analyze-topics', {
      documents,
      language,
      num_topics: numTopics,
    })
  },

  /**
   * 文本摘要生成
   * @param {string} text - 输入文本
   * @param {string} summaryLength - 摘要长度
   * @param {string} language - 语言代码
   * @returns {Promise}
   */
  async generateSummary(text, summaryLength = 'medium', language = 'zh') {
    return client.post('/nlp/text-summarization', {
      text,
      summary_length: summaryLength,
      language,
    })
  },

  /**
   * 处理会议转录稿
   * @param {Array<Object>} segments - 转录分段列表
   * @param {string} language - 语言代码
   * @param {boolean} extractEntities - 是否提取实体
   * @param {boolean} extractKeywords - 是否提取关键词
   * @param {boolean} analyzeSentiment - 是否分析情感
   * @returns {Promise}
   */
  async processTranscript(
    segments,
    language = 'zh',
    extractEntities = true,
    extractKeywords = true,
    analyzeSentiment = true
  ) {
    return client.post('/nlp/process-transcript', {
      segments,
      language,
      extract_entities: extractEntities,
      extract_keywords: extractKeywords,
      analyze_sentiment: analyzeSentiment,
    })
  },
}

export default nlpAnalysisService
