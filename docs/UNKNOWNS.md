---
layout: default
title: "NES Music Studio -- Open Unknowns"
---

# NES Music Studio -- Open Unknowns

A structured list of unsolved problems in this project. Each entry is a
self-contained research task with enough context for someone new to pick
it up. This is a bounty board: find the evidence, build the model,
verify against hardware.

The NES has hundreds of games with undocumented sound engines. Most were
written by individual programmers at Japanese studios between 1985 and
1995, with no surviving source code and no published documentation. The
only path to understanding them is reverse engineering: reading ROM hex,
tracing emulator output, and comparing hypotheses against what the
hardware actually produces. Every unknown listed here is a real gap in
human knowledge about how these games make music. Solving any one of
them teaches you something no manual can.

If you are new to NES reverse engineering, start with UNK-004 or UNK-008.
They require the least specialized knowledge and produce the most
immediately satisfying results. If you want to go deep on hardware
behavior, UNK-001 and UNK-005 will teach you how the APU actually works.
If you want to reverse engineer a sound driver from scratch, UNK-008 is
the gateway.

---

## How to Read Each Entry

- **ID**: Stable reference for cross-linking.
- **Category**: ENGINE (driver software), DATA (ROM content), HARDWARE
  (APU behavior), TOOLING (pipeline infrastructure).
- **Confidence**: How certain we are the problem is real. HIGH = we have
  direct evidence. MEDIUM = strong circumstantial evidence. LOW = we
  suspect but have not confirmed.
- **Priority**: How much solving this blocks other work. CRITICAL =
  blocks multiple tasks. HIGH = blocks one task or significantly improves
  fidelity. MEDIUM = improves quality. LOW = nice to have.
- **Suggested Approach**: Where to start. Not prescriptive -- if you
  find a better path, take it.
- **Estimated Effort**: Rough guide. "Sessions" refers to focused
  investigation periods (2-4 hours each). Solo human work without
  AI assistance may take longer.

---

## UNK-001: Triangle Linear Counter Precision

**Category**: HARDWARE
**Confidence**: HIGH -- 195 volume mismatches in the CV1 Vampire Killer
trace prove the current model is approximate.
**Priority**: MEDIUM -- audible only as occasional bass notes cutting
off 1 frame early or late. Does not affect pitch or timing.

**Description**: The NES triangle channel is gated by a linear counter
at APU register $4008. Our model approximates sounding duration as
`(reload_value + 3) // 4` frames, based on the assumption that the
counter is clocked at 240 Hz (4 times per 60 Hz frame). In practice,
the APU quarter-frame sequencer has jitter: depending on which sub-frame
the note starts, the counter may tick 3 or 5 times in the first frame.
This produces +/-1 frame errors on approximately 8 of 195 triangle
notes in Vampire Killer.

**Evidence**: Trace comparison shows 8 real sounding mismatches on
triangle (the other 187 of the 195 volume mismatches are cosmetic --
both sides silent, disagreeing only on the retained period value).
The `(reload+3)//4` formula is correct to within 1 frame for all
observed reload values. See `docs/HANDOVER_FIDELITY.md` for the linear
counter model derivation and `docs/LATESTFIXES.md` for the fix history.

**Suggested Approach**: Model the APU quarter-frame sequencer explicitly.
The sequencer runs a 5-step sequence (modes 0 and 1) documented in the
NESDev wiki article "APU Frame Counter." Track which step the sequencer
is on when a note starts, count exact clocks to determine how many
decrements occur per frame. Validate against the Mesen trace by
comparing predicted sounding frames to actual `$4008_linear` countdown
values.

**Estimated Effort**: 3-5 sessions. Requires understanding the APU
frame counter. The model change is small (replace integer division with
sequencer simulation) but getting the edge cases right demands careful
trace analysis.

---

## UNK-002: UNKNOWN_SOUND_01 Subtraction

