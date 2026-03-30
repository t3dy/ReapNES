# Jackal (Konami, 1988) -- Hypotheses

## ROM Facts (To Be Verified)

| Property | Value |
|----------|-------|
| Publisher | Konami |
| Year | 1988 |
| Mapper | **2 (UxROM)** (hypothesis -- standard for Konami action titles of this era) |
| PRG ROM | Likely 128KB (8 x 16KB banks, same as Contra) |
| CHR ROM | Likely 0 (CHR-RAM, typical for UxROM) |
| Mirroring | TBD -- run `rom_identify.py` |
| Battery | No |

**Status**: These are predictions based on Konami's 1988 catalog patterns. Mapper and PRG size MUST be confirmed with `rom_identify.py` before any parser work begins. Jackal shipped on the same UxROM board type Konami used for Contra, Top Gun, and other 1987-1988 titles. If mapper is NOT 2, all bank-switching assumptions below are invalid.

## Driver Family Hypothesis

**H1: Jackal uses the Konami Maezawa pre-VRC driver family.**

Rationale:
- Konami (1988), same year as Contra, same approximate dev team era
- No expansion audio chips (base APU only on UxROM)
- Composer: likely Maezawa or a colleague using the same internal sound engine
- Konami reused their pre-VRC driver extensively across 1986-1990 titles (CV1, Contra, Super C, TMNT, Goonies II, Life Force)
- The DRIVER_TAXONOMY lists 8-12 games in this family with HIGH reuse level

Confidence: 0.75. This is the most likely driver family, but "same publisher, same era" is exactly the kind of assumption that burned us on CV2 (Fujio variant, not Maezawa). Must verify with DX/FE/FD command signatures before writing any code.

**H2: Jackal uses the Contra branch (1988) rather than the CV1 branch (1986).**

Rationale:
- Contra and Jackal are both 1988 UxROM releases
- The Maezawa driver evolved between CV1 (1986) and Contra (1988): DX byte count changed from 2 to 3/1, envelope model changed from parametric to lookup table, percussion moved from inline E9/EA to separate DMC channel
- Games from the same year are more likely to share the same driver revision

Confidence: 0.55. This is a plausible guess, not a fact. The driver may have branched differently for Jackal. The DX byte count question is the single most important thing to determine early.

## Key Questions

### Q1: DX Byte Count -- CV1 variant (DX=2) or Contra variant (DX=3/1)?

This is the critical fork. The two known branches:

| Variant | DX bytes (pulse) | DX bytes (triangle) | Envelope Model |
|---------|-------------------|---------------------|----------------|
| CV1 (1986) | 2 (instrument + fade) | 0 | Parametric (fade_start/fade_step) |
| Contra (1988) | 3 (config + vol_env + decrescendo) | 1 (triangle config) | Lookup table |

If Jackal is DX=3/1, the Contra parser can be adapted with address changes. If DX=2, the CV1 parser path applies. If it is something else entirely, a new branch may be needed.

**How to determine**: Find a DX command in the ROM music data and count the bytes before the next note/rest/octave command. Alternatively, if a disassembly exists, read the DX handler directly.

### Q2: Is there an annotated disassembly available?

Check `references/` and the romhacking.net/nesdev community. An annotated Jackal disassembly would resolve Q1, Q3, and Q4 immediately. Without one, all answers require trace analysis or manual ROM scanning.

### Q3: Pointer Table Format and Location

Two known formats:

| Game | Format | Location |
|------|--------|----------|
| CV1 | 9 bytes/track (3 ptrs + 3 separator bytes) | ROM $0825 |
| Contra | Flat `sound_table_00` (3 bytes/entry) | ROM $48F8 (bank 1) |

Jackal's pointer table format is unknown. If mapper 2 with bank switching, the table is likely in the sound bank (need to identify which bank). The FD/FE target addresses can help locate the table by working backwards from known music data.

### Q4: Percussion Model

| CV1 | Contra |
|-----|--------|
| Inline E9/EA triggers (snare/hi-hat) | Separate DMC channel with sample playback |

Jackal has percussion. Which model it uses affects whether the noise channel data stream contains inline percussion commands or whether there is a dedicated 4th channel.

### Q5: Period Table Location

The standard Maezawa 12-entry period table should be present if this is the same family. Scanning for the known byte sequence (starting with $06AE for C, $064E for C#) will help confirm driver identity and locate the sound bank.

## Envelope Model

**Unknown.** Two possibilities:

1. **Parametric (CV1 style)**: fade_start + fade_step parameters after DX. Simple two-phase decay. No envelope tables in ROM.
2. **Lookup table (Contra style)**: vol_env byte indexes into a table of per-frame volume values. 54 entries in Contra.

The envelope model follows from the DX byte count (Q1). If DX=2, likely parametric. If DX=3, likely lookup table. A Mesen APU trace of the first few seconds of gameplay music will show the volume envelope shape and confirm which model is in use.

## Predicted Difficulty

**MEDIUM.**

Favorable factors:
- Almost certainly Maezawa family, meaning the core note/octave/rest/loop command set is already decoded
- UxROM mapper 2 is well understood (same as Contra)
- Base APU only, no expansion chip complications
- Existing parser infrastructure can be adapted

Challenging factors:
- Need to determine which Maezawa branch (CV1 vs Contra)
- No known disassembly (unlike Contra, which has a full annotated source)
- Pointer table location and format must be discovered
- Envelope model must be verified before volume automation will be correct
- If the driver turns out NOT to be Maezawa (like CV2), the effort resets to zero

## Known Tracks

Jackal has approximately 6-8 distinct music tracks:

| Context | Description |
|---------|-------------|
| Title screen | Title theme |
| Stage 1 | Opening stage music |
| Stage 2 | Second stage music |
| Stage 3-6 | Later stage themes (may reuse or have unique tracks) |
| Boss | Boss encounter music |
| Game over | Game over jingle |
| Ending | Victory/ending theme |

Exact track count and mapping to ROM data will be determined once the pointer table is located. Reference audio from gameplay recordings or NSF rips can be used for ear-matching.

## Recommended Next Steps

Follow the workflow in CLAUDE.md section "Workflow: New Game":

1. **Run `rom_identify.py`** on the Jackal ROM. Confirm mapper type, PRG size, and check for Maezawa period table signature. This is step 0 -- do not skip.

2. **Search for disassembly** in `references/` and online (romhacking.net, github). If one exists, read the sound engine code before doing anything else.

3. **Create manifest** at `extraction/manifests/jackal.json` with verified ROM facts and hypotheses from this document. Mark everything unverified as `"status": "hypothesis"`.

4. **Locate the period table** by scanning for the known Maezawa byte sequence ($06, $AE, $06, $4E...). If found, this confirms Maezawa family membership and reveals the sound bank.

5. **Determine DX byte count** by finding DX commands near the period table or music data and counting trailing bytes. This resolves whether to use the CV1 or Contra parser path.

6. **Capture a Mesen APU trace** of the first stage music. Run `trace_compare.py --dump-frames 0-60` equivalent to see actual APU register writes and volume envelope shapes.

7. **Parse ONE track and listen.** Compare to game audio before batch extraction.

## Files

| File | Purpose |
|------|---------|
| This document | Hypotheses and analysis plan |
| `extraction/manifests/jackal.json` | To be created -- per-game manifest |
| ROM file (locate in AllNESRoms) | Jackal (U) ROM |
