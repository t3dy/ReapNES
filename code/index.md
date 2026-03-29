---
layout: default
title: "Annotated Source Code"
---

# Annotated Source Code

The core extraction pipeline, annotated as a tutorial for ROM hackers. Every function has inline comments explaining what it does, why it does it that way, and what bugs were discovered here.

These are the actual working source files — the same code that produces zero-mismatch extractions for Castlevania 1 and 96.6% volume accuracy for Contra. Comments prefixed with `# TUTORIAL:` were added for this guide.

---

## The Pipeline

The files are listed in pipeline order — data flows from parser through frame IR to MIDI export, with trace comparison as the verification layer.

| File | Role | Lines | Layer |
|------|------|-------|-------|
| [parser.py](parser) | CV1 parser + shared event types | 665 | Data + Engine |
| [contra_parser.py](contra_parser) | Contra-specific parser | 532 | Data |
| [frame_ir.py](frame_ir) | Frame IR + volume envelope strategies | 544 | Engine + Hardware |
| [midi_export.py](midi_export) | MIDI export with CC11 automation | 354 | Output |
| [trace_compare.py](trace_compare) | Trace validation tool | 327 | Verification |

## How to Read These

Each page has:
1. **Tutorial intro** — what the file does, what bugs lived here, and how it connects to the pipeline
2. **Annotated source** — the full source code with `# TUTORIAL:` comments added inline
3. **Key concepts** — bullet summary of the most important things to understand

The annotations focus on **why**, not what. The code itself says what it does. The tutorial comments explain the reasoning, the bugs that were found, and the invariants that prevent regressions.

---

## Also See

- [Using LLMs for NES RE](../docs/LLM_METHODOLOGY) — how AI assistants were used in this project
- [Invariants](../docs/INVARIANTS) — the hard rules encoded in tests
- [Research Log](../docs/RESEARCH_LOG) — the chronological record of discoveries
