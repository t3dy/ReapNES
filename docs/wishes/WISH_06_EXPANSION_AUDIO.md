# WISH #6: Expansion Audio (VRC6, MMC5)

## 1. What This Wish Is

Add support for NES cartridge expansion audio chips to the extraction
pipeline. Two chips are in scope:

- **MMC5** (mapper 5): 2 additional pulse channels, identical register
  format to the base APU. Used in the US release of Castlevania III:
  Dracula's Curse.
- **VRC6** (mapper 24/26): 2 pulse channels with 8-level duty cycle
  plus 1 sawtooth channel. Used in the Japanese release of Castlevania
  III: Akumajou Densetsu.

This affects every layer of the pipeline: parser (new channel count),
frame IR (new channel types), MIDI export (additional MIDI channels),
render_wav.py (new synth waveforms), generate_project.py (additional
REAPER tracks), and trace_compare.py (expansion register capture).

## 2. Why It Matters

**Castlevania III is the prize.** It is the most musically celebrated
NES Castlevania game and the natural next target after CV1 (complete)
and Contra (in progress). But CV3 cannot be extracted at all without
expansion audio support -- the expansion channels carry critical melodic
content, not optional embellishment.

The Japanese VRC6 version is widely regarded as having the superior
soundtrack due to the sawtooth channel's harmonically rich timbre. The
US MMC5 version had to rearrange its music to compensate for the missing
sawtooth. Both versions are high-value extraction targets.

Beyond CV3, expansion audio unlocks:
- **Just Breed** (MMC5) -- Enix RPG with expansion pulse
- **Madara** and **Esper Dream 2** (VRC6) -- additional Konami VRC6 titles
- Future pathway to Sunsoft 5B (Gimmick!), N163, FDS, and VRC7

## 3. Current State

**No expansion audio support exists.** The pipeline is hardcoded for
4 base APU channels:

- `ChannelIR.channel_type` accepts "pulse1", "pulse2", "triangle" only.
- `DriverCapability` has no `expansion_chip` field.
- `midi_export.py` maps to 4 MIDI channels (pulse1=0, pulse2=1,
  triangle=2, drums=3).
- `render_wav.py` synthesizes pulse (4 duty cycles), triangle, and
  noise. No VRC6 sawtooth, no 8-duty-cycle pulse.
- `trace_compare.py` reads APU registers $4000-$4017 only. VRC6
  registers ($9000-$B002) and MMC5 registers ($5000-$5015) are not
  captured.
- `generate_project.py` creates 4 REAPER tracks. No expansion tracks.
- No manifests exist for CV3 JP or CV3 US.

The architectural foundation is sound: `DriverCapability` dispatches
envelope strategy, and the manifest system separates per-game config
from engine code. The extension points are identified but not built.

## 4. Concrete Steps

### Phase A: MMC5 Support (trivial synth, new plumbing)

MMC5 pulse channels use the exact same register format as base APU
pulse. The synth code already exists. The work is all plumbing.

**A1. Extend DriverCapability and ChannelIR**
- Add `expansion_chip: Literal[None, "mmc5", "vrc6"] = None` to
  `DriverCapability`.
- Add channel types "mmc5_pulse1" and "mmc5_pulse2" to the allowed
  set in `ChannelIR`.
- Ensure `SongIR` handles 6 channels (4 base + 2 MMC5).

**A2. Extend MIDI export**
- Map mmc5_pulse1 to MIDI channel 4, mmc5_pulse2 to MIDI channel 5.
- Same CC11 volume automation as base pulse.
- Same pitch-to-MIDI conversion (MMC5 pulse frequency formula is
  identical to base APU pulse).

**A3. Extend render_wav.py**
- MMC5 pulse uses the existing pulse synth with the same 4 duty
  cycles. Reuse `render_pulse()` for mmc5_pulse1 and mmc5_pulse2.
