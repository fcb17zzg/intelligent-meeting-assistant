#!/usr/bin/env python
import subprocess
import sys
import os

os.chdir(r'H:\study\graduate_paper\auto-meeting-assistent')
result = subprocess.run([
    sys.executable, '-m', 'pytest', 
    'tests/transcription/test_transcribe_endpoint.py::test_transcribe_sync_monkeypatch',
    '-v', '--tb=short'
])
sys.exit(result.returncode)
