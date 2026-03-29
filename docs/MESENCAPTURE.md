# Mesen APU Trace Capture — Workflow Guide

## Overview

The same Lua script (`docs/mesen_scripts/mesen_apu_capture.lua`)
works for any NES game. It polls decoded APU state once per frame
(no register-write hooks, zero audio interference) and outputs a
CSV that our pipeline can compare against the extracted frame IR.

This is the single most valuable step in the fidelity pipeline.
It turns "sounds close" into "verified correct" by giving frame-level
ground truth for pitch, volume, duty cycle, and sounding state.

## What You Need

- **Mesen 2** (the emulator — not Mesen 1, the Lua API is different)
- **The ROM** (e.g., Contra (U) [!].nes)
- **The Lua script**: `docs/mesen_scripts/mesen_apu_capture.lua`

## Step-by-Step Capture

### 1. Open Mesen 2 and load the ROM

File → Open → select the ROM. Let the game boot to the title screen.

### 2. Load the Lua script

- Go to **Tools → Script Window** (or Debug → Script Window,
  depending on Mesen version)
- Click **Open** (folder icon) and select:
  `C:\Dev\NESMusicStudio\docs\mesen_scripts\mesen_apu_capture.lua`
- Click **Run** (play icon)
- You should see in the script log:

```
==============================================
 NES Music Lab — APU Capture v7 (state poll)
==============================================

 [  = Start capture
 ]  = Stop capture and save
 \  = Check status

 Output: C:\Users\PC\Documents\Mesen2\capture.csv

 Ready. Press [
==============================================
```

### 3. Navigate to the music you want to capture

- For Contra Jungle: start the game, begin Level 1. Wait for the
  music to start. You want to capture from the very first note.
- For Castlevania Vampire Killer: start the game, begin Stage 1.

**Tip**: Pause the game right before the music starts (Mesen
pause, not game pause). This lets you start capture at the exact
right moment.

### 4. Start capture

- Make sure the **Mesen game window** has focus (not the script
  window) — keyboard controls only work when the game window is
  focused.
- Press **`[`** (left square bracket) on your keyboard.
- The script log shows: `CAPTURE STARTED at frame NNNN`
- Unpause if you paused.

### 5. Let the music play

- Let it run for the full song loop (or however much you need).
- For a first capture, one full loop is enough. Contra Jungle
  loops after about 51 seconds (~3072 frames).
- Press **`\`** (backslash) anytime to check status:
  `CAPTURING: 8432 changes, 2100 frames (35.0s)`

### 6. Stop capture and save

- Press **`]`** (right square bracket).
- The script log shows:

```
======================================
 CAPTURE STOPPED
 14817 state changes
 3072 frames
 51.2 seconds
======================================

 SAVED: C:\Users\PC\Documents\Mesen2\capture.csv
```

### 7. Copy the CSV to the project

The script always writes to `C:\Users\PC\Documents\Mesen2\capture.csv`
(overwriting any previous capture). Copy it to the project's trace
directory:

```bash
# Contra
mkdir -p extraction/traces/contra
cp /c/Users/PC/Documents/Mesen2/capture.csv extraction/traces/contra/jungle.csv

