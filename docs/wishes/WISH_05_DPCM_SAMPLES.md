# WISH #5: DMC Sample Decoding

## 1. What This Wish Is

Add DPCM (Delta Pulse Code Modulation) sample playback to the rendering
pipeline. Instead of approximating all percussion with white noise
synthesis, decode the actual 1-bit delta-encoded samples stored in
Contra's ROM and mix them into the WAV output at the correct positions.

This affects `render_wav.py` primarily, with minor touches to
`contra_parser.py` (to carry sample metadata) and `frame_ir.py`
(to pass sample references through to the renderer).

## 2. Why It Matters

Contra's Jungle theme has 283 DAC changes across its percussion track.
Of those, the majority are DPCM sample triggers (hi-hat and snare),
not pure noise-channel kicks. The current pipeline renders all drum
hits as random noise bursts with decay envelopes. This produces:

- **Hi-hats that sound like static** instead of the crisp metallic
  click of the actual 81-byte sample played at 33 kHz.
- **Snares that sound like white noise** instead of the sharp,
  punchy crack of the 593-byte sample.
- **No timbral distinction** between noise-only kicks (sound_02)
  and DPCM-triggered hits (sound_5a/5b/5c/5d). The hybrid layering
  that gives Contra its characteristic percussion punch is lost.

DPCM samples are the single largest remaining gap between our rendered
audio and actual NES output for Contra. Fixing this moves percussion
from "recognizably wrong" to "recognizably Contra."

## 3. Current State

**What exists:**
- `PERCUSSION_MODELS.md` documents the full DPCM system: sample
  addresses, configuration table layout, sound code routing, and
  the hybrid noise+DPCM layering mechanism.
- `contra_parser.py` correctly parses the percussion channel and
  emits `DrumEvent` instances with type labels (kick, snare, hihat,
  kick_snare, kick_hihat) that distinguish noise-only from DPCM hits.
- `render_wav.py` has per-type drum rendering with different volume,
  decay, and lowpass parameters for each drum type.

**What is missing:**
- No code reads DPCM sample bytes from the ROM.
- No code decodes the 1-bit delta format to PCM audio.
- `render_wav.py` uses `render_noise_hit()` for all drum types.
  There is no `render_dpcm_sample()` function.
- The `DrumEvent` dataclass carries no sample metadata (address,
  length, rate, initial DAC value).
- The pipeline has no mechanism to pass ROM bytes to the renderer.

## 4. Concrete Steps

### Step 1: DPCM Decoder Function

Write a standalone function that converts raw DPCM bytes to a PCM
float32 array. The NES DPCM format works as follows:

- Each byte encodes 8 1-bit deltas, processed LSB first.
- The output is a 7-bit DAC value (range 0-127).
- For each bit: if 1, DAC += 2; if 0, DAC -= 2.
- DAC is clamped to [0, 127] after each step.
- Initial DAC value comes from the $4011 register write.

```
def decode_dpcm(sample_bytes: bytes, initial_dac: int = 64) -> np.ndarray:
    """Decode NES 1-bit delta PCM to float32 audio.

    Each input byte produces 8 output samples. Output range is [-1, 1].
    """
    dac = initial_dac
    samples = []
    for byte in sample_bytes:
        for bit in range(8):
            if byte & (1 << bit):
                dac = min(127, dac + 2)
            else:
                dac = max(0, dac - 2)
            samples.append(dac)
    # Convert 0-127 range to -1.0 to 1.0
    arr = np.array(samples, dtype=np.float32)
    return (arr - 63.5) / 63.5
```

### Step 2: Extract Sample Data from ROM

Contra stores two physical samples in the fixed bank (bank 7):

| Sample | CPU Address | ROM Offset | Size | Description |
|--------|-------------|------------|------|-------------|
| dpcm_sample_00 | $FC00 | iNES header (16) + 7 * 16384 + ($FC00 - $C000) = 0x1C010 | 81 bytes | Hi-hat |
| dpcm_sample_01 | $FCC0 | 0x1C0D0 | 593 bytes | Snare |

ROM offset formula: `INES_HEADER_SIZE + (NUM_PRG_BANKS - 1) * BANK_SIZE + (cpu_addr - 0xC000)`

This is already implemented as `contra_cpu_to_rom()` for addresses
in the $C000-$FFFF range.

The `dpcm_sample_data_tbl` provides per-sound-code configuration:

| Sound Code | Rate ($4010) | Initial DAC ($4011) | Addr ($4012) | Len ($4013) |
|------------|-------------|---------------------|-------------|-------------|
| $5A (hi-hat) | $0F (33 kHz) | $2F (47) | $F0 -> $FC00 | $05 -> 81 bytes |
| $5B (snare) | $0F (33 kHz) | $75 (117) | $F3 -> $FCC0 | $25 -> 593 bytes |
| $5C (hi-hat variant) | $0F (33 kHz) | $00 (0) | $F0 -> $FC00 | $05 -> 81 bytes |

Address formula: `$C000 + register_value * 64`
Length formula: `register_value * 16 + 1`

### Step 3: Build a DPCM Sample Cache

Add a class or dictionary that, given a ROM and a game manifest,
pre-decodes all DPCM samples at parse time:

```
@dataclass
class DPCMSample:
    pcm: np.ndarray       # decoded float32 audio
    rate_hz: float        # playback rate (e.g., 33143.9 for rate $0F)
    initial_dac: int      # $4011 value
    source_addr: int      # CPU address for provenance

NTSC_DPCM_RATES = [
    4181.71, 4709.93, 5264.04, 5593.04,
    6257.95, 7046.35, 7919.35, 8363.42,
    9419.86, 11186.1, 12604.0, 13982.6,
    16884.6, 21306.8, 24858.0, 33143.9,
]
```

### Step 4: Map DrumEvent Types to Samples

The `contra_parser.py` percussion table mapping already distinguishes
which hits use DPCM. Extend the mapping to carry sample references:

- High nibble 1 (snare): sound_5a -> dpcm_sample_00 (hi-hat sample)
- High nibble 2 (hihat): sound_5b -> dpcm_sample_01 (snare sample)
- High nibble 3 (kick_snare): sound_5a + sound_02
- High nibble 4 (kick_hihat): sound_5b + sound_02
- High nibble 6: sound_5c + sound_02
- High nibble 7: sound_5d + sound_02

Note: the disassembly labels are counterintuitive. The `percussion_tbl`
at $82CD maps index 1 to sound_5a and index 2 to sound_5b. Verify
against the actual sample content (81-byte click vs 593-byte crack)
to confirm which is hi-hat and which is snare.

### Step 5: Add `render_dpcm_hit()` to render_wav.py

```
def render_dpcm_hit(sample: DPCMSample, target_samples: int) -> np.ndarray:
    """Render a DPCM sample resampled to the output sample rate."""
    # Resample from DPCM rate to output rate
    ratio = SAMPLE_RATE / sample.rate_hz
    resampled_len = int(len(sample.pcm) * ratio)
    indices = np.arange(resampled_len) / ratio
    int_indices = np.clip(indices.astype(int), 0, len(sample.pcm) - 1)
    resampled = sample.pcm[int_indices]

    # Pad or truncate to target length
    if len(resampled) < target_samples:
        out = np.zeros(target_samples, dtype=np.float32)
        out[:len(resampled)] = resampled
    else:
        out = resampled[:target_samples]
    return out
```

### Step 6: Update `render_song()` Drum Rendering

Replace the `render_noise_hit()` calls for DPCM-bearing drum types
with `render_dpcm_hit()`. For hybrid hits (kick_snare, kick_hihat),
mix the DPCM sample with a noise-channel kick:

```
if dtype == "snare" and dpcm_samples:
    dpcm = render_dpcm_hit(dpcm_samples["snare"], dur_samples)
    mix[start:start+len(dpcm)] += dpcm * 0.20
elif dtype == "kick_snare" and dpcm_samples:
    kick = render_noise_hit(dur_samples, 0.8, 20.0, lowpass=0.7)
    dpcm = render_dpcm_hit(dpcm_samples["snare"], dur_samples)
    mix[start:start+len(kick)] += kick * 0.18
    mix[start:start+len(dpcm)] += dpcm * 0.15
```

### Step 7: Validate

- Decode both samples and inspect waveforms visually (plot or export
  as short WAV files). The hi-hat should be a brief click (~2.4 ms).
  The snare should be a sharp crack (~17.9 ms).
- Render Contra Jungle with DPCM samples, compare to game audio.
- Verify no DC offset drift accumulates across repeated sample triggers
  (each trigger resets DAC via $4011 write).

