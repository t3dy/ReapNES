# NES Sound Driver Envelope Systems — Taxonomy

This document catalogs envelope system types across NES sound drivers,
with emphasis on how each type affects our extraction pipeline
(frame_ir.py, MIDI export, trace validation).

---

## 1. Parametric Envelopes (CV1 Model)

### How It Works

The Konami Maezawa driver in Castlevania 1 uses a two-phase parametric
envelope defined by three values embedded in the DX instrument command:

- **initial_volume** (4 bits, 0-15): from the instrument byte ($4000 format DDLCVVVV)
- **fade_start** (4 bits, high nibble of fade byte): frames of 1/frame attack decay
- **fade_step** (4 bits, low nibble of fade byte): frames of 1/frame release at note end

No ROM tables are involved. The entire envelope shape is derived from
these two bytes at runtime.

### Envelope Shape

```
vol ---+
       | Phase 1: -1/frame for fade_start frames (attack decay)
       +-------- Hold at (vol - fade_start) --------+
                                                      | Phase 2: -1/frame
                                                      | for fade_step frames
                                                      +---- 0
       |<- fade_start ->|<-------- hold -------->|<- fade_step ->|
```

Phase 2 starts at `max(1, duration - fade_step)` frames from the note
start. If fade_step is 0, the note holds indefinitely (no release).

### ROM Storage

Two bytes per instrument change, inline in the command stream after
the DX tempo/instrument command:

```
DX II FF
     ^^ ^^
     |  +-- fade byte: high nibble = fade_start, low nibble = fade_step
     +----- instrument byte: duty(2) + flags(2) + volume(4)
```

Triangle channels skip the fade byte entirely -- they use the hardware
linear counter ($4008) for gating instead.

### Interaction with Note Duration

The envelope is computed fresh for each note event. Duration is
`tempo * (duration_nibble + 1)` frames. The hold phase absorbs whatever
frames remain between the end of Phase 1 and the start of Phase 2.
Short notes may have Phase 1 and Phase 2 overlap, producing a straight
decay with no hold.

### APU Trace Signature

- $4000/$4004 volume field decrements by 1 per frame during active phases
- Volume holds constant during the hold phase
- Volume reaches 0 at or near the note boundary
- No register writes between frames during hold (driver skips writes when volume unchanged)

### MIDI Mapping

- CC11 (Expression): per-frame volume automation, scaled 0-15 to 0-127
- Note velocity: set from initial_volume
- Note duration: truncated to sounding frames (where volume > 0)
- Silent tail frames emitted as gaps for staccato articulation

### Limitations

- Only 16 volume levels (4-bit). Coarse dynamics.
- No attack phase (volume starts at max, immediately decays).
- fade_start and fade_step are both 4-bit, so maximum 15 frames each.
- No per-instrument variation beyond these two parameters -- all timbral
  difference comes from duty cycle selection.

### Verified Status

Zero pitch mismatches, fewer than 0.5% volume mismatches across 1792
frames of Vampire Killer. See `docs/HANDOVER_FIDELITY.md`.

---

## 2. Lookup Table Envelopes (Contra Model)

### How It Works

Contra stores volume envelope shapes as byte sequences in ROM. A pointer
table (`pulse_volume_ptr_tbl` at CPU $8001 in bank 1) holds 54 entries
(8 envelopes per level, organized by game level). Each pointer references
a sequence of volume values terminated by $FF.

The DX instrument command includes a `vol_env_index` that selects which
table entry to use. The driver steps through the table one entry per
frame, writing each value to $4000/$4004.

### Envelope Shape

Arbitrary -- each table defines its own contour. Common patterns include:

- **Sharp attack**: high initial values, quick decay to sustain
- **Swell**: low start, rising to peak, then decay
- **Staccato**: a few high frames then immediate zero
- **Sustained**: constant volume for many frames

After the table ends ($FF terminator), the driver holds the last table
value as a sustain level.

### Decrescendo Tail

Contra adds a "decrescendo" system on top of the table envelope. When
the remaining frames in a note drop below a threshold computed as
`(decrescendo_mul * duration) >> 4`, the driver switches to 1/frame
volume decay (with a "bounce at 1" behavior -- volume holds at 1 rather
than reaching 0, then drops to 0 at note end).

### Auto-Decrescendo Mode

