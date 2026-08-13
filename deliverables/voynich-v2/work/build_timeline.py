#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
MASTER_DURATION = 457.42
SOURCE_DURATIONS = [60.50, 63.89, 79.25, 71.78, 73.42, 79.34, 75.38]
CHUNK_BOUNDS = []
scale = MASTER_DURATION / sum(SOURCE_DURATIONS)
cursor = 0.0
for duration in SOURCE_DURATIONS:
    adjusted = duration * scale
    CHUNK_BOUNDS.append((cursor, cursor + adjusted))
    cursor += adjusted

ASSET_GROUPS = [
    ["27-yale-folio-100v-101r.jpg", "17-glyph-macro.jpg", "31-three-facts.jpg", "12-five-scribes.jpg", "02-codebreakers.jpg", "06-botanical.jpg", "04-stars.jpg", "01-opening-library.jpg", "07-cipher-analysis.jpg", "27-yale-folio-100v-101r.jpg"],
    ["11-vellum-workshop.jpg", "32-carbon-range.jpg", "05-lab.jpg", "13-pigment-workshop.jpg", "03-medieval-scribe.jpg", "33-five-hands.jpg", "12-five-scribes.jpg", "17-glyph-macro.jpg", "31-three-facts.jpg"],
    ["34-six-worlds.jpg", "06-botanical.jpg", "26-yale-pharmaceutical-pages.jpg", "04-stars.jpg", "27-yale-folio-100v-101r.jpg", "17-glyph-macro.jpg", "06-botanical.jpg", "04-stars.jpg", "13-pigment-workshop.jpg", "26-yale-pharmaceutical-pages.jpg"],
    ["35-timeline.jpg", "08-prague.jpg", "14-rudolf-court.jpg", "15-kircher-letter.jpg", "08-prague.jpg", "16-jesuit-library.jpg", "09-antiquarian.jpg", "15-kircher-letter.jpg", "10-ending-vault.jpg"],
    ["17-glyph-macro.jpg", "18-language-analysis.jpg", "36-pattern-not-translation.jpg", "02-codebreakers.jpg", "07-cipher-analysis.jpg", "20-ai-analysis.jpg", "17-glyph-macro.jpg", "18-language-analysis.jpg", "36-pattern-not-translation.jpg"],
    ["37-four-theories.jpg", "19-four-theories.jpg", "02-codebreakers.jpg", "17-glyph-macro.jpg", "03-medieval-scribe.jpg", "12-five-scribes.jpg", "11-vellum-workshop.jpg", "09-antiquarian.jpg", "19-four-theories.jpg", "37-four-theories.jpg"],
    ["20-ai-analysis.jpg", "05-lab.jpg", "38-solution-test.jpg", "18-language-analysis.jpg", "27-yale-folio-100v-101r.jpg", "10-ending-vault.jpg", "01-opening-library.jpg", "39-final-question.jpg", "10-ending-vault.jpg"],
]


def label_for(name: str) -> str:
    number = int(name[:2])
    if number in (26, 27):
        return "SOURCE IMAGE  •  YALE LIBRARY"
    if 31 <= number <= 39:
        return "EDITORIAL EVIDENCE GRAPHIC"
    if number in (7, 18, 20):
        return "ANALYTICAL VISUALIZATION"
    return "ORIGINAL DRAMATIZED VISUAL"


def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, rem = divmod(cs, 360000); m, rem = divmod(rem, 6000); s, c = divmod(rem, 100)
    return f"{h}:{m:02}:{s:02}.{c:02}"


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    h, rem = divmod(ms, 3600000); m, rem = divmod(rem, 60000); s, milli = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{milli:03}"


def caption_groups(text: str) -> list[str]:
    groups, current = [], []
    for word in text.split():
        current.append(word)
        joined = " ".join(current)
        sentence = bool(re.search(r'[.!?][\"”’]?$', word))
        if len(joined) >= 64 or len(current) >= 11 or (sentence and len(current) >= 6):
            groups.append(joined); current = []
    if current: groups.append(" ".join(current))
    return groups


def wrap_caption(text: str, ass: bool = True) -> str:
    lines = textwrap.wrap(text, width=43, break_long_words=False, break_on_hyphens=False)
    if len(lines) > 2:
        midpoint = len(text) // 2
        split = text.rfind(" ", 0, midpoint)
        if split < 1: split = text.find(" ", midpoint)
        lines = [text[:split], text[split + 1:]]
    return ("\\N" if ass else "\n").join(lines)


def weight(text: str) -> float:
    pause = 15 if re.search(r'[.!?][\"”’]?$', text) else 5 if re.search(r'[,;:][\"”’]?$', text) else 0
    return len(text) + pause


def captions():
    result = []
    for index, (start, end) in enumerate(CHUNK_BOUNDS, 1):
        text = (WORK / f"narration-{index:02}.txt").read_text().strip()
        groups = caption_groups(text); weights = [weight(group) for group in groups]; total = sum(weights)
        cursor = start
        for group, group_weight in zip(groups, weights):
            duration = (end - start) * group_weight / total
            result.append((cursor, cursor + duration, group)); cursor += duration
    start, _, text = result[-1]; result[-1] = (start, MASTER_DURATION, text)
    return result


