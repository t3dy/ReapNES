# Studio Environment -- Claude Code Instructions

Read this file when working on studio/, scripts/, JSFX, RPP, or MIDI files.

---

## The 14 Blunder Prevention Rules

These are NOT suggestions. Every rule comes from a real bug that caused hours
of silent failure. See `docs/BLOOPERS.md` for the full horror story.

### JSFX Plugin Rules

1. **`tags:instrument` not `//tags:instrument`** -- The `//` makes it a comment. REAPER silently ignores it, won't route MIDI to the plugin. No error, no warning, just silence.

2. **`in_pin:none` is required** -- Without it, REAPER treats the plugin as an audio effect, not a synth. It won't generate audio from MIDI. No error, just silence.

3. **ASCII only in JSFX files** -- No unicode anywhere. No `->` arrows, no `--` dashes, no special characters. REAPER's JSFX compiler doesn't support unicode. The plugin loads, shows in FX list, but produces no audio.

4. **REAPER caches compiled JSFX** -- After fixing bugs, the plugin may STILL not work because REAPER cached the old broken version. Rename the file to force a fresh compile.

5. **`^` is POWER in JSFX, not XOR** -- `0 ^ 0 = 1` (power) vs `0 ^ 0 = 0` (XOR). Use `((a + b) & 1)` for single-bit XOR.

### RPP File Rules

6. **Use `MAINSEND 1 0` not `MASTER_SEND`** -- REAPER v7.27 doesn't recognize `MASTER_SEND`.

7. **Never use `REC_INPUT`, `RECINPUT`, or `RECMON` tokens** -- Unrecognized in REAPER v7.27.

8. **Use `SOURCE MIDI` with `FILE "path"` not `SOURCE MIDIPOOL`** -- `MIDIPOOL` shows notes visually but produces no audio.

### Audio Output Rules

9. **Output signal must be centered at zero** -- Use `(value / 15.0 - 0.5)` to center. Only mix active oscillators (check `en` flag before adding to mix).

10. **Only include active oscillators in the mix** -- Inactive oscillators at value 0 produce DC offset of -0.25 each.

### Channel Architecture Rules

11. **Channel mode must FILTER, never REMAP** -- Each track's plugin must skip non-matching MIDI channels, NOT redirect all channels to one.
    ```
    // WRONG: ch_mode == 0 ? ch = 0;  (remaps ALL channels to 0)
    // RIGHT: ch != ch_mode ? use_msg = 0;  (skips non-matching)
    ```

12. **MIDI channels must be remapped to 0-3 before project generation** -- Community MIDIs use random channel numbers. The project generator must analyze and remap.

### Drum and MIDI Rules

13. **Drum notes need self-decaying volume envelopes, not sustain** -- Real NES drums punch and fade. Without decay, noise pops on/off creating clicks.

14. **Community MIDI files are unreliable -- prefer ROM extraction** -- VGMusic transcriptions have random channels, wrong registers, too many voices.

---

## Blunder Prevention Checklist

```
[ ] JSFX has desc: on first line (plain ASCII)
[ ] JSFX has tags:instrument (NOT //tags:)
[ ] JSFX has in_pin:none
[ ] JSFX has out_pin:Left and out_pin:Right
[ ] JSFX is ASCII only (no unicode anywhere)
[ ] JSFX slider numbers are sequential (no gaps)
[ ] No ^ used for XOR (use ((a+b)&1) instead)
[ ] Output centered at zero (no DC offset)
[ ] Silence when no notes playing (spl0 = spl1 = 0)
[ ] Channel mode FILTERS, not REMAPS
[ ] Only active channels contribute to mix
[ ] Drum envelopes decay to zero (don't sustain)
[ ] RPP uses MAINSEND 1 0 (not MASTER_SEND)
[ ] RPP uses SOURCE MIDI with FILE reference
[ ] RPP has 64 space-separated slider values
[ ] MIDI channels are 0-3 (remapped if needed)
```

## JSFX Instruments MUST have:
```
desc:Plugin Name
tags:instrument synthesizer
in_pin:none
out_pin:Left
out_pin:Right
```

## RPP Files MUST:
- Use per-track channel mode: slider13 = 0/1/2/3 for P1/P2/Tri/Noise
- Never use Full APU mode (4) in multi-track projects
- Use `SOURCE MIDI` with `FILE` reference
- Have 64 space-separated slider values (dashes for unused)
- Have `BYPASS 0 0 0` before plugin block, `FLOATPOS`/`FXID`/`WAK` after
- Have GUIDs on tracks, items, FX instances

## MIDI Output Quality Rules

- Exactly 4 channels (0-3): Pulse1, Pulse2, Triangle, Noise
- Strictly monophonic per channel
- Minimum 6 semitone register separation between melodic channels
- Triangle channel velocity always 127 (no volume control)
- Noise channel uses GM drum note range 35-57
- Every note-on has matching note-off
- Tempo derived from driver, not guessed
- CC11 for mid-note volume changes, CC12 for duty cycle (nesmdb standard)
