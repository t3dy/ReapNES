# WISH #1: Contra Trace Validation to Zero Mismatches

## 1. What This Wish Is

Reduce Contra Jungle's trace comparison mismatches from their current
levels (72 pitch / 175 volume on pulse1, 72 pitch / 199 volume on
pulse2, 17 pitch / 250 volume on triangle) to zero pitch mismatches
and near-zero volume mismatches -- matching the CV1 standard of 0 pitch
mismatches across 1792 frames.

This is NOT about capturing the trace. The trace already exists at
`extraction/traces/contra/jungle.csv` (captured 2026-03-28, 2976
frames, start offset 155). The wish is about closing the gap between
our parser/IR output and what the trace shows the hardware actually
produced.

## 2. Why It Matters

### What it blocks

Every remaining Contra fidelity gap is blocked on trace-level debugging:

- **Decrescendo timing** -- the `(mul * dur) >> 4` formula is marked
  "provisional" in `docs/CONTRAGOALLINE.md`. Without frame-level trace
  comparison, we cannot determine if the onset is off by 1 frame or if
  the formula itself is wrong.
- **UNKNOWN_SOUND_01 subtraction** -- accounts for the remaining ~3.4%
  volume gap (per `docs/NOTEDURATIONS.md`). The trace shows
  post-subtraction values; our model shows pre-subtraction. Closing
  this requires comparing specific frames where vol=2 in our IR but
  vol=1 in the trace.
- **Triangle linear counter precision** -- 250 sounding mismatches on
  triangle. The CV1 triangle has 195 sounding mismatches (labeled
  APPROXIMATE). Contra's 250 may include both the same hardware
  approximation issue AND parser-level bugs.
- **Auto-decrescendo mode (bit 7)** -- approximated as linear 1/frame
  decay, but the real engine uses `PULSE_VOL_DURATION` which we have
  not extracted. Trace frames for bit-7 notes would reveal the actual
  decay shape.

### What it would unlock

- **Validated envelope tables**: All 54 lookup tables from
  `pulse_volume_ptr_tbl` confirmed correct or identified as wrong,
  with specific frame numbers pointing to the error.
