# Metroid Extraction Blooper Reel

## What Happened

On 2026-03-29, we ran `batch_nsf_all.py` to process 19 games through
the NSF→MIDI→REAPER pipeline. Metroid produced 12 tracks with **zero
notes on every channel**. All MIDI files were empty, all WAVs were
silence, and all REAPER projects had no musical content.

## Root Cause: Missing NSF Bankswitch Emulation

The `NsfEmulator` class in `nsf_to_reaper.py` loaded ROM data linearly
starting at the NSF's `load_addr`. This works for games with linear
address space (mapper 0), but **Metroid's NSF uses bankswitch**.

### How NSF Bankswitch Works

The NSF header contains 8 bytes at offset $70-$77 specifying the
initial 4KB page mapping:

```
Metroid:  [5, 5, 5, 5, 5, 5, 5, 5]  ← all 8 slots map to page 5
```

This means:
- $8000-$8FFF → page 5 of ROM data
- $9000-$9FFF → page 5 of ROM data
- ... (all identical)
- $F000-$FFFF → page 5 of ROM data

But Metroid's ROM has **6 pages** (24KB). Pages 0-4 contain the bulk
of the music engine. The initial mapping puts *only* page 5 everywhere
as a starting point — the INIT routine at $A000 then writes to
$5FF8-$5FFF to swap in the correct pages.

### Why Linear Loading Silently Failed

The linear loader did:
```python
for i, byte in enumerate(self.rom_data):
    addr = self.load_addr + i  # $8000 + i
    cpu.memory[addr] = byte
```

This loaded all 24KB starting at $8000, which placed the data
sequentially ($8000-$DFFF). The bankswitch table was ignored entirely.

The INIT routine ran for only **8 CPU cycles** before returning — it
hit `TAX` ($AA) at $A000 (which was the correct byte from page 5),
but the subsequent code tried to read from addresses that should have
had different page data. Without correct page mapping, the init didn't
set up any music state.

The PLAY routine at $B3B4 entered an infinite loop (hitting max cycles
at PC=$C0C0 every frame), never writing to any APU registers.

### Why Zero Notes Instead of Wrong Notes

If the bankswitch mapping had been *partially* correct, we might have
gotten garbled music. Instead, the INIT didn't configure anything, so
PLAY had no state to work with. The APU registers ($4000-$4017) stayed
at zero for all 5400 frames. Zero notes, zero volume, zero everything.

## The Fix

Two changes to `NsfEmulator`:

1. **`_load_rom()`**: For bankswitched NSFs, map 4KB pages according
   to the bankswitch table at $70-$77 instead of loading linearly.

2. **`_install_bankswitch_handler()`**: Wrap the CPU's memory array
   with a proxy that intercepts writes to $5FF8-$5FFF. When the driver
   writes a page number to these registers, immediately swap the
   corresponding 4KB page into the $8000-$FFFF address space.

After the fix, Metroid Brinstar (song 3) produced:
- P1=38 notes, P2=61 notes, Tri=71 notes
- CC11/CC12 automation: 306/421/71 events
- WAV RMS: 10537 (strong signal)

## Games Affected

| Game | Bankswitch Table | Status |
|------|-----------------|--------|
| Metroid | [5,5,5,5,5,5,5,5] | **FIXED** — all slots to page 5, then driver swaps |
| Castlevania 3 US | [0,0,0,0,11,12,10,7] | Needs re-run |
| Castlevania 3 JP | [0,0,0,0,11,12,10,10] | Needs re-run |
| Kirby's Adventure | [0,1,2,3,8,8,8,8] | Needs re-run |
| Legend of Zelda | [0,1,6,0,2,3,4,5] | Needs re-run |
| Ninja Gaiden 1/2/3 | Various | Untested |
| Super Mario Bros 2/3 | Various | Untested |
| Zelda II | [0,1,2,3,4,5,6,7] | Untested |
| Mega Man 2 | [0,1,2,3,4,0,0,0] | Worked by accident (sequential pages matched linear layout) |

## Lesson

**Same emulator ≠ same ROM layout.** This is the NSF-level version of
the same invariant from ROM parsing. The bankswitch table is per-game
metadata that must be respected. The linear loader worked for 60% of
the library because many smaller games don't use bankswitching, but it
silently produced empty output for the rest.

The Deckard boundary analysis correctly classified NSF emulation as
deterministic, but the deterministic code had an unhandled case. This
is a reminder that "deterministic" doesn't mean "correct" — it means
"always wrong in the same way."
