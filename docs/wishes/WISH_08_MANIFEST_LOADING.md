# WISH #8: Runtime Manifest Loading

## 1. What This Wish Is

Make parsers load their per-game configuration from manifest JSON files
at runtime instead of using hardcoded constants in source code. The
manifest already captures every fact that varies between games (pointer
table offset, DX byte counts, channel addresses, mapper layout, envelope
model). The parsers should read these values from the manifest rather
than embedding them as Python literals.

## 2. Why It Matters

**Adding a new game requires editing parser source code.** Today, to
support a new Maezawa-family game, you must either copy an entire parser
file and change the constants (Contra approach) or modify the existing
parser. This violates the architecture principle stated in
FLEXIBLE_PARSER_ARCHITECTURE.md: "manifest declares, parser executes."

Specific costs of the current approach:

- **Duplication.** `parser.py` hardcodes `POINTER_TABLE_ROM_OFFSET =
  0x0825`, `TRACK_ENTRY_SIZE = 9`, `NUM_TRACKS = 15`. `contra_parser.py`
  hardcodes `SOUND_BANK = 1`, `NUM_PRG_BANKS = 8`, `BANK_SIZE = 16384`,
  and a full `TRACK_ADDRESSES` dictionary with 11 entries of hex CPU
  addresses. These are all facts already recorded in the manifests.
- **Drift risk.** If someone corrects a channel address in the manifest
  but forgets to update the parser, the manifest becomes a lie.
- **Scaling wall.** Each new game means a new parser file or a growing
  set of if/elif branches. With manifest loading, a new Maezawa game
  needs only a JSON file and an ear-check.

## 3. Current State

### Manifests (reference only, not loaded by code)

| File | Key data it holds |
|------|-------------------|
| `extraction/manifests/castlevania1.json` | mapper, resolver_method, pointer table at 0x0825, 9-byte entries, 15 tracks, DX bytes (2/0), envelope model (parametric) |
| `extraction/manifests/contra.json` | mapper, bank layout, pointer table at 0x48F8, flat_sound_table format, DX bytes (3/1), 11 track addresses, envelope model (lookup_table) |

### Parsers (hardcoded constants)

**parser.py (CV1):**
```
POINTER_TABLE_ROM_OFFSET = 0x0825
TRACK_ENTRY_SIZE = 9
NUM_TRACKS = 15
```
Address resolution uses `cpu_addr - 0x8000 + INES_HEADER_SIZE` (linear,
mapper 0 style).

**contra_parser.py (Contra):**
```
BANK_SIZE = 16384
SOUND_BANK = 1
NUM_PRG_BANKS = 8
TRACK_ADDRESSES = {"title": (0x9195, 0x91AB, ...), ...}
```
Address resolution uses bank-switched formula with hardcoded bank number.

### Gap

The manifests and the parser constants encode the same facts
independently. No code reads the manifest at parse time.

## 4. Concrete Steps

### Step 1: Manifest loader module

Create `extraction/manifest_loader.py` with:
- `load_manifest(game_name: str) -> dict` — finds and loads
  `extraction/manifests/{game_name}.json`
- Schema version check (v1 passthrough, v2 when schema evolves)
- Validation: required fields present, hex strings parseable

### Step 2: Address resolver factory

Create `extraction/drivers/shared/address.py` (or add to existing
shared module) with:
- `get_resolver(rom_layout: dict) -> Callable[[int], int]`
- "linear" resolver: `cpu - 0x8000 + 16`
- "bank_switched" resolver: reads `sound_bank` and `prg_banks` from
  manifest

Replace the hardcoded `cpu_to_rom` in parser.py and
`contra_cpu_to_rom` in contra_parser.py with calls to this factory.

### Step 3: Inject manifest into CV1 parser

Modify `KonamiCV1Parser.__init__` to accept an optional `manifest`
parameter. When provided, read pointer table offset, entry size, and
track count from it. When absent, fall back to current hardcoded values
(backward compatibility).

### Step 4: Inject manifest into Contra parser

Modify `ContraParser.__init__` to accept an optional `manifest`
parameter. When provided, read track addresses and bank layout from it.
When absent, fall back to current hardcoded dict.

### Step 5: Update pipeline entry points

Modify `full_pipeline.py` and `trace_compare.py` to load the manifest
and pass it to the parser constructor. The `--game` parameter maps to a
manifest file.

