# Contra Extraction: Version History

## v1 — First Attempt (Using CV1 Parser)

Ran the CV1 pipeline directly against the Contra ROM. Used the CV1
pointer table offset ($0825) and command format assumptions.

**Result**: 2/15 tracks exported, 13 failed with division-by-zero.
The "working" tracks were accidents — the CV1 pointer table pointed
to random data that happened to partially parse.

**Lesson**: The pointer table is game-specific. Same driver family
does not mean same ROM layout.

## v2 — Contra-Specific Addresses from Disassembly

Extracted the 11 music track addresses directly from the annotated
Contra disassembly (`references/nes-contra-us/`). Still used the
CV1 channel parser with monkey-patched cpu_to_rom for bank mapping.

**Result**: 11/11 tracks exported, but:
- Missing melody parts and nonsense notes
- No drums at all
- Everything sounded "off"

**Root cause**: Three critical command format differences from CV1:
1. DX instrument reads 3 extra bytes for pulse (not 2)
2. $C0-$CF was treated as 1-frame mute (actually a rest with duration)
3. Noise channel uses separate percussion parser (not E9/EA triggers)

**Lesson**: Same driver family shares the note/octave/repeat commands
but diverges on instrument setup, rest semantics, and percussion.
Byte count mismatches after DX cascade into total corruption.

## v3 — Contra-Specific Parser

Built `contra_parser.py` with correct command handling:
- DX reads 3 config bytes for pulse, 1 for triangle
- $C0-$CF computes rest duration = tempo * (lo + 1)
- Noise channel has separate `_parse_percussion` method
- DECRESCENDO_END_PAUSE splits notes into sounding + silent portions
- Drums on their own MIDI channel with correct timing

**Result**: Recognizably Contra. Notes are right, drums present,
timing consistent (all 4 channels align at 3072 frames). But:
- Note articulation still too legato in some sections
- Volume/dynamics completely flat
- Some melody phrasing feels wrong

**Root cause**: decrescendo_mul=0 for many instruments means no
staccato splitting. The game's volume envelope lookup tables
(`pulse_volume_ptr_tbl`) create per-note volume shapes that we
don't model.

## v4 — Minimum Staccato + Default Envelope

Added a minimum staccato gap (dur/6) for notes where decrescendo_mul=0.
This prevents full legato on notes that the game plays with some decay.

**Result**: Better articulation. Still issues with:
- Note durations around measure 20+ feel too long in places
- Pulse 1 tone slightly off (duty cycle changes may need verification)
- Dynamics still mostly flat — no volume shaping per note

## What's Still Missing

### 1. Volume Envelope Lookup Tables (Biggest Gap)
Contra's pulse channels use `pulse_volume_ptr_tbl` to shape each
note's volume over time. There are 8 envelope patterns per level,
selected by the `SOUND_VOL_ENV` byte in each DX instrument command.
Without these tables, notes play at constant volume.

**To fix**: Extract the volume tables from ROM (addresses are in the
disassembly at `pulse_volume_ptr_tbl`), parse the per-frame volume
sequences, and apply them in the frame IR.

### 2. DECRESCENDO_END_PAUSE Interaction with Envelopes
The decrescendo pause and volume envelope interact — the envelope
shapes the first part of the note, then DECRESCENDO_END_PAUSE cuts
the tail. We model the tail cut but not the envelope shape.

### 3. Percussion Sample Mapping
Contra uses DMC samples for hi-hats and snares (sound codes $5A-$5C).
Our drum mapping uses simple GM note numbers. The actual samples
from the ROM could be extracted for more authentic playback.

### 4. Per-Level Differences
The volume envelope tables change per level — level 1 Jungle has
different envelope shapes than level 3 Waterfall. Each track may
need its own set of envelope tables decoded.

### 5. Tone/Duty Verification
Some duty cycle changes ($37 = 12.5%) might be correct for timbral
variety or might indicate a parsing error. A Mesen APU trace for
one Contra track would resolve this.

## Effort Estimate

| Fix | Impact | Complexity |
|-----|--------|------------|
| Volume envelope tables | High (dynamics) | Medium (tables are in disassembly) |
| Per-level envelope switching | Medium | Low (table addresses known) |
| DMC sample extraction | Medium (authentic drums) | Medium |
| Duty cycle verification | Low | Low (needs trace) |
| Full multi-game support | High | High (per-game parser configs) |
