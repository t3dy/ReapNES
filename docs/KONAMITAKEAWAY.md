---
layout: default
title: "Konami NES Music Coding: What We Know"
---

# Konami NES Music Coding: What We Know

Takeaways from reverse engineering Castlevania 1 (1986) and
Contra (1988), both using the Konami pre-VRC sound driver
attributed to Kinuyo Yamashita and Hidenori Maezawa.

## What's Shared Across Games

### The Period Table Is Universal

Both games use the same 12-entry period table starting at 1710:
```
C:1710  C#:1614  D:1524  D#:1438  E:1358  F:1281
F#:1209  G:1142  G#:1078  A:1017  A#:960  B:906
```

This is standard NES NTSC tuning derived from the CPU clock
(1.789773 MHz). Any Konami game from this era likely uses the
same table. Finding it in a ROM is the first step in identifying
the driver.

### The Command Set Is Stable

Both games share these commands:
- **$00-$BF**: Note (high nibble = pitch 0-11, low = duration)
- **$C0-$CF**: Rest with duration
- **$D0-$DF**: Instrument setup (DX) with tempo in low nibble
- **$E0-$E4**: Set octave (0 = highest, 4 = lowest)
- **$E8**: Flag set (flatten note / envelope enable)
- **$EB**: Vibrato setup (2 parameter bytes)
- **$EC**: Pitch adjustment (1 parameter byte)
- **$FD**: Subroutine call (2-byte pointer)
- **$FE**: Repeat (count + 2-byte pointer; $FF count = infinite)
- **$FF**: Return/end

### Volume Handling Is Engine-Level

The `resume_decrescendo` routine, `set_pulse_config`, and
`check_decrescendo_end_pause` are shared engine code. Behaviors
like:
- Volume bouncing at 1 during resume phase
- `UNKNOWN_SOUND_01` subtraction
- `DECRESCENDO_END_PAUSE = (mul * duration) >> 4`

These are the same across games because they're in the engine,
not in the per-game data.

## What Changes Per Game

### DX Byte Count

The DX instrument command reads different numbers of extra bytes:
- **CV1**: 2 bytes (config + fade parameter)
- **Contra pulse**: 3 bytes (config + vol_env + decrescendo_mul)
- **Contra triangle**: 1 byte (linear counter config)

The byte count is determined by the channel type check in the
engine code. But the specific logic for WHAT those bytes mean
differs.

### Volume Envelope Model

- **CV1**: Parametric. Two parameters (fade_start, fade_step)
  control a two-phase decay. Simple, predictable.
- **Contra**: Lookup table. 54 pre-built envelope patterns in
  `pulse_volume_ptr_tbl`, selected by the vol_env byte from DX.
  Complex, expressive.

Both systems use the same `resume_decrescendo` for tail fade-out.
The difference is in the initial envelope shape.

### Percussion Format

- **CV1**: Inline drum triggers (E9 = snare, EA = hihat) within
  pulse/triangle channels. Drums share timing with the melodic
  channel they're embedded in.
- **Contra**: Separate noise/DMC channel (slot 3) with its own
  command stream. High nibble selects from `percussion_tbl`,
  which maps to DMC sample codes. Compound hits play both a DMC
  sample and a noise channel bass drum.

### ROM Layout

- **CV1**: Mapper 0, linear addressing. All music in one 32K PRG
  block. CPU addresses = ROM offsets + iNES header.
- **Contra**: Mapper 2 (UNROM), bank-switched. Music in bank 1
  (16K at $8000-$BFFF). Address resolution requires knowing the
  bank number.

### Pitch Adjustment

- **CV1**: No EC commands found. All notes use the period table
  directly.
- **Contra**: EC pitch adjustment shifts the period table lookup
  by N semitones. Jungle and Base tracks use EC=1 (+1 semitone).

## Mysteries That Remain

### Per-Game Envelope Table Mapping

Contra's envelope table has 54 entries organized by "level" (8 per
level, 6 for level 7). But tracks freely reference entries from
other levels (Boss uses level 2 entry 14, Stage Clear uses level
7 entry 53). The "level" grouping is the disassembler's naming
convention, not a runtime constraint. What determines which
envelope a track uses is simply what vol_env byte the DX command
contains in the music data.

We don't know if there's a higher-level composition tool that
assigned these or if they were hand-coded.

### Triangle Linear Counter Precision

Our formula `sounding_frames = (reload + 3) // 4` is approximate.
The real APU uses quarter-frame clocking (240 Hz) that doesn't
divide evenly into 60 fps frames. The Mesen trace for CV1 shows
195 triangle sounding mismatches. These are probably 1-frame
timing errors where the linear counter expires on a different
frame boundary than our approximation predicts. The fix requires
modeling the APU's frame counter / quarter-frame sequencer cycle
precisely.

### UNKNOWN_SOUND_01

The engine subtracts this per-channel variable from pulse volume
before writing to the APU register. We don't fully understand
when and how it's set. CV1 appears to have it at 0 (no effect).
Contra may use non-zero values. The variable name itself (from
the disassembly) suggests the original reverse engineer didn't
know its purpose either.

### Duty Cycle Modulation

Contra's trace shows 2 mid-note duty cycle changes in Jungle
(frames 1979 and 2075, duty 3 to 0). These are either part of
the instrument setup or driven by a separate duty modulation
system. We don't model mid-note duty changes.

### What Happens at the Hardware-Software Boundary

The engine writes decoded values to APU registers once per frame
(during NMI). But the APU processes audio continuously at CPU
clock speed. Writes in the middle of a waveform cycle can cause
pops, clicks, and phase artifacts. Our model applies changes at
frame boundaries, missing these transient effects.

## Practical Advice for ROM Hackers

### Starting a New Konami Game

1. **Find the period table** — scan for the 2-byte sequence
   $AE,$06 (period 1710 as little-endian). If found, you have
   a Maezawa family driver.

2. **Check the mapper** — read ROM byte 6-7 for the mapper
   number. This determines address resolution.

3. **Find the disassembly** — search GitHub for annotated source.
   10 minutes reading saves hours guessing. The disassembly tells
   you DX byte count, percussion format, and volume model.

4. **Capture a trace first** — before writing any parser code,
   capture 60 seconds of Mesen APU data. This gives you ground
   truth to test against immediately.

5. **Don't assume** — the fact that CV1 and Contra share a
   command set does NOT mean they share command semantics.
   Check every parameter independently. Particularly:
   - How many bytes does DX read?
   - Does the game use EC pitch adjustment?
   - Is percussion inline or separate channel?
   - Are volume envelopes parametric or lookup table?

### The Sound Engine Parts List

Any Konami Maezawa-family game will have these components
somewhere in ROM:

| Component | How to Find |
|-----------|-------------|
| Period table | Scan for $AE,$06 (period 1710 LE) |
| Pointer table | Referenced from sound init routine |
| Note period lookup | Near `note_period_tbl` label |
| Volume envelope table | Near start of sound bank |
| Percussion table | After volume envelope handling code |
| DX instrument handler | Follows the $D0 command dispatch |
| EC pitch adjust | Follows the $E0 octave handler |
| FE repeat handler | In the $F0 command dispatch |

### What We'd Do Differently

If starting over:
1. Capture trace BEFORE building parser (not after)
2. Extract ALL commands as raw bytes first, classify later
3. Build the manifest FIRST with status fields for each command
4. Test ONE track against trace, fix, repeat
5. Never assume a parameter is the same as another game's
