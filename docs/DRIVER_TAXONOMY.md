# NES Sound Driver Taxonomy

A reference taxonomy of known NES sound driver families, organized by
publisher/developer lineage. Written for the NES Music Studio pipeline
to inform parser architecture, identify reuse opportunities, and
prevent the driver-conflation errors documented in MISTAKEBAKED.md.

Throughout this document, concerns are separated into three layers:

- **ENGINE** — the sound driver code: command interpreter, sequencer
  loop, envelope processing, channel management. Lives in PRG ROM.
- **DATA** — music data consumed by the engine: note streams, pointer
  tables, envelope tables, instrument definitions. Layout varies per
  game even within the same engine family.
- **HARDWARE** — the NES APU (2x pulse, triangle, noise, DMC) plus
  any expansion audio chips on the cartridge. Fixed per mapper/board.

---

## 1. Konami Pre-VRC (Maezawa Family)

**Our primary target. Two games decoded, architecture well understood.**

### 1.1 Defining Traits

ENGINE: Frame-driven sequencer. One command byte processed per channel
per frame when the duration counter expires. Commands encode pitch in
the high nibble, duration in the low nibble (0x00-0xBF). Tempo set by
DX command (low nibble = frame multiplier). Subroutine calls (FD) and
counted/infinite loops (FE) for structure. Volume processing runs
every frame on active channels via a flags register.

DATA: Varies significantly per game despite shared command opcodes.
Pointer table format, DX extra byte count, envelope parameters, and
percussion encoding all differ. See `extraction/drivers/konami/spec.md`
for the CV1 vs Contra comparison table.

HARDWARE: Base APU only (no expansion chips). Mapper 0 (NROM) for
CV1, mapper 2 (UxROM) for Contra/Super C. Bank switching affects
address resolution but not the engine logic.

### 1.2 Known Games

| Game | Mapper | DX Bytes (pulse) | Envelope Model | Status in Project |
|------|--------|-------------------|----------------|-------------------|
| Castlevania (1986) | 2 (UxROM) | 2 (inst + fade) | Parametric (fade_start/fade_step) | COMPLETE |
| Contra (1988) | 2 (UxROM) | 3 (config + vol_env + decresc) | Lookup table (54 entries) | IN PROGRESS |
| Super C (1990) | 2 (UxROM) | TBD | Likely lookup table | Partial (9/15) |
| TMNT (1989) | 4 (MMC3) | TBD | TBD | Untested |
| Goonies II (1987) | 2 (UxROM) | TBD | TBD | Untested |
| Gradius (1986) | 0 (NROM) | TBD | TBD | Untested |
| Life Force (1988) | 2 (UxROM) | TBD | TBD | Untested |

### 1.3 Reuse Patterns

The note/octave/rest/loop command set (0x00-0xBF, C0-CF, E0-E4,
FD/FE/FF) is shared across the family. What changes per game:

- DX extra byte count and meaning (envelope parametrization vs table index)
- Pointer table location and entry format
- Percussion approach (inline E9/EA vs separate DMC channel)
- Volume envelope strategy (parametric vs lookup table)
- ROM layout (linear vs bank-switched, sound bank location)

### 1.4 Critical Warning

Same period table does NOT prove same driver. CV2 has identical NTSC
period values but uses a completely different sound engine (Fujio
variant, not Maezawa). This mistake cost 4 prompts during the CV2
investigation. See `docs/MOVINGONTOCV2.md`.

---

## 2. Konami VRC Expansion Drivers

### 2.1 VRC6 (Konami VRC6 chip)

