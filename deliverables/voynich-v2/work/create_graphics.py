#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIS = ROOT / "visuals"
W, H = 1920, 1080
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GOLD = (255, 205, 58)
WHITE = (248, 250, 252)
MUTED = (172, 187, 204)
TEAL = (55, 205, 204)
BG = (5, 10, 17)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def base() -> Image.Image:
    image = Image.open(VIS / "17-glyph-macro.jpg").convert("RGB")
    ratio = W / H
    w, h = image.size
    if w / h > ratio:
        nw = int(h * ratio); left = (w - nw) // 2; image = image.crop((left, 0, left + nw, h))
    else:
        nh = int(w / ratio); top = (h - nh) // 2; image = image.crop((0, top, w, top + nh))
    image = image.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(7))
    image = ImageEnhance.Brightness(image).enhance(0.20).convert("RGBA")
    shade = Image.new("RGBA", (W, H), (2, 7, 13, 150))
    image = Image.alpha_composite(image, shade)
    d = ImageDraw.Draw(image)
    for y in range(H):
        alpha = int(75 * y / H)
        d.line((0, y, W, y), fill=(0, 0, 0, alpha))
    d.rectangle((25, 25, W - 26, H - 26), outline=(*GOLD, 95), width=2)
    d.text((80, 62), "RAHASYA  /  EVIDENCE FILE", font=font(27, True), fill=GOLD)
    return image


