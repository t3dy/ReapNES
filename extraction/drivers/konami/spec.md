# Konami Pre-VRC Sound Driver — Specification

## Status: Partially Decoded (Castlevania 1)

Primary source: "Castlevania Music Format v1.0" by Sliver X (romhacking.net #150)
Secondary source: Contra (US) fully annotated disassembly (vermiceli/nes-contra-us)

## Driver Identity
- **Family name**: konami_pre_vrc (Maezawa variant)
- **Active period**: ~1986-1990
- **Primary target**: Castlevania (U) (V1.0) — UxROM, mapper 2
- **Same driver family**: Contra, Super C, TMNT, Goonies II, Gradius II
- **Different driver**: Castlevania II uses Fujio variant (do NOT assume compatibility)

## Command Byte Format (from Sliver X, confidence: high)

### Note Commands (0x00-0xBF)

Each byte encodes pitch in the high nibble and duration in the low nibble:

```
Byte = [PITCH_NIBBLE][DURATION_NIBBLE]

High nibble (pitch):
  0 = C
  1 = C#
  2 = D
  3 = D#
  4 = E
  5 = F
  6 = F#
  7 = G
  8 = G#
  9 = A
  A = A#
  B = B
  C = rest (CX = rest of duration X)

Low nibble (duration):
  0 = shortest (fastest)
  F = longest (slowest)
  Duration is relative to the current tempo setting.
```

### Control Commands

| Byte/Range | Args | Meaning | Confidence |
|-----------|------|---------|------------|
| `CX` | none | Rest of duration X (X = low nibble) | high |
| `D0` | none | Extremely slow tempo | high |
| `D1-DF` | none | Set tempo (D1=fastest, DF=slowest) | high |
| `E0-E4` | none | Set octave (E0=highest, E4=lowest/silent) | high |
| `E8` | none | Set octave back to highest | high |
| `E9` | none | Snare drum trigger (noise channel) | high |
| `EA` | none | Closed hi-hat trigger (noise channel) | high |
| `FE XX YY ZZ` | 3 bytes | Repeat: XX=count (FF=infinite), YYZZ=pointer (little-endian) | high |

### Instrument Commands (0x00-0xFF range, context-dependent)

Instrument changes are context-dependent — an instrument byte MUST be preceded
by a tempo change (DX), otherwise it will be interpreted as a note.

```
Instrument byte format:
  High nibble: selects the ADSR envelope type (fade, attack, etc.)
  Low nibble: duty cycle setting (0=harshest, F=smoothest)

  Example: x0 = harshest duty cycle, xF = smoothest
  Each range of 16 employs different ADSR techniques.
```

**IMPORTANT:** Instrument set byte + required preceding tempo byte means the
format is: `DX II` where DX is tempo and II is the instrument number.

## Octave System

| Command | Octave | Description |
|---------|--------|-------------|
| E0 | Highest | High pitched |
| E1 | High | Lower than E0 |
| E2 | Mid | Very low |
| E3 | Low | Barely audible |
| E4 | Silent | Used for drum-only sections |
| E5-E7 | — | Silent (unused) |
| E8 | Highest | Wraps back to highest |

## Noise / Percussion

Drum triggers (E9, EA) follow a note definition that controls their duration:
- `B0 E9` = fast snare hit (B0 = short duration note preceding the trigger)
- `BF E9` = snare followed by long pause

The drum sounds simultaneously with the preceding note. For percussion-only
sections, set octave to E4 (silent) first.

**E9** = snare sound
**EA** = closed hi-hat sound

## Repeat / Loop Structure

```
FE XX YYYY

XX   = repeat count (FF = infinite loop)
YYYY = pointer to loop target (little-endian, CPU address space)
```

### Pointer Conversion (ROM offset <-> CPU address)

```
CPU address to ROM offset:
  1. Swap bytes (little-endian to big-endian): B59D -> 9DB5
  2. Subtract $8000: 9DB5 -> 1DB5
  3. Add $10 (iNES header): 1DB5 -> 1DC5

ROM offset to CPU pointer:
  1. Subtract $10: 1DC5 -> 1DB5
  2. Add $8000: 1DB5 -> 9DB5
  3. Swap bytes: 9DB5 -> B59D
```

## Master Pointer Table

Song pointers are stored as 6-byte groups (3 channels x 2-byte pointer each):
Square 1, Square 2, Triangle. Noise data is embedded via E9/EA triggers
within the melodic channel data.

### Track Pointer Locations (ROM file offsets, hex)

| Track | Sq1 | Sq2 | Tri |
|-------|-----|-----|-----|
| 1 | 825 | 828 | 82B |
| 2 | 82E | 831 | 834 |
| 3 | 837 | 83A | 83D |
| 4 | 840 | 843 | 846 |
| 5 | 849 | 84C | 84F |
| 6 | 852 | 855 | 858 |
| 7 | 85B | 85E | 861 |
| 8 | 864 | 867 | 86A |
| 9 | 86D | 870 | 873 |
| 10 | 876 | 879 | 87C |
| 11 | 87F | 882 | 885 |
| 12 | 888 | 88B | 88E |
| 13 | 891 | 894 | 897 |
| 14 | 89A | 89D | 8A0 |
| 15 | 8A3 | 8A6 | 8A9 |

Note: These are file offsets (not CPU addresses). 15 tracks total.
Track 1 = "Vampire Killer" (Stage 1). Sound effects follow after Track 15.

## Architecture (from Contra disassembly, confidence: high)

### Slot System (6 slots, priority-ordered)
- Slot 0: Pulse 1 (music)
- Slot 1: Pulse 2 (music)
- Slot 2: Triangle (music)
- Slot 3: Noise/DMC (music percussion)
- Slot 4: Pulse 1 (SFX, higher priority)
- Slot 5: Noise (SFX, higher priority)

### Frame Execution
- Every NMI (60Hz), iterate through populated slots
- Decrement `SOUND_CMD_LENGTH` for current sound
- When length expires, advance to next command byte
- SFX slots (4-5) override music slots (0-3) on same channel

### Key Contra Sound Commands (for comparison)
- `$FD XX YY` = branch to child sound command at address XXYY
- `$FE XX YY ZZ` = repeat (same as CV1)
- `$FF` = end of sound code
- Low commands (< $30): SFX (length, decrescendo, pitch, duty)
- High commands (>= $30): Music sequences with volume envelopes

## Open Questions

1. ~~Exact format of note commands?~~ DECODED: high nibble = pitch, low nibble = duration
2. ~~How are octaves set?~~ DECODED: E0-E4 commands
3. ~~What are the drum triggers?~~ DECODED: E9 = snare, EA = hi-hat
4. How does the instrument byte map to specific duty cycle + ADSR envelope?
   (Sliver X says "each range of 16 employs different ADSR techniques" but
   doesn't list the specific envelope tables)
5. Where are the envelope lookup tables stored in ROM?
6. Are there commands between EB-EF or E5-E7 that Sliver X didn't document?
7. How does the noise channel work for non-drum pitched noise?
8. Is there a vibrato or pitch bend command? (Contra has one but CV1 may not)
9. What are the exact tempo multiplier values for D0-DF?

## Evidence Sources

- Sliver X, "Castlevania Music Format v1.0" (2011) — romhacking.net #150 — **high confidence**
- vermiceli, Contra (US) fully annotated disassembly — **high confidence** for architecture
- Data Crystal Castlevania RAM map — **medium confidence** for memory layout
- NESdev forum threads on CV1 music patching — **medium confidence**

## Confidence Summary

| Component | Confidence | Source |
|-----------|-----------|--------|
| Note encoding (pitch+duration in one byte) | 0.9 | Sliver X |
| Octave commands (E0-E4) | 0.9 | Sliver X |
| Tempo commands (D0-DF) | 0.9 | Sliver X |
| Drum triggers (E9, EA) | 0.9 | Sliver X |
| Repeat/loop (FE XX YYYY) | 0.9 | Sliver X |
| Master pointer table locations | 0.9 | Sliver X |
| Instrument byte format | 0.6 | Sliver X (partial — no envelope tables) |
| Slot/priority system | 0.85 | Contra disassembly (same driver family) |
| Commands E5-E8, EB-EF | 0.3 | Undocumented by Sliver X |
| Envelope table locations in ROM | 0.0 | Not yet investigated |
