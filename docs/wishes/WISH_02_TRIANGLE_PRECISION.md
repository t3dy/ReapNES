# WISH #2: Triangle Linear Counter Precision

## 1. What This Wish Is

Replace the approximate integer formula for triangle linear counter
gating with a cycle-accurate model of the NES APU quarter-frame
sequencer. The current formula `(reload + 3) // 4` estimates how many
60Hz frames the triangle channel sounds before the linear counter
silences it. A precise model would track the 240Hz quarter-frame
clocking that the real 2A03 uses to decrement the linear counter,
computing the exact frame on which the counter reaches zero.

## 2. Why It Matters

**Correctness**: The triangle channel is the bass voice in every NES
game. Its note durations are entirely controlled by the linear counter
-- unlike pulse channels, the triangle has no volume register. Every
frame where the extraction disagrees with hardware about whether the
triangle is sounding is a frame where the bass line is wrong.

**Trace cleanliness**: 195 sounding mismatches on triangle represent
the single largest remaining error source in the CV1 validation. Pulse
channels show zero mismatches across all 1792 frames. Eliminating the
triangle residual would bring the entire CV1 extraction to zero
mismatches on all three melodic channels.

**Audibility**: Individual mismatches are 1/60th of a second (16.7ms)
and inaudible in isolation. However, they cluster at note boundaries
(the trace comparison shows ~8 notes per loop affected, often in runs
of 3-10 consecutive mismatch frames). On short bass notes, a 1-frame
error is a measurable percentage of the total sounding duration. The
cumulative effect may be detectable as slightly clipped or extended
bass articulations when comparing rendered audio against the game.

**Multi-game scaling**: Any game using the Konami Maezawa driver (CV1,
Contra, Super C, potentially others) shares this same linear counter
mechanism. Fixing it once benefits all current and future extractions.

## 3. Current State

**Formula**: `sounding_frames = min(duration, (tri_reload + 3) // 4)`

**Location**: `extraction/drivers/konami/frame_ir.py`, lines 367-373,
inside `parser_to_frame_ir()` in the triangle branch.

**Mismatch count**: 195 sounding mismatches on triangle across 1792
frames of CV1 Vampire Killer (track 2). Zero pitch mismatches, zero
volume mismatches, zero duty mismatches on triangle. The only triangle
errors are sounding state (on vs off).

**Error pattern**: From the trace comparison, mismatches appear as
runs of 1-10+ consecutive frames at note boundaries. Examples from
the first 200 frames:

- Frames 4-13 (10 frames) -- extraction says silent, trace says sounding
- Frames 18-20 (3 frames)
- Frames 25-27 (3 frames)
- Frames 32-48 (17 frames)
- Frames 53-55 (3 frames)

The first-frame diff table confirms the pattern: at frame 4, the
extraction has volume=0 / sounding=False while the trace has volume=15
/ sounding=True. The extraction is cutting notes short (or starting
them late) relative to what the hardware actually produces.

**Invariant**: INV-007 in INVARIANTS.md explicitly labels this as
APPROXIMATE and documents the root cause: the real APU clocks the
linear counter at 240Hz (quarter-frame ticks), which does not divide
evenly into 60Hz frame boundaries.

**Status label**: The frame_ir.py STATUS block lists this as a known
limitation: "Triangle linear counter: APPROXIMATION (reload+3)//4,
off by ~1 frame per note."

## 4. Concrete Steps

### Step 1: Understand the APU quarter-frame sequencer

The NES APU frame counter runs at 240Hz (4x the 60Hz video frame
rate). It produces quarter-frame clock signals that decrement both the
linear counter and the length counter. On NTSC hardware:

- CPU clock: 1,789,773 Hz
- APU frame counter period: 7457.5 CPU cycles (mode 0, 4-step)
- Quarter-frame ticks per video frame: 4 (approximately)
- The quarter-frame ticks do NOT align exactly with video frame
  boundaries -- they drift by fractional CPU cycles

