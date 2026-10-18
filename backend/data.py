"""Only fictional candidates. Evidence is deliberately varied and imperfect."""
SAMPLE_JOB = '''Data Analyst
Grove & Grain, a fictional consumer commerce company
Bengaluru | Hybrid, 3 days in office
Experience: 3 to 5 years
Must-have skills: SQL, Python, Excel, Power BI
Nice-to-have skills: Tableau, A/B testing
Domain: e-commerce
Education: Any degree or equivalent practical experience
You will turn shopping and retention data into useful decisions. Build clear dashboards,
investigate changes in conversion and explain findings to colleagues.
We are looking for a rockstar who can own weekly reporting.
'''

CANDIDATES = [
    dict(id='c1', name='Ananya Rao', filename='Ananya_Rao.pdf', layout='clean', text='''Ananya Rao
Experience: 4 years
WORK EXPERIENCE
Data Analyst | Tamarind Cart | 2022 to 2026
Built SQL reports for e-commerce orders and reduced reconciliation time by 35%.
Automated weekly reporting with Python, saving 6 hours per week.
Built Power BI dashboards used by 12 category managers.
Used Excel to check revenue figures against finance records.
Ran an A/B testing experiment on the checkout page with a 4% conversion lift.
EDUCATION
BSc Statistics, 2021
PREFERENCES
Pay: 16 to 20 lakh per year
Location: Bengaluru
Work style: Hybrid
Deal-breakers: Regular weekend work
'''),
    dict(id='c2', name='Kabir Siddiqui', filename='Kabir_Siddiqui.docx', layout='compact', text='''Kabir Siddiqui
Experience: 5 years
WORK EXPERIENCE
Business Analyst | Cedar Basket | 2021 to 2026
Built SQL dashboards to monitor e-commerce delivery and repeat purchases.
Designed Power BI reporting for 18 operations colleagues.
Used Excel to investigate missing delivery payments.
Developed Tableau dashboards for regional leads.
EDUCATION
BCom, 2020
PREFERENCES
Pay: 18 to 23 lakh per year
Location: Bengaluru
Work style: Hybrid
Deal-breakers: Relocation outside Bengaluru
'''),
    dict(id='c3', name='Meera Nair', filename='Meera_Nair.pdf', layout='gap', text='''Meera Nair
Experience: 3.5 years
WORK EXPERIENCE
Reporting Analyst | Silt & Seed | 2020 to 2022 and 2024 to 2026
Wrote SQL reports for e-commerce subscription retention.
Used Python to clean weekly subscription payment records.
Built Excel reports and explained findings to the support team.
Career break, 2022 to 2024. Available for full-time work.
EDUCATION
BA Economics, 2019
PREFERENCES
Pay: 14 to 18 lakh per year
Location: Kochi
Work style: Remote
Deal-breakers: Mandatory office attendance
'''),
    dict(id='c4', name='Rohan Deshmukh', filename='Rohan_Deshmukh.docx', layout='messy', text='''Rohan Deshmukh
Experience: 2.5 years
WORK EXPERIENCE
Junior Analyst | Flint Orchard | 2023 to 2026
Used SQL to check e-commerce inventory and purchase records.
Built Excel dashbaords for the warehouse team.
Created Tableau charts for monthly inventory reviews.
Built Python scripts to combine daily sales files.
EDUCATION
Diploma in Business Analytics, 2023
PREFERENCES
Pay: 11 to 15 lakh per year
Location: Pune
Work style: Hybrid
Deal-breakers: Night shifts
'''),
    dict(id='c5', name='Zoya Fernandes', filename='Zoya_Fernandes.pdf', layout='clean', text='''Zoya Fernandes
Experience: 4 years
WORK EXPERIENCE
Operations Analyst | Elm Healthworks | 2022 to 2026
Built Excel reports to track clinic appointment utilisation.
Designed Power BI dashboards for hospital operations teams.
Explained weekly findings to clinic managers.
EDUCATION
BSc Mathematics, 2021
PREFERENCES
Pay: 13 to 17 lakh per year
Location: Bengaluru
Work style: On-site
Deal-breakers: Frequent travel
'''),
    dict(id='c6', name='Dev Patel', filename='Dev_Patel.docx', layout='compact', text='''Dev Patel
Experience: 1 year
WORK EXPERIENCE
Customer Support Associate | Cove Retail | 2025 to 2026
Resolved customer delivery complaints and maintained order notes.
COURSES AND PRACTICE
Completed a course in SQL, Python, Excel, Power BI and Tableau.
Practised A/B testing with a classroom e-commerce dataset.
No professional analytics work yet.
EDUCATION
BBA, 2024
PREFERENCES
Pay: 8 to 11 lakh per year
Location: Bengaluru
Work style: Hybrid
Deal-breakers: None shared
'''),
]

MARKET = [
    dict(id='m1',company='Razorpay',experience='3–5 years · Estimate',pay='₹14–22 lakh · Estimate',low=14,high=22,location='Bengaluru · Estimate',url='https://razorpay.com/jobs/',status='Illustrative example. Current opening not confirmed.'),
    dict(id='m2',company='Meesho',experience='2–5 years · Estimate',pay='₹12–20 lakh · Estimate',low=12,high=20,location='Bengaluru · Estimate',url='https://www.meesho.io/jobs',status='Illustrative example. Current opening not confirmed.'),
    dict(id='m3',company='Freshworks',experience='3–6 years · Estimate',pay='₹15–24 lakh · Estimate',low=15,high=24,location='Chennai / Bengaluru · Estimate',url='https://www.freshworks.com/company/careers/',status='Illustrative example. Current opening not confirmed.'),
]
