# 유튜브 라이브 동일 주제 탐지기 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 여러 유튜브 채널의 라이브(또는 마지막 라이브) 채팅을 수집·분석해 "오늘의 핫한 주제"와 각 영상의 주제 시작 시각을 웹 대시보드로 보여주는 시스템을 만든다.

**Architecture:** Python 백엔드(FastAPI). Scheduler가 20분 주기로 사이클을 돌린다 → Collector가 yt-dlp/chat-downloader로 라이브를 식별하고 타임스탬프 채팅을 증분 수집 → TopicEngine이 1차 로컬 필터(kiwipiepy 형태소+빈도)로 노이즈를 걸러 후보를 압축하고, 2차로 `claude -p`(구독 인증, 추가비용 0)에 키워드 요약만 보내 주제를 정규화·그룹핑 → Scoring이 교차 채널 수 가중 핫 점수와 절대 시작시각을 산정 → SQLite에 저장하고 대시보드에 push. 외부(YouTube/LLM) 의존부는 주입 가능한 인터페이스로 감싸 결정론적으로 테스트한다.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, SQLite(표준 라이브러리 sqlite3), yt-dlp, chat-downloader, kiwipiepy, pytest, claude CLI(구독 인증).

---

## 파일 구조

```
15_유튜브라이브영상같은주제영상찾기/
├── pyproject.toml                     # 의존성·패키지 메타
├── README.md                          # 실행 방법
├── .gitignore
├── src/topicfinder/
│   ├── __init__.py
│   ├── config.py                      # 설정값(주기·버킷·임계값·경로)
│   ├── models.py                      # 데이터클래스 (ChannelRef, VideoRef, ChatMsg, Bucket, Topic, TopicMatch)
│   ├── store.py                       # SQLite 스키마 + DAO
│   ├── scoring.py                     # 순수 함수: 활성도·핫점수·절대시각·jump_url
│   ├── filtering.py                   # 1차 로컬 필터 (형태소·버킷·키워드)
│   ├── llm.py                         # claude -p subprocess 래퍼 + 프롬프트/파싱
│   ├── collector.py                   # yt-dlp 라이브 식별 + chat-downloader 채팅 수집
│   ├── topic_engine.py               # 1차→2차→매칭→점수 오케스트레이션
│   ├── scheduler.py                   # 20분 주기 사이클 루프
│   ├── app.py                         # FastAPI 앱 + REST + WebSocket
│   └── web/
│       ├── index.html                 # 대시보드 화면
│       └── app.js                     # 실시간 갱신·렌더링
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── sample_chats.py
    │   └── llm_response.json
    ├── test_store.py
    ├── test_scoring.py
    ├── test_filtering.py
    ├── test_llm.py
    ├── test_collector.py
    ├── test_topic_engine.py
    └── test_app.py
```

각 파일은 단일 책임을 가진다: `scoring.py`/`filtering.py`는 순수 로직(외부 의존 0), `collector.py`/`llm.py`는 외부 도구 래퍼(주입 가능한 호출자), `topic_engine.py`는 이들을 조립, `store.py`는 영속화, `app.py`는 표출.

---

## Task 1: 프로젝트 스캐폴드

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/topicfinder/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: git 저장소 초기화**

Run:
```bash
cd "/Users/foreverskhd/PROJECT/99_CLAUDE_PROJECT/05_Programs/15_유튜브라이브영상같은주제영상찾기"
git init
```
Expected: `Initialized empty Git repository ...`

- [ ] **Step 2: pyproject.toml 작성**

```toml
[project]
name = "topicfinder"
version = "0.1.0"
description = "유튜브 라이브 동일 주제 탐지기"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "yt-dlp>=2024.1.1",
    "chat-downloader>=0.2.8",
    "kiwipiepy>=0.17",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 3: .gitignore 작성**

```gitignore
__pycache__/
*.pyc
.venv/
venv/
*.db
*.sqlite3
.pytest_cache/
data/
```

- [ ] **Step 4: 패키지 초기화 파일 생성**

`src/topicfinder/__init__.py`:
```python
"""유튜브 라이브 동일 주제 탐지기."""
```

`tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
```

- [ ] **Step 5: 가상환경 생성 및 설치**

Run:
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```
Expected: 의존성 설치 완료, 마지막에 `Successfully installed ... topicfinder-0.1.0`

- [ ] **Step 6: pytest 동작 확인**

Run: `.venv/bin/pytest -q`
Expected: `no tests ran` (테스트 없음, 에러 없이 종료)

- [ ] **Step 7: 커밋**

```bash
git add pyproject.toml .gitignore src/topicfinder/__init__.py tests/conftest.py
git commit -m "chore: 프로젝트 스캐폴드 및 의존성 설정"
```

---

## Task 2: 설정 모듈

