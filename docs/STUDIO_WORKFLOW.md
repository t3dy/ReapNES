# ReapNES Studio — Complete Workflow Guide

## The 3-Minute Path to Sound

```bash
# 1. Generate a project from a song set
python scripts/generate_project.py --song-set mm2_wily1

# 2. Copy plugins to REAPER
#    jsfx/ → %APPDATA%\REAPER\Effects\ReapNES Studio\

# 3. Copy presets to REAPER data directory
#    presets/ → %APPDATA%\REAPER\Data\ReapNES-Studio\presets\

# 4. Open reaper_projects/mm2_wily1.rpp in REAPER

# 5. Play MIDI keyboard — channels 1-4 map to Pulse/Tri/Noise
```

## Available Workflows

### A. Quick Generic Session
No game palette — just open NES synths and play.

```bash
python scripts/generate_project.py --generic
# Open reaper_projects/generic_nes.rpp
```

Tracks use ReapNES_Full.jsfx with default settings. Tweak duty cycles, noise period, and volume manually.

### B. Game Palette Session
Choose a song set for authentic NES game sounds.

```bash
# See what's available
python scripts/generate_project.py --list-sets

# Generate a specific palette
python scripts/generate_project.py --song-set cv1_wicked_child
# Open reaper_projects/cv1_wicked_child.rpp
```

Tracks use ReapNES_Instrument.jsfx with extracted presets wired into the correct slots. Envelope automation plays back automatically at 24 Hz frame rate.

### C. MIDI Import Session
Map any MIDI file onto NES instruments.

```bash
# Auto-mapping (bass→triangle, drums→noise, leads→pulse)
python scripts/generate_project.py --song-set mm2_wily1 --midi path/to/file.mid

# Custom mapping
python scripts/generate_project.py --song-set mm2_wily1 --midi file.mid --mapping mapping.json
```

Auto-mapping rules:
- MIDI channel 10 (drums) → Noise
- Lowest-pitch melodic track → Triangle (bass)
- Highest note-count melodic track → Pulse 1 (lead)
- Second busiest → Pulse 2 (harmony)

### D. Browse and Curate
Explore the 54K extracted preset corpus.

```bash
# List all games in the corpus
python scripts/preset_catalog.py games

# List songs for a specific game
python scripts/preset_catalog.py songs --game MegaMan2

# Search for specific presets
python scripts/preset_catalog.py search --game Castlevania --tag vibrato

# Export a song's presets as a song set
python scripts/preset_catalog.py export --game MegaMan2 --song "07AirManStage"
```

### E. Generate Custom Song Set
Create your own palette from any combination of presets.

1. Search for presets: `python scripts/preset_catalog.py search --channel pulse --tag looping`
2. Copy `examples/midi_mapping_example.json` as a template
3. Edit `song_sets/my_palette.json` with your chosen presets
4. Generate: `python scripts/generate_project.py --song-set my_palette`

## MIDI CC Controls (in REAPER)

When playing ReapNES_Full.jsfx live:

| CC | Function |
|----|----------|
| CC 1 (Mod Wheel) | Duty cycle on pulse channels; noise mode toggle on ch 4 |
| CC 74 (Brightness) | Sweep unit: low=pitch drop, center=off, high=pitch rise |
| Velocity | Maps to NES volume (0-127 → 0-15) |

## File Installation

### REAPER Effects Directory
Copy the entire `jsfx/` folder including `lib/`:
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

### REAPER Data Directory
Copy the `presets/` folder:
```
REAPER/Data/ReapNES-Studio/presets/
  generic/          (16 hand-crafted presets)
  mario/            (5 game-specific presets)
  jsfx_data/        (54K extracted presets)
  drum_kits/        (drum kit definitions)
```

Paths:
- Windows: `%APPDATA%\REAPER\`
- macOS: `~/Library/Application Support/REAPER/`
- Linux: `~/.config/REAPER/`
