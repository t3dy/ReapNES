# NES Percussion and DPCM Models

Research catalog of percussion implementations in NES sound drivers,
focused on the Konami Maezawa driver family used by Castlevania 1 and
Contra. Written to inform pipeline decisions in midi_export.py and
frame_ir.py.

---

## NES Percussion Hardware

The NES APU provides two channels relevant to percussion:

**Noise channel ($400C-$400F)**
- $400C: --LC VVVV (length counter halt, constant volume, volume/envelope)
- $400E: M---PPPP (mode flag, period index)
- $400F: LLLLL--- (length counter load)
- Mode 0 = long-loop pseudo-random noise (white noise character)
- Mode 1 = short-loop (93-step), metallic/tonal quality
- 16 period values control pitch. Lower period = higher frequency.
- No pitch in the melodic sense; frequency controls timbre (hiss vs rumble).

**Delta Modulation Channel (DMC, $4010-$4013)**
- $4010: IL--RRRR (IRQ enable, loop, rate index)
- $4011: -DDDDDDD (direct load / DAC value)
- $4012: AAAAAAAA (sample address = $C000 + A * 64)
- $4013: LLLLLLLL (sample length = L * 16 + 1 bytes)
- Plays 1-bit delta-encoded samples from ROM.
- 16 rate settings: 4181 Hz to 33144 Hz (NTSC).
- Samples must reside at $C000-$FFFF (last 16KB of CPU address space).
- Each sample byte encodes 8 1-bit deltas. Output steps +/- 2 per bit.

---

## Model 1: Inline Triggers (CV1)

**Used by**: Castlevania 1 (and likely Super C, Goonies II)

### Encoding

Percussion is embedded in melodic channel streams using special
E-commands:

```
E9 = trigger snare drum (calls sound routine with value 2)
EA = trigger hi-hat drum (calls sound routine with value 1)
```

These bytes appear immediately after a note command in the data
stream. The parser reads a note, then checks if the next byte is
E9 or EA. If so, the drum fires alongside the note.

### Timing Behavior

