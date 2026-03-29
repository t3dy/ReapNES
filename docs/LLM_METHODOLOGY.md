---
layout: default
title: "Using LLMs to Reverse Engineer NES Music"
---

# Using LLMs to Reverse Engineer NES Music

A practical guide for ROM hackers considering LLMs as reverse engineering
assistants. Based on extracting complete soundtracks from Castlevania 1
(15 tracks, zero pitch mismatches) and Contra (11 tracks, 96.6% volume
accuracy) using Claude as the primary RE tool, with Mesen traces as
ground truth and annotated disassemblies as reference.

This is not a hype piece. LLMs are genuinely useful for NES music RE,
but they fail in specific and predictable ways. This document covers
both sides honestly.

---

## Why LLMs Work for This

NES sound engine reverse engineering sits at an unusual intersection of
tasks: reading 6502 assembly, understanding byte-level data formats,
correlating hardware traces with code, writing parsers, and iterating
on hypotheses about engine behavior. No single tool covers all of these
well. An LLM covers most of them adequately and some of them very well.

The key insight is that LLM reasoning alone is not enough. What makes
this work is the combination of LLM reasoning with deterministic tools:

- **Mesen APU trace capture** provides frame-level hardware ground truth
- **pytest** encodes discovered invariants as regression tests
- **git** versions every output file so comparisons are always possible
- **trace_compare.py** produces machine-readable diffs between extraction
  and hardware

The LLM sits in the middle: it reads the disassembly, writes the parser,
interprets the trace diff, proposes a fix, applies it, and re-runs the
comparison. This creates a feedback loop that converges on correctness --
but only because the trace provides an external oracle that the LLM
cannot argue with.

Without the trace, the LLM will confidently produce wrong output that
sounds plausible. More on this below.

---

## What LLMs Are Good At

### Reading Annotated Disassembly and Extracting Command Semantics

An annotated disassembly like the Contra source
(`references/nes-contra-us/`) contains thousands of lines of 6502
assembly with human-written labels. An LLM can read this and extract
structured information: "the DX command reads 3 extra bytes for pulse
channels, 1 for triangle," or "the EC command applies a semitone offset
to all subsequent note lookups."

In our project, reading the Contra disassembly took the LLM about one
prompt. It identified the DX byte count difference from CV1, the
separate DMC percussion channel, and the volume envelope lookup table
structure. Doing this manually would take a human several hours of
cross-referencing labels and tracing execution paths.

### Writing Parsers from Byte Format Specifications

Given a command format specification -- "bytes $00-$BF are notes, $C0-$CF
are rests, $D0-$DF are tempo/instrument changes, $E0-$E4 are octave
shifts, $FE is repeat, $FF is end" -- an LLM can produce a working
parser in a single response. The parser will handle the basic command
dispatch loop, byte extraction, and event emission.

The CV1 parser (`extraction/drivers/konami/parser.py`) was bootstrapped
this way in roughly 5-6 prompts, including the frame IR and MIDI export.
The Contra parser required a separate implementation because the byte
counts and semantics differ, but the LLM wrote it from the disassembly
in about 3 prompts.

### Correlating Trace Data with Extraction Output

This is where LLMs provide the most leverage. Given a trace diff showing
"frame 47: expected MIDI 72, got MIDI 71, channel pulse1," the LLM can
trace back through the parser logic, identify which command produced that
note, check the octave state, and determine whether the error is in
parsing, pitch mapping, or envelope modeling.

The EC pitch bug in Contra is the canonical example. The trace showed
every note was +1 semitone higher than our extraction across all 23
unique pitches. The LLM identified that the parser was reading the EC
byte and discarding its parameter (`self.pos += 1  # skip pitch adj
byte`), then proposed the fix: apply the EC parameter as a semitone
offset to the period table lookup.

### Generating Hypotheses from Disassembly Code

When the disassembly contains routines like `resume_decrescendo` with
an `inc PULSE_VOLUME` instruction, the LLM can reason about what this
means: "when volume hits 0, the driver increments it back to 1 and
holds." This hypothesis can then be tested against the trace.

