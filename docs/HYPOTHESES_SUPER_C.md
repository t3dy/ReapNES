# Super C (Super Contra) -- Hypotheses

## ROM Facts (Verified)

| Property | Value |
|----------|-------|
| Full title | Super C (US), Super Contra (JP) |
| Publisher | Konami |
| Year | 1990 |
| Mapper | **2 (UxROM)** -- same as Contra |
| PRG ROM | 8 banks x 16KB = 128KB |
| CHR ROM | 0 (CHR RAM) |
| Mirroring | Vertical |
| Battery | No |
| Composer(s) | Hidenori Maezawa, Kazuki Muraoka |

## Driver Family Hypothesis

**H1: Super C uses the Konami Maezawa driver, Contra variant.**

Confidence: **HIGH (0.90)**

Evidence:
- Same publisher (Konami), same mapper (2/UxROM), same PRG size (128KB)
  as Contra.
- Direct sequel to Contra (1988 vs 1990), same development team.
- 9 of 15 tracks parsed successfully using the CV1 parser (wrong pointer
  table, wrong DX byte count, wrong envelope model), which means the
  note/octave/rest command encoding is Maezawa-compatible.
- The DRIVER_TAXONOMY lists Super C as a known Maezawa family game with
  status "Partial (9/15)".
- rom_identify.py should confirm Maezawa DX+E8 signatures and locate
  the period table in ROM.

**H2: The DX byte count is 3 (pulse) / 1 (triangle), matching Contra.**

Confidence: **HIGH (0.85)**

Rationale: Same development team, same mapper, same era. The 6 tracks
that FAILED with the CV1 parser (which reads DX+2 bytes) likely failed
because the parser read too few bytes and fell out of alignment. The
Contra format (DX+3 for pulse, DX+1 for triangle) is the expected
match.

**H3: The envelope model uses lookup tables, matching Contra.**

Confidence: **MODERATE (0.75)**

Rationale: Contra moved from CV1's parametric fade_start/fade_step to
indexed envelope tables (54 entries, 8 per level). Super C, as a later
game by the same team, likely uses the same approach. However, the table
size, entry count, and location in ROM are unknown and may differ.

**H4: Percussion uses a separate DMC channel, matching Contra.**

Confidence: **HIGH (0.85)**

Rationale: Contra uses separate-channel DMC percussion (not inline
E9/EA like CV1). Super C likely follows the same pattern. Verify by
checking whether the pointer table has 4-channel entries (sq1, sq2,
tri, noise/dmc).

## Known Differences from Contra

### Pointer table location: UNKNOWN

This is the **single largest unknown**. The pointer table is NOT at
Contra's location ($48F8 ROM / $88E8 CPU in bank 1). The 6 failed
tracks prove the CV1 address ($0825) is also wrong. The correct pointer
table address must be found by:

1. Running rom_identify.py to scan for pointer table signatures
2. Scanning the ROM for clusters of 3-byte entries with addresses in
   $8000-$BFFF range (Contra's flat_sound_table format)
3. Using Mesen debugger: breakpoint on APU register writes ($4000),
   trace back to the data read address
4. Checking near Contra's offset ($48F8) -- Super C may use a similar
   layout at a different offset within the same bank

### Sound bank: UNKNOWN (likely bank 1)

Contra keeps all sound engine code and music data in bank 1. Super C
probably does the same (mapper 2, sound bank in lower PRG). Needs
verification.

### Envelope table contents: UNKNOWN

Even if the format matches Contra (indexed lookup tables), the actual
envelope shapes, table count, and ROM location will differ. Must extract
from ROM after confirming the driver variant.

### Track count and mapping: UNKNOWN

The nesmdb dataset has 14 tracks (indices 00-13). The existing CV1-based
extraction attempted 15 tracks. Mapping between track indices and song
names needs verification.

## The Problem: 9 Tracks Extracted with WRONG Parser

### What happened

The 9 tracks at `output/Super_C/` were extracted using the CV1 parser
with CV1's pointer table address ($0825). This is fundamentally wrong
in three ways:

1. **Wrong pointer table address.** The CV1 pointer table starts at ROM
   $0825 with 9 bytes per entry (3 pointers + 3 separator bytes). Super C
   has its own pointer table at an unknown location, likely in Contra's
   flat_sound_table format (3 bytes per entry). Reading from $0825 in the
   Super C ROM reads arbitrary data that happens to look like valid
   pointers for some tracks.

2. **Wrong DX byte count.** The CV1 parser reads DX + 2 extra bytes
   (instrument + fade). If Super C uses Contra's format (DX + 3 for
   pulse, DX + 1 for triangle), the CV1 parser consumes the wrong number
   of bytes after every DX command, causing cumulative alignment drift.
   This explains why 6 tracks crash with division-by-zero errors (the
   parser falls out of alignment and reads note data as commands).

