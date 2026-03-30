# WISH #10: The Combinatorial Fugue Matrix Render

## 1. What This Wish Is

Render the full combinatorial matrix of Bach-meets-NES mashups to WAV.
The project generator has already produced 117 REAPER project files in
`studio/reaper_projects/bach_mashups/`, each pairing one of 13 Bach
compositions with one of 9 NES instrument palettes. Zero of these have
corresponding WAV files. A previous batch render session was interrupted
by a crash before producing any output in this directory.

The matrix is:

**13 Bach pieces:**
Fugue 1, Fugue 2, Fugue 5, Fugue 7, Prelude 1, Aria, Invention 1,
Invention 4, Invention 8, Invention 13, Invention 14, Sinfonia 1,
Toccata 1

**9 NES palettes (5 Castlevania, 4 Contra):**
Castlevania: Heart of Fire, Nothing to Lose, Stalker, Vampire Killer,
Wicked Child
Contra: Flame, Jungle, Maze, Waterfall

13 x 9 = 117 combinations. All 117 RPP files exist. Zero WAV files
exist in `bach_mashups/`.

## 2. Why It Matters

This is the creative capstone of the NES Music Studio project. The
extraction pipeline (ROM to parser to frame IR to MIDI) and the
synthesis pipeline (MIDI to NES APU to WAV) are both proven and
working. Twenty-eight earlier mashup WAVs already exist in the parent
`studio/reaper_projects/` directory from prior one-off render sessions
(Chapters 1-7 of ANTIGRAVITYADVENTURES.md). The matrix represents the
systematic exploration of the full timbral space: every contrapuntal
Bach piece heard through every iconic NES soundscape. Without the
renders, 117 project files are inert data.

## 3. Current State

| Asset | Count | Location |
|-------|-------|----------|
| RPP project files | 117 | `studio/reaper_projects/bach_mashups/` |
| WAV renders | 0 | `studio/reaper_projects/bach_mashups/` |
| Prior one-off WAVs | 28 | `studio/reaper_projects/` |
| Song set JSONs available | 48 | `studio/song_sets/` |
| Render script | 1 | `scripts/bach_render_mashup.py` |
| Batch script | 1 | `scripts/render_batch.py` |

The `bach_render_mashup.py` script is a working standalone NES APU
synthesizer that parses MIDI, maps notes to NES timer periods, applies
frame-by-frame volume envelopes from extracted JSFX presets, and writes
WAV. It produced all 28 existing renders successfully.

The `render_batch.py` script is hardcoded to a specific set of 6 jobs
from a prior session. It needs to be rewritten or replaced with a
matrix-aware batch driver.

## 4. Concrete Steps

### Step 1: Build a matrix batch renderer
Write a new script (or refactor `render_batch.py`) that:
- Scans `bach_mashups/*.rpp` to discover the full job list
- Extracts the MIDI source path and song set name from each RPP file
- Calls `render_mashup()` for each combination
- Writes WAV output alongside each RPP (same directory, same basename)
- Supports resume: skip any RPP that already has a matching WAV
- Logs progress and errors per job

### Step 2: Verify MIDI source files are accessible
The RPP files reference MIDI paths (likely under `Downloads/` or
`studio/reaper_projects/midi_remapped/`). Confirm all 13 source MIDIs
exist and are reachable from the batch script.

### Step 3: Verify song set mapping
Map each palette name in the RPP filenames to its song set JSON. The
9 palette names must resolve to files in `studio/song_sets/`. Known
mappings from prior work:
- Castlevania_VampireKiller -> cv1_vampire_killer.json (or Castlevania_02VampireKiller.json)
- Castlevania_WickedChild -> cv1_wicked_child.json (or Castlevania_04WickedChild.json)
- Castlevania_Stalker -> cv1_stalker.json (or Castlevania_03Stalker.json)
- Castlevania_HeartOfFire -> Castlevania_06HeartofFire.json
- Castlevania_NothingToLose -> Castlevania_13NothingtoLose.json
- Contra_Jungle -> contra_jungle.json
- Contra_Waterfall -> contra_waterfall.json
- Contra_Maze -> contra_maze.json
- Contra_Flame -> contra_flame.json

### Step 4: Test render on 3-5 samples
Pick one from each category (fugue, invention, sinfonia) with different
palettes. Listen to confirm output quality matches the 28 existing
renders.

### Step 5: Full batch render
Run the matrix renderer. 117 WAVs at roughly 30-120 seconds each,
rendered via Python NES APU synthesis. Expect 10-30 minutes total
depending on piece length and machine speed.

### Step 6: Validate output
- Confirm 117 WAV files exist
- Check file sizes are non-zero and reasonable (100KB-10MB range)
- Spot-listen to 5-10 renders across different pieces and palettes

## 5. Estimated Effort

| Task | Time |
|------|------|
| Build/refactor batch renderer | 1-2 hours |
| Verify MIDI sources and song set mappings | 30 minutes |
| Test render (3-5 samples) | 15 minutes |
| Full batch render (compute time) | 10-30 minutes |
| Validation and spot-listening | 30 minutes |
| **Total** | **2.5-4 hours** |

## 6. Dependencies

- **MIDI source files**: The 13 Bach MIDIs must be present on disk.
  Some were originally in `c:/Users/PC/Downloads/` which may have been
  cleaned. Others may be in `studio/reaper_projects/midi_remapped/`.
  This is the highest-risk dependency.
- **`scripts/render_wav.py`**: The NES APU synthesis engine imported by
  `bach_render_mashup.py`. Must be importable.
- **`studio/presets/`**: The directory of extracted NES instrument
  envelope files referenced by song set JSONs.
- **`mido` Python package**: Required for MIDI parsing.
- **`numpy` Python package**: Required for audio synthesis.

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missing MIDI source files (Downloads cleaned) | HIGH | Blocks render | Check all 13 MIDIs before starting; re-download from IMSLP if needed |
| Crash during long batch (repeat of prior failure) | MEDIUM | Wastes time | Resume support in batch script; render in chunks of 20 |
| Song set name mismatch (filename conventions differ) | LOW | Per-palette failure | Build explicit mapping dict, not filename heuristics |
| Memory pressure from long pieces (Goldberg, Toccata) | LOW | OOM crash | Process one WAV at a time, release arrays between renders |
| Output quality regression vs existing 28 WAVs | LOW | Wasted renders | Test render before full batch |

## 8. Success Criteria

- [ ] 117 WAV files exist in `studio/reaper_projects/bach_mashups/`,
      one per RPP file, with matching basenames
- [ ] All WAV files are non-zero size and playable
- [ ] Spot-check of 10 WAVs across all 9 palettes confirms correct
      instrument timbres (pulse duty cycles, envelope shapes match the
      named NES game)
- [ ] Batch script supports resume (re-running skips completed renders)
- [ ] No regression: the 28 existing WAVs in the parent directory are
      untouched

## 9. Priority Ranking

**Priority: MEDIUM-HIGH (P2)**

Rationale: This is not on the critical path for the core extraction
pipeline (CV1 is complete, Contra is in progress). However, it is the
single largest block of unrealized creative output in the project --
117 ready-to-render projects sitting idle. The technical risk is low
because the synthesis pipeline is proven. The main blocker is likely
just locating the MIDI source files and writing a proper batch driver.
This could be completed in a single focused session.

Ranks below: Contra volume envelope tables (P1, blocks extraction work).
Ranks above: CV3/Super C investigation (P3, requires new RE work).