The key insight: within a single 60Hz video frame, the linear counter
is decremented 4 times (approximately). But depending on where the
note starts relative to the quarter-frame sequencer phase, the first
and last frames of a note may see 3, 4, or 5 decrements.

### Step 2: Model the quarter-frame counter state

Add a `_triangle_linear_counter_precise()` function that:

1. Takes the reload value and the absolute frame number (to track
   sequencer phase across notes).
2. Tracks the 240Hz tick counter as a running state variable.
3. For each 60Hz frame, computes how many 240Hz ticks fall within
   that frame's CPU cycle window.
4. Decrements the linear counter by that many ticks.
5. Returns the sounding state (counter > 0) for each frame.

Pseudocode:

```python
def _triangle_sounding_frames_precise(
    reload: int,
    duration: int,
    sequencer_phase: int,  # CPU cycle offset into the APU frame counter
) -> list[bool]:
    """Compute per-frame sounding state using quarter-frame clocking.

    The APU frame counter (mode 0, 4-step) generates quarter-frame
    clocks at CPU cycles: 7457, 14913, 22371, 29829 (then resets).
    Each quarter-frame clock decrements the linear counter by 1.
    """
    QUARTER_FRAME_TICKS = [7457, 14913, 22371, 29829]
    FRAME_COUNTER_PERIOD = 29830  # CPU cycles per APU frame
    CYCLES_PER_VIDEO_FRAME = 29780.5  # CPU_CLK / 60

    counter = reload
    cpu_cycle = sequencer_phase
    sounding = []

    for f in range(duration):
        frame_start = cpu_cycle
        frame_end = cpu_cycle + CYCLES_PER_VIDEO_FRAME

        # Count quarter-frame ticks in this video frame
        ticks_this_frame = 0
        # ... (count ticks between frame_start and frame_end
        #      modulo the frame counter period)

        counter = max(0, counter - ticks_this_frame)
        sounding.append(counter > 0)
        cpu_cycle = frame_end

    return sounding
```

### Step 3: Determine sequencer phase at note start

The critical unknown is the APU frame counter's phase when a note
begins. Two approaches:

**Approach A (from trace)**: Extract the exact frame where each
triangle note starts sounding and stops sounding from the APU trace.
Back-calculate the sequencer phase that produces this behavior. If the
phase is consistent across notes (likely, since the driver writes
$4008 on deterministic frame boundaries), a single phase offset may
explain all 195 mismatches.

**Approach B (from disassembly)**: The sound engine runs in the NMI
handler (once per video frame). Find where in the NMI the $4008 write
occurs. The CPU cycle count from NMI entry to the write determines the
phase relationship between the video frame and the linear counter
reload.

Approach A is more practical and does not require cycle-counting the
NMI handler.

### Step 4: Validate against trace

Run `trace_compare.py --frames 1792` after implementation. The target
is 0 sounding mismatches on triangle. If the model is correct, all
195 mismatches should disappear simultaneously (they share the same
root cause). If some remain, the sequencer phase is wrong or there is
a second mechanism at play.

### Step 5: Add invariant test

Write `test_triangle_linear_counter_precise` that:
- Verifies known reload values produce the correct sounding frame
  count
- Checks edge cases: reload=0, reload=1, reload=127
- Validates against a subset of trace data (specific notes with
  known reload values and known sounding durations from the trace)

### Step 6: Update documentation

- Promote INV-007 from APPROXIMATE to VERIFIED
- Update frame_ir.py STATUS block
- Update CHECKLIST.md triangle section

## 5. Estimated Effort

**Research phase**: 2-4 prompts. Dump triangle trace data for 20+
notes, tabulate reload value vs actual sounding frames, look for a
pattern that reveals the sequencer phase offset.

**Implementation**: 2-3 prompts. Write the precise function, integrate
into `parser_to_frame_ir()`, run trace comparison.

