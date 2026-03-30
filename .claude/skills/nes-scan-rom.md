---
name: nes-scan-rom
description: Analyze a NES ROM file — extract mapper, PRG/CHR size, scan for period tables, command signatures, and music data density per bank. Creates or updates the game manifest with VERIFIED facts only.
user_invocable: true
---

# NES ROM Scanner

Extract verified facts from a NES ROM file.

## When to use

When starting work on a new game, or when the user says "scan the ROM" or "analyze the ROM."

## Instructions

### 1. Preconditions
- ROM must exist at `extraction/roms/{game}.nes`
- If not found, search `AllNESRoms/All NES Roms (GoodNES)/USA/` and copy it

### 2. Header analysis (VERIFIED)
Read iNES header: mapper, PRG banks, CHR banks, mirroring, battery.
These are VERIFIED facts — write directly to manifest.

### 3. Period table scan
Search for:
1. Full Maezawa 12-entry table (struct.pack("<12H", *[1710,1614,1524,1438,1357,1281,1209,1141,1077,1017,960,906]))
2. Contra-variant table (1358,1142,1078 instead of 1357,1141,1077)
3. CV3-variant extended table (36 entries)
4. Any 12 consecutive 16-bit values with semitone ratios (1.04-1.08)

If found: record address, format, tuning, entry count. Status = VERIFIED.
If not found: status = NOT_FOUND. Do NOT guess.

### 4. Command signature scan (per bank)
For each PRG bank, count: E0-E4 (octave), D0-DF (instrument), FE (repeat), FD (subroutine).
Compute music density score. Report top 3 banks.

### 5. Music data density
Identify which banks likely contain music data vs code vs graphics.

### 6. Create/update manifest
Write `extraction/manifests/{game}.json` with all VERIFIED fields.
Mark all unscanned fields as "UNKNOWN" — never guess.

### Postconditions
- Manifest exists with mapper, prg_banks, period_table fields
- All fields have explicit status (VERIFIED / NOT_FOUND / UNKNOWN)

### Hard failures
- ROM file not found → STOP
- iNES header invalid (missing "NES\x1A" magic) → STOP

### What NOT to do
- Do NOT predict driver family from publisher or year
- Do NOT write hypothesis documents
- Do NOT search for pointer tables (that's /nes-find-pointer-table)
- Do NOT attempt to parse music data