**Files:**
- Create: `src/topicfinder/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_config.py`:
```python
from topicfinder.config import Config


def test_default_config_values():
    cfg = Config()
    assert cfg.cycle_interval_sec == 1200          # 20분 절약 주기
    assert cfg.bucket_size_sec == 120              # 2분 버킷
    assert cfg.activity_threshold == 3.0
    assert cfg.min_keywords == 2
    assert cfg.max_llm_calls_per_cycle == 2
    assert cfg.llm_model == "haiku"
    assert cfg.top_keywords_per_bucket == 8


def test_config_override():
    cfg = Config(cycle_interval_sec=300, llm_model="sonnet")
    assert cfg.cycle_interval_sec == 300
    assert cfg.llm_model == "sonnet"
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.config'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/config.py`:
```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    cycle_interval_sec: int = 1200        # 20분
    bucket_size_sec: int = 120            # 2분
    activity_threshold: float = 3.0
    min_keywords: int = 2
    max_llm_calls_per_cycle: int = 2
    llm_model: str = "haiku"
    top_keywords_per_bucket: int = 8
    max_msgs_per_bucket: int = 500        # 폭주 라이브 샘플링 캡
    db_path: str = "data/topicfinder.db"

    def ensure_dirs(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/config.py tests/test_config.py
git commit -m "feat: 설정 모듈 추가"
```

---

## Task 3: 데이터 모델

**Files:**
- Create: `src/topicfinder/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.models'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/models.py`:
```python
from dataclasses import dataclass, field


@dataclass
class ChannelRef:
    url: str
    channel_id: str | None = None
    title: str | None = None


@dataclass
class VideoRef:
    video_id: str
    title: str
    status: str              # 'LIVE' | 'VOD'
    started_at: str          # ISO8601 (KST)
    channel_url: str


@dataclass
class ChatMsg:
    video_id: str
    t_sec: float
    author: str
    message: str


@dataclass
class Bucket:
    video_id: str
    bucket_start: float
    keywords: list[str]
    activity: float
    topic_id: int | None = None


@dataclass
class TopicMatch:
    video_id: str
    start_t_sec: float
    start_abs: str
    jump_url: str


@dataclass
class Topic:
    label: str
    hot_score: float
    channel_count: int
    members: list[TopicMatch] = field(default_factory=list)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/models.py tests/test_models.py
git commit -m "feat: 데이터 모델 추가"
```

---

## Task 4: Scoring (순수 함수)

**Files:**
- Create: `src/topicfinder/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_scoring.py`:
```python
import math
from topicfinder.scoring import (
    compute_activity, hot_score, to_absolute_time, jump_url,
)


def test_compute_activity_spike():
    # 이전 버킷엔 '잡담', 이번 버킷에 '금리'가 급증 → 활성도 상승
    prev = {"잡담": 5}
    cur = {"금리": 10, "연준": 4}
    act = compute_activity(msg_count=14, cur_keywords=cur, prev_keywords=prev)
    assert act > 0


def test_compute_activity_quiet_bucket_low():
    act = compute_activity(msg_count=1, cur_keywords={"안녕": 1}, prev_keywords={})
    assert act < 3.0   # 한산한 버킷은 임계값 미만


def test_hot_score_weights_channel_count():
    # 같은 활성도면 교차 채널이 많을수록 핫점수가 커야 한다
    s1 = hot_score(channel_count=1, activity_sum=100.0)
    s3 = hot_score(channel_count=3, activity_sum=100.0)
    assert s3 > s1
    assert math.isclose(s3, 9 * math.log(101))


def test_to_absolute_time_adds_seconds():
    # 14:00:00 + 152초 = 14:02:32
    abs_t = to_absolute_time("2026-05-31T14:00:00+09:00", 152.0)
    assert abs_t == "2026-05-31T14:02:32+09:00"


def test_jump_url_format():
    assert jump_url("abc123", 152.0) == "https://www.youtube.com/watch?v=abc123&t=152s"
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.scoring'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/scoring.py`:
```python
import math
from datetime import datetime, timedelta


def compute_activity(msg_count: int, cur_keywords: dict[str, int],
                     prev_keywords: dict[str, int]) -> float:
    """버킷 활성도 = 메시지량 가중 × (1 + 신규 키워드 급증률)."""
    if msg_count <= 0:
        return 0.0
    cur_total = sum(cur_keywords.values()) or 1
    prev_set = set(prev_keywords)
    new_weight = sum(c for k, c in cur_keywords.items() if k not in prev_set)
    spike_ratio = new_weight / cur_total          # 0..1
    return math.log(msg_count + 1) * (1.0 + 2.0 * spike_ratio)


def hot_score(channel_count: int, activity_sum: float) -> float:
    """교차 채널 수를 제곱으로 강하게 가중."""
    return (channel_count ** 2) * math.log(activity_sum + 1.0)


def to_absolute_time(started_at_iso: str, t_sec: float) -> str:
    base = datetime.fromisoformat(started_at_iso)
    return (base + timedelta(seconds=t_sec)).isoformat()


def jump_url(video_id: str, t_sec: float) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={int(t_sec)}s"
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_scoring.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/scoring.py tests/test_scoring.py
git commit -m "feat: 활성도·핫점수·시각 변환 순수 함수 추가"
```

---

## Task 5: 1차 로컬 필터

**Files:**
- Create: `src/topicfinder/filtering.py`
- Create: `tests/fixtures/sample_chats.py`
- Test: `tests/test_filtering.py`

- [ ] **Step 1: 채팅 픽스처 작성**

