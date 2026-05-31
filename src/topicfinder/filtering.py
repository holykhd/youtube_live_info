from collections import Counter
from topicfinder.models import ChatMsg, Bucket
from topicfinder.scoring import compute_activity

STOPWORDS = {"안녕", "하세요", "여러분", "구독", "좋아요", "오늘", "지금", "진짜", "그냥"}


def extract_keywords(text: str, kiwi) -> list[str]:
    """한국어 명사·고유명사만 추출 (2글자 이상, 불용어 제외)."""
    tokens = kiwi.tokenize(text)
    out = []
    for tok in tokens:
        if tok.tag in ("NNG", "NNP") and len(tok.form) >= 2 and tok.form not in STOPWORDS:
            out.append(tok.form)
    return out


def bucketize(chats: list[ChatMsg], bucket_size: int) -> dict[float, list[ChatMsg]]:
    buckets: dict[float, list[ChatMsg]] = {}
    for c in chats:
        start = float(int(c.t_sec // bucket_size) * bucket_size)
        buckets.setdefault(start, []).append(c)
    return buckets


def analyze_video(chats: list[ChatMsg], kiwi, *, bucket_size: int,
                  activity_threshold: float, min_keywords: int,
                  top_keywords: int, max_msgs_per_bucket: int = 500) -> list[Bucket]:
    grouped = bucketize(chats, bucket_size)
    result: list[Bucket] = []
    prev_counts: dict[str, int] = {}
    for start in sorted(grouped):
        msgs = grouped[start][:max_msgs_per_bucket]
        counts: Counter[str] = Counter()
        for m in msgs:
            counts.update(extract_keywords(m.message, kiwi))
        activity = compute_activity(len(msgs), dict(counts), prev_counts)
        prev_counts = dict(counts)
        if activity >= activity_threshold and len(counts) >= min_keywords:
            top = [w for w, _ in counts.most_common(top_keywords)]
            video_id = msgs[0].video_id
            result.append(Bucket(video_id=video_id, bucket_start=start,
                                 keywords=top, activity=activity))
    return result
