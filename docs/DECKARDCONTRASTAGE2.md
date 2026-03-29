# Deckard Boundary Analysis: NES Driver Reverse Engineering

## Context

After extracting CV1 (complete) and Contra (v4, in progress), we now face
the general problem: how do we approach a new NES game whose sound driver
we haven't seen before? This analysis maps which tasks in the reverse
engineering pipeline are deterministic (solvable by code) vs probabilistic
(requiring LLM judgment or human ears), and identifies where we've been
using the wrong approach.

---

## DETERMINISTIC TASKS

These should be code, not LLM reasoning. If we're spending prompts on
these, we need a script.

### D1: iNES Header Parsing
- **What**: Read mapper, PRG bank count, CHR bank count from ROM bytes 0-15
- **Why deterministic**: Fixed binary format, fully documented
- **Status**: Partially implemented (we read it ad hoc each time)
- **SHOULD BE**: A `rom_info(path)` function that returns mapper, banks, size

### D2: Period Table Location
- **What**: Find the 12-entry note period table in a ROM
- **Why deterministic**: Search for the exact byte sequence (1710, 1614, 1524...)
  as 16-bit LE values. Only one hit per ROM.
- **Status**: We do this manually each time with ad hoc Python
- **SHOULD BE**: A `find_period_table(rom)` function

### D3: Driver Signature Detection
- **What**: Determine if a ROM uses the Maezawa driver
- **Why deterministic**: Scan for the E8+DX byte pattern cluster AND
  the FE+count+addr repeat structure. Count occurrences. Threshold-based.
