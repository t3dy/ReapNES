---
name: nes-rip
description: Extract all music tracks from a Konami NES ROM, create MIDI files, REAPER projects, render WAV audio, and produce an MP4 video with YouTube description. Works with games using the Konami pre-VRC Maezawa sound driver (Castlevania, Contra, Super C, TMNT, Goonies II, Gradius).
user_invocable: true
---

# NES ROM Music Extraction Pipeline

Run the full extraction pipeline on a Konami NES ROM.

## What this skill does

1. Parses all music tracks from the ROM using the Konami Maezawa driver parser
2. Exports each track as MIDI with per-frame volume envelopes (CC11 automation)
3. Generates REAPER projects (.rpp) with the NES APU JSFX synth
4. Renders audio to WAV using a Python NES APU synthesizer
5. Concatenates all tracks with 1-second gaps
6. Creates an MP4 video with a screenshot background (or black if no image provided)
7. Generates a YouTube description with clickable chapter timestamps

## Usage

The user provides a ROM path. Optionally they may specify:
- A game name (auto-detected from filename if omitted)
- A screenshot image for the MP4 background
- Specific track numbers to extract

## Instructions

Run the pipeline script:

```bash
cd C:/Dev/NESMusicStudio
PYTHONPATH=. python scripts/full_pipeline.py "<rom_path>" [--game-name "Name"] [--screenshot path/to/image.png] [--tracks 1,2,5]
```

If the user provides just a game name without a full path, search for the ROM in:
- `C:/Dev/NESMusicStudio/AllNESROMs/All NES Roms (GoodNES)/USA/`
- `C:/Dev/NESMusicStudio/extraction/roms/`

Prefer `[!]` (verified good dump) versions. Prefer `(U)` (USA) region.

After the pipeline completes, report:
- Number of tracks extracted successfully
- Total duration
- Any tracks that failed (with error)
- Paths to the MP4 and YouTube description

If a track fails with "negative shift count" or similar, that's an octave value > 4 from a misinterpreted E-series command — the track still exports but those notes may be wrong. This is a known limitation for some tracks.

For parallel processing of multiple ROMs, launch separate Agent instances for each ROM — the pipeline is self-contained and writes to separate output directories.
