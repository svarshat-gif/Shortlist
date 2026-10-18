"""Inspectable evidence scoring. Identity and preferences never enter the scorer."""
import re
from copy import deepcopy

SKILLS = ['SQL', 'Python', 'Excel', 'Power BI', 'Tableau', 'A/B testing', 'JavaScript', 'React', 'Java', 'Figma', 'Salesforce', 'Recruitment', 'Communication', 'Accounting', 'AWS', 'Kubernetes']
DEFAULT_WEIGHTS = dict(skills=50, experience=25, domain=20, education=5)


def has_skill(skill, line):
    return bool(re.search(r'(?<!\w)' + re.escape(skill) + r'(?!\w)', line, re.I))


def job_from_text(text):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if len(text.strip()) < 40:
        raise ValueError('There is not enough detail to read the role. Add a title, skills and responsibilities, then try again.')
    must_line = next((x for x in lines if re.match(r'must.have|key skills|required skills', x, re.I)), '')
    nice_line = next((x for x in lines if re.match(r'nice.to.have|preferred skills', x, re.I)), '')
    must = [s for s in SKILLS if has_skill(s, must_line or text) and not (nice_line and has_skill(s, nice_line) and not has_skill(s, must_line or text.replace(nice_line,'')))]
    nice = [s for s in SKILLS if has_skill(s, nice_line) and s not in must]
    exp = re.search(r'(\d+)\s*(?:to|[-–])\s*(\d+)\s*years', text, re.I)
    loc = next((s for s in ['Bengaluru','Bangalore','Mumbai','Delhi','Pune','Hyderabad','Chennai','Remote','Kochi'] if re.search(r'\b'+s+r'\b',text,re.I)), 'Not shared')
    domain = re.search(r'^Domain:\s*(.+)',text,re.M|re.I)
    salary = re.search(r'(?:pay|salary):\s*(.+)', text, re.I)
    flags = []
    if not salary:
        flags.append(dict(id='salary',text='No salary range shared',fix='Add ₹16–22 lakh per year',replacement='Salary: 16 to 22 lakh per year'))
    if re.search('rockstar|ninja|guru',text,re.I):
        flags.append(dict(id='vague',text='“Rockstar” is hard to measure',fix='Use “analyst”',replacement='analyst'))
    if re.search(r'young|digital native|manpower|male only|female only',text,re.I):
        flags.append(dict(id='inclusive',text='Some wording may put people off applying',fix='Use inclusive wording',replacement='colleague'))
    if exp and int(exp[1]) >= 8 and re.search('junior|analyst|entry',text,re.I):
        flags.append(dict(id='years',text='The experience asked for is unusually high for this role',fix='Ask for 3 to 5 years',replacement='3 to 5 years'))
    return dict(text=text,role=lines[0][:100],must=must,nice=nice,experience=f'{exp[1]} to {exp[2]} years' if exp else 'Not shared',years_min=int(exp[1]) if exp else 0,location=loc,domain=domain[1].strip() if domain else '',education='Any degree or equivalent practical experience' if 'equivalent' in text.lower() else 'Review the job description',pay=salary[1].strip() if salary else 'Not shared',flags=flags)


def scoring_document(text):
    """Allow only occupational sections; unknown layouts are flagged for human review."""
    sections = dict(work=[],course=[],education=[])
    section = None
    for line in text.splitlines():
        line=line.strip()
        if not line:
            continue
        if re.match(r'^(work experience|professional experience|employment|work history|experience)$',line,re.I): section='work'; continue
        if re.match(r'^(courses?[^:]*|certifications?|projects|training|skills)$',line,re.I): section='course'; continue
        if re.match(r'^education$',line,re.I): section='education'; continue
        if re.match(r'^(preferences|personal|contact|profile|interests|references|career break)',line,re.I): section=None; continue
        if re.search(r'@|https?://|\b(?:name|gender|sex|age|marital|dob|born|nationality|religion|phone|address)\s*:',line,re.I): continue
        if re.search(r'\b(?:married|unmarried|male|female|he/him|she/her|years old)\b',line,re.I): continue
        if section:
            sections[section].append(line)
    return sections


def work_years(lines):
    years = set()
    for line in lines:
        if '|' not in line: continue
        for a,b in re.findall(r'\b(20\d\d)\s*(?:to|[-–])\s*(20\d\d)\b',line):
            years.update(range(int(a),min(int(b),int(a)+40)))
    return len(years)


