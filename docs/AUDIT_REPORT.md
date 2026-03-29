# NES Music Studio — Phase 2 Audit Report

Generated: 2026-03-28
Baseline: 17 tests pass, CV1 pulse 0/0/0, triangle 0/195/195

---

## 1. Baseline Status

| Check | Command | Expected | Actual | Status |
|-------|---------|----------|--------|--------|
| Invariant tests | pytest -v | 17 pass | 17 pass | PASS |
| CV1 pulse1 trace | trace_compare --frames 1792 | 0/0/0 | 0/0/0 | PASS |
| CV1 pulse2 trace | trace_compare --frames 1792 | 0/0/0 | 0/0/0 | PASS |
| CV1 triangle trace | trace_compare --frames 1792 | 0/195/195 | 0/195/195 | PASS |

---

## 2. Module Classification Table

| File | Layer | Classification | Violations | Risk |
|------|-------|---------------|------------|------|
| extraction/drivers/konami/parser.py | DATA+ENGINE | EXPLICIT (self-labels "mixed") | MIXED_LAYER, DOC_CONTRADICTION | MED |
| extraction/drivers/konami/contra_parser.py | DATA | EXPLICIT | None | LOW |
| extraction/drivers/konami/frame_ir.py | ENGINE+HARDWARE | EXPLICIT (self-labels "mixed") | MIXED_LAYER, DOC_CONTRADICTION | HIGH |
| extraction/drivers/konami/midi_export.py | DATA | EXPLICIT | DEPRECATED_API_PATH | LOW |
| extraction/drivers/konami/identify.py | DATA | IMPLICIT | MISSING_STATUS, PLACEHOLDER | LOW |
| scripts/trace_compare.py | TOOLING | EXPLICIT | VOLUME_MISMATCH_HIDING | MED |
| scripts/render_wav.py | HARDWARE+TOOLING | IMPLICIT | MISSING_STATUS, HIDDEN_APPROXIMATION, CV1_HARDCODED | MED |
| scripts/rom_identify.py | TOOLING | IMPLICIT | MISSING_STATUS | LOW |
| scripts/full_pipeline.py | TOOLING | IMPLICIT | MISSING_STATUS, CV1_HARDCODED | LOW |
| scripts/generate_project.py | TOOLING | IMPLICIT | MISSING_STATUS | LOW |

### Classification notes

**parser.py**: Self-labels as "mixed (shared types + CV1-specific parser)".
Shared event types (NoteEvent, RestEvent, InstrumentChange, etc.) are
defined here and imported by contra_parser.py. This is pragmatic — the
types are genuinely shared. The CV1-specific code (ChannelParser,
KonamiCV1Parser, pointer table constants) could theoretically be
separated, but the coupling is low-risk because Contra has its own
parser class.

**frame_ir.py**: Self-labels as "mixed (engine envelope strategies +
hardware period/freq conversion)". Contains: ENGINE (envelope strategies),
HARDWARE (period_to_freq, PERIOD_TABLE, freq_to_midi_note), DATA
(parser_to_frame_ir conversion). The mixing is architecturally deliberate
(strategies + conversion in one module), but the HARDWARE functions are
pure and could be extracted if the module grows.

**render_wav.py**: Contains HARDWARE APU synthesis (pulse/triangle
waveform generation) and TOOLING (file I/O, CLI). Uses linear mixing
(UNKNOWNS.md UNK-005) but does not label this as APPROXIMATE.

---

## 3. Invariant Enforcement Matrix

| INV | Name | Documented | Tested | Enforced | Status |
|-----|------|-----------|--------|----------|--------|
| 001 | phase2_start >= 1 | Y | test_frame0_always_initial_volume, test_phase2_start_clamped | `max(1, ...)` frame_ir.py:196 | OK |
| 002 | Full hardware duration | Y | test_valid_song_passes, test_truncated_duration_detected | validate_full_duration() | OK (not auto-called) |
| 003 | Bounce at 1 (Contra) | Y | test_bounce_at_1_during_decrescendo | `max(1, vol-1)` in _contra_lookup_envelope | OK |
| 004 | Triangle -12 offset | Y | test_pitch_to_midi_triangle_offset | `midi -= 12` in pitch_to_midi | OK |
| 005 | BASE_MIDI_OCTAVE4=36 | Y | test_base_octave4_is_36 | Constant definition | OK |
| 006 | EC pitch adjustment | Y | **N/A** | Parser state tracking | **MISSING_TEST** |
| 007 | Triangle linear counter | Y | **N/A** | `(reload+3)//4` | **MISSING_TEST** (no expected-mismatch assertion) |
| 008 | DX byte count per-game | Y | **N/A** | Separate parsers | **MISSING_TEST** |
| 009 | Decrescendo threshold | Y (PROVISIONAL) | **N/A** | `(mul*dur)>>4` | **MISSING_TEST** |
| 010 | Derived timing clamped | Y | Partial (INV-001) | Various max/min | OK (general principle) |

