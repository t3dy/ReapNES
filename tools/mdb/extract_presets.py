"""extract_presets.py — Batch pipeline: NES-MDB scores → ReapNES instrument presets.

Usage:
  python -m tools.mdb.extract_presets /path/to/nesmdb/scores ./output/presets

  # With options:
  python -m tools.mdb.extract_presets ./scores ./presets \
    --pattern "*.npy" \
    --min-notes 3 \
    --distance 0.15 \
    --format both
"""

from __future__ import annotations

import argparse
import logging
import pickle
import sys
from pathlib import Path

import numpy as np

from .instrument_extractor import (
    ChannelType,
    ExtractedInstrument,
    extract_instruments_from_score,
)
from .instrument_clustering import deduplicate_instruments
from .preset_format import (
    save_jsfx_data_bank,
    save_preset_bank_json,
)

logger = logging.getLogger(__name__)


def load_score(filepath: Path) -> np.ndarray | None:
    """Load an NES-MDB expressive score.

    Handles the actual NES-MDB format (.exprsco.pkl) as well as
    plain .npy/.npz files. The pickle format stores a tuple:
      (rate, nsamps, exprsco)
    where exprsco is an (N, 4, 3) uint8 array.

    Expected output shape: (N, 4, 3) uint8.
    """
    filepath = Path(filepath)

    try:
        # Handle pickle format (.exprsco.pkl or .pkl)
        if filepath.suffix == ".pkl" or ".exprsco" in filepath.name:
            with filepath.open("rb") as f:
                data = pickle.load(f, encoding="latin1")

            # NES-MDB pickle format: (rate, nsamps, score_array)
            if isinstance(data, (tuple, list)) and len(data) >= 3:
                arr = data[2]
            elif isinstance(data, np.ndarray):
                arr = data
            else:
                logger.warning("Unexpected pickle structure in %s", filepath)
                return None
        else:
            # Plain numpy format
            data = np.load(filepath, allow_pickle=False)
            if isinstance(data, np.lib.npyio.NpzFile):
                key = list(data.keys())[0]
                arr = data[key]
            else:
                arr = data

        arr = np.asarray(arr)

        # Validate shape
        if arr.ndim == 3 and arr.shape[1] == 4 and arr.shape[2] == 3:
            return arr

        # Some files may have a flat layout
        if arr.ndim == 2 and arr.shape[1] == 12:
            return arr.reshape(-1, 4, 3)

        logger.warning(
            "Unexpected shape %s in %s, skipping", arr.shape, filepath,
        )
        return None

    except Exception as e:
        logger.warning("Failed to load %s: %s", filepath, e)
        return None


def extract_from_directory(
    score_dir: Path,
    pattern: str = "*.pkl",
    min_note_frames: int = 3,
    max_envelope_len: int = 240,
) -> list[ExtractedInstrument]:
    """Extract instruments from all scores in a directory.

    Args:
        score_dir: Root directory containing NES-MDB score files.
        pattern: Glob pattern for score files.
        min_note_frames: Minimum note length to consider.
        max_envelope_len: Truncate envelopes longer than this.

    Returns:
        Flat list of all extracted instruments (before dedup).
    """
    score_dir = Path(score_dir)
    paths = sorted(score_dir.rglob(pattern))
    logger.info("Found %d score files in %s", len(paths), score_dir)

    all_instruments: list[ExtractedInstrument] = []

    for i, path in enumerate(paths):
        if i % 100 == 0 and i > 0:
            logger.info("  Processing %d / %d ...", i, len(paths))

        score = load_score(path)
        if score is None:
            continue

        # Derive game/song name from NES-MDB filename convention:
        #   002_1943_TheBattleofMidway_03_04AirBattleA.exprsco.pkl
        #   ^^^                        ^^_^^^^^^^^^^^^^^
        #   game ID                    track num + song name
        stem = path.name.split(".")[0]  # strip .exprsco.pkl
        parts = stem.split("_")
        if len(parts) >= 3:
            # parts[0] = game ID, parts[1:N-2] = game name, rest = song
            # Heuristic: game name is CamelCase chunks before track numbers
            game_name = "_".join(parts[1:-2]) if len(parts) > 3 else parts[1]
            song_name = parts[-1] if parts else stem
        else:
            game_name = path.parent.name if path.parent != score_dir else "Unknown"
            song_name = stem

        instruments = extract_instruments_from_score(
            score,
            source_game=game_name,
            source_song=song_name,
            min_frames=min_note_frames,
            max_envelope_len=max_envelope_len,
        )
        all_instruments.extend(instruments)

    logger.info("Total raw instruments extracted: %d", len(all_instruments))
    return all_instruments