**Category**: ENGINE
**Confidence**: MEDIUM -- the code exists in the Contra disassembly but
we have not observed its effect in any traced track.
**Priority**: LOW -- no known musical impact in currently extracted
games.

**Description**: The Contra disassembly contains a routine labeled
`UNKNOWN_SOUND_01` that subtracts a value from the current note period.
The purpose is unclear. It could be a pitch bend, a detuning effect for
chorus, or a legacy routine from an earlier driver version that is never
called in Contra's music data.

For CV1, the trace comparison now shows 0 pitch mismatches on both
pulse channels, meaning either CV1 does not invoke this routine or its
value is always 0.

**Evidence**: Present in the annotated disassembly at
`references/nes-contra-us/`. Not triggered by any music command in the
Jungle, Waterfall, or Base tracks (the three most thoroughly tested).
May be triggered by sound effect codes or unused music commands.

**Suggested Approach**: Set a breakpoint on the routine address in Mesen
debugger. Play through all Contra stages and sound effects. If it never
fires, it is dead code. If it does fire, capture the context (which
channel, which music code triggered it, what period values change) and
model the behavior.

**Estimated Effort**: 1-2 sessions if using Mesen debugger breakpoints.
Longer if tracing manually.

---

## UNK-003: Mid-Note Duty Cycle Changes

**Category**: DATA
**Confidence**: HIGH -- 2 instances observed in the Contra Jungle trace
at frames 1979 and 2075.
**Priority**: LOW -- rare (2 out of ~3000 frames) and the timbral
difference is subtle.

**Description**: The standard model assumes duty cycle is set once per
note (at the DX instrument command) and remains constant. But the Contra
Jungle trace shows two frames where the pulse duty cycle ($4000 bits
6-7) changes mid-note without a new DX command. This could be a
deliberate timbral effect (duty cycle envelope within the volume lookup
table), a side effect of the volume envelope table writing to the full
$4000 register (which includes duty bits), or an artifact of SFX
priority overriding the music channel momentarily.

**Evidence**: Trace frames 1979 and 2075 in the Contra Jungle pulse1
channel show duty value changing from 2 (50%) to 3 (75%) and back
within a single note. No corresponding DX or instrument command in the
parsed data stream. See `docs/CHECKLIST.md` duty cycle section for
full context.

**Suggested Approach**: Extract the full $4000 register writes for
frames 1975-1985 and 2070-2080 from the trace. Check whether the volume
envelope table entries include the duty bits (they are in the same
register byte -- $4000 format is DDLCVVVV where DD is duty). If so,
the envelope tables need to be modeled as writing the full register,
not just the volume nibble. If not, check for SFX channel activity on
those frames.

**Estimated Effort**: 1-2 sessions. Mostly trace extraction and
comparison against the 54 extracted envelope tables.

---

## UNK-004: DMC Sample Extraction

**Category**: DATA
**Confidence**: HIGH -- the samples exist at known ROM addresses and
the trace shows 283 $4011 DAC changes in the first 1000 frames of
Contra Jungle alone.
**Priority**: HIGH -- currently all percussion is synthesized noise.
Real DPCM samples would dramatically improve the authenticity of kicks,
snares, and cymbals.

**Description**: The NES DMC (delta modulation channel) plays 1-bit
delta-encoded samples from ROM. Contra uses DMC for snare and cymbal
sounds triggered by the percussion channel. The sample addresses and
lengths are available from trace registers $4012 (address) and $4013
(length). The samples are stored in the ROM's last bank (CPU $C000-$FFFF)
at 64-byte aligned addresses.

CV1 uses inline percussion commands (E9/EA) that trigger noise channel
hits, not DMC samples. Contra's DMC samples are a significant fidelity
improvement opportunity.

