# NES Audio Hardware Variants

Reference document for NES Music Studio. Covers the base APU and all
cartridge expansion audio chips that appear in games this project may
target. Written to inform pipeline decisions in render_wav.py,
frame_ir.py, midi_export.py, and generate_project.py.

---

## 1. Base APU: Ricoh 2A03 (NTSC) / 2A07 (PAL)

The standard NES sound hardware. Every NES game uses this. Our current
pipeline (CV1, Contra) targets ONLY this chip.

### Channels (5 total)

| Channel   | Type          | Registers     | Key Capabilities |
|-----------|---------------|---------------|------------------|
| Pulse 1   | Square wave   | $4000-$4003   | 4 duty cycles (12.5/25/50/75%), sweep unit, 4-bit volume, length counter |
| Pulse 2   | Square wave   | $4004-$4007   | Identical to Pulse 1 except sweep negate differs by 1 |
| Triangle  | Triangle wave | $4008-$400B   | Fixed volume (no amplitude control), linear counter, 32-step waveform |
| Noise     | LFSR noise    | $400C-$400F   | 2 modes (long/short sequence), 16 rate presets, 4-bit volume |
| DMC/DPCM  | 1-bit delta   | $4010-$4013   | Plays delta-encoded samples from ROM, 16 rate presets, 7-bit DAC |

### Register Address Space: $4000-$4017

See REGISTER_MAP.md for the full bit-level layout.

### Hardware Facts Relevant to Our Pipeline

- **Clock**: CPU_CLK = 1,789,773 Hz (NTSC). PAL = 1,662,607 Hz.
- **Pulse frequency**: CPU_CLK / (16 * (period + 1)). Minimum period ~8 before artifacts.
- **Triangle frequency**: CPU_CLK / (32 * (period + 1)). Same period value = half the frequency of pulse. This is why triangle subtracts 12 MIDI semitones.
- **Triangle has no volume register**. It is either sounding or silent. The linear counter controls duration only.
- **Noise period table**: 16 fixed rates, not a continuous frequency. Short mode (bit 7 of $400E) produces metallic/tonal noise.
- **DMC conflicts**: DMC playback steals CPU cycles and can cause audible glitches in other channels. DMC IRQ can also interfere with timing.
- **Mixing**: Channels are mixed through a nonlinear DAC. Pulse 1+2 share one output path; Triangle+Noise+DMC share another. The mixing formula is nonlinear but approximated well by linear mixing at moderate volumes.

### Current Pipeline Coverage

render_wav.py synthesizes Pulse 1, Pulse 2, and Triangle. Noise is
rendered as simple random bursts for drum hits. DMC is not synthesized
(drum events are approximated). This is adequate for CV1 and Contra.

---

## 2. VRC6 (Konami VRC VI)

Konami's most musically capable expansion chip. Adds 3 audio channels
to the base APU, for a total of 8 channels of audio.

### Games

- Akumajou Densetsu (Castlevania III JP) -- mapper 24
- Madara -- mapper 24
- Esper Dream 2 -- mapper 26

**Mapper 24 vs 26**: Register addresses have A0 and A1 swapped. Same
chip, different board routing. The audio registers are equivalent.

### Channels (3 additional)

| Channel     | Type      | Registers       | Key Capabilities |
|-------------|-----------|-----------------|------------------|
| VRC6 Pulse 1| Square    | $9000-$9002     | 8 duty cycle settings (6.25% to 50% in 8 steps), 4-bit volume, no sweep |
| VRC6 Pulse 2| Square    | $A000-$A002     | Identical to VRC6 Pulse 1 |
| VRC6 Saw    | Sawtooth  | $B000-$B002     | 6-bit accumulator, produces staircase sawtooth at configurable rate |

### Register Layout

**VRC6 Pulse ($9000/$A000)**:
| Addr     | Bits        | Field |
|----------|-------------|-------|
| $9000    | MDDD.VVVV   | Mode (1=constant), Duty (3 bits, 0-7), Volume (4 bits) |
| $9001    | PPPP.PPPP   | Period low 8 bits |
| $9002    | E---.PPPP   | Enable (1), Period high 4 bits |

