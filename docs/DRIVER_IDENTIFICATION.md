# NES Sound Driver Identification Methods

A technical reference for identifying the sound driver in an unknown NES
ROM. This document catalogs six identification heuristics, ranks their
reliability, provides a decision tree for first-contact analysis, and
maps implications for the NES Music Studio pipeline.

Written from direct experience decoding Castlevania 1, Contra, and the
Castlevania II false-positive investigation.

---

## 1. Period Table Signatures

**Reliability: MEDIUM** -- necessary but not sufficient.

### What It Is

Every NES game that plays pitched music needs a lookup table mapping
note indices to APU timer period values. The NTSC 2A03 CPU clock
(1.789773 MHz) dictates specific period values for standard tuning.
The base octave table for the 12 chromatic notes is:

```
C:1710  C#:1614  D:1524  D#:1438  E:1358  F:1281
F#:1209  G:1142  G#:1078  A:1017  A#:960  B:906
```

These values are derived from physics, not from any particular driver.
Any driver targeting standard Western tuning on NTSC hardware will
contain these exact values (or very close approximations).

### How to Find It

Scan the ROM for the byte signature of the first entry. The value 1710
in little-endian is `$AE $06`. Search for this two-byte sequence, then
verify the subsequent 22 bytes match the remaining 11 entries.

`rom_identify.py` implements this as `find_period_table()`, searching
for the packed signature `struct.pack("<HHH", 1710, 1614, 1524)` and
validating all 12 entries fall in the range 100-2000.

Some drivers store the table in big-endian (`$06 $AE`). Check both
byte orders.

### What It Proves

- The ROM contains pitched music data addressed through a standard
  NTSC tuning table.
- The table's ROM offset reveals which PRG bank contains sound data
  (critical for bank-switched mappers).
- Multiple period table hits may indicate PAL/NTSC dual tables,
  separate music/SFX tables, or duplicated data across banks.

### What It Does NOT Prove

- **It does not identify the driver.** The period table is universal
  NES tuning, not a driver signature. Castlevania II has the same
  period values as Castlevania 1 but uses a completely different sound
  engine (the "Fujio variant"). This false positive cost 4 prompts to
  investigate during the CV2 session.
- It does not reveal the command format, pointer table structure,
  envelope model, or any other driver-specific behavior.

### Failure Mode

Treating a period table hit as driver confirmation. This is the single
most common identification error. The period table narrows the search
to "this bank contains sound data" but says nothing about how that
data is structured.

---

## 2. Opcode Pattern Scanning

**Reliability: HIGH** -- when multiple command patterns co-occur in
the same ROM region, identification is near-certain.

### What It Is

Each sound driver family uses a proprietary command byte format. The
Konami Maezawa driver, for example, uses these distinctive patterns:

- **E8 + DX**: Envelope enable flag followed by instrument/tempo setup.
  E8 sets bit 4 of the channel flags register. The DX byte (high
  nibble $D, low nibble 1-F) sets tempo and is followed by instrument
  parameter bytes.

- **FE + count + 16-bit address**: Repeat command. FE is followed by
  a loop count (1-20 for finite repeats, $FF for infinite loop), then
  a 2-byte little-endian CPU address ($8000-$FFFF range).

- **FD + 16-bit address**: Subroutine call. FD followed by a 2-byte
  target address. The driver saves a return pointer and resumes after
  the subroutine's $FF terminator.

- **E0-E4**: Octave set commands. These appear frequently before note
  data and are stateful (persist until changed).

- **$C0-$CF**: Rest commands with duration in the low nibble.

### How to Scan

`rom_identify.py` implements `detect_maezawa_signature()` which counts
occurrences of three pattern types across the entire ROM:

| Pattern | Threshold (strong) | Threshold (moderate) | Score weight |
|---------|-------------------|---------------------|-------------|
| FE repeat (count 1-20, valid ptr) | >= 20 | >= 5 | 0.4 |
| FD subroutine (valid ptr) | >= 10 | >= 3 | 0.3 |
| E8 + DX cluster | >= 5 | >= 2 | 0.3 |

