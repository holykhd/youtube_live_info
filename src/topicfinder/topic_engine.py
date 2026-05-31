from topicfinder.models import Bucket, Topic, TopicMatch
from topicfinder.scoring import hot_score, to_absolute_time, jump_url


def build_topics(buckets: list[Bucket], started_at: dict[str, str],
                 channel_of: dict[str, str], prev_labels: list[str],
                 judge) -> list[Topic]:
    """후보 버킷 → LLM 그룹핑(judge) → 핫점수·시작시각이 채워진 Topic 리스트."""
    groups = judge(buckets, prev_labels)
    act_index = {(b.video_id, float(b.bucket_start)): b.activity for b in buckets}
    topics: list[Topic] = []
    for g in groups:
        earliest: dict[str, float] = {}
        activity_sum = 0.0
        for m in g["members"]:
            vid, bstart = m["video"], float(m["bucket"])
            activity_sum += act_index.get((vid, bstart), 0.0)
            if vid not in earliest or bstart < earliest[vid]:
                earliest[vid] = bstart
        members = []
        for vid, t in earliest.items():
            abs_t = to_absolute_time(started_at[vid], t)
            members.append(TopicMatch(vid, t, abs_t, jump_url(vid, t)))
        channel_count = len({channel_of[vid] for vid in earliest})
        topics.append(Topic(
            label=g["label"],
            hot_score=hot_score(channel_count, activity_sum),
            channel_count=channel_count,
            members=members,
        ))
    topics.sort(key=lambda t: -t.hot_score)
    return topics