`tests/fixtures/sample_chats.py`:
```python
from topicfinder.models import ChatMsg

# 0~120초 버킷: 금리/연준 관련 의미 채팅이 몰림
# 120~240초 버킷: 잡담·이모지뿐
SAMPLE = [
    ChatMsg("v1", 5.0, "u1", "연준 금리 인상하나요"),
    ChatMsg("v1", 12.0, "u2", "파월 발언 시작됐다"),
    ChatMsg("v1", 33.0, "u3", "금리 동결 예상이요"),
    ChatMsg("v1", 80.0, "u4", "연준 매파적이네"),
    ChatMsg("v1", 119.0, "u5", "금리 금리 금리"),
    ChatMsg("v1", 130.0, "u6", "ㅋㅋㅋㅋ"),
    ChatMsg("v1", 145.0, "u7", "안녕하세요"),
    ChatMsg("v1", 200.0, "u8", "ㅎㅇ"),
]
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/test_filtering.py`:
```python
from kiwipiepy import Kiwi
from topicfinder.filtering import extract_keywords, bucketize, analyze_video
from tests.fixtures.sample_chats import SAMPLE

KIWI = Kiwi()


def test_extract_keywords_returns_nouns_only():
    kw = extract_keywords("연준 금리 인상하나요 ㅋㅋ", KIWI)
    assert "연준" in kw
    assert "금리" in kw
    assert "ㅋㅋ" not in kw          # 이모지/자모 제외
    assert all(len(w) >= 2 for w in kw)  # 1글자 제외


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
    assert 0.0 in starts          # 의미 있는 버킷 유지
    assert 120.0 not in starts    # 잡담 버킷 탈락
    first = next(b for b in buckets if b.bucket_start == 0.0)
    assert "금리" in first.keywords
```

- [ ] **Step 3: 실패 확인**

Run: `.venv/bin/pytest tests/test_filtering.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.filtering'`

- [ ] **Step 4: 최소 구현**

`src/topicfinder/filtering.py`:
```python
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
```

- [ ] **Step 5: 통과 확인**

Run: `.venv/bin/pytest tests/test_filtering.py -v`
Expected: PASS (3 passed)
참고: 임계값으로 `120.0` 버킷이 탈락하지 않으면 `activity_threshold`를 픽스처 기준으로 미세 조정한다(테스트가 기준).

- [ ] **Step 6: 커밋**

```bash
git add src/topicfinder/filtering.py tests/fixtures/sample_chats.py tests/test_filtering.py
git commit -m "feat: 1차 로컬 필터(형태소·버킷·활성도) 추가"
```

---

## Task 6: LLM 래퍼 (claude -p)

**Files:**
- Create: `src/topicfinder/llm.py`
- Create: `tests/fixtures/llm_response.json`
- Test: `tests/test_llm.py`

- [ ] **Step 1: LLM 응답 픽스처 작성**

`tests/fixtures/llm_response.json`:
```json
{"topics": [{"label": "연준 금리/파월 발언", "members": [{"video": "v1", "bucket": 0}, {"video": "v2", "bucket": 60}]}, {"label": "환율 급등", "members": [{"video": "v3", "bucket": 120}]}]}
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/test_llm.py`:
```python
import json
from pathlib import Path
from topicfinder.models import Bucket
from topicfinder.llm import build_prompt, parse_response, judge_topics

FIXTURE = Path(__file__).parent / "fixtures" / "llm_response.json"


def test_build_prompt_includes_keywords_and_prev_labels():
    buckets = [Bucket("v1", 0.0, ["금리", "연준"], 5.0)]
    prompt = build_prompt(buckets, prev_labels=["환율 급등"])
    assert "금리" in prompt and "연준" in prompt
    assert "v1" in prompt
    assert "환율 급등" in prompt      # 기존 라벨 제공 → 주제 안정성


def test_parse_response_extracts_topics():
    raw = FIXTURE.read_text(encoding="utf-8")
    topics = parse_response(raw)
    assert topics[0]["label"] == "연준 금리/파월 발언"
    assert len(topics[0]["members"]) == 2


def test_parse_response_handles_codefence():
    raw = "```json\n" + FIXTURE.read_text(encoding="utf-8") + "\n```"
    topics = parse_response(raw)
    assert topics[0]["label"] == "연준 금리/파월 발언"


def test_judge_topics_uses_injected_runner():
    buckets = [Bucket("v1", 0.0, ["금리"], 5.0)]
    fake_output = FIXTURE.read_text(encoding="utf-8")
    captured = {}

    def fake_runner(prompt: str, model: str) -> str:
        captured["prompt"] = prompt
        captured["model"] = model
        return fake_output

    topics = judge_topics(buckets, prev_labels=[], runner=fake_runner, model="haiku")
    assert captured["model"] == "haiku"
    assert topics[0]["label"] == "연준 금리/파월 발언"
```

- [ ] **Step 3: 실패 확인**

Run: `.venv/bin/pytest tests/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.llm'`

- [ ] **Step 4: 최소 구현**

