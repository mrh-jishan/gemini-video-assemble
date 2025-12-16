from pathlib import Path
from io import BytesIO
from typing import Optional
from google.genai import types
from google import genai
from PIL import Image
import requests


class GeminiImageClient:
    """
    Uses google-genai client. Supports generate_images (Imagen) or generate_content (Gemini image).
    """

    def __init__(self, api_key: str, model: str = "imagen-3.0-generate-001", method: str = "generate_images"):
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY required for gemini provider")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.method = method

    def generate(self, prompt: str, dest: Path) -> Path:
        if self.method.lower() == "generate_content":
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
            )
            
            text_parts = []

            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        try:
                            img = part.as_image()
                            img.save(dest)
                            return dest
                        except Exception as e:
                            print(f"Error saving image part: {e}")

                    if part.text:
                        text_parts.append(part.text)

            error_msg = "Gemini returned no image data."
            if text_parts:
                clean_text = " ".join(text_parts)
                error_msg += f" The model responded with text instead: '{clean_text}'"
            
            raise RuntimeError(error_msg)
        
        else:
            response = self.client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                ),
            )

            if not response.generated_images:
                raise RuntimeError("Imagen returned no images")
            
            image_obj = response.generated_images[0]

            image_bytes = None
            if hasattr(image_obj, "image") and image_obj.image:
                image_bytes = image_obj.image.image_bytes
            
            if not image_bytes:
                raise RuntimeError("Imagen response missing image payload")
            
            dest.write_bytes(image_bytes)
            return dest


class PixabayImageClient:
    """
    Simple stock image/video fetcher using Pixabay (requires API key).
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("PIXABAY_KEY required for stock provider")
        self.api_key = api_key
        self.image_url = "https://pixabay.com/api/"
        self.video_url = "https://pixabay.com/api/videos/"

    def _fetch(self, url: str, params: dict, dest: Path) -> Path:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Pixabay failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data

    def _download_image_with_validation(self, image_url: str, dest: Path) -> Path:
        """Download image with validation to ensure file integrity."""
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code != 200:
            raise RuntimeError(f"Pixabay image download failed ({img_resp.status_code})")
        if not img_resp.content or len(img_resp.content) < 1000:
            raise RuntimeError("Pixabay image download incomplete or corrupted")
        dest.write_bytes(img_resp.content)
        return dest

    def _download_video_with_fallback(self, candidates: list, dest: Path) -> Path:
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

    def generate_image(self, prompt: str, dest: Path, orientation: str = "horizontal") -> Path:
        params = {
            "key": self.api_key,
            "q": prompt,
            "image_type": "photo",
            "orientation": orientation,
            "safesearch": "true",
            "per_page": 10,
            "min_width": 1920 if orientation == "horizontal" else 1080,
            "min_height": 1080 if orientation == "horizontal" else 1920,
        }
        data = self._fetch(self.image_url, params, dest)
        hits = data.get("hits", [])
        if not hits:
            raise RuntimeError("Pixabay returned no images")
        # Prioritize highest resolution available (largeImageURL is typically 1920px wide)
        image_url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
        if not image_url:
            raise RuntimeError("Pixabay hit missing image URL")
        return self._download_image_with_validation(image_url, dest)

    def generate_video(self, search_term: str, dest: Path, target_size: tuple[int, int]) -> Path:
        params = {
            "key": self.api_key,
            "q": search_term,
            "video_type": "all",
            "safesearch": "true",
            "per_page": 5,
            "min_width": 1920,
            "min_height": 1080,
        }
        data = self._fetch(self.video_url, params, dest)
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
        
        return self._download_video_with_fallback(sorted_candidates, dest)
