# Konami Maezawa-Family NES Game Matrix

Status matrix for every known or suspected Konami Maezawa-family NES
game. This document tracks which games have been decoded, which are
blocked, and which remain untested. It serves as both a progress
tracker and a guide for anyone wanting to contribute new game support.

Machine-readable status values: `COMPLETE`, `IN_PROGRESS`, `BLOCKED`,
`UNTESTED`, `UNLIKELY`.

Last updated: 2026-03-28

---

## Master Status Table

| Game | Year | Mapper | Driver Confirmed | Tracks Decoded | Total Tracks | Pulse Fidelity | Tri Fidelity | Status | Blockers |
|------|------|--------|------------------|----------------|--------------|----------------|--------------|--------|----------|
| Castlevania | 1986 | 2 (UxROM) | YES (verified) | 15 | 15 | 99.5% (0 pitch mismatch) | 99.5% (linear counter approx) | COMPLETE | None |
| Gradius | 1986 | 0 (NROM) | Suspected | 0 | ~10 | -- | -- | UNTESTED | No disassembly found |
| Castlevania II | 1987 | 1 (MMC1) | NO (Fujio variant) | 0 | ~15 | -- | -- | BLOCKED | Different driver entirely |
| Goonies II | 1987 | 2 (UxROM) | Suspected | 0 | ~12 | -- | -- | UNTESTED | No disassembly found |
| Contra | 1988 | 2 (UNROM) | YES (verified) | 11 | 11 | 91% pitch / 82% volume | 70% pitch / 94% volume | IN_PROGRESS | Triangle pitch drift, vibrato unimplemented |
| Jackal | 1988 | 2 (UxROM) | Suspected | 0 | ~8 | -- | -- | UNTESTED | No disassembly found |
| Life Force | 1988 | 2 (UxROM) | Suspected | 0 | ~10 | -- | -- | UNTESTED | No disassembly found |
| Castlevania III | 1989 | 5 (MMC5) | Suspected | 0 | ~20 | -- | -- | UNTESTED | MMC5 expansion audio, bank switching |
| TMNT | 1989 | 4 (MMC3) | Suspected | 0 | ~15 | -- | -- | UNTESTED | MMC3 bank switching |
| Adventures of Bayou Billy | 1989 | 4 (MMC3) | Unknown | 0 | ~8 | -- | -- | UNTESTED | No information |
| Super C | 1990 | 2 (UNROM) | Likely (9/15 parsed with CV1) | 9 | ~15 | Unknown | Unknown | UNTESTED | Needs own config, 6 tracks fail |
| Blades of Steel | 1990 | 1 (MMC1) | Unknown | 0 | ~6 | -- | -- | UNTESTED | No information |
| TMNT II: The Arcade Game | 1990 | 4 (MMC3) | Unknown | 0 | ~12 | -- | -- | UNTESTED | MMC3 bank switching |
| Tiny Toon Adventures | 1991 | 4 (MMC3) | Unknown | 0 | ~10 | -- | -- | UNTESTED | Late title, may use different driver |

Notes on the table:

- "Total Tracks" for untested games is an estimate based on the number
  of distinct songs audible during gameplay.
- "Pulse Fidelity" and "Tri Fidelity" are measured against Mesen APU
  traces when available. A dash means no trace data exists.
- Mapper numbers determine address resolution difficulty. See the
  Difficulty Ratings section below.

---

## Per-Game Detail

### Castlevania (1986) -- COMPLETE

Status: `COMPLETE`. 15/15 tracks extracted, validated, and rendered.

Composer: Kinuyo Yamashita. Mapper 2 (UxROM) with linear address
resolution. Pointer table at ROM $0825, 9-byte entries. Two-phase
parametric envelope model (fade_start + fade_step). Triangle uses
$4008 linear counter with approximate formula `(reload+3)//4` frames.

Validation: zero pulse pitch mismatches across full 1792-frame Vampire
Killer trace. 9 pulse sounding mismatches (fade_step edge cases), 8
triangle sounding mismatches (linear counter off by 1 frame). Overall
envelope accuracy 99.5%.