When the vol_env_index has bit 7 set (no table), the driver uses a
simpler mode: decay 1/frame for `vol_duration` frames (low nibble of
the envelope byte), hold, then resume decrescendo at the tail threshold.
This is structurally similar to CV1's parametric model but with
different parameter encoding.

### ROM Storage

```
pulse_volume_ptr_tbl:   ; 54 x 2-byte pointers (CPU addresses)
  .addr env_00, env_01, env_02, ...

env_00:                 ; volume sequence
  .byte $0F, $0E, $0D, $0C, $0B, $0A, $09, $FF  ; linear decay, 7 frames
env_01:
  .byte $0F, $0F, $0F, $0E, $0C, $09, $05, $FF  ; slow attack, fast release
```

Each byte: low 5 bits = volume value (0-31, though APU only uses 0-15).
Our extraction masks with `& 0x1F`.

### Interaction with Note Duration

Table playback and decrescendo tail are both duration-aware. The table
runs from frame 0; the decrescendo activates based on remaining frames.
If the note is shorter than the table, only the first N entries are used.

### APU Trace Signature

- $4000/$4004 volume changes every frame during table playback (non-monotonic
  changes are possible -- swells, wobbles)
- Volume holds steady after table ends
- Late-note 1/frame decay indicates decrescendo activation
- Volume may "bounce" at 1 before final silence

### MIDI Mapping

Same as parametric: CC11 per-frame automation. The richer envelope shapes
mean CC11 curves are more varied than CV1's simple linear decays.

### Limitations

- Tables are per-level, not per-instrument. The same instrument index
  points to different tables depending on which game level is active.
  Our extraction currently uses a single level's tables.
- 54 tables is a lot of data to validate. Each needs trace comparison.
- The decrescendo threshold formula `(mul * dur) >> 4` is derived from
  disassembly but marked PROVISIONAL -- not yet fully trace-validated.

### Verified Status

96.6% volume match on Jungle pulse channels (2976 frames). Table
extraction verified. Decrescendo model provisional.

---

## 3. Hardware Envelopes (APU Native)

### How It Works

The NES APU has built-in envelope and length counter hardware in
registers $4000/$4004 (pulse) and $400C (noise). When bit 4 (constant
volume flag) is CLEAR, the APU runs its own volume envelope:

- **Decay rate**: bits 0-3 set the period of the internal divider
- **Loop flag** (bit 5): if set, envelope loops; if clear, it decays
  to 0 and stops
- **Length counter**: register $4003/$4007 bits 3-7 load a length value
  from a lookup table. When the counter expires, the channel silences.

### Who Uses This

Some simpler or early NES drivers let the hardware handle envelope
entirely. This is common in:

- Very early NES titles (1985-1986) before sophisticated sound engines
- Games where the programmer wrote sound code directly rather than
  using a reusable driver
- SFX channels (even in games with software envelopes for music)

The CV1 Maezawa driver sets bit 4 (constant volume) and manages volume
in software. The E8 command may relate to toggling between hardware and
software envelope modes, though this is not fully confirmed.

### ROM Storage

No tables needed. The envelope parameters are encoded in the $4000
register write:

```
$4000: DDLCVVVV
  DD = duty cycle
  L  = length counter halt
  C  = constant volume (1 = use VVVV as volume; 0 = use as decay rate)
  VVVV = volume OR decay rate
```

### Interaction with Note Duration

Hardware envelopes run independently of the driver's note duration
tracking. The length counter provides its own note cutoff mechanism.
This creates a potential conflict: the driver may consider a note
"active" while the hardware has already silenced it, or vice versa.

### APU Trace Signature

- Volume changes happen at sub-frame rate (240Hz envelope clock vs 60Hz
  frame rate) -- trace data sampled at frame rate will miss intermediate
  steps
- Decay is always exponential-looking at frame rate (multiple decrements
  per frame at fast rates)
- Length counter cutoff appears as abrupt silence mid-note

### MIDI Mapping

Challenging. The sub-frame timing means CC11 automation at 60Hz cannot
perfectly represent the envelope. Best approach: sample the effective
volume at each frame boundary and emit CC11 from that.

### Limitations

- Only 16 decay rates, all producing the same exponential shape
- No attack, no sustain level control, no release phase
- Length counter values are from a fixed ROM table (not arbitrary)
- Cannot produce arbitrary envelope shapes

---

## 4. Hybrid Systems

### How They Work

