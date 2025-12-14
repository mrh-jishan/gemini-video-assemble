# Prompt-to-Video Flask Service

This service turns a text prompt into a stitched video by combining:
- Scene planning with a Gemini model
- Image generation via Gemini Imagen 3 (or Hugging Face Inference)
- Scene-level narration with keyless Edge TTS
- Assembly with MoviePy/ffmpeg

## Quickstart
1) System deps: Python 3.11 (pyenv respected via `.python-version`), ffmpeg on `PATH`.
2) Create env:
   ```bash
   pyenv install 3.11.0 --skip-existing
   pyenv virtualenv 3.11.0 videogen
   pyenv local 3.11.0
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3) Set environment variables:
   - `GOOGLE_API_KEY` (required; used for Gemini text + Imagen)
   - `GEMINI_TEXT_MODEL` (default `gemini-1.5-flash`) and `GEMINI_IMAGE_MODEL` (default `imagen-3.0-generate-001`). The code auto-selects image method: Imagen models use `generate_images`, others use `generate_content`.
   - TTS: Google via gTTS (keyless): set `TTS_LANG` (default `en`)
   - Visual feel & assembly knobs: `IMAGE_STYLE`, `CROSSFADE_SEC` (default `0.6`), `KENBURNS_ZOOM` (default `0.04`), `SUBTITLES_ENABLED` (default on), `SUBTITLE_FONT`, `SUBTITLE_FONTSIZE`, `SUBTITLE_COLOR`, `SUBTITLE_STROKE_COLOR`, `SUBTITLE_STROKE_WIDTH`.
4) Run the server: `python app.py`

### Optional UI
- Navigate to `http://localhost:5000/` for a minimal form (Jinja template) to create renders without a REST client.

## Running with Gunicorn
- Local: `gunicorn -b 0.0.0.0:5000 app:app`

## Docker
1) Build: `docker build -t prompt-video .`
2) Run: `docker run --rm -p 5000:5000 --env-file .env prompt-video`

## API
- `POST /api/render`
  - Body: `{"prompt":"long-form topic", "duration":90, "scenes":5}`
  - Response: `{"status":"ok","path":"renders/<uuid>.mp4"}`
- `GET /api/download/<uuid>.mp4` streams the rendered video.
- `GET /health` for readiness checks.

## Notes
- The app generates narration and imagery per scene, then stitches clips at 24 fps with AAC audio.
- Image prompts are cached by hash so repeated scenes reuse the same frame and save cost.
- Keep prompts concise for cheaper runs; default stack uses Gemini + keyless gTTS to avoid upfront spend.
- Add your preferred logging/monitoring and swap providers easily (see modules under `video_app/`).

## Project layout
- `app.py`: WSGI entrypoint
- `video_app/config.py`: settings/env wiring
- `video_app/planner.py`: LLM scene planning + prompt styling
- `video_app/images.py`: image providers + cache
- `video_app/tts.py`: text-to-speech
- `video_app/assembler.py`: video stitching, transitions, subtitles
- `video_app/pipeline.py`: orchestration
- `video_app/server.py`: Flask routes
