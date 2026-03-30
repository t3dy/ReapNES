# WISH #11: Castlevania II Investigation Revisited

## 1. What This Wish Is

Re-evaluate the Castlevania II: Simon's Quest extraction that was
previously labeled a "dead end" due to the Fujio driver (not Maezawa).
The earlier CV2 investigation (documented in `docs/MOVINGONTOCV2.md`)
concluded that CV2 uses a completely different sound engine and pivoted
to Contra. However, the Antigravity session subsequently ran the CV1
full pipeline against the CV2 ROM and produced 7 tracks with MIDI, WAV,
REAPER projects, and a combined MP4 video. These 7 tracks need to be
audited for correctness: some may be garbled artifacts of running the
wrong parser, while others may coincidentally contain real music data.

## 2. Why It Matters

- **CV2 has an iconic soundtrack.** Bloody Tears and Simon's Theme are
  among the most recognized NES compositions. If even partial extraction
  is achievable, the musical value is high.
- **The "dead end" label may be premature.** The Antigravity session
  produced 7 tracks that rendered to WAV without crashing. The original
  investigation found that 7/15 tracks survived when the CV1 parser
  read CV2's ROM (the other 8 hit division-by-zero or were empty). The
  surviving tracks may contain real note data that happens to parse
  under the Maezawa command set, even though the driver is different.
- **Palette extraction worked.** The Antigravity session successfully
  extracted CV2 instrument envelopes (Bloody Tears, Silence of the
  Daylight, Monster Dance) from `preset_bank.json` for Bach mashups.
  This confirms the preset bank contains CV2 tonal data, even if the
  parser is wrong.
- **Understanding the Fujio driver opens 2-3 additional games.** The
  driver taxonomy (`docs/DRIVER_TAXONOMY.md`) estimates 2-3 games use
  the Fujio variant. Cracking CV2 would unlock a new driver family.

## 3. Current State

### Extracted Tracks (7 total)

These tracks were produced by the Antigravity session using the CV1
Maezawa parser against the CV2 ROM. Track numbers are CV1 pointer
table indices, NOT CV2 track IDs:

| Track | MIDI | WAV | REAPER | YouTube Duration |
|-------|------|-----|--------|-----------------|
| 02 | Yes | Yes | Yes | 0:00 - 0:44 |
| 05 | Yes | Yes | Yes | 0:44 - 0:50 |
| 07 | Yes | Yes | Yes | 0:50 - 1:16 |
| 08 | Yes | Yes | Yes | 1:16 - 1:36 |
| 10 | Yes | Yes | Yes | 1:36 - 2:25 |
| 12 | Yes | Yes | Yes | 2:25 - 3:36 |
| 13 | Yes | Yes | Yes | 3:36 - end |

Output location: `output/Castlevania_II/`

A full MP4 (`Castlevania_II_full_soundtrack.mp4`) and YouTube
description were generated. The YouTube description labels the driver
as "Konami Pre-VRC (Maezawa variant)" which is incorrect -- CV2 uses
the Fujio variant.

### What the Original Investigation Found

From `docs/MOVINGONTOCV2.md`:

- CV2 uses mapper 1 (MMC1), 128KB PRG, 16 CHR banks
- Period table found at ROM $1C2D (same NTSC tuning values as CV1)
- Only 10 E8 bytes in ROM, all in machine code (6502 INX instruction)
- No Maezawa pointer table format (9-byte or 6-byte entries) found
- No Maezawa command signatures (DX/FE/FD patterns) confirmed
- Conclusion: different driver, different composer (Kenichi Matsubara)

### What the GAME_MATRIX Says

CV2 is listed as `BLOCKED` with the note "Different driver entirely."
Driver confirmed: NO (Fujio variant). 0 tracks officially decoded.
The 7 tracks from the Antigravity session are not reflected in the
matrix because they were produced using the wrong parser.

### What the Driver Taxonomy Says

Section 10.1 ("Konami Fujio Variant") describes CV2 as sharing NTSC
period table values with Maezawa but having a "completely different
command interpreter." Estimated 2-3 games in this family. Confidence
level: LOW. Requires independent reverse engineering.

## 4. Concrete Steps

### Phase 1: Listening Audit (1-2 hours)

1. Play each of the 7 WAV files in `output/Castlevania_II/wav/`
2. Compare each against the actual CV2 game audio (play the ROM in
   Mesen or use a YouTube reference recording)
3. For each track, classify as:
   - **MATCH**: recognizable CV2 music, roughly correct pitch/rhythm
   - **GARBLED**: sounds like noise, wrong notes, or nonsensical data
   - **PARTIAL**: some recognizable elements mixed with garbage
4. Document findings per track with timestamps of notable issues

### Phase 2: ROM Analysis (2-3 hours)

1. Run `rom_identify.py` on the CV2 ROM to get the full diagnostic
   output (mapper, period table, command signatures)
2. Use Mesen debugger to set breakpoints on APU register writes
   ($4000-$4017) during known CV2 music playback
3. Trace the call stack backward from APU writes to find the sound
   engine entry point
4. Identify the music data pointer table by watching which ROM
   addresses the engine reads from during track changes

### Phase 3: Fujio Driver Characterization (4-8 hours)

1. Disassemble the CV2 sound engine from the entry point found in
   Phase 2
2. Document the command format: how are pitch, duration, volume,
   and control flow encoded?
3. Compare against Maezawa command set to identify similarities and
   differences
4. Determine DX-equivalent byte count, loop/subroutine mechanism,
   and envelope model
5. Write findings to a new manifest: `extraction/manifests/cv2.json`

### Phase 4: Parser Prototype (4-6 hours)