`src/topicfinder/llm.py`:
```python
import json
import re
import subprocess
from topicfinder.models import Bucket

_SYSTEM = (
    "너는 여러 유튜브 라이브 방송의 시간대별 채팅 키워드를 보고 "
    "각 구간의 핵심 주제를 짧은 라벨로 정규화하고, "
    "같은 주제를 다루는 구간끼리 묶는 분석가다. "
    "반드시 JSON만 출력한다."
)


def build_prompt(buckets: list[Bucket], prev_labels: list[str]) -> str:
    lines = []
    for b in buckets:
        lines.append(f"[{b.video_id} | {int(b.bucket_start)} | {', '.join(b.keywords)}]")
    prev = ", ".join(prev_labels) if prev_labels else "(없음)"
    return (
        f"{_SYSTEM}\n\n"
        f"기존 주제 라벨(가능하면 재사용): {prev}\n\n"
        "다음 구간들의 주제를 정규화하고 같은 주제끼리 그룹으로 묶어라.\n"
        + "\n".join(lines)
        + "\n\n출력 형식(JSON): "
        '{"topics":[{"label":"주제명","members":[{"video":"영상ID","bucket":시작초}]}]}'
    )


def parse_response(raw: str) -> list[dict]:
    """코드펜스/잡텍스트가 섞여도 JSON 객체를 추출."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    data = json.loads(text)
    return data.get("topics", [])


def _claude_runner(prompt: str, model: str) -> str:
    """claude -p 를 구독 인증으로 호출 (추가 API 과금 없음)."""
    proc = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--model", model, prompt],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude 호출 실패: {proc.stderr.strip()}")
    # --output-format json 은 {"result": "...본문..."} 형태 → 본문에서 토픽 JSON 추출
    try:
        envelope = json.loads(proc.stdout)
        return envelope.get("result", proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout


def judge_topics(buckets: list[Bucket], prev_labels: list[str], *,
                 runner=_claude_runner, model: str = "haiku") -> list[dict]:
    prompt = build_prompt(buckets, prev_labels)
    raw = runner(prompt, model)
    return parse_response(raw)
```

- [ ] **Step 5: 통과 확인**

Run: `.venv/bin/pytest tests/test_llm.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: 커밋**

```bash
git add src/topicfinder/llm.py tests/fixtures/llm_response.json tests/test_llm.py
git commit -m "feat: claude -p 구독 LLM 래퍼(프롬프트·파싱·주입형 runner) 추가"
```

---

## Task 7: SQLite 저장소

**Files:**
- Create: `src/topicfinder/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_store.py`:
```python
from topicfinder.store import Store
from topicfinder.models import VideoRef, ChatMsg


def make_store():
    return Store(":memory:")          # 인메모리 DB로 테스트


def test_upsert_channel_idempotent():
    s = make_store()
    s.upsert_channel("https://youtube.com/@a", title="A")
    s.upsert_channel("https://youtube.com/@a", title="A2")
    chans = s.list_channels()
    assert len(chans) == 1            # 같은 URL → 중복 안 생김
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
    assert inserted == 1              # 동일 (video,t,msg) → 1건만
    again = s.insert_chats([ChatMsg("v1", 5.0, "u1", "금리")])
    assert again == 0                # 재실행 멱등성


def test_get_chats_since():
    s = make_store()
    s.insert_chats([ChatMsg("v1", 5.0, "u", "a"), ChatMsg("v1", 200.0, "u", "b")])
    after = s.get_chats_since("v1", 100.0)
    assert len(after) == 1
    assert after[0].t_sec == 200.0
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.store'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/store.py`:
```python
import sqlite3
from topicfinder.models import ChannelRef, VideoRef, ChatMsg

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY, url TEXT UNIQUE, channel_id TEXT, title TEXT,
  enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY, video_id TEXT UNIQUE, channel_url TEXT,
  title TEXT, status TEXT, started_at TEXT, last_chat_t REAL DEFAULT 0,
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY, video_id TEXT, t_sec REAL, author TEXT, message TEXT,
  UNIQUE(video_id, t_sec, message)
);
CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY, label TEXT, hot_score REAL,
  channel_count INTEGER, first_seen_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS topic_matches (
  id INTEGER PRIMARY KEY, topic_id INTEGER, video_id TEXT,
  start_t_sec REAL, start_abs TEXT, jump_url TEXT,
  UNIQUE(topic_id, video_id)
);
"""


class Store:
    def __init__(self, db_path: str = ":memory:"):
        # check_same_thread=False: 분석 루프 스레드와 웹 요청 스레드가 연결 공유
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- channels ---
    def upsert_channel(self, url: str, channel_id: str | None = None,
                       title: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO channels(url, channel_id, title) VALUES(?,?,?) "
            "ON CONFLICT(url) DO UPDATE SET channel_id=excluded.channel_id, "
            "title=excluded.title",
            (url, channel_id, title),
        )
        self.conn.commit()

    def list_channels(self) -> list[ChannelRef]:
        rows = self.conn.execute(
            "SELECT url, channel_id, title FROM channels WHERE enabled=1"
        ).fetchall()
        return [ChannelRef(r["url"], r["channel_id"], r["title"]) for r in rows]

    # --- videos / cursor ---
    def upsert_video(self, v: VideoRef) -> None:
        self.conn.execute(
            "INSERT INTO videos(video_id, channel_url, title, status, started_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(video_id) DO UPDATE SET "
            "title=excluded.title, status=excluded.status, "
            "started_at=excluded.started_at, updated_at=datetime('now')",
            (v.video_id, v.channel_url, v.title, v.status, v.started_at),
        )
        self.conn.commit()

    def get_last_chat_t(self, video_id: str) -> float:
        row = self.conn.execute(
            "SELECT last_chat_t FROM videos WHERE video_id=?", (video_id,)
        ).fetchone()
        return row["last_chat_t"] if row else 0.0

    def set_last_chat_t(self, video_id: str, t: float) -> None:
        self.conn.execute(
            "UPDATE videos SET last_chat_t=? WHERE video_id=?", (t, video_id)
        )
        self.conn.commit()

    # --- chats ---
    def insert_chats(self, msgs: list[ChatMsg]) -> int:
        before = self.conn.total_changes
        self.conn.executemany(
            "INSERT OR IGNORE INTO chats(video_id, t_sec, author, message) "
            "VALUES(?,?,?,?)",
            [(m.video_id, m.t_sec, m.author, m.message) for m in msgs],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def get_chats_since(self, video_id: str, t: float) -> list[ChatMsg]:
        rows = self.conn.execute(
            "SELECT video_id, t_sec, author, message FROM chats "
            "WHERE video_id=? AND t_sec>? ORDER BY t_sec", (video_id, t)
        ).fetchall()
        return [ChatMsg(r["video_id"], r["t_sec"], r["author"], r["message"])
                for r in rows]
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/store.py tests/test_store.py
git commit -m "feat: SQLite 저장소(채널·영상·채팅, 증분 커서·멱등성) 추가"
```

