"""MiniMax M2 API client (OpenAI-compatible endpoint)."""
import os
import json
import time
import requests
from typing import List, Dict, Any


class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
        self.base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip().rstrip("/")
        self.model = os.environ.get("MINIMAX_MODEL", "MiniMax-M2").strip()

        if not self.api_key:
            raise RuntimeError("MINIMAX_API_KEY is not set. Add it in GitHub → Settings → Secrets.")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        Send a chat completion request. Returns the assistant's text.
        Tries OpenAI-compatible endpoint first, then MiniMax native format.
        """
        # Attempt 1: OpenAI-compatible /chat/completions
        try:
            return self._call_openai_style(messages, temperature, max_tokens)
        except Exception as e1:
            err1 = str(e1)

        # Attempt 2: MiniMax native /text/chatcompletion_v2
        try:
            return self._call_minimax_native(messages, temperature, max_tokens)
        except Exception as e2:
            raise RuntimeError(
                f"LLM call failed on both endpoints.\n"
                f"OpenAI-style error: {err1}\n"
                f"MiniMax-native error: {e2}"
            )

    def _call_openai_style(self, messages, temperature, max_tokens) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        # OpenAI-compatible shape
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        raise RuntimeError(f"Unexpected response: {json.dumps(data)[:400]}")

    def _call_minimax_native(self, messages, temperature, max_tokens) -> str:
        url = f"{self.base_url}/text/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        base = data.get("base_resp", {})
        raise RuntimeError(
            f"MiniMax native error: {base.get('status_code')} {base.get('status_msg')} — full: {json.dumps(data)[:400]}"
        )
