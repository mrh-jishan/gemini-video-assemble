from flask import Flask, jsonify, render_template, request, send_file

from .config import Settings
from .config_store import ConfigStore
from .pipeline import VideoPipeline
from .storage import DataStore


def create_app(config_path: str | None = None, db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    data_store = DataStore(db_path)
    config_store = ConfigStore(config_path)

    def current_settings() -> Settings:
        return Settings.from_sources(config_store.load())

    def build_pipeline() -> VideoPipeline:
        return VideoPipeline(current_settings())

    @app.route("/api/render", methods=["POST"])
    def render_video():
        body = request.get_json(force=True, silent=True) or {}
        prompt = body.get("prompt")
        duration = int(body.get("duration", 60))
        scenes = int(body.get("scenes", 5))
        aspect = body.get("aspect") or current_settings().default_aspect
        image_provider = body.get("image_provider")

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        run_id = data_store.record_run(
            prompt=prompt,
            duration=duration,
            scenes=scenes,
            aspect=aspect,
            image_provider=image_provider or current_settings().default_image_provider,
            status="pending",
        )
        try:
            output_path = build_pipeline().build_video_from_prompt(
                prompt, duration, scenes, aspect, image_provider
            )
            data_store.update_run(run_id, status="completed", output_path=str(output_path))
        except Exception as exc:  # noqa: BLE001
            data_store.update_run(run_id, status="failed", error=str(exc))
            return jsonify({"error": str(exc)}), 500

        return jsonify({"status": "ok", "path": str(output_path), "run_id": run_id})

    @app.route("/api/config", methods=["GET"])
    def get_config():
        settings = current_settings()
        overrides = config_store.load()
        for key in ("GOOGLE_API_KEY", "PIXABAY_KEY", "FREESOUND_KEY"):
            if key in overrides and overrides[key]:
                overrides[key] = f"{overrides[key][:4]}***"
        return jsonify(
            {
                "config": settings.to_public_dict(mask_secrets=True),
                "overrides": overrides,
            }
        )

    @app.route("/api/config", methods=["POST"])
    def update_config():
        payload = request.get_json(force=True, silent=True) or {}
        saved = config_store.update(payload)
        settings = Settings.from_sources(saved)
        return jsonify({"status": "ok", "config": settings.to_public_dict(mask_secrets=True)})

    @app.route("/api/download/<path:filename>", methods=["GET"])
    def download(filename: str):
        path = current_settings().output_dir / filename
        if not path.exists():
            return jsonify({"error": "file not found"}), 404
        return send_file(path, mimetype="video/mp4", as_attachment=True)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/runs", methods=["GET"])
    def runs():
        return jsonify({"runs": data_store.list_runs(limit=25)})

    @app.route("/", methods=["GET", "POST"])
    def ui():
        settings = current_settings()
        prompt = ""
        duration = 60
        scenes = 5
        aspect = settings.default_aspect
        image_provider = settings.default_image_provider
        video_path = None
        error = None
        config_saved = None
        runs = data_store.list_runs(limit=10)

        if request.method == "POST":
            form = request.form or {}
            form_type = form.get("form_type", "render")
            if form_type == "config":
                updates = {
                    "GOOGLE_API_KEY": form.get("google_api_key") or None,
                    "PIXABAY_KEY": form.get("pixabay_key") or None,
                    "FREESOUND_KEY": form.get("freesound_key") or None,
                    "GEMINI_TEXT_MODEL": form.get("gemini_text_model") or None,
                    "GEMINI_IMAGE_MODEL": form.get("gemini_image_model") or None,
                    "TTS_LANG": form.get("tts_lang") or None,
                    "TTS_VOICE": form.get("tts_voice") or None,
                    "DEFAULT_IMAGE_PROVIDER": form.get("default_image_provider") or None,
                    "OUTPUT_DIR": form.get("output_dir") or None,
                    "PORT": form.get("port") or None,
                }
                config_store.update(updates)
                config_saved = "Configuration saved. New requests will use these values."
                settings = current_settings()
                aspect = settings.default_aspect
                image_provider = settings.default_image_provider
            else:
                prompt = form.get("prompt", "").strip()
                duration = int(form.get("duration") or 60)
                scenes = int(form.get("scenes") or 5)
                aspect = form.get("aspect") or settings.default_aspect
                image_provider = form.get("image_provider") or settings.default_image_provider
                if not prompt:
                    error = "Prompt is required."
                else:
                    try:
                        video_path = build_pipeline().build_video_from_prompt(
                            prompt, duration, scenes, aspect, image_provider
                        )
                    except Exception as exc:  # noqa: BLE001
                        error = str(exc)

        return render_template(
            "index.html",
            prompt=prompt,
            duration=duration,
            scenes=scenes,
            aspect=aspect,
            image_provider=image_provider,
            video_path=video_path,
            error=error,
            config_saved=config_saved,
            settings=settings,
            runs=runs,
        )

    return app