Outputs: MIDI, WAV, REAPER projects for all 15 tracks, full soundtrack
MP4 with YouTube description.

Key lessons learned during CV1 that apply to all future games:
- Dump trace data before modeling envelopes. We guessed three wrong
  hypotheses before looking at actual frame data.
- Automated trace comparison can show zero mismatches while the octave
  is wrong by 12 semitones. Human listening is mandatory.
- Triangle is hardware-1-octave-lower than pulse (32-step vs 16-step
  waveform). Any pitch mapping change must account for this.

### Contra (1988) -- IN_PROGRESS

Status: `IN_PROGRESS`. 11/11 tracks parsed. Currently at version v5.

Composer: Hidenori Maezawa. Mapper 2 (UNROM) with bank-switched
address resolution (all sound data in bank 1). Pointer table at ROM
$48F8 (CPU $88E8), flat 3-byte entries. Volume envelopes use a 54-entry
lookup table (`pulse_volume_ptr_tbl`) instead of CV1's parametric model.
Percussion is a separate DMC channel rather than inline E9/EA triggers.

Validation: pulse1 pitch 91%, pulse1 volume 82%, triangle pitch 70%,
triangle volume 94% against Mesen trace (2976 frames, Jungle theme).
Ear-validated against game audio.

Key differences from CV1:
- DX reads 3 extra bytes on pulse (config + vol_env + decrescendo_mul)
  and 1 on triangle, vs 2 and 0 for CV1.
- EC pitch adjustment command used (+1 semitone in Jungle and Base).
- Auto-decrescendo mode (bit7 of vol_env byte) not fully modeled.
- EB vibrato command parameters skipped.

Remaining work: triangle pitch drift investigation, vibrato
implementation, auto-decrescendo refinement.

### Castlevania II: Simon's Quest (1987) -- BLOCKED

Status: `BLOCKED`. This game does NOT use the Maezawa driver.

Composer: Kenichi Matsubara (different team from CV1). Despite sharing
the same NES period table values (which are universal NTSC tuning, not
driver-specific), CV2's ROM contains none of the Maezawa command
signatures. Only 10 E8 bytes were found, all in machine code regions
where E8 is the 6502 INX instruction. No pointer table matching the
9-byte or 6-byte Maezawa format exists.

The period table match was a false positive that cost 4 prompts to
investigate. This is why spec.md now carries the warning: same period
table does NOT prove same driver.

Unblocking this game requires a full reverse engineering effort on a
different sound engine (the "Fujio variant" per spec.md). No annotated
disassembly is known to exist for the CV2 sound driver.

### Castlevania III: Dracula's Curse (1989) -- UNTESTED

Status: `UNTESTED`. Potentially the most interesting target in the matrix.

Mapper 5 (MMC5) with expansion audio -- two additional pulse channels
beyond the standard APU. This means CV3 has 5 melodic voices instead
of 3, which is why its soundtrack sounds richer than CV1 or Contra.
The expansion audio channels are memory-mapped at $5000-$5015.

The base driver may be Maezawa-family (Konami used consistent sound
engines across titles in this period), but the MMC5 expansion requires
additional handling that no existing parser supports. Bank switching
on mapper 5 is also more complex than mapper 2.

No annotated disassembly is known. The Japanese Famicom version
(Akumajou Densetsu) uses the VRC6 mapper with even more expansion
audio (sawtooth + 2 pulse), which is a separate target entirely.

Difficulty: HARD. Worth investigating because the musical payoff is
high.

### Super C (1990) -- UNTESTED

Status: `UNTESTED`. Partially worked with the CV1 parser: 9 out of 15
tracks produced output before the remaining 6 hit division-by-zero
errors from misaligned pointer reads.

The 9 successful tracks suggest the command set is compatible (same
note/octave/repeat format). The failures are caused by the CV1 parser
reading from CV1's pointer table address ($0825) instead of Super C's
actual pointer table. The game likely uses a different pointer table
offset and possibly different DX byte counts or envelope parameters.

