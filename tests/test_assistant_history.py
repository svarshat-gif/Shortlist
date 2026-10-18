import json
import importlib
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import automation,history
from backend.app import app
from backend.data import SAMPLE_JOB,CANDIDATES
from backend.engine import job_from_text,DEFAULT_WEIGHTS,assess

ROOT=Path(__file__).resolve().parent.parent


@pytest.fixture
def desk(monkeypatch):
    tmp_path=ROOT/'test-results'/'isolated'/uuid.uuid4().hex
    tmp_path.mkdir(parents=True)
    monkeypatch.setenv('SHORTLIST_HISTORY_PATH',str(tmp_path/'memory.sqlite3'))
    incoming=tmp_path/'incoming';incoming.mkdir()
    monkeypatch.setattr(automation,'folder',lambda state:ROOT/'samples' if state['agent']['source']=='samples' else incoming)
    monkeypatch.setattr(importlib.import_module('backend.app'),'assistant_folder',automation.folder)
    with TestClient(app) as c:
        c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123'})
        c.post('/api/job',json={'sample':True})
        c.post('/api/assistant/folder/create')
        c.post('/api/assistant/folder/grant',json={'allowed':True})
        yield c,incoming


def check(c):
    result=c.post('/api/assistant/check')
    assert result.status_code==200,result.text
    return result.json()


