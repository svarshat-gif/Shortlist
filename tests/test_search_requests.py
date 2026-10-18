from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.data import SAMPLE_JOB
from backend.engine import job_from_text,search_strings
from backend.search_requests import generate_settings


@pytest.fixture
def desk():
    with TestClient(app) as c:
        c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123'})
        c.post('/api/job',json={'sample':True})
        yield c


def test_specific_request_replaces_old_skills_and_filters(desk):
    before=desk.get('/api/state').json()
    request='Find a senior React developer in Pune with TypeScript and Node.js, 3 to 5 years.'
    response=desk.post('/api/search/generate',json={'text':request})
    assert response.status_code==200,response.text
    data=response.json();settings=data['settings']
    assert settings['titles']==['Senior React Developer']
    assert set(settings['skills'])=={'React','TypeScript','Node.js'}
    assert data['filters']=={'location':'Pune','experience':'3 to 5 years'}
    assert 'SQL' not in data['linkedin']['smart']
    assert data['request_text']==request
    assert desk.get('/api/state').json()['job']==before['job']
    assert desk.get('/api/state').json()['weights']==before['weights']
    assert desk.get('/api/search').json()['settings']==settings


def test_labelled_request_supports_unknown_roles_skills_and_locations(desk):
    text='Role: Quantum Hardware Specialist; Skills: Qiskit, cryogenics; Location: Zurich; Experience: 4 to 6 years'
    data=desk.post('/api/search/generate',json={'text':text}).json()
    assert data['settings']['titles']==['Quantum Hardware Specialist']
    assert data['settings']['skills']==['Qiskit','cryogenics']
    assert data['filters']=={'location':'Zurich','experience':'4 to 6 years'}
    assert '"Qiskit"' in data['naukri']['smart']


def test_unknown_terms_in_a_natural_request_are_editable_search_terms():
    settings,_=generate_settings('Find a Rust specialist in Oslo with Tokio and Axum',job_from_text(SAMPLE_JOB))
    assert settings['titles']==['Rust specialist']
    assert set(settings['skills'])=={'Rust','Tokio','Axum'}
    assert settings['location']=='Oslo'
    assert settings['experience']=='Not shared'


def test_negative_terms_do_not_become_required_skills(desk):
    data=desk.post('/api/search/generate',json={'text':'Find a Python developer with Django and PostgreSQL; not Java; match any skill'}).json()
    assert set(data['settings']['skills'])=={'Python','Django','PostgreSQL'}
    assert data['settings']['breadth']=='wider'
    assert data['settings']['exclude_terms']==['Java']
    assert 'NOT ("Java")' in data['linkedin']['smart']
    assert 'AND "Java"' not in data['linkedin']['smart']
    settings,_=generate_settings('Find a Python developer not Java with Django',job_from_text(SAMPLE_JOB))
    assert 'Django' in settings['skills'] and 'Java' not in settings['skills']


def test_intern_request_and_unstated_filters_do_not_inherit_senior_job(desk):
    data=desk.post('/api/search/generate',json={'text':'Find a recruitment intern with Communication and Excel'}).json()
    assert data['settings']['titles']==['Recruitment Intern']
    assert not data['settings']['exclude_internships']
    assert data['filters']=={'location':'Not shared','experience':'Not shared'}
    assert 'NOT' not in data['linkedin']['smart']


def test_skills_only_request_explains_role_fallback_and_reset(desk):
    data=desk.post('/api/search/generate',json={'text':'Find candidates with Rust and Kubernetes'}).json()
    assert data['settings']['titles']==['Data Analyst']
    assert set(data['settings']['skills'])=={'Rust','Kubernetes'}
    assert any('current job title' in note for note in data['notes'])
    original=desk.post('/api/search/reset').json()
    assert original['request_text']=='' and original['notes']==[]
    assert original['settings']['titles'][0]=='Data Analyst'
    assert original['filters']['location']=='Bengaluru'


def test_catalogue_and_request_validation(desk):
    data=desk.get('/api/search/catalog').json()
    assert 'React Developer' in data['titles'] and 'Rust' in data['skills']
    assert desk.post('/api/search/generate',json={'text':'hi'}).status_code==422
    assert desk.post('/api/search/generate',json={'text':'x'*2001}).status_code==422
    assert desk.post('/api/search/generate',json={'text':'        '}).status_code==400
    desk.post('/api/logout')
    assert desk.get('/api/search/catalog').status_code==401
    assert desk.post('/api/search/generate',json={'text':'Find candidates with Rust'}).status_code==401


def test_custom_keywords_filters_and_exclusions_round_trip_safely(desk):
    settings={'titles':['Specialist in strange work'],'skills':['Qiskit','C++','C#'],'location':'Oslo','experience':'4+ years','exclude_terms':['Java" OR "PHP']}
    response=desk.post('/api/search',json=settings)
    assert response.status_code==200
    data=response.json()
    assert data['filters']=={'location':'Oslo','experience':'4+ years'}
    assert 'NOT ("Java OR PHP")' in data['linkedin']['smart']
    assert 'AND "C++" AND "C#"' in data['linkedin']['smart']
    desk.post('/api/job',json={'sample':True})
    reset=desk.get('/api/search').json()
    assert reset['request_text']=='' and reset['filters']['location']=='Bengaluru'
