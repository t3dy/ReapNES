# Why NSF Matters: The Universal NES Music Reverse Engineering Tool

## The Goal

The goal is NOT to produce WAV files. WAVs are a byproduct.

The goal is to produce **complete musical scores with synthesizer
parameters** that can be loaded into REAPER and manipulated:

- MIDI note events with correct pitch, timing, and velocity
- Per-frame volume envelopes (CC11 expression)
- Duty cycle / pulse width modulation (CC12 = timbre changes)
- Triangle bass with linear counter timing
- Noise channel drum patterns with period and mode
- REAPER projects with ReapNES_APU.jsfx synth loaded per track
- Loop points marked in the MIDI

This is what the CV1 pipeline already produces. The question is
how to produce it for EVERY NES game, not just games with known
ROM parsers.

## What the NSF Emulator Captures

When the 6502 emulator runs the NSF driver, every APU register
write is captured with frame-level timing:

### Pulse Channels ($4000-$4007)

| Register | Data | Musical Parameter |
|----------|------|-------------------|
| $4000 | duty cycle (2 bits) + volume (4 bits) | **Waveform shape + amplitude** |
| $4001 | sweep (enable, period, negate, shift) | **Pitch slide / portamento** |
| $4002 | period low 8 bits | **Pitch (combined with $4003)** |
| $4003 | period high 3 bits + length counter | **Pitch + note trigger** |

From these 4 registers per frame, we extract:
- **MIDI note number**: period → frequency → MIDI note
- **Velocity / CC11**: volume value (0-15) → MIDI velocity or expression
- **CC12 / program change**: duty cycle (12.5%, 25%, 50%, 75%) → timbre
- **Pitch bend**: frame-to-frame period changes within a note = vibrato
- **Note on/off**: when period changes to a new pitch = new note

### Triangle Channel ($4008-$400B)

| Register | Data | Musical Parameter |
|----------|------|-------------------|
| $4008 | linear counter reload | **Note duration / sustain** |
| $400A | period low 8 bits | **Pitch** |
| $400B | period high 3 bits + length counter | **Pitch + trigger** |

Triangle has no volume control — it's either on or off. The
linear counter determines how long it sounds. This maps to MIDI
note duration directly.

### Noise Channel ($400C-$400F)

| Register | Data | Musical Parameter |
|----------|------|-------------------|
| $400C | volume (4 bits) | **Hit velocity** |
| $400E | period (4 bits) + mode (1 bit) | **Drum type / pitch** |

Noise period + mode determines the drum sound:
- Low period + long mode = snare
- High period + long mode = hi-hat
- Short mode = metallic / pitched noise

These map to MIDI drum notes (GM mapping or custom).

## The Pipeline: NSF → MIDI → REAPER

```
NSF file
  ↓
6502 Emulator (py65)
  ↓ captures APU register writes per frame
Frame-level Register Dump
  ↓ same format as Mesen trace
Note Event Extraction
  ↓ period changes = note on/off
  ↓ volume per frame = CC11 envelope
  ↓ duty cycle changes = CC12 timbre
  ↓ vibrato detection = pitch bend
MIDI File (4-5 tracks)
  ↓ with CC11, CC12, pitch bend, loop markers
REAPER Project (.rpp)
  ↓ with ReapNES_APU.jsfx loaded per channel
  ↓ preset per channel matching the game's sound
Playable Project
  ↓ open in REAPER, hit play, hear NES-accurate audio
  ↓ edit notes, change synth params, remix
```

## Why This Is Better Than Just WAVs

### WAVs are fixed
A WAV is a rendered recording. You can't change the tempo, pitch,
arrangement, or instrumentation. You can't extract the bass line
or mute the lead. It's baked.

### MIDI + JSFX is malleable
With MIDI note data and the ReapNES synth:
- Change tempo without pitch shift
- Transpose the whole song
- Mute/solo individual channels
- See the score in REAPER's piano roll
- Edit individual notes
- Apply different duty cycles or envelopes
- Layer with other instruments
- Use as backing tracks for covers or remixes

### The synth parameters ARE the instrument
The NES APU has a tiny parameter space:
- 4 duty cycles (12.5%, 25%, 50%, 75%)
- 16 volume levels
- ~2048 period values (pitch)
- 16 noise rates × 2 modes

These parameters are fully captured by the NSF emulator. The
ReapNES_APU.jsfx synth recreates them in REAPER. The MIDI CC
values drive the synth to match what the original game produced
frame-by-frame.

## What This Means for Every Game

### Games we already have (CV1, Contra)
Already have MIDI + REAPER projects from the ROM parser. The NSF
approach would produce equivalent output and serves as validation.

### Games we struggled with (Bionic Commando, Super C)
The ROM parser failed because we couldn't decode the byte format.
The NSF player runs the ACTUAL driver code — no format knowledge
needed. It captures the same register data that the ROM parser
would have produced, but without needing to understand the
encoding.

### Games we never tried
Any NES game with an NSF file on Zophar's (thousands of games).
Download NSF → run emulator → extract MIDI + build REAPER project.
No ROM analysis, no driver identification, no format documentation.

## The Complete Extraction Pipeline

For ANY NES game:

1. Download NSF from zophar.net
2. Download M3U playlist (has track names + durations)
3. Run NSF emulator on each song
4. Extract MIDI with CC11/CC12/pitch bend from register dumps
5. Generate REAPER project with ReapNES synth per channel
6. Apply song-specific presets (duty cycle defaults, tempo)

This is the universal version of what we built for CV1. Same
output format, same REAPER integration, same JSFX synth — but
working on every publisher's sound engine automatically.

## Performance and Scaling

- py65 renders ~10-20 seconds of audio per second of wall time
- A typical NES soundtrack (15-20 songs) takes 30-60 minutes
- This is a batch process — run overnight, have everything ready
- Each game produces: MIDI files + REAPER projects + WAV previews
- Total storage: ~1MB MIDI + ~5KB RPP + ~50MB WAV per soundtrack
