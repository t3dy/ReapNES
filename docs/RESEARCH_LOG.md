# NES Music Studio -- Research Log

A chronological record of discoveries made while reverse engineering
NES sound engines. Each entry follows the same structure: hypothesis,
evidence, verdict. This documents the actual research process -- messy,
iterative, and mistake-driven -- for anyone attempting similar work.

---

## SESSION 1 -- CV1 Initial Extraction

**Date**: ~2026-03-25
**Goal**: Extract Vampire Killer (track 2) from Castlevania 1 ROM.

### Hypothesis
The Konami period table at ROM $079A maps note indices to NES timer
periods. Combined with octave shift commands (E0-E4), this should
produce correct MIDI note numbers.

### Evidence
- 12-entry period table found at $079A, values match NTSC CPU clock
  (1789773 Hz) for chromatic scale C through B.
- Pointer table at $0825: 15 tracks, 9-byte entries (3 channels x
  3 bytes each).
- Parsed track 2 (Vampire Killer), played in REAPER. First listen:
  the melody was recognizable. Notes in the right key.
- The byte-level command format decoded cleanly: $00-$BF = notes,
  $C0-$CF = rests, $D0-$DF = tempo/instrument, $E0-$E4 = octave,
  $FE = repeat, $FF = end.

### Verdict
CONFIRMED. The period table maps directly to MIDI via the standard
NES frequency formula. Octave shifts work as right-shifts on the
base period. But the absolute octave mapping needed calibration --
initial output sounded correct in relative pitch but the absolute
register was unverified.

**Files changed**: `parser.py` (initial version), `frame_ir.py`
(initial version).
**Prompts spent**: ~5-6 (bootstrapping the entire extraction pipeline).
**Lesson**: The period table is universal NES tuning, not driver-specific.
It proves "this is an NES," not "this is the Maezawa driver."

---

## SESSION 2 -- CV1 Octave Bug

**Date**: ~2026-03-26
**Goal**: Investigate user report that pulse channels sound an octave low.

### Hypothesis
`BASE_MIDI_OCTAVE4 = 24` (C1) is the correct base, since it matches
the APU trace frequency-to-MIDI conversion.

### Evidence
- Trace comparison showed **zero pitch mismatches** across all channels.
  Parser and trace agreed perfectly -- both said A3 (MIDI 57) for the
  first Sq1 note.
- But the user compared REAPER playback side-by-side with the game in
  Mesen. The lead melody started on A3 (220 Hz) when the game clearly
  played A4 (440 Hz).
- The Contra disassembly (same driver family) documents the octave
  shift: `shifts = 4 - octave_value`. For E2, that gives 2 shifts,
  producing period 254 (A4). The trace showed period 511 (A3), which
  corresponds to only 1 shift.
- The resolution: the trace captures the raw hardware timer value, but
  the driver's musical convention places the base period table at
  octave 2 (C2 = MIDI 36). The frequency-to-MIDI conversion was one
  octave too low because it used the hardware frequency without the
  driver's octave convention.

### Verdict
DISPROVEN. `BASE_MIDI_OCTAVE4` corrected from 24 to 36 (C2). The
`freq_to_midi_note()` function in frame_ir.py gained a +12 offset so
trace comparison still shows zero mismatches.

**Files changed**: `parser.py` (BASE_MIDI_OCTAVE4 = 36),
`frame_ir.py` (+12 trace offset).
**Prompts spent**: ~3 (the automated test showing 0 mismatches was
actively misleading).
**Lesson**: Automated tests verify internal consistency, not absolute
correctness. Both the parser and trace comparison had the same error,
so they agreed on the wrong answer. Only a human ear comparing against
the actual game could detect the discrepancy.

---

## SESSION 3 -- CV1 Envelope Model

**Date**: ~2026-03-26
**Goal**: Reduce volume mismatches from ~2500 to near zero.

### Hypothesis
The Konami driver uses a two-phase parametric envelope: `fade_start`
frames of 1/frame decay from attack volume, hold, then `fade_step`
frames of 1/frame release at the note's end.

### Evidence
- Frame-by-frame trace extraction for instrument $B5 (vol=5, fade=2/3)
  showed: 5, 4, 3, [hold at 3], 2, 1, 0. The last 3 frames had 3
  decrements -- matching fade_step=3.
- Instrument $B4 (fade=3/1): hold at 1, then 0 on last frame.
- Instrument $F3 (fade=1/0): decay once, then hold at 2 forever.
- Three failed hypotheses preceded this:
  1. "fade_step = continued decay rate" -- made vol mismatches worse
     (185 to 758).
  2. "Force vol=0 on last frame" -- wrong direction (trace shows vol=1
     on some final frames).
  3. "E8 gates fading" -- disproven when Sq2 (zero E8 commands) still
     decayed in the trace.

