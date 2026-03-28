# WHATELSEWETRIED.md -- Full Troubleshooting Log

## The Core Problem
ReapNES_Full.jsfx does not produce sound when loaded via RPP project file, even though:
- MIDI input is connected (meter shows activity from keyboard)
- Track is armed and monitoring is on
- ReapNES_Simple.jsfx (a minimal version) DOES produce sound from the same RPP format

## Attempt 1: Pin Declarations
**Theory:** REAPER treats JSFX without `in_pin:none` as audio effects, not instruments.
**Fix:** Added `in_pin:none`, `out_pin:Left`, `out_pin:Right` to all plugins.
**Result:** ReapNES_Test.jsfx (minimal beep) started working when added manually via FX browser. ReapNES_Full still silent.

## Attempt 2: Tags Directive
**Theory:** `//tags:` was a comment. REAPER never saw the `instrument` tag.
**Fix:** Changed `//tags:synthesizer...` to `tags:instrument synthesizer...`
**Result:** No change. Plugin still silent.

## Attempt 3: Slider Gap Fix
**Theory:** slider20 (Master Gain) with gap from slider15 caused RPP parameter misalignment.
**Fix:** Renumbered slider20 to slider16, then slider16 to slider12. Made all sliders sequential.
**Result:** No change.

## Attempt 4: Unicode Removal
**Theory:** Em dashes and arrows in JSFX comments might break compilation on Windows cp1252.
**Fix:** Replaced all unicode (em dashes, arrows, approximately signs) with ASCII equivalents in all .jsfx and .jsfx-inc files.
**Result:** No change. (But this was a real issue -- the library files had 72 lines of unicode.)

## Attempt 5: Remove Library Imports
**Theory:** The imported library files (apu_core.jsfx-inc, etc.) had compilation errors.
**Fix:** Rewrote ReapNES_Full.jsfx as a fully self-contained file with no `import` statements. All synthesis code inline.
**Result:** SUCCESS -- the plugin produced sound once. But then stopped working on subsequent project loads.

## Attempt 6: JSFX Cache Update
**Theory:** REAPER's `reaper-jsfx.ini` cache still had old plugin names/tags with unicode.
**Fix:** Manually edited reaper-jsfx.ini to update NAME, REV, and TAGS entries.
**Result:** After REAPER restart, the plugin worked once. Then stopped again on next project load.

## Attempt 7: REC Field Fix (7 vs 8 values)
**Theory:** REC field had 7 values, working projects had 8.
**Fix:** Added 8th field: `REC 1 6112 1 0 0 0 0 0`
**Result:** No effect on sound. Also did not fix MIDI input auto-configuration.

## Attempt 8: MIDI Input Value (6112 vs 5088)
**Theory:** Device index 63 ("all inputs" per docs) was wrong for this system.
**Fix:** Saved a track template from REAPER to discover the real value. Found `REC 1 5088 1 0 0 0 0 0` (device 31, not 63).
**Result:** SUCCESS for MIDI input -- tracks now auto-configure to "MIDI: All: All chan". But still no sound from Full plugin.

## Attempt 9: Fresh Filename (pending)
**Theory:** REAPER has a compiled JSFX cache separate from reaper-jsfx.ini. The old broken version of ReapNES_Full is still being used despite the file being overwritten.
**Fix:** Copied the working self-contained code to a new filename `ReapNES_APU.jsfx` that REAPER has never seen. Generated RPP referencing this new name.
**Result:** Pending test.

## What We Know For Sure

| Fact | Evidence |
|------|----------|
| ReapNES_Simple.jsfx produces sound | Confirmed in test_simple.rpp |
| ReapNES_Test.jsfx produces sound | Confirmed when added via FX browser |
| ReapNES_Full.jsfx produced sound ONCE | Screenshot showing all 4 meters active |
| ReapNES_Full.jsfx stopped working after RPP regeneration | Multiple subsequent tests show silence |
| MIDI input reaches the plugin | Track meters show activity from keyboard |
| Audio output works | Master meter shows signal when Simple plays |
| RPP format is correct | Simple plugin loads and plays from RPP |
| MIDI input auto-config works with 5088 | Tracks show "MIDI: All: All chan" |
| Library imports caused compilation failures | Self-contained version worked, import version didn't |
| REAPER JSFX cache is sticky | Old plugin descriptions persisted after file overwrites |

## Remaining Theories

1. **REAPER compiled cache is separate from reaper-jsfx.ini.** The .ini file is just a name index. REAPER may cache compiled JSFX bytecode elsewhere and reuse it even when the source file changes. A new filename (ReapNES_APU.jsfx) would bypass this.

2. **The Full plugin code has a subtle JSFX syntax error.** Even though it's self-contained and looks correct, JSFX may have a silent parsing failure on some construct (e.g., ternary without parentheses, `>>` operator in certain contexts, or `^` being power not XOR).

3. **The RPP slider values are being applied incorrectly** and setting Master Gain to 0 or some channel enable to 0.

## Potential Bug: `^` is Power, Not XOR
In JSFX, the `^` operator is **exponentiation** (power), NOT bitwise XOR like in C. The noise channel LFSR code uses:
```
fb = (lfsr & 1) ^ ((lfsr >> 6) & 1)
```
This computes `0^0 = 1, 0^1 = 0, 1^0 = 1, 1^1 = 1` (power) instead of XOR. This is a BUG in the noise channel but should not prevent pulse/triangle from producing sound since they don't use XOR.

The fix for XOR in JSFX would be: `fb = ((lfsr & 1) + ((lfsr >> 6) & 1)) & 1` (addition mod 2 = XOR for single bits).

## What Should Be Tried Next

1. Test `test_newname.rpp` which uses `ReapNES_APU.jsfx` (fresh filename, no cache)
2. If still silent: open the FX window in REAPER, check if the plugin shows an error
3. If no error visible: compare the output of Simple vs Full by adding both to the same track
4. If Full produces 0 output: the formula `(mixed - 0.35) * slider12 * 2.8` might be producing near-zero when only one channel is active
5. Nuclear option: replace ReapNES_Full.jsfx with an exact copy of ReapNES_Simple.jsfx but with the Full's filename and slider names
