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
        assert login.json()['assistant']['source'] == 'samples'
        assert login.json()['assistant']['access_granted'] is True
        assert 'secure' in login.headers['set-cookie'].lower()

        assert client.post('/api/job', json={'sample': True}).status_code == 200
        assert client.post('/api/assistant/settings', json={'source': 'inbox'}).status_code == 403
        assert client.post('/api/assistant/settings', json={'source': 'browser'}).status_code == 403
        started = client.post('/api/assistant/settings', json={'enabled': True})
        assert started.status_code == 200
        assert started.json()['assistant']['enabled'] is True
        checked = client.post('/api/assistant/check')
        assert checked.status_code == 200
        assert len(checked.json()['candidates']) == 6
        assert checked.json()['assistant']['totals']['read'] == 6

        upload = client.post('/api/cvs', files=[
            ('files', ('private.pdf', b'%PDF-1.4 invalid fixture', 'application/pdf')),
        ])
        assert upload.status_code == 403
        assert 'Direct uploads' in upload.json()['detail']
        assert client.post('/api/job/file', files={'file': ('private.docx', b'private', 'application/octet-stream')}).status_code == 403
        assert client.post('/api/assistant/folder/create').status_code == 403
        not_connected = client.post('/api/assistant/intake', files=[
            ('files', ('private.pdf', b'%PDF-1.4 invalid fixture', 'application/pdf')),
        ])
        assert not_connected.status_code == 400
        assert 'Connect your folder' in not_connected.json()['detail']
        assert client.post('/api/history/examples').status_code == 403


def test_public_demo_allows_explicit_browser_folder_intake_only(monkeypatch):
    from backend.data import CANDIDATES

    monkeypatch.setattr(app_module, 'PUBLIC_DEMO', True)
    sample = CANDIDATES[0]
    sample_path = app_module.ROOT / 'samples' / sample['filename']

    with TestClient(app, base_url='https://testserver') as client:
        login = client.post('/api/login', json={'email': 'recruiter@demo.com', 'password': 'demo123'})
        assert login.status_code == 200
        assert client.post('/api/job', json={'sample': True}).status_code == 200
        assert client.post('/api/assistant/folder/create').status_code == 403

        folder = client.post('/api/assistant/folder/connect', json={
            'name': 'My selected CVs',
            'count': 1,
            'files': [sample['filename']],
            'allowed': True,
        })
        assert folder.status_code == 200
        assert folder.json()['assistant']['source'] == 'browser'
        assert folder.json()['assistant']['access_granted'] is True
        assert folder.json()['assistant']['enabled'] is True
        started = client.post('/api/assistant/settings', json={'enabled': True})
        assert started.status_code == 200

        intake = client.post('/api/assistant/intake', files=[
            ('files', (sample['filename'], sample_path.read_bytes(), 'application/pdf')),
        ])
        assert intake.status_code == 200
        assert len(intake.json()['candidates']) == 1
        assert intake.json()['assistant']['totals']['read'] == 1

        disconnected = client.post('/api/assistant/folder/disconnect')
        assert disconnected.status_code == 200
        assert disconnected.json()['assistant']['enabled'] is False
        assert client.post('/api/cvs', files=[
            ('files', ('private.pdf', b'%PDF-1.4 invalid fixture', 'application/pdf')),
        ]).status_code == 403
