# Flexibility Goals

How to hold what we know without letting it calcify into dogma.

---

## The Problem

We've built a good system of warnings, invariants, checklists, and
failure mode catalogs. They exist because real mistakes cost real
time. But there's a risk: the warnings become walls instead of
guardrails. "CV2 is a dead end" prevented us from even looking at
the 7 tracks that might have taught us something. "Same period table
does NOT prove same driver" is true, but it could also discourage
us from exploring what two games with the same period table DO share.

Every lesson we've baked in was learned from exactly two games. Two.
That's not a law of NES sound engines — it's a sample size of two.

The next game we touch will either confirm or challenge every
assumption we've encoded. We need to be ready for both.

---

## Principle 1: Warnings Are Hypotheses, Not Laws

Every rule in CLAUDE.md, every invariant in INVARIANTS.md, every
failure mode in FAILURE_MODES.md — these are observations from CV1
and Contra. They are our best current understanding. They are not
physics.

When a new ROM contradicts a warning, the correct response is not
"the ROM must be wrong" or "skip it." The correct response is:

1. Note the contradiction
2. Investigate whether the warning was too narrow
3. Update the warning if the new evidence warrants it
4. Document WHY the warning changed, not just that it changed

The warning system should evolve. A warning that hasn't been
challenged by the third game might be a real invariant. A warning
that breaks on the third game was an artifact of the first two.

---

## Principle 2: Try It Before Ruling It Out

CV2 was labeled "dead end" based on solid evidence: no Maezawa
command signatures found. But the Antigravity session extracted 7
tracks anyway. Are they garbled? Probably. Are they definitely
garbled? We haven't listened. The listening would take 20 minutes
and might teach us something about driver boundaries that the
signature scan couldn't.

Super C parsed 9 tracks with the wrong pointer table. Are they all
wrong? Probably. But "probably wrong" and "verified wrong" are
different things. One of those 9 tracks might accidentally be
correct because the pointer offset happened to land on real music
data. That would be a data point about ROM layout patterns.

**Goal:** Before declaring anything impossible, spend 20 minutes
trying it and documenting what happens. The failure is often more
informative than the success.

---

## Principle 3: Hold Driver Families Loosely

We have "Maezawa" and "Fujio" as labels for Konami's sound drivers.
These are our names, inferred from 2 games and a dead-end
investigation. The actual Konami engineers may have used one driver
with compile-time flags, or three drivers that share subroutines,
or five drivers with overlapping code. We don't know.

What we know:
- CV1 and Contra share note/octave/repeat/end commands
- CV1 and Contra differ in DX byte count, envelope model, percussion
- CV2 didn't match the Maezawa signature scan
- CV3 uses a different mapper and expansion audio

What we don't know:
- Whether "Maezawa" and "Fujio" are truly separate engines or
  branches of the same codebase
- Whether CV2's command encoding shares ANY opcodes with CV1
- Whether there are intermediate variants (half-Maezawa, half-Fujio)
- Whether the Konami period table appearing in CV2 means shared
  utility code even if the driver is different

**Goal:** Treat driver family labels as working hypotheses. When a
new game doesn't fit cleanly into "Maezawa" or "Fujio," don't force
it. Create a new label or note the overlap. The taxonomy should
describe what we find, not prescribe what we expect.

---

## Principle 4: Let the ROM Speak First

The strongest pattern from our wins: every time we looked at actual
data before theorizing, we converged faster. Every time we theorized
before looking, we wasted prompts.

But "look at data first" doesn't mean "only look at data we expect
to find." When approaching a new ROM:

- **Scan broadly before scanning narrowly.** Don't just search for
  the Maezawa DX/FE/FD signature. Dump the first 256 unique byte
  values in the music data region. Look at what's there, not just
  what you're looking for.

- **Compare to known games structurally, not just by signature.**
  If a ROM has a 12-entry period table at a different offset, that's
  interesting even if the surrounding code is unfamiliar. If the
  pointer table format is 6-byte entries instead of 9 or 3, that's
  a new data point, not a failure.

- **Capture trace data for unknown games too.** The trace is pure
  hardware output. It doesn't care what driver produced it. A trace
  from an unknown game tells you channel count, volume behavior,
  timing resolution, and pitch patterns — all before you understand
  a single byte of the driver code.

