# Pattern Matching: What We Learned

## The Core Problem

We're trying to find specific data structures inside NES ROM files.
The structures we're looking for (period tables, pointer tables,
sound tables) are byte patterns with known properties but unknown
locations. Pattern matching is how we find them.

## What Worked

### Exact match on known byte sequences
The Maezawa period table has EXACT known values: 1710, 1614, 1524...
Searching for `struct.pack("<12H", *maezawa)` either finds it or
proves it's absent. Binary. No false positives. This worked on CV1,
CV3, and CV2 (with a different but equally exact table).

### Ratio-based chromatic detection
When the exact values are unknown (CV3's ±1 tuning), searching for
12 consecutive 16-bit values where each ratio is 1.04-1.08 finds
period tables regardless of exact tuning. This found CV3's 36-entry
extended table.

### Trace-guided search
The Mesen trace tells us EXACTLY what period values the game uses.
Searching the ROM for those specific values narrows the bank. This
is the most reliable method because the trace is GROUND TRUTH.

## What Failed

### Heuristic scoring of parsed output
We scored pointer table candidates by how many "valid notes" a
Maezawa parser could extract from their targets. This rewarded
permissive parsing — the top scorer had 576 "notes" from what was
probably tile map data. A permissive parser finds notes in noise.

### Structural pattern matching across game boundaries
We searched Super C for Contra's exact control byte pattern
(18-01-02-03). Zero results. The same engine used different
metadata encoding in a different game. Structural patterns within
a SINGLE game's disassembly are reliable. Assuming they transfer
to other games is not.

### Increasingly permissive search relaxation
Each time a search returned zero results, we relaxed the filter.
Each relaxation expanded the search space and increased false
positives. After 5 rounds: thousands of candidates, no validated
matches. Relaxation is a death spiral — it doesn't converge.

## The Asymmetry

**Finding the note encoding: EASY.**
Maezawa notes (pitch×16 + duration) are self-describing. A few bytes
of E0-E4 octave commands mixed with note bytes is unmistakable.
There's no other NES data that looks like E3 42 06 32 06.

**Finding the table that INDEXES the note data: HARD.**
The table format varies per game. Control byte encodings,
entry sizes, grouping conventions, and slot assignments all change.
A 3-byte triple in Contra looks completely different from a
9-byte grouped record in CV1 or a nested pointer pair in CV3.

## Principles

1. **Search for invariants, not conventions.**
   Period values are invariant (physics). Table formats are
   conventions (programmer's choice). Search for invariants first.

2. **Dynamic analysis beats static analysis for unknowns.**
   ROM scanning = static analysis. Mesen breakpoints = dynamic
   analysis. When the format is unknown, dynamic wins because it
   observes the driver's actual behavior, not our guess about
   its data layout.

3. **Two attempts max, then switch tools.**
   Exact match → relaxed match → STOP SCANNING AND USE DEBUGGER.
   Each additional scan iteration has diminishing returns and
   increasing false positives.

4. **The reference disassembly is the most valuable resource.**
   Reading the Contra disassembly for 10 minutes would have
   saved 90 minutes of blind scanning. Always read the docs first.

5. **Validate against trace before trusting any candidate.**
   No amount of structural plausibility replaces comparing parsed
   output to the Mesen APU trace. The trace is always right.
