# Gradius (NES, Konami 1986) — Hypotheses

## ROM Facts (VERIFIED by direct ROM analysis)

| Property | Value |
|----------|-------|
| Publisher | Konami |
| Release year | 1986 (April Famicom, December NES) |
| Mapper | **3 (CNROM)** — NOT mapper 0 as initially predicted |
| PRG ROM | 2 × 16KB = **32KB** (linear, no PRG bank switching) |
| CHR ROM | 4 × 8KB = 32KB (CHR banking only) |
| Expansion audio | None (base APU only) |
| NMI vector | $806A |
| RESET vector | $8010 |

## Critical Finding: NOT Maezawa

**No standard period table exists anywhere in the ROM.**

Exhaustive searches performed:
- Full 12-entry Maezawa table (16-bit LE) → **NOT FOUND**
- CV3-style modified table (±1 tuning) → **NOT FOUND**
- Any chromatic 12-entry descending period sequence → **NOT FOUND**
- Split lo/hi byte period tables → **NOT FOUND**
- Any 12 or 16 consecutive 16-bit values with semitone ratios → **NOT FOUND**

**This is definitively NOT a Maezawa-family driver.** The initial hypothesis
(H1: Maezawa, confidence 0.65) is **rejected**.

## What the Driver Actually Looks Like

### E-Command System (16 values, NOT 5)

All 16 values E0-EF appear with roughly even distribution:

```
E0: 196   E4: 156   E8: 208   EC: 103
E1: 205   E5: 124   E9:  99   ED:  67
E2: 317   E6: 124   EA:  54   EE:  84
E3: 264   E7: 119   EB:  71   EF:  62
```

In Maezawa, only E0-E4 are used (octave select). Gradius uses **all 16**.

### E-commands appear in variable-length groups

```
1 E-cmd in a row: 1347x
2 in a row:         88x
3 in a row:         26x
4 in a row:         29x
5 in a row:         15x
6 in a row:         10x
7 in a row:          5x
8 in a row:         18x
10+ in a row:       17x
```

Each group is followed by small-value bytes (0x00, 0x01, 0x04, 0x08, 0x3C, 0x40).

### Observed patterns

```
[E3 E4 E0 E1 E2 E7] -> [0x08 0x04 0x01]
[E8 E0 E1 E2]        -> [0x40 0x40 0x01 0x3C 0x01 0x01 0x00]
[E0 E2 E7 E8]        -> [0x3B 0x00 0x04 0x08 0x00 0x40 0x08 0x04]
[E9 EA]               -> [0x00 0x3F]
[E8 E0 E1 E2 EB EC]  -> [0x01]
```

### Hypothesis H1: E-commands set individual APU parameters

Each Ex byte programs one register parameter. A group sets up a complete
note (pitch, volume, duty, envelope, length). The following bytes are
duration/timing values.

Frequently co-occurring: E0, E2, E7, E8 (the "core note" group).
E3/E4 appear to modify timbre or set octave.
E9-EF are less common — possibly effects (vibrato, pitch bend, etc.).

### Hypothesis H2: Periods are computed, not stored

With no lookup table, the driver likely computes NES period values
from note indices using arithmetic at runtime. This was common in
early NES drivers before table-driven approaches became standard.

### Hypothesis H3: Pre-Maezawa driver

Gradius Famicom shipped **5 months before CV1**. This driver is likely
the predecessor to Maezawa's engine — or a completely separate engine
used only for arcade ports.

## Pointer Architecture

Two flat pointer tables found:

| Table | CPU Address | Entries | Target Range | Purpose |
|-------|------------|---------|-------------|---------|
| Table 1 | $D7E2 | 40 | $DA87-$DBF2 | Channel 1 phrases |
| Table 2 | $D83A | 31 | $DBDF-$DE50 | Channel 2 phrases |

Between the tables: 4 "bridge" pointers at $D832 pointing into the
$DC range — possibly song-level structure indices.

Music data occupies ~1,480 bytes ($DA87-$DE50).
Driver code likely occupies $D000-$D7E0.

## Other Command Bytes Present

| Byte | Count | Likely Role |
|------|-------|-------------|
| D0-DF | 1,079 | Instrument/timbre changes (same range as Maezawa DX) |
| FE | 262 | Repeat/loop marker |
| FD | 132 | Subroutine call |
| FF | 391 | End of phrase/stream |
| FB | 57 | Unknown command |

FE, FD, FF semantics appear to match Maezawa control flow conventions.
This suggests **partial command compatibility** — the control flow may
be shared even though the note encoding is completely different.

## Predicted Difficulty

**HIGH.** This requires a new driver RE project.

| Factor | Assessment |
|--------|-----------|
| Period table | NONE — must decode from E-command groups |
| Note encoding | Unknown — 16 E-values, not Maezawa pitch×16+dur |
| Banking | None (32KB linear) — simplest possible |
| ROM size | 32KB — small search space, tractable for manual RE |
| Disassembly | None known — check nesdev/romhacking.net |
| Existing parser reuse | ~0% for notes, ~30% for FE/FD/FF control flow |

## Recommended Strategy

**DEPRIORITIZE.** Gradius is the hardest Konami target in the queue.
Do Super C, CV3, and Goonies II first (all confirmed/likely Maezawa).

If proceeding:
1. **Search for Gradius NES disassembly** — this would save weeks
2. **Capture Mesen trace** of "Challenger 1985" with APU write breakpoints
3. **Trace the E-command decoder** — set breakpoint on $4002/$4003 writes,
   trace backwards to find which ROM bytes determine the period value
4. **Decode the E-command→period mapping** — this is THE key to cracking it
5. **Build minimal prototype parser** for one track once encoding is known

## Reference Renders

12 Gradius tracks rendered from nesmdb:
`output/Gradius/wav/nesmdb/gradius_XX_name.wav`

| # | Track | Duration |
|---|-------|----------|
| 00 | Coin | 0.7s |
| 01 | Beginning of History | 10.3s |
| 02 | Challenger 1985 | 11.2s |
| 03 | Beat Back | 8.9s |
| 04 | Blank Mask | 8.2s |
| 05 | Free Flyer | 8.3s |
| 06 | Mazed Music | 7.2s |
| 07 | Mechanical Globule | 13.6s |
| 08 | Final Attack | 9.5s |
| 09 | Aircraft Carrier | 3.1s |
| 10 | Ending | 4.5s |
| 11 | Game Over | 2.3s |

## Files

| File | Purpose |
|------|---------|
| `extraction/roms/gradius.nes` | Gradius US ROM |
| `output/Gradius/wav/nesmdb/` | 12 reference WAV renders |
| This document | Verified hypotheses from ROM analysis |
