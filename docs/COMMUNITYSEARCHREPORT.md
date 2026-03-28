# Community Search Report: Konami NES Sound Driver Intelligence

Research conducted 2026-03-27 across NESdev forums, VGMPF wiki, romhacking.net,
GitHub, and Retro Reversing. Everything relevant to cracking Konami's NES sound
driver for our extraction pipeline.

---

## CRITICAL DISCOVERY: Contra Fully Annotated Disassembly

**https://github.com/vermiceli/nes-contra-us**

A COMPLETE, ANNOTATED disassembly of Contra (US) NES exists on GitHub, including
dedicated **Sound Documentation** with the Konami sound driver's internal
architecture documented at the opcode level. This is the Rosetta Stone.

### What It Documents

**Slot System:** 6 sound slots in memory, priority-ordered:
- Slots 0-1: Pulse 1 & 2 (music)
- Slot 2: Triangle (music)
- Slot 3: Noise/DMC (percussion)
- Slots 4-5: Secondary pulse/noise (SFX, higher priority)

**Command Encoding:**
- Bytes < $30: Sound effects (control length, decrescendo, pitch, duty)
- Bytes >= $30: Music sequences (melodic + percussion)
- $2x: Frame delay multiplier + APU config
- $10: Enable/disable sweep and volume decrescendo
- $FD: Branch to child sound command at address
- $FE: Repeat command at address N times
- $FF: Command termination

**Sound Table:** `sound_table_00` maps each sound to its number of slots and
per-channel CPU addresses.

**Frame Execution:** Every video frame, the driver iterates populated slots,
decrements `SOUND_CMD_LENGTH`, and advances to the next command when duration
expires. Pauses when gameplay pauses.

### Why This Matters

Contra uses **Hidenori Maezawa's driver variant** — the SAME driver family
used in Castlevania 1. The command format may differ in details, but the
architecture (slot system, frame-based tick, song table structure) should be
very similar. This disassembly gives us a working model of how the driver
functions before we even open the Castlevania ROM.

**ACTION:** Clone this repo immediately. Read the Sound Documentation. Map the
Contra driver architecture onto our extraction engine design.

---

## CRITICAL DISCOVERY: Castlevania Music Format Document

**https://www.romhacking.net/documents/150/**

"Castlevania Music Format" by Sliver X — described as containing **all the
information you need to know to hack Castlevania melodies.** This is a
downloadable document (not viewable inline on the site). Multiple NESdev
forum users reference it as the definitive byte-level spec for CV1's music
data.

### Known Details (from forum references)

- Control bytes: $E9, $EA = drum triggers; $C0 = rest
- Values $01-$7F and $80-$BF likely map to rests and notes
- Per-channel data pointers for Stage 1 ("Vampire Killer"):
  Square 1: $9C83, Triangle: $9DB5, Square 2: $9D18

**ACTION:** Download this document immediately. It may be the complete command
byte specification we need.

### Also Available