- Mix MMC5 channels into the output. Note: MMC5 expansion audio mixes
  at a slightly lower level than base APU -- apply a gain factor
  (approximately 0.8x, adjustable by ear).

**A4. Extend generate_project.py**
- Add 2 additional REAPER tracks for MMC5 pulse channels.
- ReapNES_APU.jsfx can drive these as-is (same synth model).

**A5. Extend trace_compare.py**
- Capture MMC5 registers $5000-$5015 in Mesen trace export.
- Add mmc5_pulse1 and mmc5_pulse2 columns to the comparison.
- Document the Mesen trace configuration for expansion registers.

**A6. CV3 US manifest and parser config**
- Create `extraction/manifests/cv3_us.json` with mapper 5, PRG mode,
  bank configuration, pointer table address, and 6-channel layout.
- Determine the sound engine: is CV3 US a Maezawa-family driver with
  expansion channel extensions, or a distinct codebase? This requires
  disassembly analysis. Check `references/` for CV3 disassembly.
- If Maezawa-family: extend the existing parser with MMC5 channel
  awareness. If distinct: write a new parser module.
- Address resolution: mapper 5 uses multi-window banking. The manifest
  must declare PRG mode and all active bank registers. See
  POINTER_MODELS.md section on mapper 5.

**A7. Parse one CV3 US track, listen, validate**
- Extract one well-known track (e.g., "Beginning" / Stage 1).
- Compare to game audio by ear.
- Run trace comparison on all 6 channels.
- Gate: do not batch-extract until the reference track passes.

### Phase B: VRC6 Support (new synth code required)

VRC6 requires new synthesis for the sawtooth channel and an 8-level
duty cycle model for VRC6 pulse.

**B1. VRC6 pulse synth in render_wav.py**
- VRC6 pulse has 3-bit duty (8 levels: 1/16, 2/16, ... 8/16) vs
  base APU's 2-bit duty (4 levels). The waveform generation is
  the same square wave approach but with finer duty resolution.
- Add `render_vrc6_pulse()` alongside existing `render_pulse()`.
- Frequency formula is identical to base APU pulse:
  `CPU_CLK / (16 * (period + 1))`.

**B2. VRC6 sawtooth synth in render_wav.py**
- New waveform type. The sawtooth accumulator adds a 6-bit rate
  value every 2 CPU clocks, resets every 7 steps. High 5 bits of
  the accumulator form the DAC output.
- Approximately 30 lines of synthesis code.
- Rate value controls effective volume; period register controls
  pitch. Frequency formula: same as pulse.

**B3. Extend ChannelIR, MIDI export, REAPER generator**
- Add channel types "vrc6_pulse1", "vrc6_pulse2", "vrc6_saw".
- MIDI channels: vrc6_pulse1=4, vrc6_pulse2=5, vrc6_saw=6.
- VRC6 sawtooth could map to MIDI program 81 (Sawtooth Lead) for
  General MIDI playback. Use CC12 for the 8-level duty on VRC6
  pulse channels.
- REAPER: 3 additional tracks. The JSFX synth needs a "VRC6 saw"
  mode or a separate JSFX instance.

**B4. Extend trace_compare.py for VRC6**
- Capture VRC6 registers $9000-$9002, $A000-$A002, $B000-$B002.
- Add vrc6_pulse1, vrc6_pulse2, vrc6_saw to comparison.
- Handle mapper 24 vs 26 register address swapping (A0/A1 swapped).

**B5. CV3 JP manifest and parser config**
- Create `extraction/manifests/cv3_jp.json` with mapper 24, VRC6
  banking model (16KB + 8KB + 8KB switchable, 8KB fixed), pointer
  table address, and 7-channel layout.
- The JP and US sound drivers are different codebases with partially
  different music data. Do not assume the US parser works on JP.
- Address resolution: VRC6 mapper uses mixed bank sizes. See
  POINTER_MODELS.md section on mapper 24/26.

