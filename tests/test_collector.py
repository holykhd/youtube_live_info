from topicfinder.collector import identify_video, collect_chats
from topicfinder.models import VideoRef


def test_identify_live_video():
    def fake_extract(url):
        assert url.endswith("/live")
        return {"id": "liveID", "title": "라이브중", "is_live": True,
                "timestamp": 1780203600}
    v = identify_video("https://youtube.com/@a", extract=fake_extract)
    assert v.status == "LIVE"
    assert v.video_id == "liveID"
    assert v.started_at.startswith("2026-05-31T14:00:00")


def test_identify_falls_back_to_last_stream():
    def fake_extract(url):
        if url.endswith("/live"):
            raise RuntimeError("no live")
        if url.endswith("/streams"):
            return {"entries": [
                {"id": "vodID", "title": "지난라이브",
                 "timestamp": 1748662800}]}
        raise AssertionError(url)
    v = identify_video("https://youtube.com/@a", extract=fake_extract)
    assert v.status == "VOD"
    assert v.video_id == "vodID"


def test_identify_returns_none_when_no_streams():
    def fake_extract(url):
        if url.endswith("/live"):
            raise RuntimeError("no live")
        return {"entries": []}
    assert identify_video("https://youtube.com/@a", extract=fake_extract) is None


def test_collect_chats_filters_since_and_maps():
    def fake_chat(video_id):
        return [
            {"time_in_seconds": 5.0, "message": "금리",
             "author": {"name": "u1"}},
            {"time_in_seconds": 200.0, "message": "환율",
             "author": {"name": "u2"}},
        ]
    msgs = collect_chats("vodID", since_t=100.0, get_chat=fake_chat)
    assert len(msgs) == 1
    assert msgs[0].t_sec == 200.0
    assert msgs[0].message == "환율"
    assert msgs[0].video_id == "vodID"
