from kiwipiepy import Kiwi
from topicfinder.scheduler import run_cycle
from topicfinder.store import Store
from topicfinder.config import Config
from topicfinder.models import VideoRef, ChatMsg

KIWI = Kiwi()


def _deps():
    s = Store(":memory:")
    s.upsert_channel("https://youtube.com/@a")
    s.upsert_channel("https://youtube.com/@b")

    def fake_identify(url):
        vid = "v1" if url.endswith("@a") else "v2"
        return VideoRef(vid, "t", "LIVE", "2026-05-31T14:00:00+09:00", url)

    def fake_collect(video_id, since_t):
        return [
            ChatMsg(video_id, 5.0, "u1", "연준 금리 인상"),
            ChatMsg(video_id, 12.0, "u2", "파월 금리 발언"),
            ChatMsg(video_id, 40.0, "u3", "금리 동결"),
        ]

    def fake_judge(cands, prev_labels):
        return [{"label": "연준 금리",
                 "members": [{"video": b.video_id, "bucket": b.bucket_start}
                             for b in cands]}]

    return s, fake_identify, fake_collect, fake_judge


def test_run_cycle_produces_topics_and_persists():
    s, fi, fc, fj = _deps()
    cfg = Config(activity_threshold=0.0, min_keywords=1)
    stats = run_cycle(s, cfg, KIWI, identify=fi, collect=fc, judge=fj)
    topics = s.load_topics()
    assert len(topics) == 1
    assert topics[0].channel_count == 2
    assert stats["videos"] == 2
    assert stats["llm_calls"] == 1


def test_run_cycle_fallback_on_llm_error():
    s, fi, fc, _ = _deps()
    cfg = Config(activity_threshold=0.0, min_keywords=1)

    def boom(cands, prev_labels):
        raise RuntimeError("한도 초과")

    stats = run_cycle(s, cfg, KIWI, identify=fi, collect=fc, judge=boom)
    assert stats["llm_failed"] is True
    assert len(s.load_topics()) >= 1
    assert all("[키워드]" in t.label for t in s.load_topics())


def test_run_cycle_default_judge_uses_cfg_llm_model(monkeypatch):
    # 기본 judge 사용 시 cfg.llm_model 이 llm.judge_topics 로 전달되는지 검증
    import topicfinder.scheduler as sched
    captured = {}

    def fake_judge_topics(cands, prev_labels, *, model="haiku"):
        captured["model"] = model
        return [{"label": "X", "members": [{"video": b.video_id, "bucket": b.bucket_start}
                                           for b in cands]}]

    monkeypatch.setattr(sched._llm, "judge_topics", fake_judge_topics)

    s, fi, fc, _ = _deps()
    cfg = Config(activity_threshold=0.0, min_keywords=1, llm_model="sonnet")
    # judge 를 주입하지 않음 → 기본 judge 경로 사용
    stats = sched.run_cycle(s, cfg, KIWI, identify=fi, collect=fc)
    assert captured["model"] == "sonnet"


def test_run_cycle_handles_negative_offset_chat():
    s = Store(":memory:")
    s.upsert_channel("https://youtube.com/@a")

    def fake_identify(url):
        return VideoRef("v1", "재방송", "LIVE", "2026-05-31T16:00:00+09:00", url)

    def fake_collect(video_id, since_t):
        # 재방송: 음수 오프셋 채팅 (since_t=UNSEEN_CURSOR 이므로 모두 통과해야 함)
        base = [ChatMsg("v1", -3000.0, "u1", "연준 금리 인상 발언"),
                ChatMsg("v1", -2990.0, "u2", "파월 금리 동결 시사"),
                ChatMsg("v1", -2980.0, "u3", "금리 인하 기대감")]
        return [m for m in base if m.t_sec > since_t]

    def fake_judge(cands, prev_labels):
        return [{"label": "금리", "members": [{"video": b.video_id, "bucket": b.bucket_start}
                                              for b in cands]}]

    cfg = Config(activity_threshold=0.0, min_keywords=1, bucket_size_sec=120)
    stats = run_cycle(s, cfg, KIWI, identify=fake_identify, collect=fake_collect, judge=fake_judge)
    topics = s.load_topics()
    assert stats["videos"] == 1
    assert len(topics) >= 1            # 음수 오프셋 채팅도 주제로 잡힘 (이전엔 0이었음)
