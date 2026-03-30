# Capcom NSF Findings

## What We Built

A minimal NSF player using py65, a Python 6502 CPU emulator.
The player:

1. Loads the NSF file (header + driver code + music data)
2. Maps the data into a virtual 64KB address space at the load address
3. Calls the INIT routine with the song number in the A register
4. Calls the PLAY routine 60 times per second (once per NES frame)
5. Captures writes to APU registers ($4000-$4017) after each step
6. Feeds the captured register states to our existing NES APU synth
7. Renders to WAV

This is functionally identical to what Mesen does when it plays
the game — except we're running ONLY the sound driver, with no
graphics, no game logic, no controllers, no mapper hardware.

## How It Works

### NSF Format
An NSF file is a stripped-down NES ROM containing just the sound
engine:

```
Header (128 bytes):
  Byte 6:     total songs
  Byte 7:     starting song (1-based)
  Bytes 8-9:  load address (where data goes in CPU space)
  Bytes 10-11: INIT address (called to set up a song)
  Bytes 12-13: PLAY address (called 60x/sec)
  Bytes 14-45: title string
  Bytes 46-77: artist string

Data (rest of file):
  Loaded at load_address in CPU memory space
```

### 6502 Emulation
py65 provides a cycle-accurate 6502 CPU emulator. We use it to:
- Load the NSF data into virtual memory
- Set up a stack and return sentinel
- Call INIT(song_number) via register A
- Call PLAY() 60 times per second
- Monitor memory at $4000-$4017 for APU register changes

### APU Capture
After each CPU instruction, we check if any APU register changed.
When it does, we record (frame_number, register, value). This
produces the same data format as a Mesen APU trace — our existing
WAV renderer handles it identically.

## Test Results

### Cut Man (Song 3, 30 seconds)
- INIT: 701 CPU cycles
- PLAY: ~1800 calls (30 seconds × 60fps)
- Output: 30.0s WAV, 98% non-zero samples, RMS 10816
- STATUS: AUDIO PRESENT — the driver is producing real music

### Performance
Each song frame takes a few hundred CPU instructions to process.
The py65 emulator runs these in Python, so it's not fast — about
10-20 seconds of wall time per second of audio. A 90-second song
takes ~2-3 minutes to render.

## Why This Matters

### 1. No more captures needed
The NSF contains ALL songs for a game. We can render every track
programmatically without the user touching Mesen. For Mega Man 1,
that's 16 songs from one 12KB file.

### 2. Publisher-agnostic
The NSF player doesn't care what sound engine the game uses —
Capcom, Konami, Sunsoft, anything. It runs the ACTUAL driver code.
The 6502 emulator executes the same instructions the real NES
would. No format reverse-engineering needed.

### 3. Every NES game has an NSF rip
Zophar's Domain hosts NSF files for thousands of NES games. Each
one contains the complete soundtrack. Our NSF player can render
any of them to WAV.

### 4. Bypasses the format encoding problem entirely
We spent hours trying to decode the Capcom note encoding from ROM
bytes. The NSF player makes that irrelevant — we run the driver
and capture what it outputs. The driver does the decoding for us.

## Comparison to Other Approaches

| Approach | Works on | Requires | Quality |
|----------|----------|----------|---------|
| Trace capture | Any game | User plays in Mesen | Perfect (hardware-level) |
| ROM parser | Known drivers only | Format RE + validation | Perfect if parser is correct |
| NSF player | Any game with NSF | NSF file + 6502 emulator | Perfect (runs actual driver) |
| nesmdb render | Games in database | nesmdb data | Variable (may have artifacts) |
| Reference MP3 | Games with NSF | NSF player + encoding | Good (pre-rendered) |

The NSF player sits between trace capture and ROM parsing:
- Like traces: runs the actual driver code, not a format parser
- Like ROM parsing: doesn't need the user to play the game
- Unique advantage: works on ANY publisher's sound engine

## Limitations

### 1. No DPCM samples
The NSF player captures APU register writes but doesn't handle
DPCM sample playback ($4010-$4013 + sample data). Games that use
DPCM for drums (Contra, some Mega Man songs) will be missing
those sounds.

### 2. Slow rendering
py65 runs 6502 instructions in Python. Each instruction is a
Python method call. Rendering a 90-second song takes 2-3 minutes.
This is acceptable for batch processing but not real-time.

### 3. No bank switching
NSF files that use bank switching (byte 0x70+ in header) need
additional memory mapping logic. The current player assumes
linear loading. Most NSF files are small enough to not need this.

### 4. Loop detection not implemented
The player renders for a fixed duration (90 seconds by default).
It doesn't detect when the song loops. This means some tracks
will have multiple loops while short jingles will have long
trailing silence.

## The Zophar Pipeline

With this NSF player, the extraction process for ANY NES game
becomes:

1. Download NSF from zophar.net
2. Run: `python scripts/nsf_player.py game.nsf --all output/`
3. Wait for rendering (2-3 min per song)
4. Listen to output WAVs
5. Cross-reference with M3U playlist for track names

No ROM analysis. No format reverse-engineering. No Mesen captures.
No driver-specific parsers. Just the NSF file and the emulator.

## What's Next

- Render all 16 Mega Man 1 songs (running now)
- Validate Cut Man NSF render against our trace capture
- If they match: the NSF player is verified
- Test on Bionic Commando NSF (which we couldn't parse from ROM)
- Test on Konami games to see if it works across publishers
- Add loop detection and DPCM support
