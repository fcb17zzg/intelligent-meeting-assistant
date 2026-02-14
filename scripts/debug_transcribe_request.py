from fastapi.testclient import TestClient
from app import app
import io

def run():
    c = TestClient(app)
    files = {"file": ("test.wav", io.BytesIO(b"RIFF....FAKEAUDIO"), "audio/wav")}
    r = c.post('/api/meetings/test_meeting/transcribe', files=files, params={'mode':'sync'})
    print('status', r.status_code)
    try:
        import json
        print('json:', json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print('text:', r.text)
        print('error:', e)

if __name__ == '__main__':
    run()
