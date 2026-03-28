# Handover: Fidelity Iteration on Vampire Killer

## Session Summary

Built frame-accurate IR and trace comparison infrastructure. Made significant
progress on fidelity — first 400 frames (A section x2) now have **zero pitch
mismatches** against the emulator APU trace. Identified the remaining bugs
causing drift in the B section.

## Current State

### What's Working
- Frame IR module (`extraction/drivers/konami/frame_ir.py`) converts parser
  output to per-frame states with proper envelope decay
- Trace comparison tool (`scripts/trace_compare.py`) generates frame-by-frame
  diff reports between our extraction and the emulator trace
- Envelope model corrected: `fade_start` = number of volume decrements (not
  a delay), decay starts at frame 1, vol decrements by 1 per frame
- First 400 frames of Vampire Killer: 0 pitch errors across all channels
- JSFX synth now responds to CC11 (volume) and CC12 (duty cycle)

### What's Broken (Identified, Not Yet Fixed)

**Bug 1: FE repeat count semantics (HIGH PRIORITY)**
At `extraction/drivers/konami/parser.py` line 398-415, the FE repeat handler
sets `repeat_counters[offset] = count - 1` on first encounter. For count=2,
this means: initial play + 2 replays = 3 total plays. But the real driver
likely means "play 2 times total" (initial + 1 replay).

Evidence: The B section of Vampire Killer starts at frame ~896 with a byte
misalignment. All three channels drift at this same point. The FE repeat
at ROM $1E62 has count=2, targeting ROM $1E2E. If Section A plays 3 times
instead of 2, the B section starts at the wrong frame.

Fix: Change line 402 from `count - 1` to `count - 2` (already played through
once before hitting FE, and count includes the initial play). Then verify
against the trace.

After this fix, also check: does the code after the FE (at ROM $1E66)
correctly parse the B section? Bytes there are `$D7 $C1 $E2 $EA $11 ...`
which would be: DX tempo=7, instrument=$C1, octave E2, drum, note C#...
That would give C#3 which MATCHES the trace.

**Bug 2: Post-FE byte alignment**
Even after fixing the repeat count, need to verify that the byte stream
after the FE repeat parses correctly. The B section data at $1E66 starts
with D7 C1 which should be a DX+instrument. Instrument $C1 = 0b11000001
= duty 3, halt 0, const 0, vol 1. For triangle (no fade byte), next is
E2 (octave 2), EA (drum), $11 = C# dur 1. If alignment is correct after
the repeat fix, these should parse to the right notes.

**Bug 3: fade_step meaning unclear**
The fade_step parameter (low nibble of the fade byte) is extracted but
not used in the frame IR. For instruments with fade_step=1, decay is
1-per-frame (same as step=0). For step=9, step=2, etc., the behavior
is unknown. Possibly: step=0 means 1-per-frame, step>0 means slower
decay (skip frames between decrements). Needs trace verification with
an instrument that has step>1.

**Bug 4: MIDI export doesn't use frame IR**
The MIDI export still uses the old event-based conversion. It should
be rebuilt to convert from the frame IR, which has correct envelope
shapes. This would give proper staccato articulation.

## Files Changed This Session

| File | What |
|------|------|
| `extraction/drivers/konami/frame_ir.py` | NEW: Frame-accurate IR with envelope model |
| `scripts/trace_compare.py` | NEW: Frame-by-frame trace comparison tool |
| `docs/FidelityAudit_CV1.md` | NEW: Audit of all fidelity risks |
| `docs/TraceComparison_CV1.md` | NEW: Generated comparison report |
| `data/trace_diff_cv1.json` | NEW: Machine-readable diff |
| `extraction/drivers/konami/parser.py` | Updated: octave fix, repeat handling |
| `extraction/drivers/konami/midi_export.py` | Updated: volume dynamics, CC11/CC12 |
| `studio/jsfx/ReapNES_APU.jsfx` | Updated: CC11/CC12 support |
| `docs/HANDOVER_FIDELITY.md` | This file |

## How To Run

```bash
# Parse Vampire Killer from ROM
PYTHONPATH=. python extraction/drivers/konami/parser.py \
  "extraction/roms/Castlevania (U) (V1.0) [!].nes" 2

# Run trace comparison (first 400 frames)
PYTHONPATH=. python scripts/trace_compare.py --frames 400

# Run full song comparison (2016 frames)
PYTHONPATH=. python scripts/trace_compare.py --frames 2016

# Export MIDI
PYTHONPATH=. python -c "
from extraction.drivers.konami.parser import KonamiCV1Parser
from extraction.drivers.konami.midi_export import export_to_midi
parser = KonamiCV1Parser('extraction/roms/Castlevania (U) (V1.0) [!].nes')
song = parser.parse_track(2)
export_to_midi(song, 'output.mid', song_name='Vampire Killer')
"

# Validate
python scripts/validate.py --all
```

## Next Steps (Priority Order)

1. **Fix FE repeat count** — change `count - 1` to `count - 2` in parser.py
   line 402. Run trace comparison to verify B section alignment.

2. **Verify B section byte parsing** — after repeat fix, check that bytes
   at $1E66 (D7 C1 E2 EA 11...) parse correctly as DX+instrument+notes.

3. **Rebuild MIDI export from frame IR** — the MIDI should be generated from
   the frame IR (which has correct envelope shapes) rather than from the raw
   event list. This gives proper staccato articulation for notes that decay
   to silence before their full duration.

4. **Investigate fade_step behavior** — find a note in the trace where
   fade_step > 1 and verify whether it slows the decay rate.

5. **Regenerate REAPER project** with corrected MIDI and test playback.

## Key Insight From This Session

The driver is a **stateful frame-based interpreter**, not a simple data format.
The frame IR approach (expanding every note into per-frame volume states) is
the correct model. The trace comparison tool proves it: the first 400 frames
match at frame accuracy when the envelope model is right.

The remaining errors are structural (repeat count semantics causing byte
misalignment in the B section), not pitch or timing formula errors.
