# The Goonies II (Konami, 1987) — Hypotheses

## ROM Facts (Verified)

| Property | Value |
|----------|-------|
| Publisher | Konami |
| Year | 1987 |
| Mapper | **2 (UxROM)** |
| PRG ROM | 128KB (8 x 16KB banks) |
| CHR ROM | 0KB (CHR RAM) |
| Mirroring | Vertical |
| Battery | No |
| Composer | Satoe Terashima (credited as S. Terashima) |

UxROM banking model: one 16KB switchable bank at $8000-$BFFF, one 16KB
fixed bank at $C000-$FFFF. Identical mapper to Contra and Castlevania 1.

## Driver Family Hypothesis

**H1: Goonies II uses the Konami Maezawa pre-VRC sound driver.**

Evidence supporting this hypothesis:
- Konami game from 1987, same year as Castlevania 1 (1986) and one year
  before Contra (1988). Squarely within the Maezawa driver era (~1986-1990).
- Mapper 2 (UxROM), same as CV1 and Contra. No expansion audio hardware.
- Listed in `spec.md` line 14 as a member of the "same driver family" alongside
  CV1, Contra, Super C, TMNT, Gradius II.
- Listed in `DRIVER_TAXONOMY.md` section 1.2 as a known Maezawa game (status: Untested).
- Base APU only (2 pulse + triangle + noise + DMC). No expansion chips.

**Confidence: 0.8.** The listing in spec.md as "same driver family" is based on
community knowledge, not our own ROM analysis. Must verify with `rom_identify.py`
and direct ROM scanning for Maezawa command signatures (E0-E4 octave, DX instrument,
FE repeat, FD subroutine, FF end).

## Key Questions

### Q1: Same command set as CV1?

**Hypothesis H2**: The note encoding (high nibble = pitch, low nibble = duration),
octave commands (E0-E4), rest commands (C0-CF), and control flow (FD/FE/FF) are
shared with CV1 and Contra.

Basis: All confirmed Maezawa-family games share this command layer. It is the
defining trait of the family (DRIVER_TAXONOMY.md section 1.1).

**To verify**: Scan ROM for E8+DX and FE+count+address patterns. If found, Maezawa
identity is confirmed. If not found, STOP — this is not the same driver.

### Q2: Same DX byte count?

**Hypothesis H3**: DX extra byte count is 2 (instrument + fade), matching CV1.

Basis: Goonies II (1987) is closer in era to CV1 (1986) than to Contra (1988).
The 3-byte DX format in Contra may be a later evolution. However, this is speculative.
DX byte count varies within the family (CV1=2, Contra=3/1) and there is no reliable
way to predict it without inspecting the ROM data or disassembly.

**Confidence: 0.5.** Could be 2 (CV1-style) or 3 (Contra-style). Must determine
empirically by finding a DX command in ROM and counting following bytes before the
next note/command.

### Q3: Same period table?

