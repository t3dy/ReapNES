# CV2 Bloody Tears — First Trace Analysis

Source: `extraction/traces/cv2/bloody_tears.csv`
Captured: 2026-03-29, Mesen 2, ~61.5 seconds (3688 frames)

---

## What the Trace Tells Us

### 1. It IS Bloody Tears

The chromatic ascending bass line is unmistakable: C - C# - D - D#,
then descending D - C# - C, repeating. This is the iconic Bloody
Tears opening, confirmed by the pitch sequence from the trace.

The melody repeats at octave 3 first (MIDI 48-51), then octave 4
(MIDI 60-63), matching the real song's structure.

### 2. The Period Table IS Maezawa

**Triangle channel: 9 of 10 periods are exact Maezawa table matches.**
The triangle uses the same 12-entry period table as CV1 and Contra,
with periods at 213, 285, 302, 320, 339, 359, 403, 427, 538. Only
period 1792 (initial silence) is non-table.

**Pulse channels: periods come in pairs differing by exactly 2.**
Every pulse period appears as both N and N+2 (e.g., 853/855, 805/807,
761/763). The ODD members (855, 807, 763, 719, 427, 403, 381, 359)
are exact Maezawa table values. The EVEN members are off by 1.

This strongly suggests the Fujio driver uses the SAME period table
but writes the period register across two frames with a 1-unit jitter
on the low byte. This is a different APU write pattern from Maezawa
(which writes both period bytes atomically each frame).

### 3. The Envelope System Is Different

**Max volume: 6** (not 15). CV1 and Contra use the full 0-15 range.
CV2 pulse channels never exceed vol=6. This could mean:
- The driver caps volume at 6 by design
- UNKNOWN_SOUND_01-style subtraction is always active
- The envelope tables use a reduced range

**Envelope shape: Attack-Decay with sustain at 1.**
Typical note pattern (10 frames per note):
```
Frame 0: vol=1 (or 3)  — attack rising
Frame 1: vol=3 (or 5)  — attack peak
Frame 2: vol=4 (or 6)  — peak
Frame 3: (gap)
Frame 4: vol=1          — decay to sustain
Frames 5-9: vol=1       — sustain at 1
```

This is NOT the CV1 parametric model (fade_start + fade_step).
This is NOT the Contra lookup table model (54 pre-built tables).
This looks like a HARDWARE envelope using the APU's built-in
$4000 decay counter with length_halt=0, possibly with the
constant_volume flag toggling mid-note. Or it could be a very
short software lookup table with only 3-4 entries.

### 4. Note Timing Is 10 Frames

Notes are exactly 10 frames apart (every other note start shifts
by +/-1 due to the period jitter). At 60fps, 10 frames = 1/6 second.
This is a fast tempo consistent with Bloody Tears' driving rhythm.

The timing appears perfectly regular — no swing, no rubato. This
is consistent with a frame-based sequencer like Maezawa.

### 5. Channel Usage

| Channel | Unique Periods | Vol Changes | Active |
|---------|---------------|-------------|--------|
| Pulse 1 | 16 | 1321 | Yes, melody |
| Pulse 2 | 20 | 1056 | Yes, harmony/echo |
| Triangle | 10 | 1154 linear changes | Yes, bass |
| Noise | 6 | 267 | Yes, drums |
| DMC | 449 DAC changes | — | Yes, samples |

All 5 APU channels active. DMC has 449 DAC changes — more than
Contra Jungle (283). CV2 uses DPCM samples for percussion.

Noise uses 6 unique period values: 3, 15, 31, 63, 127, 2033.
More varied than Contra (which uses 2).

### 6. Duty Cycle

Both pulse channels use duty 0 and 1 (12.5% and 25%). CV1 uses
higher duties. This gives CV2 its thinner, more cutting sound.

---

## What This Changes About Our Understanding

### The "Dead End" Was Wrong

CV2 is not a completely different engine. The evidence:

1. **Same period table** — not just the same 12 base frequencies,
   but the same octave-shifted values across both pulse and triangle
2. **Same note timing model** — frame-based, regular intervals
3. **Same channel assignment** — 2 pulse + triangle + noise + DMC
4. **Period write jitter** — this is the ONE clear driver difference,
   and it's a write-timing issue, not a command-format issue

The Fujio driver may share MORE with Maezawa than we concluded.
The period table match isn't a false positive — it's evidence of
shared utility code or a shared codebase with different envelope
and I/O routines.

### What's Actually Different

1. **Envelope system** — max vol 6, attack-decay pattern unlike
   either CV1 parametric or Contra lookup tables
2. **Period write timing** — 2-frame jitter (writes low/high bytes
   on alternating frames) vs Maezawa's atomic write
3. **Command format** — still unknown, needs ROM investigation
4. **Pointer table** — still unknown, not at $0825

### Overlap Score: ~60-70%

Per FLEXIBILITYGOALS Principle 6 (measure overlap, not just identity):

| Feature | Same as Maezawa? |
|---------|-----------------|
| Period table | YES (exact match) |
| Octave shifting | YES (same >>N pattern) |
| Channel assignment | YES |
| Frame-based timing | YES |
| Note duration regularity | YES |
| Duty cycle usage | PARTIAL (narrower range) |
| Envelope model | NO (different shape, lower max) |
| Period write pattern | NO (jitter vs atomic) |
| Command format | UNKNOWN |
| Pointer table | UNKNOWN |

---

## ROM Investigation Results

All steps completed in a single session from the trace capture.

### Period Table: 32-Entry Multi-Octave

