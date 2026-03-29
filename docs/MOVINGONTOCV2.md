# Moving On to Castlevania II

## What Went Wrong on First Attempt

When we ran the CV1 pipeline against Castlevania II, Contra, CV3, and
Super C, we got partial results at best:

| Game | Tracks OK | Failures |
|------|-----------|----------|
| Castlevania II | 7/15 | 6 division-by-zero, 2 empty |
| Castlevania III | 10/15 | 5 division-by-zero |
| Contra | 2/15 | 13 division-by-zero |
| Super C | 9/15 | 6 division-by-zero |

### Root Cause: Hardcoded Pointer Table

The CV1 parser has three hardcoded values that are specific to
Castlevania 1's ROM layout:

```python
POINTER_TABLE_ROM_OFFSET = 0x0825  # where the track pointers live
TRACK_ENTRY_SIZE = 9               # bytes per track entry
NUM_TRACKS = 15                    # how many tracks
```

These values are WRONG for every other ROM. When the parser reads
from $0825 in a different game's ROM, it gets garbage data instead
of music pointers. The "pointers" point to random bytes, and when
those random bytes happen to include a DX command with tempo=0 in
the low nibble, the frame duration calculation does `tempo * (nibble + 1)`
which is `0 * anything = 0`, and later divides by zero.

The tracks that DID work were lucky — the garbage pointers happened
to land on actual music data from the other game, or the first few
bytes at the bogus address happened to form valid commands.

### Why Not Just Change the Offset?

Each game has its pointer table at a different ROM address. Finding
that address requires either:

1. **A disassembly** — look for the code that loads track pointers
2. **ROM scanning** — search for the period table (shared across
   all Maezawa-family games) as an anchor, then look nearby for
   pointer-table-like data
3. **APU trace comparison** — record one track in Mesen, find the
   matching note pattern in the ROM

### Additional Complications

- **Mapper differences**: CV1 uses mapper 0 (NROM, simple linear
  mapping). CV2 uses mapper 1 (MMC1, bank switching). CV3 uses
  mapper 5 (MMC5). This changes how CPU addresses map to ROM offsets.
- **Command variations**: Later games may add new command bytes or
  change the meaning of existing ones.
- **Pointer table format**: The 9-byte-per-entry format with
  separator bytes may differ across games.

## The Plan for CV2

### What We Know

- CV2 uses mapper 1 (MMC1), 8 PRG banks (128KB), 16 CHR banks
- The period table is at ROM $1C2D — same 12 values as CV1 (confirming
  same driver family)
- No Mesen trace needed — the envelope model, fade_step, triangle
  linear counter, and octave mapping are all driver-level and already
  decoded

### What We Need to Find

1. **Pointer table address** — scan the ROM for sequences of valid
   CPU pointers ($8000-$FFFF range) in a plausible grouping pattern
2. **Pointer table format** — confirm whether it uses the same
   9-byte-per-entry format as CV1, or a different layout
3. **Number of tracks** — CV2 has different music from CV1, likely
   a different track count
4. **Bank mapping** — with MMC1, CPU addresses $8000-$BFFF are
   bank-switched, so the cpu_to_rom conversion needs to know which
   bank is active for each pointer

### Investigation Results

**CV2 does NOT use the Maezawa driver.** Despite having the same NES
period table values (which are universal tuning data, not driver-specific),
the ROM contains no Maezawa command signatures:

- Only 10 E8 DX byte sequences found, all in machine code regions
  (E8 = INX in 6502, not an envelope enable command)
- No pointer table matching the 9-byte or 6-byte Maezawa format
- Music data format is completely different

CV2 was developed by a different internal Konami team with a different
composer (Kenichi Matsubara vs Kinuyo Yamashita), which explains the
different driver. CV2 requires its own driver reverse-engineering effort.

### Pivot: Contra First

Contra is a better next target because:
1. We have the **complete annotated disassembly** in references/
2. The disassembly documents the **exact pointer table address** ($86D5)
3. Hidenori Maezawa himself composed the music — it IS the Maezawa driver
4. The command format is identical to CV1

### What's Reusable from CV1

Everything except the ROM entry point:
- Command byte decoder (notes, rests, instruments, octaves, drums)
- Two-phase envelope model (fade_start + fade_step)
- Triangle linear counter gating
- Frame IR generation
- MIDI export with CC11 automation
- WAV renderer
- REAPER project generator
- Full pipeline script and /nes-rip skill

The goal is to make the parser configurable per-game rather than
hardcoded. A game-specific config would just specify:
- Pointer table ROM offset
- Number of tracks
- CPU-to-ROM mapping (for banked mappers)
- Any command byte overrides
