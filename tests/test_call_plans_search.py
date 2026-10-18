from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.call_plans import candidate_questions
from backend.data import SAMPLE_JOB,CANDIDATES
from backend.engine import job_from_text,search_strings


@pytest.fixture
def desk():
    with TestClient(app) as c:
        c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123'})
        c.post('/api/job',json={'sample':True});c.post('/api/cvs/sample')
        yield c


def test_every_candidate_has_a_distinct_ten_question_plan(desk):
    plans=[]
    for candidate in CANDIDATES:
        response=desk.get('/api/questions',params={'cid':candidate['id']})
        assert response.status_code==200
        items=response.json();plans.append(tuple(q['question'] for q in items))
        assert len(items)==10
        assert [q['group'] for q in items].count('Technical')==4
        assert [q['group'] for q in items].count('Experience')==3
        assert [q['group'] for q in items].count('Fit')==3
        assert all(q['candidate_id']==candidate['id'] for q in items)
        assert all(not q['quote'] or q['quote'] in candidate['text'] for q in items)
    assert len(set(plans))==6


def test_questions_distinguish_work_study_and_missing_evidence(desk):
    ananya=desk.get('/api/questions?cid=c1').json()
    kabir=desk.get('/api/questions?cid=c2').json()
    dev=desk.get('/api/questions?cid=c6').json()
    assert all(q['focus_kind']=='Work evidence' for q in ananya[:4])
    assert kabir[0]['skill']=='Python' and kabir[0]['focus_kind']=='No clear evidence found'
    assert all(q['focus_kind']=='Course evidence only' for q in dev[:4])
    assert all('study' in q['question'] for q in dev[:4])
    assert '35%' in ananya[0]['quote']


def test_candidate_selection_difficulty_short_and_stale_ids(desk):
    original=desk.get('/api/questions?cid=c3').json()
    shorter=desk.get('/api/questions?cid=c3&short=true&difficulty=harder').json()
    assert len(shorter)==10 and shorter[0]['candidate_id']=='c3'
    assert shorter[0]['question']!=original[0]['question']
    assert all('trade-off' in q['question'] for q in shorter)
    assert desk.get('/api/questions?cid=not-on-desk').status_code==404
    assert desk.get('/api/questions?difficulty=unknown').status_code==400
    desk.post('/api/job',json={'text':SAMPLE_JOB,'must':['Accounting'],'nice':[]})
    updated=desk.get('/api/questions?cid=c3').json()
    assert updated[0]['skill']=='Accounting' and not updated[0]['quote']


def test_personal_traits_and_breaks_do_not_enter_call_plan():
    candidate=deepcopy(CANDIDATES[2]);job=job_from_text(SAMPLE_JOB)
    before=candidate_questions(job,candidate)
    candidate['text']+='\nPERSONAL\nAge: 52\nGender: female\nMarital status: married\n'
    assert candidate_questions(job,candidate)==before
    combined=' '.join(q['question'] for q in before).lower()
    assert 'career break' not in combined and 'married' not in combined


def test_search_breadth_titles_skills_and_exclusions_are_editable(desk):
    original=desk.get('/api/search').json()
    assert 'NOT' not in original['linkedin']['smart']
    settings={'titles':['Data Analyst','Reporting Analyst'],'skills':['Python','SQL'],'breadth':'wider','exclude_internships':False}
    result=desk.post('/api/search',json=settings).json()
    assert '("Python" OR "SQL")' in result['linkedin']['smart']
    assert 'Power BI' not in result['linkedin']['smart']
    assert result['linkedin']['simple']=='Data Analyst Python SQL'
    assert desk.get('/api/search').json()['settings']==settings
    settings.update(breadth='focused',exclude_internships=True)
    result=desk.post('/api/search',json=settings).json()
    assert 'AND "Python" AND "SQL"' in result['linkedin']['smart']
    assert 'NOT ("intern" OR "internship")' in result['naukri']['smart']
    assert result['filters']['location']=='Bengaluru'
    desk.post('/api/job',json={'sample':True})
    assert desk.get('/api/search').json()['settings']!=settings


def test_intern_search_never_silently_excludes_internships():
    job=job_from_text('Recruitment Intern\nMust-have skills: Recruitment, Communication\nLocation: Bengaluru\nSupport the hiring team with sourcing.')
    result=search_strings(job,category='Intern')
    assert 'NOT' not in result['linkedin']['smart']
    assert all('Intern' in title for title in result['settings']['titles'])
    assert not any('Senior' in title for title in result['titles'])


def test_search_validates_options_and_quotes_terms_as_literals(desk):
    assert desk.post('/api/search',json={'titles':[],'skills':[]}).status_code==400
    assert desk.post('/api/search',json={'titles':['Data Analyst'],'skills':[],'breadth':'unknown'}).status_code==400
    result=desk.post('/api/search',json={'titles':['Data "Analyst"'],'skills':['SQL" OR "Java\n'],'breadth':'focused'}).json()
    assert '"Data Analyst"' in result['linkedin']['smart']
    assert 'AND "SQL OR Java"' in result['linkedin']['smart']
    assert '\n' not in result['linkedin']['smart']
