# New ROM Workflow — Step-by-Step Onboarding Playbook

This document is the canonical guide for tackling any new NES ROM in the
NES Music Studio pipeline. Every step exists because skipping it has
burned significant debugging time on past games (CV1, Contra, CV2).

---

## PHASE 1: IDENTIFICATION (before writing any code)

### Step 1 — Run rom_identify.py

**What to do:** Run the deterministic ROM analysis tool. It reports
mapper type, PRG/CHR layout, period table location(s), Maezawa driver
signature confidence, and whether a manifest already exists.

**Command:**
```bash
PYTHONPATH=. python scripts/rom_identify.py <rom_path>
```

For batch scanning a directory:
```bash
PYTHONPATH=. python scripts/rom_identify.py --scan-dir <directory>
```

**What you learn:**
- Mapper number and banking type (0=linear, 1=MMC1, 2=UNROM, 4=MMC3, 5=MMC5, 7=AxROM)
- Whether the standard NES period table is present (and where)
- Maezawa driver confidence score (LIKELY / POSSIBLE / NOT)
- Whether a manifest already exists for this ROM

**Decision gate:** If the driver verdict is NOT MAEZAWA and there is no
period table match, this ROM uses an unknown sound engine. Stop here and
assess whether reverse engineering is feasible before proceeding.

**Common mistake:** Assuming a period table match means the driver is
Maezawa. The period table is universal NES tuning. CV2 has the identical
period table but a completely different sound engine. Cost: 4 prompts on
the CV2 dead end.

---

### Step 2 — Check for Existing Manifest

**What to do:** Look in `extraction/manifests/` for a JSON file matching
this game. If one exists, read it thoroughly before doing anything else.
The manifest contains verified facts, hypotheses, known anomalies, and
validation status.

**Command:**
```bash
ls extraction/manifests/
```

**What you learn:** Everything the project already knows about this game:
ROM layout, pointer table format, command format differences, envelope
model, validated tracks, and known issues.

**Stopping condition:** If a manifest exists with `status: COMPLETE`,
the game is already done. If `status: IN_PROGRESS`, read the anomalies
and pick up where the last session left off.

---

### Step 3 — Search for Annotated Disassembly

**What to do:** Check `references/` for an existing annotated
disassembly of the game. If one exists, read the sound engine code.
This is not optional. 10 minutes reading a disassembly saves hours
guessing at command formats.

**Command:**
```bash
ls references/
```

**What you learn:** The exact command format, byte counts, pointer table
layout, envelope system, and percussion handling for this specific game.

**Common mistake:** Skipping the disassembly and guessing at the DX byte
count based on another game. The Contra parser assumed DX reads 2 bytes
(CV1 format) instead of 3. Cost: 3 prompts.

**If no disassembly exists:** Check nesdev wiki, romhacking.net, and
GitHub for community disassemblies. Search for
`"<game name>" NES disassembly sound engine` or
`"<game name>" NES music format`.

---

### Step 4 — Search Community Resources

**What to do:** Search for known driver documentation from the NES
reverse engineering community:
- nesdev.org wiki sound engine pages
- romhacking.net document database
- GitHub for annotated disassemblies
- VGMRips for logged APU data

**What you learn:** Whether someone has already documented the sound
engine, which saves the entire reverse engineering effort. The Sliver X
document on romhacking.net was the foundation for the CV1 parser.

---

### Step 5 — Classify the Driver Family

**What to do:** Based on Steps 1-4, classify the driver into one of
three categories:

| Category | Definition | Action |
|----------|-----------|--------|
| **Known** | Matches an existing driver module (e.g., konami_maezawa) | Configure existing parser with new game's addresses |
| **Variant** | Same family, different parameters (e.g., Contra vs CV1) | Fork existing parser, adjust DX bytes/envelope/percussion |
| **Unknown** | No match to any existing driver | Full reverse engineering required |

**Key discriminators for the Maezawa family:**
- rom_identify.py confidence >= 0.6
- E8+DX clusters present (envelope enable + instrument set)
- FE repeat and FD subroutine patterns present
- Note encoding: high nibble = pitch (0-B), low nibble = duration

**Common mistake:** Classifying by period table alone. Same period table
does NOT mean same driver.

---

### Step 6 — Decision Gate: Enough Info to Proceed?

