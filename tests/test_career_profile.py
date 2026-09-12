from .conftest import auth, register
from .test_marketplace_mvp import CANDIDATE_ACCOUNT


def test_career_sections_round_trip_and_remove(client):
    account = register(client, "candidate", "career@example.com", CANDIDATE_ACCOUNT)
    headers = auth(account["access_token"])
    profile = client.get('/api/candidate/profile', headers=headers).json()
    data = {**profile['country_specific_data'],
            'education_history': [{'qualification': 'Graduation', 'institution_name': 'University',
                                   'course': 'BTech', 'specialization': 'Computer Science', 'end_year': '2020'}],
            'work_experiences': [{'company_name': 'Example', 'job_title': 'Engineer',
                                  'start_date': '2020-01-01', 'is_current': True}],
            'projects': [{'title': 'Recruitment platform', 'description': 'Built APIs'}],
            'it_skills': [{'name': 'Python', 'experience_years': '4'}],
            'accomplishments': [{'type': 'Certification', 'title': 'Cloud engineer'}],
            'languages': [{'language': 'Hindi', 'abilities': 'Read, write and speak'}],
            'industry': 'Software Product', 'preferred_shift': 'Flexible', 'resume_headline': 'Backend engineer'}
    body = {key: profile[key] for key in ('full_name', 'email', 'phone', 'country', 'city',
            'current_title', 'total_experience', 'skills', 'current_employer', 'linkedin_url')}
    body['country_specific_data'] = data
    response = client.put('/api/candidate/profile', headers=headers, json=body)
    assert response.status_code == 200, response.text
    reloaded = client.get('/api/candidate/profile', headers=headers).json()['country_specific_data']
    for key, value in data.items():
        assert reloaded[key] == value
    body['country_specific_data']['projects'] = []
    assert client.put('/api/candidate/profile', headers=headers, json=body).status_code == 200
    reloaded = client.get('/api/candidate/profile', headers=headers).json()['country_specific_data']
    assert reloaded['projects'] == []
    assert reloaded['it_skills'] == data['it_skills']


def test_section_patch_preserves_unrelated_fields_and_setup_state(client):
    account = register(client, "candidate", "partial@example.com", CANDIDATE_ACCOUNT)
    headers = auth(account["access_token"])
    before = client.get('/api/candidate/profile', headers=headers).json()
    patch = {'country_specific_data': {'profile_summary': 'Updated summary'}}
    response = client.patch('/api/candidate/profile', headers=headers, json=patch)
    assert response.status_code == 200, response.text
    after = response.json()
    assert after['country_specific_data'] == {**before['country_specific_data'], 'profile_summary': 'Updated summary'}
    for key in ('full_name', 'email', 'city', 'skills', 'current_employer', 'total_experience'):
        assert after[key] == before[key]
    invalid = client.patch('/api/candidate/profile', headers=headers, json={'skills': ['Python', 'python', 'Python']})
    assert invalid.status_code == 422
    assert client.patch('/api/candidate/profile', headers=headers, json={'country_specific_data': {'projects': [{'title': ''}]}}).status_code == 422
    assert client.patch('/api/candidate/profile', headers=headers, json={'country_specific_data': {'_profile_completed': True}}).status_code == 422


def test_section_patch_does_not_require_complete_onboarding(client):
    account = register(client, "candidate", "section-only@example.com", {"full_name": "Section Candidate", "phone": "9999999999", "country": "IN", "onboarding_stage": "account", "career_stage": "fresher", "city": "Delhi"})
    headers = auth(account["access_token"])
    before = client.get('/api/candidate/profile', headers=headers).json()
    response = client.patch('/api/candidate/profile', headers=headers, json={'country_specific_data': {'projects': [{'title': 'Portfolio'}]}})
    assert response.status_code == 200, response.text
    after = response.json()
    assert after['country_specific_data'] == {**before['country_specific_data'], 'projects': [{'title': 'Portfolio'}]}
    assert after['skills'] == before['skills']