**Goal:** Build exploration tools that show us what a ROM contains,
not just whether it matches what we've seen before.

---

## Principle 5: The Pipeline Should Degrade Gracefully

Right now, the pipeline either works (correct parse, good MIDI) or
crashes (wrong byte count, division by zero, infinite loop). There's
no middle ground. A parser that hits an unknown command should:

- Log the unknown byte with its offset and context
- Skip it with a best-guess byte count
- Continue parsing
- Produce output with gaps marked, not crash

This matters because partial output from an unknown driver is
often more valuable than no output. A parse that gets 60% of the
notes right tells you which commands you understand and which you
don't. A crash tells you nothing.

**Goal:** Unknown commands produce warnings, not errors. Every
parser should be able to produce partial output from any ROM in the
same driver family, even if some commands are unrecognized.

---

## Principle 6: Measure Overlap, Not Just Identity

The current driver identification approach is binary: "Is this
Maezawa? Yes/no." This misses a whole spectrum of partial overlap.

What if CV2's Fujio driver shares:
- The same period table (confirmed)
- The same note encoding ($00-$BF = pitch + duration)
- Different instrument commands
- Different envelope system
- Different pointer table format

That's not "same driver" or "different driver" — it's 40% overlap.
And that 40% might be enough to parse notes and timing even if
we can't decode the envelopes. A MIDI with correct pitches and
rhythms but flat dynamics is useful. A MIDI with correct pitches
and wrong dynamics is more useful than no MIDI.

**Goal:** Build comparison tools that measure the degree of overlap
between an unknown ROM and known drivers. Report similarity scores,
not just match/no-match.

---

## Principle 7: Version Everything, Regret Nothing

Every output file gets a version number. Every hypothesis gets a
status label. Every manifest entry says whether it's verified,
hypothesis, or unknown. This lets us be aggressive with
experimentation because nothing is lost.

Try parsing CV2 with the Maezawa parser? Version it as
`cv2_maezawa_attempt_v1`. It's wrong? Great — now we have a
labeled artifact that shows exactly how and where it's wrong.
That artifact is more valuable than the absence of an attempt.

**Goal:** The cost of trying something and being wrong should be
near zero. Version labels and status tags make this possible.

---

## Principle 8: The Third Game Changes Everything

CV1 taught us the driver. Contra taught us what varies per game.
The third game (Super C, or whichever comes next) will teach us
which of our abstractions are real and which are premature.

We should approach the third game with maximum openness:
- Don't assume it matches CV1 OR Contra
- Don't assume the unified parser design is correct
- Don't assume the manifest schema has the right fields
- DO use the existing tools and workflow
- DO capture everything that surprises us
- DO update the architecture AFTER the third game, not before

**Goal:** The third game is a learning opportunity, not a
validation exercise. If it breaks our assumptions, that's the
most valuable outcome.

---

## What This Means in Practice

### For the warning system:
- Keep the warnings. They prevent real mistakes.
- Add a "Confidence" field: HIGH (3+ games confirm), MEDIUM
  (2 games confirm), LOW (1 game, inferred).
- Review and potentially revise warnings after each new game.

### For driver identification:
- Report similarity scores, not just binary match/no-match.
- When a ROM partially matches, say what matches and what doesn't.
- Don't use "dead end" as a label. Use "requires new parser" or
  "partially compatible" or "unknown overlap."

### For the parser:
- Unknown commands warn, not crash.
- Partial output is better than no output.
- Every parse attempt is versioned and labeled.

### For our mental model:
- We know a lot about 2 games.
- We know a little about 2 more (CV2, CV3 partial extractions).
- We know almost nothing about the other 800 NES games.
- Every rule we've written is a hypothesis with n=2 evidence.
- The next game is the most important game.

---

## The Flexibility Spectrum

```
RIGID                                              FLEXIBLE
|-------|-------|-------|-------|-------|-------|-------|
   ^                  ^                           ^
   |                  |                           |
   "Dead end,      "Warnings        "Try everything,
    don't try"      as guides,        version the
                    verify with        failures,
                    data"              learn from
                                       partial
                                       results"

We were here -----> We should be here
```

The goal is not to abandon rigor. The trace is still ground truth.
The invariants still matter. The checklists still prevent real
mistakes. But rigor should make us more willing to experiment,
not less. Because every experiment, even a failed one, produces
data. And data is what moves us forward.
