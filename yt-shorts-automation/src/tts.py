"""Text-to-speech — edge-tts primary (free, Hindi neural voices + word timings),
gTTS fallback, OpenAI TTS optional, and 'silent' mode for testing."""
from __future__ import annotations

import asyncio
import io
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .utils import ffmpeg_bin, probe_duration

log = logging.getLogger("omnishorts.tts")


@dataclass
class WordTiming:
    text: str
    start_ms: int
    end_ms: int


@dataclass
class LineAudio:
    path: Path
    duration: float          # seconds
    words: list[WordTiming] = field(default_factory=list)
    text: str = ""


class TTSBackend:
    name = "base"

    def __init__(self, cfg: dict, workdir: Path):
        self.cfg = cfg
        self.workdir = workdir
        self.pause = float(cfg.get("pause_between_lines", 0.35))

    def synthesize_lines(self, items: list[dict]) -> list[LineAudio]:
        """items: [{'text','kind'}...] -> list of LineAudio with word timings."""
        raise NotImplementedError

    # ------------------------------------------------------------ utils
    def _fallback(self, items: list[dict]) -> list[LineAudio]:
        """edge/gtts failure → gTTS → silent (never crash)."""
        try:
            import gtts  # noqa: F401
            return GttsBackend(self.cfg, self.workdir).synthesize_lines(items)
        except ImportError:
            log.warning("gTTS not installed — using silent TTS")
            return SilentTTSBackend(self.cfg, self.workdir).synthesize_lines(items)

    @staticmethod
    def _clean(text: str) -> str:
        """Normalize Hindi punctuation for TTS engines."""
        text = text.replace("।", ".")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _silence(self, seconds: float, path: Path) -> None:
        ff = ffmpeg_bin()
        subprocess.run(
            [ff, "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
             "-t", f"{seconds:.3f}", "-c:a", "libmp3lame", "-q:a", "9", str(path)],
            capture_output=True, check=True,
        )


# =====================================================================
#  edge-tts — default backend (word-level karaoke timings)
# =====================================================================
class EdgeTTSBackend(TTSBackend):
    name = "edge"

    def synthesize_lines(self, items: list[dict]) -> list[LineAudio]:
        import edge_tts
        try:
            from edge_tts import SubMaker  # v6+
        except ImportError:  # pragma: no cover
            from edge_tts.submakers import SubMaker  # older

        voice = self.cfg.get("voice", "hi-IN-MadhurNeural")
        rate = self.cfg.get("rate", "+8%")
        pitch = self.cfg.get("pitch", "+0Hz")

        results: list[LineAudio] = []
        for i, item in enumerate(items):
            text = self._clean(item["text"])
            out = self.workdir / f"line_{i:02d}.mp3"
            com = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
            sub = SubMaker()
            buf = io.BytesIO()
            try:
                asyncio.run(self._stream(com, sub, buf))
            except Exception as exc:  # noqa: BLE001
                log.warning("edge-tts failed for line %d (%s) — falling back to gTTS", i, exc)
                return self._fallback(items)
            buf.seek(0)
            out.write_bytes(buf.read())
            duration = probe_duration(out)
            if duration <= 0:
                log.warning("edge-tts produced empty audio for line %d", i)
                return self._fallback(items)
            words = self._words_from_subs(sub, duration, text)
            results.append(LineAudio(path=out, duration=duration, words=words, text=text))
            log.info("  [tts] %s (%.1fs, %d words)", item["kind"], duration, len(words))
        return results

    @staticmethod
    async def _stream(com, sub: "SubMaker", buf: io.BytesIO) -> None:
        async for chunk in com.stream():
            ctype = chunk.get("type")
            if ctype == "audio":
                buf.write(chunk["data"])
            elif ctype == "WordBoundary":
                sub.feed(chunk)

    @staticmethod
    def _words_from_subs(sub, duration: float, text: str) -> list[WordTiming]:
        words = []
        try:
            raw = sub.get_subs()  # list of (start_ms, end_ms, word)
            for start, end, word in raw:
                if word.strip():
                    words.append(WordTiming(word.strip(), int(start), int(end)))
        except Exception:  # noqa: BLE001
            words = []
        if not words:
            words = EdgeTTSBackend._proportional_words(text, duration)
        return words

    @staticmethod
    def _proportional_words(text: str, duration: float) -> list[WordTiming]:
        """Distribute duration across words by character share (fallback)."""
        tokens = text.split()
        total_chars = sum(len(t) for t in tokens) or 1
        out, cursor = [], 0.0
        for tok in tokens:
            frac = len(tok) / total_chars
            start = cursor
            end = cursor + frac * duration
            out.append(WordTiming(tok, int(start * 1000), int(end * 1000)))
            cursor = end
        return out