**Evidence**: Contra disassembly documents the `percussion_tbl` and
DMC setup routines. Trace register $4011 shows rapid DAC value changes
during drum hits, confirming active sample playback. ROM addresses
derivable from $4012 values: `sample_addr = $C000 + ($4012_value * 64)`.
The checklist (`docs/CHECKLIST.md`) documents 283 DAC changes in 1000
frames and notes only 2 noise period values (7 and 31) in the Jungle
track.

**Suggested Approach**:
1. Extract unique ($4012, $4013) pairs from the Contra trace.
2. Read the corresponding bytes from the ROM.
3. Decode DPCM format: each byte is 8 1-bit deltas. Starting from
   DAC value 64, each bit adds or subtracts 1. Clamp to 0-127.
4. Convert to WAV at the NES sample rate (derived from $4010 rate
   index, documented in NESDev wiki "APU DMC" article).
5. Map each percussion table entry to its sample.

This is an excellent first task for someone learning NES audio internals.
The format is simple, the results are immediately audible, and the
samples are short (typically 100-500 bytes each).

**Estimated Effort**: 2-3 sessions. The DPCM format is well-documented.
Most of the work is plumbing (connecting samples to the pipeline and
matching playback timing to drum events).

---

## UNK-005: NES Mixer Nonlinearity

**Category**: HARDWARE
**Confidence**: HIGH -- the nonlinear mixing formulas are documented in
the NESDev wiki and confirmed by hardware measurements.
**Priority**: MEDIUM -- affects overall tonal character but not note
accuracy. Our renders sound "cleaner" than the real hardware because
we mix linearly.

**Description**: The NES audio output path uses a nonlinear DAC. The
two pulse channels share one resistor ladder, and the triangle, noise,
and DMC share another. The mixing formulas are:

```
pulse_out  = 95.88 / (8128 / (pulse1 + pulse2) + 100)
tnd_out    = 159.79 / (1 / (triangle/8227 + noise/12241 + dmc/22638) + 100)
output     = pulse_out + tnd_out
```

This means: two pulse channels at volume 8 do not produce the same
loudness as one channel at volume 16 (which does not exist -- max is
15). Triangle at full amplitude is quieter relative to pulse than a
linear mix would predict. These nonlinearities give NES audio its
characteristic warmth and weight.

**Evidence**: The formulas are derived from hardware analysis by blargg
and kevtris and are used by all accurate NES emulators. Our
`render_wav.py` currently sums channels linearly. See `docs/CHECKLIST.md`
duty cycle / timbre section.

**Suggested Approach**: Implement the lookup-table approximation from
the NESDev wiki in `render_wav.py`. Generate two WAV files (linear vs
nonlinear) of Vampire Killer and compare. The difference is most
audible in sections where all channels are active simultaneously.

**Estimated Effort**: 1 session. The formulas are known; this is pure
implementation work.

---

## UNK-006: Vibrato EB Command

**Category**: ENGINE
**Confidence**: MEDIUM -- the command parsing code exists in the Contra
disassembly but no Contra music data uses it.
**Priority**: LOW for Contra. Potentially HIGH for other Konami games
that may use it heavily.

**Description**: The EB command in the Maezawa driver takes parameters
for vibrato (periodic pitch modulation). The disassembly shows it sets
up an LFO that modulates the period register on each frame. In Contra,
the EB command is parsed but the Jungle, Waterfall, and other traced
tracks contain no EB bytes. It may be used in other Konami titles
(TMNT, Gradius, Super C) where lead melodies need expressive pitch
wobble.

CV1's spec (spec.md) lists EB-EF as invalid for that game, which may
reflect an earlier driver version that lacks vibrato support entirely.

**Evidence**: Contra disassembly documents EB parameter format. No EB
bytes found in any of the 11 parsed Contra tracks. The checklist
(`docs/CHECKLIST.md`) lists vibrato as "NOT IMPLEMENTED" with the note
to look for $4002 period oscillation within a single note in the trace.

