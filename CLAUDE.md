# NES Music Studio

ROM → parser → frame IR → MIDI → REAPER/WAV/MP4.

## Workflow: New Game (follow this order)

1. **Identify** — run `PYTHONPATH=. python scripts/rom_identify.py <rom>`. This reports mapper, period table, driver signature, and manifest status. Do not skip this.
2. **Check manifest** — look in `extraction/manifests/` for an existing JSON. If found, read it for known facts, hypotheses, and anomalies before doing anything else.
3. **Find disassembly** — check `references/` for annotated source. If one exists, read the sound engine code. This is not optional. 10 minutes reading saves hours guessing.
4. **Configure address resolver** — mapper 0 = linear, mapper 2 = bank-switched. Never hardcode; use the manifest's resolver_method.
5. **Determine command format** — DX byte count, $C0 semantics, percussion type. Read from disassembly or infer from data. Record findings in manifest as `verified` or `hypothesis`.
6. **Parse ONE track, listen** — user compares to game. Do not batch-extract before this gate passes.
7. **Iterate on fidelity** — dump trace frames (`trace_compare.py --dump-frames N-M`), fix one thing at a time, re-listen.
8. **Batch extract** — only after the reference track sounds right.

## Hard Invariants

- **Trace is ground truth.** Run `PYTHONPATH=. python scripts/trace_compare.py --frames 1792` after any parser or frame_ir change.
- **Same driver ≠ same ROM layout.** Pointer tables, byte counts, and bank mappings are per-game. Check the manifest.
- **Same period table ≠ same driver.** Period table is universal NES tuning. Verify with DX/FE/FD command signatures.
- **Automated tests miss systematic errors.** User MUST listen after pitch/octave changes. Zero trace mismatches ≠ correct.
- **Triangle is 1 octave lower than pulse** (32-step vs 16-step hardware). Account for this in any pitch mapping change.
- **Version output files** (v1, v2...). Never overwrite a tested file.
- **Dump trace data before modeling.** 20 real frames first, then fit. Never guess at envelope shapes.
- **Check all channels, not just one.** Cross-channel verification catches false assumptions (E8 gate incident).

## State

Per-game structured truth: `extraction/manifests/*.json` — verified facts, hypotheses, anomalies, validation status.
Current priorities: @docs/HANDOVER.md
Mistake narratives: @docs/MISTAKEBAKED.md

## Key Commands

```bash
PYTHONPATH=. python scripts/rom_identify.py <rom>                          # identify ROM
PYTHONPATH=. python scripts/trace_compare.py --frames 1792                 # validate CV1
PYTHONPATH=. python scripts/trace_compare.py --dump-frames 0-20 --channel pulse1  # dump trace
PYTHONPATH=. python scripts/full_pipeline.py <rom> --game-name X           # full pipeline
python scripts/generate_project.py --midi <f> --nes-native -o <out>        # REAPER project
```
