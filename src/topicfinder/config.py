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