**Suggested Approach**: Parse a TMNT or Gradius ROM and search for EB
bytes in the music data streams. If found, capture a Mesen trace of
the relevant section and measure the pitch oscillation (period register
fluctuating within a sustained note). Model as an LFO with depth,
speed, and delay parameters read from the EB command bytes.

**Estimated Effort**: 2-4 sessions. Finding a game that uses EB is the
hard part. Modeling it is straightforward once you have trace data.

---

## UNK-007: Contra Decrescendo Timing Precision

**Category**: ENGINE
**Confidence**: MEDIUM -- approximately 3.4% of volume frames still
mismatch in the Contra Jungle trace after all current fixes.
**Priority**: MEDIUM -- audible as slightly incorrect note tails on
sustained passages.

**Description**: The Contra auto-decrescendo system (bit 7 of the
vol_env byte) causes notes to decay over `vol_duration` frames, pause,
then resume tail decay. The pause-to-resume transition is calculated as
`(decrescendo_mul * vol_duration) >> 4`. Our model implements this but
the remaining 3.4% volume mismatches suggest the timing formula is not
exact. Possible sources of error: the `vol_duration` extraction from
the low nibble may be off by 1, the pause calculation may use a
different rounding mode, or there is interaction with the envelope
table lookup that changes the decay shape.

**Evidence**: Contra trace validation shows pulse1 volume match at
81.7% baseline (v4). After envelope table extraction, bounce-at-1 fix,
and decrescendo improvements, this reached approximately 96.6%. The
remaining mismatches cluster at note tail boundaries -- exactly where
the decrescendo pause/resume transition occurs. See
`extraction/manifests/contra.json` for current validation percentages
and `docs/CHECKLIST.md` volume envelope section for the parameter
status table.

**Suggested Approach**: Dump 20-30 frames around 5 different volume
mismatches using `trace_compare.py --dump-frames`. For each, compare
the exact frame where our model transitions vs where the trace
transitions. Look for a consistent +/-1 frame offset (rounding error)
or a pattern tied to specific envelope table indices (table interaction).
The CV1 envelope investigation (Research Log Session 3) used exactly
this methodology and solved the problem in 2 sessions.

**Estimated Effort**: 2-3 sessions. Requires patient frame-by-frame
analysis. The fix is likely a one-line change once the pattern is found.

---

## UNK-008: Super C / TMNT / Gradius Driver Identity

**Category**: DATA
**Confidence**: LOW -- these games are completely untested. They are
listed as "same driver family" in the spec based on period table
presence, but that proves nothing (see the CV2 lesson: same period
table, completely different engine).
**Priority**: MEDIUM -- each new game validated expands the project's
scope significantly and tests the parser's generality.

**Description**: Several Konami NES titles are believed to use variants
of the Maezawa sound driver: Super C, Teenage Mutant Ninja Turtles,
Gradius, and Goonies II. None have been tested with our extraction
pipeline. The CV2 investigation proved that sharing a period table
does not mean sharing a driver -- CV2 uses a completely different
engine (Fujio variant). Each game requires independent verification.

Super C is the most promising candidate: it is the Contra sequel and
partially worked (9/15 tracks) with the CV1 parser in an early test.
But partial success is the most dangerous state -- it means some
commands parse correctly while others silently corrupt the data stream.
TMNT is interesting because its soundtrack is musically complex
(multiple tempo changes, long songs). Gradius may use an earlier driver
variant.

**Evidence**: `rom_identify.py` can detect the period table and scan
for DX/FE/FD command signatures, giving a preliminary yes/no on driver
family membership. But byte count, pointer table format, percussion
system, and envelope model must all be verified independently. See
`docs/HANDOVER.md` other games section and the per-game differences
table in `extraction/drivers/konami/spec.md`.

**Suggested Approach**:
1. Run `rom_identify.py` on each ROM to check mapper and driver
   signatures.
2. Check `extraction/manifests/` for existing knowledge.
3. Search for annotated disassemblies online (romhacking.net, GitHub,
   Data Crystal wiki).