**4 invariants lack dedicated tests.** INV-006, INV-007, INV-008, INV-009.

---

## 4. Violation Registry

### V-001: DOC_CONTRADICTION in _cv1_parametric_envelope docstring

- **File**: extraction/drivers/konami/frame_ir.py:185-186
- **Layer**: ENGINE
- **Problem**: Docstring says "Bounce-at-1: volume holds at 1, never
  reaches 0 during phase 2 (same resume_decrescendo behavior as Contra)."
  But the code does NOT bounce at 1 for CV1. Phase 2 decrements vol to 0.
  The verified test `test_verified_b5_vol5_fade2_3` confirms:
  `[5, 4, 3, 3, 3, 3, 3, 2, 1, 0]` — final frame is 0.
- **Evidence**: test_verified_b5_vol5_fade2_3 line 49, code line 202-203
- **Risk Level**: MEDIUM — misleads future developers about CV1 behavior
- **Fix**: Remove bounce-at-1 claim from CV1 docstring. Bounce-at-1 is
  Contra-specific (INV-003).

### V-002: Volume mismatches hidden from mismatch_regions in trace_compare.py

- **File**: scripts/trace_compare.py:109
- **Layer**: TOOLING
- **Problem**: `any_mismatch` is computed as `not (pitch_match and
  sounding_match)` — it does NOT include `vol_match` or `duty_match`.
  Volume-only mismatches are counted in `volume_mismatches` but do not
  appear in `mismatch_regions`. This means the region report could show
  "no mismatch regions" while volume_mismatches > 0.
- **Evidence**: Line 109: `any_mismatch = not (pitch_match and sounding_match)`
- **Risk Level**: MEDIUM — could hide volume regression
- **Fix Recommended**: Include vol_match in any_mismatch, OR add separate
  volume_mismatch_regions tracking. Note: this would change the existing
  report format for triangle (195 sounding mismatches already tracked).

### V-003: render_wav.py linear mixing not labeled APPROXIMATE

- **File**: scripts/render_wav.py:123-148
- **Layer**: HARDWARE
- **Problem**: The mixer sums channels linearly (`mix[start:end] += audio * 0.25`).
  Real NES uses nonlinear DAC (UNKNOWNS.md UNK-005). No APPROXIMATE label.
- **Evidence**: Lines 139, 142, 147 — linear addition with fixed gain
- **Risk Level**: LOW — known limitation, affects tonal character not accuracy
- **Fix**: Add APPROXIMATE comment at the mixing section.

### V-004: render_wav.py and full_pipeline.py hardcoded to CV1

- **File**: scripts/render_wav.py:27, scripts/full_pipeline.py:27
- **Layer**: TOOLING
- **Problem**: Both only import KonamiCV1Parser, not ContraParser. No
  DriverCapability dispatch. Cannot render Contra tracks without modification.
- **Evidence**: Import statements, no ContraParser reference
- **Risk Level**: LOW — known limitation, documented in handover
- **Fix Recommended**: Out of scope for Phase 2. Note in STATUS.

### V-005: MISSING_STATUS on 4 scripts

- **File**: scripts/render_wav.py, scripts/rom_identify.py, scripts/full_pipeline.py, scripts/generate_project.py
- **Layer**: TOOLING
- **Problem**: No STATUS comment block as required by architecture rule 4.
- **Risk Level**: LOW
- **Fix**: Add STATUS blocks.

### V-006: identify.py is a non-functional placeholder

- **File**: extraction/drivers/konami/identify.py
- **Layer**: DATA
- **Problem**: Contains only a `register_konami_signatures` function
  with a `pass` body. References `nesml.static_analysis.driver_identify`
  types. Not connected to any working code path.
- **Evidence**: Lines 13-27 — empty function body
- **Risk Level**: LOW — dead code, not harmful
- **Fix Recommended**: Add MISSING_STATUS label. No code change needed.

### V-007: midi_export.py uses deprecated envelope_tables parameter

- **File**: extraction/drivers/konami/midi_export.py:240
- **Layer**: DATA
- **Problem**: `export_to_midi()` passes `envelope_tables=envelope_tables`
  to `parser_to_frame_ir()` using the deprecated compatibility shim
  instead of constructing a `DriverCapability` object.
- **Evidence**: Line 240
- **Risk Level**: LOW — the shim works correctly, just not canonical
- **Fix Recommended**: Out of scope for Phase 2 (working code).

---

## 5. Triangle Isolation Assessment

