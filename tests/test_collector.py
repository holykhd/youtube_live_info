from topicfinder.collector import identify_video, collect_chats, parse_live_chat_lines
from topicfinder.models import VideoRef
from tests.fixtures.live_chat_lines import SAMPLE_LINES


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


def test_parse_live_chat_extracts_offset_seconds():
    msgs = parse_live_chat_lines(SAMPLE_LINES, "vid")
    # 3개의 유효 메시지만 (비JSON/메시지없음/offset없음 제외)
    assert len(msgs) == 3
    assert msgs[0].video_id == "vid"
    assert msgs[0].t_sec == 0.0
    assert msgs[0].message == "연준 금리 인상"
    assert msgs[0].author == "u1"
    assert msgs[1].t_sec == 5.0           # 5000ms → 5.0s (원값 유지, 비정규화)
    assert msgs[2].t_sec == 130.0


def test_collect_chats_filters_since_via_injected_fetch():
    def fake_fetch(video_id):
        assert video_id == "vid"
        return SAMPLE_LINES
    msgs = collect_chats("vid", since_t=10.0, fetch_lines=fake_fetch)
    # t_sec>10 인 것만 → 130.0 하나
    assert len(msgs) == 1
    assert msgs[0].t_sec == 130.0
    assert msgs[0].message == "ㅋㅋㅋㅋ"
