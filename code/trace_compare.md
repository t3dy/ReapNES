---
layout: default
title: "trace_compare.py — Trace Validation Tool"
---

# trace_compare.py -- Trace Validation Tool

## The Verification Layer

This script is the project's ground truth validator. It compares the output of
our extraction pipeline (parser -> frame IR) against an APU trace captured from
the Mesen emulator. If the extraction is correct, every frame's pitch, volume,
duty cycle, and sounding state should match what the real NES hardware produces.

### Bugs This Tool Found

- **The EC pitch bug**: An off-by-one in the pitch command handler caused certain
  notes to be one semitone sharp. The trace comparison flagged the exact frame
  where extracted pitch diverged from the emulator, leading directly to the fix.

- **The phase2_start bug**: The envelope model's "fade start" parameter was
  miscalculated, causing volume decay to begin too early. Trace comparison
  showed volume mismatches clustering at the start of notes, pinpointing the
  envelope phase transition as the culprit.

- **Zero-mismatch proof for CV1**: After all fixes, running `--frames 1792`
  (the full Vampire Killer loop) produces zero pitch mismatches on all three
  melodic channels. This is the gold standard -- it means our static extraction
  from the ROM byte-for-byte matches what the NES would actually play.

### The --game parameter

The tool supports multiple games through the `GAME_CONFIGS` dictionary. Each
game has its own ROM path, trace file, trace start offset, parser class, and
output paths. Currently supported: `cv1` (Castlevania 1) and `contra`.
Adding a new game means adding an entry to `GAME_CONFIGS` and providing a
Mesen APU trace CSV.

### How to capture a trace

In Mesen, open the APU debugger, start the game, let the target music play
for the desired duration, and export the APU state log as CSV. The trace
includes per-frame register values for all 5 APU channels. The
`trace_start_frame` config value tells the tool where in the CSV the actual
music begins (skipping title screen silence, etc.).

## Source

