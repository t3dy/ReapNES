---
driver_family: konami_maezawa
status: substantially_decoded
games_decoded:
  - cv1
  - contra
games_untested:
  - cv3
  - super_c
  - tmnt
  - gradius
  - goonies_ii
  - life_force
  - adventures_of_bayou_billy
  - teenage_mutant_ninja_turtles_ii
  - tiny_toon_adventures
---

# The Konami Maezawa NES Sound Driver

A technical reference for the sound driver used in Castlevania (1986),
Contra (1988), and likely a dozen other Konami NES titles from the
pre-VRC era (~1986-1990). Attributed to composers Kinuyo Yamashita
and Hidenori Maezawa. This document describes the architecture as
decoded by the NES Music Studio project, verified against emulator
APU traces and annotated disassembly.

---

## 1. What Is a NES Sound Driver

A NES sound driver is not a data format. It is a runtime interpreter --
a small program embedded in the game ROM that executes once per video
frame during the Non-Maskable Interrupt (NMI) handler. On NTSC
hardware, NMI fires at 60 Hz. Each invocation, the driver reads the
next byte(s) from a per-channel data stream, updates its internal
state, and writes computed values to the 2A03 APU registers.

The driver is stateful. Each of its 6 logical channels maintains 16
bytes of zero-page RAM:

| Offset | Name | Purpose |
|--------|------|---------|
| +$00 | DURATION | Frames remaining on current note |
| +$01 | PREV_PERIOD_HI | Previous period high byte |
| +$02 | ACTIVE | Channel active flag |
| +$03-$04 | DATA_PTR | Current read pointer into music data |
| +$05 | INSTRUMENT | APU register 0 value (DDLCVVVV) |
| +$07 | VOLUME_STATE | Current volume with flags |
| +$08 | FLAGS | Bit field: b0=SFX, b3=subroutine, b4=envelope, b7=sweep |
| +$09 | TEMPO | Current tempo multiplier |
| +$0A | OCTAVE | Current octave (0-4) |
| +$0B | FADE_COUNTER | Volume fade countdown |
| +$0C | FADE_START | Attack decay length |
| +$0D | FADE_STEP | Release phase length |
| +$0E-$0F | RETURN_PTR | Subroutine return address |

The 6 channels are:

| X Register | Channel | APU Base | Role |
|-----------|---------|----------|------|
| $80 | Pulse 1 | $4000 | Music |
| $90 | Pulse 2 | $4004 | Music |
| $A0 | Triangle | $4008 | Music |
| $B0 | Noise | $400C | Music / Percussion |
| $C0 | Pulse 1 SFX | $4000 | Sound effects (overrides $80) |
| $D0 | Pulse 2 SFX | $4004 | Sound effects (overrides $90) |

SFX channels share APU registers with their music counterparts. When
an SFX channel is active, its writes take priority and the music
channel is silenced until the effect completes.

The per-frame update loop:

1. Check global music-active flag ($E2).
2. Apply global fade-out if active.
3. For each channel ($80, $90, $A0, $B0, $C0, $D0):
   a. Decrement duration counter.
   b. If expired: read and execute the next command byte.
   c. If not expired: process volume envelope (if applicable).

The same byte can mean different things depending on the channel's
current state -- octave, tempo, instrument, and flags all carry forward
from previous commands. You cannot interpret bytes in isolation. This
is a stateful interpreter, not a lookup table.

---

## 2. The Three Layers

The driver architecture separates into three layers. Understanding
which layer a behavior belongs to determines whether it transfers to
other games in the family.

### Engine Layer (shared across games)

Compiled routines that live in the sound bank:

- `resume_decrescendo` -- 1/frame volume decay at note tail-end
- `set_pulse_config` -- writes duty/volume/envelope to APU registers
- `check_decrescendo_end_pause` -- threshold calculation for tail decay
- Command dispatch loop, repeat/subroutine handling, channel switching

These routines are the same binary code across CV1 and Contra (confirmed
by disassembly comparison). Any Konami game using this driver family
will have them. They define the driver's identity.

### Data Layer (per-game)

Byte streams specific to each game. The command set is shared (see
section 4), but critical parameters vary:

- **DX byte count**: CV1 reads 2 extra bytes per instrument setup;
  Contra reads 3 for pulse, 1 for triangle.
- **Volume model**: CV1 uses parametric envelopes from 2 inline bytes;
  Contra indexes into 54 pre-built lookup tables.
- **Percussion**: CV1 embeds drum triggers (E9/EA) inline in melodic
  channels; Contra has a dedicated DMC channel.
