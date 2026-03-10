from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module


client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_security_headers_and_request_id():
    res = client.get('/subjects')
    assert res.status_code == 200
    assert 'X-Request-ID' in res.headers
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'


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
    assert 0 <= report_data['recent_7d_accuracy'] <= 1


def test_dictation_flow_report_and_timeline():
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

    timeline = client.get('/memory/timeline', params={'user_id': 'u2', 'subject': 'english', 'limit': 10})
    assert timeline.status_code == 200
    events = timeline.json()['events']
    assert len(events) >= 1
    assert events[0]['event_type'] in {'practice', 'dictation'}


def test_study_plan_endpoint(monkeypatch):
    async def _fake_plan(**kwargs):
        return {
            'summary': '7天提分计划',
            'daily_plan': ['D1 函数复习', 'D2 导数训练'],
            'checkpoints': ['完成2次小测'],
        }

    monkeypatch.setattr(main_module, 'generate_study_plan', _fake_plan)

    res = client.post(
        '/study/plan',
        json={
            'user_id': 'u3',
            'subject': 'math',
            'target': '月考提升20分',
            'weak_points': ['函数', '导数'],
            'available_minutes_per_day': 90,
            'days': 7,
            'model_config': {
                'provider': 'openai_compatible',
                'base_url': 'https://api.openai.com/v1',
                'api_key': 'test_key',
                'model': 'gpt-4o-mini',
                'timeout_s': 60,
            },
        },
    )
    assert res.status_code == 200
    assert 'summary' in res.json()


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
