---
name: nes-separate-sfx
description: Separate a trace render into music-only, SFX-only, and per-channel stem WAVs using pitch-jump heuristics. Always produces both versions for human comparison — never treat the algorithmic separation as final.
user_invocable: true
---

# NES SFX Separation

Split trace audio into music and sound effects.

## When to use

After `/nes-capture` has rendered a trace WAV that contains gameplay SFX mixed with background music. User says "separate the SFX" or "give me stems."

## Instructions

### 1. Preconditions
- Trace CSV must exist
- User should specify the frame range (or use full trace)

### 2. SFX detection heuristics
For each pulse channel, flag frames as SFX if:
- Pitch jumps > 12 semitones from previous frame
- Pitch exceeds MIDI 90 (very high, likely laser/explosion)
- Flag the frame + next 7 frames as SFX

For noise channel:
- Bursts > 8 frames at volume >= 8 = explosion SFX
- Shorter bursts = likely musical drums, keep in music mix

Triangle channel: always music (almost never hijacked for SFX).

### 3. Render 6 WAVs
```
output/{Game}/wav/separated/{game}_music_only_v1.wav
output/{Game}/wav/separated/{game}_sfx_only_v1.wav
output/{Game}/wav/separated/{game}_stem_pulse1_v1.wav
output/{Game}/wav/separated/{game}_stem_pulse2_v1.wav
output/{Game}/wav/separated/{game}_stem_triangle_v1.wav
output/{Game}/wav/separated/{game}_stem_noise_v1.wav
```

### 4. Report
Print: how many SFX frames detected per channel, total duration of SFX.

### 5. Ask user to validate
"Listen to music_only and sfx_only. Is the separation clean?"
The pitch-jump threshold is a heuristic — some games may need adjustment.

### Postconditions
- 6 WAV files in separated/ directory
- User has been asked to validate

### Important
- The separation is HEURISTIC, not ground truth
- Always produce both versions so the user can judge
- Per-channel stems are more reliable than the algorithmic split
- Never overwrite — version all outputs
