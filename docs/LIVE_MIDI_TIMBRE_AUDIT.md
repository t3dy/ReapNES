# Live MIDI Timbre Audit

Engineering report: why live keyboard input sounded different from MIDI
file playback through ReapNES_APU.jsfx, and what was done to fix it.

## Symptom

- MIDI file playback through ReapNES_APU.jsfx: correct NES timbre (duty
  cycle variations, volume shaping, characteristic chip sound)
- Live MIDI keyboard through same plugin: generic 50% pulse tone, flat
  volume, no NES character

## Root Cause

**The ROM-derived timbre is not a static patch. It is encoded as MIDI CC
automation in the file stream.**

The ROM-to-MIDI pipeline (`nsf_to_reaper.py`, `midi_export.py`) embeds
per-frame CC messages in every MIDI file:

| CC | Purpose | Values |
|----|---------|--------|
| CC12 | Duty cycle (NES timbre) | 0=12.5%, 1=25%, 2=50%, 3=75% |
| CC11 | Expression/volume | 0-127, maps to NES 4-bit volume |

When REAPER plays a MIDI item, these CCs flow through `midirecv()` in
the plugin's `@block`, driving duty and volume frame-by-frame. The
plugin is acting as a raw register-level APU emulator -- it has no
concept of "instruments" or "patches" -- the MIDI stream IS the patch.

A live keyboard sends only note-on/off and velocity. No CC12 (duty
stays at slider default = 50%), no CC11 (volume stays at velocity-derived
flat level). The result is a plain 50% square wave with no articulation.

## Divergence Map

```
MIDI File Playback          Live Keyboard Input
------------------          -------------------
CC12 -> duty cycle          (none) -> slider1 default (50%)
CC11 -> volume envelope     (none) -> velocity flat
note-on -> freq + vel       note-on -> freq + vel
Channels 0-3 correct        Channel depends on keyboard config
```

## What Was Changed

### 1. Live Patch System (ReapNES_APU.jsfx)

Added a **Live Patch** system that provides NES-authentic behavior on
note-on when the channel has NOT received CC automation:

- **slider14**: Live Patch mode
  - `Off` (0): original behavior, no envelope, for MIDI file playback
  - `NES Sustain` (1): hold at peak volume while key held, decay on release
  - `NES Decay` (2): auto-decay after ~200ms sustain (like NES hardware)
- **slider15**: Debug overlay toggle

**Key design: CC-override detection.** Each channel tracks whether CC11
or CC12 has been received (`lp_cc_active[ch]`). When a MIDI file plays,
CC events arrive before/during notes, marking the channel as CC-driven.
The Live Patch envelope is bypassed for CC-driven channels, so existing
MIDI file playback is completely unchanged.

CC123 (all notes off) and CC121 (reset all controllers) clear the
CC-active flags, resetting to live mode.

### 2. Per-Note Envelope

