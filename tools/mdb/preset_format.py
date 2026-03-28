"""preset_format.py — ReapNES instrument preset schema and I/O.

Defines the .reapnes preset format (JSON) and the .reapnes-data format
(plain text) that JSFX can read via file_open/file_string/file_var.

Preset JSON (for tooling/browsing):
{
  "format": "reapnes-instrument",
  "version": 1,
  "name": "pulse2_d50_decay_12f",
  "channel": "pulse",
  "source_game": "Mega Man 2",
  "source_song": "Dr. Wily Stage 1",
  "envelope_length": 12,
  "frame_rate": 24,
  "loop_start": null,
  "volume": [15, 14, 13, 11, 9, 7, 5, 4, 3, 2, 1, 0],
  "timbre": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
  "pitch": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "tags": ["lead", "decay"],
  "cluster_id": null
}

JSFX data file (.reapnes-data) — line-oriented plain text:
  Line 1: envelope_length loop_start channel_type frame_rate
  Line 2: volume values (space-separated integers)
  Line 3: timbre values (space-separated integers)
  Line 4: pitch values (space-separated floats)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from .instrument_extractor import ChannelType, ExtractedInstrument

logger = logging.getLogger(__name__)

PRESET_FORMAT = "reapnes-instrument"
PRESET_VERSION = 1

CHANNEL_NAMES = {
    ChannelType.PULSE1: "pulse",
    ChannelType.PULSE2: "pulse",
    ChannelType.TRIANGLE: "triangle",
    ChannelType.NOISE: "noise",
}


# ---------------------------------------------------------------------------
#  JSON preset I/O
# ---------------------------------------------------------------------------

def instrument_to_json(inst: ExtractedInstrument) -> dict:
    """Convert an ExtractedInstrument to JSON-serializable dict."""
    return {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
        "name": inst.name,
        "channel": CHANNEL_NAMES.get(inst.channel_type, "unknown"),
        "channel_index": int(inst.channel_type),
        "source_game": inst.source_game,
        "source_song": inst.source_song,
        "envelope_length": inst.envelope_length,
        "frame_rate": 24,
        "loop_start": inst.loop_start,
        "volume": inst.volume_envelope,
        "timbre": inst.timbre_envelope,
        "pitch": inst.pitch_envelope,
        "note_count": inst.note_count,
        "tags": _auto_tag(inst),
        "cluster_id": None,
    }


def save_preset_json(inst: ExtractedInstrument, filepath: Path) -> None:
    """Write a single preset as JSON."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    data = instrument_to_json(inst)
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.debug("Saved JSON preset: %s", filepath)


def load_preset_json(filepath: Path) -> dict:
    """Load a JSON preset file."""
    return json.loads(Path(filepath).read_text(encoding="utf-8"))


def save_preset_bank_json(
    instruments: list[ExtractedInstrument],
    filepath: Path,
) -> None:
    """Write a bank of presets as a JSON array."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    bank = [instrument_to_json(inst) for inst in instruments]
    filepath.write_text(json.dumps(bank, indent=2), encoding="utf-8")
    logger.info("Saved preset bank (%d instruments): %s", len(bank), filepath)


def load_preset_bank_json(filepath: Path) -> list[dict]:
    """Load a preset bank JSON file."""
    return json.loads(Path(filepath).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
#  JSFX data file I/O (.reapnes-data)
# ---------------------------------------------------------------------------

def instrument_to_jsfx_data(inst: ExtractedInstrument) -> str:
    """Serialize an instrument to the JSFX-readable plain text format.

    Format:
      Line 1: envelope_length loop_start channel_type frame_rate
              (loop_start = -1 if None)
      Line 2: volume values (space-separated)
      Line 3: timbre values (space-separated)
      Line 4: pitch offsets (space-separated, 2 decimal places)
    """
    loop = inst.loop_start if inst.loop_start is not None else -1
    ch_type = int(inst.channel_type)

    header = f"{inst.envelope_length} {loop} {ch_type} 24"
    vol_line = " ".join(str(v) for v in inst.volume_envelope)
    timbre_line = " ".join(str(t) for t in inst.timbre_envelope)
    pitch_line = " ".join(f"{p:.2f}" for p in inst.pitch_envelope)

    return f"{header}\n{vol_line}\n{timbre_line}\n{pitch_line}\n"


def save_jsfx_data(inst: ExtractedInstrument, filepath: Path) -> None:
    """Write a single instrument as a JSFX-readable data file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(instrument_to_jsfx_data(inst), encoding="utf-8")
    logger.debug("Saved JSFX data: %s", filepath)


