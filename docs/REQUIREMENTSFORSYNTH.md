# Requirements for NES Synth Plugins (JSFX)

What we learned building ReapNES_APU.jsfx about what makes an NES synth
plugin work correctly in REAPER. Use this as a specification when building
new synth plugins or improving existing ones.

---

## The Bugs We Hit

Every rule below exists because we hit its absence as a real bug:
- Missing `in_pin:none` → total silence, no error (Blunder 2)
- `//tags:instrument` → comment, REAPER ignores it (Blunder 1)
- Unicode characters → silent compilation failure (Blunder 3)
- `^` used as XOR → actually computes exponentiation (Blunder 9)
- DC offset in mixer → inaudible signal masked by constant voltage (Blunder 8)
- All channels mixed when only one active → noise from inactive oscillators (Blunder 8 redux)
- Channel remap instead of filter → every track plays all notes (Blunder 10)

See `docs/BLOOPERS.md` for the full horror story.

---

## File Header (MANDATORY)

Every JSFX instrument plugin MUST start with exactly this structure:

```
desc:Plugin Name - Short Description
tags:instrument synthesizer chiptune NES 8-bit
in_pin:none
out_pin:Left
out_pin:Right
```

### Rules:
- `desc:` — first line, plain ASCII, no unicode
- `tags:` — NOT `//tags:`, NOT `// tags:`. No comment prefix.
- `in_pin:none` — tells REAPER this is a synthesizer, not an effect
- `out_pin:Left` / `out_pin:Right` — stereo output
- **ASCII only** in the entire file. No `→`, `—`, `≈`, or any character > U+007E

---

## Slider Declarations

### Rules:
- Sequential numbering starting at 1. NO GAPS.
  - Valid: slider1, slider2, slider3, slider4
  - Invalid: slider1, slider2, slider4, slider10 (gaps at 3, 5-9)
- Maximum 64 sliders
- Use descriptive names
- Use enum syntax for discrete choices: `{Choice1,Choice2,Choice3}`

### Required Sliders for Full APU:

```
slider1:2<0,3,1{12.5%,25%,50%,75%}>P1 Duty
slider2:15<0,15,1>P1 Volume
slider3:1<0,1,1{Off,On}>P1 Enable
slider4:1<0,3,1{12.5%,25%,50%,75%}>P2 Duty
slider5:15<0,15,1>P2 Volume
slider6:1<0,1,1{Off,On}>P2 Enable
slider7:1<0,1,1{Off,On}>Tri Enable
slider8:0<0,15,1>Noise Period (0-15)
slider9:0<0,1,1{Long,Short}>Noise Mode
slider10:15<0,15,1>Noise Volume
slider11:1<0,1,1{Off,On}>Noise Enable
slider12:0.8<0,1,0.01>Master Gain
slider13:4<0,4,1{P1 Only,P2 Only,Tri Only,Noise Only,Full APU}>Channel Mode
```

### Channel Mode (slider13) — Critical for Multi-Track

| Value | Mode | Behavior |
|-------|------|----------|
| 0 | Pulse 1 Only | Only process MIDI ch 0, only output pulse 1 oscillator |
| 1 | Pulse 2 Only | Only process MIDI ch 1, only output pulse 2 oscillator |
| 2 | Triangle Only | Only process MIDI ch 2, only output triangle oscillator |
| 3 | Noise Only | Only process MIDI ch 3, only output noise oscillator |
| 4 | Full APU | Process all channels, output all oscillators (keyboard play) |

**In multi-track projects**: each track MUST use its own channel mode (0-3).
**In single-track keyboard play**: use Full APU mode (4).

**NEVER remap channels. FILTER them.**
```
// WRONG (Blunder 10):
ch_mode == 0 ? ch = 0;     // remaps ALL channels to 0 — plays everything!

// RIGHT:
ch_mode < 4 ? (
  ch != ch_mode ? use_msg = 0;  // skip messages for other channels
);
```

---

## Audio Output (MANDATORY)

### DC Offset Prevention

The output signal MUST be centered around zero at all times.

```
// WRONG (Blunder 8):
out = (mixed - 0.35) * gain;  // constant DC offset when mixed = 0

// ALSO WRONG:
mix = 0;
mix += (p1_out / 15.0 - 0.5) * 0.5;  // inactive channel at 0 → -0.25 offset
mix += (p2_out / 15.0 - 0.5) * 0.5;  // another -0.25
mix += (tri_out / 15.0 - 0.5) * 0.4;  // another -0.20
// Total DC from inactive channels: -0.70!

// RIGHT:
mix = 0;
p1_en ? ( mix += (p1_out / 15.0 - 0.5) * 0.5; );  // only active channels
p2_en ? ( mix += (p2_out / 15.0 - 0.5) * 0.5; );
tri_en ? ( mix += (tri_out / 15.0 - 0.5) * 0.4; );
noi_en ? ( mix += (noi_out / 15.0 - 0.5) * 0.3; );
```

