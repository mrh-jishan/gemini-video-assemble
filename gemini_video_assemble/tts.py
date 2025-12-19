from pathlib import Path
from typing import Optional

from gtts import gTTS

try:
    import boto3
except ImportError:
    boto3 = None


class TTSSynthesizer:
    def synthesize(self, text: str, dest: Path) -> Path:
        raise NotImplementedError


class GoogleTTSSynthesizer(TTSSynthesizer):
    """
    Keyless Google TTS via gTTS (relies on public translate TTS endpoint).
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang

    def synthesize(self, text: str, dest: Path) -> Path:
        tts = gTTS(text=text, lang=self.lang)
        tts.save(str(dest))
        return dest


class AmazonPollySynthesizer(TTSSynthesizer):
    """
    Amazon Polly TTS via boto3.
    """

    def __init__(
        self,
        aws_access_key_id: Optional[str],
        aws_secret_access_key: Optional[str],
        region_name: str = "us-east-1",
        voice_id: str = "Joanna",
        engine: str = "standard",
    ):
        if boto3 is None:
            raise RuntimeError("boto3 is not installed. Please install it to use Amazon Polly.")
            
        self.client = boto3.client(
            "polly",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        self.voice_id = voice_id
        self.engine = engine

    def synthesize(self, text: str, dest: Path) -> Path:
        response = self.client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=self.voice_id,
            Engine=self.engine,
        )

        if "AudioStream" in response:
            with open(dest, "wb") as f:
                f.write(response["AudioStream"].read())
        else:
            raise RuntimeError("Could not stream audio from Amazon Polly")
        
        return dest