def assess(candidate, job, weights):
    doc = scoring_document(candidate['text'])
    evidence=[]; matched=[]; missing=[]; credit=0
    for skill in job['must']:
        work=[x for x in doc['work'] if has_skill(skill,x) and not re.search(r'no\b|no professional',x,re.I)]
        study=[x for x in doc['course'] if has_skill(skill,x)]
        if work:
            matched.append(skill)
            # Specific outcomes strengthen evidence; a bare skill list never earns full credit.
            credit+=min(0.96,0.84+(0.08 if any(re.search(r'\d',x) for x in work) else 0)+(0.04 if len(work)>1 else 0))
            evidence.append(dict(skill=skill,quote=work[0],kind='Work evidence'))
        elif study:
            credit+=0.2; missing.append(skill)
            evidence.append(dict(skill=skill,quote=study[0],kind='Course evidence only'))
        else:
            missing.append(skill); evidence.append(dict(skill=skill,quote='',kind='No clear evidence found'))
    years=work_years(doc['work'])
    domain_lines=[x for x in doc['work'] if job.get('domain') and job['domain'].lower() in x.lower()]
    education=bool(doc['education'])
    breakdown=dict(skills=round(credit/max(len(job['must']),1)*100),experience=min(100,round(years/max(job['years_min']+1.75,1)*100)) if job['years_min'] else 0,domain=(94 if any(re.search(r'\d',x) for x in domain_lines) else 86) if domain_lines else 0,education=75 if education else 0)
    total=sum(weights.values()) or 1
    score=round(sum(breakdown[k]*weights[k] for k in weights)/total)
    strength=f"Work evidence supports {', '.join(matched[:3])}." if matched else 'The listed skills come from a course, with no clear work evidence yet.'
    gap=f" Confirm {', '.join(missing[:2])} on a call." if missing else ' The main skills are supported by examples of work.'
    confidence='High' if len(matched)>=3 else 'Medium' if matched else 'Low'
    prefs={}
    for field,label in [('pay','Pay'),('location','Location'),('style','Work style'),('dealbreakers','Deal-breakers')]:
        m=re.search(r'^'+label+r':\s*(.+)',candidate['text'],re.M|re.I)
        prefs[field]=m[1] if m else 'Not shared'
    return dict(**{k:candidate[k] for k in ['id','name','filename']},score=score,suggested_score=score,breakdown=breakdown,matched=matched,missing=missing,evidence=evidence,years=years,reason=strength+gap,confidence=confidence,preferences=prefs,domain_evidence=domain_lines,education_evidence=doc['education'],reading_warning='' if doc['work'] else 'Work history headings were not clear. Please review this CV before using the score.')


def ranked(state):
    result=[]
    for candidate in state['candidates']:
        row=assess(candidate,state['job'],state['weights'])
        override=state['overrides'].get(candidate['id'],{})
        row.update(override)
        # Recruiter-added skills remain reviewable; an edit cannot manufacture proof.
        existing={x['skill'] for x in row['evidence']}
        sections=scoring_document(candidate['text'])
        for skill in row['matched']:
            if skill in existing: continue
            work=[x for x in sections['work'] if has_skill(skill,x)]
            row['evidence'].append(dict(skill=skill,quote=work[0] if work else '',kind='Work evidence' if work else 'No clear evidence found'))
        row['selected']=candidate['id'] in state['selected']
        row['record']=deepcopy(state['records'].get(candidate['id'],[]))
        result.append(row)
    return sorted(result,key=lambda x:(-x['score'],x['id']))