The bounce-at-1 discovery in Contra came exactly this way. The LLM
read the disassembly, formed the hypothesis, and the trace confirmed
it: implementing the bounce improved volume accuracy from 82% to 96.6%.

### Writing Invariant Tests That Encode Discoveries

Once a behavior is confirmed, the LLM can write pytest tests that
encode it as a regression check. These tests prevent future changes
from breaking verified behavior -- for example, ensuring that
`phase2_start` never goes below 1, or that triangle pitch is always
12 semitones below pulse for the same period value.

### Cross-Referencing Findings Across Games

Working on Contra exposed a bug in the CV1 envelope model that single-
game testing never revealed. The `phase2_start` calculation went negative
for 9 specific notes in Vampire Killer where `fade_step > duration`.
This bug was invisible in CV1 testing because it only affected the first
frame of a few notes by 1 volume step. The Contra work forced a deeper
look at the shared driver code, and the fix applied backwards to CV1,
dropping pulse volume mismatches from 45 to zero.

An LLM is well-suited to this kind of cross-referencing because it can
hold both games' parser logic, envelope models, and trace data in
context simultaneously.

### Producing Structured Documentation from Scattered Notes

Over the course of multiple sessions, discoveries accumulate as inline
comments, commit messages, and chat history. The LLM can consolidate
these into structured documents: research logs, command manifests,
per-game comparison tables, and handover docs that preserve session
state for future work.

---

## What LLMs Are Bad At

### Hearing Audio Differences

The most fundamental limitation. An LLM cannot listen to the rendered
MIDI and compare it to the game audio. When the extraction produces
notes that are systematically one semitone flat (the EC pitch bug) or
one octave low (the CV1 octave bug), the LLM has no way to detect this
from data alone -- especially when the automated trace comparison also
shows zero mismatches.

The user must ear-check every extraction against the actual game running
in an emulator. This is non-negotiable and cannot be automated away.

### Running Code

An LLM reasons about code but cannot execute it without tool access.
In a CLI environment with Bash, this is solved. But the boundary
matters: the LLM must write the code, run it, read the output, and
iterate. It cannot "just try things" the way a human developer does
in a REPL. Every iteration costs a prompt round-trip.

This is the Deckard boundary -- the line between what the LLM reasons
about and what deterministic tools execute. Getting this boundary right
determines whether the workflow converges in 5 prompts or 50.

### Remembering Across Sessions

Each new LLM session starts with zero knowledge of previous work. Without
explicit context engineering -- handover documents, manifests, CLAUDE.md
rules -- every session rediscovers the same mistakes.

In our project, the octave mapping bug (BASE_MIDI_OCTAVE4 = 24 vs 36)
was discovered in session 2. Without the CLAUDE.md rule "Triangle is 1
octave lower than pulse," a future session attempting a pitch mapping
change would likely break triangle in the same way it was broken before.

The LLM does not learn from past mistakes. You must encode those mistakes
into files the LLM reads at session start.

### Avoiding Systematic Assumptions

LLMs carry assumptions from one context into another. After working on
CV1, the LLM assumed Contra used the same DX byte count (2 instead of
3), the same parametric envelope model (instead of lookup tables), and
the same pitch mapping (ignoring the EC semitone offset). Each
assumption cost 2-4 prompts to identify and correct.

The pattern is consistent: whatever the LLM learned from the last game
becomes the default assumption for the next game, even when told
explicitly that games differ. The surface similarity of the Konami
command set makes this worse -- the commands look the same but their
parameters have different lengths and semantics.

### Knowing When to Stop Reasoning and Start Measuring

The most expensive failure mode is the LLM generating increasingly
elaborate hypotheses about engine behavior instead of extracting 20
frames of trace data and looking at the actual values. The CV1 envelope
model went through 3 wrong hypotheses before trace extraction revealed
the real pattern. Those 3 hypotheses cost 5 prompts. The trace
extraction that resolved it cost 1.

The rule is simple: 20 frames of trace data are worth more than 2000
words of analysis. But the LLM's natural tendency is to reason rather
than measure, because reasoning is what it does well.

---

## The Workflow That Works

