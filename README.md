# ReapNES — NES Music Studio

Extract music from NES ROMs, convert to MIDI with per-frame volume automation, render audio, and produce REAPER projects with NES APU synthesis.

**Pipeline**: ROM → parser → frame IR → MIDI → REAPER/WAV/MP4

## What's Been Extracted

### Castlevania (1986) — COMPLETE
All 15 tracks extracted and validated. Zero pitch mismatches against Mesen APU trace across 1792 frames of Vampire Killer. Two-phase parametric envelope model verified to 96%+ volume accuracy.

### Contra (1988) — COMPLETE
All 11 tracks extracted with lookup-table volume envelopes. Validated against Mesen APU trace: zero real pitch mismatches, 96.6% per-frame volume accuracy on Jungle (Level 1).

## How It Works

### The Extraction Pipeline

1. **ROM Identification** (`scripts/rom_identify.py`) — Reads the iNES header, identifies mapper type, scans for driver signatures (period table, command patterns), and checks for existing manifests.

2. **Parsing** (`extraction/drivers/konami/parser.py`, `contra_parser.py`) — Reads the Konami Maezawa sound driver command stream from ROM. Commands include note/duration bytes, octave changes (E0-E4), instrument setup (DX), pitch adjustment (EC), repeat loops (FE), and subroutines (FD).

3. **Frame IR** (`extraction/drivers/konami/frame_ir.py`) — Converts parsed events to per-frame state (period, MIDI note, volume, duty cycle). Dispatches volume shaping via `DriverCapability`:
   - **CV1**: Two-phase parametric envelope (fade_start/fade_step)
   - **Contra**: 54 lookup-table envelopes extracted from `pulse_volume_ptr_tbl` + threshold-linear decrescendo

4. **MIDI Export** (`extraction/drivers/konami/midi_export.py`) — Writes Type 1 MIDI with CC11 (Expression) automation encoding the per-frame volume envelope. Each channel gets its own track.

5. **WAV Render** (`scripts/render_wav.py`) — Python NES APU synth: pulse waves with duty cycle modulation, triangle with phase reset on note changes, noise for drums.

6. **REAPER Projects** (`scripts/generate_project.py`) — Generates .RPP files with the JSFX NES APU synth plugin, pre-configured per channel.

### Trace Validation

The Mesen 2 APU capture script (`docs/mesen_scripts/mesen_apu_capture_auto.lua`) records per-frame hardware state. The trace comparison tool (`scripts/trace_compare.py`) diffs our extraction against this ground truth frame-by-frame.

## What We Learned

This project was built through iterative reverse engineering — parsing music data from ROM, comparing against emulator output, and fixing errors one at a time. The documentation in `docs/` records the full journey.

### Key Technical Discoveries

**Same driver family, different everything else.** CV1 and Contra both use the Konami Maezawa sound driver, share the same period table, and use identical note/octave/repeat commands. But they differ in: DX byte count (2 vs 3/1), percussion format (inline E9/EA vs separate DMC channel), volume envelopes (parametric vs lookup table), and ROM layout (mapper 0 vs mapper 2 bank-switched). Surface similarity is the trap.

**The EC pitch adjustment.** Contra's Jungle track begins with `EC 01` — shifting every subsequent note up 1 semitone in the period table. Our parser initially skipped this byte. The Mesen trace showed every note was exactly 1 semitone flat. This systematic error was invisible to ear testing (melody sounds right, just in the wrong key) and invisible to self-referential comparison (both paths shared the bug).

**Volume never reaches zero during decrescendo.** When the `resume_decrescendo` routine decrements volume to 0, the engine immediately increments it back to 1 (line 411 of the Contra disassembly). Notes sustain at vol=1 through their tail instead of going silent. Missing this caused notes to sound 15+ frames too short.

**PULSE_VOL_DURATION limits auto-decay.** In auto-decrescendo mode (vol_env bit 7 set), the low nibble controls how many frames the initial decay runs — NOT until volume reaches 0. With vol=5 and vol_dur=3, volume goes 5→4→3→2 then holds. Without this, the Contra Base track's middle section was nearly silent.

