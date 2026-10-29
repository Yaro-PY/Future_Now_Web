"""Real HTTP cookies and credentials survive a backend process restart."""
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import httpx


class WebsiteRuntimeTests(unittest.TestCase):
    def test_http_session_profile_and_filters_survive_restart(self):
        qa_dir = Path('.qa').resolve()
        qa_dir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=qa_dir) as temp:
            database = (Path(temp) / 'website.db').as_posix()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            base = f'http://127.0.0.1:{port}'
            with httpx.Client(base_url=base, timeout=10) as client:
                public_id = None
                for attempt in range(2):
                    with open(Path(temp) / f'website-{attempt}.log', 'w', encoding='utf-8') as log:
                        process = subprocess.Popen([sys.executable, '-B', '-m', 'tests.qa_web_server', database, str(port)],
                            stdout=log, stderr=log,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                        try:
                            deadline = time.monotonic() + 20
                            while time.monotonic() < deadline:
                                try:
                                    if client.get('/health', timeout=1).status_code == 200: break
                                except httpx.HTTPError:
                                    pass
                                if process.poll() is not None: self.fail('QA website server exited')
                                time.sleep(0.1)
                            else: self.fail('QA website server did not start')
                            if attempt == 0:
                                response = client.post('/api/v1/auth/register', json={
                                    'nickname': 'restart_user', 'display_name': 'Restart User',
                                    'password': 'FutureNow-Restart-Test-42'})
                                self.assertEqual(response.status_code, 201, response.text)
                                public_id = response.json()['user']['public_id']
                                csrf = response.json()['csrf_token']
                                response = client.put('/api/v1/me/filters', json={'country': 'europe'},
                                                      headers={'X-CSRF-Token': csrf})
                                self.assertEqual(response.status_code, 200)
                            else:
                                response = client.get('/api/v1/auth/session')
                                self.assertEqual(response.status_code, 200, response.text)
                                self.assertEqual(response.json()['user']['public_id'], public_id)
                                self.assertEqual(response.json()['user']['filters']['country'], 'europe')
                            contract = client.get('/openapi.json').json()
                            parameters = contract['paths']['/api/v1/me/filters']['put']['parameters']
                            self.assertTrue(any(item['name'] == 'X-CSRF-Token' for item in parameters))
                            self.assertEqual(client.get('/api/v1/bootstrap?lang=en').json()['app'], 'Future Now')
                        finally:
                            try:
                                if process.poll() is None: client.post('/__qa__/shutdown', timeout=3)
                                process.wait(timeout=10)
                            except (httpx.HTTPError, subprocess.TimeoutExpired):
                                if process.poll() is None: process.terminate()
                                process.wait(timeout=10)
