from fastapi.testclient import TestClient
from topicfinder.app import create_app
from topicfinder.store import Store


def client_with_store():
    store = Store(":memory:")
    app = create_app(store)
    return TestClient(app), store


def test_add_and_list_channels():
    c, _ = client_with_store()
    r = c.post("/api/channels", json={"url": "https://youtube.com/@a"})
    assert r.status_code == 200
    r2 = c.get("/api/channels")
    assert r2.status_code == 200
    assert any(ch["url"] == "https://youtube.com/@a" for ch in r2.json())


def test_get_topics_empty_initially():
    c, _ = client_with_store()
    r = c.get("/api/topics")
    assert r.status_code == 200
    assert r.json() == []


def test_get_topics_returns_saved():
    c, store = client_with_store()
    from topicfinder.models import Topic, TopicMatch
    store.save_topics([Topic("연준 금리", 9.0, 2, [
        TopicMatch("v1", 0.0, "2026-05-31T14:00:00+09:00",
                   "https://www.youtube.com/watch?v=v1&t=0s")])])
    r = c.get("/api/topics")
    body = r.json()
    assert body[0]["label"] == "연준 금리"
    assert body[0]["members"][0]["video_id"] == "v1"
