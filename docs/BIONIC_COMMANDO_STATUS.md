# Bionic Commando: Current Status

## What We Found

### Song Table (VERIFIED)
Bank 0 at $8000: 20-entry master table. Each entry points to a
sub-structure with 3-4 channel pointers.
- 8 entries are BGM tracks (3 real channels + $8600 empty)
- 12 entries are SFX/jingles (1 channel)

### Period Table (FOUND)
Bank 12 at offset $0997: 65 consecutive 16-bit period values
covering MIDI 33-97 (A1 to C#7). NOT a 12-entry Maezawa table —
Capcom precomputes every semitone across 5+ octaves.

Quirk: entries 13-14 are non-monotonic (879 then 906). This
might be intentional (different tuning for certain notes) or
indicates the table has a slightly different structure than
assumed.

### Sound Engine (LOCATED)
Bank 12 has the most APU register writes (STA $40xx,x pattern).
The sound engine code and period table are both in this bank.

### Track List (FROM WEB SOURCES)
20 tracks total, matching our ROM findings:
- 8 BGMs: Intro, Map Select, 5 stage themes, Boss, Staff Roll
- 12 short: jingles, fanfares, game over

### Trace Captures (2 of 20)
- Capture 1: Enemy Base Theme (Stage 1, "Bionic Commando Theme")
- Capture 2: Map/Area Select

### Reference MP3s (COMPLETE)
All 20 tracks from Zophar's NSF rip, extracted to
output/Bionic_Commando/reference_mp3/

## What We Haven't Cracked

### Byte-to-Note Encoding
The song data bytes (0x00-0x7F) don't directly index the period
table. Many values exceed the 65-entry table range. The encoding
likely involves:
- Some bytes = note indices (into the period table)
- Some bytes = commands (volume, duration, loop, instrument)
- The split point between notes and commands is unknown
- Possible bit packing (high bits = command flags, low bits = note)

### Channel Assignment
The non-$8600 channels are the real music channels, but we don't
know which channel is pulse1, pulse2, or triangle. The ordering
may differ per song.

### Timing/Duration Encoding
From the trace, notes are 5-frame ticks with 6-frame multiples.
But we don't know how duration is encoded in the song bytes.
It could be:
- Fixed duration per tick (every byte = one tick)
- Duration bytes interspersed with note bytes
- Run-length encoding

## What We CAN Deliver Right Now

### From Traces (high quality)
- WAV renders of Stage 1 and Map Screen (done)
- Music-only versions with SFX stripped (done)
- Per-channel stems (done)
- MIDI with CC11 volume envelopes (done)

### From Reference MP3s (complete but not our renders)
- All 20 tracks as MP3s from the NSF rip (done)
- These are the "correct" reference audio

### From ROM Analysis (structural only)
- Song table with 8 BGM entries mapped
- Period table located
- Sound engine bank identified

## Next Steps to Crack the Encoding

The fastest path: use the TWO trace captures as Rosetta Stones.

1. The trace gives us frame-exact pitch sequences for each channel
2. The ROM has the byte data that produces those sequences
3. By aligning the timing (trace frames to byte positions in the
   64-byte blocks), we can determine which byte produces which pitch
4. Once we have ~10 byte-to-pitch mappings, the encoding falls

The blocker is that we need to figure out the TIMING first:
how many frames does each byte represent? Is it fixed (1 byte =
1 tick = 6 frames?) or variable?

Alternative: find or request a Capcom NES sound driver disassembly.
Yoshihiro Sakaguchi's driver is used in MANY Capcom NES games
(Mega Man, DuckTales, etc.). An existing RE of ANY Capcom NES
game's sound engine would immediately solve Bionic Commando too.
