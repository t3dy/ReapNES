# Grinding on the Pointer Table: What We Learned

## The Grind

We spent approximately 90 minutes and 15+ code iterations trying to
find the Super C pointer table / sound table. Here's what we tried
and why each approach failed.

### Attempt 1: Generic pointer table scan
**Method:** Search every 2-byte-aligned offset for sequences of 16-bit
values in the $8000-$BFFF range.
**Result:** 1,202 candidates. Top results were all false positives
with repeated pointer values ($8E8E, $A5A5). The search space was
too broad and the filter too weak.
**Why it failed:** NES ROMs are full of 16-bit values that happen to
fall in the $8000-$BFFF range. Without structural constraints, most
matches are tile data, code, or other non-music data.

### Attempt 2: Require unique ascending pointers
**Method:** Filter for 3+ unique pointers in ascending order with
targets containing E0-E4 octave commands.
**Result:** 37 candidates. Better, but still too many to manually
verify. The best candidate (Bank 6 $AE84) had real music data at
its targets but turned out to be a single track fragment, not the
master song table.
**Why it failed:** The filter was structural (pointer properties)
but didn't incorporate knowledge of the ACTUAL sound table format.

### Attempt 3: Brute-force parse scoring
**Method:** For each candidate, try to Maezawa-parse the target data
and count how many valid notes are produced.
**Result:** Top scorer had 576 "notes" — all from a single repeated
data region that the parser happened to not crash on. The scoring
function rewarded quantity without checking musical validity.
**Why it failed:** A permissive parser will find "notes" in almost
any data. The score correlated with data region size, not musical
content.

### Attempt 4: Contra-exact pattern match (18-01-02-03)
**Method:** Read the Contra disassembly to learn the exact control
byte encoding, then search Super C for that exact byte sequence.
**Result:** ZERO matches. Super C does not use the 18-01-02-03
control byte pattern at all.
**Why it failed:** We assumed Super C would use identical metadata
encoding. The note data is Maezawa-compatible but the sound table
format diverged.

### Attempt 5: Relaxed pattern match
**Method:** Search for any 4 consecutive 3-byte triples with
ascending unique addresses and E0-E4 in targets.
**Result:** Banks 5/6 at $8AFC emerged as the strongest candidate,
with real Maezawa note data (E3 32 06 = octave 3, D# dur 6).
But the control bytes ($3E, $09, $EB, $F4) don't match any known
Contra slot encoding.
**Status:** Best lead so far but unvalidated.

## What We Should Have Done

### 1. Read the disassembly FIRST, not last
We had the Contra disassembly the entire time. It documents:
- The sound_table_00 format (3-byte triples)
- The control byte encoding (slot = bits 0-2, additional = bits 3+)
- The exact BGM control byte values (0x18, 0x01, 0x02, 0x03)
- The channel mapping (slot 0=pulse1, 1=pulse2, 2=triangle, 3=noise)

We should have read this documentation BEFORE writing any search
code. Instead, we wrote generic search code, then gradually
re-derived what the disassembly already told us.

### 2. Use the trace to narrow the search
The trace tells us exactly what period values the driver outputs.
Those values come from a period table that's loaded from a specific
bank. By finding which bank uniquely contains the period table,
we identify the sound bank. We partially did this but didn't follow
through.

### 3. Search for the DRIVER CODE, not the data table
Instead of searching for the data table directly, we should search
for the DRIVER CODE that reads it. The sound engine's entry point
is called from the NMI handler every frame. The code that reads
sound_table_00 has a known pattern from the Contra disassembly:
- LDA (SOUND_TABLE_PTR),y
- Specific zero-page addresses ($E0, $E1, etc.)
- APU register writes ($4000-$4017)

Searching for these code patterns would locate the sound engine,
and the data table address would be hardcoded in the engine code.

### 4. The Mesen debugger is the right tool
A single breakpoint on $4002 (pulse period register) during music
playback would immediately show which code writes the period value.
Tracing back from that code to the table read would reveal the
table address in seconds. We spent 90 minutes doing ROM scanning
that a 30-second debugger session would have solved.

## The Meta-Lesson

**The pointer table grind is a symptom of working at the wrong
abstraction level.**

We were searching for DATA when we should have been searching for
CODE. The data table's format can vary between games, but the
driver code's behavior is observable via the Mesen debugger. The
debugger gives you ground truth: "THIS code at THIS address reads
from THIS table." No heuristics, no false positives, no scoring
functions.

The ROM scanning approach works when you know the EXACT format
(CV1: contiguous pointer table at known offset). It fails when
the format is unknown or has diverged from the reference
implementation.

## Rules for Next Time

1. **Read the reference disassembly COMPLETELY before searching.**
   Not just the data tables — read the code that accesses them.

2. **If the exact pattern isn't found in 2 searches, use the
   debugger.** Don't iterate through increasingly permissive
   heuristics. Each relaxation increases false positives
   exponentially.

3. **Search for code patterns, not data patterns.** The driver code
   is more conserved than the data layout. APU register writes
   ($4000-$4017) are invariant. Zero-page variable assignments are
   game-specific but structurally similar.

4. **The Mesen debugger > ROM scanning** for unknown formats.
   ROM scanning is appropriate for KNOWN formats. For UNKNOWN
   formats, dynamic analysis (breakpoints, trace) beats static
   analysis (byte pattern search) every time.

5. **Budget your search: 2 attempts max.** If attempt 1 (exact
   pattern) and attempt 2 (relaxed pattern) both fail, STOP
   scanning and switch to the debugger. Don't grind.
