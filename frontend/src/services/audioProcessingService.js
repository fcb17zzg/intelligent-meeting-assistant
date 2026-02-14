/**
 * 音频处理服务
 * 提供音频上传、转录和处理的API
 */
import client from '../api/client'

export const audioProcessingService = {
  /**
   * 上传音频文件
   * @param {File} file - 音频文件
   * @param {string} language - 语言代码
   * @param {boolean} speakerDiarization - 是否进行说话人分离
   * @returns {Promise}
   */
  async uploadAudio(file, language = 'auto', speakerDiarization = true) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('language', language)
    formData.append('speaker_diarization', speakerDiarization)

    return client.post('/audio/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  /**
   * 转录音频文件
   * @param {string} fileId - 文件ID
   * @param {string} language - 语言代码
   * @param {boolean} speakerDiarization - 是否进行说话人分离
   * @param {string} context - 上下文提示
   * @returns {Promise}
   */
  async transcribeAudio(fileId, language = 'auto', speakerDiarization = true, context = null) {
    return client.post('/audio/transcribe', {
      file_id: fileId,
      language,
      speaker_diarization: speakerDiarization,
      context,
    })
  },

  /**
   * 获取转录结果
   * @param {string} transcriptionId - 转录ID
   * @returns {Promise}
   */
  async getTranscription(transcriptionId) {
    return client.get(`/audio/transcription/${transcriptionId}`)
  },

  /**
   * 预处理音频
   * @param {string} fileId - 文件ID
   * @param {boolean} normalize - 是否进行音量标准化
   * @param {boolean} denoise - 是否降噪
   * @param {number} sampleRate - 目标采样率
   * @returns {Promise}
   */
  async preprocessAudio(fileId, normalize = true, denoise = true, sampleRate = 16000) {
    return client.post('/audio/preprocess', {
      file_id: fileId,
      normalize,
      denoise,
      sample_rate: sampleRate,
    })
  },

  /**
   * 获取音频信息
   * @param {string} fileId - 文件ID
   * @returns {Promise}
   */
  async getAudioInfo(fileId) {
    return client.get(`/audio/info/${fileId}`)
  },
}

export default audioProcessingService
