# MIDI.md — MIDI Routing, Playback, and Import Status Report

## How REAPER Handles MIDI (What We Learned)

### MIDI Input to Tracks
REAPER tracks can receive MIDI from two sources:
1. **Live input**: A MIDI keyboard/controller, configured via the track's input dropdown
2. **MIDI items**: Embedded MIDI data in items on the track timeline

These are independent. A track can have MIDI items that play back AND receive live MIDI simultaneously.

### Configuring MIDI Input (Live Keyboard)
From the REAPER User Guide (p59-60, p72-73, p273):
- Right-click the record arm button → Input: MIDI → select device → select channel
- Or click the input dropdown on the track → MIDI → device → channel
- Input monitoring must be enabled for the sound to pass through to output
- Setting the input to "All: All Channels" receives MIDI from any connected device on any channel

**Critical lesson**: The RPP token `MIDI_INPUT_CHANMAP` is NOT the same as setting the MIDI input device. `MIDI_INPUT_CHANMAP` only filters which MIDI channel the track listens to, but the track also needs `RECINPUT` set to a MIDI input (not audio). In REAPER v7.27, the exact `RECINPUT` format was not documented and our attempts to use it (`RECINPUT 4096`, `RECINPUT 4192`) produced "token not recognized" warnings.

**What actually works**: Setting MIDI input manually in REAPER's UI after opening the project. We have NOT found a reliable way to set MIDI input via RPP file for REAPER v7.27.

### MIDI Item Embedding in RPP Files

We tried two approaches:

#### Approach 1: SOURCE MIDIPOOL with external file reference
```xml
<SOURCE MIDIPOOL
  FILE "C:/Users/PC/Downloads/Kraid.mid"
>
```
**Result**: REAPER shows MIDI items on the tracks with visible note bars, but the plugin does NOT receive the MIDI events during playback. No audio output. The MIDIPOOL/FILE approach may be deprecated or may only work for specific REAPER versions.

**Visual evidence**: The MIDI item bars were visible on tracks in the arrange view, but all track meters showed -inf during playback.

#### Approach 2: SOURCE MIDI with inline events
```xml
<SOURCE MIDI
  HASDATA 1 96 QN
  CCINTERP 32
  E 0 90 3c 7f
  E 48 80 3c 00
  E 0 ff 2f 00
>
```
**Result**: REAPER loads the project but does NOT show MIDI item content as visible note bars on the tracks. The items appear empty/blank. No audio during playback.

**What real REAPER projects use**: Examining a working REAPER project ("kraid lair.rpp" created by the user), MIDI data is stored as:
```xml
<SOURCE MIDI
  HASDATA 1 120 QN
  CCINTERP 32
  POOLEDEVTS {C7A25443-BE1B-49AF-BA60-38232136F59D}
  <X 0 0
  /yEBAA==
>
```
The actual MIDI events are referenced via `POOLEDEVTS` (a GUID pointing to a shared event pool stored elsewhere in the RPP). The inline data is minimal (just a meta event). The POOLEDEVTS system is REAPER's internal deduplication — when multiple items share the same MIDI data, they reference one pool.

**We do not know how to generate POOLEDEVTS entries.** This is an undocumented internal format.

### The E/X Event Format
From examining working RPP files:
- `E delta status [data...]` — channel MIDI events (note on/off, CC, etc.)
- `X delta length data...` — meta/sysex events
- `e` / `x` — same but for selected events
- Delta values are in ticks (relative to previous event)
- All bytes are lowercase hex
- `HASDATA 1 <tpb> QN` declares ticks-per-beat and that data follows

Our inline MIDI generator produces syntactically correct E/X events, but REAPER v7.27 may require additional fields (POOLEDEVTS, GUID, etc.) to properly recognize the data.

## What Works for MIDI Playback

The ONLY confirmed working approach: **drag and drop a .mid file onto a track in REAPER's UI.** This lets REAPER handle the MIDI import natively, creating proper POOLEDEVTS references internally.

## What Does NOT Work

1. `SOURCE MIDIPOOL FILE "path.mid"` — items appear but no audio
2. `SOURCE MIDI` with inline E events — items appear empty, no audio
3. Any RPP-based MIDI embedding we've tried

## Recommendations

1. **Stop trying to embed MIDI in RPP files.** Generate the project with tracks and plugins ready, then import MIDI via drag-and-drop or REAPER's Insert > Media File menu.
2. **Alternatively**, create a REAPER Lua/Python script (ReaScript) that runs inside REAPER to insert MIDI items programmatically using REAPER's API. This would use the proper internal format.
3. **Document the two-step workflow**: (a) generate project with plugins, (b) import MIDI manually.

## Auto-Mapping Logic (This Part Works)

The MIDI analysis and auto-mapping code in `generate_project.py` correctly:
- Reads MIDI files using the `mido` library
- Identifies tracks, channels, note counts, pitch ranges
- Detects drum tracks (MIDI channel 10 / index 9)
- Maps: drums → noise, lowest pitch → triangle, busiest → pulse 1, second → pulse 2

This logic is sound but currently has no way to deliver its results into REAPER.
