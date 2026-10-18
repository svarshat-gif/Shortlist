import importlib
from pathlib import Path
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from backend import automation
from backend.app import app

ROOT=Path(__file__).resolve().parent.parent


@pytest.fixture
def desk(monkeypatch):
    incoming=ROOT/'test-results'/'folder-setup'/uuid.uuid4().hex
    monkeypatch.setattr(automation,'folder',lambda s:incoming)
    monkeypatch.setattr(importlib.import_module('backend.app'),'assistant_folder',automation.folder)
    with TestClient(app) as c:
        c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123','assistant':True})
        yield c,incoming


def upload(c,name='arriving.pdf',data=None):
    return c.post('/api/assistant/intake',files={'files':(name,data or (ROOT/'samples'/'Ananya_Rao.pdf').read_bytes(),'application/pdf')})


def test_initial_state_and_permission_are_required(desk):
    c,incoming=desk
    s=c.get('/api/state').json()
    assert not s['assistant']['enabled'] and not s['assistant']['access_granted']
    assert not s['assistant']['folder_details']['exists'] and not incoming.exists()
    assert c.post('/api/assistant/settings',json={'enabled':True}).status_code==400
    c.post('/api/job',json={'sample':True})
    assert c.post('/api/assistant/settings',json={'enabled':True}).status_code==400
    s=c.post('/api/assistant/folder/create').json()
    assert incoming.is_dir() and s['assistant']['folder_details']['count']==0
    assert not s['assistant']['enabled'] and not s['assistant']['access_granted']
    assert c.post('/api/assistant/settings',json={'enabled':True}).status_code==400
    assert upload(c).status_code==400


def test_samples_show_count_but_do_not_read_until_permission_and_start(desk):
    c,incoming=desk;c.post('/api/job',json={'sample':True})
    s=c.post('/api/assistant/folder/examples').json()
    assert s['assistant']['folder_details']['count']==6
    assert len(list(incoming.iterdir()))==6
    assert not s['candidates'] and not s['assistant']['enabled']
    assert c.post('/api/assistant/settings',json={'enabled':True}).status_code==400
    s=c.post('/api/assistant/folder/grant',json={'allowed':True}).json()
    assert s['assistant']['access_granted'] and not s['assistant']['enabled']
    assert not s['candidates']
    assert c.post('/api/assistant/settings',json={'enabled':True}).status_code==200
    s=c.post('/api/assistant/check').json()
    assert len(s['candidates'])==6
    s=c.post('/api/assistant/folder/disconnect').json()
    assert not s['assistant']['enabled'] and not s['assistant']['access_granted']
    assert c.post('/api/assistant/settings',json={'enabled':True}).status_code==400


def test_browser_folder_intake_requires_start_and_stops_on_disconnect(desk):
    c,_=desk;c.post('/api/job',json={'sample':True})
    assert c.post('/api/assistant/folder/connect',json={'name':'CVs','allowed':False}).status_code==400
    s=c.post('/api/assistant/folder/connect',json={'name':'My CVs','allowed':True,'count':1,'files':['arriving.pdf']}).json()
    assert s['assistant']['folder_details']['name']=='My CVs'
    assert not s['assistant']['enabled'] and not s['candidates']
    assert upload(c).status_code==400
    c.post('/api/assistant/settings',json={'enabled':True})
    s=upload(c).json();assert len(s['candidates'])==1
    s=upload(c,'duplicate.pdf').json();assert len(s['candidates'])==1
    assert s['assistant']['totals']['duplicates']==1
    s=c.post('/api/assistant/check').json()
    assert len(s['assistant']['suggestions'])==1 and s['assistant']['questions_ready']==10
    assert not s['candidates'][0]['selected']
    s=c.post('/api/assistant/folder/status',json={'count':2,'files':['arriving.pdf','duplicate.pdf']}).json()
    assert s['assistant']['folder_details']['count']==2
    c.post('/api/assistant/folder/disconnect')
    assert upload(c).status_code==400
    assert c.post('/api/assistant/folder/status',json={'count':3}).status_code==400


def test_revoking_permission_and_changing_folder_pauses(desk):
    c,_=desk;c.post('/api/job',json={'sample':True});c.post('/api/assistant/folder/create')
    c.post('/api/assistant/folder/grant',json={'allowed':True})
    c.post('/api/assistant/settings',json={'enabled':True})
    s=c.post('/api/assistant/folder/grant',json={'allowed':False}).json()
    assert not s['assistant']['enabled'] and not s['assistant']['access_granted']
    c.post('/api/assistant/folder/grant',json={'allowed':True})
    c.post('/api/assistant/settings',json={'enabled':True})
    s=c.post('/api/assistant/folder/connect',json={'name':'Other CVs','allowed':True}).json()
    assert not s['assistant']['enabled']
    assert s['assistant']['folder_details']['count']==0


def test_browser_read_errors_can_be_retried_and_grant_cannot_read_arbitrary_path(desk):
    c,incoming=desk;c.post('/api/job',json={'sample':True})
    assert c.post('/api/assistant/folder/grant',json={'allowed':True,'name':str(ROOT/'samples')}).status_code==400
    c.post('/api/assistant/folder/connect',json={'name':str(ROOT/'samples'),'allowed':True,'count':0})
    c.post('/api/assistant/settings',json={'enabled':True})
    s=c.post('/api/assistant/check').json()
    assert not s['candidates'] and not incoming.exists()
    s=upload(c,data=b'broken pdf').json();assert not s['files'][0]['ok']
    old=s['assistant']['retry_revision']
    s=c.post('/api/assistant/retry').json()
    assert s['assistant']['retry_revision']==old+1 and not s['files']
    assert len(upload(c).json()['candidates'])==1
