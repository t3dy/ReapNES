# The Wishes Adventure

What we learned by investigating all 14 wishes from WINSWISHES.md.
Each wish got its own agent, its own deep-dive report, and its own
surprises. This document captures the discoveries, corrections, and
strategic clarity that came from the investigation — not just what
we want to do, but what we now know that we didn't know before.

---

## The Discoveries

### The Contra Trace Already Exists (Wish 1)

We wrote "capture the Contra trace" as wish #1 — the single
highest-value action. The agent found it's already done:
`extraction/traces/contra/jungle.csv`, 2976 frames, captured
2026-03-28. The real work is closing the gap between parser output
and trace: 72 pitch mismatches and 175-250 volume mismatches per
channel. The wish was reframed from "capture" to "converge."
Estimated 2-3 sessions.

### The CV1 Parser EB Bug (Wish 4)

The vibrato investigation uncovered a **latent parser bug**: CV1's
`parser.py` line 421 treats EB as a 1-byte command, but the Maezawa
engine reads 3 bytes (opcode + delay + amount). If EB ever appears
in a game parsed via the CV1 path, the parse stream desynchronizes
and every subsequent note is wrong. Neither CV1 nor Contra music
data contains EB, so this has never fired — but it's a time bomb
for Super C, TMNT, or Gradius. Fix: 30-60 minutes of defensive work.

### Super C's 9 Tracks Are Probably Garbled (Wish 3)

The existing Super C output (9 tracks with MIDI/WAV/REAPER) was
parsed using the CV1 parser with CV1's pointer table address ($0825).
But Super C is a different ROM with a different pointer table location.
The parser was reading arbitrary bytes that happened not to crash.
The 6 missing tracks (02, 04, 06, 07, 09, 10) hit division-by-zero.
The 9 "successful" tracks need a listening audit — they may be garbled
data that coincidentally sounds like music.

### CV2's 7 Tracks Are Almost Certainly Wrong (Wish 11)

Same story as Super C but worse. CV2 uses the Fujio driver (confirmed
different from Maezawa), but the Antigravity session ran the CV1
parser against it anyway. The 7 surviving tracks are CV1 pointer
offsets ($0825) landing on arbitrary CV2 ROM bytes. The YouTube
description incorrectly labels the driver as "Maezawa variant."
A listening audit would confirm, but the agent's assessment is that
these are almost certainly noise, not music. Full Fujio driver RE
would take 12-21 hours (6-8 sessions).

### The Noise Synth Is Pure Random (Wish 13)

`render_wav.py` uses `np.random.uniform(-1, 1)` for percussion —
literal white noise, not the NES hardware LFSR. Real NES noise uses
a 15-bit linear feedback shift register with 16 rate presets and 2
modes (long sequence vs short 93-step loop). Contra Jungle uses only
2 period values (7 and 31) and mode 0. Implementing the real LFSR
plus per-hit period/mode from trace data would transform the drum
sound from generic static to recognizable NES percussion. 7-10 hours.

### 117 Fugue RPPs Need Missing MIDIs (Wish 10)

