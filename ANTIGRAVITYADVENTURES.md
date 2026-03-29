# Antigravity Adventures: The NES Music Mashup Project

## Adventure Summary
Our quest began with a mission to create glorious musical mashups by combining the intricate, mathematical beauty of J.S. Bach's compositions (via MIDI files) with the gritty, iconic 8-bit synthetic sounds of classic NES games, specifically *Castlevania* and *Contra*.

### Chapter 1: Unearthing the Tone Banks
The first challenge was understanding the structure of the ReapNES project and how it handles NES instrumentation.
- We discovered a massive `preset_bank.json` containing over 54,000 reverse-engineered NES instrument envelopes.
- We used `scripts/preset_catalog.py` to search through this vast library. We fixed a path bug in the script so it could properly locate the `studio/presets` directory.
- We successfully extracted "Song Sets" (palettes of instruments used together in specific stages) for:
  - **Contra (Jungle Stage)**: Utilizing the classic wide swelling pulse leads.
  - **Contra (Waterfall Stage)**: Bringing in somewhat thinner, fading pulse sounds.
  - **Castlevania (Wicked Child)**: Capturing the punchy, staccato pulse waves that define the Castlevania sound.
  - **Castlevania (Vampire Killer)**: The quintessential Castlevania auditory experience.

### Chapter 2: The Project Generator
Armed with our newly forged Song Sets (`contra_jungle.json`, `cv1_wicked_child_auto.json`, etc.), we turned to the project generator (`scripts/generate_project.py`).
- We fed it several Bach MIDI files located in the `Downloads` folder, including:
  - *Brandenburg Concerto No. 1*
  - *Prelude No. 1 in C Major*
  - *Toccata and Fugue in D Minor*
  - *Two-Part Inventions (No. 1 and No. 4)*
