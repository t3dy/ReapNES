"""Konami pre-VRC sound driver parser.

Parses music data from Konami NES ROMs using the pre-expansion-audio
sound driver. Target ROM: Castlevania (U).

This parser is the first end-to-end driver implementation for NES Music Lab.
It will be developed incrementally during Phase 3.
"""

from __future__ import annotations

from nesml.static_analysis.sequence_decode import SequenceDecoder, DecodeContext
from nesml.models.song import Song, ChannelStream, Pattern
from nesml.models.core import Confidence


class KonamiPreVRCDecoder(SequenceDecoder):
    """Sequence decoder for the Konami pre-VRC sound driver.

    STUB: Command handling will be implemented during Phase 3
    as we reverse-engineer the Castlevania driver bytecode.
    """

    def decode_command(self, ctx: DecodeContext, opcode: int) -> None:
        """Decode a single Konami driver command byte.

        TODO Phase 3:
        - Identify note command range and decode pitch + duration
        - Identify rest commands
        - Identify control flow (loop, end, jump)
        - Identify envelope/duty selection commands
        - Handle speed change commands
        """
        ctx.emit_unknown(opcode)
        # Stop after 200 unknowns during initial investigation
        if len(ctx.unknowns) > 200:
            ctx.halted = True


class KonamiPreVRCParser:
    """High-level parser for Konami pre-VRC ROM music data.

    Usage:
        parser = KonamiPreVRCParser()
        song = parser.parse_song(prg_data, song_index=0)

    STUB: Will be fleshed out during Phase 3.
    """

    def __init__(self):
        self.decoder = KonamiPreVRCDecoder()
        # These will be discovered during Phase 3
        self.song_table_offset: int | None = None
        self.song_count: int | None = None

    def locate_song_table(self, prg_data: bytes) -> int | None:
        """Find the song table in PRG data.

        TODO Phase 3: Implement actual song table discovery using
        pointer scanning and code signature matching.

        Returns the byte offset of the song table, or None.
        """
        return self.song_table_offset

    def parse_song(self, prg_data: bytes, song_index: int) -> Song:
        """Parse a single song from the ROM.

        STUB: Returns a placeholder Song until Phase 3 implementation.
        """
        return Song(
            song_id=song_index,
            driver_family="konami_pre_vrc",
            provenance=None,  # will be filled by pipeline
        )
