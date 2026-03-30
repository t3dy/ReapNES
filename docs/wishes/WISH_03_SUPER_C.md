# WISH #3: Super C -- The Third Konami Data Point

## 1. What This Wish Is

Complete the Super C (1990) extraction to full-pipeline status: all
tracks parsed with correct pointer table, validated against APU trace,
rendered to MIDI/WAV/REAPER, and delivered as a finished soundtrack
package. Super C is the third game in the Konami Maezawa driver family,
after Castlevania 1 (COMPLETE) and Contra (IN_PROGRESS).

---

## 2. Why It Matters

### Third data point for the Maezawa driver family

Two games is a pair. Three games is a pattern. CV1 and Contra revealed
that the Maezawa command set shares note/octave/repeat encoding but
varies in DX byte count, pointer table format, envelope model, and
percussion handling. Super C as a third data point answers critical
questions:

- **Does the Contra variant stabilize?** Super C is a direct Contra
  sequel (1990 vs 1988, same mapper 2/UNROM). If it uses the same
  DX=3/1, lookup-table envelopes, and DMC percussion as Contra, the
  "Contra variant" becomes a confirmed sub-family rather than a
  one-off divergence.

- **What evolves between 1988 and 1990?** Two years of engine
  evolution may surface new commands (like EC pitch adjustment in
  Contra) or parameter changes (different envelope table sizes,
  new percussion samples). These differences feed the driver taxonomy.

- **Does the parser generalize?** If `contra_parser.py` handles
  Super C with only address/config changes, the parser is truly
  multi-game. If it requires structural changes, those changes
  inform what a generic Maezawa parser needs.

- **Unlocks the EASY tier.** Completing Super C proves the workflow
  for "known driver, mapper 2, no disassembly needed" games.
  Goonies II, Life Force, and Jackal are all mapper 2 Konami titles
  in the same tier. Super C is the gate that validates the approach.

### Musical value

Super C has a well-regarded soundtrack (composed by Hidenori Maezawa
and Kazuki Muraoka). The game is less covered by the NES music
community than Contra, making high-quality extractions more novel.

---

## 3. Current State

### What exists

9 of ~15 tracks have been extracted with MIDI, WAV, and REAPER output:

| Track | MIDI | WAV | REAPER | Status |
|-------|------|-----|--------|--------|
| 01 | Yes | Yes | Yes | Extracted (unvalidated) |
| 02 | -- | -- | -- | FAILED -- parser error |
| 03 | Yes | Yes | Yes | Extracted (unvalidated) |
| 04 | -- | -- | -- | FAILED -- parser error |
| 05 | Yes | Yes | Yes | Extracted (unvalidated) |
| 06 | -- | -- | -- | FAILED -- parser error |
| 07 | -- | -- | -- | FAILED -- parser error |
| 08 | Yes | Yes | Yes | Extracted (unvalidated) |
| 09 | -- | -- | -- | FAILED -- parser error |
| 10 | -- | -- | -- | FAILED -- parser error |
| 11 | Yes | Yes | Yes | Extracted (unvalidated) |
| 12 | Yes | Yes | Yes | Extracted (unvalidated) |
| 13 | Yes | Yes | Yes | Extracted (unvalidated) |
| 14 | Yes | Yes | Yes | Extracted (unvalidated) |
| 15 | Yes | Yes | Yes | Extracted (unvalidated) |

A full soundtrack MP4 and YouTube description also exist at
`output/Super_C/`, built from the 9 working tracks.

### What is wrong

Per the GAME_MATRIX, the 9 successful tracks were parsed using the
**CV1 parser** with CV1's pointer table address ($0825). The 6 failures
hit division-by-zero errors from misaligned pointer reads -- the CV1
parser is reading from the wrong pointer table location for Super C.

The 9 "successful" tracks are suspect: they parsed without crashing
but used the wrong pointer table, wrong DX byte count (CV1=2 vs likely
Contra=3/1), and wrong envelope model (CV1 parametric vs likely Contra
lookup-table). These tracks may contain correct notes by coincidence
but almost certainly have wrong envelopes and articulation.

### What does not exist

- No Super C manifest in `extraction/manifests/`
- No APU trace for validation
- No disassembly in `references/`
- No ear-validation against the game
- No driver confirmation (hypothesis only, based on partial parsing)
- The existing output is unversioned (no v1/v2 suffix)

---

## 4. Concrete Steps

Following the NEW_ROM_WORKFLOW phases:

### Phase 1: Identification (no code)

**Step 1.** Run `rom_identify.py` on the Super C ROM.
```bash
PYTHONPATH=. python scripts/rom_identify.py AllNESROMs/Super\ C\ \(U\)\ \[!\].nes
```
Record mapper (expected: 2/UNROM), period table location, driver
signature confidence, PRG bank count.

**Step 2.** Confirm no manifest exists (confirmed: none in
`extraction/manifests/`).

