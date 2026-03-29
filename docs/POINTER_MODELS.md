# NES Sound Driver Pointer and Memory Addressing Models

Reference catalog for pointer table structures and address resolution
across NES mapper types. Written for the NES Music Studio pipeline,
which must convert CPU addresses found in ROM pointer tables into
file offsets for parsing music data.

---

## Background: NES Address Space

The NES CPU (6502) has a 16-bit address bus (64KB). Program ROM (PRG)
is mapped into $8000-$FFFF (32KB). Games larger than 32KB use mapper
hardware to swap banks of ROM into that window. The interrupt vectors
(RESET, NMI, IRQ) live at $FFFA-$FFFF, so the bank containing those
vectors must always be accessible — this is the "fixed" bank.

All pointer tables in NES sound drivers store **CPU addresses** (the
values the 6502 sees at runtime), not ROM file offsets. The extraction
pipeline must convert these CPU addresses to ROM file offsets, which
requires knowing:

1. Which mapper the game uses
2. Which bank is active when the sound engine reads the pointer
3. How banks map to positions in the ROM file

The iNES header (16 bytes at offset 0) precedes all PRG data. Every
ROM offset calculation must account for this header.

---

## Mapper 0 — NROM (Linear)

### Layout

- PRG size: 16KB or 32KB (1-2 banks)
- No bank switching — the entire PRG is visible at once
- 16KB ROM: mirrored at $8000-$BFFF and $C000-$FFFF
- 32KB ROM: $8000-$FFFF maps linearly to the full PRG

### Pointer Table Structure

Pointer tables contain absolute 16-bit CPU addresses. Each pointer
maps directly to a single location in ROM.

### Address Resolution

```
rom_offset = cpu_addr - 0x8000 + 16
```

The `+ 16` accounts for the iNES header. That is the entire formula.
For 16KB ROMs, addresses in $C000-$FFFF should subtract $C000 instead
(or equivalently, mask with $3FFF).

### Project Usage

CV1 uses this model despite the ROM being mapper 2 (UNROM). The
pointer table and all music data happen to reside in the portion of
ROM that maps as if it were linear. The manifest declares
`"resolver_method": "linear"` and the parser uses the simple
`cpu_to_rom()` function:

```python
def cpu_to_rom(cpu_addr: int) -> int:
    return cpu_addr - 0x8000 + INES_HEADER_SIZE
```

### Failure Modes

- Forgetting the 16-byte iNES header offset (off by 16 bytes)
- Applying bank-switching math to a mapper 0 ROM (unnecessary)
- For 16KB ROMs: not handling the mirror at $C000

### Games

Early/small NES titles: Balloon Fight, Donkey Kong, Ice Climber,
Excitebike, many early Famicom titles.

---

## Mapper 2 — UNROM (Bank-Switched, 16KB Window)

### Layout

- PRG size: 64KB-256KB (4-16 banks of 16KB each)
- $8000-$BFFF: switchable bank (any of the N banks)
- $C000-$FFFF: fixed to the **last** bank (bank N-1)
- Bank select: write to any address in $8000-$FFFF

### Pointer Table Structure

Same as mapper 0 — 16-bit CPU addresses. The critical difference is
that addresses in $8000-$BFFF refer to **whichever bank is active**
when the sound engine executes. The sound engine itself typically
resides in the fixed bank ($C000-$FFFF) and swaps in the data bank
before reading music data.

### Address Resolution

Two cases, depending on whether the CPU address falls in the
switchable or fixed region:

```
if 0x8000 <= cpu_addr <= 0xBFFF:
    # Switchable bank — must know which bank is active
    rom_offset = 16 + (sound_bank * 16384) + (cpu_addr - 0x8000)

elif 0xC000 <= cpu_addr <= 0xFFFF:
    # Fixed bank — always the last bank
    rom_offset = 16 + ((num_banks - 1) * 16384) + (cpu_addr - 0xC000)
```

### Project Usage

Contra uses this model. All sound engine code and music data reside
in bank 1 (the second 16KB block). The manifest declares
`"resolver_method": "bank_switched"` with `"sound_bank": 1`. The
parser has a dedicated function:

```python
def contra_cpu_to_rom(cpu_addr: int) -> int:
    if 0x8000 <= cpu_addr <= 0xBFFF:
        return INES_HEADER_SIZE + SOUND_BANK * BANK_SIZE + (cpu_addr - 0x8000)
    elif 0xC000 <= cpu_addr <= 0xFFFF:
        return INES_HEADER_SIZE + (NUM_PRG_BANKS - 1) * BANK_SIZE + (cpu_addr - 0xC000)
```

### Failure Modes

- **Wrong bank assumption**: assuming bank 0 when data is in bank 1
  (or vice versa). This shifts every pointer by 16KB, producing
  garbage data. This is the single most common failure when porting
  a parser to a new UNROM game.
- **Ignoring the fixed bank**: pointers into $C000-$FFFF always
  resolve to the last bank. Using the switchable bank formula
  produces the wrong offset.
- **PRG bank count mismatch**: the iNES header declares the bank
  count. If the ROM image has extra trainer data (512 bytes) and
  you forget to account for it, every offset shifts.
- **Subroutine/repeat targets in wrong bank**: FD/FE commands embed
  CPU addresses that jump within the music data. If the sound engine
  switches banks between the pointer table read and the data read,
  the embedded addresses could refer to a different bank than
  expected. Most drivers avoid this by keeping all music in one bank.

### Games

Castlevania (data is linear but mapper is 2), Contra, Mega Man,
DuckTales, Metal Gear, many Konami and Capcom titles.

---

## Mapper 1 — MMC1 (Nintendo)

### Layout

- PRG size: up to 256KB (16 banks of 16KB)
- Two switchable configurations (set via control register):
  - Mode 2: fix first bank at $8000, switch $C000 (uncommon)
  - Mode 3: switch $8000, fix last bank at $C000 (most common)
- Bank select via serial interface (5 writes to shift register)

### Pointer Table Structure

Same 16-bit CPU addresses. The complication is that the fixed bank
can be at either end depending on the control register setting. Most
games use mode 3 (fixed last bank), which behaves identically to
mapper 2 from the address resolution perspective.

### Address Resolution

Identical to mapper 2 in mode 3 (most games):

```
if 0x8000 <= cpu_addr <= 0xBFFF:
    rom_offset = 16 + (sound_bank * 16384) + (cpu_addr - 0x8000)
elif 0xC000 <= cpu_addr <= 0xFFFF:
    rom_offset = 16 + ((num_banks - 1) * 16384) + (cpu_addr - 0xC000)
```

In mode 2 (fixed first bank):

```
if 0x8000 <= cpu_addr <= 0xBFFF:
    rom_offset = 16 + 0 + (cpu_addr - 0x8000)  # always bank 0
elif 0xC000 <= cpu_addr <= 0xFFFF:
    rom_offset = 16 + (sound_bank * 16384) + (cpu_addr - 0xC000)
```

Some games use 32KB mode (both halves switch together). In that case
the bank number refers to a 32KB unit and both $8000-$BFFF and
$C000-$FFFF are the same contiguous block.

### Failure Modes

- **Not knowing the switching mode**: mode 2 vs mode 3 reverses
  which half is fixed. Guessing wrong means the fixed bank resolves
  to the wrong ROM offset.
- **32KB mode**: treating it as two 16KB halves with separate bank
  numbers produces wrong offsets.
- **Serial register state**: the bank select requires 5 sequential
  writes. Static analysis of the ROM can determine the mode from
  the init routine, but it is not always obvious.

### Games

The Legend of Zelda, Metroid, Kid Icarus, Blaster Master,
Castlevania II (which uses MMC1 and a non-Maezawa sound driver),
many early-to-mid NES era titles. Zelda uses mode 2 (fixed first
bank) which is the less common configuration.

---

## Mapper 4 — MMC3 (Nintendo)

### Layout

- PRG size: up to 512KB (32 banks of 8KB)
- Four 8KB windows in the CPU map:
  - $8000-$9FFF and $A000-$BFFF: two independently switchable banks
  - $C000-$DFFF: fixed to second-to-last bank
  - $E000-$FFFF: fixed to last bank
- Variant: the two switchable windows can be swapped with the two
  fixed windows via a control bit

### Pointer Table Structure

Still 16-bit CPU addresses, but pointer table entries and music data
may span different 8KB banks. A single track's data could cross an
8KB boundary, meaning the resolver must handle mid-parse bank
transitions.