- **Pointer table format**: CV1 uses 9 bytes/track (3 pointers +
  separators); Contra uses a flat 3-byte-per-entry table.
- **ROM layout**: CV1 is mapper 0 (linear 32K); Contra is mapper 2
  (128K bank-switched). Address resolution differs fundamentally.

The data layer is where every new game requires fresh investigation.
Shared period table and shared command opcodes do NOT guarantee shared
semantics.

### Hardware Layer (universal NES)

The 2A03 APU imposes timing constraints that affect all games equally:

- **Frame counter**: The APU's internal frame counter generates
  quarter-frame clocks at ~240 Hz and half-frame clocks at ~120 Hz.
  These drive the length counter and linear counter independently of
  the driver's 60 Hz NMI loop.
- **Linear counter**: The triangle channel's gating mechanism. Clocked
  at 240 Hz, it counts down a reload value from $4008. Because 240
  does not divide evenly into 60, the exact frame at which the triangle
  silences can differ by 1 frame from any integer approximation.
- **Period registers**: 11-bit values written across two APU registers.
  The high-byte write resets the sequencer phase, causing audible clicks
  if done mid-waveform. The driver writes both bytes every frame.

Hardware-layer behaviors are not bugs in the driver or in the data.
They are the physics of the platform.

---

## 3. How the Maezawa Command Set Works

All commands are single bytes, some followed by parameter bytes. The
high nibble determines the command class.

### Notes ($00-$BF)

```
Byte = [PITCH:4][DURATION:4]

Pitch (high nibble):
  0=C  1=C#  2=D  3=D#  4=E  5=F  6=F#  7=G  8=G#  9=A  A=A#  B=B

Duration (low nibble): 0-F
  actual_frames = tempo * (duration_nibble + 1)
```

MIDI note calculation: `pitch + (4 - octave) * 12 + BASE_MIDI_OCTAVE4`
where `BASE_MIDI_OCTAVE4 = 24` (C1). For triangle, subtract 12 from
the result (see section 6).

### Rests ($C0-$CF)

```
CX = rest for duration X
actual_frames = tempo * (X + 1)
```

Channel output is silenced for the computed duration.

### Instrument / Tempo ($D0-$DF)

The DX command sets the tempo AND configures the channel's sound:

```
DX II [FF] [F0 SS]

DX  = set tempo to X (low nibble, 1-15)
II  = instrument byte, written directly to APU register $4000/$4004/$4008
      Format: DDLCVVVV
        DD   = duty cycle (0=12.5%, 1=25%, 2=50%, 3=75%)
        L    = length counter halt
        C    = constant volume flag
        VVVV = volume (0-15)
FF  = fade parameters (pulse only, NOT triangle)
      High nibble = fade_start (frames of attack decay)
      Low nibble  = fade_step (frames of release)
F0 SS = optional sweep (only if next byte == $F0)
```

The number of parameter bytes after DX varies by game and channel type.
This is the single most important thing to verify for each new game.

### Octave ($E0-$E4)

```
E0 = highest (C6-B6, period >> 4)
E1 = high    (C5-B5, period >> 3)
E2 = mid     (C4-B4, period >> 2)
E3 = low     (C3-B3, period >> 1)
E4 = base    (C2-B2, no shift)
```

Octave is stateful -- it persists until the next E0-E4 command.

### Special E-commands

```
E8       = set flag bit 4 (envelope-related; does NOT gate volume fade)
E9       = trigger snare drum (CV1 inline percussion)
EA       = trigger hi-hat drum (CV1 inline percussion)
EB XX YY = vibrato (XX=speed, YY=depth)
EC XX    = pitch adjustment (shift period table lookup by XX semitones)
```

E5-E7 and ED-EF are invalid -- they would cause infinite right-shifts,
producing silence.

### Control Flow ($FD-$FF)

```
FD XX YY    = jump to subroutine at address YYXX (little-endian)
              Saves return address at +$0E/+$0F
FE XX YY ZZ = repeat section at ZZYY, count XX
              XX=$FF = infinite loop (used for song looping)
              count=2 means 2 total passes, NOT 3
FF          = end of channel / return from subroutine
```

### Period Table

12 entries of 16-bit big-endian base periods for octave 4 (no shift):

```
C:1710  C#:1614  D:1524  D#:1438  E:1358  F:1281
F#:1209  G:1142  G#:1078  A:1017  A#:960  B:906
```

