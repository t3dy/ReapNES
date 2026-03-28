# Deckard Tool Report: NES Music Extraction Landscape

## What We're Building vs What Already Exists

Our goal: **ROM -> full-fidelity extraction (notes + instruments + envelopes + duty cycles) -> REAPER project that sounds like the original NES game.** Community tool, CLI-first, 2-3 driver families.

Nobody has built exactly this. But significant pieces exist. Here's the full landscape.

---

## TIER 1: Tools That Do Part of What We Want

### FamiStudio (CRITICAL — study this first)
- **What:** Full NES music editor with NSF import, composition, and export
- **URL:** https://famistudio.org/ | https://github.com/BleuBleu/FamiStudio
- **NSF Import:** Plays NSF through NotSoFatso emulator core, logs APU writes at 60fps, records into tracker format
- **Instrument extraction:** DOES NOT extract structured instruments. All envelopes become frame-by-frame effect commands. Reconstructing instruments is manual.
- **Why it matters to us:** FamiStudio's NSF import is essentially what our dynamic analysis pipeline does (emulate -> log APU -> record events). Their demo songs were made by reverse-engineering NSFs this way. Their source code shows exactly how to capture APU state.
- **What they DON'T do:** No driver-specific parsing. No ROM analysis. No instrument table extraction. No confidence/provenance. No REAPER output. No automation of the "reconstruct instruments from frame data" step.
- **Boundary classification:** DETERMINISTIC (emulation + APU logging)
- **Action:** Study their NSF import code in `FamiStudio/Source/` for the APU capture loop.

### CAP2MID by turboboy215 (CRITICAL — closest to our extraction goal)
- **What:** Converts NES ROM music data directly to MIDI for Capcom games
- **URL:** https://github.com/turboboy215/CAP2MID
- **How it works:** Reverse-engineered Capcom's NES sound driver format. Reads ROM bytes, parses the sequence data, outputs MIDI. Supports NES, SNES, GB/GBC.
- **Why it matters:** This is EXACTLY what our Capcom driver parser needs to do. turboboy215 has already cracked Capcom's NES sound engine.
- **Limitation:** Written in C, outputs MIDI only (no instrument/envelope extraction), no REAPER integration, no confidence scoring. Single-purpose CLI.
- **Boundary classification:** DETERMINISTIC (ROM byte parsing -> MIDI)
- **Action:** Study the NES-specific code for Capcom's command byte format. This could accelerate our Capcom driver by months.

### KONAMID by turboboy215 (IMPORTANT — but GB/GBC only)
- **What:** Konami sound driver to MIDI converter for Game Boy/GBC
- **URL:** https://github.com/turboboy215/KONAMID
- **Limitation:** GB/GBC only, NOT NES. Konami used different drivers per platform. However, the general approach (find song table, decode command bytes, output MIDI) is identical to what we need.
- **Planned:** The repo mentions planned NES support but it hasn't been implemented.
- **Action:** Study the command decoding approach. The GB driver structure may inform NES driver expectations.

### ValleyBell/MidiConverters (USEFUL — large collection of driver-specific converters)
- **What:** 50+ converters for various game music formats to MIDI
- **URL:** https://github.com/ValleyBell/MidiConverters
- **NES support:** Has an NES converter based on Somari's sound driver disassembly
- **Konami support:** Has a MegaDrive Konami converter (not NES) that exports MIDI AND instrument data (GYB files)
- **Why it matters:** The MegaDrive Konami converter with `-InsAnalyse` option proves that instrument extraction from ROM is achievable. The approach (disassemble driver, write format-specific converter) is the same.
- **Boundary classification:** DETERMINISTIC
- **Action:** Study the NES converter and the Konami MegaDrive converter for architectural patterns.

### nsf2midi (USEFUL — but limited)
- **What:** Classic Win32 tool that converts NSF to MIDI via emulation
- **URL:** https://www.zophar.net/utilities/converters/nsf2midi.html
- **Also:** Python package on PyPI: https://pypi.org/project/nsf2midi/
- **How it works:** Emulates NSF playback, monitors APU register writes, attempts to reconstruct note events from raw register data
- **Limitation:** Does NOT extract instruments or envelopes. Outputs bare MIDI. Struggles with note detection (hard to distinguish "note" from "register write" without understanding the driver). No driver-specific parsing.
- **Why it matters:** Demonstrates the limits of emulation-only extraction. Our approach (driver-specific parsing) should produce far better results.
- **Boundary classification:** DETERMINISTIC but PROBABILISTIC note detection

### vgm2midi by JamesDunne (USEFUL — emulation-based)
- **What:** NSF/SPC to MIDI converter based on higan (accurate console emulation)
- **URL:** https://github.com/JamesDunne/vgm2midi
- **Limitation:** Same fundamental problem as nsf2midi: works from APU register level, doesn't understand the driver format. Cannot extract instruments.