**Go criteria (all must be true):**
- [ ] Mapper type is known
- [ ] Driver family is classified (known, variant, or unknown)
- [ ] If known/variant: DX byte count is determined (from disassembly or data inspection)
- [ ] If known/variant: pointer table location is found
- [ ] If unknown: a disassembly or substantial community docs exist

**No-go criteria (any one blocks):**
- Driver is unknown AND no disassembly or docs exist
- Mapper type is unsupported (e.g., MMC5 expansion audio without tooling)
- ROM appears to be a hack, translation, or corrupted dump

**If no-go:** Document what is known in a partial manifest and stop.
Record the game as "BLOCKED — needs RE work" (as was done for CV2).

---

## PHASE 2: MANIFEST CREATION

### Step 7 — Create Manifest JSON

**What to do:** Create a new file in `extraction/manifests/<game>.json`
following the structure of `castlevania1.json` or `contra.json`.

**Required fields:**
```json
{
  "game": "<Game Name>",
  "rom_aliases": ["<filename patterns for rom_identify matching>"],
  "status": "NEW",
  "driver_family": "<family name>",
  "driver_family_status": "verified|hypothesis",
  "rom_layout": { ... },
  "pointer_table": { ... },
  "command_format": { ... },
  "envelope_model": { ... },
  "octave_mapping": { ... },
  "validated_tracks": [],
  "trace_validated_tracks": [],
  "ear_validated_tracks": [],
  "known_anomalies": [],
  "outputs": {}
}
```

**Architecture rule:** Manifests Before Code (architecture.md rule 2).
Every new game MUST have a manifest BEFORE any parser code is written.
Without a manifest, assumptions get baked into code.

---

### Step 8 — Mark Everything as "verified" or "hypothesis"

**What to do:** For every fact in the manifest, add a `_status` field
with one of:
- `"verified"` — confirmed by disassembly, trace, or multiple sources
- `"hypothesis"` — inferred from one source or by analogy to another game
- `"unknown"` — not yet determined

**Why this matters:** Hypotheses that get treated as facts are the
single largest source of wasted debugging time in this project. The
CV1-to-Contra transition assumed DX byte count was the same (hypothesis
treated as fact). Explicitly marking status forces you to check before
relying on it.

---

### Step 9 — Document the Address Resolver Method

**What to do:** Record how CPU addresses map to ROM offsets for this
game.

| Mapper | Resolver | Formula |
|--------|----------|---------|
| 0 (NROM) | linear | `rom_offset = cpu_addr - 0x8000 + 0x10` |
| 2 (UNROM) | bank_switched | `rom_offset = bank * 0x4000 + (cpu_addr - 0x8000) + 0x10` |
| 4 (MMC3) | bank_switched | 8KB switchable banks, more complex |
| 5 (MMC5) | bank_switched | Complex, expansion audio |

**Architecture rule:** Never hardcode addresses. Use the manifest's
`resolver_method`. Mapper 0 = linear, mapper 2 = bank-switched.

---

### Step 10 — Document Command Format Hypotheses

**What to do:** Fill in the `command_format` section of the manifest
with what is known or hypothesized:

- `dx_extra_bytes_pulse`: How many bytes follow a DX command on pulse channels?
- `dx_extra_bytes_triangle`: How many bytes follow DX on triangle?
- `c0_semantics`: Does $C0-$CF mean "rest with duration" or something else?
- `percussion`: Inline (E9/EA like CV1) or separate channel (DMC like Contra)?

**Common mistake:** Copying command handling from another game without
checking. Same opcode does NOT mean same semantics. DX reads 2 bytes in
CV1, 3/1 in Contra. E8 means different things. EC is unused in CV1 but
shifts pitch in Contra.

---

## PHASE 3: FIRST TRACK PARSING

### Step 11 — Extract Raw Command Stream for ONE Track

**What to do:** Pick the most recognizable track from the game (usually
Stage 1 music). Extract and dump the raw command bytes from the ROM at
the pointer table address.

**If using an existing driver:**
```python
parser = KonamiCV1Parser("<rom_path>")
# or ContraParser("<rom_path>")
song = parser.parse_track(<track_id>)
```

**If building a new parser:** Start with just the byte stream reader.
Do not implement envelope, percussion, or advanced commands yet.