**Step 3.** Search for annotated disassembly: check `references/`,
GitHub, romhacking.net for Super C NES disassembly. Search terms:
"Super C NES disassembly sound engine", "Super Contra NES sound driver."

**Step 4.** Search VGMRips for Super C APU logs.

**Step 5.** Classify driver. Expected outcome: "Contra variant" based
on same publisher, same mapper, same era, 9/15 tracks partially
parsing with compatible command set.

**Step 6.** Decision gate: proceed if rom_identify confirms Maezawa
signatures and mapper 2.

### Phase 2: Manifest Creation

**Step 7.** Create `extraction/manifests/super_c.json` using the
Contra manifest as template. Key fields to determine:

| Field | Likely Value | Status |
|-------|-------------|--------|
| mapper | 2 (UNROM) | hypothesis (confirm with rom_identify) |
| sound_bank | unknown | unknown (likely bank 1 like Contra) |
| resolver_method | bank_switched | hypothesis |
| pointer_table offset | unknown | unknown (NOT $0825) |
| pointer_table format | flat_sound_table (3 bytes/entry) | hypothesis |
| dx_extra_bytes_pulse | 3 | hypothesis (if Contra variant) |
| dx_extra_bytes_triangle | 1 | hypothesis |
| percussion | separate_channel_dmc | hypothesis |
| envelope_model | lookup_table | hypothesis |

**Step 8.** Mark every field as `hypothesis` or `unknown` until
verified by rom_identify, disassembly, or trace data.

**Step 9.** Document address resolver: mapper 2 bank-switched,
`rom_offset = 16 + bank * 16384 + (cpu_addr - 0x8000)`.

**Step 10.** Document command format hypotheses based on Contra.

### Phase 3: First Track Parsing

**Step 11.** Find Super C's actual pointer table. Without a
disassembly, options are:
- Scan ROM for Maezawa pointer table signatures (clusters of
  addresses in $8000-$FFFF range with 3-byte spacing)
- Use Mesen debugger: set write breakpoint on $4000 (APU pulse1),
  identify which bank and address the sound engine reads from
- Compare ROM hex near Contra's pointer table offset ($48F8) --
  Super C may use a similar layout at a different offset

**Step 12.** Configure `contra_parser.py` with Super C's pointer
table address and bank number. Parse one recognizable track
(Stage 1 music).

**Step 13.** Generate MIDI: `output/Super_C_v2/` (v2 since
unversioned v1 output already exists).

**Step 14.** User listens and compares to game audio.

**Step 15.** Gate: does it sound right?

### Phase 4: Trace Validation

**Step 16.** Record APU trace from Mesen while Stage 1 plays.
Store at `extraction/traces/super_c/stage1.csv`.

**Step 17.** Add Super C config to `trace_compare.py` GAME_CONFIGS.
Run trace comparison.

**Step 18-20.** Iterate on first mismatch, one hypothesis at a time.

### Phase 5: Refinement

**Step 21.** Determine envelope model. If Contra-style lookup tables,
extract `pulse_volume_ptr_tbl` from the Super C ROM. If different,
model from trace data.

**Step 22.** Handle percussion (likely DMC like Contra).

**Step 23.** Validate all channels.

**Step 24.** User listens again.

### Phase 6: Batch Extraction

**Step 25.** Gate: reference track must pass.

**Step 26.** Extract all ~15 tracks to `output/Super_C_v2/`.

**Step 27.** Generate REAPER projects and WAVs.

**Step 28.** Final quality check, user spot-listens 3-5 tracks.

---

## 5. Estimated Effort

| Phase | Sessions | Notes |
|-------|----------|-------|
| Phase 1: Identification | 0.5 | rom_identify + disassembly search |
| Phase 2: Manifest | 0.5 | Template from Contra manifest |
| Phase 3: First Track | 1-2 | Finding pointer table is the bottleneck |
| Phase 4: Trace Validation | 1 | If Contra parser works, minimal iteration |
| Phase 5: Refinement | 1-2 | Envelope model: 0 if identical to Contra, 2 if different |
| Phase 6: Batch Extraction | 0.5 | Mechanical once parser is validated |
| **Total** | **4-7 sessions** | |

The range depends primarily on two unknowns:
1. Whether a disassembly exists (saves 1-2 sessions on pointer table)
2. Whether the envelope model matches Contra (saves 1-2 sessions)

Best case (disassembly found, Contra-identical driver): 4 sessions.
Worst case (no disassembly, novel envelope variant): 7 sessions.

---

## 6. Dependencies

### Hard dependencies (blocking)

- **Contra parser stability.** `contra_parser.py` is the starting
  point. Any structural changes to the Contra parser must land before
  Super C work begins, or Super C will be built on a moving foundation.
  Contra is currently IN_PROGRESS with known anomalies (triangle pitch
  drift, vibrato unimplemented).

- **rom_identify.py functional.** Must correctly report mapper type
  and Maezawa signature confidence for Super C. Already built and
  tested on CV1 and Contra.