### Verdict
CONFIRMED with 99.5% accuracy. The two-phase model dropped pulse
mismatches from ~1500 to ~50 (cosmetic). A phase2_start bug was found
later (see Session 7).

**Files changed**: `frame_ir.py` (envelope model rewrite),
`midi_export.py` (complete rebuild from frame IR).
**Prompts spent**: ~5 (3 failed hypotheses before trace extraction
revealed the actual pattern).
**Lesson**: Dump trace data before modeling. 20 real frames of evidence
beats any amount of reasoning about what bytes "should" mean.

---

## SESSION 4 -- Contra Initial Attempt

**Date**: ~2026-03-27
**Goal**: Extract Contra soundtrack using the CV1 parser.

### Hypothesis
Contra uses the same Maezawa driver as CV1, so the CV1 parser should
work with only address changes.

### Evidence
- Ran CV1 pipeline against Contra ROM. Result: 2/15 tracks exported,
  13 crashed with division-by-zero. The 2 "working" tracks were
  accidents -- the CV1 pointer table ($0825) pointed to random Contra
  data that happened to partially parse.
- Tried automated pointer table scanning. Produced thousands of false
  positives across 128KB of PRG data.
- Read the annotated Contra disassembly (`references/nes-contra-us/`).
  Found 3 critical differences from CV1:
  1. DX reads 3 extra bytes for pulse (not 2).
  2. Percussion uses a separate DMC channel (not inline E9/EA).
  3. Pointer table is a flat sound code table, not 9-byte entries.

### Verdict
DISPROVEN. Same command set (notes, octaves, repeats) does NOT mean
same semantics. The DX byte count difference causes every byte after
the first instrument command to be read at the wrong offset, cascading
into total data corruption.

**Files changed**: `contra_parser.py` (new file), `contra.json`
manifest (new file).
**Prompts spent**: ~3 on the failed CV1 parser attempt, ~3 more reading
the disassembly and building the Contra-specific parser.
**Lesson**: Same period table does not prove same driver. Same driver
family does not mean same ROM layout. Always read the disassembly
before writing code.

---

## SESSION 5 -- Contra Envelope Tables

**Date**: ~2026-03-27
**Goal**: Extract Contra's volume envelope lookup tables for dynamics.

### Hypothesis
Contra uses `pulse_volume_ptr_tbl` lookup tables instead of CV1's
parametric envelopes. The disassembly labels identify 54 tables.

### Evidence
- Extracted 54 envelope tables from ROM bank 1 starting at CPU $8001.
- Each table is a sequence of per-frame volume values (0-15),
  terminated by $FF.
- Table patterns match expected attack-decay shapes: quick attacks,
  sustained holds, gradual releases.
- 8 tables per level (7 levels, 6 for level 7), selected by the
  `SOUND_VOL_ENV` byte in each DX instrument command.
- Frame-level volume comparison against the Mesen trace: 82-94%
  match on first comparison (before timing alignment).

### Verdict
CONFIRMED. 54 tables extracted successfully, verified against
disassembly labels. Volume shapes are correct. Remaining mismatches
come from auto-decrescendo timing and note-boundary alignment, not
from the tables themselves.

**Files changed**: `contra_parser.py` (envelope table extraction),
`frame_ir.py` (`_contra_pulse_envelope()` function).
**Prompts spent**: ~3.
**Lesson**: When a disassembly documents data structures, extract them
directly. Do not try to infer envelope shapes from ear comparison.

---

## SESSION 6 -- EC Pitch Adjustment

**Date**: ~2026-03-28
**Goal**: Investigate why the Contra trace shows every note +1 semitone
higher than our extraction.

### Hypothesis
Our extraction notes are correct; any pitch difference is a trace
alignment issue.

### Evidence
- The Mesen trace showed MIDI 72 where we produced 71. MIDI 60 where
  we produced 59. Systematic +1 on every single note across all 23
  unique pitches in the Jungle melody.
- Found `EC 01` as the first byte of the Jungle Sq1 channel data.
  The EC command shifts all subsequent note lookups by +1 in the
  period table.
- Our parser was reading the EC byte and discarding its parameter.
  Every note in the song inherited the invisible +1 shift.
- This is the same class of error as the CV1 octave bug (Session 2):
  a systematic pitch offset that is invisible to relative comparison
  because all notes shift equally.

### Verdict
DISPROVEN. Parser now reads the EC parameter and applies it as a
semitone offset. Post-fix pulse pitch match: 91% (remaining 9% is
timing drift, not pitch error).

**Files changed**: `contra_parser.py` (EC command handling),
`contra.json` (pitch_adjustment field added).
**Prompts spent**: ~2.
**Lesson**: Systematic pitch offsets are invisible to relative testing
and nearly inaudible in isolation. Only absolute ground truth (hardware
trace) catches them reliably.

---

## SESSION 7 -- Cross-Game Lessons (CV1 Revisited)

