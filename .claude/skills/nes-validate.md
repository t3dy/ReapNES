---
name: nes-validate
description: Parse one track from ROM and compare to Mesen APU trace. This is the GATE — batch extraction cannot proceed until this passes. Refuses to run without both a trace and a pointer table.
user_invocable: true
---

# NES Single Track Validation

Parse one track and validate against trace. This is the mandatory gate.

## When to use

After `/nes-find-pointer-table` has a candidate or verified pointer table, AND a trace exists. User says "validate" or "test one track."

## Instructions

### 1. Preconditions — ALL REQUIRED, NO EXCEPTIONS
- `extraction/manifests/{game}.json` must exist
- Manifest must have pointer_table.address (verified or candidate)
- Trace CSV must exist in `extraction/traces/{game}/`
- User must have identified which track the trace contains

If ANY is missing: print what's missing and REFUSE TO RUN.

### 2. Parse one track
Using the appropriate parser (Maezawa/Contra variant based on manifest driver_family):
- Read pointer table at the manifest address
- Parse the track that matches the user-identified trace capture
- Extract note events with pitch, duration, volume

### 3. Compare to trace
Frame-by-frame comparison:
- Pitch: period from parser vs period from trace. Match if within ±2 (vibrato tolerance).
- Volume: parsed volume vs trace volume. Match if within ±1.
- Sounding: parsed "note on" vs trace "volume > 0".

### 4. Report
```
Track: {name}
Frames compared: {N}
Pitch matches: {match}/{total} ({pct}%)
Volume matches: {match}/{total} ({pct}%)
Sounding matches: {match}/{total} ({pct}%)

First mismatch: frame {N}, channel {ch}
  Expected (trace): period={p}, vol={v}
  Got (parser):     period={p}, vol={v}
```

### 5. Verdict
- Pitch >= 95%: PASS
- Pitch 80-95%: CLOSE — investigate mismatches
- Pitch < 80%: FAIL — wrong pointer table or wrong parser

Ask user to listen to both the trace render and the parsed render.
User gives final verdict: PASS / FAIL.

### 6. Update manifest
If PASS: set pointer_table.status = "verified", add track to tracks_extracted with validated_against_trace = true.

### Postconditions
- Validation report printed
- User has given PASS/FAIL verdict
- Manifest updated

### Hard failures
- No trace → REFUSE. Print: "Cannot validate without a trace. Run /nes-capture first."
- No pointer table → REFUSE. Print: "Cannot validate without a pointer table. Run /nes-find-pointer-table first."
- Parser crashes → Report the error, do NOT mark as validated
