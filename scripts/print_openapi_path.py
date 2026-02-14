import json
from app import app

def main():
    schema = app.openapi()
    path = schema['paths'].get('/api/meetings/{meeting_id}/transcribe')
    print(json.dumps(path, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
