# Voynich Manuscript — Version 2 deliverable

A 7:37 cinematic/viral-hybrid documentary package for **RAHASYA: Global Mysteries**, produced in US English.

## Primary deliverables

| File | Purpose | Technical profile |
|---|---|---|
| `voynich-manuscript-v2.mp4` | YouTube upload master | 1920×1080, 24 fps, H.264 High, AAC-LC stereo, 7:37.43 |
| `voynich-v2-mobile-compatible.mp4` | Small review/download copy | 854×480, 24 fps, H.264 Constrained Baseline, AAC-LC stereo, 13.5 MiB |
| `youtube-thumbnail.jpg` | YouTube thumbnail | 1280×720 JPEG |
| `captions.srt` | Separate accessibility captions | 124 cues, en-US |
| `youtube-package.md` | Release copy and strategy | Title, description, chapters, sources, tags, pinned comment, launch plan |
| `youtube-metadata.json` | Automation-readable metadata | Private-at-ingest defaults and asset references |
| `qa-contact-sheet.jpg` | Visual QA overview | Eleven frames across all seven chapters |

## Editorial and production improvements

- Entirely rewritten evidence-led seven-part story
- Newly selected masculine US-English narration
- 66 edited scenes, generally cut every 5.5–7.6 seconds
- Newly generated cinematic reconstructions and analytical visuals
- Nine custom evidence graphics
- Yale/Beinecke manuscript images presented in attributed archival composites
- On-screen provenance labels distinguishing source imagery, dramatized scenes, analytical visualizations, and editorial graphics
- Chapter cards, opening title and fact hooks, channel branding, burned captions, and separate SRT captions
- Original atmospheric score bed with chapter impacts, mixed to an integrated loudness of -16.0 LUFS

## Evidence standard

The episode preserves these distinctions:

- Radiocarbon analysis dates sampled animal-skin parchment to 1404–1438; it does not independently date every ink stroke.
- Lisa Fagin Davis's paleographic work supports five scribal hands.
- No decipherment currently has scholarly consensus.
- Authorship, language, purpose, and meaning remain unresolved.

## QA results

- Full master decode: passed with zero reported media errors
- Mobile copy decode: passed with zero reported media errors
- Master audio: -16.00 LUFS integrated, -3.93 dBTP, 3.50 LU LRA
- Duration: 457.43 seconds
- Chapter and caption synchronization: checked against the adjusted narration boundaries
- Visual review: title/captions remain inside safe areas; evidence graphics remain readable at 480p
- Master SHA-256: `70cfa92b7e09d81c81d75f2de0733478109936a36b80477216b06cf92f61e04a`
- Mobile SHA-256: `5ca6934587c75eee5ff5639922ebe6f4b0e515d4eabb0591574642ad9ef674da`

## Source and reconstruction disclosure

Archival manuscript material is credited to Yale University Library / Beinecke Rare Book and Manuscript Library, MS 408. Original dramatized historical scenes are reconstructions, not archival photographs, and are labeled on screen. Narration and selected visuals were produced with AI-assisted tools under human editorial direction.

The reproducible generators are under `work/`: timeline/captions, evidence graphics, thumbnail, render, and mobile transcode scripts.
