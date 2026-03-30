# WISH #12: Non-Konami Drivers (Capcom, Sunsoft)

## 1. What This Wish Is

Extend NES Music Studio beyond the Konami Maezawa driver family to
support two additional publisher-specific sound engines: Capcom
(Mega Man series and related titles) and Sunsoft (Batman, Blaster
Master, Journey to Silius). Each requires a new parser module, new
signature scanner in rom_identify.py, new DriverCapability envelope
models, and (for Sunsoft) a new DPCM output path in the pipeline.

This is the project's first venture outside the Konami family and
will validate whether the ENGINE / DATA / HARDWARE separation and the
manifest-driven architecture actually generalize to non-Konami drivers.

---

## 2. Why It Matters

**Coverage expansion.** The Konami Maezawa family covers roughly 8-12
games. Capcom's MM-era driver covers an estimated 10-15 games from a
single parser. Sunsoft covers 5-8 games. Together they roughly triple
the project's game coverage.

**Architectural proof.** The current pipeline was designed for
multi-driver scaling (DriverCapability dispatch, manifest-first
workflow, per-family parser modules), but every line of production code
targets one driver family. Capcom and Sunsoft are the cheapest way to
prove the architecture works, because both use only the base APU (no
expansion chips) and have high driver reuse across titles.

**Audience value.** Mega Man 2 and Batman are among the most requested
NES soundtracks in the chiptune and game music communities. Extracting
these with per-frame volume automation and REAPER projects has strong
YouTube and educational appeal.

**Sunsoft as a technical milestone.** Sunsoft's DPCM bass technique
pushes the pipeline into sample-based audio, which no current path
handles. Solving DPCM opens the door for any game that uses DMC
samples (including later Konami and Capcom titles).

---

## 3. Current State

### What Exists

- **Driver taxonomy** (docs/DRIVER_TAXONOMY.md): Capcom and Sunsoft
  sections document known characteristics at MODERATE confidence.
  Command style, envelope approach, reuse patterns, and pipeline
  implications are described but not verified against ROM data.

- **Stub driver directories**: `extraction/drivers/capcom/` and
  `extraction/drivers/sunsoft/` exist with `__init__.py` and
  `NOTES.md` files. No parser code.

- **rom_identify.py**: Has a Maezawa signature scanner only. No
  Capcom or Sunsoft scanners.

- **DriverCapability**: Supports `volume_model` values "parametric"
  and "lookup_table". Does not yet support "duty_cycling" (Capcom)
  or "dpcm_bass" (Sunsoft).

- **Community resources**: Mega Man 2 has multiple annotated
  disassemblies on GitHub. The Sunsoft engine has been analyzed by
  the nesdev community. Neither has been pulled into `references/`.

### What Does Not Exist

- No Capcom or Sunsoft parser code.
- No signature scanners for either family.
- No manifests for any Capcom or Sunsoft game.
- No DPCM sample playback path in the frame IR or render pipeline.
- No APU traces for any non-Konami game.
- No disassemblies in `references/` for Capcom or Sunsoft titles.

---

## 4. Concrete Steps

### Phase A: Capcom (Mega Man 2 as reference game)

Capcom is the lower-risk target. It uses base APU only, multi-byte
opcode commands, and table-based envelopes with duty cycling. The
command format is different from Konami but the output path (MIDI
with CC11 volume automation) is identical.

**A1. Gather disassembly and community docs (1-2 hours)**

Search GitHub for Mega Man 2 NES disassembly. The game is heavily
studied; at least one annotated disassembly exists. Download into
`references/mega-man-2/`. Read the sound engine code. Record:
- Pointer table address and format
- Command byte encoding (opcode + params, not pitch-in-nibble)
- Envelope table structure (indexed volume arrays)
- Duty cycle rotation behavior
- Tick/timing model

**A2. Build Capcom signature scanner (2-3 hours)**

Add a `detect_capcom_signature()` function to rom_identify.py. The
scanner should look for:
- Duty cycle rotation patterns (12.5% / 25% / 50% cycling) in
  envelope table data
- Capcom-specific opcode clusters in the sound data bank
- Multi-byte command sequences characteristic of the MM-era engine

This extends the decision tree in DRIVER_IDENTIFICATION.md step [5]
to check Capcom patterns when the Maezawa score is low.

**A3. Create Mega Man 2 manifest (1 hour)**

Create `extraction/manifests/mega_man_2.json` with all fields from
the manifest template. Mark disassembly-sourced fields as "verified",
inference-based fields as "hypothesis".

