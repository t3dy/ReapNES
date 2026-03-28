# PROJECTS.md — RPP Project Generation Status Report

## What generate_project.py Does

Creates REAPER .RPP project files with:
- Multiple tracks (one per NES channel: Pulse 1, Pulse 2, Triangle, Noise)
- ReapNES JSFX plugins loaded in FX chains
- Track naming and color coding
- Tempo and project metadata from song sets
- (Attempted) MIDI item embedding
- (Attempted) MIDI input configuration

## RPP Format: What We Got Right

### Project header
```
<REAPER_PROJECT 0.1 "7.27/win64" 1707000000
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 129
  TEMPO 120 4 4
  ...
```
Initially used `"6.0"` version string — works but triggers "5 elements not understood" warnings for tokens that changed between versions. Changed to `"7.27/win64"` which matches the user's REAPER version.

### Track structure
```
<TRACK
  NAME "NES - Pulse 1"
  PEAKCOL 16576606
  BEAT -1
  AUTOMODE 0
  VOLPAN 1 0 -1 -1 1
  MUTESOLO 0 0 0
  NCHAN 2
  FX 1
  MAINSEND 1 0
  REC 0 0 1 0 0 0 0 0
  ...
>
```
This matches the format from the user's working projects. Loads without warnings.

### FX chain with JSFX
```
<FXCHAIN
  SHOW 0
  LASTSEL 0
  DOCKED 0
  <JS "ReapNES Studio/ReapNES_Full.jsfx" ""
    2.0 15.0 1.0
    ...
  >
>
```
The plugin loads and REAPER finds it (confirmed: no "effects not available" error after installing to Effects dir).

## RPP Format: What We Got Wrong

### 1. MASTER_SEND token
Used `MASTER_SEND 0 0` — REAPER v7.27 does not recognize this. Removed.

### 2. REC_INPUT token
Used `REC_INPUT 6112 "MIDI > Ch 1"` — not recognized. The correct v7 format is just `REC 0 0 1 0 0 0 0 0` for the record state. Removed REC_INPUT.

### 3. RECINPUT and RECMON tokens
Tried `RECINPUT 4096` and `RECMON 1` — not recognized by v7.27. Removed. We have NOT found the correct RPP token to set MIDI input device in this version.

### 4. MIDI_INPUT_CHANMAP
Used this to specify which MIDI channel a track listens to. It may or may not be recognized — it didn't produce warnings, but it also didn't visibly configure the MIDI input in REAPER's UI.

### 5. SOURCE MIDIPOOL FILE
```
<SOURCE MIDIPOOL
  FILE "C:/path/to/file.mid"
>
```
REAPER v7 does not play back MIDI from external file references this way. Items appear visually but produce no audio.

### 6. SOURCE MIDI with inline E events
```
<SOURCE MIDI
  HASDATA 1 96 QN
  CCINTERP 32
  E 0 90 3c 7f
  ...
>
```
Our inline MIDI events are syntactically correct but REAPER v7 may require POOLEDEVTS references or other metadata we haven't provided. Items appear empty.

### 7. JSFX slider parameter values
The RPP passes slider values as space-separated numbers after the plugin path. With ReapNES_Full.jsfx having sliders 1-15 then a gap to slider 20, the positional mapping is unclear. We may be setting Master Gain to 0 or misaligning other values, causing silent output even when the plugin compiles correctly.

## What the Generated Projects Actually Do

### Loads cleanly (no warnings): YES (after removing bad tokens)
### Has correct tracks with names and colors: YES
### Has plugins loaded: YES (REAPER finds them)
### Plugin produces sound from MIDI input: UNKNOWN (not verified via RPP load)
### MIDI items play back: NO (neither approach works)
### MIDI keyboard input works automatically: NO (requires manual setup)

## Generated Project Files

```
reaper_projects/
  generic_nes.rpp          — 4 tracks, ReapNES_Full, no presets, no MIDI
  smb1_overworld.rpp       — 4 tracks, Instrument plugin with preset refs
  smb1_underground.rpp     — 4 tracks, Instrument plugin with preset refs
  mm2_wily1.rpp            — 4 tracks, mixed Full/Instrument
  cv1_wicked_child.rpp     — 4 tracks, mixed Full/Instrument
  cv3_beginning.rpp        — 4 tracks, Instrument on pulse, Full on rest
  silius_stage2.rpp        — 4 tracks, mixed Full/Instrument
  kraid_with_midi.rpp      — 4 tracks, Full APU, SOURCE MIDIPOOL (broken)
  kraid_inline.rpp         — 3 tracks, Full APU, inline MIDI (broken)
  test_synth.rpp           — 1 track, Full APU, no MIDI (plugin didn't sound)
  test_beep.rpp            — 1 track, Test beep, no MIDI (plugin didn't sound via RPP)
```

## Recommendations

1. **Stop embedding MIDI in RPP.** Generate clean projects with plugins and tracks. Import MIDI separately.
2. **Verify plugin slider mapping.** The gap between slider15 and slider20 needs investigation. Consider renumbering slider20 → slider16.
3. **Test RPP plugin loading.** Generate a minimal RPP with ReapNES_Full and NO custom slider values (let defaults apply). If that produces sound from keyboard, the issue is slider value encoding.
4. **Consider ReaScript.** REAPER's API can insert MIDI items, set track inputs, and configure FX programmatically. A Lua script run after project load could do what RPP tokens cannot.
5. **Reference the Cockos wiki** for RPP format: `wiki.cockos.com/wiki/index.php/RPP` — the user guide does not document RPP internals.
