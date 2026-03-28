# SYNTHDESIGN.md -- ReapNES Synth Plugin Design

## What Users Expect From a REAPER Synth Plugin

A REAPER synth plugin should behave identically to any VSTi instrument:

1. **Receives MIDI from any source** -- keyboard, MIDI items on timeline, MIDI sends from other tracks
2. **Produces audio output** -- stereo, properly centered at zero, no DC offset
3. **Has a visual interface** -- opens when you click FX on the track, shows controls you can click/drag
4. **Parameters are automatable** -- REAPER can record and play back parameter changes
5. **Responds to standard MIDI** -- note on/off, velocity, CCs, pitch bend, program change
6. **Appears in the Instruments list** -- not buried in Effects
7. **Works without manual configuration** -- load it, play it

## Current ReapNES_APU.jsfx Status

### Working
- Receives MIDI from keyboard and MIDI items
- 4-channel NES APU (Pulse x2, Triangle, Noise)
- Hardware-accurate duty cycles, triangle waveform, LFSR noise
- Oscilloscope display (@gfx)
- 13 sliders for all parameters
- CC1 controls duty cycle in real-time
- "Any Ch -> P1" mode for single-track keyboard play

### Missing (standard synth features)
- No interactive UI controls (just read-only oscilloscope + REAPER's default slider panel)
- No ADSR envelope (NES uses frame-rate envelopes, not ADSR -- but a simplified attack/release would help)
- No pitch bend response
- No preset system via REAPER's preset menu
- No visual feedback showing which notes are active
- No per-channel volume meters in the display
- No waveform selector buttons in the display

## Synth UI Design

### Layout: Oscilloscope + Controls

```
+================================================================+
|  ReapNES APU -- NES 2A03 Synthesizer                           |
|================================================================|
|                                                                |
|  P1 ~~~~~/\/\/\/\/\/\/\~~~~~  [50%] Vol [====|===] 15  [ON]  |
|  P2 ~~~~~\/\/\/\/\/\/\/~~~~~  [25%] Vol [====|===] 15  [ON]  |
|  TRI ~~~~^v^v^v^v^v^v^v~~~~        Vol [fixed    ]     [ON]  |
|  NOI ~~~~||||||||||||||||~~~~  [Long] Vol [====|===] 15 [ON]  |
|  MIX ~~~~waveform~~~~~~~~                                      |
|                                                                |
|----------------------------------------------------------------|
|  MASTER [==========|=====] 0.80     Mode: [Any Ch -> P1]      |
|                                                                |
|  Active: C4 (Pulse 1)   Vel: 96                               |
+================================================================+
```

### Controls (all adjustable via mouse in @gfx)

| Control | Type | Values | Notes |
|---------|------|--------|-------|
| P1 Duty | Clickable cycle | 12.5%, 25%, 50%, 75% | Click to cycle through 4 modes |
| P1 Volume | Drag slider | 0-15 | Horizontal bar |
| P1 Enable | Toggle | On/Off | Click to toggle |
| P2 Duty | Clickable cycle | 12.5%, 25%, 50%, 75% | |
| P2 Volume | Drag slider | 0-15 | |
| P2 Enable | Toggle | On/Off | |
| Tri Enable | Toggle | On/Off | Triangle has no volume control (hardware accurate) |
| Noise Period | Drag slider | 0-15 | |
| Noise Mode | Toggle | Long/Short | |
| Noise Volume | Drag slider | 0-15 | |
| Noise Enable | Toggle | On/Off | |
| Master Gain | Drag slider | 0.0-1.0 | |
| Any Ch -> P1 | Toggle | On/Off | Routes all MIDI channels to Pulse 1 |

### MIDI Implementation

| MIDI Event | Action |
|------------|--------|
| Note On (ch 0) | Pulse 1: set frequency + velocity -> volume |
| Note On (ch 1) | Pulse 2: set frequency + velocity -> volume |
| Note On (ch 2) | Triangle: set frequency |
| Note On (ch 3) | Noise: note -> period index, velocity -> volume |
| Note Off | Release corresponding channel |
| CC 1 (Mod Wheel) | Duty cycle on pulse channels, mode on noise |
| CC 7 (Volume) | Per-channel volume (future) |
| CC 74 (Brightness) | Sweep effect on pulse channels (future) |
| Pitch Bend | Pitch bend +/- 2 semitones (future) |
| Velocity | Maps to NES volume 0-15 |

### What "Any Ch -> P1" Mode Does

When ON: all MIDI channels are remapped to channel 0 (Pulse 1). This means you can play the keyboard on any channel and hear Pulse 1. Useful for single-track experimentation.

When OFF: each MIDI channel routes to its own NES channel. Required for multi-track projects where each track sends on a specific channel.

## Future: Preset-Driven Instrument Plugin

ReapNES_Instrument.jsfx (currently broken due to library imports) is designed to load .reapnes-data envelope files that automate volume, duty cycle, and pitch per-note at 24 Hz frame rate -- matching how NES games actually shaped their sounds.

Once the library import issue is resolved (or the envelope code is inlined), this plugin would:
- Load 4 preset files (one per channel slot)
- Play back extracted NES instrument envelopes automatically
- Make each note sound like a specific NES game instrument
- Support the 54K extracted preset corpus

## Architecture Principles

1. **Self-contained code only** -- no library imports until we solve the JSFX cache problem
2. **ASCII only** -- no unicode anywhere in JSFX files
3. **Sequential slider numbering** -- no gaps
4. **Zero output when silent** -- no DC offset from mixer formulas
5. **`tags:instrument`** -- so it appears in REAPER's instrument list
6. **Standard MIDI behavior** -- velocity, CCs, pitch bend work as expected
7. **Filename: ReapNES_APU.jsfx** -- not ReapNES_Full (cached broken version)
