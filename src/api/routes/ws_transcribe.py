"""
WebSocket 实时转录路由
客户端可以通过 WebSocket 发送音频二进制数据（或 base64 文本），服务器在收到结束信号后返回最终转录结果。
如果本地音频处理模块可用，将使用 WhisperClient 转录；否则返回模拟结果。
"""
import os
import uuid
import base64
import logging
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# 临时上传目录，复用已有的 uploads 目录
UPLOAD_DIR = Path("./cache/audio/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    temp_filename = UPLOAD_DIR / f"ws_{session_id}.wav"
    f = open(temp_filename, "wb")
    logger.info(f"WebSocket 连接已建立: {session_id}")

    try:
        # 会话状态
        language = None
        while True:
            data = await websocket.receive()

            # 文本消息或二进制
            if "text" in data and data["text"] is not None:
                try:
                    msg = data["text"]
                except Exception:
                    msg = None
                if not msg:
                    continue

                # 简单的控制协议：json-like 前缀
                # start:{"language":"zh"}
                if msg.startswith("start:"):
                    try:
                        payload = msg[len("start:"):]
                        # 期望 payload 为语言标签，例如 "zh" 或 "auto"
                        language = payload.strip() or None
                        await websocket.send_text("status:recording")
                        logger.info(f"开始录制会话 {session_id}, language={language}")
                    except Exception:
                        await websocket.send_text("error:invalid_start")

                # audio 数据采用 base64 文本形式
                elif msg.startswith("audio_base64:"):
                    b64 = msg[len("audio_base64:"):]
                    try:
                        chunk = base64.b64decode(b64)
                        f.write(chunk)
                        # 可选择发送中间结果（模拟）
                        await websocket.send_text("partial:ok")
                    except Exception as e:
                        logger.warning(f"写入音频块失败: {e}")
                        await websocket.send_text("error:chunk_write_failed")

                # 结束录制并触发转录
                elif msg.startswith("end:"):
                    await websocket.send_text("status:processing")
                    f.flush()
                    f.close()

                    # 尝试使用本地音频处理模块
                    try:
                        from src.audio_processing.core.whisper_client import WhisperClient
                        from src.audio_processing.config.settings import settings

                        client = WhisperClient(
                            model_name=settings.whisper_model,
                            device=settings.whisper_device,
                            compute_type=settings.compute_type,
                        )
                        # 调用同步转录方法
                        result = client.transcribe(
                            audio_path=str(temp_filename),
                            language=language if language and language != "auto" else None,
                            detect_language=(language == "auto")
                        )

                        text = str(result) if result else ""
                        await websocket.send_text(f"final:{text}")
                        logger.info(f"会话 {session_id} 转录完成")
                    except Exception as e:
                        logger.warning(f"本地转录不可用或失败: {e}")
                        # 返回模拟结果
                        await websocket.send_text("final:这是模拟的实时转录结果（服务器未配置转录模型）")

                    # 关闭连接后删除临时文件
                    try:
                        os.remove(temp_filename)
                    except Exception:
                        pass

                    await websocket.close()
                    break

                else:
                    await websocket.send_text("error:unknown_command")

            elif "bytes" in data and data["bytes"] is not None:
                # 直接收到二进制数据（WebSocket binary frames）
                try:
                    chunk = data["bytes"]
                    f.write(chunk)
                    await websocket.send_text("partial:ok")
                except Exception as e:
                    logger.warning(f"写入二进制块失败: {e}")
                    await websocket.send_text("error:chunk_write_failed")

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: {session_id}")
        try:
            f.close()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket 会话错误: {e}")
        try:
            f.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