def write_scenes():
    scenes = []
    for chapter, ((start, end), assets) in enumerate(zip(CHUNK_BOUNDS, ASSET_GROUPS), 1):
        duration = (end - start) / len(assets)
        cursor = start
        for asset_index, asset in enumerate(assets):
            scene_end = end if asset_index == len(assets) - 1 else cursor + duration
            scenes.append({
                "image": asset,
                "start": round(cursor, 4),
                "end": round(scene_end, 4),
                "duration": round(scene_end - cursor, 4),
                "chapter": chapter,
                "label": label_for(asset),
            })
            cursor = scene_end
    assert abs(scenes[-1]["end"] - MASTER_DURATION) < .001
    (WORK / "scene-plan.json").write_text(json.dumps(scenes, indent=2) + "\n")
    return scenes


def write_srt(items):
    blocks = []
    for i, (start, end, text) in enumerate(items, 1):
        blocks.append(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{wrap_caption(text, False)}")
    (ROOT / "captions.srt").write_text("\n\n".join(blocks) + "\n")


def write_ass(items, scenes):
    header = """[Script Info]
Title: RAHASYA - Voynich Manuscript V2
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,50,&H00FFFFFF,&H000000FF,&H00101010,&H58000000,-1,0,0,0,100,100,0,0,3,1.4,0,2,160,160,58,1
Style: Brand,DejaVu Sans,25,&H003ACDFF,&H000000FF,&H00101010,&H00000000,-1,0,0,0,100,100,2,0,1,2,0,7,55,55,35,1
Style: Source,DejaVu Sans,20,&H00D1D7DE,&H000000FF,&H00101010,&H42000000,0,0,0,0,100,100,1,0,3,1,0,9,55,55,38,1
Style: Main,DejaVu Sans,76,&H00FFFFFF,&H000000FF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,4,1,5,100,100,0,1
Style: Chapter,DejaVu Sans,35,&H003ACDFF,&H000000FF,&H00101010,&H46000000,-1,0,0,0,100,100,2,0,3,1,0,8,100,100,64,1
Style: Callout,DejaVu Sans,36,&H00FFFFFF,&H000000FF,&H00101010,&H6C000000,-1,0,0,0,100,100,1,0,3,1.5,0,4,70,70,0,1
Style: Credit,DejaVu Sans,23,&H00D5DAE0,&H000000FF,&H00101010,&H52000000,0,0,0,0,100,100,0,0,3,1,0,8,60,60,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, text in items:
        safe = wrap_caption(text).replace("{", "\\{").replace("}", "\\}")
        events.append(f"Dialogue: 1,{ass_time(start+.025)},{ass_time(max(start+.12,end-.025))},Caption,,0,0,0,,{safe}")

    # Persistent, restrained channel identity.
    events.append(f"Dialogue: 2,{ass_time(0.2)},{ass_time(MASTER_DURATION-1)},Brand,,0,0,0,,{{\\fad(350,600)}}RAHASYA")

    # Scene provenance and disclosure labels.
    for scene in scenes:
        start, end = scene["start"], scene["end"]
        events.append(f"Dialogue: 2,{ass_time(start+.12)},{ass_time(min(end-.1,start+2.8))},Source,,0,0,0,,{{\\fad(180,350)}}{scene['label']}")

    overlays = [
        (0.45, 8.2, "Main", r"{\fad(450,650)}THE BOOK NO ONE CAN READ\N{\fs39\c&H003ACDFF&}THE VOYNICH MANUSCRIPT"),
        (55.5, 60.0, "Chapter", r"{\fad(300,500)}01  /  WHAT THE OBJECT PROVES"),
        (113.5, 118.0, "Chapter", r"{\fad(300,500)}02  /  SIX WORLDS INSIDE ONE BOOK"),
        (185.5, 190.0, "Chapter", r"{\fad(300,500)}03  /  THE TRAIL THROUGH EUROPE"),
        (250.7, 255.2, "Chapter", r"{\fad(300,500)}04  /  DOES IT BEHAVE LIKE LANGUAGE?"),
        (317.4, 321.9, "Chapter", r"{\fad(300,500)}05  /  FOUR THEORIES ENTER"),
        (389.4, 393.9, "Chapter", r"{\fad(300,500)}06  /  WHAT COUNTS AS A SOLUTION?"),
        (8.0, 13.5, "Callout", r"{\an4\pos(85,765)\fad(250,400)\c&H003ACDFF&}FACT 01\N{\fs55\c&H00FFFFFF&}MEDIEVAL PARCHMENT"),
        (13.6, 19.0, "Callout", r"{\an4\pos(85,765)\fad(250,400)\c&H003ACDFF&}FACT 02\N{\fs55\c&H00FFFFFF&}FIVE SCRIBAL HANDS"),
        (19.1, 24.4, "Callout", r"{\an4\pos(85,765)\fad(250,400)\c&H003ACDFF&}FACT 03\N{\fs55\c&H00FFFFFF&}ZERO ACCEPTED READINGS"),
        (445.0, 456.8, "Credit", r"{\fad(400,900)}RESEARCH: YALE LIBRARY + PEER-REVIEWED SCHOLARSHIP  •  ORIGINAL DRAMATIZED VISUALS"),
    ]
    for start, end, style, text in overlays:
        events.append(f"Dialogue: 3,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}")

    (WORK / "titles-and-captions.ass").write_text(header + "\n".join(events) + "\n")


scene_items = write_scenes()
caption_items = captions()
write_srt(caption_items)
write_ass(caption_items, scene_items)
print(f"{len(scene_items)} scenes, {len(caption_items)} captions, {MASTER_DURATION:.2f}s")
