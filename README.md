# Prompt-to-Video Flask Service

An advanced AI-powered video generation service that transforms text prompts into complete videos with:
- **Intelligent scene planning** using Google Gemini
- **AI-powered image generation** (Gemini Imagen 3 or Hugging Face)
- **Professional narration** with Google Text-to-Speech
- **Rich multimedia audio** including background music and per-scene sound effects
- **Interactive animated subtitles** with varied effects
- **Scene break transitions** with titles and transition audio
- **Professional video assembly** with MoviePy/ffmpeg

## Features

### 🎬 Scene Planning & Narration
- Gemini AI breaks your prompt into optimized scenes
- Each scene includes:
  - Title for context
  - 2-3 sentence narration (converted to speech)
  - Visual prompt for image generation
  - Duration calculated to match total target time
  - Music mood keywords (for background music)
  - SFX keywords (for scene-specific sound effects)

### 🎨 Visual Generation
- **Gemini Imagen 3** or **Hugging Face** image generation
- Supports both **Pixabay stock images/videos** and AI-generated visuals
- Automatic image caching by hash to reduce API costs
- Responsive layout for horizontal (16:9) and vertical (9:16) aspect ratios

### 🔊 Multi-Layer Audio System
**Background Music:**
- Intelligent Freesound API integration
- Uses Gemini-provided mood keywords (e.g., "inspiring, cinematic, light")
- Automatically loops to match video duration
- 30% volume blending with main audio

**Per-Scene Sound Effects:**
- Context-aware SFX for each scene from Freesound
- Gemini generates specific keywords (e.g., "wind howling", "door opening")
- 40% volume to enhance narration without overwhelming it

**Narration:**
- Google Cloud Text-to-Speech with customizable voices
- Full-volume primary audio track

**Scene Break Audio:**
- Transition sounds (e.g., whoosh effects) between scenes
- 50% volume for subtle separation

### 📝 Interactive Animated Subtitles
- **Varied animations** that cycle through 4 different effects:
  - **Pop-in with scale** (0.5 → 1.0)
  - **Fade-in** (0.3 → 1.0 opacity)
  - **Bounce effect** (0.7 → 1.2 scale)
  - **Zoom and fade** (0.6 → 1.0 scale)
- **Dynamic font sizing** based on aspect ratio:
  - Horizontal (16:9): 65px base, alternating between 84px (emphasized) and 55px (supporting)
  - Vertical (9:16): 45px base, alternating between 58px and 38px
- **Paced text segments** to reduce visual crowding
- **Customizable styling**: font, color, stroke width/color

### 🎞️ Scene Breaks & Transitions
- 2.5-second break clips inserted between scenes
- Features:
  - Scene image as background
  - Large scene title overlay with fade effects
  - Transition sound effects (e.g., whoosh)
  - Smooth visual separation between content segments

### 🎥 Video Assembly & Effects
- **Ken Burns effect** (subtle zoom throughout scenes)
- **Crossfade transitions** between clips (configurable duration)
- **Professional encoding**: H.264 video + AAC audio at 24 fps
- **Multi-audio compositing**: Perfectly mixed narration + SFX + background music
- **Responsive dimensions**: Automatic scaling for different aspect ratios

## Quickstart

### Install from source (pip)
```bash
pip install .
# or: pip install git+https://github.com/<your-org>/gemini-video-assemble.git

# Launch server (loads ~/.gemini_video_assemble/config.json overrides + env vars)
gemini-video-server --host 0.0.0.0 --port 5000
# or:
python -m gemini_video_assemble --host 0.0.0.0 --port 5000

# Optional: purge cached data/config and renders
gemini-video-server --purge-data
```
Open `http://localhost:5000` to use the UI. A **Runtime Config** panel in the browser lets you set API keys and defaults without restarting. Values plus run history are saved to SQLite at `~/.gemini_video_assemble/data.db` (safe to delete with `--purge-data`).

### 1. System Requirements
```bash
# macOS
brew install python@3.12 ffmpeg

# Linux (Ubuntu/Debian)
sudo apt-get install python3.12 python3.12-venv ffmpeg

# Or use pyenv (recommended)
pyenv install 3.12.0 --skip-existing
pyenv virtualenv 3.12.0 videogen
pyenv local 3.12.0
```

### 2. Setup
```bash
# Clone and navigate
cd /path/to/VisaGuidanceBD-NB

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file with:

```bash
# Required APIs
GOOGLE_API_KEY=your_google_api_key_here
FREESOUND_KEY=your_freesound_api_key_here
PIXABAY_KEY=your_pixabay_api_key_here  # Optional, for stock images

# Model Configuration
GEMINI_TEXT_MODEL=gemini-2.5-flash
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image

