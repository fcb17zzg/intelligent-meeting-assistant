/**
 * 可视化服务
 * 提供图表和报告生成的API
 */
import client from '../api/client'

export const visualizationService = {
  /**
   * 生成说话人分布饼图
   * @param {Object} insights - 会议洞见数据
   * @param {string} outputFormat - 输出格式
   * @returns {Promise}
   */
  async generateSpeakerDistribution(insights, outputFormat = 'html') {
    return client.post('/visualization/speaker-distribution', {
      insights,
      output_format: outputFormat,
    })
  },

  /**
   * 生成行动项优先级柱状图
   * @param {Object} insights - 会议洞见数据
   * @param {string} outputFormat - 输出格式
   * @returns {Promise}
   */
  async generateActionItemsChart(insights, outputFormat = 'html') {
    return client.post('/visualization/action-items-bar', {
      insights,
      output_format: outputFormat,
    })
  },

  /**
   * 生成会议时间轴
   * @param {Object} insights - 会议洞见数据
   * @param {string} outputFormat - 输出格式
   * @returns {Promise}
   */
  async generateTimeline(insights, outputFormat = 'html') {
    return client.post('/visualization/timeline', {
      insights,
      output_format: outputFormat,
    })
  },

  /**
   * 生成主题气泡图
   * @param {Object} insights - 会议洞见数据
   * @param {string} outputFormat - 输出格式
   * @returns {Promise}
   */
  async generateTopicsBubbleChart(insights, outputFormat = 'html') {
    return client.post('/visualization/topics-bubble', {
      insights,
      output_format: outputFormat,
    })
  },

  /**
   * 生成完整仪表盘
   * @param {Object} insights - 会议洞见数据
   * @param {number} meetingId - 会议ID
   * @param {string} outputFormat - 输出格式
   * @returns {Promise}
   */
  async generateDashboard(insights, meetingId, outputFormat = 'html') {
    return client.post('/visualization/dashboard', {
      insights,
      meeting_id: meetingId,
      output_format: outputFormat,
    })
  },

  /**
   * 生成会议报告
   * @param {Object} meetingData - 会议数据
   * @param {Object} insights - 会议洞见
   * @param {string} reportFormat - 报告格式
   * @param {string} title - 报告标题
   * @returns {Promise}
   */
  async generateReport(meetingData, insights, reportFormat = 'html', title = '会议报告') {
    return client.post('/visualization/generate-report', {
      meeting_data: meetingData,
      insights,
      report_format: reportFormat,
      title,
    })
  },

  /**
   * 获取报告
   * @param {string} reportId - 报告ID
   * @returns {Promise}
   */
  async getReport(reportId) {
    return client.get(`/visualization/reports/${reportId}`)
  },

  /**
   * 导出可视化数据
   * @param {string} chartType - 图表类型
   * @param {Object} insights - 洞见数据
   * @param {string} exportFormat - 导出格式
   * @returns {Promise}
   */
  async exportVisualization(chartType, insights, exportFormat = 'json') {
    return client.post('/visualization/export', {
      chart_type: chartType,
      insights,
      export_format: exportFormat,
    })
  },

  /**
   * 生成所有图表
   * @param {Object} insights - 会议洞见数据
   * @param {number} meetingId - 会议ID
   * @returns {Promise}
   */
  async generateAllCharts(insights, meetingId) {
    try {
      const results = await Promise.all([
        this.generateSpeakerDistribution(insights),
        this.generateActionItemsChart(insights),
        this.generateTimeline(insights),
        this.generateTopicsBubbleChart(insights),
        this.generateDashboard(insights, meetingId),
        this.generateReport({}, insights),
      ])

      return {
        status: 'success',
        charts: {
          speakerDistribution: results[0],
          actionItems: results[1],
          timeline: results[2],
          topicsBubble: results[3],
          dashboard: results[4],
          report: results[5],
        },
      }
    } catch (error) {
      throw error
    }
  },
}

export default visualizationService
