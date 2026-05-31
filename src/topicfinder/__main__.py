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