def run_pipeline(
    score_dir: Path,
    output_dir: Path,
    pattern: str = "*.pkl",
    min_note_frames: int = 3,
    max_envelope_len: int = 240,
    distance_threshold: float = 0.15,
    output_format: str = "both",
) -> None:
    """Full extraction pipeline: scores → instruments → clusters → presets.

    Args:
        score_dir: Input directory with NES-MDB scores.
        output_dir: Where to write preset files.
        pattern: Glob pattern for score files.
        min_note_frames: Minimum note length.
        max_envelope_len: Max envelope frames.
        distance_threshold: Clustering distance threshold.
        output_format: "json", "jsfx", or "both".
    """
    output_dir = Path(output_dir)

    # Step 1: Extract all instruments
    logger.info("Step 1: Extracting instruments from %s", score_dir)
    raw_instruments = extract_from_directory(
        score_dir, pattern, min_note_frames, max_envelope_len,
    )

    if not raw_instruments:
        logger.warning("No instruments extracted. Check your score directory.")
        return

    # Step 2: Cluster and deduplicate
    logger.info("Step 2: Clustering %d instruments...", len(raw_instruments))
    representatives = deduplicate_instruments(raw_instruments, distance_threshold)
    logger.info("  → %d unique instruments", len(representatives))

    # Step 3: Export
    logger.info("Step 3: Exporting presets to %s", output_dir)

    if output_format in ("json", "both"):
        json_path = output_dir / "preset_bank.json"
        save_preset_bank_json(representatives, json_path)
        logger.info("  Saved JSON bank: %s", json_path)

    if output_format in ("jsfx", "both"):
        jsfx_dir = output_dir / "jsfx_data"
        paths = save_jsfx_data_bank(representatives, jsfx_dir)
        logger.info("  Saved %d JSFX data files to %s", len(paths), jsfx_dir)

    # Step 4: Summary
    by_channel: dict[str, int] = {}
    for inst in representatives:
        ch = inst.channel_type.name
        by_channel[ch] = by_channel.get(ch, 0) + 1

    print("\n=== ReapNES Preset Extraction Complete ===")
    print(f"Scores processed:    {len(list(Path(score_dir).rglob(pattern)))}")
    print(f"Raw notes extracted:  {len(raw_instruments)}")
    print(f"Unique instruments:   {len(representatives)}")
    print(f"By channel:")
    for ch, count in sorted(by_channel.items()):
        print(f"  {ch:12s}: {count}")
    print(f"Output directory:     {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract NES instrument presets from NES-MDB scores.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./nesmdb_scores ./presets
  %(prog)s ./scores ./presets --distance 0.2 --format jsfx
  %(prog)s ./scores ./presets --pattern "*.npz" --min-notes 5
        """,
    )
    parser.add_argument("score_dir", type=Path, help="Directory containing NES-MDB score files")
    parser.add_argument("output_dir", type=Path, help="Output directory for presets")
    parser.add_argument("--pattern", default="*.pkl", help="Glob pattern (default: *.npy)")
    parser.add_argument("--min-notes", type=int, default=3, help="Min note length in frames (default: 3)")
    parser.add_argument("--max-envelope", type=int, default=240, help="Max envelope length (default: 240)")
    parser.add_argument("--distance", type=float, default=0.15, help="Clustering threshold (default: 0.15)")
    parser.add_argument(
        "--format", choices=["json", "jsfx", "both"], default="both",
        help="Output format (default: both)",
    )
    args = parser.parse_args()

    run_pipeline(
        score_dir=args.score_dir,
        output_dir=args.output_dir,
        pattern=args.pattern,
        min_note_frames=args.min_notes,
        max_envelope_len=args.max_envelope,
        distance_threshold=args.distance,
        output_format=args.format,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
