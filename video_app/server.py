from flask import Flask, jsonify, render_template, request, send_file

from .config import Settings
from .pipeline import build_video_from_prompt


def create_app() -> Flask:
    app = Flask(__name__)
    settings = Settings()

    @app.route("/api/render", methods=["POST"])
    def render_video():
        body = request.get_json(force=True, silent=True) or {}
        prompt = body.get("prompt")
        duration = int(body.get("duration", 60))
        scenes = int(body.get("scenes", 5))
        aspect = body.get("aspect") or settings.default_aspect

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        try:
            output_path = build_video_from_prompt(prompt, duration, scenes, aspect)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": str(exc)}), 500

        return jsonify({"status": "ok", "path": str(output_path)})

    @app.route("/api/download/<path:filename>", methods=["GET"])
    def download(filename: str):
        path = settings.output_dir / filename
        if not path.exists():
            return jsonify({"error": "file not found"}), 404
        return send_file(path, mimetype="video/mp4", as_attachment=True)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/", methods=["GET", "POST"])
    def ui():
        prompt = ""
        duration = 60
        scenes = 5
        aspect = settings.default_aspect
        image_provider = settings.default_image_provider
        video_path = None
        error = None

        if request.method == "POST":
            form = request.form or {}
            prompt = form.get("prompt", "").strip()
            duration = int(form.get("duration") or 60)
            scenes = int(form.get("scenes") or 5)
            aspect = form.get("aspect") or settings.default_aspect
            image_provider = form.get("image_provider") or settings.default_image_provider
            if not prompt:
                error = "Prompt is required."
            else:
                try:
                    video_path = build_video_from_prompt(
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
        )

    return app