This is standard NES NTSC tuning derived from the 1.789773 MHz CPU
clock. The same table appears in CV1 at ROM $079A and Contra at ROM
$46E5 (bank 1). Its presence is the primary signature for identifying
this driver family.

Octave adjustment: `period = base_period >> (4 - octave_value)`

---

## 4. Two Envelope Strategies

The Maezawa driver uses two distinct volume envelope systems across
games. Both feed into the same `resume_decrescendo` tail-end decay.

### CV1: Parametric Envelope

Status: **VERIFIED** -- 0 pitch mismatches, <0.5% volume mismatches
across 1792 frames of Vampire Killer vs Mesen APU trace.

Two bytes from the DX command define the entire envelope shape:

- `fade_start`: number of frames of 1/frame attack decay
- `fade_step`: number of frames of 1/frame release at note end

The envelope has three phases:

```
Phase 1 (attack decay):
  Frame 0: initial volume (always full)
  Frames 1 through fade_start: decrement by 1 per frame

Hold:
  Sustain at (initial_volume - fade_start)
  Duration = note_length - fade_start - fade_step

Phase 2 (release):
  Last fade_step frames: decrement by 1 per frame
  fade_step = 0 means sustain indefinitely (no release)
```

ASCII volume curve for instrument $B5 (vol=5, fade_start=2, fade_step=3)
on a 14-frame note:

```
vol
 5 |X
 4 | X
 3 |  X X X X X X X X X
 2 |                    X
 1 |                      X
 0 |                        X
   +--+--+--+--+--+--+--+--+--+--+--+--+--+--
   f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 10 11 12 13
       |fade_start|                |fade_step |
```

ASCII volume curve for instrument $F3 (vol=3, fade_start=1, fade_step=0):

```
vol
 3 |X
 2 | X X X X X X X X X X X X X X X X X X ...
   +--+--+--+--+--+--+--+--+--+--+--+--+--+--
   f0 f1 f2 f3 ...
      |fs|  (sustains forever, no release)
```

No lookup tables exist in ROM for CV1. The instrument is fully defined
by three bytes: the APU register value, fade_start, and fade_step.

### Contra: Lookup Table Envelope

Status: **TABLE EXTRACTION VERIFIED**, decrescendo model **PROVISIONAL**.

Contra stores 54 pre-built envelope patterns in `pulse_volume_ptr_tbl`
near the start of the sound bank. The DX command's vol_env byte indexes
into this table. Each table entry is a sequence of per-frame volume
values terminated by $FF.

```
DX II VV MM   (Contra pulse DX format)
  II = APU config byte
  VV = volume envelope index (high nibble) + vol_duration (low nibble)
  MM = decrescendo multiplier
```

After the table entries are exhausted ($FF terminator), the engine
holds the last table volume until the decrescendo threshold:

```
threshold = (decrescendo_mul * note_duration) >> 4
```

When `remaining_frames <= threshold`, the `resume_decrescendo` routine
activates: volume decrements by 1/frame, bouncing at 1 (the engine
increments volume back to 1 when it hits 0, preventing premature
silence).

ASCII volume curve for a Contra lookup table envelope (hypothetical
table [5, 4, 4, 3], decrescendo_mul=2, 12-frame note):

```
vol
 5 |X
 4 | X X
 3 |      X X X X X X X
 2 |                    X
 1 |                      X X
   +--+--+--+--+--+--+--+--+--+--+--+--
   f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 10 11
   |table|  |--- hold ---|  |decres.|
```

The 54 tables provide much more expressive control than CV1's
parametric model -- attack shapes, multi-stage decays, crescendos, and
complex rhythmic pulsing are all possible.

---

## 5. The Triangle Anomaly

The triangle channel is fundamentally different from the pulse channels
at the hardware level, and this creates persistent approximation errors
in any software model.

### Why Triangle Is 1 Octave Lower

The 2A03 triangle channel uses a 32-step waveform sequencer. Pulse
channels use 16-step sequences (8 high + 8 low for 50% duty, etc.).
For the same period register value, the triangle completes its cycle
in twice the time, producing a frequency one octave lower.

The driver accounts for this: triangle data is authored at the same
octave numbers as pulse, but the hardware naturally plays it an octave
lower. In MIDI export, subtract 12 semitones from the triangle's
computed MIDI note.

### Linear Counter Gating

The triangle has no volume register. Articulation is controlled by the
linear counter ($4008). The instrument byte from the DX command is
written directly to $4008:

