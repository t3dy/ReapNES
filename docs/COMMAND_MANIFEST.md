# Konami Maezawa NES Sound Driver -- Byte-Level Command Reference

## Overview

The Konami pre-VRC sound driver (Maezawa variant, ~1986-1990) uses a
stateful bytecode interpreter that processes one command per frame per
channel. The command byte is read from a linear data stream in ROM. The
high nibble determines the command family. The low nibble carries inline
parameter data. Some commands read one or more additional bytes from the
stream after the command byte itself.

The interpreter maintains per-channel state in zero-page RAM: current
octave, tempo multiplier, volume envelope parameters, a subroutine
return address, and a repeat counter. State persists across commands
until explicitly changed.

Known games using this driver family: Castlevania (U), Contra (U),
Super C, TMNT, Goonies II, Gradius II. Castlevania II uses a different
engine (Fujio variant) despite sharing the same period table.

Primary sources:
- "Castlevania Music Format v1.0" by Sliver X (romhacking.net doc #150)
- Contra (US) fully annotated disassembly (vermiceli/nes-contra-us)
- Castlevania (U) labelled disassembly + direct ROM analysis

---

## Master Command Table

Status values: `VERIFIED` = confirmed against disassembly and/or trace
data. `INFERRED` = behavior deduced from ROM patterns but not
disassembly-confirmed. `PARTIAL` = some aspects understood, others not.
`UNKNOWN` = not decoded.

| Byte Range  | Name            | Extra Bytes          | CV1             | Contra          | Status          | Notes                                              |
|-------------|-----------------|----------------------|-----------------|-----------------|-----------------|----------------------------------------------------|
| `$00-$BF`   | Note            | 0                    | hi=pitch, lo=dur| Same            | VERIFIED        | Duration = tempo * (lo + 1)                        |
| `$C0-$CF`   | Rest            | 0                    | Duration rest   | Duration rest   | VERIFIED        | lo = duration nibble, same formula as notes         |
| `$D0-$DF`   | Instrument (DX) | 2 (CV1) / 3 or 1 (Contra) | config+fade | config+env+decr (pulse), config (tri) | VERIFIED | Channel-sensitive byte count. See dedicated section |
| `$E0-$E4`   | Octave Set      | 0                    | Set octave 0-4  | Same            | VERIFIED        | 0=highest (C6), 4=lowest (C2)                      |
| `$E5-$E7`   | (Invalid)       | 0                    | Clamps to octave| Unknown         | INFERRED        | Infinite right-shift produces silence               |
| `$E8`       | Flag Set        | 0                    | Envelope enable | Flatten note    | VERIFIED        | Different semantics per game                        |
| `$E9`       | Snare Trigger   | 0                    | Inline drum     | N/A             | VERIFIED (CV1)  | CV1 only; Contra uses separate channel              |
| `$EA`       | Hi-Hat Trigger  | 0                    | Inline drum     | N/A             | VERIFIED (CV1)  | CV1 only; Contra uses separate channel              |
| `$EB`       | Vibrato Setup   | 2                    | Set vibrato     | Same (unused)   | PARTIAL         | Parameters read but not fully decoded               |
| `$EC`       | Pitch Adjust    | 1                    | Not used        | Semitone offset | VERIFIED (Contra)| Shifts index into period table                     |
| `$ED-$EF`   | (Invalid)       | 0                    | Silent/clamp    | Unknown         | INFERRED        | Same infinite-shift issue as E5-E7                  |
| `$F0 $SS`   | Sweep (inline)  | 1                    | After DX only   | Unknown         | VERIFIED (CV1)  | Only valid inside DX sequence, not standalone       |
| `$F0-$FC`   | (Unassigned)    | --                   | --              | --              | UNKNOWN         | No known standalone use outside DX context          |
| `$FD`       | Subroutine Call | 2                    | Push + jump     | Same            | VERIFIED        | Target is 16-bit LE CPU address                     |
| `$FE`       | Repeat          | 3                    | count + ptr LE  | Same            | VERIFIED        | $FF count = infinite loop (end of song)             |
| `$FF`       | End / Return    | 0                    | Pop or terminate| Same            | VERIFIED        | Pops return stack; if empty, terminates channel     |

### Low Commands ($10-$2F)

These appear in SFX contexts and occasionally in music data. They are
documented in the Contra disassembly but rarely encountered during
normal music parsing.

| Byte Range  | Name                | Extra Bytes | Status  | Notes                                          |
|-------------|---------------------|-------------|---------|------------------------------------------------|
| `$10 $XX`   | Set Sweep Register  | 1           | PARTIAL | Writes XX to APU $4001/$4005. $00 = disable    |
| `$11`       | Set Alternate Flag  | 0           | PARTIAL | Sets bit 4 of channel flags register           |
| `$20-$2F`   | Duration + Config   | 1-2         | PARTIAL | Low nibble sets duration multiplier; reads APU config byte. If lo=$F, reads extra byte for multiplier |

---

## Per-Command Detail

### $00-$BF: Note

**Format:** Single byte. No additional reads.

```
  7 6 5 4   3 2 1 0
 [PITCH  ] [DURATN ]

 PITCH (high nibble, 0-B):
   0=C  1=C#  2=D  3=D#  4=E  5=F  6=F#  7=G  8=G#  9=A  A=A#  B=B

 DURATION (low nibble, 0-F):
   actual_frames = tempo * (duration + 1)
```

**Processing:**
1. Read current octave from channel state.
2. Look up base period from the 12-entry period table (ROM $079A for
   CV1, ROM $46E5 for Contra bank 1).
3. Right-shift period by `(4 - octave)` to get the final APU period.
4. Write period to APU $4002/$4003 (pulse) or $400A/$400B (triangle).
5. Write instrument byte to APU $4000/$4004/$4008.
6. Set duration counter to `tempo * (duration_nibble + 1)`.

**MIDI mapping:**

```
midi_note = 36 + pitch + (4 - octave) * 12
```

For triangle, subtract 12 (the APU triangle uses a 32-step waveform
vs 16-step for pulse, sounding one octave lower at the same period).

**Gotcha:** In Contra, if an EC pitch-adjust command is active, the
pitch index is offset before period lookup. This can push the pitch
past 11, which requires wrapping into the next octave.

**CV1 drum triggers:** In CV1, the byte immediately following a note
may be $E9 (snare) or $EA (hi-hat). The parser must peek ahead after
every note. In Contra, drums are on a separate channel and this peek
is not needed.


### $C0-$CF: Rest

**Format:** Single byte. No additional reads.

```
  7 6 5 4   3 2 1 0
 [1 1 0 0] [DURATN ]

 actual_frames = tempo * (duration + 1)
```

**Processing:**
1. Silence the channel (write 0 volume to APU register 0).
2. Set duration counter.
3. No period write.

**Per-game variation:** Both CV1 and Contra treat $C0-$CF as a timed
rest with duration calculated identically to notes. The Contra parser
comment mentions "mute" but the actual behavior in the disassembly
(`calc_cmd_delay`) uses the same duration formula.


### $D0-$DF: Instrument (DX) -- SEE DEDICATED SECTION BELOW

**Format:** Variable-length. The DX byte itself is always 1 byte. The
number of additional bytes depends on the game AND the channel type.


### $E0-$E4: Octave Set

**Format:** Single byte. No additional reads.

```
  E0 = octave 0  (highest: C6-B6, period >> 4)
  E1 = octave 1  (high:    C5-B5, period >> 3)
  E2 = octave 2  (middle:  C4-B4, period >> 2)
  E3 = octave 3  (low:     C3-B3, period >> 1)
  E4 = octave 4  (lowest:  C2-B2, period >> 0)
```

**Processing:** Store the low nibble as the current octave. This value
persists until the next octave command.

**Gotcha:** The octave numbering is inverted relative to musical
convention. E0 is the HIGHEST octave (smallest period). E4 is the
LOWEST. When converting to MIDI: `midi_octave = 6 - engine_octave`.

**Gotcha:** Values E5-E7 are technically parsed as octave commands by
both the CV1 and Contra parsers (low nibble > 4), but they produce
infinite right-shifts that yield a period of 0, resulting in silence
or unpredictable APU behavior. The CV1 parser clamps to 0-4 range.


### $E8: Flag Set

**Format:** Single byte. No additional reads.

**CV1 behavior:** Sets bit 4 of the channel flags register ($08,x).
This enables the volume fade processing loop. Without E8, the note
plays at constant volume regardless of the fade parameters set by DX.

**Contra behavior:** Sets a "flatten note" flag. The Contra disassembly
labels this differently from CV1. The Contra parser emits an
`EnvelopeEnable` event for compatibility but the semantics differ.

**Gotcha:** This command burned us during CV1 development. It looked
correct on Square 1 but produced wrong envelopes on Square 2 because
we assumed it was a per-instrument setting rather than a per-channel
flag that persists across instrument changes.


### $E9: Snare Drum Trigger (CV1 only)

**Format:** Single byte. No additional reads.

**Processing:** Calls the sound effect routine with parameter 2,
triggering a noise-channel snare hit. In CV1, this command appears
inline in the pulse or triangle data stream, usually immediately after
a note byte. The drum borrows the duration of the preceding note.

**Contra:** Not used. Contra has a dedicated 4th channel (noise/DMC)
with its own data stream for percussion.


### $EA: Hi-Hat Trigger (CV1 only)

**Format:** Single byte. No additional reads.

**Processing:** Calls the sound effect routine with parameter 1,
triggering a noise-channel hi-hat. Same inline behavior as E9.


### $EB: Vibrato Setup

**Format:** 3 bytes total: `$EB $P1 $P2`.

```
  EB PP QQ

  PP = vibrato parameter 1 (speed or depth -- not fully decoded)
  QQ = vibrato parameter 2
```

**Processing:** Stores two vibrato parameters in channel state. The
engine's vibrato routine modulates the period register each frame when
active. The exact parameter interpretation (which is speed, which is
depth, the modulation waveform) has not been fully reverse-engineered.

**Status:** Code exists in both CV1 and Contra engines. The Contra
disassembly labels the routine but notes it is not called by any music
track data in that game. CV1 usage is unconfirmed.


### $EC: Pitch Adjust (Contra)

**Format:** 2 bytes total: `$EC $NN`.

```
  EC NN

  NN = semitone offset added to pitch index before period table lookup
```

**Processing:** Stores NN as a persistent pitch adjustment. On
subsequent note commands, the pitch index (high nibble) is offset by
this value before the period table lookup. If the adjusted pitch
exceeds 11, it wraps into the next higher octave (octave value
decremented, pitch reduced by 12).

**CV1:** Not used. The CV1 parser does not handle EC and would
misinterpret it as an invalid octave command.

**Evidence:** Confirmed in Contra disassembly. The engine doubles the
offset for 2-byte table entries internally.


### $FD: Subroutine Call

**Format:** 3 bytes total: `$FD $LO $HI`.

```
  FD LL HH

  HHLL = 16-bit little-endian CPU target address
```

**Processing:**
1. Push current position + 3 (address after FD LL HH) onto the
   return stack.
2. Set the data pointer to the target address.
3. Continue reading commands from the new location.
4. When $FF is encountered with a non-empty return stack, pop and
   resume from the saved address.

**Gotcha:** The return stack is one level deep in hardware. The parser
uses a software stack that supports nesting, but actual NES driver
behavior with nested FD calls is untested.

**Address conversion:**
- CV1 (mapper 0): `rom_offset = cpu_addr - $8000 + 16`
- Contra (mapper 2, bank 1): `rom_offset = 16 + (1 * 16384) + (cpu_addr - $8000)` for $8000-$BFFF


### $FE: Repeat

**Format:** 4 bytes total: `$FE $COUNT $LO $HI`.

```
  FE CC LL HH

  CC   = repeat count (number of total passes through the section)
  HHLL = 16-bit little-endian CPU address of loop start
```

**Processing:**
1. If CC = $FF: infinite loop. This marks the end of the song (the
   music loops forever). Parser should stop here.
2. If CC = finite value: the driver maintains a counter at offset
   $06,x in channel RAM. Each time FE is hit, the counter increments.
   When counter == CC, the loop is done and execution continues past
   the FE command (4 bytes forward). Otherwise, the data pointer jumps
   back to HHLL.

**Repeat count semantics (from disassembly at _loc_0352):**
- `count=1`: 1 pass total, 0 loop-backs. The section plays once.
- `count=2`: 2 passes total, 1 loop-back.
- `count=N`: N passes total, N-1 loop-backs.
- `count=$FF`: infinite loop, never falls through.

**Gotcha:** We initially implemented count=2 as "loop back 2 times"
(3 total passes). The disassembly shows the count byte is the total
number of passes, not the number of loop-backs. This off-by-one
burned 2+ prompts and produced songs that were too long.


### $FF: End / Return

**Format:** Single byte. No additional reads.

**Processing:**
1. Check the return stack.
2. If non-empty: pop the saved address and resume from there
   (subroutine return).
3. If empty: terminate the channel. No more data is read.

---

## DX: The Most Dangerous Command

The DX command ($D0-$DF) is the single largest source of parsing errors
in this driver family. It has three properties that make it treacherous:

1. **Variable byte count.** The number of bytes consumed after DX
   depends on the game AND the channel type. Getting this wrong
   desynchronizes the entire parse -- every subsequent byte is read as
   the wrong command type.

2. **Channel-sensitive behavior.** Triangle channels read fewer bytes
   than pulse channels in every known game.

3. **Game-specific semantics.** The meaning of the extra bytes differs
   between CV1 and Contra despite using the same command byte range.

### DX Byte Count Comparison

| Game   | Channel  | Byte 0 (DX) | Byte 1        | Byte 2        | Byte 3        | Total |
|--------|----------|-------------|---------------|---------------|---------------|-------|
| CV1    | Pulse    | Tempo       | APU config    | Fade params   | --            | 3     |
| CV1    | Triangle | Tempo       | (none)        | --            | --            | 1     |
| Contra | Pulse    | Tempo       | APU config    | Vol env byte  | Decrescendo   | 4     |
| Contra | Triangle | Tempo       | Tri config    | --            | --            | 2     |

### CV1 DX Format (Pulse)

```
  DX II FF [F0 SS]

  DX: low nibble = tempo (1-15). Stored as SOUND_LENGTH_MULTIPLIER.
  II: APU register $4000/$4004 value (DDLCVVVV).
      DD   = duty cycle (0=12.5%, 1=25%, 2=50%, 3=75%)
      L    = length counter halt (usually 1)
      C    = constant volume flag (usually 1)
      VVVV = initial volume (0-15)
  FF: fade parameters.
      High nibble = fade_start (frames before fade begins)
      Low nibble  = fade_step (volume decrement rate)
  F0 SS: OPTIONAL. Only present if the byte after FF is $F0.
      SS = sweep register value ($4001/$4005). $00 = disable sweep.
```

### CV1 DX Format (Triangle)

```
  DX

  DX: low nibble = tempo only. No additional bytes.
```

The triangle channel skips the instrument and fade bytes entirely. The
triangle's APU register ($4008) is set separately or defaults. This
asymmetry is confirmed in the disassembly: the triangle branch jumps
past the instrument-read code.

### Contra DX Format (Pulse)

```
  DX CC VV UU

  DX: low nibble = tempo.
  CC: APU config byte (same DDLCVVVV format as CV1).
  VV: volume envelope selector.
      Bit 7 set   = automatic decrescendo (1/frame decay).
                     Low nibble = PULSE_VOL_DURATION (frame limit).
      Bit 7 clear = index into pulse_volume_ptr_tbl (54 entries).
                     The table contains pointers to per-frame volume
                     sequences terminated by $FF.
  UU: low nibble = decrescendo multiplier (UNKNOWN_SOUND_00).
      Controls how many frames of silence are appended at the note end.
```

### Contra DX Format (Triangle)

```
  DX CC

  DX: low nibble = tempo.
  CC: triangle config byte (written to $4008).
```

### The F0 Sweep Trap (CV1 only)

After reading the fade byte (FF), the CV1 parser must peek at the next
byte. If it is $F0, two more bytes are consumed (the $F0 marker and
the sweep register value SS). If it is NOT $F0, the byte belongs to
the next command and must not be consumed.

This means the CV1 DX command is either 3 bytes (DX II FF) or 5 bytes
(DX II FF F0 SS) depending on context. Failing to handle this
lookahead desynchronizes the parser.

### Why DX Errors Are Catastrophic

If the parser reads too few bytes after DX, the leftover bytes are
interpreted as command bytes. A stray instrument byte like $F4 would
be parsed as an unknown F-command. A fade byte like $31 would be
parsed as a note (pitch=3, duration=1). From that point forward, every
single command is wrong.

If the parser reads too many bytes, it consumes the start of the next
real command. The symptoms are the same: total desynchronization.

**Rule:** When adding a new game, determine the DX byte count from the
disassembly FIRST. Do not guess. Do not assume it matches CV1 or
Contra. Read the `sound_cmd_routine_0d` equivalent in the target
game's disassembly and count the `lda (sound_current_ptr),y` /
`iny` sequences.

---

## Commands We Don't Fully Understand

### $10-$1F: Sweep and Flag Commands

From the Contra disassembly:

```
$10 $XX  -- Writes XX to the APU sweep register ($4001 for pulse 1,
            $4005 for pulse 2). Value $00 disables sweep. This is
            confirmed in disassembly but rarely seen in music data.

$11      -- Sets bit 4 of the channel flags register. In CV1, this is
            the same bit as E8 (envelope enable). In Contra, labeled
            as a "flatten note" flag. The exact musical effect when
            used standalone (outside E8 context) is unclear.
```

These commands appear primarily in SFX data streams. Their presence in
music data has not been confirmed for any track, but a parser
encountering them must handle the byte count correctly ($10 reads 1
extra byte, $11 reads 0) to avoid desynchronization.

### $20-$2F: Duration Multiplier + APU Config

From the Contra disassembly:

```
$2X      -- Low nibble sets a duration multiplier override.
            If low nibble = $F, reads one additional byte as the
            multiplier value.
            Then reads one more byte as the APU config high nibble.
```

These are used in SFX contexts to set up rapid-fire note patterns.
Their interaction with the normal DX tempo system in a music context
is not documented. Total byte count: 2 (if lo != $F) or 3 (if lo == $F).

### $EB: Vibrato Parameters

The vibrato routine exists in both the CV1 and Contra engines. Two
parameter bytes are read after the $EB command byte. The Contra
disassembly labels these but notes they are never referenced by any
music track's data stream. Possible interpretations:

- Byte 1 = vibrato speed (frames per cycle)
- Byte 2 = vibrato depth (period modulation amount)

Without a game that actually uses EB in its music data, the parameter
encoding remains unverified. A parser MUST still consume the 2
parameter bytes to keep the stream aligned.

### $E8: CV1 vs Contra Semantics

In CV1, E8 sets bit 4 of the flags register, enabling the parametric
volume fade loop. Notes played without E8 hold constant volume.

In Contra, E8 is labeled as setting a "flatten note" flag. The Contra
parser emits an `EnvelopeEnable` event for structural compatibility,
but the actual effect on Contra's lookup-table-based envelope system
differs from CV1's parametric fade.

The behavioral difference means: code that works correctly for CV1
envelope processing may produce wrong results if applied to Contra
data (or vice versa) when E8 is encountered. Always check which game
you are targeting.

---

## How to Decode a New Command

When you encounter a byte pattern that doesn't match any known command,
follow this protocol. Do not guess.

### Step 1: Identify the Exact Byte

Record the byte value and its ROM offset. Record the channel type
(pulse, triangle, noise) and the game. Check the master table above --
is this byte in a range that should be handled?

### Step 2: Check the Disassembly

If an annotated disassembly exists for the game (check `references/`),
find the command dispatch routine. In CV1, this is the jump table after
the `cmp` chain in the sound update loop. In Contra, look for
`sound_cmd_routine_XX` labels.

Count the number of `lda (sound_current_ptr),y` / `iny` instructions
in the handler. Each one reads one additional byte from the data
stream. This gives you the exact byte count.

### Step 3: Dump Surrounding Context

If no disassembly exists, dump 16-32 bytes around the unknown command
from ROM. Look for recognizable patterns:

- Does the byte after the unknown command look like a valid note
  ($00-$BF)?
- Does skipping N bytes after the unknown command realign the parser
  with known commands?
- Is this byte at a position where desynchronization from an earlier
  DX error could have placed it?

### Step 4: Test with Trace Data

If the game can be run in Mesen, set a breakpoint on the sound update
routine and step through the unknown command. Record which APU
registers are written, which RAM locations change, and how many bytes
the data pointer advances.

```bash
# Dump trace frames around the suspected location
PYTHONPATH=. python scripts/trace_compare.py --dump-frames N-M --channel <ch>
```

### Step 5: Record Findings

Add the command to the per-game manifest JSON with status `hypothesis`.
Include the byte value, observed byte count, and your interpretation.
Do not mark as `verified` until confirmed against disassembly or trace
data. Update the master table in this document.

### Step 6: Do Not Batch-Fix

If you discover a new command while parsing a full song, fix the
handling for THAT command only. Do not attempt to fix multiple unknown
commands in one pass. Each unknown command is an independent hypothesis
that must be validated separately.

---

## Channel Memory Layout (Zero-Page RAM)

Each channel occupies 16 bytes. Base addresses: $80 (Pulse 1), $90
(Pulse 2), $A0 (Triangle), $B0 (Noise), $C0 (SFX Pulse 1), $D0 (SFX
Pulse 2).

| Offset | Name          | Description                                    |
|--------|---------------|------------------------------------------------|
| +$00   | DURATION      | Frames remaining for current note/rest          |
| +$01   | PREV_PERIOD_HI| Previous period high byte (for hardware writes) |
| +$02   | ACTIVE        | Channel active flag (0 = inactive)              |
| +$03   | DATA_PTR_LO   | Current read pointer, low byte                  |
| +$04   | DATA_PTR_HI   | Current read pointer, high byte                 |
| +$05   | INSTRUMENT    | APU register 0 value (DDLCVVVV)                 |
| +$06   | REPEAT_CTR    | FE repeat counter                               |
| +$07   | VOLUME_STATE  | Current volume with flags                       |
| +$08   | FLAGS         | Bit flags: b0=SFX, b3=subroutine, b4=envelope, b7=sweep |
| +$09   | TEMPO         | Current tempo multiplier                        |
| +$0A   | OCTAVE        | Current octave value (0-4)                       |
| +$0B   | FADE_COUNTER  | Volume fade countdown timer                      |
| +$0C   | FADE_START    | Fade start delay (from DX fade byte high nibble) |
| +$0D   | FADE_STEP     | Volume decrement rate (from DX fade byte low nibble) |
| +$0E   | RETURN_PTR_LO | Subroutine return address, low byte              |
| +$0F   | RETURN_PTR_HI | Subroutine return address, high byte             |

SFX channels ($C0, $D0) override music channels ($80, $90) when active.

---

## Period Table

12 entries, 16-bit values, located at ROM $079A (CV1) / $46E5 (Contra
bank 1). These represent the base period for octave 4 (E4, no shift).

| Index | Note | Period (decimal) | Freq (Hz) | MIDI |
|-------|------|------------------|-----------|------|
| 0     | C    | 1710             | 65.4      | 36   |
| 1     | C#   | 1614             | 69.3      | 37   |
| 2     | D    | 1524             | 73.4      | 38   |
| 3     | D#   | 1438             | 77.7      | 39   |
| 4     | E    | 1358             | 82.3      | 40   |
| 5     | F    | 1281             | 87.3      | 41   |
| 6     | F#   | 1209             | 92.5      | 42   |
| 7     | G    | 1142             | 97.9      | 43   |
| 8     | G#   | 1078             | 103.7     | 44   |
| 9     | A    | 1017             | 109.9     | 45   |
| 10    | A#   | 960              | 116.4     | 46   |
| 11    | B    | 906              | 123.3     | 47   |

Octave shift: `final_period = base_period >> (4 - octave_value)`

The period table is identical between CV1 and Contra (standard NES
NTSC tuning). This does NOT indicate the same driver -- CV2 also uses
these exact values with a completely different engine.

---

## Contra Percussion Channel

Contra's noise/DMC channel uses a simplified command format that shares
only the F-series control commands with the melodic channels.

| Byte Range  | Name           | Extra Bytes | Notes                              |
|-------------|----------------|-------------|------------------------------------|
| `$00-$CF`   | Percussion Hit | 0           | hi=sample type, lo=duration nibble |
| `$D0-$DF`   | Set Tempo      | 0           | lo=tempo, no additional bytes      |
| `$FD`       | Subroutine     | 2           | Same as melodic channels           |
| `$FE`       | Repeat         | 3           | Same as melodic channels           |
| `$FF`       | End/Return     | 0           | Same as melodic channels           |

Percussion sample mapping (from `percussion_tbl` in disassembly):

| High Nibble | Sample             | Noise Channel |
|-------------|--------------------|---------------|
| 0           | Kick               | Yes (sound_02)|
| 1           | Snare              | No (DMC only) |
| 2           | Hi-Hat             | No (DMC only) |
| 3           | Kick + Snare       | Yes + DMC     |
| 4           | Kick + Hi-Hat      | Yes + DMC     |
| 5           | Snare (alt)        | No (DMC only) |
| 6           | Kick + Snare (alt) | Yes + DMC     |
| 7           | Kick + Snare (alt) | Yes + DMC     |

Values >= 3 trigger both a noise-channel bass drum burst (sound_02)
and a DMC sample playback. Values 1-2 trigger DMC only. Value 0
triggers noise-channel kick only.