- **Status**: We did this once for CV2 (found it wasn't Maezawa) but manually
- **SHOULD BE**: A `detect_maezawa_driver(rom)` function returning bool + confidence

### D4: CPU-to-ROM Address Mapping
- **What**: Convert NES CPU address to ROM file offset for a given mapper
- **Why deterministic**: Each mapper has a fixed formula. Mapper 0 = linear,
  mapper 2 = bank-switched with fixed last bank, etc.
- **Status**: Hardcoded per game (cv1 uses one formula, contra another)
- **SHOULD BE**: A `make_address_resolver(mapper, prg_banks, sound_bank)` factory

### D5: Disassembly Parsing
- **What**: Extract music data addresses from annotated disassembly files
- **Why deterministic**: Pattern match for `.addr sound_XX` or `CPU address $XXXX`
  annotations. Fixed format per disassembly project.
- **Status**: We read the disassembly manually and transcribe addresses by hand
- **SHOULD BE**: A script that parses `.asm` files for labeled sound data pointers

### D6: Frame-Level Trace Comparison
- **What**: Compare parser output against APU trace, frame by frame
- **Why deterministic**: Pure numerical comparison, no judgment needed
- **Status**: Implemented (`trace_compare.py`). Working well.

### D7: MIDI Export from Frame IR
- **What**: Convert per-frame volume/pitch states to MIDI events
- **Why deterministic**: Algorithmic conversion with defined rules
- **Status**: Implemented. Working well.

### D8: WAV Rendering
- **What**: Synthesize NES APU waveforms from frame IR
- **Why deterministic**: Mathematical waveform generation
- **Status**: Implemented (`render_wav.py`). Adequate fidelity.

### D9: Pointer Table Validation
- **What**: Given a candidate pointer table offset, check if the pointed-to
  data starts with valid Maezawa commands
- **Why deterministic**: Binary pattern matching against known command bytes
- **Status**: We did this manually once for CV2
- **SHOULD BE**: A `validate_pointer_table(rom, offset, format, bank)` function

---

## PROBABILISTIC TASKS (LLM or human judgment needed)

These genuinely require reasoning, pattern recognition across contexts,
or perceptual evaluation.

### P1: Identifying Unknown Command Semantics
- **What**: When a new game has command bytes that behave differently
  from CV1/Contra, determine what they do
- **Why probabilistic**: Requires reading disassembly code, understanding
  6502 control flow, and inferring musical intent from register writes.
  No fixed algorithm — each driver variant is different.
- **Best approach**: LLM reads disassembly + trace data, forms hypothesis,
  tests against trace. The "Debugging Protocol" in CLAUDE_EXTRACTION.md
  structures this process.

### P2: Determining DX Byte Count for Unknown Games
- **What**: How many bytes does the instrument command consume after the
  DX byte? CV1=2, Contra=3/1. Unknown games=?
- **Why probabilistic**: Without a disassembly, you must infer from the
  data stream. Look at bytes after DX: do they look like valid commands
  if you skip 2? Skip 3? Skip 4? Requires judgment about what "looks
  valid" means.
- **Best approach**: If disassembly exists → deterministic (read the code).
  If no disassembly → LLM tries multiple byte counts and evaluates which
  produces coherent note sequences. Could be partially automated:
  try all plausible byte counts and score the resulting parse quality.

### P3: Matching Volume Envelope Behavior
- **What**: Determine how the volume changes per-frame for a given instrument
- **Why probabilistic**: Multiple possible models (parametric fade, lookup
  table, hardware envelope). Must compare trace data against hypotheses.
- **Best approach**: Extract 20 frames of trace volume data. LLM proposes
  model. Validate model against trace for additional notes. The trace
  is deterministic ground truth; the model selection is judgment.

### P4: Musical Correctness Evaluation
- **What**: Does the extracted output sound right?
- **Why probabilistic**: No automated test can determine if music sounds
  correct. Requires human comparison against the game.
- **Best approach**: Human listens. Always. No substitute.
- **KEY LESSON**: The octave mapping was wrong by exactly 12 semitones
  with zero automated test failures. Only human ears caught it.

### P5: Identifying Which Sound Codes Are Music vs SFX
- **What**: In a flat sound table (like Contra's), which entries are
  level music and which are sound effects?
- **Why probabilistic**: No structural marker distinguishes them. Must
  infer from: channel count (music=4, SFX=1-2), slot assignment (music
  uses slots 0-3, SFX uses 4-5), or data length (music is much longer).
- **Best approach**: If disassembly exists → deterministic (read labels).
  If not → parse each entry, measure duration, count channels. Music
  entries are typically >100 notes across 4 channels.

### P6: Cross-Game Driver Variant Classification
- **What**: Is this game's driver "close enough" to CV1/Contra to use
  an existing parser, or does it need a new one?
- **Why probabilistic**: Drivers evolve gradually. Some games may share
  90% of the command set with one known variant. Judgment call on whether
  to adapt vs rewrite.
- **Best approach**: Parse one track with existing parser. If it produces
  recognizable music with minor glitches → adapt. If it crashes or
  produces garbage → different driver, needs investigation.

---

## VALIDATION LAYERS

Where probabilistic output enters deterministic systems:

| Boundary | Risk | Validation |
|----------|------|------------|
| LLM identifies pointer table → parser uses it | Wrong offset → garbage | Run `validate_pointer_table()` on the candidate before committing |
| LLM selects DX byte count → parser consumes bytes | Wrong count → byte misalignment | Parse one track, check total channel frame counts match |
| LLM proposes envelope model → frame IR applies it | Wrong model → bad volume | Compare 20 frames against trace before applying globally |
| LLM determines command semantics → parser implements | Wrong semantics → wrong notes | Parse one track, listen against game |
| Human says "sounds right" → batch extract all tracks | Systematic error undetected | Compare at least 2 tracks, from different sections of the game |

---

## BOUNDARY VIOLATIONS (mistakes we made)

### WASTE: LLM Doing Deterministic Work

| Violation | What Happened | Fix |
|-----------|---------------|-----|
| Manual ROM header reading | Read mapper/banks with ad hoc Python each time | Write `rom_info()` utility |
| Manual period table scanning | Wrote custom scan code in prompts | Write `find_period_table()` |
| Manual disassembly reading | Transcribed 11 Contra addresses by hand from .asm | Write asm label parser |
| Manual address conversion | Wrote `contra_cpu_to_rom()` from scratch | Parameterize existing `cpu_to_rom()` with mapper config |
| Manual trace data extraction | Wrote per-session scripts to dump specific frames | Add `--dump-frames N-M` to trace_compare.py |

### RISK: Deterministic Code Doing Judgment Work

| Violation | What Happened | Fix |
|-----------|---------------|-----|
| Hardcoded pointer table offset | $0825 baked into parser.py, crashed on all other games | Move to per-game config |
| Assumed E8 gates fading | Implemented as boolean without checking other channels | Evidence checklist before implementing ANY behavior |
| Fixed DX byte count | CV1's 2-byte count hardcoded, wrong for Contra's 3 | Per-game config or disassembly-driven |

---

## RECOMMENDED TOOLING TO BUILD

Priority order based on prompt-hours saved:

### Tier 1: Build These Now (saves 3+ prompts per new game)

1. **`scripts/rom_identify.py`** — deterministic
   - Input: ROM path
   - Output: mapper, PRG banks, period table offset, driver signature
     (maezawa/capcom/unknown), candidate pointer table offsets
   - Replaces: manual header reading + period table scanning + driver
     detection that we currently do from scratch each time

2. **Parameterized `cpu_to_rom()`** — deterministic
   - Input: CPU address, mapper type, bank number
   - Replaces: per-game monkey-patching

3. **`--dump-frames` flag on trace_compare.py** — deterministic
   - Input: frame range, channel
   - Output: per-frame vol/period/duty values
   - Replaces: ad hoc Python scripts to extract trace data

### Tier 2: Build When Tackling Third Game (saves 2+ prompts)

4. **Per-game config files** (JSON) — deterministic
   ```json
   {
     "game": "Contra",
     "mapper": 2,
     "sound_bank": 1,
     "pointer_table": {"format": "flat_sound_table", "rom_offset": "0x48F8"},
     "dx_extra_bytes": {"pulse": 3, "triangle": 1},
     "percussion": "separate_channel",
     "tracks": [{"key": "jungle", "name": "...", "sq1": "0x9428", ...}]
   }
   ```

5. **Disassembly label parser** — deterministic
   - Input: .asm file path, label pattern (e.g., `sound_XX`)
   - Output: dict of {label: cpu_address}
   - Replaces: manual transcription

### Tier 3: Build When Scaling (nice to have)

6. **Auto-DX-byte-count detector** — semi-deterministic
   - Try parsing a track with N=1,2,3,4 extra bytes after DX
   - Score each parse: channel frame alignment, note range sanity,
     command distribution
   - Report the most likely byte count
   - Requires: one-track parse + scoring heuristic

7. **Driver fingerprint database** — deterministic
   - Catalog of known driver signatures (byte patterns, code sequences)
   - Match unknown ROMs against known drivers
   - Bootstrap from: CV1, Contra, and eventually Capcom

---

## EXECUTION NOTES

- **Tier 1 items are all deterministic** — no LLM judgment needed.
  Pure utility functions. Should be written and tested in one session.
- **The biggest prompt-saver is `rom_identify.py`** — it replaces the
  first 3-4 prompts of every new game investigation.
- **Per-game config files (Tier 2)** make the parser extensible without
  code changes. New game = new JSON file + pointer addresses.
- **Human listening is irreplaceable** — no amount of tooling eliminates
  the need to compare output against the game. Budget 1-2 prompts per
  game for "sounds wrong, what changed" iteration.
- **The debugging protocol in CLAUDE_EXTRACTION.md is the most important
  non-code artifact** — it structures the LLM's reasoning when things
  go wrong, preventing the multi-hypothesis guessing that burned 5+
  prompts on the CV1 envelope model.
