---
name: nes-capture
description: Archive a Mesen APU trace CSV into the project and render it to a listenable WAV. The first step for any new game — trace is ground truth.
user_invocable: true
---

# NES Capture & Render

Archive a Mesen2 APU trace and render it to WAV.

## When to use

User says "SAVED: path/to/capture.csv" or "I captured [game name]" or provides a Mesen trace file.

## Instructions

### 1. Preconditions
- User must provide the capture CSV path (or it's at `C:\Users\PC\Documents\Mesen2\capture.csv`)
- User must specify the game name

If either is missing, ask.

### 2. Archive the trace
```bash
mkdir -p extraction/traces/{game_slug}
cp "{capture_path}" extraction/traces/{game_slug}/capture{N}.csv
```
Where N = next available number (check existing files).

### 3. Quick analysis
Report: total frames, duration, pulse 1 note count, first 10 notes with names.

### 4. Render WAV
Use the trace-to-WAV renderer (inline Python APU synth at 44100Hz):
- All 4 channels: pulse1, pulse2, triangle, noise
- NES LFSR noise (not random)
- Frame-accurate volume and period from trace
- Normalize to 0.9 peak

Output: `output/{GameName}/wav/{game}_capture{N}_full_v1.wav`

### 5. Report
Print:
- Duration
- File path
- "Listen and tell me which track this is"

### Postconditions
- Trace CSV archived in extraction/traces/
- WAV file exists and duration > 0
- NEVER overwrite existing files — increment version

### Hard failures
- Capture CSV not found → STOP, ask user for correct path
- CSV has zero music frames → WARN user (might be title screen silence)