---

## TIER 2: Tools for the Studio/Synth Side

### Nintendo VST by Matt Montag (STUDY)
- **What:** Free VST plugin that faithfully emulates the NES 2A03 chip
- **URL:** https://www.mattmontag.com/projects-page/nintendo-vst
- **Why it matters:** Built to match the 2A03 chip specs, evaluated against FamiTracker's Blip Buffer. Has portamento, legato, pitch bend, velocity. If this already does what ReapNES_APU does but better, we should consider using it instead.
- **Boundary classification:** DETERMINISTIC (synth engine)
- **Action:** Test in REAPER. Compare sound quality to ReapNES_APU.jsfx. If it handles volume envelopes via MIDI CC, it might eliminate the need to add envelope support to our JSFX plugin.

### Plogue Chipsounds (REFERENCE)
- **What:** Commercial plugin ($95) that emulates actual NES (and other) sound chips
- **URL:** https://www.plogue.com/products/chipsounds.html
- **Why it matters:** The gold standard for authentic chip sound in a DAW. Emulates the actual hardware, not just waveforms. If our REAPER output needs to sound identical to the NES, this is the benchmark.
- **Limitation:** Paid, not scriptable, no ROM import capability
- **Action:** Use as a reference for audio fidelity comparison, not as a component.

### ReaperDAW.Chiptune preset project (MINOR)
- **What:** REAPER preset project for chiptune using Magical 8bit Plug
- **URL:** https://github.com/jiriKuba/ReaperDAW.Chiptune
- **Action:** Low priority. Our JSFX approach is more faithful than generic chiptune presets.

---

## TIER 3: Reference Data and Communities

### NES Music Database (nesmdb) by Chris Donahue (ALREADY IN USE)
- **What:** 5,278 songs from 397 NES games, extracted via APU register logging
- **URL:** https://github.com/chrisdonahue/nesmdb
- **We already have:** 54K preset files extracted from this database in `studio/presets/jsfx_data/`
- **Key insight from paper:** They extract by emulating and logging APU register writes at 44.1 kHz resolution. MIDI output includes CC11 (velocity) and CC12 (timbre/duty cycle) per voice. This is the CC automation approach to encoding envelopes.
- **Action:** Their MIDI format with CC11/CC12 is a proven encoding for NES performance data. Consider adopting their CC mapping standard.

### VGMPF Wiki — Konami Sound Driver Documentation
- **What:** Documents which games used which Konami driver variants, composer credits, general workflow
- **URL:** https://www.vgmpf.com/Wiki/index.php?title=Konami
- **Key finding:** Konami had multiple driver variants (Maezawa's variant, Fujio's variant). Castlevania used an early version. No byte-level format specification exists publicly.
- **Action:** Read the Konami and Castlevania pages for historical context before ROM analysis.

### VGMPF — Famicom/NES Sound Driver List
- **What:** Comprehensive list of which games use which sound drivers
- **URL:** https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List
- **Action:** Use to identify which ROMs share drivers with our target games.

### NESdev Wiki — Audio Drivers
- **What:** Technical documentation of NES audio driver concepts and known engines
- **URL:** https://wiki.nesdev.org/w/index.php/Audio_drivers
- **Action:** Essential reference for understanding driver architecture.

