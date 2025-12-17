from pathlib import Path
import requests


class PixabayMusicClient:
    """Pixabay background music fetcher."""

    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("PIXABAY_KEY required for music provider")
        self.api_key = api_key
        # FIX: Use the Audio endpoint, not Video
        self.music_url = "https://pixabay.com/api/audio/"

    def _fetch(self, url: str, params: dict) -> dict:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Pixabay failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def _download_with_fallback(self, candidates: list, dest: Path) -> Path:
        last_error = None
        for url in candidates: # Candidates are now just direct URLs
            try:
                if not url: continue
                print(f"Attempting to download background music from {url}")
                m_resp = requests.get(url, timeout=120, stream=True)
                
                if m_resp.status_code != 200:
                    last_error = f"HTTP {m_resp.status_code}"
                    continue
                
                content = m_resp.content
                if not content or len(content) < 50000:
                    last_error = f"Downloaded file too small ({len(content)} bytes)"
                    continue
                
                dest.write_bytes(content)
                print(f"Successfully downloaded background music ({len(content)} bytes)")
                return dest
            except Exception as e:
                last_error = str(e)
                print(f"Failed to download music: {e}")
                continue
        
        raise RuntimeError(f"All music download attempts failed. Last error: {last_error}")

    def generate_background_music(self, search_term: str, dest: Path) -> Path:
        """Download background music from Pixabay."""
        params = {
            "key": self.api_key,
            "q": search_term,
            "order": "popular",
            "per_page": 3,
            "category": "music" # Optional but helpful
        }
        data = self._fetch(self.music_url, params)
        hits = data.get("hits", [])
        if not hits:
            raise RuntimeError("Pixabay returned no background music")
        
        # FIX: The Audio API structure is different from Video API
        # It returns a list of hits where 'url' is the direct download link
        candidates = []
        for hit in hits:
            # Pixabay Audio object usually has 'url' or 'download' field
            # We collect the URLs from the top 3 hits to try
            if hit.get("url"):
                candidates.append(hit.get("url"))
        
        if not candidates:
            raise RuntimeError("Pixabay music payload missing URL")
        
        return self._download_with_fallback(candidates, dest)