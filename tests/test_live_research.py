"""Exercise paid integration boundaries without spending money or leaking CVs."""
import json
from fastapi.testclient import TestClient
from backend.app import app

class FakeResponse:
    def __init__(self,data):self.data=data
    def raise_for_status(self):pass
    def json(self):return self.data

def live_client():
    c=TestClient(app)
    c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123','demo':False})
    c.post('/api/job',json={'sample':True})
    return c

def test_live_research_only_uses_returned_public_sources(monkeypatch):
    seen={}
    source='https://example.org/careers/analyst'
    rows=[dict(company='Public Example',experience='3–5 years',pay='Not shared · Estimate',low=0,high=0,location='Bengaluru',url=source,status='Pay is not shared in the public post.'),dict(company='Forbidden',experience='3 years',pay='Estimate',low=0,high=0,location='Bengaluru',url='https://linkedin.com/jobs/123',status='Not allowed'),dict(company='Not cited',experience='3 years',pay='Estimate',low=0,high=0,location='Bengaluru',url='https://uncited.example/careers',status='Not cited')]
    async def fake_post(self,url,**kwargs):
        seen.update(kwargs['json'])
        return FakeResponse({'output':[{'type':'web_search_call','action':{'sources':[{'url':source}]}},{'type':'message','content':[{'type':'output_text','text':json.dumps({'rows':rows}),'annotations':[]}]}]})
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    monkeypatch.setattr('backend.app.httpx.AsyncClient.post',fake_post)
    with live_client() as c:
        result=c.get('/api/market').json()
        assert result['live'] and len(result['rows'])==1
        assert result['checked']
        assert result['rows'][0]['url']==source
        assert seen['store'] is False
        assert 'Ananya' not in seen['input'] and 'Dev Patel' not in seen['input']
        assert seen['tools'][0]['filters']['blocked_domains']==['linkedin.com','naukri.com']
        again=c.post('/api/market/check/live0').json()
        assert again['confirmed'] and 'Public Example' in seen['input']

def test_network_failure_falls_back_honestly(monkeypatch):
    async def fail(self,*args,**kwargs):raise RuntimeError('private detail must never reach the interface')
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    monkeypatch.setattr('backend.app.httpx.AsyncClient.post',fail)
    with live_client() as c:
        result=c.get('/api/market').json()
        assert not result['live'] and result['checked'] is None
        assert 'could not check' in result['note']
        assert 'private detail' not in json.dumps(result)

def test_malformed_paid_response_keeps_demo_working(monkeypatch):
    async def malformed(self,*args,**kwargs):return FakeResponse({'output':[{'content':[{'type':'output_text','text':'not valid structured content'}]}]})
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    monkeypatch.setattr('backend.app.httpx.AsyncClient.post',malformed)
    with live_client() as c:
        result=c.get('/api/market').json()
        assert not result['live'] and len(result['rows'])==3
