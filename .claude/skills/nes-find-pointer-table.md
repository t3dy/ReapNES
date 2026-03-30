---
name: nes-find-pointer-table
description: Locate the sound table / pointer table in a NES ROM. Uses 2-attempt budget — exact pattern match then relaxed search. If both fail, recommends Mesen debugger breakpoint instead of grinding.
user_invocable: true
---

# NES Pointer Table Finder

Find where the ROM indexes its music tracks.

## When to use

After `/nes-scan-rom` has identified the mapper and (optionally) the period table. The manifest must exist.

## Instructions

### 1. Preconditions
- `extraction/manifests/{game}.json` must exist with mapper field
- ROM must exist at `extraction/roms/{game}.nes`
- RECOMMENDED: trace data exists (for validation)

### 2. Check for reference disassembly FIRST
Search `references/` for an annotated disassembly of this game or a related game with the same driver. If found, READ THE SOUND TABLE FORMAT from the disassembly before searching.

For Maezawa/Contra family: the Contra disassembly at `references/nes-contra-us/` documents sound_table_00 (3-byte triples with slot encoding: 0x18/0x01/0x02/0x03 for BGMs).

### 3. Attempt 1: Exact pattern match
If driver family is known, search for the EXACT control byte pattern from the reference disassembly.
- Contra family: search for 0x18 xx xx 0x01 xx xx 0x02 xx xx 0x03 xx xx
- CV1 family: search for grouped 9-byte records with 3 valid pointers
- Unknown: skip to attempt 2

### 4. Attempt 2: Relaxed structural search
Search for 3-4 consecutive pointer groups where:
- All addresses are valid ($8000-$BFFF), UNIQUE, and ascending
- First target contains E0-E4 octave commands within 16 bytes
- Control bytes (if present) are consistent

### 5. Validate against trace (if available)
For the top candidate: parse the first channel target as Maezawa notes. Compare the resulting pitch sequence to the trace melody. If pitches match (with ±12 semitone octave tolerance): CANDIDATE CONFIRMED.

### 6. If both attempts fail: STOP
Do NOT iterate with increasingly permissive searches.
Instead recommend:
```
POINTER TABLE NOT FOUND after 2 attempts.
RECOMMENDATION: Use Mesen debugger.
  1. Open the game in Mesen2
  2. Set breakpoint on $4002 write (pulse period low byte)
  3. Play until music starts
  4. When breakpoint hits: note the calling code address
  5. The code reads from a table — the table address is in the code
This will find the table in ~30 seconds.
```

### 7. Update manifest
Set pointer_table.address and pointer_table.status:
- If found and validated: status = "verified"
- If found but not validated: status = "candidate"
- If not found: status = "unknown"

### Postconditions
- Manifest pointer_table field updated
- At most 2 search iterations performed

### Hard failures
- Manifest doesn't exist → REFUSE, suggest /nes-scan-rom
- More than 2 search iterations → STOP, recommend debugger
