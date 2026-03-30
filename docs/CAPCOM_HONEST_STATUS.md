# Capcom: Honest Status

## What we achieved today
- Bionic Commando: 2 trace renders that sound correct (Stage 1 + Map)
- Bionic Commando: SFX separation, per-channel stems, MIDI with envelopes
- Bionic Commando: song table found (8 BGMs), period table found
- Bionic Commando: 20 reference MP3s from NSF rip
- Mega Man 3: 1 trace render (Stage Select) that sounds correct
- Found the Capcom 6C80 engine documentation from the rom hacking community

## What failed
- Applied the 6C80 format to Bionic Commando (wrong engine version)
- ROM-parsed Bionic Commando tracks sound like chaos
- Mega Man 3 ROM parsing: can't find note data using 6C80 format
- No contiguous period table found in Mega Man 3
- Launched 3 agents that all failed (no Bash access)
- The Super Famicom wiki 6C80 docs may describe the SNES variant,
  not the NES variant

## What we learned
1. Capcom had at LEAST 3 engine versions across NES games
2. The 6C80 documentation from the wiki describes the SNES format
   which may differ from the NES format
3. The actual NES-specific documentation is in downloadable PDFs
   on romhacking.net that we can't directly fetch
4. Period values are NOT stored as contiguous tables in Capcom games
5. The Capcom note encoding is fundamentally different from what
   the SNES wiki describes (or we're applying it wrong)

## The trace-based approach still works perfectly
Every trace capture we've done produces accurate audio:
- Castlevania 2: 3 captures, all render correctly
- Gradius: 1 capture, renders correctly
- Super C: 1 capture, renders correctly
- Bionic Commando: 2 captures, both render correctly
- Mega Man 3: 1 capture, renders correctly

The trace renderer is publisher-agnostic and never fails.

## What to do next
1. **User downloads the romhacking.net PDFs** — the real NES-specific
   Capcom engine documentation. I can read PDFs.
   - https://www.romhacking.net/documents/274/ (6C80 for MM3+)
   - https://www.romhacking.net/documents/875/ (Engine 1 for earlier)

2. **OR: stick with trace-based extraction** — capture each track in
   Mesen, render from trace. This works NOW and produces good audio.

3. **Don't attempt ROM parsing for Capcom until the docs are read.**
   The SNES wiki was misleading. The actual NES format may differ.
