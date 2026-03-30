# Huge Breakthrough: March 29 Day Two

## What Happened

We were stuck on Bionic Commando. We had:
- The song table (8 BGM tracks with channel pointers)
- The period table (65 entries in bank 12)
- Two trace captures (Stage 1 + Map Screen)
- All 20 reference MP3s from the NSF rip

But we couldn't read the music data from ROM because we didn't
know how the bytes encode notes. The byte values didn't directly
index the period table. Interval matching against the trace didn't
correlate. We were dead in the water for ROM-based extraction.

## The Breakthrough

You asked me to research whether existing reverse engineering
documentation was available for the Capcom sound driver. I searched
and found THREE critical resources:

1. **Capcom "6C80" Sound Engine Documentation** on romhacking.net —
   a full specification of the music data format used in Mega Man 3
   and later Capcom NES games.

2. **Capcom Music Format** on the Super Famicom Development Wiki —
   a complete byte-level specification with every command documented,
   including the note encoding formula.

3. **Capcom Sound Engine 1 Format** on romhacking.net — documentation
   of the EARLIER engine used in Commando and Trojan.

The Super Famicom wiki page gave us the complete encoding:

```
Notes ($20-$FF):
  Upper 3 bits = duration class (1=64th through 7=whole note)
  Lower 5 bits = pitch (0=rest, 1-31=semitone index)

Commands ($00-$1F):
  $00 = triplet toggle
  $05 = tempo (2 bytes)
  $07 = volume (1 byte)
  $08 = instrument (1 byte)
  $09 = octave correction (1 byte)
  $0A = global transpose (1 byte)
  $16 = unconditional jump (2 bytes = loop address)
  $17 = end of track
  ... and 20+ more documented commands
```

## Why This Is Huge

### 1. It's not just Bionic Commando — it's ALL of Capcom

The same sound driver (with minor versions) was used in:
- Mega Man 1-6
- DuckTales 1-2
- Chip 'n Dale Rescue Rangers
- Bionic Commando
- Strider
- Little Nemo
- Gargoyle's Quest 2
- ~35 Capcom NES games total

One format specification unlocks an entire publisher's library.
This is the equivalent of what the Contra disassembly did for
Konami, but covering 3x as many games.

### 2. The encoding is elegant and well-documented

Unlike Konami's Maezawa driver (which we had to reverse-engineer
from the Contra disassembly), the Capcom format has been
documented by the ROM hacking community. The byte encoding is
clean: one byte = one note (pitch + duration packed into 8 bits).
Commands are $00-$1F with known parameter lengths.

### 3. We can verify it immediately

We have two trace captures with known pitches. We can decode the
ROM data using the documented format and compare the result to
the trace. If the pitches match, the format is confirmed and we
can extract all 8 BGM tracks without any more captures.

### 4. It validates the adaptive skill system

The breakthrough came from RESEARCH, not from more ROM scanning
or more traces. The existing documentation was sitting on
romhacking.net the entire time. Our earlier approach (brute-force
byte correlation, interval matching, period table indexing) was
working at the wrong level — we were trying to re-derive something
that was already documented.

This proves the principle we wrote into the skills: **check for
existing disassemblies/documentation BEFORE attempting to crack
a format from scratch.**

## What's Left

### Confirmed
- Note encoding: upper 3 bits = duration, lower 5 bits = pitch
- Command bytes: $00-$1F with documented parameter lengths
- Song table: 20 entries at $8000, 8 are BGMs
- Period table: 65 entries at bank 12 offset $0997

### Needs testing
- Does Bionic Commando use the "6C80" engine or the older one?
  (1988 release date falls between Engine 1 and 6C80)
- What octave correction value does each song start with?
- Do the decoded pitches match our trace captures?
- Are the command byte meanings the same or slightly different?

### Needs building
- A Capcom parser (equivalent to our Konami parser.py)
- Render all 8 BGMs to WAV and compare to reference MP3s
- If successful: extend to other Capcom games (Mega Man, DuckTales)

## The Lesson

The ROM hacking community has already done enormous amounts of
reverse engineering work on NES sound drivers. Before spending
hours on byte-level ROM analysis, ALWAYS search for existing
documentation. The searches that found this:

- "Capcom NES sound driver disassembly"
- "Capcom 6C80 sound engine format"
- romhacking.net documents section

Three web searches = the complete format specification. Three
hours of ROM scanning with diminishing returns = nothing.

**Research beats brute force. Every time.**