**A4. Write Capcom parser module (4-6 hours)**

Create `extraction/drivers/capcom/parser.py`. The parser must:
- Decode multi-byte opcode commands (not pitch-in-nibble like Konami)
- Handle Capcom's tick-based timing system
- Emit full-duration ParsedSong events (architecture rule)
- Support the envelope table index in instrument commands
- Handle pitch slide/portamento commands

The parser should be configurable by manifest (pointer table address,
envelope table address, tick rate) so that later Capcom games can
reuse it with different manifests.

**A5. Extend DriverCapability for duty cycling (1-2 hours)**

Add `volume_model: "duty_cycling"` to DriverCapability. The frame IR
must apply per-frame duty cycle changes from the envelope table in
addition to volume changes. This is Capcom's distinctive feature and
affects timbre, not just volume.

**A6. Parse Mega Man 2 Stage 1, listen (2-3 hours)**

Follow the New ROM Workflow phases 3-4. Parse one track. Export MIDI.
User listens and compares to game. Fix issues one at a time. Capture
an APU trace if available and run trace validation.

**A7. Batch extract Mega Man 2 (1-2 hours)**

After the reference track validates, extract all tracks. Generate
MIDI, REAPER projects, and WAVs. Version output as v1.

**A8. Validate on second Capcom game (2-4 hours)**

Test the Capcom parser on DuckTales or Mega Man 3 with only a new
manifest (no parser code changes). This proves the parser generalizes
across the Capcom family. If parser changes are needed, they reveal
intra-family variation that must be handled by configuration, not
code forks.

### Phase B: Sunsoft (Batman as reference game)

Sunsoft is higher-risk due to the DPCM bass technique, which requires
a new output path. The standard channels (pulse, triangle, noise)
follow the same MIDI export pipeline, but the DPCM bass channel
cannot be represented as standard MIDI note-on/note-off.

**B1. Gather disassembly and community docs (1-2 hours)**

Search for Batman NES sound engine documentation. Check nesdev wiki
and romhacking.net. The DPCM bass technique has been analyzed by
community members. Download relevant resources into
`references/batman-nes/`.

**B2. Build Sunsoft signature scanner (2-3 hours)**

Add `detect_sunsoft_signature()` to rom_identify.py. Key signatures:
- Rapid DPCM register ($4010-$4013) writes at pitched intervals
  (the DPCM bass fingerprint)
- DPCM sample data aligned to $C000-$FFFF, 64-byte boundaries
- Compact multi-byte command format

**B3. Create Batman manifest (1 hour)**

Create `extraction/manifests/batman.json`. Include DPCM sample
addresses and the bass note-to-sample mapping table.

**B4. Write Sunsoft parser module (4-6 hours)**

Create `extraction/drivers/sunsoft/parser.py`. Must handle:
- Standard channels (pulse, triangle, noise) with table-based ADSR
  envelopes
- DPCM bass channel: map DPCM trigger commands to note events with
  sample references
- Sunsoft's tick-based timing model

**B5. Design DPCM output path (3-5 hours)**

This is the novel engineering work. Options:
- **Option 1: MIDI + sample reference.** Export DPCM bass as MIDI
  note events with a custom instrument mapping. The REAPER project
  uses a sampler plugin loaded with extracted DPCM samples instead
  of the NES APU synth.
- **Option 2: Direct WAV rendering.** Extract DPCM samples from ROM,
  render the bass channel directly to WAV at the correct pitches,
  mix with the synthesized pulse/triangle/noise channels.
- **Option 3: Extended synth.** Add DPCM sample playback to
  ReapNES_APU.jsfx.

Option 2 is likely the fastest to implement. Option 1 is more
flexible for user editing. Decision should be made after examining
the actual sample data.

**B6. Extend DriverCapability for DPCM bass (1-2 hours)**

Add `volume_model: "table_adsr"` and `expansion_chip: None` with a
new field `dpcm_bass: true` to indicate the DPCM channel carries
pitched bass rather than percussion samples.

**B7. Parse Batman Stage 1, listen (2-4 hours)**

Follow New ROM Workflow. The DPCM bass channel will need special
attention during listening -- verify that bass pitches are correct
and that the sample-based timbre is recognizably Sunsoft.

**B8. Batch extract Batman (1-2 hours)**

Extract all tracks. The DPCM output path must be integrated into
full_pipeline.py for this to work end-to-end.

