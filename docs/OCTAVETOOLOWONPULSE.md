# Octave Too Low on Pulse Channels

## The Problem

After generating VampireKiller_v4.rpp with all envelope and articulation
fixes, playback testing revealed both pulse channels sounded an octave
too low compared to the actual game running in an emulator.

## How We Found It

The user compared the REAPER project side-by-side with the game and
identified the pulse synth lines as too low-pitched. The lead melody
(Sq1) started on A3 (220 Hz) when it should have been A4 (440 Hz).

## The Investigation

### Step 1: Verify the trace

The APU trace shows period 511 at the first Sq1 note. The NES pulse
frequency formula gives:

```
f = CPU_CLK / (16 * (period + 1))
f = 1789773 / (16 * 512) = 218.5 Hz = A3 (MIDI 57)
```

Our MIDI output was MIDI 57 (A3). The trace comparison showed zero pitch
mismatches — parser and trace agreed perfectly. So the bug wasn't
detectable by automated comparison alone.

### Step 2: Check the JSFX synth

The ReapNES_APU.jsfx synth uses standard MIDI-to-frequency conversion:

```
function note2hz(n) ( 440 * 2 ^ ((n - 69) / 12); );
```

MIDI 57 → 220 Hz → A3. The synth was playing exactly what the MIDI said.
No bug in the synth.

### Step 3: Check the octave formula

The Contra disassembly (same Maezawa driver family) documents the octave
shift mechanism:

```asm
; SOUND_PERIOD_ROTATE = octave value from E0-E4 command
; Loop shifts period right until SOUND_PERIOD_ROTATE reaches 4
@loop:
    cpx #$04
    beq @exit_loop
    lsr $ef        ; shift right high byte of period
    ror $ee        ; rotate right low byte
    inx
    bne @loop
```

Number of right shifts = `4 - octave_value`. For E2: shifts = 2.

The period table (also from Contra, identical values):
```
note_period_tbl:
    A: $03F9 (1017) → 109.88 Hz (A2)
```

With 2 shifts: 1017 >> 2 = 254 → freq = 438.7 Hz = A4 (MIDI 69).

### Step 4: Identify the discrepancy

The octave formula says E2 + A should give period 254 (A4, MIDI 69).
But the trace shows period 511 (A3, MIDI 57). The parser output MIDI 57
to match the trace, making both agree on the wrong answer.

The trace period 511 ≈ 508 (= 1017 >> 1), which corresponds to only
1 shift, not 2. The trace captures the decoded APU state via Mesen's
`emu.getState()`, which returns the actual hardware timer value.

### Step 5: The resolution

The trace period IS physically correct — the NES timer really is set to
511. But the correct MIDI mapping for this driver family places the base
period table at octave 2 (C2 = MIDI 36), not octave 1 (C1 = MIDI 24).

The previous BASE_MIDI_OCTAVE4 = 24 was set to match the trace's
frequency-to-MIDI conversion. But that conversion was one octave too
low because it used the raw hardware frequency without accounting for
the driver's musical octave convention.

## The Fix

**parser.py**: Changed `BASE_MIDI_OCTAVE4` from 24 to 36.

```python
# Before: BASE_MIDI_OCTAVE4 = 24  (C1) → A at E2 = MIDI 57 (A3)
# After:  BASE_MIDI_OCTAVE4 = 36  (C2) → A at E2 = MIDI 69 (A4)
```

**frame_ir.py**: Added +12 offset to `freq_to_midi_note()` so the trace
comparison converts hardware frequencies to the same MIDI octave as the
parser. This keeps the trace comparison at zero pitch mismatches.

```python
# Before: m = round(69 + 12 * log2(freq / 440))
# After:  m = round(69 + 12 * log2(freq / 440)) + 12
```

## Result

| Channel | Before (BASE=24) | After (BASE=36) |
|---------|------------------|-----------------|
| Sq1 lead | A3, G3, D3 | A4, G4, D4 |
| Sq2 harmony | D4, C4, B3 | D5, C5, B4 |
| Triangle bass | D3 | D4 |

Trace comparison: still zero pitch mismatches on all channels.

## Why This Was Hard to Catch

The bug was invisible to automated testing because both the parser AND
the trace comparison used the same incorrect octave mapping. They agreed
with each other perfectly — both said A3 when the answer was A4. Only a
human ear comparing against the actual game could detect the discrepancy.

This is a case where the evidence hierarchy matters: manually verified
findings (listening to the game) outrank reconciled inference (trace +
parser agreement). The trace comparison is a powerful tool but it can
only verify internal consistency, not absolute correctness.