Many commercial NES drivers combine hardware and software envelope
control. Common patterns:

**Software volume + hardware length counter**: The driver writes volume
per frame (software envelope) but also loads the length counter for
automatic note cutoff. CV1's triangle channel is an example -- the
linear counter ($4008) provides hardware gating while the driver manages
note scheduling.

**Hardware envelope with software override**: The driver starts a note
with hardware envelope enabled, then takes over volume control after a
certain number of frames (e.g., for a sustain phase the hardware cannot
produce).

**Per-channel split**: Pulse channels use software envelopes; triangle
uses hardware linear counter; noise uses hardware length counter. This
is the CV1 model -- each channel type has a different envelope strategy.

### ROM Storage

Varies. Typically the instrument definition includes flags indicating
which mode to use, plus parameters for whichever mode is active.

### APU Trace Signature

Mixed signatures. Look for:
- Frame-rate volume changes (software) transitioning to sub-frame
  changes (hardware) or vice versa
- Abrupt length counter cutoffs interrupting smooth software decay
- Triangle linear counter gating (distinct from pulse volume behavior)

### MIDI Mapping

Must detect which envelope mode is active per note/channel and apply
the appropriate CC11 strategy. The frame IR handles this by dispatching
on channel type (triangle vs pulse) and driver capability.

---

## 5. Duty Cycle Envelopes

### How They Work

Some NES drivers modulate the duty cycle ($4000 bits 6-7) over time as
part of the instrument definition. This changes the timbre (harmonic
content) of the pulse wave without affecting volume.

Common patterns:
- **Duty sweep**: 12.5% -> 25% -> 50% over the first few frames (brightening attack)
- **Duty wobble**: alternating between two duty values for a chorusing effect
- **Duty + volume envelope**: combined timbral and amplitude shaping

### Who Uses This

FamiTracker-style engines (used in homebrew and some commercial titles)
support duty cycle sequences as a first-class instrument parameter.
Some Capcom and Sunsoft drivers also include duty modulation.

The Konami Maezawa driver does NOT use duty cycle envelopes. Duty is set
once per instrument change and remains constant for the note's duration.

### ROM Storage

Typically stored alongside volume envelope tables as a parallel sequence:
```
instrument_definition:
  .byte volume_env_ptr_lo, volume_env_ptr_hi
  .byte duty_env_ptr_lo, duty_env_ptr_hi
  .byte arpeggio_ptr_lo, arpeggio_ptr_hi
```

Each envelope is a byte sequence with loop points and terminators.

### APU Trace Signature

- $4000/$4004 duty bits (6-7) change between frames
- Volume may remain constant while duty changes (pure timbral envelope)
- Look for periodic duty patterns (2-3 frame cycles = wobble)

### MIDI Mapping

No standard MIDI equivalent for duty cycle. Options:
- Ignore (lose timbral detail, keep volume accuracy)
- Map to CC1 (modulation wheel) for playback with NES synth plugins
- Encode as program changes or NRPN for custom synths

Our pipeline currently sets duty once per instrument and does not
automate it. Supporting duty envelopes would require a new CC channel
or sysex encoding in the MIDI export.

---

## 6. Pitch Envelopes and Vibrato

### How They Work

Many NES drivers modulate pitch over time for expressive effects:

**Vibrato**: Periodic pitch oscillation around the base frequency.
The Contra driver implements this via the EB command, which sets vibrato
speed and depth parameters. The driver adds a sine-like offset to the
period register each frame.

**Pitch slide (portamento)**: Gradual period change from one value to
another. Some drivers implement this with sweep hardware ($4001/$4005);
others do it in software.

**Arpeggio**: Rapid cycling through 2-3 pitch offsets (e.g., +0, +4, +7
semitones) to simulate chords on a single channel. Common in FamiTracker
engines and Sunsoft drivers.

### ROM Storage

- **Vibrato**: typically 2 parameters (speed + depth) set by a command byte
- **Arpeggio tables**: stored similarly to volume envelopes -- byte
  sequences of semitone offsets with loop points
- **Sweep**: single byte written to $4001/$4005 (hardware does the rest)

### Contra Specifics

The EB command sets vibrato parameters. Our parser currently skips these
(marked as KNOWN_LIMITATION in contra_parser.py). The Contra disassembly
shows vibrato is applied as a periodic addition to the period register,
modulated by a counter.

