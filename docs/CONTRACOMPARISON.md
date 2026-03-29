# Contra — Trace Comparison Results

## What the Capture Proved

On March 28 2026, the first Mesen APU trace was captured for Contra
Jungle (Level 1). 4000 frames (~66 seconds) of per-frame hardware
state. This is the same technique that validated CV1 Vampire Killer
to zero pitch mismatches.

### The +1 Semitone Discovery

The single biggest finding: **every note in our extraction was
exactly 1 semitone flat.** Not approximately, not on some notes —
every single one of the 23 unique pitches used in the Jungle
melody, across all three melodic channels.

The trace showed MIDI 72 where we produced 71. MIDI 60 where we
produced 59. Systematic, universal, +1.

**Root cause**: The `EC` command (pitch adjustment) at the very
first byte of the Jungle track data (`EC 01`) shifts all subsequent
notes up 1 semitone in the period table. Our parser was reading the
byte and discarding it. Every note in the song inherited this
invisible shift, and we never noticed because the melody was
internally consistent — all notes were wrong by the same amount.

This is the same class of error that hit CV1 (the octave mapping
bug where all notes were 12 semitones off but trace comparison
showed zero mismatches because both paths had the same error). The
pattern: systematic pitch offsets are invisible to relative
comparisons and inaudible in isolation. Only absolute ground truth
catches them.

**Fix**: Parser now reads the EC parameter and applies it as a
semitone offset to all subsequent note lookups. The adjustment
wraps octave boundaries correctly.

### What Matched Before the Fix

Even before finding the EC bug, the trace comparison revealed that
the structural extraction was sound:

- **Note set**: All 23 unique pitches in the extraction mapped
  exactly to the 23 trace pitches (offset by +1)
- **Volume envelopes** (aligned section): 82-94% frame-level match
  on first comparison
- **Song timing**: 3072 extracted frames aligned with trace at
  offset 155 (capture started mid-loop, not at song beginning)

### Current Comparison Results (post-fix, aligned section)

```
Square 1:  91.0% pitch match, 81.7% volume match
Square 2:  91.1% pitch match, 74.7% volume match
Triangle:  70.3% pitch match, 93.5% volume match
```

The remaining ~9% pitch mismatches on pulse channels are likely
timing drift (notes starting 1 frame early/late, accumulating over
the song). The 30% triangle mismatch may include the EC adjustment
applying differently to triangle, or linear counter timing
differences.

## Pre-Capture vs Post-Capture Knowledge

### What We Knew Before (v1-v5, reverse engineering only)

| Aspect | Status | Source |
|--------|--------|--------|
| Note sequence | Correct | Disassembly pointer table |
| DX byte count (3/1) | Verified | Disassembly |
| Percussion format (DMC) | Verified | Disassembly |
| Volume envelope tables | Extracted | ROM + disassembly |
| Decrescendo model | Hypothesis | Disassembly inference |
| Pitch mapping | Wrong by +1 | Inherited from CV1, untested |
| EC pitch adjustment | Ignored | Parser skipped the byte |
| Absolute pitch accuracy | Unknown | No ground truth |

### What the Trace Added

| Aspect | Before | After |
|--------|--------|-------|
| Pitch accuracy | Unknown (off by 1) | Fixed via EC command |
| Envelope shapes | Hypothesis | 82-94% confirmed |
| Song loop alignment | Assumed frame 0 | Capture offset = 155 |
| Decrescendo timing | Provisional | Still provisional |
| Noise register values | Not captured | Available in trace |
| DMC output level | Not captured | Available in trace |

### What Remains Unvalidated

1. **Triangle pitch** — 70.3% match suggests either EC adjustment
   applies differently to triangle, or the linear counter timing
   model has errors
2. **Decrescendo threshold** — `(mul * dur) >> 4` model contributes
   to the volume mismatches but hasn't been isolated yet
3. **Note timing drift** — 9% pitch mismatches may indicate our
   tempo/duration calculation drifts from hardware over long
   sequences
4. **Noise channel** — the trace captured $400C/$400E values for
   noise, which we haven't compared yet. This would validate
   kick drum tuning.

## The Value of Trace Capture

The EC pitch adjustment bug is exactly the kind of error that:
- Is invisible to relative testing (all notes shift equally)
- Is inaudible in isolation (melody sounds right, just in wrong key)
- Is invisible to automated comparison if both paths share the bug
- Only shows up against absolute ground truth (hardware trace)

This validates the workflow principle from CLAUDE.md: "Automated
tests miss systematic errors. User MUST listen after pitch/octave
changes." And adds a stronger version: even human listening can
miss systematic offsets. The trace is the only reliable check for
absolute pitch accuracy.