4. If no disassembly exists, use Mesen's debugger to set breakpoints
   on APU register writes and trace the sound engine entry point.
5. Follow the Per-Game Parser Checklist in
   `extraction/CLAUDE_EXTRACTION.md`.
6. Parse ONE track, listen, compare to game. Do not batch-extract
   until the reference track sounds right.

This is the recommended starting point for aspiring NES ROM hackers.
You will learn the full workflow: ROM analysis, disassembly reading,
hypothesis formation, trace validation. Every game teaches something
the previous one did not.

**Estimated Effort**: 3-6 sessions per game. Faster if an annotated
disassembly exists. Much slower if you are working from raw ROM hex.

---

## UNK-009: Castlevania III VRC6 Expansion Audio

**Category**: HARDWARE
**Confidence**: HIGH that the hardware exists. Completely unexplored
in this project. The most musically interesting target among known
Konami NES titles.
**Priority**: MEDIUM -- substantial payoff but substantial scope.

**Description**: Castlevania III: Dracula's Curse (Japanese version,
"Akumajou Densetsu") uses the VRC6 mapper chip, which adds two extra
pulse channels and one sawtooth channel to the NES audio output. The
US version uses MMC5 (mapper 5) which has two extra pulse channels
but no sawtooth. The Japanese version's soundtrack is widely considered
among the finest on the Famicom, in large part because of the VRC6
expansion audio.

This is a fundamentally different extraction challenge: the expansion
audio registers ($9000-$B002) are not part of the standard NES APU and
are not captured by standard APU traces. The sound driver is also
different from CV1 (different development team, later vintage). Our
entire pipeline assumes 4 standard APU channels. VRC6 support would
require:
- New hardware model for VRC6 pulse (8 duty cycle settings) and
  sawtooth (6-bit accumulator).
- Extended frame IR to carry 7 channels instead of 4.
- New MIDI export mapping for the extra channels.
- REAPER project generation with additional tracks.
- A VRC6-capable WAV renderer (or delegation to Mesen for audio).

**Evidence**: VRC6 audio register documentation is available on the
NESDev wiki. The Japanese CV3 ROM is readily available. No annotated
disassembly is known to exist for the CV3 sound engine.

**Suggested Approach**:
1. Determine if Mesen supports VRC6 register tracing (it likely does
   in the trace logger -- check "Expansion Audio" options).
2. Identify the CV3 sound driver entry point using Mesen debugger
   breakpoints on VRC6 register writes.
3. Map the CV3 command format. It may share some Konami conventions
   (note encoding, octave commands) but the driver will be different.
4. Build a CV3-specific parser following the Per-Game Parser Checklist.
5. Extend `render_wav.py` to synthesize VRC6 channels (2 extra pulse
   with 8 duty cycle settings + 1 sawtooth with 6-bit accumulator).

**Estimated Effort**: 8-15 sessions. This is a substantial project:
new mapper, new audio hardware, new sound driver, no disassembly. But
the musical payoff is high. The VRC6 sawtooth channel produces a sound
unlike anything in standard NES audio.

---

## UNK-010: Per-Game Envelope Table Mapping Logic

**Category**: DATA
**Confidence**: HIGH that the tables exist in Contra. LOW priority
because the current extraction works for known games.
**Priority**: LOW -- only matters when adding new games to the pipeline.

**Description**: The Contra driver selects envelope tables using a
formula: 8 tables per volume level, 7 levels (level 7 has only 6
tables), totaling 54 entries. The `SOUND_VOL_ENV` byte in each DX
command indexes into this structure. The exact mapping logic (which
bits select level vs table within level) is documented in the Contra
disassembly but has not been verified for other Konami games. Super C
and TMNT may use different table counts, level counts, or indexing
formulas.

**Evidence**: 54 envelope tables extracted from Contra ROM bank 1,
verified against disassembly labels. The formula
`table_index = level * 8 + sub_index` holds for all Contra tracks.
See `extraction/manifests/contra.json` envelope_model section.

