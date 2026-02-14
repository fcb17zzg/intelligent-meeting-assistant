<template>
  <div class="recorder">
    <h3>实时录音并上传（WebSocket 实例）</h3>
    <div>
      <button @click="toggleRecording">{{ recording ? '停止录音' : '开始录音' }}</button>
      <label style="margin-left:12px"><input type="checkbox" v-model="useBase64" /> 使用 Base64 发送</label>
    </div>
    <div style="margin-top:10px">
      <label>语言: </label>
      <select v-model="language">
        <option value="auto">自动检测</option>
        <option value="zh">中文</option>
        <option value="en">英语</option>
      </select>
    </div>
    <div style="margin-top:8px">
      <strong>状态：</strong> {{ statusMessage }}
    </div>
    <div v-if="messages.length" style="margin-top:8px">
      <strong>消息：</strong>
      <ul>
        <li v-for="(m, idx) in messages" :key="idx">{{ m }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import WsTranscriptionService from '../services/wsTranscriptionService'

const recording = ref(false)
const statusMessage = ref('空闲')
const messages = ref([])
const language = ref('auto')
const useBase64 = ref(false)

let mediaRecorder = null
let svc = null

function pushMsg(m) {
  messages.value.unshift(`${new Date().toLocaleTimeString()} - ${m}`)
  if (messages.value.length > 20) messages.value.pop()
}

async function startRecording() {
  try {
    svc = new WsTranscriptionService({})
    svc.onMessage = (msg) => {
      pushMsg(`WS → ${msg}`)
      if (String(msg).startsWith('status:processing')) statusMessage.value = '处理中'
      if (String(msg).startsWith('final:')) statusMessage.value = '已完成'
    }
    svc.onOpen = () => { pushMsg('WS 已连接') }
    svc.onClose = () => { pushMsg('WS 已关闭') }

    statusMessage.value = '连接 WS...' 
    await svc.start(language.value)

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    // 使用默认 mime，MediaRecorder 会分片触发 dataavailable
    mediaRecorder = new MediaRecorder(stream)

    mediaRecorder.addEventListener('dataavailable', async (e) => {
      if (!e.data || e.data.size === 0) return
      try {
        const arr = await e.data.arrayBuffer()
        if (useBase64.value) {
          // base64 发送
          const uint8 = new Uint8Array(arr)
          const b64 = btoa(String.fromCharCode(...uint8))
          svc.sendChunkBase64(b64)
          pushMsg('发送 chunk（base64）')
        } else {
          svc.sendChunk(arr)
          pushMsg('发送 chunk（二进制）')
        }
      } catch (err) {
        console.error('chunk 发送失败', err)
        pushMsg('chunk 发送失败')
      }
    })

    // 每秒产生一段数据（若浏览器支持 timeslice）
    mediaRecorder.start(1000)
    statusMessage.value = '录音中...'
    recording.value = true
  } catch (e) {
    console.error(e)
    statusMessage.value = `启动失败: ${e.message || e}`
  }
}

async function stopRecording() {
  try {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
    // 触发 end，等待服务器返回最终结果
    if (svc) {
      statusMessage.value = '请求转录...'
      await svc.end()
      pushMsg('已请求转录')
      svc.dispose()
      svc = null
    }
    recording.value = false
    statusMessage.value = '空闲'
  } catch (e) {
    console.error(e)
    statusMessage.value = `停止失败: ${e.message || e}`
  }
}

function toggleRecording() {
  if (!recording.value) startRecording()
  else stopRecording()
}
</script>

<style scoped>
.recorder { border: 1px solid #ddd; padding: 12px; border-radius:6px; max-width:480px }
button { padding:6px 12px }
ul { margin:6px 0 0 18px }
</style>
