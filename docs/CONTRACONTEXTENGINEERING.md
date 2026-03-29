# Context Engineering: What Was Built and Why

## The Diagnosis

After CV1 and Contra extraction, two patterns were burning prompts:

1. **Deterministic work done by LLM reasoning** — ROM header parsing,
   period table scanning, address conversion, trace data extraction.
   Each instance cost 1-3 prompts of work a script should do.

2. **Missing structured state** — each session re-discovered what was
   verified vs hypothesized for each game. Prose handover docs carried
   the knowledge but not in a queryable form.

3. **Startup context doing three jobs** — CLAUDE.md was simultaneously
   policy (rules), memory (mistake narratives), and procedure (checklists).
   These have different lifetimes and access patterns.

## What Was Built

### Layer 1: Deterministic Tooling (replaces prompt-time reasoning)

**`scripts/rom_identify.py`** — single command ROM analysis:
- iNES header parsing (mapper, PRG banks, CHR banks)
- Period table search (finds the 12-entry note table anywhere in ROM)
- Maezawa driver signature detection (scores E8+DX, FE, FD patterns)
- Manifest lookup (checks if game is already configured)
- `--scan-dir` mode for batch identification

**`trace_compare.py --dump-frames N-M`** — direct trace extraction:
- Dumps raw vol/period/duty/sounding per frame for any channel
- Replaces ad hoc Python scripts written fresh each debugging session
- `--channel pulse1|pulse2|triangle|all` filtering

### Layer 2: Structured State (replaces prose memory)

**`extraction/manifests/*.json`** — per-game truth manifests:

Each manifest records verified facts and hypotheses separately:
```json
{
  "command_format": {
    "dx_extra_bytes_pulse": 3,
    "dx_byte_count_status": "verified"   ← not just the value, but its provenance
  },
  "envelope_model": {
    "type": "lookup_table",
    "status": "HYPOTHESIS"               ← future session knows this is unproven
  },
  "known_anomalies": [...]               ← specific unresolved issues
}
```

Fields use explicit status values:
- `verified` — confirmed by trace comparison or disassembly
- `provisional` — inherited from another game, not independently confirmed
- `HYPOTHESIS` — proposed model, not yet tested

**Populated for**: Castlevania 1 (COMPLETE), Contra (IN_PROGRESS).

### Layer 3: Context Architecture (replaces monolithic CLAUDE.md)

**Before:**
| File | Lines | Loads | Content |
|------|-------|-------|---------|
| CLAUDE.md | 120 | Always | Rules + 56 lines of stories + stale milestones |
| CLAUDE_EXTRACTION.md | 145 | Lazy | Rules + checklists + methodology |
| Total startup | ~265 | | |

**After:**
| File | Lines | Loads | Content |
|------|-------|-------|---------|
| CLAUDE.md | 41 | Always | Ordered workflow gates + hard invariants |
| CLAUDE_EXTRACTION.md | 43 | Lazy (extraction/) | Core principles + tool reference |
| .claude/rules/new-game-parser.md | 19 | Path-specific (drivers/) | Per-game checklist |
| .claude/rules/debugging-protocol.md | 22 | Path-specific (extraction/) | 5-step debug order |
| .claude/rules/output-versioning.md | 11 | Path-specific (output/) | Versioning rules |
| Total startup | ~41 | | |

Key structural change: CLAUDE.md is now **ordered workflow gates**, not
flat bullets. The 8-step new-game sequence encodes the correct order of
operations. A flat list of rules doesn't prevent doing step 6 before
step 3. An ordered pipeline does.

### Layer 4: Separation of Concerns

| Layer | Location | Purpose | Access |
|-------|----------|---------|--------|
| Policy | CLAUDE.md | Workflow order, hard invariants | Always loaded |
| Procedure | .claude/rules/ | Checklists, debugging protocol | Path-triggered |
| State | extraction/manifests/ | Per-game verified/hypothesized facts | On demand |
| History | docs/*.md | Narratives, postmortems, lessons | On demand via @import |
| Tools | scripts/ | Deterministic utilities | CLI invocation |

Previously, all five of these lived in CLAUDE.md and CLAUDE_EXTRACTION.md.

## What This Changes for Future Sessions

### New game investigation
Before: 4-6 prompts of manual ROM analysis + guessing.
After: `python scripts/rom_identify.py <rom>` → immediate driver ID + manifest check → read disassembly if exists → configure from manifest template.

### Debugging envelope/pitch issues
Before: write ad hoc Python to extract trace frames, guess at models.
After: `trace_compare.py --dump-frames 0-20 --channel pulse1` → see real data → one hypothesis → test.

### Session startup
Before: model reads 265 lines, most irrelevant to current task.
After: model reads 41 lines of ordered gates + invariants. Path rules load only when relevant. Manifests provide structured game state on demand.

### Adding a new game
Before: copy-paste from CV1 parser, change offsets, hope for the best.
After: `rom_identify.py` → check for disassembly → create manifest from template → fill in verified fields → parser reads manifest for addresses and byte counts.

## What's Still Missing

1. **Parser reading manifests** — contra_parser.py still hardcodes addresses.
   Next step: parser should load from manifest JSON.
2. **Manifest validation** — no script checks manifest against actual ROM.
3. **Contra volume tables** — the #1 fidelity gap remains.
4. **More game manifests** — Super C, TMNT need investigation.
5. **Deterministic/probabilistic repo separation** — the Deckard analysis
   recommends separating deterministic tools from hypothesis-driven RE
   notes at the directory level. Not yet implemented.

## Implementation Order Rationale

Following the user's feedback: build tools before compressing context.

1. `rom_identify.py` — built first because it eliminates the most prompts
2. `--dump-frames` — built second because debugging is the second biggest cost
3. Per-game manifests — built third because they anchor structured state
4. CLAUDE.md revision — built last, shaped by what the tools make unnecessary

The compressed CLAUDE.md (41 lines) is anchored to real capabilities:
- "Run rom_identify.py" is actionable because the script exists
- "Check manifest" is actionable because manifests exist
- "Dump trace frames" is actionable because the flag exists

Previous version said "verify pointer table per game" without providing
the tool to do it. Now the warning and the tool are paired.