### Address Resolution

With four 8KB regions, resolution requires mapping each region:

```
# For the common configuration (switchable low, fixed high):
if 0x8000 <= cpu_addr <= 0x9FFF:
    rom_offset = 16 + (bank_8000 * 8192) + (cpu_addr - 0x8000)
elif 0xA000 <= cpu_addr <= 0xBFFF:
    rom_offset = 16 + (bank_A000 * 8192) + (cpu_addr - 0xA000)
elif 0xC000 <= cpu_addr <= 0xDFFF:
    rom_offset = 16 + ((num_8k_banks - 2) * 8192) + (cpu_addr - 0xC000)
elif 0xE000 <= cpu_addr <= 0xFFFF:
    rom_offset = 16 + ((num_8k_banks - 1) * 8192) + (cpu_addr - 0xE000)
```

### Failure Modes

- **Data spanning an 8KB boundary**: if a track's command stream
  starts at $9F00 and runs past $A000, the second half is in a
  different 8KB bank. The parser must detect this boundary and
  resolve the continuation correctly.
- **Swapped configuration**: the control bit can swap which pair of
  windows is fixed vs switchable. If you assume the wrong config,
  the fixed bank offsets are wrong.
- **Two switchable banks**: the sound engine may set bank_8000 and
  bank_A000 independently. You need to know both values, not just
  one.
- **IRQ-based bank switching**: MMC3 has a scanline counter used
  for CHR, but some games use creative timing that could affect
  PRG banking mid-frame. Rare for sound but possible.

### Games

Super Mario Bros. 3, Kirby's Adventure, Mega Man 3-6, many
late-era NES games. This is the most common mapper for licensed
NES games with larger ROMs.

---

## Mapper 5 — MMC5 (Nintendo)

### Layout

- PRG size: up to 1MB (64 banks of 16KB, or 128 of 8KB)
- Extremely flexible banking: supports four different PRG modes
  - Mode 0: one 32KB switchable bank
  - Mode 1: two 16KB banks (one switchable, one fixed)
  - Mode 2: one 16KB + two 8KB banks
  - Mode 3: four 8KB banks (maximum granularity)
- 1KB of on-cartridge RAM at $5C00-$5FFF (ExRAM)
- Expansion audio: two extra pulse channels + PCM

### Pointer Table Structure

Same 16-bit CPU addresses, but the extreme banking flexibility means
that determining which ROM data backs a given CPU address requires
knowing the PRG mode and all active bank register values. Some games
store sound data in ExRAM or use it as a scratch buffer.

### Address Resolution

Depends entirely on the PRG mode. For mode 1 (most common for games
with expansion audio):

```
if 0x8000 <= cpu_addr <= 0xBFFF:
    rom_offset = 16 + (switchable_bank * 16384) + (cpu_addr - 0x8000)
elif 0xC000 <= cpu_addr <= 0xFFFF:
    rom_offset = 16 + (fixed_bank * 16384) + (cpu_addr - 0xC000)
```

For mode 3 (four 8KB banks), resolution is similar to MMC3 but with
four independently switchable windows.

### Challenges for Extraction

- **Expansion audio channels**: MMC5 adds two pulse channels and a
  PCM channel. The sound driver has 5-7 channels instead of 4. The
  pointer table may have entries for the extra channels, changing
  the entry size and count.
- **ExRAM as workspace**: some drivers copy decompressed music data
  into ExRAM ($5C00-$5FFF) before playback. The pointer table may
  contain ExRAM addresses that do not map to any ROM offset.
- **PRG mode uncertainty**: without tracing the init code, you may
  not know which PRG mode the game uses.
- **Multiple bank registers**: in mode 3, four different bank values
  must be determined. Static analysis of the ROM is insufficient;
  you need to trace execution or find the bank-setup routine.

### Failure Modes

- **Assuming mode 1 when game uses mode 3**: off by a factor of 2
  in bank size, wrong offsets for everything.
- **ExRAM addresses**: pointer tables referencing $5C00-$5FFF cannot
  be resolved to ROM offsets — the data is generated at runtime.
- **Expansion channel pointers**: parsing a 3-channel pointer table
  when there are 5 channels causes misalignment.

