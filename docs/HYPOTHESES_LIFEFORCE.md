# Life Force / Salamander (Konami, 1988) — Hypotheses

## ROM Facts (Verified)

| Property | Value |
|----------|-------|
| Title | Life Force (US) / Salamander |
| Publisher | Konami |
| Year | 1988 |
| Mapper | **2 (UxROM)** |
| PRG ROM | 128KB (8 x 16KB banks) |
| CHR ROM | 0 (CHR RAM) |
| Mirroring | Vertical |
| Expansion audio | None (base APU only) |

Life Force uses the same mapper (UxROM, mapper 2) as Contra and Super C.
128KB PRG with bank switching means the sound engine is in one bank and
music data may span multiple banks, requiring the same bank-resolution
approach used for Contra.

## Driver Family Hypothesis

### H1: Maezawa Family (HIGH confidence)

Life Force is listed in `DRIVER_TAXONOMY.md` as a known Konami Maezawa
family game (section 1.2). The evidence chain:

1. **Publisher**: Konami, 1988 — squarely within the Maezawa driver's
   active period (~1986-1990).
2. **Mapper**: UxROM (mapper 2), same as Contra (1988) and Super C (1990).
3. **Timeframe**: Released the same year as Contra (both 1988). The sound
   driver would have been available as internal Konami middleware.
4. **No expansion hardware**: Base APU only, consistent with pre-VRC
   Konami drivers.

### H2: Closer to Contra than CV1 (MEDIUM confidence)

Life Force and Contra are both 1988 UxROM Konami games with 128KB PRG.
Hypothesis: Life Force's sound engine is the same binary (or a close
variant) as Contra's, meaning:

- DX byte count is likely 3/1 (pulse/triangle), not 2/0 (CV1)
- Envelope model is likely lookup-table-based, not parametric
- Percussion is likely separate DMC channel, not inline E9/EA
- Pointer table is likely a flat `sound_table` format, not the 9-byte
  grouped format of CV1

This hypothesis must be verified by scanning for DX+byte patterns and
checking the pointer table structure.

### H3: Not Fujio Variant (HIGH confidence)