**B6. Parse one CV3 JP track, listen, validate**
- Same gate as A7: one reference track, ear comparison, trace
  validation on all 7 channels.

## 5. Estimated Effort

| Step | Description | Effort | Notes |
|------|-------------|--------|-------|
| A1 | DriverCapability + ChannelIR extension | 1 session | Mostly type additions |
| A2 | MIDI export for MMC5 | 0.5 session | Trivial channel mapping |
| A3 | render_wav.py for MMC5 | 0.5 session | Reuse existing pulse synth |
| A4 | REAPER generator for MMC5 | 0.5 session | Additional tracks |
| A5 | trace_compare.py for MMC5 | 1 session | Mesen config + new columns |
| A6 | CV3 US manifest + parser | 2-4 sessions | Depends on driver similarity to Maezawa |
| A7 | Validation gate | 1-2 sessions | Debugging, iteration |
| **Phase A total** | | **6-9 sessions** | |
| B1 | VRC6 pulse synth | 0.5 session | 8-duty variation of existing code |
| B2 | VRC6 sawtooth synth | 1 session | New waveform, ~30 lines |
| B3 | ChannelIR + MIDI + REAPER for VRC6 | 1 session | Parallel to MMC5 work |
| B4 | trace_compare.py for VRC6 | 1 session | New register addresses |
| B5 | CV3 JP manifest + parser | 2-4 sessions | Distinct driver from US version |
| B6 | Validation gate | 1-2 sessions | 7 channels to validate |
| **Phase B total** | | **6-9 sessions** | |
| **Grand total** | | **12-18 sessions** | |

The biggest variable is A6/B5: how different are the CV3 sound engines
from the known Maezawa command set? If they share the core command
format (DX/note/FE/FF), the parser work is configuration; if they
diverge significantly, each needs a dedicated parser module.

## 6. Dependencies

**Hard dependencies (must exist before starting):**
- CV3 US ROM image in `AllNESROMs/` -- needed for manifest creation
- CV3 JP ROM image in `AllNESROMs/` -- needed for VRC6 work
- Mesen emulator configured for expansion register trace export
- Disassembly of CV3 sound engine (check `references/` or NESdev
  community resources). Without this, driver identification follows
  the brute-force path documented in CLAUDE.md step 3.

**Soft dependencies (helpful but not blocking):**
- Contra extraction complete (validates the manifest + DriverCapability
  pattern before extending it further)
- `rom_identify.py` enhanced to detect expansion audio mapper type
  (currently reports mapper number but does not flag expansion chips)

**No dependency on:**
- VRC7, N163, FDS, or Sunsoft 5B support -- those are separate wishes
- Any changes to the JSFX synth (REAPER can use raw MIDI for initial
  validation; synth enhancement is follow-up work)

## 7. Risks

### 7.1 CV3 Uses a Different Sound Engine (HIGH)

CV3 may not be a Maezawa-family driver. If it uses a distinct command
set, the existing parser cannot be extended -- a new parser module is
needed. This is the single largest risk because it could double the
effort estimate.

**Mitigation:** Run `rom_identify.py` on both ROMs first. Scan for
DX/FE/FD command signatures. Check for disassembly in the community.
Make a go/no-go decision before writing any parser code.

### 7.2 Mapper 5 Banking Complexity (MEDIUM)

MMC5 has four PRG modes with varying bank granularity. Determining
which mode CV3 uses and which banks contain sound data requires either
disassembly analysis or emulator tracing. Wrong bank = silent
corruption (valid-looking but musically wrong output).

**Mitigation:** Follow the address resolution checklist in
POINTER_MODELS.md. Test with one pointer manually before trusting the
resolver.

### 7.3 Expansion Register Trace Capture (MEDIUM)

Standard Mesen APU trace does not include expansion registers. If
Mesen cannot be configured to log VRC6/MMC5 writes, trace validation
is impossible and we lose ground truth.