This is the workflow that produced zero-mismatch Castlevania 1 and
96.6%-accurate Contra extractions.

### Step 1: User Provides Inputs

The user supplies three things:

- **The ROM file** -- the raw NES cartridge data
- **A Mesen APU trace** -- frame-level capture of what the hardware
  actually produces (period values, volume levels, channel enable flags)
- **A disassembly reference** (if available) -- annotated 6502 source
  with labels for the sound engine routines

The trace is captured by playing the target song in Mesen with APU
logging enabled. This takes 2-3 minutes and produces the ground truth
that the entire workflow depends on.

### Step 2: LLM Reads Disassembly, Builds Parser

The LLM reads the annotated disassembly (or, if none exists, scans the
ROM data for command patterns). It identifies the command format, byte
counts, pointer table structure, and channel layout. It writes a parser
that converts raw ROM bytes into an event stream: notes, rests, octave
changes, instrument switches, repeats.

### Step 3: LLM Extracts One Track

The parser runs on a single reference track. The LLM examines the
output for obvious errors: crashed parsing, missing notes, nonsensical
pitch values. The user listens to a MIDI render and compares it to the
game.

This is the first gate. Do not batch-extract before the reference track
sounds right.

### Step 4: LLM Compares Extraction Against Trace

The trace comparison tool (`trace_compare.py`) runs frame-by-frame,
comparing the parser's output against the hardware trace. It reports
mismatches by category: pitch errors, volume errors, sounding-state
errors. The LLM reads this report and classifies the mismatch:

- **Engine error**: the parser misunderstands a command (e.g., wrong DX
  byte count)
- **Data error**: the parser reads the wrong ROM address (e.g., wrong
  pointer table)
- **Hardware error**: the frame IR models the APU incorrectly (e.g.,
  triangle linear counter approximation)

### Step 5: LLM Proposes ONE Fix

One fix per iteration. Not three. The LLM applies the fix, re-runs the
trace comparison, and measures the improvement. If the mismatch count
drops, the fix is correct. If it increases or stays the same, the
hypothesis was wrong.

This is critical discipline. Changing multiple things simultaneously
makes it impossible to attribute improvements or regressions to specific
changes.

### Step 6: User Ear-Checks

The user renders the updated MIDI and compares it to the game. This
catches systematic errors that the trace comparison misses -- like the
octave bug where both the parser and the trace comparison agreed on
the wrong answer.

### Step 7: Iterate or Batch-Extract

If mismatches remain, return to step 4. If the reference track sounds
correct and the trace comparison shows acceptable accuracy, batch-
extract all remaining tracks.

---

## Context Engineering for NES RE

LLM-driven reverse engineering is a multi-session endeavor. A single
game takes 3-8 sessions depending on driver complexity. Without
deliberate context engineering, each session starts from scratch and
re-makes the same mistakes.

### CLAUDE.md: Hard Rules That Prevent Known Mistakes

The project's CLAUDE.md contains 8 hard invariants, each derived from a
specific incident that cost 2-5 prompts:

| Rule | What It Prevents |
|------|-----------------|
| Trace is ground truth | Reasoning without measuring |
| Same driver does not mean same ROM layout | Applying CV1 addresses to Contra |
| Same period table does not mean same driver | Assuming CV2 uses Maezawa |
| Automated tests miss systematic errors | Trusting zero-mismatch reports blindly |
| Triangle is 1 octave lower than pulse | Breaking triangle when changing pitch mapping |
| Version output files | Overwriting tested MIDIs with untested ones |
| Dump trace data before modeling | Guessing envelope shapes instead of measuring |
| Check all channels, not just one | Missing cross-channel bugs like the E8 gate |

These rules are positioned to fire at decision points. Starting a new
game triggers rules 2-3. Debugging pitch triggers rules 4-5. Generating
output triggers rule 6.

### Manifests: Structured State That Persists

Each game has a JSON manifest (`extraction/manifests/*.json`) that
records verified facts, hypotheses, and anomalies. The manifest tracks
every command the parser encounters with a status field: `verified`,
`hypothesis`, or `unknown`.

