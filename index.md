---
layout: default
title: Home
---

# ReapNES

**Extract, validate, and reproduce NES game music at frame-level fidelity.**

ReapNES is a reverse engineering pipeline that extracts actual musical data — notes, durations, volume envelopes, timing — directly from NES ROM files. Every extraction is validated against Mesen 2 APU trace captures: frame-by-frame comparison of our output against real hardware register writes.

Two complete Konami soundtracks have been extracted so far. The methodology is designed to generalize across the entire NES library.

---

## Current Status

| Game | Tracks | Pulse Fidelity | Status |
|------|--------|----------------|--------|
| **Castlevania 1** (1986) | 15/15 | 0 mismatches / 1792 frames | COMPLETE |
| **Contra** (1988) | 11/11 | 96.6% volume match | IN PROGRESS |
| 15+ Konami titles | 0 | Untested | OPEN |

---

## How It Works

```
 .nes ROM file
      |
      v
 +-----------+     +-----------+     +-------------+
 |  Parser   | --> |  Frame IR | --> | MIDI Export  |
 | (per-game)|     | (envelope |     | (CC11 auto-  |
 |           |     |  shaping) |     |  mation)     |
 +-----------+     +-----------+     +-------------+
                                           |
                              +------------+------------+
                              |            |            |
                              v            v            v
                          WAV render   REAPER .rpp   MP4 video
```

The pipeline has three layers:
- **Engine layer** — per-game parsers read the sound driver command stream from ROM
- **Data layer** — the frame IR converts events into per-frame hardware state, dispatched through a DriverCapability schema
- **Hardware layer** — output stages (MIDI, WAV, REAPER) consume the IR without knowing which game produced it

---

## Documentation

### Architecture and Reference

| Document | Description |
|----------|-------------|
| [Driver Model](docs/DRIVER_MODEL) | The Konami Maezawa sound driver as a three-layer system |
| [Game Matrix](docs/GAME_MATRIX) | Per-game status: what's decoded, what's untested, what's blocked |
| [Command Manifest](docs/COMMAND_MANIFEST) | Byte-level command reference ($00-$FF) with per-game variations |
| [Invariants](docs/INVARIANTS) | Hard rules discovered through debugging — with evidence and tests |
| [Unknowns](docs/UNKNOWNS) | Open questions ranked by priority — the bounty board |

### Workflow and Methodology

| Document | Description |
|----------|-------------|
| [Trace Workflow](docs/TRACE_WORKFLOW) | How to capture a Mesen trace and validate against it |
| [Research Log](docs/RESEARCH_LOG) | Chronological record of hypotheses, experiments, and verdicts |
| [Mesen Capture Guide](docs/MESENCAPTURE) | Step-by-step Mesen 2 APU trace capture |
| [How to Read a Capture](docs/HOWTOREADACAPTURE) | Reading APU capture files (for humans and agentic systems) |
| [How to Be More Flexible](docs/HOWTOBEMOREFLEXIBLE) | Lessons for anticipating the unexpected |

### Game-Specific

| Document | Description |
|----------|-------------|
| [Contra Goal Line](docs/CONTRAGOALLINE) | How close the Contra extraction is and what remains |
| [Contra vs Trace](docs/CONTRACOMPARISON) | What the Mesen trace proved vs our assumptions |
| [Contra Lessons to CV1](docs/CONTRALESSONSTOCV1) | Cross-game debugging: how Contra fixed a CV1 bug |
| [Konami Takeaways](docs/KONAMITAKEAWAY) | What we learned about Konami's music coding |
| [Musical Parameters](docs/CHECKLIST) | Every parameter that affects the sound |
| [Note Durations](docs/NOTEDURATIONS) | Five systems that control perceived note length |
| [Prior Art](docs/DONEBEFORE) | What exists already and how this project differs |

### Process

| Document | Description |
|----------|-------------|
| [Swarm Analysis](docs/SWARMPERFORMED1) | How parallel AI agents performed on documentation tasks |
| [Agent Roster](docs/SWARMAGENTIDS) | The 10-agent swarm deployment and results |

---

## For ROM Hackers

### How to start on a new game

The methodology is **trace-first**: capture hardware ground truth before writing any parser code, then iterate against it. The full walkthrough is in [Trace Workflow](docs/TRACE_WORKFLOW). The short version:

1. Identify the ROM with `rom_identify.py`
2. Find a disassembly (check GitHub)
3. Capture a Mesen APU trace
4. Parse one track
5. Compare frame-by-frame
6. Fix one thing at a time
7. Do not batch-extract until the reference track passes

### Pick an unknown

There are dozens of Konami NES titles using variants of the Maezawa sound driver that no one has documented. The [Unknowns](docs/UNKNOWNS) page lists open questions — unexplained engine behaviors, untested games, and partially understood subsystems. Each one is an opportunity.

### What we learned the hard way

Two complete extractions produced a detailed record of mistakes, false assumptions, and corrections. The [Research Log](docs/RESEARCH_LOG) covers the full chronology. Key lessons:

- Same driver family does not mean same ROM layout
- Same period table does not prove same driver
- Automated tests miss systematic errors (an entire octave off shows zero mismatches)
- Surface similarity between games is the trap, not the shortcut
- The Mesen trace is the only reliable check for absolute accuracy

---

## The Bigger Picture

The NES library contains hundreds of games with undocumented sound engines. Most NES music preservation relies on NSF rips — useful for listening, but opaque for analysis, arrangement, or remix. Extracting the actual musical data requires reverse engineering each game's sound driver.

This project demonstrates a methodology that generalizes: trace-first validation, per-game manifests, invariant-aware pipelines, and driver capability schemas. The Konami Maezawa family alone covers a significant portion of the late-1980s NES catalog. The tools and workflow here are designed to make each subsequent game faster than the last.

---

[View on GitHub](https://github.com/t3dy/ReapNES)
