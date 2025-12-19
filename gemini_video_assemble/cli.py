import argparse
from typing import Optional

import os
import shutil
import sys

try:
    from gunicorn.app.base import BaseApplication
except ImportError:
    BaseApplication = None

from .config import Settings
from .config_store import ConfigStore
from .server import create_app
from .storage import DataStore


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the Gemini video assemble server (Flask)."
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port to bind. If omitted, uses PORT from config/env (default 5000).",
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Path to a JSON config store (defaults to ~/.gemini_video_assemble/config.json).",
    )
    parser.add_argument(
        "--db-path",
        dest="db_path",
        help="Path to SQLite cache/db (defaults to ~/.gemini_video_assemble/data.db).",
    )
    parser.add_argument(
        "--purge-data",
        action="store_true",
        help="Delete cached data/config/runs and exit (also clears output dir).",
    )
    args = parser.parse_args(argv)

    config_store = ConfigStore(args.config_path)
    settings = Settings.from_sources(config_store.load())
    data_store = DataStore(args.db_path)

    if args.purge_data:
        data_store.purge(delete_outputs=True, output_dir=settings.output_dir)
        # Also remove legacy JSON config if present
        if args.config_path and os.path.exists(args.config_path):
            try:
                os.remove(args.config_path)
            except OSError:
                pass
        print("All cached data/config cleared.")
        return

    app = create_app(config_path=args.config_path, db_path=args.db_path)
    port = args.port or settings.port

    if BaseApplication:
        print(f"Starting Gunicorn server on {args.host}:{port}...")
        options = {
            "bind": f"{args.host}:{port}",
            "workers": 2,
            "threads": 4,
            "worker_class": "gthread",
            "accesslog": "-",
            "errorlog": "-",
            "timeout": 120,  # Longer timeout for video generation
        }
        StandaloneApplication(app, options).run()
    else:
        print("Gunicorn not found, falling back to Flask development server.")
        app.run(host=args.host, port=port)


if __name__ == "__main__":
    main()
