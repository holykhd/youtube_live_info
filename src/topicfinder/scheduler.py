from topicfinder.config import Config
from topicfinder.store import Store
from topicfinder.filtering import analyze_video
from topicfinder.topic_engine import build_topics
from topicfinder.models import Bucket, Topic, TopicMatch
from topicfinder.scoring import hot_score, to_absolute_time, jump_url
from topicfinder import collector as _collector
from topicfinder import llm as _llm


def _default_identify(url):
    return _collector.identify_video(url)


def _default_collect(video_id, since_t):
    return _collector.collect_chats(video_id, since_t)


def _default_judge(cands, prev_labels):
    return _llm.judge_topics(cands, prev_labels)


def _fallback_topics(buckets, started_at, channel_of):
    """LLM 실패 시: 같은 최상위 키워드를 공유하는 버킷을 묶는 단순 폴백."""
    by_key: dict[str, list[Bucket]] = {}
    for b in buckets:
        if not b.keywords:
            continue
        by_key.setdefault(b.keywords[0], []).append(b)
    topics = []
    for key, bs in by_key.items():
        earliest: dict[str, float] = {}
        activity_sum = 0.0
        for b in bs:
            activity_sum += b.activity
            if b.video_id not in earliest or b.bucket_start < earliest[b.video_id]:
                earliest[b.video_id] = b.bucket_start
        members = [TopicMatch(v, t, to_absolute_time(started_at[v], t),
                              jump_url(v, t)) for v, t in earliest.items()]
        cc = len({channel_of[v] for v in earliest})
        topics.append(Topic(f"[키워드] {key}", hot_score(cc, activity_sum), cc, members))
    topics.sort(key=lambda t: -t.hot_score)
    return topics


def run_cycle(store: Store, cfg: Config, kiwi, *,
              identify=_default_identify, collect=_default_collect,
              judge=None) -> dict:
    if judge is None:
        judge = lambda cands, prev: _llm.judge_topics(cands, prev, model=cfg.llm_model)
    stats = {"videos": 0, "llm_calls": 0, "llm_failed": False}
    started_at: dict[str, str] = {}
    channel_of: dict[str, str] = {}
    all_buckets: list[Bucket] = []

    for ch in store.list_channels():
        try:
            v = identify(ch.url)
        except Exception:
            continue
        if v is None:
            continue
        store.upsert_video(v)
        stats["videos"] += 1
        started_at[v.video_id] = v.started_at
        channel_of[v.video_id] = ch.url

        since = store.get_last_chat_t(v.video_id)
        try:
            new_msgs = collect(v.video_id, since)
        except Exception:
            new_msgs = []
        if new_msgs:
            store.insert_chats(new_msgs)
            store.set_last_chat_t(v.video_id, max(m.t_sec for m in new_msgs))

        chats = store.get_chats_since(v.video_id, -1.0)
        buckets = analyze_video(
            chats, kiwi, bucket_size=cfg.bucket_size_sec,
            activity_threshold=cfg.activity_threshold,
            min_keywords=cfg.min_keywords,
            top_keywords=cfg.top_keywords_per_bucket,
            max_msgs_per_bucket=cfg.max_msgs_per_bucket,
        )
        all_buckets.extend(buckets)

    if not all_buckets:
        store.save_topics([])
        return stats

    prev_labels = store.current_labels()
    try:
        stats["llm_calls"] += 1
        topics = build_topics(all_buckets, started_at, channel_of,
                              prev_labels, judge)
    except Exception:
        stats["llm_failed"] = True
        topics = _fallback_topics(all_buckets, started_at, channel_of)

    store.save_topics(topics)
    return stats
