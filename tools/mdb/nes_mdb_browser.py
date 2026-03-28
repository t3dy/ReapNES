"""nes_mdb_browser.py — Browse and filter the NES Music Database (NES-MDB).

NES-MDB provides expressive MIDI-like scores extracted from NES ROMs.
This module loads the nesmdb "expressive score" format and exposes
filtering, search, and export helpers for integration with ReapNES Studio.

Reference: https://github.com/chrisdonahue/nesmdb
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Data structures
# ---------------------------------------------------------------------------

@dataclass
class NESScore:
    """A single NES-MDB expressive score entry."""

    name: str
    path: Path
    num_channels: int = 4
    duration_sec: float = 0.0
    score_data: Optional[np.ndarray] = None
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
#  Loader
# ---------------------------------------------------------------------------

def load_expressive_score(filepath: Path) -> NESScore:
    """Load a single NES-MDB expressive score (.npy or .npz).

    The nesmdb expressive format stores a (T, 4) array where each column
    corresponds to Pulse1, Pulse2, Triangle, and Noise.  Each row is a
    time step at the NES frame rate (~60 Hz NTSC).

    Args:
        filepath: Path to the .npy/.npz score file.

    Returns:
        Populated NESScore dataclass.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        msg = f"Score file not found: {filepath}"
        raise FileNotFoundError(msg)

    data = np.load(filepath, allow_pickle=False)

    # .npz files store arrays by key; grab the first one
    if isinstance(data, np.lib.npyio.NpzFile):
        key = list(data.keys())[0]
        arr = data[key]
    else:
        arr = data

    duration = arr.shape[0] / 60.0  # ~60 Hz frame rate

    return NESScore(
        name=filepath.stem,
        path=filepath,
        num_channels=arr.shape[1] if arr.ndim > 1 else 1,
        duration_sec=duration,
        score_data=arr,
    )


# ---------------------------------------------------------------------------
#  Browser / filter
# ---------------------------------------------------------------------------

def scan_directory(root: Path, pattern: str = "*.npy") -> list[Path]:
    """Recursively find all score files under *root*.

    Args:
        root: Directory to scan.
        pattern: Glob pattern for score files.

    Returns:
        Sorted list of matching paths.
    """
    root = Path(root)
    if not root.is_dir():
        logger.warning("Directory does not exist: %s", root)
        return []
    return sorted(root.rglob(pattern))


def filter_by_duration(
    scores: Sequence[NESScore],
    min_sec: float = 0.0,
    max_sec: float = float("inf"),
) -> list[NESScore]:
    """Return scores whose duration falls within [min_sec, max_sec].

    Args:
        scores: Iterable of NESScore objects.
        min_sec: Minimum duration in seconds.
        max_sec: Maximum duration in seconds.

    Returns:
        Filtered list.
    """
    return [s for s in scores if min_sec <= s.duration_sec <= max_sec]


def filter_by_name(
    scores: Sequence[NESScore],
    query: str,
) -> list[NESScore]:
    """Case-insensitive substring search on score names.

    Args:
        scores: Iterable of NESScore objects.
        query: Search string.

    Returns:
        Matching scores.
    """
    q = query.lower()
    return [s for s in scores if q in s.name.lower()]


# ---------------------------------------------------------------------------
#  Export helpers
# ---------------------------------------------------------------------------

def score_to_midi_cc_map(score: NESScore) -> dict[int, list[int]]:
    """Convert a score's channel data to a MIDI CC-style mapping.

    Placeholder for future expansion — maps each NES channel index
    to a list of MIDI CC values suitable for driving ReapNES sliders.

    Args:
        score: A loaded NESScore.

    Returns:
        Dict mapping channel index (0..3) to a list of integer values.
    """
    if score.score_data is None:
        return {}

    result: dict[int, list[int]] = {}
    for ch in range(min(score.num_channels, 4)):
        if score.score_data.ndim > 1:
            col = score.score_data[:, ch]
        else:
            col = score.score_data
        # Normalize to 0..127 MIDI range
        col_min, col_max = float(col.min()), float(col.max())
        span = col_max - col_min if col_max != col_min else 1.0
        normalized = ((col - col_min) / span * 127).astype(int).tolist()
        result[ch] = normalized

    return result


# ---------------------------------------------------------------------------
#  CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Simple CLI for browsing NES-MDB scores."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Browse and filter NES-MDB expressive scores.",
    )
    parser.add_argument("directory", type=Path, help="Root directory of NES-MDB scores")
    parser.add_argument("--pattern", default="*.npy", help="Glob pattern (default: *.npy)")
    parser.add_argument("--min-duration", type=float, default=0.0, help="Min duration (sec)")
    parser.add_argument("--max-duration", type=float, default=float("inf"), help="Max duration (sec)")
    parser.add_argument("--search", type=str, default=None, help="Name substring filter")
    args = parser.parse_args()

    paths = scan_directory(args.directory, args.pattern)
    logger.info("Found %d score files", len(paths))

    scores = [load_expressive_score(p) for p in paths]

    if args.search:
        scores = filter_by_name(scores, args.search)
    scores = filter_by_duration(scores, args.min_duration, args.max_duration)

    for s in scores:
        print(f"{s.name:40s}  {s.duration_sec:6.1f}s  ch={s.num_channels}  {s.path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