```python
#!/usr/bin/env python3
# TUTORIAL: This script has two modes:
#   1. Compare mode (default): parse a track, build frame IR, load trace,
#      diff every frame, write a report.
#   2. Dump mode (--dump-frames): just show raw trace values for a frame range.
#      Invaluable for debugging -- you can see exactly what the NES was doing
#      at any point without running the full comparison.
"""Compare extracted frame IR against emulator APU trace.

Produces a frame-by-frame diff showing pitch, volume, duty, and
sounding-state mismatches between our parser output and ground truth.

Usage:
    python scripts/trace_compare.py [--frames N] [--start-frame F] [--game cv1|contra]

Outputs:
    docs/TraceComparison_<game>.md  (human-readable report)
    data/trace_diff_<game>.json     (machine-readable)
"""
# ---------------------------------------------------------------
# STATUS: MULTI_GAME (supports --game parameter)
# SCOPE: cv1, contra
# VALIDATED: 2026-03-28
# TRACE_RESULT: produces 0-mismatch reports for CV1 pulse
# KNOWN_LIMITATIONS:
#   - Contra trace validation is provisional (~91% pitch match)
# LAYER: tooling
# ---------------------------------------------------------------

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from extraction.drivers.konami.parser import KonamiCV1Parser
from extraction.drivers.konami.contra_parser import ContraParser
from extraction.drivers.konami.frame_ir import (
    parser_to_frame_ir, trace_to_frame_ir, SongIR, FrameState, PITCH_NAMES,
    DriverCapability,
)

# TUTORIAL: GAME_CONFIGS -- the per-game registry.
# Each entry defines everything needed to run a trace comparison:
#
#   rom_path:          where the ROM lives on disk
#   trace_path:        Mesen APU trace CSV (captured from emulator)
#   trace_start_frame: which CSV row corresponds to "frame 0" of the music.
#                      The trace includes boot-up silence, menu screens, etc.
#                      This offset skips to where the target song begins.
#   track:             which song to parse (int for CV1, string for Contra)
#   parser_class:      which parser to instantiate (string, dispatched below)
#   driver:            None for CV1 (default envelope model), "contra" for
#                      Contra (lookup-table envelopes via DriverCapability)
#   report_path:       where to write the human-readable markdown report
#   diff_path:         where to write the machine-readable JSON diff
#
# To add a new game: create a new entry here, provide a trace CSV, and
# ensure the parser class exists.
# ---------------------------------------------------------------------------
# Per-game configuration
# ---------------------------------------------------------------------------
GAME_CONFIGS = {
    "cv1": {
        "rom_path": REPO_ROOT / "extraction" / "roms" / "Castlevania (U) (V1.0) [!].nes",
        "trace_path": REPO_ROOT / "extraction" / "traces" / "castlevania" / "stage1.csv",
        "trace_start_frame": 111,
        "track": 2,
        "parser_class": "KonamiCV1Parser",
        "driver": None,  # uses default CV1 driver
        "report_path": REPO_ROOT / "docs" / "TraceComparison_CV1.md",
        "diff_path": REPO_ROOT / "data" / "trace_diff_cv1.json",
    },
    "contra": {
        "rom_path": REPO_ROOT / "AllNESRoms" / "All NES Roms (GoodNES)" / "USA" / "Contra (U) [!].nes",
        "trace_path": REPO_ROOT / "extraction" / "traces" / "contra" / "jungle.csv",
        "trace_start_frame": 155,
        "track": "jungle",
        "parser_class": "ContraParser",
        "driver": "contra",  # signals to use DriverCapability.contra()
        "report_path": REPO_ROOT / "docs" / "TraceComparison_Contra.md",
        "diff_path": REPO_ROOT / "data" / "trace_diff_contra.json",
    },
}

# Legacy constants kept for backward compat with --start-frame default
TRACE_START_FRAME = 111


def note_name(midi: int) -> str:
    if midi == 0:
        return "---"
    return f"{PITCH_NAMES[midi % 12]}{midi // 12 - 1}"


# TUTORIAL: compare_channels -- THE CORE COMPARISON ENGINE.
#
# This function walks two SongIR objects frame by frame (extracted vs trace)
# and classifies every mismatch into one of four categories:
#
#   pitch_mismatches:    extracted note != trace note (both channels sounding).
#                        This is the most important metric. Zero pitch mismatches
#                        means our parser reads the correct notes from the ROM.
#
#   volume_mismatches:   extracted volume != trace volume (at least one sounding).
#                        Common during envelope tuning. Less critical than pitch
#                        because small volume differences are hard to hear.
#
#   duty_mismatches:     extracted duty != trace duty (skipped for triangle).
#                        Rare -- duty cycle changes are straightforward to parse.
#
#   sounding_mismatches: one side says the channel is sounding, the other says silent.
#                        Often caused by envelope model errors (note ends too early
#                        or too late) or rest command misinterpretation.
#
# The function also tracks:
#   - first_pitch_mismatch / first_sounding_mismatch: frame number of the FIRST
#     error. This is where debugging starts -- always look at the first mismatch.
#   - mismatch_regions: contiguous ranges of frames with errors. Helps identify
#     whether errors are isolated (one bad note) or systematic (wrong octave).
#   - frame_diffs: detailed per-frame data for the first 50 mismatches. Used
#     in the markdown report tables.
def compare_channels(extracted: SongIR, trace: SongIR, max_frames: int) -> dict:
    """Compare two IRs frame by frame. Returns structured diff."""
    results = {}

    ch_pairs = list(zip(extracted.channels, trace.channels))

    for ext_ch, tr_ch in ch_pairs:
        ch_name = ext_ch.channel_type
        diff = {
            "channel": ch_name,
            "total_frames": max_frames,
            "pitch_mismatches": 0,
            "volume_mismatches": 0,
            "duty_mismatches": 0,
            "sounding_mismatches": 0,
            "first_pitch_mismatch": None,
            "first_sounding_mismatch": None,
            "mismatch_regions": [],
            "frame_diffs": [],
        }

        in_mismatch = False
        mismatch_start = 0

        # TUTORIAL: The inner loop. For each frame, we pull the FrameState from
        # both the extracted IR and the trace IR, then compare field by field.
        # Note: duty_match ignores triangle because triangle has no duty cycle
        # register on the NES (it is always a fixed waveform shape).
        # any_mismatch only considers pitch and sounding -- volume and duty
        # mismatches are tracked but do not contribute to "mismatch regions"
        # because they are lower-priority and would create noise in the report.
        for f in range(max_frames):
            ext = ext_ch.get_frame(f)
            tr = tr_ch.get_frame(f)

            pitch_match = ext.midi_note == tr.midi_note
            vol_match = ext.volume == tr.volume
            duty_match = ext.duty == tr.duty or ch_name == "triangle"
            sounding_match = ext.sounding == tr.sounding

            any_mismatch = not (pitch_match and sounding_match)

            if not pitch_match and ext.sounding and tr.sounding:
                diff["pitch_mismatches"] += 1
                if diff["first_pitch_mismatch"] is None:
                    diff["first_pitch_mismatch"] = f

            if not vol_match and (ext.sounding or tr.sounding):
                diff["volume_mismatches"] += 1

            if not duty_match and (ext.sounding or tr.sounding):
                diff["duty_mismatches"] += 1

            if not sounding_match:
                diff["sounding_mismatches"] += 1
                if diff["first_sounding_mismatch"] is None:
                    diff["first_sounding_mismatch"] = f

            # TUTORIAL: Mismatch region tracking. We use a simple state machine:
            # when we enter a mismatch stretch, record the start frame. When we
            # exit, record (start, end) as a region. Regions in the report show
            # patterns -- e.g., "frames 100-115 (16 frames)" suggests a single
            # note is wrong, while "frames 0-1792" suggests a systematic error
            # like wrong octave mapping.
            # Track mismatch regions
            if any_mismatch and not in_mismatch:
                mismatch_start = f
                in_mismatch = True
            elif not any_mismatch and in_mismatch:
                diff["mismatch_regions"].append((mismatch_start, f - 1))
                in_mismatch = False

            # Record individual frame diffs for first 20 mismatches
            if any_mismatch and len(diff["frame_diffs"]) < 50:
                diff["frame_diffs"].append({
                    "frame": f,
                    "ext_note": note_name(ext.midi_note),
                    "tr_note": note_name(tr.midi_note),
                    "ext_vol": ext.volume,
                    "tr_vol": tr.volume,
                    "ext_duty": ext.duty,
                    "tr_duty": tr.duty,
                    "ext_sounding": ext.sounding,
                    "tr_sounding": tr.sounding,
                })

        if in_mismatch:
            diff["mismatch_regions"].append((mismatch_start, max_frames - 1))

        results[ch_name] = diff

    return results


# TUTORIAL: generate_report -- produces the markdown file that humans read.
# The report has three sections:
#   1. Summary table: one row per channel, showing mismatch counts at a glance.
#   2. Mismatch regions: contiguous frame ranges where errors occur.
#   3. Frame diffs: the actual extracted-vs-trace values for individual frames.
# The report is written to docs/TraceComparison_<GAME>.md.
def generate_report(results: dict, max_frames: int, config: dict) -> str:
    """Generate a human-readable markdown report."""
    game_name = [k for k, v in GAME_CONFIGS.items() if v is config][0]
    trace_start = config["trace_start_frame"]

    lines = [
        f"# Trace Comparison: {game_name.upper()} (track: {config['track']})",
        "",
        f"Comparing parser output against emulator APU trace.",
        f"Trace start offset: frame {trace_start}",
        f"Frames compared: {max_frames}",
        "",
    ]

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Channel | Pitch Mismatches | Volume Mismatches | Duty Mismatches | Sounding Mismatches | First Pitch Error |")
    lines.append("|---------|-----------------|-------------------|-----------------|--------------------|--------------------|")

    for ch_name in ["pulse1", "pulse2", "triangle"]:
        if ch_name not in results:
            continue
        d = results[ch_name]
        fp = f"frame {d['first_pitch_mismatch']}" if d['first_pitch_mismatch'] is not None else "none"
        lines.append(
            f"| {ch_name} | {d['pitch_mismatches']} | {d['volume_mismatches']} "
            f"| {d['duty_mismatches']} | {d['sounding_mismatches']} | {fp} |"
        )

    lines.append("")

    # Mismatch regions
    lines.append("## Mismatch Regions")
    lines.append("")
    for ch_name in ["pulse1", "pulse2", "triangle"]:
        if ch_name not in results:
            continue
        d = results[ch_name]
        if d["mismatch_regions"]:
            lines.append(f"### {ch_name}")
            for start, end in d["mismatch_regions"][:20]:
                dur = end - start + 1
                lines.append(f"- frames {start}-{end} ({dur} frames, {dur/60:.2f}s)")
            if len(d["mismatch_regions"]) > 20:
                lines.append(f"- ... ({len(d['mismatch_regions']) - 20} more regions)")
            lines.append("")

    # Detailed frame diffs
    lines.append("## First Frame Diffs (per channel)")
    lines.append("")
    for ch_name in ["pulse1", "pulse2", "triangle"]:
        if ch_name not in results:
            continue
        d = results[ch_name]
        if d["frame_diffs"]:
            lines.append(f"### {ch_name}")
            lines.append("")
            lines.append("| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |")
            lines.append("|-------|-----------|-------|---------|--------|---------|--------|")
            for fd in d["frame_diffs"][:30]:
                lines.append(
                    f"| {fd['frame']} | {fd['ext_note']} | {fd['tr_note']} "
                    f"| {fd['ext_vol']} | {fd['tr_vol']} "
                    f"| {fd['ext_sounding']} | {fd['tr_sounding']} |"
                )
            lines.append("")

    return "\n".join(lines)


# TUTORIAL: main() -- CLI entry point with two modes.
#
# Compare mode (default):
#   python scripts/trace_compare.py --game cv1 --frames 1792
#   Parses the track, builds frame IR, loads the trace, runs compare_channels,
#   prints a summary to stdout, writes the full report to markdown, and writes
#   a machine-readable JSON diff.
#
# Dump mode (--dump-frames):
#   python scripts/trace_compare.py --game cv1 --dump-frames 0-20 --channel pulse1
#   Loads ONLY the trace (no parser needed) and prints raw frame values.
#   This is the "20 real frames first, then fit" principle from CLAUDE.md --
#   always look at what the hardware actually does before writing envelope models.
def main():
    import argparse

    ap = argparse.ArgumentParser(description="Compare extraction vs APU trace")
    ap.add_argument("--game", default="cv1", choices=list(GAME_CONFIGS.keys()),
                    help="Game to compare (default: cv1)")
    ap.add_argument("--frames", type=int, default=600, help="Number of frames to compare")
    ap.add_argument("--start-frame", type=int, default=None,
                    help="Trace frame where music starts (default: from game config)")
    ap.add_argument("--dump-frames", help="Dump raw trace values for frame range (e.g. 0-20)")
    ap.add_argument("--channel", default="all",
                    help="Channel to dump: pulse1, pulse2, triangle, all")
    args = ap.parse_args()

    config = GAME_CONFIGS[args.game]
    trace_path = config["trace_path"]
    trace_start = args.start_frame if args.start_frame is not None else config["trace_start_frame"]

    # TUTORIAL: Dump mode. This bypasses the parser entirely and just reads
    # the emulator trace. Output format is a simple table:
    #   frame  note   vol  duty  snd  period
    # "snd" is Y/. for sounding/silent. "period" is the raw NES timer value.
    # Use this to understand what the hardware is doing before writing code.
    if args.dump_frames:
        # Dump mode: show raw trace values without parser comparison
        parts = args.dump_frames.split("-")
        dump_start = int(parts[0])
        dump_end = int(parts[1]) if len(parts) > 1 else dump_start + 20

        trace_ir = trace_to_frame_ir(
            str(trace_path),
            start_frame=trace_start,
            end_frame=trace_start + dump_end + 1,
        )

        channels = ["pulse1", "pulse2", "triangle"] if args.channel == "all" \
            else [args.channel]

        for ch_ir in trace_ir.channels:
            if ch_ir.channel_type not in channels:
                continue
            print(f"=== {ch_ir.name} (frames {dump_start}-{dump_end}) ===")
            print(f"{'frame':>5s} {'note':>5s} {'vol':>4s} {'duty':>4s} {'snd':>4s} {'period':>6s}")
            for f in range(dump_start, dump_end + 1):
                fs = ch_ir.get_frame(f)
                nn = note_name(fs.midi_note)
                print(f"{f:5d} {nn:>5s} {fs.volume:4d} {fs.duty:4d} "
                      f"{'Y' if fs.sounding else '.':>4s} {fs.period:6d}")
            print()
        sys.exit(0)

    # TUTORIAL: Compare mode. The parser class is dispatched from the config
    # string. ContraParser needs DriverCapability.contra() with envelope tables
    # extracted from the ROM. KonamiCV1Parser uses the default parametric
    # envelope model (no special driver capability needed).
    # Parse track using the appropriate parser
    if config["parser_class"] == "ContraParser":
        print(f"Loading ROM and parsing track '{config['track']}' (Contra)...")
        parser_obj = ContraParser(str(config["rom_path"]))
        song = parser_obj.parse_track(config["track"])
        driver = DriverCapability.contra(parser_obj.envelope_tables)
        print("Converting to frame IR...")
        extracted_ir = parser_to_frame_ir(song, driver=driver)
    else:
        print(f"Loading ROM and parsing track {config['track']}...")
        parser_obj = KonamiCV1Parser(str(config["rom_path"]))
        song = parser_obj.parse_track(config["track"])
        print("Converting to frame IR...")
        extracted_ir = parser_to_frame_ir(song)

    print(f"Loading trace from {trace_path}...")
    trace_ir = trace_to_frame_ir(
        str(trace_path),
        start_frame=trace_start,
        end_frame=trace_start + args.frames,
    )

    print(f"Comparing {args.frames} frames...")
    results = compare_channels(extracted_ir, trace_ir, args.frames)

    # Print summary
    for ch_name in ["pulse1", "pulse2", "triangle"]:
        if ch_name not in results:
            continue
        d = results[ch_name]
        print(f"  {ch_name}: pitch={d['pitch_mismatches']} vol={d['volume_mismatches']} "
              f"sounding={d['sounding_mismatches']} mismatches")

    # TUTORIAL: Two outputs are written:
    #   1. Markdown report (human-readable, committed to docs/)
    #   2. JSON diff (machine-readable, committed to data/)
    # The JSON diff preserves all frame-level detail and can be loaded by
    # other scripts for automated regression testing.
    # Write report
    report = generate_report(results, args.frames, config)
    report_path = config["report_path"]
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport: {report_path}")

    # Write machine-readable diff
    diff_path = config["diff_path"]
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    # Convert tuples to lists for JSON
    json_results = {}
    for ch, d in results.items():
        jd = dict(d)
        jd["mismatch_regions"] = [list(r) for r in d["mismatch_regions"]]
        json_results[ch] = jd
    diff_path.write_text(json.dumps(json_results, indent=2), encoding="utf-8")
    print(f"Diff: {diff_path}")


if __name__ == "__main__":
    main()
```

