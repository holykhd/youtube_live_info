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

    from fastapi.staticfiles import StaticFiles
    web_dir = Path(__file__).parent / "web"
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

    return app
