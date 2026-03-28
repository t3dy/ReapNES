"""instrument_clustering.py — Deduplicate and cluster extracted instruments.

Many notes in NES games share identical or near-identical envelope shapes.
This module groups similar instruments, picks a representative for each
cluster, and assigns human-readable names.

Two-phase approach for scalability:
  Phase 1: Quantized hash dedup — collapse instruments with identical
           quantized envelope signatures (O(n), handles millions).
  Phase 2: Vectorized batch clustering — pairwise distance matrix on
           the remaining unique signatures (numpy, fast for <50k).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import replace
from typing import Optional

import numpy as np

from .instrument_extractor import ChannelType, ExtractedInstrument

logger = logging.getLogger(__name__)

# Maximum envelope length for comparison (zero-padded if shorter)
MAX_COMPARE_LEN = 48

# Quantization bins for phase-1 hash dedup (reduces 0-15 to 0-3)
QUANT_BINS = 4


def _normalize_envelope(env: list[int | float], length: int = MAX_COMPARE_LEN) -> np.ndarray:
    """Pad/truncate and normalize an envelope to [0, 1] range."""
    arr = np.zeros(length, dtype=np.float64)
    n = min(len(env), length)
    arr[:n] = env[:n]
    mx = arr.max()
    if mx > 0:
        arr /= mx
    return arr


def _timbre_signature(timbre: list[int]) -> tuple[int, ...]:
    """Reduce a timbre envelope to a short signature for grouping."""
    if not timbre:
        return (0,)
    return (timbre[0], len(set(timbre)))


def _quantize_envelope(env: list[int], length: int = MAX_COMPARE_LEN) -> tuple[int, ...]:
    """Quantize an envelope into coarse bins for hash-based dedup.

    Reduces 16 volume levels to QUANT_BINS levels, pads/truncates
    to fixed length. Identical quantized tuples → same instrument.
    """
    arr = np.zeros(length, dtype=np.int8)
    n = min(len(env), length)
    for i in range(n):
        # Quantize 0-15 to 0-(QUANT_BINS-1)
        arr[i] = min(env[i] * QUANT_BINS // 16, QUANT_BINS - 1)
    return tuple(arr.tolist())


# ---------------------------------------------------------------------------
#  Phase 1: Hash-based dedup (O(n))
# ---------------------------------------------------------------------------

def _hash_dedup(
    instruments: list[ExtractedInstrument],
) -> list[list[ExtractedInstrument]]:
    """Group instruments by quantized envelope hash.

    Instruments with the same (channel_type, timbre_sig, quantized_vol)
    are considered identical and merged into one group.
    """
    buckets: dict[tuple, list[ExtractedInstrument]] = defaultdict(list)

    for inst in instruments:
        key = (
            int(inst.channel_type),
            _timbre_signature(inst.timbre_envelope),
            _quantize_envelope(inst.volume_envelope),
        )
        buckets[key].append(inst)

    return list(buckets.values())


# ---------------------------------------------------------------------------
#  Phase 2: Vectorized batch clustering
# ---------------------------------------------------------------------------

def _batch_cluster(
    groups: list[list[ExtractedInstrument]],
    distance_threshold: float = 0.15,
) -> list[list[ExtractedInstrument]]:
    """Merge hash-dedup groups that are close in normalized envelope space.

    Uses vectorized numpy pairwise distance computation. Groups are
    represented by their first member's envelope.
    """
    if len(groups) <= 1:
        return groups

    # Separate by channel+timbre for independent clustering
    by_key: dict[tuple, list[int]] = defaultdict(list)
    for i, group in enumerate(groups):
        rep = group[0]
        key = (int(rep.channel_type), _timbre_signature(rep.timbre_envelope))
        by_key[key].append(i)

    merged: list[list[ExtractedInstrument]] = []

    for key, indices in by_key.items():
        if len(indices) == 1:
            merged.append(groups[indices[0]])
            continue

        # Build matrix of normalized envelopes
        envelopes = np.array([
            _normalize_envelope(groups[i][0].volume_envelope)
            for i in indices
        ])  # shape: (n_groups, MAX_COMPARE_LEN)

        n = len(indices)
        assigned = np.full(n, -1, dtype=np.int32)
        cluster_id = 0

        for i in range(n):
            if assigned[i] >= 0:
                continue

            # Compute distances from this envelope to all unassigned
            diffs = envelopes[i] - envelopes  # broadcast
            dists = np.sqrt((diffs ** 2).sum(axis=1))

            # Find all within threshold that are unassigned
            mask = (dists < distance_threshold) & (assigned < 0)
            assigned[mask] = cluster_id
            cluster_id += 1

        # Merge groups by cluster assignment
        cluster_map: dict[int, list[ExtractedInstrument]] = defaultdict(list)
        for i, cid in enumerate(assigned):
            cluster_map[int(cid)].extend(groups[indices[i]])

        merged.extend(cluster_map.values())

    return merged


# ---------------------------------------------------------------------------
#  Clustering (public)
# ---------------------------------------------------------------------------

def cluster_instruments(
    instruments: list[ExtractedInstrument],
    distance_threshold: float = 0.15,
) -> list[list[ExtractedInstrument]]:
    """Group instruments by envelope similarity.

    Phase 1: O(n) hash dedup with quantized envelopes.
    Phase 2: Vectorized pairwise clustering on survivors.

    Args:
        instruments: Flat list of extracted instruments.
        distance_threshold: Max envelope distance to merge.

    Returns:
        List of clusters (each cluster is a list of instruments).
    """
    logger.info("Phase 1: Hash dedup on %d instruments...", len(instruments))
    hash_groups = _hash_dedup(instruments)
    logger.info("  → %d unique hash groups", len(hash_groups))

    logger.info("Phase 2: Vectorized clustering (threshold=%.2f)...", distance_threshold)
    clusters = _batch_cluster(hash_groups, distance_threshold)
    logger.info("  → %d final clusters", len(clusters))

    return clusters


# ---------------------------------------------------------------------------
#  Representative selection
# ---------------------------------------------------------------------------

def _pick_representative(cluster: list[ExtractedInstrument]) -> ExtractedInstrument:
    """Pick the best representative instrument from a cluster."""
    if len(cluster) == 1:
        return cluster[0]

    # Sample up to 100 for mean computation (avoid huge matrices)
    sample = cluster[:100]
    padded = np.array([
        _normalize_envelope(inst.volume_envelope) for inst in sample
    ])
    mean_env = padded.mean(axis=0)

    best_idx = 0
    best_dist = float("inf")
    for i, inst in enumerate(sample):
        norm = _normalize_envelope(inst.volume_envelope)
        dist = float(np.linalg.norm(norm - mean_env))
        length_penalty = abs(inst.envelope_length - 12) * 0.001
        total = dist + length_penalty
        if total < best_dist:
            best_dist = total
            best_idx = i

    return sample[best_idx]


# ---------------------------------------------------------------------------
#  Naming
# ---------------------------------------------------------------------------

_PULSE_NAMES = {
    ("decay", 0): "Thin Pluck",
    ("decay", 1): "Pluck",
    ("decay", 2): "Square Pluck",
    ("decay", 3): "Wide Pluck",
    ("flat", 0): "Thin Sustain",
    ("flat", 1): "Narrow Lead",
    ("flat", 2): "Square Lead",
    ("flat", 3): "Wide Lead",
    ("fade", 0): "Thin Pad",
    ("fade", 1): "Soft Lead",
    ("fade", 2): "Square Pad",
    ("fade", 3): "Wide Pad",
    ("swell", 0): "Thin Swell",
    ("swell", 1): "Swell",
    ("swell", 2): "Square Swell",
    ("swell", 3): "Wide Swell",
}

_TRI_NAMES = {
    "decay": "Bass Pluck",
    "flat": "Bass Sustain",
    "fade": "Bass Fade",
    "swell": "Bass Swell",
}

_NOISE_NAMES = {
    ("decay", 0): "Snare",
    ("decay", 1): "Hi-Hat Closed",
    ("flat", 0): "Noise Sustain",
    ("flat", 1): "Cymbal",
    ("fade", 0): "Snare Fade",
    ("fade", 1): "Hi-Hat Open",
    ("swell", 0): "Noise Swell",
    ("swell", 1): "Crash Build",
}


def _classify_shape(vol_env: list[int]) -> str:
    """Classify envelope shape into a category."""
    if not vol_env or len(set(vol_env)) == 1:
        return "flat"
    peak = max(vol_env)
    peak_idx = vol_env.index(peak)
    if peak_idx == 0 and vol_env[-1] == 0:
        return "decay"
    if peak_idx == 0 and vol_env[-1] > 0:
        return "fade"
    return "swell"


def _name_instrument(inst: ExtractedInstrument, cluster_idx: int) -> str:
    """Generate a human-readable name for a representative instrument."""
    shape = _classify_shape(inst.volume_envelope)

    if inst.channel_type in (ChannelType.PULSE1, ChannelType.PULSE2):
        dominant_duty = 2
        if inst.timbre_envelope:
            dominant_duty = max(set(inst.timbre_envelope), key=inst.timbre_envelope.count)
        base_name = _PULSE_NAMES.get((shape, dominant_duty), f"Pulse {shape.title()}")

    elif inst.channel_type == ChannelType.TRIANGLE:
        base_name = _TRI_NAMES.get(shape, "Triangle")

    elif inst.channel_type == ChannelType.NOISE:
        dominant_mode = 0
        if inst.timbre_envelope:
            dominant_mode = max(set(inst.timbre_envelope), key=inst.timbre_envelope.count)
        base_name = _NOISE_NAMES.get((shape, dominant_mode), f"Noise {shape.title()}")

    else:
        base_name = f"Instrument {shape.title()}"

    return f"{base_name} {cluster_idx + 1:03d}"


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def deduplicate_instruments(
    instruments: list[ExtractedInstrument],
    distance_threshold: float = 0.15,
) -> list[ExtractedInstrument]:
    """Cluster instruments and return one representative per cluster.

    Each representative is renamed with a human-readable name and
    its note_count reflects the cluster size.
    """
    clusters = cluster_instruments(instruments, distance_threshold)
    representatives: list[ExtractedInstrument] = []

    for i, cluster in enumerate(clusters):
        rep = _pick_representative(cluster)
        name = _name_instrument(rep, i)
        rep = replace(rep, name=name, note_count=len(cluster))
        representatives.append(rep)

    representatives.sort(key=lambda x: (int(x.channel_type), -x.note_count))

    logger.info(
        "Deduplicated %d instruments → %d representatives",
        len(instruments), len(representatives),
    )
    return representatives
