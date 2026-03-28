# ReapNES Studio Guide

## What This Is

ReapNES Studio is a REAPER-based NES music production environment. It lets you compose, arrange, and experiment with authentic NES sounds inside REAPER. Choose a game palette, generate a project, optionally import MIDI, and start playing.

## Installation (5 minutes)

### 1. Install JSFX plugins

Copy the `jsfx/` folder into your REAPER Effects directory:
- Windows: `%APPDATA%\REAPER\Effects\ReapNES Studio\`
- macOS: `~/Library/Application Support/REAPER/Effects/ReapNES Studio/`

Include the `lib/` subfolder:
```
REAPER/Effects/ReapNES Studio/
  ReapNES_Full.jsfx
  ReapNES_Instrument.jsfx
  ReapNES_Pulse.jsfx
  lib/
    apu_core.jsfx-inc
    mixer_nonlinear.jsfx-inc
    lfsr_noise.jsfx-inc
    envelope.jsfx-inc
```

### 2. Install presets

Copy the `presets/` folder to your REAPER Data directory:
- Windows: `%APPDATA%\REAPER\Data\ReapNES-Studio\presets\`
- macOS: `~/Library/Application Support/REAPER/Data/ReapNES-Studio/presets\`

### 3. Open a project

Open any `.rpp` file from `reaper_projects/`. Play with a MIDI keyboard (channels 1-4) or REAPER's virtual keyboard.

## The Three Plugins

### ReapNES_Full.jsfx (recommended)
Full 4-channel NES APU in one plugin. All channels synthesized with hardware-accurate models. Includes sweep unit for pitch bending effects.

Controls:
- **P1/P2 Duty**: 12.5%, 25%, 50%, 75%
- **P1/P2 Volume**: 0-15 (4-bit)
- **Tri Enable**: On/Off (triangle has no volume control)
- **Noise Period/Mode/Volume**: Full noise channel
- **P1 Sweep**: Enable, rate, direction, shift
- **Master Gain**: Output level

MIDI CCs:
- CC 1 (Mod Wheel): Duty cycle control (pulse), mode toggle (noise)
- CC 74 (Brightness): Sweep control — low=pitch drop, center=off, high=pitch rise

### ReapNES_Instrument.jsfx (for preset-driven work)
Loads `.reapnes-data` preset files. Each note triggers envelope automation for volume, duty cycle, and pitch at 24 Hz — matching the NES hardware sequencer timing.

4 preset slots, one per channel type. Generated projects wire the correct preset into the correct slot automatically.

### ReapNES_Pulse.jsfx (focused pulse work)
Dedicated dual-pulse with oscilloscope. For when you want detailed control over just the pulse channels.

## Preset Library

### Curated Presets

**Generic** (`presets/generic/`, 16 presets):
- Pulse: lead (50%/25%/12.5%), pluck, staccato, swell, vibrato, duty sweep
- Triangle: sustained bass, pluck, vibrato
- Noise: closed/open hi-hat, snare, kick, crash

**Mario** (`presets/mario/`, 5 presets):
- Overworld lead, harmony, bass
- Underground lead, bass

### Extracted Corpus

**54,000+ presets** (`presets/jsfx_data/`) from 390 NES games, extracted from the NES Music Database. Browse with:

```bash
python scripts/preset_catalog.py games                      # All games
python scripts/preset_catalog.py songs --game Castlevania   # Songs in a game
python scripts/preset_catalog.py search --tag vibrato       # By tag
python scripts/preset_catalog.py search --game MegaMan2 --channel noise
```

### Drum Kits

`presets/drum_kits/default_kit.json` maps GM drum notes to noise presets:
- Note 36: Kick
- Note 38: Snare
- Note 42: Closed hi-hat
- Note 46: Open hi-hat
- Note 49: Crash

## Song Sets

6 available palettes. Generate more from the corpus.

```bash
python scripts/generate_project.py --list-sets
```

| Set | Game | Description |
|-----|------|-------------|
| smb1_overworld | Super Mario Bros. | Classic overworld sound |
| smb1_underground | Super Mario Bros. | Dark, thin underground |
| mm2_wily1 | Mega Man 2 | Wily Stage 1 extracted instruments |
| cv1_wicked_child | Castlevania | Stage 4 extracted instruments |
| cv3_beginning | Castlevania III | Opening theme extracted |
| silius_stage2 | Journey to Silius | Heavy noise percussion |

## MIDI Import

Map any MIDI file onto NES instruments:

```bash
# Auto-mapping
python scripts/generate_project.py --song-set mm2_wily1 --midi song.mid

# Custom mapping
python scripts/generate_project.py --song-set mm2_wily1 --midi song.mid --mapping map.json
```

Auto-mapping assigns:
- Drum tracks → Noise
- Lowest pitch → Triangle (bass)
- Busiest melodic → Pulse 1 (lead)
- Second busiest → Pulse 2 (harmony)

See `docs/MIDI_MAPPING.md` for details.

## What Is Implemented vs. Provisional

| Feature | Status |
|---------|--------|
| Pulse synthesis (2 channels) | Production — wire-accurate |
| Triangle synthesis | Production — wire-accurate |
| Noise (LFSR) | Production — wire-accurate |
| Non-linear mixer | Production — hardware-accurate DAC formulas |
| Sweep unit | Production — hardware-accurate timing |
| Preset envelope playback | Production — 24 Hz frame rate |
| Project generation | Production — creates working RPP files |
| MIDI import (auto-map) | Functional — basic heuristic mapping |
| Preset catalog/browser | Functional — CLI-based search and export |
| Song sets (6 palettes) | Functional — 2 hand-authored, 4 extracted |
| Drum kits | Provisional — noise-only, no DMC samples |
| DMC channel | Not implemented — placeholder only |
| Length counter / frame counter | Deferred — minimal user-facing impact |
| ROM/NSF register extraction | Not started — header parsing only |

## Fastest Path to Audible Results

1. `python scripts/generate_project.py --song-set mm2_wily1`
2. Copy `jsfx/` and `presets/` to REAPER directories
3. Open `reaper_projects/mm2_wily1.rpp`
4. Play MIDI keyboard on channels 1-4
