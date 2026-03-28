# Extraction Engine -- Claude Code Instructions

Read this file when working on extraction/, drivers/, or ROM analysis.

---

## Core Principle

Treat NES commercial game music as **driver-specific code plus data**, not as
a universal score format. Every driver family has its own command bytes, its
own instrument table format, and its own playback behavior.

## Fidelity Methodology

The driver is a **stateful frame-based interpreter**. Do not treat it as a
simple parse-and-convert format. The canonical time model is **NES frames**
(1/60s NTSC). Only convert to MIDI ticks at the final export stage.

The APU emulator trace (`extraction/traces/castlevania/stage1.csv`) is **ground truth**.
All extraction work must be validated against the trace, not just by ear.

Tools:
- `scripts/trace_compare.py` — frame-by-frame diff against trace
- `extraction/drivers/konami/frame_ir.py` — frame-accurate IR with envelope model
- `docs/FidelityAudit_CV1.md` — current audit of all fidelity risks
- `docs/HANDOVER_FIDELITY.md` — current state and next steps for fidelity work

## Evidence Hierarchy (never violate)

1. **Manually verified reverse-engineering findings** -- highest authority
2. **Exact static parser extraction** from known command format
3. **Exact runtime observation** from APU trace
4. **Reconciled inference** supported by both static and dynamic evidence
5. **Provisional inference** from one source only
6. **Speculative research notes** -- lowest tier

Never allow lower-tier evidence to overwrite higher-tier without explicit review.

## Confidence Policy

Every extracted object carries:
- `source_type`: static | dynamic | reconciled | manual | heuristic | provisional
- `confidence.score`: 0.0-1.0
- `confidence.reason`: why this confidence level
- `evidence_refs`: pointers to supporting evidence

## Terminology Discipline

- Do NOT call something an "instrument preset" unless the driver truly supports named instrument definitions
- Do NOT call inferred timing "tempo" without marking it as a hypothesis
- Do NOT use "note" for raw APU period values -- use "period" until symbolic reconstruction confirms note mapping
- Do NOT flatten pattern/subroutine structure prematurely

## Three-Pipeline Architecture

- **Pipeline A (Static):** ROM -> driver identification -> sequence parser -> symbolic model
- **Pipeline B (Dynamic):** ROM/NSF -> emulator APU trace -> normalized event stream
- **Pipeline C (Reconciliation):** Static <-> dynamic alignment -> confidence adjustment

## Driver Family Structure

Each driver family in `drivers/{family}/` contains:
- `spec.md` -- formal specification of the command format (update as bytes are decoded)
- `NOTES.md` -- research notes and open questions
- `identify.py` -- code signatures and detection heuristics
- `parser.py` -- sequence decoder and song parser
- `fixtures/` -- test data
- `tests/` -- driver-specific tests

## Key References (Don't Reinvent)

- **Contra disassembly** (`references/nes-contra-us/docs/Sound Documentation.md`) -- Maezawa driver architecture, same family as Castlevania 1
- **CAP2MID** (`docs/WHEELSNOTTOREINVENT.md` section 1) -- Capcom NES command format fully decoded. Port to Python, don't re-derive.
- **nesmdb apu.py** -- APU register bitmask definitions for all 38 functions. Copy into our code.
- **nesmdb CC11/CC12** -- MIDI encoding standard for NES performance data. Adopt.
- **FamiStudio NotSoFatso** -- APU emulation for Pipeline B. Study, don't rebuild.

## MIDI Output Contract

Extraction MIDI output MUST conform to `docs/REQUIREMENTSFORMIDI.md`:
- Exactly 4 channels (0-3)
- Monophonic per channel
- CC11 for velocity changes, CC12 for duty cycle changes
- Tempo derived from driver, not guessed
- Metadata track with game, song, source, confidence

## Current Targets

### Konami Maezawa Driver (Primary)
- Games: Castlevania 1, Contra, Super C, TMNT, Goonies II, Gradius II
- Reference: Contra disassembly (fully annotated sound engine)
- Key doc: romhacking.net #150 (Castlevania Music Format by Sliver X)
- Status: Architecture known from Contra, CV1 byte format partially documented

### Capcom NES Driver (Secondary)
- Games: Mega Man series, DuckTales, Chip 'n Dale
- Reference: CAP2MID by turboboy215 (complete C implementation)
- Status: Fully decoded by CAP2MID. Port to Python.