def questions(job,difficulty='standard',short=False):
    skills=job['must'] or ['the core skill in this role']
    s=skills[0]; t=skills[1] if len(skills)>1 else s
    items=[
        ('Technical',f'How would you use {s} to investigate an unexpected drop in a weekly result?',f'Checks the definitions and data quality before using {s} to compare periods.',f'Write out your approach to using {s}.','Structured investigation'),
        ('Technical',f'Walk me through a piece of work where you used {t}.',f'Explains the problem, the specific use of {t} and how the result was checked.', 'Share a written walkthrough or an annotated work sample.',f'Practical use of {t}'),
        ('Technical','How would you check that a report is accurate?','Reconciles totals, checks missing values and asks a colleague to review assumptions.','Send a short checklist before the call.','Quality checks'),
        ('Technical','How would you explain a surprising finding to a colleague?','Uses a clear example, states uncertainty and connects the finding to a decision.','Send a short written explanation or a simple chart.','Clear communication'),
        ('Experience','Tell me about work that changed a decision.','Describes their own contribution, evidence and a measurable result.','Take extra thinking time and use written notes.','Ownership and impact'),
        ('Experience','Describe a time you found a mistake in your work.','Explains how they spotted it, corrected it and prevented a repeat.','Write a brief example instead of speaking.','Accountability'),
        ('Experience','How did you manage two competing requests?','Makes trade-offs explicit and agrees priorities with the people involved.','Use a written timeline or bullet points.','Prioritisation'),
        ('Fit',f'What would help you do your best work as a {job["role"]}?','Describes working conditions and support needs related to the work.','Share preferences in writing before the call.','Working arrangements'),
        ('Fit','Which part of this role would you like to learn more about?','Connects a learning goal to a responsibility in the job.','Send a written response after the call.','Learning priorities'),
        ('Fit','What would you want to agree on before joining?','Discusses role expectations, pay, location and ways of working.','Answer by email or take more time to consider.','Mutual expectations'),
    ]
    brief=[f'How would you check a change using {s}?',f'Where have you used {t} at work?','How do you check a report?','How do you explain a finding?','What decision did your work change?','How did you fix a work mistake?','How do you choose what comes first?','What helps you work well?','What would you like to learn?','What should we agree before joining?']
    return [dict(id=i+1,group=g,question=(brief[i] if short else q)+(' What trade-off would you make?' if difficulty=='harder' else ''),good=a+(' Ask for a trade-off and a second possible approach.' if difficulty=='harder' else ' A small, everyday example is enough.' if difficulty=='easier' else ''),accessible=b,skill=c,time='About 30 seconds each' if short else 'About 1 minute each') for i,(g,q,a,b,c) in enumerate(items)]


def search_strings(job,options=None,category='Experienced'):
    def clean(value):
        return re.sub(r'[\x00-\x1f"“”]', '', value).strip()[:100]
    role=clean(job['role'])
    junior=category in ('Intern','Graduate') or bool(re.search(r'\bintern|internship|graduate|entry.level',role,re.I))
    if re.search('analyst|analytics',role,re.I): titles=['Reporting Analyst','Insights Analyst','Business Analyst','Analytics Specialist']
    elif re.search('engineer|developer',role,re.I): titles=['Software Developer','Application Developer','Software Engineer','Development Engineer']
    elif re.search('recruit|talent|hiring',role,re.I): titles=['Recruiter','Talent Acquisition Specialist','Talent Partner','Recruitment Associate']
    elif re.search('design',role,re.I): titles=['UX Designer','Product Designer','UI Designer','Interaction Designer']
    else: titles=[role+' Specialist',role+' Associate']
    if junior:
        # Keep the level explicit, rather than adding senior roles or excluding interns.
        suffix='Intern' if category=='Intern' or re.search('intern',role,re.I) else 'Graduate'
        titles=[title if suffix.lower() in title.lower() else title+' '+suffix for title in titles]
    defaults=dict(titles=list(dict.fromkeys([role,*titles]))[:3],skills=job['must'][:3],breadth='focused',exclude_internships=False)
    settings={**defaults,**(options or {})}
    settings['titles']=list(dict.fromkeys(clean(t) for t in settings['titles'] if clean(t)))[:8] or [role]
    settings['skills']=list(dict.fromkeys(clean(t) for t in settings['skills'] if clean(t)))[:12]
    if 'exclude_terms' in settings:settings['exclude_terms']=list(dict.fromkeys(clean(t) for t in settings['exclude_terms'] if clean(t)))[:12]
    for field in ('location','experience'):
        if field in settings:settings[field]=clean(settings[field]) or 'Not shared'
    selected=settings['titles'];skills=settings['skills']
    smart='('+' OR '.join('"'+t+'"' for t in selected)+')'
    if skills:
        smart+=(' AND ('+' OR '.join('"'+t+'"' for t in skills)+')') if settings['breadth']=='wider' else ''.join(' AND "'+t+'"' for t in skills)
    exclusions=list(dict.fromkeys([*settings.get('exclude_terms',[]),*(['intern','internship'] if settings['exclude_internships'] else [])]))
    if exclusions:smart+=' NOT ('+' OR '.join('"'+t+'"' for t in exclusions)+')'
    simple=' '.join([selected[0],*skills])
    return dict(naukri=dict(smart=smart,simple=simple),linkedin=dict(smart=smart,simple=simple),titles=titles,settings=settings,filters=dict(location=settings.get('location',job['location']),experience=settings.get('experience',job['experience'])),available_skills=list(dict.fromkeys(job['must']+job['nice'])))