**Hypothesis H4**: The ROM contains the standard Maezawa 12-entry NTSC period table
(starting with $06AE for C, $064E for C#, etc.).

Basis: All Maezawa-family games use the same hardware-derived NES period values.
CV1, Contra, and CV3 all have this table (CV3 with 3 entries differing by +/-1).

**WARNING**: Finding the period table does NOT confirm the driver. CV2 has the
identical period table but uses a completely different engine (Fujio variant).
The period table confirms NES NTSC tuning, not driver identity.

**To verify**: Search ROM for the byte sequence $06 $AE $06 $4E (first two entries
of the Maezawa period table in big-endian format).

### Q4: Pointer table format?

**Hypothesis H5**: The pointer table format is unknown and must be located by one
of two methods:
1. If a disassembly exists in `references/`, read the sound engine init routine.
2. If no disassembly exists, use Mesen debugger to set breakpoints on APU writes
   and trace back to the data pointer load.

The format could be:
- CV1-style: 9 bytes per track (3 channel pointers + 3 separator bytes)
- Contra-style: flat table with 3 bytes per entry
- Something else entirely

**Confidence: 0.3.** No data. Need ROM analysis.

### Q5: Percussion approach?

**Hypothesis H6**: Goonies II uses inline percussion commands (E9/EA like CV1)
rather than a separate DMC channel (like Contra).

Basis: The inline approach is simpler and appears in the earlier CV1. Contra's
DMC-based percussion may be a later refinement. However, this is a weak basis
for prediction.

**Confidence: 0.4.** Could go either way. Need to check the noise/DMC channel
behavior in the ROM or a Mesen trace.

## Envelope Model

**Hypothesis H7**: Goonies II uses a parametric envelope model (fade_start +
fade_step), like CV1, rather than lookup tables (like Contra).

Basis: The parametric model is the simpler approach and appears in the earlier
game (CV1, 1986). The lookup table approach in Contra (1988) may be a later
development to support the more varied dynamics of the Contra soundtrack.

**Confidence: 0.5.** The envelope model is one of the aspects that varies most
within the Maezawa family. Cannot predict reliably. Must determine from either:
- ROM analysis (presence or absence of volume lookup tables)
- Mesen APU trace (observe per-frame volume shapes and check if they match
  parametric decay or indexed table patterns)

## Predicted Difficulty

**EASY-MEDIUM**, assuming Maezawa compatibility is confirmed.

| Factor | Assessment |
|--------|-----------|
| Mapper complexity | EASY — mapper 2, identical to CV1/Contra |
| Command set | EASY (if Maezawa) — existing parser handles note/octave/rest/control |
| DX byte count | UNKNOWN — must determine, but easy once known |
| Pointer table | UNKNOWN — must locate, moderate effort |
| Envelope model | UNKNOWN — but either parametric or lookup is already implemented |
| Disassembly availability | UNKNOWN — check references/ and romhacking.net |
| Track count | MODERATE — estimated 8-12 tracks |

If the driver is confirmed Maezawa and the DX byte count matches CV1, this game
could be extracted with minimal new code: just a new manifest JSON with ROM addresses
and game-specific configuration. The existing CV1 parser + frame IR pipeline
should handle most of the work.

If the DX byte count or envelope model differs, moderate adaptation is needed
(similar scope to the CV1-to-Contra transition).

## Known Tracks

The Goonies II has an estimated 8-12 distinct music tracks:

| Context | Description |
|---------|-------------|
| Overworld map | Top-down exploration theme |
| Underground areas | Side-scrolling underground theme |
| Sideview rooms | First-person room exploration theme |
| Waterfall area | Distinct area theme |
| Ice area | Distinct area theme |
| Boss/danger | Tense encounter music |
| Game over | Short game over jingle |
| Title screen | Title theme |
| Ending | Ending/credits theme |

### Cyndi Lauper Connection

The original Goonies game (1986, Famicom-only) famously included an arrangement
of Cyndi Lauper's "The Goonies 'R' Good Enough" from the movie soundtrack.
Goonies II (1987) has an original soundtrack by Satoe Terashima that does not
directly quote the Lauper track, but the overworld theme carries a similar
upbeat energy. The soundtrack is well-regarded in the NES community for its
catchy melodies and effective use of the APU.

## Comparison to Decoded Games

| Aspect | CV1 (1986) | Goonies II (1987) | Contra (1988) |
|--------|-----------|-------------------|---------------|
| Mapper | 2 (UxROM) | 2 (UxROM) | 2 (UxROM) |
| PRG size | 128KB | 128KB | 128KB |
| Year | 1986 | 1987 | 1988 |
| Composer | K. Terashima / S. Terashima | S. Terashima | K. Hattori / H. Maezawa |
| Driver | Maezawa (confirmed) | Maezawa (hypothesis) | Maezawa (confirmed) |
| DX bytes (pulse) | 2 | TBD | 3 |
| Envelope | Parametric | TBD | Lookup table |
| Percussion | Inline E9/EA | TBD | Separate DMC |

Note: Satoe Terashima composed both Goonies II and is credited on some
Castlevania 1 tracks. Shared composer across CV1 and Goonies II strengthens
the hypothesis that the same sound engine was used — composers typically
worked within the tools available to them.

## Recommended Next Steps

Follow the workflow in CLAUDE.md strictly:

1. **Run `rom_identify.py`** on the Goonies II ROM to confirm mapper, detect
   period table, and scan for Maezawa driver signatures.

2. **Check for disassembly** in `references/` and on romhacking.net / GitHub.
   If one exists, read the sound engine code before anything else.

3. **Create manifest** at `extraction/manifests/goonies2.json` with verified
   ROM facts and open hypotheses (H1-H7 above).

4. **Scan for period table** — search ROM for $06AE $064E byte sequence.
   Record the address.

5. **Scan for DX+E commands** — locate a DX command in the music data and
   count the extra bytes. Record in manifest as verified or hypothesis.

6. **Locate pointer table** — either from disassembly or by tracing APU
   writes in Mesen debugger back to the data load routine.

7. **Parse ONE track and listen** — choose the overworld theme (most
   recognizable). Compare to game audio before proceeding.

8. **Determine envelope model** — capture a Mesen APU trace of the overworld
   theme. Observe per-frame pulse volume patterns. Match against parametric
   decay (CV1) or stepped table shapes (Contra).

Do NOT batch-extract or write parser code until step 7 passes the listening gate.

## Files

| File | Purpose |
|------|---------|
| This document | Hypotheses and analysis |
| `extraction/manifests/goonies2.json` | To be created (step 3) |
| `extraction/drivers/konami/spec.md` | Command format reference |
| `docs/DRIVER_TAXONOMY.md` | Driver family classification |