```
Bit 7:   control flag
          1 = sustain mode (reload continuously, sounds full duration)
          0 = one-shot mode (counts down and silences)
Bits 6-0: reload value
```

In one-shot mode, the linear counter is clocked at 240 Hz (quarter-
frame rate). The triangle sounds for approximately:

```
sounding_frames = (reload_value + 3) // 4
```

This formula is an approximation. The actual APU quarter-frame sequencer
does not align perfectly with 60 Hz frame boundaries. The result:

**Status: APPROXIMATE** -- 195 sounding mismatches on CV1 Vampire
Killer (1792 frames). Approximately 8 of these are real sounding-frame
errors; the rest are cosmetic (both sides silent, but one retains a
stale period value). Fixing this requires modeling the APU's internal
frame counter step sequence, not just integer division.

This is a hardware-layer issue. The driver data and engine code are
correct. The approximation error is in our model of the 2A03 timing.

---

## 6. What Remains Undiscovered

The following Konami NES games from the 1986-1990 era are candidates
for the Maezawa driver family. None have been tested by this project.
Difficulty ratings reflect estimated effort to produce a working parser,
assuming the driver family is confirmed.

| Game | Year | Mapper | Estimated Difficulty | Notes |
|------|------|--------|---------------------|-------|
| Castlevania III: Dracula's Curse | 1989 | 5 (MMC5) | HARD | MMC5 expansion audio adds 2 extra pulse channels. Bank switching is complex. Possible VRC variant. |
| Super C (Super Contra) | 1990 | 0 | MODERATE | Partially worked with CV1 parser (9/15 tracks). Needs own DX config. |
| TMNT (Teenage Mutant Ninja Turtles) | 1989 | 1 (MMC1) | MODERATE | Listed in driver family. New mapper type to handle. |
| Gradius | 1986 | 0 | MODERATE | Early Konami title. May use proto-Maezawa or different driver entirely. |
| Goonies II | 1987 | 2 | MODERATE | Listed in same driver family as CV1/Contra. Bank-switched. |
| Life Force (Salamander) | 1988 | 2 | MODERATE | Konami STG. Likely same era driver. |
| Adventures of Bayou Billy | 1989 | 1 | MODERATE | Multi-genre game. May have complex sound routing. |
| TMNT II: The Arcade Game | 1990 | 4 (MMC3) | MODERATE-HARD | New mapper type (MMC3). Late-era, possible driver evolution. |
| Tiny Toon Adventures | 1991 | 1 | MODERATE | Late Konami NES title. May use evolved driver. |
| Stinger (Moero TwinBee) | 1987 | 0 | EASY | Early mapper 0 title. If Maezawa, similar to CV1 layout. |
| The Lone Ranger | 1991 | 4 | HARD | MMC3, late era. Possible VRC variant. |
| Bucky O'Hare | 1992 | 4 | HARD | Very late NES. Likely evolved or replaced driver. |
| Jackal | 1988 | 2 | MODERATE | Same era as Contra. Good candidate. |
| Blades of Steel | 1988 | 2 | MODERATE | Sports title. Same era, may share driver. |
| Track & Field II | 1988 | 0 | EASY | Mapper 0, same era. Good candidate. |
| Rollergames | 1990 | 4 | MODERATE-HARD | MMC3 mapper. |
| Castlevania II: Simon's Quest | 1987 | 2 | N/A | **CONFIRMED NOT Maezawa.** Uses Fujio variant -- different engine entirely. Same period table, different driver. |

Each game is a potential research project. The procedure is always:
scan for the period table, confirm the driver identity, find the
disassembly if one exists, then verify DX byte count and volume model
before writing any parser code.

**WARNING**: Castlevania II demonstrates that finding the period table
is necessary but NOT sufficient. CV2 has the same period values but a
completely different sound engine. Always verify engine routines.

---

## 7. How to Identify This Driver in an Unknown ROM

A step-by-step procedure for determining whether an unknown Konami NES
ROM uses the Maezawa driver family.

### Step 1: Scan for the Period Table Signature

Search the ROM for the two-byte sequence `$AE $06`. This is the first
entry of the period table -- the value 1710 stored in little-endian
format (some games use big-endian; also try `$06 $AE`).

If found, note the ROM offset. The full table is 24 bytes (12 entries
of 2 bytes each). Verify by checking that subsequent entries match the
known values: 1614, 1524, 1438, 1358, 1281, 1209, 1142, 1078, 1017,
960, 906.

If NOT found, this is not a Maezawa-family driver. Stop.

### Step 2: Check the Mapper

