"""Script generation — AI-first, template fallback (works with zero keys)."""
from __future__ import annotations

import json
import logging
import random
from typing import Optional

from .llm import LLMClient

log = logging.getLogger("omnishorts.script")

# Hindi speech ≈ 11-13 chars/sec for neural TTS → budget ~11 chars/s
CHARS_PER_SEC = 11.5

SCRIPT_PROMPT = """Topic: {topic}
Language: Hindi (Devanagari)
Target: a 45-58 second YouTube Short for a mystery/facts channel.

Write a script as JSON with EXACTLY this shape:
{{
  "hook": "one punchy opening question, max 70 chars",
  "lines": ["4 to 5 short factual sentences, each max 100 chars", "..."],
  "cta": "subscribe call-to-action, max 70 chars",
  "title": "viral title for the short, max 95 chars, Hindi",
  "tags": ["5-8 Hindi search tags"]
}}
Rules: simple everyday Hindi words, facts must be accurate and surprising,
no emojis inside JSON values, no English words unless unavoidable."""


class ScriptWriter:
    def __init__(self, cfg: dict, llm: Optional[LLMClient] = None):
        self.cfg = cfg
        self.llm = llm

    # ---------------------------------------------------------- topic
    def pick_topic(self, explicit: Optional[str] = None) -> str:
        bank = [t for t in self.cfg.get("topics", []) if isinstance(t, str) and t.strip()]
        if explicit:
            return explicit.strip()
        if self.llm and self.cfg.get("use_ai", True):
            chosen = self.llm.pick_topic(bank)
            if chosen and len(chosen) < 200:
                log.info("AI topic: %s", chosen)
                return chosen.strip()
        topic = random.choice(bank)
        log.info("Template topic: %s", topic)
        return topic

    # ---------------------------------------------------------- script
    def write_script(self, topic: str) -> dict:
        if self.llm and self.cfg.get("use_ai", True):
            data = self.llm.generate_json(SCRIPT_PROMPT.format(topic=topic))
            if data:
                script = self._normalize(topic, data)
                log.info("AI script generated (%d lines)", len(script["lines"]))
                return script
        return self._template_script(topic)

    # ------------------------------------------------------ template mode
    def _template_script(self, topic: str) -> dict:
        facts = [f for f in self.cfg.get("facts", []) if isinstance(f, str)]
        if not facts:
            facts = ["यह दुनिया का सबसे अनोखा रहस्य है।"]
        random.shuffle(facts)
        hook = f"क्या आप जानते हैं, {topic}"
        lines = [
            topic.rstrip("?") + "?",
            facts[0],
            facts[1 % len(facts)],
            facts[2 % len(facts)],
            "वैज्ञानिकों के लिए यह आज भी एक रहस्य है।",
        ]
        cta = "ऐसे ही रोचक तथ्यों के लिए चैनल को सब्सक्राइब करना मत भूलना!"
        title = f"{topic} 😱 | हैरान कर देने वाले तथ्य"
        tags = ["रोचक तथ्य", "हिंदी फैक्ट्स", "दुनिया का रहस्य", "amazing facts", "hindishorts"]
        return self._normalize(topic, {"hook": hook, "lines": lines, "cta": cta, "title": title, "tags": tags})

    # -------------------------------------------------------- normalize
    @staticmethod
    def _normalize(topic: str, data: dict) -> dict:
        hook = str(data.get("hook") or f"क्या आप जानते हैं, {topic}").strip()
        lines = [str(x).strip() for x in (data.get("lines") or []) if str(x).strip()]
        cta = str(data.get("cta") or "चैनल को सब्सक्राइब करना मत भूलना!").strip()
        title = str(data.get("title") or f"{topic} | दुनिया का रहस्य").strip()
        tags = [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()][:8]

        if not lines:
            lines = [f"{topic} — यह सुनकर आप हैरान रह जाएँगे।"]
        # enforce length budget (~55s)
        total = hook + " " + " ".join(lines) + " " + cta
        budget = int(55 * CHARS_PER_SEC)
        while len(total) > budget and len(lines) > 3:
            lines.pop()
            total = hook + " " + " ".join(lines) + " " + cta
        return {"topic": topic, "hook": hook, "lines": lines, "cta": cta, "title": title, "tags": tags}

    # -------------------------------------------------------- helpers
    @staticmethod
    def all_speech(script: dict) -> list[dict]:
        """Returns [{'text':..., 'kind': hook|line|cta}, ...] in speaking order."""
        items = [{"text": script["hook"], "kind": "hook"}]
        items += [{"text": ln, "kind": "line"} for ln in script["lines"]]
        items.append({"text": script["cta"], "kind": "cta"})
        return items

    @staticmethod
    def to_json_file(script: dict, path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(script, fh, ensure_ascii=False, indent=2)
