# Minimum Playable Studio — Milestone Checklist

This defines the smallest version that proves the ReapNES Studio concept.
Every item must be genuinely usable, not aspirational.

## JSFX Plugins

- [x] ReapNES_Full.jsfx — 4-channel APU (Pulse x2 + Triangle + Noise), MIDI-driven
- [x] ReapNES_Instrument.jsfx — Preset-driven envelope playback
- [x] ReapNES_Pulse.jsfx — Focused dual-pulse with oscilloscope
- [x] apu_core.jsfx-inc — Phase accumulators, duty tables
- [x] mixer_nonlinear.jsfx-inc — Hardware DAC mixer
- [x] lfsr_noise.jsfx-inc — 15-bit LFSR noise
- [x] envelope.jsfx-inc — Frame-rate envelope engine
- [ ] DMC channel — not yet implemented (placeholder only)

## Preset Library

- [x] 8 pulse presets (lead x3, pluck, staccato, swell, vibrato, duty sweep)
- [x] 3 triangle presets (bass, pluck, vibrato)
- [x] 5 noise presets (closed hat, open hat, snare, kick, crash)
- [x] 5 Mario presets (overworld lead/harmony/bass, underground lead/bass)
- [ ] Presets tested in REAPER — requires manual verification by user

## Song Sets

- [x] Song set JSON schema defined
- [x] SMB1 Overworld song set
- [x] SMB1 Underground song set
- [ ] Additional game song set (Castlevania, Mega Man, etc.)

## REAPER Integration

- [x] NES_Orchestra.RTrackTemplate — 4 tracks with plugins loaded
- [x] generic_nes.rpp — blank session ready to play
- [x] smb1_overworld.rpp — Mario overworld session
- [x] smb1_underground.rpp — Mario underground session
- [ ] Verify .RPP files open correctly in REAPER (user must test)

## Automation Scripts

- [x] generate_project.py — creates .RPP from song set or generic
- [x] --list-sets and --list-presets commands
- [ ] MIDI import integration in project generator

## Documentation

- [x] STUDIO_GUIDE.md — full user walkthrough
- [x] README.md — studio-oriented project overview
- [x] CLAUDE.md — Claude Code project instructions
- [x] MILESTONE_CHECKLIST.md — this file

## What's NOT in the Minimum Playable Studio

These are real goals but not part of the initial milestone:

- NES-MDB extraction pipeline (tools exist, not yet run to produce presets)
- ROM / NSF register-level extraction
- MIDI import and NES remapping workflow
- Lua automation scripts inside REAPER
- Desktop application / GUI
- Full drum map support in project generator
- Automated testing