# Castlevania (already done)
# extraction/traces/castlevania/stage1.csv
```

### 8. Validate against our extraction

For Contra, we'll need a comparison script (currently
`trace_compare.py` is hardcoded for CV1). Once in place:

```bash
PYTHONPATH=. python scripts/trace_compare.py --game contra --track jungle --frames 3072
```

For now, you can dump raw trace data to inspect manually:

```bash
PYTHONPATH=. python scripts/trace_compare.py --dump-frames 0-20 --channel pulse1
```

## CSV Format

The output CSV has three columns:

```csv
frame,parameter,value
1,$4000_duty,2
1,$4000_vol,6
1,$4002_period,359
6,$4000_vol,7
```

- **frame**: relative frame number (0 = first frame of capture)
- **parameter**: pseudo-register address (see table below)
- **value**: decoded numeric value

Only changes are logged (if a value stays the same frame to frame,
it's not repeated). This keeps the file small — typically 10-20K
lines for a full song.

### Parameter Reference

| Parameter | NES Register | Meaning |
|-----------|-------------|---------|
| `$4000_duty` | $4000 bits 7-6 | Pulse 1 duty cycle (0-3) |
| `$4000_vol` | $4000 bits 3-0 | Pulse 1 volume (0-15) |
| `$4000_const` | $4000 bit 4 | Pulse 1 constant volume flag |
| `$4001_sweep` | $4001 | Pulse 1 sweep enabled |
| `$4002_period` | $4002-$4003 | Pulse 1 timer period (0-2047) |
| `$4004_duty` | $4004 bits 7-6 | Pulse 2 duty cycle (0-3) |
| `$4004_vol` | $4004 bits 3-0 | Pulse 2 volume (0-15) |
| `$4004_const` | $4004 bit 4 | Pulse 2 constant volume flag |
| `$4005_sweep` | $4005 | Pulse 2 sweep enabled |
| `$4006_period` | $4006-$4007 | Pulse 2 timer period (0-2047) |
| `$400A_period` | $400A-$400B | Triangle timer period (0-2047) |
| `$4008_linear` | $4008 | Triangle linear counter |
| `$400B_length` | $400B | Triangle length counter |
| `$400C_vol` | $400C bits 3-0 | Noise volume (0-15) |
| `$400C_const` | $400C bit 4 | Noise constant volume flag |
| `$400E_period` | $400E bits 3-0 | Noise timer period (0-15) |
| `$400E_mode` | $400E bit 7 | Noise mode (0=long, 1=short) |
| `$4010_rate` | $4010 | DMC timer period |
| `$4011_dac` | $4011 | DMC DAC output level (0-127) |
| `$4012_addr` | $4012 | DMC sample address |
| `$4013_len` | $4013 | DMC sample length |

## What the Trace Captures (and What It Doesn't)

### Captured
- Per-frame decoded APU state for all 5 channels
- Volume after hardware envelope processing (the actual value
  written to the DAC, not the register configuration)
- Period after sweep unit modifications
- Triangle linear counter state (critical for gating)
- Noise channel mode and period (needed for kick drum modeling)
- DMC output level (shows sample playback waveform)

### Not Captured
- CPU register state or memory
- Which sound engine code ran this frame
- ROM bank switching
- Which music command triggered a change

The trace is pure hardware output. That's the point — it tells us
what the NES actually produced, regardless of how the sound engine
got there.

## Workflow History

### Castlevania 1 (complete)

**Trace**: `extraction/traces/castlevania/stage1.csv`
**Track**: Vampire Killer (Stage 1), captured from music start
**Start frame offset**: 111 (music begins at frame 111 in capture)
**Duration**: 1792 frames (~30 seconds, full loop)

**How it was captured**: Loaded CV1 ROM, started Stage 1, ran the
capture script, let Vampire Killer play through one full loop.

**Results**: Zero pitch mismatches across all 1792 frames. 45/50
volume mismatches on pulse channels (envelope edge cases). This
trace validated the entire CV1 extraction pipeline and caught the
octave mapping bug that automated tests missed.

**Key lesson**: The trace caught that pulse notes were 12 semitones
too low despite the `trace_compare.py` mismatch count showing zero
pitch errors — because the comparison at the time was using period
values, not MIDI notes. The tool was fixed and the octave mapping
corrected. Always verify that the comparison tool itself is
comparing the right thing.

### Contra (needed)

**Trace**: not yet captured
**Track**: Jungle (Level 1) is the reference track
**Expected duration**: ~3072 frames (~51 seconds, full loop)
**What to capture**:

1. Load Contra (U) [!].nes in Mesen 2
2. Load the Lua script
3. Start a new game → Level 1 begins
4. Press `[` when the Jungle music starts
5. Let it play through at least one full loop
6. Press `]` to stop and save
7. Copy to `extraction/traces/contra/jungle.csv`

**What it will validate**:
- Envelope table shapes (are our extracted tables producing the
  right per-frame volumes?)
- Decrescendo threshold timing (is `(mul * dur) >> 4` correct?)
- Auto-decrescendo mode behavior (bit 7 set notes)
- Noise channel register values (what $400C/$400E values does
  sound_02 actually produce?)
- DMC output level (shows the actual sample waveform for snares)
- Triangle linear counter behavior with Contra's specific $4008
  values

**What to look for in the comparison**:
- Volume mismatches on pulse channels → envelope model errors
- Period mismatches → wrong notes or octave mapping
- Noise volume/period patterns → reveal actual kick drum tuning
- DMC DAC level → shows the shape of percussion samples

## Future Games

For any new game, the capture workflow is identical:

1. Load ROM in Mesen 2
2. Load `mesen_apu_capture.lua` in the script window
3. Navigate to the music you want
4. `[` to start, `]` to stop and save
5. Copy CSV to `extraction/traces/<game>/<track>.csv`
6. Run comparison against your parser's frame IR

### Naming Convention

```
extraction/traces/
  castlevania/
    stage1.csv          # Vampire Killer
  contra/
    jungle.csv          # Level 1 (Jungle)
    waterfall.csv       # Level 3 (optional, later)
  super_c/
    level1.csv          # when we get there
```

### Start Frame Offset

Each capture may have a different number of silence frames before
music begins. Record this in the manifest:

```json
"trace_validation": {
    "trace_path": "extraction/traces/contra/jungle.csv",
    "start_frame_offset": ???,
    "validated_frames": 3072
}
```

The start frame offset is determined by inspecting the trace —
look for the first frame where pulse volume becomes non-zero.
Use `--dump-frames 0-30` to find it.

## Troubleshooting

**Script doesn't load**: Make sure you're using Mesen 2, not
Mesen 1. The Lua API (`emu.getState()`, `emu.addEventCallback()`)
is Mesen 2 specific.

**Keyboard controls don't work**: The game window must have focus,
not the script window. Click on the game window before pressing
`[` or `]`.

**No output file**: Check that `C:\Users\PC\Documents\Mesen2\`
exists. The script writes to a hardcoded path. If your Mesen
documents folder is different, edit line 20 of the Lua script.

**Capture too short**: Make sure you didn't accidentally stop
capture. Use `\` to check status while running.

**Capture has no changes**: The script only logs changes. If you
started capture during silence, the first few frames will have
the initial state dump and then nothing until music starts. This
is normal — the start frame offset accounts for it.
