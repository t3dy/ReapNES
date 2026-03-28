# INSTRUMENTS.md — ReapNES JSFX Plugin Status Report

## What We Built

Three JSFX plugins that model the NES 2A03 APU:

1. **ReapNES_Full.jsfx** — 4-channel APU (Pulse x2, Triangle, Noise) with sweep unit
2. **ReapNES_Instrument.jsfx** — Preset-driven synth that loads .reapnes-data envelope files
3. **ReapNES_Pulse.jsfx** — Focused dual-pulse with oscilloscope display

Plus a minimal test plugin:
4. **ReapNES_Test.jsfx** — 30-line square wave beep for debugging

## Critical Fix: Pin Declarations

The plugins were originally missing `in_pin:none` / `out_pin:Left` / `out_pin:Right` declarations. Without these, REAPER treats a JSFX as an audio pass-through effect, not a synthesizer. It expects audio input, finds none on a MIDI-only track, and produces silence.

**Fix applied:** All four plugins now have:
```
in_pin:none
out_pin:Left
out_pin:Right
```

This tells REAPER: "This plugin generates audio from MIDI, it has no audio input."

## What Works

- **ReapNES_Test.jsfx**: Confirmed working. When manually added to a track via REAPER's FX browser (Add FX > search "ReapNES Test"), with the track record-armed and MIDI input set to the keyboard, it produces audible sound from keyboard input.
- The test was done by adding the plugin to a track that already had a working VSTi instrument, then bypassing the VSTi. This confirmed the JSFX synth engine itself works.

## What Does NOT Work

- **Loading via RPP file**: When ReapNES_Full.jsfx is loaded via a generated .RPP project file, it does not produce audible sound from MIDI keyboard input even when the track is record-armed and MIDI input is set to "All: All Channels."
- **Possible cause 1 — Slider parameter mismatch**: The RPP file passes slider values positionally. ReapNES_Full has sliders 1-15 then jumps to slider 20 (Master Gain). The gap between slider 15 and slider 20 may cause REAPER to misassign the gain value, potentially setting it to 0.
- **Possible cause 2 — MIDI channel routing**: ReapNES_Full internally routes MIDI channel 0 → Pulse 1, channel 1 → Pulse 2, etc. If the keyboard sends on channel 0 but the RPP configures the track for a different channel, the plugin won't respond.
- **Possible cause 3 — Plugin compilation error**: The sweep unit additions to apu_core.jsfx-inc may have introduced a silent error that prevents the plugin from compiling in REAPER. JSFX compilation errors are not always visible.

## What We Have NOT Tested

- Opening the FX window to verify the plugin loaded without errors
- Checking whether the plugin's @gfx display renders (confirms compilation)
- Whether slider values in the RPP are being received correctly
- Whether the MIDI messages are reaching the @block handler
- Adding ReapNES_Full manually via FX browser (instead of via RPP) to a track with MIDI input

## ReapNES_Instrument.jsfx — Additional Issues

This plugin loads preset files via JSFX `file_open()` using slider file references. In the RPP we wrote paths like:
```
/ReapNES-Studio/presets/mario/smb_overworld_lead.reapnes-data
```

This path format was never verified in REAPER. The JSFX file slider system may expect a different path convention. When presets fail to load, the plugin produces silence (it only generates audio when an envelope is playing).

**Status: Untested and likely broken for RPP-based loading.**

## Recommendations

1. **Test manually first**: Add ReapNES_Full.jsfx to a track via FX browser, set MIDI input, verify sound. This isolates plugin code from RPP generation issues.
2. **Check the FX window**: Open the plugin UI to see if it compiled and if sliders show expected values.
3. **Fix the slider gap**: Either renumber slider20 to slider16, or ensure the RPP writes the correct number of parameter values.
4. **Test ReapNES_Instrument preset loading**: Open the plugin UI, try to select a preset file manually via the REAPER file browser slider.

## Files

Installed location: `%APPDATA%\REAPER\Effects\ReapNES Studio\`
Source location: `C:\Dev\ReapNES-Studio\jsfx\`

```
ReapNES_Full.jsfx          (main synth — 4 channels + sweep)
ReapNES_Instrument.jsfx    (preset-driven — loads .reapnes-data)
ReapNES_Pulse.jsfx         (dual pulse + oscilloscope)
ReapNES_Test.jsfx          (minimal beep — confirmed working)
lib/
  apu_core.jsfx-inc        (phase accumulators, duty tables, sweep unit)
  mixer_nonlinear.jsfx-inc (hardware DAC mixer formulas)
  lfsr_noise.jsfx-inc      (15-bit LFSR noise generator)
  envelope.jsfx-inc        (24 Hz frame-rate envelope engine)
```
