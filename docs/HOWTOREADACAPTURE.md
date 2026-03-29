---
layout: default
title: "How to Read an APU Capture File"
---

# How to Read an APU Capture File

## For Humans

### What It Is

A capture file is a CSV recording of the NES sound chip's state,
sampled once per video frame (60 times per second). Each line says
"at frame N, register X changed to value Y."

Open any capture in a text editor or spreadsheet. You'll see:

```csv
frame,parameter,value
1,$4000_duty,3
1,$4000_vol,3
1,$4002_period,429
6,$4000_vol,2
7,$4000_vol,1
12,$4000_duty,3
12,$4000_vol,5
12,$4002_period,381
```

### Reading It

**Frame**: the time axis. Frame 1 = first frame of capture. At
60fps, frame 60 = 1 second, frame 600 = 10 seconds.

**Parameter**: which part of the sound chip changed. The names
look like `$4000_vol` — the `$4000` part is the NES hardware
register address, the `_vol` part says which decoded field.

**Value**: the new value. Only changes are logged. If a value
stays the same for 100 frames, you won't see it repeated —
assume it held the last logged value.

### The Channels

The NES has 5 sound channels. The capture covers all of them:

| Channel | Registers | What It Sounds Like |
|---------|-----------|-------------------|
| Pulse 1 | $4000-$4003 | Lead melody, sharp/buzzy |
| Pulse 2 | $4004-$4007 | Harmony, same as pulse 1 |
| Triangle | $4008-$400B | Bass, smooth/round |
| Noise | $400C-$400F | Drums, hiss, explosions |
| DMC | $4010-$4013 | Sampled audio (snare, voice) |

### What to Look For

**Note starts**: When `$4002_period` (or `$4006_period`) changes,
a new note has started. The period value determines the pitch —
lower period = higher pitch.

**Volume envelopes**: Watch `$4000_vol` frame by frame. You'll see
patterns like `7, 6, 5, 4, 3, 2, 1, 0` (decay) or
`3, 4, 3, 2` (attack-decay). These are the envelope shapes the
sound engine produces.

**Drum hits**: When `$400C_vol` spikes (noise channel volume goes
from 0 to something), that's a drum hit. The `$400E_period` value
determines the drum's pitch/timbre.

**Triangle gating**: The triangle channel has no volume control —
it's either on or off. Watch `$4008_linear` — when the linear
counter reaches 0, the triangle silences.

**DMC samples**: The `$4011_dac` value changes rapidly when a DMC
sample plays. You'll see it jump around as the delta-modulated
sample streams through.

### Quick Checks

**Is the capture aligned?** Look at frame 1. If `$4000_vol` > 0,
music was already playing when capture started. If it's 0,
the capture started during silence (ideal).

**How long is the song loop?** Search for a distinctive volume
pattern (like the first few notes' envelope) and find where it
repeats. The frame difference is the loop length.

**Which notes are playing?** Period 1710 = lowest C (C2). Period
855 = one octave up (C3). Period 428 = C4. Period 214 = C5.
Halving the period raises by one octave.

## For Agentic Readers (Claude, etc.)

### Loading

```python
from extraction.drivers.konami.frame_ir import trace_to_frame_ir

ir = trace_to_frame_ir("extraction/traces/contra/jungle.csv",
                        start_frame=155,  # skip to song start
                        end_frame=155 + 3072)
```

The `start_frame` parameter skips N frames from the beginning of
the capture. Use this to align with the song's actual start (which
may not be frame 0 if the capture started mid-playback).

### Structure

`trace_to_frame_ir()` returns a `SongIR` with three channels:
- `channels[0]`: pulse 1 (Square 1)
- `channels[1]`: pulse 2 (Square 2)
- `channels[2]`: triangle

Each channel has a `frames` dict mapping frame number to `FrameState`:

```python
fs = ir.channels[0].get_frame(42)
fs.period      # NES timer period (0-2047)
fs.midi_note   # computed MIDI note (0 = silent)
fs.volume      # 0-15
fs.duty        # 0-3 (pulse only)
fs.sounding    # True/False
```

### MIDI Note Computation

The trace path computes MIDI from period:
```
freq = CPU_CLK / (divisor * (period + 1))
midi = round(69 + 12 * log2(freq / 440)) + octave_offset
```

Where:
- `divisor` = 16 for pulse, 32 for triangle
- `octave_offset` = +12 for pulse (BASE_MIDI_OCTAVE4 convention), 0 for triangle
- Silent when volume = 0 (pulse/noise) or linear counter = 0 (triangle)

### Comparing Against Extraction

```python
from extraction.drivers.konami.contra_parser import ContraParser
from extraction.drivers.konami.frame_ir import parser_to_frame_ir, DriverCapability

parser = ContraParser("rom.nes")
song = parser.parse_track("jungle")
ext_ir = parser_to_frame_ir(song, driver=DriverCapability.contra(parser.envelope_tables))

# Compare frame by frame
for f in range(3072):
    ext = ext_ir.channels[0].get_frame(f)
    trace = ir.channels[0].get_frame(f)
    if ext.midi_note != trace.midi_note:
        print(f"Pitch mismatch at frame {f}")
```

### Finding Alignment

If the capture didn't start at the song's beginning, you need to
find the offset. Brute-force search:

```python
import numpy as np
trace_notes = np.array([ir.channels[0].get_frame(f).midi_note for f in range(4000)])
ext_notes = np.array([ext_ir.channels[0].get_frame(f).midi_note for f in range(3072)])

best_offset = max(range(4000 - 3072),
                  key=lambda o: np.sum(trace_notes[o:o+3072] == ext_notes))
```

### What the Trace Does NOT Tell You

- Which sound engine command produced a change
- ROM bank state or CPU execution flow
- Why a value changed (only that it did)
- Anything about the music data structure

The trace is pure hardware output. It proves what the NES produced
but not how. For "how", read the disassembly and manifest.

### Register Reference

| Parameter | Type | Range | Meaning |
|-----------|------|-------|---------|
| `$4000_duty` | int | 0-3 | Pulse 1 duty (0=12.5%, 1=25%, 2=50%, 3=75%) |
| `$4000_vol` | int | 0-15 | Pulse 1 volume (0 = silent) |
| `$4000_const` | bool | 0-1 | Pulse 1 constant volume mode |
| `$4001_sweep` | bool | 0-1 | Pulse 1 sweep enabled |
| `$4002_period` | int | 0-2047 | Pulse 1 timer period |
| `$4004_duty` | int | 0-3 | Pulse 2 duty |
| `$4004_vol` | int | 0-15 | Pulse 2 volume |
| `$4004_const` | bool | 0-1 | Pulse 2 constant volume |
| `$4005_sweep` | bool | 0-1 | Pulse 2 sweep enabled |
| `$4006_period` | int | 0-2047 | Pulse 2 timer period |
| `$4008_linear` | int | 0-127 | Triangle linear counter |
| `$400A_period` | int | 0-2047 | Triangle timer period |
| `$400B_length` | int | 0-254 | Triangle length counter |
| `$400C_vol` | int | 0-15 | Noise volume |
| `$400C_const` | bool | 0-1 | Noise constant volume |
| `$400E_period` | int | 0-15 | Noise timer period |
| `$400E_mode` | bool | 0-1 | Noise mode (0=long, 1=short/metallic) |
| `$4010_rate` | int | 0-15 | DMC timer period |
| `$4011_dac` | int | 0-127 | DMC output level |
| `$4012_addr` | int | 0-255 | DMC sample address (addr * 64 + $C000) |
| `$4013_len` | int | 0-255 | DMC sample length (len * 16 + 1 bytes) |