**VRC6 Sawtooth ($B000)**:
| Addr     | Bits        | Field |
|----------|-------------|-------|
| $B000    | --AA.AAAA   | Accumulator rate (6 bits, added every 2 CPU clocks) |
| $B001    | PPPP.PPPP   | Period low 8 bits |
| $B002    | E---.PPPP   | Enable (1), Period high 4 bits |

### Key Differences from Base APU Pulse

- **Duty cycle**: 3 bits = 8 settings (steps of ~6.25%), vs base APU's 2 bits = 4 settings. Finer timbral control.
- **No sweep unit**: VRC6 pulse channels cannot do hardware pitch sweep.
- **No length counter**: Sound continues until explicitly silenced.
- **12-bit period**: Same range as base APU pulse. Frequency formula is the same: CPU_CLK / (16 * (period + 1)).

### Sawtooth Channel

The sawtooth is unique to VRC6. It works by accumulating a 6-bit rate
value into an internal counter every 2 CPU clocks. The high 5 bits of
the accumulator form the output DAC value. The accumulator resets every
7 steps, producing a staircase waveform. The rate value controls
volume (higher rate = louder), and the period register controls pitch.

This produces a characteristic buzzy, harmonically rich tone unlike
anything in the base APU. It is prominently featured in Akumajou
Densetsu's soundtrack.

### Emulator Trace Implications

VRC6 registers are at $9000-$9002, $A000-$A002, $B000-$B002. These
are in the cartridge address space, NOT the APU address space
($4000-$4017). Mesen's trace logger can capture expansion audio
register writes, but it must be configured to do so -- standard APU
trace will NOT include VRC6 data.

---

## 3. MMC5 (Nintendo MMC5)

Nintendo's expansion mapper. Adds 2 audio channels. Used in the US
release of Castlevania III as a substitute for the VRC6.

### Games

- Castlevania III: Dracula's Curse (US) -- mapper 5
- Just Breed -- mapper 5
- Uchuu Keibitai SDF (some PCM usage) -- mapper 5

### Channels (2 additional)

| Channel     | Type      | Registers       | Key Capabilities |
|-------------|-----------|-----------------|------------------|
| MMC5 Pulse 1| Square    | $5000-$5003     | Same 4 duty cycles as base APU, 4-bit volume, no sweep |
| MMC5 Pulse 2| Square    | $5004-$5007     | Identical to MMC5 Pulse 1 |
| MMC5 PCM    | 8-bit PCM | $5010-$5011     | 8-bit unsigned PCM output, rarely used for music |

### Register Layout

**MMC5 Pulse ($5000/$5004)**:
| Addr     | Bits        | Field |
|----------|-------------|-------|
| $5000    | DD.LC.VVVV  | Duty (2), Length halt (1), Constant vol (1), Volume (4) |
| $5002    | PPPP.PPPP   | Period low 8 bits |
| $5003    | LLLL.LTTT   | Length counter load (5), Period high 3 bits |

### Key Differences from VRC6 and Base APU

- **Register layout matches base APU**: Same bit fields as $4000-$4003. Code that writes to base APU pulse can trivially target MMC5 pulse by changing the base address.
- **No sweep unit**: Like VRC6, MMC5 pulse has no hardware sweep.
- **Only 4 duty cycles**: Same 12.5/25/50/75% as base APU. The VRC6 has 8 duty settings, so VRC6 offers finer timbral control.
- **No sawtooth**: This is the big loss. The US Castlevania III had to rearrange its soundtrack to compensate for losing the VRC6 sawtooth channel.
- **PCM channel**: $5011 is an 8-bit DAC that can play raw PCM samples. Rarely used musically; some games use it for speech.

### The CV3 JP vs US Problem

This is the critical case for our project:

| Aspect | JP (Akumajou Densetsu) | US (Dracula's Curse) |
|--------|------------------------|----------------------|
| Mapper | 24 (VRC6) | 5 (MMC5) |
| Extra channels | 2 pulse + 1 sawtooth | 2 pulse + PCM |
| Total melodic channels | 7 (2 APU pulse + tri + 2 VRC6 pulse + saw) | 6 (2 APU pulse + tri + 2 MMC5 pulse) |
| Duty cycle options | 4 (APU) + 8 (VRC6) | 4 (APU) + 4 (MMC5) |
| Sound driver | Different code, same music data (mostly) | Different code, rearranged music |
| Musical quality | Widely regarded as superior | Noticeably thinner due to missing sawtooth |

The JP and US versions have DIFFERENT sound drivers and partially
different music data. The sawtooth parts from the JP version are
either dropped or reassigned to other channels in the US version. A
parser for one version will NOT work on the other without modification.

---

## 4. VRC7 (Konami VRC VII)

Contains a clone of Yamaha's YM2413 (OPLL) FM synthesis chip. The most
sonically powerful NES expansion, but used in only one game.

### Games

- Lagrange Point -- mapper 85

### Channels (6 additional)

All 6 channels are 2-operator FM synthesis voices. The YM2413 core
supports 15 built-in instrument patches plus 1 user-defined custom
patch.

| Channel   | Type | Registers |
|-----------|------|-----------|
| VRC7 ch0-5 | FM (2-op) | $9010, $9030, $10-$35 (indirect) |

### Register Layout

**VRC7 uses indirect register access**:
- Write register number to $9010
- Write data to $9030

**Per-channel registers ($10-$35)**:
| Reg       | Bits        | Field |
|-----------|-------------|-------|
| $10+ch    | FFFF.FFFF   | F-number low 8 bits |
| $20+ch    | --ST.OOOF   | Sustain, Trigger, Octave (3), F-number high bit |
| $30+ch    | IIII.VVVV   | Instrument (4 bits, 0=custom, 1-15=preset), Volume (4 bits) |

**Custom instrument registers ($00-$07)**: Define modulator/carrier
parameters (attack, decay, sustain, release, multiplier, key scale,
waveform select, feedback). 8 bytes total.

### FM Synthesis Model

Each VRC7 voice is a 2-operator FM pair (modulator + carrier):
- Modulator output frequency-modulates the carrier
- Carrier output goes to DAC
- 15 preset patches are hardcoded in silicon (not in ROM)
- Patch 0 uses the 8 custom registers for user-defined timbre

The 15 preset patches approximate common instruments (strings, brass,
organ, guitar, etc.). The exact patch parameters were reverse-engineered
by the community since Konami never published them.

### Emulator Trace Implications

VRC7 registers are at $9010 and $9030 (indirect). Tracing requires
capturing both the address write and the data write as a pair. The
internal FM state (operator phases, envelope generators) is not
directly observable from register writes alone -- the synth must be
modeled.

### Pipeline Implications

VRC7 is the hardest expansion to support in render_wav.py because it
requires a full 2-operator FM synthesis engine. The YM2413 envelope
generator alone has 4 phases (attack, decay, sustain, release) with
exponential curves. MIDI export would need to map FM patches to
General MIDI program changes (an imperfect approximation).

---

## 5. Namco 163 (N163)

Wavetable synthesis chip with up to 8 channels. Channel count is
configurable; more channels = lower sample rate per channel.

### Games

- Megami Tensei II
- King of Kings
- Rolling Thunder
- Various Namco titles (mapper 19)

### Channels (1-8 configurable)

Each channel plays from a shared 128-byte wavetable RAM. More active
channels means each channel gets updated less frequently, reducing
effective sample rate and introducing audible aliasing.

| Active Channels | Update Rate per Channel |
|-----------------|------------------------|
| 1               | CPU_CLK / (15 * period) |
| 8               | CPU_CLK / (120 * period) |

### Register Layout

N163 uses indirect register access at $F800 (address) and $4800 (data).

**Per-channel registers (8 bytes each, at RAM offsets $40-$7F)**:
| Offset | Field |
|--------|-------|
| +0     | Frequency low 8 bits |
| +1     | Phase low 8 bits |
| +2     | Frequency mid 8 bits |
| +3     | Phase mid 8 bits |
| +4     | Frequency high 2 bits + wave length (3 bits) + wave offset (8 bits from +5) |
| +5     | Wave address (offset into wavetable RAM) |
| +6     | Phase high 8 bits |
| +7     | Volume (4 bits) + channel count enable |

### Wavetable System

- 128 bytes of shared RAM store waveform samples (4 bits per sample, 2 samples per byte)
- Each channel has a configurable wave length (32, 16, 8, or 4 samples) and offset into RAM
- Waves can be updated in real-time for evolving timbres
- Channels share RAM: more channels = less room for unique waveforms
- Sound quality degrades noticeably above 4-5 active channels due to reduced update rate

### Pipeline Implications

N163 requires wavetable rendering: read the 4-bit samples from RAM,
step through them at the configured frequency. The timbral variety is
high (arbitrary waveforms), making MIDI instrument mapping imprecise.
Each channel would need its own wavetable definition in the frame IR.

---

## 6. FDS (Famicom Disk System)

The FDS adds a single wavetable channel with a hardware modulation
unit. Japan-only hardware (the disk drive peripheral), but many games
were later converted to cartridge format.

### Games

- Akumajou Dracula (Castlevania JP, FDS version)
- Metroid (FDS version)
- Zelda no Densetsu (FDS version)
- Various Famicom Disk System titles

### Channels (1 additional)

| Channel   | Type          | Registers       | Key Capabilities |
|-----------|---------------|-----------------|------------------|
| FDS Wave  | 64-sample wavetable | $4040-$4092 | 6-bit amplitude per sample, hardware frequency modulation |

### Register Layout

| Addr        | Field |
|-------------|-------|
| $4040-$407F | Wavetable RAM: 64 entries, 6-bit amplitude each |
| $4080       | Volume envelope: speed + direction + gain |
| $4082-$4083 | Frequency (12 bits) |
| $4084       | Modulation envelope (sweep): speed + direction + gain |
| $4085       | Modulation counter (bias) |
| $4086-$4087 | Modulation frequency (12 bits) |
| $4088       | Modulation table write (32 entries, 3-bit signed values) |
| $4089       | Wave write enable + master volume (2 bits) |
| $408A       | Envelope speed |

### Unique Synthesis Capabilities

The FDS channel has features no other NES expansion matches:
- **64-sample wavetable**: Much higher resolution than N163's 4-bit samples. Each sample is 6 bits (0-63).
- **Hardware modulation**: A separate 32-entry modulation table modulates the main waveform's frequency in hardware. This produces vibrato, tremolo, or more complex timbral effects without CPU intervention.
- **Volume envelope**: Hardware-controlled volume sweep (up or down at configurable rate).
- **Master volume**: 4 levels (100%, 66%, 50%, 40%).

### Pipeline Implications

FDS requires a wavetable renderer with a modulation engine. The
modulation unit is complex: it uses a 32-step signed modulation table
to frequency-modulate the main oscillator. Accurate reproduction
requires modeling the modulation accumulator and its interaction with
the main frequency counter. MIDI export would need to approximate
modulation as pitch bend or vibrato CC messages.

---

## 7. Sunsoft 5B (FME-7 / 5B)

Contains a Yamaha YM2149F (AY-3-8910 compatible) PSG. Adds 3 square
wave channels with hardware envelope generator.

### Games

- Gimmick! -- the canonical example, outstanding soundtrack
- (Very few other games used the audio capability)

### Channels (3 additional)

| Channel     | Type    | Key Capabilities |
|-------------|---------|------------------|
| 5B ch A     | Square  | 12-bit period, 4-bit volume OR hardware envelope, noise mixing |
| 5B ch B     | Square  | Same as A |
| 5B ch C     | Square  | Same as A |

Plus a shared noise generator and hardware envelope generator.

### Register Layout

Sunsoft 5B uses indirect register access at $C000 (address) and $E000 (data).

| Reg  | Field |
|------|-------|
| $00-$01 | Channel A period (12 bits) |
| $02-$03 | Channel B period (12 bits) |
| $04-$05 | Channel C period (12 bits) |
| $06     | Noise period (5 bits) |
| $07     | Mixer: tone/noise enable per channel (6 bits) |
| $08-$0A | Channel A/B/C volume (4 bits) or envelope mode flag |
| $0B-$0C | Envelope period (16 bits) |
| $0D     | Envelope shape (4 bits: continue, attack, alternate, hold) |

### Hardware Envelope Generator

The AY-3-8910 has a single hardware envelope generator shared across
all 3 channels. When a channel sets bit 4 of its volume register, it
uses the shared envelope instead of its fixed volume. The envelope
shape register ($0D) selects from 16 waveforms (sawtooth up, sawtooth
down, triangle, etc.) with configurable repeat and hold behavior.

This envelope generator is what gives Gimmick! its distinctive
pulsating bass sounds.

### Pipeline Implications

Sunsoft 5B channels are conceptually similar to base APU pulse (square
waves with period control), but with 12-bit period (vs 11-bit), no
duty cycle control (always 50%), and the shared hardware envelope.
render_wav.py could handle the basic square wave synthesis easily.
The hardware envelope would need a dedicated model (16 envelope shapes
with period-controlled rate).

---

## Implications for Our Pipeline

### render_wav.py

Currently synthesizes 3 channel types: pulse (4 duty cycles), triangle
(32-step fixed waveform), and noise (random bursts). To support
expansion audio:

| Expansion | New Synth Code Required |
|-----------|------------------------|
| VRC6      | Pulse with 8 duty steps (minor change), sawtooth accumulator (new) |
| MMC5      | Same as existing pulse synth (trivial) |
| VRC7      | Full 2-operator FM engine (substantial) |
| N163      | Wavetable playback with configurable length/offset (moderate) |
| FDS       | 64-sample wavetable + modulation unit (substantial) |
| Sunsoft 5B| 50% square wave + hardware envelope shapes (moderate) |

**Priority**: VRC6 and MMC5 are the most relevant (Castlevania III).
VRC6 pulse is nearly identical to existing pulse code. The sawtooth
accumulator is ~30 lines of new synthesis. MMC5 pulse needs zero new
synth code.

### frame_ir.py

Currently defines FrameState with fields: period, volume, duty,
sounding, midi_note, channel_type. The channel_type is one of
"pulse1", "pulse2", "triangle". To support expansion audio:

- **Channel count**: Must support more than 4 channels. VRC6 adds 3,
  MMC5 adds 2, VRC7 adds 6, N163 adds up to 8.
- **New channel types**: "vrc6_pulse1", "vrc6_pulse2", "vrc6_saw",
  "mmc5_pulse1", "mmc5_pulse2", "vrc7_fm0"-"vrc7_fm5",
  "n163_wave0"-"n163_wave7", "fds_wave", "5b_a", "5b_b", "5b_c".
- **New state fields**: VRC7 needs instrument/patch number. N163 needs
  wavetable data reference. FDS needs modulation state. Sunsoft 5B
  needs envelope shape.
- **DriverCapability**: Already dispatches by driver. Adding expansion
  chip type to DriverCapability is the correct extension point.

### midi_export.py

Currently maps to 4 MIDI channels (pulse1=0, pulse2=1, triangle=2,
drums=3). MIDI supports 16 channels (with channel 10 reserved for
percussion in General MIDI).

| Expansion | MIDI Channel Allocation |
|-----------|------------------------|
| VRC6      | +3 channels (ch4=VRC6 pulse1, ch5=VRC6 pulse2, ch6=VRC6 saw) |
| MMC5      | +2 channels (ch4=MMC5 pulse1, ch5=MMC5 pulse2) |
| VRC7      | +6 channels (ch4-ch9 for FM voices) |
| N163      | +1 to +8 channels (varies by game) |
| FDS       | +1 channel |
| Sunsoft 5B| +3 channels |

Maximum case (N163 with 8 channels): 4 base + 8 expansion = 12 MIDI
channels. This fits within MIDI's 16-channel limit. VRC7 with 6 FM +
5 base = 11, also fine. No expansion pushes past the MIDI ceiling.

CC12 (timbre/duty) mapping needs expansion-specific values. VRC6 duty
values 0-7 map naturally. VRC7 instrument patches 0-15 could map to
MIDI program changes instead of CC.

### generate_project.py (REAPER)

Additional tracks in the REAPER project, each with appropriate synth
settings. The JSFX synth (ReapNES_APU.jsfx) currently handles base APU
channels only. Expansion channels would need either:
- Extended JSFX synth with expansion chip modes, OR
- Separate JSFX instances per expansion channel type, OR
- External VST (e.g., a VRC6/VRC7 emulator plugin)

---

## Failure Risks If Misunderstood

### 1. Treating VRC6 pulse as identical to APU pulse

VRC6 pulse has 8 duty cycle settings (3-bit field), not 4. If the
parser reads 3 duty bits but the synth only handles 2-bit duty, half
the timbral range is lost. The duty encoding is also different: VRC6
duty 0 = 1/16, vs APU duty 0 = 1/8.

### 2. Ignoring the JP/US split for Castlevania III

Parsing the Japanese ROM with a mapper-5 assumption (or vice versa)
will produce garbage. The ROMs have different mapper types, different
expansion register addresses, different channel counts, and partially
different music data. The sound driver code is also different. There is
no shortcut: each version needs its own parser configuration.

### 3. Missing expansion registers in trace capture

Standard Mesen APU trace captures $4000-$4017. VRC6 registers are at
$9000-$B002. MMC5 registers are at $5000-$5015. If trace capture does
not include expansion registers, validation against real hardware is
impossible. The trace_compare.py script must be expansion-aware.

### 4. Assuming VRC7 patches from register writes alone

VRC7's 15 built-in patches are in silicon, not in ROM. The register
writes only specify which patch number to use (4-bit field). To
synthesize the sound, you need the actual patch parameters, which were
reverse-engineered by the community (Nuke.YKT's decloak of the
YM2413). Using wrong patch data produces completely wrong timbres.

### 5. N163 channel count vs audio quality tradeoff

N163 can run 1-8 channels, but games typically use 4-5 because more
channels means lower per-channel update rate and audible aliasing. If
the parser assumes 8 channels but the game only activates 4, the
unused channels produce silence (harmless). But if the synth does not
model the reduced update rate, the audio will sound cleaner than real
hardware (the aliasing is part of the characteristic N163 sound).

### 6. FDS modulation unit is not optional

The FDS modulation unit produces pitch wobble that is integral to the
sound. Synthesizing the FDS wavetable without the modulation table
produces a flat, static tone that sounds nothing like the real
hardware. The modulation must be modeled even for basic accuracy.

### 7. Sunsoft 5B envelope is shared

The AY-3-8910 has ONE hardware envelope generator for all 3 channels.
If multiple channels use the envelope simultaneously, they all share
the same shape and rate. A per-channel envelope model would be wrong.

### 8. Expansion audio mixing levels

Each expansion chip mixes into the NES audio output at a different
level relative to the base APU. VRC6 and MMC5 tend to be quieter than
the base APU. VRC7 FM voices can be louder. Getting the relative mix
wrong makes the expansion channels either inaudible or overpowering.
The exact mixing ratios are hardware-dependent and vary by individual
console.

---

## Summary Table

| Chip      | Channels Added | Type           | Registers     | Notable Game(s) | Synth Difficulty |
|-----------|---------------|----------------|---------------|-----------------|------------------|
| Base APU  | 5 (baseline)  | 2 pulse, tri, noise, DMC | $4000-$4017 | All NES games | Done |
| VRC6      | 3             | 2 pulse + saw  | $9000-$B002   | CV3 JP          | Low-moderate |
| MMC5      | 2 (+PCM)      | 2 pulse        | $5000-$5015   | CV3 US          | Trivial |
| VRC7      | 6             | FM synthesis   | $9010/$9030   | Lagrange Point  | High |
| N163      | 1-8           | Wavetable      | $F800/$4800   | Megami Tensei II| Moderate |
| FDS       | 1             | Wavetable+mod  | $4040-$408A   | CV1 JP FDS ver  | Moderate-high |
| Sunsoft 5B| 3             | Square+envelope| $C000/$E000   | Gimmick!        | Moderate |

### Recommended Priority for This Project

1. **MMC5** -- trivial synth (reuse existing pulse), enables CV3 US
2. **VRC6** -- low-moderate synth, enables CV3 JP (the better soundtrack)
3. **Sunsoft 5B** -- moderate, enables Gimmick! (exceptional soundtrack)
4. **FDS** -- moderate-high, enables FDS versions of early Konami titles
5. **N163** -- moderate, enables Namco catalog
6. **VRC7** -- high effort, only one game (Lagrange Point)
