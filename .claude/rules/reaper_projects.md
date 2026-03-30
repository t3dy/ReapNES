# REAPER Project Requirements

When generating .rpp files, ALWAYS use `scripts/generate_project.py`
with the `--midi` and `--nes-native` flags. NEVER write bare-bones
RPP files manually.

## What a working REAPER project needs

1. **RPP v7 format** with proper header (RIPPLE, AUTOXFADE, TEMPO, etc.)
2. **GUID-based IDs** on every TRACK and ITEM (use uuid.uuid4())
3. **FXCHAIN block** per track with `<JS "ReapNES Studio/ReapNES_APU.jsfx">`
4. **64 slider parameters** for the JSFX (duty, volume, enable, channel mode)
5. **Per-channel slider config**: Channel Mode 0=P1, 1=P2, 2=Tri, 3=Noise
6. **MIDI item** with absolute FILE path, POSITION, LENGTH, LOOP 0
7. **Track colors**: pulse1=16576606, pulse2=10092441, triangle=16744192, noise=11184810
8. **Track naming**: "NES - Pulse 1", "NES - Pulse 2", "NES - Triangle", "NES - Noise / Drums"

## Command to generate

```bash
python scripts/generate_project.py --midi <midi_file> --nes-native -o <output.rpp>
```

## What the MIDI must contain

- Track 0: metadata (tempo, game name, song name, source)
- Track 1: Square 1 (channel 0) with CC11 (volume) and CC12 (duty cycle)
- Track 2: Square 2 (channel 1) with CC11 and CC12
- Track 3: Triangle (channel 2) with CC11
- Track 4: Noise (channel 3) with drum note mapping

## NEVER do this

- Write RPP files with just `<SOURCE WAVE>` and no synth
- Write RPP files without FXCHAIN blocks
- Write RPP files without GUIDs
- Skip the generate_project.py script
- Forget CC11/CC12 automation in the MIDI