**Status: CLEAN — no triangle assumptions leak into pulse/shared code.**

Triangle-specific logic is isolated in these locations:

1. **frame_ir.py:361-386** — Triangle branch in `parser_to_frame_ir()`.
   Self-contained `if is_triangle:` block with APPROXIMATION label at
   line 369. Computes sounding_frames from linear counter. Does not
   affect pulse branches.

2. **frame_ir.py:523** — Triangle sounding in `trace_to_frame_ir()`:
   `tr_sounding = tr_period > 2 and tr_linear > 0`. Different logic
   than parser's linear counter model (trace uses raw register values).

3. **parser.py:188-203** — `pitch_to_midi()` has `is_triangle` parameter
   for -12 offset. Clean parameterization, no implicit branching.

4. **render_wav.py:77-95** — `render_triangle_frame()` is a separate
   function from `render_pulse_frame()`. No shared state.

**Missing**: No test asserting that triangle is expected to produce
mismatches. If someone accidentally "fixes" triangle to 0 mismatches
by breaking the model, no test would catch it.

---

## 6. DX/Command Parser Assessment

**Status: CLEAN — DX parsing is fully polymorphic via separate parsers.**

- CV1 DX: `parser.py:350-398` reads 2 bytes (instrument + fade).
  Triangle skips fade byte (line 373).
- Contra DX: `contra_parser.py:201-283` reads 3 bytes (pulse) or
  1 byte (triangle). Completely separate implementation.
- No shared DX parsing function exists. Each parser handles its own
  format independently.
- FE/FD/FF control flow commands: duplicated between parsers with
  identical logic but different `cpu_to_rom` functions. This is
  acceptable — the address resolution differs per game (mapper 0 vs 2).

**Missing**: No test validates that CV1 DX reads exactly 2 bytes or
that Contra DX reads exactly 3/1 bytes.

---

## 7. Unknown Classification Validation

| UNK | Classification | Code State | Correct? |
|-----|---------------|------------|----------|
| 001 | HARDWARE | APPROXIMATE label in frame_ir.py:369 | YES |
| 002 | ENGINE | STATUS block says "NOT MODELED" | YES |
| 003 | DATA | Not modeled, not falsely solved | YES |
| 004 | DATA | Not implemented | YES |
| 005 | HARDWARE | render_wav.py linear mixing, NO label | **MISSING LABEL** |
| 006 | ENGINE | contra_parser.py skips EB params (line 299) | YES — documented as limitation |
| 007 | ENGINE | INV-009 labeled PROVISIONAL | YES |
| 008-012 | Various | N/A (future games / SFX) | N/A |

**One issue**: UNK-005 (mixer nonlinearity) is correctly classified in
UNKNOWNS.md but render_wav.py has no APPROXIMATE label on the mixing code.

---

## 8. Status Label Coverage

| Module | Has STATUS Block | Layer Labeled |
|--------|-----------------|---------------|
| parser.py | YES | YES ("mixed") |
| contra_parser.py | YES | YES ("data") |
| frame_ir.py | YES | YES ("mixed") |
| midi_export.py | YES | YES ("data") |
| identify.py | NO | NO |
| trace_compare.py | YES | YES ("tooling") |
| render_wav.py | NO | NO |
| rom_identify.py | NO | NO |
| full_pipeline.py | NO | NO |
| generate_project.py | NO | NO |

**5 modules missing STATUS blocks.** All are in scripts/ or identify.py.
The 4 core driver modules (parser, contra_parser, frame_ir, midi_export)
all have complete STATUS blocks.

---

## 9. Recommended Fixes (ordered by risk)

### CRITICAL: None

### HIGH:

1. **Add triangle expected-mismatch test** (V: missing, INV-007)
   — Prevents false fixes. Assert triangle produces ≥ 100 sounding
   mismatches on a known pattern.

2. **Add INV-006 (EC pitch adjustment) test**
   — Validates that Contra parser applies pitch_adj correctly.

### MEDIUM:

3. **Fix V-001: Remove bounce-at-1 claim from CV1 docstring**
   — frame_ir.py _cv1_parametric_envelope docstring contradicts code+tests.

4. **Fix V-002: Include volume in mismatch_regions** (or document exclusion)
   — trace_compare.py any_mismatch ignores volume.

5. **Add INV-008 (DX byte count) test**
   — Validates parser byte consumption for DX commands.

6. **Add INV-009 (decrescendo threshold) test**
   — Basic property test for the PROVISIONAL formula.

### LOW:

7. **Add STATUS blocks to 5 modules** (V-005, V-006)
8. **Add APPROXIMATE label to render_wav.py mixing** (V-003)
9. **Note CV1-hardcoded limitation on render_wav.py and full_pipeline.py** (V-004)
