import math
from topicfinder.scoring import (
    compute_activity, hot_score, to_absolute_time, jump_url,
)


def test_compute_activity_spike():
    prev = {"잡담": 5}
    cur = {"금리": 10, "연준": 4}
    act = compute_activity(msg_count=14, cur_keywords=cur, prev_keywords=prev)
    assert act > 0


def test_compute_activity_quiet_bucket_low():
    act = compute_activity(msg_count=1, cur_keywords={"안녕": 1}, prev_keywords={})
    assert act < 3.0


def test_hot_score_weights_channel_count():
    s1 = hot_score(channel_count=1, activity_sum=100.0)
    s3 = hot_score(channel_count=3, activity_sum=100.0)
    assert s3 > s1
    assert math.isclose(s3, 9 * math.log(101))


def test_to_absolute_time_adds_seconds():
    abs_t = to_absolute_time("2026-05-31T14:00:00+09:00", 152.0)
    assert abs_t == "2026-05-31T14:02:32+09:00"


def test_jump_url_format():
    assert jump_url("abc123", 152.0) == "https://www.youtube.com/watch?v=abc123&t=152s"


def test_jump_url_clamps_negative_offset():
    # 재방송 음수 오프셋 → t=0 으로 클램프(무효 링크 방지)
    assert jump_url("abc123", -22200.0) == "https://www.youtube.com/watch?v=abc123&t=0s"
