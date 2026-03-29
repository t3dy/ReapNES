# Version 4 Story: Vampire Killer Fidelity

## Starting Point (v3)

Version 3 had **zero pitch mismatches** across all 3 channels for the full
1792-frame song, verified against the emulator APU trace. But playback in
REAPER sounded wrong: too legato, too sustained, no staccato articulation.

The MIDI export used the old event-based model with constant-velocity notes
spanning full durations. The per-frame volume envelopes from the frame IR
were not being used.

Mismatch summary entering this session:
```
pulse1:   pitch=0  vol=495   sounding=181
pulse2:   pitch=0  vol=1518  sounding=336
triangle: pitch=0  vol=518   sounding=518
```

## What v4 Fixed

### Fix 1: Envelope Off-By-One

**Problem**: Volume at frame 4 of a note with vol=4, fade_start=4 showed
vol=1 in our IR but vol=0 in the trace.

**Root cause**: The volume decrement was applied AFTER writing the frame
state. The decrement should happen BEFORE writing, so the decremented value
is what gets recorded.

**Evidence**: Trace shows instrument $F4 (vol=4, fade=4/1): frame 4 = vol 0.
Our IR had vol=1 because we wrote the old value before decrementing.

**Files changed**: `extraction/drivers/konami/frame_ir.py`

### Fix 2: E8 Envelope Gate Removal

**Problem**: Sq2 had 1518 volume mismatches — the envelope wasn't being
applied at all.

**Root cause**: The `E8` (EnvelopeEnable) command was gating the fade system.
Sq2 has **zero** E8 commands in its data, so no fading was applied. But the
APU trace shows Sq2 notes clearly decaying.

**Discovery method**: Listed all EnvelopeEnable events per channel. Sq1 had 1,
Sq2 had 0. Removing the gate immediately dropped Sq2 vol mismatches from
1518 to 226.

**Conclusion**: E8 does NOT gate the driver's volume fade. Fading is always
active when fade_start > 0. The E8 command likely controls something else
(perhaps the hardware APU envelope mode vs constant volume mode).

**Files changed**: `extraction/drivers/konami/frame_ir.py`

### Fix 3: fade_step Decoded

**Problem**: Instruments with fade_step > 0 showed incorrect hold volumes at
the end of notes. The `fade_step` parameter was documented as "uncertain."

**Discovery method**: Extracted the actual trace volume values frame-by-frame
for specific notes and compared against different hypotheses.

**What we tried and failed**:
1. "fade_step = continued decay rate" — made things much worse (vol 185 -> 758)
2. "Force vol=0 on last frame" — wrong direction (trace shows vol=1 on some last frames)

**What worked**: Detailed trace analysis of instrument $B5 (vol=5, fade=2/3)
revealed the pattern:
```
frame 0: vol=5  (attack)
frame 1: vol=4  (phase 1 decay)
frame 2: vol=3  (phase 1 done — 2 decrements)
frame 3-10: vol=3  (hold)
frame 11: vol=2  (phase 2 release)
frame 12: vol=1
frame 13: vol=0
```

The last 3 frames have 3 decrements — matching fade_step=3.

**The rule**: fade_step = number of 1-per-frame volume decrements applied
at the END of the note (the release phase). fade_step=0 means hold forever.

**Verified across multiple instruments**:
- $B5 (fade=2/3): ...hold at 3...2->1->0 on last 3 frames
- $B4 (fade=3/1): ...hold at 1...0 on last 1 frame
- $F3 (fade=1/0): ...hold at 2 forever (no release)

**Files changed**: `extraction/drivers/konami/frame_ir.py`

### Fix 4: Triangle Linear Counter

**Problem**: Triangle had 518 sounding-state mismatches — notes played for
full duration when they should silence partway through.

**Root cause**: Triangle notes are gated by the APU linear counter ($4008),
not volume. Our trace comparison was also wrong — it treated any non-zero
period as "sounding" without checking the linear counter.

**Discovery method**: Checked the trace CSV for $4008_linear values during
rest periods. Found that $4008 reaches 0 during rests (confirming silence),
even though the period register retains the previous note's value.

**The model**: The triangle instrument byte IS the $4008 register value:
- Bit 7 = control (1 = sustain/reload continuously)
- Bits 6-0 = linear counter reload value
- Counter decrements ~4 times per NES frame (240Hz quarter-frame clocks)
- Triangle sounds for approximately `(reload + 3) / 4` frames

