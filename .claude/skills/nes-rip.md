---
name: nes-rip
description: "Adaptive orchestrator: process any NES game through the best available extraction path. Assesses what we have (traces, ROM, parser, nesmdb data), determines what's possible, and executes. Works on ANY publisher — Konami, Capcom, Sunsoft, anything."
user_invocable: true
---

# NES Adaptive Orchestrator

Assess, route, execute. Works on any NES game regardless of publisher or driver.

## Trigger

User says a game name, "process [game]", provides a capture, or asks for status.

## Core Principle

There is no single pipeline. There are CAPABILITIES that unlock PATHS.

```
CAPABILITIES (what we might have):
  trace          — Mesen APU capture CSV
  rom            — NES ROM file
  nesmdb         — reference data in nesmdb database
  parser         — known driver with existing parser code
  disassembly    — annotated source for this game or related game
  manifest       — existing game manifest with prior work

PATHS (what we can do):
  trace_render   — render WAV directly from trace (ANY game)
  trace_midi     — extract MIDI with CC11 envelopes from trace (ANY game)
  sfx_separate   — split music from gameplay SFX (ANY game with trace)
  nesmdb_render  — render labeled reference tracks (games in database)
  rom_parse      — parse music from ROM data (games with known driver)
  rom_scan       — extract ROM facts (ANY game with ROM)
```

## Instructions

### 1. Assess current state

Read `extraction/manifests/{game}.json` if it exists.
Check for: traces, ROM, nesmdb data, parser availability.

Report what we HAVE and what we CAN DO:

```
Game: Bionic Commando
  ROM: ✓ (mapper 1, Capcom)
  Traces: ✓ capture1 (64.8s, Stage 1)
  nesmdb: ✗ not in database
  Parser: ✗ no Capcom driver parser
  Disassembly: ✗ none available

Available paths:
  ✓ trace_render (already done)
  ✓ trace_midi (can generate)
  ✓ sfx_separate (already done)
  ✗ nesmdb_render (not in database)
  ✗ rom_parse (no Capcom parser)
  ✓ rom_scan (can extract ROM facts)

Next suggested action: capture more tracks
```

### 2. Route to the best available path

**If user provides a new capture:**
→ Archive trace → render WAV → segment → separate SFX → generate MIDI with envelopes
→ Ask user to identify tracks
→ This works for ANY game, ANY publisher

**If user says "find tracks" or "extract all":**
→ Check: do we have a parser for this driver?
  YES → ROM parse path (scan → find pointer table → validate → batch)
  NO → Trace extraction path (need captures of each track)
→ Check: is it in nesmdb?
  YES → Render references so user knows what to capture
  NO → List known track names from training knowledge (with caveat)

**If user says "scan the ROM":**
→ Run ROM analysis regardless of publisher
→ Report: mapper, period table (if found), command signatures, music banks
→ Update manifest with VERIFIED facts

**If user says "improve [track]":**
→ Check what exists for that track
→ Can re-render with different SFX threshold
→ Can re-extract MIDI with adjusted envelope parameters
→ Can produce per-channel stems

### 3. What to do when there's NO parser

For non-Konami games (Capcom, Sunsoft, etc.):

```
TIER 1: Trace-based extraction (ALWAYS available)
  - Render WAV from trace (frame-accurate, game-agnostic)
  - Generate MIDI with CC11 volume envelopes from trace
  - Separate SFX from music using pitch-jump heuristic
  - Produce per-channel stems
  - Detect loop points via melody comparison
  OUTPUT: WAV + MIDI + stems per captured track

TIER 2: Reference-assisted (if nesmdb available)
  - Render all nesmdb tracks as labeled references
  - Cross-reference trace durations with nesmdb durations
  - User matches captures to track names
  OUTPUT: labeled track library

TIER 3: ROM parsing (ONLY if parser exists)
  - Maezawa family: use existing CV1/Contra parsers
  - Other families: would need new parser development
  - NEVER attempt ROM parsing for unknown drivers
  OUTPUT: full parsed soundtrack with per-note control
```

Most games will use Tier 1. That's fine. Tier 1 produces
accurate audio that sounds like the game.

### 4. Manage the capture queue

When the user wants a full soundtrack but we're in Tier 1:

```
Known tracks for [game]:
  ✓ Stage 1 — captured (capture1.csv)
  ✗ Stage 2 — need capture
  ✗ Boss — need capture
  ✗ Title — need capture
  ✗ Ending — need capture

"Capture [next track] in Mesen and tell me when saved."
```

Track each capture in the manifest. Build the soundtrack
incrementally across captures.

### 5. Enforcement (still applies)

- Trace renders: ALWAYS use per-frame volume from trace (CC11)
- nesmdb renders: ALWAYS validate frame rate from pickle
- SFX separation: ALWAYS produce both versions for user to compare
- Output versioning: NEVER overwrite (v1, v2, v3)
- ROM parser path: STILL requires validation gate before batch

But these are per-PATH enforcements, not global sequential gates.
A trace-only extraction doesn't need a pointer table.
A ROM parse does need validation. Different paths, different rules.

### 6. After every action

Update manifest. Report: what was done, what's available, what's next.
Keep it to 3-4 lines — don't dump the full state every time.