### Games

Castlevania III (the primary reason this project cares about MMC5),
Uncharted Waters, Laser Invasion, Romance of the Three Kingdoms II,
and a handful of other late-era Konami titles.

---

## Expansion Audio Mappers

These mappers add audio hardware on the cartridge, producing channels
beyond the base NES APU. They are relevant because the sound driver
must manage extra channels, changing pointer table layout.

### VRC6 — Mapper 24/26 (Konami)

- **Extra audio**: two pulse channels + one sawtooth
- **Banking**: 16KB + 8KB + 8KB switchable, 8KB fixed
- **Pointer tables**: entries for 7 channels (4 APU + 3 expansion)
- **Address resolution**: similar to MMC3 with mixed bank sizes.
  $8000-$BFFF is one 16KB switchable bank. $C000-$DFFF and
  $E000-$FFFF are two 8KB banks (one switchable, one fixed).
- **Games**: Castlevania III (Japan, Akumajou Densetsu), Madara,
  Esper Dream 2
- **Note**: the Japanese CV3 uses VRC6 while the US version uses
  MMC5. Same game, different mappers, different expansion audio,
  different pointer table layouts.

### VRC7 — Mapper 85 (Konami)

- **Extra audio**: 6-channel FM synthesis (OPLL-derived)
- **Banking**: similar to VRC6 with 8KB switchable banks
- **Pointer tables**: entries for up to 10 channels (4 APU + 6 FM)
- **Address resolution**: three 8KB switchable banks at $8000-$DFFF,
  one 8KB fixed at $E000-$FFFF.
- **Games**: Lagrange Point (only game to use VRC7 audio)

### Namco 163 (N163)

- **Extra audio**: up to 8 wavetable channels
- **Banking**: 8KB switchable banks, complex register layout
- **Pointer tables**: highly game-specific; some games use all 8
  extra channels, others only a few
- **Games**: King of Kings, Erika to Satoru no Yume Bouken,
  Megami Tensei II

### FDS (Famicom Disk System)

- **Extra audio**: one wavetable channel
- **Memory model**: entirely different — no ROM mapper, uses RAM
  loaded from disk. Addresses are direct RAM addresses.
- **Pointer tables**: point into RAM ($6000-$DFFF), no bank
  switching needed but offsets depend on the disk image format
  (FDS header + side data).
- **Games**: Zelda no Densetsu, Metroid (Japan), Doki Doki Panic,
  many Famicom-exclusive titles

---

## Quick Reference Table

| Mapper | Name | Bank Size | Windows | Fixed Bank | Example Games | Resolver Strategy |
|--------|------|-----------|---------|------------|---------------|-------------------|
| 0 | NROM | N/A | 1x 32KB | All | Balloon Fight | `cpu - 0x8000 + 16` |
| 1 | MMC1 | 16KB | 2x 16KB | Last (mode 3) or First (mode 2) | Zelda, CV2, Metroid | Same as mapper 2 (mode 3) |
| 2 | UNROM | 16KB | 2x 16KB | Last | Contra, Mega Man, CV1 | `bank * 16384 + (cpu - 0x8000) + 16` |
| 3 | CNROM | N/A (CHR only) | 1x 32KB PRG | All | Gradius, Arkanoid | Same as mapper 0 |
| 4 | MMC3 | 8KB | 4x 8KB | Last two | SMB3, Kirby, MM3-6 | Per-window bank lookup |
| 5 | MMC5 | 8/16/32KB | 1-4 windows | Mode-dependent | CV3 (US) | Requires PRG mode + all bank regs |
| 7 | AxROM | 32KB | 1x 32KB | None (all switch) | Battletoads, Marble Madness | `bank * 32768 + (cpu - 0x8000) + 16` |
| 24/26 | VRC6 | 16/8KB | Mixed | Last 8KB | CV3 (JP), Madara | Per-window, 3 different sizes |
| 85 | VRC7 | 8KB | 4x 8KB | Last 8KB | Lagrange Point | Similar to MMC3 |

---

## Implications for Our Pipeline

### What the Address Resolver Must Support

1. **Linear resolution** (mapper 0, CNROM, and cases like CV1 where
   data is in a predictable location): single formula, no bank state.