**B9. Validate on Blaster Master (2-4 hours)**

Test the Sunsoft parser on Blaster Master with a new manifest.
Confirms the parser generalizes within the Sunsoft family.

---

## 5. Estimated Effort

| Phase | Task | Hours (est.) |
|-------|------|-------------|
| A1 | Capcom disassembly research | 1-2 |
| A2 | Capcom signature scanner | 2-3 |
| A3 | Mega Man 2 manifest | 1 |
| A4 | Capcom parser module | 4-6 |
| A5 | DriverCapability duty cycling | 1-2 |
| A6 | First track parse + validate | 2-3 |
| A7 | Batch extract MM2 | 1-2 |
| A8 | Second Capcom game validation | 2-4 |
| **Phase A total** | | **14-23** |
| B1 | Sunsoft disassembly research | 1-2 |
| B2 | Sunsoft signature scanner | 2-3 |
| B3 | Batman manifest | 1 |
| B4 | Sunsoft parser module | 4-6 |
| B5 | DPCM output path | 3-5 |
| B6 | DriverCapability DPCM bass | 1-2 |
| B7 | First track parse + validate | 2-4 |
| B8 | Batch extract Batman | 1-2 |
| B9 | Second Sunsoft game validation | 2-4 |
| **Phase B total** | | **17-29** |
| **Combined total** | | **31-52 hours** |

Phase A (Capcom) can be completed independently. Phase B (Sunsoft)
depends on Phase A only insofar as the architectural extensions
(DriverCapability, rom_identify multi-scanner) established in A
carry forward to B.

---

## 6. Dependencies

### Hard Dependencies (must exist before starting)

| Dependency | Status | Blocking |
|------------|--------|----------|
| Annotated disassembly for Mega Man 2 | Not yet pulled into references/ | Blocks A4 |
| rom_identify.py multi-scanner framework | Exists for Maezawa only | Blocks A2 |
| DriverCapability extensibility | Exists, needs new enum values | Blocks A5 |
| Manifest template and workflow | Exists and documented | Not blocked |

### Soft Dependencies (would help but not required)

| Dependency | Status | Impact if Missing |
|------------|--------|-------------------|
| Contra extraction complete | IN PROGRESS | Lessons from Contra inform Capcom work, but not blocking |
| Per-game config files replacing hardcoded addresses | Not done | Parser addresses stay in code; works but inelegant |
| Automated trace capture | Not done | Manual Mesen sessions needed; adds 30-60 min per game |
| DPCM sample extraction tooling | Does not exist | Must be built as part of Phase B5 |

### External Dependencies

- **Community disassemblies**: Mega Man 2 disassemblies exist on
  GitHub. Batman NES disassembly availability is less certain; may
  need to rely on partial docs and APU traces instead.
- **ROM availability**: Both Mega Man 2 and Batman are in the GoodNES
  collection at `AllNESROMs/`.

---

## 7. Risks

### R1: Capcom Command Format Is More Complex Than Expected

**Likelihood**: Medium.
**Impact**: Phase A4 takes 8-12 hours instead of 4-6.
**Mitigation**: Start with the disassembly, not with byte scanning.
The Capcom command set may include features (pitch slides, multi-speed
ticks, sub-pattern calls) that require more parser state than the
Konami driver. Budget for iteration.

### R2: No Adequate Disassembly for Batman

**Likelihood**: Medium.
**Impact**: Phase B requires APU trace-first reverse engineering
instead of disassembly-first. Adds 4-8 hours.
**Mitigation**: Search broadly (nesdev, romhacking.net, GitHub,
VGMRips). If no disassembly exists, capture APU traces first and
reverse-engineer the command format from register write patterns
(DRIVER_IDENTIFICATION.md method 5). This is slower but proven.

### R3: DPCM Bass Path Requires Significant Pipeline Changes

**Likelihood**: High.
**Impact**: Phase B5 is the most uncertain task. The current pipeline
assumes all channels emit MIDI notes with CC11 volume automation.
DPCM bass breaks this assumption. May require changes to frame_ir.py,
midi_export.py, generate_project.py, and render_wav.py.
**Mitigation**: Prototype the DPCM path on a single track before
committing to a design. Option 2 (direct WAV rendering) sidesteps
the MIDI representation problem at the cost of losing user editability
on the bass channel.

### R4: Driver Family Variation Within Capcom Catalog

