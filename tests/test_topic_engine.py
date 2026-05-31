from topicfinder.topic_engine import build_topics
from topicfinder.models import Bucket


def test_build_topics_computes_score_and_start():
    buckets = [
        Bucket("v1", 0.0, ["금리", "연준"], 5.0),
        Bucket("v1", 120.0, ["금리"], 3.0),
        Bucket("v2", 60.0, ["파월", "금리"], 4.0),
    ]
    started_at = {"v1": "2026-05-31T14:00:00+09:00",
                  "v2": "2026-05-31T14:10:00+09:00"}
    channel_of = {"v1": "https://youtube.com/@a",
                  "v2": "https://youtube.com/@b"}

    def fake_judge(cands, prev_labels):
        return [{"label": "연준 금리",
                 "members": [{"video": "v1", "bucket": 0},
                             {"video": "v1", "bucket": 120},
                             {"video": "v2", "bucket": 60}]}]

    topics = build_topics(buckets, started_at, channel_of,
                          prev_labels=[], judge=fake_judge)
    assert len(topics) == 1
    t = topics[0]
    assert t.label == "연준 금리"
    assert t.channel_count == 2
    assert t.hot_score > 0
    members = {m.video_id: m for m in t.members}
    assert members["v1"].start_t_sec == 0.0
    assert members["v1"].start_abs == "2026-05-31T14:00:00+09:00"
    assert members["v2"].jump_url.endswith("v=v2&t=60s")


def test_build_topics_sorted_by_hot_score():
    buckets = [
        Bucket("v1", 0.0, ["a"], 5.0), Bucket("v2", 0.0, ["a"], 5.0),
        Bucket("v3", 0.0, ["b"], 5.0),
    ]
    started_at = {v: "2026-05-31T14:00:00+09:00" for v in ("v1", "v2", "v3")}
    channel_of = {"v1": "@a", "v2": "@b", "v3": "@c"}

    def fake_judge(cands, prev_labels):
        return [
            {"label": "단독", "members": [{"video": "v3", "bucket": 0}]},
            {"label": "교차", "members": [{"video": "v1", "bucket": 0},
                                          {"video": "v2", "bucket": 0}]},
        ]

    topics = build_topics(buckets, started_at, channel_of,
                          prev_labels=[], judge=fake_judge)
    assert topics[0].label == "교차"