---

## Task 8: 저장소 — 주제/매칭 영속화

**Files:**
- Modify: `src/topicfinder/store.py`
- Test: `tests/test_store.py` (추가)

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_store.py` 끝에 추가:
```python
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
    # 핫점수 내림차순 정렬 보장
    assert loaded == sorted(loaded, key=lambda t: -t.hot_score)


def test_save_topics_replaces_snapshot():
    s = make_store()
    s.save_topics([Topic("A", 1.0, 1)])
    s.save_topics([Topic("B", 2.0, 2)])
    labels = {t.label for t in s.load_topics()}
    assert labels == {"B"}            # 최신 사이클 스냅샷으로 교체
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_store.py -v`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'save_topics'`

- [ ] **Step 3: Store에 메서드 추가**

`src/topicfinder/store.py` 의 `Store` 클래스 끝(get_chats_since 다음)에 추가:
```python
    # --- topics / matches (사이클 스냅샷) ---
    def save_topics(self, topics: list[Topic]) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM topic_matches")
        cur.execute("DELETE FROM topics")
        for t in topics:
            cur.execute(
                "INSERT INTO topics(label, hot_score, channel_count) VALUES(?,?,?)",
                (t.label, t.hot_score, t.channel_count),
            )
            tid = cur.lastrowid
            for m in t.members:
                cur.execute(
                    "INSERT OR IGNORE INTO topic_matches"
                    "(topic_id, video_id, start_t_sec, start_abs, jump_url) "
                    "VALUES(?,?,?,?,?)",
                    (tid, m.video_id, m.start_t_sec, m.start_abs, m.jump_url),
                )
        self.conn.commit()

    def load_topics(self) -> list[Topic]:
        trows = self.conn.execute(
            "SELECT id, label, hot_score, channel_count FROM topics "
            "ORDER BY hot_score DESC"
        ).fetchall()
        topics = []
        for tr in trows:
            mrows = self.conn.execute(
                "SELECT video_id, start_t_sec, start_abs, jump_url "
                "FROM topic_matches WHERE topic_id=? ORDER BY start_abs",
                (tr["id"],),
            ).fetchall()
            members = [TopicMatch(m["video_id"], m["start_t_sec"],
                                  m["start_abs"], m["jump_url"]) for m in mrows]
            topics.append(Topic(tr["label"], tr["hot_score"],
                                tr["channel_count"], members))
        return topics

    def current_labels(self) -> list[str]:
        rows = self.conn.execute("SELECT label FROM topics").fetchall()
        return [r["label"] for r in rows]
```

`store.py` 상단 import 에 `Topic, TopicMatch` 추가:
```python
from topicfinder.models import ChannelRef, VideoRef, ChatMsg, Topic, TopicMatch
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_store.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/store.py tests/test_store.py
git commit -m "feat: 주제·매칭 스냅샷 저장/조회 추가"
```

---

## Task 9: Collector (yt-dlp + chat-downloader)

**Files:**
- Create: `src/topicfinder/collector.py`
- Test: `tests/test_collector.py`

외부 도구(yt-dlp/chat-downloader)는 주입 가능한 호출자로 감싸 결정론적으로 테스트한다.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_collector.py`:
```python
from topicfinder.collector import identify_video, collect_chats
from topicfinder.models import VideoRef


def test_identify_live_video():
    # yt-dlp /live 추출이 is_live=True 를 주면 LIVE 로 식별
    def fake_extract(url):
        assert url.endswith("/live")
        return {"id": "liveID", "title": "라이브중", "is_live": True,
                "timestamp": 1748666400}   # 2026-05-31T14:00:00+09:00
    v = identify_video("https://youtube.com/@a", extract=fake_extract)
    assert v.status == "LIVE"
    assert v.video_id == "liveID"
    assert v.started_at.startswith("2026-05-31T14:00:00")


