# Wheels Not To Reinvent

Detailed technical study of three existing projects whose work we should build on
rather than duplicating. Each section covers what they do, how they do it at the
byte level, what we can reuse, and what gaps remain for us to fill.

---

## 1. CAP2MID — Capcom NES ROM to MIDI Converter

**Repo:** https://github.com/turboboy215/CAP2MID
**Author:** Will Trowbridge (turboboy215)
**Language:** C (single file, 2720 lines)
**License:** Not specified

### What It Does

Reads Capcom NES ROM files directly and extracts music sequence data to MIDI.
Supports three distinct Capcom driver versions spanning early NES (pre-1989)
through late NES (1990+), as well as SNES SPC and GB/GBC ROMs.

### How It Finds Music Data

Uses **magic byte pattern scanning** to locate the sound driver in a user-specified
ROM bank. The tool searches for known 6502 instruction sequences from Capcom's
sound driver code:

| Signature | Platform | Driver Version | Byte Pattern |
|-----------|----------|---------------|--------------|
| MagicBytesANES | NES | 1st (pre-1989) | `84 29 0A AA BD` |
| MagicBytesBNES | NES | 2nd (~1989) | `C9 FF D0 0B A9 01 85` |
| MagicBytesCNES | NES | 3rd (1990+) | `90 06 38 ED` |

After finding the magic bytes, it reads a 16-bit pointer at a known offset relative
to the match — this gives the **song table** address. The song table is a list of
16-bit pointers, each referencing a song header.

### Song Header Format (Driver v3, the most common)

```
Byte 0:     Flag (0x00 = music, nonzero = SFX)
Bytes 1-2:  Channel 1 pointer (big-endian)
Bytes 3-4:  Channel 2 pointer
Bytes 5-6:  Channel 3 pointer
Bytes 7-8:  Channel 4 pointer
```

### Command Byte Format (Driver v3)

Capcom packs duration AND pitch into a single byte for note commands:

**Control commands (0x00-0x1F):**

| Byte | Args | Meaning |
|------|------|---------|
| 0x00 | none | Toggle triplet mode |
| 0x01 | none | Toggle tie/connect |
| 0x02 | none | Dotted note (1.5x length) |
| 0x03 | none | Toggle +24 semitone shift |
| 0x05 | 2 bytes | Set tempo (value / 3.45 = BPM) |
| 0x07 | 1 byte | Set volume (0x00-0x0F) |
| 0x08 | 1 byte | Set vibrato / instrument select |
| 0x09 | 1 byte | Set octave (0-7) |
| 0x0A | 1 byte | Global transpose |
| 0x0B | 1 byte | Channel transpose |
| 0x0E-0x11 | count + addr | Repeat (4 nesting levels) |
| 0x16 | 2 bytes | Loop point (infinite loop) |
| 0x17 | none | End of channel |
| 0x18 | 1 byte | Set duty cycle |
| 0x19 | 1 byte | Set envelope |

**Note commands (0x20-0xFF):**

High 3 bits = duration, low 5 bits = pitch (0 = rest, 1-31 = note):

| Range | Duration |
|-------|----------|
| 0x20-0x3F | 64th note |
| 0x40-0x5F | 32nd note |
| 0x60-0x7F | 16th note |
| 0x80-0x9F | 8th note |
| 0xA0-0xBF | Quarter note |
| 0xC0-0xDF | Half note |
| 0xE0-0xFF | Whole note |

MIDI note = (byte - range_base) + 23 + (octave * 12) + transpose

### Bank Loading (NES)

```
fseek(rom, ((bank-1) * 0x2000) + 0x10, SEEK_SET)  // skip iNES header
```

Each NES bank = 8KB. Reads 3 consecutive banks (24KB). CPU address base = $8000.
Pointers in sequence data are absolute NES CPU addresses; converted to ROM offsets
by subtracting $8000.

**The user must specify which bank contains the music.** No auto-detection.

### What It Extracts

- Notes with pitch and duration
- Tempo changes
- Volume levels (but mapped to MIDI velocity, not envelope curves)
- Instrument numbers (written as MIDI Program Change)
- Repeat/loop structure

### What It Does NOT Extract

- Volume envelope curves (only static volume level)
- Duty cycle data (parsed but NOT written to MIDI)
- Envelope data (parsed but NOT written to MIDI)
- DPCM/sample data
- Gate time / note articulation
- Loop points are treated as end-of-track (not marked)

### What We Should Reuse

1. **The Capcom NES command byte format** — This is fully reverse-engineered.
   We do not need to crack Capcom's driver ourselves. Port the v3 format parsing
   to Python and ADD the missing parts (duty cycle CC output, envelope extraction).

2. **Magic byte scanning approach** — Find known instruction patterns to locate
   the song table. Apply the same technique to Konami's driver.

