# Document Air Traffic Control

Where to look for what. Read this before diving into docs/.

## By Task

| If you need to... | Read this |
|---|---|
| Understand the project and its rules | `CLAUDE.md` (router) |
| Work on JSFX/RPP/MIDI (studio side) | `studio/CLAUDE_STUDIO.md` |
| Work on ROM extraction (drivers, parsing) | `extraction/CLAUDE_EXTRACTION.md` |
| Know why the plugin was silent | `docs/BLOOPERS.md` |
| Write or modify a JSFX plugin | `docs/REQUIREMENTSFORSYNTH.md` |
| Write or validate extracted MIDI | `docs/REQUIREMENTSFORMIDI.md` |
| Understand NES sound drivers | `docs/DRIVER_FAMILIES.md` |
| Plan Konami parser work | `docs/FIRST_TARGET_FAMILY.md` |
| Study the Contra sound engine (Rosetta Stone) | `references/nes-contra-us/docs/Sound Documentation.md` |
| Check extraction roadmap | `docs/PHASED_PLAN.md` |
| Generate REAPER projects | `docs/PROJECT_GENERATION.md` |
| Understand the full merger plan | `docs/NESREAPERMEETSSTUDIO.md` |
| See what tools already exist | `docs/DECKARDTOOLREPORT.md` |
| See what to reuse vs build | `docs/WHEELSNOTTOREINVENT.md` |
| See community intelligence for ROM cracking | `docs/COMMUNITYSEARCHREPORT.md` |
| Check current project status | `STATUS.md` |
| Learn RPP format details | `docs/REAPER_PROGRAMMING_REFERENCE.md` |
| Browse APU register details | `docs/REGISTER_MAP.md` |
| Learn about NES instrument presets | `docs/INSTRUMENTS.md` |
| Understand MIDI channel mapping | `docs/MIDI_MAPPING.md` |
| Capture APU traces from Mesen | `docs/TRACE_CAPTURE_GUIDE.md` |
| Operate the extraction pipeline | `docs/OPERATOR_GUIDE.md` |

## By Domain

### Extraction (ROM Cracking)
- `extraction/CLAUDE_EXTRACTION.md` -- Rules and approach
- `extraction/drivers/konami/spec.md` -- Konami driver format (update as decoded)
- `extraction/drivers/konami/NOTES.md` -- Research notes
- `docs/FIRST_TARGET_FAMILY.md` -- Konami attack plan
- `docs/DRIVER_FAMILIES.md` -- Driver catalog
- `docs/PHASED_PLAN.md` -- Extraction roadmap
- `docs/COMMUNITYSEARCHREPORT.md` -- Community intelligence
- `docs/WHEELSNOTTOREINVENT.md` -- What to reuse (CAP2MID, FamiStudio, nesmdb)
- `references/nes-contra-us/` -- Contra disassembly with sound engine docs

### Studio (REAPER/JSFX)
- `studio/CLAUDE_STUDIO.md` -- All 14 blunder rules
- `docs/BLOOPERS.md` -- Full bug stories
- `docs/REQUIREMENTSFORSYNTH.md` -- JSFX plugin spec
- `docs/REQUIREMENTSFORMIDI.md` -- MIDI output spec
- `docs/REAPER_PROGRAMMING_REFERENCE.md` -- RPP format reference
- `docs/REGISTER_MAP.md` -- NES APU registers
- `docs/SYNTHDESIGN.md` -- Synth design notes
- `docs/PROJECT_GENERATION.md` -- How RPP generation works
- `docs/STUDIO_WORKFLOW.md` -- End-user workflow

### Architecture / Planning
- `docs/NESREAPERMEETSSTUDIO.md` -- Full merger plan
- `docs/DECKARDTOOLREPORT.md` -- Tool landscape + boundary analysis
- `docs/MERGE_INIT_PROMPT.md` -- Original merge instructions
- `STATUS.md` -- Current state