### Silence When Idle

When no notes are playing, output MUST be exactly 0.0:
```
n_active > 0 ? (
  spl0 = mix * gain;
  spl1 = mix * gain;
) : (
  spl0 = 0;
  spl1 = 0;
);
```

---

## NES 2A03 APU Specifications

### Pulse Channels (2)

| Parameter | Range | Hardware Register |
|-----------|-------|-------------------|
| Duty Cycle | 12.5%, 25%, 50%, 75% | $4000/$4004 bits 6-7 |
| Volume | 0-15 | $4000/$4004 bits 0-3 |
| Period | 0-2047 (11-bit) | $4002-3/$4006-7 |
| Sweep | enable, period, negate, shift | $4001/$4005 |

**Frequency calculation**:
```
freq_hz = CPU_CLK / (16 * (period + 1))
// CPU_CLK = 1789773 Hz (NTSC)
```

**Duty cycle waveforms** (8-step sequences):
```
12.5%: 0 1 0 0 0 0 0 0
25%:   0 1 1 0 0 0 0 0
50%:   0 1 1 1 1 0 0 0
75%:   1 0 0 1 1 1 1 1
```

**Phase increment per sample**:
```
phase_inc = 8.0 * freq_hz / sample_rate
output = duty_table[duty * 8 + (floor(phase) & 7)] * volume
```

### Triangle Channel (1)

| Parameter | Range | Notes |
|-----------|-------|-------|
| Period | 0-2047 (11-bit) | Same formula as pulse but /32 not /16 |
| Linear Counter | 0-127 | Controls note duration |
| Volume | FIXED | No volume control — always full amplitude |

**Waveform** (32-step triangle):
```
15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0,
 0,  1,  2,  3,  4,  5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
```

**Frequency calculation**:
```
freq_hz = CPU_CLK / (32 * (period + 1))
```

### Noise Channel (1)

| Parameter | Range | Notes |
|-----------|-------|-------|
| Period Index | 0-15 | Indexes into period lookup table |
| Mode | 0 (long) / 1 (short) | LFSR feedback tap position |
| Volume | 0-15 | Same as pulse |

**Period lookup table** (CPU cycles per LFSR clock):
```
4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068
```

**LFSR** (15-bit linear feedback shift register):
```
// Mode 0 (long): feedback from bits 0 and 1
fb = ((lfsr & 1) + ((lfsr >> 1) & 1)) & 1;  // XOR via addition

// Mode 1 (short): feedback from bits 0 and 6
fb = ((lfsr & 1) + ((lfsr >> 6) & 1)) & 1;

lfsr = (lfsr >> 1) | (fb << 14);
output = (lfsr & 1) ? 0 : volume;
```

**CRITICAL**: JSFX `^` is POWER, not XOR. Use `((a + b) & 1)` for XOR.

### Drum Mapping (Noise → GM Drums)

For MIDI playback, map GM drum notes to noise parameters:

| GM Note | Drum | Noise Period | Mode | Attack Vol | Decay (samples) |
|---------|------|-------------|------|------------|-----------------|
| 35-36 | Kick | 13-14 | Long | 15 | 500-600 |
| 38 | Snare | 6 | Long | 15 | 350 |
| 42 | Closed HH | 1 | Short | 10 | 100 |
| 46 | Open HH | 2 | Long | 11 | 250 |
| 41-45 | Toms | 8-11 | Long | 14 | 400-500 |
| 49/57 | Crash | 3 | Long | 13 | 800-900 |

Drum hits use a **self-decaying volume envelope**:
```
trigger_drum(gm_note):
  set noise period, mode from lookup table
  set drum_vol = attack_volume * (velocity / 127)
  set drum_decay = samples per volume step
  drum_active = 1

per_sample:
  drum_timer -= 1
  drum_timer <= 0:
    drum_vol -= 1
    if drum_vol <= 0: noi_en = 0; drum_active = 0
    else: drum_timer = drum_decay
```

---

## MIDI Processing

### @block Section Structure

```
@block
ch_mode = slider13;

while (midirecv(offset, msg1, msg2, msg3)) (
  status = msg1 & 0xF0;
  ch = msg1 & 0x0F;

  // FILTER (not remap!) based on channel mode
  use_msg = 1;
  ch_mode < 4 ? (
    ch != ch_mode ? use_msg = 0;
  );

  // Note On
  use_msg && status == 0x90 && msg3 > 0 ? (
    // route to correct oscillator based on ch
  );

  // Note Off
  use_msg && (status == 0x80 || (status == 0x90 && msg3 == 0)) ? (
    // disable correct oscillator
  );

  // Always pass MIDI through
  midisend(offset, msg1, msg2, msg3);
);
```