The EC command in Contra shifts the pitch lookup index (semitone offset
into the period table). This is NOT present in CV1.

### APU Trace Signature

- **Vibrato**: period register oscillates around a center value with
  regular periodicity (typically 4-8 frame cycles)
- **Arpeggio**: period register jumps between 2-3 discrete values in a
  repeating pattern (typically 1-2 frame cycle)
- **Slide**: period register changes monotonically frame over frame

### MIDI Mapping

- **Vibrato**: pitch bend messages or CC1 (mod wheel) if using a synth
  that interprets it as vibrato. Our pipeline does not currently emit
  pitch bend.
- **Arpeggio**: could be represented as rapid note sequences or as a
  single note with pitch bend automation. Neither is ideal.
- **Slide**: portamento CC (CC65 on, CC5 time) or pitch bend ramp.

### Implications

Pitch envelopes interact with the period-to-MIDI conversion. If vibrato
is active, the trace will show period values that do NOT match the
note's base period. This can cause false pitch mismatches in
trace_compare.py if the comparison does not account for modulation.

---

## 7. Complex and Unusual Systems

### Multi-Table Instruments (Sunsoft)

Sunsoft's driver (used in titles like Sunsoft Batman and Journey to
Silius) defines instruments with up to four parallel envelope sequences:
volume, duty cycle, arpeggio, and pitch. All four run simultaneously,
each at potentially different rates. This produces rich, evolving
timbres but is difficult to extract because the instrument definition
is spread across multiple ROM tables with cross-references.

### DPCM-Driven Percussion

The NES delta modulation channel ($4010-$4013) plays back 1-bit delta
PCM samples. Some drivers use this for percussion (Contra's noise
channel triggers DMC samples). The "envelope" is baked into the sample
data itself -- there is no separate volume envelope. Extraction requires
reading the sample data, not modeling an envelope.

### Capcom Drivers

Capcom NES titles (Mega Man series, DuckTales) use a driver family with
indexed instrument definitions that include volume envelope pointers,
duty cycle sequences, and vibrato parameters. The envelope tables use a
loop-point system where a byte value indicates "jump back to offset N"
rather than $FF termination.

### FamiTracker / NSF Engines

Modern homebrew and NSF-based engines (FamiTracker, FamiStudio) use a
rich instrument model with volume, arpeggio, pitch, and duty sequences,
each with independent loop points and release triggers. These engines
are well-documented, but their ROM format varies by export target.

---

## Comparison Table

| Aspect | CV1 Parametric | Contra Lookup | Hardware APU | Hybrid |
|--------|---------------|---------------|-------------|--------|
| **Volume source** | 2 parameters | ROM byte table | APU decay register | Mixed |
| **ROM cost** | 2 bytes/instrument | 8-20 bytes/envelope + 2-byte pointer | 0 (register config) | Varies |
| **Shape flexibility** | Linear decay only | Arbitrary contour | Exponential only | Varies |
| **Attack phase** | None (starts at max) | Table can define any attack | None | Possible |
| **Sustain** | Hold at (vol - fade_start) | Last table value | Loop flag | Possible |
| **Release** | Linear fade_step tail | Decrescendo threshold | Length counter | Possible |
| **Duty modulation** | No | No | No | Some drivers |
| **Pitch modulation** | No | EB vibrato, EC transpose | Sweep unit ($4001) | Common |
| **Frames per update** | 1 (software) | 1 (software) | Sub-frame (240Hz) | Mixed |
| **Trace validation** | Straightforward | Straightforward | Needs sub-frame sampling | Complex |
| **MIDI mapping** | CC11 linear | CC11 arbitrary | CC11 sampled | CC11 + extras |
| **Our support** | VERIFIED | PROVISIONAL | Triangle only | Partial |

---

## Implications for Our Pipeline

### What frame_ir.py Must Support

1. **Parametric model** (`_cv1_parametric_envelope`): fully implemented,
   verified. Handles CV1 and any future Maezawa game with the same
   2-byte fade system.

2. **Lookup table model** (`_contra_lookup_envelope`): implemented,
   provisional. Must handle:
   - Table playback with $FF termination
   - Sustain at last table value
   - Decrescendo tail with `(mul * dur) >> 4` threshold
   - Auto-decrescendo mode (bit 7 set, no table)
   - Bounce-at-1 behavior

