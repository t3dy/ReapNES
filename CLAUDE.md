# NES Music Studio -- Claude Code Instructions

## Project Identity

NES Music Studio is a full-pipeline NES music system:
ROM -> extraction -> MIDI + presets -> REAPER project -> playable music.

Two halves:
- **Extraction engine** (`extraction/`) -- ROM analysis, driver parsing, APU trace processing
- **Studio environment** (`studio/`) -- JSFX synths, project generation, preset management

## Context Routing

**If working on extraction/ or drivers/:** Read `extraction/CLAUDE_EXTRACTION.md`
**If working on studio/, scripts/, or JSFX/RPP/MIDI:** Read `studio/CLAUDE_STUDIO.md`
**If unsure which docs to read:** See `DOCUMENTAIRTRAFFICCONTROL.md`

## MANDATORY: Run Validation

After ANY change to JSFX, RPP generation, MIDI handling, or extraction code:
```
python scripts/validate.py --all
```

## Key Scripts

| Script | Purpose | Example |
|--------|---------|---------|
| `scripts/generate_project.py` | Create .RPP projects | `--generic`, `--midi FILE` |
| `scripts/validate.py` | Lint JSFX/RPP/MIDI/extraction | `--all`, `--jsfx`, `--rpp`, `--midi` |
| `scripts/preset_catalog.py` | Browse preset corpus | `games`, `search --tag X` |
| `scripts/pipeline.py` | End-to-end ROM->RPP | `--rom FILE --song NAME` |

## Anti-Creep Rules

- Do not build speculative features before the basic pipeline works
- Do not deepen low-level emulation without user-facing payoff
- Verify the simplest case first, always
- A working single-note test beats a speculative framework
- Run validation after every change, not just at the end

## Current Focus: Fidelity

The end-to-end pipeline works (ROM -> parser -> MIDI -> REAPER). The current
task is **closing the fidelity gap** between extracted output and the real
game audio. See `docs/HANDOVER_FIDELITY.md` for detailed current state,
identified bugs, and prioritized next steps.

Key rule: **Use the APU trace as ground truth.** Run `scripts/trace_compare.py`
after any parser or export change to verify against the emulator trace.

## First Milestone

**"Castlevania Stage 1 from ROM to REAPER"**

1. ~~Complete Konami driver parser for Castlevania Stage 1~~ DONE
2. ~~Extract MIDI sequence + instrument presets from ROM~~ DONE
3. ~~Generate RPP project with per-channel instruments~~ DONE
4. ~~Open in REAPER, press play, hear Vampire Killer~~ DONE
5. Close fidelity gap: fix repeat count, B section alignment, envelope accuracy
6. Rebuild MIDI export from frame IR for proper staccato articulation
