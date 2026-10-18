"""Turn a sourcing brief into editable, literal search terms without a remote service."""
import re

ROLES=[
    'Data Analyst','Reporting Analyst','Insights Analyst','Business Analyst','Product Analyst','Financial Analyst','Supply Chain Analyst',
    'Data Scientist','Data Engineer','Analytics Engineer','BI Developer','Machine Learning Engineer','AI Engineer','MLOps Engineer',
    'Software Engineer','Software Developer','Backend Developer','Backend Engineer','Frontend Developer','Frontend Engineer',
    'Full Stack Developer','Full Stack Engineer','React Developer','Python Developer','Java Developer','Node.js Developer','.NET Developer',
    'DevOps Engineer','Cloud Engineer','Site Reliability Engineer','Security Analyst','Cybersecurity Analyst','Database Administrator',
    'QA Engineer','QA Analyst','Automation Tester','Manual Tester','Technical Support Engineer','Support Engineer',
    'Product Designer','UX Designer','UI Designer','UI/UX Designer','Graphic Designer','UX Researcher',
    'Recruiter','Recruitment Specialist','Talent Acquisition Specialist','Talent Acquisition Intern','Recruitment Intern',
    'HR Intern','HR Generalist','HR Manager','Product Manager','Project Manager','Program Manager',
    'Customer Success Manager','Customer Support Associate','Account Manager','Business Development Executive','Sales Executive','Sales Manager',
    'Marketing Manager','Digital Marketing Specialist','Content Writer','Copywriter','SEO Specialist','Accountant','Finance Manager',
    'Operations Manager','Administrative Assistant','Receptionist','Teacher','Research Assistant','Mechanical Engineer','Civil Engineer','Electrical Engineer',
]
SKILLS=[
    'SQL','Python','Excel','Power BI','Tableau','A/B testing','Statistics','R','Pandas','NumPy','Spark','Snowflake','dbt',
    'JavaScript','TypeScript','React','Next.js','Vue','Angular','HTML','CSS','Node.js','Express','Java','Spring Boot',
    'C++','C#','.NET','Go','Rust','Django','Flask','FastAPI','Ruby','Ruby on Rails','PHP','Laravel','Swift','Kotlin','Flutter',
    'AWS','Azure','Google Cloud','Docker','Kubernetes','Terraform','Linux','Git','CI/CD','PostgreSQL','MySQL','MongoDB','Redis',
    'Machine Learning','Deep Learning','PyTorch','TensorFlow','Computer Vision','NLP','OpenCV','CUDA','Scikit-learn',
    'Figma','Sketch','User Research','Prototyping','Interaction Design','Accessibility',
    'Recruitment','Sourcing','Interviewing','Communication','Stakeholder Management','Salesforce','HubSpot',
    'Accounting','Bookkeeping','Tally','SAP','Financial Reporting','Budgeting','Project Management','Agile','Scrum','Jira',
    'Customer Support','Sales','SEO','Content Writing','Digital Marketing','Google Analytics','Supply Chain','AutoCAD','SolidWorks',
]
ALIASES={'js':'JavaScript','ts':'TypeScript','nodejs':'Node.js','node js':'Node.js','reactjs':'React','react.js':'React','nextjs':'Next.js','k8s':'Kubernetes','powerbi':'Power BI','gcp':'Google Cloud','postgres':'PostgreSQL','golang':'Go','dotnet':'.NET'}
ROLE_ALIASES={'front-end developer':'Frontend Developer','front end developer':'Frontend Developer','back-end developer':'Backend Developer','back end developer':'Backend Developer','full-stack developer':'Full Stack Developer','fullstack developer':'Full Stack Developer','nodejs developer':'Node.js Developer','node js developer':'Node.js Developer'}
LOCATIONS=['Bengaluru','Bangalore','Mumbai','Delhi','New Delhi','Pune','Hyderabad','Chennai','Kochi','Kolkata','Ahmedabad','Gurugram','Gurgaon','Noida','London','Singapore','Berlin','Zurich','New York','San Francisco','Remote']


def clean(value):
    return re.sub(r'[\x00-\x1f"“”]','',value).strip(' ,.;:')[:100]


def unique(values,limit):
    result=[];seen=set()
    for value in values:
        value=clean(value)
        if value and value.casefold() not in seen:result.append(value);seen.add(value.casefold())
    return result[:limit]


def term_pattern(term):
    return r'(?<![\w+#])'+re.escape(term).replace(r'\ ',r'[\s-]+')+r'(?![\w+#])'


def split_terms(value):
    return [clean(t) for t in re.split(r'\s*(?:,|\band\b|\bor\b|\n)\s*',value,flags=re.I) if clean(t)]


def catalogue_matches(text,terms,aliases=None):
    hits=[]
    for term in terms:
        for match in re.finditer(term_pattern(term),text,re.I):hits.append((match.start(),match.end(),term))
    for alias,term in (aliases or {}).items():
        for match in re.finditer(term_pattern(alias),text,re.I):hits.append((match.start(),match.end(),term))
    selected=[]
    for start,end,term in sorted(hits,key=lambda x:(x[0],-(x[1]-x[0]))):
        if any(start<other_end and end>other_start for other_start,other_end,_ in selected):continue
        selected.append((start,end,term))
    return selected


