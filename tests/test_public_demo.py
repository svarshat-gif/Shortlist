from fastapi.testclient import TestClient

from backend import app as app_module
from backend.app import app


def test_public_demo_allows_samples_but_blocks_uploads_and_shared_writes(monkeypatch):
    monkeypatch.setattr(app_module, 'PUBLIC_DEMO', True)
    with TestClient(app, base_url='https://testserver') as client:
        login = client.post('/api/login', json={
            'email': 'recruiter@demo.com',
            'password': 'demo123',
            'demo': False,
            'assistant': True,
        })
        assert login.status_code == 200
        assert login.json()['public_demo'] is True
        assert login.json()['demo'] is True
        assert login.json()['assistant']['enabled'] is False
        assert 'secure' in login.headers['set-cookie'].lower()

        assert client.post('/api/job', json={'sample': True}).status_code == 200
        samples = client.post('/api/cvs/sample')
        assert samples.status_code == 200
        assert len(samples.json()['candidates']) == 6

        upload = client.post('/api/cvs', files=[
            ('files', ('private.pdf', b'%PDF-1.4 invalid fixture', 'application/pdf')),
        ])
        assert upload.status_code == 403
        assert 'fictional sample CVs only' in upload.json()['detail']
        assert client.post('/api/assistant/folder/create').status_code == 403
        assert client.post('/api/history/examples').status_code == 403
