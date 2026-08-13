"""Title / description / tags generation."""
from __future__ import annotations

import json
from pathlib import Path


class MetadataBuilder:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.meta_cfg = cfg.get("metadata", {})

    def build(self, script: dict) -> dict:
        topic = script["topic"]
        hook = script["hook"]
        title = self.meta_cfg.get("title_template", "{hook} | {topic} #shorts").format(
            hook=hook, topic=topic
        )
        max_chars = int(self.meta_cfg.get("title_max_chars", 95))
        if len(title) > max_chars:
            title = title[: max_chars - 1].rstrip() + "…"

        lines_plain = "\n".join(f"• {ln}" for ln in script["lines"])
        hashtags = " ".join(f"#{t}" for t in script.get("tags", []))
        description = self.meta_cfg.get("description_template", "{topic}\n{script_lines}\n{hashtags}").format(
            topic=topic,
            script_lines=lines_plain,
            hashtags=hashtags,
            channel_handle=self.cfg.get("channel", {}).get("handle", "@channel"),
            channel_name=self.cfg.get("channel", {}).get("name", "Channel"),
        ).strip()

        tags = list(script.get("tags", [])) + list(self.meta_cfg.get("tags", []))
        seen, uniq = set(), []
        for t in tags:
            t = t.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                uniq.append(t)

        return {
            "title": title,
            "description": description,
            "tags": uniq[:15],
            "categoryId": str(self.cfg.get("channel", {}).get("category_id", "24")),
            "defaultLanguage": "hi",
        }

    def to_json_file(self, meta: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
