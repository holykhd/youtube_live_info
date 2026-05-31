# 유튜브 라이브 동일 주제 탐지기 — 설계 문서

작성일: 2026-05-31
상태: 설계 확정 (구현 계획 전)

## 1. 목적

구독 중인 여러 유튜브 채널의 **라이브 방송**(진행 중이 아니면 마지막 라이브 다시보기)을 분석해,
**오늘의 핫한 주제**를 찾아내고, 같은 주제를 다루는 여러 라이브 영상과 **각 영상에서 그 주제를
처음 다룬 시작 시간**을 한눈에 보여준다.

핵심 가치: "지금 여러 채널이 동시에 다루는 주제 = 오늘의 핫 토픽"을 자동 포착하고,
같은 주제 라이브들을 시작 시각과 함께 모아 준다.

## 2. 핵심 결정 사항 (브레인스토밍 결과)

| 항목 | 결정 | 이유 |
|------|------|------|
| 주제 판별 신호 | **실시간 채팅(1차) + 댓글·메타데이터(보조)** (음성 STT 미사용) | 채팅은 타임스탬프가 있고 "사람들이 반응하는 핫한 순간"을 직접 보여줌. STT보다 가볍고 목적에 부합. 댓글은 타임스탬프가 없어 시작시간 산정엔 못 쓰고, 채팅이 약한 VOD의 주제 추정 보조로만 사용 |
| 실행 모델 | **실시간 상시 모니터링** (주기적 사이클) | 뜨고 있는 주제를 계속 추적 |
| 출력 형태 | **웹 대시보드** (실시간 갱신) | 핫 주제 랭킹·영상별 시작시간·바로가기 |
| 주제 추출 엔진 | **LLM 기반** (`claude -p`, 구독 인증) | 한국어 채팅 노이즈에 가장 강함 |
| 비용 | **추가 종량 과금 0** — 구독(Pro/Max) 한도만 사용 | `claude -p` headless를 구독 인증으로 subprocess 호출 |
| 모니터링 주기 | **기본 20분 (절약 모드)**, 설정 가능 | 구독 한도 보호 |
| 대상 채널 수 | **10개 내외** | 20분 주기에서 한도 여유 충분 |
| 데이터 소스 | **yt-dlp + chat-downloader** (API 키 불필요, 무료) | 종료된 라이브 채팅 리플레이까지 접근 가능 |

### 비용 구조 (중요)
- Anthropic **종량제 API**는 구독과 별개로 토큰당 과금된다.
- 대신 이 환경의 `claude` CLI는 **구독 인증으로 동작**하며 `claude -p --output-format json --model haiku|sonnet`를 지원한다.
- 백엔드가 LLM이 필요할 때 `claude -p`를 **subprocess로 호출** → 종량 과금 없이 구독 한도 안에서 처리.
- 단, 구독에는 **5시간 롤링 한도 + 주간 한도**가 있으므로 LLM 호출을 아끼는 하이브리드 구조가 필수.

## 3. 아키텍처

```
브라우저(웹 대시보드)
   ▲  HTTP / WebSocket(실시간 갱신)
FastAPI 백엔드
   ├─ Scheduler   : 20분 주기로 사이클 트리거
   ├─ Collector   : 채널별 라이브/마지막 라이브 식별 + 채팅·메타데이터 수집
   ├─ Topic Engine: 1차 로컬 필터 → 2차 claude -p 판정 → 영상 간 주제 매칭
   ├─ Store       : SQLite 영속화, 증분 수집/중복 방지
   └─ Web API/UI  : 채널 관리, 핫 주제·매칭·시작시간 표시
외부 도구(subprocess)
   ├─ yt-dlp          (라이브 식별, 메타데이터)
   ├─ chat-downloader (라이브 채팅 수집, 타임스탬프)
   ├─ kiwipiepy       (한국어 형태소, 로컬·무료)
   └─ claude -p       (구독 LLM, 토픽 판정)
```

### 컴포넌트 단일 책임

| 컴포넌트 | 책임 | 의존 |
|---------|------|------|
| Scheduler | 주기(기본 20분, 설정 가능)로 수집·분석 사이클 트리거. 중복 실행 방지 | Collector, TopicEngine |
| Collector | 채널 URL → 라이브 정보 + 채팅 리스트(증분) | yt-dlp, chat-downloader |
| Topic Engine | 1차 로컬 필터 → 2차 LLM 토픽 판정 → 영상 간 매칭 → 핫 점수·시작시간 | kiwipiepy, claude -p |
| Store | 모든 데이터 영속화, 증분 커서·멱등성 | SQLite |
| Web API/UI | 채널 관리, 결과 표시, 실시간 push | FastAPI |

각 컴포넌트는 명확한 인터페이스로 분리되어 독립 테스트가 가능하다.

## 4. 데이터 흐름 (한 사이클, 20분마다 반복)