### Step 6: Validate

- `PYTHONPATH=. python scripts/trace_compare.py --frames 1792` (CV1):
  0 pitch mismatches
- Contra Jungle ear-check: same output as before
- Parsers still work WITHOUT manifest argument (backward compat)

### Step 7: Remove hardcoded constants

Once validation passes, delete the module-level constants from both
parsers and make manifest loading the only path. Mark old constants
as removed in a commit message.

## 5. Estimated Effort

| Step | Effort |
|------|--------|
| Manifest loader module | 1 hour |
| Address resolver factory | 1 hour |
| CV1 parser manifest injection | 1-2 hours |
| Contra parser manifest injection | 1-2 hours |
| Pipeline wiring | 1 hour |
| Validation (trace + ear) | 1 hour |
| Constant removal + cleanup | 30 min |
| **Total** | **6-8 hours** |

This is a medium-sized refactoring task. The risk is not in complexity
but in accidentally changing parsing behavior during the transition.

## 6. Dependencies

- **No blockers.** Both manifests exist and contain all needed data.
- **WISH relationship:** This is a prerequisite for the unified
  MaezawaParser described in FLEXIBLE_PARSER_ARCHITECTURE.md Phase 2.
  The unified parser cannot be config-driven if there is no config
  loading mechanism.
- **Shared types extraction (Phase 1 of FLEXIBLE_PARSER_ARCHITECTURE):**
  Not strictly required first, but doing Phase 1 before this wish
  produces cleaner code since the address resolver would go directly
  into `shared/address.py` rather than a temporary location.

## 7. Risks

### Behavioral divergence during transition
If the manifest values do not exactly match the hardcoded constants
(e.g., a typo in a hex address), parsing silently produces wrong output.
**Mitigation:** Step 6 validation is mandatory. Trace comparison catches
pitch errors. Add an assertion during the transition period that
manifest-loaded values equal the old hardcoded values.

### Backward compatibility breakage
Scripts and notebooks that import `KonamiCV1Parser("rom.nes")` without
a manifest argument must continue to work.
**Mitigation:** Manifest parameter is optional with fallback to
hardcoded defaults until Step 7.

### Manifest schema drift
If the manifest schema changes (e.g., v2 from
FLEXIBLE_PARSER_ARCHITECTURE.md section 7), the loader must handle both
versions.
**Mitigation:** `load_manifest` checks `schema_version` and migrates.
Start with v1 (current implicit schema). Add v2 migration when needed.

### Over-engineering the loader
Temptation to build a full validation framework, JSON schema, migration
pipeline. This is a 6-hour task, not a 6-week one.
**Mitigation:** The loader is one function that reads JSON and checks
for required keys. Nothing more.

## 8. Success Criteria

1. `KonamiCV1Parser(rom, manifest=cv1_manifest)` produces identical
   `ParsedSong` output to `KonamiCV1Parser(rom)` for all 15 tracks.
2. `ContraParser(rom, manifest=contra_manifest)` produces identical
   output to `ContraParser(rom)` for all 11 tracks.
3. No hardcoded pointer table offsets, bank numbers, or track addresses
   remain in parser source after Step 7.
4. `trace_compare.py --frames 1792` shows 0 pitch mismatches on CV1.
5. Adding a hypothetical third Maezawa game requires only a new manifest
   JSON — no parser source changes.
6. All existing scripts work without modification (backward compat
   maintained through Step 6).

## 9. Priority Ranking

**Priority: MEDIUM.** Important for scaling but not blocking current work.

Rationale:
- CV1 is complete and Contra is close. Neither benefits retroactively
  from this change.
- The payoff arrives with the third game (Super C, TMNT, or Goonies II).
  That is when hardcoded constants become a real maintenance burden.
- FLEXIBLE_PARSER_ARCHITECTURE.md recommends doing Phase 1 (shared types
  extraction) before Phase 2 (unified parser). This wish sits between
  those phases — it is the plumbing that makes Phase 2 possible.
- No urgency, but doing it before the third game arrives avoids the
  "copy parser file again" anti-pattern.

Suggested sequencing:
1. Phase 1: shared types extraction (low risk, do now)
2. **WISH #8: manifest loading (this wish, medium risk, do next)**
3. Phase 2: unified MaezawaParser (do when third game arrives)
