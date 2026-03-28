# Requirements for NES-Quality MIDI Files

What we learned the hard way about what makes a MIDI file work well
through our NES synth pipeline. Use this as a checklist when building
MIDI exports from ROM/NSF extraction.

---

## The Problem We Solved

Community MIDI transcriptions (VGMusic, etc.) are unreliable:
- Random channel assignments (ch 1,3,4 instead of 0,1,2)
- Too many channels (10+ crammed into a file)
- All parts in the same register (no bass/treble separation)
- Missing notes, wrong timing, bad arrangements
- Drum channel sometimes missing or on non-standard channels

ROM-extracted MIDI must be better than this. Here are the rules.

---

## Hard Requirements (MUST)

### 1. Exactly 4 MIDI Channels (0-3)

The NES has 5 sound channels but only 4 are relevant for MIDI:

| MIDI Channel | NES Channel | Role | Notes |
|-------------|-------------|------|-------|
| 0 | Pulse 1 | Lead melody | Square wave, 4 duty cycles |
| 1 | Pulse 2 | Harmony / counter-melody | Square wave, 4 duty cycles |
| 2 | Triangle | Bass line | Fixed waveform, no volume control |
| 3 | Noise | Drums / percussion | LFSR noise, 16 period settings |

**Never use more than 4 channels.** If the source has DMC (channel 5),
it must be handled separately or merged into the noise channel.

**Never use GM channel 9 for drums.** Use channel 3. Our pipeline can
remap channel 9 → 3, but native channel 3 is cleaner.

### 2. Register Separation Between Channels

Each channel must occupy a distinct pitch register:

| Channel | Typical Range | MIDI Note Range | Why |
|---------|--------------|-----------------|-----|
| Pulse 1 (lead) | C4-C6 | 60-84 | Melody sits in the vocal range |
| Pulse 2 (harmony) | C3-C5 | 48-72 | Below or interleaving with lead |
| Triangle (bass) | C2-C4 | 36-60 | Bass foundation, often 1-2 octaves below |
| Noise (drums) | N/A | 35-57 (GM drum map) | Pitch maps to noise period, not musical pitch |

**Minimum separation**: 6 semitones average between any two melodic channels.
**Ideal separation**: 12+ semitones between triangle and pulse channels.

If all channels are in the same register, the NES synth produces mud.

### 3. Monophonic Per Channel

Each NES channel is **strictly monophonic** — one note at a time.

- No chords on any single channel
- No overlapping notes (note-off must precede next note-on)
- If the source has polyphonic passages, they must be split across channels

**Validation rule**: For any channel, at any point in time, there must be
at most 1 active note. If two note-on events occur without an intervening
note-off, the second note-on implicitly kills the first (NES behavior).

### 4. Note-Off for Every Note-On

Every `note_on` (velocity > 0) must have a corresponding:
- `note_off` (status 0x80), OR
- `note_on` with velocity 0 (status 0x90, vel 0)

Missing note-offs cause the synth to sustain indefinitely, which is
especially bad for the triangle channel (no volume control = infinite drone).

### 5. Tempo and Timing from Frame Rate

NES music runs at 60 Hz (NTSC) or 50 Hz (PAL). All timing derives from
the frame counter.

- **Tempo** should be derived from the driver's tempo register, not guessed
- **Tick resolution**: Use 480 PPQ (standard) or higher
- **Quantization**: Notes should align to frame boundaries where possible
  (1 frame = 16.67ms at 60Hz)

If the driver uses a speed/tempo system (like FamiTracker rows/frames),
convert accurately:
```
BPM = (60 * frame_rate) / (speed * rows_per_beat)
```

### 6. Clean Note Boundaries

- Note-on and note-off should be on exact tick positions
- No zero-length notes (note-on immediately followed by note-off at same tick)
- Minimum note duration: 1 frame (approximately 17ms at 60Hz)
- Rests between notes should be explicit gaps, not overlapping note-offs

---

## Recommended (SHOULD)

### 7. Velocity Mapping

NES volume is 0-15 (4-bit). Map to MIDI velocity:

```
midi_velocity = round(nes_volume * 127 / 15)
```

| NES Volume | MIDI Velocity | Description |
|-----------|---------------|-------------|
| 15 | 127 | Maximum |
| 12 | 102 | Loud |
| 8 | 68 | Medium |
| 4 | 34 | Soft |
| 1 | 8 | Barely audible |
| 0 | 0 (note-off) | Silent |

For channels with volume envelopes, use the **attack volume** as the
note-on velocity. The envelope shape is stored in the preset, not the MIDI.

### 8. Duty Cycle as CC

Pulse channels switch duty cycles during playback. Encode as MIDI CC:

```
CC 1 (Mod Wheel):
  0-31   = 12.5% duty
  32-63  = 25% duty
  64-95  = 50% duty
  96-127 = 75% duty
```