**Stopping condition:** You should be able to see note commands
(high nibble 0-B), rest commands ($C0-$CF), octave changes ($E0-$E4),
and tempo/instrument ($DX). If the byte stream looks like garbage,
the pointer table address is wrong.

---

### Step 12 — Build Minimal Parser (or Configure Existing Driver)

**What to do:** Get a parser that emits `ParsedSong` objects with
correct note pitches and durations. Nothing else yet.

**Architecture rule:** Parsers emit full-duration events. No staccato,
no envelope shaping, no volume-based truncation in the parser. All
temporal shaping is the frame IR's responsibility.
`duration_frames = tempo * (nibble + 1)`.

**If configuring an existing driver:** You may need a new parser subclass
or a game-specific configuration block. The key differences to handle:
- DX byte count (how many extra bytes to read)
- Pointer table format and address resolution
- Any game-specific commands (EC pitch shift, EB vibrato, etc.)

---

### Step 13 — Generate MIDI for Single Track

**What to do:** Run the track through the frame IR and MIDI export.

```python
from extraction.drivers.konami.frame_ir import parser_to_frame_ir, DriverCapability
from extraction.drivers.konami.midi_export import export_midi

ir = parser_to_frame_ir(song, driver=driver_capability)
export_midi(ir, "output/<game>_v1_<track>.mid")
```

Or use the full pipeline:
```bash
PYTHONPATH=. python scripts/full_pipeline.py <rom> --game-name <name> --track <id>
```

**Architecture rule:** Use `DriverCapability` to dispatch envelope
strategy. Never use isinstance checks on game name or parser class.

**Version the output.** Always use v1, v2, etc. Never overwrite a
tested file. Cost of ignoring this: 2 prompts (overwrote Contra MIDI
files, user could not compare versions).

---

### Step 14 — User Listens and Compares to Game

**What to do:** The user plays the MIDI in a DAW or MIDI player and
compares it to the actual game audio (from an emulator or YouTube).

**This step cannot be automated.** Zero trace mismatches does NOT mean
the output is correct. The octave can be wrong by exactly 12 semitones
and trace comparison will show zero mismatches. Cost: 3 prompts.

**What to listen for:**
- Are the notes the right pitch? (Wrong octave is the most common error)
- Is the rhythm correct? (Wrong tempo or duration formula)
- Are all channels present? (Missing triangle or noise)
- Do notes start and stop at the right time?

---

### Step 15 — Decision Gate: Does It Sound Right?

**Go criteria:**
- [ ] Notes are in the correct octave (user confirmed)
- [ ] Rhythm matches the game
- [ ] All expected channels are present
- [ ] No stuck notes or missing sections

**If it does not sound right, classify the mismatch:**

| Symptom | Likely Cause | Next Action |
|---------|-------------|-------------|
| All notes wrong pitch, same interval | Octave mapping error | Check BASE_MIDI_OCTAVE4, triangle offset |
| Some notes wrong, others right | DX byte count wrong (parser eating note bytes as DX args) | Check disassembly for DX format |
| Rhythm is double/half speed | Tempo formula wrong | Check `tempo * (nibble + 1)` calculation |
| Notes cut off early | Staccato in parser (architecture violation) | Move shaping to frame IR |
| Missing sections | Pointer table wrong or FE/FD not handled | Check loop/subroutine commands |
| Channel sounds like wrong instrument | Channel assignment wrong in pointer table | Verify which pointer is which channel |

---

## PHASE 4: TRACE VALIDATION

### Step 16 — Generate APU Trace from Emulator

**What to do:** Record an APU trace from Mesen (or another emulator with
APU logging) while the target track plays in the game.

**Trace format:** CSV with per-frame APU register values for each
channel (period, volume, duty cycle, enable flags).

**Store the trace at:**
`extraction/traces/<game>/<track>.csv`

**Important:** Record the exact frame number where the music starts
playing (the trace start offset). This offset is critical for alignment.

---

### Step 17 — Run trace_compare.py

**What to do:** Compare the parser's frame IR output against the
emulator trace.

**Command:**
```bash
PYTHONPATH=. python scripts/trace_compare.py --game <game> --frames <N>
```

To add a new game to trace_compare.py, add an entry to the
`GAME_CONFIGS` dictionary with:
- `rom_path`: path to the ROM
- `trace_path`: path to the trace CSV
- `trace_start_frame`: frame offset where music starts
- `track`: track ID
- `parser_class`: which parser to use
- `driver`: driver capability key (or None for default)
- `report_path` and `diff_path`: where to write output