When a new session starts, reading the manifest tells the LLM what is
known, what is uncertain, and what has not been investigated. This
prevents re-deriving facts that were already established.

### Path-Specific Rules

The `.claude/rules/` directory contains rules that auto-load based on
which files the LLM is editing. Rules about the parser load when editing
parser files. Rules about trace comparison load when editing trace
scripts. This keeps the context focused and prevents rule overload.

### Handover Documents

Each session ends with an update to the handover doc (`docs/HANDOVER.md`)
that captures current state, recent changes, and priority next steps.
The next session reads this first and knows exactly where to pick up.

### NEXT_SESSION_PROMPT.md

A file containing the exact startup instructions for the next LLM
window. This removes ambiguity about what the new session should do
first.

### Why This Matters

Without context engineering, a fresh LLM session on Contra would:

1. Assume the CV1 parser works (it does not -- different DX byte count)
2. Produce garbage output and spend 3 prompts diagnosing why
3. Discover the DX byte count difference (already documented in spec.md)
4. Fix it and proceed, having wasted 3 prompts rediscovering known facts

With context engineering, the session reads the manifest, sees that DX
byte count is verified as 3/1, and starts from the correct baseline.
The 3 wasted prompts become zero.

Across a multi-game project, context engineering saves dozens of prompts
and prevents the most demoralizing kind of failure: re-making a mistake
that was already solved.

---

## Swarm Agents for Documentation

### When to Use Parallel Agents

Swarm agents work well for tasks that are:

- **Write-only**: creating new files, not modifying existing ones
- **Read-many, write-one**: each agent reads shared source files and
  produces one unique output document
- **Independent**: no agent needs output from another agent
- **Non-executable**: the task does not require running code to verify

Good swarm tasks: writing documentation files, annotating code with
comments, creating test files that import from existing code, generating
per-game comparison tables.

### When NOT to Use Parallel Agents

Swarm agents fail at tasks that require:

- **Bash access**: agents cannot run code or verify output
- **Iterative debugging**: logic changes need test-fix-retest cycles
- **Cross-file coordination**: modifying imports, renaming shared
  functions
- **Stateful reasoning about existing code paths**: adding CLI
  parameters to an argument parser, changing control flow

In our first deployment, an agent tasked with adding a `--game` CLI
parameter to `trace_compare.py` did not complete. The task required
reading the existing argument parser, understanding control flow,
modifying conditional branches, and preserving backward compatibility.
This exceeds what a swarm agent can do without running the code.

### Our Results

Ten agents, 7-8 completed their full deliverable. Roughly 130KB of
structured documentation produced in about 5 minutes wall clock time,
plus 10 minutes of gap-filling for incomplete agents.

Key metrics:

- **Completion rate**: 70-80%
- **File conflicts**: zero (each agent owned its output exclusively)
- **Logic bugs introduced**: zero (no logic changes completed)
- **Context preservation**: the main session's context window was not
  consumed by documentation writing

### The Gap-Fill Pattern

Plan for 20-30% failure. Assign one file per agent (not two). Budget
time for the main session to check results and complete what the swarm
missed. The value is not 100% automation -- it is 70% automation plus
context preservation in the main session.

---

## Mesen Trace as Ground Truth

This is the single most important section in this document.

### The Trace Is What Makes LLM-Driven RE Converge

Without a hardware trace, the LLM's workflow is: read disassembly,
write parser, listen to output, guess what is wrong, modify parser,
listen again. This is a random walk through hypothesis space. The LLM
has no objective function to optimize against. It will produce output
that sounds "close enough" and declare victory, even when every note
is systematically wrong.

With a hardware trace, the workflow becomes: read disassembly, write
parser, compare against trace, identify the exact frame and channel
where the first mismatch occurs, fix it, re-compare. This is gradient
descent. Each iteration moves closer to the correct answer because the
trace provides an unambiguous target.

### The EC Pitch Bug: A Case Study

During Contra extraction, the LLM was confident the parser was correct.
The output sounded like the Jungle theme. Notes were in the right
rhythm. The melody was recognizable.

