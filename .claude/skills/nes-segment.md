---
name: nes-segment
description: Split a trace render into individual track segments using silence detection and melody loop comparison. Outputs per-segment WAVs and a segment table.
user_invocable: true
---

# NES Track Segmentation

Split a captured trace into individual tracks.

## When to use

After `/nes-capture` has produced a full trace render. User wants to identify track boundaries.

## Instructions

### 1. Preconditions
- Trace CSV must exist in `extraction/traces/{game}/`
- Full trace WAV must exist in `output/{Game}/wav/`

If missing, suggest running `/nes-capture` first. REFUSE to proceed without a trace.

### 2. Silence detection
Build per-frame total volume (sum all channel volumes). Find runs of 15+ frames where total = 0. These are track boundaries.

Gaps 5-14 frames = musical rests, NOT boundaries.

### 3. Melody loop detection
For adjacent segments: compare first 20 note transitions (pitch only, pulse 1). If >=18/20 match, it's a LOOP of the same track, not a new track.

### 4. Render segments
Output: `output/{Game}/wav/segments/{game}_seg{NN}_v1.wav`
Skip segments shorter than 0.5 seconds.

### 5. Segment table
Print a table:
```
| Seg | Frames     | Duration | Silence Before | Notes |
|-----|------------|----------|----------------|-------|
| 01  | 0-442      | 7.4s     | -              |       |
| 02  | 442-4076   | 60.6s    | 5.7s           |       |
```

### 6. Cross-reference with nesmdb
If nesmdb tracks exist for this game, compare segment durations to nesmdb track durations. Flag matches within ±15%.

### 7. Ask user
"Listen to each segment and tell me which track it is."
Update the manifest's traces array with track identifications.

### Postconditions
- Segment WAVs exist
- Segment table printed
- Manifest updated if user identifies tracks

### Hard failures
- No trace exists → REFUSE, suggest /nes-capture
