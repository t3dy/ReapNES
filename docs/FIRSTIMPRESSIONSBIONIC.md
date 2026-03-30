# First Impressions: Bionic Commando vs Konami Models

## The Basics

| Property | Bionic Commando | CV1 | Contra | Gradius |
|----------|----------------|-----|--------|---------|
| Publisher | **Capcom** | Konami | Konami | Konami |
| Year | 1988 | 1986 | 1988 | 1986 |
| Mapper | 1 (MMC1) | 2 (UNROM) | 2 (UNROM) | 3 (CNROM) |
| PRG | 256KB (16 banks) | 128KB (8) | 128KB (8) | 32KB (2) |
| CHR | 0 (CHR-RAM) | — | — | 32KB |
| Period table | NOT FOUND | 12-entry Maezawa | 12-entry Contra | NONE |

This is our first Capcom game. Everything we know about Konami
drivers is potentially irrelevant.

## What the Trace Reveals

### Vibrato is heavy and universal

Pulse 1 most common periods cluster around target notes with ±4
spread. C4 appears as 423, 427, 431. C#4 as 399, 403, 407. This
is the SAME vibrato pattern we saw in Super C — but Capcom and
Konami arrived at it independently.

**Implication:** vibrato-tolerant pitch matching is not a Konami
quirk. It's a common NES driver technique. Our trace comparison
tools need vibrato tolerance for ALL games, not just Konami.

### Volume envelope is simple: 10-9-10-9 alternation

Pulse 1 volume alternates between 10 and 9 every ~2 frames. This
is NOT the Maezawa parametric decay (fade_start/fade_step) or
the Contra lookup table model. It's a **tremolo** — rapid volume
oscillation for a shimmering effect.

This is a third envelope type not in our taxonomy:
- Maezawa: parametric decay (vol decreases over time)
- Contra: lookup table (vol follows a preset curve)
- **Capcom: tremolo** (vol oscillates between two values)

### Note timing uses multiples of 6

Pulse 2 durations: 6, 12, 24, 48, 96 frames. These are all
multiples of 6. At 60fps, 6 frames = 100ms = a sixteenth note
at 150 BPM. This is a cleaner timing grid than Konami games,
which use variable duration nibbles (1-15 frames × tempo).

**Implication:** Capcom likely uses a tick-based timing system
rather than Konami's frame-count-in-nibble system. The duration
encoding is probably a note LENGTH VALUE (quarter, eighth, etc.)
rather than raw frame count.

### Pitch range is reasonable

