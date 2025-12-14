from pathlib import Path
from io import BytesIO
from google.genai import types
from google import genai
from PIL import Image


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
