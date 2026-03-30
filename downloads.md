---
layout: default
title: Downloads
---

# Downloads

## ReapNES Synth Plugin

The ReapNES_APU.jsfx plugin recreates the NES Audio Processing Unit in REAPER. Four waveform modes (Pulse 12.5%/25%/50%/75%, Triangle, Noise) with per-channel volume and duty cycle control driven by MIDI CC automation.

**Download:** [ReapNES_APU.jsfx](studio/jsfx/ReapNES_APU.jsfx) (install to REAPER Effects folder)

Additional synth variants:
- [ReapNES_Pulse.jsfx](studio/jsfx/ReapNES_Pulse.jsfx) — Pulse channel only
- [ReapNES_Full.jsfx](studio/jsfx/ReapNES_Full.jsfx) — Full APU with mixing
- [ReapNES_Instrument.jsfx](studio/jsfx/ReapNES_Instrument.jsfx) — Instrument mode

## MIDI Files

4-channel NES musical scores with CC11 volume envelope automation and CC12 duty cycle control. Open in any DAW or MIDI editor.

*MIDI files are in each game's directory in the [GitHub repository](https://github.com/t3dy/ReapNES/tree/master/output).*

## REAPER Projects

Ready-to-play .rpp files with ReapNES synth loaded per channel. Requires REAPER v7+ and the ReapNES JSFX plugins above.

*REAPER projects are alongside the MIDI files in each game's output directory.*

## NSF Extraction Tools

Extract your own MIDI + REAPER projects from any NES game:

```bash
# Convert one song:
python scripts/nsf_to_reaper.py game.nsf 3 90 -o output/Game/

# Convert entire soundtrack:
python scripts/nsf_to_reaper.py game.nsf --all -o output/Game/ \
    --names "Track 1,Track 2,Track 3,..."

# Generate proper REAPER project from MIDI:
python scripts/generate_project.py --midi output/Game/midi/song.mid \
    --nes-native -o output/Game/reaper/song.rpp

# Batch process all NSF zips in folder:
python scripts/batch_nsf_extract.py
```

NSF files for thousands of NES games are available at [Zophar's Domain](https://www.zophar.net/music/nintendo-nes-nsf).

## WAV Audio Previews

WAV preview renders are too large for the repository. They are generated locally when you run the extraction tools.

*Coming soon: downloadable soundtrack ZIP packages via GitHub Releases.*

---

## Installation

### Requirements
- Python 3.10+
- REAPER v7+ (for .rpp projects)
- Python packages: `pip install mido numpy py65`

### Setup
```bash
git clone https://github.com/t3dy/ReapNES.git
cd ReapNES
pip install mido numpy py65
```

### Install Synth Plugin
Copy the `studio/jsfx/` folder contents to your REAPER Effects directory:
- Windows: `%APPDATA%\REAPER\Effects\ReapNES Studio\`
- Mac: `~/Library/Application Support/REAPER/Effects/ReapNES Studio/`
- Linux: `~/.config/REAPER/Effects/ReapNES Studio/`
