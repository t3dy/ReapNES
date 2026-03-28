# NES Sound Driver Families

## Overview

NES music is not stored in a universal format. Each game (or group of games) uses a **sound driver** — a custom engine that reads proprietary data structures and writes APU registers at runtime. Understanding the driver is a prerequisite for meaningful analysis.

This document catalogs known driver families, their characteristics, and NES Music Lab's support status.

## Identification Strategy

1. **NSF header inspection** — some NSFs identify their driver via init/play addresses.
2. **Code pattern matching** — known driver families have recognizable code signatures (init routines, play loop structure, register write patterns).
3. **APU write fingerprinting** — the order and pattern of register writes can suggest a driver family even without code access.
4. **Community documentation** — NSFe metadata, NESdev wiki, and reverse-engineering communities.

## Known Driver Families

### Konami (Pre-VRC)
- **Games**: Castlevania, Contra, Gradius, etc.
- **Characteristics**: Frame-based engine ticks, simple volume envelopes, duty cycling, compact data format.
- **Data format**: Sequential command bytes with inline parameters.
- **Status**: Planned (Phase 4 candidate)

### Konami VRC6/VRC7
- **Games**: Castlevania III (JP), Lagrange Point
- **Characteristics**: Extended audio via mapper hardware (VRC6 adds 2 pulse + 1 sawtooth; VRC7 adds FM synthesis).
- **Data format**: Similar to base Konami but with extended register set.
- **Status**: Planned (Phase 6)

### Capcom
- **Games**: Mega Man series, DuckTales, Chip 'n Dale
- **Characteristics**: Multi-speed engine ticks, complex volume/pitch envelopes, subroutine-style data.
- **Data format**: Pointer-based with per-channel data streams.
- **Status**: Planned (Phase 4 candidate)

### Nintendo (First-Party)
- **Games**: Super Mario Bros., Zelda, Metroid, Kid Icarus
- **Characteristics**: Varies significantly across titles. SMB uses a simple sequential engine; later titles use more complex systems.
- **Data format**: Title-specific — no single "Nintendo driver."
- **Status**: Planned (individual titles)

### Sunsoft
- **Games**: Batman, Blaster Master, Gremlins 2
- **Characteristics**: Aggressive DPCM usage for bass/percussion, complex duty cycling, tight timing.
- **Data format**: Compact per-channel streams.
- **Status**: Planned (Phase 6)

### FamiTracker / Modern
- **Games**: Homebrew, modern NES releases
- **Characteristics**: FamiTracker's NSF export driver is well-documented. Instruments defined as macro sets.
- **Data format**: FamiTracker module format (well-documented).
- **Status**: Planned (good validation target — format is known)

## Adding a New Driver Family

1. Create `drivers/{family_name}/` directory.
2. Write `NOTES.md` documenting known characteristics, data format hypotheses, and sources.
3. Write `parser.py` implementing driver-specific extraction.
4. Add test fixtures in `tests/fixtures/{family_name}/`.
5. Update this document.
6. Run `/nes-driver-recon` skill for structured investigation.

## References

- NESdev Wiki: https://www.nesdev.org/wiki/
- NSFe specification
- Community reverse-engineering efforts (credited per driver)