Found at ROM 0x01C1D (bank 0, CPU $9C1D). Unlike Maezawa's 12-entry
table with runtime octave shifting (E0-E4 commands), CV2 pre-computes
all 32 pitches across 2.67 octaves (E1 through B3, MIDI 28-59).

```
Index  0-7:  E1 F1 F#1 G1 G#1 A1 A#1 B1  (octave 1)
Index  8-19: C2 C#2 D2 D#2 E2 F2 F#2 G2 G#2 A2 A#2 B2  (octave 2 = Maezawa base)
Index 20-31: C3 C#3 D3 D#3 E3 F3 F#3 G3 G#3 A3 A#3 B3  (octave 3)
```

The frequencies are **identical** to Maezawa. Same NTSC clock,
same 12-note chromatic tuning. Just indexed differently.

### Note Encoding: 3-Part Byte

```
Bit 7:    Flag (0x80+ = long note / tied / modified)
Bits 6-5: Duration class (0-3)
Bits 4-0: Period table index (0-31)
```

So `0x14` = index 20, dur 0 = C3 short.
`0x34` = index 20, dur 1 = C3 medium.
`0x54` = index 20, dur 2 = C3 long.

### Music Architecture: Hierarchical Phrase System

**Three levels of indirection:**

**Level 1 — Phrase Library** at ROM 0x00B60 (CPU $8B50):
30 pointers to short melodic motifs (4-8 bytes each). Each phrase
contains note bytes and ends with FF or chains to another phrase
via an Fx command.

**Level 2 — Song Table** at ROM 0x00CE0 (CPU $8CD0):
17 unique song pointers (+ padding). Each song entry contains
FB-prefixed commands (instrument/tempo/volume settings), note
bytes (0x20-0x3F range — possibly phrase indices or drum/channel
data), FE repeat markers, and FF end markers.

**Level 3 — Phrase Chaining** via Fx commands:
Within phrases, `F5` means "continue to phrase 5", `F6` means
"continue to phrase 6", etc. This creates melodic sequences from
short reusable motifs.

### Bloody Tears Found In Phrases

The Bloody Tears chromatic bass line appears across multiple phrases:

- **Phrase 19**: E3 D#3 D3 → F5 (chain to phrase 5)
- **Phrase 5**: D3 D#3 → F6 (chain to phrase 6)
- **Phrase 6**: C3 D3 D#3 E3 A#2 B2 C3 C#3 (ascending run!)
- **Phrase 20**: C3 D3 D#3 → F6 F5 F5 F4 F4 F4 F3 F2 (bass + chain cascade)

The melody is built from linked phrase fragments, not a continuous
data stream like Maezawa.

### Command Vocabulary Identified

| Byte Range | Meaning | Maezawa Equivalent |
|------------|---------|-------------------|
| 0x00-0x1F | Note (dur=0, index 0-31) | Similar but index = pitch+octave |
| 0x20-0x3F | Note (dur=1, index 0-31) | — |
| 0x40-0x5F | Note (dur=2, index 0-31) | — |
| 0x60-0x7F | Note (dur=3, index 0-31) | — |
| 0x80-0x9F | Modified note (flag set) | — |
| 0xA0-0xBF | Modified note (flag set) | — |
| 0xC0 | Rest? | $C0-$CF in Maezawa |
| 0xE0-0xEF | Commands? | $E0-$E4 octave in Maezawa |
| 0xF0-0xF7 | Phrase chain (Fx → phrase x) | No equivalent |
| 0xFB | Parameter prefix (FB xx) | No equivalent |
| 0xFE | Repeat (FE xx) | Same as Maezawa! |
| 0xFF | End marker | Same as Maezawa! |

### Envelope Model (from trace)

- **Max volume: 6** (not 15)
- **Shape: 3-frame attack (1→3→4 or 3→5→6), then instant drop to 1, sustain**
- **Not parametric** (no fade_start/fade_step)
- **Not lookup table** (pattern is too simple and regular)
- **Possibly hardware-assisted** (APU $4000 decay counter?)
- **All notes same envelope** in the bass line (no per-instrument variation seen yet)

### Overlap Score Updated: ~50-60% with Maezawa

| Feature | Same? | Notes |
|---------|-------|-------|
| Period table values | YES | Identical frequencies |
| Period table structure | NO | 32-entry flat vs 12-entry + octave shift |
| Note encoding | PARTIAL | Both use byte = pitch + duration, but different bit layout |
| FF end marker | YES | Identical |
| FE repeat | YES | Identical |
| Phrase architecture | NO | Hierarchical with chaining vs flat streams |
| Envelope model | NO | Simpler, max vol 6, different shape |
| Duration encoding | NO | 2-bit duration class vs 4-bit nibble |
| FB command prefix | NO | Not in Maezawa |
| Fx phrase chaining | NO | Not in Maezawa |

## What We Know After One Session

Starting from "CV2 is a dead end," one trace capture and one
investigation session has produced:

1. **Period table location and full decode** (32 entries, ROM 0x01C1D)
2. **Phrase library location** (30 phrases, ROM 0x00B60)
3. **Song table location** (17 songs, ROM 0x00CE0)
4. **Note encoding model** (5-bit index + 2-bit duration + 1-bit flag)
5. **Phrase chaining mechanism** (Fx commands)
6. **Command vocabulary** (partial: FF, FE, FB, Fx, C0 identified)
7. **Envelope characterization** (max vol 6, 3-frame attack-decay-sustain)
8. **Bloody Tears melody verified** in phrase data

This is enough to write a prototype parser. The driver is NOT
Maezawa, but it shares enough DNA (period values, FF/FE semantics,
byte-stream architecture) that the existing pipeline infrastructure
(frame IR, MIDI export, trace comparison) can be reused.

**CV2 is not a dead end. It never was.**
