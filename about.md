---
layout: default
title: About
---

# About ReapNES

## The Project

ReapNES extracts complete musical scores from NES games and converts them into editable MIDI files with synthesizer automation for the REAPER digital audio workstation.

This is not audio recording. It's **reverse engineering the actual musical performance data** — every note, every volume envelope shape, every duty cycle change — from the game's sound driver, and translating it into a format that modern music production tools can work with.

## Two Methods, One Output

### Method 1: ROM Parser (Original)

The project started by reverse-engineering Konami's Maezawa sound driver from Castlevania 1 and Contra. A custom parser reads the game ROM's music data structures, extracts note events with frame-level timing, and validates every pitch and volume value against Mesen 2 APU traces — frame-by-frame comparison of our output against real hardware register writes.

**Castlevania 1 achieved 0 pitch mismatches across 1,792 frames of Vampire Killer.** Contra reached 96.6% volume accuracy with a validated two-phase envelope model.

This method produces the highest fidelity output but requires weeks of reverse engineering per sound driver family. It works for Konami's Maezawa driver (Castlevania, Contra, Super C) but not for other publishers.

### Method 2: NSF Emulation (New — March 2025)

The breakthrough: instead of reverse-engineering each publisher's music format, **run the game's actual sound driver on a 6502 CPU emulator**.

NSF files (Nintendo Sound Format) contain the sound driver code extracted from the game ROM. Our emulator (built on py65) loads the NSF, calls the driver's INIT and PLAY routines, and captures every APU register write at 60fps. These register captures are identical to what the real NES hardware produces — they contain the complete musical performance.

The register data is then converted to MIDI: period values become note events, volume registers become CC11 automation, duty cycle changes become CC12 automation. The output format is identical to what the ROM parser produces.

**This works on ANY NES game regardless of publisher or sound engine.** No format reverse engineering needed. The driver does the decoding for us.

The NSF method opened the project from 2 games (Castlevania, Contra) to **35+ games across 6 publishers** in a single session.

## How Much Easier Is the New Method?

| Aspect | ROM Parser | NSF Emulation |
|--------|-----------|---------------|
| Setup time per game | Days to weeks | Minutes |
| Requires format documentation | Yes | No |
| Works across publishers | No (per-driver) | Yes (universal) |
| Needs Mesen trace capture | Yes (for validation) | No |
| Needs disassembly | Helps enormously | Not at all |
| Output quality | Frame-perfect (validated) | Frame-accurate (driver-produced) |
| Games supported | ~5 (Maezawa family) | ~3,000+ (any NSF on Zophar's) |

The ROM parser remains valuable for the deepest analysis — understanding exactly how a sound engine works, why it makes the choices it does, and how to modify the data. But for extracting playable MIDI scores, the NSF emulator is dramatically faster and works everywhere.

## The Technical Journey

The project's documentation captures the full reverse engineering process:

- **[Driver Taxonomy](docs/DRIVER_TAXONOMY)** — NES sound driver families across publishers
- **[Command Variability](docs/COMMAND_VARIABILITY)** — How command systems differ across drivers
- **[Envelope Systems](docs/ENVELOPE_SYSTEMS)** — Volume envelope types (parametric, lookup, tremolo)
- **[Hardware Variants](docs/HARDWARE_VARIANTS)** — NES APU and expansion audio chips
- **[Failure Modes](docs/FAILURE_MODES)** — 25 cataloged mistakes and how to avoid them
- **[NSF to MIDI Pipeline](docs/NSF_TO_MIDI_PIPELINE)** — How the 6502 emulator extracts music
- **[NSF to Synth Plugins](docs/NSF_TO_SYNTH_PLUGINS)** — APU registers to MIDI CC mapping

## Built With

- **Python** — parsing, emulation, MIDI generation, WAV rendering
- **py65** — 6502 CPU emulator for NSF playback
- **mido** — MIDI file creation
- **numpy** — NES APU waveform synthesis
- **REAPER** — DAW for playback and editing
- **ReapNES_APU.jsfx** — Custom NES APU synthesizer plugin
- **Claude Code** — AI-assisted reverse engineering and development

## Status

### Complete
- Castlevania 1 (15 tracks, ROM parser, frame-validated)
- Contra (11 tracks, ROM parser)
- Mega Man 1 (16 tracks, NSF emulation)
- Bionic Commando (20 tracks, NSF emulation)
- Blaster Master (16 tracks, NSF emulation)
- Batman (11 tracks, NSF emulation)
- Castlevania 2 (9 tracks, NSF emulation)

### Processing
- 25+ additional games running through NSF batch extraction

### Coming Soon
- Piano roll video generation from MIDI
- Guitar tablature conversion
- Standard music notation / sheet music
- Downloadable soundtrack ZIP packages