# Text-to-Speech
TTS_LANG=en
TTS_VOICE=en-US-JennyNeural

# Video Assembly
CROSSFADE_SEC=0.6          # Crossfade duration between clips
KENBURNS_ZOOM=0.04         # Subtle zoom effect strength
SUBTITLES_ENABLED=1        # Enable/disable subtitles

# Subtitle Styling
SUBTITLE_FONT=Arial.ttf
SUBTITLE_FONTSIZE=60
SUBTITLE_COLOR=white
SUBTITLE_STROKE_COLOR=black
SUBTITLE_STROKE_WIDTH=1

# Output
OUTPUT_DIR=./renders
```

### 4. Run the Server
```bash
python app.py
```
Server runs on `http://localhost:5000`

### Optional: With Gunicorn
```bash
pip install gunicorn
gunicorn -b 0.0.0.0:5000 app:app
```

### Optional: Docker
```bash
# Build
docker build -t prompt-video .

# Run
docker run --rm -p 5000:5000 --env-file .env prompt-video
```

## API Usage

### Generate Video
```bash
curl -X POST http://localhost:5000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The history of the Silk Road trade routes and their impact on civilizations",
    "duration": 120,
    "scenes": 4,
    "aspect": "horizontal",
    "image_provider": "gemini"
  }'
```

**Response:**
```json
{
  "status": "ok",
  "path": "renders/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp4"
}
```

### Download Video
```bash
curl http://localhost:5000/api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp4 -o video.mp4
```

### Runtime Config API
Configure keys and defaults without restarting:
```bash
# Read current effective config (secrets masked)
curl http://localhost:5000/api/config

# Update keys (persisted to ~/.gemini_video_assemble/config.json)
curl -X POST http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"GOOGLE_API_KEY": "your-key", "FREESOUND_KEY": "..." }'
```

### Run History API
SQLite-backed history and caching is enabled by default (stored at `~/.gemini_video_assemble/data.db`):
```bash
curl http://localhost:5000/api/runs
# returns the latest runs with ids, status, and output paths (if finished)
```

### Health Check
```bash
curl http://localhost:5000/health
```

## Web UI

Navigate to `http://localhost:5000/` for an interactive form to generate videos without using curl.

## Example Video Flow

When you submit this prompt:
```
"The journey of a coffee bean from farm to cup in Ethiopia"
```

The system:

1. **Plans scenes** with Gemini:
   ```json
   {
     "scenes": [
       {
         "title": "Farm Harvest",
         "narration": "In the highlands of Ethiopia, coffee farmers carefully pick ripe cherries by hand...",
         "visual_prompt": "Ethiopian coffee farmers harvesting red coffee cherries on misty mountain slopes",
         "duration_sec": 20,
         "search_terms": "coffee harvest Ethiopia farm",
         "music_keywords": "earthy, natural, ambient, traditional",
         "sfx_keywords": "birds chirping, rustling leaves"
       },
       {
         "title": "Processing",
         "narration": "The harvested cherries are transported to processing facilities where they undergo fermentation...",
         "visual_prompt": "Traditional coffee processing with fermentation tanks in Ethiopian facility",
         "duration_sec": 20,
         "search_terms": "coffee processing fermentation",
         "music_keywords": "rhythmic, industrial, energetic",
         "sfx_keywords": "water flowing, machinery grinding"
       }
     ]
   }
   ```

2. **Generates assets**:
   - Images via Gemini Imagen 3
   - Narration via Google TTS
   - Background music via Freesound (using "earthy, natural, ambient")
   - Scene SFX via Freesound (e.g., "birds chirping", "water flowing")
   - Transition audio for breaks (whoosh effects)

3. **Assembles video** with:
   ```
   Timeline (2-minute video example):
   
   [Scene 1: Farm Harvest] - 20s
   ├─ Video: AI-generated farm image with Ken Burns zoom
   ├─ Audio Layer 1: Narration (100% volume)
   ├─ Audio Layer 2: "birds chirping" SFX (40% volume)
   └─ Audio Layer 3: "earthy, natural" background music (30% volume)
   └─ Subtitles: Animated narration with pop-in effect
   
   [BREAK 1: "Farm Harvest" Title] - 2.5s
   ├─ Visual: Farm image with large title overlay
   ├─ Audio: "whoosh" transition sound (50% volume)
   └─ Fade effects on title
   
   [Scene 2: Processing] - 20s
   ├─ Video: Processing facility image
   ├─ Audio Layer 1: Narration (100%)
   ├─ Audio Layer 2: "water flowing, machinery" SFX (40%)
   └─ Audio Layer 3: Background music continues (30%)
   └─ Subtitles: Animated with fade-in effect
   
   [BREAK 2: "Processing" Title] - 2.5s
   ... and so on
   
   Throughout entire video:
   └─ Background music: "earthy, natural, ambient" track 
      auto-looped to match 2-min duration
   ```

