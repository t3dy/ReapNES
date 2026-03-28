# First Target Family: Konami Pre-VRC

## Why Konami / Castlevania

1. **Available ROM:** Castlevania (U) (V1.0) is in `roms/`, mapper 2 (UxROM), 128K PRG.
2. **Well-studied:** The Castlevania sound driver has been partially documented by the NES reverse-engineering community.
3. **Clean architecture:** UxROM is a simple mapper — no complex bank switching for music data.
4. **Recognizable music:** "Vampire Killer" (Stage 1) is iconic and easy to validate by ear.
5. **Manageable scope:** ~15–20 songs in the game, simple command format expected.
6. **Contrasts with Phase 6 target:** Konami's simpler format will highlight architectural differences when we tackle Capcom's more complex driver later.

## Concrete Attack Plan

### Step 1: Locate the Music Engine (Phase 2)

**Approach:** Start from the NMI vector and trace the call chain.

1. Read the NMI vector from the ROM header (address at $FFFA-$FFFB in the last PRG bank).
2. Disassemble the NMI handler to find the music update routine call.
3. The music update routine will contain the main play loop:
   - Read the speed counter
   - If counter hits zero, advance sequence position for each channel
   - Write new APU register values
4. Find the song initialization routine (called when music changes):
   - This loads the song table pointer
   - Reads the song header
   - Sets up per-channel data pointers

**Tools:** Static analysis with `pointer_scan.py` + manual ROM inspection.

### Step 2: Map the Song Table (Phase 2)

1. The init routine will load from a pointer table — this is the song table.
2. Each song entry likely contains:
   - Speed byte
   - 4 pointers (one per channel: pulse1, pulse2, triangle, noise)
3. Verify by checking that pointer targets land in plausible data regions.
4. Count songs by scanning until pointers become invalid.

**Deliverable:** `drivers/konami/spec.md` updated with song table offset and format.

### Step 3: Decode the Command Stream (Phase 3)

1. Start at the first channel pointer for Song 0 (probably "Vampire Killer").
2. Read bytes and classify:
   - **Hypothesis:** Values 0x00–0x7F might be note commands (encoding pitch index).
   - **Hypothesis:** Values 0x80+ might be control commands (tempo, loop, envelope, end).
3. Cross-reference with runtime trace:
   - Play Castlevania in Mesen, capture APU trace for Stage 1.
   - Correlate static byte positions with runtime APU writes.
   - Use timing to confirm note durations.
4. Build a command byte table iteratively:
   - Decode one command, test against trace, document, move to next.
   - Mark any unrecognized bytes as UnknownCommand.

**Deliverable:** Working `KonamiPreVRCDecoder` that handles Castlevania's music data.

### Step 4: Extract Songs (Phase 3)

1. Parse at least 3 songs: Stage 1 ("Vampire Killer"), Boss fight, Title screen.
2. Produce Song objects with:
   - ChannelStreams with note events (period values, not pitch names yet)
   - Loop points (from static loop commands)
   - Speed/tempo values
   - InstrumentBehavior stubs from observed envelope patterns
3. Create golden test fixtures from the decoded output.

### Step 5: Reconcile with Traces (Phase 4)

1. Capture Mesen traces for the same 3 songs.
2. Run the dynamic pipeline.
3. Reconcile static Song output with runtime events.
4. Validate:
   - Note timing matches within 2 frames
   - Period values from static decode match runtime period writes
   - Loop behavior matches
5. Adjust confidence scores.

### Step 6: Export (Phase 5)

1. Map periods to MIDI note numbers using the NTSC frequency table.
2. Export per-channel MIDI files.
3. Generate REAPER metadata with duty and volume automation suggestions.
4. Run `/midi-export-audit`.

## Risk Factors

1. **The Konami driver may be more complex than expected.** The command format might have conditional branches, nested subroutines, or bank-switching that complicates static parsing.
   - **Mitigation:** Start with the simplest songs. Use runtime traces as ground truth to disambiguate.

2. **SFX priority may contaminate music channels.** The driver may share channels between music and SFX.
   - **Mitigation:** Trace music from the title screen or during gameplay pauses where SFX are minimal.

3. **Multiple driver revisions across Konami titles.** Castlevania's driver may differ from Contra's or Life Force's.
   - **Mitigation:** Complete Castlevania first, then compare with other Konami ROMs later. Do not assume transferability.

## Success Criteria

The Konami target is **complete** when:
- [ ] Song table found and documented in spec.md
- [ ] Command byte format fully decoded (or all unknowns explicitly documented)
- [ ] 3+ songs produce valid Song objects with patterns, events, and loop points
- [ ] Reconciliation confirms >70% event match with runtime traces
- [ ] MIDI export plays back recognizably as the original music
- [ ] All findings documented with confidence and provenance
- [ ] Golden tests lock in correct output
