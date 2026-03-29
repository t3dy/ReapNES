# NES Music Studio — Session Handover (2026-03-28)

## What Happened This Session

Started with Contra at v4 (notes close, dynamics flat). Ended with:

- **Contra v8**: 11/11 tracks extracted with lookup-table volume envelopes,
  EC pitch adjustment, auto-decrescendo vol_duration, bounce-at-1,
  corrected percussion mapping. Trace-validated: 0 real pitch mismatches,
  96.6% volume match on Jungle.
- **CV1 pulse: 0/0/0**: Fixed phase2_start bug discovered via cross-game
  analysis. 45 volume mismatches eliminated. Both pulse channels now
  perfectly match the Mesen trace across 1792 frames.
- **Methodological refactor**: 7 structured docs, 17 invariant tests,
  status labels on all driver modules, architecture rules.
- **Swarm deployment**: 10 parallel agents wrote docs/tests/labels.
  8/10 completed, 2 gap-filled. Analysis in SWARMPERFORMED1.md.

## Current Fidelity

| Game | Channel | Pitch | Volume | Sounding |
|------|---------|-------|--------|----------|
| CV1 | Pulse 1 | 0 | 0 | 0 |
| CV1 | Pulse 2 | 0 | 0 | 0 |
| CV1 | Triangle | 0 | 195 | 195 |
| Contra | Pulse 1 | 0 real | 96.6% | 85.3% |
| Contra | Pulse 2 | 0 real | 74.7% | 78.7% |
| Contra | Triangle | ~70% | 93.5% | 93.5% |

## Key Files Changed

### Code
- `extraction/drivers/konami/parser.py` — Added vol_env_index, decrescendo_mul,
  vol_duration to InstrumentChange. Added validate_full_duration().
  NoteEvent docstring documents full-duration invariant. STATUS labels added.
- `extraction/drivers/konami/contra_parser.py` — NEW. EC pitch adjustment,
  extract_envelope_tables(), corrected percussion mapping (kick/snare/compound).
- `extraction/drivers/konami/frame_ir.py` — DriverCapability schema,
  _cv1_parametric_envelope (phase2_start fix), _contra_lookup_envelope
  (bounce-at-1, vol_duration). Triangle labeled APPROXIMATION.
- `extraction/drivers/konami/midi_export.py` — envelope_tables passthrough.
- `scripts/render_wav.py` — Drum timing fix (abs_frame advance), triangle
  phase reset, kick/compound drum rendering.
- `scripts/trace_compare.py` — Still CV1-hardcoded. Agent 9 was supposed
  to add --game param but did not complete.

### Documentation (7 new structured docs)
- `docs/DRIVER_MODEL.md` — Three-layer architecture (engine/data/hardware)
- `docs/GAME_MATRIX.md` — Per-game status matrix
- `docs/COMMAND_MANIFEST.md` — Byte-level command reference
- `docs/INVARIANTS.md` — 10 invariants with evidence and test names
- `docs/TRACE_WORKFLOW.md` — Mesen capture and validation workflow
- `docs/RESEARCH_LOG.md` — Chronological hypothesis/verdict record
- `docs/UNKNOWNS.md` — Open questions as bounty board

### Additional docs from this session
- `docs/CONTRAGOALLINE.md` — Contra fidelity story
- `docs/CONTRACOMPARISON.md` — Trace vs extraction comparison
- `docs/CONTRALESSONSTOCV1.md` — Cross-game lessons
- `docs/KONAMITAKEAWAY.md` — Konami music coding principles
- `docs/CHECKLIST.md` — Musical parameter checklist
- `docs/NOTEDURATIONS.md` — Duration dynamics explainer
- `docs/MESENCAPTURE.md` — Mesen trace capture workflow
- `docs/HOWTOREADACAPTURE.md` — Capture file reading guide
- `docs/HOWTOBEMOREFLEXIBLE.md` — Flexibility in RE methodology
- `docs/DONEBEFORE.md` — Prior art survey
- `docs/SWARMPERFORMED1.md` — Swarm performance analysis
- `docs/SWARMAGENTIDS.md` — Agent roster

### Tests
- `tests/test_envelope_invariants.py` — 10 tests: phase2_start, bounce-at-1,
  verified envelopes, volume bounds, pure functions
- `tests/test_parser_invariants.py` — 7 tests: pitch_to_midi, octave clamp,
  triangle offset, full-duration invariant

### Manifests
- `extraction/manifests/contra.json` — Updated: envelope verified, EC verified,
  trace validation stats, vol_duration documented
- `extraction/manifests/castlevania1.json` — Unchanged (already complete)

### Traces
- `extraction/traces/contra/jungle.csv` — NEW. 4000 frames captured from Mesen 2.

### Output
- `output/Contra_v8/midi/` — 11 MIDI files (latest batch)

## What's Left Incomplete

### trace_compare.py --game parameter
Agent 9 did not complete the --game CLI parameter. Currently the
script is hardcoded to CV1. Adding `--game contra` support requires:
- GAME_CONFIGS dict with per-game paths/settings
- Branching parser instantiation (KonamiCV1Parser vs ContraParser)
- DriverCapability selection
- Backward compatibility (default=cv1)

### Triangle fidelity (195 mismatches)
The `(reload+3)//4` linear counter approximation is labeled
APPROXIMATE in INVARIANTS.md (INV-007). Real fix requires modeling
the APU quarter-frame sequencer. This is a HARDWARE layer issue.

### Contra remaining volume gap (~3.4%)
The UNKNOWN_SOUND_01 subtraction (disassembly line 316-320 of bank1.asm)
reduces the volume written to the APU register. We don't model this.

### Base track Sq2 early loop
Base Sq2 loops at 2688 frames while other channels loop at 3456.
This is correct game behavior (Sq2 replays its intro) but our
single-pass extraction produces 768 frames of silence on Sq2.

### Website
User wants a website showing both projects with documentation
commentary, version history with audio samples, and ROM hacker
tutorial framing. README.md is website-ready. Docs are structured
markdown. No site generator configured yet.

## Verification Commands

```bash
# Run invariant tests (17 tests, all must pass)
PYTHONPATH=. python -m pytest tests/test_envelope_invariants.py tests/test_parser_invariants.py -v

# CV1 trace validation (must show 0 pulse mismatches)
PYTHONPATH=. python scripts/trace_compare.py --frames 1792

# Extract one Contra track
PYTHONPATH=. python -c "
from extraction.drivers.konami.contra_parser import ContraParser
from extraction.drivers.konami.midi_export import export_to_midi
parser = ContraParser('AllNESRoms/All NES Roms (GoodNES)/USA/Contra (U) [!].nes')
song = parser.parse_track('jungle')
export_to_midi(song, 'test.mid', game_name='Contra', envelope_tables=parser.envelope_tables)
"
```

## Git State

Latest commit: `0c597e8` (Methodological refactor)
Branch: `master`
Remote: `origin` → `https://github.com/t3dy/ReapNES.git`
Uncommitted: trace_compare.py has minor unstaged changes, old MIDI deletions.
