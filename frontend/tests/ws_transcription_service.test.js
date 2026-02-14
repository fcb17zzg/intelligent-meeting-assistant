import assert from 'assert'
import WsTranscriptionService from '../src/services/wsTranscriptionService.js'

// 该测试不实例化类（避免在 Node 环境访问浏览器全局），仅检查导出和原型方法存在
assert.ok(WsTranscriptionService, 'WsTranscriptionService 应导出为默认类/函数')

const proto = WsTranscriptionService.prototype
const methods = ['start', 'sendChunk', 'sendChunkBase64', 'end', 'dispose']
for (const m of methods) {
  assert.strictEqual(typeof proto[m], 'function', `方法 ${m} 应存在于原型上`)
}

console.log('✅ WsTranscriptionService 导出检测通过')
