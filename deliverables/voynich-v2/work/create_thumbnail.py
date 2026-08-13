#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "visuals" / "27-yale-folio-100v-101r.jpg"
OUT = ROOT / "youtube-thumbnail.jpg"
W, H = 1280, 720
GOLD = "#f6c944"

img = Image.open(SRC).convert("RGB")
# A dark enlarged archival backdrop, retaining the manuscript's actual palette.
base = img.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(22))
base = ImageEnhance.Brightness(base).enhance(0.34)
base = ImageEnhance.Contrast(base).enhance(1.18)

# Build a crisp, high-contrast manuscript panel from the framed source area.
source_crop = img.crop((315, 168, 1244, 707))
panel = source_crop.resize((705, 410), Image.Resampling.LANCZOS)
panel = ImageEnhance.Contrast(panel).enhance(1.28)
panel = ImageEnhance.Sharpness(panel).enhance(1.5)

# Add an asymmetric black gradient behind the headline.
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pix = overlay.load()
for x in range(W):
    strength = int(236 * max(0, min(1, 1.06 - x / 790)))
    for y in range(H):
        pix[x, y] = (3, 7, 12, strength)
base = Image.alpha_composite(base.convert("RGBA"), overlay)

# Panel shadow and gold keyline.
draw = ImageDraw.Draw(base)
px, py = 555, 155
draw.rounded_rectangle((px + 15, py + 18, px + 720, py + 428), radius=7, fill=(0, 0, 0, 175))
base.alpha_composite(panel.convert("RGBA"), (px, py))
draw.rectangle((px - 3, py - 3, px + 708, py + 413), outline=GOLD, width=5)

bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
condensed = bold
brand = ImageFont.truetype(bold, 25)
big = ImageFont.truetype(condensed, 94)
small = ImageFont.truetype(bold, 29)
seal = ImageFont.truetype(bold, 32)

# Channel identity and a three-line mobile-first hook.
draw.text((55, 48), "RAHASYA  /  GLOBAL MYSTERIES", font=brand, fill=GOLD)

def outlined_text(pos, text, font, fill):
    draw.text(pos, text, font=font, fill=fill, stroke_width=7, stroke_fill="#05070a")

outlined_text((48, 148), "NO ONE", big, "white")
outlined_text((48, 245), "CAN READ", big, GOLD)
outlined_text((48, 342), "THIS.", big, "white")

# Compact age badge and authentic-source cue.
draw.rounded_rectangle((58, 492, 348, 555), radius=10, fill="#a91f2b", outline="#ff6f76", width=3)
draw.text((81, 504), "600 YEARS UNSOLVED", font=seal, fill="white")
draw.text((58, 592), "THE REAL VOYNICH MANUSCRIPT", font=small, fill="white")
draw.text((58, 634), "YALE  •  BEINECKE MS 408", font=brand, fill="#b9c3cc")

# Fine border to retain contrast against light YouTube backgrounds.
draw.rectangle((7, 7, W - 8, H - 8), outline=GOLD, width=4)
base.convert("RGB").save(OUT, quality=93, optimize=True, subsampling=1)
print(OUT)