# =====================================================================
#  gTTS — free fallback (no word timings → proportional)
# =====================================================================
class GttsBackend(TTSBackend):
    name = "gtts"

    def synthesize_lines(self, items: list[dict]) -> list[LineAudio]:
        from gtts import gTTS

        lang = self.cfg.get("language", "hi")
        results: list[LineAudio] = []
        for i, item in enumerate(items):
            text = self._clean(item["text"])
            out = self.workdir / f"line_{i:02d}.mp3"
            try:
                gTTS(text=text, lang=lang, slow=False).save(str(out))
            except Exception as exc:  # noqa: BLE001
                log.warning("gTTS failed for line %d (%s) — using silent", i, exc)
                self._silence(2.0, out)
            duration = probe_duration(out) or 2.0
            words = EdgeTTSBackend._proportional_words(text, duration)
            results.append(LineAudio(path=out, duration=duration, words=words, text=text))
            log.info("  [tts] %s (%.1fs)", item["kind"], duration)
        return results


# =====================================================================
#  OpenAI TTS — optional high-quality backend
# =====================================================================
class OpenAiTTSBackend(TTSBackend):
    name = "openai"

    def synthesize_lines(self, items: list[dict]) -> list[LineAudio]:
        from openai import OpenAI

        key = self.cfg.get("api_key") or ""
        base = self.cfg.get("base_url") or None
        client = OpenAI(api_key=key or "sk-none", base_url=base if base.endswith("/v1") else None)
        voice = self.cfg.get("openai_voice", "alloy")
        results: list[LineAudio] = []
        for i, item in enumerate(items):
            text = self._clean(item["text"])
            out = self.workdir / f"line_{i:02d}.mp3"
            try:
                resp = client.audio.speech.create(model="tts-1", voice=voice, input=text)
                resp.stream_to_file(str(out))
            except Exception as exc:  # noqa: BLE001
                log.warning("OpenAI TTS failed for line %d (%s) — using silent", i, exc)
                self._silence(2.0, out)
            duration = probe_duration(out) or 2.0
            words = EdgeTTSBackend._proportional_words(text, duration)
            results.append(LineAudio(path=out, duration=duration, words=words, text=text))
        return results


# =====================================================================
#  Silent — for testing the full pipeline without network (durations
#  estimated from character count).
# =====================================================================
class SilentTTSBackend(TTSBackend):
    name = "silent"

    CHARS_PER_SEC = 11.5

    def synthesize_lines(self, items: list[dict]) -> list[LineAudio]:
        results: list[LineAudio] = []
        for i, item in enumerate(items):
            text = self._clean(item["text"])
            duration = max(1.5, len(text) / self.CHARS_PER_SEC)
            out = self.workdir / f"line_{i:02d}.mp3"
            self._silence(duration, out)
            words = EdgeTTSBackend._proportional_words(text, duration)
            results.append(LineAudio(path=out, duration=duration, words=words, text=text))
            log.info("  [tts-silent] %s (%.1fs)", item["kind"], duration)
        return results


BACKENDS = {
    "edge": EdgeTTSBackend,
    "gtts": GttsBackend,
    "openai": OpenAiTTSBackend,
    "silent": SilentTTSBackend,
}


def make_tts(cfg: dict, workdir: Path) -> TTSBackend:
    name = str(cfg.get("backend", "edge")).lower()
    cls = BACKENDS.get(name, EdgeTTSBackend)
    return cls(cfg, workdir)