Inline triggers do NOT consume their own duration slot. They
piggyback on the preceding note's duration. The drum sounds for a
hardware-determined length (the noise channel's envelope), not for
the note's frame count.

This means:
- Drums never cause timing gaps in the melodic stream
- A channel can play a note and trigger a drum simultaneously
- Drum density is limited to one trigger per note event
- There is no independent percussion rhythm; drums are subordinate
  to the melodic timing grid

### Hardware Effect

E9 and EA call the sound engine's noise channel routines directly:
- E9 writes to $400C-$400F to produce a short noise burst (snare)
- EA writes to $400C-$400F with different period/mode (hi-hat)

CV1 does NOT use DPCM samples for percussion. All drums are pure
noise channel synthesis.

### Limitations

- Only 2 drum sounds (snare and hi-hat). No kick drum.
- Drums are tied to note positions in pulse/triangle channels.
  No independent drum pattern is possible.
- The noise channel has no dedicated data stream; it is driven
  entirely by E9/EA triggers from the melodic channels.
- If no note plays, no drum can fire (unless E9/EA appears
  standalone, which the parser handles as a fallback).

### In APU Traces

Noise channel ($400C-$400F) shows brief activity bursts correlated
with note events on other channels. No continuous noise pattern
exists; activity is sparse and event-driven.

---

## Model 2: Dedicated Channel Stream (Contra)

**Used by**: Contra, and likely other later Konami titles

### Encoding

Contra allocates sound slot 3 as a full percussion channel with its
own data stream pointer in the track table. Each track entry has 4
pointers: sq1, sq2, tri, noise (vs CV1's 3: sq1, sq2, tri).

The percussion command format:

```
High nibble (0-B): percussion sample selector
Low nibble (0-F): duration multiplier (same formula as notes)

Duration = SOUND_LENGTH_MULTIPLIER * (low_nibble + 1)
```

Special high nibbles:
- $Dx: set SOUND_LENGTH_MULTIPLIER (tempo), then read next command
- $Fx: control flow (FD=subroutine, FE=repeat, FF=end)
- $Cx: rest/silence (high nibble $C = no percussion hit)

### Sample Dispatch via percussion_tbl

The high nibble indexes into an 8-entry lookup table at CPU $82CD:

```
percussion_tbl: $02, $5a, $5b, $5a, $5b, $25, $5c, $5d

Index 0: sound_02 (bass drum - noise channel burst)
Index 1: sound_5a (DMC hi-hat sample)
Index 2: sound_5b (DMC snare sample)
Index 3: sound_5a + sound_02 (hi-hat + bass drum)
Index 4: sound_5b + sound_02 (snare + bass drum)
Index 5: sound_25 (noise explosion)
Index 6: sound_5c + sound_02 (DMC hi-hat variant + bass drum)
Index 7: sound_5d + sound_02 (DMC sample + bass drum)
```

For indices >= 3, the engine also calls sound_02 (bass drum) as a
second hit, creating layered kick+snare or kick+hihat combinations.
This is a hybrid noise+DPCM system (see Model 5 below).

### Timing Behavior

Unlike CV1's inline model, Contra percussion events DO consume
their own duration slot. The percussion channel has independent
timing:
- It has its own SOUND_LENGTH_MULTIPLIER (set by $Dx commands)
- Duration is calculated identically to melodic notes
- The channel advances through its data stream at its own pace
- Percussion patterns are fully independent of melodic rhythm

### In APU Traces

Both noise and DMC channels show activity. Noise bursts appear for
kick drum (sound_02) hits. DMC channel ($4010-$4013) activates for
sampled sounds ($5a-$5d). The two can fire simultaneously for
layered hits.

---

## Model 3: DPCM Sample System (Contra Detail)

### Sample Storage

Contra stores DPCM samples in the fixed bank (bank 7) at CPU
$FC00-$FFD0. The linker config allocates a dedicated DPCM_SAMPLES
segment:

```
DPCM_SAMPLES: start = $FC00, size = $03D0
```

Two physical samples exist in the ROM:
- `dpcm_sample_00` at $FC00 (81 bytes = 648 delta bits)
- `dpcm_sample_01` at $FCC0 (593 bytes = 4744 delta bits)

### Sample Configuration Table (dpcm_sample_data_tbl)

Each entry is 4 bytes mapping to APU registers:

```
Byte 0 -> $4010 (APU_DMC): rate + loop flag
Byte 1 -> $4011 (APU_DMC_COUNTER): initial DAC value
Byte 2 -> $4012 (APU_DMC_SAMPLE_ADDR): address = $C000 + val * 64
Byte 3 -> $4013 (APU_DMC_SAMPLE_LEN): length = val * 16 + 1
```

Contra's entries:

| Sound Code | Rate | Counter | Address | Length | Description |
|-----------|------|---------|---------|--------|-------------|
| $5a | $0F (33kHz) | $2F | $F0 ($FC00) | $05 (81 bytes) | Hi-hat |
| $5b | $0F (33kHz) | $75 | $F3 ($FCC0) | $25 (593 bytes) | Snare |
| $5c | $0F (33kHz) | $00 | $F0 ($FC00) | $05 (81 bytes) | Hi-hat variant |

All samples use the maximum rate ($0F = 33,143.9 Hz NTSC). The
counter value ($4011) sets the initial DAC level, which affects the
DC offset and perceived volume of the sample.

### Sound Code Routing

The engine routes sound codes >= $5A to `play_dpcm_sample`. The
offset into dpcm_sample_data_tbl is computed as:
`(sound_code - $5A) * 4`

Sound codes < $5A route to the general sound table (sound_table_00)
for noise-channel and melodic sounds.

### Sample Quality

At 33 kHz with 1-bit delta encoding, quality is extremely limited:
- 81 bytes = ~2.4 ms of audio (hi-hat click)
- 593 bytes = ~17.9 ms of audio (snare crack)
- The 1-bit delta means the output can only move +2 or -2 per
  sample, creating a heavily quantized waveform.
- DC offset drift is inherent to delta modulation (no reset
  mechanism between samples).

---

## Model 4: Noise Channel as Percussion (General NES Pattern)

Many NES drivers use the noise channel alone for all percussion,
without DPCM. This is simpler than either CV1's inline model or
Contra's dedicated stream.

### Common Approach

- Noise channel gets its own data stream (like Contra)
- Commands set period ($400E) and volume envelope ($400C)
- Short-loop mode (bit 7 of $400E) for metallic timbres
- Long-loop mode for white-noise-like sounds
- Period value controls "pitch": low period = high hiss, high
  period = low rumble
- Volume envelope (hardware or software) controls duration

### Typical Drum Sounds

| Sound | Mode | Period | Envelope |
|-------|------|--------|----------|
| Kick | Long loop | High (8-12) | Fast decay, high initial vol |
| Snare | Long loop | Mid (3-6) | Medium decay |
| Hi-hat | Short loop | Low (0-2) | Very fast decay |
| Tom | Long loop | Mid-high (6-9) | Medium decay |

CV1's sound_02 (bass drum) uses this approach: a short noise burst
on the noise channel with specific period and envelope values.

---

## Model 5: Hybrid Systems (Noise + DPCM Together)

Contra is the primary example in our codebase. Its percussion
channel fires BOTH noise and DPCM simultaneously:

### Layering Mechanism

When percussion_tbl index >= 3, the engine:
1. Plays the DMC sample (sound_5a/5b/5c/5d) via play_sound
2. Then plays sound_02 (noise channel bass drum) via a second
   play_sound call

This creates a layered hit: the DPCM provides the sharp attack
transient (sampled hi-hat or snare) while the noise channel
provides the low-frequency body (kick drum rumble).

### Why Hybrid?

- DPCM has better transient detail (sampled attack)
- Noise channel has better low-frequency content
- Combined, they produce fuller drum sounds than either alone
- The DPCM samples are tiny (81-593 bytes) and lack bass content
- The noise burst fills in what the samples lack

### Channel Interaction

The noise channel and DMC are independent hardware. They can
play simultaneously without conflict. However:
- Both contribute to the final mixed output
- The DMC's output amplitude is fixed by the sample data
- The noise channel's volume is controllable per frame
- Balancing requires knowing both are active

---

## Model 6: DPCM DMA Conflicts

### The Hardware Problem

When the DMC channel plays a sample, it performs DMA reads that
steal CPU cycles. Each DMA read takes 4 CPU cycles and occurs
every N cycles (where N depends on the rate setting). At the
maximum rate ($0F, 33 kHz), this means a DMA read roughly every
54 CPU cycles.

### Effects on Other Channels

- **APU register write corruption**: If a CPU write to an APU
  register coincides with a DMC DMA read, the write can be
  delayed or lost. This can cause audible glitches on pulse and
  triangle channels (wrong period for one frame, clicks).
- **Controller read corruption**: DPCM DMA during controller
  polling can cause phantom button presses. Some games disable
  DPCM during input reads.
- **Timing jitter**: Frame-critical code can be disrupted by
  the stolen cycles.

### How Drivers Handle It

**Contra**: Largely ignores the problem. The engine writes APU
registers without DMC-aware timing. The init_dmc_sample_value
routine resets APU_DMC_COUNTER to 0 before starting certain
songs (jungle, waterfall), which reduces DC offset issues but
does not address DMA conflicts.

**CV1**: Avoids the problem entirely by not using DPCM. All
percussion is noise-channel only, so no DMA occurs during music
playback.

**General NES practice**: Some later drivers (e.g., FamiTracker-
based engines) use careful timing to avoid writing APU registers
during DMC DMA windows. Others accept occasional glitches as
inaudible or masked by the percussion itself.

### Impact on Extraction

DPCM DMA conflicts are a hardware timing issue. They do not
affect the extracted music data. However, they can affect:
- APU trace accuracy (Mesen traces may or may not model DMA
  cycle stealing perfectly)
- Audio rendering fidelity if we attempt cycle-accurate playback

---

## MIDI Mapping

### Current Implementation (midi_export.py)

Drums are exported on MIDI channel 3 (0-indexed), NOT channel 10
(the GM percussion convention). This is a pragmatic choice for
REAPER workflows where channel 10 routing adds complexity.

```python
DRUM_CHANNEL = 3
DRUM_NOTES = {
    "snare": 38,    # GM Acoustic Snare
    "hihat": 42,    # GM Closed Hi-Hat
}
```

### CV1 Mapping

Only two drum types exist (snare and hihat). They map directly
to GM percussion notes. Drums are collected by scanning all
channels for DrumEvent instances and placing them on a single
drum track.

### Contra Mapping

Contra has richer percussion. The contra_parser.py maps high
nibble values to drum types:

| High Nibble | Type | Current Mapping |
|-------------|------|-----------------|
| 0 | kick | "kick" |
| 1 | snare | "snare" |
| 2 | hihat | "hihat" |
| 3 | kick+snare | "kick_snare" |
| 4 | kick+hihat | "kick_hihat" |
| 5 | snare (alt) | "snare" |
| 6 | kick+snare (alt) | "kick_snare" |
| 7 | kick+snare (alt) | "kick_snare" |

The combined types (kick_snare, kick_hihat) represent the hybrid
noise+DPCM layering. In MIDI, these should ideally produce two
simultaneous notes (e.g., kick + snare at the same tick).

### Gap: Missing GM Mappings

midi_export.py's DRUM_NOTES dict only has "snare" and "hihat".
Contra's "kick", "kick_snare", and "kick_hihat" types will fall
through to the default (38 = snare). This needs extension:

```
Proposed additions:
  "kick": 36       # GM Bass Drum 1
  "kick_snare": [36, 38]  # simultaneous kick + snare
  "kick_hihat": [36, 42]  # simultaneous kick + hihat
```

---

## How Percussion Flows Through the Pipeline

### Parser Stage

**CV1 (parser.py)**: After parsing a note command, checks if the
next byte is E9 or EA. If so, emits a DrumEvent with the
preceding note's duration_frames. DrumEvents are interleaved in
the melodic channel's event list.

**Contra (contra_parser.py)**: The noise channel gets its own
ContraChannelParser instance with `is_noise=True`. The
`_parse_percussion()` method handles the different byte format
(high nibble = sample, low nibble = duration). DrumEvents are
emitted into a dedicated noise ChannelData.

### Frame IR Stage (frame_ir.py)

Percussion is explicitly skipped:
```
if ch_type == "noise":
    continue  # noise/drums go straight to MIDI, not through frame IR
```

This means drums have no per-frame volume automation. They are
passed directly from parser events to MIDI export. This is
acceptable because:
- NES drum sounds are short (< 10 frames typically)
- Hardware envelopes handle the decay
- Per-frame volume control adds little to percussion

### MIDI Export Stage (midi_export.py)

Drums are collected in a post-processing pass after the melodic
tracks are built from the frame IR. The exporter:
1. Walks all channels looking for DrumEvent instances
2. Converts frame positions to MIDI ticks
3. Emits note_on/note_off pairs on DRUM_CHANNEL
4. For CV1: advances abs_frame only for NoteEvent/RestEvent
   (drums piggyback on note timing)
5. For Contra: the noise channel's DrumEvents advance
   abs_frame by their own duration_frames

### WAV Render Stage (render_wav.py)

Uses `render_noise_hit()` to synthesize percussion:
- White noise with optional low-pass filtering
- Volume decay envelope
- No DPCM sample playback (samples are not decoded)

---

## Implications for the Pipeline

### What Works Now

1. CV1 inline drums (E9/EA) parse correctly and export to MIDI
2. Contra dedicated percussion channel parses correctly
3. Basic snare/hihat mapping to GM notes
4. Drum timing is correct for both models

### What Needs Work

1. **Contra drum type expansion**: DRUM_NOTES needs kick, kick_snare,
   kick_hihat mappings. Combined types should emit multiple
   simultaneous MIDI notes.

2. **DPCM sample decoding**: render_wav.py synthesizes noise but
   does not decode actual DPCM samples. For accurate Contra
   drum rendering, the pipeline would need to:
   - Read dpcm_sample_data_tbl from ROM
   - Extract raw sample bytes from the DPCM_SAMPLES region
   - Decode 1-bit delta encoding to PCM
   - Mix decoded samples into the WAV output

3. **Noise channel parameters**: The pipeline does not currently
   extract noise period or mode values from the ROM. All noise
   hits use the same synthesized white noise. Accurate rendering
   would need per-hit period and mode from the driver's sound
   data tables.

4. **Frame IR bypass**: The decision to skip noise in frame_ir.py
   is correct for short percussive hits but may miss longer noise
   patterns (e.g., sound_25 explosion effect in Contra).

---

## Failure Risks If Misunderstood

### Risk 1: Treating Inline Drums as Independent Events

If the parser treats E9/EA as consuming their own duration (like
a note), the timing of the entire channel will shift. Every drum
trigger would insert a phantom gap in the melodic stream.

**Symptom**: Notes after drum hits play late; song gradually
drifts out of sync.

**Prevention**: The parser correctly treats E9/EA as zero-duration
side effects of the preceding note.

### Risk 2: Applying CV1 Percussion Model to Contra

CV1 has no dedicated percussion channel. Contra does. If a parser
assumes inline triggers for Contra, it will:
- Miss the entire percussion data stream
- Potentially misparse noise channel data as melodic commands
- Produce silent or garbled drum output

**Prevention**: Check percussion format in the manifest before
parsing. The spec.md per-game table documents this difference.

### Risk 3: Ignoring Hybrid Layering

Contra's combined hits (kick_snare, kick_hihat) fire two sound
channels simultaneously. If the MIDI export only emits one note
per DrumEvent, the kick component is lost for combined hits.

**Symptom**: Percussion sounds thin; kick drum is missing from
patterns that should have it.

**Prevention**: Extend DRUM_NOTES to handle combined types as
multi-note events.

### Risk 4: DPCM Address Assumptions

DPCM samples must reside at $C000-$FFFF. Different games put
samples in different banks. Contra uses bank 7 (fixed bank).
Other games may use switchable banks, meaning the sample address
in $4012 resolves to different ROM locations depending on the
current bank configuration.

**Symptom**: Extracted samples contain garbage data (wrong ROM
region).

**Prevention**: Always resolve DPCM addresses through the game's
specific banking/mapper configuration, not by assuming linear
ROM layout.

### Risk 5: Confusing Noise Period with Pitch

The noise channel's period register does not map to musical pitch
in the conventional sense. Treating noise period values like note
periods would produce meaningless MIDI note numbers.

**Prevention**: Always map noise/drum events to GM percussion
notes by type (kick/snare/hihat), never by computing pitch from
the noise period register.

---

## Summary Table

| Aspect | CV1 (Inline) | Contra (Dedicated) |
|--------|-------------|-------------------|
| Percussion data location | Embedded in melodic streams | Separate 4th channel pointer |
| Drum trigger format | E9 (snare), EA (hihat) | High nibble = sample index |
| Duration slot consumed | No (piggybacks on note) | Yes (own timing) |
| Available sounds | 2 (snare, hihat) | 8 (via percussion_tbl) |
| Noise channel used | Yes (E9/EA fire noise regs) | Yes (sound_02 bass drum) |
| DPCM used | No | Yes (sound_5a-5d) |
| Hybrid layering | No | Yes (indices >= 3) |
| Independent rhythm | No (tied to notes) | Yes (own data stream) |
| Frame IR processing | Skipped (DrumEvent passthrough) | Skipped (DrumEvent passthrough) |
| MIDI channel | 3 (non-GM) | 3 (non-GM) |