## How to Read the Output

### Console summary

When you run `python scripts/trace_compare.py --game cv1 --frames 1792`, the
console prints one line per channel:

```
  pulse1: pitch=0 vol=12 sounding=0 mismatches
  pulse2: pitch=0 vol=8 sounding=0 mismatches
  triangle: pitch=0 vol=0 sounding=3 mismatches
```

**pitch=0** is the target. Zero pitch mismatches means every note our parser
extracted matches what the NES hardware actually played. This is the primary
correctness metric.

**vol=N** counts frames where our envelope model disagrees with the trace.
Small numbers (under 2% of total frames) are acceptable -- the parametric
envelope is an approximation of the hardware's behavior, and a few frames
of volume difference are inaudible.

**sounding=N** counts frames where one side thinks the channel is active and
the other thinks it is silent. A small number on triangle is normal because
the triangle channel's linear counter has edge cases at note boundaries.

### Mismatch types explained

| Type | What it means | Severity | Common cause |
|------|---------------|----------|--------------|
| Pitch mismatch | Wrong note | Critical | Parser read wrong byte, octave mapping error, period table mismatch |
| Volume mismatch | Wrong loudness | Low | Envelope model approximation, fade timing off by 1-2 frames |
| Duty mismatch | Wrong timbre | Medium | Duty byte not parsed, duty command missed |
| Sounding mismatch | Note on/off disagreement | Medium | Rest command misinterpreted, envelope ends too early/late |

