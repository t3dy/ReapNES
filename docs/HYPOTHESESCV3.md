# CV3 (Castlevania III: Dracula's Curse) — Hypotheses

## ROM Facts (Verified)

| Property | Value |
|----------|-------|
| File size | 393,232 bytes |
| Mapper | **5 (MMC5)** |
| PRG ROM | 16 banks × 16KB = 256KB |
| CHR ROM | 16 banks × 8KB = 128KB |
| Mirroring | Horizontal |
| Battery | No |

## Key Finding: Modified Maezawa Period Table

A **36-entry** period table was found at **three** ROM locations:

| Location | Bank | Bank Offset |
|----------|------|-------------|
| ROM 0x1071B | 4 | 0x070B |
| ROM 0x1471B | 5 | 0x070B |
| ROM 0x3071B | 12 | 0x070B |

The table spans C1 (MIDI 24) through B3 (MIDI 59) — **three full chromatic octaves**.

### Comparison to Maezawa Base Table

9 of 12 base entries match CV1 exactly. Three differ by ±1:

| Note | CV1 (Maezawa) | CV3 | Delta |
|------|---------------|-----|-------|
| E2 | 1357 | 1358 | +1 |
| G2 | 1141 | 1142 | +1 |
| G#2 | 1077 | 1078 | +1 |