Read bytes 6-7 of the iNES header (ROM offset 6-7):

```
Mapper = (rom[6] >> 4) | (rom[7] & 0xF0)
```

| Mapper | Type | Address Resolution |
|--------|------|-------------------|
| 0 | NROM (32K) | Linear: CPU = ROM + $10 (iNES header) |
| 1 | MMC1 (128-256K) | Bank-switched, 16K banks |
| 2 | UNROM (128K) | Bank-switched, 16K banks |
| 4 | MMC3 (128-512K) | Bank-switched, 8K banks |
| 5 | MMC5 (128-1024K) | Bank-switched + expansion audio |

Bank-switched mappers require knowing which bank contains the sound
data. This is typically determined from the disassembly or by tracing
execution in an emulator debugger.

### Step 3: Scan for Command Patterns

Search the ROM near the period table for characteristic byte patterns:

- **DX + instrument bytes**: sequences like `D7 F4 21` (tempo 7,
  instrument $F4, fade $21). The DX byte will have high nibble $D and
  low nibble 1-F.
- **FE repeat commands**: `FE XX YY ZZ` where XX is a small count
  (01-0F) or $FF (infinite loop), and YYZZ is a valid ROM address.
- **FD subroutine calls**: `FD YY ZZ` followed by music data at the
  target address.
- **E0-E4 octave commands**: these should appear frequently before
  note data.

### Step 4: Locate the Pointer Table

The pointer table is best found from a disassembly. Search GitHub for
"[game name] NES disassembly" or check the references/ directory.

If no disassembly exists, use an emulator debugger (Mesen recommended):
set a breakpoint on the sound init routine (typically called when music
changes), then trace execution to find where channel data pointers are
loaded from ROM.

The pointer table contains 2-byte little-endian CPU addresses, grouped
by track. The format varies per game (CV1 uses 9 bytes/track with
separator bytes; Contra uses a flat 3-byte/entry table).

### Step 5: Determine DX Byte Count

This is the critical per-game variable. After the DX byte and
instrument byte, how many additional parameter bytes does the engine
read?

- CV1: 1 additional byte (fade parameter), total = DX + 2
- Contra pulse: 2 additional bytes (vol_env + decrescendo), total = DX + 3
- Contra triangle: 0 additional bytes, total = DX + 1

Verify by reading the DX command handler in the disassembly. If no
disassembly, parse one track and check whether the note data following
the DX sequence makes musical sense (correct octave values, reasonable
durations, no garbage bytes).

### Step 6: Identify the Volume Model

Two possibilities:

- **Parametric** (CV1 style): the fade byte after the instrument IS
  the envelope. No separate table exists.
- **Lookup table** (Contra style): a vol_env byte indexes into an
  array of per-frame volume sequences stored elsewhere in the sound
  bank. Search for a block of small integers (0-15) terminated by $FF
  bytes near the start of the sound bank.

### Step 7: Parse One Track and Listen

Parse a single well-known track (first stage music is usually a good
choice). Export to MIDI. Listen side-by-side with the game running in
an emulator. Do NOT batch-extract until this reference track sounds
correct.

If the notes are right but timing is off: check the tempo multiplier.
If pitch is systematically wrong: check the octave mapping and triangle
offset. If volume shape is wrong: check the envelope model.

### Quick Reference: Identification Checklist

```
[ ] Period table found ($AE $06 or $06 $AE)?
[ ] Mapper identified?
[ ] DX/FE/FD command patterns present?
[ ] Disassembly located?
[ ] Pointer table found?
[ ] DX byte count determined?
[ ] Volume model identified (parametric vs lookup)?
[ ] One track parsed and verified by ear?
```

---

## Appendix: Key File Paths

| File | Purpose |
|------|---------|
| `extraction/drivers/konami/parser.py` | CV1 parser (Maezawa command set) |
| `extraction/drivers/konami/contra_parser.py` | Contra parser |
| `extraction/drivers/konami/frame_ir.py` | Frame IR with both envelope strategies |
| `extraction/drivers/konami/midi_export.py` | MIDI export from frame IR |
| `extraction/drivers/konami/spec.md` | Full command byte specification |
| `extraction/manifests/*.json` | Per-game structured truth |
| `scripts/trace_compare.py` | Frame-level validation vs APU trace |
| `scripts/rom_identify.py` | ROM analysis and driver identification |
| `docs/HANDOVER_FIDELITY.md` | CV1 envelope verification evidence |
| `docs/KONAMITAKEAWAY.md` | Cross-game comparison findings |