**Percussion is bass reinforcement.** Contra's `percussion_tbl` shows that most drum hits (nibble 3, the dominant type) trigger both a DMC sample AND a noise channel bass drum. The kick syncs with triangle notes, giving the bass its attack. Mapping all drums as "snare" (our initial approach) eliminated the bass punch entirely.

**Trace captures are non-negotiable.** The trace caught the EC pitch bug, validated envelope table shapes, confirmed the bounce-at-1 behavior, and revealed that our 9% "pitch mismatches" were actually volume-envelope zeros — not wrong notes. Every other testing method (automated comparison, ear testing) missed at least one of these.

### Architecture Lessons

**Parser emits full-duration events. IR handles all shaping.** This invariant (`ParsedSong.validate_full_duration()`) prevents parsers from encoding volume/staccato assumptions that belong in the driver-specific IR layer.

**DriverCapability schema replaces implicit branching.** Instead of `if envelope_tables: contra_path else: cv1_path`, each driver declares its volume model, and the IR dispatches on the declaration. This scales to additional drivers without hidden coupling.

**Volume strategies are isolated functions.** `_cv1_parametric_envelope()` and `_contra_lookup_envelope()` are independently testable and can be compared against trace data without running the full pipeline.

**Per-game manifests carry structured state.** Each game's `extraction/manifests/*.json` tracks verified facts, hypotheses, anomalies, and trace validation results. This prevents re-discovering what previous sessions already established.

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/HANDOVER.md` | Project state, architecture, priority next steps |
| `docs/CHECKLIST.md` | Every musical parameter: what we model, what we don't, how to check |
| `docs/NOTEDURATIONS.md` | Five systems that affect perceived note length |
| `docs/CONTRAGOALLINE.md` | How close the Contra extraction is and what remains |
| `docs/CONTRACOMPARISON.md` | What the Mesen trace proved vs our pre-capture assumptions |
| `docs/HOWTOBEMOREFLEXIBLE.md` | Lessons for anticipating the unexpected in NES RE |
| `docs/HOWTOREADACAPTURE.md` | Guide to reading APU capture files (human + agentic) |
| `docs/MESENCAPTURE.md` | Full Mesen trace capture workflow |
| `docs/MISTAKEBAKED.md` | Every mistake that cost 2+ prompts, now encoded as warnings |
| `docs/HANDOVER_FIDELITY.md` | CV1 envelope model details and verification |
| `docs/LATESTFIXES.md` | All CV1 fixes with evidence |
| `docs/CONTRALESSONS.md` | Contra architecture and RE lessons |
| `docs/CONTRAVERSIONS.md` | Contra v1-v8 version history |
| `extraction/drivers/konami/spec.md` | Command format and per-game differences table |
| `extraction/manifests/contra.json` | Contra: verified facts, hypotheses, trace validation |

## Quick Start

```bash
# Identify a ROM
PYTHONPATH=. python scripts/rom_identify.py path/to/rom.nes

# Extract one Contra track
PYTHONPATH=. python -c "
from extraction.drivers.konami.contra_parser import ContraParser
from extraction.drivers.konami.midi_export import export_to_midi
parser = ContraParser('path/to/Contra.nes')
song = parser.parse_track('jungle')
export_to_midi(song, 'jungle.mid', game_name='Contra',
               envelope_tables=parser.envelope_tables)
"

# Validate against trace
PYTHONPATH=. python scripts/trace_compare.py --frames 1792

# Capture your own trace (in Mesen 2)
# Load docs/mesen_scripts/mesen_apu_capture_auto.lua in Script Window
```

## Project Structure

```
extraction/
  drivers/konami/         Parser, frame IR, MIDI export
  manifests/              Per-game structured state (JSON)
  traces/                 Mesen APU trace CSVs
scripts/                  Pipeline tools
studio/
  jsfx/                   ReapNES_APU.jsfx synth plugin
  reaper_projects/        Generated .RPP files
output/                   Extracted MIDI and WAV files
docs/                     Full documentation
```

## Requirements

- Python 3.10+
- `mido` (MIDI I/O)
- `numpy` (WAV rendering)
- Mesen 2 (for trace capture)
- REAPER (optional, for production-quality renders)
