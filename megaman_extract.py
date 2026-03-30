
import csv, math, wave, os
import numpy as np
import mido

SAMPLE_RATE = 44100
SPF = SAMPLE_RATE // 60
TICKS_PER_FRAME = 16

param_map = {
    "$4002_period": ("pulse1", "period"), "$4000_vol": ("pulse1", "vol"), "$4000_duty": ("pulse1", "duty"),
    "$4006_period": ("pulse2", "period"), "$4004_vol": ("pulse2", "vol"), "$4004_duty": ("pulse2", "duty"),
    "$400A_period": ("triangle", "period"), "$4008_linear": ("triangle", "linear"),
    "$400E_period": ("noise", "period"), "$400C_vol": ("noise", "vol"), "$400E_mode": ("noise", "mode"),
}

def p2m(p, tri=False):
    if p <= (2 if tri else 8): return 0
    div = 32 if tri else 16
    freq = 1789773 / (div * (p + 1))
    return 69 + 12 * math.log2(freq / 440)

def load_trace(path):
    st = {"pulse1":{"period":0,"vol":0,"duty":1},"pulse2":{"period":0,"vol":0,"duty":1},
          "triangle":{"period":0,"linear":0},"noise":{"period":0,"vol":0,"mode":0}}
    mf = 0; fe = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            frame = int(row["frame"]); param = row["parameter"]; val = int(row["value"])
            mf = max(mf, frame)
            if param in param_map:
                ch, field = param_map[param]
                fe.setdefault(frame, []).append((ch, field, val))
    full = {}
    for frame in range(mf+1):
        if frame in fe:
            for ch, field, val in fe[frame]: st[ch][field] = val
        full[frame] = {ch: dict(s) for ch, s in st.items()}
    return full, mf

def render_and_midi(full, mf, start_f, end_f, wav_path, midi_path, sfx_filter=True):
    n_frames = end_f - start_f
    music = np.zeros(n_frames * SPF, dtype=np.float64)
    ph = {"pulse1":0.0,"pulse2":0.0,"triangle":0.0}
    lfsr = 1
    
    # SFX detection
    sfx = set()
    if sfx_filter:
        prev = 0
        for f in range(start_f, end_f):
            p = full[f]["pulse1"]["period"]; v = full[f]["pulse1"]["vol"]
            if p > 0 and v > 0:
                m = p2m(p)
                if m > 88 or p < 50:
                    for j in range(max(start_f,f-1), min(end_f,f+10)): sfx.add(j)
                elif prev > 0 and abs(m-prev) > 16:
                    for j in range(max(start_f,f-1), min(end_f,f+8)): sfx.add(j)
                prev = m
    
    for frame in range(start_f, end_f):
        idx = frame - start_f
        s = idx*SPF; e = s+SPF
        fs = full[frame]
        for ch in ["pulse1","pulse2"]:
            p,v,d = fs[ch]["period"],fs[ch]["vol"],fs[ch]["duty"]
            if p>=8 and v>0:
                if ch=="pulse1" and frame in sfx: continue
                freq=1789773/(16*(p+1)); dv=[.125,.25,.5,.75][min(d,3)]; a=v/15*.25
                pa=(np.arange(SPF)*freq/SAMPLE_RATE+ph[ch])%1.0
                music[s:e]+=np.where(pa<dv,a,-a); ph[ch]=(ph[ch]+SPF*freq/SAMPLE_RATE)%1.0
        p,lin = fs["triangle"]["period"],fs["triangle"]["linear"]
        if p>=2 and lin>0:
            freq=1789773/(32*(p+1)); a=.25
            pa=(np.arange(SPF)*freq/SAMPLE_RATE+ph["triangle"])%1.0
            music[s:e]+=np.where(pa<.5,a*(4*pa-1),a*(3-4*pa)); ph["triangle"]=(ph["triangle"]+SPF*freq/SAMPLE_RATE)%1.0
        nv = fs["noise"]["vol"]
        if nv > 0:
            rt=[4,8,16,32,64,96,128,160,202,254,380,508,762,1016,2034,4068]
            np_v=fs["noise"]["period"]; nm=fs["noise"]["mode"]
            nf=1789773/rt[min(np_v,15)]; na=nv/15*.12
            ns=np.zeros(SPF); nc=0.0; nstep=nf/SAMPLE_RATE
            for i in range(SPF):
                nc+=nstep
                while nc>=1:
                    fb=(lfsr&1)^((lfsr>>(1 if nm==0 else 6))&1)
                    lfsr=((lfsr>>1)|(fb<<14))&0x7FFF; nc-=1
                ns[i]=na if lfsr&1 else -na
            music[s:e]+=ns
    
    pk = np.max(np.abs(music))
    if pk > 0: music = music/pk*.9
    a16 = (music*32767).astype(np.int16)
    with wave.open(wav_path,"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE); wf.writeframes(a16.tobytes())
    
    # MIDI with CC11
    mid = mido.MidiFile(ticks_per_beat=480)
    for ch_idx, (ch_name, label, is_tri) in enumerate([
        ("pulse1","P1",False),("pulse2","P2",False),("triangle","Tri",True)]):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=label))
        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(150)))
        track.append(mido.Message("program_change", channel=ch_idx, program=80))
        prev_midi=0; prev_vol=-1; ticks=0
        for frame in range(start_f, end_f):
            fs=full[frame][ch_name]; p=fs["period"]
            v=fs.get("vol",0) if not is_tri else (8 if fs.get("linear",0)>0 else 0)
            midi=round(p2m(p,is_tri)) if p>(2 if is_tri else 8) and v>0 else 0
            if ch_name=="pulse1" and frame in sfx: midi=0
            if v!=prev_vol and midi>0:
                track.append(mido.Message("control_change",channel=ch_idx,control=11,value=min(127,v*8),time=ticks))
                ticks=0; prev_vol=v
            if midi!=prev_midi:
                if prev_midi>0: track.append(mido.Message("note_off",note=prev_midi,velocity=0,channel=ch_idx,time=ticks)); ticks=0
                if midi>0: track.append(mido.Message("note_on",note=midi,velocity=min(127,v*8),channel=ch_idx,time=ticks)); ticks=0
                prev_midi=midi
            ticks+=TICKS_PER_FRAME
        if prev_midi>0: track.append(mido.Message("note_off",note=prev_midi,velocity=0,channel=ch_idx,time=ticks))
        mid.tracks.append(track)
    mid.save(midi_path)
    return len(a16)/SAMPLE_RATE

