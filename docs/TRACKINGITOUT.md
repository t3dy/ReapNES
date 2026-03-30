# Tracking It Out: How Track Boundary Detection Evolved

## Castlevania 1: The Easy Case

CV1 was our first game and we had every advantage: a known
disassembly, a verified parser, and a pointer table that told
us exactly where each track started in ROM. There was no "track
boundary detection" problem because the pointer table IS the
track list. Parse track 0, you get Prologue. Parse track 1, you
get Vampire Killer. Done.

**Method: pointer table gives you tracks directly.**
**Accuracy: 100% — the ROM tells you.**
**Effort: zero detection work, all parsing work.**

The pointer table at $0825 holds 15 entries, each with 3 channel
pointers (pulse1, pulse2, triangle) grouped in 9-byte records.
Track boundaries are defined by the data structure, not inferred
from audio.

## Contra: Same Story, Known Structure

Contra also had a full annotated disassembly. The pointer table
format was different (flat list of 2-byte pointers, 4 per track
including DMC) but the principle was the same: the ROM data
structure defines the track list.

**Method: pointer table + disassembly.**
**Accuracy: 100%.**
**Effort: zero detection, needed the disassembly to find the format.**

The lesson from CV1→Contra: same driver family, different pointer
table format. You can't assume the grouping (9-byte vs 8-byte
entries) or the channel count (3 vs 4) carries over.

## CV2: First Real Detection Problem

CV2 was where we first needed to FIND tracks without a known
pointer table. We discovered a hierarchical structure:

1. **Song table** at ROM 0x00CE0 — 17 pointers to song data
2. **Song data** — sequences of phrase references (0x20-0x3F)
   with FB section markers and FE loop counts
3. **Phrase library** at ROM 0x00B60 — 30 phrase pointers to
   note-level data

Track boundaries here were defined by the song table. Each of
the 17 entries is one "song" (though some share data and some
are padding entries pointing to the same address).

But we couldn't NAME the tracks without the user's help. We
rendered Mesen traces and the user identified:
- "That's the load screen music, not Bloody Tears"
- "That's the night music"

**Method: ROM song table structure + user ear identification.**
**Accuracy: structural boundaries 100%, naming requires user.**
**Effort: significant RE to find the song table.**

The nesmdb reference renders (once fixed to 24fps) gave us
labeled tracks to compare against. But the nesmdb data is one
loop — it doesn't tell you where the track is in the ROM.

## Gradius: Trace-Only Detection

Gradius was the first game where we had NO ROM understanding
(non-Maezawa driver, unknown encoding) and relied entirely on
the Mesen trace for track detection.

**The algorithm:**
1. Build per-frame total volume (sum all channel volumes)
2. Find runs of N+ frames where total volume = 0
3. Each silence gap = potential track boundary
4. Split the audio at these boundaries
5. User listens to each segment and identifies

**Results on Gradius (80.2 second capture):**
```
Silence gaps found (≥10 frames):
  Frames 23-85    (62f, 1.0s) — gap between intro jingle and main theme
  Frames 1085-1118 (33f, 0.6s) — loop point (same song restarts)
  Frames 4746-4779 (33f, 0.6s) — another loop point
```

This produced 4 segments:
- Seg 1 (1.4s): intro jingle
- Seg 2 (17.2s): one full loop of Stage 1
- Seg 3 (61.0s): same song looping (identical first 20 notes)
- Seg 4 (0.6s): tail

**Key discovery: melody comparison confirms loop vs new track.**
We compared the first 20 notes of Seg 2 and Seg 3 — perfect
20/20 match. That's not a track boundary, it's a loop.

**Method: silence gap detection + melody comparison + user ear.**
**Accuracy: boundaries correct, but only ONE song in the capture.**
**Effort: minimal code, but only detects what you capture.**

### The SFX separation problem

Gradius gameplay traces include laser sounds, explosions, and
power-up jingles mixed with the background music. We separated
these using a pitch-jump heuristic:

- If a pulse channel's pitch jumps >12 semitones in one frame,
  flag it and the next 7 frames as SFX
- If pitch exceeds MIDI 90, flag as SFX
- Noise channel: bursts >8 frames at volume ≥8 = explosion SFX

This produced usable music-only and SFX-only renders, plus
per-channel stems. The user can evaluate whether the separation
is clean.

**Limitation: the threshold is arbitrary.** 12 semitones works
for Gradius but would false-positive on games with large melodic
intervals. The noise threshold misses short drum-like SFX that
are part of the music.

## Super C: Combining All Methods

Super C uses everything we learned:

1. **Mesen trace capture** (5 min) → render WAV → user identifies
   "that's Thunder Landing with the helicopter intro"
2. **Silence gap detection** → found one 5.7s gap separating
   intro SFX from Stage 1 theme