def generate_settings(text,job):
    text=text.strip()
    if len(text)<8:raise ValueError('Describe the role or skills you want to find.')
    fields={m.group(1).lower():m.group(2).strip() for m in re.finditer(r'(?:^|[;\n])\s*(role|roles|title|titles|job title|job titles|skills|location|experience|exclude|match)\s*:\s*([^;\n]+)',text,re.I)}
    exclusions=[];masked=text
    for match in list(re.finditer(r'\b(?:exclude|excluding|without|except|not|no)\s+([^.;\n]+)',text,re.I)):
        phrase=re.split(r'\b(?:with|based in|located in)\b',match[1],maxsplit=1,flags=re.I)[0]
        exclusions.extend(split_terms(phrase))
        end=match.start(1)+len(phrase)
        masked=masked[:match.start()]+' '*(end-match.start())+masked[end:]
    if fields.get('exclude'):exclusions.extend(split_terms(fields['exclude']))
    exclusions=unique(exclusions,12)
    excluded={v.casefold() for v in exclusions}
    internship=bool(excluded&{'intern','interns','internship','internships'})
    exclusions=[v for v in exclusions if v.casefold() not in {'intern','interns','internship','internships'}]
    # Labelled sections and a "with …" clause let people use terms outside the catalogue.
    explicit_title=next((fields[k] for k in ['role','roles','title','titles','job title','job titles'] if fields.get(k)),'')
    roles=split_terms(explicit_title) if explicit_title else []
    if not roles:
        for start,end,role in catalogue_matches(masked,ROLES,ROLE_ALIASES):
            before=masked[max(0,start-24):start]
            seniority=re.search(r'\b(senior|junior|lead|principal|staff|graduate)\s+$',before,re.I)
            if seniority and not role.lower().startswith(seniority[1].lower()+' '):role=seniority[1].title()+' '+role
            after=masked[end:]
            level=re.match(r'\s+(intern|trainee|graduate)\b',after,re.I)
            if level and not re.search(r'\b'+level[1]+r'\b',role,re.I):role+=' '+level[1].title()
            roles.append(role)
    if not roles:
        leading=re.sub(r'^\s*(?:please\s+)?(?:(?:i(?:\s+am|\'m)?\s+)?(?:am\s+)?looking for|i need|find|search for|hire|hiring|need|want)\s+(?:me\s+)?(?:an?\s+)?','',masked,flags=re.I)
        candidate=re.split(r'\s+(?:with|using|in|based|who|having|skilled)\b|[,;\n.]',leading,maxsplit=1,flags=re.I)[0].strip()
        if candidate and len(candidate.split())<=9 and not re.search(r'\b(?:candidates?|people|profiles?|someone|skills?|any|all)\b',candidate,re.I):
            if re.search(r'\b(?:engineer|developer|specialist|analyst|manager|designer|consultant|architect|intern|scientist|writer|tester|associate|technician|coordinator|assistant|officer|teacher|nurse|recruiter|accountant)\b',candidate,re.I):roles=[candidate]
    notes=[]
    if not roles:
        roles=[job['role']];notes.append('Used the current job title. You can replace it below.')
    roles=unique(roles,8)
    skill_terms=[term for _,_,term in catalogue_matches(masked,SKILLS,ALIASES)]
    clauses=[fields['skills']] if fields.get('skills') else [m[1] for m in re.finditer(r'\b(?:with|using|skilled in|skills include|skills are|knowledge of|must have)\s+(.+?)(?=[;\n.]\s|;|\n|$)',masked,re.I)]
    for clause in clauses:
        clause=re.split(r'\s+(?:based in|located in|for \d|with \d|match (?:any|all))\b|\s+in\s+(?=[A-Z])',clause,maxsplit=1)[0]
        for item in split_terms(clause):
            item=re.sub(r'^(?:any of|all of|strong|solid|hands-on|experience in|knowledge of|proficiency in)\s+','',item,flags=re.I).strip()
            item=re.sub(r'\s+(?:skills?|experience|knowledge)$','',item,flags=re.I).strip()
            if not item or re.search(r'\b(?:years?|months?|match|remote|hybrid|on.site)\b|^\d',item,re.I):continue
            exact=next((term for term in SKILLS if term.casefold()==item.casefold()),ALIASES.get(item.casefold(),item))
            skill_terms.append(exact)
    skills=unique([s for s in skill_terms if s.casefold() not in excluded],12)
    if not skills:notes.append('No skills were identified. Add the skills you want below.')
    location=clean(fields.get('location',''))
    if not location:
        locations=catalogue_matches(masked,LOCATIONS)
        if locations:location=locations[0][2]
        else:
            place=re.search(r'\b(?:based in|located in|in)\s+([A-Za-z][A-Za-z .-]{1,70}?)(?=\s+(?:with|using|who|having|and|for|match)\b|[,;\n]|$)',masked,re.I)
            if place:location=clean(place[1])
    years=re.search(r'(\d{1,2})\s*(?:to|[-–])\s*(\d{1,2})\s*years?',masked,re.I)
    minimum=re.search(r'(\d{1,2})\s*\+?\s*years?',masked,re.I)
    experience=clean(fields.get('experience',''))
    if not experience and years:experience=f'{years[1]} to {years[2]} years'
    elif not experience and minimum:experience=f'{minimum[1]}+ years'
    if re.search(r'\b(?:intern|internship|graduate|fresher)\b',' '.join(roles),re.I):internship=False
    breadth='wider' if re.search(r'\b(?:match any|any skill|any selected|any of|either|at least one)\b',text,re.I) or fields.get('match','').lower()=='any' else 'focused'
    settings=dict(titles=roles,skills=skills,breadth=breadth,exclude_internships=internship,location=location or 'Not shared',experience=experience or 'Not shared')
    if exclusions:settings['exclude_terms']=exclusions
    notes.append('Check the titles, skills and filters before using this search.')
    return settings,notes