def save_jsfx_data_bank(
    instruments: list[ExtractedInstrument],
    directory: Path,
) -> list[Path]:
    """Write each instrument as a separate .reapnes-data file.

    Files are named by index and instrument name for easy browsing.

    Args:
        instruments: List of instruments to export.
        directory: Output directory.

    Returns:
        List of written file paths.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for i, inst in enumerate(instruments):
        safe_name = inst.name.replace(" ", "_").replace("/", "_")[:60]
        filename = f"{i:04d}_{safe_name}.reapnes-data"
        path = directory / filename
        save_jsfx_data(inst, path)
        paths.append(path)

    logger.info("Saved %d JSFX data files to %s", len(paths), directory)
    return paths


def load_jsfx_data(filepath: Path) -> dict:
    """Parse a .reapnes-data file back into a dict.

    Returns dict with keys: envelope_length, loop_start, channel_type,
    frame_rate, volume, timbre, pitch.
    """
    text = Path(filepath).read_text(encoding="utf-8").strip().split("\n")

    header = text[0].split()
    env_len = int(header[0])
    loop_start = int(header[1])
    ch_type = int(header[2])
    frame_rate = int(header[3])

    volume = [int(v) for v in text[1].split()]
    timbre = [int(t) for t in text[2].split()]
    pitch = [float(p) for p in text[3].split()]

    return {
        "envelope_length": env_len,
        "loop_start": loop_start if loop_start >= 0 else None,
        "channel_type": ch_type,
        "frame_rate": frame_rate,
        "volume": volume,
        "timbre": timbre,
        "pitch": pitch,
    }


# ---------------------------------------------------------------------------
#  Auto-tagging
# ---------------------------------------------------------------------------

def _auto_tag(inst: ExtractedInstrument) -> list[str]:
    """Generate descriptive tags from envelope shape analysis."""
    tags: list[str] = []

    # Channel type
    tags.append(CHANNEL_NAMES.get(inst.channel_type, "unknown"))

    vol = inst.volume_envelope
    if not vol:
        return tags

    # Duration class
    if inst.envelope_length <= 6:
        tags.append("staccato")
    elif inst.envelope_length <= 24:
        tags.append("short")
    elif inst.envelope_length <= 72:
        tags.append("medium")
    else:
        tags.append("sustained")

    # Volume shape
    peak = max(vol)
    peak_idx = vol.index(peak)

    if len(set(vol)) == 1:
        tags.append("flat")
    elif peak_idx == 0 and vol[-1] == 0:
        tags.append("decay")
    elif peak_idx == 0 and vol[-1] > 0:
        tags.append("fade")
    elif peak_idx > 0 and peak_idx < len(vol) // 3:
        tags.append("attack")
    elif peak_idx >= len(vol) // 3:
        tags.append("swell")

    if inst.loop_start is not None:
        tags.append("looping")

    # Duty (pulse only)
    if inst.channel_type in (ChannelType.PULSE1, ChannelType.PULSE2):
        duties = set(inst.timbre_envelope)
        if len(duties) == 1:
            d = list(duties)[0]
            duty_labels = {0: "thin", 1: "narrow", 2: "square", 3: "wide"}
            tags.append(duty_labels.get(d, f"duty{d}"))
        else:
            tags.append("duty-sweep")

    # Pitch movement
    if any(abs(p) > 0.5 for p in inst.pitch_envelope):
        if any(abs(p) > 2 for p in inst.pitch_envelope):
            tags.append("pitch-slide")
        else:
            tags.append("vibrato")

    # Noise mode
    if inst.channel_type == ChannelType.NOISE:
        modes = set(inst.timbre_envelope)
        if 1 in modes:
            tags.append("metallic")
        else:
            tags.append("hiss")

    return tags
