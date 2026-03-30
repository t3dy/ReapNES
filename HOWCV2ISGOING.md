# How CV2 Is Going

Reflections on the third game decode, written mid-session.

---

## What Got Easier

### Trace-first is now automatic

We didn't even think about it. You captured a trace, I analyzed it.
No ROM scanning first, no hypothesis-building, no guessing at the
command format. The trace immediately told us: 3 active melodic
channels, all 5 APU channels used, 449 DMC events, period values
matching the Maezawa table, notes at 10-frame intervals, max volume
6. That's more actionable information than hours of ROM scanning
would produce.

For CV1, we built the parser FIRST and then captured a trace to fix
it. For Contra, we had a trace but it came mid-session. For CV2,
the trace came FIRST and everything after was faster because of it.
The methodology is now internalized.

### Period table scan took minutes, not sessions

CV1's period table was found by reading a disassembly. Contra's was
found by reference to CV1. CV2's was found by a 5-line Python script
that searched for the known byte sequence. Found it in one shot at
ROM 0x01C1D. The fact that it's the same 12 base frequencies meant
we could search for a known signature. For the first game, we didn't
know what to search for. Now we do.

### Pointer table discovery was same session as period table

For CV1, the pointer table came from reading the disassembly (took a
full session). For Contra, it came from an annotated source. For CV2,
we found it by examining bytes near the music data — the pointer
structure was visible in the hex dump because we now know what
pointer tables look like. 16-bit LE values in the $8000-$8FFF range,
clustered together. Pattern recognition from 2 prior games.

### The manifest was written DURING investigation, not after

For CV1 and Contra, manifests were written retroactively to document
what we'd already figured out. For CV2, the manifest was written as
we discovered each fact, with explicit `verified` and `hypothesis`
labels. This is the workflow we designed working correctly.

### Prototype parser in under an hour

The cv2_parser.py was written, run, and producing output within one
session. It parses 30 phrases, follows phrase chains, decodes notes,
and outputs MIDI numbers that match the trace. Not perfect, but
functional. For CV1, the parser took 5-6 prompts across 2 sessions.
For Contra, 3 prompts. For CV2, one concentrated push — and on a
DIFFERENT driver, not a Maezawa variant.

### The shared event types work across drivers

NoteEvent, RestEvent, EndMarker, RepeatMarker, ChannelData, ParsedSong
all import cleanly from the CV1 parser. The frame IR and MIDI export
pipeline don't need to know this is a different driver. The
architecture worked exactly as designed — shared types, pluggable
parser. FLEXIBLE_PARSER_ARCHITECTURE.md Phase 1 is validated.

### Unknown commands don't crash the parser

The UnknownCommand event type logs what we don't understand without
stopping the parse. This is FLEXIBILITYGOALS Principle 5 in action.
The parser produced useful output on its first run despite not
understanding FB, 0x80+ modified notes, or song-level data. Partial
output is more valuable than a crash.

### The "dead end" label was wrong — and we caught it

MOVINGONTOCV2.md said CV2 was a dead end. GAME_MATRIX.md said
BLOCKED. HANDOVER.md said different driver. All of these were
based on a ROM scan that found no Maezawa command signatures. But
the trace immediately showed shared period values, shared FF/FE
commands, and recognizable note encoding. One trace capture
overturned months of assumptions.

This is the biggest win from FLEXIBILITYGOALS: we tried it before
ruling it out, and the trace — not our assumptions — determined
what was possible.

---

## What's Still Hard

### The hierarchical phrase system is confusing

Maezawa stores music as flat byte streams — one channel, start to
end. CV2 stores music as a hierarchy: songs point to phrase chains
that point to short motifs that chain to each other via Fx commands.
Reconstructing the actual melody requires traversing multiple levels
of indirection.