**Suggested Approach**: When adding a new game (see UNK-008), extract
its envelope tables and check whether the same indexing formula applies.
If not, document the difference in the game's manifest JSON. Check the
`play_note` routine in the disassembly for how `SOUND_VOL_ENV` is
resolved to a table pointer and look for level-dependent offset
calculations.

**Estimated Effort**: 1-2 sessions per game, as part of the broader
driver identification work.

---

## UNK-011: Sweep Unit Usage in Other Konami Games

**Category**: HARDWARE
**Confidence**: LOW -- we have not observed sweep unit activation in
CV1 or Contra, but other Konami games may use it.
**Priority**: LOW -- sweep is a pitch slide effect. If unused, there
is nothing to model.

**Description**: The NES pulse channels have a hardware sweep unit
(registers $4001 and $4005) that automatically adjusts the period
register each half-frame, producing ascending or descending pitch
slides. The Konami driver has code to set the sweep register (command
$10 XX in the Contra disassembly), but neither CV1 nor Contra music
data appears to use it. Sound effects may use sweep for laser and
explosion sounds.

**Evidence**: Trace data for CV1 Vampire Killer and Contra Jungle show
$4001 always at 0 (sweep disabled). The command $10 exists in the driver
code but may only be triggered by SFX codes, not music codes. See
`docs/CHECKLIST.md` pitch section: "Sweep unit ($4001) -- Not used
(Contra/CV1)."

**Suggested Approach**: Search other Konami ROMs for $10 commands in
music data streams (not SFX). Alternatively, set a Mesen breakpoint
on writes to $4001/$4005 and play through several Konami games, filtering
for music context (not SFX). TMNT boss fights and Gradius power-up
jingles are good candidates for sweep effects.

**Estimated Effort**: 1-2 sessions with Mesen debugger. Mostly
exploratory.

---

## UNK-012: Sound Effect Priority System

**Category**: ENGINE
**Confidence**: HIGH that the system exists. Partially understood from
the Contra disassembly.
**Priority**: LOW -- sound effects are not part of music extraction.
Relevant only if the project expands to SFX ripping or full audio
scene reconstruction.

**Description**: The Konami driver allocates 6 channel slots: 4 for
music ($80-$B0) and 2 for sound effects ($C0-$D0). SFX channels
override music channels when active -- the music data continues
advancing but its output is suppressed. This is visible in traces as
brief periods where the music channel's register values are overwritten
by SFX values.

The priority system determines which SFX wins when multiple are
triggered simultaneously. The Contra disassembly shows a priority
byte per sound code, but the comparison logic and preemption rules
are not fully documented.

**Evidence**: The channel memory layout in `extraction/drivers/konami/spec.md`
documents the 6-slot architecture (channels at $80, $90, $A0, $B0, $C0,
$D0). The FLAGS byte (offset +$08) bit 0 indicates SFX active. The
Contra disassembly labels `SOUND_PRIORITY` values but the comparison
routine has not been fully traced.

**Suggested Approach**: Trace the SFX dispatch routine in the Contra
disassembly. Document the priority comparison: does higher priority
preempt, or does the currently-playing SFX always win? Check whether
music state is preserved or corrupted when SFX override ends. This
matters for scene reconstruction accuracy and for explaining trace
anomalies (like UNK-003) that may be caused by SFX channel sharing.

**Estimated Effort**: 2-3 sessions of disassembly reading. The code
is in the Contra annotated source at `references/nes-contra-us/`.

---

## Summary Table

