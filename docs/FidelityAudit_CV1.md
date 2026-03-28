# Fidelity Audit: Castlevania 1 Vampire Killer

## Methodology

Compared parser output against APU emulator trace (`extraction/traces/castlevania/stage1.csv`)
at frame resolution. Trace covers frames 1-5524 (92 seconds at 60fps). Vampire Killer begins
at approximately frame 111 in the trace.

## Findings

### 1. PITCH MAPPING — FIXED
Parser was one octave too high. Fixed: base MIDI changed from 36 to 24.
**Status: Correct.** Parser first note A3 (MIDI 57) matches trace period 511 -> A3.

### 2. FRAME DURATION — STRUCTURALLY CORRECT BUT NOT REPRESENTED IN OUTPUT
Parser computes `duration_frames = tempo * (duration_nibble + 1)`.
For tempo 7, duration 0: 7 frames. Trace confirms first note occupies 7 frames
(111-117 inclusive, next note at 118). **The total duration per note is correct.**

However, the parser treats each note as a single block of `duration_frames`.
The REAL driver behavior is:
- Note starts with attack volume
- Volume decays per the fade parameters over the duration
- Note may reach vol=0 before its duration expires

This means the **sounding portion** of each note is shorter than the duration.
Our MIDI export emits notes spanning the full duration, making them sound too
sustained compared to the real game.

### 3. ENVELOPE BEHAVIOR — THE BIGGEST FIDELITY GAP
Trace evidence for first two notes of Sq1:
```
Frame 111: A3 vol=4 (note start)
Frame 112: A3 vol=3 (decay)
Frame 113: A3 vol=2
Frame 114: A3 vol=1
Frame 115: A3 vol=0 (silent, but duration continues)
Frame 116: (still in duration, silent)
Frame 117: (still in duration, silent)
Frame 118: A3 vol=4 (next note start)
```

The instrument has fade_start=4, fade_step=1. Volume starts at 4, decrements
each frame after the start delay. With start=4, the driver waits 4 frames
before starting to decrement — but the trace shows immediate decay from frame
111. This suggests the fade_start parameter works differently than we
documented, OR the trace is measuring the hardware envelope (which the driver
configures but doesn't directly control frame-by-frame for constant-volume
mode).

**Key insight**: Looking at the instrument byte $F4 = 0b11110100:
- Duty=3 (75%), Length halt=1, Constant volume=1, Volume=4
- With constant_vol=1, volume IS 4 and doesn't change through hardware envelope
- But the trace shows vol decaying 4->3->2->1->0 across frames 111-115

This means EITHER:
a) The "volume" column in the trace represents the hardware envelope decay
   level (not the constant volume register), OR
b) The driver is writing decreasing volume values each frame (our fade system)

If (b), the fade_start=4 is probably "sustain for 4 frames at peak then decay"
rather than "delay before decay starts." OR the fade parameters are being
applied differently than our model.

**Resolution needed**: This is the #1 fidelity issue. The current MIDI output
plays notes at constant volume for their full duration. The real driver produces
short plucked notes with rapid decay.

### 4. LOOP/SUBROUTINE SEMANTICS — LIKELY CORRECT
Repeat count handling was fixed (FE now replays sections).
Subroutine FD/FF return stack appears correct.
Total duration for all 3 channels matches at 2016 frames after the fix.
**Status: Probably correct. Needs trace validation to confirm.**

### 5. INSTRUMENT STATE PERSISTENCE — MINOR CONCERN
The parser carries instrument state (tempo, volume, duty, octave) across
events. After a subroutine call, state changes inside the subroutine persist
after return. This matches the real driver behavior (RAM variables are global
to the channel, not scoped to subroutines).
**Status: Likely correct.**

### 6. DUTY CYCLE HANDLING — CORRECT IN PARSER, NOT APPLIED IN SYNTH
Parser correctly extracts duty changes. MIDI CC12 is emitted.
The JSFX synth was updated to respond to CC12.
**Status: Correct in data. Need to verify synth picks up CC12 changes.**

### 7. TRIANGLE BEHAVIOR — CORRECT
Triangle has no volume control. Parser sets velocity=127.
Triangle at E2 gives D3 (MIDI 50), matching trace period 381.
**Status: Correct.**

### 8. NOTE BOUNDARIES — AFFECTED BY ENVELOPE ISSUE
Because notes play at constant volume for their full duration in our output,
adjacent notes blend together without the silence gap that the real envelope
creates. This makes the output sound "legato" where the original sounds
"staccato."
**Status: Incorrect. Dependent on envelope fix.**

### 9. DRUM HANDLING — TIMING UNCERTAIN
Drums (E9/EA) are extracted as separate events. The trace shows noise
channel activity at the expected frames. Duration mapping needs verification.
**Status: Probably correct for timing. Drum sound quality depends on synth.**

### 10. FRAME OFFSET BETWEEN TRACE AND PARSER
The trace starts at frame 1 (game boot). Vampire Killer starts at ~frame 111.
Our parser starts at frame 0. A constant offset of ~111 frames exists.
When comparing, we need to align the two timelines.
**Status: Known offset. Not a bug, just an alignment requirement.**

## Priority Fix Order

1. **Build frame-accurate IR** so we can compare against trace precisely
2. **Build trace comparison tool** to identify exact mismatches
3. **Fix envelope/volume behavior** — either in MIDI export (CC11 automation
   per frame during decay) or in JSFX synth (parametric fade implementation)
4. **Validate loop/subroutine timing** against trace
5. **Tighten note boundaries** after envelope is fixed
