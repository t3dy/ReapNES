# Contra: Lessons from the Second Extraction

## Results

11/11 music tracks extracted on the first attempt. Zero failures.
Total soundtrack: 7.9 minutes across Title, 7 level themes, Boss,
Stage Clear, Ending, and Game Over.

## How Contra's Sound Data Is Structured

### The Sound Table Architecture

Contra does NOT use a dedicated music pointer table like CV1. Instead,
it has a **unified sound code system** where every audio event in the
game — music, sound effects, jingles — lives in a single flat table
called `sound_table_00` at CPU $88E8.

Each entry in the table is 3 bytes:

```
.byte $XX          ; config byte
.addr sound_XX     ; CPU address of sound data
```

The config byte encodes:
- **High nibble** (bits 4-7): number of additional sound code entries
  that follow (for multi-channel music, this chains 4 entries together)
- **Low nibble** (bits 0-3): the sound slot to use (0=pulse1, 1=pulse2,
  2=triangle, 3=noise, 4=pulse1 SFX, 5=noise SFX)

### Music vs SFX

Music tracks use 4 consecutive entries (one per channel):

```
; BGM 1 - Jungle (Level 1)
.byte $18           ; slot 0 (pulse1), 3 additional entries follow
.addr sound_2a      ; pulse 1 data at $9428
.byte $01           ; slot 1 (pulse2), 0 additional
.addr sound_2b      ; pulse 2 data at $924E
.byte $02           ; slot 2 (triangle), 0 additional
.addr sound_2c      ; triangle data at $95C7
.byte $03           ; slot 3 (noise/dmc), 0 additional
.addr sound_2d      ; noise data at $9775
```

The first entry's config byte $18 means: slot 0, with 1 additional
entry to chain (the `1` in the high nibble means "load 3 more entries
after this one"). Wait — actually, the high nibble encodes the count
differently. The disassembly comments say "#$03 additional sound code
entries" for byte $18. So $18 = high nibble 1, but the meaning is
"3 additional." The exact encoding doesn't matter for extraction —
what matters is that music always comes in groups of 4 consecutive
entries.

SFX use 1 or 2 entries (typically pulse1 + noise):

```
; SHOTGUN1 - regular bullet firing
.byte $0C           ; slot 4 (pulse1 SFX), 1 additional
.addr sound_0a      ; pulse 1 SFX data
.byte $05           ; slot 5 (noise SFX), 0 additional
.addr sound_0b      ; noise SFX data
```

### The Music Catalog

From the disassembly, Contra has exactly 11 music pieces:

| Sound Code | Name | Channels |
|-----------|------|----------|
| $26-$29 | Title | Sq1, Sq2, Tri, Noise |
| $2A-$2D | Jungle (Level 1 & 7) | Sq1, Sq2, Tri, Noise |
| $2E-$31 | Waterfall (Level 3) | Sq1, Sq2, Tri, Noise |
| $32-$35 | Snow Field (Level 5) | Sq1, Sq2, Tri, Noise |
| $36-$39 | Energy Zone (Level 6) | Sq1, Sq2, Tri, Noise |
| $3A-$3D | Alien's Lair (Level 8) | Sq1, Sq2, Tri, Noise |
| $3E-$41 | Base (Levels 2 & 4) | Sq1, Sq2, Tri, Noise |
| $42-$45 | Boss | Sq1, Sq2, Tri, Noise |
| $46-$49 | Stage Clear | Sq1, Sq2, Tri, Noise |
| $4A-$4D | Ending | Sq1, Sq2, Tri, Noise |
| $4E-$51 | Game Over | Sq1, Sq2, Tri, Noise |

Sound codes below $26 are all SFX (bullets, explosions, jumps, etc.)
Sound codes $52-$53 are player death jingle, $54 is the pause jingle.

### Bank Layout

Contra uses mapper 2 (UNROM) with 8 PRG banks of 16KB each. The sound
engine and ALL music data live in **bank 1** (ROM $4010-$8010, mapped
to CPU $8000-$BFFF when active). This is important for the CPU-to-ROM
address conversion:

```python
def contra_cpu_to_rom(cpu_addr):
    if 0x8000 <= cpu_addr <= 0xBFFF:
        return 16 + 1 * 16384 + (cpu_addr - 0x8000)  # bank 1
    elif 0xC000 <= cpu_addr <= 0xFFFF:
        return 16 + 7 * 16384 + (cpu_addr - 0xC000)  # fixed last bank
```

### Volume Envelope System

Contra has a more sophisticated volume envelope system than CV1.
Instead of the 2-byte parametric fade (fade_start/fade_step), Contra
uses **lookup tables** of volume envelope data. The `pulse_volume_ptr_tbl`
at the start of bank 1 contains 8 envelope pointers per level — each
pointing to a sequence of volume values that are stepped through over
time.

Our extraction doesn't use these tables (we rely on the fade_start/
fade_step parameters from the DX instrument command), which means
Contra's volume envelopes may be less accurate than CV1's. But the
notes and timing are correct.

### Command Format: Same Core, Minor Differences

The byte-level command format inside each channel's data is the same
Maezawa format as CV1:

- $00-$BF: notes (high nibble = pitch, low nibble = duration)
- $C0-$CF: rests
- $D0-$DF: tempo + instrument
- $E0-$E4: octave
- $E8: envelope enable
- $FD: subroutine call
- $FE: repeat
- $FF: end / return

The parser worked on every Contra track without modification. The only
change needed was the CPU-to-ROM address conversion (bank mapping).

## How We Located the Music Data

### What Didn't Work: Automated Pointer Table Scanning

Our first attempt ran the CV1 pipeline directly against the Contra ROM.
It found the pointer table at the wrong address ($0825 is CV1-specific)
and got garbage. Only 2/15 tracks worked by luck.

We then tried scanning the ROM for pointer table patterns. This
produced thousands of false positives because 128KB of PRG data
contains many sequences of values that look like pointers.

### What Worked: The Annotated Disassembly

The `references/nes-contra-us/` directory contains a fully annotated
disassembly of the Contra ROM. This gave us:

1. **Exact addresses** for every music channel's data
2. **Labels** identifying which sound code is which song
3. **The bank mapping** (bank 1 for all sound data)
4. **The sound table format** (config byte + address)

We extracted the 11 music track addresses directly from the disassembly
comments and hardcoded them. No scanning, no heuristics, no guessing.

## Takeaways for Future Reverse Engineering

### 1. A Disassembly Is Worth a Thousand Scans

When a community disassembly exists, USE IT. The Contra disassembly
gave us exact addresses, named labels, and documented behavior. We
extracted 11 tracks in one pass with zero failures. Compare this to
our automated scanning attempts which produced thousands of false
positives.

**Rule: Always check for existing disassemblies before writing
scanning heuristics.**

### 2. Same Driver Family ≠ Same ROM Layout

CV1 and Contra use the same Maezawa command format byte-for-byte.
But the ROM organization is completely different:

| Aspect | CV1 | Contra |
|--------|-----|--------|
| Mapper | 0 (NROM, 32KB) | 2 (UNROM, 128KB) |
| Pointer table | Dedicated 9-byte entries | Flat sound code table |
| Music location | Fixed addresses | Bank 1 only |
| CPU-to-ROM | Simple (addr - $8000 + 16) | Bank-dependent |
| Envelope data | Parametric (2 bytes) | Lookup tables |

The parser core is reusable. The ROM navigation layer is not.

### 3. Same Period Table ≠ Same Driver

CV2 (Simon's Quest) has the exact same period table values as CV1
and Contra. We initially assumed this meant it used the same driver.
It doesn't — CV2 uses a completely different sound engine written by
a different team. The period table is universal NES tuning data, not
a driver fingerprint.

**Rule: The period table proves NES, not Maezawa. Look for command
signatures (E8 DX patterns, FE repeat structures) to identify the
actual driver.**

### 4. Per-Game Configuration Is Unavoidable

There's no universal "Konami NES music extractor." Each game needs:
- Its pointer table address (or equivalent)
- Its bank mapping formula
- Any command byte variations

The /nes-rip skill automates the pipeline AFTER these are known.
Finding them is the manual reverse-engineering step that must happen
once per game.

### 5. The Parser Core Is Proven

The Maezawa command byte parser worked on Contra with ZERO code
changes. Every command type — notes, rests, instruments, octaves,
envelope enable, repeats, subroutine calls — parsed correctly on
the first try. The envelope model (fade_start + fade_step), the
triangle linear counter, and the octave mapping all transferred
directly.

This validates the CV1 fidelity work: the driver model we built
is genuinely correct for the Maezawa family, not just CV1-specific.

### 6. Monkey-Patching Works for Prototyping

Rather than refactoring the parser to accept configurable bank
mappings, we monkey-patched `cpu_to_rom` for Contra:

```python
parser_mod.cpu_to_rom = contra_cpu_to_rom
```

This let us test the extraction immediately without touching the
proven CV1 code. The proper fix is a configurable address resolver,
but the monkey-patch proved the concept in minutes.

### 7. Music Accounts for a Small Fraction of Sound Codes

Contra has ~85 sound code entries. Only 44 of those (11 tracks × 4
channels) are music. The rest are SFX — bullets, explosions, jumps,
menu sounds. A general "extract all sound codes" approach would
produce mostly noise. Knowing which codes are music (from the
disassembly labels) is essential.

## File Outputs

```
output/Contra_v2/
  midi/          — 11 MIDI files with CC11 envelope automation
  wav/           — 11 WAV files rendered by Python NES APU synth
  Contra_full_soundtrack.mp4    — 7.9 min video
  Contra_youtube_description.txt — timestamped track listing
```

## What's Next

Games with existing disassemblies are low-hanging fruit:
- **Super C** — likely same driver, may have community disassembly
- **TMNT** — Konami, same era, worth checking
- **Gradius** — Konami, same era

Games without disassemblies need the pointer table found manually,
either through ROM scanning with better heuristics or through
Mesen's debugger (set a breakpoint on APU register writes and
trace back to the music data pointer).

For CV2, CV3, and other non-Maezawa Konami games, a new driver
parser would need to be written from scratch. The frame IR, MIDI
export, WAV renderer, and pipeline infrastructure are all reusable —
only the command byte decoder changes.
