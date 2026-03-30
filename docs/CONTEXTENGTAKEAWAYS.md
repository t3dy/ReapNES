# Context Engineering Takeaways

How to progressively reveal what the LLM needs to know about NES
music data structures, and how to modify our init files to make
this automatic.

## The Problem We Kept Hitting

Every new session starts with the LLM reading CLAUDE.md, HANDOVER.md,
and various docs. But the LLM doesn't know WHICH knowledge matters
for the CURRENT task until it's already mid-task and failing.

Examples of wasted context:
- CV1 envelope model details loaded when working on Gradius (useless)
- Maezawa command format loaded when Gradius turned out to be non-Maezawa
- All 8 MISTAKEBAKED rules loaded when only 2 are relevant to the task

Examples of MISSING context that caused failures:
- Contra sound_table_00 format not loaded when searching Super C
- UNROM banking model not loaded when computing ROM offsets
- nesmdb frame rate (24fps not 60fps) not loaded when rendering

## Progressive Revelation Strategy

### Layer 0: Always loaded (CLAUDE.md, <500 words)

What the project IS and the current priority. No technical details.

```
- Pipeline: ROM → parser → frame IR → MIDI → REAPER/WAV
- Current focus: expanding to new NES ROMs
- Workflow: capture trace FIRST, then ROM scan, then parse
- Hard rule: trace is ground truth
- Hard rule: one track validated before batch
- Hard rule: version all outputs, never overwrite
```

### Layer 1: Game-specific (manifest JSON, loaded per game)

When working on a specific game, load its manifest. The manifest
contains ALL verified facts and known unknowns:

```json
{
  "game": "super_c",
  "mapper": 2,
  "driver_family": "contra_variant",
  "driver_family_confidence": "high",
  "period_table_address": "NOT_FOUND",
  "pointer_table_address": "UNKNOWN",
  "sound_bank": "UNKNOWN",
  "vibrato_detected": true,
  "traces_captured": ["capture1.csv"],
  "tracks_identified": {"seg02": "Thunder Landing (Stage 1)"}
}
```

### Layer 2: Driver-specific (loaded when driver family is known)

Once the manifest says `driver_family: "maezawa"` or `"contra_variant"`,
load the relevant driver documentation:

For Maezawa family:
- Note encoding: pitch×16 + duration in low nibble
- Octave commands: E0-E4 set current octave
- DX instrument: D0-DF with variable byte count
- Control flow: FE repeat, FD subroutine, FF end
- Period table: 12 entries, specific tuning values

For Contra variant specifically:
- DX reads 3 bytes (pulse) or 1 byte (triangle)
- Lookup table envelopes (not parametric)
- DMC percussion on separate channel
- sound_table_00 format: 3-byte triples with slot encoding
- Vibrato code present but per-game activation

For unknown drivers:
- Load NOTHING about Maezawa. Start fresh.
- Load only: how to capture trace, how to render WAV

### Layer 3: Task-specific (loaded for the current operation)

When parsing: load the command spec, parser code structure
When trace-comparing: load trace_compare.py usage
When searching ROM: load pointer table search patterns
When debugging: load the debugging protocol (dump trace first,
one hypothesis at a time)

### Layer 4: Mistake context (loaded ONLY at decision points)

The 8 MISTAKEBAKED rules should fire ONLY when relevant:
- Starting a new game? → "Same driver ≠ same ROM layout"
- Writing a parser? → "Read the disassembly before guessing"
- Changing octave mapping? → "Triangle is 1 octave lower"
- Generating output? → "Version the files"

Don't load all 8 rules at session start. Load the 1-2 rules
that apply to the current task.

## How to Modify Init Files

### CLAUDE.md changes

Current CLAUDE.md is 31 lines of compressed rules plus a workflow
section. It tries to be everything at once. Change it to:

```
1. Project identity (3 lines)
2. Current priority (2 lines)
3. Workflow (5 lines: capture → scan → parse → validate → batch)
4. Hard invariants (5 lines: trace=truth, version files, etc.)
5. "For game-specific context, read extraction/manifests/{game}.json"
6. "For driver-specific context, read extraction/drivers/{family}/spec.md"
```

### .claude/rules/ structure

Currently rules load by PATH (files in the working directory trigger
specific rules). This is the right mechanism but the rules need to
be reorganized by LAYER:

```
.claude/rules/
  always.md           — Layer 0: universal invariants
  game_manifest.md    — Layer 1: "read the manifest for this game"
  maezawa_driver.md   — Layer 2: Maezawa encoding rules
  contra_driver.md    — Layer 2: Contra variant specifics
  unknown_driver.md   — Layer 2: rules for unknown drivers
  parsing.md          — Layer 3: parser-specific rules
  debugging.md        — Layer 3: debugging protocol
  rom_scanning.md     — Layer 3: ROM search rules (2 attempts max)
  output.md           — Layer 3: versioning, file naming
```

### Manifest as the context anchor

The manifest JSON should be the SINGLE source of truth for what
we know about a game. Every session should start by reading it.
Every discovery should update it. No fact should exist only in
a prose document — if it's verified, it goes in the manifest.

The manifest replaces hypothesis documents. Instead of writing
HYPOTHESES_GRADIUS.md with predictions, we write
`extraction/manifests/gradius.json` with verified facts and
explicit "UNKNOWN" fields.

## What Changes in Practice

### Before (current approach)
1. Load all docs at session start
2. LLM has 5000 tokens of context about CV1 envelopes when
   working on Gradius
3. LLM writes hypothesis docs from training knowledge
4. LLM tries to parse with wrong assumptions
5. User corrects, LLM adjusts

### After (progressive revelation)
1. Load CLAUDE.md (200 tokens) + manifest JSON (100 tokens)
2. Manifest says `driver_family: "unknown"` → load unknown_driver.md
3. Capture trace, render WAV, user identifies track
4. ROM scan finds no Maezawa table → manifest stays `"unknown"`
5. LLM knows NOT to load Maezawa rules, NOT to try Maezawa parser
6. Decision: use debugger or move to next game

The LLM never wastes context on irrelevant driver details.
The LLM never writes hypotheses that contradict the manifest.
The manifest enforces what the LLM should and shouldn't know.
