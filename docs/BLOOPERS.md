# ReapNES Studio Blooper Reel

A chronicle of every format trap, silent failure, and misguided assumption
that stood between "I wrote a synth" and "I can hear a synth."

---

## Act I: The Plugin That Would Not Speak

### Blunder 1: `//tags:instrument` (comment, not a tag)
JSFX uses `tags:` as a metadata directive. Writing `//tags:instrument` makes it a
comment. REAPER silently ignores it, doesn't classify the plugin as an instrument,
and won't route MIDI to it. No error. No warning. Just silence.

**Fix:** `tags:instrument synthesizer` (no `//` prefix)

### Blunder 2: Missing `in_pin:none`
Without `in_pin:none`, REAPER treats the plugin as an audio effect, not a synth.
It won't generate audio from MIDI. Again: no error, no warning, just silence.

**Fix:** Every instrument JSFX needs:
```
in_pin:none
out_pin:Left
out_pin:Right
```

### Blunder 3: Unicode characters in JSFX
Using Unicode arrows and special characters in comments or string literals causes
silent compilation failure. The plugin loads, shows up in the FX list, but produces
no audio. REAPER's JSFX compiler doesn't support Unicode.

**Fix:** ASCII only. Use `->` not `→`, use `--` not `—`.

### Blunder 4: REAPER's compiled JSFX cache
After fixing the above bugs, the plugin STILL didn't work because REAPER cached
the old broken compiled version. Updating the file on disk wasn't enough. Even
deleting the `reaper-jsfx.ini` cache didn't help. The only reliable fix was to
rename the file to something REAPER had never seen before, forcing a fresh compile.

**Fix:** Renamed `ReapNES_Full.jsfx` to `ReapNES_APU.jsfx`. Sound appeared instantly.

---

## Act II: The RPP Format Gauntlet

### Blunder 5: `MASTER_SEND` and `REC_INPUT` tokens
Our first RPP files used tokens that REAPER v7.27 didn't recognize. REAPER showed
a "Project tokens not recognized" warning but loaded the project anyway, silently
ignoring the unrecognized settings.

**Fix:** Removed `MASTER_SEND`, used `MAINSEND 1 0` instead. Used `REC` with
the correct 8-field format.

### Blunder 6: The REC field MIDI input saga
Spent multiple iterations trying to auto-configure MIDI input via the REC field.

- `REC 1 6112 1` — too few fields, REAPER v7.27 ignored it
- `REC 1 6112 1 0 0 0 0` — 7 fields, still ignored
- `REC 1 6112 1 0 0 0 0 0` — 8 fields, still ignored
- `REC 1 5088 1 0 0 0 0 0` — tried different device encoding, still ignored

REAPER shows "MIDI (not connec..." on every track. The user had to manually set
MIDI input to "All: All Channels" every single time. After 6+ requests to fix this,
it turned out that the only way to get reliable MIDI input is to save a track template
FROM REAPER with the correct settings, then read it back to discover the format.

Eventually discovered that REAPER v7.27 track templates use a completely different
REC encoding than documented in any available reference.

**Status:** Partially resolved. The current format works on some REAPER versions
but the user may still need to set MIDI input manually on first open.

### Blunder 7: `SOURCE MIDI` inline format vs `SOURCE MIDI FILE`
First attempt: `SOURCE MIDIPOOL FILE "path.mid"` — REAPER showed the notes
visually but produced no audio.

Second attempt: `SOURCE MIDI` with inline `E` events — REAPER showed empty
items with no notes and no audio.

Third attempt: `SOURCE MIDI` with `FILE "path.mid"` — REAPER showed the notes
AND played audio. But only after fixing the DC offset bug (Blunder 8).

**Fix:** Use `SOURCE MIDI` with `FILE "absolute/path.mid"` referencing the
original MIDI file. REAPER handles the import.

---

## Act III: The Inaudible Audio

### Blunder 8: The DC offset that ate the music
The non-linear NES mixer formula produced a constant -0.784 DC offset when no
notes were playing. The meter showed -2.1 dB on all tracks even when stopped.
When notes DID play, the signal changed from -0.784 to about -0.45 — a valid
audio swing, but buried under a massive DC component.

The meter showed constant activity, so it LOOKED like the plugin was working,
but the sound was either inaudible or deeply distorted.

**Fix:** Replaced the non-linear mixer with a simple centered mix:
```
mix += (p1_out / 15.0 - 0.5) * 0.5;
```
This produces a clean bipolar signal centered at zero.

### Blunder 9: `^` is POWER, not XOR, in JSFX
The LFSR noise generator used `(lfsr & 1) ^ ((lfsr >> 1) & 1)` to compute
the feedback bit. In C, `^` is XOR. In JSFX, `^` is POWER (exponentiation).

`0 ^ 0 = 1` (power) vs `0 ^ 0 = 0` (XOR) — completely different behavior.
This produced incorrect noise patterns but didn't crash.