2. **Single-bank resolution** (UNROM, MMC1 mode 3): the manifest
   declares `sound_bank` and the resolver applies the bank offset.
   This covers most Konami games.

3. **Multi-window resolution** (MMC3, MMC5 mode 3, VRC6): the
   resolver must know which 8KB (or mixed-size) bank is active for
   each CPU address window. The manifest would need a `bank_map`
   field listing the bank number for each window.

4. **Expansion channel awareness**: for mappers with extra audio
   hardware, the parser must know the total channel count to
   correctly parse the pointer table.

### Manifest Schema Implications

The current manifest has `resolver_method` as either `"linear"` or
`"bank_switched"` with a `sound_bank` field. To support more mappers:

```json
{
  "rom_layout": {
    "mapper": 4,
    "resolver_method": "multi_window",
    "bank_map": {
      "8000": 5,
      "A000": 6,
      "C000": "fixed_second_to_last",
      "E000": "fixed_last"
    },
    "prg_bank_size": 8192,
    "prg_banks": 32
  }
}
```

### Resolver Function Design

A general-purpose resolver could dispatch on `resolver_method`:

- `"linear"` -> `cpu - 0x8000 + 16`
- `"bank_switched"` -> switchable/fixed split with one bank number
- `"multi_window"` -> per-window bank lookup from `bank_map`

Each game's parser should call through the resolver, never hardcode
the formula. The current codebase has `cpu_to_rom()` (linear) and
`contra_cpu_to_rom()` (bank-switched) as separate functions; a
unified resolver dispatching on the manifest would prevent the need
for per-game address functions.

---

## Failure Risks If Misunderstood

### Wrong Bank = Wrong Data (Silent Corruption)

If the resolver picks the wrong bank, every pointer resolves to a
valid but incorrect ROM offset. The parser will read bytes, decode
them as commands, and produce output that looks plausible but is
completely wrong musically. There is no error or crash — just garbage
notes. This is the most dangerous failure mode because it passes all
automated validation (the parser does not know the notes are wrong).

**Mitigation**: always verify the first parsed track by ear against
the game before batch extraction.

### Trainer Bytes Shift Everything

Some ROMs have a 512-byte "trainer" section between the iNES header
and PRG data (indicated by bit 2 of header byte 6). If present and
not accounted for, every ROM offset is shifted by 512 bytes.

**Mitigation**: check `rom[6] & 0x04` and add 512 to the header
offset if set.

### iNES 2.0 Header Differences

NES 2.0 headers encode mapper numbers and bank counts differently
in bytes 8-15. If the ROM uses NES 2.0 format and the parser assumes
iNES 1.0, the mapper number or bank count could be wrong.

**Mitigation**: check for NES 2.0 signature (bits 2-3 of byte 7 ==
0b10) and parse accordingly.

### Subroutine Targets Across Banks

FD (subroutine call) and FE (repeat) commands embed CPU addresses.
If the target is in a different bank than the caller, the resolver
must switch banks before following the pointer. Most sound drivers
keep all music in one bank to avoid this, but it is not guaranteed.

**Mitigation**: the manifest should declare whether music data spans
multiple banks. If it does, the parser must track bank switches
during command parsing.

### MMC5 ExRAM Addresses Are Unresolvable

If a pointer table entry contains an address in $5C00-$5FFF (MMC5
ExRAM), it refers to data generated at runtime and cannot be
extracted from the ROM image alone. This requires emulator-assisted
extraction (run the game, dump RAM at the right moment).

**Mitigation**: detect ExRAM addresses and flag them. For CV3
extraction, this may require a hybrid approach: ROM extraction for
static data, emulator trace for dynamic data.

---

## Per-Game Checklist for Address Resolution

Before writing a resolver for a new game:

1. Read mapper number from iNES header bytes 6-7
2. Determine PRG bank count and size from header byte 4
3. Check for trainer (header byte 6, bit 2)
4. Find the sound engine's bank-setup routine in the disassembly
5. Identify which bank(s) contain music data
6. Determine the fixed bank configuration (last, first, or none)
7. Record all findings in the manifest's `rom_layout` section
8. Test with ONE track pointer: manually compute the ROM offset,
   read 16 bytes at that offset, verify they look like valid
   sound commands (DX, note bytes, E-series, FE/FF)