The combinatorial Fugue matrix (117 REAPER projects, 0 WAVs) can't
just be batch-rendered — the source Bach MIDI files were referenced
from `C:\Users\PC\Downloads\` which may have been cleaned up. Only 6
MIDIs exist in `midi_remapped/`. The batch render script is also
hardcoded to 6 specific jobs from a prior session. Completing this
requires: finding/re-downloading the Bach MIDIs, updating the batch
driver, then rendering. 2.5-4 hours if MIDIs are available.

### ~25 Website Pages Are Invisible (Wish 9)

The Jekyll site has ~50 pages that render correctly but only ~26 are
linked from the homepage. The rest have no navigation path — they
exist but are invisible to visitors. The hacker theme provides no
sidebar, breadcrumbs, or table of contents. Several internal docs
(HANDOVER, MISTAKEBAKED, DECKARDCONTRASTAGE2) are being served
publicly because they're not in _config.yml's exclude list. 6.5 hours
to fix navigation, exclude internal docs, and add cross-linking.

### The Big Commit Landed But ~40 Files Remain (Wish 14)

The 305-file commit covered the bulk of Antigravity work, but ~40
files are still untracked: 20 REAPER projects (CV1 full soundtrack,
Contra versions, VampireKiller iterations), 19 Bach MIDIs in
`midi_remapped/`, 1 PNG screenshot. All are small text/binary files.
The 106 MB of WAV files are correctly gitignored. Cleanup: 5 minutes.

---

## The Priority Stack

The investigation crystallized a clear ordering. Here's the stack
ranked by value-per-effort, with the agents' estimates:

### Tier 1: Do Now (High Value, Low Effort)

| # | Wish | Effort | Why Now |
|---|------|--------|---------|
| 4 | Fix EB byte count in CV1 parser | 30-60 min | Latent bug, prevents future desync |
| 14 | Commit remaining ~40 files | 5 min | Prevents data loss |
| 1 | Close Contra trace gap | 2-3 sessions | Trace exists, highest fidelity payoff |

### Tier 2: Do Next (High Value, Medium Effort)

| # | Wish | Effort | Why Next |
|---|------|--------|----------|
| 3 | Super C (third game) | 4-7 sessions | Validates multi-game workflow, HIGH priority |
| 7 | Address resolver abstraction | ~2 hours | Prerequisite for any new mapper |
| 8 | Runtime manifest loading | 6-8 hours | Prerequisite for config-driven parsing |
| 13 | Noise channel LFSR | 7-10 hours | 4th in fidelity stack, real drum sounds |

### Tier 3: Medium Term (Medium Value, Medium Effort)

| # | Wish | Effort | When |
|---|------|--------|------|
| 5 | DPCM sample decoding | 5-7 hours | After noise channel |
| 9 | Website polish | 6.5 hours | After content stabilizes |
| 10 | Fugue matrix render | 2.5-4 hours | When Bach MIDIs are located |
| 2 | Triangle precision | 5-9 prompts | After Contra converges |

### Tier 4: Long Term (High Value, High Effort)

| # | Wish | Effort | When |
|---|------|--------|------|
| 6 | Expansion audio (MMC5+VRC6) | 12-18 sessions | After Super C, for CV3 |
| 11 | CV2 Fujio driver RE | 12-21 hours | After easy Maezawa games done |
| 12 | Non-Konami (Capcom, Sunsoft) | 15-25 sessions | After Konami family complete |

---

## Corrections to Our Understanding

The wishes investigation corrected several beliefs:

1. **"We need to capture the Contra trace"** → It already exists.
   The real gap is parser-to-trace convergence.

2. **"Super C's 9 tracks are working"** → They were parsed with the
   wrong pointer table. Probably garbled.

3. **"CV2 extracted 7 tracks successfully"** → Almost certainly wrong.
   CV1 parser on a Fujio-driver ROM produces noise, not music.

4. **"EB is unused and harmless"** → The CV1 parser has a byte-count
   bug that would desync on any game that uses EB. Time bomb.

5. **"The Fugue matrix just needs a batch render"** → The source MIDI
   files may be missing. The batch script is hardcoded. More work
   than expected.

6. **"The website is deployed"** → It's deployed but half the pages
   are invisible and internal docs are leaking publicly.

7. **"All Antigravity work is uncommitted"** → 305 files were just
   committed. ~40 remain. The crisis is mostly resolved.

---

## What This Means for CV2

Wish 11 was the deep dive into Castlevania II. Here's the bottom line:

**The 7 extracted tracks are almost certainly wrong.** They were
produced by running the CV1 Maezawa parser against a ROM that uses
the completely different Fujio sound engine. The parser happened not
to crash on 7 of ~15 tracks, but the bytes it read as "music data"
were whatever the CV1 pointer table offset ($0825) pointed to in the
CV2 ROM — which is arbitrary data in a different driver's format.

**CV2 is a real reverse engineering project, not a config change.**
The Fujio driver has different command encoding, different envelope
system, different pointer structure. It requires:
- Mapper 1 (MMC1) address resolution (not yet implemented)
- New command format discovery (no disassembly known)
- New envelope model (unknown type)
- New parser module (not a config variant of Maezawa)

**Estimated effort: 12-21 hours across 6-8 sessions.**

**But Phase 1 (listening audit) is just 1-2 hours** and would
definitively answer whether any of the 7 tracks are usable or if
they're all garbled. That's the first thing to do if we want to
pursue CV2.

---

## The Session's Output

| Artifact | Count | Location |
|----------|-------|----------|
| Wish investigation reports | 14 | `docs/wishes/WISH_01` through `WISH_14` |
| Bugs discovered | 1 (EB byte count) | parser.py line 421 |
| Corrections to beliefs | 7 | Listed above |
| Priority stack | 4 tiers, 14 items | This document |
| Total estimated effort (all wishes) | ~80-130 hours | Across all tiers |

The wishes aren't just a list anymore. They're individually researched,
estimated, risk-assessed, and prioritized. The next step for any wish
is to read its report in `docs/wishes/` and follow the concrete steps.
