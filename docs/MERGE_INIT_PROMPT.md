# Initialization Prompt for NES Music Studio (Merged Project)

Copy everything below the line into a new Claude Code session.

---

## PROMPT START

You are initializing a new project called **NES Music Studio** by merging two existing projects into a single repository with a unified pipeline.

### Source Projects

1. **NES Music Lab** at `C:/Dev/NESMusicLab/` — ROM extraction and analysis engine
2. **ReapNES Studio** at `C:/Dev/ReapNES-Studio/` — REAPER synth plugins and studio tools

### Your Task

Create a new repo at `C:/Dev/NESMusicStudio/` that combines both projects into a single codebase with a shared pipeline. Do the following steps in order.

### STEP 1: Read These Files First (MANDATORY)

Before writing any code, read ALL of these files. They contain hard-won lessons from dozens of bugs. Do not skip any.

```
C:/Dev/ReapNES-Studio/docs/BLOOPERS.md           — 14 critical bugs and how to avoid them
C:/Dev/ReapNES-Studio/docs/REQUIREMENTSFORMIDI.md — spec for MIDI files from ROM extraction
C:/Dev/ReapNES-Studio/docs/REQUIREMENTSFORSYNTH.md — spec for JSFX synth plugins
C:/Dev/ReapNES-Studio/docs/NESREAPERMEETSSTUDIO.md — full merger plan with structure
C:/Dev/ReapNES-Studio/CLAUDE.md                   — ReapNES Studio rules
C:/Dev/NESMusicLab/CLAUDE.md                      — NES Music Lab rules
C:/Dev/NESMusicLab/docs/PHASED_PLAN.md            — extraction roadmap
C:/Dev/NESMusicLab/docs/DRIVER_FAMILIES.md        — NES sound driver catalog
C:/Dev/NESMusicLab/docs/FIRST_TARGET_FAMILY.md    — Konami target plan
```

### STEP 2: Create the Repository Structure

Follow the structure in `NESREAPERMEETSSTUDIO.md`. The key directories:

```
NESMusicStudio/
├── extraction/          ← from NES Music Lab (src/nesml, drivers, roms, traces)
├── studio/              ← from ReapNES Studio (jsfx, presets, song_sets, reaper_projects, midi)
├── scripts/             ← combined automation (generate_project, validate, preset_catalog)
├── tests/               ← combined test suite
├── docs/                ← combined documentation
├── data/                ← shared artifacts
└── tools/               ← specialized tooling
```

### STEP 3: Copy Files from Both Projects

Copy the actual working code, not just stubs:
- From ReapNES Studio: the JSFX plugin, project generator, validation suite, all tests, all presets/song_sets, all MIDI files, all docs
- From NES Music Lab: all source code in src/nesml, all drivers, all ROMs, all traces, all docs, all data models

Preserve git history if practical (use subtree merge or similar). If not, a clean copy is acceptable.

### STEP 4: Write CLAUDE.md

Create `C:/Dev/NESMusicStudio/CLAUDE.md` that combines the rules from both source projects. This file MUST include:

#### A. Project Identity
```
NES Music Studio is a full-pipeline NES music system:
ROM → extraction → MIDI + presets → REAPER project → playable music.

Two halves:
- Extraction engine (ROM analysis, driver parsing, APU trace processing)
- Studio environment (JSFX synths, project generation, preset management)
```

#### B. Mandatory Validation Rule
```
After ANY change to JSFX, RPP generation, or MIDI handling, run:
  python scripts/validate.py --all
Do NOT deliver code that fails validation.
```

#### C. All 14 Blunder Prevention Rules

Include every rule from `BLOOPERS.md` as a concrete checklist:

1. `tags:instrument` not `//tags:instrument` — the `//` makes it a comment
2. `in_pin:none` required or REAPER produces silence
3. ASCII only in JSFX files — no unicode anywhere
4. REAPER caches compiled JSFX — rename file to force recompile after changes
5. Use `MAINSEND 1 0` not `MASTER_SEND` in RPP files
6. Never use `REC_INPUT`, `RECINPUT`, or `RECMON` tokens
7. Use `SOURCE MIDI` with `FILE "path"` not `SOURCE MIDIPOOL`
8. Output signal must be centered at zero — no DC offset from inactive oscillators
9. `^` is POWER in JSFX, not XOR — use `((a + b) & 1)` for single-bit XOR
10. Channel mode must FILTER (skip non-matching), never REMAP (redirect all to one)
11. MIDI channels must be remapped to 0-3 before project generation
12. Drum notes need self-decaying volume envelopes, not sustain
13. Community MIDI files are unreliable — prefer ROM extraction
14. Only include active oscillators in the mix (inactive at 0 produces DC offset)

