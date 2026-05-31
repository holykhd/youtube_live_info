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
