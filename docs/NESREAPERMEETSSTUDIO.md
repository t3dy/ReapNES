# NES REAPER Meets Studio — Project Merger Handover

## What This Document Is

A complete handover for merging two existing projects into one unified repo:

- **NES Music Lab** (`C:/Dev/NESMusicLab/`) — ROM extraction and analysis
- **ReapNES Studio** (`C:/Dev/ReapNES-Studio/`) — REAPER synth plugins and studio tools

The merged project should be a single repo that handles the full pipeline:
ROM → extraction → MIDI + presets → REAPER project → playable music.

---

## The Two Projects

### NES Music Lab (Extraction Side)

**Location**: `C:/Dev/NESMusicLab/`

**Purpose**: Research-grade extraction of music data from NES ROMs.

**Architecture**: Three-pipeline system:
- Pipeline A: Static analysis (ROM bytecode → symbolic music models)
- Pipeline B: Dynamic analysis (emulator APU traces → event streams)
- Pipeline C: Reconciliation (validate static vs dynamic, alignment scoring)

**What it has**:
- 7 NES ROMs (Bionic Commando, Castlevania I-III, Darkwing Duck, Demon Sword, Final Fantasy, Ghosts'n Goblins)
- Castlevania Stage 1 APU trace (304KB CSV)
- Driver family catalog (8 families: Konami, Capcom, Nintendo, Sunsoft, etc.)
- Konami Pre-VRC driver spec and parser stub
- Typed data models (Song, Pattern, NoteEvent, InstrumentBehavior, Envelope)
- iNES header parser
- Driver identification heuristics
- APU register reference tables
- Emulator trace ingestion

**What it produces** (planned):
- Normalized JSON (song structure, channel behavior, loop points, confidence annotations)
- Per-channel MIDI exports
- REAPER-oriented metadata (duty changes, volume envelopes, pitch modulation)
- Provenance records (every extracted value traced to source evidence)

**Key principles**:
- Every extracted object carries source_type and confidence score
- Evidence hierarchy: manual verification > static parser > runtime observation > heuristic
- Driver-family-specific parsing (no universal parser — each engine is different)
- Zero external dependencies for core extraction (Python stdlib only)

**Current phase**: Phase 1 (architecture) complete, Phase 2-3 (trace ingestion + Konami parsing) next.

**Key files**:
- `CLAUDE.md` — project instructions
- `docs/PHASED_PLAN.md` — 6-phase roadmap
- `docs/DRIVER_FAMILIES.md` — NES sound driver catalog
- `docs/FIRST_TARGET_FAMILY.md` — Konami phase plan
- `src/nesml/models/` — typed data models
- `src/nesml/static_analysis/` — ROM inspection tools
- `src/nesml/dynamic_analysis/` — trace processing
- `drivers/konami/` — first target driver parser

---

### ReapNES Studio (Production Side)

**Location**: `C:/Dev/ReapNES-Studio/`

**Purpose**: REAPER-based NES music production environment.

**What it has** (working, tested):
- ReapNES_APU.jsfx — self-contained 4-channel NES synth with:
  - Pulse 1 + Pulse 2 (4 duty cycles, volume, pitch)
  - Triangle (fixed waveform)
  - Noise (LFSR, 16 periods, long/short mode)
  - GM drum mapping with decay envelopes (kick, snare, hi-hat, toms, crash)
  - Per-channel mode (filter, not remap) for multi-track isolation
  - Interactive GUI (oscilloscope + clickable controls)
  - DC-offset-free mixing
- 27 generated REAPER projects (.RPP) — working, tested in REAPER v7.27
- Project generator script with MIDI channel remapping
- 71 MIDI files (NES games + classical)
- 54,000 extracted instrument presets from NES Music Database
- 90+ song set JSON files (game/song instrument palettes)
- Full validation suite (JSFX lint, RPP lint, MIDI quality, integration tests)
- Preset catalog browser
- Comprehensive documentation including 14 documented blunders

**What it needs** (not yet built):
- Volume envelopes (biggest missing feature for faithful NES sound)
- Per-game preset loading into the JSFX plugin
- DMC sample playback
- Sweep unit integration with MIDI
- ROM-extracted MIDI (currently using community transcriptions)

**Key files**:
- `CLAUDE.md` — project instructions (includes all REAPER rules)
- `jsfx/ReapNES_APU.jsfx` — the working synth plugin
- `scripts/generate_project.py` — RPP project generator
- `scripts/validate.py` — validation suite
- `docs/BLOOPERS.md` — 14 bugs and how to avoid them
- `docs/REQUIREMENTSFORMIDI.md` — spec for MIDI files from extraction
- `docs/REQUIREMENTSFORSYNTH.md` — spec for JSFX synth plugins

---

## How They Connect

```
NES Music Lab                          ReapNES Studio
=============                          ==============

ROM files ─────► Static Analysis
                      │
Emulator ─────► Dynamic Analysis
                      │
                 Reconciliation
                      │
                      ▼
              Extracted Data:
              - MIDI sequences ──────► MIDI files ──────► RPP projects
              - Instrument presets ──► Song set JSON ──► Plugin sliders
              - Envelope data ───────► Volume automation ► REAPER envelopes
              - Duty cycle changes ──► CC automation ───► Plugin parameters
              - Provenance metadata ─► Confidence tags ► Documentation
                                                              │
                                                              ▼
                                                    Open in REAPER
                                                    Hit play, hear music
```

---

## Merger Plan

### Proposed Unified Structure

```
NESMusicStudio/                    (or whatever name you choose)
│
├── CLAUDE.md                      Combined project instructions
│
├── extraction/                    ← from NES Music Lab
│   ├── src/nesml/                 Core extraction engine
│   │   ├── models/                Typed data models
│   │   ├── static_analysis/       ROM inspection
│   │   ├── dynamic_analysis/      Trace processing
│   │   ├── reconcile/             Static ↔ dynamic alignment
│   │   └── export/                MIDI + REAPER export
│   ├── drivers/                   Driver-family parsers
│   │   ├── konami/                Castlevania, etc.
│   │   ├── capcom/                Mega Man, etc.
│   │   └── ...
│   ├── roms/                      NES ROM files
│   ├── nsf/                       NSF sound files
│   └── traces/                    Emulator APU logs
│
├── studio/                        ← from ReapNES Studio
│   ├── jsfx/                      JSFX synth plugins
│   ├── presets/                    Instrument preset data
│   ├── song_sets/                 Game/song palettes
│   ├── reaper_projects/           Generated .RPP files
│   ├── reaper_templates/          Track templates
│   └── midi/                      MIDI files (source + remapped)
│
├── scripts/                       Combined automation
│   ├── generate_project.py        RPP project generation
│   ├── validate.py                Lint suite
│   ├── preset_catalog.py          Preset browser
│   ├── extract_from_rom.py        ROM → MIDI + presets (future)
│   └── build_song_bundle.py       Extraction → song set → RPP (future)
│
├── tests/                         Combined test suite
│   ├── test_jsfx_lint.py
│   ├── test_rpp_lint.py
│   ├── test_midi_quality.py
│   ├── test_project_generator.py
│   └── test_extraction/           Extraction pipeline tests
│
├── docs/                          Combined documentation
│   ├── BLOOPERS.md                14 documented failure modes
│   ├── REQUIREMENTSFORMIDI.md     MIDI output spec
│   ├── REQUIREMENTSFORSYNTH.md    JSFX plugin spec
│   ├── DRIVER_FAMILIES.md         NES sound driver catalog
│   ├── PHASED_PLAN.md             Extraction roadmap
│   ├── STUDIO_WORKFLOW.md         End-user workflow guide
│   ├── OPERATOR_GUIDE.md          Extraction operator guide
│   └── schemas/                   JSON schema definitions
│
├── data/                          Shared data artifacts
│   ├── analysis/                  Extraction outputs (JSON)
│   ├── exports/                   Final exported artifacts
│   └── reports/                   Provenance records
│
└── tools/                         Specialized tooling
    ├── mdb/                       NES Music Database tools
    └── parsers/                   Format parsers (NSF, etc.)
```

### What To Preserve From Each Project

**From NES Music Lab** (keep everything):
- All source code in `src/nesml/`
- All driver parsers in `drivers/`
- All data models and schemas
- All ROMs, traces, and analysis outputs
- All documentation
- The evidence hierarchy and confidence system
- The phased plan

**From ReapNES Studio** (keep everything):
- `jsfx/ReapNES_APU.jsfx` — the working synth plugin
- `scripts/generate_project.py` — the project generator
- `scripts/validate.py` — the validation suite
- All test files
- All song sets and presets
- All generated projects
- All MIDI files
- All documentation including BLOOPERS.md

### What To Create New

1. **Unified CLAUDE.md** combining rules from both projects
2. **End-to-end pipeline script**: ROM → extract → MIDI → preset → RPP → open in REAPER
3. **Shared data models**: extraction output format that directly feeds the studio pipeline
4. **Integration tests**: extraction output validates against MIDI requirements doc

---

## Critical Rules for the Merged Project

### From NES Music Lab:
- Every extracted value must carry confidence and provenance
- Driver-specific parsing, no universal assumptions
- Evidence hierarchy must be respected
- Zero external dependencies for extraction core

### From ReapNES Studio:
- Run `python scripts/validate.py --all` after any change to JSFX/RPP/MIDI
- JSFX rules: `tags:instrument`, `in_pin:none`, ASCII only, sequential sliders
- RPP rules: `MAINSEND` not `MASTER_SEND`, `SOURCE MIDI FILE`, per-track channel mode
- Audio output centered at zero, silence when idle
- Channel mode FILTERS, never REMAPS
- The 14 blunders in BLOOPERS.md are mandatory reading

### New rules for the merged project:
- Extraction outputs must conform to REQUIREMENTSFORMIDI.md
- Synth plugins must conform to REQUIREMENTSFORSYNTH.md
- The pipeline must be end-to-end testable
- Every MIDI file must pass `validate.py --midi` before project generation

---

## The End-to-End Workflow (Goal)

```
1. User has a NES ROM (e.g., Castlevania III)
2. Extraction pipeline identifies the sound driver (Konami Pre-VRC)
3. Static analysis parses the ROM's music data
4. Dynamic analysis processes an APU trace
5. Reconciliation validates and merges both
6. Export produces:
   - Per-channel MIDI file (channels 0-3, monophonic, correct register separation)
   - Song set JSON (instrument presets with duty/envelope/noise params)
   - Confidence report (which parts are verified, which are provisional)
7. Project generator creates an RPP file with:
   - 4 tracks (P1, P2, Tri, Noise) each with correct channel mode
   - MIDI items loaded from extracted MIDI
   - Plugin presets loaded from song set
8. User opens RPP in REAPER
9. Presses play
10. Hears faithful NES music with per-track instrument controls
```

---

## Current State Summary

| Component | Status | Quality |
|-----------|--------|---------|
| JSFX synth plugin (ReapNES_APU) | Working | Good — missing volume envelopes |
| RPP project generation | Working | Solid — tested with 27 projects |
| MIDI channel remapping | Working | Solid |
| Drum engine | Working | Decent — GM drum → NES noise mapping |
| Validation suite | Working | Comprehensive — 14 blunders covered |
| Preset corpus | Exists | 54K presets, not yet wired to plugin |
| Song sets | Exists | 90+ sets, JSON format defined |
| ROM extraction pipeline | Architecture only | Models defined, parsing not started |
| Konami driver parser | Stub | Phase 3 target |
| APU trace ingestion | Planned | Data models exist |
| End-to-end pipeline | Not built | Depends on extraction completing |

---

## First Milestone After Merge

**"Castlevania Stage 1 from ROM to REAPER"**

1. Complete Konami driver parser for Castlevania Stage 1
2. Extract MIDI sequence from ROM (4 channels, correct timing)
3. Extract instrument presets (duty cycles, volume envelopes)
4. Generate song set JSON from extracted data
5. Generate RPP project from song set + MIDI
6. Open in REAPER, press play, hear Vampire Killer

This is the minimum viable proof that the full pipeline works.
