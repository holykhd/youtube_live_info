from topicfinder.store import Store
from topicfinder.models import VideoRef, ChatMsg


def make_store():
    return Store(":memory:")


def test_upsert_channel_idempotent():
    s = make_store()
    s.upsert_channel("https://youtube.com/@a", title="A")
    s.upsert_channel("https://youtube.com/@a", title="A2")
    chans = s.list_channels()
    assert len(chans) == 1
    assert chans[0].title == "A2"


def test_upsert_video_and_get_cursor():
    s = make_store()
    v = VideoRef("v1", "제목", "LIVE", "2026-05-31T14:00:00+09:00",
                 "https://youtube.com/@a")
    s.upsert_video(v)
    assert s.get_last_chat_t("v1") == 0.0
    s.set_last_chat_t("v1", 152.0)
    assert s.get_last_chat_t("v1") == 152.0


def test_insert_chats_dedup():
    s = make_store()
    msgs = [ChatMsg("v1", 5.0, "u1", "금리"), ChatMsg("v1", 5.0, "u1", "금리")]
    inserted = s.insert_chats(msgs)
    assert inserted == 1
    again = s.insert_chats([ChatMsg("v1", 5.0, "u1", "금리")])
    assert again == 0


def test_get_chats_since():
    s = make_store()
    s.insert_chats([ChatMsg("v1", 5.0, "u", "a"), ChatMsg("v1", 200.0, "u", "b")])
    after = s.get_chats_since("v1", 100.0)
    assert len(after) == 1
    assert after[0].t_sec == 200.0


from topicfinder.models import Topic, TopicMatch


def test_save_and_load_topics():
    s = make_store()
    topic = Topic(label="연준 금리", hot_score=9.0, channel_count=3, members=[
        TopicMatch("v1", 0.0, "2026-05-31T14:00:00+09:00",
                   "https://www.youtube.com/watch?v=v1&t=0s"),
        TopicMatch("v2", 60.0, "2026-05-31T14:01:00+09:00",
                   "https://www.youtube.com/watch?v=v2&t=60s"),
    ])
    s.save_topics([topic])
    loaded = s.load_topics()
    assert len(loaded) == 1
    assert loaded[0].label == "연준 금리"
    assert loaded[0].channel_count == 3
    assert len(loaded[0].members) == 2
    assert loaded == sorted(loaded, key=lambda t: -t.hot_score)


def test_save_topics_replaces_snapshot():
    s = make_store()
    s.save_topics([Topic("A", 1.0, 1)])
    s.save_topics([Topic("B", 2.0, 2)])
    labels = {t.label for t in s.load_topics()}
    assert labels == {"B"}
