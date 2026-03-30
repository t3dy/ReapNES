# How Gradius Went: Pre- and Post-Capture

## The Prediction vs Reality

### What the swarm predicted (pre-capture)

The research swarm agent wrote HYPOTHESES_GRADIUS.md with these claims:

- **Mapper 0 (NROM)** — WRONG. Actual: mapper 3 (CNROM)
- **Maezawa family driver (65% confidence)** — WRONG. No period table at all
- **Standard 12-entry chromatic period table** — WRONG. No period table exists
- **MEDIUM difficulty** — partially right, but for wrong reasons
- **"Scan ROM for byte sequence `06 AE 06 4E 05 F4`"** — would have found nothing

The swarm agent was writing from training knowledge without touching
the ROM. Every concrete prediction was wrong because Gradius doesn't
follow the Maezawa pattern at all.

### What hands-on ROM analysis found (15 minutes of actual work)

1. **Mapper 3 (CNROM)**, 32KB PRG, 32KB CHR, no PRG banking
2. **ZERO period table** — searched exhaustively (full 12-entry, partial,
   split lo/hi, chromatic ratio scan, CV3-style modified). Nothing.
3. **E0-EF command system** — all 16 values used (vs Maezawa's 5).
   Variable-length groups of E-commands followed by small data bytes.
4. **Two flat pointer tables** at $D7E2 (40 entries) and $D83A (31 entries)
5. **FE/FD/FF control flow** present — partial DNA shared with Maezawa
6. **Conclusion: pre-Maezawa or independent Konami driver**

Every one of these findings came from direct ROM scanning in python,
not from assumptions or training knowledge.

### What the Mesen capture proved (5 minutes)

1. **The trace render sounds like Gradius.** Frame-accurate APU playback
   of the capture produces recognizable Stage 1 music. This validates
   our entire trace→synth pipeline on a non-Maezawa game.
2. **One capture = one song.** 80 seconds of capture yielded one intro
   jingle (1.4s) + one song looping 4x (17.2s per loop). The silence
   gap detection correctly found the loop boundary.
3. **Melody is in B4-B5 range** with E/B/F# as dominant notes = E major,
   consistent with "Challenger 1985."

## What Went Right

### 1. The trace pipeline is game-agnostic

The trace→WAV renderer we built for CV2 worked on Gradius with zero
modifications. Feed it any Mesen APU capture CSV and it produces
accurate audio. This is a **universal tool** — it doesn't care what
driver the game uses because it operates at the hardware register level.

### 2. ROM scanning killed bad hypotheses fast

15 minutes of python scripts scanning for period tables and command
signatures definitively proved this is NOT Maezawa. Without this step,
we could have spent hours trying to make the CV1 parser work on data
that has a fundamentally different encoding.

This is the `rom_identify.py` workflow from CLAUDE.md paying off:
**identify the driver BEFORE writing any parser code.**

### 3. The nesmdb renders exposed their own bugs

The nesmdb v1 renders were 2.5x too fast (rendering at 60fps instead
of the dataset's 24fps) and 2 octaves too high on Gradius. The user
caught this by listening ("tempo values might be off and the melodies
are all wild"). We fixed both issues and preserved v1 for comparison.

**Lesson: the user's ear is the ultimate validator.** This is exactly
what CLAUDE.md rule 6 says: "Automated tests miss systematic errors.
User MUST listen."

### 4. Silence-gap detection segmented the capture automatically

A simple algorithm (find runs of 5+ frames where all channel volumes
are zero) correctly identified:
- The intro jingle boundary
- The main song start
- The loop point
- The capture end

This is the seed of an automated track segmentation tool.

### 5. We got playable output in one session

Despite Gradius being the "hardest Konami target," we produced:
- 1 trace-accurate WAV of the Stage 1 theme
- 4 segmented WAVs (intro, one loop, extended, outro)
- 12 nesmdb reference renders (corrected tempo)
- A comprehensive hypothesis document with verified ROM facts

## What Went Wrong

### 1. The swarm prediction was almost entirely wrong

The research agent confidently predicted mapper 0, Maezawa family,
standard period table — all wrong. This is exactly the failure mode
documented in MISTAKEBAKED.md: **"Same publisher ≠ same driver."**

The swarm agent had no way to check its claims against the actual ROM.
Hypothesis documents written without ROM access are essentially
fan fiction with confidence scores.

**Fix going forward:** Hypothesis reports should have a bright red
"UNVERIFIED — requires ROM analysis" banner until someone runs the
actual scans. Or better: run the scans AS PART OF the hypothesis
generation.

### 2. The nesmdb pitch offset went undetected until the user listened

We rendered all nesmdb tracks with pitches 2 octaves too high and
didn't notice until the user said "melodies are all wild." Our
rendering code didn't validate that the pitch range was reasonable
for NES music (typically MIDI 36-84, not 83-93).

**Fix going forward:** Add a sanity check — if median pitch > MIDI 80
for a pulse channel, flag it.

### 3. We can't track-split from a single long capture

The 80-second capture was one song looping. To get the full Gradius
soundtrack, the user would need to capture each track separately
(play through stages, die, game over screen, etc.). There's no way
to extract Track 3 from a capture of Track 2.

This is a fundamental limitation of the trace approach: **one capture
= one song.** We need either ROM parsing or multiple captures.

## How This Shapes Super C

### What carries over directly

1. **The trace→WAV pipeline.** Capture in Mesen, copy CSV, render WAV.
   Works on any game. We should capture Super C's Stage 1 theme as
   the first validation target.

2. **ROM scanning scripts.** Period table search, command signature
   scan, pointer table finder — all reusable. Run these FIRST on the
   Super C ROM before touching any parser code.

3. **The nesmdb reference library.** We found 14 Super C tracks in
   nesmdb. Render them at the correct 24fps rate as listening targets
   for the user to identify.

4. **Silence-gap segmentation.** If the user captures a long play
   session, we can automatically split it into tracks.

### What's different about Super C

Super C is the **opposite** of Gradius on the difficulty spectrum:

| Factor | Gradius | Super C |
|--------|---------|---------|
| Driver family | Unknown/pre-Maezawa | 90% Contra variant |
| Period table | NONE | Will be standard |
| Existing parser | None applicable | contra_parser.py |
| Mapper | 3 (CNROM) | 2 (UNROM, same as Contra) |
| Key unknown | Everything | Pointer table address only |

Super C should be a **configuration task**, not a reverse engineering
task. The contra_parser.py already handles:
- DX 3/1 byte count
- Lookup table envelopes
- DMC percussion
- Bank-switched addressing

We need to find:
1. The pointer table address (currently hardcoded for Contra)
2. The sound bank number
3. The track count and mapping

### Concrete Super C plan

1. **Run ROM scans** — period table location, command signatures,
   pointer table candidates
2. **Capture one Mesen trace** — Stage 1 "Thunder Landing"
3. **Find the pointer table** — scan near the period table, or use
   Mesen breakpoints on the JSR that reads it
4. **Create `extraction/manifests/super_c.json`** with the addresses
5. **Run contra_parser.py with Super C manifest** — parse one track
6. **Compare to trace** — fix any mismatches
7. **Batch extract all 14 tracks**

If the pointer table is at a different address but the format matches
Contra, steps 4-7 could take under an hour.

### The meta-lesson

**Gradius taught us that ROM analysis must come before hypothesis
generation.** The swarm's predictions were worthless without ROM access.
For Super C, we skip the speculation phase entirely and go straight to:
scan ROM → find addresses → configure manifest → parse.

The swarm research documents (DRIVER_TAXONOMY.md, COMMAND_VARIABILITY.md,
etc.) are still valuable as a FRAMEWORK for thinking about what to look
for. But the specific predictions for individual games need empirical
validation before they're trusted.

This is the Deckard boundary in action: **deterministic ROM scanning
is ENGINE work (always correct), while driver family prediction is
LLM work (often wrong).** Trust the scanner, verify the prediction.