**Output:** A markdown report at `docs/TraceComparison_<game>.md` and
a JSON diff at `data/trace_diff_<game>.json` showing per-channel pitch,
volume, duty, and sounding mismatches.

---

### Step 18 — Identify First Mismatch

**What to do:** Look at the trace comparison report. Find the FIRST
pitch mismatch on each channel. Dump the raw trace values around that
frame.

**Command:**
```bash
PYTHONPATH=. python scripts/trace_compare.py --game <game> --dump-frames <start>-<end> --channel pulse1
```

**Why first mismatch matters:** Mismatches cascade. A wrong DX byte
count at frame 50 will cause every subsequent note to be wrong. Fix
the first error and re-run before looking at later frames.

**Common mistake:** Trying to fix multiple mismatches at once. Form ONE
hypothesis and test it. Cost of shotgun debugging: 5 prompts (guessed
3 envelope hypotheses before looking at actual frame data).

---

### Step 19 — Form ONE Hypothesis, Test It

**What to do:** Based on the first mismatch, form a single hypothesis
about what is wrong. Implement the fix. Re-run trace_compare.py.

**Debugging protocol (mandatory order):**
1. Identify the symptom precisely (which channel, which aspect, which frame)
2. Extract trace data for the exact frames (do not reason abstractly)
3. Compare at frame level (look at FIRST mismatch)
4. Form ONE hypothesis and test it (do not try 3 at once)
5. If trace shows zero mismatches but sounds wrong: octave mapping error,
   user must compare to game

**Common mistake:** Dumping trace data before modeling costs 0 prompts.
Guessing at envelope shapes without data costs 5. Always dump 20 real
frames first, then fit the model.

---

### Step 20 — Iterate Until Zero Mismatches

**What to do:** Repeat Steps 18-19 until pitch mismatches reach zero
(or an acceptable threshold for the current stage).

**Acceptable thresholds:**
- CV1 achieved 0 pitch mismatches on pulse across 1792 frames
- Contra is at 91% pitch match (9% mismatches, likely timing drift)
- For a new game, aim for 95%+ on pulse channels as the Phase 4 gate

**Architecture rule:** After any change to parser or frame_ir code, run
the full CV1 validation to make sure nothing regressed:
```bash
PYTHONPATH=. python scripts/trace_compare.py --frames 1792
```

---

## PHASE 5: REFINEMENT

### Step 21 — Add Envelope Model

**What to do:** Implement the volume envelope system for this game.

**Two known models in the codebase:**
- **Parametric (CV1):** `fade_start` frames of decay, hold, then
  `fade_step` frames of release. No lookup tables in ROM.
- **Lookup table (Contra):** `pulse_volume_ptr_tbl` in ROM provides
  per-frame volume values indexed by envelope ID.

**Architecture rule:** Use `DriverCapability` to select the volume model.
Never use isinstance checks.

**For a new game:** Dump 20 frames of trace data showing volume changes.
Fit the model to the data. Do not guess the envelope shape.

**Common mistake:** Checking only one channel. The E8 envelope gate
looked correct on Sq1 but was wrong for Sq2. Cost: 2 prompts.

---

### Step 22 — Handle Percussion

**What to do:** Implement the percussion/noise channel handling.

**Two known approaches:**
- **Inline (CV1):** E9 and EA commands in the music data trigger snare
  and hi-hat via a sound routine call.
- **Separate channel (Contra):** Slot 3 is a dedicated percussion
  channel using DMC sample triggers.

**Check the manifest** for which percussion type this game uses before
implementing.

---

### Step 23 — Validate All Channels

**What to do:** Run trace_compare.py and check ALL channels, not just
pulse1. Cross-channel verification catches assumptions that happen to
work on one channel but fail on others.

**Channels to verify:**
- pulse1 (pitch + volume + duty)
- pulse2 (pitch + volume + duty)
- triangle (pitch + sounding — no volume control on triangle)
- noise (if applicable)

**Architecture rule:** Triangle is always 1 octave lower than pulse for
the same timer period (32-step vs 16-step hardware sequencer).
`pitch_to_midi` must subtract 12 for triangle.

