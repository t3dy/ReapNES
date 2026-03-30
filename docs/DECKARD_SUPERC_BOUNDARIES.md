# Deckard Boundary Analysis: NES Music Studio ROM Extraction Pipeline

Applied to: the process of extracting music from new NES ROMs, with
Super C as the current case study and Gradius/CV2/CV3 as recent evidence.

---

## DETERMINISTIC TASKS

These should be code, not LLM judgment. If we're using the LLM for
these, it's WASTE.

- **ROM header parsing** (mapper, PRG/CHR banks, mirroring): iNES
  format is a fixed spec. `rom_identify.py` handles this correctly.

- **Period table scanning**: search ROM for known byte sequences.
  Exhaustive, zero ambiguity. Our python scripts do this right.

- **Mesen trace → WAV rendering**: read CSV, apply register values
  to APU synth, write WAV. Completely deterministic. Our trace
  renderer is game-agnostic and works perfectly.

- **Silence gap detection**: scan per-frame volume state, find runs
  of zero. Simple threshold logic. Works on every game tested.

- **nesmdb exprsco → WAV rendering**: read pickle, synth per-frame.
  Deterministic (once we fixed the 24fps rate bug).

- **Period-to-MIDI conversion**: `1789773 / (16 * (period + 1))` →
  frequency → MIDI. Pure math. No judgment needed.

- **Pointer validation**: given a candidate address, check if the
  16-bit values at that address fall in the $8000-$BFFF range and
  point to data containing E0-E4 octave commands. Deterministic.

- **Vibrato detection**: measure period variance per note. If
  period wobbles ±N around a center, flag as vibrato. Statistics.

- **Note encoding decode**: given a byte and the Maezawa rule
  (pitch = high nibble, duration = low nibble), extract pitch
  and duration. Bit manipulation.

- **Bank-switched address resolution**: given mapper type, bank
  number, and CPU address, compute ROM offset. Fixed formula
  per mapper.

---

## PROBABILISTIC TASKS

These genuinely need judgment. LLM or human ear required.

- **Driver family identification**: "Is this Maezawa?" requires
  pattern matching across multiple heuristic signals (command byte
  distribution, period table format, pointer structure). No single
  deterministic test is sufficient. **BUT** the confidence should
  always be LOW until verified by ROM scanning.

- **Track identification by ear**: "Is this Bloody Tears or the
  title screen?" Only a human who knows the game can answer this.
  Cannot be automated without a reference database.

- **Music vs SFX classification**: our pitch-jump heuristic
  (>12 semitones = SFX) is a GUESS. Some games have legitimate
  large interval jumps in music. Needs human validation.

- **Hypothesis document generation**: writing docs like
  HYPOTHESES_GRADIUS.md is inherently LLM work — synthesizing
  knowledge about game history, hardware, and driver families.
  BUT the specific claims need deterministic validation.

- **Command semantics inference**: "Does E7 mean vibrato speed
  or envelope index?" Requires reading disassembly, comparing
  across games, or trace correlation. Partially deterministic
  (trace correlation) but the interpretation is judgment.

- **Pointer table brute-force scoring**: our scoring function
  (count valid notes from parsed data) is heuristic. A "valid
  note" threshold is arbitrary. The top-scoring candidate isn't
  guaranteed to be correct.

---

## VALIDATION LAYERS

Where LLM/heuristic output enters the deterministic pipeline,
and how we validate it.

- **Driver family prediction → parser selection**: The LLM says
  "this is Maezawa" → we run the Maezawa parser. VALIDATION:
  trace comparison. If the parser output doesn't match the APU
  trace, the prediction was wrong. The trace is ground truth.

- **Pointer table candidate → track parsing**: The brute-force
  scorer says "$AE84 is the pointer table" → we parse tracks.
  VALIDATION: do the parsed notes match the trace melody? Cross-
  reference with nesmdb reference renders.

- **Track boundary detection → segment splitting**: Silence gap
  algorithm says "track boundary at frame 442". VALIDATION: user
  listens to both segments and confirms they're different songs.
  Cross-reference with nesmdb track durations.

- **SFX classification → music-only render**: Pitch-jump detector
  flags frames as SFX. VALIDATION: user listens to music-only
  and SFX-only renders. Are they properly separated?

- **Hypothesis → manifest JSON**: The hypothesis says "sound bank
  = 1, DX bytes = 3". VALIDATION: parser either produces correct
  output or crashes. Manifest fields are either right or wrong.

---

## BOUNDARY VIOLATIONS

### WASTE: LLM doing deterministic work

1. **Hypothesis docs predicting mapper number.**
   The swarm agent wrote "Mapper 0 (NROM)" for Gradius based on
   training knowledge. The actual mapper was 3 (CNROM). A 2-line
   python script reading ROM byte 6 is always right.
   RECOMMENDATION: `rom_identify.py` runs BEFORE any hypothesis
   doc is written. Hypothesis docs should cite ROM scan results,
   not training knowledge.

2. **LLM predicting period table format.**
   The swarm predicted "standard 12-entry chromatic table" for
   every game. Gradius has NO table. Super C's table is missing
   or stored differently. Prediction adds no value.
   RECOMMENDATION: scan first, document findings. Don't predict.

3. **LLM guessing pointer table addresses.**
   No amount of reasoning can guess that the pointer table is at
   $AE84 vs $B9F0. Only ROM scanning or disassembly can find it.
   RECOMMENDATION: brute-force scan with heuristic scoring (which
   we built), validated against trace data.

### RISK: Deterministic code doing judgment work

4. **Pitch-jump SFX detector using fixed >12 semitone threshold.**
   Some legitimate music jumps more than an octave (arpeggios,
   bass drops). The threshold should be configurable and validated
   per game against the user's ear.
   RECOMMENDATION: expose threshold as a parameter, always produce
   both music-only and SFX-only for human review.

5. **nesmdb pitch offset assumed to be zero.**
   Gradius nesmdb data was 2 octaves too high. We applied a fixed
   -24 semitone correction without understanding WHY it was offset.
   RECOMMENDATION: validate nesmdb pitch against trace data from
   the same game. The trace is always correct.

### DANGER: Unvalidated output entering the pipeline

6. **Brute-force pointer table → direct parser invocation.**
   If we take the top scoring candidate and feed it directly to
   the parser without trace validation, we could produce plausible
   but WRONG output (like the Antigravity session's CV2 tracks
   that were parsed with the CV1 pointer table).
   RECOMMENDATION: ALWAYS compare parser output to Mesen trace
   before declaring success. One validated track before batch.

---

## THE FUNDAMENTAL BOUNDARY

```
DETERMINISTIC (trust completely)     PROBABILISTIC (verify always)
─────────────────────────────────    ────────────────────────────
ROM bytes                            Driver family membership
Mesen APU trace                      Command semantics
Period math                          Track identification
Silence detection                    "Does this sound right?"
Pointer validation                   Pointer table scoring
Note decode (given encoding)         Encoding determination
nesmdb frame data                    nesmdb pitch calibration
Bank/address resolution              Which bank has the driver
```

The LEFT column is ENGINE work. Build it once, trust it forever.
The RIGHT column is INTELLIGENCE work. Always validate against
the left column before acting on it.

**The meta-lesson from this session**: we spent 15 minutes on
hypothesis documents that were wrong, and 5 minutes on a Mesen
capture that was right. The trace is the boundary between
speculation and ground truth. Capture first, hypothesize second.