Super C is mapper 2 (UNROM) like Contra. Given that it is a direct
sequel to Contra, the sound engine is very likely the same Contra
variant with lookup-table envelopes and separate DMC percussion.

Difficulty: EASY to MEDIUM. The Contra parser (`contra_parser.py`)
is probably the right starting point. Needs its own manifest with
correct pointer table address and track count.

### TMNT (1989) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 4 (MMC3) with 8KB PRG bank switching. Konami's TMNT titles
were major releases with substantial soundtracks. The composer is
not definitively attributed in available references.

MMC3 bank switching is more granular than UNROM (8KB banks vs 16KB),
which complicates address resolution. The sound engine is likely
Maezawa-family given Konami's consistency, but this is unverified.

Difficulty: MEDIUM. Bank switching adds complexity but is well
documented.

### Gradius (1986) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 0 (NROM), which is the simplest possible configuration --
linear address mapping with no bank switching. This makes it
potentially the easiest untested game to crack. The soundtrack
is well-regarded and relatively complex for a 1986 title.

Being from the same year as Castlevania, it may use an early form
of the Maezawa driver or a predecessor. Running `rom_identify.py`
would immediately reveal whether the period table and command
signatures are present.

Difficulty: EASY if Maezawa-family. Mapper 0 means no address
resolution headaches.

### Goonies II (1987) -- UNTESTED

Status: `UNTESTED`. Listed in spec.md as a known Maezawa-family game.

Mapper 2 (UxROM), same as CV1 and Contra. If the driver family is
confirmed, this should be straightforward given existing tooling.

Difficulty: EASY to MEDIUM.

### Life Force (1988) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Life Force (Salamander) is a Gradius spinoff. Mapper 2 (UxROM).
Given Konami's reuse of sound engines, likely Maezawa-family, but
unverified.

Difficulty: MEDIUM. No disassembly known.

### Jackal (1988) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 2 (UxROM). Another mid-period Konami title that likely shares
the sound engine. No disassembly known.

Difficulty: MEDIUM. No disassembly known.

### Adventures of Bayou Billy (1989) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 4 (MMC3). A later Konami title with mixed gameplay styles.
Whether it uses the Maezawa driver is unknown.

Difficulty: MEDIUM to UNKNOWN.

### TMNT II: The Arcade Game (1990) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 4 (MMC3). A 1990 port of the arcade game. Late enough in
Konami's NES lifecycle that the sound engine may have evolved or
been replaced.

Difficulty: MEDIUM to UNKNOWN.

### Blades of Steel (1990) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 1 (MMC1). A sports title, which may have a smaller soundtrack
than action games. Whether it uses the Maezawa driver is unknown.
Mapper 1 uses a different bank switching scheme from mapper 2/4.

Difficulty: MEDIUM to UNKNOWN.

### Tiny Toon Adventures (1991) -- UNTESTED

Status: `UNTESTED`. No investigation has been done.

Mapper 4 (MMC3). A 1991 title near the end of the NES lifecycle.
At this point Konami may have moved to newer sound engines. The
probability of this being Maezawa-family is lower than earlier titles.

Difficulty: UNKNOWN. Late title, driver family uncertain.

---

## The Unmapped Territory

For every game that has been decoded in this project, there are more
than ten that have not been touched. Konami released over 40 NES games
in the US market between 1986 and 1992. The Maezawa-family driver was
active during roughly 1986-1990, which covers at least 20-25 titles.

The matrix above lists 14 games. Additional Konami NES titles that
may use related sound engines include:

- Stinger (1987)
- The Lone Ranger (1991)
- Bucky O'Hare (1992)
- Zen: Intergalactic Ninja (1993)
- Track & Field II (1988)
- Double Dribble (1987)
- Teenage Mutant Ninja Turtles III (1991)
- Rollergames (1990)
- Parodius (1990, Japan only)

ROM hackers can contribute by running `rom_identify.py` on any Konami
NES ROM and reporting the results. The script checks for:

1. **Mapper type** -- read from the iNES header
2. **Period table** -- scans for the $AE,$06 signature (period 1710 LE)
3. **Driver command signatures** -- scans for E8+DX and FE+count+addr
   patterns

A positive hit on all three confirms the Maezawa driver family.
A period table hit alone is NOT confirmation (the CV2 false positive
proved this). Command signature hits are required.

To run:
```bash
PYTHONPATH=. python scripts/rom_identify.py path/to/rom.nes
```

Results should be filed as a manifest JSON in `extraction/manifests/`
with `driver_family_status: "hypothesis"` until a track is successfully
parsed and ear-validated against game audio.

---

## Difficulty Ratings for New Games

### EASY

Requirements: mapper 0 (NROM) or mapper 2 (UxROM) with linear or
simple bank-switched addressing. An annotated disassembly exists on
GitHub or romhacking.net. The Maezawa command signatures are confirmed.

What this means in practice: you can find the pointer table address
from the disassembly, plug it into an existing parser (CV1 or Contra
variant), parse one track, and compare to game audio within a single
session.

Games in this category:
- **Gradius** -- mapper 0, simplest possible addressing
- **Goonies II** -- mapper 2, listed as known Maezawa-family
- **Super C** -- mapper 2, already partially works with existing parser

### MEDIUM

Requirements: bank-switched mapper (2 or 4) with no annotated
disassembly available. The driver family is suspected but not confirmed.

What this means in practice: you must find the pointer table by
scanning the ROM for signature patterns or by using a Mesen debugger
to set breakpoints on APU register writes. The DX byte count,
percussion format, and envelope model must be determined empirically.
Expect 2-3 sessions of investigation before the first track plays
correctly.

Games in this category:
- **Life Force** -- mapper 2, no disassembly
- **Jackal** -- mapper 2, no disassembly
- **TMNT** -- mapper 4 (MMC3), adds bank-switching complexity
- **Blades of Steel** -- mapper 1 (MMC1), different bank scheme

### HARD

Requirements: expansion audio hardware (MMC5, VRC6, VRC7). The mapper
adds extra sound channels that the standard NES APU does not have.
These channels have their own register sets, waveform types, and
timing characteristics that must be modeled separately.

What this means in practice: even if the base driver is Maezawa-family,
the expansion channels require new code paths in frame_ir.py,
midi_export.py, and render_wav.py. The REAPER project generator and
JSFX synth also need expansion channel support. This is a significant
engineering effort beyond just finding pointer tables.

Games in this category:
- **Castlevania III (US)** -- mapper 5 (MMC5), 2 extra pulse channels
- **Akumajou Densetsu (JP CV3)** -- VRC6, sawtooth + 2 extra pulse

### UNKNOWN

Requirements: the game's sound driver has not been identified. It may
not be Maezawa-family at all.

What this means in practice: start with `rom_identify.py`. If no
command signatures are found, the game requires its own reverse
engineering effort from scratch, similar to what CV2 would need.

Games in this category:
- **Castlevania II** -- confirmed NOT Maezawa (Fujio variant)
- **Adventures of Bayou Billy** -- no information
- **TMNT II** -- late title, uncertain
- **Tiny Toon Adventures** -- late title, uncertain
- **Blades of Steel** -- sports title, uncertain

---

## How to Add a New Game

Follow the workflow documented in CLAUDE.md:

1. Run `rom_identify.py` on the ROM. Record mapper, period table hit,
   and command signature results.
2. Check `extraction/manifests/` for an existing JSON. If none, create
   one with `status: "UNTESTED"` and `driver_family_status: "hypothesis"`.
3. Search `references/` and GitHub for annotated disassemblies. Read
   the sound engine code if one exists.
4. Determine the pointer table address, DX byte count, percussion
   format, and envelope model. Record each finding in the manifest
   with `status: "verified"` or `"hypothesis"`.
5. Parse one track. Listen against the game. Do not batch-extract
   until the reference track sounds correct.
6. Update this matrix with the results.
