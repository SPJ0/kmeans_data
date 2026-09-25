"""Audio engine: synthesized music, sound effects, TTS voices, mixing."""
import os, hashlib, json
import numpy as np
from scipy import signal
import soundfile as sf

SR = 48000
ASSETS = os.environ.get('PARROT_ASSETS', os.path.join(os.path.dirname(__file__), '..', 'assets'))
CACHE = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE, exist_ok=True)
rng = np.random.default_rng(7)


def t_arr(dur):
    return np.arange(int(dur * SR)) / SR


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.1, sus_len=None):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    if sus_len is None:
        sus_n = max(0, n - a_n - d_n - r_n)
    else:
        sus_n = int(sus_len * SR)
    e = np.concatenate([np.linspace(0, 1, a_n, endpoint=False), np.linspace(1, s, d_n, endpoint=False),
                        np.full(sus_n, s), np.linspace(s, 0, r_n)])
    if len(e) < n:
        e = np.concatenate([e, np.zeros(n - len(e))])
    return e[:n]


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), 'low')
    return signal.lfilter(b, a, x)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high')
    return signal.lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], 'band')
    return signal.lfilter(b, a, x)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def osc(kind, freq, dur, duty=0.5, phase_mod=None):
    t = t_arr(dur)
    if np.isscalar(freq):
        ph = freq * t
    else:
        ph = np.cumsum(freq) / SR
    ph = ph % 1.0
    if kind == 'sine':
        return np.sin(2 * np.pi * ph)
    if kind == 'square':
        return np.where(ph < duty, 1.0, -1.0)
    if kind == 'saw':
        return 2 * ph - 1
    if kind == 'tri':
        return 4 * np.abs(ph - 0.5) - 1
    raise ValueError(kind)


def add(buf, x, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    if buf.ndim == 2 and x.ndim == 1:
        buf[i:j] += gain * x[:j - i, None]
    else:
        buf[i:j] += gain * x[:j - i]


# ---------------------------------------------------------------- drums
def kick(dur=0.35):
    t = t_arr(dur)
    f = 45 + 110 * np.exp(-t * 35)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.3
    return np.tanh(1.6 * (x + click))


def snare(dur=0.22):
    t = t_arr(dur)
    n = bandpass(rng.standard_normal(len(t)), 1200, 9000) * np.exp(-t * 18)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return 0.8 * n + 0.5 * tone


def clap(dur=0.25):
    t = t_arr(dur)
    n = bandpass(rng.standard_normal(len(t)), 900, 5000)
    e = np.zeros_like(t)
    for off in (0, 0.011, 0.022):
        e += (t >= off) * np.exp(-np.clip(t - off, 0, None) * 60)
    e += (t >= 0.03) * np.exp(-np.clip(t - 0.03, 0, None) * 14) * 0.6
    return n * e


def hat(dur=0.05, open_=False):
    d = 0.3 if open_ else dur
    t = t_arr(d)
    n = highpass(rng.standard_normal(len(t)), 7000)
    return n * np.exp(-t * (9 if open_ else 70))


# ---------------------------------------------------------------- instruments
def pluck_chord(notes, dur, bright=3500):
    x = np.zeros(int(dur * SR))
    for m in notes:
        f = midi_hz(m)
        for det in (-0.12, 0.12):
            x += osc('saw', f * 2 ** (det / 12), dur)
    t = t_arr(dur)
    x = lowpass(x, bright) * np.exp(-t * 11)
    return x / len(notes) * 0.5


def bass_note(m, dur):
    f = midi_hz(m)
    x = 0.6 * osc('square', f, dur, 0.5) + 0.6 * osc('saw', f * 1.003, dur)
    t = t_arr(dur)
    fc = 300 + 1600 * np.exp(-t * 18)
    # time-varying lowpass approximated by blending two filters
    lo, hi = lowpass(x, 350), lowpass(x, 1800)
    w = (fc - 300) / 1600
    x = lo * (1 - w) + hi * w
    return np.tanh(1.5 * x) * env_adsr(len(x), 0.004, 0.08, 0.7, 0.03)


def lead_note(m, dur, duty=0.25):
    f = midi_hz(m)
    t = t_arr(dur)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 6 * t) * np.clip((t - 0.12) * 8, 0, 1)
    x = osc('square', f * vib, dur, duty)
    return lowpass(x, 5000) * env_adsr(len(x), 0.004, 0.06, 0.55, 0.05)