- **Super C ROM available.** Must be in `AllNESROMs/` collection.

### Soft dependencies (helpful but not blocking)

- **Contra trace validation improvements.** Fixing Contra's 9% pulse
  pitch mismatch and 30% triangle pitch mismatch before starting
  Super C would mean the base parser is more accurate. But Super C
  can proceed in parallel if the mismatches are timing-related rather
  than command-parsing errors.

- **Manifest-driven parser config.** Currently parsers read hardcoded
  addresses. If manifests drove parser configuration, Super C would
  be a config change rather than a code fork. This is a tooling gap
  identified in NEW_ROM_WORKFLOW but not blocking.

- **Annotated disassembly.** No known Super C sound engine
  disassembly exists. Finding one would eliminate the pointer table
  search bottleneck.

---

## 7. Risks

### R1: Pointer table location unknown (MEDIUM)

The single largest risk. Without a disassembly, finding the pointer
table requires ROM scanning or Mesen debugging. This took ~1 session
for Contra (with a disassembly) and could take 2 sessions without one.

**Mitigation:** Super C is mapper 2 like Contra. The sound engine is
likely in a fixed bank. Scan the ROM for the same pointer table
signature patterns used by Contra (clusters of 3-byte entries with
addresses in the $8000-$BFFF range).

### R2: DX byte count differs from both CV1 and Contra (LOW)

Super C might use a third DX variant. If so, the parser needs new
byte-reading logic.

**Mitigation:** This is LOW risk because Super C is a direct sequel
to Contra by the same development team. The DX format is almost
certainly the Contra variant (3/1). Verify with first-track parsing.

### R3: Envelope model is a third variant (LOW-MEDIUM)

Super C might use lookup-table envelopes with a different table size,
format, or location than Contra.

**Mitigation:** Extract 20 frames of trace volume data before modeling.
If tables exist, they will be near the period table in ROM (same bank
layout pattern as Contra).

### R4: Existing 9 tracks are misleadingly correct (MEDIUM)

The 9 tracks that parsed with the CV1 parser may have correct-sounding
pitches but wrong envelopes, wrong articulation, and wrong dynamics.
Users who listened to the existing MP4 may have calibrated expectations
to incorrect output.

**Mitigation:** Version all new output as v2. Keep v1 (existing) for
comparison. Ear-validate against the actual game, not against v1.

### R5: Super C is NOT the Contra variant (VERY LOW)

Despite being a direct sequel, Super C could use a different driver.
This would make it a MEDIUM-difficulty target instead of EASY.

**Mitigation:** rom_identify.py will detect this immediately. If
Maezawa signatures are absent, STOP and reassess before writing code.

---

## 8. Success Criteria

### Minimum viable (Phase 3 gate)

- [ ] Super C manifest exists with all fields populated
- [ ] rom_identify confirms Maezawa driver family
- [ ] Pointer table address found and documented in manifest
- [ ] One reference track (Stage 1) parses and sounds correct by ear
- [ ] Output versioned as v2

### Full extraction (Phase 6 gate)

- [ ] All ~15 tracks extracted to MIDI, WAV, and REAPER
- [ ] APU trace recorded for reference track
- [ ] Pulse pitch match >= 90% against trace
- [ ] All channels validated (pulse1, pulse2, triangle, noise)
- [ ] User ear-confirmed 3+ tracks against game audio
- [ ] Manifest updated with all verified findings
- [ ] GAME_MATRIX updated: status = COMPLETE

### Stretch goals

- [ ] Identify which DX/envelope parameters differ from Contra
- [ ] Document Super C's differences in spec.md per-game table
- [ ] Full soundtrack MP4 with YouTube description (v2, replacing v1)
- [ ] DriverCapability entry for Super C (if parameters differ)

---

## 9. Priority Ranking

**Priority: HIGH (second after Contra refinement)**

Justification:

| Factor | Score | Reasoning |
|--------|-------|-----------|
| Effort-to-value ratio | HIGH | 4-7 sessions for a complete game, vs 7+ for any MEDIUM or HARD target |
| Scientific value | HIGH | Third data point confirms or refutes "Contra variant" hypothesis |
| Tooling validation | HIGH | Proves the workflow for EASY-tier mapper 2 games |
| Musical novelty | MEDIUM | Good soundtrack, less community coverage than Contra |
| Prerequisite impact | HIGH | Success unlocks Goonies II, Life Force, Jackal |
| Risk level | LOW | Same mapper, same era, same publisher, partially works already |

**Recommended sequencing:**

1. Finish Contra refinement (triangle pitch, vibrato) -- stabilizes
   the base parser
2. Super C extraction (this wish) -- validates the multi-game workflow
3. Gradius or Goonies II -- expands to mapper 0 or confirms another
   mapper 2 title

Super C should not begin until Contra's parser is structurally stable
(no more command-format changes expected). Volume refinement and
vibrato can continue in parallel with Super C work.
