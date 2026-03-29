# Trace Validation System — Audit Notes

Generated: 2026-03-28
File audited: scripts/trace_compare.py

---

## 1. Mismatch Category Separation

The trace comparison system tracks 4 mismatch types independently:

| Category | Counter | Condition |
|----------|---------|-----------|
| Pitch | pitch_mismatches | `ext.midi_note != tr.midi_note` AND both sounding |
| Volume | volume_mismatches | `ext.volume != tr.volume` AND either sounding |
| Duty | duty_mismatches | `ext.duty != tr.duty` AND either sounding (triangle excluded) |
| Sounding | sounding_mismatches | `ext.sounding != tr.sounding` |

**Assessment**: Categories are properly separated in counters. Each
tracks independently. The summary report shows all 4 columns.

**Issue**: The `mismatch_regions` tracking uses `any_mismatch` which is
defined as `not (pitch_match and sounding_match)` — this does NOT include
volume or duty. Volume-only mismatches are counted but do not generate
mismatch regions. This means the "Mismatch Regions" section of the report
could show no regions even when volume_mismatches > 0.

**Impact**: For CV1 pulse (0 volume mismatches), this is invisible.
For triangle (195 sounding mismatches), regions are correctly tracked
because sounding IS included. For Contra (3.4% volume gap), the volume
mismatches would not appear as contiguous regions in the report.

---

## 2. Systematic Error Hiding Risk Assessment

### Known systematic error class: octave shift

The trace comparison compares MIDI note numbers, not raw periods. If
both the parser and the trace-to-IR conversion share the same octave
mapping bug, they would agree (0 mismatches) while both being wrong.

**Current safeguard**: INV-005 documents this exact scenario. The
`freq_to_midi_note` function in frame_ir.py applies a +12 offset to
pulse channels (`octave_offset=12` at trace_compare.py indirectly via
trace_to_frame_ir). If this offset were wrong, BOTH the parser output
AND the trace interpretation would shift by the same amount, hiding
the error.

**Mitigation**: The +12 offset was validated by ear comparison against
the game (INV-005 evidence). There is no automated test for this —
and by design, there cannot be one (the test would need an external
ground truth).

### "Both silent" masking

Pitch mismatches are only counted when BOTH sides are sounding
(line 111: `if not pitch_match and ext.sounding and tr.sounding`).
This means: if the parser says a note is sounding but the trace says
silence (or vice versa), the pitch comparison is skipped. This is
correct — comparing pitch of a sounding vs non-sounding frame is
meaningless. But it means sounding mismatches can mask pitch errors.

**Current state**: CV1 pulse has 0 sounding mismatches, so no masking
occurs. CV1 triangle has 195 sounding mismatches — pitch comparison
is skipped for those frames, which is correct (triangle pitch is
always 0 when not sounding in the trace).

### Period retention in trace

When the trace shows a channel going silent (volume = 0), the period
register retains its last value. The trace_to_frame_ir function sets
`midi_note = 0` when volume = 0 (line 520-521), not using the retained
period. The parser similarly sets volume = 0 for rest events but keeps
period = 0. This means silent frames always agree on midi_note = 0,
which is correct.

---

## 3. Known Limitations

1. **No cross-validation between parser and trace for absolute pitch.**
   Both use the same `freq_to_midi_note` with the same octave offset.
   A shared mapping error would be invisible.

2. **Volume mismatch regions not tracked.** Only pitch + sounding
   mismatches generate region entries.

3. **Trace start frame is manually calibrated.** CV1 = frame 111,
   Contra = frame 155. If these offsets are wrong by even 1 frame,
   every subsequent frame comparison is shifted, producing cascading
   false mismatches.

4. **No noise/percussion channel comparison.** Drums are not in the
   frame IR and are not compared against the trace.

5. **Duty cycle comparison disabled for triangle.** Line 106:
   `duty_match = ext.duty == tr.duty or ch_name == "triangle"`.
   This is correct (triangle has no duty) but means any duty bug
   on triangle would be silently ignored.

6. **Frame diffs capped at 50.** Line 136: only first 50 mismatched
   frames are recorded in detail. For triangle (195 mismatches), the
   last 145 are not in the detailed diff. The counts are still accurate.