A combined score >= 0.6 yields "LIKELY MAEZAWA". A score >= 0.3 yields
"POSSIBLE MAEZAWA". Below 0.3 is "NOT MAEZAWA".

### What Makes It Reliable

The co-occurrence of FE/FD/E8+DX patterns in a concentrated ROM region
is highly specific. Individual bytes like $FE or $FD appear everywhere
in ROM (they are valid 6502 opcodes: SBC and SBC indirect), but the
combination of $FE followed by a small count byte followed by a valid
$8000+ pointer is statistically rare outside actual Maezawa music data.

### Per-Driver-Family Signatures

Different driver families have different characteristic patterns:

| Driver Family | Key Signatures | Notes |
|---------------|---------------|-------|
| Konami Maezawa | E8+DX, FE+count+addr, FD+addr, E0-E4 | Note encoding in high nibble (0-B = C through B) |
| Capcom | Variable-length commands, pointer-based streams | Often use a different note encoding scheme |
| Sunsoft | Heavy DPCM usage, compact command format | Distinctive percussion approach |
| Nintendo (varied) | No single signature -- varies per title | SMB, Zelda, Metroid all use different engines |
| FamiTracker | Well-documented NSF export format | Instrument macros as defining feature |

For non-Maezawa drivers, identification requires building a new
signature scanner. The methodology is the same: find 2-3 command byte
patterns that co-occur uniquely in that driver's music data.

### Failure Mode

False positives from 6502 machine code. The byte $E8 is the INX
instruction. In the CV2 investigation, the scanner found E8 bytes, but
they were all in executable code regions, not music data. Cross-
referencing hit locations against the period table location (which marks
the sound data bank) reduces this risk.

---

## 3. Pointer Table Structures

**Reliability: HIGH** -- if found, provides direct access to all track
data.

### What It Is

Every multi-track sound driver needs a table mapping track numbers to
data addresses. The pointer table contains 2-byte little-endian CPU
addresses, one per channel per track.

### Known Formats

| Game | Format | Entry Size | Location Method |
|------|--------|-----------|----------------|
| CV1 | 3 pointers + 3 separator bytes per track | 9 bytes | ROM $0825 (from Sliver X doc) |
| Contra | Flat table, 3 bytes per entry (channel + ptr) | 3 bytes | ROM $48F8 (from disassembly) |

The format varies per game even within the same driver family. CV1
uses 9-byte grouped entries; Contra uses a flat indexed table with a
separate dispatch mechanism.

### How to Find It

**Best method: disassembly.** Search GitHub, romhacking.net, and the
nesdev community for annotated disassemblies of the target game. The
pointer table address is typically referenced in the sound init routine
(called when a new song starts). For Contra, the annotated disassembly
at `references/nes-contra-us/` made this trivial.

**Without disassembly: emulator debugger.** In Mesen, set a write
breakpoint on APU register $4002 (pulse 1 period low). Start a song.
The breakpoint fires inside the driver's note-play routine. Trace
backward through execution to find where the channel's data pointer
was loaded, which leads to the pointer table.

**Last resort: ROM scanning.** Near the period table, look for clusters
of 2-byte values in the $8000-$FFFF range. Valid pointer tables will
have entries that point to addresses within the sound bank. This is
unreliable because many other data structures also contain 16-bit
address values.

### What It Proves

- Confirms the track count and channel layout.
- Provides entry points for parsing every track.
- The table format itself is a secondary driver identification signal
  (9-byte grouped vs flat indexed vs other layouts).

### Failure Mode

Finding a pointer-like data structure that is not actually the music
pointer table. NES ROMs contain many tables of 16-bit addresses (level
data, sprite tables, etc.). Verify by following a pointer and checking
that the data at that address parses as valid music commands.

---

## 4. Mapper Correlations

**Reliability: LOW** -- suggestive context only, never deterministic.

### What It Is

The iNES header (bytes 6-7) encodes the mapper number, which determines
how the CPU addresses ROM banks. Certain mapper types correlate loosely
with time periods, publishers, and ROM sizes.

### Mapper Reference