**Hypothesis H1**: The CV3 driver is a Maezawa-family variant with minor tuning adjustments and an extended multi-octave table (like CV2, unlike CV1's 12-entry + octave shift).

**Hypothesis H2**: Higher octaves (C4+) are computed at runtime by bit-shifting table values, since the table stops at B3 but the game uses higher pitches.

## Key Finding: Maezawa Note Encoding Confirmed

Music data at ROM 0x00194 (CPU $8184) decodes perfectly as Maezawa format:

```
0x45 = E dur=5    (high nibble = pitch 4 = E)
0x47 = E dur=7
0x36 = D# dur=6   (pitch 3 = D#)
```

This is **identical** to CV1's encoding: `byte = (pitch × 16) + duration_nibble`.

The second channel at ROM 0x002F0 ($82E0) also uses the same encoding:
```
0x08 = C dur=8
0x13 = C# dur=3
0x14 = C# dur=4
```

**Hypothesis H3**: The CV3 US command set is Maezawa-compatible. E0-E4 octave commands, DX instrument commands, FE repeat, FD subroutine, FF end should all work as in CV1.

## Key Finding: Three-Level Pointer Architecture

### Level 1: Song Table (ROM 0x00076, Bank 0)
40 two-byte pointers at CPU $8066. Each points to a song's section table.

### Level 2: Section Tables (ROM 0x00094+)
Each song entry contains **pairs of 16-bit pointers**: (channel1_ptr, channel2_ptr).
8 pairs per song = 8 sections with 2 channels each.

Example (Song 0):
```
Section 0: ch1=$8184  ch2=$82E0
Section 1: ch1=$8187  ch2=$82E2
Section 2: ch1=$8193  ch2=$82EA
...
Section 7: ch1=$81AE  ch2=$8302
```

### Level 3: Note Data (ROM 0x00194+, 0x002F0+)
Maezawa-encoded note bytes in two separate regions:
- $8184-$82DF: Channel 1 data (pulse melody?)
- $82E0-$8400+: Channel 2 data (bass/accompaniment?)

**Hypothesis H4**: The pointer pair structure encodes two channels per section. A third channel (triangle) may have its own pointer chain, or may be implicitly derived.

**Hypothesis H5**: The 40-entry song table at $8066 contains ~15 songs with ~2-3 entries per song (the table may include separate entries for intro, loop, and ending sections).

## Music Data Banks

| Bank | Music Score | E-DX Pairs | Role (Hypothesis) |
|------|------------|------------|-------------------|
| **5** | **470.0** | **182** | Primary music data bank |
| **4** | **355.8** | **133** | Secondary music data bank |
| **13** | 255.2 | 121 | Additional music data |
| **15** | 192.5 | 53 | Fixed bank (driver code + some data) |
| **3** | 185.2 | 18 | Music data (high FE count = many repeats) |
| **12** | 140.3 | 31 | Music data + period table copy |
| **1** | 132.4 | 43 | Music data |
| **10** | 129.7 | 53 | Music data |

**Hypothesis H6**: The sound driver code lives in bank 15 (fixed bank, always mapped to $C000-$FFFF in MMC5). Music data is distributed across banks 0-5 and 10-13, with bank switching at song boundaries.

**Hypothesis H7**: The period table appearing at the same offset (0x070B) in banks 4, 5, and 12 suggests these banks are loaded into the same CPU address range ($8000-$BFFF) at different times. The driver references the table at a fixed CPU address.

## MMC5-Specific Concerns

### Expansion Audio (NOT present in US version)
The US CV3 uses MMC5 but does **not** use MMC5 expansion audio channels. The Japanese version (Akumajou Densetsu, VRC6 mapper) has 2 extra pulse + 1 sawtooth channel. The US version's soundtrack was recomposed for standard APU only.

**Hypothesis H8**: The US CV3 driver handles only 4 standard APU channels (2 pulse, triangle, noise). No expansion audio parsing is needed for the US ROM.

### Banking Model
MMC5 supports multiple PRG banking modes (32KB, 16KB, 8KB). CV3 likely uses 16KB mode:
- $8000-$BFFF: switchable (any of 16 banks)
- $C000-$FFFF: fixed to bank 15

**Hypothesis H9**: Music data bank switching is controlled by the driver in bank 15. Each song's data may span multiple switchable banks, with the driver loading the correct bank before reading note data.

## Comparison: CV3 vs CV1 vs CV2

| Feature | CV1 | CV2 | CV3 US |
|---------|-----|-----|--------|
| Mapper | 0 (NROM) | 1 (MMC1) | 5 (MMC5) |
| Period table | 12 entries | 32 entries | 36 entries |
| Octave handling | E0-E4 commands | Direct index + runtime shift | E0-E4 + extended table (hypothesis) |
| Note encoding | pitch×16 + duration | Table index + duration bits | pitch×16 + duration (confirmed) |
| Pointer structure | Flat (3 ptrs per track) | Phrase library + song sequences | Nested pairs (section table → note data) |
| Command bytes | DX, E0-E4, FE, FD, FF | FB, FE, FF, F0-F7 | DX, E0-E4, FE, FD, FF (Maezawa) |
| Banks | 1 (linear) | 8 (MMC1) | 16 (MMC5) |

## Predicted Difficulty

**MEDIUM**. The note encoding is Maezawa-compatible, which means our existing CV1 parser logic can be adapted. The main challenges are:

1. **Bank switching**: Music data spans multiple banks. Need manifest-driven bank resolution.
2. **Pointer architecture**: Three-level nesting is more complex than CV1's flat table.
3. **DX byte count**: Unknown — could be 2 (CV1), 3/1 (Contra), or something new.
4. **Envelope model**: Unknown — could be parametric (CV1), lookup (Contra), or hybrid.
5. **No disassembly available**: All hypotheses need trace validation.

## Recommended Next Steps

1. **Capture a Mesen trace** of "Beginning" (Stage 1 music, most iconic track)
2. **Verify DX byte count** by finding a DX command in the ROM and counting following bytes
3. **Map the song table** to track names using nesmdb reference renders (all 28 rendered)
4. **Test the Maezawa parser** on CV3 data with address adjustments
5. **Determine envelope model** from trace volume patterns

## Reference Renders Available

28 CV3 tracks rendered from nesmdb data at:
`output/Castlevania_III/wav/nesmdb/cv3_XX_name.wav`

These are ground truth reference audio for ear-matching against game captures.

## Files

| File | Purpose |
|------|---------|
| `extraction/roms/cv3.nes` | CV3 US ROM |
| `output/Castlevania_III/wav/nesmdb/` | 28 reference WAV renders |
| This document | Hypotheses and analysis |
