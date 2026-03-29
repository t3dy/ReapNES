---
layout: default
title: "Trace Comparison Workflow"
---

# Trace Comparison Workflow

This document covers how to capture APU traces from the emulator,
compare them against extracted frame IRs, and debug mismatches
systematically. It is the primary quality assurance process for the
extraction pipeline.

---

## 1. Why Trace First

The APU trace is the single most important tool in the fidelity
pipeline. It converts subjective judgments ("sounds close") into
objective measurements ("zero pitch mismatches, 45 volume mismatches
across 1792 frames").

More critically, traces catch errors that no other method can detect.

**The canonical example: the EC pitch bug.** Contra's Jungle theme
uses the EC command to shift the period table index by +1 semitone on
certain channels. Before this was implemented in the parser, every
note on those channels was off by exactly 1 semitone. The melody
sounded correct in isolation -- all intervals were preserved, the
rhythm was right, the notes were in tune with each other. A human
listener comparing the extraction to the game would need absolute
pitch to notice. The trace comparison flagged every single note as a
pitch mismatch on the first run.

This is the class of error that trace comparison exists to catch:
**systematic errors where the output is internally consistent but
wrong.** Other examples from the project's history:

- BASE_MIDI_OCTAVE4 was set to 24 instead of 36. Every note was 12
  semitones too low. The intervals were perfect. The trace comparison
  (once fixed to compare MIDI notes instead of raw periods) caught it
  instantly.

- The Phase 2 envelope start was not clamped to frame 1. Nine notes
  in Vampire Killer had their first-frame volume 1 step too low. The
  error was inaudible in casual listening. The trace showed 45 volume
  mismatches that eventually led to the fix.

**Rule: run trace_compare.py after every change to the parser or frame
IR.** Do not rely on listening. Do not rely on "it looks right in the
MIDI editor." The trace is ground truth.

---

## 2. Capture Workflow

### Prerequisites

- Mesen 2 (not Mesen 1 -- the Lua API is different)
- The target ROM
- The Lua capture script: `docs/mesen_scripts/mesen_apu_capture.lua`

### Step by step

**a. Load the ROM in Mesen 2.**
File, Open, select the ROM. Let the game boot to the title screen.

**b. Load the capture script.**
Open Tools, Script Window (or Debug, Script Window depending on your
Mesen version). Click the Open icon and select
`mesen_apu_capture.lua`. Click Run. The script log should display a
ready message with keyboard controls.

**c. Navigate to the music you want to capture.**
For Contra Jungle: start a new game, begin Level 1. For Castlevania
Vampire Killer: start a new game, begin Stage 1. If you want to
capture from the very first note, pause Mesen (emulator pause, not
game pause) right before the music starts.

**d. Start capture.**
Make sure the Mesen game window has focus (not the script window).
Press `[` (left square bracket). The script log shows the starting
frame number. Unpause if paused.

**e. Let the music play.**
One full loop is sufficient for initial validation. Contra Jungle
loops at approximately 3072 frames (51 seconds). Castlevania Vampire
Killer loops at approximately 1792 frames (30 seconds). Press `\`
(backslash) at any time to check capture status.

**f. Stop capture.**
Press `]` (right square bracket). The script saves the CSV and reports
the number of state changes and frames captured.

**g. Copy the CSV to the project.**

```bash
# Example for Contra
mkdir -p extraction/traces/contra
cp /c/Users/PC/Documents/Mesen2/capture.csv extraction/traces/contra/jungle.csv

