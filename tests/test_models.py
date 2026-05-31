from topicfinder.models import (
    ChannelRef, VideoRef, ChatMsg, Bucket, TopicMatch, Topic,
)


def test_video_ref_fields():
    v = VideoRef(video_id="abc", title="제목", status="LIVE",
                 started_at="2026-05-31T14:00:00+09:00",
                 channel_url="https://youtube.com/@x")
    assert v.video_id == "abc"
    assert v.status == "LIVE"


def test_bucket_default_topic_id_none():
    b = Bucket(video_id="abc", bucket_start=120.0, keywords=["금리"], activity=5.0)
    assert b.topic_id is None


def test_topic_members_default_empty():
    t = Topic(label="연준 금리", hot_score=4.0, channel_count=2)
    assert t.members == []
