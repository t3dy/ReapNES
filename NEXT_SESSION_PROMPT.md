# Startup Prompt — Paste Into New Claude Code Window

---

You are continuing work on NES Music Studio at C:/Dev/NESMusicStudio/.

Read these files in order:

C:/Dev/NESMusicStudio/CLAUDE.md
C:/Dev/NESMusicStudio/docs/HANDOVER.md
C:/Dev/NESMusicStudio/extraction/manifests/contra.json

Then read the Contra parser:

C:/Dev/NESMusicStudio/extraction/drivers/konami/contra_parser.py

Context: Castlevania 1 is COMPLETE (15 tracks, verified). Contra is at v4 — notes and timing are close but volume dynamics are flat. The project now has deterministic tooling (`rom_identify.py`, `trace_compare.py --dump-frames`) and per-game manifests that distinguish verified facts from hypotheses.

Priority work:

1. Implement Contra's volume envelope lookup tables — the `pulse_volume_ptr_tbl` in the Contra disassembly (`references/nes-contra-us/src/bank1.asm` lines 23-95). Extract the envelope data from the ROM, apply per-frame volume shaping in the frame IR. This is the #1 Contra fidelity gap. The contra.json manifest marks this as status: HYPOTHESIS.

2. Once Jungle sounds right (user ear-check), batch all 11 Contra tracks.

3. Investigate next Konami game — run `PYTHONPATH=. python scripts/rom_identify.py <rom>` first, then follow the workflow gates in CLAUDE.md.

Rules:
- CLAUDE.md has ordered workflow gates — follow the sequence, don't skip steps.
- Per-game manifests in extraction/manifests/ carry structured state. Read them. Update them when you verify or disprove something.
- Path-specific rules in .claude/rules/ load automatically. They contain checklists and protocols.
- Run `PYTHONPATH=. python scripts/trace_compare.py --frames 1792` after parser/frame_ir changes.
- Use `--dump-frames N-M --channel X` to extract trace data. Never write ad hoc extraction scripts.
- Version output files. Never overwrite tested files.
- The Contra disassembly at references/nes-contra-us/ is primary source. Read before guessing.

---