def test_identify_falls_back_to_last_stream():
    # /live 가 라이브 없음(예외) → /streams 첫 항목(VOD)으로 폴백
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


def test_collect_chats_filters_since_and_maps():
    def fake_chat(video_id):
        return [
            {"time_in_seconds": 5.0, "message": "금리",
             "author": {"name": "u1"}},
            {"time_in_seconds": 200.0, "message": "환율",
             "author": {"name": "u2"}},
        ]
    msgs = collect_chats("vodID", since_t=100.0, get_chat=fake_chat)
    assert len(msgs) == 1
    assert msgs[0].t_sec == 200.0
    assert msgs[0].message == "환율"
    assert msgs[0].video_id == "vodID"
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_collector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.collector'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/collector.py`:
```python
from datetime import datetime, timezone, timedelta
from topicfinder.models import VideoRef

KST = timezone(timedelta(hours=9))


def _ts_to_kst_iso(ts: int | None) -> str:
    if not ts:
        return datetime.now(KST).isoformat()
    return datetime.fromtimestamp(ts, KST).isoformat()


def _default_extract(url: str) -> dict:
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def identify_video(channel_url: str, *, extract=_default_extract) -> VideoRef | None:
    """진행 중 라이브가 있으면 그것을, 없으면 마지막 라이브(VOD)를 식별."""
    base = channel_url.rstrip("/")
    # 1) 진행 중 라이브 시도
    try:
        info = extract(base + "/live")
        if info and info.get("is_live"):
            return VideoRef(info["id"], info.get("title", ""), "LIVE",
                            _ts_to_kst_iso(info.get("timestamp")), channel_url)
    except Exception:
        pass
    # 2) 마지막 라이브(VOD) 폴백
    try:
        streams = extract(base + "/streams")
    except Exception:
        return None
    entries = (streams or {}).get("entries") or []
    if not entries:
        return None
    e = entries[0]
    return VideoRef(e["id"], e.get("title", ""), "VOD",
                    _ts_to_kst_iso(e.get("timestamp")), channel_url)


def _default_get_chat(video_id: str) -> list[dict]:
    from chat_downloader import ChatDownloader
    url = f"https://www.youtube.com/watch?v={video_id}"
    return list(ChatDownloader().get_chat(url))


def collect_chats(video_id: str, since_t: float, *,
                  get_chat=_default_get_chat) -> list:
    """since_t 이후의 채팅만 ChatMsg 로 변환(증분)."""
    from topicfinder.models import ChatMsg
    out = []
    for m in get_chat(video_id):
        t = float(m.get("time_in_seconds") or 0.0)
        if t <= since_t:
            continue
        author = (m.get("author") or {}).get("name", "")
        out.append(ChatMsg(video_id, t, author, m.get("message", "")))
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_collector.py -v`
Expected: PASS (4 passed)
참고: `timestamp` 1748666400이 KST 14:00:00이 아니면 테스트의 기대 문자열을 실제 변환값에 맞춰 조정한다.

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/collector.py tests/test_collector.py
git commit -m "feat: Collector(라이브 식별·증분 채팅 수집, 주입형 호출자) 추가"
```

---

## Task 10: TopicEngine (오케스트레이션)

**Files:**
- Create: `src/topicfinder/topic_engine.py`
- Test: `tests/test_topic_engine.py`

1차 결과(버킷) + 2차 LLM 그룹핑 → Topic 리스트(핫점수·시작시각 포함)로 조립한다.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_topic_engine.py`:
```python
from topicfinder.topic_engine import build_topics
from topicfinder.models import Bucket


def test_build_topics_computes_score_and_start():
    # 두 영상이 같은 주제 → 교차 채널 2, 핫점수>0, 시작시각=가장 이른 버킷
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
    assert t.channel_count == 2            # 서로 다른 채널 2개
    assert t.hot_score > 0
    members = {m.video_id: m for m in t.members}
    assert members["v1"].start_t_sec == 0.0    # 가장 이른 버킷
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
    assert topics[0].label == "교차"        # 교차 채널 주제가 상위
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_topic_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.topic_engine'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/topic_engine.py`:
```python
from topicfinder.models import Bucket, Topic, TopicMatch
from topicfinder.scoring import hot_score, to_absolute_time, jump_url


def build_topics(buckets: list[Bucket], started_at: dict[str, str],
                 channel_of: dict[str, str], prev_labels: list[str],
                 judge) -> list[Topic]:
    """후보 버킷 → LLM 그룹핑(judge) → 핫점수·시작시각이 채워진 Topic 리스트."""
    groups = judge(buckets, prev_labels)
    # 버킷 활성도 조회용 인덱스
    act_index = {(b.video_id, float(b.bucket_start)): b.activity for b in buckets}
    topics: list[Topic] = []
    for g in groups:
        # 영상별 가장 이른 버킷 = 그 영상이 주제를 처음 다룬 시각
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
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_topic_engine.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/topic_engine.py tests/test_topic_engine.py
git commit -m "feat: TopicEngine(LLM 그룹핑→핫점수·시작시각 조립) 추가"
```

---

