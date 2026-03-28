# REAPER Project Generation

## Overview

`scripts/generate_project.py` creates ready-to-open REAPER `.RPP` project files with:
- Color-coded tracks for each NES channel
- ReapNES plugins loaded with correct presets
- MIDI routing configured
- Optional MIDI file items embedded on tracks

## Quick Reference

```bash
# List what's available
python scripts/generate_project.py --list-sets
python scripts/generate_project.py --list-presets

# Generate projects
python scripts/generate_project.py --generic                    # Blank NES session
python scripts/generate_project.py --song-set mm2_wily1         # Game palette
python scripts/generate_project.py --song-set mm2_wily1 -o my.rpp  # Custom output path
python scripts/generate_project.py --all                        # Rebuild all projects

# With MIDI import
python scripts/generate_project.py --song-set mm2_wily1 --midi song.mid
python scripts/generate_project.py --song-set mm2_wily1 --midi song.mid --mapping map.json
```

## How It Works

### Generic Mode (`--generic`)
Creates 4 tracks, each with ReapNES_Full.jsfx (raw hardware controls). No presets loaded. Good for experimenting.

### Song Set Mode (`--song-set NAME`)
Reads a song set JSON from `song_sets/`. For each channel:
- If the song set defines a preset → uses ReapNES_Instrument.jsfx with the preset file wired into the correct slot
- If no preset is defined → falls back to ReapNES_Full.jsfx with default settings

### MIDI Import (`--midi PATH`)
Analyzes the MIDI file, maps tracks to NES channels, and embeds MIDI items directly into the generated project.

**Auto-mapping** (default, no `--mapping`):
1. MIDI channel 10 tracks → Noise
2. Lowest average pitch melodic track → Triangle
3. Highest note-count melodic track → Pulse 1
4. Second busiest melodic track → Pulse 2

**Config-driven** (`--mapping PATH`):
Provide a JSON file specifying which MIDI track index maps to which NES channel:
```json
{
  "channel_map": {
    "pulse1": 0,
    "pulse2": 1,
    "triangle": 2,
    "noise": 9
  }
}
```

See `examples/midi_mapping_example.json` for a full template.

## Generated Project Structure

Each project contains:
- **Pulse 1** (MIDI Ch 1, green) — lead melody
- **Pulse 2** (MIDI Ch 2, teal) — harmony / counter-melody
- **Triangle** (MIDI Ch 3, orange) — bass
- **Noise / Drums** (MIDI Ch 4, gray) — percussion

Track names include the channel role when a song set is used:
`NES - Pulse 1 [lead]`

## Plugin Configuration in RPP

When using ReapNES_Instrument.jsfx, the generated RPP wires preset files into JSFX slider references:
```
<JS "ReapNES Studio/ReapNES_Instrument.jsfx" ""
  /ReapNES-Studio/presets/jsfx_data/24811_Square_Pad_3680.reapnes-data none none none
  2.0 15.0 0.0
  1.000000
  0.8
>
```

This requires that preset files are installed in REAPER's Data directory at the path `ReapNES-Studio/presets/`.

## Regenerating All Projects

When you add new song sets or change the generator:
```bash
python scripts/generate_project.py --all
```

This rebuilds every song set project plus the generic session.
