from kiwipiepy import Kiwi
from topicfinder.filtering import extract_keywords, bucketize, analyze_video
from tests.fixtures.sample_chats import SAMPLE

KIWI = Kiwi()


def test_extract_keywords_returns_nouns_only():
    kw = extract_keywords("연준 금리 인상하나요 ㅋㅋ", KIWI)
    assert "연준" in kw
    assert "금리" in kw
    assert "ㅋㅋ" not in kw
    assert all(len(w) >= 2 for w in kw)


def test_bucketize_groups_by_window():
    buckets = bucketize(SAMPLE, bucket_size=120)
    assert set(buckets.keys()) == {0.0, 120.0}
    assert len(buckets[0.0]) == 5
    assert len(buckets[120.0]) == 3


def test_analyze_video_keeps_meaningful_drops_chatter():
    buckets = analyze_video(
        SAMPLE, KIWI, bucket_size=120, activity_threshold=3.0,
        min_keywords=2, top_keywords=8,
    )
    starts = {b.bucket_start for b in buckets}
    assert 0.0 in starts
    assert 120.0 not in starts
    first = next(b for b in buckets if b.bucket_start == 0.0)
    assert "금리" in first.keywords