1. Write `extraction/drivers/konami/fujio_parser.py` based on the
   characterized command format
2. Parse one known track (e.g., Bloody Tears) and render to WAV
3. Compare against game audio -- this is the gate
4. If the reference track passes, parse remaining tracks

### Phase 5: Cleanup (1-2 hours)

1. Update `GAME_MATRIX.md` to change CV2 status from BLOCKED to
   IN_PROGRESS or COMPLETE
2. Update `DRIVER_TAXONOMY.md` Section 10.1 with verified Fujio
   driver details
3. Re-render CV2 tracks with correct parser, replacing the
   Antigravity session output
4. Fix the YouTube description to reference the Fujio driver

## 5. Estimated Effort

| Phase | Hours | Sessions | Confidence |
|-------|-------|----------|------------|
| Phase 1: Listening Audit | 1-2 | 1 | HIGH (just listening) |
| Phase 2: ROM Analysis | 2-3 | 1 | MEDIUM (Mesen debugging) |
| Phase 3: Driver Characterization | 4-8 | 2-3 | LOW (unknown territory) |
| Phase 4: Parser Prototype | 4-6 | 1-2 | MEDIUM (if Phase 3 succeeds) |
| Phase 5: Cleanup | 1-2 | 1 | HIGH (mechanical) |
| **Total** | **12-21** | **6-8** | |

Phase 1 alone has value even if later phases are not pursued -- it
tells us whether the existing 7 tracks are usable or should be deleted.

## 6. Dependencies

- **Mesen emulator with debugger**: Required for Phase 2 APU tracing.
  Must be installed and configured to load the CV2 ROM.
- **CV2 ROM**: Must be present in `AllNESROMs/` (Castlevania II -
  Simon's Quest (USA).nes or equivalent GoodNES name).
- **Reference audio**: Either play CV2 in Mesen with audio output, or
  use a known-good YouTube recording of the complete CV2 soundtrack for
  the Phase 1 listening comparison.
- **No code dependencies**: The Fujio parser would be a new module. It
  does not depend on any in-progress Contra work.
- **rom_identify.py**: Already built and functional. No changes needed
  for Phase 2 step 1.

## 7. Risks

### HIGH RISK: Fujio driver may be fundamentally incompatible with the pipeline

The existing pipeline assumes pitch+duration encoded in a single byte
(Maezawa style). If the Fujio driver uses a multi-byte opcode format
(like Capcom or Sunsoft), the parser architecture would need significant
changes. The frame IR and MIDI export should still work since they are
driver-agnostic, but the parser layer may not fit the current
`ParsedSong` / `ParsedNote` contract without modifications.

### MEDIUM RISK: No disassembly exists

The original investigation found no annotated CV2 sound driver
disassembly. All Phase 3 work must be done from scratch using Mesen
debugger traces. This is significantly harder than the Contra path
(which had a complete annotated disassembly in `references/`).

### MEDIUM RISK: The 7 existing tracks may all be garbled

If the CV1 pointer table at $0825 points to arbitrary CV2 ROM
locations, the "tracks" are just the parser interpreting random bytes
as Maezawa commands. They may sound vaguely musical due to the
constrained note range (0x00-0xBF maps to valid pitches), but they
would not correspond to any actual CV2 composition.

### LOW RISK: Mapper 1 bank switching complications

MMC1 uses a serial-load register for bank selection (5 consecutive
writes to configure). The CPU-to-ROM address mapping is more complex
than mapper 2 (UNROM). However, mapper 1 is well-documented on NESdev
wiki and Mesen handles it transparently during debugging.

## 8. Success Criteria

### Minimum Viable (Phase 1 only)

- Each of the 7 tracks is classified as MATCH, GARBLED, or PARTIAL
- A written verdict on whether any tracks contain real CV2 music
- The `GAME_MATRIX.md` entry is updated to reflect findings
- Decision made on whether to proceed to Phase 2 or archive the
  existing output as "wrong parser, historical artifact"

### Full Success (all phases)

- Fujio driver command format documented in a manifest JSON
- At least one CV2 track (preferably Bloody Tears) parsed correctly
  and ear-validated against game audio
- `fujio_parser.py` exists and can extract CV2 tracks
- CV2 status in GAME_MATRIX upgraded from BLOCKED to IN_PROGRESS
- Driver Taxonomy updated with verified Fujio details
- Zero reliance on the Maezawa parser for CV2 output

## 9. Priority Ranking

**Priority: LOW-MEDIUM (P3)**

Rationale:

- The Fujio driver is a brand-new reverse engineering effort with no
  disassembly to guide it. This is the highest-risk, highest-effort
  category of work in the project.
- Contra (IN_PROGRESS) should reach completion before starting a new
  driver family. The triangle pitch drift and vibrato implementation
  are known, bounded problems.
- The remaining untested Maezawa-family games (Gradius, Goonies II,
  Super C) offer much higher ROI -- they can reuse existing parsers
  with only configuration changes.
- However, Phase 1 (listening audit) is zero-risk and takes 1-2 hours.
  It should be done regardless of whether the full investigation
  proceeds, because it resolves the question of whether the existing
  7 tracks should be kept or discarded.

Recommended sequencing:
1. Complete Contra to COMPLETE status
2. Extract 2-3 easy Maezawa games (Gradius, Super C, Goonies II)
3. Run Phase 1 listening audit for CV2
4. If Phase 1 shows any MATCH tracks, proceed to Phase 2+
5. If all tracks are GARBLED, archive and deprioritize

---

*Filed: 2026-03-29*
*Related: docs/MOVINGONTOCV2.md, docs/GAME_MATRIX.md, docs/DRIVER_TAXONOMY.md*
*Output under review: output/Castlevania_II/*
