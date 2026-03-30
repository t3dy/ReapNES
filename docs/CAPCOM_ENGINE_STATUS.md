# Capcom Engine Status: What We Know and Don't Know

## The Three Capcom NES Engines

From community research, Capcom used three distinct sound engines:

### Engine 1 (1985-1986)
- **Games:** Commando, Trojan
- **Documentation:** [Capcom Sound Engine 1 Format](https://www.romhacking.net/documents/875/) (downloadable PDF on romhacking.net)
- **Status:** NOT downloaded yet. Need user to grab from romhacking.net.

### Engine 2 / "Old Engine" (1987-1988)
- **Games:** Mega Man 1, Mega Man 2, Bionic Commando, others
- **Documentation:** NONE FOUND. This is the gap.
- **Status:** Bionic Commando uses this engine. We found the song table
  and period table but can't decode the note data.

### Engine 3 / "6C80" (1990+)
- **Games:** Mega Man 3-6, DuckTales, Chip 'n Dale, Mighty Final Fight
- **Documentation:** [6C80 format docs](https://www.romhacking.net/documents/274/) + [Super Famicom wiki](https://wiki.superfamicom.org/capcom-music-format)
- **Status:** Format documented. Notes = upper 3 bits duration + lower
  5 bits pitch. Commands = $00-$1F. NOT yet validated on any ROM.

## What Went Wrong

1. We assumed Bionic Commando (1988) used the 6C80 engine (1990+).
   It doesn't. The byte patterns don't match.

2. We applied the documented format without validating against the
   trace first. The `/nes-validate` gate we designed specifically
   to prevent this was bypassed.

3. We launched a 3-game swarm before confirming the format worked
   on even one track. All three agents failed (no Bash access).

4. We kept launching agents for Bash-requiring tasks despite
   knowing agents can't access Bash.

## What To Do Next

### Option A: Download the docs
User downloads the two romhacking.net PDFs:
- https://www.romhacking.net/documents/274/ (6C80 engine)
- https://www.romhacking.net/documents/875/ (Engine 1)

Read both. Determine which engine Bionic Commando actually uses.
Apply the correct format. Validate against trace.

### Option B: Trace-based only
Accept that Bionic Commando ROM parsing needs more research.
Use trace captures for Bionic Commando (works perfectly).
Focus Capcom ROM parsing on Mega Man 3+ where 6C80 is confirmed,
but validate ONE TRACK against nesmdb or a trace before batch.

### Option C: Trace-first for Mega Man 3
Capture a Mega Man 3 trace in Mesen. Use it to validate the
6C80 parser. If validation passes, THEN extract all tracks.
If it fails, we know the 6C80 docs need adjustment too.

## Lessons (Again)

- **Validate before batch.** We built the gate, then ignored it.
- **One game at a time.** Don't swarm until one game works.
- **Agents can't Bash.** Stop trying. Do it directly.
- **Research beats guessing.** The 6C80 docs were a breakthrough
  but we applied them to the wrong game.
- **The trace is always right.** Compare to trace FIRST.
