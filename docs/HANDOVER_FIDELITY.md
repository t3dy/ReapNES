# Handover: Fidelity Iteration on Vampire Killer

## Status: ZERO PITCH MISMATCHES — Full Song

The extraction pipeline now produces **zero pitch errors** across all three
channels for the entire 1792-frame Vampire Killer song, verified frame-by-frame
against the emulator APU trace.

## What Was Fixed This Session

### Fix 1: FE Repeat Count Semantics
The driver's repeat counter at `$06,x` starts at 0 and increments before
comparing to the count byte. `count=2` means 2 total passes (1 loop-back),
not 3. The parser was doing `count-1` loop-backs from first encounter;
correct is `count-2` (since we already completed pass 1 before hitting FE,
and count includes all passes).

**Evidence**: The B section started at the repeat target ($1E2E) instead of
the post-FE position ($1E66), causing all three channels to drift at ~frame 896.
After the fix, the parser reads from $1E66 which parses correctly as
D7 C1 E2 EA 11... = DX + instrument + octave + drum + C# note, matching trace.

### Fix 2: Envelope Model
`fade_start` = number of volume decrements (not a delay). Decay starts at
frame 1 after note onset, decrements by 1 per frame for exactly `fade_start`
frames, then holds at (initial_vol - fade_start).

**Evidence**: Trace shows instrument $F4 (vol=4, fade=4/1) decaying
4→3→2→1→0 across frames 0-4. Instrument $F3 (vol=3, fade=1/0) decaying
3→2 at frame 1 then holding.

### Fix 3: State Divergence Analysis
The key insight (from user): the $D7 byte at the B section wasn't a format
ambiguity — it was a **state context** problem. The parser was in the wrong
interpreter state because the repeat count was wrong, causing it to read
bytes from the wrong position. The same bytes parse correctly from the right
position with the right state.

## Current Mismatch Summary (Full Song)

```
pulse1:   pitch=0  vol=687  sounding=373  mismatches
pulse2:   pitch=0  vol=1728 sounding=546  mismatches
triangle: pitch=0  vol=742  sounding=742  mismatches
```

All remaining mismatches are **volume and sounding-state** — the envelope
tails are not perfectly modeled yet. No pitch errors remain.

## What's Still Not Right

### 1. Pulse Envelope Tail Behavior
The frame IR models the initial attack-to-sustain decay correctly, but the
volume hold and final note-off don't match the trace perfectly. There may
be additional volume processing (the `fade_step` parameter is still not
fully understood). Volume mismatches = ~687 frames on Sq1.

### 2. Pulse 2 Volume Mismatches (1728 frames)
Pulse 2 has significantly more volume mismatches than Pulse 1. This suggests
a different instrument/envelope configuration that our model doesn't handle.
Need to examine which Sq2 instruments are causing the most mismatches.

### 3. Triangle Sounding-State (742 frames)
Triangle has 0 pitch errors but 742 sounding-state mismatches. The triangle
channel has no volume control but does have a linear counter that gates
note duration. Our IR doesn't model the linear counter — it treats triangle
notes as sounding for their full duration. The real driver uses the linear
counter to create note-off before duration expires.

### 4. MIDI Export Still Uses Old Event Model
The MIDI export hasn't been rebuilt to use the frame IR. Notes still play
at constant volume for their full duration in MIDI output. Rebuilding the
export from the frame IR would give proper staccato articulation.

## Files

| File | State |
|------|-------|
| `extraction/drivers/konami/parser.py` | Updated: correct repeat count, corrected base MIDI |
| `extraction/drivers/konami/frame_ir.py` | Updated: correct envelope model |
| `extraction/drivers/konami/midi_export.py` | Needs rebuild from frame IR |
| `scripts/trace_compare.py` | Working: produces frame-level diff reports |
| `studio/jsfx/ReapNES_APU.jsfx` | Updated: CC11/CC12 support |
| `docs/TraceComparison_CV1.md` | Generated: current mismatch report |
| `data/trace_diff_cv1.json` | Generated: machine-readable diff |

## How To Run

```bash
# Trace comparison (full song)
cd C:/Dev/NESMusicStudio
PYTHONPATH=. python scripts/trace_compare.py --frames 1792

# Parse and show events
PYTHONPATH=. python extraction/drivers/konami/parser.py \
  "extraction/roms/Castlevania (U) (V1.0) [!].nes" 2

# Export MIDI (needs PYTHONPATH=. for correct imports)
PYTHONPATH=. python -c "
from extraction.drivers.konami.parser import KonamiCV1Parser
from extraction.drivers.konami.midi_export import export_to_midi
parser = KonamiCV1Parser('extraction/roms/Castlevania (U) (V1.0) [!].nes')
song = parser.parse_track(2)
export_to_midi(song, 'output.mid', song_name='Vampire Killer')
"
```

## Next Steps (Priority Order)

1. **Rebuild MIDI export from frame IR** — convert the per-frame volume states
   into proper MIDI note-on/off with shortened durations for decaying notes.
   This is the #1 user-facing improvement: staccato articulation.

2. **Investigate Pulse 2 volume model** — examine which instruments on Sq2 have
   the most mismatches. The `fade_step` parameter may control decay speed
   differently for some instruments.

3. **Model triangle linear counter** — the triangle's note-off timing is
   controlled by the APU linear counter, not just the duration counter. Need
   to read the $4008 linear counter values from the trace to understand the
   gate behavior.

4. **Regenerate REAPER project** with corrected MIDI from frame IR.

5. **Validate all other tracks** — run the parser on all 15 CV1 tracks and
   check for parsing errors or crashes.

## Key Methodology Rules

- **APU trace is ground truth.** Always run `trace_compare.py` after changes.
- **Time model is frames.** Only convert to MIDI at the final export step.
- **The driver is a stateful interpreter.** Same byte means different things
  depending on execution context. Don't reason about bytes in isolation.
- **State misalignment, not byte misalignment.** When pitch drifts after a
  control flow point, the issue is interpreter state, not data pointer offset.
