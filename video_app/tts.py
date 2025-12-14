from pathlib import Path

from gtts import gTTS


class GoogleTTSSynthesizer:
    """
    Keyless Google TTS via gTTS (relies on public translate TTS endpoint).
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang

    def synthesize(self, text: str, dest: Path) -> Path:
        tts = gTTS(text=text, lang=self.lang)
        tts.save(str(dest))
        return dest
