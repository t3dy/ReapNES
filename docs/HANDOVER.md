# NES Music Studio — Session Handover

## What This Project Does

Extracts music from NES ROM files, converts to MIDI with per-frame
volume automation, generates REAPER projects with NES APU synth plugins,
renders WAV audio, and packages MP4 videos with YouTube descriptions.
Full pipeline: ROM → parser → frame IR → MIDI → REAPER/WAV/MP4.

## Current State

### Castlevania 1 — COMPLETE
15/15 tracks extracted. Zero pitch mismatches against Mesen APU trace
across full 1792-frame Vampire Killer. Two-phase envelope model
(fade_start + fade_step + triangle linear counter) verified to 99.5%.
All tracks have MIDI, REAPER projects, WAVs, and a complete MP4 video.

### Contra — IN PROGRESS (v4 of Jungle theme)
11 tracks parsed using addresses from the annotated disassembly.
Contra-specific parser (`contra_parser.py`) handles different DX byte
count, percussion channel, and decrescendo. Notes and timing are close.
Remaining: volume envelope lookup tables for dynamics.

### Other Games
- **CV2**: Different driver (not Maezawa). Dead end without new RE work.
- **CV3**: Untested. Mapper 5 (MMC5) with expansion audio.
- **Super C**: Partially worked (9/15) with CV1 parser. Needs own config.
- **TMNT, Gradius, Goonies II**: Untested.

## Architecture

```
extraction/drivers/konami/
  parser.py           — CV1 parser (Maezawa command set)
  contra_parser.py    — Contra parser (different DX/percussion)
  frame_ir.py         — frame IR with envelope model
  midi_export.py      — MIDI from frame IR (CC11 automation)
  spec.md             — command format + per-game differences table
scripts/
  trace_compare.py    — frame-level validation vs APU trace
  render_wav.py       — Python NES APU synth (pulse/tri/noise)
  full_pipeline.py    — ROM → MIDI → WAV → MP4 pipeline
  generate_project.py — REAPER .rpp generator
studio/jsfx/          — ReapNES_APU.jsfx synth
references/nes-contra-us/ — annotated Contra disassembly
AllNESROMs/           — ROM collection (GoodNES USA set)
.claude/rules/        — path-specific rules (load only when relevant)
.claude/skills/nes-rip.md — /nes-rip extraction skill
```

## Key Technical Decisions

**Envelope model (CV1)**: Two-phase parametric. `fade_start` frames of
1/frame decay, hold, then `fade_step` frames of 1/frame release at end.
Triangle: $4008 linear counter, sounds `(reload+3)/4` frames.

**Octave mapping**: `BASE_MIDI_OCTAVE4 = 36` (C2). Pulse standard,
triangle subtracts 12. Trace adds +12 to pulse freq-to-MIDI.

**CV1 vs Contra**: Same note/octave/repeat commands. Different DX byte
count (2 vs 3/1), percussion (inline E9/EA vs separate DMC channel),
volume envelopes (parametric vs lookup tables), ROM layout (mapper 0
vs mapper 2 bank-switched).

## Priority Next Steps

1. **Contra volume envelope tables** — extract `pulse_volume_ptr_tbl`
   from ROM (disassembly bank1.asm lines 23-95), apply per-frame in IR
2. **Build `rom_identify.py`** — deterministic ROM analysis (mapper,
   period table, driver signature). Saves 3-4 prompts per new game.
3. **Per-game JSON configs** — replace hardcoded addresses with config files
4. **Test Super C, TMNT** — use Per-Game Parser Checklist

## Context Engineering

CLAUDE.md is 31 lines (compressed from 120). Rules and checklists are
in `.claude/rules/` as path-specific files that load only when relevant.
Full mistake narratives in `docs/MISTAKEBAKED.md`. Deckard boundary
analysis in `docs/DECKARDCONTRASTAGE2.md`.

## Documentation Map

| Doc | Purpose |
|-----|---------|
| `docs/HANDOVER.md` | This file |
| `docs/HANDOVER_FIDELITY.md` | CV1 envelope model details |
| `docs/CONTRAVERSIONS.md` | Contra v1-v4 version history |
| `docs/CONTRALESSONS.md` | Contra architecture and lessons |
| `docs/DECKARDCONTRASTAGE2.md` | Deterministic vs LLM boundary map |
| `docs/CONTRACONTEXTENGINEERING.md` | Context file restructure rationale |
| `docs/MISTAKEBAKED.md` | What warnings are baked where and why |
| `docs/LATESTFIXES.md` | All CV1 fixes with evidence |
| `docs/VERSION4STORY.md` | CV1 v4 session narrative |
| `docs/OCTAVETOOLOWONPULSE.md` | Octave mapping investigation |
| `docs/MOVINGONTOCV2.md` | CV2 investigation (dead end) |
| `extraction/drivers/konami/spec.md` | Command format + per-game table |
