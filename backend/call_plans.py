"""Candidate-specific call plans grounded in occupational CV evidence."""
from .engine import assess,DEFAULT_WEIGHTS,scoring_document

CHECKS={
    'SQL':'Explain the joins and filters, reconcile totals, and check missing or duplicate records.',
    'Python':'Explain the inputs, error checks, repeatability and how the output was verified.',
    'Excel':'Explain the formulas or lookups, reconcile totals and check for broken references.',
    'Power BI':'Explain the source relationships, calculations and checks on refreshed totals.',
    'Tableau':'Explain the data preparation, chart choices and checks against the source figures.',
    'React':'Explain the component boundaries, interaction states and how the behaviour was tested.',
    'Java':'Explain the inputs, error cases, tests and the reason for the chosen approach.',
    'Recruitment':'Explain the role requirements, evidence checks and consistent candidate follow-up.',
    'Communication':'Show a clear explanation, check understanding and make uncertainty explicit.',
}


def candidate_questions(job,candidate,difficulty='standard',short=False,weights=None):
    result=assess(candidate,job,weights or DEFAULT_WEIGHTS)
    priority={'No clear evidence found':0,'Course evidence only':1,'Work evidence':2}
    evidence=sorted(result['evidence'],key=lambda e:priority[e['kind']])
    if not evidence:evidence=[dict(skill='the main responsibility',kind='No clear evidence found',quote='')]
    items=[]
    for i in range(4):
        item=evidence[i%len(evidence)];skill=item['skill'];kind=item['kind'];quote=item['quote']
        excerpt=quote if len(quote)<=160 else quote[:157].rsplit(' ',1)[0]+'…'
        if kind=='Work evidence':
            question=f'You mention “{excerpt}” How did you use {skill}, and how did you check the result?'
            concise=f'In your {skill} example, what did you do and check?'
            basis=f'Build on the work evidence for {skill}.'
        elif kind=='Course evidence only':
            question=f'Your {skill} example comes from study. How would you use it for a small task in this {job["role"]} role?'
            concise=f'How would you turn your {skill} study into a practical task?'
            basis=f'Check practical application of {skill}; the CV currently shows study.'
        else:
            question=f'{skill} matters for this role, but is not clear in your CV. How would you approach a first task using it?'
            concise=f'What would be your first steps with {skill}?'
            basis=f'Clarify {skill}. Missing evidence does not prove a missing skill.'
        # A narrow job can have fewer than four skills. Explore a different aspect on repeats.
        if i>=len(evidence):
            question=f'What could go wrong in that {skill} task, and how would you spot and fix it?'
            concise=f'How would you spot and fix a {skill} mistake?'
        items.append(dict(group='Technical',question=question,concise=concise,good=CHECKS.get(skill,f'Use a concrete {skill} task, explain the steps and describe a check on the result.'),accessible=f'Share a written walkthrough or annotated {skill} sample instead of a spoken answer.',skill=skill,basis=basis,quote=quote,focus_kind=kind))
    work=[line for line in scoring_document(candidate['text'])['work'] if '|' not in line]
    anchor=next((line for line in work if any(e['quote']==line for e in evidence)),work[0] if work else '')
    anchor_short=anchor if len(anchor)<=160 else anchor[:157].rsplit(' ',1)[0]+'…'
    practical=next((e['skill'] for e in evidence if e['kind']=='Work evidence'),evidence[0]['skill'])
    gap=next((e['skill'] for e in evidence if e['kind']!='Work evidence'),practical)
    experience=[
        (f'Your CV says “{anchor_short}” What was your own contribution, and what changed?' if anchor else f'Choose a project related to {practical}. What did you personally contribute?',f'What was your contribution to that {practical} example?','Explain the starting point, personal contribution, checks and outcome. A course or voluntary project is valid evidence to discuss.','Ownership and impact',anchor),
        (f'Describe a mistake or difficult check in your {practical} work or practice. How did you resolve it?',f'How did you fix a mistake while using {practical}?','Explain what signalled the problem, how it was fixed and what prevented a repeat.','Quality and accountability',next((e['quote'] for e in evidence if e['skill']==practical),'')),
        (f'If you had to deliver a {practical} task while learning {gap}, how would you agree priorities with your colleague?',f'How would you balance delivery with learning {gap}?','Make deadlines, support and trade-offs explicit. Ask for help where needed.','Prioritisation',''),
    ]
    for q,concise,good,skill,quote in experience:
        items.append(dict(group='Experience',question=q,concise=concise,good=good,accessible='Use written notes, a timeline or an example shared before the call.',skill=skill,basis='Follow up on this person’s work and learning evidence.',quote=quote,focus_kind='Experience'))
    fit=[
        (f'What support would help you use {practical} well in this {job["role"]} role?',f'What support would help you with {practical}?','Discuss practical support and ways of working without treating support needs as a score.','Working arrangements'),
        (f'What would you want to learn or demonstrate next in {gap}?',f'What would you like to develop in {gap}?','Connect a realistic learning goal to the role. Explain how progress could be demonstrated.','Learning priorities'),
        (f'This role lists {job["location"]} as its location. What role expectations, pay and working arrangements would you want to discuss?', 'What should we agree about pay, location and the role?','Confirm preferences openly. Do not assume suitability from personal circumstances.','Mutual expectations'),
    ]
    for q,concise,good,skill in fit:
        items.append(dict(group='Fit',question=q,concise=concise,good=good,accessible='Share preferences in writing, or take extra time before responding.',skill=skill,basis='Check mutual expectations for this role; this does not change the score.',quote='',focus_kind='Fit'))
    result=[]
    for i,item in enumerate(items,1):
        item=dict(item);concise=item.pop('concise')
        item['question']=(concise if short else item['question'])+(' What trade-off would you make, and why?' if difficulty=='harder' else '')
        item['good']+=(' Compare two approaches and discuss their limitations.' if difficulty=='harder' else ' A small example explained step by step is enough.' if difficulty=='easier' else '')
        result.append(dict(id=i,candidate_id=candidate['id'],candidate_name=candidate['name'],time='About 30 seconds each' if short else 'About 1 minute each',**item))
    return result