## Task 11: Scheduler (사이클 오케스트레이션)

**Files:**
- Create: `src/topicfinder/scheduler.py`
- Test: `tests/test_scheduler.py`

한 사이클 = 채널 식별 → 채팅 증분 수집/저장 → 1차 필터 → 2차 LLM(상한·fallback) → 점수·저장. 외부 의존은 모두 주입한다.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_scheduler.py`:
```python
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
    # graceful degradation: 키워드 기반으로라도 주제가 비어있지 않게 생성
    assert len(s.load_topics()) >= 1
    assert all("[키워드]" in t.label for t in s.load_topics())
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.scheduler'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/scheduler.py`:
```python
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
              judge=_default_judge) -> dict:
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

        chats = store.get_chats_since(v.video_id, -1.0)   # 전체 누적 채팅
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
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_scheduler.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 실행**

Run: `.venv/bin/pytest -q`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/topicfinder/scheduler.py tests/test_scheduler.py
git commit -m "feat: Scheduler(한 사이클 오케스트레이션·LLM fallback) 추가"
```

---

## Task 12: FastAPI 앱 (REST + 채널 관리)

**Files:**
- Create: `src/topicfinder/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_app.py`:
```python
from fastapi.testclient import TestClient
from topicfinder.app import create_app
from topicfinder.store import Store


def client_with_store():
    store = Store(":memory:")
    app = create_app(store)
    return TestClient(app), store


def test_add_and_list_channels():
    c, _ = client_with_store()
    r = c.post("/api/channels", json={"url": "https://youtube.com/@a"})
    assert r.status_code == 200
    r2 = c.get("/api/channels")
    assert r2.status_code == 200
    assert any(ch["url"] == "https://youtube.com/@a" for ch in r2.json())


def test_get_topics_empty_initially():
    c, _ = client_with_store()
    r = c.get("/api/topics")
    assert r.status_code == 200
    assert r.json() == []


def test_get_topics_returns_saved():
    c, store = client_with_store()
    from topicfinder.models import Topic, TopicMatch
    store.save_topics([Topic("연준 금리", 9.0, 2, [
        TopicMatch("v1", 0.0, "2026-05-31T14:00:00+09:00",
                   "https://www.youtube.com/watch?v=v1&t=0s")])])
    r = c.get("/api/topics")
    body = r.json()
    assert body[0]["label"] == "연준 금리"
    assert body[0]["members"][0]["video_id"] == "v1"
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'topicfinder.app'`

- [ ] **Step 3: 최소 구현**

`src/topicfinder/app.py`:
```python
from dataclasses import asdict
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from topicfinder.store import Store


class ChannelIn(BaseModel):
    url: str


def create_app(store: Store) -> FastAPI:
    app = FastAPI(title="유튜브 라이브 동일 주제 탐지기")

    @app.get("/api/channels")
    def list_channels():
        return [asdict(c) for c in store.list_channels()]

    @app.post("/api/channels")
    def add_channel(ch: ChannelIn):
        store.upsert_channel(ch.url)
        return {"ok": True}

    @app.get("/api/topics")
    def get_topics():
        return [asdict(t) for t in store.load_topics()]

    @app.get("/", response_class=HTMLResponse)
    def index():
        html = Path(__file__).parent / "web" / "index.html"
        return html.read_text(encoding="utf-8") if html.exists() else "<h1>topicfinder</h1>"

    return app
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/topicfinder/app.py tests/test_app.py
git commit -m "feat: FastAPI 앱(채널 관리·주제 조회 REST) 추가"
```

---

## Task 13: 웹 대시보드 + 엔트리포인트

**Files:**
- Create: `src/topicfinder/web/index.html`
- Create: `src/topicfinder/web/app.js`
- Create: `src/topicfinder/__main__.py`
- Create: `README.md`

UI는 정적 페이지가 REST를 폴링해 렌더링한다(웹소켓 없이 단순 폴링으로 시작 — YAGNI).

- [ ] **Step 1: 대시보드 HTML 작성**

`src/topicfinder/web/index.html`:
```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>유튜브 라이브 핫 주제</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 24px; background:#0f1115; color:#e6e6e6; }
    h1 { font-size: 20px; }
    .topic { border:1px solid #2a2f3a; border-radius:10px; padding:14px; margin:12px 0; }
    .label { font-size:16px; font-weight:700; }
    .score { color:#8ab4ff; font-size:13px; }
    .member { margin:6px 0; font-size:14px; }
    a { color:#7ee787; text-decoration:none; }
    input,button { padding:8px; border-radius:8px; border:1px solid #2a2f3a; background:#1a1d24; color:#e6e6e6; }
  </style>
</head>
<body>
  <h1>🔥 오늘의 핫한 라이브 주제</h1>
  <div>
    <input id="url" placeholder="채널 주소 (예: https://youtube.com/@handle)" size="40" />
    <button onclick="addChannel()">채널 추가</button>
  </div>
  <div id="channels"></div>
  <hr/>
  <div id="topics">불러오는 중…</div>
  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 대시보드 JS 작성**

`src/topicfinder/web/app.js`:
```javascript
async function addChannel() {
  const url = document.getElementById('url').value.trim();
  if (!url) return;
  await fetch('/api/channels', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url}),
  });
  document.getElementById('url').value = '';
  loadChannels();
}

