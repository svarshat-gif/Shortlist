from copy import deepcopy
from io import BytesIO
import time
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from backend.app import app,SESSIONS
from backend.data import SAMPLE_JOB,CANDIDATES
from backend.engine import assess,job_from_text,DEFAULT_WEIGHTS,scoring_document,questions,search_strings

@pytest.fixture
def client():
    with TestClient(app) as c:
        assert c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123'}).status_code==200
        assert c.post('/api/job',json={'sample':True}).status_code==200
        yield c

def test_course_keywords_do_not_count_as_work():
    job=job_from_text(SAMPLE_JOB)
    professional=assess(CANDIDATES[0],job,DEFAULT_WEIGHTS)
    course=assess(CANDIDATES[-1],job,DEFAULT_WEIGHTS)
    assert professional['score']>course['score']+40
    assert not course['matched']
    assert all(e['kind']=='Course evidence only' for e in course['evidence'])

def test_proof_is_exact_and_never_invented():
    for c in CANDIDATES:
        result=assess(c,job_from_text(SAMPLE_JOB),DEFAULT_WEIGHTS)
        for proof in result['evidence']:
            assert not proof['quote'] or proof['quote'] in c['text']
        assert all(p['kind']=='Work evidence' for p in result['evidence'] if p['skill'] in result['matched'])

@pytest.mark.parametrize('personal',['Gender: female','Age: 52','Marital status: married','Nationality: Indian','Religion: Hindu','Photo: portrait'])
def test_personal_details_do_not_change_ranking(personal):
    c=deepcopy(CANDIDATES[0]);j=job_from_text(SAMPLE_JOB)
    before=assess(c,j,DEFAULT_WEIGHTS)
    c['name']='Other Name';c['text']='Other Name\n'+personal+'\n'+'\n'.join(c['text'].splitlines()[1:])
    after=assess(c,j,DEFAULT_WEIGHTS)
    assert before['score']==after['score']
    assert before['breakdown']==after['breakdown']

def test_gap_and_preferences_are_not_scored():
    c=deepcopy(CANDIDATES[2]);j=job_from_text(SAMPLE_JOB)
    before=assess(c,j,DEFAULT_WEIGHTS)
    c['text']=c['text'].replace('Career break, 2022 to 2024. Available for full-time work.','').replace('Remote','Hybrid').replace('Kochi','Bengaluru')
    assert assess(c,j,DEFAULT_WEIGHTS)['score']==before['score']

def test_auth_is_required_and_session_expires():
    with TestClient(app) as c:
        assert c.get('/api/state').status_code==401
        c.post('/api/login',json={'email':'recruiter@demo.com','password':'demo123'})
        sid=c.cookies['shortlist_session'];SESSIONS[sid]['expires']=time.time()-1
        assert c.get('/api/state').status_code==401
        assert sid not in SESSIONS

def test_actual_pdf_and_word_samples(client):
    r=client.post('/api/cvs/sample').json()
    assert len(r['candidates'])==6 and len(r['files'])==6
    assert sum(f['name'].endswith('.pdf') for f in r['files'])==3
    assert sum(f['name'].endswith('.docx') for f in r['files'])==3
    assert all(f['ok'] for f in r['files'])
    assert next(c for c in r['candidates'] if c['id']=='c6')['confidence']=='Low'
    assert len(client.post('/api/cvs/sample').json()['candidates'])==6

def test_weights_drive_order_and_are_recorded(client):
    original=client.post('/api/cvs/sample').json()
    new=client.post('/api/weights',json=dict(skills=0,experience=100,domain=0,education=0)).json()
    assert original['candidates'][0]['id']!=new['candidates'][0]['id']
    assert new['candidates'][0]['id']=='c2'
    assert new['candidates'][0]['record'][-1]['title']=='Priorities changed'
    assert client.post('/api/weights',json=dict(skills=0,experience=0,domain=0,education=0)).status_code==400

def test_override_requires_reason_and_download_records_it(client):
    client.post('/api/cvs/sample')
    assert client.post('/api/candidates/c6/review',json={'score':29}).status_code==400
    assert client.post('/api/candidates/c6/review',json={'score':29,'reason':'Course evidence checked.','reviewed':True}).status_code==200
    text=client.get('/api/download/record/c6').text
    assert 'Course evidence checked.' in text and 'Reviewed by me' in text
    assert client.post('/api/candidates/c6/review',json={'score':101,'reason':'Invalid'}).status_code==422

