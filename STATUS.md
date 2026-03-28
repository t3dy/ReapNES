# NES Music Studio — Status

## What Works End-to-End Right Now

- **ReapNES_APU.jsfx synth plugin** — 4-channel NES synth (Pulse 1, Pulse 2, Triangle, Noise) with interactive GUI, drum engine with decay envelopes, per-channel mode filtering, DC-offset-free mixing. Installed in REAPER and producing sound.
- **Project generation** — `scripts/generate_project.py` creates valid .RPP projects with correct track routing, channel modes, MIDI channel remapping, and SOURCE MIDI FILE references. 27 tested projects.
- **Validation suite** — `scripts/validate.py --all` catches all 14 documented blunders across JSFX, RPP, and MIDI files. All tests passing (except known legacy JSFX files and BAD-rated community MIDIs).
- **MIDI channel remapping** — Automatic analysis and remapping of arbitrary MIDI channel numbers to NES standard 0-3.
- **71 MIDI files** — NES game transcriptions (Castlevania, Mega Man 2, Metroid, Bionic Commando) and classical (Bach, Beethoven, Mozart). Quality-rated PERFECT/GOOD/OK/BAD.
- **54,000+ instrument presets** from NES Music Database.
- **90+ song set JSON files** with game/song instrument palettes.
- **Preset catalog browser** — `scripts/preset_catalog.py`.

## What's Partially Built

- **End-to-end pipeline** — `scripts/pipeline.py` stub exists. Can find ROMs, check for existing MIDI, fall back to community MIDI, generate projects, and validate output. ROM extraction step is stubbed.
- **Extraction engine architecture** — Three-pipeline system (static/dynamic/reconciliation) with typed data models, scaffolding for all layers, 106 tests passing. No actual driver parsing yet.
- **Konami driver parser** — Stub in `extraction/drivers/konami/`. Spec documented, attack plan written. Code signatures and data format TBD.
- **5 Castlevania MIDI exports** — From NES Music Lab's export layer, but generated from trace analysis not full ROM parsing.

## What's Planned

- **Konami Pre-VRC driver parser** — Decode Castlevania music bytecode, extract symbolic Song objects
- **APU trace reconciliation** — Align static parser output with runtime traces, adjust confidence
- **Volume envelope support** — Biggest missing feature for faithful NES sound reproduction
- **Per-game preset loading** — Wire 54K preset corpus into the JSFX plugin via song sets
- **DMC sample playback** — Delta modulation channel for sampled audio
- **Sweep unit integration** — Hardware pitch sweep mapped to MIDI pitch bend
- **Capcom driver** — Second driver family (Mega Man, DuckTales)

## First Milestone

**"Castlevania Stage 1 from ROM to REAPER"**

1. Complete Konami driver parser for Castlevania Stage 1
2. Extract MIDI sequence from ROM (4 channels, correct timing)
3. Extract instrument presets (duty cycles, volume envelopes)
4. Generate song set JSON from extracted data
5. Generate RPP project from song set + MIDI
6. Open in REAPER, press play, hear Vampire Killer

## Validation Results (at merge time)

```
JSFX:  2/4 PASS (ReapNES_APU.jsfx + ReapNES_Full.jsfx pass; 2 legacy files have known issues)
RPP:   27/27 PASS
MIDI:  52/71 PASS (19 BAD-rated community MIDIs with >6 channels — expected per Blunder 13/14)
```
