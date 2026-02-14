import io
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.transcribe import router


@pytest.fixture
def app():
    """Create a minimal FastAPI app with just the transcribe router for testing."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_transcribe_sync_monkeypatch(client, monkeypatch):
    # 模拟转录函数，避免依赖模型或外部环境
    fake_whisper_result = {"text": "这是假的转录", "segments": []}

    def fake_whisper(path, language="auto"):
        return fake_whisper_result

    # monkeypatch Whisper 函数而非增强转录函数
    import src.api.transcribe as trans_mod
    monkeypatch.setattr(trans_mod, "_run_whisper_transcription", fake_whisper)

    # 构造模拟音频文件（内容不重要，因为已被 monkeypatch）
    file_content = io.BytesIO(b"RIFF....FAKEAUDIO")
    files = {"file": ("test.wav", file_content, "audio/wav")}
    response = client.post("/api/meetings/test_meeting/transcribe", files=files, params={"mode": "sync"})

    assert response.status_code == 200
    data = response.json()
    assert data["meeting_id"] == "test_meeting"
    assert "result" in data
    # 新格式包含 original_text、segments、speakers 和 metadata
    assert data["result"]["original_text"] == "这是假的转录"
    assert "segments" in data["result"]
    assert "speakers" in data["result"]
    assert "metadata" in data["result"]
