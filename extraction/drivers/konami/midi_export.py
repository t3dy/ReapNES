"""Export parsed Konami CV1 song data to MIDI.

Produces a 4-channel MIDI file conforming to REQUIREMENTSFORMIDI.md
and the nesmdb CC11/CC12 encoding standard.

Usage:
    from extraction.drivers.konami.parser import KonamiCV1Parser
    from extraction.drivers.konami.midi_export import export_to_midi

    parser = KonamiCV1Parser("Castlevania.nes")
    song = parser.parse_track(2)
    export_to_midi(song, "vampire_killer.mid")
"""

from __future__ import annotations

from pathlib import Path

import mido

from extraction.drivers.konami.parser import (
    ParsedSong, NoteEvent, RestEvent, InstrumentChange,
    DrumEvent, OctaveChange, EnvelopeEnable, RepeatMarker,
    SubroutineCall, EndMarker, PITCH_NAMES,
)


# MIDI constants
PPQ = 480           # ticks per quarter note
FRAMES_PER_SEC = 60  # NTSC

# nesmdb CC standard
CC_VELOCITY = 11    # mid-note volume changes
CC_TIMBRE = 12      # duty cycle

# Channel mapping
CHANNEL_MAP = {
    "pulse1": 0,
    "pulse2": 1,
    "triangle": 2,
}
DRUM_CHANNEL = 3

# Drum MIDI note mapping
DRUM_NOTES = {
    "snare": 38,    # GM Acoustic Snare
    "hihat": 42,    # GM Closed Hi-Hat
}

# GM program numbers for channel identification
GM_PROGRAMS = {
    "pulse1": 80,   # Lead 1 (square)
    "pulse2": 81,   # Lead 2 (sawtooth)
    "triangle": 38,  # Synth Bass 1
}


def frames_to_ticks(frames: int, bpm: float = 120.0) -> int:
    """Convert NES frame count to MIDI ticks."""
    seconds = frames / FRAMES_PER_SEC
    ticks_per_second = PPQ * bpm / 60.0
    return max(1, int(seconds * ticks_per_second + 0.5))


def estimate_bpm(song: ParsedSong) -> float:
    """Estimate BPM from the song's tempo and note patterns.

    Heuristic: assume the most common short duration is a 16th note.
    """
    # Collect all tempos used
    tempos = set()
    for ch in song.channels:
        for ev in ch.events:
            if isinstance(ev, InstrumentChange):
                tempos.add(ev.tempo)

    if not tempos:
        return 120.0

    # Most common tempo
    primary_tempo = max(tempos, key=lambda t: sum(
        1 for ch in song.channels for ev in ch.events
        if isinstance(ev, InstrumentChange) and ev.tempo == t
    ))

    # Duration 0 at this tempo = primary_tempo frames
    # Assume duration 0 = 16th note
    # 16th note = beat / 4
    # beat_frames = primary_tempo * 4
    # BPM = 60 * 60 / beat_frames
    beat_frames = primary_tempo * 4
    bpm = 60.0 * FRAMES_PER_SEC / beat_frames
    return round(bpm, 1)


def nes_vol_to_velocity(vol: int) -> int:
    """Convert NES 4-bit volume (0-15) to MIDI velocity (0-127)."""
    if vol <= 0:
        return 0
    return min(127, max(1, int(vol * 127 / 15 + 0.5)))