def heading(d: ImageDraw.ImageDraw, kicker: str, title: str, subtitle: str = ""):
    d.text((90, 155), kicker.upper(), font=font(27, True), fill=TEAL)
    d.text((86, 205), title, font=font(72, True), fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
    if subtitle:
        d.text((90, 302), subtitle, font=font(29), fill=MUTED)


def save(image: Image.Image, name: str):
    image.convert("RGB").save(VIS / name, quality=94, subsampling=0)


def three_facts():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Why this mystery survives", "THREE FACTS. ZERO TRANSLATION.")
    items = [("1404–1438", "PARCHMENT RANGE"), ("5", "SCRIBAL HANDS"), ("0", "ACCEPTED READINGS")]
    for i, (big, label) in enumerate(items):
        x = 85 + i * 605
        d.rounded_rectangle((x, 410, x + 545, 840), radius=22, fill=(6, 18, 29, 225), outline=(*GOLD, 145), width=3)
        box = d.textbbox((0, 0), big, font=font(105, True)); tw = box[2] - box[0]
        d.text((x + (545 - tw) / 2, 495), big, font=font(105, True), fill=GOLD)
        box = d.textbbox((0, 0), label, font=font(25, True)); tw = box[2] - box[0]
        d.text((x + (545 - tw) / 2, 665), label, font=font(25, True), fill=WHITE)
    save(im, "31-three-facts.jpg")


def carbon():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Physical evidence", "THE PARCHMENT HAS A DATE")
    d.text((90, 420), "1404", font=font(170, True), fill=WHITE)
    d.line((700, 545, 1215, 545), fill=GOLD, width=8)
    d.text((1300, 420), "1438", font=font(170, True), fill=WHITE)
    d.text((90, 710), "RADIOCARBON RANGE  •  FOUR SAMPLES", font=font(35, True), fill=GOLD)
    d.text((90, 785), "Parchment date ≠ exact ink date", font=font(30), fill=MUTED)
    save(im, "32-carbon-range.jpg")


def hands():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Paleography", "NOT ONE WRITER. FIVE.")
    for i in range(5):
        x = 130 + i * 345
        d.ellipse((x, 445, x + 215, 660), outline=GOLD, width=6, fill=(8, 20, 31, 220))
        d.text((x + 73, 477), str(i + 1), font=font(78, True), fill=WHITE)
        d.line((x + 108, 675, x + 108, 805), fill=TEAL, width=5)
    d.text((130, 875), "DIFFERENT HANDS  •  ONE SHARED WRITING SYSTEM", font=font(33, True), fill=WHITE)
    save(im, "33-five-hands.jpg")


def six_worlds():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Inside the manuscript", "SIX VISUAL WORLDS")
    labels = ["BOTANICAL", "ASTRONOMICAL", "BIOLOGICAL", "COSMOLOGICAL", "PHARMACEUTICAL", "RECIPES"]
    for i, label in enumerate(labels):
        col, row = i % 3, i // 3; x, y = 85 + col * 605, 410 + row * 245
        d.rounded_rectangle((x, y, x + 545, y + 185), radius=18, fill=(7, 20, 31, 230), outline=(*TEAL, 135), width=3)
        d.text((x + 34, y + 34), f"0{i + 1}", font=font(30, True), fill=GOLD)
        d.text((x + 34, y + 95), label, font=font(28, True), fill=WHITE)
    save(im, "34-six-worlds.jpg")


def timeline():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Documented trail", "PRAGUE  →  ROME  →  YALE")
    y = 600; d.line((135, y, 1785, y), fill=(110, 129, 151), width=6)
    points = [(200, "c. 1600", "RUDOLF II"), (690, "1666", "LETTER TO KIRCHER"), (1190, "1912", "WILFRID VOYNICH"), (1690, "1969", "YALE")]
    for x, year, label in points:
        d.ellipse((x - 19, y - 19, x + 19, y + 19), fill=GOLD)
        d.text((x - 65, y - 115), year, font=font(34, True), fill=WHITE)
        box = d.textbbox((0,0), label, font=font(22, True)); tw=box[2]-box[0]
        d.text((x - tw/2, y + 65), label, font=font(22, True), fill=TEAL)
    save(im, "35-timeline.jpg")


def pattern():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Linguistic evidence", "PATTERN  ≠  TRANSLATION")
    d.text((100, 480), "STRUCTURE", font=font(86, True), fill=WHITE)
    d.text((885, 480), "MEANING", font=font(86, True), fill=WHITE)
    d.line((760, 470, 760, 735), fill=GOLD, width=6)
    left = ["REPETITION", "POSITION", "FREQUENCY"]
    right = ["NO KEY", "NO GRAMMAR", "NO CONSENSUS"]
    for i, text in enumerate(left): d.text((110, 630 + i * 72), f"✓  {text}", font=font(28, True), fill=TEAL)
    for i, text in enumerate(right): d.text((900, 630 + i * 72), f"?  {text}", font=font(28, True), fill=GOLD)
    save(im, "36-pattern-not-translation.jpg")


def theories():
    im = base(); d = ImageDraw.Draw(im); heading(d, "Theory board", "FOUR EXPLANATIONS. NO WINNER.")
    items = [("01", "CIPHER"), ("02", "LOST SHORTHAND"), ("03", "CONSTRUCTED SYSTEM"), ("04", "ELABORATE HOAX")]
    for i, (number, label) in enumerate(items):
        col, row = i % 2, i // 2; x, y = 90 + col * 895, 405 + row * 245
        d.rounded_rectangle((x, y, x + 835, y + 190), radius=18, fill=(6, 19, 31, 230), outline=(*GOLD, 135), width=3)
        d.text((x + 35, y + 30), number, font=font(46, True), fill=GOLD)
        d.text((x + 135, y + 50), label, font=font(34, True), fill=WHITE)
    save(im, "37-four-theories.jpg")


def solution():
    im = base(); d = ImageDraw.Draw(im); heading(d, "The standard of proof", "WHAT WOULD COUNT AS A SOLUTION?")
    items = [("01", "REPRODUCIBLE METHOD"), ("02", "HISTORICAL + GRAMMATICAL SENSE"), ("03", "CONSISTENT ACROSS THE BOOK")]
    for i, (number, text) in enumerate(items):
        y=420+i*170
        d.ellipse((110,y,210,y+100),fill=GOLD)
        d.text((137,y+20),number,font=font(30,True),fill=BG)
        d.text((260,y+22),text,font=font(36,True),fill=WHITE)
        if i<2: d.line((160,y+105,160,y+157),fill=TEAL,width=5)
    save(im, "38-solution-test.jpg")


def final_question():
    im = base(); d = ImageDraw.Draw(im)
    d.text((90, 82), "RAHASYA: GLOBAL MYSTERIES", font=font(28, True), fill=GOLD)
    d.text((85, 330), "WHICH THEORY", font=font(92, True), fill=WHITE)
    d.text((85, 450), "FAILS LEAST?", font=font(110, True), fill=GOLD)
    d.text((95, 660), "CIPHER  •  LOST SCRIPT  •  CONSTRUCTED SYSTEM  •  HOAX", font=font(28, True), fill=MUTED)
    d.text((95, 755), "COMMENT THE CLUE YOUR THEORY CANNOT EXPLAIN", font=font(31, True), fill=TEAL)
    save(im, "39-final-question.jpg")


for build in (three_facts, carbon, hands, six_worlds, timeline, pattern, theories, solution, final_question):
    build()
print("Created 9 evidence graphics")