- **[Castlevania III US Music Data](https://www.romhacking.net/documents/922/)** (doc #922) by sl3DZ — CV3 track hacking guide
- **[Hacking NES Music](https://www.romhacking.net/documents/39/)** by Sliver X — General NES music editing methodology via NSF
- **[NES Music Ripping Guide](https://www.romhacking.net/documents/573/)** by Chris Covell — NSF ripping fundamentals

---

## Konami NES Driver Variant Map

The VGMPF wiki documents Konami's full driver lineage. This is critical for
knowing which games share drivers (= which games our parser can handle with
minimal changes).

### Maezawa Driver (our primary target)

Castlevania 1 uses Hidenori Maezawa's driver. Same driver family also used in:

| Game | Notes |
|------|-------|
| **Castlevania** (FDS/NES) | Primary target |
| **Contra** | Fully disassembled (see above) |
| **Super C** | Contra sequel, likely same format |
| **TMNT** | Teenage Mutant Ninja Turtles |
| **The Goonies II** | |
| **Gradius II** | |
| **Getsu Fuuma Den** | |
| **Crackout** | |
| **Top Gun: The Second Mission** | |

**Implication:** Cracking the Maezawa driver for Castlevania gives us ~10+ games.

### Fujio Driver (secondary target)

Atsushi Fujio's variant, used in:

| Game | Notes |
|------|-------|
| **Castlevania II: Simon's Quest** | Different driver than CV1! |
| **Life Force** | |
| **Metal Gear** | |
| **Jackal** | |
| **Blades of Steel** | |
| **Bucky O'Hare** | |
| **TwinBee 3** | Cloned by Chinese devs |
| **Lagrange Point** | VRC7 FM synthesis variant |

**Implication:** CV1 and CV2 use DIFFERENT drivers. Don't assume CV1 findings
transfer to CV2.

### Funahashi/Ogura Driver (tertiary)

| Game | Notes |
|------|-------|
| **Contra Force** | |
| **Snake's Revenge** | |
| **Tiny Toon Adventures 1 & 2** | Cloned by Chinese devs |

### Key Insight: Unlicensed Clones

Chinese/Taiwanese developers (Waixing, Gamtec, etc.) successfully reverse-engineered
and reused Konami drivers from Super Contra, Tiny Toon Adventures, and TwinBee 3.
This proves the drivers ARE crackable and that at least some variants have been
decoded before (just not publicly documented in English).

---

## Castlevania 1 RAM Map (from Data Crystal)

The sound engine's zero-page RAM layout:

| Address | Purpose |
|---------|---------|
| $0080-$008E | Square Wave 1 BGM: duration, octave, track, note address (2 bytes), volume envelope, halt, timbre, fade params, loop address |
| $0090-$009E | Square Wave 2 BGM (identical structure) |
| $00A0-$00AE | Triangle Wave: duration, octave, track, note address, linear counter, loop address |
| $00B0-$00B7 | Noise Channel: duration, octave, track, note address, volume |
| $00C0-$00CE | Square Wave 1 SFX |
| $00D0-$00DE | Square Wave 2 SFX |
| $00AB | Audio Channel Index (80=Sq1, 90=Sq2, A0=Tri, B0=Noise, C0/D0=SFX) |
| $00E0 | Audio Track Address (2 bytes) |
| $00E4 | Audio Track Offset |
| $00E5 | Audio Track |
| $00EF | Pause Music flag |
| $07F6 | Next Sound Effect |

**Key Fields:** Each channel has dedicated bytes for `volume envelope` and `timbre`
— confirming the driver stores instrument behavior per-channel, not just notes.

### ROM Patching Offsets

- $698 (CPU $8688): Compare value — changing this mutes melodic notes
- $646 / $64A: Mute drum sounds
- $5D2 (CPU $85C2): Music disable point (replace with $60/RTS)

---

## Castlevania III Technical Details

### Banking Layout

- Bank #04: Audio Engine + Background Music
- Bank #05: Background Music (overflow)
- Bank #0C: Audio Engine + Sound Effects

### Sound Play Routine

Entry point: $E249 (US) / $E25F (JP). Accumulator value = which sound/music to play.

### Music Track Pointers

Stored as WORDs at $031010-$031020:

| Address | Theme |
|---------|-------|
| $AD92 | Beginning |
| $FD92 | Clockwork |
| $C192 | Mad Forest |

### VRC6 Expansion (JP version)

The Japanese version adds 3 extra channels via VRC6:
- 2 pulse waves (8 duty cycle settings each — vs standard 2A03's 4)
- 1 sawtooth wave (critical for bass — lost in US version)

VRC6 register layout:
```
$9000: Pulse 1 — MDDD VVVV (M=mode, D=duty[3-bit], V=volume[4-bit])
$9001: Pulse 1 period low (8 bits)
$9002: Pulse 1 period high (4 bits) + enable
$A000-$A002: Pulse 2 (same layout)
$B000: Sawtooth accumulator rate (6 bits)
$B001-$B002: Sawtooth period + enable
```

Pulse freq: f = CPU / (16 * (t + 1)). Sawtooth freq: f = CPU / (14 * (t + 1)).

---

## GitHub Repos to Study

### Directly Relevant

| Repo | What | Stars | Action |
|------|------|-------|--------|
| [vermiceli/nes-contra-us](https://github.com/vermiceli/nes-contra-us) | **Full Contra disassembly with sound docs** | — | CLONE AND STUDY |
| [josephstevenspgh/Castlevania-Labelled-Disassembly](https://github.com/josephstevenspgh/Castlevania-Labelled-Disassembly) | Incomplete CV1 disassembly | 8 | Check for sound engine labels |
| [cyneprepou4uk/NES-Games-Disassembly](https://github.com/cyneprepou4uk/NES-Games-Disassembly) | Collection including CV3 disassembly | — | Find CV3 audio engine code |

### Reference Implementations

| Repo | What | Why |
|------|------|-----|
| [bbbradsmith/nsfplay](https://github.com/bbbradsmith/nsfplay) | NSF player with full Konami chip support (VRC6/7) | Reference for expansion chip emulation |
| [bbbradsmith/nes-audio-tests](https://github.com/bbbradsmith/nes-audio-tests) | Hardware behavior test ROMs for APU + expansion chips | Ground truth for APU envelope/sweep behavior |
| [HertzDevil/0CC-FT-NSF-Driver](https://github.com/HertzDevil/0CC-FT-NSF-Driver) | 6502 sound driver supporting all Konami chips | Reference for VRC6/VRC7 register driving |
| [svsdval/VideoGameMusicConverters](https://github.com/svsdval/VideoGameMusicConverters) | Python NSF-to-MIDI/XM converter | Study their note detection approach |

### Homebrew Drivers (architectural reference)

| Repo | What |
|------|------|
| [CutterCross/Sabre](https://github.com/CutterCross/Sabre) | Lightweight NES driver with envelope support (1688 bytes) |
| [Shaw02/nsdlib](https://github.com/Shaw02/nsdlib) | NES sound driver with MML compiler |

---

## NESdev Forum Threads

| Thread | Topic | URL |
|--------|-------|-----|
| Castlevania 1 - turning off music | ROM offsets, music pointers, APU breakpoints | [nesdev.org/viewtopic.php?t=16165](https://forums.nesdev.org/viewtopic.php?t=16165) |
| Sound Effects for Akumajo Densetsu | NSF track count hack for CV3 SFX | [nesdev.org/viewtopic.php?t=11359](https://forums.nesdev.org/viewtopic.php?t=11359) |
| CV3 with Famicom Expansion Audio | VRC6 hardware details, register quirks | [nesdev.org/viewtopic.php?t=25586](https://forums.nesdev.org/viewtopic.php?t=25586) |
| Removing music from NES games | General technique applicable to Konami | [nesdev.org/viewtopic.php?t=21850](https://forums.nesdev.org/viewtopic.php?t=21850) |
| Ripping NSF files to MIDI | Fundamental challenges discussion | [nesdev.org/viewtopic.php?t=6071](https://forums.nesdev.org/viewtopic.php?t=6071) |
| NSF to MIDI discussion | Technical approaches | [nesdev.org/viewtopic.php?t=11634](https://forums.nesdev.org/viewtopic.php?t=11634) |
| NSF disassembly help | NSF structure and disassembly guidance | [nesdev.org/viewtopic.php?t=18081](https://forums.nesdev.org/viewtopic.php?t=18081) |
| CV3 JP with VRC6 on unmodded NES | Register mapping differences | [nesdev.org/viewtopic.php?t=9333](https://forums.nesdev.org/viewtopic.php?t=9333) |

---

## Romhacking.net Documents to Download

| # | Title | Author | What |
|---|-------|--------|------|
| **150** | **Castlevania Music Format** | Sliver X | **THE byte-level CV1 music spec** |
| **922** | Castlevania III US Music Data | sl3DZ | CV3 track hacking guide |
| **39** | Hacking NES Music | Sliver X | General NES music editing via NSF |
| **573** | NES Music Ripping Guide | Chris Covell | NSF ripping fundamentals |

---

## Reverse Engineering Methodology (Community-Established)

The standard approach documented across NESdev forums:

1. Load ROM/NSF in **Mesen** (recommended over FCEUX for APU debugging)
2. Set **write breakpoints** on $4000-$4013 (APU registers)
3. When breakpoint hits, **trace back** through call stack to find the playback subroutine
4. From playback, find the **song-start subroutine** (receives song number, shifts left, indexes pointer table)
5. Pointer table leads to **song headers**: number of streams, channel assignments, initial values
6. Each channel stream = interleaved **note values, durations, and control bytes**
7. Cross-reference with **Sliver X doc #150** for Castlevania 1 specifically
8. Cross-reference with **Contra disassembly** for the Maezawa driver architecture

---

## What Nobody Has Done (Our Novel Contribution)

After exhaustive search:

- **No public tool** parses Konami NES music into MIDI with instrument data
- **No public document** provides a complete, machine-readable spec of any Konami NES driver variant's command set (the Contra disassembly comes closest but is 6502 ASM, not a format spec)
- **No public tool** extracts Konami instrument envelopes or duty cycle tables from ROM
- **KONAMID** (turboboy215) covers GB/GBC only; NES listed as future work
- **ValleyBell/MidiConverters** has Konami MegaDrive support only, not NES
- Multiple Chinese/Taiwanese dev teams cracked Konami drivers but never published specs

**We would be the first public project to:**
1. Document the Maezawa-variant Konami NES driver format as a machine-readable spec
2. Extract instruments (envelopes, duty sequences) from Konami NES ROMs
3. Convert Konami NES music to MIDI with full performance data (CC11/CC12)
4. Generate REAPER projects from Konami NES ROM data

---

## Immediate Next Steps

1. **Download** romhacking.net document #150 (Castlevania Music Format)
2. **Clone** vermiceli/nes-contra-us and read the Sound Documentation
3. **Clone** josephstevenspgh/Castlevania-Labelled-Disassembly
4. **Open** Castlevania ROM in Mesen, set APU write breakpoints, trace the sound engine
5. **Map** the Contra driver architecture onto Castlevania — identify commonalities and differences
6. **Document** findings in `extraction/drivers/konami/spec.md` as we decode each command byte