## 5. Estimated Effort

| Component | Effort |
|-----------|--------|
| `decode_dpcm()` function | 30 min |
| Sample extraction + cache | 1 hour |
| DrumEvent metadata extension | 30 min |
| `render_dpcm_hit()` + resampling | 1 hour |
| Integration into `render_song()` | 1 hour |
| Validation + mixing balance | 1-2 hours |
| **Total** | **5-7 hours** |

## 6. Dependencies

- **No external dependencies.** All decoding uses numpy, which is
  already in the project.
- **ROM access at render time.** Currently `render_wav.py` receives
  a `SongIR` and optionally a `ParsedSong`. To pass DPCM data, either:
  (a) attach decoded samples to the `ParsedSong` or `SongIR`, or
  (b) pass the ROM path and have the renderer extract samples directly.
  Option (a) is cleaner and avoids coupling the renderer to ROM layout.
- **Contra manifest.** The sample addresses and configuration table
  offsets should be recorded in `extraction/manifests/contra.json`
  rather than hardcoded in the renderer. This is consistent with
  the existing architecture rule (manifests before code).

## 7. Risks

### Risk 1: Sample Byte Boundaries
The DPCM length register encodes `L * 16 + 1` bytes. Getting this
formula wrong by even 1 byte means reading past the sample into
unrelated ROM data, producing a click or garbage at the end of every
hit. Mitigation: validate decoded sample length against the known
81 and 593 byte sizes from the disassembly.

### Risk 2: Initial DAC Value Matters
The three sound codes use different $4011 values ($2F, $75, $00).
This sets the DC offset of the decoded waveform. Using a default
value of 64 for all samples will shift the waveform and change the
perceived volume and character. Mitigation: always use the per-sound
initial_dac from the configuration table.

### Risk 3: Resampling Artifacts
The DPCM samples play at 33 kHz but our output is 44.1 kHz. Nearest-
neighbor resampling (as shown in step 5) is adequate for these very
short, low-fidelity samples. Linear interpolation would add minimal
benefit. Do NOT use high-quality resampling (e.g., sinc interpolation)
as it would smooth out the intentionally harsh delta-encoded character.

### Risk 4: Mixing Balance
DPCM samples have a fixed amplitude determined by the delta encoding.
The noise-channel kick has a tunable volume parameter. Getting the
relative balance wrong will make the hybrid hits sound either
DPCM-dominant (thin, clicky) or noise-dominant (muddy). Mitigation:
compare A/B against game audio, adjust mix coefficients empirically.

### Risk 5: Scope Creep to Other Games
This wish is scoped to Contra only. CV1 does not use DPCM. Future
games (Super C, TMNT) may have different sample tables, rates, and
addresses. The decoder function itself is universal (1-bit delta is
a hardware spec), but sample extraction must be per-game. Do not
generalize the extraction code until a second game needs it.

## 8. Success Criteria

1. `decode_dpcm()` correctly decodes both Contra samples. Verify by
   exporting as standalone WAV files and confirming the 81-byte sample
   sounds like a hi-hat click and the 593-byte sample sounds like a
   snare crack.
2. Contra Jungle rendered WAV has audibly distinct hi-hat and snare
   timbres that match the game's percussion character, replacing the
   current uniform white noise approximation.
3. Hybrid hits (kick_snare, kick_hihat) produce layered output with
   both the DPCM transient and the noise-channel body present.
4. No DC offset clicks between consecutive DPCM triggers.
5. Existing CV1 rendering is unaffected (no DPCM code path activates
   when no samples are provided).
6. All 283 DAC changes in Jungle percussion map to the correct sample
   type (verified by spot-checking at least 10 hits across the track).

## 9. Priority Ranking

**Priority: Medium.** This is a fidelity improvement, not a
correctness fix. The current noise-based percussion is recognizably
drum-like and rhythmically correct. DPCM decoding improves timbre
authenticity but does not fix any wrong notes, timing errors, or
missing content.

Rank relative to other wishes:
- Lower priority than volume envelope accuracy (audible across entire
  track, not just drum hits).
- Higher priority than expansion audio support (VRC6/MMC5) because
  Contra is the active game and this improves it directly.
- Roughly equal priority to noise channel parameter extraction (both
  improve percussion fidelity in complementary ways).

Recommended sequencing: complete after Contra volume envelopes are
validated, before moving to new games.
