# MIDI Import & NES Remapping

## Overview

ReapNES Studio can take any MIDI file and map it onto NES-style instruments, generating a REAPER project ready to play.

## Quick Start

```bash
# Auto-map a MIDI file using Mega Man 2 instruments
python scripts/generate_project.py --song-set mm2_wily1 --midi path/to/beethoven.mid
```

Open the generated `.rpp` in REAPER — MIDI items are already placed on tracks with NES instruments loaded.

## Auto-Mapping Rules

When no mapping config is provided, the system analyzes MIDI tracks and assigns them:

| Priority | Detection | NES Channel |
|----------|-----------|-------------|
| 1 | MIDI channel 10 (GM drums) | Noise |
| 2 | Lowest average pitch melodic track | Triangle (bass) |
| 3 | Highest note-count melodic track | Pulse 1 (lead) |
| 4 | Second busiest melodic track | Pulse 2 (harmony) |

Tracks that don't fit are dropped. The NES has 4 channels — this is a fundamental constraint.

## Custom Mapping

Create a mapping config JSON:

```json
{
  "format": "reapnes-midi-mapping",
  "version": 1,
  "channel_map": {
    "pulse1": 0,
    "pulse2": 1,
    "triangle": 2,
    "noise": 9
  }
}
```

Values are MIDI track indices (0-based). Use:

```bash
python scripts/generate_project.py --song-set mm2_wily1 --midi file.mid --mapping my_map.json
```

See `examples/midi_mapping_example.json` for a full template with documentation.

## NES Channel Constraints

The NES APU imposes real musical constraints:

| Channel | Notes | Volume | Timbre |
|---------|-------|--------|--------|
| Pulse 1 | Monophonic | 16 levels (0-15) | 4 duty cycles |
| Pulse 2 | Monophonic | 16 levels (0-15) | 4 duty cycles |
| Triangle | Monophonic | Fixed (no control) | Fixed waveform |
| Noise | Monophonic | 16 levels (0-15) | 16 periods, 2 modes |

**Monophonic**: Each channel plays one note at a time. Polyphonic MIDI tracks will lose notes — the newest note wins.

**Volume**: MIDI velocity (0-127) maps to NES volume (0-15) via `floor(velocity / 127 * 15)`.

**Range**: Pulse channels can produce ~54 Hz to ~12.4 kHz. Triangle goes one octave lower. Notes outside range will sound wrong or be silent.

## Practical Tips

1. **Simplify first**: Reduce your MIDI to 4 parts before importing. The NES doesn't do orchestras.
2. **Bass to triangle**: Triangle has a warm, round tone — perfect for bass lines. It has no volume control, so dynamics come from note length only.
3. **Drums to noise**: The noise channel is limited but effective for hi-hats, snares, and kicks. Complex drum patterns will lose detail.
4. **Leads to pulse**: The pulse channels are the most expressive, with duty cycle and volume control. Assign your most important melodic parts here.
5. **Edit after import**: The generated project is a starting point. Open it in REAPER and edit MIDI, adjust presets, tweak envelopes.

## What's Not Yet Implemented

- **Automatic polyphony reduction**: You need to reduce chords to single notes manually
- **Note range clamping**: Notes outside NES range are passed through (may sound wrong)
- **Velocity curve adjustment**: Direct linear mapping from MIDI velocity to NES volume
- **Interactive mapping UI**: Currently CLI-only with config files