def wait_for(c,predicate,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        data=c.get('/api/state').json()
        if predicate(data):return data
        time.sleep(.15)
    raise AssertionError('The assistant did not finish the expected check.')


def test_background_folder_intake_without_upload_or_check(desk):
    c,incoming=desk
    (incoming/'new-cv.pdf').write_bytes((ROOT/'samples'/'Ananya_Rao.pdf').read_bytes())
    c.post('/api/assistant/settings',json={'enabled':True})
    data=wait_for(c,lambda s:len(s['candidates'])==1)
    assert data['candidates'][0]['name']=='Ananya Rao'
    assert data['assistant']['totals']['read']==1
    assert not data['candidates'][0]['selected']
    assert data['assistant']['questions_ready']==10
    assert any(e['title']=='Assistant review' for e in data['candidates'][0]['record'])


def test_pause_blocks_automatic_intake(desk):
    c,incoming=desk
    (incoming/'cv.pdf').write_bytes((ROOT/'samples'/'Ananya_Rao.pdf').read_bytes())
    assert c.post('/api/assistant/check').status_code==400
    assert not c.get('/api/state').json()['candidates']
    c.post('/api/assistant/settings',json={'enabled':True})
    assert len(check(c)['candidates'])==1
    c.post('/api/assistant/settings',json={'enabled':False})
    (incoming/'second.docx').write_bytes((ROOT/'samples'/'Kabir_Siddiqui.docx').read_bytes())
    assert c.post('/api/assistant/check').status_code==400
    assert len(c.get('/api/state').json()['candidates'])==1


def test_same_cv_with_another_filename_is_not_added_twice(desk):
    c,incoming=desk
    data=(ROOT/'samples'/'Ananya_Rao.pdf').read_bytes()
    (incoming/'first.pdf').write_bytes(data);(incoming/'copy.pdf').write_bytes(data)
    c.post('/api/assistant/settings',json={'enabled':True})
    s=check(c)
    assert len(s['candidates'])==1
    assert s['assistant']['totals']['duplicates']==1
    assert len(check(c)['candidates'])==1


def test_unreadable_file_can_be_fixed_and_retried(desk):
    c,incoming=desk
    path=incoming/'cv.pdf';path.write_bytes(b'broken file')
    c.post('/api/assistant/settings',json={'enabled':True})
    s=check(c);assert not s['candidates'];assert not s['files'][0]['ok']
    path.write_bytes((ROOT/'samples'/'Ananya_Rao.pdf').read_bytes())
    c.post('/api/assistant/retry')
    s=check(c);assert len(s['candidates'])==1;assert all(f['ok'] for f in s['files'])


def test_samples_are_explicit_and_low_evidence_is_flagged(desk):
    c,_=desk
    assert c.post('/api/assistant/settings',json={'source':'../private'}).status_code==400
    c.post('/api/assistant/settings',json={'enabled':True,'source':'samples'})
    s=check(c);assert len(s['candidates'])==6
    dev=next(x for x in s['assistant']['suggestions'].values() if x['name']=='Dev Patel')
    assert not dev['suggested']
    assert any('Course' in f for f in dev['flags'])
    assert not any(c['selected'] for c in s['candidates'])


def test_priorities_trigger_review_of_existing_files(desk):
    c,_=desk
    c.post('/api/assistant/settings',json={'enabled':True,'source':'samples'})
    original=check(c)
    c.post('/api/weights',json={'skills':0,'experience':100,'domain':0,'education':0})
    updated=check(c)
    assert len(updated['candidates'])==6
    old=next(s for s in original['assistant']['suggestions'].values() if s['name']=='Ananya Rao')
    new=next(s for s in updated['assistant']['suggestions'].values() if s['name']=='Ananya Rao')
    assert old['score']!=new['score']


def test_history_requires_human_review_and_saves_no_identity(desk):
    c,_=desk;c.post('/api/cvs/sample')
    body={'category':'Experienced','reason':'Ananya Rao demonstrated SQL reporting and careful checks.'}
    assert c.post('/api/history/from-candidate/c1',json=body).status_code==400
    c.post('/api/candidates/c1/review',json={'reviewed':True,'reason':'Checked the quoted work examples.'})
    r=c.post('/api/history/from-candidate/c1',json=body)
    assert r.status_code==200
    record=r.json()['record'];stored=json.dumps(record)
    assert 'Ananya' not in stored and 'Rao' not in stored and '.pdf' not in stored
    assert record['category']=='Experienced' and 'SQL' in record['skills']
    again=c.post('/api/history/from-candidate/c1',json=body).json()
    assert not again['created'] and again['record']['id']==record['id']
    c.post('/api/logout');c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123'})
    assert len(c.get('/api/history').json()['hires'])==1


def test_history_retrieval_isolated_by_role_and_level(desk):
    c,_=desk;c.post('/api/history/examples')
    context=c.get('/api/history/context').json()
    assert context['sources']
    assert all(s['category']=='Experienced' and s['role']=='Data Analyst' for s in context['sources'])
    c.post('/api/job',json={'text':SAMPLE_JOB,'category':'Intern'})
    context=c.get('/api/history/context').json()
    assert context['sources'] and all(s['category']=='Intern' for s in context['sources'])
    c.post('/api/job',json={'text':'Recruitment Intern\nMust-have skills: Recruitment, Communication\nDomain: hiring\nLocation: Bengaluru','category':'Intern'})
    assert not c.get('/api/history/context').json()['sources']


def test_history_links_are_exact_and_scores_do_not_change(desk):
    c,_=desk
    before=assess(CANDIDATES[0],job_from_text(SAMPLE_JOB),DEFAULT_WEIGHTS)['score']
    c.post('/api/history/examples');c.post('/api/cvs/sample')
    context=c.get('/api/history/context?cid=c1').json()
    source_rows={h['id']:h for h in c.get('/api/history').json()['hires']}
    for source in context['sources']:
        assert source['id'] in source_rows
        for e in source['references']:assert e in source_rows[source['id']]['evidence']
    after=next(row['score'] for row in c.get('/api/state').json()['candidates'] if row['id']=='c1')
    assert before==after


def test_followup_and_delete_change_retrieval(desk):
    c,_=desk;c.post('/api/history/examples')
    c.post('/api/history/EX-A1/outcome',json={'outcome':'Needs follow-up'})
    assert 'EX-A1' not in [s['id'] for s in c.get('/api/history/context').json()['sources']]
    c.post('/api/history/EX-A1/outcome',json={'outcome':'Doing well'})
    assert 'EX-A1' in [s['id'] for s in c.get('/api/history/context').json()['sources']]
    assert c.delete('/api/history/EX-A1').status_code==200
    assert 'EX-A1' not in [s['id'] for s in c.get('/api/history/context').json()['sources']]


def test_history_rejects_personal_trait_notes(desk):
    c,_=desk;c.post('/api/cvs/sample')
    c.post('/api/candidates/c1/review',json={'reviewed':True,'reason':'Checked evidence.'})
    assert c.post('/api/history/from-candidate/c1',json={'category':'Experienced','reason':'Young and unmarried'}).status_code==400


def test_bounded_language_agent_calls_only_read_tools(monkeypatch):
    import asyncio
    seen=[]
    result=assess(CANDIDATES[0],job_from_text(SAMPLE_JOB),DEFAULT_WEIGHTS)
    memory=dict(sources=[dict(id='H-TEST',role='Data Analyst',category='Experienced',shared=['SQL'],references=[dict(skill='SQL',quote='Built SQL reports.')],outcome='Not checked yet')],questions=['Ask about SQL checks.'])
    class Response:
        def raise_for_status(self):pass
        def json(self):
            if len(seen)==1:return {'output':[dict(type='function_call',name='check_work_evidence',call_id='a',arguments='{}'),dict(type='function_call',name='find_related_hires',call_id='b',arguments='{}')]}
            return {'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(dict(summary='Work examples support SQL reporting.',questions=['How did you check the totals?'],source_ids=['H-TEST']))}]}]}
    async def post(self,url,**kwargs):seen.append(kwargs['json']);return Response()
    monkeypatch.setenv('OPENAI_API_KEY','test-only');monkeypatch.setattr('backend.automation.httpx.AsyncClient.post',post)
    draft=asyncio.run(automation.connected_note(result,memory,job_from_text(SAMPLE_JOB)))
    assert draft['writer']=='Connected AI' and draft['source_ids']==['H-TEST']
    assert all(request['store'] is False for request in seen)
    assert 'Ananya' not in json.dumps(seen)
    assert 'function_call_output' in json.dumps(seen[1]['input'])


def test_unrecognised_language_citations_fall_back(monkeypatch):
    import asyncio
    result=assess(CANDIDATES[0],job_from_text(SAMPLE_JOB),DEFAULT_WEIGHTS)
    memory=dict(sources=[],questions=[])
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(dict(summary='Invented reference.',questions=[],source_ids=['not-saved']))}]}]}
    async def post(self,*args,**kwargs):return Response()
    monkeypatch.setenv('OPENAI_API_KEY','test-only');monkeypatch.setattr('backend.automation.httpx.AsyncClient.post',post)
    result=asyncio.run(automation.connected_note(result,memory,job_from_text(SAMPLE_JOB)))
    assert result['writer']=='Evidence checks' and result['source_ids']==[]
