---
layout: default
title: Home
---

# ReapNES

**NES Music Reverse Engineering Studio**

Extract complete musical scores from NES games — notes, volume envelopes, duty cycles, drum patterns — as playable MIDI files and REAPER DAW projects with the ReapNES NES APU synthesizer plugin.

Not WAV recordings. Not tracker modules. **Editable MIDI scores with per-frame synthesizer automation**, ready to open in REAPER and play, edit, remix, or transcribe.

---

## Game Library

Every game below has been extracted to 4-channel MIDI (Pulse 1, Pulse 2, Triangle, Noise) with CC11 volume envelope automation and CC12 duty cycle control.

### Konami

| Game | Year | Tracks | Method |
|------|------|--------|--------|
| Castlevania | 1986 | 15 | ROM parser + NSF |
| Castlevania II: Simon's Quest | 1987 | 9 | NSF emulation |
| Castlevania III: Dracula's Curse | 1989 | 28 | NSF emulation |
| Contra | 1988 | 11 | ROM parser |
| Super C | 1990 | 15 | NSF emulation |
| Gradius | 1986 | 12 | NSF emulation |

### Capcom

| Game | Year | Tracks | Method |
|------|------|--------|--------|
| Mega Man | 1987 | 16 | NSF emulation |
| Mega Man 2 | 1988 | 24 | NSF emulation |
| Mega Man 3 | 1990 | 30+ | NSF emulation |
| Mega Man 4 | 1991 | 30+ | NSF emulation |
| Bionic Commando | 1988 | 20 | NSF emulation |
| Ghosts 'n Goblins | 1986 | — | NSF emulation |
| Section Z | 1987 | — | NSF emulation |
| Strider | 1989 | — | NSF emulation |
| Legendary Wings | 1988 | — | NSF emulation |
| Trojan | 1987 | — | NSF emulation |

### Sunsoft

| Game | Year | Tracks | Method |
|------|------|--------|--------|
| Batman | 1989 | 11 | NSF emulation |
| Blaster Master | 1988 | 16 | NSF emulation |
| Journey to Silius | 1990 | — | NSF emulation |

### Nintendo

| Game | Year | Tracks | Method |
|------|------|--------|--------|
| Super Mario Bros. | 1985 | — | NSF emulation |
| Super Mario Bros. 2 | 1988 | — | NSF emulation |
| Super Mario Bros. 3 | 1988 | — | NSF emulation |
| The Legend of Zelda | 1986 | — | NSF emulation |
| Zelda II: Adventure of Link | 1987 | — | NSF emulation |
| Metroid | 1986 | — | NSF emulation |
| Kid Icarus | 1986 | — | NSF emulation |
| Kirby's Adventure | 1993 | — | NSF emulation |
| Punch-Out!! | 1987 | — | NSF emulation |

### Tecmo

| Game | Year | Tracks | Method |
|------|------|--------|--------|
| Ninja Gaiden | 1988 | — | NSF emulation |
| Ninja Gaiden II | 1990 | — | NSF emulation |
| Ninja Gaiden III | 1991 | — | NSF emulation |
| Rygar | 1987 | — | NSF emulation |

### Other

| Game | Year | Publisher | Method |
|------|------|-----------|--------|
| Marble Madness | 1989 | Rare/Tengen | NSF emulation |
| Faxanadu | 1987 | Hudson/Falcom | NSF emulation |
| Goonies II | 1987 | Konami | NSF emulation |
| Gargoyle's Quest II | 1992 | Capcom | NSF emulation |
| Silver Surfer | 1990 | Arcadia/LJN | NSF emulation |

---

## What You Get

For each game:

- **MIDI files** — 4-track scores (Pulse 1 lead, Pulse 2 harmony, Triangle bass, Noise drums) with CC11 volume envelopes and CC12 duty cycle automation
- **REAPER projects** — .rpp files with ReapNES_APU.jsfx synthesizer loaded per channel, ready to play
- **WAV previews** — NES APU synth renders for quick listening
- **ReapNES Synth Plugin** — JSFX plugin that recreates the NES APU in REAPER

---

## How It Works

### Two Extraction Methods

**ROM Parser** (Castlevania 1, Contra): Reads music data directly from the game ROM using reverse-engineered driver format specifications. Validated frame-by-frame against Mesen 2 APU traces.

**NSF Emulation** (everything else): Runs the game's actual sound driver code on a 6502 CPU emulator, captures every APU register write per frame, and converts to MIDI with synthesizer automation. Works on any NES game regardless of publisher or sound engine.

### The Pipeline

```
NSF file (game sound driver + music data)
  → 6502 CPU emulator (py65)
  → APU register captures ($4000-$4017, 60fps)
  → Note extraction (period → MIDI pitch)
  → Envelope extraction (volume → CC11, duty → CC12)
  → MIDI file (4 tracks + metadata)
  → REAPER project (ReapNES synth per channel)
```

### What Makes This Different

NSF players render audio. FamiTracker importers produce messy per-frame effect dumps. **ReapNES produces clean MIDI scores with synthesizer automation in a professional DAW.** Every note event, volume envelope shape, and duty cycle change from the original game is captured as editable MIDI data driving an accurate NES APU synthesizer plugin.

---

## Downloads

- **ReapNES_APU.jsfx** — NES APU synthesizer plugin for REAPER
- **Source Code** — [github.com/t3dy/ReapNES](https://github.com/t3dy/ReapNES)
- **NSF Extraction Tools** — `nsf_to_reaper.py` converts any NSF file to MIDI + REAPER projects

---

## Technical Documentation

- [NSF to MIDI Pipeline](docs/NSF_TO_MIDI_PIPELINE) — How the 6502 emulator extracts musical data
- [NSF to Synth Plugins](docs/NSF_TO_SYNTH_PLUGINS) — How APU registers map to MIDI CC automation
- [Driver Taxonomy](docs/DRIVER_TAXONOMY) — NES sound driver families across publishers
- [Hardware Variants](docs/HARDWARE_VARIANTS) — NES APU and expansion audio chips
