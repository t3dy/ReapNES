# TMNT (Teenage Mutant Ninja Turtles) — Hypotheses

## ROM Facts

| Property | Value | Source |
|----------|-------|--------|
| Publisher | Konami | Cartridge/title screen |
| Year | 1989 | Between Contra (1988) and Super C (1990) |
| Mapper | **4 (MMC3 / TxROM)** | iNES header; Nintendo MMC3 chip |
| PRG ROM | 128KB (8 x 16KB banks) | Standard for MMC3 TMNT cart |
| CHR ROM | 128KB (16 x 8KB banks) | Standard for MMC3 TMNT cart |
| Mirroring | Vertical (hardwired) or MMC3-controlled | MMC3 supports software mirroring control |
| Battery | No | No SRAM/save feature in game |
| Expansion audio | **None** | MMC3 has no expansion audio channels |
| APU channels | Standard 5 (2 pulse, triangle, noise, DMC) | Base 2A03 only |

## MMC3 Banking Model

MMC3 uses **8KB switchable PRG banks**, which is more granular than
UNROM (16KB) or MMC5 (configurable). The banking layout:

| CPU Address | Size | Behavior |
|-------------|------|----------|
| $8000-$9FFF | 8KB | Switchable (bank register 6) OR fixed to second-to-last bank |
| $A000-$BFFF | 8KB | Switchable (bank register 7) |
| $C000-$DFFF | 8KB | Fixed to second-to-last bank OR switchable (mirrors $8000 mode) |
| $E000-$FFFF | 8KB | **Always fixed to last bank** (contains vectors, likely driver code) |

MMC3 has two PRG banking modes (controlled by bit 6 of $8000):
- **Mode 0**: $8000-$9FFF and $A000-$BFFF are switchable; $C000-$FFFF fixed.
- **Mode 1**: $8000-$9FFF fixed; $A000-$BFFF switchable; $C000-$DFFF switchable; $E000-$FFFF fixed.

**Implication for sound driver**: The driver code almost certainly
resides in the fixed bank ($E000-$FFFF). Music data may be in one or
more switchable banks. The address resolver must handle 8KB bank
granularity, not 16KB like UNROM or 32KB like NROM.

This is **more complex than Contra's UNROM** (which has a single 16KB
switchable bank + 16KB fixed) but **simpler than CV3's MMC5** (which
has multiple banking modes and a larger address space).

## Driver Family Hypothesis

**H1: TMNT likely uses a Maezawa-family driver variant.**

Evidence supporting this hypothesis:
- Konami game from the correct era (1989, within the 1986-1990 Maezawa window)
- Listed in `spec.md` as part of the "same driver family" group alongside
  CV1, Contra, Super C, and Goonies II
- Same development team/publisher lineage as confirmed Maezawa games
- Konami reused their sound engine heavily across NES titles of this period

Evidence against or complicating:
- TMNT is on MMC3 (mapper 4), unlike any confirmed Maezawa game (CV1=mapper 0,
  Contra/Super C=mapper 2, CV3 US=mapper 5). The banking model is different.
- No annotated disassembly is known to exist in `references/`
- Driver family membership is stated in spec.md but marked as unverified
  for TMNT specifically. The period table and command signatures have not
  been confirmed in ROM.

**Confidence: 0.65** — Likely but not confirmed. The same-publisher,
same-era reasoning has been wrong before (CV2 is Konami 1987 but uses
the Fujio driver, not Maezawa). Must verify with rom_identify.py.

## Key Unknowns

### DX Byte Count (CRITICAL)

| Game | DX Extra Bytes (pulse) | DX Extra Bytes (triangle) |
|------|------------------------|---------------------------|
| CV1 | 2 (instrument + fade) | 0 |
| Contra | 3 (config + vol_env + decrescendo) | 1 (tri config) |
| TMNT | **Unknown** | **Unknown** |

**H2**: TMNT's DX byte count is likely 3/1 (Contra model) rather than
2/0 (CV1 model), since TMNT (1989) postdates Contra (1988) and Konami
tended to evolve the driver forward. But this is speculation — it could
also be 2/0 or something new entirely.

