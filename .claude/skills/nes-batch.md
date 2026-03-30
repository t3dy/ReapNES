---
name: nes-batch
description: Parse all tracks from a ROM and render MIDI, WAV, and REAPER projects. REFUSES to run unless /nes-validate has passed first. This is the final extraction step.
user_invocable: true
---

# NES Batch Extract

Parse all tracks and produce the complete soundtrack package.

## When to use

After `/nes-validate` has PASSED. User says "extract all" or "batch extract."

## Instructions

### 1. Preconditions — MANDATORY GATE
- Manifest must have pointer_table.status = "verified"
- Manifest must have at least one track in tracks_extracted with validated_against_trace = true
- Manifest status must be "validated" or later

If ANY condition fails: REFUSE TO RUN. Print:
```
BATCH EXTRACTION BLOCKED.
Reason: {specific missing condition}
Run /nes-validate first to pass the one-track gate.
```

### 2. Parse all tracks
Using the validated parser configuration from the manifest:
- Parse every track referenced by the pointer table
- Export each as MIDI with CC11 volume automation
- Generate REAPER .rpp projects

### 3. Render WAVs
Render each track using the Python NES APU synth.

### 4. Output structure
```
output/{GameName}/midi/{game}_track_{NN}_{name}.mid
output/{GameName}/wav/{game}_track_{NN}_{name}_v1.wav
output/{GameName}/reaper/{game}_track_{NN}_{name}_v1.rpp
output/{GameName}/{game}_youtube_description.txt
```

### 5. Version control
- Check for existing files. NEVER overwrite.
- If v1 exists, create v2. If v2 exists, create v3.
- Report which version was created.

### 6. Report
```
Extracted {N} tracks:
  01: {name} — MIDI ✓ WAV ✓ RPP ✓ ({duration}s)
  02: {name} — MIDI ✓ WAV ✓ RPP ✓ ({duration}s)
  ...
  {M}: {name} — FAILED: {error}

Total duration: {sum}s
Output version: v{N}
YouTube description: {path}
```

### 7. Update manifest
Set status = "complete", update tracks_extracted array.

### Postconditions
- All successfully parsed tracks have MIDI + WAV + RPP files
- YouTube description generated
- Manifest status = "complete"

### Hard failures
- Validation gate not passed → REFUSE
- Parser crash on a track → skip that track, continue others, report failure
