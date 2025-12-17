from pathlib import Path
import requests


class FreesoundClient:
    """Freesound background music and sound effect fetcher."""

    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("FREESOUND_KEY required for music/sound provider")
        self.api_key = api_key
        self.api_url = "https://freesound.org/apiv2/search/text/"

    def _fetch(self, params: dict) -> dict:
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        # Log outgoing request (without exposing token)
        try:
            print(f"[Freesound] GET {self.api_url} params={params}")
        except Exception:
            pass
        resp = requests.get(self.api_url, params=params, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Freesound failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def _download_with_fallback(self, candidates: list, dest: Path) -> Path:
        """Download audio with fallback to lower quality if needed."""
        last_error = None
        for audio_url in candidates:
            try:
                if not audio_url:
                    continue
                print(f"Attempting to download audio from {audio_url}")
                a_resp = requests.get(audio_url, timeout=120, stream=True)
                
                if a_resp.status_code != 200:
                    last_error = f"HTTP {a_resp.status_code}"
                    continue
                
                content = a_resp.content
                if not content or len(content) < 50000:  # At least 50KB for audio
                    last_error = f"Downloaded file too small ({len(content)} bytes)"
                    continue
                
                dest.write_bytes(content)
                print(f"Successfully downloaded audio ({len(content)} bytes)")
                return dest
            except Exception as e:
                last_error = str(e)
                print(f"Failed to download audio: {e}")
                continue
        
        raise RuntimeError(f"All audio download attempts failed. Last error: {last_error}")

    def generate_background_music(self, search_term: str, dest: Path) -> Path:
        """Download background music or ambient sound from Freesound."""
        params = {
            "query": f"{search_term} ambient OR background OR music",
            "filter": "duration:[10 TO 600]",  # 10 seconds to 10 minutes
            "sort": "rating_desc",
            "page_size": 5,
            "fields": "id,name,previews,download"
        }
        # High-level log before request
        try:
            print(f"[Freesound] Searching background music for query='{search_term}' with params={params}")
        except Exception:
            pass
        data = self._fetch(params)
        results = data.get("results", [])
        print(f"[Freesound] Background music results: {len(results)} found")
        if not results:
            raise RuntimeError("Freesound returned no background music")
        
        # Collect download URLs from top results
        candidates = []
        for result in results:
            # Freesound provides previews and direct download link
            if result.get("previews") and result["previews"].get("preview-hq-mp3"):
                candidates.append(result["previews"]["preview-hq-mp3"])
            elif result.get("previews") and result["previews"].get("preview-lq-mp3"):
                candidates.append(result["previews"]["preview-lq-mp3"])
        
        try:
            print(f"[Freesound] Background music candidate previews (up to 3): {candidates[:3]}")
        except Exception:
            pass

        if not candidates:
            raise RuntimeError("Freesound results missing audio previews")
        
        return self._download_with_fallback(candidates, dest)

    def generate_sound_effect(self, effect_name: str, dest: Path) -> Path:
        """Download a specific sound effect from Freesound."""
        params = {
            "query": effect_name,
            "filter": "duration:[0.5 TO 10]",  # 0.5 seconds to 10 seconds for SFX
            "sort": "rating_desc",
            "page_size": 5,
            "fields": "id,name,previews,download"
        }
        try:
            print(f"[Freesound] Searching sound effect '{effect_name}' with params={params}")
        except Exception:
            pass
        data = self._fetch(params)
        results = data.get("results", [])
        print(f"[Freesound] Sound effect results: {len(results)} found")
        if not results:
            raise RuntimeError(f"Freesound returned no sound effects for '{effect_name}'")
        
        # Collect download URLs from top results
        candidates = []
        for result in results:
            if result.get("previews") and result["previews"].get("preview-hq-mp3"):
                candidates.append(result["previews"]["preview-hq-mp3"])
            elif result.get("previews") and result["previews"].get("preview-lq-mp3"):
                candidates.append(result["previews"]["preview-lq-mp3"])
        
        try:
            print(f"[Freesound] SFX candidate previews (up to 3): {candidates[:3]}")
        except Exception:
            pass

        if not candidates:
            raise RuntimeError("Freesound results missing audio previews")
        
        return self._download_with_fallback(candidates, dest)
