# REAPER Programming Reference for ReapNES Studio

This document captures everything we've learned about REAPER file formats,
JSFX development, and RPP generation. It serves as the authoritative reference
for all REAPER integration code in this project.

## JSFX Instrument Development

### Required Header for Instruments

```
desc:Plugin Name - Short Description
tags:instrument synthesizer chiptune
in_pin:none
out_pin:Left
out_pin:Right
```

**Critical rules:**
- `tags:` NOT `//tags:` -- the `//` makes it a comment, REAPER never sees it
- `in_pin:none` is REQUIRED for synths -- without it, REAPER treats the plugin as an audio effect and expects audio input
- `tags:instrument` (REAPER v6.74+) makes the plugin appear in the "Instruments" section of the FX browser
- Use only ASCII in all JSFX files -- no em dashes, arrows, or unicode

### Slider Numbering

Sliders MUST be numbered sequentially without gaps. RPP files store slider values
as 64 positional fields. A gap (e.g., slider15 then slider20) causes values to
misalign when loading from RPP.

```
slider1:2<0,3,1{12.5%,25%,50%,75%}>P1 Duty
slider2:15<0,15,1>P1 Volume
slider3:1<0,1,1{Off,On}>P1 Enable
// ... continue sequentially ...
slider16:0.8<0,1,0.01>Master Gain   // NOT slider20
```

### MIDI Processing Pattern

```
@block
while (midirecv(offset, msg1, msg2, msg3)) (
  status = msg1 & 0xF0;
  channel = msg1 & 0x0F;

  status == 0x90 && msg3 > 0 ? (
    // Note On: msg2 = note, msg3 = velocity
  );
  (status == 0x80 || (status == 0x90 && msg3 == 0)) ? (
    // Note Off
  );
  status == 0xB0 ? (
    // CC: msg2 = CC number, msg3 = value
  );

  midisend(offset, msg1, msg2, msg3); // pass through
);
```

**Critical:** If `midirecv()` is called, you MUST drain all events. Always call
`midisend()` to pass events to downstream plugins.

### JSFX Special Variables

- `srate` -- host sample rate (e.g., 44100)
- `samplesblock` -- samples per block
- `spl0`, `spl1` -- left/right audio output samples
- `play_state` -- playback state
- `tempo` -- current BPM

### JSFX Reference URLs

- Programming: https://www.reaper.fm/sdk/js/js.php
- MIDI: https://www.reaper.fm/sdk/js/midi.php
- Variables: https://www.reaper.fm/sdk/js/vars.php
- Keith Haydon Guide: https://www.keithhaydon.com/Reaper/JSFX2.pdf

---

## RPP File Format

### Project Structure

```
<REAPER_PROJECT 0.1 "7.27/win64" timestamp
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 129
  TEMPO 120 4 4
  PLAYRATE 1 0 0.25 4
  MASTERAUTOMODE 0
  MASTER_VOLUME 1 0 -1 -1 1
  MASTER_NCH 2 2
  <TRACK {GUID}
    ...
  >
>
```

Use `"7.27/win64"` as the version string to match the user's REAPER version.
REAPER is forgiving -- missing properties use defaults.

### Track Structure (Complete)

```
<TRACK {GUID}
  NAME "Track Name"
  PEAKCOL 16576606
  BEAT -1
  AUTOMODE 0
  VOLPAN 1 0 -1 -1 1
  MUTESOLO 0 0 0
  IPHASE 0
  PLAYOFFS 0 1
  ISBUS 0 0
  BUSCOMP 0 0 0 0 0
  NCHAN 2
  FX 1
  TRACKID {same-GUID-as-track}
  PERF 0
  MIDIOUT -1
  MAINSEND 1 0
  REC 1 6112 1 0 0 0 0
  VU 2
  <FXCHAIN
    ...
  >
>
```

### REC Field (MIDI Input Configuration)

`REC armed input monitor mode monitor_media preserve_pdc path`

| Field | Values |
|-------|--------|
| armed | 0=disarmed, 1=armed |
| input | Bitmask (see below) |
| monitor | 0=off, 1=on, 2=auto |
| mode | 0=input, 7=MIDI overdub, 8=MIDI replace |
| monitor_media | 0=off, 1=on |
| preserve_pdc | 0=off, 1=on |
| path | 0=primary |

**MIDI input bitmask (field 2):**

