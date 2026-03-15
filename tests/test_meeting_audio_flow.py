from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app import app


def _create_meeting(client: TestClient, suffix: str) -> int:
    now = datetime.utcnow()
    payload = {
        "title": f"音频流程测试会议-{suffix}",
        "description": "用于验证会议音频处理主链路",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(minutes=45)).isoformat(),
        "duration": 45,
        "participants": 4,
        "location": "测试会议室",
    }
    response = client.post("/api/meetings", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_upload_audio_persists_meeting_audio_path(monkeypatch, tmp_path):
    monkeypatch.setattr("src.api.routes.meetings.AUDIO_UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("src.api.routes.meetings._get_audio_duration", lambda _: 18.5)

    with TestClient(app) as client:
        meeting_id = _create_meeting(client, "upload")

        response = client.post(
            f"/api/meetings/{meeting_id}/upload-audio",
            files={"file": ("sample.wav", b"fake wav data", "audio/wav")},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ready_to_transcribe"
        assert Path(data["audio_path"]).exists()
        assert data["duration"] == 18.5

        detail_response = client.get(f"/api/meetings/{meeting_id}")
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.json()["audio_path"] == data["audio_path"]


def test_transcribe_meeting_persists_transcript_and_segments(monkeypatch, tmp_path):
    monkeypatch.setattr("src.api.routes.meetings.AUDIO_UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("src.api.routes.meetings._get_audio_duration", lambda _: 32.0)

    fake_transcription = {
        "text": "今天讨论项目进度和下周交付安排。",
        "language": "zh",
        "processing_time": 1.2,
        "duration": 32.0,
        "segments": [
            {
                "speaker": "SPEAKER_00",
                "text": "今天讨论项目进度。",
                "start_time": 0.0,
                "end_time": 12.0,
                "confidence": 0.91,
            },
            {
                "speaker": "SPEAKER_01",
                "text": "下周交付安排需要确认。",
                "start_time": 12.0,
                "end_time": 24.0,
                "confidence": 0.88,
            },
        ],
    }
    monkeypatch.setattr("src.api.routes.meetings._transcribe_audio_for_meeting", lambda *args, **kwargs: fake_transcription)

    with TestClient(app) as client:
        meeting_id = _create_meeting(client, "transcribe")

        upload_response = client.post(
            f"/api/meetings/{meeting_id}/upload-audio",
            files={"file": ("meeting.wav", b"fake wav data", "audio/wav")},
        )
        assert upload_response.status_code == 200, upload_response.text

        transcribe_response = client.post(f"/api/meetings/{meeting_id}/transcribe")
        assert transcribe_response.status_code == 200, transcribe_response.text
        transcribe_data = transcribe_response.json()
        assert transcribe_data["status"] == "completed"
        assert transcribe_data["meeting_status"] == "completed"
        assert transcribe_data["segments_count"] == 2

        transcript_response = client.get(f"/api/meetings/{meeting_id}/transcript")
        assert transcript_response.status_code == 200, transcript_response.text
        transcript_data = transcript_response.json()
        assert transcript_data["transcript_raw"] == fake_transcription["text"]
        assert transcript_data["segments_count"] == 2
        assert transcript_data["segments"][0]["speaker"] == "SPEAKER_00"


def test_get_summary_generates_and_persists_summary(monkeypatch):
    monkeypatch.setattr("src.api.routes.meetings._build_llm_config", lambda: None)

    with TestClient(app) as client:
        meeting_id = _create_meeting(client, "summary")

        update_response = client.put(
            f"/api/meetings/{meeting_id}",
            json={
                "transcript_raw": "今天讨论项目进度。李明负责整理需求文档。下周五前完成接口联调。",
                "transcript_formatted": "[SPEAKER_00] 今天讨论项目进度。\n[SPEAKER_01] 李明负责整理需求文档。\n[SPEAKER_00] 下周五前完成接口联调。",
            },
        )
        assert update_response.status_code == 200, update_response.text

        summary_response = client.get(f"/api/meetings/{meeting_id}/summary")
        assert summary_response.status_code == 200, summary_response.text
        summary_data = summary_response.json()
        assert summary_data["summary_text"]
        assert summary_data["summary_type"] == "extractive"
        assert isinstance(summary_data["action_items"], list)

        detail_response = client.get(f"/api/meetings/{meeting_id}")
        assert detail_response.status_code == 200, detail_response.text
        detail_data = detail_response.json()
        assert detail_data["summary"] == summary_data["summary_text"]
        assert detail_data["summary_type"] == "extractive"