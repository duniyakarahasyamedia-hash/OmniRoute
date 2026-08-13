"""LLM client — talks to OmniRoute (OpenAI-compatible) or any OpenAI-compatible API."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

import requests

log = logging.getLogger("omnishorts.llm")

SYSTEM_PROMPT = (
    "You are a viral Hindi YouTube Shorts scriptwriter for a mystery/facts channel "
    "called 'Duniya Ka Rahasya'. Write short, punchy Hindi sentences that a 10-year-old "
    "can understand. Use simple Devanagari Hindi, no English transliteration."
)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = (cfg.get("base_url") or "").rstrip("/")
        self.api_key = cfg.get("api_key") or ""
        self.model = cfg.get("model") or "auto"
        self.temperature = float(cfg.get("temperature", 0.8))
        self.timeout = int(cfg.get("timeout", 60))

    def available(self) -> bool:
        return bool(self.base_url) and self.base_url not in ("http://localhost:8787/v1",)

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def chat(self, messages: list[dict]) -> Optional[str]:
        """Returns assistant text or None on failure."""
        if not self.available():
            return None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 1024,
        }
        try:
            log.debug("LLM request -> %s", self._endpoint())
            resp = requests.post(
                self._endpoint(), headers=headers, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM call failed (%s) — falling back to templates", exc)
            return None

    def generate_json(self, user_prompt: str, system: str = SYSTEM_PROMPT) -> Optional[dict]:
        text = self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ]
        )
        if not text:
            return None
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> Optional[dict]:
        text = text.strip()
        # strip markdown fences
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    def pick_topic(self, bank: list[str]) -> Optional[str]:
        prompt = (
            "From this list of Hindi topics, pick the ONE most likely to go viral "
            "today as a YouTube Short, and reply with ONLY the topic text:\n\n"
            + "\n".join(f"- {t}" for t in bank)
        )
        return self.chat([{"role": "user", "content": prompt}])


def make_llm(cfg: dict) -> LLMClient:
    return LLMClient(cfg)