Insert a CC 1 message before or at the same tick as any note that
changes duty cycle from the previous note.

### 9. Pitch Bend for Sweeps and Slides

NES sweep unit and programmatic pitch slides map to MIDI pitch bend:

```
Pitch bend range: +/- 2 semitones (standard)
Center: 8192
1 semitone up: 12288
1 semitone down: 4096
```

For sweep effects that exceed 2 semitones, use multiple pitch bend
messages across frames. Reset pitch bend to center (8192) before
the next note if the sweep was note-specific.

### 10. Noise Channel Drum Mapping

Map NES noise parameters to GM drum notes for our drum engine:

| NES Noise Period | NES Mode | GM Drum Note | Name |
|-----------------|----------|--------------|------|
| 13-14 | Long | 36 | Kick |
| 6-7 | Long | 38 | Snare |
| 1 | Short | 42 | Closed Hi-Hat |
| 2 | Long | 46 | Open Hi-Hat |
| 8-11 | Long | 41-45 | Toms |
| 2-3 | Long | 49/57 | Crash/Ride |

If the noise channel plays pitched noise (not drums), use regular
note numbers and set velocity for volume.

### 11. Loop Points

Many NES songs loop. Encode loop information as:

- A MIDI marker/text event at the loop start point: `text: "LOOP_START"`
- A MIDI marker/text event at the loop end point: `text: "LOOP_END"`

The REAPER project generator can use these to set the loop region.

### 12. Metadata in Track Names

```
Track 0: "Tempo/Meta"        — tempo changes, time signature, song title
Track 1: "Pulse 1 [lead]"    — channel 0
Track 2: "Pulse 2 [harmony]" — channel 1
Track 3: "Triangle [bass]"   — channel 2
Track 4: "Noise [drums]"     — channel 3
```

Include the role in brackets so the project generator can label tracks.

---

## MIDI File Template

```
MIDI Type 1 (multi-track)
PPQ: 480
Tracks: 5 (1 meta + 4 channel)

Track 0 (Meta):
  Tick 0: Time Signature 4/4
  Tick 0: Tempo (derived from driver)
  Tick 0: Text "Game: Castlevania III"
  Tick 0: Text "Song: Beginning"
  Tick 0: Text "Source: ROM static extraction"
  Tick 0: Text "Confidence: 0.85"
  Tick 0: Text "Driver: Konami Pre-VRC"
  Tick X: Text "LOOP_START"
  Tick Y: Text "LOOP_END"

Track 1 (Pulse 1, Channel 0):
  Tick 0: CC 1 value 64    (initial duty = 50%)
  Tick 0: Note On  ch=0 note=72 vel=102  (C5, loud)
  Tick 240: Note Off ch=0 note=72
  Tick 240: Note On  ch=0 note=74 vel=102  (D5)
  ...
  (strictly monophonic, one note at a time)

Track 2 (Pulse 2, Channel 1):
  Tick 0: CC 1 value 32    (initial duty = 25%)
  Tick 0: Note On  ch=1 note=60 vel=85   (C4, medium)
  ...

Track 3 (Triangle, Channel 2):
  Tick 0: Note On  ch=2 note=48 vel=127  (C3, always max — triangle has no volume)
  ...

Track 4 (Noise, Channel 3):
  Tick 0: Note On  ch=3 note=42 vel=68   (Closed HH, medium)
  Tick 120: Note Off ch=3 note=42
  Tick 120: Note On  ch=3 note=36 vel=102 (Kick, loud)
  ...
```

---

## Validation Checklist

Run these checks on every extracted MIDI before delivering:

```
[ ] Exactly 4 note channels (0-3), no others
[ ] No polyphony on any single channel
[ ] Every note-on has a matching note-off
[ ] Triangle channel (2) uses velocity 127 for all notes
[ ] Noise channel (3) uses GM drum note range 35-57 for drums
[ ] Register separation >= 6 semitones between melodic channels
[ ] Tempo derived from driver, not guessed
[ ] No zero-length notes
[ ] Metadata track includes game, song, source, confidence
[ ] Loop points marked if song loops
[ ] Total channel count <= 4 (excluding meta track)
```

Our `scripts/validate.py --midi` checks most of these automatically.

---

## Anti-Patterns (NEVER Do These)

1. **Never use GM channel 9 for drums** — use channel 3
2. **Never put all channels in the same octave** — separate by register
3. **Never leave notes sustaining across phrase boundaries** — explicit note-offs
4. **Never guess the tempo** — derive from driver speed/tempo registers
5. **Never include channels the NES doesn't have** — max 4 channels
6. **Never use chords on a single channel** — NES is monophonic per channel
7. **Never omit provenance metadata** — always include source game/song/confidence
