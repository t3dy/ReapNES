---
layout: default
title: "Has This Been Done Before? A Survey of NES Music Extraction"
---

# Has This Been Done Before? A Survey of NES Music Extraction

## Summary

NES music preservation and extraction is a well-explored space in terms
of **playback** (NSF ripping, emulator recording) and **academic
datasets** (NESMDB). What is NOT well-covered is **structured
data extraction from ROM** with frame-level fidelity validation against
hardware behavior. This document surveys what exists, what each project
does and does not do, and where NES Music Studio fits.

---

## 1. Existing Projects and Tools

### NSF / NSFe Ripping

**What it is**: The NES Sound Format (NSF) is the dominant standard for
NES music preservation. An NSF file contains the game's sound engine
code plus a thin shim that calls the play routine once per frame. NSFe
extends it with track names and durations.

**Tools**: NSFImport, ROMs2NSF, various per-game NSF rippers. Nearly
every commercial NES game has been ripped to NSF (the set at
vgmrips.net and zophar.net is close to complete).

**What it does**: Plays back NES music exactly as the game would, using
the actual driver code running in an emulated 6502 CPU. Perfect
fidelity because it IS the original code.

**What it does NOT do**: Extract any structured data. An NSF is a
black box --- you feed it a frame tick and it writes to APU registers.
You cannot get note events, tempo, volume envelopes, or song structure
from an NSF without running it and logging APU register writes (which
is what emulator tracing does). NSF preserves the *program*, not the
*data*.

**Relevance**: NSF is the gold standard for playback fidelity. Our
trace comparison methodology essentially uses NSF-equivalent playback
(Mesen APU trace) as ground truth.

---

### NESMDB (NES Music Database)