### Mismatch regions

The report groups consecutive mismatched frames into regions:

```
- frames 100-115 (16 frames, 0.27s)
```

A single short region usually means one note is wrong -- check the frame diff
table for that range to see what the parser produced vs what the trace shows.

Many short regions scattered throughout suggest a recurring pattern error --
perhaps a specific command byte is being misinterpreted.

One very long region (hundreds of frames) indicates a systematic error like
wrong octave, wrong channel assignment, or the parser falling out of sync
with the data stream.

### Frame diff table

The most detailed view. Each row shows one mismatched frame:

| Frame | Extracted | Trace | Ext Vol | Tr Vol | Ext Snd | Tr Snd |
|-------|-----------|-------|---------|--------|---------|--------|
| 105 | C4 | C5 | 12 | 12 | True | True |

This example: frame 105, our parser says C4, trace says C5. Volume and
sounding state match. Diagnosis: octave is off by exactly 12 semitones.
This is the classic "triangle is 1 octave lower" issue documented in
CLAUDE.md.

### Dump mode output

Running `--dump-frames 0-20 --channel pulse1` shows raw trace data:

```
=== Pulse 1 (frames 0-20) ===
frame  note  vol  duty  snd  period
    0   C4   12     2    Y     428
    1   C4   11     2    Y     428
    2   C4   10     2    Y     428
```

Use this to understand the hardware's behavior before writing or debugging
envelope models. The "20 real frames first, then fit" principle: look at
actual data before guessing at parameters.
