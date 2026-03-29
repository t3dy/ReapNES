---
layout: default
title: "Contra — The Goal Line"
---

# Contra — The Goal Line

## Where We Are

Contra Jungle v5c is the closest extraction yet. Three major fidelity
gaps have been closed in this session:

1. **Volume envelopes** — extracted all 54 lookup tables from
   `pulse_volume_ptr_tbl` in the ROM. Per-frame volume shaping now
   follows the real hardware path: table read → hold → decrescendo
   tail. The flat dynamics of v1-v4 are gone.

2. **Percussion mapping** — the `percussion_tbl` in the disassembly
   revealed that most drum hits are compound: a DMC sample plus a
   noise channel bass drum (sound_02). Nibble 3 (the dominant hit
   type, 212 occurrences in Jungle) plays DMC snare + kick
   simultaneously. The kick is what gives the triangle bass its
   attack.

3. **Bass punch** — triangle phase now resets on new notes, mimicking
   the hardware transient that creates the percussive "thwack" at the
   start of each bass note.

The architecture has also been restructured:
- `DriverCapability` schema replaces implicit branching
- Volume strategies are isolated, named, testable functions
- `ParsedSong.validate_full_duration()` enforces the invariant that
  parsers emit raw durations and the IR handles all shaping

## What Sounds Right

- Note pitches and timing (verified since v2)
- Volume dynamics on pulse channels — the characteristic Contra
  "pluck" from the lookup table envelopes
- Drum pattern placement — kicks sync with bass notes
- Triangle bass line melody and rhythm

## What Still Isn't Accurate

### The Synth Sound

The pulse channels use the correct duty cycles from the DX config
byte (mostly duty=3, 75%), but the rendered tone doesn't quite match
the game. Possible causes:

- **Sweep unit**: The disassembly shows `EB` vibrato commands with
  parameters. Our parser skips the vibrato bytes. The real sound has
  subtle pitch modulation that we're not reproducing.
- **Duty cycle switching mid-note**: Some instruments may change duty
  cycle within a single note for timbral effects. We apply duty
  statically per instrument change.
- **The renderer itself**: `render_wav.py` uses a simple 8-step
  lookup for pulse duty. Real NES pulse waves have analog
  characteristics (slight rounding, DC offset, mixer nonlinearity)
  that affect the perceived timbre.

### The Noise Channel

The noise rendering is still approximate:

- **No DMC samples**: The real Contra plays DPCM samples for snares
  and cymbals through the DMC channel ($4010-$4013). Our renderer
  uses filtered white noise for everything. The DMC samples have
  specific tonal character — a crunchy, lo-fi quality that white
  noise can't replicate.
- **Noise mode**: The NES noise channel has two modes (long/short
  period, controlled by $400E bit 7). Short mode creates metallic
  pitched noise. We don't model this distinction.
- **Kick drum tuning**: Our low-pass filtered noise approximates the
  bass drum, but the real sound_02 plays specific noise register
  values that create a precise pitch contour.

### The Decrescendo Model

The threshold-linear decrescendo (`(mul * dur) >> 4` remaining frames)
is derived from disassembly but marked **provisional**. It hasn't
been validated against a Contra APU trace. The interaction between
the envelope table ending ($FF → set flag bit 2) and the decrescendo
resumption (bit 1+2 set when `SOUND_CMD_LENGTH < DECRESCENDO_END_PAUSE`)
is complex — there may be off-by-one frames or edge cases we're
missing.

### Auto-Decrescendo Mode (bit 7)

When `vol_env` byte has bit 7 set, the engine uses automatic decay
instead of a lookup table. Our approximation (linear 1/frame decay
from initial volume) doesn't account for `PULSE_VOL_DURATION` — a
separate counter that controls how many frames the initial decay
runs before pausing. We'd need to extract that value from the DX
context to model it correctly.

## What Would Close the Remaining Gaps

In priority order:

1. **Capture a Contra APU trace** — record Mesen's per-frame register
   writes for Jungle. This is the single highest-value action. It
   would let us validate envelope shapes, decrescendo timing, and
   noise register values against ground truth, the same way CV1's
   trace anchored that extraction.

2. **Implement vibrato** — the `EB` command parameters control pitch
   modulation depth and speed. The disassembly documents this clearly.
   Adding it would improve the pulse channel "feel" significantly.

3. **Extract DMC sample data** — the DPCM samples live in the ROM at
   known addresses (sound_5a, sound_5b, etc.). They could be decoded
   and mixed into the audio output for authentic snare/cymbal sounds.

4. **Model noise register values** — sound_02 (bass drum) writes
   specific values to $400C/$400E/$400F. These are in the
   disassembly. Modeling them would give the kick drum its correct
   pitch and decay character.

## The Pattern

This extraction follows the same path CV1 did:

1. Parse notes and timing (v1-v2) — get the skeleton right
2. Add volume dynamics (v3-v5) — get the expression right
3. Validate against trace — find what you can't hear
4. Polish remaining channels — noise, DMC, vibrato

CV1 reached step 3 and found zero pitch mismatches across 1792
frames. Contra is at step 2, solidly. Step 3 (trace capture) is
what turns "sounds close" into "verified correct."

## The Architectural Lesson

The biggest insight from this session isn't about Contra specifically.
It's that the system now carries truth in layers:

- ROM + disassembly = ground truth
- Manifest = extracted facts with confidence levels
- Parser = lossless event translation (full-duration invariant)
- IR = driver-specific execution (DriverCapability dispatch)

Each layer has a defined responsibility. When something sounds wrong,
you can isolate which layer is at fault. That's what makes the
remaining mysteries tractable rather than overwhelming.

The mysteries aren't "we don't know what's wrong." They're specific,
enumerable, and each has a clear path to resolution. That's the
difference between v1 and v5.