3. **Wrong envelope model.** The CV1 parser applies parametric envelopes
   (fade_start + fade_step). If Super C uses lookup tables, all volume
   automation in the extracted MIDIs is incorrect -- the notes may have
   approximately right pitches but completely wrong dynamics.

### Why some tracks "worked"

The 9 tracks that parsed without crashing likely have data that, by
coincidence, aligns at the memory addresses the CV1 parser reads from
$0825. The note pitches may be approximately correct (Maezawa note
encoding is shared), but the envelope articulation is wrong. These
tracks should NOT be trusted as correct output.

### Existing output (treat as v1, unvalidated)

| Track | Files | Status |
|-------|-------|--------|
| 01 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 02 | -- | FAILED (parser error) |
| 03 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 04 | -- | FAILED (parser error) |
| 05 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 06 | -- | FAILED (parser error) |
| 07 | -- | FAILED (parser error) |
| 08 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 09 | -- | FAILED (parser error) |
| 10 | -- | FAILED (parser error) |
| 11 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 12 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 13 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 14 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |
| 15 | MIDI + WAV + REAPER | Parsed (WRONG parser, unvalidated) |

A full soundtrack MP4 and YouTube description also exist at
`output/Super_C/`, built from the 9 working tracks. These should be
considered v1 (unversioned) and replaced once correct extraction is done.

## What Needs to Happen for Correct Extraction

### Phase 1: Identification

1. Run `rom_identify.py` on the Super C ROM to confirm Maezawa
   signatures, mapper type, period table location, and PRG bank layout.
2. Search for an annotated disassembly (GitHub, romhacking.net). Search
   terms: "Super C NES disassembly", "Super Contra NES sound engine".
3. If no disassembly exists, use Mesen debugger to locate the pointer
   table by setting an APU write breakpoint.

### Phase 2: Manifest Creation

4. Create `extraction/manifests/super_c.json` using the Contra manifest
   as template. All values start as `hypothesis` until verified.
5. Document the pointer table address, sound bank, DX byte count,
   envelope model type, and track list.

### Phase 3: First Track Parsing

6. Configure `contra_parser.py` with Super C's pointer table address
   and bank number. Parse Stage 1 ("Thunder Landing / Area 1") as the
   reference track.
7. Generate MIDI and WAV to `output/Super_C_v2/`.
8. User listens and compares to game audio. This is the critical gate.

### Phase 4: Trace Validation

9. Capture APU trace from Mesen for Stage 1.
10. Add Super C config to `trace_compare.py` GAME_CONFIGS.
11. Iterate on mismatches, one hypothesis at a time.

### Phase 5: Envelope Extraction

12. If Contra-style lookup tables confirmed, extract the envelope table
    from ROM (locate `pulse_volume_ptr_tbl` equivalent).
13. If the envelope format differs, model from trace volume data (dump
    20 frames, fit parameters).

### Phase 6: Batch Extraction

14. Extract all tracks. Version output as v2.
15. Generate REAPER projects and WAVs for complete soundtrack.
16. Final ear-check on 3-5 tracks against game audio.

## Predicted Difficulty

**EASY** -- the easiest new game target in the project.

| Factor | Assessment |
|--------|-----------|
| Driver family | Known (Maezawa, Contra variant) |
| Mapper | 2 (UxROM) -- identical to Contra, bank switching understood |
| Parser exists | Yes -- `contra_parser.py` handles this command set |
| DX byte count | Likely Contra-compatible (3/1), needs verification only |
| Envelope model | Likely Contra-compatible (lookup tables), needs extraction |
| Disassembly | Not found, but not required -- Contra parser + Mesen debugger suffice |
| Expansion audio | None -- base APU only |
| Blocking unknowns | Pointer table address (solvable with rom_identify or Mesen) |