**Confidence: 0.4** — Pure chronological inference. Must verify from
ROM data or disassembly.

### Pointer Table Format

**H3**: The pointer table format is unknown. Possibilities:
- CV1 style: 9 bytes per track (3 pointers + 3 separator bytes)
- Contra style: flat sound_table with 3-byte entries
- CV3 style: nested section table with pointer pairs
- Something new driven by MMC3 banking needs

The MMC3's 8KB banks may require the pointer table to include bank
numbers alongside CPU addresses, since music data could span multiple
8KB banks that are not all mapped simultaneously.

**Confidence: 0.3** — No data. Must find from Mesen debugger or
disassembly.

### Envelope Model

**H4**: The volume envelope model is unknown. Possibilities:
- Parametric (CV1): fade_start + fade_step, no ROM tables
- Lookup table (Contra): 54-entry ROM table of per-frame volume values
- Hybrid or new variant

TMNT's sound has noticeably more dynamic range and varied timbres
compared to CV1, suggesting a lookup table model (which allows more
complex envelope shapes) rather than the simple parametric decay of CV1.

**Confidence: 0.35** — Subjective audio impression. Must verify from
trace data.

### Percussion Format

**H5**: Percussion is likely separate-channel DMC (Contra model) rather
than inline E9/EA (CV1 model). Contra introduced DMC sample-based drums,
and later Konami NES titles generally continued with DMC percussion.
TMNT's drum sounds (particularly in boss and action sequences) sound
sample-based.

**Confidence: 0.5** — Reasonable inference, unverified.

## Period Table

**H6**: TMNT likely uses the standard NES NTSC chromatic period table
(or a close variant). The 12-entry base table at the heart of all
Maezawa games is derived from the NTSC CPU clock and equal temperament
tuning. Minor deviations of +/-1 in some entries are expected (as seen
in CV3's table).

The table could be:
- 12 entries with octave shift via E0-E4 commands (CV1 model)
- 36 entries spanning 3 octaves (CV3 model)
- Some other size

**Confidence: 0.6** — Standard tuning is nearly universal across NES
games. The exact table size and location are unknown.

## Predicted Difficulty

**MEDIUM.** Comparable to CV3, harder than Contra.

| Factor | Assessment |
|--------|------------|
| MMC3 8KB banking | Adds address resolution complexity beyond UNROM |
| No known disassembly | All findings must come from ROM scanning + Mesen tracing |
| Maezawa family (if confirmed) | Existing parser logic can be adapted |
| Standard APU only | No expansion audio complicates nothing |
| Multiple tracks to validate | More content, more testing surface |

The primary difficulty driver is the **MMC3 banking**. With 8KB
switchable banks, the address resolver needs to handle a mapping where
the sound bank may not be contiguous. Finding which bank(s) contain
the sound driver and music data is the first obstacle.

Secondary difficulty is the **absence of a disassembly**. For CV1 and
Contra, annotated disassemblies provided pointer table locations, DX
byte counts, and envelope model details. For TMNT, all of this must be
discovered through ROM analysis and Mesen debugging.

## Known Track Names

TMNT has a substantial soundtrack. Expected tracks based on the game's
structure:

| # | Context | Expected Track Name |
|---|---------|-------------------|
| 1 | Title screen | Title Theme |
| 2 | Overworld map | Overworld |
| 3 | Area 1 (streets) | Sewer / Streets |
| 4 | Area 2 (burning building) | Burning Building |
| 5 | Area 3 (dam/underwater) | Dam (the infamous underwater level) |
| 6 | Area 4 (Technodrome approach) | Area 4 Theme |
| 7 | Area 5 (Technodrome interior) | Technodrome |
| 8 | Area 6 (final area) | Final Area |
| 9 | Boss battle | Boss Theme |
| 10 | Sewer/indoor sections | Indoor / Sewer Theme |
| 11 | Game over | Game Over |
| 12 | Stage clear / rescued | Rescue / Stage Clear |
| 13 | Ending | Ending Theme |
| 14 | Password screen | Password |

The exact count and naming will depend on what the ROM's pointer table
reveals. Some area themes may be reused across multiple stages.

The overworld theme is one of the most recognizable tracks from the
game and would serve as a good reference track for initial validation.

## Comparison to Other Maezawa Games

| Feature | CV1 | Contra | TMNT (predicted) |
|---------|-----|--------|------------------|
| Mapper | 0 (NROM) | 2 (UNROM) | 4 (MMC3) |
| PRG size | 32KB | 128KB | 128KB |
| Bank granularity | N/A (linear) | 16KB | 8KB |
| Sound bank count | 1 (whole ROM) | 1 (bank 1) | Unknown (1-2 expected) |
| DX bytes (pulse) | 2 | 3 | Unknown |
| Envelope | Parametric | Lookup table | Unknown |
| Percussion | Inline E9/EA | Separate DMC | Unknown (likely DMC) |
| Track count | 15 | 11 | ~12-16 (estimated) |

## Recommended Next Steps

### Step 1: ROM Identification (MANDATORY FIRST)
```bash
PYTHONPATH=. python scripts/rom_identify.py <tmnt_rom_path>
```
This will confirm mapper 4, report period table location (if found),
and check for Maezawa driver signatures (DX/FE/FD patterns). If the
driver signature check fails, STOP — TMNT may not be Maezawa family.

### Step 2: Locate Sound Driver in ROM
Using Mesen's debugger, set a write breakpoint on $4000 (Pulse 1
volume register). When music plays, the call stack will reveal which
bank contains the sound driver update loop. The driver should be in
the fixed bank ($E000-$FFFF).