# Castlevania (already captured)
# extraction/traces/castlevania/stage1.csv
```

### CSV format

The output has three columns: `frame`, `parameter`, `value`. Only
changes are logged (if a register value stays the same, it is not
repeated). Parameters use pseudo-register names like `$4000_vol`,
`$4002_period`, `$400A_period`. See `docs/MESENCAPTURE.md` for the
full parameter reference table.

### Start frame offset

Each capture has some number of silence frames before music begins.
Inspect the first frames to find where notes start:

```bash
PYTHONPATH=. python scripts/trace_compare.py --dump-frames 0-30 --channel pulse1
```

Look for the first frame where volume becomes non-zero. Record this
offset in the game's manifest JSON under `trace_validation.start_frame_offset`.
For CV1 Vampire Killer, the offset is 111.

---

## 3. Comparison Workflow

### Running the comparison

```bash
cd C:/Dev/NESMusicStudio
PYTHONPATH=. python scripts/trace_compare.py --frames 1792
```

This parses the ROM, converts to frame IR, loads the trace CSV,
converts the trace to frame IR, and compares them frame by frame. It
produces two outputs:

- `docs/TraceComparison_CV1.md` -- human-readable report with summary
  table, mismatch regions, and first frame diffs per channel.
- `data/trace_diff_cv1.json` -- machine-readable diff for programmatic
  analysis.

### Reading the report

The summary table is the first thing to check:

```
| Channel  | Pitch | Volume | Duty | Sounding | First Pitch Error |
|----------|-------|--------|------|----------|-------------------|
| pulse1   | 0     | 45     | 0    | 9        | none              |
| pulse2   | 0     | 50     | 0    | 10       | none              |
| triangle | 0     | 195    | -    | 195      | none              |
```

**Pitch mismatches** should be zero. Any non-zero value means the
parser is producing wrong notes. This is the highest priority fix.

**Volume mismatches** are expected to be non-zero for two reasons:
cosmetic mismatches (both sides have volume 0 but differ in the
retained period/MIDI note) and genuine envelope model errors. Inspect
the frame diffs to distinguish them.

**Sounding mismatches** indicate disagreement about whether a note is
audible on a given frame. On pulse channels, these usually follow from
volume envelope errors. On triangle, they come from the linear counter
approximation (INV-007).

### Inspecting specific frames

When you find mismatches, dump the raw trace data for those frames:

```bash
# Dump pulse1 frames 100-120
PYTHONPATH=. python scripts/trace_compare.py --dump-frames 100-120 --channel pulse1
```

This prints one line per frame showing note name, volume, duty cycle,
sounding state, and raw period value. Compare these against the frame
IR output to identify exactly where the model diverges from reality.

---

## 4. Debugging Protocol

When the trace comparison shows mismatches, follow these steps in
order. Do not skip steps. Do not try multiple fixes at once.

### Step 1: Identify the symptom precisely

Which channel? Which aspect (pitch, volume, sounding)? Which frame
range? "Pulse 1 has volume mismatches" is not precise enough. "Pulse 1
frames 45-51 show volume 3 in our IR but volume 2 in the trace" is
precise enough to act on.

### Step 2: Dump trace data for the exact frames

```bash
PYTHONPATH=. python scripts/trace_compare.py --dump-frames 45-55 --channel pulse1
```

Do not reason abstractly about what the engine "should" produce. Look
at what the hardware actually produced. Write down the frame numbers
and values. This is the evidence you will work from.

### Step 3: Compare at frame level and find the FIRST mismatch

The first mismatch in a region is almost always the root cause. Later
mismatches are usually consequences. If frames 45-51 are all wrong,
focus exclusively on frame 45. What changed between frame 44 (correct)
and frame 45 (wrong)?

### Step 4: Classify the mismatch by layer

- **ENGINE**: The sound driver's software is doing something our model
  does not account for. Examples: envelope phase timing, decrescendo
  threshold, bounce-at-1 behavior.
- **DATA**: The parser is reading the wrong bytes or interpreting them
  incorrectly. Examples: wrong DX byte count, skipped EC command,
  incorrect repeat count.
- **HARDWARE**: The NES APU hardware behaves differently from our
  model. Examples: triangle linear counter timing, sweep unit effects,
  quarter-frame clock boundaries.

The classification determines where to look for the fix. Engine bugs
are in `frame_ir.py`. Data bugs are in the parser. Hardware bugs
require reading the APU specification or NESdev wiki.

### Step 5: Form ONE hypothesis and test it

Change one thing. Rerun `trace_compare.py`. Check whether the first
mismatch moved or disappeared. If it moved forward, you fixed that
instance but there may be more. If it disappeared entirely, the fix
is correct for this case -- check if it introduced regressions
elsewhere.

Do not change multiple things at once. Multi-hypothesis changes make
it impossible to determine which change had which effect.

### Step 6: Handle the zero-mismatch-but-sounds-wrong case

If `trace_compare.py` reports zero pitch mismatches but the output
does not match the game when a human listens, you have a systematic
error. The two known categories:

- **Octave mapping error**: Every note is shifted by a fixed number of
  semitones. The intervals are correct, so the trace comparison (if
  comparing periods or relative pitch) shows no mismatches. Fix: ensure
  the comparison tool compares absolute MIDI note numbers, then check
  BASE_MIDI_OCTAVE4 and the triangle -12 offset.

- **Comparison tool bug**: The tool itself may be comparing the wrong
  thing. The CV1 project had a period where `trace_compare.py` compared
  raw period values instead of MIDI notes, which masked the octave
  error entirely. If you suspect this, dump raw frames from both the
  extracted IR and the trace and compare them manually.

In both cases, the human ear is the backstop. Automated tests that
are self-referential (comparing the output to itself or to a derived
value) cannot catch errors where the derivation is wrong.

---

## 5. Mismatch Taxonomy

When the trace comparison reports mismatches, classify each one to
determine the appropriate fix.

### Pitch mismatch, both sides sounding

The extracted note and the trace note are both audible, but they
disagree on which note is playing. This is a data bug -- the parser
is producing the wrong pitch. Common causes:

- Missing or incorrect EC pitch adjustment (INV-006)
- Wrong period table lookup
- Octave calculation error
- Parser desynchronized from data stream (often caused by wrong DX
  byte count, INV-008)

### Pitch mismatch, one side silent

The extracted IR thinks a note is sounding but the trace has silence
(or vice versa). This usually indicates a volume envelope disagreement
rather than a true pitch error -- the pitch "mismatch" is an artifact
of one side having the note gated off while the other still has it
sounding. Fix the volume/sounding issue first; the pitch mismatch
will likely resolve as a side effect.

### Volume mismatch, both sides sounding

Both sides agree the note is playing, but disagree on the volume
level. This is an engine bug -- the envelope model is producing the
wrong volume curve. Common causes:

- Phase 2 start frame computation (INV-001)
- Missing bounce-at-1 behavior (INV-003)
- Wrong decrescendo threshold (INV-009)
- Envelope table data extracted incorrectly

### Volume mismatch, cosmetic

Both sides have volume 0, but the extracted IR retains the period and
MIDI note from the last sounding frame while the trace zeros them.
This is not audible and can be ignored. The trace comparison tool
counts these in the volume mismatch total but they do not represent
real errors.

### Sounding mismatch on pulse channels

The extracted IR and the trace disagree about whether the note is
audible. On pulse channels, this usually follows from an envelope
model error -- our model says the note has faded to volume 0 but the
trace still shows volume 1 (or vice versa). Check INV-003
(bounce-at-1) and the envelope phase boundaries.

### Sounding mismatch on triangle

The triangle channel has no volume control. It is either sounding or
silent, gated by the linear counter. Sounding mismatches on triangle
indicate that the linear counter model (INV-007) is off by 1 frame.
The current approximation `(reload + 3) // 4` produces approximately
8 such mismatches per Vampire Killer loop. These are a known
limitation of the integer approximation and are not audible.

---

## 6. Trace File Conventions

### Directory structure

```
extraction/traces/
  castlevania/
    stage1.csv          # Vampire Killer (complete, validated)
  contra/
    jungle.csv          # Level 1 (pending capture)
  super_c/
    level1.csv          # future
```

### Manifest integration

Each game's manifest JSON should record trace validation status:

```json
"trace_validation": {
    "trace_path": "extraction/traces/castlevania/stage1.csv",
    "start_frame_offset": 111,
    "validated_frames": 1792,
    "pitch_mismatches": 0,
    "volume_mismatches": 45,
    "sounding_mismatches": 9
}
```

Update these numbers after every successful comparison run. They
serve as the regression baseline -- if a code change increases any
mismatch count, the change introduced a bug.
