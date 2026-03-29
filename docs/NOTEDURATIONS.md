---
layout: default
title: "Note Duration Dynamics — Everything That Affects What You Hear"
---

# Note Duration Dynamics — Everything That Affects What You Hear

## Why Notes Sound Shorter or Longer Than Expected

The perceived duration of a NES note is NOT just the frame count.
It's the interaction of five systems, each of which can cut a note
short, extend its tail, or change its character.

## The Five Systems

### 1. Raw Duration (Parser Level)

Each note byte encodes: `high_nibble = pitch, low_nibble = duration_multiplier`

Actual frames = `tempo * (low_nibble + 1)`

Where tempo is set by the DX command's low nibble (SOUND_LENGTH_MULTIPLIER).

Example: tempo=6, nibble=0 → 6 frames. Nibble=9 → 60 frames.

**Our status**: Verified correct. 0 frame drift across 24 consecutive
notes in the trace-aligned section.

### 2. Volume Envelope (Lookup Table)

For most notes, the `pulse_volume_ptr_tbl` entry shapes volume
frame by frame. Example table `[3,4,3,2]`:
- Frame 0: vol=3 (attack)
- Frame 1: vol=4 (peak)
- Frame 2: vol=3 (decay)
- Frame 3: vol=2 (sustain)
- Frame 4+: $FF terminator → hold at last value (2)

The note is still "playing" but at vol=2. If the table has zeros
in the middle (e.g. `[7,6,5,4,3,0,0,0,0,0,1,1]`), the note goes
SILENT for several frames then comes back. This creates a rhythmic
"gap" that isn't a real rest — it's the envelope design.

**What you hear**: Notes with short tables (4 entries) feel staccato
because the envelope reaches its sustain quickly and holds at a
low volume. Notes with long tables (12+ entries) have more dynamic
movement.

**Our status**: 54 tables extracted from ROM. 96.6% frame-level
volume match against trace (up from 82% before the bounce-at-1 fix).

### 3. Decrescendo End Pause

At the tail end of each note, the engine checks:
`remaining_frames < (decrescendo_mul * duration) >> 4`

When this triggers, volume starts decrementing by 1 per frame.
This creates the fade-out at the end of longer notes.

**Critical behavior**: When the resumed decrescendo reaches vol=0,
the engine IMMEDIATELY increments it back to 1. The volume never
actually reaches 0 during this phase — it bounces and holds at 1.

This means notes sustain at vol=1 through their entire tail, rather
than going silent. This is the biggest single factor in perceived
note length.

Example for a 60-frame note (env table [3,4,3,2], decr_mul=4):
```
DEP = (4 * 60) >> 4 = 15 frames
frames  0-3:  table [3,4,3,2]
frames  4-44: hold at 2
frame  45:    decrescendo starts, vol=2→1
frames 46-59: hold at 1 (bounced from 0)
```

**Our status**: Fixed. Previously went to 0 at frame 46, killing
the note 14 frames early.

### 4. Auto-Decrescendo Mode (bit 7)

When vol_env byte has bit 7 set, instead of reading from a lookup
table, the engine does simple 1-per-frame decay — BUT only for
`PULSE_VOL_DURATION` frames (low nibble of vol_env byte).

Example: vol_env=0x84, vol=5 → vol_duration=4
```
frame 0: vol=5
frame 1: vol=4
frame 2: vol=3
frame 3: vol=2
frame 4: vol=1 (decay paused after 4 frames)
frames 5+: hold at 1
... tail: resume decrescendo (bounce at 1)
```

Without vol_duration, our old model decayed all the way to 0 in
5 frames. With it, the note holds at 1 from frame 4 onward.

**Our status**: Fixed. Base track's middle section now sustains
properly.

### 5. UNKNOWN_SOUND_01 Subtraction

The engine subtracts `UNKNOWN_SOUND_01` from the volume before
writing to the APU register, but only when vol >= 2:
```
if vol >= 2: actual_vol = max(0, vol - UNKNOWN_SOUND_01)
else:        actual_vol = vol
```

This means a note at internal vol=2 might only produce vol=1 at
the hardware level if UNKNOWN_SOUND_01=1.

**Our status**: NOT MODELED. This accounts for the remaining ~3.4%
volume mismatch against the trace. The trace shows actual register
values (post-subtraction), our model shows pre-subtraction values.

## What This Means for What You Hear

### "Notes seem too short"
Most likely cause: the decrescendo dropping to 0 instead of bouncing
at 1. Fixed in v8. Notes now sustain at vol=1 through their tail.

### "Notes seem too long"
Could be: our model holding at a value the real hardware subtracts
to 0 via UNKNOWN_SOUND_01. If the hardware shows vol=0 but we show
vol=1, the note sounds like it sustains when it shouldn't.

### "The decay sounds wrong"
The envelope table shape determines the attack-decay character. If
a table has [7,6,5,4,3,0,0,0,0,0,1,1], the note has a sharp attack
then goes SILENT for 5 frames before a soft sustain. That mid-note
silence is intentional — it's the Contra sound.

### "Tone is different from the game"
This is the synth, not the data. Our Python renderer uses simple
8-step duty cycle lookup. The real NES APU has nonlinear DAC mixing
that gives each channel a different character at different volumes.
Load the MIDIs into REAPER with the JSFX NES plugin for better tone.

## Remaining Gaps

| Gap | Impact | Fix |
|-----|--------|-----|
| UNKNOWN_SOUND_01 subtraction | ~3% volume frames wrong | Extract value from DX parsing, apply in IR |
| Decrescendo onset off by 1 frame | 2 frames per long note | Compare `SOUND_CMD_LENGTH` counting direction |
| Mid-note duty changes | Rare (2 in Jungle) | Parse duty from envelope or track data |
| Vibrato (EB) | Not used in Contra | Implement for future games |