3. **Bank-to-CPU-address mapping** — The iNES bank offset calculation is reusable
   for any NES ROM parser.

4. **Song table walking** — Array of 16-bit pointers terminated by sentinel value.
   Common pattern across NES drivers.

### What We Add Beyond CAP2MID

- Duty cycle output as MIDI CC (command 0x18 is parsed but discarded)
- Envelope data extraction (command 0x19 is parsed but discarded)
- Volume envelope curves (not just static levels)
- REAPER project generation from the extracted data
- Confidence scoring and provenance tracking
- Python implementation (portable, extensible)

---

## 2. FamiStudio — NSF Import via APU Emulation

**Repo:** https://github.com/BleuBleu/FamiStudio
**Author:** BleuBleu
**Language:** C# + C++ (NotSoFatso emulator core)
**License:** MIT

### What It Does

FamiStudio is a full NES music editor. Its NSF import feature plays an NSF file
through a real 6502 CPU + APU emulator and captures the hardware state at 60fps,
recording it into the tracker format.

### Architecture (Three Layers)

1. **NotSoFatso** (C++ native) — Modified NSF player with full 6502 CPU emulator.
   Actually RUNS the NSF code and exposes internal APU state.
2. **NotSoFatso.cs** (C# P/Invoke) — Marshals calls to native library. Defines
   33 state type constants.
3. **NsfFile.cs** (C# import logic, ~1610 lines) — Converts per-frame APU state
   into FamiStudio's musical data model.

### How APU State Is Captured

**State polling, not write logging:**

1. `NsfOpen()` loads NSF into the 6502 emulator at 44100Hz sample rate
2. `NsfSetTrack()` calls the NSF INIT routine via 6502 emulation
3. For each frame: `NsfRunFrame()` executes the NSF PLAY routine
4. During execution, every write to $4000-$401F updates internal wave structs
5. **After** the frame, `NsfGetState(channel, stateType)` polls the final state

The critical insight: NotSoFatso IS the hardware. It doesn't sniff register
writes — the NSF code writes directly to the emulated APU registers.

### Note Detection (`UpdateChannel()`)

For each channel, each frame:

1. Read `period`, `volume`, `duty` from NotSoFatso
2. Look up closest matching note from frequency table (`GetBestMatchingNote()`)
3. Detect note triggers: volume 0->nonzero or period change = new note
4. Detect note stops: volume -> 0
5. Only emit data when state changes from previous frame (differential encoding)

### Instrument Extraction

FamiStudio DOES create structured instruments, but limited:

- **Duty cycle instruments** — One per unique duty value ("Duty 0", "Duty 1", etc.)
  with a 1-sample DutyCycle envelope
- **FDS instruments** — Full 64-sample wavetable + 32-sample modulation table
- **VRC7 instruments** — Built-in patch numbers or custom 8-register patches
- **N163 instruments** — Wave data + position + size from N163 RAM

**But NO volume envelope extraction.** All volume/pitch changes are stored as
per-frame effect commands, not as instrument envelope definitions. Reconstructing
envelopes is left as a manual reverse-engineering task.

### What We Should Reuse

1. **NotSoFatso as our APU emulator** — It's a complete 6502+APU emulator that
   runs real NSF code. The `GetState()` API gives clean per-frame channel state.
   This IS our dynamic analysis pipeline (Pipeline B).

2. **Note frequency lookup tables** — `NesApu.cs` has precomputed period-to-note
   tables for NTSC and PAL, plus all expansion chips.

3. **The differential state tracking pattern** — Only emit when state changes.
   Efficient and clean.

4. **The trigger detection heuristic** — Volume 0->nonzero = note on, volume->0 =
   note off, period change = new note. Simple and effective.

5. **DPCM sample extraction** — FamiStudio reads sample data byte-by-byte from
   the emulator and deduplicates truncated variants. We need this for DMC support.

### What We Add Beyond FamiStudio

- **Automatic envelope reconstruction** — FamiStudio leaves this manual. We should
  detect repeating volume/pitch patterns across notes and collapse them into
  instrument envelope definitions.
- **Driver-specific parsing** (Pipeline A) — FamiStudio only does emulation-based
  extraction. It never looks at the ROM bytecode. Our static analysis can find
  the instrument tables directly in the ROM.
- **Reconciliation** — Cross-reference emulated behavior with parsed ROM data to
  validate extraction and build confidence.
- **REAPER output** — FamiStudio outputs to its own format, FamiTracker, NSF, WAV,
  or ROM. We output to REAPER projects.

### Key Source Files to Study

| File | What It Contains |
|------|-----------------|
| `Source/IO/NsfFile.cs` | Main import/export (~1610 lines). `Load()` is entry, `UpdateChannel()` is per-frame extraction |
| `Source/IO/NotSoFatso.cs` | C# P/Invoke wrapper. 33 STATE_* constants |
| `Source/Player/NesApu.cs` | Note frequency tables, register constants |
| `ThirdParty/NotSoFatso/NSF_Core.cpp` | 6502 emulator + APU. `GetState()`, `RunOneFrame()` |
| `ThirdParty/NotSoFatso/Wave_Square.h` | Pulse channel wave struct (duty, volume, period) |
| `ThirdParty/NotSoFatso/Wave_TND.h` | Triangle, Noise, DPCM wave structs |

---

## 3. nesmdb — NES Music Database (APU to MIDI with CC Encoding)

**Repo:** https://github.com/chrisdonahue/nesmdb
**Author:** Chris Donahue (UCSD)
**Language:** Python
**License:** MIT
**Paper:** ISMIR 2018 — "The NES Music Database: A Multi-Instrumental Dataset
with Expressive Performance Attributes"

### What It Does

Extracts music from 5,278 NES songs (397 games) via VGM register logs, then
converts through a multi-stage pipeline into MIDI with sample-accurate timing
and full performance data (volume envelopes, duty cycle changes) encoded as
MIDI CC events.

### Data Pipeline

```
VGM binary log (44.1 kHz register writes)
    |
    v
NDR: Raw register writes as (register, value) tuples
    |
    v
NDF: Functional decomposition (each write split into constituent fields
     via bitmasks — duty, volume, period, length halt, etc.)
    |
    v
Raw Score: Full APU state machine emulation at 44.1 kHz
    - Emulates frame counter (240/192 Hz)
    - Emulates envelope generator (divider-based decay 15->0)
    - Emulates sweep unit (period modification)
    - Emulates length counters
    Output: numpy array shape (N_samples, 4_channels, 4_bytes)
    |
    v
Expressive Score: Timer values converted to MIDI note numbers
    - Pulse: f = clock / (16 * (timer + 1))
    - Triangle: f = clock / (32 * (timer + 1))
    - midi_note = round(69 + 12 * log2(f / 440))
    Output: numpy array shape (N_samples, 4_channels, 3_values)
    Column 0: MIDI note (0=off, 21-108 valid)
    Column 1: Velocity (0-15 for P1/P2/NO; 0 for TR)
    Column 2: Timbre (duty 0-3 for P1/P2; noise_loop 0-1 for NO; 0 for TR)
    |
    v
MIDI with CC11/CC12 encoding
```

### The MIDI Encoding Standard (What We Should Adopt)

**Timing:** 22050 ticks per beat at 120 BPM = exactly 44100 ticks/second.
This gives **sample-accurate** timing resolution.

**Channels:**

| Channel | GM Program | is_drum |
|---------|-----------|---------|
| P1 | Lead 1 (square) | false |
| P2 | Lead 2 (sawtooth) | false |
| TR | Synth Bass 1 | false |
| NO | Breath Noise | true |

**CC11 — Velocity (Expression):**

Emitted when volume changes mid-note (same pitch sustained, volume shifts).
Value range: 0-15 (raw NES 4-bit volume, NOT scaled to 0-127).
Only for P1, P2, NO. Triangle has no volume control.

**CC12 — Timbre (Duty Cycle):**

Emitted when timbre changes.
- P1/P2: duty cycle 0-3 (12.5%, 25%, 50%, 75%)
- NO: noise loop flag 0-1
- TR: no CC12 events

**Note velocity at onset:** The MIDI Note On velocity field carries the volume
at the moment the note starts. CC11 handles subsequent changes during sustain.

**Triangle special handling:** Velocity forced to 1 (MIDI forbids velocity 0 for
note-on). No CC events. No timbre changes.

**Noise channel:** Note value = 16 - noise_period (inverted so higher = higher
perceived pitch). Range 1-16. Uses `is_drum=True`.

### APU State Machine Emulation (rawsco.py)

This is where nesmdb goes deeper than FamiStudio's import. The raw score
extraction **genuinely emulates the APU hardware**:

- **Frame counter** at 240 Hz (4-step) or 192 Hz (5-step)
- **Envelope generator** — divider-based decay from 15 to 0, with looping
- **Sweep unit** — period modification via bit-shifting
- **Length counters** — gate notes off after programmed duration

This means the volume values in the output reflect **actual envelope decay**,
not just the programmed volume register. A note with volume 15 and a decaying
envelope will show decreasing CC11 values frame by frame.

### APU Register Bitmasks (apu.py)

All 38 APU functions are defined with exact bitmasks. Key ones:

```python
# Pulse 1, Register 0 ($4000)
p1_du = 0b11000000  # duty cycle (2 bits)
p1_lh = 0b00100000  # length counter halt
p1_cv = 0b00010000  # constant volume flag
p1_vo = 0b00001111  # volume / envelope divider

# Pulse 1, Register 2-3 ($4002-$4003)
p1_tl = 0b11111111  # timer low (8 bits)
p1_ll = 0b11111000  # length counter load (5 bits)
p1_th = 0b00000111  # timer high (3 bits)

# Noise, Register 2 ($400E)
no_nl = 0b10000000  # noise loop (short mode)
no_np = 0b00001111  # noise period index
```

### What We Should Reuse

1. **CC11/CC12 encoding standard** — Proven, lossless encoding of NES performance
   data in MIDI. Adopt this as our output format.

2. **APU bitmask definitions** (apu.py) — Complete register field decomposition.
   Copy directly into our extraction engine.

3. **Timer-to-MIDI-note conversion** — The frequency formulas and note lookup
   approach. Use the same math.

4. **APU state machine** (rawsco.py) — If we need to emulate APU behavior for
   dynamic analysis, this is a complete Python implementation.

5. **The "expressive score" concept** — The idea of a (note, velocity, timbre)
   triple per sample per channel as an intermediate representation.

### What We Add Beyond nesmdb

- **Driver-specific parsing** — nesmdb works purely from VGM logs (emulation
  output). It never touches ROM bytecode. We parse the actual driver data.
- **Instrument table extraction** — nesmdb records frame-by-frame envelope
  behavior but doesn't identify the underlying instrument definitions from ROM.
  We extract the actual envelope tables the driver uses.
- **Structured instrument output** — nesmdb produces flat CC streams. We produce
  named instrument presets with envelope definitions that can be loaded into a
  synth plugin.
- **Higher-level structure** — Loop points, patterns, song structure from ROM
  data. nesmdb has no concept of musical form.
- **REAPER integration** — nesmdb outputs MIDI for ML research. We output
  complete REAPER projects with per-track instruments.

### Key Source Files to Study

| File | What It Contains |
|------|-----------------|
| `nesmdb/apu.py` | APU register bitmasks, all 38 functions |
| `nesmdb/vgm/vgm_ndr.py` | VGM binary file parser |
| `nesmdb/vgm/ndr_ndf.py` | Register writes to functional decomposition |
| `nesmdb/score/rawsco.py` | Full APU state machine emulation (the heavyweight) |
| `nesmdb/score/exprsco.py` | Timer-to-MIDI-note conversion |
| `nesmdb/score/midi.py` | Expressive score to/from MIDI with CC11/CC12 |
| `nesmdb/convert.py` | Top-level pipeline orchestration |

---

## Summary: What We Build vs What We Borrow

| Component | Source | Action |
|-----------|--------|--------|
| Capcom NES command format | CAP2MID | **Port to Python**, add CC output for duty/envelope |
| Magic byte song table scanning | CAP2MID | **Adapt pattern** for Konami driver |
| Bank-to-CPU address mapping | CAP2MID | **Copy** the iNES offset calculation |
| 6502 + APU emulation for NSF | FamiStudio/NotSoFatso | **Use as-is** or wrap for Pipeline B |
| Note frequency tables (NTSC/PAL) | FamiStudio | **Copy** the lookup tables |
| Note detection heuristic | FamiStudio | **Adopt** vol 0->nonzero trigger pattern |
| DPCM sample extraction | FamiStudio | **Study** their byte-by-byte approach |
| CC11/CC12 MIDI encoding | nesmdb | **Adopt as standard** output format |
| APU register bitmasks | nesmdb | **Copy** apu.py definitions |
| APU state machine emulation | nesmdb | **Use for** dynamic analysis validation |
| Timer-to-MIDI-note math | nesmdb | **Copy** the frequency formulas |
| Konami NES driver parser | NOBODY | **Build from scratch** (novel work) |
| Envelope table extraction from ROM | NOBODY | **Build from scratch** (novel work) |
| ROM to REAPER project pipeline | NOBODY | **Build from scratch** (novel work) |
| Envelope reconstruction from frames | NOBODY | **Build from scratch** (novel work) |
| Confidence/provenance system | NOBODY | **Build from scratch** (novel work) |

### Priority for Reuse

1. **Immediate:** Copy nesmdb's `apu.py` bitmasks and CC11/CC12 encoding into our
   extraction engine. These are small, self-contained, and directly useful.

2. **Before Capcom work:** Port CAP2MID's v3 NES parser to Python. Don't
   reverse-engineer what turboboy215 already cracked.

3. **For dynamic analysis:** Evaluate whether to use nesmdb's Python APU emulator
   (rawsco.py) or FamiStudio's NotSoFatso C++ emulator. nesmdb is pure Python
   (simpler to integrate) but slower. NotSoFatso is faster but requires C++ binding.

4. **For envelope reconstruction:** This is novel work. Study FamiStudio's
   frame-by-frame import output to understand what raw data looks like, then build
   pattern detection on top.
