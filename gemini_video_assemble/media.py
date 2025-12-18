from pathlib import Path
import requests


class PixabayVideoClient:
    """Pixabay video fetcher."""

    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("PIXABAY_KEY required for video provider")
        self.api_key = api_key
        self.video_url = "https://pixabay.com/api/videos/"

    def _fetch(self, url: str, params: dict) -> dict:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Pixabay failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def _download_with_fallback(self, candidates: list, dest: Path) -> Path:
        """Download video with fallback to smaller formats if larger ones fail."""
        last_error = None
        for candidate in candidates:
            try:
                url = candidate.get("url")
                if not url:
                    continue
                print(f"Attempting to download video from {url}")
                v_resp = requests.get(url, timeout=120, stream=True)
                if v_resp.status_code != 200:
                    last_error = f"HTTP {v_resp.status_code}"
                    continue
                
                # Write content and validate file size
                content = v_resp.content
                if not content or len(content) < 100000:  # At least 100KB
                    last_error = f"Downloaded file too small ({len(content)} bytes)"
                    continue
                
                dest.write_bytes(content)
                print(f"Successfully downloaded video ({len(content)} bytes)")
                return dest
            except Exception as e:
                last_error = str(e)
                print(f"Failed to download video: {e}")
                continue
        
        raise RuntimeError(f"All video download attempts failed. Last error: {last_error}")

    def generate_video(self, search_term: str, dest: Path, target_size: tuple[int, int]) -> Path:
        """Download video matching target resolution."""
        params = {
            "key": self.api_key,
            "q": search_term,
            "video_type": "all",
            "safesearch": "true",
            "per_page": 5,
            "min_width": 1920,
            "min_height": 1080,
        }
        data = self._fetch(self.video_url, params)
        hits = data.get("hits", [])
        if not hits:
            raise RuntimeError("Pixabay returned no videos")
        
        hit = hits[0]
        videos = hit.get("videos") or {}
        candidates = []
        # Prioritize large/medium for 1080p output, build fallback chain
        for key in ("large", "medium", "small", "tiny"):
            entry = videos.get(key)
            if entry and entry.get("url"):
                candidates.append(entry)
        if not candidates:
            raise RuntimeError("Pixabay video payload missing URL")
        
        target_w = target_size[0] if target_size else 1920
        # Sort by closest to target width, keeping all as fallback chain
        sorted_candidates = sorted(
            candidates,
            key=lambda e: abs((e.get("width") or target_w) - target_w),
        )
        
        return self._download_with_fallback(sorted_candidates, dest)
