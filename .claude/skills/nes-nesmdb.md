---
name: nes-nesmdb
description: Render all available nesmdb reference tracks for a game as WAV files. Uses correct frame rate from the dataset (usually 24fps, NOT 60fps). Produces labeled reference tracks for ear-matching against trace captures.
user_invocable: true
---

# NES nesmdb Reference Renderer

Render nesmdb dataset tracks as reference WAVs.

## When to use

When starting a new game, render nesmdb tracks so the user has labeled reference audio to compare against their Mesen captures.

## Instructions

### 1. Find nesmdb files
Search `data/nesmdb/nesmdb24_exprsco/train/` for files matching the game.
Report how many tracks found and their names.

### 2. Render each track
For each .exprsco.pkl file:
- Load the pickle: (rate, num_samples, exprsco_array)
- **Use the `rate` field for frame timing** (typically 24fps, NOT 60fps)
- SPF = 44100 / round(rate)
- Synth all 4 channels: pulse1, pulse2, triangle, noise
- Normalize to 0.9 peak

### 3. Pitch sanity check
If median pulse channel pitch > MIDI 80: **WARN** — likely needs octave correction. Report the median pitch and suggest checking against a trace.

### 4. Output
Files: `output/{Game}/wav/nesmdb/{game}_{num}_{name}.wav`

Print a track table:
```
| # | Track Name | Duration |
|---|-----------|----------|
| 00 | Title | 13.6s |
| 01 | Stage 1 | 56.7s |
```

### Postconditions
- All nesmdb tracks rendered
- Rate field used (not hardcoded 60fps)
- Pitch sanity check performed

### Hard failures
- No nesmdb files found for this game → report "not in nesmdb database" and continue without
- Pickle load fails → skip that track, report error