def test_fairness_uses_suggested_score(client):
    client.post('/api/cvs/sample')
    client.post('/api/candidates/c1/review',json={'score':23,'reason':'An intentional review.'})
    result=client.post('/api/fairness/c1').json()['fairness']
    assert result['before']==result['after'] and result['before']!=23

def test_each_question_has_accessible_option_and_still_ten():
    j=job_from_text(SAMPLE_JOB)
    standard=questions(j);brief=questions(j,'harder',True)
    assert len(standard)==len(brief)==10
    assert all(q['accessible'] and q['skill'] and q['good'] for q in brief)
    assert brief[0]['question']!=standard[0]['question']

def test_unreadable_files_have_helpful_rows(client):
    r=client.post('/api/cvs',files=[('files',('bad.pdf',b'not a pdf','application/pdf')),('files',('plain.txt',b'not supported','text/plain'))]).json()
    assert len(r['files'])==2 and not any(f['ok'] for f in r['files'])
    assert not r['candidates']
    assert 'fresh' in r['files'][0]['warning']

def test_demo_market_is_honest_and_double_check_not_fake(client):
    r=client.get('/api/market').json()
    assert not r['live'] and r['checked'] is None
    assert all('Estimate' in row['pay'] and 'not confirmed' in row['status'] for row in r['rows'])
    assert client.post('/api/market/check/m1').json()['confirmed'] is False

def test_review_request_and_sharing_recorded(client):
    client.post('/api/cvs/sample')
    r=client.post('/api/candidates/c3/review',json={'request_review':True,'sharing':{'skills':False,'contact':False}}).json()
    c=next(x for x in r['candidates'] if x['id']=='c3')
    assert c['review_requested'] and not c['sharing']['skills']
    assert any(e['title']=='Review requested' for e in c['record'])

def test_downloads_and_one_page_brief(client):
    client.post('/api/cvs/sample');client.post('/api/candidates/c1/review',json={'selected':True})
    csv=client.get('/api/download/shortlist')
    assert csv.status_code==200 and 'Ananya Rao' in csv.text and 'Dev Patel' not in csv.text
    pdf=client.get('/api/download/brief');reader=PdfReader(BytesIO(pdf.content))
    assert len(reader.pages)==1
    assert 'Ananya' in reader.pages[0].extract_text()
    assert 'Not run yet' in reader.pages[0].extract_text()

def test_job_change_clears_stale_decisions(client):
    client.post('/api/cvs/sample');client.post('/api/candidates/c1/review',json={'score':12,'reason':'Old role.'})
    r=client.post('/api/job',json={'text':SAMPLE_JOB+'\nSalary: 16 to 22 lakh per year'}).json()
    assert r['candidates'][0]['score']!=12
    assert r['candidates'][0]['record'][-1]['title']=='Job updated'

def test_logout_purges_session(client):
    sid=client.cookies['shortlist_session'];client.post('/api/cvs/sample')
    assert client.post('/api/logout').status_code==200
    assert sid not in SESSIONS
    assert client.get('/api/state').status_code==401

def test_cross_origin_write_rejected(client):
    assert client.post('/api/cvs/sample',headers={'Origin':'https://example.com'}).status_code==403

def test_search_titles_follow_the_uploaded_role():
    j=job_from_text('Software Engineer\nMust-have skills: Java, React\nExperience: 3 to 5 years\nLocation: Bengaluru')
    strings=search_strings(j)
    assert 'Business Analyst' not in strings['linkedin']['smart']
    assert 'Software Developer' in strings['linkedin']['smart']
    assert 'AND "Java"' in strings['naukri']['smart']

def test_human_added_skill_cannot_invent_proof(client):
    client.post('/api/cvs/sample')
    result=client.post('/api/candidates/c6/review',json={'matched':['Accounting'],'reason':'Checking a recruiter-supplied skill.'}).json()
    c=next(x for x in result['candidates'] if x['id']=='c6')
    p=next(x for x in c['evidence'] if x['skill']=='Accounting')
    assert p['quote']=='' and p['kind']=='No clear evidence found'