On note-on in live mode:
- Duty cycle is applied from the slider (user's chosen timbre)
- Volume envelope triggers: instant attack -> sustain -> decay
- Volume envelope runs per-sample in `@sample`, updating `p1_vol`/`p2_vol`
- Note-off triggers release -> decay to zero

Envelope timing (at any sample rate):
- Attack: instant (1 sample)
- Sustain: ~200ms hold at peak
- Decay: ~300ms linear ramp to 0

### 3. Debug Overlay

When slider15=On, the GFX panel shows:
- MIDI event counters (NoteOn, CC11, CC12, LiveEnv triggers)
- Per-channel source indicator (LIVE / CC / --)
- CC-active flags per channel
- Envelope phase per channel (ATK/SUS/DEC/OFF)
- Current duty and volume values
- Live envelope volume (fractional)

### 4. Bugfixes in Other Plugins

- `ReapNES_Instrument.jsfx`: Fixed `//tags:instrument` -> `tags:instrument`
  (was commented out, REAPER wouldn't route MIDI to it)
- `ReapNES_Pulse.jsfx`: Same fix

### 5. Project Generator Update

Updated `FULL_APU_DEFAULTS` in `generate_project.py` to include slider14=0
and slider15=0 in generated projects. MIDI file projects explicitly disable
Live Patch since they carry their own CC automation.

## Files Changed

| File | Change |
|------|--------|
| `studio/jsfx/ReapNES_APU.jsfx` | Live Patch system, debug overlay |
| `studio/jsfx/ReapNES_Instrument.jsfx` | Fixed commented-out tags directive |
| `studio/jsfx/ReapNES_Pulse.jsfx` | Fixed commented-out tags directive |
| `scripts/generate_project.py` | Updated slider defaults for slider14/15 |
| `tests/test_live_patch.py` | 24 regression tests (new file) |
| `docs/LIVE_MIDI_TIMBRE_AUDIT.md` | This report |

## Tests Added

`tests/test_live_patch.py` -- 24 tests across 8 test classes:

- **TestLivePatchStructure** (7): slider14/15 exist, state arrays init,
  trigger/release/process functions present
- **TestCCDrivenDetection** (4): CC11/CC12 set cc_active, CC123/121 reset it
- **TestNoteOnPath** (3): note-on checks lp_active, triggers envelope,
  sets duty from slider in live mode
- **TestEnvelopeProcessing** (3): @sample gates on slider14, checks cc_active
  per channel, applies volume to pulse
- **TestDebugOverlay** (3): shows CC counts, source indicators, env phase
- **TestPlaybackPreservation** (3): CC11/CC12 still set volume/duty, drums
  unchanged
- **TestMemorySafety** (1): no memory region overlaps between Live Patch
  and existing state

## Repro Steps

To verify the fix:

1. Open REAPER, load ReapNES_APU.jsfx on a track
2. Set Channel Mode to "Full APU" or "Pulse 1 Only"
3. Set Live Patch to "NES Sustain" or "NES Decay"
4. Play notes from MIDI keyboard -- should hear duty-cycle-shaped pulse
   with volume envelope, not flat 50% square wave
5. Load a ROM-ripped MIDI file on the same track and play -- should
   sound exactly as before (CC automation overrides Live Patch)
6. Enable Debug Overlay to see source indicators: "LIVE" for keyboard,
   "CC" for file playback

## Remaining Risks

1. **Envelope timing is fixed.** The 200ms sustain / 300ms decay is a
   reasonable NES approximation but not game-specific. For per-game
   fidelity, the user should use ReapNES_Instrument.jsfx with preset
   files (now that its tags: directive is fixed).

2. **CC-active is sticky per session.** If a MIDI file plays CC11/CC12
   on a channel, that channel stays CC-driven until CC123/CC121 or
   transport stop sends a reset. This is correct behavior (prevents
   mid-sequence glitches) but could confuse users who play a file then
   switch to live without stopping.

3. **No per-note duty variation in live mode.** MIDI keyboard sends no
   CC12, so all notes get the same duty cycle from the slider. For duty
   variation, use mod wheel (CC1 already mapped to duty) or connect a
   controller that sends CC12.

## Product Definition Clarification

This audit reveals that ReapNES_APU.jsfx occupies a hybrid position:

| Capability | Status |
|------------|--------|
| ROM sequence playback | Working (CC automation drives everything) |
| Playable NES instrument | Now working (Live Patch + slider duty) |
| Strict driver-faithful emulator | Not applicable (this is a synth, not an emulator) |

For users who want extracted-instrument fidelity from a keyboard,
`ReapNES_Instrument.jsfx` with .reapnes-data preset files is the
intended path. The Live Patch in ReapNES_APU.jsfx provides a
reasonable approximation without requiring external preset files.

## Recommended Next Steps

1. **Expose CC-active reset in UI.** Add a "Reset Live" button or make
   transport stop auto-clear CC-active flags via REAPER's play_state
   variable.

2. **Per-game Live Patches.** Add slider presets that set duty and
   envelope timing to match specific game characteristics (Castlevania
   25% duty fast decay, Mega Man 50% duty longer sustain, etc.).

3. **Mod wheel polish.** The CC1 -> duty mapping already works but is
   coarse (floor(msg3/32)). Consider smoother mapping or CC12 pass-through
   from controllers that send it.

4. **ReapNES_Instrument.jsfx activation.** Now that its tags: is fixed,
   it can receive MIDI and use .reapnes-data presets for per-note envelope
   playback from a keyboard. Needs a test REAPER project demonstrating
   keyboard-to-preset workflow.
