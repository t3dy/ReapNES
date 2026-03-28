# FIRSTEXPERIMENT.md -- Bach Through Castlevania

## The Concept

Map Bach keyboard works onto NES Castlevania instrument palettes. The Castlevania series has some of the most baroque-influenced music on the NES -- its composers (Kinuyo Yamashita, Kenichi Matsubara, the Konami Kukeiha Club) drew heavily from classical harmony and counterpoint. Bach's contrapuntal keyboard works are a natural fit.

## The Matchups

### 1. Bach Invention No. 1 in C Major (BWV 772) x Castlevania 1

**Why this pairing:** The two-part invention is clean, bright counterpoint between two voices -- perfect for the two pulse channels of the NES. Castlevania 1's "Vampire Killer" stage music has a similarly bright, driving energy in a major-adjacent mode. The C major invention's clarity maps naturally to CV1's clean pulse-heavy sound.

**Mapping:**
- Track 1 (right hand, higher voice) -> **Pulse 1** (50% duty, bright lead)
- Track 2 (left hand, lower voice) -> **Pulse 2** (25% duty, slightly thinner harmony)
- No triangle needed (two-voice invention)
- No noise (no percussion in the original)

**File:** `midi/classical/bach/invention_1_c.mid` (158s, 2 voices)

### 2. Bach Invention No. 8 in F Major (BWV 779) x Castlevania 3

**Why this pairing:** The F major invention has a more ornate, flowing quality with wider leaps and faster passagework. Castlevania 3's "Beginning" is the most technically ambitious Castlevania track, with fast arpeggios and dramatic harmonic motion. CV3's sound palette is broader and more aggressive than CV1.

**Mapping:**
- Track 1 (soprano voice, fast runs) -> **Pulse 1** (25% duty, sharper attack for fast passages)
- Track 2 (bass voice, counterpoint) -> **Pulse 2** (50% duty, warmer for the bass line)
- Triangle silent (no bass register needed for a two-part invention)
- Noise silent

**File:** `midi/classical/bach/invention_8_f.mid` (323s, 2 voices)

### 3. Bach Toccata and Fugue in D Minor (BWV 565) x Castlevania 2: Simon's Quest

**Why this pairing:** The Toccata and Fugue is THE iconic dark-baroque organ work -- dramatic, brooding, with that famous descending opening. Simon's Quest's "Bloody Tears" and "Dwelling of Doom" share the same gothic minor-key intensity. The D minor tonality perfectly matches CV2's darker, more atmospheric sound world.

**Mapping:**
- Track 1 (main keyboard part, 1807 notes) -> **Pulse 1** (50% duty, full organ-like sound)
- Track 2 (bass/pedal, 496 notes) -> **Triangle** (deep bass, the organ pedals map perfectly to triangle's warm low register)
- Pulse 2 silent (the original is essentially two-voice with pedal)
- Noise silent

**File:** `midi/classical/bach/toccata_fugue_dmin.mid` (284s, 2 voices)

### 4. Bach WTC Book 1 Prelude No. 1 in C Major (BWV 846) x Castlevania 1

**Why this pairing:** The famous broken-chord prelude is meditative and flowing -- every classical musician knows it. Against Castlevania 1's more restrained palette, the arpeggiated figures will ring out clearly through the NES pulse channels. This is also a good test of how NES monophony handles Bach's implied polyphony.

**Mapping:**
- Track 1 (upper arpeggios) -> **Pulse 1** (50% duty)
- Track 2 (bass notes) -> **Triangle** (sustained bass)
- Track 5 (middle voice if present) -> **Pulse 2** (25% duty)
- Track 4 (percussion) -> **Noise** (if present in MIDI arrangement)

**File:** `midi/classical/bach/wtc1_prelude1_c.mid` (327s, 6 tracks)

### 5. Bach WTC Book 1 Fugue No. 1 in C Major (BWV 846) x Castlevania 3

**Why this pairing:** The 4-voice fugue is the ultimate test of NES polyphony -- each voice enters independently and maintains its own melodic identity. Castlevania 3 is the only CV game with the musical complexity to support this. Four voices map to four NES channels: two pulse voices for the upper parts, triangle for the tenor, and the bass will double with the triangle.

**Mapping:**
- Track with highest avg pitch -> **Pulse 1** (soprano, 50% duty)
- Second highest -> **Pulse 2** (alto, 25% duty)
- Third -> **Triangle** (tenor/bass)
- Any remaining -> doubled or dropped

**File:** `midi/classical/bach/wtc1_fugue1_c.mid` (245s, multi-voice)

### 6. Bach Goldberg Variations Aria (BWV 988) x Castlevania 2: Simon's Quest

**Why this pairing:** The Aria is gentle, stately, in G major -- a sarabande. Simon's Quest has the most atmospheric, contemplative moments of the trilogy ("Silence of Daylight" in the town sections). The Goldberg Aria's slow grace maps beautifully to CV2's more restrained timbres.

**Mapping:**
- Melody track -> **Pulse 1** (50% duty, singing quality)
- Piano/accompaniment -> **Pulse 2** (25% duty)
- Bass -> **Triangle**
- Drums -> **Noise** (if present in this MIDI arrangement)

**File:** `midi/classical/bach/goldberg_aria.mid` (159s, 8 tracks)

## Design Principles

1. **Higher voices -> Pulse channels** (more expressive, duty cycle variety)
2. **Bass -> Triangle** (warm, round tone, no volume control = constant presence, perfect for organ pedals and bass lines)
3. **Faster passages -> 25% duty** (sharper, cuts through better at speed)
4. **Sustained melodies -> 50% duty** (fuller, more singing tone)
5. **No noise unless the MIDI has percussion** (Bach keyboard works don't)
6. **Castlevania 1 = cleaner, brighter** (simpler arrangements)
7. **Castlevania 2 = darker, more atmospheric** (minor keys, slower pieces)
8. **Castlevania 3 = most complex, aggressive** (fugues, fast counterpoint)

## Technical Notes

- The NES is monophonic per channel. Bach's keyboard writing sometimes implies polyphony within a single voice (held notes while other notes move). The NES will play only the most recent note per channel, so some sustain will be lost. This is a feature, not a bug -- it creates a distinctive NES articulation.
- Triangle has no volume control. It's always on or off. This means bass notes will have uniform dynamics -- appropriate for organ-pedal-like bass lines.
- Pitch range: NES pulse covers roughly C2-B7. Bach keyboard music generally stays within C2-C6, so range is not an issue.