def brass_stab(notes, dur):
    x = np.zeros(int(dur * SR))
    t = t_arr(dur)
    for m in notes:
        f = midi_hz(m)
        for det in (-0.08, 0, 0.08):
            x += osc('saw', f * 2 ** (det / 12), dur)
    fc_env = np.exp(-t * 4)
    x = lowpass(x, 900) * (1 - fc_env) * 0.3 + lowpass(x, 3500) * fc_env
    return x / len(notes) * env_adsr(len(x), 0.01, 0.2, 0.5, 0.2) * 0.5


def timpani(m, dur=1.2):
    t = t_arr(dur)
    f = midi_hz(m) * (1 + 0.05 * np.exp(-t * 20))
    x = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (3 + 2 * k)) / k for k in (1, 1.5, 1.98))
    n = lowpass(rng.standard_normal(len(t)), 600) * np.exp(-t * 30)
    return 0.8 * x + 0.3 * n


# ---------------------------------------------------------------- music
BPM = 116
BEAT = 60 / BPM
BAR = 4 * BEAT
# F major funk progression: F  Dm  Bb  C
PROG = [(41, [65, 69, 72]), (38, [62, 65, 69]), (46, [62, 65, 70]), (36, [64, 67, 72])]
MELODY = [  # (beat offset within 4 bars, midi, beats)
    (0, 77, .5), (.5, 81, .5), (1, 84, .75), (2, 81, .5), (2.5, 79, .5), (3, 77, 1),
    (4, 74, .5), (4.5, 77, .5), (5, 81, .75), (6, 79, .5), (6.5, 77, .5), (7, 74, 1),
    (8, 74, .5), (8.5, 77, .5), (9, 82, .75), (10, 81, .5), (10.5, 79, .5), (11, 77, .5), (11.5, 74, .5),
    (12, 76, .5), (12.5, 79, .5), (13, 84, 1), (14.5, 82, .25), (14.75, 81, .25), (15, 79, 1),
]


def music_stems(dur):
    n = int((dur + 2) * SR)
    stems = {k: np.zeros(n) for k in ('drums', 'bass', 'chords', 'lead')}
    k_, s_, c_, h_, oh_ = kick(), snare(), clap(), hat(), hat(open_=True)
    bars = int(dur / BAR) + 2
    swing = 0.035
    for b in range(bars):
        t0 = b * BAR
        root, chord = PROG[b % 4]
        # drums
        for beat in (0, 2):
            add(stems['drums'], k_, t0 + beat * BEAT, 1.0)
        add(stems['drums'], k_, t0 + 2.75 * BEAT if b % 2 else t0 + 1.5 * BEAT, 0.7)
        for beat in (1, 3):
            add(stems['drums'], s_, t0 + beat * BEAT, 0.55)
            add(stems['drums'], c_, t0 + beat * BEAT, 0.45)
        for e in range(8):
            off = swing if e % 2 else 0
            if e == 7 and b % 2:
                add(stems['drums'], oh_, t0 + e * BEAT / 2 + off, 0.22)
            else:
                add(stems['drums'], h_, t0 + e * BEAT / 2 + off, 0.28 if e % 2 else 0.18)
        # bass: funky octave pattern
        patt = [(0, 0, .45), (.75, 0, .2), (1.5, 12, .25), (2, 0, .4), (2.75, 7, .2), (3.25, 12, .2), (3.5, 10, .4)]
        for pos, iv, ln in patt:
            add(stems['bass'], bass_note(root + iv, ln * BEAT * 1.6), t0 + pos * BEAT, 0.5)
        # chord stabs on off-beats
        for pos in (0.5, 1.5, 2.25, 3.5):
            add(stems['chords'], pluck_chord(chord, BEAT * 0.6), t0 + pos * BEAT + swing, 0.9)
        # lead melody
        if b % 4 == 0:
            for pos, m, ln in MELODY:
                add(stems['lead'], lead_note(m, ln * BEAT * 0.95), t0 + pos * BEAT, 0.22)
    return stems


