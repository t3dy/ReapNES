# NES Music Studio -- Claude Code Instructions

## Project Identity

NES Music Studio is a full-pipeline NES music system:
ROM -> extraction -> MIDI + presets -> REAPER project -> playable music.

Two halves:
- **Extraction engine** (`extraction/`) — ROM analysis, driver parsing, APU trace processing
- **Studio environment** (`studio/`) — JSFX synths, project generation, preset management

## MANDATORY: Run Validation Before Delivering

After ANY change to JSFX, RPP generation, or MIDI handling, run:
```
python scripts/validate.py --all
```

Do NOT deliver code that fails validation. The test suite exists because every one of these bugs caused hours of silent failure in REAPER.

Individual checks:
```
python scripts/validate.py --jsfx   # Lint all JSFX plugins
python scripts/validate.py --rpp    # Lint all generated RPP files
python scripts/validate.py --midi   # Quality-check MIDI files
pytest tests/ -v                    # Full test suite with integration tests
```

---

## The 14 Blunder Prevention Rules

These are NOT suggestions. Every rule comes from a real bug that caused hours of silent failure. See `docs/BLOOPERS.md` for the full horror story.

### JSFX Plugin Rules

1. **`tags:instrument` not `//tags:instrument`** — The `//` makes it a comment. REAPER silently ignores it, won't route MIDI to the plugin. No error, no warning, just silence.

2. **`in_pin:none` is required** — Without it, REAPER treats the plugin as an audio effect, not a synth. It won't generate audio from MIDI. No error, just silence.

3. **ASCII only in JSFX files** — No unicode anywhere. No `->` arrows, no `--` dashes, no special characters. REAPER's JSFX compiler doesn't support unicode. The plugin loads, shows in FX list, but produces no audio.

4. **REAPER caches compiled JSFX** — After fixing bugs, the plugin may STILL not work because REAPER cached the old broken version. Rename the file to force a fresh compile. This is the nuclear option that always works.

5. **`^` is POWER in JSFX, not XOR** — `0 ^ 0 = 1` (power) vs `0 ^ 0 = 0` (XOR). Use `((a + b) & 1)` for single-bit XOR.

### RPP File Rules

6. **Use `MAINSEND 1 0` not `MASTER_SEND`** — REAPER v7.27 doesn't recognize `MASTER_SEND`. Shows a warning but silently ignores the setting.

7. **Never use `REC_INPUT`, `RECINPUT`, or `RECMON` tokens** — Unrecognized in REAPER v7.27. The `REC` field format is tribal knowledge; save a track template FROM REAPER to discover the correct encoding.

8. **Use `SOURCE MIDI` with `FILE "path"` not `SOURCE MIDIPOOL`** — `MIDIPOOL` shows notes visually but produces no audio. Inline `E` events show empty items. Only `SOURCE MIDI` with `FILE` reference works.

### Audio Output Rules

9. **Output signal must be centered at zero** — The non-linear NES mixer formula produces a constant DC offset when no notes play. The meter shows signal but nothing is audible. Use `(value / 15.0 - 0.5)` to center. Only mix active oscillators (check `en` flag before adding to mix).

10. **Only include active oscillators in the mix** — Inactive oscillators at value 0 produce DC offset of -0.25 each. With 4 inactive channels that's -0.70 DC offset. Check the enable flag before adding any channel to the mix.

### Channel Architecture Rules

11. **Channel mode must FILTER, never REMAP** — Each track's plugin must skip non-matching MIDI channels, NOT redirect all channels to one. Remapping causes every track to play all 4 channels = 16 channels of mush.
    ```
    // WRONG: ch_mode == 0 ? ch = 0;  (remaps ALL channels to 0)
    // RIGHT: ch != ch_mode ? use_msg = 0;  (skips non-matching)
    ```

12. **MIDI channels must be remapped to 0-3 before project generation** — Community MIDIs use random channel numbers (ch 1,3,4 or ch 0,1,11). The project generator must analyze and remap to NES standard 0-3.

### Drum and MIDI Rules

13. **Drum notes need self-decaying volume envelopes, not sustain** — Real NES drums punch and fade. Without decay, noise pops on/off creating clicks instead of drum sounds.

14. **Community MIDI files are unreliable — prefer ROM extraction** — VGMusic transcriptions have random channels, wrong registers, too many voices, bad arrangements. The long-term fix is NSF extraction from actual ROMs.

---

## Blunder Prevention Checklist

Run this mental checklist before any JSFX/RPP/MIDI change:

```
[ ] JSFX has desc: on first line (plain ASCII)
[ ] JSFX has tags:instrument (NOT //tags:)
[ ] JSFX has in_pin:none
[ ] JSFX has out_pin:Left and out_pin:Right
[ ] JSFX is ASCII only (no unicode anywhere)
[ ] JSFX slider numbers are sequential (no gaps)
[ ] No ^ used for XOR (use ((a+b)&1) instead)
[ ] Output centered at zero (no DC offset)
[ ] Silence when no notes playing (spl0 = spl1 = 0)
[ ] Channel mode FILTERS, not REMAPS
[ ] Only active channels contribute to mix
[ ] Drum envelopes decay to zero (don't sustain)
[ ] RPP uses MAINSEND 1 0 (not MASTER_SEND)
[ ] RPP uses SOURCE MIDI with FILE reference
[ ] RPP has 64 space-separated slider values
[ ] MIDI channels are 0-3 (remapped if needed)
```

---

## REAPER-Specific Rules

