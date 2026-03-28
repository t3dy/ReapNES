# SUCCESSANDFAIL.md — Honest Progress Report

## The Goal

"I can open REAPER and immediately start making music with NES-style sounds, templates, and imported material without fighting the interface."

## Overall Verdict

We are NOT there yet. The synthesis engine works (proven by test_beep), but the delivery layer — project files, MIDI embedding, automated configuration — is broken. The user still cannot open a generated project and hear sound without manual intervention.

---

## SUCCESSES

### 1. JSFX Synthesis Engine Works
**ReapNES_Test.jsfx** (minimal beep synth) was confirmed to produce sound when:
- Added manually to a track via REAPER's FX browser
- Track record-armed with MIDI input set to keyboard
- Input monitoring enabled

This proves: JSFX can work as a MIDI instrument in REAPER on this system.

### 2. Pin Declaration Fix
Discovered that `in_pin:none` / `out_pin:Left` / `out_pin:Right` are REQUIRED for JSFX instruments. Without them, REAPER treats the plugin as an audio effect (needs audio in) rather than a synthesizer (generates audio from MIDI). All plugins now have correct pin declarations.

### 3. RPP Files Load Without Errors
After removing unrecognized tokens (`MASTER_SEND`, `REC_INPUT`, `RECINPUT`, `RECMON`), the generated .RPP files open in REAPER v7.27 with no warnings. Tracks appear with correct names, colors, and plugins loaded.

### 4. Plugin Installation
Successfully installed all JSFX files to `%APPDATA%\REAPER\Effects\ReapNES Studio\` and presets to `%APPDATA%\REAPER\Data\ReapNES-Studio\presets\`. REAPER finds the plugins and loads them.

### 5. Preset Corpus
54,000+ instrument presets extracted from NES-MDB. Preset catalog tool (`preset_catalog.py`) works correctly for searching, browsing, and exporting song sets.

### 6. Song Set Data Model
6 song sets defined with proper schema, metadata, and provenance tracking. Export pipeline from corpus to song set JSON works.

### 7. Sweep Unit
Hardware-accurate sweep unit added to apu_core.jsfx-inc and exposed via sliders and CC74 in ReapNES_Full.jsfx.

---

## FAILURES

### 1. Generated Projects Do Not Produce Sound
**The core failure.** Opening any generated .RPP and pressing Play or hitting a MIDI key produces no audible output. This defeats the entire purpose of the project generator.

**Root causes (suspected, not all confirmed):**
- MIDI input is not configured by the RPP — user must manually set it every time
- JSFX slider values in the RPP may be misaligned due to the gap between slider15 and slider20
- ReapNES_Full.jsfx may have a compilation error from the sweep unit changes (not verified)
- ReapNES_Instrument.jsfx preset file loading via RPP slider values has never been verified

### 2. MIDI Embedding Does Not Work
Two approaches tried, both failed:
- `SOURCE MIDIPOOL FILE` — items visible but no playback audio
- `SOURCE MIDI` with inline E events — items appear empty, no playback

Real REAPER projects use `POOLEDEVTS` (internal pooled event system) which we don't know how to generate.

### 3. MIDI Input Cannot Be Set Via RPP
We tried `MIDI_INPUT_CHANMAP`, `RECINPUT`, `REC_INPUT` — none successfully configure the MIDI input device in REAPER v7.27. The user must manually set MIDI input on every track after opening every project.

### 4. ReapNES_Full.jsfx Not Verified Working Via RPP
The test_beep plugin works when added manually. ReapNES_Full has NOT been tested the same way. It may have:
- Compilation errors from the sweep unit code
- Slider value issues (the gap in slider numbering)
- Issues with the imported library files

### 5. ReapNES_Instrument.jsfx Preset Loading Unverified
The preset file path format (`/ReapNES-Studio/presets/...`) in RPP files has never been tested. The JSFX file slider mechanism for loading files may require a completely different path format.

### 6. Too Much Time on Infrastructure, Not Enough on Verification
We built a catalog tool, 6 song sets, a project generator, MIDI analysis, sweep unit, drum kit model, and extensive documentation — but never verified the fundamental question: "Does the plugin produce sound when loaded from a project file?"

---

## WHAT NEEDS TO HAPPEN NEXT

### Immediate (blocks everything else)

1. **Manually test ReapNES_Full.jsfx**: Add it to a track via REAPER FX browser (not via RPP). Set MIDI input. Does it produce sound? If not, the plugin code has a bug.

2. **If it works manually, test a minimal RPP**: Generate an RPP with ReapNES_Full and NO custom slider values (just `<JS "ReapNES Studio/ReapNES_Full.jsfx" "">` with no parameter lines). See if defaults work.

3. **If defaults work, add slider values one at a time** to find the misalignment.

4. **If the plugin doesn't work manually**, bisect the code: try ReapNES_Full WITHOUT the sweep unit imports, then WITH. Find the compilation error.

### After Sound Works

5. **Stop embedding MIDI in RPP.** Accept the two-step workflow: generate project → import MIDI via drag-and-drop.

6. **Or build a ReaScript** (Lua/Python script that runs inside REAPER) that can insert MIDI items and configure tracks using REAPER's API instead of raw RPP manipulation.

7. **Test ReapNES_Instrument preset loading** manually in the REAPER UI before trying to automate it.

### Attitude Adjustment

- **Verify before building.** Don't build 6 song sets before confirming the plugin produces sound.
- **Test the simplest case first.** One track, one plugin, one note.
- **Don't trust RPP format guesses.** Reference the Cockos wiki or examine working projects.
- **Manual REAPER testing is not optional.** RPP generation is useless if we don't verify the output.

---

## SESSION TIMELINE

1. Built preset catalog, song sets, drum kits, MIDI mapping — all worked at the script level
2. Rewrote generate_project.py to wire Instrument plugin with presets — untested in REAPER
3. Added sweep unit to apu_core.jsfx-inc — untested in REAPER
4. First REAPER test: project loads with 5 warnings (bad RPP tokens) and no plugin sound
5. Fixed RPP tokens — project loads cleanly, still no sound
6. Discovered missing pin declarations — the fundamental synthesis blocker
7. Added in_pin/out_pin to all plugins — test_beep works when added manually via FX browser
8. test_beep does NOT work when loaded via RPP (MIDI input not configured)
9. Tried MIDI embedding via MIDIPOOL FILE — items visible but silent
10. Tried inline MIDI via SOURCE MIDI — items invisible and silent
11. Current state: plugin works manually, project generation does not deliver working projects

## Key Lesson

The synthesis engine is solid. The REAPER integration layer is where we failed. We should have started by getting one note to play from an RPP file before building the entire studio infrastructure on top.