Pulse 1: MIDI 41-70 (F2 to A#4). Pulse 2: MIDI 49-55 (C#3 to G3).
Triangle would be lower. This is a normal NES range — unlike the
Gradius nesmdb data that was 2 octaves too high.

Exception: MIDI 153 appears on pulse 1 (period = very small value).
This is definitely SFX (weapon shots or grapple sounds), not music.
The game interleaves SFX on the pulse channels during gameplay.

## Comparing Driver Architecture

### What's SIMILAR to Konami

1. **E0-EF byte range is heavily used.** Bionic Commando has
   high E0-EF counts across banks 4-10 (600-900 per bank).
   This could mean octave commands, or it could mean something
   completely different in a Capcom driver.

2. **D0-DF range is used.** Could be instrument/timbre commands
   like Konami's DX, or something else entirely.

3. **FE appears frequently** in banks 4-9 (200-400 per bank).
   Could be repeat/loop markers like Konami, or different.

4. **Music data spans multiple banks.** Banks 4-9 all have high
   music density scores. Konami typically concentrates music in
   1-2 banks. Capcom spreads it more.

### What's DIFFERENT from Konami

1. **No standard period table.** No 12-entry chromatic sequence
   found anywhere in the ROM. Like Gradius, the driver may
   compute periods at runtime or use a non-standard table format.

2. **MMC1 mapper.** Konami uses UNROM (mapper 2) for most games.
   MMC1 has more complex banking (configurable 16KB/32KB modes,
   switchable PRG and CHR). The address resolver will need a new
   mode.

3. **CHR-RAM instead of CHR-ROM.** Graphics are loaded into RAM
   at runtime. This doesn't affect music directly but indicates
   a different ROM utilization strategy.

4. **Music in MANY banks.** 10+ banks show music-like signatures.
   The Konami model assumes one "sound bank" with all music data.
   Capcom may distribute tracks across banks, loading them on
   demand.

5. **Tremolo envelope.** The 10-9-10-9 volume pattern is unlike
   any Konami envelope model. The Capcom driver handles dynamics
   differently.

6. **Tick-based timing (6-frame multiples).** Konami uses raw
   frame counts encoded in the low nibble (1-15). Capcom appears
   to use a tempo-driven tick system with note values.

## What This Means for the Pipeline

### The trace pipeline works perfectly

Our trace→WAV renderer produced a 64.8s render with zero
modifications for Capcom. The renderer is truly game-agnostic —
it just replays APU register writes. This validates the core
architecture decision: **trace rendering is ENGINE work that
never changes.**

### ROM parsing is a new problem

Our entire parser infrastructure (parser.py, contra_parser.py,
frame_ir.py) is built for Maezawa-family note encoding:
pitch×16 + duration in high/low nibbles, E0-E4 octave commands.

Capcom uses a different encoding. To parse Bionic Commando from
ROM, we would need:
1. A Capcom-specific period table finder (or runtime computation model)
2. A Capcom-specific note decoder
3. A Capcom-specific pointer table format
4. New envelope processing (tremolo model)

This is equivalent to the Gradius situation: the trace gives us
ground truth audio, but ROM parsing requires reverse-engineering
an entirely new driver.

### The manifest model still applies

Even without a parser, we can create a valid manifest:

```json
{
  "game": "bionic_commando",
  "mapper": 1,
  "driver_family": "capcom",
  "driver_family_confidence": "high",
  "driver_family_evidence": "publisher",
  "period_table": {"status": "not_found"},
  "pointer_table": {"status": "unknown"},
  "vibrato_detected": true,
  "envelope_model": "tremolo",
  "status": "capture_done"
}
```

The manifest tracks what we KNOW without requiring a parser to
exist. The trace renders are valid outputs regardless.

## Priority Assessment

**LOW for ROM parsing.** Capcom is a completely new driver family.
No disassembly, no reference implementation, no shared code with
Konami. Reverse-engineering the Capcom driver is weeks of work for
one publisher's games.

**HIGH for trace-based extraction.** The trace pipeline already
produces accurate audio. If the user captures each track separately
(via the game's sound test or level progression), we can build a
complete soundtrack from traces alone — no ROM parsing needed.

**MEDIUM for nesmdb reference.** Check if Bionic Commando is in
the nesmdb database. If so, render reference tracks for labeling.

## The Emerging Pattern

Every new publisher we encounter follows the same arc:

1. **Trace works immediately** (universal, game-agnostic)
2. **ROM scan finds no Maezawa table** (different driver family)
3. **Command byte ranges overlap but semantics differ** (E0-EF
   is used by everyone, but means different things)
4. **The driver is publisher-specific** (Konami ≠ Capcom ≠ whoever
   made Gradius's engine)

The pipeline we've built has two tiers:
- **Tier 1 (trace-based):** works on ANY NES game, produces
  accurate audio from captures. No parsing needed.
- **Tier 2 (ROM-based):** works only on games with a known,
  reverse-engineered driver. Currently: Maezawa family only.

Bionic Commando is a Tier 1 game. We can extract its soundtrack
through trace captures. Moving it to Tier 2 would require
building a Capcom parser from scratch.

## What Bionic Commando Teaches Us About the Konami Models

1. **Vibrato is not Konami-specific.** It's a universal NES
   technique. Build vibrato tolerance into all tools.

2. **Period tables are not universal.** Capcom doesn't use one.
   The "scan for period table" step only works for some drivers.

3. **The E0-EF byte range is overloaded.** Every driver uses
   these bytes but for different purposes. Don't assume E0-E4
   means "octave" in a non-Konami game.

4. **Tick-based vs frame-based timing.** Konami counts frames.
   Capcom counts ticks (multiples of 6 frames). The timing model
   is a driver-level decision, not a hardware constraint.

5. **The trace is the great equalizer.** Regardless of publisher,
   driver, or encoding, the APU trace captures exactly what the
   hardware produces. This is why the trace-first workflow
   matters — it works before you understand the driver.