**What it is**: An academic dataset created by Chris Donahue et al.
(2018, "The NES Music Database: A multi-instrumental dataset with
expressive performance attributes"). Published at ISMIR.

**What it does**: Runs NSF files through an emulator, logs APU register
writes per frame, and converts those register logs into a piano-roll
representation. The dataset covers ~5000 songs from the licensed NES
library. Each song is represented as a multi-track sequence of
(pitch, volume, timbre) tuples at 60Hz frame resolution.

**What it does NOT do**:
- Does NOT extract data from ROM. It plays NSF files and records output.
- Does NOT model the sound driver's command format or song structure.
- Does NOT produce MIDI with musical semantics (measures, tempo, key).
- Does NOT handle looping, repeats, or subroutine calls --- it records
  a fixed number of frames of linear playback.
- Does NOT distinguish between driver types or per-game differences.
- The output is a machine-learning-friendly matrix, not a
  human-readable transcription.

**Relevance**: NESMDB's register-logging approach is similar in spirit
to our trace comparison, but they use it as the *output* (dataset
generation) while we use it as *validation* (checking our parser
against ground truth). NESMDB answered "what does the APU do?" while
we answer "what does the ROM data say, and does our interpretation
match what the APU does?"

---

### VGMTrans

**What it is**: A tool for extracting sequence and instrument data from
console game ROMs. Supports SNES (with strong SPC700 driver coverage),
PS1, PS2, GBA, NDS, and others.

**What it does**: Identifies known sound driver formats in ROM data,
parses sequence events, and exports to MIDI + DLS/SF2 instrument banks.
For supported formats, it produces clean MIDI with proper note events.

**What it does NOT do**:
- Has essentially **no NES support**. The NES APU is register-mapped
  with per-game custom drivers, which does not fit VGMTrans's model of
  identifying a standard sequence format in ROM.
- Does not handle the NES's diversity of custom sound engines. Every
  NES developer wrote their own driver; there is no SNES-SPC700
  equivalent standard.
- No APU trace validation or fidelity checking.

**Relevance**: VGMTrans demonstrates that structured extraction from
ROM is valuable and possible when driver formats are known. The NES
is the major gap in its coverage, precisely because of driver diversity.

---

### FamiTracker / FamiStudio

**What they are**: NES music composition tools. FamiTracker (0CC fork
still maintained) is the long-running standard; FamiStudio is a modern
alternative with a cleaner UI.

**What they do**: Let users compose NES music using tracker-style or
piano-roll interfaces, then export to NSF, WAV, or ROM-ready data.
FamiTracker uses its own .ftm format with instruments, patterns, and
effects columns.

**What they do NOT do**:
- Neither tool imports from ROM. They are composition tools, not
  extraction tools.
- FamiTracker has an NSF import feature, but it works by playing the
  NSF and logging register writes (same as NESMDB), then quantizing
  to tracker rows. The result loses song structure and is not
  meaningfully editable.
- FamiStudio's NSF import is similar: play-and-record, not parse.
- Neither understands game-specific driver formats.

**Community request**: "Import NES ROM music into FamiTracker" is one of
the most frequently asked questions in the chiptune community. The
standard answer is "you can't, because every game has its own driver."
Some users manually transcribe by ear or by reading NSF register logs.

**Relevance**: FamiTracker/FamiStudio represent the destination format
many people want. The gap is getting FROM ROM data TO tracker/MIDI
format with correct note boundaries, tempo, and envelopes --- which is
exactly what structured extraction provides.

---

### NSF2MIDI / nsf2midi

**What it is**: Various attempts (mostly abandoned) to convert NSF
playback into MIDI by monitoring APU register writes and detecting note
boundaries.

**What it does**: Plays an NSF, logs period register changes, maps
periods to MIDI notes, and attempts to detect note-on/note-off events
from volume changes.

**What it does NOT do**:
- Struggles with note boundary detection. The NES APU has no concept of
  "note on" --- a note change is just a period register write. Detecting
  whether a period change is a new note or a pitch bend requires
  understanding the driver's intent.
- Cannot recover song structure (loops, repeats, subroutines).
- Volume envelopes are flattened to the frame level --- the parametric
  envelope model (fade_start, fade_step) is invisible.
- Results are typically messy MIDI with many short notes and artifacts.

**Relevance**: NSF-to-MIDI conversion is the "easy path" that avoids
driver reverse engineering but produces inferior results. Our approach
inverts this: understand the driver first, then the MIDI is clean
because we know what each command means.

---

### Game-Specific Disassemblies and Documentation

**What exists**: Annotated disassemblies and partial documentation for
specific games' sound engines:

- **Castlevania 1**: Sliver X's "Castlevania Music Format v1.0" on
  romhacking.net (document #150). Covers note encoding, octave commands,
  and pointer table. Does not cover the envelope system in detail.
- **Contra**: Full annotated disassembly by vermiceli (nes-contra-us on
  GitHub). Covers the complete sound engine including volume envelope
  tables, DX byte format, and percussion system.
- **Mega Man 2**: CAP2MID by Wiki Wikipedia (Wikipedia user, not the
  encyclopedia). A C program that parses Capcom's sound driver format
  and exports MIDI. Capcom-specific, not generalizable.
- **Dragon Quest / Final Fantasy**: Some Japanese documentation of
  Enix/Square sound drivers, mostly in the context of fan translations
  and romhacking.
- **Kirby's Adventure**: HAL Laboratory driver partially documented on
  Data Crystal wiki.
- **Generic NES APU**: NESDev wiki has extensive APU hardware docs but
  does not cover game-specific drivers.

**What this does NOT add up to**: A systematic methodology. Each
document is an isolated effort for one game. There is no framework for
approaching a new game, no validation methodology, and no structured
output format. The Sliver X document, for example, is a plain-text
description with some hex examples --- useful as a starting point, but
not a parser specification.

**Relevance**: These per-game documents are invaluable primary sources.
Our spec.md builds on Sliver X and the Contra disassembly. But the
documents themselves do not extract music --- they describe the format
for humans to read.

---

### Mesen / FCEUX Debugger Tracing

**What it is**: NES emulators with debugging features including APU
register logging, memory watches, and execution tracing.

**What they do**: Mesen's APU trace logs every register write to the
sound chip, producing a per-frame record of period, volume, duty cycle,
and control register values for all channels. FCEUX has similar
capabilities through its debugger and Lua scripting.

**What they do NOT do**:
- No interpretation of the logged data. A trace tells you WHAT the APU
  did, not WHY (which command caused it, what the song structure is).
- No export to MIDI or any musical format.
- The trace is enormous (thousands of register writes per second) and
  requires custom tooling to analyze.

**Relevance**: Emulator traces are the foundation of our validation
methodology. We use Mesen APU traces as ground truth and wrote
trace_compare.py to diff our parser's frame IR against the trace at
the frame level. This is, as far as we can determine, a novel
methodology --- using emulator traces not as the extraction mechanism
but as the validation oracle.

---

### VGM / VGZ Format and Logging

**What it is**: Video Game Music format --- a register-write log format
used across many platforms (Master System, Genesis, Game Boy, NES, etc.).
Supported by vgmplay and related tools.

**What it does**: Records APU register writes with timing, producing a
lossless capture of what the sound hardware did. Can be played back
through hardware emulation.

**What it does NOT do**:
- Same limitation as NSF: preserves the *output*, not the *structure*.
- VGM for NES is less common than NSF because NSF is more compact
  (stores the program, not the trace).
- No note/event extraction --- it is a raw register log.

---

### GBS/SPC/PSF Family (Other Platforms)

For context, other platforms have more mature extraction ecosystems:

- **SNES**: SPC700 has a relatively standard driver interface, and
  VGMTrans handles many games well. N-SPC (Nintendo's standard driver)
  covers a large fraction of the library.
- **Game Boy**: GBS format is analogous to NSF. Some driver-specific
  extractors exist.
- **PS1/PS2**: SEQ/VAB formats are standardized enough for VGMTrans.

The NES stands out as the platform where **every developer rolled their
own sound driver**, making universal extraction impossible and per-game
reverse engineering necessary.

---

## 2. What Our Approach Does Differently

### Driver-Aware Structured Extraction

Instead of recording APU output and trying to reverse-engineer note
boundaries from register changes, we read the ROM's music data directly
using knowledge of the sound driver's command format. This produces:

- Clean note events with exact pitch, duration, and octave
- Song structure (loops via FE, subroutines via FD/FF)
- Parametric envelope definitions (not just frame-by-frame volume)
- Tempo as a musical concept, not an inferred BPM

### Frame-Level Trace Validation

We do not trust the parser output on its own. Every change is validated
against an emulator APU trace using trace_compare.py, which diffs our
frame IR against Mesen's register log at the individual frame level.
This catches:

- Pitch errors (wrong note or octave)
- Timing errors (note starts/ends on wrong frame)
- Volume envelope errors (wrong decay shape)
- Control flow errors (repeat counts, subroutine returns)

The trace is the oracle. Zero pitch mismatches across 1792 frames of
Vampire Killer is not a claim --- it is a measured result.

### Per-Game Manifest System

Each game gets a JSON manifest recording verified facts, hypotheses,
and anomalies. This prevents the "same driver = same layout" mistake
that cost multiple sessions. The manifest records mapper type, pointer
table format, DX byte count, percussion system, and envelope model
as per-game configurations, not hardcoded assumptions.

### MIDI with Musical Semantics

The MIDI output includes:
- CC11 (Expression) automation reflecting the actual per-frame volume
  envelope, not just note-on velocity
- Correct note durations based on the envelope's sounding length (not
  the driver's duration counter, which includes silence)
- Staccato gaps where the hardware silences the channel before the
  next note
- Tempo events derived from the driver's tempo commands

### REAPER Integration and Rendering

The pipeline goes all the way to DAW project files (REAPER .rpp) with
NES APU synth plugins, rendered WAV audio, and MP4 video with YouTube
metadata. This is the "last mile" that most extraction projects skip.

---

## 3. What Remains Unsolved

### The Driver Diversity Problem

The fundamental challenge of NES music extraction is that there is no
standard sound driver. Estimates from the romhacking community suggest
30-50+ distinct sound engines across the licensed NES library. Major
families include:

- Konami (Maezawa variant, Fujio variant, VRC6/VRC7 variants)
- Capcom (shared across Mega Man, Bionic Commando, etc.)
- Nintendo (several internal engines for different teams)
- Sunsoft (distinctive bass engine in games like Batman, Blaster Master)
- Konami VRC6/VRC7 (expansion audio chips with extra channels)
- Namco N163 (wavetable expansion)
- Jaleco, Tecmo, Taito, and dozens of smaller studios

Each requires its own parser. There is no shortcut.

### Expansion Audio

Games using mapper chips with extra sound channels (VRC6, VRC7, MMC5,
N163, FDS) add 1-8 additional channels with different capabilities
(sawtooth, FM synthesis, wavetable). These are less documented than
the base APU and require chip-specific modeling.

### Percussion and DPCM

The NES noise channel and DPCM sample channel are poorly handled by
most extraction approaches. Noise uses a different pitch model (period
modes rather than note frequencies), and DPCM samples are raw 1-bit
delta-encoded audio with no standard indexing.

### Volume Envelope Diversity

CV1's parametric envelope (fade_start + fade_step) is specific to the
Maezawa driver. Other drivers use lookup tables (Contra), hardware
envelopes, or more complex multi-phase shapes. Each needs its own
modeling.

### Systematic Error Detection

Our project discovered that automated trace comparison can show zero
mismatches while the output is still wrong (the octave-off-by-12
incident, where both trace and parser agreed on the wrong absolute
pitch). Human listening remains necessary for catching systematic
errors that are consistent across both sides of the comparison.

### Tempo and Timing Recovery

Most NES music does not use constant tempo. Tempo changes are embedded
in the data stream (DX commands in Konami's driver). Recovering
musical timing (measures, beats, time signatures) from frame-level
data requires understanding the driver's tempo model, which varies
per engine.

---

## 4. The Landscape in Summary

| Approach | Examples | Extracts Structure? | Validates Fidelity? | Per-Game? |
|----------|----------|--------------------|--------------------|-----------|
| NSF ripping | ROMs2NSF | No (playback only) | N/A (IS the original) | No |
| Register logging | NESMDB, VGM | No (raw APU output) | N/A (IS ground truth) | No |
| NSF-to-MIDI | nsf2midi variants | Attempts (lossy) | No | No |
| FamiTracker import | FT NSF import | Attempts (quantized) | No | No |
| Game-specific docs | Sliver X, CAP2MID | Partial (manual) | No | Yes |
| VGMTrans | VGMTrans | Yes (for supported platforms) | No | Yes (driver-aware) |
| **NES Music Studio** | **This project** | **Yes (ROM data)** | **Yes (trace diff)** | **Yes (manifest)** |

The key insight: **most NES music preservation is playback-based, not
data-based**. NSF files preserve the ability to play the music but not
the ability to understand, edit, or re-arrange it. NESMDB records what
the APU did but not what the composer wrote. The unexplored territory
is structured extraction --- reading the composer's data as the driver
reads it, validating against hardware behavior, and producing output
that preserves musical intent.

This is a large space. With 700+ licensed NES games and 30+ driver
families, systematic coverage would be a multi-year effort. But the
methodology --- manifest-driven, trace-validated, driver-specific
parsing --- is generalizable. Each new driver added to the system
unlocks dozens of games.

---

## 5. Key References

- Donahue, C. et al. "The NES Music Database." ISMIR 2018.
  https://github.com/chrisdonahue/nesmdb
- Sliver X. "Castlevania Music Format v1.0." romhacking.net doc #150.
- vermiceli. "nes-contra-us" annotated disassembly.
  https://github.com/vermiceli/nes-contra-us
- VGMTrans. https://github.com/vgmtrans/vgmtrans
- NESDev Wiki, APU documentation. https://www.nesdev.org/wiki/APU
- FamiTracker. https://famitracker.com
- FamiStudio. https://famistudio.org
- Data Crystal NES disassembly wiki. https://datacrystal.tcrf.net
- Mesen emulator (APU trace logging). https://www.mesen.ca