#### D. REAPER-Specific Rules

```
JSFX Instruments MUST have:
  desc:Plugin Name
  tags:instrument synthesizer
  in_pin:none
  out_pin:Left
  out_pin:Right

RPP Files MUST:
  - Use per-track channel mode: slider13 = 0/1/2/3 for P1/P2/Tri/Noise
  - Never use Full APU mode (4) in multi-track projects
  - Use SOURCE MIDI with FILE reference
  - Have 64 space-separated slider values

Audio Output MUST:
  - Only mix active oscillators (check en flag before adding to mix)
  - Output exactly 0.0 when no notes playing
  - Center signal around zero (use value/15 - 0.5)
```

#### E. Extraction Rules (from NES Music Lab)

```
- Every extracted value carries confidence (0.0-1.0) and provenance
- Evidence hierarchy: manual > static parser > runtime observation > heuristic
- Driver-specific parsing (no universal parser)
- Terminology discipline (never conflate "period" with "note")
- MIDI output must conform to REQUIREMENTSFORMIDI.md
```

#### F. MIDI Output Quality Rules

```
- Exactly 4 channels (0-3): Pulse1, Pulse2, Triangle, Noise
- Strictly monophonic per channel
- Minimum 6 semitone register separation between melodic channels
- Triangle channel velocity always 127 (no volume control)
- Noise channel uses GM drum note range 35-57
- Every note-on has matching note-off
- Tempo derived from driver, not guessed
- Metadata track includes game, song, source, confidence
```

#### G. Key Scripts Reference Table

```
| Script | Purpose | Example |
|--------|---------|---------|
| scripts/generate_project.py | Create .RPP projects | --generic, --midi FILE |
| scripts/validate.py | Lint JSFX/RPP/MIDI | --all, --jsfx, --rpp, --midi |
| scripts/preset_catalog.py | Browse preset corpus | games, search --tag X |
```

#### H. Anti-Creep Rules

```
- Do not build speculative AI features before the basic pipeline works
- Do not deepen low-level emulation without user-facing payoff
- Verify the simplest case first, always
- A working single-note test beats a speculative framework
- Run validation after every change, not just at the end
- Test that the plugin makes sound in REAPER before building projects
```

### STEP 5: Install the Validation Suite

Copy the test files and validate.py script. Run `python scripts/validate.py --all` and confirm it works in the new repo. This is the safety net that prevents all 14 blunders from recurring.

### STEP 6: Verify the JSFX Plugin

Confirm that `studio/jsfx/ReapNES_APU.jsfx`:
- Is installed at `$APPDATA/REAPER/Effects/ReapNES Studio/ReapNES_APU.jsfx`
- Passes `validate.py --jsfx`
- Produces sound when added to a REAPER track and played via MIDI keyboard

### STEP 7: Verify Project Generation

Run:
```
python scripts/generate_project.py --generic -o studio/reaper_projects/test_generic.rpp
python scripts/validate.py --rpp
```

Confirm the generated RPP opens in REAPER without errors and produces sound.

### STEP 8: Create the End-to-End Pipeline Stub

Create `scripts/pipeline.py` that will eventually run the full flow:
```
python scripts/pipeline.py --rom roms/castlevania.nes --song "Stage 1" --output project.rpp
```

For now, make it a stub that:
1. Checks that the ROM exists
2. Checks that the driver is identified
3. Looks for existing extracted MIDI/presets
4. Falls back to manual MIDI if extraction isn't ready
5. Generates the RPP project
6. Runs validation on the output
7. Reports what's real vs stubbed

### STEP 9: Write a Status Report

Create `STATUS.md` at the repo root with:
- What works end-to-end right now
- What's partially built
- What's planned
- The first milestone: "Castlevania Stage 1 from ROM to REAPER"

### STEP 10: Commit

Commit with a clear message describing the merge of both projects.

### CONSTRAINTS

- Do NOT rewrite working code. Copy it.
- Do NOT rename the JSFX plugin file (REAPER caches by filename — Blunder 4).
- Do NOT change the RPP generation format (it's tested and working).
- Do NOT remove any validation checks.
- Do NOT skip reading the BLOOPERS.md — every rule exists because of a real bug.
- Run `python scripts/validate.py --all` before declaring the merge complete.

### SUCCESS CRITERIA

The merge is successful when:
1. `validate.py --all` passes (except known legacy JSFX files)
2. `generate_project.py --generic` produces a working RPP
3. The JSFX plugin makes sound in REAPER
4. All extraction source code is present and importable
5. All documentation is present
6. CLAUDE.md contains all 14 blunder prevention rules
7. A clear path exists from ROM extraction to REAPER playback