- **Noise channel register values**: The trace includes `$400C_vol`,
  `$400E_period`, `$400E_mode` -- actual kick drum tuning data that
  would enable accurate percussion modeling (Wish #13).
- **DMC timing data**: The trace includes `$4011_dac` changes -- the
  exact DAC output waveform for snare/cymbal samples, usable for
  Wish #5 (DMC sample decoding).
- **Regression baseline**: Once mismatches hit zero (or a known floor),
  any future code change that increases the count is instantly flagged
  as a regression.
- **Confidence for batch extraction**: The 10 remaining Contra tracks
  can be batch-extracted with confidence that the parser and IR are
  correct, rather than relying on ear-checks alone.

### Specific numbers

| Metric | CV1 (achieved) | Contra (current) | Contra (target) |
|--------|---------------|-------------------|-----------------|
| Pitch mismatches (pulse1) | 0 / 1792 | 72 / 2976 | 0 / 2976 |
| Pitch mismatches (pulse2) | 0 / 1792 | 72 / 2976 | 0 / 2976 |
| Volume mismatches (pulse1) | 45 / 1792 | 175 / 2976 | <50 / 2976 |
| Volume mismatches (pulse2) | 50 / 1792 | 199 / 2976 | <50 / 2976 |
| Triangle pitch | 0 / 1792 | 17 / 2976 | 0 / 2976 |
| Triangle sounding | 195 / 1792 | 250 / 2976 | <20 / 2976 |

## 3. Current State

### What exists

- **Trace file**: `extraction/traces/contra/jungle.csv` -- 2976 frames
  of per-frame APU state for all 5 channels, captured from Mesen 2
  using `docs/mesen_scripts/mesen_apu_capture.lua`.
- **Trace comparison script**: `scripts/trace_compare.py` with
  `--game contra` support. Produces
  `docs/TraceComparison_Contra.md` and
  `data/trace_diff_contra.json`.
- **Comparison report**: `docs/TraceComparison_Contra.md` showing the
  current mismatch counts and regions.
- **Contra parser**: `extraction/drivers/konami/contra_parser.py` --
  handles DX byte count (3 pulse / 1 triangle), percussion channel,
  EC pitch adjustment, 54 envelope lookup tables.
- **Frame IR**: `extraction/drivers/konami/frame_ir.py` with
  `_contra_pulse_envelope()` and `DriverCapability.contra()`.
- **Manifest**: `extraction/manifests/contra.json` with trace
  validation section recording current match percentages.

### What's missing

1. **Root cause analysis of the 72 pitch mismatches on pulse channels.**
   The manifest notes "likely timing drift over long sequences" but this
   has not been investigated frame-by-frame. The first pitch error is at
   frame 0, which suggests an alignment/offset problem rather than drift.

2. **Root cause of the 17 triangle pitch mismatches.** The manifest
   suspects EC adjustment or linear counter timing but neither has been
   tested.

3. **UNKNOWN_SOUND_01 extraction and modeling.** The value needs to be
   read from the DX parsing context and applied as a post-processing
   step in the IR.

4. **PULSE_VOL_DURATION extraction** for auto-decrescendo mode (bit 7
   notes). Currently approximated.

5. **Frame-level debugging session** using the established protocol:
   dump frames around first mismatch, classify by layer (ENGINE / DATA /
   HARDWARE), form one hypothesis, test, iterate.

## 4. Concrete Steps to Accomplish It

### Phase 1: Alignment (fix pitch mismatches)

**Step 1.1**: Dump the first mismatch region on pulse1.
```bash
cd C:/Dev/NESMusicStudio
PYTHONPATH=. python scripts/trace_compare.py --game contra --dump-frames 0-10 --channel pulse1
```
The first pitch error is at frame 0. This likely means the
`trace_start_frame` offset (155) is wrong by a few frames. Compare the
first sounding note in our IR against the trace and adjust.

**Step 1.2**: If the offset fix doesn't resolve all 72 mismatches,
dump frames around each remaining mismatch region (frames 882-885,
900-903, etc. from the report). These 4-frame clusters suggest the
parser is producing notes that are 4 frames offset from where the
hardware plays them -- possibly a repeat-count or rest-duration bug.

**Step 1.3**: Rerun comparison after each fix:
```bash
PYTHONPATH=. python scripts/trace_compare.py --game contra --frames 2976
```

### Phase 2: Volume model (fix volume mismatches)

**Step 2.1**: With pitch at zero, dump volume mismatches on pulse1.
Look for patterns: are they all at note boundaries (envelope phase
transition)? At note ends (decrescendo timing)? At specific envelope
table indices?

**Step 2.2**: Extract UNKNOWN_SOUND_01 from the Contra DX parsing
path. The disassembly (`references/nes-contra-us/`) documents where
this value is set. Apply `vol = max(0, vol - unknown_01)` when
`vol >= 2` in `_contra_pulse_envelope()`.

**Step 2.3**: Extract PULSE_VOL_DURATION for bit-7 notes. Modify the
auto-decrescendo branch to use the actual duration counter instead of
decaying to zero.

**Step 2.4**: Compare decrescendo onset frame against trace. The
formula `(decrescendo_mul * duration) >> 4` may need to use
`SOUND_CMD_LENGTH` (counting down) instead of `duration` (total).
Dump 5 long notes and compare the frame where volume starts
decrementing.

### Phase 3: Triangle (fix triangle mismatches)

**Step 3.1**: Dump triangle frames 0-100. The 78-frame mismatch region
at the start may be another alignment issue.

**Step 3.2**: For the recurring 2-frame mismatches (frames 100-101,
106-107, etc.), check whether these are linear counter off-by-one
errors (known limitation, same as CV1's 195 mismatches) or parser bugs.

**Step 3.3**: Verify EC pitch adjustment applies to triangle. The
manifest confirms EC for pulse but triangle may need separate handling.

### Phase 4: Manifest update

**Step 4.1**: Update `extraction/manifests/contra.json` with new
mismatch counts.

**Step 4.2**: Move "jungle" from `ear_validated_tracks` to
`trace_validated_tracks` once pitch mismatches hit zero.

## 5. Estimated Effort

| Phase | Sessions | Prompts | Human time |
|-------|----------|---------|------------|
| Phase 1 (alignment) | 1 | 5-8 | 30 min (reviewing dumps, adjusting offset) |
| Phase 2 (volume) | 1-2 | 8-15 | 1 hr (reading disassembly for UNKNOWN_SOUND_01) |
| Phase 3 (triangle) | 1 | 3-5 | 15 min |
| Phase 4 (manifest) | 0 | 1 | 5 min |
| **Total** | **2-3** | **17-29** | **~2 hours human time** |

The CV1 trace validation took approximately 3 sessions from first
capture to zero pitch mismatches. Contra should be faster because:
- The trace already exists (CV1's first session was mostly capture).
- The comparison tooling is built and tested.
- The debugging protocol is established.
- The parser is already at 91% pitch match (CV1 started lower).

## 6. Dependencies

### Hard dependencies (must exist first)

All satisfied:
- Mesen APU trace for Contra Jungle -- EXISTS at
  `extraction/traces/contra/jungle.csv`
- `trace_compare.py` with `--game contra` -- EXISTS and produces
  reports
- Contra parser (`contra_parser.py`) -- EXISTS, parses all 11 tracks
- Frame IR with Contra envelope support -- EXISTS via
  `DriverCapability.contra()`
- Annotated disassembly -- EXISTS at `references/nes-contra-us/`

### Soft dependencies (helpful but not blocking)

- Understanding of UNKNOWN_SOUND_01 from disassembly (needed for
  Phase 2, can be read during the session)
- PULSE_VOL_DURATION location in ROM (needed for Phase 2 bit-7 notes)

## 7. Risks and Failure Modes

### Risk 1: Start frame offset is fundamentally wrong

**Likelihood**: Medium. The first pitch error at frame 0 strongly
suggests this.
**Impact**: Fixing it could resolve the majority of the 72 pitch
mismatches in one change.
**Mitigation**: Dump frames 0-30 on all channels, find the first
sounding note in the trace, align manually.

### Risk 2: Timing drift accumulates over the song

**Likelihood**: Medium. The manifest notes this as the suspected cause
of pitch mismatches.
**Impact**: If the parser's tempo/repeat handling is off by even 1
frame per phrase, the error compounds. By frame 2976, the parser and
trace could be dozens of frames apart.
**Mitigation**: Check alignment at multiple points (frame 500, 1000,
1500, 2000). If drift exists, it means a duration calculation is wrong
-- likely in repeat count or rest handling.

### Risk 3: The trace itself has artifacts

**Likelihood**: Low. The capture script is validated against CV1.
**Impact**: Would produce phantom mismatches.
**Mitigation**: Spot-check a few trace frames against Mesen's
debugger manually. Look for impossible values (period=0 with vol>0).

### Risk 4: UNKNOWN_SOUND_01 varies per instrument

**Likelihood**: Medium. Different DX contexts may set different values.
**Impact**: A single global correction would fix some notes but break
others.
**Mitigation**: Group volume mismatches by DX instrument and check
whether the offset is consistent within each group.

### Risk 5: Volume floor is a hardware behavior, not engine

**Likelihood**: Low. The disassembly shows explicit software
subtraction.
**Impact**: Would require modeling a hardware effect we haven't
encountered before.
**Mitigation**: The trace shows actual register values. If the
subtraction is in hardware, the engine writes the pre-subtraction
value and the trace reads the post-subtraction value. But the Mesen
capture script reads decoded state, not raw writes, so this
distinction should be visible.

### Risk 6: Changing comparison tool masks real errors

**Likelihood**: Low but has happened before (the period-vs-MIDI-note
comparison bug on CV1).
**Impact**: Zero mismatches reported while actual errors persist.
**Mitigation**: After reaching zero mismatches, human must listen to
the output and compare against the game. This is rule 6 in CLAUDE.md.

## 8. Success Criteria

### Gate 1: Zero pitch mismatches on pulse channels
```
| pulse1  | 0 pitch mismatches / 2976 frames |
| pulse2  | 0 pitch mismatches / 2976 frames |
```
This means every note our parser produces matches what the hardware
played, on every frame, for the entire Jungle loop.

### Gate 2: Zero pitch mismatches on triangle
```
| triangle | 0 pitch mismatches / 2976 frames |
```

### Gate 3: Volume mismatches below CV1 baseline ratio
CV1 achieves ~2.5% volume mismatch rate on pulse (45/1792). Contra
target: <5% (148/2976), acknowledging that the lookup-table envelope
model is inherently more complex than CV1's parametric model.

### Gate 4: Human ear-check passes
User listens to the Contra Jungle MIDI rendered through REAPER with
the NES JSFX plugin and confirms it matches the game. This catches
the class of errors that trace comparison cannot (shared bugs in both
the parser and the comparison tool).

### Gate 5: Manifest updated
`extraction/manifests/contra.json` shows:
```json
"trace_validated_tracks": ["jungle"],
"trace_validation": {
    "pitch_mismatches": 0,
    "volume_mismatches": "<148",
    "status": "verified"
}
```

### Gate 6: No CV1 regressions
```bash
PYTHONPATH=. python scripts/trace_compare.py --game cv1 --frames 1792
```
Must still show 0 pitch mismatches on CV1. Any shared code changes
(frame_ir.py) could break the existing validated game.

## 9. Priority Ranking

**#1 of 14 wishes. Highest priority.**

This is the single highest-leverage action in the project because:

1. **It validates the entire Contra pipeline.** Parser, envelope
   tables, decrescendo model, pitch mapping -- all confirmed or
   corrected in one process.

2. **It unblocks at least 4 other wishes.** Wish #5 (DMC samples),
   Wish #13 (noise modeling), and aspects of Wish #2 (triangle
   precision) and Wish #3 (Super C) all benefit from a validated
   Contra extraction.

3. **It has the highest ratio of value to effort.** 2-3 sessions to
   close the gap, vs. 3-5 sessions for triangle precision (Wish #2)
   or unknown effort for a new driver family (Wish #12).

4. **The infrastructure is already built.** The trace exists, the
   comparison tool works, the parser is at 91% match. This is
   finishing work, not greenfield work.

5. **It establishes the second validated game.** CV1 alone could be
   a fluke. Two games with zero pitch mismatches proves the
   methodology works across different ROM layouts, envelope models,
   and command formats within the Konami driver family.