**Likelihood**: Medium.
**Impact**: The MM2-era parser may not work on Mega Man 1 (earlier,
simpler engine) or Mega Man 4-6 (later, extended commands) without
modification. Could fragment into 2-3 parser variants.
**Mitigation**: Target the MM2-era variant first (MM2, DuckTales,
Chip'n Dale). Validate on a second game (A8) before claiming family
coverage. Accept that early and late Capcom may need separate parsers,
as documented in DRIVER_TAXONOMY.md section 3.2.

### R5: Assumption Transfer from Konami

**Likelihood**: High.
**Impact**: The team's deep familiarity with Konami's pitch-in-nibble,
DX-based command format creates strong priors that do not apply to
Capcom or Sunsoft. Risk of unconsciously assuming Konami patterns
(e.g., E0-E4 octave commands, FE repeat format) exist in non-Konami
drivers.
**Mitigation**: The FAILURE_MODES.md document catalogs this class of
error (sections 1.1-1.4). The manifest-first workflow forces explicit
documentation of each command's meaning before coding. Treat every
non-Konami command byte as semantically unknown until verified.

### R6: Scope Creep into Expansion Chips

**Likelihood**: Low-Medium.
**Impact**: Temptation to also tackle VRC6 (CV3 Famicom) or Sunsoft
5B (Gimmick!) while working on base-APU drivers. These require
expansion chip emulation in the synth and render pipeline.
**Mitigation**: This wish is strictly base-APU Capcom and Sunsoft.
Expansion chips are a separate wish. Park any expansion ideas per
the Abendsen parking protocol.

---

## 8. Success Criteria

### Minimum Viable (Phase A only)

- [ ] rom_identify.py detects Capcom driver signature with >= 0.6
      confidence on Mega Man 2 ROM
- [ ] Capcom parser extracts Mega Man 2 Stage 1 (Dr. Wily's Castle)
      with correct note pitches
- [ ] MIDI output of MM2 reference track passes user ear-validation
      against game audio
- [ ] At least 8 of ~12 MM2 tracks batch-extract without parser errors
- [ ] Capcom parser works on a second game (DuckTales or MM3) with
      only a new manifest, no code changes

### Full Completion (Phase A + B)

- [ ] All Phase A criteria met
- [ ] Sunsoft parser extracts Batman Stage 1 with correct pitches on
      pulse, triangle, and noise channels
- [ ] DPCM bass channel produces recognizable bass line (correct
      pitches, Sunsoft timbre)
- [ ] End-to-end pipeline (ROM to WAV) works for Batman
- [ ] Sunsoft parser works on Blaster Master with only a new manifest
- [ ] DriverCapability supports at least 4 volume models: parametric,
      lookup_table, duty_cycling, table_adsr
- [ ] rom_identify.py can distinguish Maezawa, Capcom, and Sunsoft
      drivers on a ROM it has not seen before

### Stretch Goals

- [ ] Mega Man 2 full soundtrack with REAPER projects and YouTube
      description
- [ ] Batman full soundtrack with DPCM bass rendered
- [ ] Journey to Silius extraction (peak Sunsoft audio quality)

---

## 9. Priority Ranking

**Overall priority: 2 (after completing remaining Konami Maezawa games)**

The DRIVER_TAXONOMY.md scaling strategy ranks targets by ROI:

| Priority | Target | Rationale |
|----------|--------|-----------|
| 1 | Konami Maezawa remaining (Super C, TMNT, Gradius, etc.) | Existing parser, just needs per-game config |
| **2** | **Capcom MM-era (this wish, Phase A)** | **High reuse (10-15 games), no expansion HW, proven community docs** |
| **3** | **Sunsoft DPCM (this wish, Phase B)** | **5-8 games, iconic audio, but requires DPCM path** |
| 4 | Tecmo (Ninja Gaiden) | High demand, moderate reuse, base APU only |
| 5 | Konami VRC6/MMC5 (CV3) | Expansion chip emulation needed |

Capcom Phase A should begin once Contra extraction reaches COMPLETE
status or when a natural pause in Konami work occurs. Phase B (Sunsoft)
should follow Phase A, not run in parallel, because the DPCM path
design benefits from having the Capcom experience as a second data
point on non-Konami driver integration.

**Do not start this wish before the Contra lookup table envelope
work is done.** The Contra work validates the DriverCapability
dispatch pattern that Capcom and Sunsoft will rely on. Shipping
Capcom on a pattern that has only been tested with one driver family
risks discovering architectural problems after two families of code
depend on it.