**Fix:** Used `((a + b) & 1)` as a single-bit XOR equivalent.

---

## Act IV: The MIDI Channel Catastrophe

### Blunder 10: Every track plays every channel
The biggest architectural bug. Each track in a multi-track project loaded the same
MIDI file and the same Full APU plugin. Each plugin instance received ALL MIDI
channels from the file and processed ALL FOUR oscillators. With 4 tracks, this
meant the music played 4 times simultaneously with slight variations.

Result: thick, muddy, noisy sound with tones cutting in and out. Some tracks
sounded like they had a broken chorus effect. Others were just distorted.

**Fix:** Added a "Channel Mode" slider (0=P1 Only, 1=P2 Only, 2=Tri Only,
3=Noise Only, 4=Full APU). Each track in a generated project now has its plugin
set to its own channel mode, so Track 1 only runs the Pulse 1 oscillator, Track 2
only runs Pulse 2, etc.

### Blunder 11: VGMusic MIDIs use random channel numbers
Our plugin expected channels 0, 1, 2, 3 (NES standard). But community MIDI
transcriptions use whatever channels they feel like:

- Mega Man 2 Air Man: channels 1, 3, 4 (not 0, 1, 2)
- Castlevania 3 Stage 2: channels 0, 1, 11
- Various games: drums on GM channel 9 (standard) but sometimes on other channels

Result: tracks mapped to the wrong oscillators or not mapped at all.

**Fix:** Added channel remapping in the project generator. Analyzes the MIDI,
identifies which channels have notes, sorts by pitch/role, and creates a remapped
copy with channels reassigned to 0-3.

### Blunder 12: Drums had no envelope
The original noise channel handler just turned noise on at a fixed period when
receiving a note, and turned it off on note-off. Real NES drums need a sharp
attack and fast decay — the noise should punch and fade, not drone.

With GM drum MIDIs, many drum notes have very short durations, so the noise
would pop on and off rapidly, creating clicking artifacts instead of drum sounds.

**Fix:** Added a drum mapping table that maps GM drum notes (35-57) to specific
NES noise parameters (period, mode, volume, decay rate). Each drum hit now
triggers a self-decaying envelope that simulates a real NES drum.

---

## Act V: The Bad MIDI Files

### Blunder 13: Fan transcriptions are not NES rips
VGMusic.com MIDIs are community-made transcriptions, not data extracted from game
ROMs. Quality varies wildly:

- Some have 10+ channels crammed into a file (real NES has 5)
- Some have all melodic parts in the same register (no bass/treble separation)
- Some are "arrangements" with band instruments, not NES voices
- Beethoven's "Fur Elise" turned out to be a multi-instrument arrangement
  with an "Electric Bass" track, not a piano reduction
- Bach's Goldberg Variations had multiple versions: one 2-channel (worked great),
  one 8-channel with drums (sounded terrible)

**Fix:** Analyzed all 71 MIDI files for channel count, register separation, and
drum usage. Rated them PERFECT/GOOD/OK/BAD. Only generated projects for the
PERFECT and GOOD files. The real long-term fix is NSF extraction from actual ROMs.

### Blunder 14: Classical music needs 2-3 voices to work on NES
Orchestral pieces with 6+ voices sound terrible through 4 NES channels. The only
classical pieces that worked well were naturally 2-3 voice pieces:

- Bach Two-Part Inventions (2 voices) — perfect NES fit
- Bach Goldberg Variations (2 voices) — beautiful through pulse channels
- Mozart Symphony 40 (3 voices in this transcription) — surprisingly good

Full orchestral arrangements of Beethoven symphonies, Moonlight Sonata, etc. were
hopeless. The lesson: NES is a 4-channel instrument. Feed it 4-channel music.

---

## Lessons Learned

1. **Test the simplest possible case first.** A 30-line beep synth would have
   caught most plugin bugs in 5 minutes instead of 5 hours.

2. **REAPER fails silently.** Missing tags, wrong pin config, bad JSFX syntax,
   unrecognized RPP tokens — REAPER quietly does nothing. No error log, no
   red warning, just silence.

3. **The RPP format is tribal knowledge.** There is no official RPP specification.
   The only reliable way to learn the format is to create something in REAPER's
   UI, save it, and read the file.

4. **Cache invalidation is the hardest problem.** REAPER caches compiled JSFX
   aggressively. Renaming the file is the nuclear option that always works.

5. **Community MIDI files are unreliable.** For NES music, the only trustworthy
   source is extraction from actual game data (NSF/ROM).

6. **Multi-instance architecture matters.** When 4 tracks each run a full
   4-channel synth, you get 16 channels of mush. Each track should run only
   its own oscillator.

7. **DC offset is invisible murder.** The meters show signal, the waveform
   looks active, but nothing is audible. Always center your output around zero.