Then the trace comparison showed that every single note across all
channels was exactly 1 semitone flat. MIDI 71 where the hardware
produced 72. MIDI 59 where the hardware produced 60. 23 unique pitches,
all off by +1.

The cause: the parser read the EC command byte but discarded its
parameter. `EC 01` means "shift all note lookups by +1 in the period
table." The parser had `self.pos += 1  # skip pitch adj byte`. One
line of ignored data made every note in every track wrong by exactly
1 semitone.

This error is nearly inaudible in isolation. A melody transposed by one
semitone sounds like the same melody in a slightly different key. Without
the trace providing absolute pitch ground truth, this bug would have
shipped.

### The CV1 Octave Bug: Another Case Study

The CV1 extraction passed the automated trace comparison with zero pitch
mismatches. Both the parser and the trace conversion used the same
frequency-to-MIDI formula, so they agreed perfectly -- on the wrong
answer.

The user compared the REAPER playback to the game running in Mesen. The
lead melody started on A3 (220 Hz) when the game clearly played A4
(440 Hz). Every note was one octave too low.

The trace comparison could not catch this because both paths shared the
same bug: an incorrect base octave constant. Only a human ear comparing
against the actual game detected it.

### The Lesson

LLM reasoning is necessary but not sufficient. The LLM reads the
disassembly, writes the parser, interprets the trace diffs, and proposes
fixes. But the trace is the oracle. Without it, the LLM will confidently
produce wrong output that passes its own consistency checks.

The evidence hierarchy, in decreasing reliability:

1. **APU trace** -- hardware ground truth, frame-level, per-channel
2. **Annotated disassembly** -- explains why the hardware does what it does
3. **Automated trace comparison** -- catches errors but misses systematic ones
4. **Ear comparison** -- catches gross errors, misses subtle offsets
5. **Reasoning about byte meanings** -- least reliable, most tempting

Spend your time at the top of this hierarchy, not the bottom.

---

## What's Next

### Every Konami NES Game Is a Potential Project

The Maezawa driver family covers Castlevania 1, Contra, Super C, TMNT,
Gradius, and Goonies II at minimum. Each game uses the same command
skeleton with per-game variations in byte counts, envelope models,
percussion systems, and ROM layouts. The methodology developed here --
manifest-driven parsing, trace validation, per-game configuration --
applies to all of them.

### The Methodology Generalizes Beyond Konami

Any NES sound driver with deterministic frame-level behavior can be
traced and validated using this approach. The driver does not need to
be from Konami. It does not need to use the same command set. It needs
to produce deterministic output that can be captured by an emulator's
APU logger.

Capcom (Mega Man series), Sunsoft (Batman, Blaster Master), and
Natsume (Shadow of the Ninja) all have distinctive sound engines. Each
would require a new parser, but the workflow is the same: read
disassembly, write parser, validate against trace, iterate.

### The Scale of the Opportunity

The NES library contains roughly 800 licensed titles, most with
completely undocumented sound engines. The homebrew and unlicensed
catalog adds hundreds more. Annotated disassemblies exist for perhaps
50-100 of the most popular games. For the rest, the LLM would need to
work from raw ROM data and partial documentation.

LLMs can read 6502 assembly for all of these. The bottleneck is not
parsing or analysis -- it is trace capture (which requires a human to
play the game or write a TAS input sequence) and ear-checking (which
requires a human to listen).

The tools built for this project -- trace comparison, frame IR, MIDI
export pipeline, REAPER project generation -- make each subsequent
game faster. The first game (Castlevania 1) took roughly 20 prompts
across 3 sessions. The second game (Contra) took roughly 15 prompts
across 2 sessions, because the tooling and methodology already existed.
A third Konami game would likely take 8-12 prompts.

### The Human Remains Essential

The LLM accelerates every step except two: capturing the trace (someone
must run the game) and ear-checking the output (someone must listen).
These two steps anchor the entire workflow to reality. Remove them, and
the LLM produces internally consistent but externally wrong results.

This is not a limitation to be engineered around. It is the architecture.
The human provides ground truth. The LLM provides throughput. Neither
alone produces correct output. Together, they converge.
