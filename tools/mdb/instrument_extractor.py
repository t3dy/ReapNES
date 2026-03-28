"""instrument_extractor.py — Extract instruments from NES-MDB expressive scores.

NES-MDB expressive scores are (N, 4, 3) uint8 arrays at 24 Hz:
  - 4 voices: P1, P2, Triangle, Noise
  - 3 bytes per voice per frame: [note, velocity, timbre]
    - note: 0 = off, 1-88 = MIDI note 21-108 (pulse/tri), 0-16 (noise pitch)
    - velocity: 0-15 (triangle always 0 — no volume control)
    - timbre: pulse duty 0-3, noise mode 0-1, triangle 0

This module segments the frame stream into individual notes, then
extracts per-note envelopes (volume, duty/timbre, pitch) that become
ReapNES instrument presets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

FRAME_RATE = 24  # NES-MDB temporal resolution (Hz)


class ChannelType(IntEnum):
    PULSE1 = 0
    PULSE2 = 1
    TRIANGLE = 2
    NOISE = 3


@dataclass
class NoteEvent:
    """A single note extracted from a channel's frame stream."""

    channel: ChannelType
    start_frame: int
    end_frame: int  # exclusive
    base_note: int  # MIDI note (pulse/tri) or noise pitch index
    volume_envelope: list[int]  # per-frame velocity values, 0-15
    timbre_envelope: list[int]  # per-frame duty (pulse) or mode (noise)
    pitch_envelope: list[int]  # per-frame note values (absolute)

    @property
    def duration_frames(self) -> int:
        return self.end_frame - self.start_frame

    @property
    def duration_sec(self) -> float:
        return self.duration_frames / FRAME_RATE

    @property
    def has_volume_shape(self) -> bool:
        """True if the volume envelope is non-trivial (not all one value)."""
        if not self.volume_envelope:
            return False
        return len(set(self.volume_envelope)) > 1

    @property
    def has_duty_change(self) -> bool:
        """True if the timbre/duty changes during the note."""
        if not self.timbre_envelope:
            return False
        return len(set(self.timbre_envelope)) > 1

    @property
    def has_pitch_bend(self) -> bool:
        """True if pitch deviates from the base note."""
        return any(p != self.base_note for p in self.pitch_envelope)


@dataclass
class ExtractedInstrument:
    """An instrument template derived from one or more similar NoteEvents."""

    name: str
    channel_type: ChannelType
    volume_envelope: list[int]  # normalized envelope, 0-15
    timbre_envelope: list[int]  # duty/mode sequence
    pitch_envelope: list[float]  # semitone offsets from base note
    loop_start: Optional[int] = None  # frame index where sustain loop begins
    source_game: str = ""
    source_song: str = ""
    note_count: int = 1  # how many notes contributed to this instrument

    @property
    def envelope_length(self) -> int:
        return len(self.volume_envelope)


# ---------------------------------------------------------------------------
#  Note segmentation
# ---------------------------------------------------------------------------

def segment_notes(
    score: np.ndarray,
    channel: ChannelType,
    min_frames: int = 2,
) -> list[NoteEvent]:
    """Segment a channel's frame stream into individual NoteEvents.

    A note begins when the note byte transitions from 0 to >0, or when
    the note value changes (re-trigger). A note ends when the note byte
    becomes 0 or changes to a different pitch.

    Args:
        score: (N, 4, 3) uint8 array — full NES-MDB expressive score.
        channel: Which channel to segment.
        min_frames: Discard notes shorter than this.

    Returns:
        List of NoteEvent objects, sorted by start_frame.
    """
    ch = int(channel)
    n_frames = score.shape[0]
    notes: list[NoteEvent] = []

    note_on = False
    start = 0
    current_note = 0
    vol_buf: list[int] = []
    timbre_buf: list[int] = []
    pitch_buf: list[int] = []

    for i in range(n_frames):
        note_val = int(score[i, ch, 0])
        vel_val = int(score[i, ch, 1])
        timbre_val = int(score[i, ch, 2])

        if note_val > 0:
            if not note_on or note_val != current_note:
                # Close previous note if open
                if note_on and len(vol_buf) >= min_frames:
                    notes.append(NoteEvent(
                        channel=channel,
                        start_frame=start,
                        end_frame=i,
                        base_note=current_note,
                        volume_envelope=list(vol_buf),
                        timbre_envelope=list(timbre_buf),
                        pitch_envelope=list(pitch_buf),
                    ))
                # Start new note
                note_on = True
                start = i
                current_note = note_val
                vol_buf = [vel_val]
                timbre_buf = [timbre_val]
                pitch_buf = [note_val]
            else:
                # Continue current note
                vol_buf.append(vel_val)
                timbre_buf.append(timbre_val)
                pitch_buf.append(note_val)
        else:
            # Note off
            if note_on and len(vol_buf) >= min_frames:
                notes.append(NoteEvent(
                    channel=channel,
                    start_frame=start,
                    end_frame=i,
                    base_note=current_note,
                    volume_envelope=list(vol_buf),
                    timbre_envelope=list(timbre_buf),
                    pitch_envelope=list(pitch_buf),
                ))
            note_on = False
            vol_buf = []
            timbre_buf = []
            pitch_buf = []

    # Close final note if still open
    if note_on and len(vol_buf) >= min_frames:
        notes.append(NoteEvent(
            channel=channel,
            start_frame=start,
            end_frame=n_frames,
            base_note=current_note,
            volume_envelope=list(vol_buf),
            timbre_envelope=list(timbre_buf),
            pitch_envelope=list(pitch_buf),
        ))

    return notes