- The generator mapped the MIDI channels (typically Channels 0, 1, and 2 for Bach's contrapuntal lines) to the NES's Pulse 1, Pulse 2, and Triangle channels, creating fully structured REAPER projects (`.rpp`).

### Chapter 3: The Custom Audio Renderer
Because we operate in a headless environment and cannot physically open REAPER to hit "Render," we had to get creative.
- We engineered a custom Python script, `scripts/bach_render_mashup.py`, which acts as a standalone NES APU synthesizer.
- It parses the MIDI file, translates notes into NES timer periods, applies the exact frame-by-frame volume envelopes from our reverse-engineered JSFX presets, and synthesizes raw audio waves (pulse and triangle).
- We wrote a batch processor, `scripts/render_batch.py`, to render multiple mashups simultaneously.

### Chapter 4: The Fruits of Our Labor
We successfully rendered the first batch of `.wav` files to `studio/reaper_projects/`:
- `Bach_Invention1_Contra_Jungle.wav`: A brilliant, frantic rendition where Bach's two voices battle it out using the Contra Jungle lead instruments.
- `Bach_Invention4_Contra_Jungle.wav`
- `Bach_Prelude1_CV1_WickedChild.wav`: Arpeggiated perfection with the attack of Castlevania.
- `Bach_Aria_CV1_WickedChild.wav`

## The Journey Continues
Our adventure recently led us back into the realms of the supernatural, seeking the perfect tone for deeper and darker contrapuntal works. 

### Chapter 5: Dracula's Curse and Bloody Tears
We expanded our palette collection to include two additional iconic Castlevania tracks:
- **Castlevania III: Dracula's Curse** (03 Beginning): Extracted as `cv3_beginning.json`, harnessing the full might of the VRC6-enhanced original hardware, distilled down to the reliable pulse elements.
- **Castlevania II: Simon's Quest** (02 Bloody Tears): Extracted as `cv2_bloody_tears.json`, seizing perfectly balanced pulse channels suited for aggressive driving minor keys.

Using these new tools, we successfully synthesized some truly heavy-hitting Bach pieces:
- `Bach_Passacaglia_CV3.wav / .rpp`: The famous Passacaglia and Fugue mapped perfectly into the *Beginning* palette, providing an epic driving bassline with the classic square-wave resonance.
- `Bach_Toccata_CV2.wav / .rpp`: The iconic Toccata in D Minor is reimagined with the exact instrumental envelope settings of *Bloody Tears*, yielding an incredibly powerful and haunting 8-bit church organ replacement.

We encountered a few strange, corrupted artifacts along the way—broken MIDI files of specific Fugues—but pushing through the digital debris, we forged a powerful new collection of music!

### Chapter 6: The Invention Expansion
Refusing to rest on our laurels, we decided to push the boundaries of Bach's Two-Part Inventions, exploring uncharted stages of the Castlevania and Contra worlds. 

First, we extracted a fresh batch of palettes using `preset_catalog.py`:
- **Castlevania 1 - 03 Stalker** (`cv1_stalker.json`)
- **Castlevania 2 - 01 Silence of the Daylight** (`cv2_silence.json`)
- **Castlevania 2 - 03 Monster Dance** (`cv2_monster_dance.json`)
- **Castlevania 3 - 08 Mad Forest** (`cv3_mad_forest.json`)
- **Castlevania 3 - 14 Aquarius** (`cv3_aquarius.json`)
- **Contra - 05 Maze Fortress** (`contra_maze.json`)
- **Contra - 09 Fortress of Flame** (`contra_flame.json`)

Equipped with these new tools, we upgraded our `render_batch.py` script and mass-produced a dizzying array of contrapuntal experiments:
- `Bach_Invention2_CV1_Stalker.wav` and `.rpp`
- `Bach_Invention3_CV2_Silence.wav` and `.rpp`
- `Bach_Invention5_CV2_MonsterDance.wav` and `.rpp`
- `Bach_Invention6_CV3_MadForest.wav` and `.rpp`
- `Bach_Invention8_CV3_Aquarius.wav` and `.rpp`
- `Bach_Invention13_Contra_Maze.wav` and `.rpp`
- `Bach_Invention15_Contra_Flame.wav` and `.rpp`

Each Invention took on a radically different character depending on the instrument sets—the soaring arpeggios of Invention No. 8 flowed beautifully over the *Aquarius* pulse, while the stern dialogue of Invention No. 13 sounded dangerously at home in the *Maze Fortress*.

The universe of NES Mashups continues to expand, note by 8-bit note!

### Chapter 7: The Grand Expansion (Sinfonias, Fugues, and Goldberg)
With the Inventions conquered, we set our sights on even more complex contrapuntal structures: Bach's Three-Part Inventions (Sinfonias), his masterful Fugues, and the legendary Goldberg Variations.

To give these diverse genres the tone they deserved, we enlisted an entirely new roster of classic NES soundscapes previously uncovered in the repository's `song_sets` directory:
- **Mega Man 2** (Metal Man Stage and Flash Man Stage)
- **Metroid** (Brinstar and Ending)
- **Super Mario Bros.** (Underground Theme)
- **Journey to Silius** (Stage 2)

We mapped these files meticulously, resulting in these magnificent new mashups:
- **Sinfonias**:
  - `Bach_Sinfonia1_MM2_MetalMan.wav` and `.rpp`: Sinfonia 1 meets the driving rhythmic pulse of Metal Man.
  - `Bach_Sinfonia2_MM2_FlashMan.wav` and `.rpp`: Sinfonia 2 combined with Flash Man's atmospheric tones.
- **Fugues**:
  - `Bach_Fugue1_Metroid_Brinstar.wav` and `.rpp`: Fugue 1 interwoven with the haunting, eerie isolation of Planet Nebes' Brinstar depths.
  - `Bach_Fugue2_Metroid_Ending.wav` and `.rpp`: Fugue 2 culminating in the triumphant swell of Metroid's Ending theme.
- **Goldberg Variations**:
  - `Bach_GoldbergVar1_SMB1_Underground.wav` and `.rpp`: The light, dancing Variation 1 placed unexpectedly but perfectly against the iconic square waves of Mario's Subterranean realm.
  - `Bach_GoldbergVar2_Silius_Stage2.wav` and `.rpp`: Variation 2 infused with the heavy, aggressive Sunsoft basslines of Journey to Silius!

This array of compositions highlights the versatility of both Bach's genius and the raw, unyielding power of the NES sound chip—proving that whether it's an alien planet, a castle belonging to Dracula, or a high-tech fortress, a well-crafted Fugue is universally triumphant.