**Validation and edge cases**: 1-2 prompts. Handle notes where the
reload value changes mid-note, verify Contra triangle behaves the
same way, write tests.

**Total**: 5-9 prompts. This is a well-scoped, single-mechanism fix
with clear success criteria.

## 6. Dependencies

**Required before starting**:
- CV1 APU trace file (`extraction/traces/cv1/vampire_killer.csv`) --
  already exists and is the validation reference.
- Understanding of the NES APU frame counter modes -- documented in
  nesdev wiki, well-understood hardware behavior.

**No code dependencies outside frame_ir.py**: The change is isolated
to the triangle branch of `parser_to_frame_ir()`. It does not touch
pulse envelope logic, parser code, MIDI export, or rendering.

**No dependency on Contra work**: This uses the CV1 trace for
validation. Contra validation is a separate effort (pending trace
capture).

## 7. Risks

**Risk 1: Sequencer phase varies per note or per track.**
If the driver resets the APU frame counter ($4017 write) at song
start or at specific points, the phase may not be a single constant.
Mitigation: dump 20+ notes from trace, check whether a single phase
value explains all of them. If not, look for $4017 writes in the
trace.

**Risk 2: Mesen trace granularity.**
The trace captures register values once per video frame. If the
driver writes $4008 multiple times within a single frame (unlikely
but possible), the trace may not capture the intermediate state.
Mitigation: use Mesen's instruction-level trace if frame-level
trace is insufficient.

**Risk 3: The approximation is actually good enough.**
195 mismatches across 1792 frames is a 10.9% error rate on triangle
sounding state, but the audible impact is minimal (each error is
1 frame = 16.7ms). The effort may not produce a perceptible audio
improvement. Mitigation: this is a correctness and completeness
goal, not an audibility goal. The value is in achieving zero
mismatches across all channels, which validates the model.

**Risk 4: Over-engineering.**
The precise model adds state tracking (sequencer phase) that the
approximate formula avoids. If future games have different APU frame
counter configurations (mode 1 vs mode 0, PAL timing), the model
needs to handle those variants. Mitigation: parameterize the
quarter-frame tick table so mode and region can be swapped.

## 8. Success Criteria

| Criterion | Target |
|-----------|--------|
| Triangle sounding mismatches (CV1 Vampire Killer, 1792 frames) | 0 |
| Pulse pitch mismatches (regression check) | 0 |
| Pulse volume mismatches (regression check) | 0 |
| INV-007 status | Promoted from APPROXIMATE to VERIFIED |
| frame_ir.py STATUS block | Updated to reflect 0 triangle mismatches |
| New invariant test passes | `test_triangle_linear_counter_precise` green |

The single definitive gate: running `PYTHONPATH=. python scripts/trace_compare.py --frames 1792`
produces zero mismatches on all three melodic channels.

## 9. Priority Ranking

**Priority: LOW-MEDIUM**

Rationale:
- **Not blocking any workflow.** CV1 is complete (15/15 tracks
  extracted, MIDI/REAPER/WAV/MP4 all delivered). The 195 mismatches
  do not affect any output artifact in a user-perceptible way.
- **Not blocking Contra.** Contra validation depends on a Contra
  APU trace capture, not on triangle precision.
- **Pure correctness improvement.** The value is intellectual
  completeness -- proving the extraction matches hardware on every
  frame of every channel. This matters for the project's credibility
  as a reverse engineering reference, but does not unblock any
  practical deliverable.
- **Well-scoped and low-risk.** When the time comes, this is a
  clean 5-9 prompt task with no architectural changes. It can be
  picked up at any point without disrupting other work.

Recommended timing: after Contra volume envelope validation is
complete (the current priority), and before tackling new games
(Super C, CV3). A clean zero-mismatch baseline on CV1 makes a
strong foundation before scaling to additional drivers.
