# What Super C Taught Us About Maezawa

## The Period Table Mystery

We searched the Super C ROM for the Maezawa period table six
different ways and found NOTHING:

1. Full 12-entry Maezawa table (16-bit LE) — NOT FOUND
2. CV3-style modified table (±1 tuning) — NOT FOUND
3. Contra-exact table (1358/1142/1078 variants) — NOT FOUND
4. Any chromatic 12-entry sequence by ratio detection — NOT FOUND
5. Split lo/hi byte tables — NOT FOUND
6. Individual Contra period values as contiguous block — NOT FOUND

But the Mesen trace PROVES the driver outputs these exact period
values to the APU registers. The music plays. The periods are correct.
They come from somewhere.

### What the Contra disassembly reveals

The Contra source code at `bank1.asm:1384` stores the period table as:

```
note_period_tbl:
    .byte $ae,$06 ; $06AE - 1,710 - C2
    .byte $4e,$06 ; $064E - 1,614 - C#2
    .byte $f4,$05 ; $05F4 - 1,524 - D2
    ...
```

This IS little-endian 16-bit storage — exactly what `struct.pack("<H")`
produces. So our search method was correct. The table just isn't in
the Super C ROM as a contiguous block.

### Three hypotheses

**H1: The table is in a bank we haven't checked properly.**

UNROM maps one switchable bank to $8000-$BFFF and fixes the last
bank at $C000-$FFFF. The sound driver code and data could be in
ANY of the 8 banks. Our scan covered all banks but the period
values were scattered — bank 0 had F# and D, bank 7 had A and C#,
etc. This scatter pattern is inconsistent with a contiguous table
in any single bank.

**H2: The table is split or interleaved with other data.**

Some drivers store the period table interleaved with other note
parameters (volume envelope index, duration default, etc.). If
each "note entry" is 4+ bytes instead of 2, our 2-byte-pair
search would miss it.

**H3: The table is computed at runtime.**

The driver might store only the base octave (12 entries) and
compute other octaves by bit-shifting, but do this at LOAD TIME
into RAM rather than reading from ROM during playback. Our ROM
scan would never find the runtime copy.

### What this means for the project

**The "scan ROM for period table" step is not reliable for all
Maezawa-family games.** It worked for CV1, CV2, and CV3 because
those games store the table as a simple contiguous block. It
fails for Super C (and possibly Contra itself, which we never
verified against the ROM — we had the disassembly).

This is exactly the failure mode documented in MISTAKEBAKED.md:
"Same driver ≠ same ROM layout." The period table format varies
even within the Maezawa family.

## The Vibrato Discovery

The trace showed something we hadn't seen in CV1:

```
F2:  1281, 1283, 1285, 1287, 1279, 1277, 1275
F#2: 1209 (exact, no wobble)
G2:  1143, 1147, 1151, 1155, 1139
```

Most notes wobble ±2-6 around their base period EVERY FRAME.
This is **real-time vibrato** — the driver modulates the period
register continuously during sustained notes.

The Contra disassembly confirms this at `bank1.asm:429`:

```
; sustains the current pitch (PULSE_NOTE,x) with optional vibrato
; (note: vibrato portion not used in Contra)
```

Contra has the vibrato CODE but doesn't USE it. Super C activates
it. Same engine, different configuration. This confirms the
DriverCapability model — the driver has features that are
enabled/disabled per game via data, not code changes.

### Implications

1. **trace_compare.py needs a vibrato tolerance.** Frame-level
   period matching can't require exact values when the driver
   applies ±6 vibrato. We need a "close enough" threshold.

2. **The frame IR needs a vibrato model.** Currently it handles
   pitch as a fixed value per note. Super C notes have pitch
   that continuously modulates. The IR needs to either:
   - Model vibrato as a per-frame pitch adjustment
   - Or snap to the nearest base period and ignore the wobble

3. **MIDI export can use pitch bend.** Vibrato maps naturally to
   MIDI pitch bend events (CC or pitch wheel). This is actually
   BETTER than CV1's static pitches for musical expressiveness.

## The Command Signature Paradox

Super C has strong Maezawa command signatures across ALL banks:

| Bank | E0-E4 | DX | FE | Score |
|------|-------|-----|-----|-------|
| 0 | 401 | 569 | 30 | 148.4 |
| 1 | 258 | 400 | 250 | 141.8 |
| 2 | 284 | 268 | 329 | 145.0 |
| 3 | 108 | 173 | 180 | 73.9 |
| 5 | 177 | 240 | 65 | 73.6 |
| 7 | 129 | 595 | 57 | 106.7 |

In CV1, the music is concentrated in ONE bank. In Super C, it's
spread across SIX banks with roughly equal density. This means
either:

- Music data is distributed across multiple banks (the driver
  bank-switches during playback)
- OR the "music-like" byte patterns in non-sound banks are
  actually code or other data that happens to use the same byte
  ranges

The Contra disassembly shows the sound engine is in bank 1 with
music data pointers referencing addresses within that bank. If
Super C follows the same pattern, we need to identify WHICH bank
is the sound bank — and the answer might not be bank 1.

## What "Maezawa Family" Actually Means

Before Super C, we thought "Maezawa family" meant:

- Same period table (12 entries, known values)
- Same note encoding (pitch×16 + duration)
- Same control flow (FE repeat, FD subroutine, FF end)
- Same pointer table structure (per-game address)
- Different envelope parameters (per-game tuning)

After Super C, we know it means:

- **Same DRIVER CODE** (the 6502 assembly is shared/forked)
- **Same command VOCABULARY** (E0-E4, DX, FE, FD, FF)
- **Different command USAGE** (vibrato active vs inactive)
- **Different data LAYOUT** (period table location, pointer
  table address, bank assignment all vary)
- **Different TUNING** (±1 on some entries: 1357 vs 1358)
- **Different FEATURES ENABLED** (vibrato, envelope type)

The family is defined by the CODE, not the DATA. Two games can
use identical assembly and still have different period table
formats, different bank layouts, and different feature flags.

## The Trace-First Workflow Vindicated

For Super C, the hypothesis document predicted:
- 90% Contra-compatible ✓ (command bytes match)
- Pointer table address is the only unknown ✓ (still unknown)
- EASY difficulty ✗ (the period table search failed)

What actually worked:
1. Capture Mesen trace (5 minutes)
2. Render WAV from trace (instant, game-agnostic pipeline)
3. User confirms "that's Stage 1 Thunder Landing" (10 seconds)
4. ROM scan for period table (15 minutes, FAILED)
5. Trace period analysis reveals vibrato and Contra-family tuning

The TRACE gave us ground truth in 5 minutes. The ROM scan gave
us confusion in 15 minutes. The trace revealed vibrato — a
feature we didn't know Super C used — which no amount of ROM
scanning would have shown without the disassembly.

**For the next game: capture first, scan second.**

## Updated Maezawa Family Model

```
MAEZAWA FAMILY (shared 6502 code lineage)
│
├── CV1 branch (1986)
│   ├── 12-entry period table (contiguous, exact Maezawa values)
│   ├── Parametric envelopes (fade_start/fade_step)
│   ├── Vibrato: code present but UNUSED
│   ├── Inline percussion (E9/EA)
│   └── Mapper 2 (UNROM), single sound bank
│
├── Contra branch (1988)
│   ├── 12-entry period table (contiguous, ±1 tuning variants)
│   ├── Lookup table envelopes (54 entries)
│   ├── Vibrato: code present but UNUSED
│   ├── Separate DMC percussion channel
│   ├── DX byte count: 3/1 (different from CV1's 2)
│   └── Mapper 2 (UNROM), sound bank = 1
│
├── Super C branch (1990)
│   ├── Period table: NOT FOUND as contiguous block
│   ├── Envelope model: UNKNOWN (likely lookup table)
│   ├── Vibrato: ACTIVE (±6 period modulation per frame)
│   ├── Percussion: UNKNOWN (likely DMC like Contra)
│   ├── Command set: matches Contra (E0-E4, DX, FE, FD, FF)
│   └── Mapper 2 (UNROM), sound bank: UNKNOWN
│
└── CV3 US branch (1990)
    ├── 36-entry extended period table (C1-B3, ±1 tuning)
    ├── Maezawa note encoding confirmed (pitch×16 + duration)
    ├── Mapper 5 (MMC5), 2 extra pulse channels
    └── Pointer structure: nested pairs (ch1_ptr, ch2_ptr)
```

Each branch shares the command vocabulary but diverges on data
layout, feature activation, and storage format. The family tree
is defined by CODE inheritance, not DATA compatibility.

## Next Steps for Super C

1. **Find the sound bank.** Set Mesen breakpoint on $4002 write
   during music playback. The calling code's bank tells us which
   bank contains the sound engine.

2. **Find the period table in that bank.** Once we know the bank,
   search it for period-like data in any format (contiguous,
   split, interleaved, or computed).

3. **Find the pointer table.** Once we have the bank and the
   driver code location, the pointer table is typically adjacent.

4. **Create manifest and test one track.** Configure contra_parser
   with Super C addresses and parse Thunder Landing. Compare to
   trace.

The Mesen debugger is now the critical tool. ROM scanning alone
can't crack Super C — we need to watch the driver execute.