The ONLY bottleneck is finding the pointer table address. Once that is
known, `contra_parser.py` should work with minimal or no code changes --
just configuration (manifest-driven addresses).

Estimated effort: **3-5 sessions**.
- Best case (pointer table found quickly, Contra-identical driver): 3
- Worst case (pointer table requires Mesen debugging, minor envelope
  differences): 5

Compare to CV3 (MEDIUM, 8-12 sessions) which requires MMC5 bank
switching, unknown pointer architecture, and no parser to start from.

## NESMDB Reference Data

14 Super C tracks exist in the nesmdb dataset (game ID 317). These can
be rendered to WAV for ear-matching reference audio.

| nesmdb Index | Track Name |
|-------------|-----------|
| 00 | Thunder Landing (Area 1) |
| 01 | Great Heli / Ruined Base / Boss 1 |
| 02 | Pattern Clear 1 / Area Clear |
| 03 | In a Tight Squeeze (Area 2) |
| 04 | Ruined Base / Boss 2 |
| 05 | Jungle Juncture (Area 3) |
| 06 | Creature from Outer Space / Boss 3 |
| 07 | No Escape (Area 4 & 7) |
| 08 | M-3 (Area 5) |
| 09 | Hotter Than Hell (Area 6) |
| 10 | Deathbed (Area 8) |
| 11 | Pattern Clear 2 / All Area Clear |
| 12 | Free World / Ending |
| 13 | Game Over |

Location: `data/nesmdb/nesmdb24_exprsco/train/317_SuperC_*.exprsco.pkl`

Note: nesmdb has 14 tracks. The existing extraction attempted 15. The
discrepancy may mean track 15 is a short jingle or SFX not included in
nesmdb, or the CV1 parser's track count was wrong for Super C.

## Comparison: Super C vs Contra vs CV1

| Aspect | CV1 | Contra | Super C (hypothesis) |
|--------|-----|--------|---------------------|
| Year | 1986 | 1988 | 1990 |
| Mapper | 2 (UxROM) | 2 (UxROM) | 2 (UxROM) |
| PRG size | 128KB | 128KB | 128KB |
| Sound bank | N/A (linear) | Bank 1 | Bank 1 (hypothesis) |
| Pointer table | $0825, 9 bytes/entry | $48F8, 3 bytes/entry | Unknown, likely 3 bytes/entry |
| DX extra bytes (pulse) | 2 | 3 | 3 (hypothesis) |
| DX extra bytes (triangle) | 0 | 1 | 1 (hypothesis) |
| Percussion | Inline E9/EA | Separate DMC | Separate DMC (hypothesis) |
| Envelope model | Parametric | Lookup table (54 entries) | Lookup table (hypothesis) |
| Track count | 15 | 11 | 14 (per nesmdb) |
| Parser | parser.py | contra_parser.py | contra_parser.py (hypothesis) |

## Recommended Next Steps

1. **Run rom_identify.py** on Super C ROM. Confirm mapper 2, Maezawa
   signature, period table location.

2. **Find the pointer table.** This is the critical path. Options:
   - rom_identify.py may detect it automatically
   - Scan ROM for flat_sound_table signature (clusters of 16-bit
     addresses at 3-byte intervals in $8000-$BFFF range)
   - Mesen debugger: breakpoint $4000 write, trace to data source

3. **Create manifest.** `extraction/manifests/super_c.json` with all
   hypothesized values from this document.

4. **Parse one track.** Stage 1 ("Thunder Landing") using contra_parser
   with Super C addresses. Listen and compare to game.

5. **Do NOT re-extract using the CV1 parser.** The existing v1 output
   is wrong. All future work must use contra_parser with the correct
   pointer table.

6. **Version all new output as v2.** Never overwrite the existing
   `output/Super_C/` directory. Use `output/Super_C_v2/`.

## Files

| File | Purpose |
|------|---------|
| `output/Super_C/` | Existing v1 output (WRONG parser, unvalidated) |
| `data/nesmdb/nesmdb24_exprsco/train/317_SuperC_*` | 14 nesmdb reference tracks |
| `extraction/drivers/konami/contra_parser.py` | Parser to use (with new addresses) |
| `extraction/manifests/contra.json` | Template for Super C manifest |
| `docs/wishes/WISH_03_SUPER_C.md` | Detailed wish document with 28-step plan |
| This document | Hypotheses and analysis |
