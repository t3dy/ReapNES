# How to Be More Flexible in NES Music Reverse Engineering

## The Pattern That Keeps Burning Us

Every game we've touched has punished assumptions carried from the
previous game. The Konami Maezawa driver family shares a common
skeleton — DX/FE/FF commands, the same period table, the same note
encoding — but every game customizes it differently. The surface
similarity is the trap.

CV1 taught us the basic command set. Then Contra used the same
commands with different byte counts, different percussion, different
volume envelopes, and an entirely different pitch adjustment system.
Both games sit in the same driver family, separated by maybe 18
months of development, and yet a parser written for one produces
garbage on the other.

The lesson isn't "Contra is different from CV1." The lesson is:
**every game will be different from every other game, in ways we
cannot predict from the previous game.**

## What Went Wrong (A Taxonomy)

### 1. Assuming Semantics Were Shared

CV1's DX command reads 2 extra bytes. We assumed Contra's did too.
It reads 3 for pulse, 1 for triangle. Cost: 3 prompts.

CV1's volume is parametric (fade_start/fade_step). We approximated
Contra the same way. It uses lookup tables. Cost: the entire
"dynamics are flat" problem that persisted from v1 through v4.

Both games use the same period table. We assumed this meant the same
pitch mapping. But Contra's EC command shifts the table index by 1
semitone, and we ignored the byte. Cost: every note in every track
was in the wrong key.

### 2. Ignoring Commands We Didn't Understand

The parser had `self.pos += 1  # skip pitch adj byte` for the EC
command. That one line threw away the information that every note
in the Jungle track is shifted +1 semitone. The parser didn't
crash — it just silently produced wrong output. This is worse than
crashing.

The EB vibrato command is still skipped. We don't know what it
costs us yet, but the pattern is the same: an ignored parameter
that may be shaping the sound in ways we can't hear in isolation.

### 3. Testing Relative Instead of Absolute

Our trace comparison tool compares the extraction against itself
(parser path vs freq-from-period path). When both paths share the
same bug, the comparison shows zero mismatches. This happened with
the octave mapping in CV1 and would have happened with the +1
semitone in Contra if we'd built a self-referential comparison.

Only the hardware trace — absolute ground truth — catches these.

### 4. Batch Extracting Before Validating

The workflow says "parse ONE track, listen before batch-extracting."
We mostly followed this. But "listen" doesn't catch systematic
pitch offsets. The melody sounds right because all notes are
equally wrong. You need either perfect pitch, a reference recording,
or a trace.

## What Would Make Us More Flexible

### Principle 1: Parse Everything, Skip Nothing

Every byte the sound engine reads should be captured in the parser
output, even if we don't know what it does yet. Store unknown
parameters as raw values in the event stream. Label them with their
byte offset and ROM address.

Currently we skip EB vibrato params, and we almost lost EC pitch
adjust. A more resilient parser would emit:

```python
UnknownCommand(byte=0xEB, params=[0x2A, 0x22], offset=0x543A)
```

This way:
- The parameter data is preserved in the event stream
- A future session can identify what it does
- Nothing is silently discarded

### Principle 2: The Manifest Is the Source of Uncertainty

The per-game manifest (`extraction/manifests/contra.json`) should
track EVERY command the parser encounters, with a status for each:

```json
"commands": {
    "EC_pitch_adjust": {"status": "verified", "handler": "applies semitone offset"},
    "EB_vibrato": {"status": "recognized_not_implemented", "params": "2 bytes"},
    "E8_flatten": {"status": "hypothesis", "theory": "envelope gate"}
}
```

When a new game is added, start by enumerating ALL commands found
in the data, marking each as `unknown`. Then verify them one at a
time against the disassembly or trace. The manifest tracks what
we know and — critically — what we don't know.

### Principle 3: Validate Absolute, Not Relative

The trace is non-negotiable. For every new game:

1. Capture a Mesen trace FIRST (before building the parser)
2. Use the trace as the target, not the parser
3. Build the parser to match the trace, not the other way around

This inverts our current workflow, where we build the parser from
the disassembly and then check it against the trace. The trace-first
approach prevents "both paths share the same bug" blindness.

For practical purposes: capture the trace while you're still
reading the disassembly. It costs 2 minutes and saves hours.

### Principle 4: The Disassembly Is the Map, Not the Territory

The annotated disassembly tells you what the code does. It doesn't
tell you what the game's music data ACTUALLY triggers. A command
might exist in the code but never appear in any track. A command
might appear in track data but never be documented because the
disassembler didn't encounter it.

**Read the disassembly to understand the engine. Read the ROM data
to understand what the music actually uses. Read the trace to
understand what the hardware actually produces.**

Three independent sources. If they agree, you have confidence.
If they disagree, you have a bug to find.

### Principle 5: Driver Capability as a Schema

The `DriverCapability` pattern (introduced this session) is the
right structural answer. Each game declares what its driver does:

```python
DriverCapability(
    volume_model="lookup_table",
    pitch_adjustment=True,
    vibrato=False,  # not yet implemented
    percussion_model="dmc_compound",
)
```

The IR dispatches on declared capabilities. When a new game
introduces a new behavior (say, pitch slides), you add a new
field to the schema. The IR gets a new strategy function. Existing
games are unaffected because their capabilities don't include the
new field.

This beats the alternative (a giant if/elif chain per game) because
it makes the contract explicit and testable.

### Principle 6: One Command at a Time

When debugging, change one thing and re-compare. The debugging
protocol in CLAUDE.md says this, but it bears repeating:

- Don't fix EC pitch adjust AND EB vibrato in the same session
- Fix EC, re-compare, measure the improvement
- Then fix EB, re-compare, measure THAT improvement
- If something regresses, you know exactly which change caused it

This is slower but prevents "I changed 5 things and now it's
worse and I don't know why."

## A More Flexible Workflow for the Next Game

1. **`rom_identify.py`** — deterministic ROM analysis (mapper,
   period table scan, driver signature)
2. **Capture trace** — before any parsing work, get 60 seconds
   of hardware ground truth
3. **Enumerate commands** — scan the track data for all unique
   byte patterns, categorize by nibble range, count occurrences
4. **Read disassembly** — understand each command's semantics
5. **Build manifest** — document every command with status
   (verified/hypothesis/unknown)
6. **Parse one track** — against the trace, not in isolation
7. **Iterate** — one command at a time, measure improvement

The key difference from our current workflow: **trace capture moves
from step 7 (validation) to step 2 (orientation)**. You don't
build the parser and then check it. You capture the answer first
and build the parser to match it.

## What This Means for the Codebase

The parser architecture should evolve from "understand the driver,
emit correct events" to "capture everything the data contains,
label what we understand, preserve what we don't." The frame IR
should evolve from "apply the correct model" to "apply the declared
model and report where it diverges from trace."

The gap between "what we extract" and "what the hardware produces"
is the measure of our understanding. The trace makes that gap
visible. Everything else is just making the gap smaller.
