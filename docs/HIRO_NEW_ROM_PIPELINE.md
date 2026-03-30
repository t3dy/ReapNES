# HiroPlantagenet Analysis: New ROM Extraction Pipeline

Applied to the prompt: "Bake all lessons for how to operate more
efficiently, smoothly, flexibly into the environment."

Source lessons: HOWGRADIUSWENTPREANDPOSTCAPTURE.md, TRACKINGITOUT.md,
SUPERCONMAEZAWA.md, DECKARD_SUPERC_BOUNDARIES.md, MISTAKEBAKED.md,
FAILURE_MODES.md, NEW_ROM_WORKFLOW.md.

---

## 1. Intent Atoms

| # | Goal | Tag |
|---|------|-----|
| 1 | Define the capture-first workflow as the standard operating procedure | PIPELINE |
| 2 | Codify what's deterministic vs what needs judgment | CLASSIFICATION |
| 3 | Encode per-game configuration into manifest JSON instead of code | ONTOLOGY |
| 4 | Build reusable trace→WAV→segment tooling that works on any game | PIPELINE |
| 5 | Establish validation gates (trace comparison) before batch extraction | META-CONTROL |
| 6 | Kill the hypothesis-before-ROM-scan pattern | META-CONTROL |
| 7 | Formalize the SFX separation and track boundary algorithms | PIPELINE |
| 8 | Make nesmdb rendering correct by default (frame rate, pitch) | PIPELINE |

## 2. Conflicts & Gaps

CONFLICTS:
- The existing CLAUDE.md workflow says "run rom_identify.py first"
  but the lesson from Gradius/Super C says "capture trace first."
  These need to be reconciled: the trace IS the identification step
  for unknown drivers. rom_identify.py is only useful for known
  Maezawa-family games.

MISSING DECISIONS:
- When should we give up on a game? (CV2 Fujio driver was declared
  dead end, but later the Antigravity session extracted 7 tracks.)
- What's the minimum capture length needed to identify a track?
  (1 loop? 30 seconds? Until user says "enough"?)

IMPLICIT ASSUMPTIONS:
- The user has Mesen2 installed and knows how to capture APU traces
- nesmdb data exists for most Konami NES games
- The Contra disassembly documents the shared engine used by Super C

## 3. Layer Architecture

```
Layer 1: CAPTURE & RENDER
  Purpose: Get listenable audio from any NES ROM in under 10 minutes.
  Atoms: #1, #4, #8
  Reasoning mode: deterministic
  Depends on: nothing

Layer 2: IDENTIFY & SEGMENT
  Purpose: Name the tracks and find boundaries.
  Atoms: #1, #7
  Reasoning mode: deterministic + human ear
  Depends on: Layer 1

Layer 3: ROM ANALYSIS
  Purpose: Find driver structure, period table, pointer table.
  Atoms: #2, #3, #6
  Reasoning mode: deterministic (scanning) + heuristic (scoring)
  Depends on: Layer 1 (trace periods guide the scan)

Layer 4: PARSE & VALIDATE
  Purpose: Parse one track from ROM, compare to trace, iterate.
  Atoms: #5
  Reasoning mode: deterministic
  Depends on: Layer 2 (know which track), Layer 3 (pointer table)

Layer 5: BATCH EXTRACT
  Purpose: Parse all tracks, render, version outputs.
  Atoms: #5
  Reasoning mode: deterministic
  Depends on: Layer 4 (one track validated)
```

## 4. Rewritten Prompts (as operational rules)

### === LAYER 1: CAPTURE & RENDER ===

OBJECTIVE: Produce listenable WAV from any NES game in under 10 minutes.

SCOPE CONSTRAINTS:
- DO: capture Mesen APU trace, render trace→WAV, render nesmdb if available
- DO NOT: scan the ROM, write hypotheses, guess the driver family

INPUTS:
- Mesen2 capture.csv from user
- nesmdb exprsco files (if game is in database)

OUTPUT CONTRACT:
```
output/{GameName}/wav/{game}_capture{N}_full_v1.wav     — full trace render
output/{GameName}/wav/nesmdb/{game}_{num}_{name}.wav    — all nesmdb tracks
extraction/traces/{game}/capture{N}.csv                 — archived trace
```

DECISION RULES:
- nesmdb render frame rate = `rate` field from pickle (usually 24fps, NOT 60fps)
- nesmdb pitch: validate median pitch is in MIDI 36-84 range for pulse channels.
  If median > 80, flag for manual pitch offset check.
- Always mono, 44100Hz, 16-bit WAV
- Never overwrite: v1, v2, v3 versioning

### === LAYER 2: IDENTIFY & SEGMENT ===

OBJECTIVE: Split the trace into individual tracks and name them.

SCOPE CONSTRAINTS:
- DO: silence detection, melody loop comparison, duration cross-reference
- DO NOT: attempt ROM parsing or driver identification

INPUTS:
- Trace WAV from Layer 1
- nesmdb track list with durations
- User identification ("that's Stage 1")

OUTPUT CONTRACT:
```
output/{GameName}/wav/segments/{game}_seg{NN}_v1.wav    — per-segment WAV
Segment table:
  | Seg | Frames     | Duration | Silence gap | User ID        | nesmdb match    |
  |-----|------------|----------|-------------|----------------|-----------------|
  | 01  | 0-442      | 7.4s     | 5.7s after  | "intro SFX"   | —               |
  | 02  | 442-4076   | 60.6s    | —           | "Thunder Land" | 56.7s match     |
```

DECISION RULES:
- Silence gap ≥ 15 frames (0.25s) = track boundary candidate
- Silence gap 5-14 frames = musical rest, NOT a boundary
- Loop detection: compare first 20 note transitions of adjacent segments.
  If ≥18/20 match, it's a loop, not a new track.
