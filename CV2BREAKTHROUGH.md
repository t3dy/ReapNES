# The CV2 Breakthrough

What happened, why it matters, and what it changes.

---

## What We Found

Castlevania II doesn't store music the way we expected.

In CV1 and Contra, music is a stream of bytes: each byte is a note,
a rest, an instrument change, or a control command. One byte, one
musical event. The song is a flat list you read from start to finish.

CV2 is completely different. The song data for Bloody Tears pulse 1
is **16 bytes long**:

```
FB 80 FB 20 2F 20 21 FE 01 FB 20 2E 20 22 FE 0F
```

That's the entire channel. Sixteen bytes produce 344 notes over 61
seconds of music. The data compression ratio is roughly **21 notes
per byte**.

The trick: **the chromatic walk pattern is hardcoded in the driver.**
The iconic Bloody Tears bass line — C C# D D# D C# — isn't stored
as six note bytes. It's a built-in engine behavior. The song data
only says "play the walk at THIS octave, then at THIS octave,
then loop."

---

## Why This Is a Breakthrough

### 1. It proves the "dead end" was completely wrong

Every previous analysis said CV2 uses a different driver (Fujio)
and can't be parsed with our tools. The GAME_MATRIX said BLOCKED.
The HANDOVER said dead end. The MOVINGONTOCV2 doc said different
driver entirely.

One trace capture disproved all of this. Not by showing the drivers
are the same — they aren't — but by showing the Fujio driver is
**understandable, structured, and shares DNA with Maezawa**:

- Same period table frequencies (identical NTSC tuning)
- Same FF end marker
- Same FE repeat command
- Runtime octave shifting (period >> 1 for +1 octave)
- Frame-based timing at consistent 10-frame intervals

### 2. It reveals a completely new music architecture

We knew two architectures:
- **CV1**: flat note streams with octave shift commands (E0-E4)
- **Contra**: flat note streams with lookup table envelopes

CV2 introduces a third:
- **Song-level sequencer**: 16 bytes encode verse/chorus structure
- **Pattern library**: reusable melodic motifs linked by Fx chains
- **Hardcoded patterns**: the chromatic walk is engine code, not data
- **Multi-octave table**: 32 pre-computed pitches (vs 12 + shift)

This is architecturally more sophisticated than Maezawa. Instead of
a dumb byte stream, it's a hierarchical composition system where
songs are assembled from patterns, patterns from motifs, and the
engine provides built-in musical primitives.

### 3. It validates the flexibility approach

Three principles from FLEXIBILITYGOALS fired and all three worked:

**Principle 2 (Try it before ruling it out)**: We captured a trace
instead of trusting the "dead end" label. The trace showed 60-70%
overlap with Maezawa immediately.

**Principle 5 (Degrade gracefully)**: The prototype parser logged
unknown commands instead of crashing, producing useful output on
its first run.

**Principle 6 (Measure overlap, not identity)**: Instead of asking
"is this Maezawa?" (no), we asked "what does it share with Maezawa?"
(period table, FF/FE, octave shifting, frame timing) and "what's
different?" (encoding, architecture, envelopes). The overlap score
guided investigation instead of blocking it.

### 4. It means CV2 is extractable

Not easily. Not with the existing parser. But extractably. The
remaining unknowns are tractable:

- How does the song sequencer map bytes to pattern + octave?
- What do the FB parameters control (instrument? channel? tempo)?
- How does the phrase library interact with the song sequencer?
- What does the 0x80 flag on notes mean?

These are answerable questions, not brick walls. We have the trace
as ground truth, we have the ROM structure mapped, and we have a
working prototype parser. Each question can be tested against the
trace and refined.

---

## What Changed in One Session

| Before | After |
|--------|-------|
| "CV2 is a dead end" | CV2 is extractable with a new parser |
| "Fujio is a completely different driver" | Fujio shares period table, FF/FE, octave shifting with Maezawa |
| "No disassembly = can't proceed" | Trace analysis + ROM scanning found all major structures |
| Period table unknown | 32-entry multi-octave table at ROM 0x01C1D |
| Pointer structure unknown | Phrase library (30 entries), song table (17 entries) |
| Note encoding unknown | 5-bit index + 2-bit duration + 1-bit flag |
| Song structure unknown | Hierarchical: song bytes → pattern + octave → hardcoded walk |
| Envelope model unknown | Max vol 6, 3-frame attack-decay, sustain at 1 |
| 0 tracks parseable | Bloody Tears partially decoded, MIDI numbers match trace |

---

## What It Means for the Project

### CV2 is now a viable target

Not a quick win — the hierarchical architecture requires a new
parser approach. But the fundamentals are cracked. The period table,
phrase library, song table, and note encoding are all located and
partially decoded. Estimated effort to full extraction: 4-6 more
sessions.

### The driver taxonomy needs updating

"Maezawa" and "Fujio" are not separate families. They're variants
of a shared Konami sound system with:
- Identical pitch tuning (period table)
- Shared control flow (FF end, FE repeat)
- Shared hardware model (runtime octave shifting)
- Different data architecture (flat streams vs hierarchical)
- Different envelope systems

The taxonomy should reflect shared ancestry, not binary separation.

### The methodology works on unknown drivers

This was the first game attempted without a disassembly. The
workflow — trace first, scan ROM for known signatures, build
prototype parser, compare to trace, iterate — worked on a driver
we'd never seen before. Every subsequent unknown game can follow
this same path.

### Hardcoded patterns are a new challenge

If the chromatic walk is in engine code rather than data, our
current approach (parse data bytes → notes) can't decode it. We
need to either:
- Find and disassemble the walk routine in the ROM
- Infer the pattern from the trace and hard-code it in our parser
- Build a hybrid parser that handles both data-driven and
  engine-driven note generation

This is a genuinely new architectural challenge that CV1 and Contra
never presented.

---

## The One-Line Summary

CV2 went from "dead end, different driver, don't try" to "period
table found, phrase library mapped, note encoding decoded, song
structure partially cracked" in a single session — because we
captured a trace instead of trusting our assumptions.