async function loadChannels() {
  const r = await fetch('/api/channels');
  const chs = await r.json();
  document.getElementById('channels').innerHTML =
    '구독 채널: ' + chs.map(c => c.title || c.url).join(', ');
}

function fmtTime(iso) {
  try { return new Date(iso).toLocaleTimeString('ko-KR'); }
  catch { return iso; }
}

async function loadTopics() {
  const r = await fetch('/api/topics');
  const topics = await r.json();
  const box = document.getElementById('topics');
  if (!topics.length) { box.innerHTML = '아직 분석된 주제가 없습니다.'; return; }
  box.innerHTML = topics.map(t => `
    <div class="topic">
      <div class="label">${t.label}
        <span class="score">· 핫점수 ${t.hot_score.toFixed(1)} · ${t.channel_count}개 채널</span>
      </div>
      ${t.members.map(m => `
        <div class="member">▶ <a href="${m.jump_url}" target="_blank">${m.video_id}</a>
          — 시작 ${fmtTime(m.start_abs)}</div>`).join('')}
    </div>`).join('');
}

loadChannels();
loadTopics();
setInterval(loadTopics, 30000);   // 30초마다 갱신
setInterval(loadChannels, 60000);
```

- [ ] **Step 3: app.py 에 정적 파일 마운트 추가**

`src/topicfinder/app.py` 의 `create_app` 안, `return app` 직전에 추가:
```python
    from fastapi.staticfiles import StaticFiles
    web_dir = Path(__file__).parent / "web"
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
```

- [ ] **Step 4: 엔트리포인트 작성**

`src/topicfinder/__main__.py`:
```python
import threading
import time
import uvicorn
from kiwipiepy import Kiwi
from topicfinder.config import Config
from topicfinder.store import Store
from topicfinder.app import create_app
from topicfinder.scheduler import run_cycle


def _loop(store: Store, cfg: Config):
    kiwi = Kiwi()
    while True:
        try:
            stats = run_cycle(store, cfg, kiwi)
            print(f"[cycle] {stats}")
        except Exception as e:
            print(f"[cycle][error] {e}")
        time.sleep(cfg.cycle_interval_sec)


def main():
    cfg = Config()
    cfg.ensure_dirs()
    store = Store(cfg.db_path)
    app = create_app(store)
    threading.Thread(target=_loop, args=(store, cfg), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 정적 마운트 회귀 테스트 확인**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: PASS (정적 마운트 추가 후에도 기존 3 테스트 유지)

- [ ] **Step 6: README 작성**

`README.md`:
```markdown
# 유튜브 라이브 동일 주제 탐지기

구독 중인 여러 유튜브 채널의 라이브(또는 마지막 라이브) 채팅을 분석해
"오늘의 핫한 주제"와 각 영상의 주제 시작 시각을 웹 대시보드로 보여줍니다.

## 요구 사항
- Python 3.11+
- 로그인된 `claude` CLI (구독 인증) — LLM 분석에 추가 API 비용이 들지 않습니다.

## 설치
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## 실행
```bash
.venv/bin/python -m topicfinder
```
브라우저에서 http://127.0.0.1:8000 접속 → 채널 주소를 추가하면
20분 주기로 분석이 돌며 핫 주제·영상별 시작 시각이 표시됩니다.

## 테스트
```bash
.venv/bin/pytest -q
```

## 동작 개요
수집(yt-dlp/chat-downloader, 무료) → 1차 로컬 필터(kiwipiepy) →
2차 LLM 판정(claude -p, 구독 한도) → 핫점수·시작시각 산정 → 대시보드.
LLM 호출 실패/한도 초과 시 키워드 기반으로 자동 강등됩니다.
```

- [ ] **Step 7: 수동 E2E 확인**

Run:
```bash
.venv/bin/python -m topicfinder
```
브라우저에서 http://127.0.0.1:8000 접속 → 실제 라이브 중인 채널 2~3개 추가 →
한 사이클(또는 `Config(cycle_interval_sec=60)`으로 단축 후) 뒤 주제·시작시각 표출 확인.
확인 후 Ctrl+C 로 종료.

- [ ] **Step 8: 커밋**

```bash
git add src/topicfinder/web/index.html src/topicfinder/web/app.js \
        src/topicfinder/app.py src/topicfinder/__main__.py README.md
git commit -m "feat: 웹 대시보드·엔트리포인트·README 추가"
```

---

## 완료 기준

- [ ] `.venv/bin/pytest -q` 전체 통과
- [ ] `python -m topicfinder` 실행 시 대시보드 접속 가능
- [ ] 채널 주소 추가 → 사이클 후 핫 주제와 영상별 시작시각·바로가기 표출
- [ ] `claude -p` 호출이 구독 인증으로 동작(추가 API 과금 없음) 확인
- [ ] LLM 실패 주입 시 키워드 기반 fallback 동작 확인

## 향후 확장 (YAGNI — 지금 구현 안 함)
- WebSocket 실시간 push (현재는 30초 폴링)
- 댓글(타임스탬프 없는 VOD 보조 신호) 통합
- LLM 호출 통계의 대시보드 노출
- 주제 하루 추이 그래프
