# 🎬 Veo 3.1 — Ready-Made Film Prompts (copy-paste into Gemini app / Flow)

## Film: "रेगिस्तान का दरवाज़ा" (The Desert Door)
Ek consistent character: "ARJUN" — 14 saal ka ladka, beige shawl, haath mein purani
lantern (oil lamp). Har scene mein same description repeat karo taaki Veo character
consistent rakhe.

---

## Scene 1 — Establishing shot (8 sec)
> Wide drone shot at night: a vast desert under a starry sky. ARJUN — a 14-year-old
> Indian boy in a beige shawl, holding a flickering old oil lantern — walks slowly
> across golden sand dunes toward a massive ancient stone door half-buried in sand.
> Wind blows sand across his path, lantern flame flickers, camera slowly pushes in.
> Cinematic, dark fantasy, teal and amber grading, 35mm anamorphic, film grain.

## Scene 2 — Close-up (8 sec)
> Close-up: ARJUN's hands brush sand off the ancient carved stone door, mysterious
> glowing runes begin to light up under his fingers. Dust particles drift in the
> lantern light. Camera slowly orbits to a side angle. Cinematic, dark fantasy,
> teal and amber grading, 35mm anamorphic, film grain.

## Scene 3 — Door opens (8 sec)
> The massive ancient stone door slowly opens by itself, blinding golden light spills
> through the widening crack. ARJUN raises his arm to shield his eyes, his shawl and
> hair blowing backward in the rush of wind and light. Cinematic, dark fantasy,
> teal and amber grading, 35mm anamorphic, film grain, dramatic lens flare.

## Scene 4 — Face reaction (8 sec)
> Extreme close-up of ARJUN's face lit by warm golden light, eyes wide with awe,
> golden light reflecting in his dark eyes, hair strands lit from behind, slow
> dolly-in. Cinematic, dark fantasy, teal and amber grading, 35mm anamorphic,
> volumetric light, film grain.

## Scene 5 — Reveal (8 sec)
> ARJUN steps through the glowing door from the desert into a breathtaking hidden
> world: floating islands with waterfalls, warm sunrise light, lush greenery and
> mist. The camera follows behind him then rises to reveal the scale. Cinematic,
> dark fantasy, teal and amber grading, 35mm anamorphic, volumetric light, film grain.

---

## Kaise use karein (Gemini app / Flow mein)

1. **Gemini app** kholo → **Flow** ya **Veo** select karo
2. Upar ka **Scene 1 prompt** paste karo → generate → download MP4
3. Scene 2, 3, 4, 5 bhi same tarah banao (har ek ~8 sec)
4. Saari clips ko naam do: `scene_01.mp4`, `scene_02.mp4` ... `scene_05.mp4`

## Phir mere pipeline mein daal do (auto film ban jayegi)

```bash
cd ai-film-studio

# 1) ek idea se story + Hindi voiceover + subtitles (FREE, Veo ke bina):
./run.sh --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है" \
         --engine veo --skip-video

# 2) is command se ek folder banega jaise storage/film-XXXXXXXX/
#    us folder ke shots/ subfolder mein apni 5 Veo clips daal do
#    (scene_01.mp4 ... scene_05.mp4)

# 3) ab clips + voiceover + subtitles ko jodkar final film banao:
./run.sh --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है" \
         --engine veo --skip-video
```

> Main pipeline `shots/` folder mein maujood clips use karta hai, unhe narration ke
> hisaab se trim karta hai, Hindi subtitles + voiceover + music add karta hai aur
> `final.mp4` banata hai. Bas.

## 💡 Veo pro tips (behtar clips ke liye)

- **Consistency:** har prompt mein character ka description repeat karo (jaise upar ARJUN)
- **Aspect ratio:** Shorts ke liye "9:16 vertical", long video ke liye "16:9"
- **Motion words:** "slow dolly-in", "camera orbits", "drone shot", "tracking shot",
  "camera rises" — ye Veo ko asli camera movement dete hain
- **Lighting:** "volumetric light", "golden hour", "moody", "cinematic grading"
- **Ek hi scene 2-3 baar banao** aur best wala chuno (Veo har baar alag result deta hai)
- **720p Fast** = drafts ke liye (50/month Pro mein), **Quality** = final ke liye

## 🔌 Full auto chahiye (bina manual clips)? 

Veo **API** use karo — iske liye:
1. https://aistudio.google.com → API key lo
2. Google Cloud mein **billing** lagao (Veo API pay-per-second hai, ~$0.15/sec Fast)
3. Phir meri pipeline **poora automatic** hai:
   ```bash
   ./run.sh --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है" --engine veo
   ```
   Ye script khud: story → shot-list → Veo clips → Hindi voiceover → subtitles →
   final film → (optional) YouTube upload — sab automatic.

> ⚠️ Yaad rakho: Pro subscription ki Veo credits **sirf Gemini app/Flow mein** chalti
> hain, API par nahi. API ke liye Cloud billing alag se lagani padti hai.
