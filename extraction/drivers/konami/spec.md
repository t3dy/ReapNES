# Konami Pre-VRC Sound Driver — Specification

## Status: Research In Progress

## Driver Identity
- **Family name**: konami_pre_vrc
- **Also known as**: Konami SCC-less driver, Konami base driver
- **Active period**: ~1986–1990
- **Target ROM**: Castlevania (U) (V1.0) — UxROM, mapper 2

## Architecture (Provisional)

### Engine Loop
- Music update runs once per NMI (60Hz NTSC).
- A speed/tempo divider counts down frames before advancing the sequence position.
- Each channel has an independent data stream pointer.

### Song Structure (Provisional)
- Song header contains:
  - Speed byte (frames per engine tick)
  - Per-channel data pointers (4 channels: pulse1, pulse2, triangle, noise)
- A song table points to song headers.

### Command Stream Format (Provisional)
- **Note commands**: encode both pitch (period lookup index) and duration.
- **Rest commands**: silence for N ticks.
- **Loop command**: jump back to a position in the stream.
- **End command**: stop channel or trigger song loop.
- **Envelope/duty commands**: set volume envelope or duty cycle mode.

### Known Command Bytes
(To be filled during Phase 3 reverse engineering)

| Byte Range | Meaning | Confidence |
|-----------|---------|------------|
| TBD | Note with duration | provisional |
| TBD | Rest | provisional |
| TBD | Set speed | provisional |
| TBD | Loop marker | provisional |
| TBD | End of stream | provisional |

### Tempo Model
- Speed value = frames per tick.
- Typical values: 4–8 (roughly 120–180 BPM).
- Some songs change speed mid-stream.

### Envelope System (Provisional)
- Short volume envelopes (4–8 entries).
- Duty cycling observed in some channels.
- No pitch envelope or arpeggio macro identified yet.

## Evidence Sources
- Community research (to be cited per finding)
- APU trace analysis of Castlevania
- Static ROM inspection of Castlevania PRG data

## Open Questions
1. Exact format of the song table header?
2. How are per-channel pointers resolved (absolute vs bank-relative)?
3. Which byte values delimit note commands from control commands?
4. Are volume envelopes stored inline or in a shared table?
5. How does the driver handle SFX priority over music channels?

## Confidence
All claims in this file are **provisional** (confidence = 0.0) unless marked otherwise.
