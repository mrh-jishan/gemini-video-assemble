import argparse
from typing import Optional

import os
import shutil

from .config import Settings
from .config_store import ConfigStore
from .server import create_app
from .storage import DataStore


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
    app.run(host=args.host, port=port)


if __name__ == "__main__":
    main()
