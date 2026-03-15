import io
import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pyttsx3
from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app

AUDIO_DIR = ROOT_DIR / "test_audio" / "generated"
REPORT_DIR = ROOT_DIR / "test_reports"


def generate_meeting_audio_wav(output_path: Path) -> str:
    """Generate a local synthetic meeting speech audio for end-to-end testing."""
    script_text = (
        "今天是项目周会。"
        "李明负责接口联调，截止时间是周五下午六点。"
        "王芳负责测试用例编写，下周一开始回归测试。"
        "本次会议决定先完成支付模块，再处理报表优化。"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    engine = pyttsx3.init()
    # 适当降低语速，提升中文识别稳定性。
    try:
        engine.setProperty("rate", 150)
    except Exception:
        pass

    engine.save_to_file(script_text, str(output_path))
    engine.runAndWait()

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("生成测试音频失败: 文件不存在或大小为0")

    return script_text


def create_meeting(client: TestClient) -> int:
    now = datetime.utcnow()
    payload = {
        "title": "真实样本验收会议",
        "description": "自动生成音频进行端到端验收",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(minutes=30)).isoformat(),
        "duration": 30,
        "participants": 3,
        "location": "自动化测试",
    }
    resp = client.post("/api/meetings", json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"创建会议失败: {resp.status_code} {resp.text}")
    return resp.json()["id"]


def evaluate_keywords(text: str, keywords: list[str]) -> dict:
    hit = [kw for kw in keywords if kw in text]
    return {
        "keywords": keywords,
        "hit_keywords": hit,
        "hit_count": len(hit),
        "hit_ratio": round(len(hit) / max(len(keywords), 1), 3),
    }


def run_e2e() -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = AUDIO_DIR / f"meeting_sample_{timestamp}.wav"

    expected_keywords = ["接口", "测试", "周五", "回归", "支付模块"]

    source_script = generate_meeting_audio_wav(audio_path)

    started = time.time()
    with TestClient(app) as client:
        meeting_id = create_meeting(client)

        with open(audio_path, "rb") as audio_file:
            upload_resp = client.post(
                f"/api/meetings/{meeting_id}/upload-audio",
                files={"file": (audio_path.name, audio_file, "audio/wav")},
            )
        if upload_resp.status_code != 200:
            raise RuntimeError(f"上传失败: {upload_resp.status_code} {upload_resp.text}")

        transcribe_resp = client.post(f"/api/meetings/{meeting_id}/transcribe")
        if transcribe_resp.status_code != 200:
            raise RuntimeError(f"转录失败: {transcribe_resp.status_code} {transcribe_resp.text}")
        transcribe_data = transcribe_resp.json()

        transcript_resp = client.get(f"/api/meetings/{meeting_id}/transcript")
        if transcript_resp.status_code != 200:
            raise RuntimeError(f"获取转录文本失败: {transcript_resp.status_code} {transcript_resp.text}")
        transcript_data = transcript_resp.json()

        summary_resp = client.get(f"/api/meetings/{meeting_id}/summary")
        if summary_resp.status_code != 200:
            raise RuntimeError(f"摘要失败: {summary_resp.status_code} {summary_resp.text}")
        summary_data = summary_resp.json()

    elapsed = round(time.time() - started, 2)

    transcript_text = str(transcript_data.get("transcript_formatted") or transcript_data.get("transcript_raw") or "")
    summary_text = str(summary_data.get("summary_text") or "")

    result = {
        "meeting_id": meeting_id,
        "audio_path": str(audio_path),
        "audio_size_bytes": audio_path.stat().st_size,
        "source_script": source_script,
        "transcription": {
            "status": transcribe_data.get("status"),
            "segments_count": transcribe_data.get("segments_count"),
            "transcript_endpoint_segments_count": transcript_data.get("segments_count"),
            "text_length": len(transcript_text),
            "text_preview": transcript_text[:240],
            "keyword_eval": evaluate_keywords(transcript_text, expected_keywords),
        },
        "summary": {
            "summary_type": summary_data.get("summary_type"),
            "text_length": len(summary_text),
            "text_preview": summary_text[:240],
            "action_items_count": len(summary_data.get("action_items", [])),
            "keyword_eval": evaluate_keywords(summary_text, expected_keywords),
        },
        "elapsed_seconds": elapsed,
        "pass": len(transcript_text) > 20 and len(summary_text) > 20 and transcribe_data.get("status") == "completed",
        "generated_at": datetime.now().isoformat(),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"real_audio_e2e_report_{timestamp}.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["report_path"] = str(report_path)
    return result


if __name__ == "__main__":
    output = run_e2e()
    print(json.dumps(output, ensure_ascii=False, indent=2))