4. **Outputs**: Complete MP4 video with all audio perfectly mixed

## Audio Mixing Details

The final video combines multiple audio tracks at optimized volumes:

```
Per-Scene Audio Mix:
┌─ Narration (100% baseline)
│  └─ CompositeAudioClip with SFX
│     ├─ Narration (100%)
│     └─ Scene SFX (40% volume)
│
└─ Global Background Music (30% volume)
   ├─ Auto-loops to match video duration
   ├─ Composited over entire final video
   └─ Never clips despite multiple tracks

Break Audio Mix:
├─ Transition SFX (50% volume)
├─ (Optional background music continues)
└─ Silent periods for dramatic effect

Result: Professional, balanced mix where:
- Narration is always primary (heard clearly)
- SFX enhances without drowning narration
- Background music sets mood without competition
- All tracks play simultaneously without clipping
```

## Configuration

All settings are loaded from `.env`:

```python
# gemini_video_assemble/config.py
class Settings:
    # API Keys
    google_api_key: str              # Google Gemini + TTS
    freesound_key: str               # Background music + SFX
    pixabay_key: str                 # Stock images/videos
    
    # Models
    gemini_text_model: str           # "gemini-2.5-flash"
    gemini_image_model: str          # "gemini-2.5-flash-image"
    
    # Text-to-Speech
    tts_lang: str                    # "en"
    tts_voice: str                   # "en-US-JennyNeural"
    
    # Video Assembly
    crossfade_sec: float             # 0.6
    kenburns_zoom: float             # 0.04
    enable_subtitles: bool           # True
    
    # Subtitle Styling
    subtitle_font: str               # "Arial.ttf"
    subtitle_fontsize: int           # 60
    subtitle_color: str              # "white"
    subtitle_stroke_color: str       # "black"
    subtitle_stroke_width: int       # 1
    
    # Output
    output_dir: Path                 # "./renders"
    default_aspect: str              # "horizontal"
```

## Project Structure

```
VisaGuidanceBD-NB/
├── app.py                    # Flask WSGI entry point
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker configuration
├── .env                     # Environment variables (not in git)
├── README.md               # Original documentation
├── renders/                # Output video directory
├── image-cache/            # Cached images by hash
└── gemini_video_assemble/
    ├── __init__.py
    ├── config.py           # Settings & environment loading
    ├── models.py           # Scene dataclass with all metadata
    ├── planner.py          # Gemini scene planning
    ├── images.py           # Image generation (Gemini + Pixabay)
    ├── media.py            # Video fetching (Pixabay)
    ├── tts.py              # Text-to-Speech (Google Cloud)
    ├── music.py            # Audio fetching (Freesound)
    ├── assembler.py        # Video assembly, effects, audio mixing
    ├── pipeline.py         # Orchestration workflow
    ├── server.py           # Flask routes
    └── templates/
        └── index.html      # Web UI form
```

## Key Technologies

- **Python 3.12+** - Core language
- **Flask** - Web framework
- **Google Gemini API** - Scene planning & image generation
- **Google Cloud Text-to-Speech** - Professional narration
- **Freesound API** - Background music & sound effects
- **MoviePy 1.0+** - Video composition, effects, audio mixing
- **FFmpeg** - Audio/video encoding and processing
- **Pixabay API** (optional) - Stock images/videos

## Performance Notes

- **First run**: ~2-3 minutes per video (API calls + generation)
- **Cached runs**: ~1-2 minutes (images cached, reused for similar scenes)
- **Output size**: Typically 1-2 GB for 2-3 minute videos
- **Typical costs** (with free tier APIs): ~$0.05-0.15 per 2-minute video
- **Audio processing**: <10 seconds for multi-track mixing regardless of video length

## Troubleshooting

### Background music not playing
- Check `FREESOUND_KEY` is set in `.env`
- Verify Freesound account has API credits
- Check console logs for "Searching background music" message
- Fallback searches simplified keywords (first word only) if complex query fails
- Try with simpler music keywords in Gemini prompt

### SFX not generating
- Ensure `FREESOUND_KEY` is valid
- Check internet connection
- Review planner output for `sfx_keywords` in scene JSON
- Freesound may not have audio matching keywords (check logs)

### Subtitles not appearing
- Check `SUBTITLES_ENABLED=1` in `.env`
- Verify font file exists (e.g., `Arial.ttf` on system)
- Check text is included in scene narration
- Try with default font if custom font fails

### Image generation failing
- Verify `GOOGLE_API_KEY` has Imagen API access
- If using Pixabay, check `PIXABAY_KEY` is set and valid
- Check API quota limits in Google Cloud Console
- Ensure you have available credits

