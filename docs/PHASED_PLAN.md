# NES Music Lab — Phased Plan (Revised)

## Phase 1: Architecture Correction and Schema Completion (Current)

**Goal:** Establish three-pipeline architecture, symbolic model, and scaffolding.

### Acceptance Criteria
- [x] Repository restructured for static/dynamic/reconciled pipelines
- [x] Typed symbolic models: Song, ChannelStream, Pattern, NoteEvent, RestEvent, LoopPoint, JumpCall, TempoModel, MeterHypothesis, InstrumentBehavior, VolumeEnvelope, PitchEnvelope, DutySequence, ArpeggioMacro, DPCMTriggerEvent, ExpansionAudioEvent, UnknownCommand, Provenance, Confidence
- [x] Static analysis scaffolding: driver identification, pointer scanning, sequence decoding base classes
- [x] Dynamic analysis: trace ingest, frame normalize, event stream, channel state tracking
- [x] Reconciliation layer: alignment, discrepancy reporting, confidence adjustment
- [x] Export layer: MIDI export scaffolding, REAPER metadata scaffolding
- [x] Driver directories restructured with spec.md, identify.py, parser.py, fixtures/, tests/
- [x] 8 skills, 5 subagents, hooks configured
- [x] CLAUDE.md updated for three-pipeline architecture
- [x] 106 tests passing across all layers
- [ ] Schema v0.2.0 reflecting static/dynamic/reconciled Song model
- [ ] End-to-end integration test: static Song → reconcile → export

### Phase 1 Status: **Near complete. Scaffolding done. Schemas need revision.**

---

## Phase 2: ROM and Driver Identification

**Goal:** Robust driver identification layer for classifying ROMs.

### Target
- Castlevania (U) (V1.0) as primary target ROM (Konami pre-VRC driver)
- Secondary: Darkwing Duck or Bionic Commando (Capcom family)

### Work
1. Implement code signature detection for Konami pre-VRC
   - Find the NMI handler → music update routine
   - Identify the play routine's APU write pattern
   - Register as DriverSignature
2. Implement pointer structure analysis
   - Scan for pointer tables in Castlevania PRG data
   - Identify song table candidates
   - Validate pointers resolve to plausible code/data regions
3. Build ROM manifest with confidence scores and manual override support
4. Test driver identification against all 7 ROMs in roms/

### Acceptance Criteria
- [ ] DriverIdentifier correctly classifies Castlevania as Konami pre-VRC
- [ ] Song table located in Castlevania PRG data
- [ ] Per-channel data pointers identified for at least one song
- [ ] Identification produces ranked candidates with evidence
- [ ] All existing tests still pass

---

## Phase 3: Static Parser for Konami Pre-VRC

**Goal:** Crack the Konami driver bytecode and produce symbolic Song output.

### Work
1. **Locate music tables.** Use pointer scanning to find the song table header.
2. **Map the command byte format.** Systematically decode Castlevania's music data:
   - Identify note command encoding (pitch index + duration)
   - Identify rest/wait commands
   - Identify control flow (loop, jump, end)
   - Identify envelope/duty selection commands
   - Document unknown opcodes explicitly
3. **Build the KonamiPreVRCDecoder.** Implement decode_command() for each identified opcode.
4. **Extract symbolic Songs.** Parse at least 3 songs (Stage 1, Boss, Title) into Song objects with:
   - Per-channel ChannelStreams
   - Pattern structure (if driver uses it)
   - Loop points
   - Tempo/speed values
5. **Document everything.** Update `drivers/konami/spec.md` with confirmed command bytes, update NOTES.md with open questions.
6. **Test against fixtures.** Create golden output fixtures for decoded songs.

### Acceptance Criteria
- [ ] KonamiPreVRCDecoder handles all command bytes for Castlevania music data
- [ ] Unknown opcodes are emitted as UnknownCommand, not silently skipped
- [ ] At least 3 songs produce valid Song objects with events and patterns
- [ ] All note events have period values; pitch mapping is done separately
- [ ] spec.md documents confirmed command format with evidence
- [ ] Golden test fixtures lock in correct decoder output
- [ ] `/research-audit` passes

---

## Phase 4: Dynamic Trace Support and Reconciliation

**Goal:** Capture traces, align with static output, produce reconciled results.

### Work
1. Capture Mesen APU traces for Castlevania songs (Stage 1, Boss, Title)
2. Run dynamic analysis pipeline: ingest → normalize → event stream
3. Run reconciliation: align static Song events with runtime trace events
4. Produce discrepancy reports
5. Adjust confidence scores based on agreement/disagreement
6. Validate:
   - Note timing from static matches runtime within 2 frames
   - Loop points from static match runtime loop behavior
   - Tempo hypothesis matches measured runtime timing

### Acceptance Criteria
- [ ] At least 3 Castlevania songs have both static and dynamic analysis
- [ ] Reconciliation produces per-channel match ratios > 0.7
- [ ] Discrepancy reports identify any mismatches with severity levels
- [ ] Reconciled Song objects carry source_type=RECONCILED where confirmed
- [ ] No higher-tier evidence was overwritten by lower-tier

---

## Phase 5: Export Layer

**Goal:** MIDI and REAPER exports from reconciled symbolic model.

### Work
1. Implement MIDI export per channel (using `mido`)
2. Noise → percussion mapping table
3. DPCM → sample trigger mapping
4. REAPER metadata: automation lanes, markers, regions
5. `/midi-export-audit` passes

### Acceptance Criteria
- [ ] Per-channel MIDI files import correctly in REAPER
- [ ] Exported timing matches reconciled analysis
- [ ] Low-confidence events are annotated or flagged
- [ ] REAPER metadata includes volume and duty automation suggestions
- [ ] Provenance chain: MIDI → reconciled analysis → (static + dynamic)

---

## Phase 6: Second Driver Family

**Goal:** Capcom or Square driver, contrasting architecture.

### Candidate: Capcom (Mega Man / Darkwing Duck / Bionic Commando)
- Different command format from Konami
- Multi-speed engine ticks
- Complex envelope system
- Good ROM availability in roms/

### Acceptance Criteria
- [ ] Driver identification distinguishes Capcom from Konami
- [ ] Static parser handles Capcom command format
- [ ] At least 2 songs parsed end-to-end
- [ ] Reconciliation works across both driver families
- [ ] Shared utilities reduce per-driver implementation effort

---

## Decision Rules (All Phases)

- When uncertain, emit structured unknowns instead of inventing meaning.
- Prefer read-only investigation first, then targeted edits.
- Keep reverse-engineering notes close to the code that depends on them.
- Every parser assumption must be tested, documented, or labeled provisional.
- Never flatten symbolic structure too early.
- Never represent a hypothesis as a fact.
- Do not build only a trace-analysis lab.
- Do not build only pretty exports.
- Do not skip the actual driver parser layer.
