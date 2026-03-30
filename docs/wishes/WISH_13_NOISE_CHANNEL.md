# WISH #13: Noise Channel Modeling

## 1. What This Wish Is

Replace the single generic white-noise synthesizer in `render_wav.py`
with a proper NES noise channel model that respects the hardware's 16
rate presets and 2 LFSR modes. Currently every drum hit -- kick, snare,
hi-hat -- passes through the same `render_noise_hit()` function, which
generates uniform random samples with an optional low-pass filter and
exponential decay. The real NES noise channel ($400C-$400F) produces
distinctly different timbres depending on the period index ($400E bits
0-3) and the mode flag ($400E bit 7).

## 2. Why It Matters

**Timbral accuracy.** The NES noise channel is not white noise. Its
15-bit LFSR in long mode (mode 0) produces pseudo-random noise with a
specific spectral character at each of 16 fixed rates. In short mode
(mode 1), the LFSR uses a 93-step loop that creates a metallic, tonal
buzz -- a completely different sound from mode 0. These differences are
clearly audible in game audio and define the character of NES percussion.

**Per-drum-type differentiation.** The CHECKLIST.md documents that
Contra's Jungle theme uses only 2 noise period values (7 and 31) across
all drum hits. Period 7 produces a mid-frequency hiss (snare character),
while period 31 produces a low rumble (kick character). Our current
renderer ignores this distinction entirely -- it differentiates drums
only through volume, decay rate, and a crude low-pass filter.

**Foundation for DPCM.** Accurate noise modeling is a prerequisite for
the hybrid noise+DPCM layering that Contra uses for compound hits
(kick_snare, kick_hihat). Without correct noise timbre, the noise
component of these layered hits will mask or clash with future DPCM
sample playback rather than complementing it.

**Renderer credibility.** The CHECKLIST.md priority list ranks "Noise
period values" at #4 and "DMC sample extraction" at #5. This wish
addresses #4 directly and enables #5.

## 3. Current State

### What exists

- `render_noise_hit()` in `render_wav.py` (lines 98-113): takes
  volume, decay rate, and an optional low-pass coefficient. Generates
  `np.random.uniform(-1, 1)` samples -- true white noise, not
  LFSR-based. Differentiates kick from snare/hihat only by decay speed
  and the low-pass filter coefficient.

- `render_song()` in `render_wav.py` (lines 149-188): dispatches drum
  types to `render_noise_hit()` with hardcoded parameters per type
  (kick: vol=0.8 decay=20 lowpass=0.7; snare: vol=0.6 decay=10;
  hihat: vol=0.3 decay=25). No noise period or mode data flows from
  the parser to the renderer.

- The parser emits `DrumEvent` objects with a `drum_type` string
  ("kick", "snare", "hihat", etc.) but no hardware register values.

- The frame IR explicitly skips noise: `if ch_type == "noise": continue`.
  Drums bypass the frame IR and go directly from parser to MIDI/WAV.

### What is missing

- No LFSR implementation (neither 15-bit long mode nor 93-step short
  mode).
- No noise period table (the 16 hardware rate presets that determine
  the LFSR clock divider).
- No per-hit noise register values ($400E period and mode) extracted
  from ROM or trace.
- No data path from parser DrumEvent to renderer that carries hardware
  parameters.

### Trace evidence

CHECKLIST.md reports:
- $400E_period: only 2 values observed in Contra Jungle (7 and 31)
- $400E_mode: always 0 (long loop) in Jungle
- $400C_vol: noise volume spikes correlate with kick drum hits
- 283 DMC DAC ($4011) changes in first 1000 frames (separate from
  noise, relevant to future DPCM work)

## 4. Concrete Steps

### Step 1: Implement NES LFSR noise generator

Write `NESNoiseGenerator` class in `render_wav.py` with:
- 15-bit LFSR state register (initial value 1)
- Long mode (mode 0): feedback = bit 0 XOR bit 1, shift right, insert
  feedback at bit 14
- Short mode (mode 1): feedback = bit 0 XOR bit 6, same shift
- Output: bit 0 of shift register (0 = silence, 1 = output volume)
- NTSC period lookup table (16 entries):
  `[4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016,
  2034, 4068]` -- these are CPU clock dividers

The generator should accept period_index (0-15) and mode (0 or 1),
and produce audio samples at 44100 Hz by stepping the LFSR at the
correct rate derived from CPU_CLK / period_value.

### Step 2: Extract per-drum noise parameters from trace data

Run `trace_compare.py --dump-frames` and extract $400E writes for each
drum hit type. Build a mapping table:

```
CV1:
  E9 (snare) -> period=?, mode=?
  EA (hihat) -> period=?, mode=?

Contra:
  sound_02 (kick)     -> period=?, mode=?
  sound_5a (hihat)    -> period=?, mode=?
  sound_5b (snare)    -> period=?, mode=?
```

Alternatively, read these directly from the disassembly where the
sound routines write to $400E.

### Step 3: Extend DrumEvent with hardware parameters

Add optional fields to `DrumEvent`:
- `noise_period`: int (0-15), default None
- `noise_mode`: int (0 or 1), default None
- `noise_volume`: int (0-15), default None

Parser populates these from ROM data or from a per-game config table
in the manifest. When None, the renderer falls back to current behavior.

### Step 4: Replace render_noise_hit with LFSR-based rendering

When `DrumEvent` carries hardware parameters, use the LFSR generator
with the specified period and mode. Apply the volume envelope from
$400C (either hardware decay or per-frame values from the sound
routine). When parameters are missing, fall back to current
`np.random.uniform` approach for backward compatibility.

### Step 5: Validate against trace

