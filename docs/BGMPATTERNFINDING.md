# BGM Pattern Finding: How It Worked Across Games

## What Is a "BGM Pattern"?

Every NES game that plays background music needs a way to say "play
track N." This requires a data structure that maps a track number to
the per-channel music data. The structure that does this mapping is
what we call the "BGM pattern" — the metadata format that the sound
engine reads to know WHERE the actual note data lives.

This is NOT the note data itself. It's the INDEX to the note data.
Finding this index is the key that unlocks the entire soundtrack.

## How Each Game Stores the BGM Pattern

### Castlevania 1: Simple Grouped Pointer Table

**Format:** Contiguous block of 9-byte records at ROM $0825.
Each record = 3 channel pointers (pulse1, pulse2, triangle) × 3 bytes
(2-byte address + 1-byte padding/config).

```
Track 0: ptr_p1, ptr_p2, ptr_tri  (9 bytes)
Track 1: ptr_p1, ptr_p2, ptr_tri  (9 bytes)
...
Track 14: ptr_p1, ptr_p2, ptr_tri (9 bytes)
```

**How we found it:** The disassembly told us. We never had to search.
The pointer table address ($0825) was known from the CV1 parser that
already existed.

**Finding difficulty:** ZERO — it was given to us.

### Contra: Sound Code Table (3-byte triples)

**Format:** `sound_table_00` at bank 1, address $88E8. NOT a simple
pointer table. Instead, a sequential table of 3-byte entries:

```
Entry: [control_byte] [addr_lo] [addr_hi]

Control byte encoding:
  bits 0-2: sound slot (0=pulse1, 1=pulse2, 2=tri, 3=noise, 4=sfx_pulse, 5=sfx_noise)
  bits 3+:  number of additional entries that follow for this sound

BGM entry: 4 consecutive triples
  0x18 addr_p1  (slot 0, 3 more entries)
  0x01 addr_p2  (slot 1, 0 more)
  0x02 addr_tri (slot 2, 0 more)
  0x03 addr_noi (slot 3, 0 more)
```

This table contains ALL sounds — SFX AND music. BGM entries are
distinguished by the $18 control byte (slot 0 with 3 additional
channels). SFX use control bytes $04 (sfx pulse, 0 additional) or
$0C (sfx pulse, 1 additional for noise).

**How we found it:** The Contra disassembly documents it fully.
`sound_table_00` is labeled, commented, and every entry is annotated
with the sound name and channel mapping.

**Finding difficulty:** ZERO for Contra itself. The problem is that
we ASSUMED Super C would use the same format. It doesn't.

### CV2: Hierarchical Song/Phrase Architecture

**Format:** Three-level structure in bank 0:

```
Level 1: Song table at ROM $00CE0
  17 pointers to per-song sequence data

Level 2: Per-song sequence data
  FB commands (set parameters) + phrase references (0x20-0x3F)
  FE repeat counts

Level 3: Phrase library at ROM $00B60
  30 pointers to note-level data
```

Each song is a SEQUENCE OF PHRASES, not raw note data. The phrases
themselves are short motifs (4-8 notes). This is a completely
different architecture from Maezawa — it's the Fujio driver.

**How we found it:** ROM scanning found the period table, then we
searched nearby for pointer-like structures. The phrase library was
found first (30 pointers at $00B60), then the song table was found
by tracing which entries the phrase pointers fed into.

**Finding difficulty:** HIGH. Required understanding a non-Maezawa
encoding from scratch. The phrase-based architecture was unexpected.

### CV3: Nested Pointer Pairs

**Format:** Pointer table at bank 0, starting at $8076.
40 entries, each pointing to a sub-structure of paired pointers:

```
Entry[0] -> ($8184, $82E0): (channel_1_data, channel_2_data)
Entry[1] -> ($8187, $82E2): next section
...
```

Each entry contains paired 16-bit pointers for two channels. The
note encoding IS Maezawa (pitch×16 + duration, E0-E4 octaves) but
the pointer structure is unique to CV3.

**How we found it:** Period table scan found a 36-entry extended
table in bank 4. The pointer table was found in bank 0 by scanning
for sequences of ascending pointer pairs. The Maezawa note encoding
was confirmed by decoding target data.

**Finding difficulty:** MEDIUM. The period table led us to the right
area, but the nested pair structure was non-obvious.

### Gradius: Unknown Driver, No Standard Pattern