### Frequency Conversion

```
function note2hz(n) ( 440 * 2 ^ ((n - 69) / 12); );

function calc_pulse_inc(freq) local(period, f) (
  period = cpu_clk / (16 * freq) - 1;
  period = max(0, min(2047, floor(period + 0.5)));
  f = cpu_clk / (16 * (period + 1));
  8.0 * f / srate;
);
```

Note: this quantizes to the NES period register, giving authentic
slightly-detuned frequencies rather than perfect equal temperament.

---

## GUI (@gfx Section)

### Recommended Layout

```
Top half:     Oscilloscope (5 lanes: P1, P2, TRI, NOI, MIX)
Bottom half:  Controls per channel (duty selector, volume slider, enable toggle)
Footer:       Master gain, channel mode display, active/idle indicator
```

### Interactive Controls

- **Sliders**: click and drag horizontally
- **Toggles**: click to flip on/off
- **Duty selector**: click to cycle through 12.5% → 25% → 50% → 75%
- **Note display**: show current note name (C4, D#5, etc.)
- **Drum display**: show drum name when noise is in drum mode (KICK, SNARE, CHH)

### Colors (Consistent Across UI)

```
Pulse 1:   RGB(77, 230, 102)   — green
Pulse 2:   RGB(102, 179, 230)  — blue
Triangle:  RGB(230, 153, 51)   — orange
Noise:     RGB(179, 179, 179)  — gray
Mix:       RGB(255, 255, 255)  — white
```

---

## Validation Checklist

Run `python scripts/validate.py --jsfx` after every change.

```
[ ] desc: line present (first line)
[ ] tags:instrument present (not //tags:)
[ ] in_pin:none present
[ ] out_pin:Left and out_pin:Right present
[ ] ASCII only (no unicode anywhere)
[ ] Sequential slider numbering (no gaps)
[ ] No ^ used for XOR (use ((a+b)&1) instead)
[ ] Output centered at zero (no DC offset)
[ ] Silence when no notes playing (spl0 = spl1 = 0)
[ ] Channel mode filters, not remaps
[ ] Only active channels contribute to mix
[ ] Drum envelope decays to zero (doesn't sustain)
[ ] Note-off properly silences the oscillator
```

---

## Plugin Template

Use this as the starting skeleton for any new NES JSFX synth:

```jsfx
desc:ReapNES PluginName - Description Here
tags:instrument synthesizer chiptune NES 8-bit
in_pin:none
out_pin:Left
out_pin:Right

slider1:2<0,3,1{12.5%,25%,50%,75%}>Duty Cycle
slider2:15<0,15,1>Volume
slider3:1<0,1,1{Off,On}>Enable
slider4:0.8<0,1,0.01>Master Gain

@init
cpu_clk = 1789773;
phase = 0;
inc = 0;
vol = 15;
en = 0;
note = -1;

// Duty table
dt = 0;
dt[0]=0; dt[1]=1; dt[2]=0; dt[3]=0; dt[4]=0; dt[5]=0; dt[6]=0; dt[7]=0;
dt[8]=0; dt[9]=1; dt[10]=1; dt[11]=0; dt[12]=0; dt[13]=0; dt[14]=0; dt[15]=0;
dt[16]=0; dt[17]=1; dt[18]=1; dt[19]=1; dt[20]=1; dt[21]=0; dt[22]=0; dt[23]=0;
dt[24]=1; dt[25]=0; dt[26]=0; dt[27]=1; dt[28]=1; dt[29]=1; dt[30]=1; dt[31]=1;

function note2hz(n) ( 440 * 2 ^ ((n - 69) / 12); );

function calc_inc(freq) local(period, f) (
  period = cpu_clk / (16 * freq) - 1;
  period = max(0, min(2047, floor(period + 0.5)));
  f = cpu_clk / (16 * (period + 1));
  8.0 * f / srate;
);

@slider
vol = slider2;

@block
while (midirecv(offset, msg1, msg2, msg3)) (
  status = msg1 & 0xF0;
  status == 0x90 && msg3 > 0 ? (
    note = msg2;
    inc = calc_inc(note2hz(msg2));
    vol = floor(msg3 / 127 * 15 + 0.5);
    en = 1;
  );
  (status == 0x80 || (status == 0x90 && msg3 == 0)) ? (
    msg2 == note ? ( en = 0; note = -1; );
  );
  midisend(offset, msg1, msg2, msg3);
);

@sample
en && slider3 ? (
  sample_out = dt[slider1 * 8 + (floor(phase) & 7)] * vol;
  phase += inc;
  phase >= 8.0 ? phase -= 8.0;
  out = (sample_out / 15.0 - 0.5) * slider4;
  spl0 = out;
  spl1 = out;
) : (
  spl0 = 0;
  spl1 = 0;
);
```