1. **채널 식별** — yt-dlp로 각 채널 확인 → 진행 중 라이브 있으면 그 영상 ID, 없으면 마지막 라이브 VOD ID. 결과: `[{채널, 영상ID, 상태(LIVE/VOD), 제목, 시작시각}]`
2. **채팅 수집(증분)** — chat-downloader로 LIVE는 직전 사이클 이후 새 채팅만 이어받기, VOD는 미수집분 리플레이 수집. 중복은 `(영상ID, t, msg)` 키로 방지.
3. **1차 로컬 필터(무료)** — 채팅을 2분 버킷으로 분할 → kiwipiepy 형태소 분석으로 명사·고유명사 추출 → 버킷별 키워드 빈도·급증 계산 → 잡담/이모지/도배 제거 → "의미 있는 버킷"만 후보로.
4. **2차 LLM 판정(구독, 아껴 씀)** — 후보 버킷들의 *키워드 요약만* 모아 `claude -p` 1~2회 호출 → 각 구간 주제 라벨 정규화 + 영상 간 동일 주제 그룹핑(JSON).
5. **핫 주제 산정 & 매칭** — 주제별 교차 채널 수·활성도로 핫 점수 계산·랭킹. 각 멤버 영상의 "그 주제 첫 등장 시각" = `started_at + 버킷t` → 절대시각(KST) 변환.
6. **대시보드 갱신** — WebSocket으로 핫 주제 랭킹 + 주제별 영상·시작시간 push.

**핵심 산출물 예시**: "핫 주제 =「연준 금리 발언」, 다루는 라이브 = ① A채널 14:32 ② B채널 14:40 ③ C채널 14:35". 바로가기 = `youtube.com/watch?v=ID&t=<버킷초>`.

**증분 처리**가 핵심: 매 사이클 전체 재수집이 아니라 직전 이후 새 채팅만 받아 한도·시간 절약.

## 5. 데이터 모델 (SQLite)

```sql
channels (
  id INTEGER PK, url TEXT UNIQUE, channel_id TEXT, title TEXT,
  enabled INTEGER DEFAULT 1, created_at TEXT
)
videos (
  id INTEGER PK, video_id TEXT UNIQUE, channel_id INTEGER FK→channels,
  title TEXT, status TEXT,            -- 'LIVE' | 'VOD'
  started_at TEXT,                    -- 라이브 시작 절대시각(KST)
  last_chat_t REAL DEFAULT 0,         -- 증분 수집 커서
  updated_at TEXT
)
chats (
  id INTEGER PK, video_id TEXT FK→videos.video_id,
  t_sec REAL, author TEXT, message TEXT,
  UNIQUE(video_id, t_sec, message)    -- 중복 수집 방지(멱등성)
)
buckets (
  id INTEGER PK, video_id TEXT FK→videos.video_id,
  bucket_start REAL, keywords TEXT,   -- JSON 상위 키워드
  activity REAL, topic_id INTEGER FK→topics,  -- 2차 판정 후 채워짐(nullable)
  UNIQUE(video_id, bucket_start)
)
topics (
  id INTEGER PK, label TEXT, hot_score REAL,
  channel_count INTEGER, first_seen_at TEXT, updated_at TEXT
)
topic_matches (
  id INTEGER PK, topic_id INTEGER FK→topics, video_id TEXT FK→videos.video_id,
  start_t_sec REAL, start_abs TEXT, jump_url TEXT,
  UNIQUE(topic_id, video_id)
)
```

설계 의도: `videos.last_chat_t`=증분 커서, `chats.UNIQUE`=멱등성, `buckets`=1·2차 결과 캐시(LLM 재호출 방지),
`topics`/`topic_matches` 분리로 "한 주제 ↔ 여러 영상·시작시간" N:N 표현, 주제 누적·갱신으로 하루 추이 관찰.

## 6. 주제 매칭 로직 (핵심 엔진)

### 6-1. 1차 로컬 필터 (무료, 전체 채팅 처리)
- 영상별 채팅 → 2분 버킷 분할
- kiwipiepy 형태소 → 명사·고유명사만 추출
- 불용어 제거: 이모지, ㅋㅋ/ㅎㅎ, 인사, 도배(같은 author 반복), 1글자
- 키워드 빈도 카운트 → 상위 N
- 활성도 = (메시지 수 가중) × (직전 버킷 대비 키워드 급증률)
- 통과 조건: 활성도 ≥ 임계값 AND 의미 키워드 ≥ 2개 → "후보 버킷"만 2차로

목적: 노이즈 제거 + LLM 입력량 압축. 한산·잡담 구간은 LLM까지 가지 않음.

### 6-2. 2차 LLM 판정 (구독, 사이클당 호출 최소화)
원칙: **원문 채팅을 보내지 않는다.** 키워드·요약만 전달해 토큰 1/10 이하로.

