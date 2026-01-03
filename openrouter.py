import os
from dotenv import load_dotenv
import json
import urllib.request
from typing import Dict

load_dotenv()

class OpenRouterLLM:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "google/gemma-3n-e2b-it:free",
        timeout: int = 30,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        self.model = model
        self.timeout = timeout
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "headers": [
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "AI Log Whisperer",
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.2,   # low creativity, high discipline
            "max_tokens": 400,
        }

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(
                f"Unexpected OpenRouter response: {body}"
            ) from e