def news_intro(dur):
    """Dramatic 'breaking news' sting."""
    x = np.zeros(int((dur + 2) * SR))
    for i, (notes, at) in enumerate([([53, 57, 60], 0), ([53, 57, 60], 0.25), ([55, 58, 62], 0.9), ([57, 60, 65], 1.6)]):
        add(x, brass_stab(notes, 1.2 if i == 3 else 0.35), at, 0.9)
        add(x, timpani(29 if i < 3 else 33, 1.0), at, 0.7)
    # pulsing news synth
    t = t_arr(dur)
    pulse = osc('square', midi_hz(65), dur, 0.5) * (np.sin(2 * np.pi * 8 * t / 2) > 0) * 0.06
    add(x, lowpass(pulse, 2000) * np.clip(t - 1.8, 0, 0.2) * 5, 0, 1)
    return x


# ---------------------------------------------------------------- sfx
def sfx(name):
    if name == 'whoosh':
        d = 0.6; t = t_arr(d)
        n = rng.standard_normal(len(t))
        out = np.zeros_like(n)
        seg = 1200
        for i in range(0, len(n), seg):
            fc = 400 + 5000 * np.sin(np.pi * i / len(n)) ** 2
            out[i:i + seg] = bandpass(n[max(0, i - 400):i + seg], fc * 0.6, fc * 1.4)[-len(n[i:i + seg]):]
        return out * np.sin(np.pi * t / d) ** 2 * 0.9
    if name == 'crash':
        d = 1.8; t = t_arr(d)
        n = rng.standard_normal(len(t))
        x = lowpass(n, 5000) * np.exp(-t * 3.5) * 0.8
        kk = kick(0.6); x[:len(kk)] += kk
        x[:int(0.8 * SR)] += 1.2 * np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t_arr(0.8) * 8)) / SR) * np.exp(-t_arr(0.8) * 4)
        for _ in range(28):  # debris
            at = rng.uniform(0.05, 1.3)
            c = bandpass(rng.standard_normal(1500), 800, 4000) * np.exp(-np.arange(1500) / 200) * rng.uniform(.2, .6)
            i = int(at * SR); x[i:i + 1500] += c[:len(x[i:i + 1500])]
        return np.tanh(x)
    if name == 'boing':
        d = 0.6; t = t_arr(d)
        f = 180 + 120 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 5) + 150 * t
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.8
    if name == 'stamp':
        d = 0.35; t = t_arr(d)
        x = np.sin(2 * np.pi * np.cumsum(70 + 80 * np.exp(-t * 60)) / SR) * np.exp(-t * 18)
        x += lowpass(rng.standard_normal(len(t)), 3000) * np.exp(-t * 60) * 0.6
        return np.tanh(2 * x)
    if name == 'ding':
        d = 1.5; t = t_arr(d)
        f = 1568
        return sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2 + 2 * i)) / (i + 1)
                   for i, k in enumerate((1, 2.76, 5.4))) * 0.5
    if name == 'scratch':
        d = 0.45; t = t_arr(d)
        rate = np.sin(2 * np.pi * 2.2 * t) * np.exp(-t * 2)
        f = 300 + 900 * np.abs(rate)
        saw = osc('saw', f, d) * 0.5
        n = bandpass(rng.standard_normal(len(t)), 500, 3000) * np.abs(rate)
        return (saw * np.abs(rate) + n) * np.exp(-t * 3) * 0.8
    if name == 'slide_up':
        d = 0.7; t = t_arr(d)
        f = 400 * 2 ** (2 * t / d)
        return np.sin(2 * np.pi * np.cumsum(f * (1 + 0.02 * np.sin(2 * np.pi * 7 * t))) / SR) * env_adsr(len(t), .03, .1, .8, .15) * 0.5
    if name == 'slide_down':
        d = 0.7; t = t_arr(d)
        f = 1600 * 2 ** (-2 * t / d)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_adsr(len(t), .03, .1, .8, .15) * 0.5
    if name == 'pop':
        d = 0.12; t = t_arr(d)
        f = 600 + 900 * t / d
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35) * 0.7
    if name == 'squawk':
        d = 0.45; t = t_arr(d)
        f = 900 + 500 * np.sin(np.pi * t / d) + 200 * np.sin(2 * np.pi * 30 * t)
        x = osc('saw', f, d) + 0.5 * osc('square', f * 1.5, d, 0.3)
        x = bandpass(x, 1200, 4500) + 0.3 * bandpass(rng.standard_normal(len(t)), 2000, 6000)
        return np.tanh(3 * x) * env_adsr(len(t), .01, .05, .8, .12) * 0.45
    if name == 'beep':
        out = np.zeros(int(1.0 * SR))
        for k in range(3):
            b = osc('square', 1000, 0.18, 0.5) * 0.25
            add(out, lowpass(b, 3000), k * 0.33)
        return out
    if name == 'airhorn':
        d = 1.2; out = np.zeros(int(d * SR))
        for at, ln in ((0, .25), (.3, .25), (.6, .6)):
            t = t_arr(ln)
            f = 466 * (1 + 0.01 * np.sin(2 * np.pi * 5 * t))
            x = sum(osc('saw', f * r, ln) for r in (1, 1.26, 1.5, 2.01))
            add(out, np.tanh(2 * lowpass(x, 3000)) * env_adsr(len(t), .01, .05, .9, .05) * 0.35, at)
        return out
    if name == 'rise':
        d = 1.4; t = t_arr(d)
        n = rng.standard_normal(len(t))
        x = np.zeros_like(n); seg = 2400
        for i in range(0, len(n), seg):
            fc = 300 + 6000 * (i / len(n)) ** 2
            x[i:i + seg] = bandpass(n[max(0, i - 600):i + seg], fc * .7, fc * 1.3)[-len(n[i:i + seg]):]
        return x * (t / d) ** 2 * 0.8
    if name == 'tada':
        out = np.zeros(int(1.6 * SR))
        add(out, brass_stab([65, 69, 72], 0.18), 0)
        add(out, brass_stab([65, 69, 72, 77], 1.3), 0.2)
        return out * 1.3
    if name == 'cricket':
        d = 1.6; t = t_arr(d)
        chirp = np.sin(2 * np.pi * 4500 * t) * (np.sin(2 * np.pi * 30 * t) > 0.3)
        gate = ((t % 0.55) < 0.18)
        return chirp * gate * 0.12
    if name == 'type':
        out = np.zeros(int(1.2 * SR))
        for k in range(12):
            c = highpass(rng.standard_normal(600), 2000) * np.exp(-np.arange(600) / 80) * 0.25
            add(out, c, k * 0.09 + rng.uniform(0, .03))
        return out
    if name == 'thud':
        return kick(0.4) * 0.9
    raise ValueError(name)


