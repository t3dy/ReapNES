"""Tests encoding known parser invariants.

These tests verify that parsers produce structurally valid output
that the frame IR can process correctly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extraction.drivers.konami.parser import (
    pitch_to_midi, ParsedSong, ChannelData, NoteEvent, RestEvent,
    InstrumentChange,
)


class TestPitchToMidi:
    """Pitch mapping invariants.

    Layer: DATA (game-specific octave convention)
    Evidence: CV1 trace 0 pitch mismatches, Contra trace 0 real mismatches.
    """

    def test_base_octave4_is_36(self):
        """INV-005: BASE_MIDI_OCTAVE4 = 36 (C2)."""
        assert pitch_to_midi(0, 4) == 36  # C at octave 4 = C2 = MIDI 36

    def test_triangle_offset_minus_12(self):
        """INV-004: Triangle is 1 octave lower than pulse."""
        pulse = pitch_to_midi(0, 4, is_triangle=False)
        tri = pitch_to_midi(0, 4, is_triangle=True)
        assert pulse - tri == 12

    def test_octave_0_is_highest(self):
        """Octave 0 produces highest notes, octave 4 lowest."""
        high = pitch_to_midi(0, 0)
        low = pitch_to_midi(0, 4)
        assert high > low

    def test_pitch_range_0_to_11(self):
        """All 12 pitches produce distinct MIDI notes within an octave."""
        notes = [pitch_to_midi(p, 2) for p in range(12)]
        assert len(set(notes)) == 12
        assert notes == sorted(notes)  # ascending

    def test_octave_clamp(self):
        """Octave values > 4 are clamped to 4."""
        normal = pitch_to_midi(0, 4)
        clamped = pitch_to_midi(0, 7)
        assert clamped == normal


class TestFullDurationInvariant:
    """Parser full-duration invariant.

    Layer: DATA
    Evidence: Contra parser produces 0 violations.
    """

    def test_valid_song_passes(self):
        """INV-002: A correctly parsed song has no duration violations."""
        song = ParsedSong(track_number=1)
        ch = ChannelData(
            name="test", channel_type="pulse1",
            events=[
                InstrumentChange(
                    tempo=6, raw_instrument=0, duty_cycle=0, volume=5,
                    length_halt=0, constant_vol=0, fade_start=0, fade_step=0,
                    has_sweep=False, sweep_value=0, offset=0,
                ),
                NoteEvent(pitch=0, octave=2, duration_nibble=0,
                         duration_frames=6, midi_note=60, offset=1),
                NoteEvent(pitch=0, octave=2, duration_nibble=2,
                         duration_frames=18, midi_note=60, offset=2),
            ],
            start_offset=0, start_cpu=0,
        )
        song.channels.append(ch)
        assert song.validate_full_duration() == []

    def test_truncated_duration_detected(self):
        """INV-002: Truncated note duration is caught."""
        song = ParsedSong(track_number=1)
        ch = ChannelData(
            name="test", channel_type="pulse1",
            events=[
                InstrumentChange(
                    tempo=6, raw_instrument=0, duty_cycle=0, volume=5,
                    length_halt=0, constant_vol=0, fade_start=0, fade_step=0,
                    has_sweep=False, sweep_value=0, offset=0,
                ),
                NoteEvent(pitch=0, octave=2, duration_nibble=2,
                         duration_frames=12, midi_note=60, offset=1),
                # duration should be 6*(2+1)=18, not 12
            ],
            start_offset=0, start_cpu=0,
        )
        song.channels.append(ch)
        violations = song.validate_full_duration()
        assert len(violations) == 1
