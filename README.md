# 유튜브 라이브 동일 주제 탐지기

구독 중인 여러 유튜브 채널의 라이브(또는 마지막 라이브) 채팅을 분석해
"오늘의 핫한 주제"와 각 영상의 주제 시작 시각을 웹 대시보드로 보여줍니다.

## 요구 사항
- Python 3.11+
- 로그인된 `claude` CLI (구독 인증) — LLM 분석에 추가 API 비용이 들지 않습니다.

## 설치
```
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## 실행
```
.venv/bin/python -m topicfinder
```

브라우저에서 http://127.0.0.1:8000 접속 → 채널 주소를 추가하면
20분 주기로 분석이 돌며 핫 주제·영상별 시작 시각이 표시됩니다.

## 테스트
```
.venv/bin/pytest -q
```

## 동작 개요
수집(yt-dlp/chat-downloader, 무료) → 1차 로컬 필터(kiwipiepy) →
2차 LLM 판정(claude -p, 구독 한도) → 핫점수·시작시각 산정 → 대시보드.
LLM 호출 실패/한도 초과 시 키워드 기반으로 자동 강등됩니다.