# ---------------------------------------------------------------- TTS
_kokoro = None


def tts(text, voice, speed=1.0, pitch=1.0, lang='en-us'):
    """Returns mono float array at SR. pitch>1 = chipmunk (resampled)."""
    global _kokoro
    key = hashlib.md5(json.dumps([text, voice, speed, pitch, lang]).encode()).hexdigest()[:16]
    path = os.path.join(CACHE, key + '.wav')
    if os.path.exists(path):
        x, _ = sf.read(path)
        return x
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(ASSETS, 'kokoro-v1.0.onnx'), os.path.join(ASSETS, 'voices-v1.0.bin'))
    s, sr = _kokoro.create(text, voice=voice, speed=speed / pitch, lang=lang)
    s = np.asarray(s, dtype=np.float64)
    # to SR, with pitch shift via resampling
    from fractions import Fraction
    fr = Fraction(SR / (sr * pitch)).limit_denominator(200)
    x = signal.resample_poly(s, fr.numerator, fr.denominator)
    # trim silence
    thr = 0.01 * np.max(np.abs(x))
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx):
        x = x[max(0, idx[0] - 800): idx[-1] + 2400]
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    sf.write(path, x, SR)
    return x


def envelope(x, fps=30):
    """Per-frame RMS amplitude envelope (0..1) for lip sync."""
    hop = SR // fps
    n = len(x) // hop + 1
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(x) else 0 for i in range(n)])
    return np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)
