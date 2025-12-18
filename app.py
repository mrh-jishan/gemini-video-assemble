from gemini_video_assemble.config import Settings
from gemini_video_assemble.config_store import ConfigStore
from gemini_video_assemble.server import create_app

app = create_app()

if __name__ == "__main__":
    settings = Settings.from_sources(ConfigStore().load())
    app.run(host="0.0.0.0", port=settings.port, debug=True)
