from fastapi.testclient import TestClient

from backend import app as app_module
from backend.app import app


def test_public_demo_allows_direct_uploads_but_blocks_shared_writes(monkeypatch):
    async def read_uploaded_file(file):
        return (
            'Taylor Example\nWORK EXPERIENCE\nData Analyst | Acme | 2022 to 2025\n'
            'Used SQL and Python to build Power BI dashboards for e-commerce.\n'
            'EDUCATION\nBSc Statistics, 2021'
        )

    async def read_uploaded_job(file):
        from backend.data import SAMPLE_JOB
        return SAMPLE_JOB

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

        monkeypatch.setattr(app_module, 'read_file', read_uploaded_file)
        upload = client.post('/api/cvs', files=[
            ('files', ('fictional.pdf', b'fictional fixture', 'application/pdf')),
        ])
        assert upload.status_code == 200
        assert len(upload.json()['candidates']) == 1
        assert upload.json()['files'][-1]['ok'] is True

        monkeypatch.setattr(app_module, 'read_file', read_uploaded_job)
        job_upload = client.post('/api/job/file', files={'file': ('fictional.docx', b'fictional fixture', 'application/octet-stream')})
        assert job_upload.status_code == 200
        assert job_upload.json()['job']['role'] == 'Data Analyst'

        assert client.post('/api/assistant/folder/create').status_code == 403
        not_connected = client.post('/api/assistant/intake', files=[
            ('files', ('fictional.pdf', b'fictional fixture', 'application/pdf')),
        ])
        assert not_connected.status_code == 400
        assert 'Connect your folder' in not_connected.json()['detail']
        assert client.post('/api/history/examples').status_code == 403


def test_public_demo_direct_job_and_cv_uploads(monkeypatch):
    from backend.data import SAMPLE_JOB

    async def read_uploaded_file(file):
        if file.filename == 'role.docx':
            return SAMPLE_JOB
        return (
            'Taylor Example\nWORK EXPERIENCE\nData Analyst | Acme | 2022 to 2025\n'
            'Used SQL and Python to build Power BI dashboards for e-commerce.\n'
            'EDUCATION\nBSc Statistics, 2021'
        )

    monkeypatch.setattr(app_module, 'PUBLIC_DEMO', True)
    monkeypatch.setattr(app_module, 'read_file', read_uploaded_file)
    with TestClient(app, base_url='https://testserver') as client:
        assert client.post('/api/login', json={
            'email': 'recruiter@demo.com',
            'password': 'demo123',
        }).status_code == 200

        job_upload = client.post('/api/job/file', files={
            'file': ('role.docx', b'fictional fixture', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        })
        assert job_upload.status_code == 200
        assert job_upload.json()['job']['role'] == 'Data Analyst'

        cv_upload = client.post('/api/cvs', files=[
            ('files', ('fictional.pdf', b'fictional fixture', 'application/pdf')),
        ])
        assert cv_upload.status_code == 200
        assert len(cv_upload.json()['candidates']) == 1
        assert cv_upload.json()['files'][-1]['ok'] is True
        assert cv_upload.json()['candidates'][0]['name'] == 'Taylor Example'
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