Compare rendered noise waveform spectral characteristics against Mesen
APU audio output. The LFSR is deterministic -- given the same initial
state and period, the output sequence is identical. Verify that the
rendered kick and snare have distinct spectral profiles matching the
game.

### Step 6: Update JSFX synth (optional)

Extend `ReapNES_APU.jsfx` to accept noise period and mode as
parameters, enabling accurate noise in REAPER renders as well.

## 5. Estimated Effort

| Step | Effort | Notes |
|------|--------|-------|
| LFSR generator | 2 hours | Well-documented algorithm, ~40 lines |
| Trace extraction | 1-2 hours | Depends on trace tooling; may need trace_compare.py changes |
| DrumEvent extension | 1 hour | Small data model change, parser updates |
| Renderer integration | 2 hours | Replace render_noise_hit, handle fallback |
| Validation | 1-2 hours | Spectral comparison, listening test |
| JSFX update | 2-3 hours | Optional; JSFX DSP is fiddly |

**Total: 7-10 hours** without JSFX, 9-13 hours with JSFX.

This is a small, self-contained change. The LFSR algorithm is
deterministic and well-understood. The main unknown is extracting the
exact per-drum $400E values from each game's sound routines.

## 6. Dependencies

**Hard dependencies (must exist before starting):**
- None. All required infrastructure exists. The parser, frame IR, and
  renderer are in place. This wish extends existing data paths.

**Soft dependencies (improve outcome but not blocking):**
- Access to Mesen APU trace with $400C-$400F register values for
  validation. The trace_compare.py script currently focuses on
  $4000-$400B (pulse and triangle). Extending it to capture noise
  registers would strengthen validation.
- Annotated disassembly for the target game's sound routines. Available
  for Contra (`references/nes-contra-us/`). CV1 disassembly status
  unclear but E9/EA routines are small.

**Downstream dependents (things that benefit from this wish):**
- DPCM sample extraction (CHECKLIST #5) -- accurate noise is half of
  Contra's hybrid drum sound.
- JSFX synth improvements -- needs noise parameters to render correctly.
- Any new game extraction -- all NES games use the noise channel.

## 7. Risks

**Risk 1: LFSR clock rate precision.**
The LFSR steps at CPU_CLK / period_value. At 44100 Hz output sample
rate, some period values produce non-integer step ratios. A naive
implementation that steps the LFSR once per output sample will produce
the wrong frequency. The implementation must accumulate fractional
steps (similar to how pulse/triangle rendering handles phase).
*Mitigation*: Use the same phase-accumulator pattern already proven in
`render_pulse_frame()`.

**Risk 2: Per-game parameter extraction.**
Different games write different values to $400E for their drum sounds.
Hardcoding Contra's values will not work for CV1 or future games.
*Mitigation*: Store noise parameters in the per-game manifest JSON.
Use trace extraction or disassembly reading per the standard workflow.

**Risk 3: Scope creep into DPCM.**
Accurate noise modeling reveals how much the current drums are missing
without DPCM samples. The temptation to also implement DPCM decoding
in the same pass is strong.
*Mitigation*: Strictly scope this wish to noise channel only. DPCM is
a separate wish. The LFSR generator and DPCM decoder are independent
subsystems.

**Risk 4: Volume envelope complexity.**
The noise channel has its own volume envelope (hardware decay via $400C
or software-driven per-frame writes). Modeling this correctly requires
understanding each game's noise volume routine, which varies by driver.
*Mitigation*: Start with a simple exponential decay approximation (as
currently exists), then refine per-game using trace data. The timbre
improvement from correct LFSR + period is larger than the improvement
from exact volume envelopes.

## 8. Success Criteria

1. **Distinct timbres per period.** Rendering the same drum hit with
   period 7 vs period 31 produces audibly and spectrally different
   output. A frequency-domain plot shows the expected spectral shift.

2. **Mode 0 vs mode 1 differentiation.** Long-mode noise sounds like
   hiss/rumble. Short-mode noise sounds metallic/tonal. A listener can
   distinguish them without being told which is which.

3. **CV1 drum improvement.** Rendered CV1 Vampire Killer drums (E9
   snare, EA hi-hat) use the correct hardware period and mode values.
   Side-by-side listening against Mesen output shows improved similarity
   compared to the current generic white noise.

4. **Contra drum improvement.** Rendered Contra Jungle kick (period 31)
   and snare (period 7) match the timbral character of the game audio.
   The kick sounds low and thumpy, the snare sounds mid-range and crisp.

5. **No regression.** Games without extracted noise parameters fall back
   to current behavior. Existing WAV renders are unchanged unless the
   manifest provides noise register data.

6. **Trace-aligned timing.** Noise hit onsets in the rendered WAV align
   with $400C volume spikes in the APU trace to within 1 frame.

## 9. Priority Ranking

**Priority: MEDIUM-HIGH (4th in fidelity stack)**

Rationale from CHECKLIST.md priority ordering:
- Items 1-3 (EC pitch, volume envelopes, auto-decrescendo) are DONE.
- Item 4 is noise period values -- this wish.
- Item 5 is DMC sample extraction -- depends on this wish for the
  hybrid drum layering to sound correct.

This is the highest-priority remaining fidelity improvement for
percussion. It is lower priority than any pitch or volume work (those
affect all notes, not just drums), but higher priority than mid-note
duty changes (#6), mixer nonlinearity (#7), or vibrato (#8), which
are either rare or cosmetic.

The effort is small (7-10 hours), the risk is low (deterministic
algorithm, well-documented hardware), and the payoff is immediate
(every rendered WAV with drums sounds more authentic). This is a
good candidate for a focused single-session implementation.
