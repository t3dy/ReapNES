# NSF to Synth Instrument Plugins

## The Synth: ReapNES_APU.jsfx

The project uses a custom JSFX plugin (`studio/jsfx/ReapNES_APU.jsfx`)
that recreates the NES APU in REAPER. It synthesizes:

- **Pulse waves** with 4 duty cycles (12.5%, 25%, 50%, 75%)
- **Triangle waves** (fixed waveform, no volume control)
- **Noise** (LFSR-based, 16 rates, 2 modes)

### Slider Parameters

| # | Parameter | Range | Default |
|---|-----------|-------|---------|
| 1 | P1 Duty | 0-3 | 2 (50%) |
| 2 | P1 Volume | 0-15 | 15 |
| 3 | P1 Enable | 0-1 | 1 |
| 4 | P2 Duty | 0-3 | 1 (25%) |
| 5 | P2 Volume | 0-15 | 15 |
| 6 | P2 Enable | 0-1 | 1 |
| 7 | Tri Enable | 0-1 | 1 |
| 8 | Noise Period | 0-15 | 0 |
| 9 | Noise Mode | 0-1 | 0 |
| 10 | Noise Vol | 0-15 | 15 |
| 11 | Noise Enable | 0-1 | 1 |
| 12 | Master Gain | 0-1 | 0.8 |
| 13 | Channel Mode | 0-4 | per-track |

### Channel Mode (Slider 13)

Each track in the REAPER project runs one instance of ReapNES_APU
with Channel Mode set to isolate one NES channel:

- **0** = Pulse 1 Only (track "NES - Pulse 1")
- **1** = Pulse 2 Only (track "NES - Pulse 2")
- **2** = Triangle Only (track "NES - Triangle")
- **3** = Noise Only (track "NES - Noise / Drums")
- **4** = Full APU (all channels, used for keyboard play)

## How NSF Data Drives the Synth

The MIDI CC events from the NSF extraction control the synth
in real time during playback:

### CC11 (Expression) → Volume Envelope

Every frame's APU volume value (0-15) is captured as CC11.
This reproduces the exact attack-decay-sustain-release shape
that the game's sound driver produces:

```
Frame 0: vol=15 → CC11=120
Frame 1: vol=12 → CC11=96
Frame 2: vol=9  → CC11=72
Frame 3: vol=6  → CC11=48
Frame 4: vol=3  → CC11=24
(note off)
```

The ReapNES synth uses CC11 to modulate its output amplitude.
This is what gives NES music its characteristic sharp attacks
and quick decays.

### CC12 → Duty Cycle (Pulse Width)

The pulse channels can switch between 4 waveforms mid-song.
Each duty cycle change is captured as CC12:

```
CC12=16  → 12.5% duty (thin, nasal)
CC12=32  → 25% duty (classic NES square)
CC12=64  → 50% duty (hollow, flute-like)
CC12=96  → 75% duty (same as 25%, inverted)
```

Many NES songs change duty cycle between song sections or even
between notes for timbral variety. The CC12 automation preserves
this.

### Note Events → Pitch

Period register values are converted to MIDI note numbers:

```
NES period → frequency: freq = 1789773 / (16 * (period + 1))
Frequency → MIDI: midi = 69 + 12 * log2(freq / 440)
```

Vibrato (frame-to-frame period modulation) appears as rapid
small pitch changes. In the MIDI, these are separate note events.
Future improvement: detect vibrato and use MIDI pitch bend instead.

### Noise Events → Drum Mapping

Noise channel hits are mapped to GM drum notes:
- Period 0-4 → Note 42 (Closed Hi-Hat)
- Period 5-8 → Note 38 (Snare)
- Period 9-15 → Note 36 (Kick)

The noise mode (long vs short LFSR) affects timbre but isn't
directly mapped to MIDI — the ReapNES synth handles this
through its own noise synthesis.

## The Complete Signal Chain

```
NSF file
  → 6502 emulator runs sound driver
  → APU register captures ($4000-$4017 per frame)
  → MIDI converter extracts notes + CC11 + CC12
  → REAPER project loads ReapNES_APU.jsfx per channel
  → MIDI playback drives the synth:
      Note On/Off → pitch
      CC11 → volume envelope (per-frame)
      CC12 → duty cycle (timbre)
  → ReapNES synthesizes NES-accurate audio
  → Output: editable, remixable, accurate NES music
```

## Limitations and Future Work

### Current
- Vibrato appears as rapid note changes instead of pitch bend
- No DPCM sample playback (affects some drum sounds)
- Triangle has no volume automation (hardware limitation)
- Loop detection not implemented (tracks render for fixed duration)

### Planned
- Detect vibrato and convert to MIDI pitch bend
- Add DPCM sample support for Contra-style drums
- Detect loop points from the NSF driver's jump commands
- Per-game presets for duty cycle defaults and tempo