| Mapper | Name | PRG Size | Bank Switching | Address Resolution | Konami Games |
|--------|------|----------|---------------|-------------------|-------------|
| 0 | NROM | 16-32 KB | None | Linear: CPU $8000 = ROM $0010 | Gradius, Track & Field II |
| 1 | MMC1 | 128-256 KB | 16 KB switchable + 16 KB fixed | Register-controlled banking | CV2, TMNT, Blades of Steel |
| 2 | UNROM | 128 KB | 16 KB switchable + 16 KB fixed (last) | Last bank always at $C000 | CV1, Contra, Super C, Goonies II, Life Force, Jackal |
| 3 | CNROM | 32 KB PRG | CHR banking only | Same as NROM for PRG | (rare for Konami) |
| 4 | MMC3 | 128-512 KB | 8 KB switchable banks | Fine-grained, register-controlled | TMNT, Bayou Billy, TMNT II, Tiny Toon |
| 5 | MMC5 | 128-1024 KB | Complex multi-mode | Most flexible, expansion audio | CV3 (US) |
| 7 | AxROM | 256 KB | 32 KB switchable | Simple, full bank switch | (rare for Konami) |

### What It Tells You

- **Mapper 0**: Simple ROM, no bank switching to worry about. All data
  is linearly addressable. If the period table and command signatures
  are found, parsing is straightforward.

- **Mapper 2**: The most common Konami mapper. Bank-switched with the
  last 16 KB bank fixed at $C000. Sound data is typically in one
  specific bank. Finding which bank requires the period table location
  or a disassembly.

- **Mapper 4 (MMC3)**: More granular banking (8 KB banks). The sound
  bank could be smaller and switched more dynamically. Address
  resolution is more complex.

- **Mapper 5 (MMC5)**: Indicates possible expansion audio (2 extra
  pulse channels). Requires additional APU modeling beyond standard
  2A03.

### What It Does NOT Tell You

- The mapper says nothing about the sound driver. Mapper 2 games
  include both Maezawa-family (CV1, Contra) and non-Maezawa (CV2 uses
  mapper 1, but mapper 2 games could also use non-Maezawa drivers).
- Publisher correlation is loose. Konami used mappers 0, 1, 2, 4,
  and 5 across different titles.

### Practical Value

The mapper determines the address resolution strategy:
- Mapper 0: `cpu_to_rom = cpu_addr - 0x8000 + 0x10`
- Mapper 2: same formula BUT only within the correct bank. The bank
  number must be known.
- Mapper 4/5: more complex formulas depending on bank configuration
  register state.

This is essential for the parser but irrelevant for driver identity.

---

## 5. APU Write Patterns from Trace

**Reliability: HIGH** -- deterministic fingerprint of driver behavior.

### What It Is

An emulator APU trace records every write to the 2A03 audio registers
($4000-$4017) with cycle-accurate timing. The sequence, ordering, and
frequency of these writes constitute a behavioral fingerprint of the
sound driver.

### How to Capture

Using Mesen (recommended emulator for NES debugging):

1. Load the ROM and navigate to a point where music is playing.
2. Open the debugger (Debug > Debugger).
3. Set a trace logger to capture APU register writes.
4. Record for several seconds (100-200 frames).
5. Export the trace as CSV.

The project's `scripts/trace_compare.py` can parse Mesen APU traces
and compare them frame-by-frame against the parser's output.

### Fingerprinting Characteristics

| Characteristic | What It Reveals |
|---------------|----------------|
| Write ordering per frame | Which channel the driver updates first |
| Writes per frame | Driver complexity (simple = 4-8, complex = 12+) |
| $4015 write frequency | How the driver enables/disables channels |
| $4017 write pattern | Frame counter configuration |
| Period register write pattern | Whether hi-byte is written every frame (causes clicks) or only on change |
| Volume register update rate | Envelope model complexity |
| Noise register ($400E/$400F) patterns | Percussion implementation style |
| DPCM register ($4010-$4013) usage | Whether driver uses sample playback |

### Maezawa-Family Fingerprint

The Konami Maezawa driver has these distinctive APU write behaviors:

- Updates all channels sequentially each frame in a fixed order
  ($80/$90/$A0/$B0/$C0/$D0 channel indices).