3. **Hardware envelope model**: NOT YET IMPLEMENTED for pulse channels.
   Would require reading the constant volume flag (bit 4 of $4000) and,
   when clear, simulating the APU's internal envelope divider. Triangle
   linear counter IS implemented (hardware gating via $4008).

4. **Duty cycle envelopes**: NOT IMPLEMENTED. Would require a new field
   in FrameState and a parallel envelope runner. Low priority unless we
   target Sunsoft or Capcom drivers.

5. **Pitch envelopes**: NOT IMPLEMENTED. Would require pitch bend or
   period modulation fields in FrameState, plus tolerance in trace
   comparison. Contra's EB vibrato is the first candidate.

### DriverCapability Extensions

The current `DriverCapability` schema supports:
```python
volume_model: "parametric" | "lookup_table"
envelope_tables: list[list[int]] | None
decrescendo_status: "verified" | "provisional"
```

Future extensions for new envelope types:
```python
volume_model: "parametric" | "lookup_table" | "hardware" | "multi_table"
duty_envelope: bool = False
pitch_envelope: "none" | "vibrato" | "arpeggio" | "slide"
hardware_length_counter: bool = False
```

Each new volume_model value gets its own isolated strategy function in
frame_ir.py, following the existing pattern.

---

## Failure Risks If Misunderstood

### 1. Applying the Wrong Envelope Model

**Symptom**: volume mismatches everywhere, but pitch is perfect.

If you apply CV1's parametric model to a game that uses lookup tables
(or vice versa), every note's volume contour will be wrong. Pitch is
independent of the envelope system, so it will still match. This is
exactly what happened with early Contra extraction attempts before
the lookup table system was identified.

**Prevention**: check the manifest's `volume_model` field. Run
trace_compare.py on pulse volume after any driver change.

### 2. Ignoring Hardware Envelopes

**Symptom**: notes appear to sustain at full volume in our IR, but the
trace shows decay. Or notes cut off earlier than expected.

If a driver uses hardware envelopes (constant volume flag = 0) and we
assume software control, the IR will produce flat volume where the
hardware is decaying. The trace comparison will catch this as volume
mismatches on every note.

**Prevention**: check bit 4 of the instrument byte. If clear, the
driver is using hardware envelopes and we need a different strategy.

### 3. Missing the Triangle Difference

**Symptom**: triangle notes sustain too long or too short. Volume
mismatches concentrated on the triangle channel.

The triangle channel has NO volume control -- it is either on or off,
gated by the linear counter ($4008). Applying a pulse volume envelope
to triangle produces nonsense. The instrument byte for triangle IS the
$4008 register value, not a DDLCVVVV pulse config.

**Prevention**: always dispatch on channel type. Triangle uses
`(reload + 3) // 4` frame approximation for sounding duration.
See `docs/HANDOVER_FIDELITY.md` Fix 6.

### 4. Assuming Envelope Tables Are Global

**Symptom**: envelopes sound right for one level but wrong for another.

Contra's envelope tables are organized per-level. The active level
determines which set of 8 envelope pointers is loaded. Our current
extraction uses a single level's tables. A game that changes levels
mid-song (unlikely for music, possible for jingles) would need
level-aware table selection.

**Prevention**: document which level's tables were used. Cross-check
with the disassembly when volume does not match.

### 5. Confusing Pitch Modulation for Pitch Errors

**Symptom**: trace shows pitch "mismatches" that oscillate or repeat
in a pattern.

If vibrato or arpeggio is active, the period register will deviate
from the note's base period on every frame. trace_compare.py will
flag these as pitch mismatches. They are not errors -- they are the
pitch envelope working as designed.

**Prevention**: if pitch mismatches follow a periodic pattern (not
random drift), check for EB vibrato or arpeggio commands in the
parsed data. Add vibrato tolerance to the comparison.

### 6. Systematic Errors That Pass Trace Validation

**Symptom**: zero trace mismatches, but the output sounds wrong to a
human listener.

If the MIDI octave mapping is wrong by exactly 12 semitones, the
period-to-MIDI conversion will be internally consistent (trace matches
itself) but every note will be one octave off. This happened during
CV1 development and is documented in `docs/OCTAVETOOLOWONPULSE.md`.

**Prevention**: after ANY pitch or octave mapping change, a human must
compare the output to the actual game audio. Automated tests cannot
catch systematic offset errors.
