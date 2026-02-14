/**
 * WebSocket 实时转录服务（前端示例）
 *
 * 用法示例:
 * const svc = new WsTranscriptionService({url: 'ws://localhost:8000/api/ws/transcribe'});
 * svc.onMessage = (msg) => console.log(msg);
 * await svc.start('auto');
 * // 每当有音频 chunk (ArrayBuffer) 时调用 svc.sendChunk(chunk)
 * await svc.end();
 */

export default class WsTranscriptionService {
  constructor({ url } = {}) {
    this.url = url || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:8000/api/ws/transcribe`;
    this.socket = null;
    this.onMessage = null; // 回调: 接收服务器消息
    this.onOpen = null;
    this.onClose = null;
  }

  async start(language = 'auto') {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) return;

    this.socket = new WebSocket(this.url);
    this.socket.binaryType = 'arraybuffer';

    this.socket.onopen = () => {
      if (this.onOpen) this.onOpen();
      // 发送开始控制信息
      this.socket.send(`start:${language}`);
    };

    this.socket.onmessage = (evt) => {
      if (this.onMessage) this.onMessage(evt.data);
    };

    this.socket.onclose = (evt) => {
      if (this.onClose) this.onClose(evt);
    };

    this.socket.onerror = (err) => {
      console.error('WebSocket error', err);
    };

    // 等待连接打开
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('ws connect timeout')), 8000);
      this.socket.addEventListener('open', () => {
        clearTimeout(timer);
        resolve();
      });
    });
  }

  // 发送 ArrayBuffer 或 Uint8Array
  sendChunk(buffer) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket 未连接');
    }

    // 直接发送二进制帧
    this.socket.send(buffer);
  }

  // 如果需要用 base64 文本发送
  sendChunkBase64(b64) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket 未连接');
    }
    this.socket.send(`audio_base64:${b64}`);
  }

  // 结束并请求转录
  async end() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send('end:');

    // 等待服务器主动关闭连接或在若干秒后手动关闭
    await new Promise((resolve) => {
      const handler = () => {
        this.socket.removeEventListener('close', handler);
        resolve();
      };
      this.socket.addEventListener('close', handler);
      setTimeout(() => {
        try { this.socket.close(); } catch (e) {}
        resolve();
      }, 20000);
    });
  }

  dispose() {
    try { this.socket && this.socket.close(); } catch (e) {}
    this.socket = null;
  }
}
