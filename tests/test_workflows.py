from .conftest import auth, register


VENDOR={"company_name":"Test Staffing","country":"IN","city":"Noida","company_type":"Staffing Company"}
PARTNER={"country":"IN","city":"Bengaluru","industries":["IT"],"skill_areas":["Python"]}
CANDIDATE={"country":"IN","city":"Pune","current_title":"Developer","total_experience":3,"skills":["Python"],"country_specific_data":{"notice_period":"30 days"}}
REQ={"title":"Python Developer","description":"Build secure APIs for our recruitment platform and its partners.","country":"IN","state_region":"Karnataka","city":"Bengaluru","work_mode":"Hybrid","employment_type":"Full-Time","min_experience":2,"max_experience":5,"required_skills":["Python","FastAPI"],"preferred_skills":[],"openings":1,"currency":"INR","compensation_type":"Annual CTC","status":"active"}


def test_only_three_roles_and_role_route_security(client):
    bad=client.post('/api/auth/register',json={"name":"Recruiter","email":"r@example.com","password":"Password123!","role":"recruiter","profile":{}})
    assert bad.status_code==422
    candidate=register(client,'candidate','candidate@example.com',CANDIDATE)
    assert client.post('/api/requirements',headers=auth(candidate['access_token']),json=REQ).status_code==403


def test_partner_submission_vendor_status_and_idor(client):
    vendor=register(client,'requirement_vendor','vendor@example.com',VENDOR)
    other_vendor=register(client,'requirement_vendor','vendor2@example.com',{**VENDOR,"company_name":"Other"})
    partner=register(client,'sourcing_partner','partner@example.com',PARTNER)
    other_partner=register(client,'sourcing_partner','partner2@example.com',PARTNER)
    requirement=client.post('/api/requirements',headers=auth(vendor['access_token']),json=REQ).json()
    assert client.post(f"/api/partner/requirements/{requirement['id']}/start",headers=auth(partner['access_token'])).status_code==200
    candidate=client.post('/api/partner/candidates',headers=auth(partner['access_token']),json={"full_name":"Amit Sharma","email":"amit@example.com","phone":"1234567890","country":"IN","city":"Noida","current_title":"Python Developer","total_experience":3,"skills":["Python"],"country_specific_data":{"notice_period":"30 days"}}).json()
    files={"file":("resume.pdf",b"%PDF-1.4 test resume %%EOF","application/pdf")}
    assert client.post(f"/api/candidates/{candidate['id']}/resume",headers=auth(partner['access_token']),files=files).status_code==200
    submitted=client.post(f"/api/partner/requirements/{requirement['id']}/submit-candidate?candidate_id={candidate['id']}",headers=auth(partner['access_token']))
    assert submitted.status_code==201
    app_id=submitted.json()['id']
    assert submitted.json()['submission_source']=='sourcing_partner'
    assert submitted.json()['submitted_by']['id']==partner['user']['id']
    assert client.get(f"/api/partner/submissions/{app_id}",headers=auth(other_partner['access_token'])).status_code==404
    assert client.get(f"/api/vendor/submissions/{app_id}",headers=auth(other_vendor['access_token'])).status_code==404
    assert client.patch(f"/api/vendor/submissions/{app_id}/status",headers=auth(vendor['access_token']),json={"status":"shortlisted"}).status_code==200
    assert client.get('/api/partner/submissions',headers=auth(partner['access_token'])).json()[0]['status']=='shortlisted'
    duplicate=client.post(f"/api/partner/requirements/{requirement['id']}/submit-candidate?candidate_id={candidate['id']}",headers=auth(partner['access_token']))
    assert duplicate.status_code==409


def test_candidate_direct_application_and_resume_validation(client):
    vendor=register(client,'requirement_vendor','vendor@example.com',VENDOR)
    candidate=register(client,'candidate','candidate@example.com',CANDIDATE)
    requirement=client.post('/api/requirements',headers=auth(vendor['access_token']),json=REQ).json()
    profile=client.get('/api/candidate/profile',headers=auth(candidate['access_token'])).json()
    invalid=client.post(f"/api/candidates/{profile['id']}/resume",headers=auth(candidate['access_token']),files={"file":("bad.exe",b"bad","application/octet-stream")})
    assert invalid.status_code==422
    client.post(f"/api/candidates/{profile['id']}/resume",headers=auth(candidate['access_token']),files={"file":("resume.docx",b"PK test docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    applied=client.post(f"/api/candidate/jobs/{requirement['id']}/apply",headers=auth(candidate['access_token']))
    assert applied.status_code==201
    assert applied.json()['submission_source']=='candidate_self'
    other_candidate=register(client,'candidate','candidate2@example.com',CANDIDATE)
    assert client.get(f"/api/candidate/applications/{applied.json()['id']}",headers=auth(other_candidate['access_token'])).status_code==404
    assert client.post(f"/api/candidate/jobs/{requirement['id']}/apply",headers=auth(candidate['access_token'])).status_code==409


def test_country_configuration_is_not_cross_contaminated():
    source=open('app/static/app.js',encoding='utf-8').read()
    india=source[source.index("IN:{"):source.index("US:{")]
    assert 'work_authorization' not in india and 'H1B' not in india
    assert 'work_authorization' in source and 'H1B' in source