3. **nesmdb reference durations** → Thunder Landing = 56.7s,
   our Seg 2 = 60.6s (close match, difference is helicopter SFX)
4. **ROM brute-force scan** → pointer table candidate at Bank 6
   $AE84 with real Maezawa note data

**Where we are: trace-identified ONE track. ROM scan found a
pointer table candidate that could give us ALL tracks. Need to
validate the candidate against the trace.**

## What We've Learned: A Formalized Process

### Level 1: Trace-Based (works on ANY game)

```
1. Capture Mesen APU trace of gameplay
2. Render WAV from trace (game-agnostic pipeline)
3. User confirms what track(s) they captured
4. Silence gap detection splits into segments
5. Melody comparison identifies loops vs new tracks
6. SFX heuristic separates music from gameplay sounds
```

**Pros:** works on any game, no RE needed, accurate audio.
**Cons:** one capture = one track. Full soundtrack requires many
captures or a sound test mode.

### Level 2: nesmdb Cross-Reference (works for games in the database)

```
1. Render all nesmdb tracks for this game at correct frame rate
2. User matches trace segments to nesmdb labeled tracks
3. nesmdb durations cross-reference against trace segment lengths
4. Use nesmdb track count to estimate how many tracks remain
```

**Pros:** gives us track NAMES and expected durations.
**Cons:** nesmdb may have pitch/tempo artifacts. Not all games
are in the database. One loop only per track.

### Level 3: ROM Pointer Table (works for known driver families)

```
1. Scan ROM for period table and command signatures
2. Brute-force pointer table search with heuristic scoring
3. Validate top candidate by parsing one track
4. Compare parsed output to Mesen trace
5. If match: pointer table is confirmed, parse all tracks
6. Each pointer table entry = one track with known channels
```

**Pros:** gives ALL tracks at once with channel separation.
**Cons:** requires driver RE. Pointer table might not be found
(Super C). Brute-force can produce false positives.

### Level 4: Full Disassembly (gold standard)

```
1. Find or create annotated disassembly of sound engine
2. Read pointer table address, track count, data format directly
3. Build manifest from verified facts
4. Parse all tracks with 100% confidence
```

**Pros:** no guessing. Every field in the manifest is verified.
**Cons:** disassembly may not exist. Creating one is weeks of work.

## Guidelines for Future Games

### Always

1. **Capture a trace first.** Before any ROM scanning, before any
   hypothesis docs. The trace gives ground truth in 5 minutes.
2. **Render nesmdb references** if the game is in the database.
   Correct the frame rate (check the `rate` field, not assumed 60fps).
3. **Version all outputs.** Never overwrite. v1, v2, v3.
4. **User listens** before anything is declared "correct."

### For track boundary detection

5. **Silence gaps ≥15 frames = track boundary.** Shorter gaps
   (5-14 frames) are usually musical rests within a track.
6. **Melody comparison across boundaries** distinguishes loop
   points from actual track changes. Compare first 20 notes.
7. **Cross-reference segment duration with nesmdb track duration.**
   ±10% match = probably same track. >2x = looping.
8. **Multiple captures are better than one long capture.** Each
   capture should target one specific track if possible.

### For SFX separation

9. **Per-channel stems are more useful than algorithmic separation.**
   Let the user decide which channel has music vs SFX at each point.
10. **Pitch-jump threshold should be per-game configurable.**
    12 semitones works for action games. RPGs and platformers may
    need different thresholds.

### For pointer table hunting

11. **Scan ROM AFTER getting a trace**, not before. The trace tells
    you what periods the game actually uses, which narrows the bank.
12. **Brute-force with validation, not scoring alone.** The
    highest-scoring pointer table candidate might be wrong. Parse one
    track and compare to trace before committing.
13. **Check for existing disassemblies** before spending hours on
    ROM scanning. The Contra disassembly exists and documents the
    exact same engine Super C uses.

## The Capture-First Pipeline

```
CAPTURE (5 min)
    ↓
RENDER WAV (instant)
    ↓
USER IDENTIFIES TRACK (10 sec)
    ↓
SCAN ROM FOR STRUCTURE (15 min)
    ↓
CROSS-REFERENCE WITH nesmdb (5 min)
    ↓
FIND POINTER TABLE (brute force or disassembly)
    ↓
VALIDATE ONE TRACK vs TRACE
    ↓
BATCH EXTRACT ALL TRACKS
```

This pipeline emerged from doing it wrong first (hypothesizing
without ROM data), then doing it partially right (ROM scanning
without trace), then doing it right (trace first, then ROM).

Each game we tackle refines the process. CV1 gave us the parser.
Contra gave us the disassembly reference. CV2 taught us about
driver diversity. Gradius proved the trace pipeline is universal.
Super C is testing whether brute-force pointer table discovery
can replace disassembly.

The next game after Super C will be the first one where we
execute this pipeline from step 1 with full confidence.