```
입력(사이클당 1~2회):
 "다음은 여러 라이브의 시간대별 채팅 키워드다.
  ① 각 구간 핵심 주제를 짧은 라벨로 정규화하라.
  ② 같은 주제 구간끼리 그룹으로 묶어라.
  [영상A | 14:30 | 금리, 연준, 파월, 인상]
  [영상B | 14:38 | 파월, 금리, 발언]
  [영상C | 14:32 | 환율, 달러, 1450] ..."
출력(--output-format json, JSON 스키마 강제):
 {"topics":[
   {"label":"연준 금리/파월 발언","members":[{"video":"A","bucket":870},{"video":"B","bucket":1080}]},
   {"label":"환율 급등","members":[{"video":"C","bucket":...}]}]}
```
- `claude -p --output-format json --model haiku` (가벼운 판정), 애매하면 sonnet
- **이전 사이클 주제 라벨 목록을 함께 제공** → 같은 주제를 새 라벨로 쪼개지 않고 기존 주제에 합류(주제 안정성)

### 6-3. 핫 점수 & 시작시간 산정 (로컬, 무료)
```
channel_count = 그 주제를 다룬 서로 다른 채널 수
activity_sum  = 멤버 버킷 활성도 합
hot_score     = channel_count² × log(activity_sum)   -- '여러 채널 동시'를 강하게 가중
시작시간 = min(해당 주제 버킷들의 bucket_start)
절대시각 = video.started_at + 버킷t  (KST)
jump_url = watch?v=영상ID&t=버킷초
```
핫 점수가 교차 채널 수를 강하게 가중 → "여러 채널이 동시에 다루는 = 오늘의 핫 주제" 정의에 부합.

### 6-4. 구독 한도 가드레일
- 사이클당 LLM 호출 상한(예 2회) — 초과 후보는 활성도 순으로 잘라 다음 사이클로
- LLM 입력 토큰 상한 (키워드만 보내 자연히 작음)
- `claude -p` 실패/한도 초과 → 1차 로컬 클러스터로 graceful degradation, "키워드 기반" 배지
- 호출 통계(횟수·추정 토큰) 기록·대시보드 노출로 한도 소진 가시화

## 7. 에러 처리 & 견고성

| 상황 | 처리 |
|------|------|
| yt-dlp가 YouTube 변경으로 깨짐 | 채널 단위 try/catch → 실패 채널만 skip, ⚠️ 표시. `yt-dlp -U` 안내 |
| 라이브 채팅 꺼진 영상 | 채팅 0건 → 메타데이터(제목/설명)만 보조 신호, "채팅 없음" 표기 |
| 채팅 폭주 인기 라이브 | 버킷당 메시지 캡 → 샘플링, 활성도엔 총량 반영 |
| claude -p 실패/한도 초과 | 1차 로컬 fallback, "키워드 기반" 배지, 다음 사이클 재시도 |
| claude JSON 파싱 실패 | 1회 재요청 → 실패 시 버킷 보류(다음 사이클) |
| 사이클 20분 초과 | 진행 중이면 다음 트리거 skip(중복 방지), 경고 로그 |
| 네트워크 단절 | 사이클 skip, 마지막 성공 결과 유지 |

원칙: 채널·영상·버킷 단위 격리로 **하나가 실패해도 전체 계속**. 모든 실패는 대시보드·로그에 가시화(조용히 삼키지 않음).

## 8. 알려진 한계

- 채팅 = 시청자 반응이지 발화자 주제가 아님 → 잡담 위주면 정확도↓ (메타데이터 보조로 완화)
- VOD 채팅 리플레이는 라이브 당시보다 누락 가능
- 구독 한도가 근본 상한 — 채널이 매우 많으면 압박 (현재 10개 내외 가정, 20분 주기로 여유)
- yt-dlp 의존 → YouTube 구조 변경 시 일시 장애 가능(업데이트로 복구)
- 핫 주제는 교차 채널 신호 기반 → 한 채널만 단독으로 다루는 주제는 후순위(의도된 동작)

## 9. 테스트 전략

```
단위 테스트(컴포넌트 독립, 외부 의존 없음):
  - 1차 필터: 고정 채팅 샘플 → 기대 키워드·활성도
  - 핫 점수/시작시간: 고정 버킷 → 기대 랭킹·절대시각
  - 증분 커서: last_chat_t 이후만 수집·멱등성(재실행 중복 없음)
  - 절대시각 변환: started_at + t초 → KST 정확성
통합 테스트(외부 도구 모킹):
  - Collector: yt-dlp/chat-downloader 출력을 fixture로 대체
  - Topic Engine: claude -p를 가짜 JSON으로 모킹 → 매칭 파이프라인 검증
  - Fallback: claude 실패 주입 → 키워드 기반 degrade 검증
E2E(수동·소규모): 실제 채널 2~3개로 1사이클 → 대시보드 표출 확인
```
핵심: 외부(YouTube/LLM) 의존부는 모킹해 결정론적으로, 분석 로직은 순수 함수로 빠르게 테스트.

## 10. 기술 스택 요약

- 언어/런타임: Python 3.11+
- 백엔드: FastAPI + Uvicorn, WebSocket
- 저장소: SQLite
- 외부 도구: yt-dlp, chat-downloader, kiwipiepy, claude CLI(구독 인증)
- 프론트: 경량 웹(정적 HTML/JS 또는 간단한 프레임워크) — 핫 주제 랭킹·주제별 영상/시작시간·바로가기·한도 통계
