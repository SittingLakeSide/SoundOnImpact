# 🥁 ImpactDrum — Mic Transient Edition

> Knock on your desk. Hit your laptop chassis. Clap. Hear drums.  
> No sensors needed — just your built-in microphone.

---

## Setup

```bash
# 1. Install (only 2 packages)
pip install -r requirements.txt

# 2. Optional: copy sample env and tune values
copy .env.example .env

# 3. Run with console — recommended first time, you'll see every hit logged live
python impact_drum.py

# 4. Run silently in the background (no terminal window)
pythonw impact_drum.py
```

> **Run on startup:** Create a shortcut to `pythonw C:\path\to\impact_drum.py`  
> and drop it in `shell:startup` (Win+R → type `shell:startup`)

---

## How the detector works

This is **not** a volume detector. It uses a **transient ratio detector** — the
same principle used in professional audio compressors:

```
short_rms (last ~6ms)  /  long_rms (last ~82ms)  >  RATIO_THRESHOLD
```

- `short_rms` measures the energy of the current spike
- `long_rms` tracks the ambient noise floor (room noise, fans, voice)
- Only a sudden physical impact produces a ratio this extreme

This means it **won't fire on**:
- Background music or TV
- Your voice or someone talking nearby
- Laptop fan noise
- Typing (unless you hit very hard)

It **will fire on**:
- Knocking on your desk
- Hitting the laptop chassis
- Clapping near the mic
- Stomping on the floor (if your mic picks it up)

---

## Drum mapping

| Impact strength | Ratio range | Sounds |
|---|---|---|
| Light | 7 – 12× | Hi-Hat · Open HH · Rimshot · Clap |
| Medium | 12 – 22× | Snare · Tom Hi · Tom Mid |
| Hard | 22×+ | Kick · Floor Tom · Crash |

Each tier rotates through its sounds independently — so you can build  
rhythm patterns by varying your hit strength.

---

## Tuning with `.env`

Open `.env` and adjust:

| Setting | Default | What it does |
|---|---|---|
| `IMPACT_RATIO_THRESHOLD` | `4.8` | **Main sensitivity knob.** Lower = more sensitive |
| `IMPACT_TIER_MEDIUM` | `9.0` | Ratio above which you get snare/tom instead of hat |
| `IMPACT_TIER_HARD` | `16.0` | Ratio above which you get kick instead of snare |
| `IMPACT_MIN_ENERGY` | `0.00045` | Minimum raw volume floor |
| `IMPACT_COOLDOWN_MS` | `120` | Min ms between hits |
| `IMPACT_MASTER_VOLUME` | `0.9` | Global output volume |
| `IMPACT_INPUT_DEVICE` | empty | Use specific input device index |
| `IMPACT_OUTPUT_DEVICE` | empty | Use specific output device index |
| `IMPACT_INPUT_CHANNELS` | `1` | Mono by default (more compatible) |

### Common problems

**False triggers (fires on its own):**  
→ Raise `IMPACT_RATIO_THRESHOLD` (try `8.0`, then `10.0`)  
→ Raise `IMPACT_MIN_ENERGY` (try `0.001`)

**Misses hits:**  
→ Lower `IMPACT_RATIO_THRESHOLD` (try `3.8`)  
→ Lower `IMPACT_MIN_ENERGY` (try `0.0002`)

**Double hits:**  
→ Raise `IMPACT_COOLDOWN_MS` (try `180`)

**Wrong mic being used:**  
→ Check the log at startup — it lists all input/output devices.  
→ Set `IMPACT_INPUT_DEVICE=2` (or your mic index) in `.env`.

---

## Custom sounds (`.wav`)

1. Put `.wav` files in the `sounds` folder (mono/stereo both OK).
2. Set any of these in `.env`:
   - `IMPACT_CUSTOM_LIGHT=hat.wav`
   - `IMPACT_CUSTOM_MEDIUM=snare.wav`
   - `IMPACT_CUSTOM_HARD=kick.wav`
3. Restart app.

If a custom file is missing/invalid, ImpactDrum automatically falls back to synthesized drums.

---

## Drum sounds (all synthesized — no audio files)

| Sound | Technique |
|---|---|
| Kick | Pitch-swept sine 175→28 Hz, tanh saturation |
| Snare | Detuned dual oscillator + bandpassed noise + crack transient |
| Hi-Hat (closed) | 6 inharmonic square partials + steep highpass noise |
| Hi-Hat (open) | Same as closed, longer sustain |
| Rimshot | Square-wave crack + hollow 375 Hz resonant body |
| Tom Hi/Mid/Lo | Pitch-swept sine at 118 / 90 / 68 Hz base |
| Crash | Inharmonic highpassed noise with 1.2s decay |
| Clap | 3 micro-delayed noise bursts (real clap flamming) |

---

## Logs

Written to: `%APPDATA%\ImpactDrum\impact_drum.log`

Each hit looks like:
```
10:42:17  HIT #  23  |  Snare     |  ratio=  15.4  |  vel=0.68
```

---

## Stopping

- Console mode: `Ctrl + C`
- Background mode (pythonw): Task Manager → `pythonw.exe` → End task