ENGINE: Extended sequencer supporting 3 additional channels: 2 extra
pulse channels with 8-level duty cycle control (vs base APU's 4-level)
and 1 sawtooth channel. The sound engine is a distinct codebase from
the pre-VRC Maezawa driver, though command structure philosophy is
similar (byte-encoded pitch/duration).

DATA: Music data must address the 3 expansion channels in addition to
the standard 4/5 APU channels. Instrument definitions include VRC6
register configurations not present in base APU games.

HARDWARE: VRC6 mapper (mapper 24/26). Adds registers at $9000-$9002
(pulse 1), $A000-$A002 (pulse 2), $B000-$B002 (sawtooth). Japan-only
cartridge board in original release.

**Known games**: Castlevania III: Akumajou Densetsu (Famicom version),
Madara, Esper Dream 2.

**Key difference from Maezawa family**: CV3 Famicom uses VRC6; the
US NES release (CV3: Dracula's Curse) uses MMC5 (mapper 5) with
different expansion audio (2 extra pulse channels, no sawtooth). Same
game, different hardware, different driver code for the expansion
channels.

### 2.2 VRC7 (Konami VRC7 chip — FM synthesis)

ENGINE: Fundamentally different from all other NES drivers. The VRC7
contains an OPLL-derivative FM synthesis chip (subset of YM2413) with
6 FM channels. The driver must manage FM patch selection, modulator/
carrier parameters, and FM-specific envelope behavior that has no
analog in the standard APU.

DATA: Instrument patches are FM operator configurations (modulator
level, feedback, attack/decay/sustain/release for both operators).
Music data includes FM patch index per note. Some games use the 15
built-in ROM patches; others define custom patches.

HARDWARE: VRC7 mapper (mapper 85). 6 FM channels via registers at
$9010 and $9030. Japan-only (Lagrange Point is the only known game).

**Known games**: Lagrange Point (1991).

### 2.3 MMC5 Expansion Audio

ENGINE: Simpler expansion than VRC6/VRC7 — adds 2 extra pulse channels
with the same register format as the base APU pulse channels, plus a
PCM channel. The driver extension is relatively straightforward since
the expansion pulses behave identically to base APU pulses.

HARDWARE: MMC5 mapper (mapper 5). Expansion pulse registers at
$5000-$5015. Used in US releases of games that had VRC6 in Japan.

**Known games**: Castlevania III: Dracula's Curse (US), Just Breed,
Uchuu Keibitai SDF.

---

## 3. Capcom

### 3.1 Defining Traits

ENGINE: Capcom used several distinct sound drivers across the NES era,
but the most widely deployed was used across the Mega Man series (2-6)
and other late-era titles. Characteristics include: variable-length
commands, a relatively sophisticated envelope system using indexed
envelope tables stored in ROM, support for pitch slides/portamento,
and a duty cycle rotation feature that cycles through duty values
during sustained notes to create a richer timbre.

The Mega Man driver processes channels sequentially each frame with a
tick-based timing system. Commands tend to be multi-byte with an opcode
byte followed by parameter bytes, rather than the Konami approach of
encoding pitch and duration in a single byte.

DATA: Envelope tables are stored as indexed arrays of per-frame volume
values, similar in concept to Contra's lookup tables but with different
encoding. Instrument definitions reference an envelope table index,
a duty cycle sequence, and pitch envelope parameters. Track pointers
use a header structure with per-channel starting addresses.

HARDWARE: Base APU only for most titles. No expansion chips used by
Capcom on NES.

### 3.2 Known Games and Variants

| Driver Variant | Games | Notes |
|---------------|-------|-------|
| Early Capcom | Mega Man 1, Ghosts'n Goblins | Simpler command set |
| MM2-era | Mega Man 2, DuckTales, Chip'n Dale | Mature engine, duty cycling |
| Late Capcom | Mega Man 3-6, DuckTales 2 | Extended commands, refined envelopes |

### 3.3 Reuse Patterns

Capcom reused their sound driver extensively across titles, with the
MM2-era engine being the most prolific. The data format is largely
stable within each variant generation, making it feasible to support
multiple games with a single parser once the variant is identified.

The duty cycle rotation is a distinctive Capcom fingerprint — if a
game cycles through 12.5% / 25% / 50% duty on sustained pulse notes,
it is likely a Capcom driver.

---

## 4. Nintendo Internal

### 4.1 Defining Traits

ENGINE: Nintendo did not use a single universal sound driver. Different
development teams within Nintendo wrote distinct engines. However,
common patterns include: relatively simple command structures, frame-
counted duration, and direct APU register manipulation without heavy
abstraction layers. Early titles (1983-1986) often had the simplest
engines with minimal envelope processing.

The sound engines for first-party titles were typically written by the
game's composer (Koji Kondo for SMB/Zelda, Hip Tanaka for Metroid/
Kid Icarus). This means the engine was tailored to the composer's
musical needs rather than being a general-purpose reusable library.

DATA: Music data formats vary significantly between games and even
between early and late Nintendo titles. SMB uses a compact custom
format. Zelda uses a different structure optimized for its musical
needs. There is no single "Nintendo format."

HARDWARE: Ranges from base APU only (SMB, Zelda) to FDS expansion
(some Famicom titles like The Legend of Zelda FDS version, Metroid
FDS) to MMC5 (some later titles).

### 4.2 Known Sub-Families

| Sub-Family | Composer | Games | Distinctive Trait |
|-----------|----------|-------|-------------------|
| Kondo early | Koji Kondo | Super Mario Bros., Zelda | Compact encoding, minimal envelopes |
| Kondo late | Koji Kondo | SMB3, Zelda II | More sophisticated, longer command set |
| Tanaka | Hip Tanaka | Metroid, Kid Icarus | Advanced noise usage, atmosphere-driven |
| HAL-adjacent | Various | Kirby's Adventure | Full envelope tables, smooth dynamics |

### 4.3 Reuse Patterns

Low reuse across titles. Each major franchise typically has its own
engine. This is the opposite of Konami's approach where a single driver
family spans many games with data-level variations.

For NES Music Studio: each Nintendo game likely needs its own parser
module. The engineering return on investment for Nintendo games is
lower per-parser than for Konami or Capcom families.

---

## 5. Sunsoft

### 5.1 Defining Traits

ENGINE: Sunsoft's NES sound driver is notable for its sophisticated
use of the base APU to produce sounds that exceed typical NES audio
quality. The key technique is rapid DPCM sample triggering on the
DMC channel to create a pseudo-bass channel with much richer timbre
than the triangle wave. The engine also features precise volume
envelope control and advanced use of hardware sweep units for pitch
effects.

The driver uses a tick-based sequencer with multi-byte commands.
Envelope processing is table-driven with per-frame volume values,
similar in concept to Contra's lookup tables but with finer
granularity and more complex shapes (attack-decay-sustain-release
rather than simple decay).

DATA: Music data includes standard note/duration streams plus DPCM
sample data for the bass technique. The DPCM samples must be aligned
to specific addresses ($C000-$FFFF, 64-byte aligned) due to hardware
constraints. Instrument definitions reference both APU envelope tables
and DPCM sample configurations.

HARDWARE: Base APU only, but exploits the DMC channel in unconventional
ways. The bass technique uses short DPCM samples triggered at high
frequency to approximate pitched bass notes — the DMC acts as a
crude wavetable synth rather than playing long recorded samples.

### 5.2 Known Games

| Game | Year | Notable Audio Feature |
|------|------|----------------------|
| Batman (1989) | 1989 | DPCM bass, aggressive pulse leads |
| Blaster Master (1988) | 1988 | DPCM bass, complex arrangements |
| Journey to Silius (1990) | 1990 | Peak Sunsoft bass, often cited as best NES audio |
| Fester's Quest (1989) | 1989 | Shared engine with Batman |
| Gremlins 2 (1990) | 1990 | Late Sunsoft driver |

### 5.3 Reuse Patterns

High reuse within the Sunsoft catalog from 1988-1990. The DPCM bass
technique is the reliable fingerprint: if a game has a clearly pitched
bass line that sounds too rich for a triangle wave, and the DMC channel
is being triggered rapidly, it is almost certainly a Sunsoft driver.

### 5.4 Pipeline Implications

The DPCM bass technique means Sunsoft games cannot be fully represented
by standard MIDI note-on/note-off with CC11 volume automation. The
bass channel needs either: (a) a dedicated DPCM sample player in the
REAPER synth, or (b) rendering the DPCM bass from ROM samples directly
into WAV. This is a fundamentally different output path from the
Konami pipeline.

---

## 6. Namco

### 6.1 N163 Expansion (Namco 163)

ENGINE: The Namco 163 chip provides up to 8 additional wavetable
synthesis channels. The driver must manage wavetable RAM (128 bytes
shared among all active channels), channel enable/disable, and
per-channel frequency/phase/waveform selection. More active channels
means fewer CPU cycles per channel (they share a single DAC in a
time-multiplexed fashion), so games typically use 4-6 expansion
channels for acceptable audio quality.

DATA: Waveform definitions are 4-bit sample tables stored in the
shared 128-byte wavetable RAM. Music data must include waveform
upload commands and channel configuration in addition to standard
note/duration streams.

HARDWARE: N163 mapper (mapper 19). Wavetable registers at $4800
(data port) and $F800 (address port). The time-multiplexing means
more channels = lower effective sample rate per channel, creating
an audible quality tradeoff.

### 6.2 Known Games

| Game | Expansion Channels Used | Notes |
|------|------------------------|-------|
| Megami Tensei II | 4-6 | Rich pad sounds |
| King of Kings | 4 | Wavetable strings |
| Rolling Thunder | ~4 | Distinctive timbre |
| Erika to Satoru no Yume Bouken | 8 | Maximum channels |
| Final Lap | ~4 | Racing game |

### 6.3 Standard Namco (No Expansion)

Namco also released many games using only the base APU. These use
a separate, simpler driver without wavetable management. Examples
include Pac-Man, Galaga, Dig Dug (NES ports) and various others.

---

## 7. Rare

### 7.1 Defining Traits

ENGINE: Rare's NES sound driver, written primarily by David Wise,
evolved across their NES catalog. Later titles (particularly the
Battletoads era) feature a sophisticated engine with advanced channel
effects including rapid arpeggios, echo simulation using delayed
channel writes, and complex multi-part compositions that push the
4-channel limitation.

DATA: Multi-byte command format with opcodes in the upper range and
note/duration encoded separately. Instrument definitions are relatively
complex, supporting pitch envelopes (for arpeggio effects) and volume
envelope tables.

HARDWARE: Base APU only. Rare achieved their signature sound entirely
through software techniques on the standard hardware.

### 7.2 Known Games

| Game | Year | Audio Character |
|------|------|-----------------|
| Battletoads (1991) | 1991 | Complex arrangements, rapid arpeggios |
| RC Pro-Am (1988) | 1988 | Earlier, simpler variant |
| Snake Rattle 'n' Roll (1990) | 1990 | Mid-era driver |
| Wizards & Warriors (1987) | 1987 | Early variant |

### 7.3 Reuse Patterns

Moderate reuse. The driver evolved across titles but the core
architecture remained recognizable. Rare's approach of simulating
echo/reverb through carefully timed channel writes is a fingerprint.

---

## 8. Tecmo

### 8.1 Defining Traits

ENGINE: Tecmo's driver is known from games like Ninja Gaiden (1-3)
and Tecmo Bowl. It features a standard frame-driven sequencer with
table-based volume envelopes. The Ninja Gaiden games are notable for
cinematic cutscene music with dynamic tempo changes and channel
muting/unmuting for dramatic effect.

DATA: Multi-byte commands, table-based envelopes. Track structure
supports section markers for the cutscene synchronization system.

HARDWARE: Base APU only. Mapper 1 (MMC1) for Ninja Gaiden 1, mapper
4 (MMC3) for sequels.

### 8.2 Known Games

Ninja Gaiden (1988), Ninja Gaiden II (1990), Ninja Gaiden III (1991),
Tecmo Bowl (1989), Tecmo Super Bowl (1991).

---

## 9. Jaleco

### 9.1 Defining Traits

ENGINE: Less documented than major publishers. Jaleco used relatively
simple sound drivers for most titles. Some Jaleco games are notable
for using the Sunsoft 5B expansion chip (an AY-3-8910 derivative
providing 3 additional square wave channels with hardware envelope
generators).

HARDWARE: Base APU for most titles. Sunsoft 5B expansion (mapper 69)
for Gimmick! (1992), which is one of the most sonically advanced NES
games despite being a Jaleco-published Sunsoft-developed title.

### 9.2 Gimmick! Special Case

Gimmick! (Sunsoft 5B expansion) is often attributed to Sunsoft's
engineering despite Jaleco publishing. The 5B chip adds 3 square wave
channels with hardware ADSR envelopes and a noise generator, for a
total of 8 sound channels. The driver is substantially different from
the standard Sunsoft DPCM-bass driver.

---

## 10. Other Notable Drivers

### 10.1 Konami Fujio Variant (CV2 family)

The driver used in Castlevania II: Simon's Quest. Shares the same
NTSC period table as the Maezawa family but has a completely different
command interpreter. Identified during this project's CV2 investigation
as a dead end for the existing Konami parser. Requires independent
reverse engineering.

### 10.2 FDS Audio Expansion

The Famicom Disk System adds a single wavetable synthesis channel with
64-sample, 6-bit waveform and frequency/volume modulation. Games like
The Legend of Zelda (FDS), Metroid (FDS), and Castlevania (FDS) use
this channel for additional bass or lead voices. The driver must
manage wavetable RAM writes and modulation parameters.

### 10.3 Codemasters

Codemasters NES titles (Micro Machines, Dizzy series) used their own
driver, notable for being designed around unlicensed cartridge hardware
that sometimes had different mapper configurations.

### 10.4 Square/Enix (before merger)

Dragon Quest (Enix) and Final Fantasy (Square) NES titles each had
custom sound engines. The Final Fantasy driver evolved across FF1-FF3
with increasing sophistication. These are high-value extraction targets
due to the popularity of the music, but each requires dedicated RE work.

---

## Summary Classification Table

| Family | Publisher | Expansion HW | Envelope Model | Command Style | Reuse Level | Games (est.) |
|--------|-----------|-------------|----------------|---------------|-------------|-------------|
| Konami Maezawa | Konami | None | Parametric or lookup table | Pitch+dur in 1 byte | HIGH | 8-12 |
| Konami Fujio | Konami | None | Unknown | Different from Maezawa | LOW | 2-3 |
| Konami VRC6 | Konami | VRC6 (2 pulse + saw) | Unknown | Similar philosophy to Maezawa | LOW | 3 |
| Konami VRC7 | Konami | VRC7 (6 FM) | FM ADSR | FM-specific | NONE (1 game) | 1 |
| Capcom MM-era | Capcom | None | Table-based + duty cycling | Multi-byte opcode | HIGH | 10-15 |
| Nintendo varied | Nintendo | None / FDS / MMC5 | Varies | Game-specific | LOW | varies |
| Sunsoft DPCM | Sunsoft | None (DPCM trick) | Table-based ADSR | Multi-byte | HIGH | 5-8 |
| Sunsoft 5B | Sunsoft | 5B (3 sq + noise) | HW ADSR + table | Extended | NONE (1 game) | 1 |
| Namco N163 | Namco | N163 (wavetable) | Table-based | Multi-byte | MODERATE | 5-8 |
| Rare | Rare | None | Table + pitch env | Multi-byte | MODERATE | 5-8 |
| Tecmo | Tecmo | None | Table-based | Multi-byte | MODERATE | 5 |

---

## Implications for Our Pipeline

### Architecture Validation

The taxonomy confirms the current ENGINE / DATA / HARDWARE separation
in NES Music Studio is correct and necessary:

1. **Parser layer** (ENGINE) must be per-driver-family, not per-game.
   The Konami Maezawa parser handles CV1 and Contra with game-specific
   configuration (DX byte count, envelope model) dispatched by the
   manifest JSON. This pattern should extend to other families.

2. **Manifest layer** (DATA) must be per-game. Even within the same
   driver family, ROM layout, pointer tables, and envelope encoding
   differ. The `extraction/manifests/*.json` pattern is correct.

3. **Frame IR layer** is driver-agnostic and should remain so. The
   `DriverCapability` dispatch mechanism (volume_model = "parametric"
   vs "lookup_table") can extend to accommodate new envelope models
   (e.g., "fm_adsr" for VRC7, "dpcm_bass" for Sunsoft) without
   changing the IR core.

4. **MIDI export and REAPER generation** are fully hardware-agnostic.
   Expansion chip channels map to additional MIDI tracks. The synth
   plugin (ReapNES_APU.jsfx) would need expansion chip emulation for
   VRC6/VRC7/N163/5B output, but MIDI representation is standard.

### Scaling Strategy

Based on reuse level, the highest-ROI next targets are:

| Priority | Family | Reason |
|----------|--------|--------|
| 1 | Konami Maezawa (remaining games) | Existing parser, just needs config |
| 2 | Capcom MM-era | High reuse, 10-15 games from 1 parser |
| 3 | Sunsoft DPCM | 5-8 games, iconic audio, but needs DPCM path |
| 4 | Tecmo (Ninja Gaiden) | High demand, moderate effort |

### DriverCapability Extensions Needed

To support families beyond Konami, `DriverCapability` will need:

```
volume_model: "parametric" | "lookup_table" | "duty_cycling" | "fm_adsr" | "dpcm_bass"
expansion_chip: None | "vrc6" | "vrc7" | "mmc5" | "n163" | "5b" | "fds"
command_style: "pitch_duration_byte" | "opcode_params"
```

These should be added incrementally as each family is implemented,
not speculatively. Add the field when the first game of that family
passes its trace validation gate.

---

## Failure Risks If Misunderstood

### 1. Driver Conflation (COST: 3-5 prompts per incident)

**The mistake**: Assuming two games use the same driver because they
share a publisher, a period table, or superficial command similarities.

**Examples from this project**:
- CV2 has the same period table as CV1 but a completely different
  engine (Fujio vs Maezawa). Cost: 4 prompts scanning for a pointer
  table that does not exist.
- Contra uses the same note opcodes as CV1 but different DX byte
  count. Cost: 3 prompts debugging wrong byte parsing.

**Prevention**: Always run `rom_identify.py` first. Check the manifest.
Read the disassembly. Never assume driver identity from publisher or
period table alone.

### 2. Envelope Model Mismatch (COST: 2-4 prompts per incident)

**The mistake**: Applying one game's envelope model to another game
in the same family.

**Example**: CV1 uses parametric envelopes (fade_start + fade_step).
Contra uses lookup tables indexed by the DX vol_env byte. Applying
CV1's parametric model to Contra produces correct pitch but wrong
volume shapes.

**Prevention**: The `DriverCapability` dispatch pattern exists
specifically for this. Never branch on game name; branch on declared
capability. Check the manifest's `envelope_model.type` field.

### 3. Expansion Chip Ignorance (COST: entire parser is wrong)

**The mistake**: Writing a parser for a game with expansion audio
using only the base APU channel model.

**Example**: Parsing CV3 (Famicom VRC6) with a 4-channel Maezawa
parser would miss the 3 expansion channels entirely — the music
would be incomplete and the pulse channels might be misinterpreted
if the engine interleaves base and expansion channel data.

**Prevention**: `rom_identify.py` reports mapper type. Mapper
24/26 = VRC6, 85 = VRC7, 5 = MMC5, 19 = N163, 69 = 5B. If an
expansion mapper is detected, STOP and assess before writing any
parser code.

### 4. DPCM Interference (COST: subtle, ongoing)

**The mistake**: Ignoring the interaction between DMC playback and
other channels. On the NES, DMC DMA steals CPU cycles and can cause
audible glitches on pulse/triangle channels. Sunsoft games are
designed around this; naively adding DPCM to a pipeline that does not
account for DMA timing will produce artifacts.

**Prevention**: For Sunsoft games (and any game using DMC samples),
the frame IR must model DMC channel state separately and account for
the DMA cycle-stealing in timing calculations.

### 5. Same Opcode, Different Semantics (COST: 2-3 prompts)

**The mistake**: Assuming command byte 0xE8 (or any opcode) means the
same thing across driver families. E8 enables envelope fade in Konami
Maezawa, but could mean something entirely different in a Capcom or
Sunsoft driver.

**Prevention**: Never reuse command handler code across driver families.
Each family's parser module must decode its own opcode table
independently. Cross-reference with disassembly, not with another
family's parser.

---

## Research Gaps and Confidence

| Topic | Confidence | Source |
|-------|-----------|--------|
| Konami Maezawa command format | HIGH | Disassembly + ROM analysis + this project |
| Konami VRC6/VRC7 channel model | MODERATE | NESdev wiki, hardware documentation |
| Capcom driver structure | MODERATE | NSF ripping community knowledge, MM disassemblies |
| Sunsoft DPCM bass technique | MODERATE | NESdev community analysis, audio comparisons |
| Namco N163 wavetable model | MODERATE | N163 hardware documentation |
| Rare driver internals | LOW | Limited public RE work |
| Tecmo driver internals | LOW | Limited public RE work |
| Jaleco/other minor publishers | LOW | Minimal documentation |

For families marked LOW confidence, disassembly of at least one
reference game is required before writing any parser code. Follow the
workflow in CLAUDE.md: identify ROM, check manifest, find disassembly,
THEN write code.

---

## Appendix: Expansion Chip Hardware Summary

| Chip | Mapper(s) | Extra Channels | Channel Type | Notable Constraint |
|------|-----------|---------------|--------------|-------------------|
| VRC6 | 24, 26 | 3 | 2 pulse (8-duty) + 1 saw | Japan-only boards |
| VRC7 | 85 | 6 | FM synthesis (OPLL subset) | Japan-only, 1 game |
| MMC5 | 5 | 2 (+PCM) | Pulse (same as base APU) | US substitute for VRC6 |
| N163 | 19 | 1-8 | Wavetable (4-bit, shared RAM) | More channels = lower quality |
| Sunsoft 5B | 69 | 3 (+noise) | Square with HW ADSR (AY-3-8910) | 1 known game (Gimmick!) |
| FDS | N/A (disk) | 1 | Wavetable (64-sample, 6-bit) | Famicom Disk System only |

All expansion chips are active only when the cartridge contains the
relevant hardware. The base 2A03 APU (2 pulse + triangle + noise + DMC)
is always present. NSF files declare expansion usage via a flag byte
at offset $7B.