- nesmdb duration match: ±15% = probable match. >2x = looping.

### === LAYER 3: ROM ANALYSIS ===

OBJECTIVE: Find the driver structure and pointer table address.

SCOPE CONSTRAINTS:
- DO: period table scan, command signature scan, pointer table brute-force
- DO NOT: write hypothesis documents before scanning. Write findings docs AFTER.

INPUTS:
- ROM file
- Trace period values (from Layer 1 — tells us what periods the game uses)
- Contra disassembly (reference for Maezawa-family games)

OUTPUT CONTRACT:
```
extraction/manifests/{game}.json with VERIFIED fields:
{
  "game": "...",
  "mapper": N,                         // from ROM header, VERIFIED
  "prg_banks": N,                      // from ROM header, VERIFIED
  "period_table_address": "0xNNNN",    // from ROM scan, or "NOT_FOUND"
  "period_table_format": "...",        // "contiguous_16bit" | "split_lohi" | "not_found"
  "period_table_tuning": "...",        // "maezawa_exact" | "contra_variant" | "unknown"
  "pointer_table_address": "0xNNNN",   // from brute-force, STATUS: "candidate" | "verified"
  "sound_bank": N,                     // from ROM scan or "UNKNOWN"
  "driver_family": "...",              // "maezawa" | "contra_variant" | "unknown"
  "driver_family_confidence": "...",   // "verified" | "high" | "low" | "rejected"
  "vibrato_detected": true/false,      // from trace analysis
  "tracks_found": N,
  "status": "..."                      // "parsing" | "validated" | "dead_end"
}
```

DECISION RULES:
- Run rom_identify.py equivalent scans (header, period table, signatures)
  BEFORE writing any prose about the game.
- If period table not found as contiguous block: check split lo/hi, check
  Contra-variant tuning (1358/1142/1078), check extended tables.
- Brute-force pointer table: require 3+ UNIQUE ascending channel pointers,
  targets must contain E0-E4 within first 16 bytes. Validate top candidate
  against trace before marking as "verified."
- If no Maezawa signatures found (Gradius case): mark driver_family as
  "unknown", status as "dead_end" for current pipeline, move on.

### === LAYER 4: PARSE & VALIDATE ===

OBJECTIVE: Parse one track from ROM and validate against trace.

SCOPE CONSTRAINTS:
- DO: parse exactly ONE track, render to MIDI/WAV, compare to trace
- DO NOT: batch extract before this gate passes

INPUTS:
- Manifest from Layer 3
- Trace from Layer 1
- User-identified track from Layer 2

OUTPUT CONTRACT:
```
Validation report:
  Track: {name}
  Pitch matches: {N}/{total} ({percent}%)
  Volume matches: {N}/{total} ({percent}%)
  Duration matches: {N}/{total} ({percent}%)
  User listening verdict: PASS / FAIL / CLOSE

  If FAIL: first mismatch at frame {N}, channel {ch}
           Expected: {trace_value}, Got: {parsed_value}
```

DECISION RULES:
- Pitch match threshold: ≥95% or FAIL
- If pitch matches but sounds wrong: octave mapping error (check ±12)
- If zero mismatches but sounds wrong: systematic error, user must
  compare to game audio (CLAUDE.md rule 6)
- ONE hypothesis at a time when debugging. Dump trace frames first.

### === LAYER 5: BATCH EXTRACT ===

OBJECTIVE: Parse all tracks, produce complete soundtrack package.

SCOPE CONSTRAINTS:
- DO: parse all tracks, render MIDI + WAV + REAPER projects
- DO NOT: start until Layer 4 passes

INPUTS:
- Verified manifest from Layer 4
- Track list from Layer 2 / pointer table

OUTPUT CONTRACT:
```
output/{GameName}/midi/{game}_track_{NN}_{name}.mid
output/{GameName}/wav/{game}_track_{NN}_{name}.wav
output/{GameName}/reaper/{game}_track_{NN}_{name}.rpp
output/{GameName}/{game}_youtube_description.txt
```

DECISION RULES:
- Version all output files (v1, v2, ...)
- Never overwrite a file the user has tested
- Render per-channel stems if requested
- Generate YouTube description with track list and timestamps

## 5. Execution Notes

**Deterministic layers:** 1 (trace render), 2 (silence detection),
4 (parse+compare), 5 (batch). These are code. Build once, reuse.

**Judgment-required layers:** 2 (user track naming), 3 (driver
family classification, pointer table scoring). Always validate
against deterministic output.

**Human review required:** Layer 2 (track identification), Layer 4
(listening test after parse).

**Caching:** nesmdb renders rarely change — render once per game,
store in nesmdb/ subfolder. Manifests are versioned per-game and
accumulate verified facts over sessions.

**Parallelism:** Layer 1 (trace render) and Layer 3 (ROM scan) can
run in parallel. Layer 2 requires user input, so it blocks.

**The kill switch:** If Layer 3 finds no Maezawa signatures AND no
period table of any kind, mark as "dead_end" and move to the next
game. Don't spend 3+ sessions on unknown drivers when there are
known-family games waiting (MISTAKEBAKED.md lesson: CV2 was a
dead end that cost 4 prompts).

---

## Baking Into the Environment

These rules should be encoded in:

1. **CLAUDE.md** — update the "Workflow: New Game" section to
   say "capture trace FIRST" instead of "run rom_identify.py first"
2. **`.claude/rules/extraction.md`** — add the Layer 1-5 gates
3. **`extraction/manifests/template.json`** — blank manifest with
   all fields from Layer 3's output contract
4. **Scripts** — the trace→WAV renderer, silence detector, and
   nesmdb renderer should be standalone scripts, not inline python