When bit 12 (4096) is set, the input is MIDI:
- Bits 0-4: MIDI channel (0=all, 1-16=specific)
- Bits 5-10: MIDI device (63=all inputs, 62=Virtual Keyboard)

Formula: `input = 4096 + (device << 5) + channel`

| Value | Meaning |
|-------|---------|
| 6112 | All MIDI inputs, all channels (`4096 + 63*32 + 0`) |
| 6080 | Virtual Keyboard, all channels (`4096 + 62*32 + 0`) |
| 4097 | First MIDI device, channel 1 |

**Common configurations:**
- `REC 1 6112 1 0 0 0 0` -- Armed, all MIDI, monitoring ON
- `REC 0 0 1 0 0 0 0 0` -- Disarmed, no input

### FX Chain with JSFX

```
<FXCHAIN
  SHOW 0
  LASTSEL 0
  DOCKED 0
  BYPASS 0 0 0
  <JS "ReapNES Studio/ReapNES_Full.jsfx" ""
    val1 val2 val3 ... (64 space-separated fields, '-' for unused)
  >
  FLOATPOS 0 0 0 0
  FXID {GUID}
  WAK 0 0
>
```

- Plugin path is relative to REAPER Effects folder
- 64 slider values on one line, dashes for unused slots
- `BYPASS 0 0 0` must appear before the plugin block
- `FLOATPOS`, `FXID`, `WAK` must appear after

### MIDI Items (Inline Format)

```
<ITEM
  POSITION 0
  LENGTH 10.0
  LOOP 0
  ALLTAKES 0
  FADEIN 0 0 0 0 0 0 0
  FADEOUT 0 0 0 0 0 0 0
  MUTE 0 0
  SEL 0
  IGUID {GUID}
  <SOURCE MIDI
    HASDATA 1 960 QN
    CCINTERP 32
    POOLEDEVTS {GUID}
    E 0 90 3c 7f        // Note On ch1, C4, vel 127
    E 960 80 3c 00      // Note Off ch1, C4 (960 ticks later)
    E 0 b0 7b 00        // All Notes Off (end marker)
    GUID {GUID}
    IGNTEMPO 0 120 4 4
    SRCCOLOR 0
    VELLANE -1 100 0
    CFGEDITVIEW 0 0 0 0 0 0
    KEYSNAP 0
    EVTFILTER 0 -1 -1 -1 -1 0 0 0 0 -1 -1 -1 -1 0 -1 0 -1 -1
  >
>
```

**MIDI event encoding:**
- `E delta hex1 hex2 hex3` -- channel event (not selected)
- `e delta hex1 hex2 hex3` -- channel event (selected)
- `X delta length hex...` -- meta/sysex event
- Delta is in ticks from previous event
- `HASDATA 1 PPQ QN` -- PPQ = pulses per quarter note (960 typical)
- `POOLEDEVTS {GUID}` -- enables MIDI pooling; use unique GUID for independent items

**Status bytes (hex1):**
- `90`-`9f`: Note On (channel 1-16)
- `80`-`8f`: Note Off
- `b0`-`bf`: CC
- `e0`-`ef`: Pitch bend
- `ff`: Meta event (via X line)

### RPP Format References

- Cockos Wiki: wiki.cockos.com/wiki/index.php/RPP
- State Chunks: github.com/ReaTeam/Doc/blob/master/State%20Chunk%20Definitions
- MIDI Format: wiki.cockos.com/wiki/index.php/Rpp_Midi_Format_Draft
- Python parser: pip install rpp (github.com/Perlence/rpp)

---

## Common Pitfalls

1. **`//tags:` vs `tags:`** -- JSFX uses `//` for comments. `tags:` is a directive, not a comment.
2. **Missing pin declarations** -- No `in_pin:none` = REAPER treats JSFX as audio effect = silence on MIDI tracks.
3. **Slider gaps** -- Non-sequential slider numbers cause RPP parameter misalignment.
4. **Unicode in JSFX** -- Use ASCII only. Windows cp1252 encoding may break unicode.
5. **RPP token guessing** -- Always examine a real .RPP saved by the target REAPER version.
6. **MIDI input in RPP** -- Use `REC 1 6112 1 0 0 0 0` for all MIDI inputs with monitoring.
7. **SOURCE MIDIPOOL FILE** -- Does NOT work for playback in REAPER v7. Use SOURCE MIDI with inline events.
8. **MIDI items need full metadata** -- POOLEDEVTS, GUID, IGNTEMPO, VELLANE, etc. are needed for proper display.