| ID | Category | Confidence | Priority | Effort | One-Line Summary |
|----|----------|------------|----------|--------|-----------------|
| UNK-001 | HARDWARE | HIGH | MEDIUM | 3-5 sessions | Triangle linear counter off by 1 frame on some notes |
| UNK-002 | ENGINE | MEDIUM | LOW | 1-2 sessions | Mystery period subtraction routine in Contra driver |
| UNK-003 | DATA | HIGH | LOW | 1-2 sessions | Duty cycle changes mid-note in 2 Contra Jungle frames |
| UNK-004 | DATA | HIGH | HIGH | 2-3 sessions | DPCM drum samples exist but are not extracted |
| UNK-005 | HARDWARE | HIGH | MEDIUM | 1 session | Linear mixing instead of NES nonlinear DAC curve |
| UNK-006 | ENGINE | MEDIUM | LOW | 2-4 sessions | Vibrato command exists in driver but unused in Contra |
| UNK-007 | ENGINE | MEDIUM | MEDIUM | 2-3 sessions | 3.4% volume mismatches in Contra decrescendo tails |
| UNK-008 | DATA | LOW | MEDIUM | 3-6 per game | Multiple Konami games completely untested |
| UNK-009 | HARDWARE | HIGH | MEDIUM | 8-15 sessions | CV3 VRC6 expansion audio -- sawtooth + extra pulse |
| UNK-010 | DATA | HIGH | LOW | 1-2 per game | Envelope table indexing may differ across games |
| UNK-011 | HARDWARE | LOW | LOW | 1-2 sessions | Sweep unit may be used in games beyond CV1/Contra |
| UNK-012 | ENGINE | HIGH | LOW | 2-3 sessions | SFX priority and preemption rules partially understood |

---

## For Aspiring ROM Hackers

The NES library contains over 700 licensed titles released in North
America alone, plus hundreds more for Famicom. The vast majority have
completely undocumented sound engines. A few prolific composers
(Kinuyo Yamashita, Hidenori Maezawa, Manami Matsumae, Takashi Tateishi)
wrote drivers that were reused across multiple titles within a
publisher, but each implementation has per-game differences in ROM
layout, command extensions, and data encoding.

No two sound engines are identical. Even within the same publisher and
the same driver family, every game is a new puzzle. Castlevania 1 and
Contra share a note encoding scheme but differ in pointer table format,
DX byte count, percussion system, envelope model, and ROM bank mapping.
Castlevania 2 shares a period table with Castlevania 1 but uses a
completely different sound engine. The period table is universal NES
tuning -- it proves you are looking at a NES game, not which driver
wrote the music.

The tools in this project -- `rom_identify.py` for initial analysis,
`trace_compare.py` for hardware validation, the frame IR for per-frame
modeling -- are designed to make each subsequent game faster to reverse
engineer. But the intellectual core of the work is always the same:

1. **Find the data.** Where does the music live in ROM? What is the
   pointer table format? Which bank contains the sound engine code?
2. **Understand the commands.** What do the bytes mean? How many bytes
   does each command consume? What state does each command modify?
3. **Model the behavior.** How does the driver interpret commands on
   each frame? What is the envelope shape? When does the channel
   silence?
4. **Verify against hardware.** Does our model match what the NES
   actually produces? Frame by frame, register by register.

The evidence hierarchy matters. In decreasing reliability:

1. APU trace (hardware ground truth -- what the chip actually outputs)
2. Annotated disassembly (explains why the hardware produces what it does)
3. Automated trace comparison (catches errors but can miss systematic ones)
4. Ear comparison (catches gross mistakes, misses subtle offsets)
5. Reasoning about byte meanings (least reliable, most tempting)

The single most productive action in any investigation is extracting
a small number of real trace frames and looking at the actual values.
Twenty frames of data are worth more than two thousand words of
analysis. Modeling without data produces wrong models. Data without
modeling produces correct models.

Every unknown on this list is an open invitation. Pick one, form a
hypothesis, test it against the hardware, and document what you find --
whether the hypothesis was confirmed, disproven, or inconclusive. That
is the entire methodology. The NES is not going to tell you its
secrets voluntarily. You have to ask precise questions and listen
carefully to the answers.