**Results**:
- Inst $10 (reload=16, control=0): triangle sounds ~4 of 14 frames
- Inst $C1 (reload=65, control=1): sounds full duration (sustain mode)

**Files changed**: `extraction/drivers/konami/frame_ir.py`, trace comparison
updated to check linear counter for triangle sounding state.

### Fix 5: MIDI Export Rebuilt from Frame IR

**Problem**: MIDI notes played at constant volume for full duration — too
legato/sustained compared to the staccato game audio.

**Solution**: Complete rewrite of `midi_export.py` to walk the frame IR
instead of raw parser events:

1. Notes shortened to actual sounding duration (note-off when vol hits 0)
2. CC11 (expression) volume automation emitted per-frame during decay
3. Proper silence gaps between adjacent notes
4. Triangle notes shortened per linear counter model

**Before**: Note on for 7 frames at velocity 34, constant
**After**: Note on for 4 frames, CC11: 34->25->17->8, then note-off + 3-frame gap

**Files changed**: `extraction/drivers/konami/midi_export.py` (complete rewrite)

## v4 Results

```
Before (v3):                    After (v4):
pulse1:   vol=495  snd=181      vol=45*  snd=9    (-91% / -95%)
pulse2:   vol=1518 snd=336      vol=50*  snd=10   (-97% / -97%)
triangle: vol=518  snd=518      vol=195* snd=8**  (-62% / -98%)

* Remaining vol mismatches are cosmetic (both sides vol=0)
** 8 real mismatches from linear counter approximation
```

Zero pitch mismatches maintained throughout all changes.

## Open Issue: Lead Pitch

**User report**: After testing v4 in REAPER, the lead synth (Sq1) sounds
too low — "maybe it's dropped an octave from what I hear in the game music."

**Investigation**:

The first Sq1 note has parser octave E2, pitch A. The trace shows APU period
511, which produces 218.5 Hz = A3 (MIDI 57).

The Contra disassembly (same driver family) confirms the octave formula:
`shifts = 4 - octave_value`. For E2: shifts = 2, giving period 254 = 438 Hz
= A4 (MIDI 69).

**The discrepancy**: The parser says E2 (should be A4 at period 254), but the
trace shows period 511 (which is A3, consistent with only 1 shift, i.e., E3).

Current BASE_MIDI_OCTAVE4 = 24 was set to match the trace (both agree on
MIDI 57 = A3). But the Contra-based octave formula says E2 should produce
A4 (MIDI 69, which needs BASE = 36).

**Possible explanations**:
1. The Castlevania driver's octave shift differs from Contra by 1
2. The Mesen trace period values may be pre-shift base values
3. The octave formula has an off-by-one specific to Castlevania's variant

**Status**: Under investigation. The MIDI data matches the APU trace
perfectly. If the game truly plays at A4, the issue may be in how the
trace captures or decodes the period values. A direct comparison with the
game running in an emulator would resolve this.

## Output Files

| File | Description |
|------|-------------|
| `output/vampire_killer_v4.mid` | Frame IR-based MIDI with staccato articulation |
| `studio/reaper_projects/VampireKiller_v4.rpp` | REAPER project ready to play |
| `extraction/drivers/konami/frame_ir.py` | Updated: two-phase envelope + triangle linear counter |
| `extraction/drivers/konami/midi_export.py` | Rebuilt: frame IR-based export with CC11 automation |
| `docs/HANDOVER_FIDELITY.md` | Updated: current state and methodology |
| `docs/LATESTFIXES.md` | Updated: all fix documentation |

## Methodology Notes

### What Worked
- **Frame-by-frame trace extraction** for specific notes to understand envelope
  shapes (not just aggregate mismatch counts)
- **Testing hypotheses against the trace** — the fade_step investigation tried
  3 different models before finding the right one
- **Checking per-channel differences** — discovering Sq2 had zero E8 commands
  was the key to the biggest improvement

### What Didn't Work
- Guessing that fade_step meant "continued decay rate" (made things worse)
- Forcing vol=0 on the last frame (correct direction but wrong magnitude)
- Reading the period table from ROM at $079A (got garbage — offset was wrong)

### Key Principle
Every fix was driven by trace evidence, not by reasoning about what bytes
"should" mean. The trace shows what the hardware actually does. When our
model disagreed with the trace, the model was always wrong.
