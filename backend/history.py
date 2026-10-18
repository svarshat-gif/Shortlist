"""Local hiring memory: SQLite FTS5 retrieval over anonymous, confirmed work evidence.

History is reference material, never a training label or an automatic score bonus.
"""
import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .engine import assess, scoring_document, has_skill

ROOT=Path(__file__).resolve().parent.parent
CATEGORIES=['Intern','Graduate','Experienced','Senior']
OUTCOMES=['Not checked yet','Doing well','Needs follow-up']


def database():
    path=Path(os.environ.get('SHORTLIST_HISTORY_PATH',str(ROOT/'data'/'hiring-history.sqlite3')))
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=10)
    conn.row_factory=sqlite3.Row
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS hires (
      id TEXT PRIMARY KEY, signature TEXT UNIQUE NOT NULL, role TEXT NOT NULL,
      role_key TEXT NOT NULL, category TEXT NOT NULL, skills TEXT NOT NULL,
      evidence TEXT NOT NULL, note TEXT NOT NULL, outcome TEXT NOT NULL,
      saved_at TEXT NOT NULL, sample INTEGER NOT NULL DEFAULT 0
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS hire_search USING fts5(id UNINDEXED,role,skills,evidence,note);
    ''')
    return conn


def role_key(role):
    text=re.sub(r'\b(intern|internship|trainee|junior|senior|lead|graduate|entry.level)\b','',role,flags=re.I)
    return ' '.join(re.findall(r'[a-z0-9]+',text.lower()))


def infer_category(job):
    title=job.get('role','')
    if re.search(r'\bintern|trainee',title,re.I):return 'Intern'
    if re.search(r'graduate|junior|entry',title,re.I):return 'Graduate'
    if re.search(r'senior|lead|head',title,re.I):return 'Senior'
    return 'Experienced'


def public_record(row):
    item=dict(row)
    item.pop('signature',None);item.pop('role_key',None)
    item['skills']=json.loads(item['skills'])
    item['evidence']=json.loads(item['evidence'])
    item['sample']=bool(item['sample'])
    return item


def list_hires(category='',role=''):
    with database() as conn:
        rows=conn.execute('SELECT * FROM hires ORDER BY saved_at DESC').fetchall()
    result=[public_record(r) for r in rows if (not category or r['category']==category) and (not role or role.lower() in r['role'].lower())]
    return result


def clean_evidence(text,name=''):
    if re.search(r'\b(gender|sex|marital|religion|caste|nationality|age|born|female|male|married|unmarried|young|older|family|mother|father|pregnant|disability|photo)\b|@|https?://',text,re.I):return ''
    for part in name.split():
        if len(part)>2:text=re.sub(r'\b'+re.escape(part)+r'\b','[name removed]',text,flags=re.I)
    text=re.sub(r'(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)','[contact removed]',text)
    return text[:600]


def save_hire(candidate,job,weights,category,note):
    if category not in CATEGORIES:raise ValueError('Choose a role level for this hire.')
    if not note.strip():raise ValueError('Add a short work-related reason for this hire.')
    if not clean_evidence(note):raise ValueError('Keep the hiring note about work and skills, then try again.')
    result=assess(candidate,job,weights)
    evidence=[dict(skill=e['skill'],quote=clean_evidence(e['quote'],candidate['name']),kind=e['kind']) for e in result['evidence'] if e['quote']]
    evidence=[e for e in evidence if e['quote']]
    if not evidence:raise ValueError('There is no clear work or course evidence to save yet. Check this CV first.')
    skills=list(dict.fromkeys(e['skill'] for e in evidence))
    note=clean_evidence(note,candidate['name'])
    signature=hashlib.sha256((role_key(job['role'])+category+json.dumps(evidence,sort_keys=True)).encode()).hexdigest()
    item=dict(id='H-'+secrets.token_hex(3).upper(),signature=signature,role=job['role'],role_key=role_key(job['role']),category=category,skills=json.dumps(skills),evidence=json.dumps(evidence),note=note,outcome='Not checked yet',saved_at=datetime.now(timezone.utc).isoformat(),sample=0)
    with database() as conn:
        old=conn.execute('SELECT * FROM hires WHERE signature=?',(signature,)).fetchone()
        if old:return public_record(old),False
        insert_record(conn,item)
    return public_record(item),True


def insert_record(conn,item):
    conn.execute('INSERT INTO hires VALUES (:id,:signature,:role,:role_key,:category,:skills,:evidence,:note,:outcome,:saved_at,:sample)',item)
    conn.execute('INSERT INTO hire_search(id,role,skills,evidence,note) VALUES (?,?,?,?,?)',(item['id'],item['role'],item['skills'],item['evidence'],item['note']))


def retrieve(job,category,candidate=None,limit=3):
    # Hard role/level boundaries stop senior hires becoming an internship benchmark.
    terms=list(dict.fromkeys(re.findall(r'[a-zA-Z0-9]+',' '.join(job['must']))))
    if not terms:return []
    expression=' OR '.join('"'+t+'"' for t in terms[:30])
    with database() as conn:
        rows=conn.execute('''SELECT h.*,bm25(hire_search) AS relevance FROM hire_search
          JOIN hires h ON h.id=hire_search.id WHERE hire_search MATCH ?
          AND h.role_key=? AND h.category=? AND h.outcome != 'Needs follow-up'
          ORDER BY relevance ASC,h.saved_at DESC LIMIT 30''',(expression,role_key(job['role']),category)).fetchall()
    candidate_skills=set()
    if candidate:
        result=assess(candidate,job,dict(skills=100,experience=0,domain=0,education=0))
        candidate_skills={e['skill'].casefold() for e in result['evidence'] if e['quote']}
    result=[]
    for row in rows:
        item=public_record(row)
        saved_skills={s.casefold() for s in item['skills']}
        related=[s for s in job['must'] if s.casefold() in saved_skills]
        shared=[s for s in related if not candidate or s.casefold() in candidate_skills]
        if not shared:continue
        item['shared']=shared
        item['references']=[dict(skill=e['skill'],quote=e['quote'],kind=e['kind']) for e in item['evidence'] if e['skill'].casefold() in {s.casefold() for s in shared}]
        item['similarity']=round(100*len(shared)/max(1,len(job['must'])))
        result.append(item)
    return sorted(result,key=lambda x:(-x['similarity'],x['outcome']!='Doing well'))[:limit]


def memory_context(job,category,candidate=None):
    sources=retrieve(job,category,candidate)
    common=list(dict.fromkeys(skill for source in sources for skill in source['shared']))
    if not sources:
        return dict(sources=[],summary='No comparable hires saved for this role and level yet.',skills=[],questions=[])
    return dict(sources=sources,summary=f'{len(sources)} comparable hire'+('s' if len(sources)!=1 else '')+' with evidence of '+', '.join(common[:4])+'.',skills=common,questions=[f'Can you show a recent example of using {s} and explain what you checked?' for s in common[:2]])


def update_outcome(hid,outcome):
    if outcome not in OUTCOMES:raise ValueError('Choose one of the listed follow-up results.')
    with database() as conn:
        changed=conn.execute('UPDATE hires SET outcome=? WHERE id=?',(outcome,hid)).rowcount
    return bool(changed)


def remove_hire(hid):
    with database() as conn:
        conn.execute('DELETE FROM hire_search WHERE id=?',(hid,))
        return bool(conn.execute('DELETE FROM hires WHERE id=?',(hid,)).rowcount)


def seed_examples():
    fixtures=[('EX-A1','Data Analyst','Experienced',['SQL','Python','Excel'],[
      ('SQL','Built SQL reports for weekly order and refund checks.'),('Python','Used Python to combine daily sales files and check missing records.'),('Excel','Used Excel to reconcile monthly revenue totals.')]),
      ('EX-A2','Data Analyst','Experienced',['SQL','Power BI'],[('SQL','Wrote SQL reports for repeat purchase and retention reviews.'),('Power BI','Built Power BI dashboards with clear definitions for the operations team.')]),
      ('EX-I1','Data Analyst Intern','Intern',['SQL','Excel'],[('SQL','Completed a SQL practice project with documented checks for missing values.'),('Excel','Built an Excel report for a supervised sales analysis exercise.')]),
      ('EX-E1','Software Engineer','Experienced',['Java','React'],[('Java','Built Java services with documented tests for payment calculations.'),('React','Built React forms with keyboard support and clear error messages.')])]
    with database() as conn:
        for hid,role,category,skills,evidence in fixtures:
            if conn.execute('SELECT 1 FROM hires WHERE id=?',(hid,)).fetchone():continue
            item=dict(id=hid,signature=hid,role=role,role_key=role_key(role),category=category,skills=json.dumps(skills),evidence=json.dumps([dict(skill=s,quote=q,kind='Course evidence only' if category=='Intern' else 'Work evidence') for s,q in evidence]),note='Fictional example for testing the saved-hire comparison.',outcome='Not checked yet',saved_at=datetime.now(timezone.utc).isoformat(),sample=1)
            insert_record(conn,item)
    return list_hires()
