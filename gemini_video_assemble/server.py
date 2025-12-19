from flask import Flask, jsonify, render_template, request, send_file, redirect, url_for
import threading

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

        if image_provider not in {"gemini", "stock"}:
            return jsonify({"error": "image_provider must be 'gemini' or 'stock'"}), 400

        run_id = data_store.record_run(
            prompt=prompt,
            duration=duration,
            scenes=scenes,
            aspect=aspect,
            image_provider=image_provider,
            status="pending",
        )

        def _background_render(r_id, p, d, s, a, i):
            try:
                output_path = build_pipeline().build_video_from_prompt(p, d, s, a, i)
                data_store.update_run(r_id, status="completed", output_path=str(output_path))
            except Exception as exc:
                data_store.update_run(r_id, status="failed", error=str(exc))
                print(f"Background render failed for run {r_id}: {exc}")

        thread = threading.Thread(
            target=_background_render,
            args=(run_id, prompt, duration, scenes, aspect, image_provider),
        )
        thread.start()

        return jsonify({"status": "submitted", "run_id": run_id, "message": "Video generation started in background"})

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
        image_provider = "stock"
        video_path = None
        error = None
        if request.method == "POST":
            form = request.form or {}
            prompt = form.get("prompt", "").strip()
            duration = int(form.get("duration") or 60)
            scenes = int(form.get("scenes") or 5)
            aspect = form.get("aspect") or settings.default_aspect
            image_provider = form.get("image_provider") or "stock"
            if not prompt:
                error = "Prompt is required."
            else:
                run_id = data_store.record_run(
                    prompt=prompt,
                    duration=duration,
                    scenes=scenes,
                    aspect=aspect,
                    image_provider=image_provider,
                    status="pending",
                )
                try:
                    output_path = build_pipeline().build_video_from_prompt(
                        prompt, duration, scenes, aspect, image_provider
                    )
                    data_store.update_run(run_id, status="completed", output_path=str(output_path))
                    video_path = output_path
                except Exception as exc:  # noqa: BLE001
                    data_store.update_run(run_id, status="failed", error=str(exc))
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
            settings=settings,
        )

    @app.route("/config", methods=["GET", "POST"]) 
    def config_page():
        settings = current_settings()
        message = None
        if request.method == "POST":
            form = request.form or {}
            updates = {
                "GOOGLE_API_KEY": form.get("google_api_key") or None,
                "PIXABAY_KEY": form.get("pixabay_key") or None,
                "FREESOUND_KEY": form.get("freesound_key") or None,
                "GEMINI_TEXT_MODEL": form.get("gemini_text_model") or None,
                "GEMINI_IMAGE_MODEL": form.get("gemini_image_model") or None,
                "TTS_PROVIDER": form.get("tts_provider") or None,
                "TTS_LANG": form.get("tts_lang") or None,
                "AWS_ACCESS_KEY_ID": form.get("aws_access_key_id") or None,
                "AWS_SECRET_ACCESS_KEY": form.get("aws_secret_access_key") or None,
                "AWS_REGION": form.get("aws_region") or None,
                "POLLY_VOICE_ID": form.get("polly_voice_id") or None,
                "POLLY_ENGINE": form.get("polly_engine") or None,
                "OUTPUT_DIR": form.get("output_dir") or None,
            }
            config_store.update(updates)
            message = "Configuration saved. New requests will use these values."
            settings = current_settings()
        return render_template("config.html", settings=settings, message=message)

    @app.route("/history", methods=["GET"]) 
    def history_page():
        runs = data_store.list_runs(limit=100)
        return render_template("history.html", runs=runs)

    return app