- Writes both period bytes ($4002/$4003 for pulse 1) every frame,
  even when the period has not changed. This causes the characteristic
  high-byte restart click on sustained notes.
- Volume is written every frame during envelope processing (1/frame
  decrement model).
- SFX channels ($C0/$D0) override music channels ($80/$90) by writing
  to the same APU registers when active.
- Triangle channel uses $4008 linear counter for articulation rather
  than $400B length counter.

### What It Proves

- The driver's update strategy and channel priority scheme.
- Whether the driver uses hardware features (sweep, length counter,
  linear counter) and how.
- The envelope update rate (per-frame vs per-N-frames).
- Percussion implementation (inline noise triggers vs dedicated
  DMC channel vs no percussion).

### Practical Application

Even without identifying the driver by name, an APU trace of a single
track provides enough information to:

1. Count active channels and their types.
2. Determine the frame rate of the driver's update loop (usually 60 Hz
   on NTSC but some drivers tick at half-rate or variable rates).
3. Extract the actual period values being written, which can be matched
   against the period table to recover note sequences.
4. Observe volume envelopes in real time, revealing the envelope model
   without needing to decode the data format.

This is the most powerful identification method but also the most
labor-intensive, requiring an emulator session rather than automated
ROM scanning.

### Failure Mode

Interpreting SFX writes as music driver behavior. Sound effects use
the same APU registers and can produce misleading patterns if captured
during gameplay rather than a clean music-only section (title screen or
sound test).

---

## 6. Known Disassembly Cross-Reference

**Reliability: HIGH** -- deterministic when available, but availability
is sparse.

### What It Is

The NES reverse engineering community has produced annotated
disassemblies for many commercially released games. These disassemblies
label subroutines, data tables, and memory locations with descriptive
names, making the sound driver's structure immediately readable.

### Where to Find Them

| Source | URL / Location | Coverage |
|--------|---------------|----------|
| GitHub search | `[game name] NES disassembly` | Growing, best for popular titles |
| romhacking.net | Documents section | Older analyses, format docs |
| nesdev.org wiki | Various articles | Driver architecture descriptions |
| Data Crystal | datacrystal.romhacking.net | RAM maps, ROM maps |
| Project references/ | `references/nes-contra-us/` | Contra full disassembly |

### What a Disassembly Provides

A complete annotated disassembly is the gold standard. It tells you:

- Exact pointer table address and format.
- Every command byte and its parameter count.
- The envelope model implementation (parametric vs lookup table).
- Bank switching behavior for bank-switched mappers.
- Channel memory layout and zero-page usage.
- The NMI handler structure and driver update loop.

For Contra, the vermiceli/nes-contra-us disassembly provided:
- `sound_table_00` at CPU $88E8 (ROM $48F8) with the pointer table.
- `pulse_volume_ptr_tbl` with 54 envelope lookup tables.
- Complete command dispatch logic showing DX reads 3 extra bytes on
  pulse and 1 on triangle.
- EC pitch adjustment command semantics.

### Partial Information Sources

Even without a full disassembly, partial information helps:

- **Sliver X's "Castlevania Music Format v1.0"** (romhacking.net
  document #150) provided the CV1 command format and pointer table.
- **Data Crystal RAM maps** provide zero-page variable assignments
  that reveal the driver's channel memory layout.
- **NSFe metadata** can identify the sound driver and provide init/play
  addresses for NSF-ripped versions.

### What It Proves

Everything. A disassembly is a complete specification. There is no
ambiguity, no false positive risk, and no guessing. The only risk is
misreading the assembly code.

### Failure Mode

Trusting labels from an inaccurate or incomplete disassembly. Community
disassemblies vary in quality. Cross-reference labeled behavior against
actual ROM execution (trace or debugger) before building a parser.

---

## Heuristic Reliability Ranking