os.makedirs("output/Mega_Man_1/wav/segments", exist_ok=True)
os.makedirs("output/Mega_Man_1/midi", exist_ok=True)

# Stage Select (trim leading silence)
print("Stage Select...")
full1, mf1 = load_trace("extraction/traces/mega_man_1/capture1_stage_select.csv")
# Find first frame with audio
first_sound = 0
for f in range(mf1+1):
    if full1[f]["pulse1"]["vol"] > 0 or full1[f]["pulse2"]["vol"] > 0:
        first_sound = max(0, f - 2)
        break
print(f"  First sound at frame {first_sound}")
d = render_and_midi(full1, mf1, first_sound, mf1+1,
    "output/Mega_Man_1/wav/mm1_stage_select_v2.wav",
    "output/Mega_Man_1/midi/mm1_stage_select_v1.mid", sfx_filter=False)
print(f"  WAV: {d:.1f}s")

# Cut Man
print("Cut Man...")
full2, mf2 = load_trace("extraction/traces/mega_man_1/capture1_cutman.csv")
d = render_and_midi(full2, mf2, 0, mf2+1,
    "output/Mega_Man_1/wav/mm1_cutman_v2.wav",
    "output/Mega_Man_1/midi/mm1_cutman_v1.mid")
print(f"  WAV: {d:.1f}s")

# Multi-capture: split into segments
print("Multi-capture segments...")
full3, mf3 = load_trace("extraction/traces/mega_man_1/capture3_select_to_gutman.csv")
segments = [
    (0, 162, "stage_select_end", False),
    (162, 216, "stage_pick_jingle", False),
    (216, 540, "ready_screen", False),
    (540, mf3+1, "gutsman_stage", True),
]
for sf, ef, name, sfx_f in segments:
    d = render_and_midi(full3, mf3, sf, ef,
        f"output/Mega_Man_1/wav/segments/mm1_{name}_v2.wav",
        f"output/Mega_Man_1/midi/mm1_{name}_v1.mid", sfx_filter=sfx_f)
    print(f"  {name}: {d:.1f}s")

print("
Done! All Mega Man 1 output:")
for d, _, files in os.walk("output/Mega_Man_1"):
    for fn in sorted(files):
        print(f"  {os.path.join(d, fn)}")