**Date**: ~2026-03-28
**Goal**: Apply Contra insights back to CV1 to see if any CV1 bugs
were masked.

### Hypothesis
The CV1 envelope model is fully correct (45/50 remaining volume
mismatches are all cosmetic edge cases).

### Evidence
- The Contra work required deep understanding of `set_pulse_config`
  and `resume_decrescendo` in the disassembly.
- This revealed the `phase2_start` bug: when `fade_step > duration`
  (9 specific notes in Vampire Killer), `phase2_start = duration -
  fade_step` goes negative. The condition `f >= phase2_start` was true
  on frame 0, causing an extra decrement before the note started.
- Before fix: `[4, 3, 2, 1, 0, 0, 0]` (vol starts at 4 instead of 5).
- After fix: `[5, 4, 3, 2, 1, 0, 0]` (matches trace exactly).
- Fix: `phase2_start = max(1, duration - fade_step)`.
- Result: 45 volume mismatches on pulse1 dropped to **zero**. Both
  pulse channels now show perfect frame-level accuracy.

### Verdict
PARTIALLY DISPROVEN. The remaining mismatches were not cosmetic -- they
were real bugs in the phase 2 start calculation. The fix was one line,
but finding it required reverse engineering a different game's volume
system.

**Files changed**: `frame_ir.py` (`phase2_start` fix).
**Prompts spent**: ~2 (the insight came from Contra work, not from
debugging CV1 directly).
**Lesson**: Cross-game reverse engineering exposes model bugs that
single-game testing hides. The games are independent data sets running
on shared infrastructure. Different parameter ranges trigger different
code paths.

---

## SESSION 8 -- Volume Bounce-at-1

**Date**: ~2026-03-28
**Goal**: Improve Contra volume accuracy beyond 82%.

### Hypothesis
Notes in the Contra driver decay to vol=0 during their tail phase
(decrescendo).

### Evidence
- The `resume_decrescendo` routine in the disassembly contains an
  `inc PULSE_VOLUME` instruction that fires when volume hits 0.
- This means notes do not stay at 0 -- they bounce back to vol=1
  and hold there.
- Implementing this in the Contra envelope model improved volume match
  from ~82% to 96.6% on the Jungle trace comparison.
- For CV1: the parametric model's phase 2 already handles this
  correctly because it only runs for `fade_step` frames and doesn't
  continue indefinitely. The bounce-at-1 applies structurally to
  the Maezawa driver but doesn't change CV1 output.

### Verdict
DISPROVEN. Notes hold at vol=1, not vol=0. The disassembly explicitly
shows the increment. 96.6% volume match after the fix; remaining 3.4%
comes from decrescendo timing precision and auto-decrescendo mode
details not yet modeled.

**Files changed**: `frame_ir.py` (Contra envelope bounce-at-1),
`contra.json` (updated validation percentages).
**Prompts spent**: ~2.
**Lesson**: Always read the disassembly for edge-case behavior.
"Decays to zero" is an assumption; the hardware (or driver) may do
something else entirely.

---

## What the Research Process Actually Looks Like

Reading a log like this might suggest a clean, linear progression.
It was not. Here is what actually happened:

**It is iterative.** Every session started with a hypothesis that was
at least partially wrong. The envelope model took 3 failed hypotheses
before trace data revealed the actual pattern. The Contra extraction
took 4 versions before notes and timing were correct. Progress is
measured in hypotheses tested, not features shipped.

**It is mistake-driven.** The most valuable discoveries came from
mistakes. The octave bug was found because automated tests gave a
false sense of correctness. The phase2_start bug was found because
working on Contra forced a deeper look at code that seemed settled.
The EC pitch adjustment was found because the trace showed something
nobody expected.

**Every game is a new puzzle.** CV1 and Contra share a command set,
but the ROM layout, envelope model, percussion system, and bank
mapping are all different. The parser core transferred; everything
around it had to be rebuilt. Future games (Super C, TMNT, Gradius)
will require the same per-game investigation.

**The evidence hierarchy matters.** In decreasing reliability:
1. APU trace (hardware ground truth)
2. Annotated disassembly (explains why)
3. Automated trace comparison (catches errors but can miss systematic ones)
4. Ear comparison (catches gross errors, misses subtle offsets)
5. Reasoning about byte meanings (least reliable, most tempting)

**20 frames of trace data are worth more than 2000 words of analysis.**
The single most productive action in every session was extracting a
small number of real trace frames and looking at the actual values.
Modeling without data produced wrong models. Data without modeling
produced correct models.

The NES has hundreds of games with undocumented sound engines. Each
one is a puzzle with the same structure: find the data, understand the
commands, model the behavior, verify against hardware. The tools
built here (trace comparison, frame IR, pipeline) make each subsequent
game faster. But the intellectual work -- forming hypotheses, testing
them against evidence, accepting when you are wrong -- never gets
automated.
