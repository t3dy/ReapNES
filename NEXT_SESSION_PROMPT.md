# Startup Prompt — Paste Into New Claude Code Window

---

You are continuing work on NES Music Studio at C:/Dev/NESMusicStudio/.
GitHub: https://github.com/t3dy/ReapNES

Read these files in order:

1. C:/Dev/NESMusicStudio/CLAUDE.md
2. C:/Dev/NESMusicStudio/docs/HANDOVER_SESSION2.md
3. C:/Dev/NESMusicStudio/docs/INVARIANTS.md

Then skim:
4. C:/Dev/NESMusicStudio/docs/UNKNOWNS.md (open questions)
5. C:/Dev/NESMusicStudio/extraction/manifests/contra.json

## Context

Two Konami NES soundtracks extracted and validated:

**Castlevania 1** — COMPLETE. 15/15 tracks. Pulse channels: 0 pitch, 0 volume,
0 sounding mismatches across 1792 frames. Triangle has 195 sounding mismatches
(linear counter approximation, labeled APPROXIMATE in INVARIANTS.md INV-007).

**Contra** — 11/11 tracks at v8. Trace-validated: 0 real pitch mismatches,
96.6% volume match on Jungle. Key fixes this session: EC pitch adjustment,
envelope lookup tables (54 extracted from ROM), bounce-at-1, vol_duration.

**Architecture** — DriverCapability schema dispatches envelope strategies.
Parsers emit full-duration events (INV-002). Frame IR handles all volume shaping.
17 invariant tests pass. Status labels on all driver modules.

**Docs** — 7 structured docs (DRIVER_MODEL, GAME_MATRIX, COMMAND_MANIFEST,
INVARIANTS, TRACE_WORKFLOW, RESEARCH_LOG, UNKNOWNS) plus 15+ narrative docs.
All written as ROM hacker tutorials with machine-readable status values.

## What Was Left Incomplete

1. **Website** — User wants a site showing both projects with docs,
   version-by-version audio comparisons, and ROM hacker tutorial framing.
   README.md is website-ready. Docs are structured markdown. No site
   generator configured yet. User said "go build and deploy the website."

2. **trace_compare.py --game parameter** — Currently hardcoded to CV1.
   Needs GAME_CONFIGS dict, --game CLI arg, ContraParser branching.
   Backward compatible (default=cv1). See HANDOVER_SESSION2.md for spec.

3. **Triangle fidelity** — 195 mismatches on CV1. Hardware layer issue
   (quarter-frame sequencer). Labeled APPROXIMATE. Not blocking but the
   most interesting open research problem.

4. **Contra remaining gaps** — UNKNOWN_SOUND_01 subtraction (~3.4% vol),
   Base Sq2 early loop (correct behavior but needs loop extension for
   full-length MIDI), EB vibrato (unused in Contra but needed for future).

5. **Apply lessons to Castlevania** — The user asked whether Contra
   insights could improve CV1 further. The phase2_start fix already
   eliminated 45 mismatches. Triangle is the remaining frontier.

## Rules

- CLAUDE.md has ordered workflow gates — follow the sequence
- Per-game manifests carry structured state — read them, update them
- Run `PYTHONPATH=. python scripts/trace_compare.py --frames 1792` after changes
- 17 invariant tests must pass: `PYTHONPATH=. python -m pytest tests/test_envelope_invariants.py tests/test_parser_invariants.py -v`
- Architecture rules in `.claude/rules/architecture.md`
- Version output files. Never overwrite tested files.

## Key Commands

```bash
PYTHONPATH=. python scripts/trace_compare.py --frames 1792           # CV1 validation
PYTHONPATH=. python -m pytest tests/test_envelope_invariants.py tests/test_parser_invariants.py -v  # invariants
PYTHONPATH=. python scripts/rom_identify.py <rom>                     # identify ROM
```

---