**Common mistake:** Changing BASE_MIDI_OCTAVE4 to fix pulse and breaking
triangle in the process. Cost: 2 prompts.

---

### Step 24 — User Listens Again

**What to do:** After adding envelopes and percussion, the user listens
again and compares to the game. This catches:
- Envelope shapes that are technically "correct" by trace but sound
  wrong musically
- Percussion timing issues
- Overall mix and balance problems

---

## PHASE 6: BATCH EXTRACTION

### Step 25 — Gate Check: Reference Track Must Pass

**All of the following must be true before batch extraction:**
- [ ] Reference track has 0 (or near-0) pitch mismatches on trace
- [ ] User has ear-confirmed the reference track sounds correct
- [ ] Envelope model is implemented and matches trace volume data
- [ ] All channels validated (not just one)
- [ ] Manifest is updated with all verified findings

**Do NOT batch-extract before this gate passes.** The reference track
is the proof that the parser, frame IR, and envelope model are correct.
Batch-extracting with a broken parser produces files that all need to
be regenerated.

---

### Step 26 — Extract All Tracks

**What to do:** Parse every track in the game's pointer table and
generate MIDI for each.

```bash
PYTHONPATH=. python scripts/full_pipeline.py <rom> --game-name <GameName>
```

**Version the output:** Use a version suffix (v1, v2, ...) on the
output directory. Never overwrite.

**Check for parser errors:** Some tracks may have commands not seen in
the reference track. Handle gracefully (log and skip unknown commands
rather than crashing).

---

### Step 27 — Generate REAPER Projects, WAVs

**What to do:** For each MIDI, generate a REAPER project with the
NES APU synth plugin and render WAV audio.

```bash
python scripts/generate_project.py --midi <midi_file> --nes-native -o <output.rpp>
```

For WAV rendering:
```bash
python scripts/render_wav.py <midi_file> -o <output.wav>
```

---

### Step 28 — Final Quality Check

**What to do:** User spot-checks 3-5 tracks by listening. Compare to
game audio. Check for:
- Tracks that sound fundamentally wrong (parser error on that track)
- Missing tracks (pointer table might have more entries than expected)
- Tracks that are SFX, not music (some pointer table entries are sound effects)

**Update the manifest:** Set `validated_tracks`, `ear_validated_tracks`,
and `status` fields. If all tracks pass, set `status: "COMPLETE"`.

---

## Quick-Reference Checklist

Copy this checklist for each new game:

```
PHASE 1: IDENTIFICATION
[ ] 1. rom_identify.py run — mapper: ___, driver verdict: ___
[ ] 2. Manifest check — exists: Y/N, status: ___
[ ] 3. Disassembly check — exists: Y/N, location: ___
[ ] 4. Community resource search — found: ___
[ ] 5. Driver classified — known / variant / unknown
[ ] 6. GATE: enough info to proceed? Y/N

PHASE 2: MANIFEST
[ ] 7. Manifest JSON created at extraction/manifests/<game>.json
[ ] 8. All fields marked verified/hypothesis/unknown
[ ] 9. Address resolver documented — method: ___
[ ] 10. Command format documented — DX bytes: ___, percussion: ___

PHASE 3: FIRST TRACK
[ ] 11. Raw command stream extracted for track: ___
[ ] 12. Minimal parser built/configured
[ ] 13. MIDI generated — file: ___ (versioned)
[ ] 14. User listened and compared to game
[ ] 15. GATE: sounds right? Y/N — if N, mismatch type: ___

PHASE 4: TRACE VALIDATION
[ ] 16. APU trace recorded — file: ___
[ ] 17. trace_compare.py run — pitch match: ___%
[ ] 18. First mismatch identified — frame: ___, channel: ___
[ ] 19. Hypothesis tested — fix: ___
[ ] 20. Iterated to target — final pitch match: ___%

PHASE 5: REFINEMENT
[ ] 21. Envelope model implemented — type: ___
[ ] 22. Percussion handled — type: ___
[ ] 23. All channels validated
[ ] 24. User listened again — approved: Y/N

PHASE 6: BATCH EXTRACTION
[ ] 25. GATE: reference track passes all checks? Y/N
[ ] 26. All tracks extracted — count: ___
[ ] 27. REAPER projects and WAVs generated
[ ] 28. Final quality check — user approved: Y/N
```

---