def export_to_midi(song: ParsedSong, output_path: str | Path,
                   game_name: str = "Castlevania",
                   song_name: str = "") -> Path:
    """Export a parsed song to a Type 1 MIDI file.

    Creates 5 tracks:
    - Track 0: Tempo/meta (tempo, time signature, metadata)
    - Track 1: Pulse 1 (channel 0)
    - Track 2: Pulse 2 (channel 1)
    - Track 3: Triangle (channel 2)
    - Track 4: Drums (channel 3)
    """
    output_path = Path(output_path)
    bpm = estimate_bpm(song)
    tempo_us = int(60_000_000 / bpm)

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)

    # Track 0: Meta
    meta_track = mido.MidiTrack()
    mid.tracks.append(meta_track)
    meta_track.append(mido.MetaMessage('set_tempo', tempo=tempo_us, time=0))
    meta_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Game: {game_name}', time=0))
    if song_name:
        meta_track.append(mido.MetaMessage('text', text=f'Song: {song_name}', time=0))
    meta_track.append(mido.MetaMessage('text', text='Source: ROM static extraction', time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Driver: Konami Pre-VRC (Maezawa)', time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Track: {song.track_number}', time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Tempo: {bpm} BPM (estimated)', time=0))

    # Drum track (channel 3)
    drum_track = mido.MidiTrack()
    drum_track.append(mido.MetaMessage('track_name', name='Noise [drums]', time=0))
    drum_events: list[tuple[int, mido.Message]] = []  # (abs_tick, message)

    # Process each melodic channel
    for ch_data in song.channels:
        ch_type = ch_data.channel_type
        midi_ch = CHANNEL_MAP[ch_type]

        track = mido.MidiTrack()
        mid.tracks.append(track)

        role = {"pulse1": "lead", "pulse2": "harmony", "triangle": "bass"}[ch_type]
        track.append(mido.MetaMessage('track_name',
                                       name=f'{ch_data.name} [{role}]', time=0))
        track.append(mido.Message('program_change',
                                   channel=midi_ch,
                                   program=GM_PROGRAMS[ch_type], time=0))

        abs_tick = 0
        current_note = -1
        current_duty = -1
        current_volume = 15  # NES volume 0-15
        last_tick = 0

        for ev in ch_data.events:
            if isinstance(ev, NoteEvent):
                dur_ticks = frames_to_ticks(ev.duration_frames, bpm)

                # Note off previous note
                if current_note >= 0:
                    delta = abs_tick - last_tick
                    track.append(mido.Message('note_off', channel=midi_ch,
                                              note=current_note, velocity=0,
                                              time=delta))
                    last_tick = abs_tick

                # Note on with velocity from current instrument volume
                delta = abs_tick - last_tick
                velocity = nes_vol_to_velocity(current_volume)
                # Triangle has no volume control — always max
                if ch_type == "triangle":
                    velocity = 127
                track.append(mido.Message('note_on', channel=midi_ch,
                                          note=ev.midi_note, velocity=velocity,
                                          time=delta))
                last_tick = abs_tick
                current_note = ev.midi_note
                abs_tick += dur_ticks

            elif isinstance(ev, RestEvent):
                # Note off if playing
                if current_note >= 0:
                    delta = abs_tick - last_tick
                    track.append(mido.Message('note_off', channel=midi_ch,
                                              note=current_note, velocity=0,
                                              time=delta))
                    last_tick = abs_tick
                    current_note = -1

                dur_ticks = frames_to_ticks(ev.duration_frames, bpm)
                abs_tick += dur_ticks

            elif isinstance(ev, InstrumentChange):
                # Update volume state
                if ev.volume != current_volume:
                    current_volume = ev.volume
                    # Emit CC11 (expression) for volume change
                    delta = abs_tick - last_tick
                    track.append(mido.Message('control_change', channel=midi_ch,
                                              control=CC_VELOCITY,
                                              value=nes_vol_to_velocity(current_volume),
                                              time=delta))
                    last_tick = abs_tick

                # Send CC12 for duty cycle change
                if ev.duty_cycle != current_duty and ch_type != "triangle":
                    delta = abs_tick - last_tick
                    track.append(mido.Message('control_change', channel=midi_ch,
                                              control=CC_TIMBRE, value=ev.duty_cycle,
                                              time=delta))
                    last_tick = abs_tick
                    current_duty = ev.duty_cycle

            elif isinstance(ev, DrumEvent):
                # Add drum event to drum track
                dur_ticks = frames_to_ticks(ev.duration_frames, bpm)
                drum_note = DRUM_NOTES.get(ev.drum_type, 38)
                drum_events.append((abs_tick, mido.Message(
                    'note_on', channel=DRUM_CHANNEL,
                    note=drum_note, velocity=100, time=0)))
                # Short drum duration (1/4 of the note duration)
                drum_off_tick = abs_tick + max(1, dur_ticks // 4)
                drum_events.append((drum_off_tick, mido.Message(
                    'note_off', channel=DRUM_CHANNEL,
                    note=drum_note, velocity=0, time=0)))

            # OctaveChange, EnvelopeEnable, etc. don't produce MIDI events
            # (they affect state used by subsequent NoteEvents)

        # Final note off
        if current_note >= 0:
            delta = abs_tick - last_tick
            track.append(mido.Message('note_off', channel=midi_ch,
                                      note=current_note, velocity=0,
                                      time=delta))

    # Build drum track from collected events
    drum_events.sort(key=lambda x: x[0])
    drum_abs = 0
    for abs_t, msg in drum_events:
        msg.time = abs_t - drum_abs
        drum_track.append(msg)
        drum_abs = abs_t

    mid.tracks.append(drum_track)

    # Find loop point for metadata
    for ch in song.channels:
        for ev in ch.events:
            if isinstance(ev, RepeatMarker) and ev.count == 0xFF:
                total_frames = sum(
                    e.duration_frames for e in ch.events
                    if isinstance(e, (NoteEvent, RestEvent))
                )
                loop_tick = frames_to_ticks(total_frames, bpm)
                meta_track.append(mido.MetaMessage('text',
                                                    text='LOOP_END', time=loop_tick))
                break
        break  # only need one channel's loop point

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python midi_export.py <rom_path> <output.mid> [track_num]")
        sys.exit(1)

    rom_path = sys.argv[1]
    output_path = sys.argv[2]
    track_num = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    from extraction.drivers.konami.parser import KonamiCV1Parser

    parser = KonamiCV1Parser(rom_path)
    song = parser.parse_track(track_num)

    result = export_to_midi(song, output_path,
                            game_name="Castlevania",
                            song_name=f"Track {track_num}")

    print(f"Exported to {result}")
    print(f"  Channels: {len(song.channels)} melodic + drums")
    for ch in song.channels:
        notes = sum(1 for e in ch.events if isinstance(e, NoteEvent))
        print(f"  {ch.name}: {notes} notes")


if __name__ == "__main__":
    main()