**Format:** Two flat pointer tables at $D7E2 (40 ptrs) and $D83A
(31 ptrs). No period table exists. The E-command system uses 16
values (E0-EF) instead of Maezawa's 5 (E0-E4).

**How we found it:** Brute-force pointer table scan. Since the
driver is non-Maezawa, we couldn't use period table location or
command signature correlation to narrow the search.

**Finding difficulty:** MEDIUM for the pointer tables themselves,
but HIGH for understanding what they mean. We can find the tables
but can't parse the music data they point to.

### Super C: Known Engine, Unknown Table Format

**Format:** UNKNOWN. The note encoding is Maezawa-compatible (E0-E4
octaves, pitch×16+duration, DX instrument commands). But the
sound_table_00 equivalent uses different control byte values than
Contra. The exact $18-$01-$02-$03 BGM pattern does NOT appear in
the Super C ROM.

Best candidate: Banks 5/6 at $8AFC, with control bytes $3E/$3F
and addresses pointing to real Maezawa note data. But this hasn't
been validated against the trace.

**How we tried to find it:**
1. Generic pointer scan → 1202 false positives
2. Filtered pointer scan → 37 candidates, none validated
3. Brute-force parse scoring → top scorer was false positive
4. Exact Contra pattern match → ZERO results
5. Relaxed pattern match → Banks 5/6 candidate, unvalidated

**Finding difficulty:** HIGH despite using a known engine. The table
format divergence from Contra was not anticipated.

## The Pattern Across Games

| Game | Engine | Table Type | How Found | Difficulty |
|------|--------|-----------|-----------|------------|
| CV1 | Maezawa | Grouped 9-byte records | Disassembly | Zero |
| Contra | Maezawa variant | 3-byte triples with slot encoding | Disassembly | Zero |
| CV2 | Fujio | 3-level hierarchy (song/phrase/note) | ROM scanning | High |
| CV3 | Maezawa extended | Nested pointer pairs | ROM scanning + period table | Medium |
| Gradius | Unknown | Flat pointer tables | Brute-force scan | Medium |
| Super C | Contra variant | UNKNOWN | Failed after 5 attempts | High |

## Key Insight: The Table Format Is the Hardest Part

The NOTE ENCODING is relatively stable within the Maezawa family:
pitch×16+duration, E0-E4 octaves, DX instruments, FE/FD/FF control
flow. This encoding works across CV1, Contra, CV3, and Super C.

But the METADATA — how the engine finds the note data — varies
drastically:
- CV1: fixed-size grouped records
- Contra: variable-size 3-byte triples with slot encoding
- CV3: nested pointer pairs
- CV2: hierarchical phrase references
- Super C: unknown (Contra-adjacent but not identical)

**The note encoding is the LANGUAGE. The table format is the
DICTIONARY INDEX. You can read the language but can't find the
right page without the index.**

## What Works and What Doesn't

### Works well:
- **Having a disassembly** (CV1, Contra): instant, zero effort
- **Period table as a starting point** (CV3): narrows the bank,
  then nearby pointer structures become findable
- **Mesen trace as ground truth**: validates any candidate

### Works poorly:
- **Brute-force pointer scanning** without structural constraints:
  produces hundreds of false positives
- **Assuming format compatibility** across games: Super C proved
  that even the same engine can use different table formats
- **Heuristic scoring** of parsed note counts: rewards false
  positives that happen to have parseable byte patterns

### The right tool we haven't used enough:
- **Mesen debugger breakpoints**: set a breakpoint on $4002 (pulse
  period low byte) during music playback. The code that hits the
  breakpoint IS the sound engine. Trace back from there to find
  the table read. This is 30 seconds of work that replaces hours
  of ROM scanning.

## Rules Going Forward

1. **If a disassembly exists: read it.** This solves the problem
   instantly.

2. **If no disassembly: use the Mesen debugger.** Breakpoint on
   APU writes, trace back to the table read.

3. **ROM scanning is a LAST RESORT** for finding the BGM pattern.
   It works when you know the exact format. It fails when the
   format is unknown or has diverged.

4. **The period table helps but doesn't solve the problem.** It
   narrows the bank but the table format is a separate question.

5. **Never assume table format compatibility** even within the
   same engine family. CV1, Contra, CV3, and Super C all use
   Maezawa-family note encoding but DIFFERENT table formats.

6. **Budget: 2 search attempts max.** If exact match and relaxed
   match both fail, switch to the debugger. Don't grind.