**Mitigation:** Verify Mesen expansion trace capability early (before
writing any parser code). If Mesen cannot do it, investigate other
emulators (FCEUX, Nestopia) or NSF-based trace approaches.

### 7.4 JP and US Music Data Divergence (LOW-MEDIUM)

The JP VRC6 soundtrack uses 7 channels; the US MMC5 version uses 6.
The sawtooth parts are either dropped or reassigned. Pointer tables,
channel counts, and potentially the music data itself differ. A parser
for one version will not work on the other.

**Mitigation:** Treat CV3 JP and CV3 US as separate games with
separate manifests. Do not attempt a unified parser.

### 7.5 VRC6 Sawtooth Mixing Level (LOW)

The sawtooth channel mixes at a different amplitude than pulse
channels. Getting the relative level wrong makes the sawtooth either
inaudible or overpowering in the rendered output.

**Mitigation:** Compare rendered output to emulator audio by ear.
Adjust the mixing gain factor iteratively.

## 8. Success Criteria

### Phase A (MMC5): CV3 US Extraction

- [ ] CV3 US manifest exists with verified mapper, banking, and
      pointer table configuration
- [ ] At least one CV3 US track extracted with all 6 channels
      (2 base pulse + triangle + noise + 2 MMC5 pulse)
- [ ] Trace comparison shows 0 pitch mismatches on all pulse channels
      (base and MMC5)
- [ ] MIDI file plays correctly in a General MIDI player with 6
      distinct channel voices
- [ ] render_wav.py produces a WAV with audible MMC5 pulse channels
      at appropriate mix level
- [ ] Human listener confirms the extraction matches game audio

### Phase B (VRC6): CV3 JP Extraction

- [ ] CV3 JP manifest exists with verified mapper 24 banking and
      7-channel pointer table
- [ ] At least one CV3 JP track extracted with all 7 channels
      (2 base pulse + triangle + noise + 2 VRC6 pulse + sawtooth)
- [ ] VRC6 sawtooth renders with correct pitch and characteristic
      buzzy timbre
- [ ] VRC6 pulse renders with 8-level duty cycle (not collapsed to
      4-level base APU duty)
- [ ] Trace comparison shows 0 pitch mismatches on all channels
- [ ] MIDI file has 7 channel voices with distinct sawtooth timbre
- [ ] Human listener confirms the sawtooth sounds correct vs game

### Infrastructure (both phases)

- [ ] `DriverCapability` has `expansion_chip` field dispatching
      correctly
- [ ] `trace_compare.py` validates expansion channels alongside
      base APU channels
- [ ] No regressions: CV1 (0 pitch mismatches on 1792 frames) and
      Contra (existing validation level) still pass

## 9. Priority Ranking

**Priority: HIGH -- but sequenced after Contra completion.**

Rationale:
- CV3 is the most-requested Castlevania extraction target after CV1.
- MMC5 support is architecturally trivial (reuse existing pulse synth)
  and validates the expansion plumbing that all future chips need.
- VRC6 support unlocks the superior JP soundtrack, which is the version
  most NES music fans care about.
- The infrastructure work (DriverCapability extension, multi-channel
  MIDI, expansion trace capture) is foundational for every future
  expansion chip (N163, FDS, Sunsoft 5B, VRC7).

**Recommended sequence within the project roadmap:**
1. Finish Contra volume envelope tables (current priority)
2. WISH #6 Phase A: MMC5 + CV3 US
3. WISH #6 Phase B: VRC6 + CV3 JP
4. Other Maezawa-family games (Super C, TMNT) -- these only need
   base APU and are lower effort once the manifest pattern is proven

**Do not start this wish before:** Contra extraction reaches at least
"volume envelope tables extracted and validated" status. The Contra
work validates the DriverCapability dispatch pattern and the
manifest-driven parser configuration that this wish extends.
