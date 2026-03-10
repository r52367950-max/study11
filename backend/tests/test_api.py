from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_practice_memory_roundtrip_and_report():
    submit = client.post(
        '/practice/submit',
        json={
            'user_id': 'u1',
            'subject': 'math',
            'total': 10,
            'correct': 7,
            'avg_duration_s': 45,
            'notes': '二次函数最值，公式代入错误',
        },
    )
    assert submit.status_code == 200

    profile = client.get('/memory/profile', params={'user_id': 'u1', 'subject': 'math'})
    assert profile.status_code == 200
    data = profile.json()
    assert data['user_id'] == 'u1'
    assert data['attempts'] >= 1
    assert 0 <= data['accuracy'] <= 1

    report = client.get('/memory/report', params={'user_id': 'u1', 'subject': 'math'})
    assert report.status_code == 200
    report_data = report.json()
    assert report_data['level'] in {'A', 'B', 'C'}
    assert report_data['trend'] in {'improving', 'stable', 'needs_attention'}
    assert len(report_data['suggestions']) >= 1


def test_dictation_flow_and_report_fields():
    start = client.post(
        '/dictation/start',
        json={'user_id': 'u2', 'subject': 'english', 'content': 'apple banana orange'},
    )
    assert start.status_code == 200
    session_id = start.json()['session_id']

    submit = client.post(
        '/dictation/submit',
        json={
            'session_id': session_id,
            'user_id': 'u2',
            'subject': 'english',
            'reference_text': 'apple banana orange',
            'answer_text': 'apple banan orange',
            'duration_s': 20,
        },
    )
    assert submit.status_code == 200
    body = submit.json()
    assert 0 <= body['accuracy'] <= 1

    report = client.get('/memory/report', params={'user_id': 'u2', 'subject': 'english'})
    assert report.status_code == 200
    report_data = report.json()
    assert 'dictation_sessions' in report_data
    assert 'dictation_accuracy' in report_data


def test_invalid_subject_validation():
    res = client.post(
        '/practice/submit',
        json={
            'user_id': 'u2',
            'subject': 'physics',
            'total': 10,
            'correct': 8,
            'avg_duration_s': 40,
        },
    )
    assert res.status_code == 422