### JSFX Instruments MUST have:
```
desc:Plugin Name
tags:instrument synthesizer
in_pin:none
out_pin:Left
out_pin:Right
```

### RPP Files MUST:
- Use per-track channel mode: slider13 = 0/1/2/3 for P1/P2/Tri/Noise
- Never use Full APU mode (4) in multi-track projects
- Use `SOURCE MIDI` with `FILE` reference
- Have 64 space-separated slider values (dashes for unused)
- Have `BYPASS 0 0 0` before plugin block, `FLOATPOS`/`FXID`/`WAK` after
- Have GUIDs on tracks, items, FX instances

### Audio Output MUST:
- Only mix active oscillators (check `en` flag before adding to mix)
- Output exactly 0.0 when no notes playing
- Center signal around zero (use `value/15 - 0.5`)

---

## Extraction Rules (from NES Music Lab)

- Every extracted value carries confidence (0.0-1.0) and provenance
- Evidence hierarchy: manual > static parser > runtime observation > heuristic
- Driver-specific parsing (no universal parser -- each engine is different)
- Terminology discipline: never conflate "period" with "note", never call inferred timing "tempo" without marking it as hypothesis
- Zero external dependencies for extraction core (Python stdlib only)
- MIDI output must conform to `docs/REQUIREMENTSFORMIDI.md`
- Synth plugins must conform to `docs/REQUIREMENTSFORSYNTH.md`

### Confidence Policy

Every extracted object carries:
- `source_type`: static | dynamic | reconciled | manual | heuristic | provisional
- `confidence.score`: 0.0-1.0
- `confidence.reason`: why this confidence level
- `evidence_refs`: pointers to supporting evidence

### Three-Pipeline Architecture
- **Pipeline A (Static):** ROM -> driver identification -> sequence parser -> symbolic model
- **Pipeline B (Dynamic):** ROM/NSF -> emulator APU trace -> normalized event stream
- **Pipeline C (Reconciliation):** Static <-> dynamic alignment -> confidence adjustment

---

## MIDI Output Quality Rules

- Exactly 4 channels (0-3): Pulse1, Pulse2, Triangle, Noise
- Strictly monophonic per channel
- Minimum 6 semitone register separation between melodic channels
- Triangle channel velocity always 127 (no volume control)
- Noise channel uses GM drum note range 35-57
- Every note-on has matching note-off
- Tempo derived from driver, not guessed
- Metadata track includes game, song, source, confidence

---

## Key Scripts Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `scripts/generate_project.py` | Create .RPP projects | `--generic`, `--midi FILE` |
| `scripts/validate.py` | Lint JSFX/RPP/MIDI | `--all`, `--jsfx`, `--rpp`, `--midi` |
| `scripts/preset_catalog.py` | Browse preset corpus | `games`, `search --tag X` |
| `scripts/pipeline.py` | End-to-end ROM->RPP | `--rom FILE --song NAME` |
| `scripts/convert_trace.py` | Convert APU traces | From NES Music Lab |
| `scripts/export_castlevania_midi.py` | Export Castlevania MIDI | From NES Music Lab |

---

## Repository Structure

```
NESMusicStudio/
|-- CLAUDE.md                     This file
|-- extraction/                   ROM extraction engine (from NES Music Lab)
|   |-- src/nesml/                Core extraction engine
|   |   |-- models/               Typed data models
|   |   |-- static_analysis/      ROM inspection
|   |   |-- dynamic_analysis/     Trace processing
|   |   |-- reconcile/            Static <-> dynamic alignment
|   |   |-- export/               MIDI + REAPER export
|   |-- drivers/                  Driver-family parsers
|   |   |-- konami/               Castlevania, etc.
|   |   |-- capcom/               Mega Man, etc.
|   |-- roms/                     NES ROM files
|   |-- nsf/                      NSF sound files
|   |-- traces/                   Emulator APU logs
|   |-- exports/                  Extraction outputs (MIDI, REAPER metadata)
|   |-- analysis/                 Analysis results (static, dynamic, reconciled)
|-- studio/                       REAPER studio environment (from ReapNES Studio)
|   |-- jsfx/                     JSFX synth plugins
|   |-- presets/                  Instrument preset data
|   |-- song_sets/                Game/song palettes
|   |-- reaper_projects/          Generated .RPP files
|   |-- templates/                Track templates
|   |-- midi/                     MIDI files (source + remapped)
|-- scripts/                      Combined automation
|-- tests/                        Combined test suite
|   |-- extraction/               Extraction pipeline tests
|-- docs/                         Combined documentation
|-- data/                         Shared data artifacts (NES Music Database)
|-- tools/                        Specialized tooling (MDB tools, parsers)
```

---

## Anti-Creep Rules

- Do not build speculative AI features before the basic pipeline works
- Do not deepen low-level emulation without user-facing payoff
- Verify the simplest case first, always
- A working single-note test beats a speculative framework
- Run validation after every change, not just at the end
- Test that the plugin makes sound in REAPER before building projects
- Never build 6 song sets before confirming one note plays

---

## First Milestone

**"Castlevania Stage 1 from ROM to REAPER"**

1. Complete Konami driver parser for Castlevania Stage 1
2. Extract MIDI sequence from ROM (4 channels, correct timing)
3. Extract instrument presets (duty cycles, volume envelopes)
4. Generate song set JSON from extracted data
5. Generate RPP project from song set + MIDI
6. Open in REAPER, press play, hear Vampire Killer
