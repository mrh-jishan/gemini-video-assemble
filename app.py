from video_app.config import Settings
from video_app.config_store import ConfigStore
from video_app.server import create_app

app = create_app()

if __name__ == "__main__":
    settings = Settings.from_sources(ConfigStore().load())
    app.run(host="0.0.0.0", port=settings.port, debug=True)