### Step 3: Find Period Table
Search all 8KB banks for the known Maezawa base period values (look
for the byte sequence corresponding to C2 period $06AE: bytes `06 AE`
in big-endian or `AE 06` in little-endian). Multiple hits may indicate
the table is duplicated across banks (as in CV3).

### Step 4: Find Pointer Table
Once the sound bank is identified, search for the pointer table
structure. A Mesen trace of the title screen music starting will show
the driver reading pointer values to initialize channel data pointers.

### Step 5: Determine DX Byte Count
Find a DX command in the music data stream and count how many bytes
follow before the next note/rest/control command. Cross-reference with
a Mesen trace showing the driver's command parsing routine.

### Step 6: Capture APU Trace
Capture a Mesen APU trace of the overworld theme (most recognizable
track, good for ear-validation). Use this trace as ground truth for
pitch and volume validation.

### Step 7: Parse One Track, Listen
Attempt to parse the overworld theme with the existing Konami parser
(with TMNT-specific configuration). Compare output to the Mesen trace
and to the game audio by ear. Do NOT batch-extract until this single
track sounds correct.

### Step 8: Search for Disassembly
Check these sources for existing TMNT NES reverse engineering work:
- romhacking.net document section
- nesdev.org forums
- GitHub (search "tmnt nes disassembly")
- Data Crystal wiki

Any partial disassembly would dramatically reduce the guesswork for
pointer table format and DX byte count.

## Open Questions

| Question | Impact if Wrong | How to Resolve |
|----------|----------------|----------------|
| Is TMNT actually Maezawa family? | Entire parser approach wrong | rom_identify.py + signature scan |
| Which 8KB bank(s) hold music data? | Cannot find pointer table or note data | Mesen write breakpoint on $4000 |
| DX byte count? | Parser reads wrong bytes, corrupts note stream | Trace DX command handling in debugger |
| Does MMC3 banking require bank IDs in pointer table? | Address resolution fails | Examine pointer table entries |
| How many tracks total? | Incomplete extraction | Count pointer table entries |

## Files

| File | Purpose |
|------|---------|
| This document | Hypotheses and analysis |
| `extraction/manifests/tmnt.json` | To be created after rom_identify.py confirms facts |
| `references/` | Check for TMNT disassembly (none found yet) |