### Video assembly slow
- Reduce scene count or video duration
- Lower `KENBURNS_ZOOM` to 0 to skip complex transformations
- Use stock images (`image_provider: stock`) instead of AI generation
- Check system memory and CPU availability

### Audio mixing issues
- Check all audio files were generated (check temp directory)
- Verify Freesound audio files downloaded successfully
- Try reducing `background_music` volume if clipping occurs
- Ensure enough disk space for temp audio files

## API Keys Setup

### Google API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable APIs:
   - Gemini API
   - Imagen API
   - Cloud Text-to-Speech API
4. Create API key (Credentials → Create Credentials → API Key)
5. Add to `.env` as `GOOGLE_API_KEY=your_key`

### Freesound API Key
1. Sign up at [Freesound.org](https://freesound.org)
2. Go to Settings → API Access
3. Create an API token
4. Add to `.env` as `FREESOUND_KEY=your_key`

### Pixabay API Key (Optional)
1. Sign up at [Pixabay.com](https://pixabay.com)
2. Go to API → Dashboard
3. Copy your API key
4. Add to `.env` as `PIXABAY_KEY=your_key`

## Notes & Best Practices

- **Prompts**: Keep concise (50-100 words) for faster processing and lower costs
- **Duration**: 60-180 seconds recommended for balanced results
- **Scenes**: 3-6 scenes optimal
  - Fewer scenes = longer per scene
  - More scenes = shorter per scene + more breaks
- **Aspect Ratio**: 
  - 16:9 (horizontal) for YouTube, website
  - 9:16 (vertical) for TikTok, Instagram Reels
- **Caching**: Identical visual prompts reuse cached images - great for iterative refinement
- **Audio**: 
  - All audio tracks are perfectly synchronized by MoviePy
  - Freesound previews (~30-45 seconds) are used for music/SFX
  - Background music auto-loops without gaps
  - Volume levels optimized to prevent clipping

## Example Workflows

### Workflow 1: Educational Content
```bash
curl -X POST http://localhost:5000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "World War II causes: Economic factors, Rise of fascism, Treaty of Versailles, Militarism",
    "duration": 300,
    "scenes": 6,
    "aspect": "horizontal",
    "image_provider": "gemini"
  }'
```
Result: 5-minute educational video with historical images, narrator explains causes, dramatic background music, scene breaks between topics.

### Workflow 2: Travel Vlog
```bash
curl -X POST http://localhost:5000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Tokyo travel guide: Shibuya crossing, Senso-ji temple, Tsukiji market, Mount Fuji views",
    "duration": 120,
    "scenes": 4,
    "aspect": "vertical",
    "image_provider": "stock"
  }'
```
Result: 2-minute vertical video (TikTok ready) with Pixabay stock footage, travel descriptions, Asian-inspired music, scene breaks.

### Workflow 3: Product Marketing
```bash
curl -X POST http://localhost:5000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Product launch video for eco-friendly water bottle: sustainable materials, keeps drinks cold 24 hours, stylish design, available in 5 colors",
    "duration": 90,
    "scenes": 3,
    "aspect": "horizontal",
    "image_provider": "gemini"
  }'
```
Result: Professional product video with AI-generated product images, marketing copy, upbeat music, clean scene breaks.

## Contributing

To add new features:
1. Modify relevant module in `gemini_video_assemble/`
2. Update pipeline orchestration in `pipeline.py` if needed
3. Test with `/api/render` endpoint
4. Update README with new settings/examples
5. Submit pull request with description

## Common Customizations

### Change subtitle animation effects
Edit `_apply_subtitle_effect()` in `gemini_video_assemble/assembler.py` - modify effects array (currently 4 effects).

### Adjust audio volumes
In `gemini_video_assemble/assembler.py`:
- Line ~220: SFX volume (currently 40%)
- Line ~330: Background music volume (currently 30%)
- Line ~240: Break audio volume (currently 50%)

### Modify break clip duration
In `gemini_video_assemble/pipeline.py`, change `break_duration=2.5` to desired seconds.

### Change Ken Burns zoom strength
In `.env`: `KENBURNS_ZOOM=0.04` (higher = more dramatic zoom)

### Customize subtitle text styling
In `.env`:
- `SUBTITLE_FONT=Arial.ttf`
- `SUBTITLE_COLOR=white`
- `SUBTITLE_STROKE_COLOR=black`
- `SUBTITLE_STROKE_WIDTH=1`

## License

See [LICENSE](LICENSE)

## Support

For issues or questions:
1. Check console logs for error messages
2. Review troubleshooting section above
3. Verify all `.env` variables are set correctly
4. Check API key quotas and permissions
5. Ensure ffmpeg is installed and on PATH
