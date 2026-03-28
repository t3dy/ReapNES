#!/usr/bin/env python3
"""Compare extracted frame IR against emulator APU trace.

Produces a frame-by-frame diff showing pitch, volume, duty, and
sounding-state mismatches between our parser output and ground truth.

Usage:
    python scripts/trace_compare.py [--frames N] [--start-frame F]

Outputs:
    docs/TraceComparison_CV1.md  (human-readable report)
    data/trace_diff_cv1.json     (machine-readable)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from extraction.drivers.konami.parser import KonamiCV1Parser
from extraction.drivers.konami.frame_ir import (
    parser_to_frame_ir, trace_to_frame_ir, SongIR, FrameState, PITCH_NAMES,
)

ROM_PATH = REPO_ROOT / "extraction" / "roms" / "Castlevania (U) (V1.0) [!].nes"
TRACE_PATH = REPO_ROOT / "extraction" / "traces" / "castlevania" / "stage1.csv"

# Vampire Killer starts at approximately frame 111 in the trace
TRACE_START_FRAME = 111


def note_name(midi: int) -> str:
    if midi == 0:
        return "---"
    return f"{PITCH_NAMES[midi % 12]}{midi // 12 - 1}"


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


def generate_report(results: dict, max_frames: int) -> str:
    """Generate a human-readable markdown report."""
    lines = [
        "# Trace Comparison: Castlevania 1 Vampire Killer",
        "",
        f"Comparing parser output against emulator APU trace.",
        f"Trace start offset: frame {TRACE_START_FRAME}",
        f"Frames compared: {max_frames}",
        "",
    ]

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Channel | Pitch Mismatches | Volume Mismatches | Duty Mismatches | Sounding Mismatches | First Pitch Error |")
    lines.append("|---------|-----------------|-------------------|-----------------|--------------------|--------------------|")

    for ch_name in ["pulse1", "pulse2", "triangle"]:
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


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Compare extraction vs APU trace")
    ap.add_argument("--frames", type=int, default=600, help="Number of frames to compare")
    ap.add_argument("--start-frame", type=int, default=TRACE_START_FRAME,
                    help="Trace frame where Vampire Killer starts")
    args = ap.parse_args()

    print("Loading ROM and parsing track 2 (Vampire Killer)...")
    parser = KonamiCV1Parser(str(ROM_PATH))
    song = parser.parse_track(2)

    print("Converting to frame IR...")
    extracted_ir = parser_to_frame_ir(song)

    print(f"Loading trace from {TRACE_PATH}...")
    trace_ir = trace_to_frame_ir(
        str(TRACE_PATH),
        start_frame=args.start_frame,
        end_frame=args.start_frame + args.frames,
    )

    print(f"Comparing {args.frames} frames...")
    results = compare_channels(extracted_ir, trace_ir, args.frames)

    # Print summary
    for ch_name in ["pulse1", "pulse2", "triangle"]:
        d = results[ch_name]
        print(f"  {ch_name}: pitch={d['pitch_mismatches']} vol={d['volume_mismatches']} "
              f"sounding={d['sounding_mismatches']} mismatches")

    # Write report
    report = generate_report(results, args.frames)
    report_path = REPO_ROOT / "docs" / "TraceComparison_CV1.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport: {report_path}")

    # Write machine-readable diff
    diff_path = REPO_ROOT / "data" / "trace_diff_cv1.json"
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
