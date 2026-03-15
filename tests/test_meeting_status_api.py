"""会议状态接口回归测试"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import app


def _create_meeting(client: TestClient, title_suffix: str) -> int:
    now = datetime.utcnow()
    payload = {
        "title": f"状态测试会议-{title_suffix}",
        "description": "用于验证会议状态更新",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(minutes=30)).isoformat(),
        "duration": 30,
        "participants": 3,
        "location": "测试会议室",
    }
    response = client.post("/api/meetings", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    return data["id"]


def test_create_meeting_accepts_status():
    now = datetime.utcnow()
    payload = {
        "title": "状态测试会议-create",
        "description": "用于验证创建时状态写入",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(minutes=30)).isoformat(),
        "duration": 30,
        "participants": 3,
        "location": "测试会议室",
        "status": "in_progress",
    }

    with TestClient(app) as client:
        create_response = client.post("/api/meetings", json=payload)
        assert create_response.status_code == 200, create_response.text
        create_data = create_response.json()
        assert create_data["status"] == "in_progress"

        detail_response = client.get(f"/api/meetings/{create_data['id']}")
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.json()["status"] == "in_progress"


def test_update_meeting_status_via_put():
    with TestClient(app) as client:
        meeting_id = _create_meeting(client, "put")

        update_response = client.put(
            f"/api/meetings/{meeting_id}",
            json={"status": "archived"},
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["status"] == "archived"

        detail_response = client.get(f"/api/meetings/{meeting_id}")
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.json()["status"] == "archived"


def test_transcribe_endpoint_updates_meeting_status(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.meetings._transcribe_audio_for_meeting",
        lambda *args, **kwargs: {
            "text": "这是测试转录文本。",
            "language": "zh",
            "processing_time": 0.5,
            "duration": 20.0,
            "segments": [
                {
                    "speaker": "SPEAKER_00",
                    "text": "这是测试转录文本。",
                    "start_time": 0.0,
                    "end_time": 10.0,
                    "confidence": 0.9,
                }
            ],
        },
    )

    with TestClient(app) as client:
        meeting_id = _create_meeting(client, "transcribe")

        upload_response = client.post(
            f"/api/meetings/{meeting_id}/upload-audio",
            files={"file": ("status.wav", b"fake wav data", "audio/wav")},
        )
        assert upload_response.status_code == 200, upload_response.text

        transcribe_response = client.post(f"/api/meetings/{meeting_id}/transcribe")
        assert transcribe_response.status_code == 200, transcribe_response.text
        transcribe_data = transcribe_response.json()
        assert transcribe_data["meeting_status"] == "completed"

        detail_response = client.get(f"/api/meetings/{meeting_id}")
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.json()["status"] == "completed"


def test_analyze_endpoint_updates_meeting_status():
    with TestClient(app) as client:
        meeting_id = _create_meeting(client, "analyze")

        update_response = client.put(
            f"/api/meetings/{meeting_id}",
            json={
                "transcript_raw": "今天讨论项目进度。下周五前完成接口联调。",
                "transcript_formatted": "[SPEAKER_00] 今天讨论项目进度。\n[SPEAKER_01] 下周五前完成接口联调。",
            },
        )
        assert update_response.status_code == 200, update_response.text

        analyze_response = client.post(f"/api/meetings/{meeting_id}/analyze")
        assert analyze_response.status_code == 200, analyze_response.text
        analyze_data = analyze_response.json()
        assert analyze_data["meeting_status"] == "completed"

        detail_response = client.get(f"/api/meetings/{meeting_id}")
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.json()["status"] == "completed"