The Bloody Tears bass line (C C# D D#) should be 7 simple bytes.
Instead, it's scattered across phrases 20, 6, 5, 19, 2, and 8, each
contributing 2-4 notes and chaining to the next. The parser follows
chains, but we can't yet assemble the FULL bass line in playback
order because we don't know which phrase is the ENTRY POINT for
Bloody Tears channel 1.

### We don't know the song-to-phrase mapping

The song table at ROM 0x00CE0 contains 17 song pointers. Each
points to data that uses FB commands and bytes in the 0x20-0x3F
range. Are those bytes phrase indices? Channel selectors? Something
else entirely? We can decode individual phrases but we can't yet
say "song 2 = Bloody Tears, channels are phrases [X, Y, Z]."

This is the gap between "we can read the notes" and "we can play
the song."

### Duration encoding is still a hypothesis

We assumed bits 6-5 encode a duration class (0-3) with a fixed
multiplier. The trace shows 10-frame notes. But the duration classes
might not be simple multipliers — they could index a duration table,
or the base tempo might change per song/phrase, or the 0x80 flag
might mean "hold" rather than "double." Without a disassembly, we're
guessing at duration semantics.

### No disassembly exists

CV1 had Sliver X's documentation. Contra had a full annotated
disassembly. CV2 has nothing. Every command meaning is inferred from
the trace and ROM patterns. This is workable for notes (the period
table is definitive) but much harder for commands (FB, phrase chains,
duration encoding, envelope system). A disassembly would collapse
multiple sessions of hypothesis testing into one reading session.

### The envelope model is opaque

The trace shows max volume 6, 3-frame attack, instant decay to 1,
sustain at 1. This is simpler than either CV1's parametric model or
Contra's lookup tables. But we don't know WHY max volume is 6 (is
it a cap? an UNKNOWN_SOUND_01 subtraction? a different register
format?). And we don't know if different instruments use different
envelopes. The bass line has one envelope shape — the melody might
have another.

### MMC1 bank switching adds complexity

CV2 uses mapper 1 (MMC1), which has more complex bank switching than
mapper 2 (UNROM). The sound data appears to be in bank 0, but we
haven't verified whether music data spans multiple banks or whether
the driver switches banks mid-song. If it does, our simple
`cv2_cpu_to_rom(addr, bank=0)` will break for songs that reference
data in other banks.

---

## The Score So Far

| Metric | CV1 (Game 1) | Contra (Game 2) | CV2 (Game 3) |
|--------|-------------|-----------------|-------------|
| Sessions to first parse | 2-3 | 1-2 | <1 |
| Trace timing | After parser | Mid-session | Before everything |
| Period table discovery | From disassembly | Reference to CV1 | 5-line script |
| Pointer table | From disassembly | From disassembly | Hex pattern recognition |
| Disassembly available | Yes | Yes | No |
| Driver family | Maezawa | Maezawa | Fujio (new) |
| Shared infrastructure | None existed | Some reuse | Full reuse of types + pipeline |
| Unknown command handling | Crash | Crash | Log and continue |
| Manifest written | Retroactively | Retroactively | During investigation |

### What the score shows:

**The tooling and methodology compound.** Each game is faster than
the last even when the driver is different. The third game took less
than one session to get a working parser — on a completely unknown
driver with no disassembly.

**The missing piece is song structure.** We can decode notes and
phrases. We can't yet assemble them into playable songs. This is the
CV2-specific challenge that the Maezawa games didn't have (flat
streams are trivially playable). Solving phrase assembly would be
the breakthrough that makes CV2 fully extractable.

---

## What to Do Next

1. **Crack the song-level data format.** The bytes at the song table
   targets (FB commands, 0x20-0x3F bytes, FE repeats) encode how
   phrases are sequenced per channel. Understanding this is THE
   remaining puzzle.

2. **Build a trace-to-phrase matcher.** We have the trace (exact
   pitches per frame) and we have the phrase library (decoded notes).
   A correlation tool could match trace note sequences against phrase
   note sequences and tell us which phrases play when — essentially
   reverse-engineering the song structure from the output.

3. **Search for a CV2 disassembly.** Even partial notes on the sound
   driver would accelerate everything. The NESdev community, romhacking
   forums, and GitHub are the places to look.

4. **Try the parser on other CV2 tracks.** Capture traces of tracks
   01 (Silence of the Daylight) and 03 (Monster Dance). Different
   songs will exercise different phrases and reveal whether our note
   encoding hypothesis holds across the soundtrack.
