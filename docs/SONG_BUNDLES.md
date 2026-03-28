# Song Bundles (Song Sets)

## What Is a Song Bundle?

A song bundle is a JSON file that describes a complete NES instrument palette for a specific song or game context. It maps NES channels to specific presets and includes metadata about the source.

## Available Song Sets

| File | Game | Song | Source | Channels |
|------|------|------|--------|----------|
| `smb1_overworld` | Super Mario Bros. | Overworld (1-1) | hand-authored | P1, P2, Tri, Noise |
| `smb1_underground` | Super Mario Bros. | Underground (1-2) | hand-authored | P1, P2, Tri, Noise |
| `mm2_wily1` | Mega Man 2 | Dr. Wily Stage 1 | nes-mdb-extracted | P1, P2, Noise |
| `cv1_wicked_child` | Castlevania | Wicked Child | nes-mdb-extracted | P1, P2, Noise |
| `cv3_beginning` | Castlevania III | Beginning | nes-mdb-extracted | P1, P2 |
| `silius_stage2` | Journey to Silius | Stage 2 | nes-mdb-extracted | P1, P2, Noise |

## Confidence Levels

Song sets carry a `provenance.confidence` field:

- **hand-authored**: Manually crafted to approximate the game's sound. Not ROM-extracted. Good for general feel, not exact reproduction.
- **nes-mdb-extracted / approximate**: Auto-generated from the NES-MDB corpus. Instruments selected by highest note-count. Reasonable approximation but may not match exactly what the hardware plays.
- **verified**: Confirmed against hardware recordings. (None exist yet.)

## Creating a Song Set

### From the Extracted Corpus

```bash
# Find the game and song you want
python scripts/preset_catalog.py songs --game Castlevania

# Export as a song set
python scripts/preset_catalog.py export --game CastlevaniaIII --song "08MadForest"
```

### By Hand

Copy this template to `song_sets/my_song.json`:

```json
{
  "format": "reapnes-song-set",
  "version": 1,
  "game": {
    "title": "Game Name",
    "developer": "Developer",
    "year": 1988,
    "platform": "NES"
  },
  "song": {
    "title": "Song Title",
    "context": "Level or screen where this plays",
    "tempo_bpm": 140
  },
  "provenance": {
    "source": "hand-authored",
    "confidence": "approximate",
    "notes": "Your notes about accuracy"
  },
  "channels": {
    "pulse1": {
      "role": "lead",
      "preset": "generic/pulse_lead_50.reapnes-data",
      "description": "Main melody"
    },
    "pulse2": {
      "role": "harmony",
      "preset": "generic/pulse_lead_25.reapnes-data",
      "description": "Counter-melody"
    },
    "triangle": {
      "role": "bass",
      "preset": "generic/tri_bass.reapnes-data",
      "description": "Bassline"
    },
    "noise": {
      "role": "percussion",
      "preset": "generic/noise_snare.reapnes-data",
      "description": "Drums"
    }
  },
  "drum_map": {
    "36": { "preset": "generic/noise_kick.reapnes-data", "description": "Kick" },
    "38": { "preset": "generic/noise_snare.reapnes-data", "description": "Snare" },
    "42": { "preset": "generic/noise_hihat_closed.reapnes-data", "description": "Hi-hat" }
  }
}
```

Preset paths are relative to `presets/`. Use `generic/`, `mario/`, or `jsfx_data/` prefixes.

## Song Set Schema

The full JSON Schema is at `song_sets/song_set_schema.json`. Key fields:

- `game.title`: Game name
- `song.title`: Song or track name
- `song.tempo_bpm`: Suggested tempo
- `provenance.source`: Where the data came from
- `provenance.confidence`: How accurate it is
- `channels.{pulse1,pulse2,triangle,noise}`: Per-channel instrument assignments
- `drum_map`: MIDI note → noise preset mapping for percussion