### NESdev Forums
- **What:** Active community of NES reverse engineers and homebrew developers
- **URL:** https://forums.nesdev.org/
- **Key threads:**
  - [Ripping NSF files to MIDI](https://forums.nesdev.org/viewtopic.php?t=6071) — discusses the fundamental challenges
  - [NSF to MIDI](https://forums.nesdev.org/viewtopic.php?t=11634) — technical approaches
  - [How are PCM samples ripped from NES ROMs?](https://forums.nesdev.org/viewtopic.php?t=17096) — DPCM extraction
- **Action:** Search for "Castlevania sound driver" and "Konami music format" threads.

### NSF Importer by rainwarrior
- **What:** FamiTracker mod that imports NSF via emulation, records frame-by-frame data
- **URL:** https://rainwarrior.ca/projects/nes/nsfimport.html
- **Key insight:** Proves that NSF emulation captures raw data, but structured instrument extraction requires manual reverse engineering. This is exactly the gap our project fills.

### loveemu/vgmdocs — Conversion Tools Guide
- **What:** Comprehensive guide to all video game music conversion tools
- **URL:** https://github.com/loveemu/vgmdocs/blob/master/Conversion_Tools_for_Video_Game_Music.md
- **Action:** Check for any NES-specific tools we missed.

### Retro Reversing — NES Reverse Engineering
- **What:** Guides and resources for reverse engineering NES games
- **URL:** https://www.retroreversing.com/nes
- **Action:** Check for Castlevania-specific disassembly resources.

---

## DECKARD BOUNDARY ANALYSIS

### What Should Be DETERMINISTIC (code, not LLM)

| Task | Tool/Approach | Exists? |
|------|--------------|---------|
| ROM byte parsing | iNES header parser | YES (we have it) |
| NMI vector tracing | Static analysis from ROM | YES (scaffolded) |
| Driver code signature matching | Pattern matching on PRG data | YES (scaffolded) |
| Command byte decoding | Per-driver parser (Konami, Capcom) | NO — this is the hard work |
| Instrument table extraction | Per-driver parser | NO |
| APU register logging from NSF | Emulation (FamiStudio approach) | EXISTS EXTERNALLY |
| MIDI output generation | Note/CC encoding | YES (scaffolded) |
| RPP project generation | Template + MIDI reference | YES (working) |
| JSFX synth audio output | DSP code | YES (working, needs envelopes) |
| Validation | Lint + schema checks | YES (working for studio side) |

### What Is PROBABILISTIC (needs judgment)

| Task | Why It Needs Judgment | Who Does It? |
|------|----------------------|--------------|
| Identifying unknown command bytes | Ambiguous byte values need cross-reference with traces | Human + LLM analysis |
| Distinguishing note vs control commands | Byte ranges overlap in some drivers | Human + heuristic |
| Mapping noise channel to drum hits | No universal standard for NES noise-to-percussion | Human-defined lookup table |
| Rating MIDI quality | "Sounds right" is subjective | LLM could assist with heuristics |
| Driver family classification for unknown ROMs | Pattern matching may be ambiguous | Heuristic + confidence score |

### BOUNDARY VIOLATIONS (current architecture)

| Violation | Type | Recommendation |
|-----------|------|----------------|
| No automated check that extraction MIDI meets studio spec | MISSING BOUNDARY | Add `validate.py --boundary` |
| Extraction engine not importable from new repo path | BROKEN BOUNDARY | Fix pyproject.toml / PYTHONPATH |
| LLM used to design scaffolding before any ROM bytes decoded | WASTE | Crack ROM first, scaffold after |
| 3-pipeline reconciliation designed before Pipeline A works | PREMATURE BOUNDARY | Get static parsing working, add dynamic later |

---

## STRATEGIC RECOMMENDATIONS

### 1. Don't reinvent CAP2MID
turboboy215 has ALREADY cracked Capcom's NES sound engine. For our Capcom driver, study and potentially port CAP2MID's C code to Python rather than reverse-engineering from scratch. This could save weeks.

### 2. Don't reinvent FamiStudio's NSF import
For dynamic analysis (Pipeline B), FamiStudio's APU capture code is battle-tested. Study their NotSoFatso integration rather than building our own emulator interface.

### 3. The Konami NES driver IS original work
No public tool extracts Konami NES music from ROM with instrument data. turboboy215's KONAMID is GB/GBC only. ValleyBell's Konami converter is MegaDrive only. VGMPF has no byte-level Konami NES format spec. **This is genuinely novel work.**

### 4. Consider Nintendo VST before extending ReapNES_APU
If Nintendo VST already handles volume envelopes via MIDI CC, the extraction side could target CC output and skip the JSFX envelope rewrite entirely. Test this before committing to synth development.

### 5. Adopt nesmdb's CC mapping as a standard
nesmdb uses CC11 for velocity and CC12 for timbre (duty cycle) at 44.1 kHz resolution. This is a proven encoding for NES performance data and aligns with our MIDI output spec.

### 6. The NESdev forums are the primary knowledge source
No documentation site has the Konami NES byte format. The people who know it are on nesdev.org. Search the forums, and consider posting there to ask if anyone has partial Castlevania driver documentation.

---

## WHAT WE'RE BUILDING THAT NOBODY ELSE HAS

| Capability | Closest Existing Tool | Gap We Fill |
|------------|----------------------|-------------|
| Konami NES driver -> MIDI + instruments | Nothing (GB only via KONAMID) | Full instrument extraction with envelopes |
| ROM -> REAPER project (end-to-end) | Nothing | Complete pipeline |
| Driver-specific extraction with confidence scoring | ValleyBell (no confidence) | Provenance + confidence |
| Full-fidelity NES reproduction in a DAW | Plogue Chipsounds (no ROM import) | Extraction + faithful playback |
| Multi-driver extraction framework | CAP2MID (Capcom only, C, MIDI only) | Python, multi-driver, multi-output |
| Community CLI tool for NES music extraction | Nothing usable | Our primary deliverable |

**Bottom line:** The Konami NES driver parser is genuinely novel. The end-to-end ROM-to-REAPER pipeline is novel. But for Capcom extraction, MIDI encoding standards, and emulation-based APU capture, we should build on existing work rather than starting from scratch.