| # | Heuristic | Reliability | Alone Sufficient? | Time Cost |
|---|-----------|-------------|-------------------|-----------|
| 6 | Known disassembly | HIGH | YES | Minutes (if it exists) |
| 5 | APU trace fingerprint | HIGH | YES | 30-60 min per trace session |
| 2 | Opcode pattern scan | HIGH | YES (with co-occurrence) | Seconds (automated) |
| 3 | Pointer table structure | HIGH | NO (confirms, doesn't identify) | Minutes to hours |
| 1 | Period table signature | MEDIUM | NO (necessary, not sufficient) | Seconds (automated) |
| 4 | Mapper correlation | LOW | NO (context only) | Seconds (automated) |

The recommended order is: check for disassembly first (free if it
exists), then run automated scans (period table + opcode patterns),
then APU trace if ambiguous.

---

## Decision Tree: First-Contact ROM Analysis

```
START: Unknown NES ROM
  |
  v
[1] Read iNES header
  |-- Not a valid NES ROM? --> STOP (not an iNES file)
  |-- Record mapper, PRG/CHR size
  |
  v
[2] Check extraction/manifests/ for existing JSON
  |-- Found? --> READ IT. Follow manifest instructions.
  |-- Not found? --> Continue.
  |
  v
[3] Search for annotated disassembly
  |-- GitHub: "[game] NES disassembly"
  |-- romhacking.net documents section
  |-- references/ directory in this project
  |-- Found? --> Read sound engine code.
  |             Record pointer table, DX byte count,
  |             envelope model. Create manifest with
  |             status "verified". Go to step [7].
  |-- Not found? --> Continue with automated scanning.
  |
  v
[4] Scan for period table ($AE $06 or $06 $AE)
  |-- Not found? --> NOT a standard-tuning driver.
  |                  May use custom tuning or non-melodic
  |                  audio. Requires manual investigation.
  |-- Found? --> Record ROM offset and bank number.
  |              WARNING: this does NOT confirm driver
  |              identity. Continue.
  |
  v
[5] Scan for Maezawa command signatures
  |   (E8+DX, FE+count+addr, FD+addr patterns)
  |
  |-- Score >= 0.6 (LIKELY MAEZAWA)
  |     --> Strong candidate. Record as hypothesis.
  |         Determine DX byte count and pointer table.
  |         Go to step [7].
  |
  |-- Score 0.3-0.6 (POSSIBLE MAEZAWA)
  |     --> Ambiguous. Need APU trace to confirm.
  |         Go to step [6].
  |
  |-- Score < 0.3 (NOT MAEZAWA)
  |     --> Different driver family. Check if period
  |         table is present (could be Capcom, Sunsoft,
  |         Nintendo, or other).
  |         Build new signature scanner for the
  |         candidate family, or go to step [6].
  |
  v
[6] Capture APU trace in Mesen
  |   Play a known track (stage 1 music recommended).
  |   Record 200+ frames.
  |   Analyze write patterns per section 5.
  |
  |-- Matches Maezawa fingerprint? --> Confirmed.
  |     Create manifest. Go to step [7].
  |-- Does not match? --> Unknown driver.
  |     Create manifest with driver_family: "unknown".
  |     Full RE effort required.
  |
  v
[7] Parse ONE track and listen
  |   Use the appropriate parser (CV1 or Contra variant).
  |   Export to MIDI.
  |   Compare to game audio in emulator.
  |
  |-- Sounds correct? --> Update manifest status to
  |     "verified". Proceed to batch extraction.
  |-- Sounds wrong? --> Debug using trace_compare.py.
  |     Check: DX byte count, octave mapping, tempo,
  |     envelope model. Fix one issue at a time.
  |
  v
DONE: Game is ready for pipeline processing.
```

---

## Implications for Our Pipeline

### How rom_identify.py Should Evolve

The current `rom_identify.py` implements steps [1], [4], and [5] of
the decision tree. It should grow in these directions:

**Near-term additions:**

1. **Big-endian period table scan.** Some drivers store the period table
   in big-endian byte order. Add a second signature search for `$06 $AE`.

2. **PAL period table.** PAL NES uses a different CPU clock (1.662607
   MHz), producing different period values. Add a PAL signature for
   games from European regions.

3. **Bank-aware hit localization.** When a period table is found, report
   not just the ROM offset but also whether the hit is in the fixed
   bank (last 16 KB for mapper 2) or a switchable bank. This affects
   whether the sound engine is always accessible or only when the
   correct bank is loaded.

4. **Command pattern localization.** Currently the Maezawa scanner
   checks the entire ROM. It should focus on the bank where the period
   table was found, reducing false positives from machine code in other
   banks.

5. **Manifest auto-creation.** When a scan produces a LIKELY result,
   auto-generate a skeleton manifest JSON with `driver_family_status:
   "hypothesis"` and all detected addresses pre-filled.

**Medium-term additions:**

6. **Non-Maezawa signature scanners.** Add pattern scanners for Capcom,
   Sunsoft, and Nintendo first-party drivers. Each scanner needs its
   own set of characteristic byte patterns identified from decoded
   games in that family.

7. **Pointer table candidate detection.** After finding the period
   table, scan nearby addresses for clusters of 16-bit values in the
   $8000-$FFFF range with consistent spacing. Rank candidates by
   density and address validity.

8. **Multi-ROM batch comparison.** When scanning a directory, compare
   period table offsets and command signature profiles across ROMs to
   cluster games by likely driver family.

**Long-term:**

9. **NSF header parsing.** NSF files (NES Sound Format) contain
   metadata including init and play addresses that can be matched
   against known driver entry points.

10. **Automated trace integration.** Accept a Mesen trace CSV alongside
    the ROM and produce a combined report: ROM-level signatures plus
    runtime behavior analysis.

### Pipeline Integration Points

| Pipeline Stage | Identification Dependency |
|---------------|-------------------------|
| Parser selection | Driver family determines which parser to use |
| Address resolution | Mapper type determines CPU-to-ROM conversion |
| Frame IR envelope | Driver family determines parametric vs lookup |
| MIDI export | DX byte count affects instrument metadata |
| Trace validation | Period table location needed for frequency matching |

Every stage downstream of identification depends on getting it right.
A misidentified driver produces garbage at every subsequent step.

---

## Failure Risks if Misunderstood

### Risk 1: Period Table = Driver Identity (FALSE)

**What happens:** You find the period table in a ROM, conclude it uses
the Maezawa driver, and run the CV1 or Contra parser against it.

**What goes wrong:** The parser reads from the wrong pointer table
address, gets garbage data, and either crashes (division by zero from
tempo=0) or produces MIDI files that sound nothing like the game.

**Why it happens:** The period table is universal NES tuning, not a
driver signature. This exact mistake was made during the CV2
investigation and cost 4 prompts.

**Prevention:** Always verify with opcode pattern scanning (method 2)
after finding the period table (method 1). Never skip step [5] in
the decision tree.

### Risk 2: Same Driver = Same ROM Layout (FALSE)

**What happens:** You confirm a ROM uses the Maezawa driver and assume
the pointer table is at the same offset as CV1 ($0825) or Contra
($48F8).

**What goes wrong:** The pointer table is at a different address. The
parser reads from the wrong location, producing the same division-by-
zero failures seen when running the CV1 parser against Super C, Contra,
and CV3.

**Why it happens:** The driver engine code may be identical across
games, but the data layout (pointer table offset, track count, entry
format) is per-game.

**Prevention:** Never hardcode addresses. Every new game needs its
pointer table located independently, preferably from a disassembly.

### Risk 3: Same Opcode = Same Semantics (FALSE)

**What happens:** You confirm a ROM uses the Maezawa driver and assume
all command bytes work the same as CV1.

**What goes wrong:** DX reads a different number of parameter bytes
(CV1: 2 for pulse, Contra: 3 for pulse). The parser gets out of sync
with the data stream. Every note after the first DX command is
misinterpreted.

**Why it happens:** The Maezawa driver evolved across games. The
command dispatch loop is shared, but individual command handlers have
per-game variations in parameter count and semantics.

**Prevention:** Check spec.md's per-game differences table. Determine
DX byte count from the disassembly or empirically before parsing.

### Risk 4: High Confidence Score = Correct (MOSTLY TRUE, BUT...)

**What happens:** `rom_identify.py` reports "LIKELY MAEZAWA" with
confidence 0.8.

**What could go wrong:** A non-Maezawa ROM with heavy use of FE/FD
bytes in non-music data (level scripts, AI routines) could produce a
false positive. The byte $FE followed by a small number followed by
a 16-bit address is a plausible pattern in game logic code.

**Prevention:** Cross-reference hit locations against the period table
bank. If FE/FD patterns cluster in the same bank as the period table,
confidence increases. If they are scattered across all banks, they may
be coincidental.

### Risk 5: No Disassembly = Guess and Hope (WASTEFUL)

**What happens:** No annotated disassembly exists. You skip straight
to parsing, guessing at pointer table addresses and DX byte counts.

**What goes wrong:** Multiple rounds of trial-and-error, each costing
a prompt or session. The Contra investigation would have been much
slower without the vermiceli disassembly.

**Prevention:** Always search for a disassembly before writing code.
Check GitHub, romhacking.net, and the nesdev wiki. Ten minutes of
searching saves hours of guessing.

### Risk 6: Ignoring Mapper Implications (SILENT CORRUPTION)

**What happens:** You find valid music data in a bank-switched ROM but
use linear address resolution (mapper 0 formula) to convert CPU
addresses to ROM offsets.

**What goes wrong:** Pointers resolve to wrong ROM locations. The
parser reads data from the wrong bank. Output may partially work
(if the target address happens to contain similar data in the wrong
bank) or fail silently with subtly incorrect notes.

**Prevention:** Always check the mapper first. For mapper 2+, determine
which bank contains the sound data (from period table location) and
use bank-aware address resolution.

---

## Appendix A: Quick Reference Table

| Question | Method | Time |
|----------|--------|------|
| Does this ROM have pitched music? | Period table scan | Seconds |
| Is this a Maezawa-family driver? | Opcode pattern scan | Seconds |
| Which bank has the sound data? | Period table offset / mapper | Seconds |
| Where is the pointer table? | Disassembly or debugger | Minutes-hours |
| What is the DX byte count? | Disassembly or trial parse | Minutes |
| What envelope model does it use? | Disassembly or trace | Minutes-hours |
| Is the game fully extractable? | Parse one track, listen | 30 min |

## Appendix B: Known Driver Family Signatures

### Konami Maezawa (~1986-1990)

- Period table: standard NTSC, 12 entries, 16-bit LE
- Command bytes: note in 0x00-0xBF (pitch high nibble, duration low),
  rest 0xC0-0xCF, instrument 0xD0-0xDF, octave 0xE0-0xE4,
  special 0xE8-0xEA, control 0xFD-0xFF
- Distinctive: E8+DX co-occurrence, FE repeat with small count,
  FD subroutine calls
- Games: CV1, Contra, Super C, Gradius (suspected), Goonies II
  (suspected), Life Force (suspected), Jackal (suspected)

### Konami Fujio Variant (~1987+)

- Period table: same NTSC values (this is what makes it confusing)
- Command format: UNKNOWN -- not decoded by this project
- Games: Castlevania II (confirmed)
- Notes: requires full RE effort. No scanner exists yet.

### Konami VRC6/VRC7 (expansion audio)

- Expansion registers at $9000-$9002 (VRC6) or $9010/$9030 (VRC7)
- Base driver may be Maezawa-family with extension
- Games: Akumajou Densetsu (JP CV3, VRC6), Lagrange Point (VRC7)
- Notes: requires mapper-specific APU emulation

## Appendix C: Files Referenced

| File | Purpose |
|------|---------|
| `scripts/rom_identify.py` | Automated ROM identification |
| `extraction/manifests/*.json` | Per-game structured truth |
| `extraction/drivers/konami/spec.md` | Maezawa command specification |
| `docs/DRIVER_FAMILIES.md` | Catalog of known NES driver families |
| `docs/DRIVER_MODEL.md` | Maezawa driver architecture reference |
| `docs/GAME_MATRIX.md` | Status matrix for candidate games |
| `docs/MOVINGONTOCV2.md` | CV2 false-positive investigation |
| `docs/MISTAKEBAKED.md` | Mistake prevention index |
| `references/nes-contra-us/` | Contra annotated disassembly |
