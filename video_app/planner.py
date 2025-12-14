import json
from typing import List

from google import genai

from .models import Scene


class ScenePlanner:
    def __init__(self, client: genai.Client, model: str):
        self.client = client
        self.model = model

    def plan(self, prompt: str, total_duration: int, target_scenes: int) -> List[Scene]:
        instruction = (
            "You are a film director. Break the topic into short scenes. "
            "Return JSON with a 'scenes' array only. Each scene needs: "
            "title, narration (2-3 sentences), visual_prompt, and duration_sec "
            f"(so total is close to {total_duration} seconds)."
        )
        
        full_prompt = f"{instruction}\n\nTopic: {prompt}\nTarget scenes: {target_scenes}"

        schema = {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "narration": {"type": "string"},
                            "visual_prompt": {"type": "string"},
                            "duration_sec": {"type": "number"},
                        },
                        "required": [
                            "title", 
                            "narration", 
                            "visual_prompt", 
                            "duration_sec"
                        ],
                    },
                }
            },
            "required": ["scenes"],
        }

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": full_prompt}],
                },
            ],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )

        body = json.loads(response.text)

        scenes = []
        for raw in body.get("scenes", []):
            scenes.append(
                Scene(
                    title=raw["title"],
                    narration=raw["narration"],
                    visual_prompt=raw["visual_prompt"],
                    duration_sec=max(3.0, float(raw["duration_sec"])),
                )
            )
        if not scenes:
            raise RuntimeError("LLM returned no scenes")
        scenes = scenes[:target_scenes]
        total = sum(s.duration_sec for s in scenes)
        if total > 0:
            scale = float(total_duration) / total
            for s in scenes:
                s.duration_sec = max(3.0, s.duration_sec * scale)
        return scenes


class PromptBuilder:
    def __init__(self, global_style: str):
        self.global_style = global_style

    def build(self, scene: Scene) -> str:
        return (
            f"{scene.visual_prompt}. "
            f"Shot composition: cinematic 16:9, gentle camera movement. "
            f"Style: {self.global_style}."
        )
