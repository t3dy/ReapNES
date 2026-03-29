# Applying Contra Lessons to Castlevania 1

## The Result

Castlevania 1 Vampire Killer pulse channels went from 45/50
volume mismatches to **zero** across 1792 frames. Both pulse
channels now have perfect frame-level pitch, volume, and sounding
accuracy against the Mesen APU trace.

This was achieved by applying one fix discovered during the
Contra reverse engineering, without changing any CV1-specific code.

## What Contra Taught Us

### Lesson: Phase 2 Cannot Start Before Frame 1

The bug was in `_cv1_parametric_envelope()`, the function that
shapes pulse volume for every CV1 note.

CV1 uses a two-phase parametric envelope:
- Phase 1: decay by 1/frame for `fade_start` frames
- Phase 2: decay by 1/frame for the last `fade_step` frames

The implementation computed `phase2_start = duration - fade_step`.
When `fade_step > duration` (which happens for 9 specific notes
in Vampire Killer), `phase2_start` goes negative. The condition
`f >= phase2_start` was true on frame 0, causing an extra
decrement before the note even started sounding.

**Before**: `[4, 3, 2, 1, 0, 0, 0]` — vol starts at 4 instead of 5
**After**: `[5, 4, 3, 2, 1, 0, 0]` — correct, matches trace exactly

The fix: `phase2_start = max(1, duration - fade_step)`.

### Why Contra Exposed This

We never noticed this CV1 bug in isolation because:

1. It only affected 9 notes out of hundreds — instruments where
   `fade_step` exceeded the note's duration.
2. The difference was 1 volume step on the first frame — subtle
   enough to be inaudible in context.
3. The trace comparison reported it as "45 volume mismatches" but
   we attributed those to "envelope edge cases" and didn't
   investigate further.

The Contra work forced us to deeply understand the Maezawa driver's
volume handling. Reading the `resume_decrescendo` disassembly (for
the bounce-at-1 fix) led to re-examining `set_pulse_config` and
the `UNKNOWN_SOUND_01` subtraction, which led to questioning ALL
our volume assumptions, which led to finding the `phase2_start`
bug.

The fix is one line. The path to finding it required reverse
engineering a different game's volume system.

## What Didn't Transfer

### Bounce-at-1

Contra's `resume_decrescendo` bounces volume from 0 back to 1.
We applied this to the Contra envelope model. For CV1, the
parametric model's phase 2 already handles this correctly because
phase 2 only runs for `fade_step` frames — it doesn't continue
indefinitely. The bounce-at-1 fix applies structurally but doesn't
change CV1's output because CV1 doesn't trigger the same code
path.

### UNKNOWN_SOUND_01 Subtraction

The `set_pulse_config` routine subtracts `UNKNOWN_SOUND_01` from
volume before writing to the APU register. For CV1, the trace
comparison now shows 0 mismatches, meaning either:
- CV1 sets `UNKNOWN_SOUND_01 = 0` (no subtraction), or
- Our parser already accounts for it implicitly

Either way, it's not needed for CV1 currently.

### EC Pitch Adjustment

CV1 has no EC commands in its music data (confirmed by byte scan).
The pitch is correct at `BASE_MIDI_OCTAVE4 = 36` without adjustment.

### Volume Lookup Tables

CV1 uses parametric envelopes exclusively. No lookup tables needed.

## CV1 Current Status

| Channel | Pitch | Volume | Sounding | Total |
|---------|-------|--------|----------|-------|
| Pulse 1 | 0 | 0 | 0 | 0 mismatches |
| Pulse 2 | 0 | 0 | 0 | 0 mismatches |
| Triangle | 0 | 195 | 195 | 195 mismatches |

**Pulse channels: 100% verified.**

Triangle's 195 mismatches are the linear counter model — a separate
issue where our `(reload + 3) // 4` approximation doesn't match the
hardware's exact counter behavior. This could be fixed by modeling
the APU's quarter-frame clocking more precisely, but it's a triangle
specific problem unrelated to the Konami driver.

## The Meta-Lesson

Cross-game reverse engineering is not just about reusing parsers.
The real transfer is understanding the sound ENGINE (shared between
games) deeply enough that bugs in your model become visible.

CV1 alone would never have exposed the `phase2_start` bug because
we had no reason to look. Contra forced us to look — and the fix
applied backwards to CV1 perfectly.

This is why the project works on multiple games from the same
driver family rather than treating each game as isolated. The games
are independent data sets running on shared infrastructure. Bugs in
your model of the infrastructure only become visible when tested
against multiple data sets with different parameter ranges.