## Implications for Our Pipeline

### Tooling Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| **No automated trace capture** | User must manually record traces in Mesen, find the start frame offset, and export CSV. This is the biggest time cost per new game. | High |
| **trace_compare.py requires manual config** | Adding a new game means editing the GAME_CONFIGS dict in Python. Should be driven by manifest JSON. | Medium |
| **No address resolver abstraction** | Each parser hardcodes its address resolution. Should be a shared utility driven by mapper type from the manifest. | Medium |
| **No unknown-command graceful handling** | Parsers crash on unrecognized commands. Should log and skip with a warning. | Medium |
| **No automated pointer table decoder** | Finding the pointer table still requires reading a disassembly or manual hex inspection. Could be partially automated for known formats. | Low |
| **No per-game config files** | Parser addresses are in code, not config. The manifest has the data but parsers do not read it yet. | Medium |
| **Envelope model selection is manual** | DriverCapability must be constructed in calling code. Should auto-construct from manifest. | Low |
| **No batch trace validation** | Can only validate one track at a time. Should support validating all trace-validated tracks in one run. | Low |

### What Would Make Phase 1 Faster

1. **rom_identify.py scanning the ROM collection** — already supported
   with `--scan-dir`, but results are not cached or stored.
2. **Manifest auto-generation** — rom_identify.py could create a skeleton
   manifest with mapper, period table, and driver signature pre-filled.
3. **Disassembly index** — a registry of which games in `references/`
   have disassemblies, auto-checked during identification.

---

## Failure Risks if Steps Are Skipped

| Skipped Step | What Goes Wrong | Historical Cost |
|-------------|-----------------|-----------------|
| **Step 1 (rom_identify)** | Waste 3-4 prompts manually discovering mapper type and driver family | 3-4 prompts per game |
| **Step 3 (disassembly)** | Guess at DX byte count, get it wrong, parse garbage for hours | 3 prompts (Contra DX=3 not 2) |
| **Step 5 (classify driver)** | Assume same driver because same publisher, waste time on dead end | 4 prompts (CV2 is not Maezawa) |
| **Step 7 (manifest)** | Assumptions baked into code, painful to change later | 3+ prompts (CV1-to-Contra transition) |
| **Step 8 (verified/hypothesis)** | Treat hypothesis as fact, build on wrong foundation | Compounds with every subsequent step |
| **Step 14 (user listens)** | Octave off by 12 semitones, trace shows zero mismatches, ship wrong output | 3 prompts (systematic octave error) |
| **Step 18 (first mismatch)** | Fix later mismatches that are caused by the first one, wasting effort | 5 prompts (envelope guessing) |
| **Step 19 (one hypothesis)** | Try 3 fixes at once, cannot tell which helped and which hurt | 5 prompts (envelope modeling) |
| **Step 23 (all channels)** | Fix works on pulse1, breaks pulse2 or triangle | 2 prompts (E8 gate incident) |
| **Step 25 (gate check)** | Batch-extract with broken parser, regenerate everything | 2+ prompts per regeneration cycle |
| **Versioning outputs** | Overwrite tested files, lose ability to compare versions | 2 prompts (Contra file overwrite) |

---

## Appendix: Manifest Template

```json
{
  "game": "",
  "rom_aliases": [],
  "status": "NEW",
  "driver_family": "",
  "driver_family_status": "",

  "rom_layout": {
    "mapper": null,
    "prg_banks": null,
    "sound_bank": null,
    "resolver_method": "",
    "resolver_status": "unknown"
  },

  "pointer_table": {
    "rom_offset": "",
    "format": "",
    "entry_size": null,
    "num_tracks": null,
    "status": "unknown"
  },

  "command_format": {
    "dx_extra_bytes_pulse": null,
    "dx_extra_bytes_triangle": null,
    "dx_byte_count_status": "unknown",
    "c0_semantics": "",
    "c0_status": "unknown",
    "percussion": "",
    "percussion_status": "unknown"
  },

  "envelope_model": {
    "type": "",
    "status": "unknown"
  },

  "octave_mapping": {
    "base_midi_octave4": 36,
    "triangle_offset": -12,
    "status": "unknown"
  },

  "validated_tracks": [],
  "trace_validated_tracks": [],
  "ear_validated_tracks": [],
  "known_anomalies": [],
  "outputs": {}
}
```