CV2 (Simon's Quest, 1987) uses a different engine (Fujio variant) despite
sharing the Konami period table. Life Force is NOT expected to be a Fujio
variant because:

- Fujio is associated with CV2 specifically, not the broader Konami catalog
- Life Force is a horizontal shooter, not an adventure/RPG — different
  development team than CV2
- The Maezawa driver was the standard Konami middleware for action games

## Relationship to Gradius

### H4: Shared Driver with Gradius (MEDIUM-LOW confidence)

Gradius (1986, mapper 0/NROM) is the parent franchise. Life Force/Salamander
is the arcade spinoff brought to NES. Key considerations:

- Gradius NES is mapper 0 (NROM, 32KB linear), Life Force is mapper 2
  (UxROM, 128KB bank-switched). The ROM layout differs fundamentally.
- Gradius predates Life Force by 2 years. The sound engine may have
  evolved between releases.
- Both are Konami games in the Maezawa active period, so both likely use
  Maezawa-family drivers — but the specific variant (DX byte count,
  envelope model) may differ between the 1986 NROM and 1988 UxROM builds.

**Prediction**: The command set (note encoding, octave commands, loop/repeat
structure) is shared. The data layout (pointer table format, DX parameters,
envelope strategy) likely differs due to the mapper and year gap. Gradius
may be closer to CV1 (1986, NROM, parametric envelopes) while Life Force
is closer to Contra (1988, UxROM, lookup envelopes).

### H5: Different Composer, Possibly Different Data Layout

Gradius NES music was composed by Miki Higashino and others. Life Force
NES music credits are less clear but the arcade version was Konami's
internal sound team. Even within the same driver family, different
composers may use different instrument configurations and envelope
strategies. The driver code is shared; the data conventions may not be.

## Key Unknowns

| Unknown | Impact | How to Resolve |
|---------|--------|----------------|
| DX byte count (pulse) | Parser correctness | Scan ROM for DX patterns, count following bytes |
| DX byte count (triangle) | Parser correctness | Same scan, triangle channel data |
| Envelope model | Volume fidelity | Trace capture + per-frame volume analysis |
| Pointer table address | Track extraction | Disassembly or Mesen debugger breakpoint |
| Pointer table format | Track extraction | Read entries and verify structure |
| Percussion type | Noise/DMC channel | Check for E9/EA in music data vs separate DMC |
| Sound bank number | Address resolution | Identify which 16KB bank holds engine code |
| Track-to-stage mapping | Naming output files | Play game and match audio |

## Period Table

### H6: Standard Chromatic Period Table (HIGH confidence)

All known Konami Maezawa family games use the same NTSC period table
(or values within +/-1 of it). Life Force will almost certainly use
the same 12-entry base period table with octave-shifted variants:

```
C=1710, C#=1614, D=1524, D#=1438, E=1358, F=1281,
F#=1209, G=1142, G#=1078, A=1017, A#=960, B=906
```

The period table is a hardware-derived constant (NTSC APU clock / desired
frequency), not a driver design choice. Finding it in the ROM is useful
as a **locator** for the sound engine bank, but its presence does NOT
confirm the driver family (per the CV2 lesson in MISTAKEBAKED.md).

## Predicted Difficulty

**MEDIUM**

Factors reducing difficulty:
- UxROM mapper 2 is well understood (same as Contra)
- Likely Maezawa family, so existing command decoder applies
- No expansion audio to handle
- Base APU only = standard 4-channel output

Factors increasing difficulty:
- No known disassembly for Life Force NES sound engine
- DX byte count and envelope model are unknown — must be determined
  empirically or through Mesen trace analysis
- Bank-switched ROM means address resolution needs to be configured per-game
- If the driver variant is closer to Contra, volume envelope lookup tables
  must be located and extracted from ROM

**Comparison to other games**:
- Easier than CV3 (no MMC5 banking complexity, no expansion audio)
- Similar difficulty to Super C (same mapper, same era, likely same variant)
- Harder than CV1 (bank switching adds complexity)

## Known Tracks

Life Force has approximately 8-12 music tracks:

| Track | Context | Character |
|-------|---------|-----------|
| Stage 1 (Organic) | Power of Anger | Driving pulse lead, fast tempo |
| Stage 2 (Fire/Prominence) | Burning Heat | Intense, ascending patterns |
| Stage 3 (Floating Temple) | Planet Ratis | Mid-tempo, atmospheric |
| Stage 4 (Cell) | Overheat | Dense, rhythmic |
| Stage 5 (Mechanical) | Crash | Mechanical feel |
| Stage 6 (Final) | Starfield | Building intensity |
| Boss theme | Boss encounter | Short, tense loop |
| Game Over | Death screen | Brief |
| Stage Clear | Victory | Brief fanfare |
| Title screen | Menu | Introduction theme |
| Ending | Credits | Longer, triumphant |

The arcade Salamander soundtrack is well-known. The NES port rearranges
tracks for the hardware — some stages may share music or use simplified
versions of the arcade originals. The NES versions are distinct
compositions, not direct ports of the arcade FM synth arrangements.

## Recommended Next Steps

1. **Run `rom_identify.py`** on the Life Force ROM to confirm mapper,
   PRG size, and scan for Maezawa driver signatures (period table, DX/FE
   patterns). This is mandatory before any parser work.

2. **Search for existing disassembly** — check romhacking.net, GitHub,
   and NESdev for any Life Force sound engine documentation. A disassembly
   would immediately resolve the DX byte count, pointer table, and
   envelope model unknowns.

3. **Create manifest** at `extraction/manifests/lifeforce.json` with
   verified ROM facts and hypotheses marked with confidence levels.

4. **Locate the period table** in ROM via hex search for the known
   Maezawa sequence (06 AE 06 4E 05 F4...). The bank containing it
   likely holds the sound engine.

5. **Capture a Mesen APU trace** of Stage 1 (Power of Anger) as the
   reference track. This is the most recognizable track and will serve
   as the validation target.

6. **Determine DX byte count** by finding DX commands near the period
   table bank and counting subsequent bytes before the next note/command.

7. **Parse ONE track and listen** before attempting batch extraction.
   Compare against game audio, not assumptions.

## Files

| File | Purpose |
|------|---------|
| This document | Hypotheses and analysis |
| `extraction/manifests/lifeforce.json` | To be created: per-game config |
| `extraction/drivers/konami/spec.md` | Command format reference |
| `docs/DRIVER_TAXONOMY.md` | Driver family classification |