def segment_all_channels(
    score: np.ndarray,
    min_frames: int = 2,
) -> dict[ChannelType, list[NoteEvent]]:
    """Segment all 4 channels of a score into NoteEvents.

    Args:
        score: (N, 4, 3) uint8 array.
        min_frames: Minimum note length to keep.

    Returns:
        Dict mapping ChannelType → list of NoteEvents.
    """
    return {
        ch: segment_notes(score, ch, min_frames)
        for ch in ChannelType
    }


# ---------------------------------------------------------------------------
#  Envelope extraction → Instrument
# ---------------------------------------------------------------------------

def _detect_loop_point(envelope: list[int], min_sustain: int = 4) -> Optional[int]:
    """Detect a sustain loop point in an envelope.

    Heuristic: find the longest run of a constant value after the
    attack phase. The loop point is the start of that run.

    Args:
        envelope: List of envelope values.
        min_sustain: Minimum run length to qualify as sustain.

    Returns:
        Frame index of loop start, or None if no sustain detected.
    """
    if len(envelope) < min_sustain + 2:
        return None

    best_start = None
    best_len = 0
    run_start = 0
    run_len = 1

    for i in range(1, len(envelope)):
        if envelope[i] == envelope[i - 1]:
            run_len += 1
        else:
            if run_len >= min_sustain and run_len > best_len:
                best_start = run_start
                best_len = run_len
            run_start = i
            run_len = 1

    # Check final run
    if run_len >= min_sustain and run_len > best_len:
        best_start = run_start

    return best_start


def note_to_instrument(
    note: NoteEvent,
    source_game: str = "",
    source_song: str = "",
) -> ExtractedInstrument:
    """Convert a single NoteEvent into an ExtractedInstrument.

    The pitch envelope is converted to semitone offsets relative to the
    base note (for pulse/triangle) or kept absolute (for noise).

    Args:
        note: The NoteEvent to convert.
        source_game: Game name metadata.
        source_song: Song name metadata.

    Returns:
        ExtractedInstrument with envelope data.
    """
    # Pitch envelope: convert to offsets from base note
    if note.channel in (ChannelType.PULSE1, ChannelType.PULSE2, ChannelType.TRIANGLE):
        pitch_offsets = [float(p - note.base_note) for p in note.pitch_envelope]
    else:
        # Noise: keep absolute pitch index
        pitch_offsets = [float(p) for p in note.pitch_envelope]

    loop_start = _detect_loop_point(note.volume_envelope)

    # Name based on channel + dominant characteristics
    ch_name = note.channel.name.lower()
    duty_str = ""
    if note.channel in (ChannelType.PULSE1, ChannelType.PULSE2) and note.timbre_envelope:
        dominant_duty = max(set(note.timbre_envelope), key=note.timbre_envelope.count)
        duty_names = {0: "12", 1: "25", 2: "50", 3: "75"}
        duty_str = f"_d{duty_names.get(dominant_duty, str(dominant_duty))}"

    shape = "flat"
    if note.has_volume_shape:
        vol = note.volume_envelope
        peak_idx = vol.index(max(vol))
        if peak_idx == 0 and len(vol) > 2 and vol[-1] < vol[0]:
            shape = "decay"
        elif peak_idx > 0:
            shape = "swell"
        elif vol[-1] < vol[0]:
            shape = "fade"

    name = f"{ch_name}{duty_str}_{shape}_{note.duration_frames}f"

    return ExtractedInstrument(
        name=name,
        channel_type=note.channel,
        volume_envelope=list(note.volume_envelope),
        timbre_envelope=list(note.timbre_envelope),
        pitch_envelope=pitch_offsets,
        loop_start=loop_start,
        source_game=source_game,
        source_song=source_song,
        note_count=1,
    )


def extract_instruments_from_score(
    score: np.ndarray,
    source_game: str = "",
    source_song: str = "",
    min_frames: int = 3,
    max_envelope_len: int = 240,
) -> list[ExtractedInstrument]:
    """Extract all instruments from a full NES-MDB score.

    Args:
        score: (N, 4, 3) uint8 array.
        source_game: Game name for metadata.
        source_song: Song name for metadata.
        min_frames: Minimum note length to consider.
        max_envelope_len: Truncate envelopes longer than this.

    Returns:
        List of ExtractedInstrument objects.
    """
    instruments: list[ExtractedInstrument] = []

    all_notes = segment_all_channels(score, min_frames)

    for ch, notes in all_notes.items():
        for note in notes:
            # Truncate very long notes (sustained pads)
            if note.duration_frames > max_envelope_len:
                note = NoteEvent(
                    channel=note.channel,
                    start_frame=note.start_frame,
                    end_frame=note.start_frame + max_envelope_len,
                    base_note=note.base_note,
                    volume_envelope=note.volume_envelope[:max_envelope_len],
                    timbre_envelope=note.timbre_envelope[:max_envelope_len],
                    pitch_envelope=note.pitch_envelope[:max_envelope_len],
                )

            inst = note_to_instrument(note, source_game, source_song)
            instruments.append(inst)

    logger.info(
        "Extracted %d instruments from %s / %s",
        len(instruments), source_game, source_song,
    )
    return instruments
