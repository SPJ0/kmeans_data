"""Build timeline -> mix audio -> render frames -> mux video."""
import math, os, sys, subprocess, pickle
import numpy as np
import cairo
import soundfile as sf

import audio as A
import gfx as G
from gfx import *  # noqa
from script import SCENES, VOICES

FPS = 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)


# ============================================================== timeline
class Line:
    def __init__(self, who, text, start, dur, env):
        self.who, self.text, self.start, self.dur, self.env = who, text, start, dur, env
        self.end = start + dur
        words = text.split()
        weights = np.array([len(w) + 2.5 for w in words], dtype=float)
        cum = np.concatenate([[0], np.cumsum(weights)]) / weights.sum()
        self.word_t = [start + c * dur * 0.97 for c in cum[:-1]]

    def words_visible(self, T):
        return sum(1 for wt in self.word_t if T >= wt)

    def mouth(self, T):
        i = int((T - self.start) * FPS)
        if 0 <= i < len(self.env):
            return float(self.env[i])
        return 0.0


class Scene:
    def __init__(self, kind, cfg, start):
        self.kind, self.cfg, self.start = kind, cfg, start
        self.marks, self.lines = {}, []
        self.end = start

    def m(self, name, default=1e9):
        return self.marks.get(name, default)

    def line(self, who, T, hold=0.7):
        """Current (or just-finished) line by `who`."""
        best = None
        for ln in self.lines:
            if ln.who == who and ln.start <= T < ln.end + hold:
                best = ln
        return best

    def talking(self, who, T):
        ln = self.line(who, T, hold=0)
        return ln.mouth(T) if ln else 0.0

    def lines_of(self, who):
        return [l for l in self.lines if l.who == who]


def build_timeline():
    t = 0.0
    scenes, sfx_events, voice_clips = [], [], []
    for sc in SCENES:
        if len(sc) == 2:
            kind, beats = sc
            cfg = {}
        else:
            kind, cfg, beats = sc
        S = Scene(kind, cfg, t)
        for b in beats:
            typ = b[0]
            if typ == 'pause':
                t += b[1]
            elif typ == 'mark':
                S.marks[b[1]] = t
            elif typ == 'sfx':
                o = b[2] if len(b) > 2 else {}
                sfx_events.append((t + o.get('at', 0), b[1], o.get('gain', 1.0)))
            elif typ == 'say':
                who, txt, o = b[1], b[2], b[3] if len(b) > 3 else {}
                v = VOICES[who]
                clip = A.tts(o.get('tts', txt), v['voice'], v['speed'], v['pitch'])
                dur = len(clip) / A.SR
                if 'mark' in o:
                    S.marks[o['mark']] = t
                ln = Line(who, txt, t, dur, A.envelope(clip, FPS))
                S.lines.append(ln)
                voice_clips.append((t, clip, who))
                t += dur + o.get('gap', 0.2)
        S.end = t
        scenes.append(S)
    total = t
    # chart: sfx when the line smashes each wall
    for S in scenes:
        if S.kind == 'chart':
            for wt in chart_wall_times(S):
                sfx_events.append((wt, 'crash', 0.35))
                sfx_events.append((wt, 'pop', 0.8))
    return scenes, sfx_events, voice_clips, total


# ============================================================== audio mix
def mix_audio(scenes, sfx_events, voice_clips, total):
    n = int((total + 0.5) * A.SR)
    voice = np.zeros(n)
    for at, clip, who in voice_clips:
        g = {'narrator': 0.95, 'anchor': 0.9, 'kevin': 0.95, 'parrot': 0.9}[who]
        A.add(voice, clip, at, g)
    fx = np.zeros(n)
    cache = {}
    for at, name, gain in sfx_events:
        if name not in cache:
            x = A.sfx(name)
            cache[name] = x / (np.max(np.abs(x)) + 1e-9)
        A.add(fx, cache[name], max(0, at), 0.32 * gain)

    news = scenes[0]
    crash = news.m('crash')
    # music: news sting at start, groove from crash onward
    music = np.zeros(n)
    sting = A.news_intro(crash)
    fade = np.clip((crash - A.t_arr(len(sting) / A.SR)) / 0.3, 0, 1)
    A.add(music, sting * fade[:len(sting)], 0, 0.55)

    groove_len = total - crash + 1
    stems = A.music_stems(groove_len)
    tt = np.arange(n) / A.SR
    # voice activity (smoothed) for ducking
    act = np.zeros(n)
    for at, clip, who in voice_clips:
        i, j = int(at * A.SR), int((at + len(clip) / A.SR) * A.SR)
        act[i:j] = 1
    k = int(0.25 * A.SR)
    act = np.convolve(act, np.ones(k) / k, mode='same')
    act_slow = np.convolve(act, np.ones(4 * k) / (4 * k), mode='same')
    duck = 1 - 0.62 * np.clip(act, 0, 1)
    lead_gain = 1 - 0.85 * np.clip(act_slow * 1.5, 0, 1)
    # silences (comedic stops)
    mute = np.ones(n)
    for S in scenes:
        if 'crickets' in S.marks:
            c0 = S.m('crickets')
            mute *= 1 - ((tt > c0 - 0.05) & (tt < c0 + 1.45))
    mute = np.convolve(mute, np.ones(600) / 600, mode='same')
    # final fade
    fin = np.clip((total - tt) / 2.0, 0, 1)
    g = {'drums': 0.5, 'bass': 0.65, 'chords': 0.5, 'lead': 0.75}
    for name, st in stems.items():
        seg = np.zeros(n)
        A.add(seg, st, crash, 1.0)
        gain = g[name] * duck * mute * fin * (np.clip((tt - crash) / 0.05, 0, 1))
        if name == 'lead':
            gain = gain * lead_gain
        music += seg * gain * 0.62
    mixd = voice + fx + music
    mixd = np.tanh(mixd * 1.1) / np.tanh(1.1)
    mixd = mixd / (np.max(np.abs(mixd)) + 1e-9) * 0.95
    path = os.path.join(OUT, 'mix.wav')
    sf.write(path, np.stack([mixd, mixd], 1), A.SR)
    return path


# ============================================================== shared bits
def blinkf(T, off=0.0):
    return ((T + off) % 3.3) < 0.11


def goal_counter(ctx, T, n, bump_t=None, y=395):
    s = 1.0
    if bump_t is not None and T >= bump_t:
        s = 1 + 0.35 * math.exp(-(T - bump_t) * 6) * abs(math.cos((T - bump_t) * 14))
    ctx.save()
    ctx.translate(540, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    rrect(ctx, -300, -46, 600, 92, 46)
    fill_stroke(ctx, INK, WHITE, 5, a=0.85)
    text(ctx, 'GOALPOSTS MOVED: %d' % n, 20, 3, 52, FONT_TITLE, YELLOW, None, shadow=False, tracking=2)
    G.goalpost(ctx, -250, 32, 0.22)
    ctx.restore()


def caption(ctx, ln, T, y, col=YELLOW, maxw=900, size=54):
    if ln is None:
        return
    a = clamp((T - ln.start) / 0.12) * clamp((ln.end + 0.5 - T) / 0.2)
    if a <= 0:
        return
    tw, th, lines = measure_block(ctx, ln.text, size, maxw, FONT_BUBBLE, 1.05, True)
    rrect(ctx, 540 - tw / 2 - 34, y - th / 2 - 22, tw + 68, th + 44, 26)
    rgb(ctx, INK, 0.78 * a)
    ctx.fill()
    text_block(ctx, ln.text, 540, y + 3, size, maxw, FONT_BUBBLE, col, INK, 1.05, a=a, lw=0.1, shadow=False,
               bold=True, words_visible=ln.words_visible(T))


def char_bubble(ctx, S, who, T, x, y, w, tail, size=46, **kw):
    ln = S.line(who, T)
    if ln is None:
        return
    pop = ease_back(prog(T, ln.start - 0.05, 0.22)) * (1 - ease_in(prog(T, ln.end + 0.45, 0.2)))
    shout = kw.pop('shout', False)
    bubble(ctx, ln.text, x, y, w, size, tail=tail, words_visible=ln.words_visible(T), pop=pop, shout=shout, **kw)


def shake_offset(T, t0, dur=0.5, amp=28):
    if t0 <= T < t0 + dur:
        k = 1 - (T - t0) / dur
        return (math.sin(T * 91) * amp * k, math.cos(T * 77) * amp * k)
    return (0, 0)


def flash(ctx, T, t0, dur=0.25, col=WHITE):
    if t0 <= T < t0 + dur:
        rgb(ctx, col, 1 - (T - t0) / dur)
        ctx.paint()


def confetti(ctx, T, t0, n=90, seed=3):
    if T < t0:
        return
    r = np.random.default_rng(seed)
    cols = [RED, YELLOW, BLUE, GREEN, PINK, PURPLE, CYAN]
    dt = T - t0
    for i in range(n):
        x0 = r.uniform(0, W)
        vy = r.uniform(250, 520)
        y = -60 + vy * dt - r.uniform(0, 500)
        x = x0 + math.sin(dt * r.uniform(2, 5) + i) * 50
        if y > H + 50 or y < -80:
            continue
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(dt * r.uniform(-8, 8))
        ctx.scale(1, abs(math.cos(dt * r.uniform(3, 9))) + 0.1)
        rrect(ctx, -14, -8, 28, 16, 3)
        rgb(ctx, cols[i % len(cols)])
        ctx.fill()
        ctx.restore()


def stars_bg(ctx, T, seed=11, n=160):
    r = np.random.default_rng(seed)
    for i in range(n):
        x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(1.5, 4.5)
        tw = 0.5 + 0.5 * math.sin(T * r.uniform(1, 4) + i)
        rgb(ctx, WHITE, 0.3 + 0.7 * tw)
        circle(ctx, x, y, s)
        ctx.fill()


# ============================================================== scenes
def draw_news(ctx, S, T):
    t = T - S.start
    wall_t, crash_t, title_t = S.m('wall_drop'), S.m('crash'), S.m('title')
    if T >= title_t:
        return draw_title(ctx, S, T)
    sx, sy = shake_offset(T, wall_t + 0.4, 0.45, 30)
    sx2, sy2 = shake_offset(T, crash_t, 0.7, 45)
    ctx.save()
    ctx.translate(sx + sx2, sy + sy2)
    vgrad(ctx, hexc('#1c2f7a'), hexc('#070b24'))
    # globe
    ctx.save()
    ctx.translate(540, 820)
    rgb(ctx, CYAN, 0.12)
    ctx.set_line_width(4)
    circle(ctx, 0, 0, 420)
    ctx.stroke()
    for k in range(-3, 4):
        ellipse(ctx, 0, 0, abs(420 * math.cos(t * 0.4 + k * 0.45)), 420)
        ctx.stroke()
        ellipse(ctx, 0, k * 110, math.sqrt(max(0, 420 ** 2 - (k * 110) ** 2)), 18)
        ctx.stroke()
    ctx.restore()
    anchor(ctx, 540, 1180, 1.25, T, mouth=S.talking('anchor', T), blink=blinkf(T),
           mood='serious' if T > S.lines[1].start else 'normal')
    # LIVE bug + network
    rrect(ctx, 70, 250, 150, 70, 12)
    rgb(ctx, RED)
    ctx.fill()
    if (t % 1.0) < 0.6:
        circle(ctx, 105, 285, 12)
        rgb(ctx, WHITE)
        ctx.fill()
    text(ctx, 'LIVE', 165, 287, 44, FONT_COND, WHITE, None, shadow=False)
    text(ctx, 'FNN  FUTURE NEWS NETWORK', 250, 287, 40, FONT_COND, WHITE, None, shadow=False, align='left', a=0.9)
    # headline banner
    p = ease_out(prog(T, S.start + 0.2, 0.4))
    bx = lerp(-1100, 0, p)
    rrect(ctx, bx + 40, 1180, 520, 90, 10)
    rgb(ctx, RED)
    ctx.fill()
    text(ctx, 'BREAKING NEWS', bx + 300, 1227, 64, FONT_COND, YELLOW, None, shadow=False)
    rrect(ctx, bx + 40, 1270, 1000, 150, 10)
    rgb(ctx, WHITE)
    ctx.fill()
    l0 = S.lines[0]
    head = 'AI HAS HIT A WALL'
    nchar = int(clamp((T - l0.start - 1.2) / 1.4) * len(head))
    text(ctx, head[:nchar], bx + 70, 1347, 96, FONT_COND, INK, None, shadow=False, align='left')
    if T >= S.lines[1].start + 0.6:
        pp = ease_back(prog(T, S.lines[1].start + 0.6, 0.3))
        text(ctx, '(AGAIN)', 880, 1180, 70, FONT_TITLE, YELLOW, INK, scale=pp, rot=0.15)
    # ticker
    rrect(ctx, 0, 1440, W, 80, 0)
    rgb(ctx, hexc('#0d1440'))
    ctx.fill()
    tick = ('ALSO REPORTED: 2022  •  2023  •  2024  •  2025  •  LAST TUESDAY  •  '
            'EXPERTS: "THIS TIME FOR SURE"  •  ') * 3
    text(ctx, tick, 1100 - t * 260, 1482, 46, FONT_COND, WHITE, None, shadow=False, align='left')
    # wall
    if T >= wall_t:
        pw = bounce(prog(T, wall_t, 0.75))
        wy = lerp(-1400, 330, pw)
        rumble = (math.sin(T * 70) * 6) if crash_t - 1.0 < T < crash_t else 0
        amt = clamp((T - crash_t) / 1.1) if T >= crash_t else 0
        brick_wall(ctx, -20 + rumble, wy, 1120, 1250, t, broken=(540, wy + 560, 430, amt) if amt > 0 else None)
        if amt == 0:
            ctx.save()
            ctx.translate(540 + rumble, wy + 180)
            ctx.rotate(-0.04)
            rrect(ctx, -330, -75, 660, 150, 18)
            fill_stroke(ctx, CREAM, INK, 9)
            text(ctx, 'THE WALL™', 0, 5, 110, FONT_TITLE, RED, INK, lw=8, shadow=False)
            ctx.restore()
            if T > crash_t - 0.8:  # cracks
                k = clamp((T - (crash_t - 0.8)) / 0.8)
                ctx.save()
                ctx.translate(540, wy + 600)
                rgb(ctx, INK)
                ctx.set_line_width(10)
                for i in range(7):
                    a = i * TAU / 7 + 0.3
                    ctx.move_to(0, 0)
                    L = 380 * k
                    ctx.line_to(math.cos(a) * L * 0.5 + 20, math.sin(a) * L * 0.5 - 15)
                    ctx.line_to(math.cos(a + 0.2) * L, math.sin(a + 0.2) * L)
                ctx.stroke()
                ctx.restore()
        # parrot bursting through
        if T >= crash_t:
            pk = clamp((T - crash_t) / 0.9)
            s = lerp(0.25, 1.35, ease_out(pk))
            px, py = 540 - 20, wy + 560 + lerp(150, 700, ease_out(pk))
            rocket_trail(ctx, px - 30 * s, py - 250 * s, -math.pi / 2 + 0.0, T, 300 * s)
            parrot(ctx, px - 60 * s, py, s, T, mouth=0.8 if pk < 0.5 else 0.2, acc=('shades',), flap=abs(math.sin(T * 18)))
    ctx.restore()
    flash(ctx, T, crash_t, 0.3)


def draw_title(ctx, S, T):
    t0 = S.m('title')
    sunburst(ctx, 540, 900, T, hexc('#ffcf3f'), hexc('#ffb020'))
    halftone(ctx, ORANGE, 0.12)
    p1 = ease_back(prog(T, t0, 0.3), 2.5)
    p2 = ease_back(prog(T, t0 + 0.35, 0.3), 2.5)
    sx, sy = shake_offset(T, t0 + 0.35, 0.3, 20)
    ctx.save()
    ctx.translate(sx, sy)
    text(ctx, 'JUST A', 540, 420, 170, FONT_TITLE, WHITE, INK, scale=lerp(3, 1, p1) if p1 > 0 else 0, rot=-0.06,
         a=clamp(p1 * 3))
    text(ctx, 'PARROT™', 540, 600, 250, FONT_TITLE, GREEN, INK, lw=28, scale=lerp(3, 1, p2) if p2 > 0 else 0,
         rot=-0.06, a=clamp(p2 * 3))
    p3 = ease_out(prog(T, t0 + 0.8, 0.4))
    rrect(ctx, 290, 740, 500, 70, 35)
    rgb(ctx, INK, 0.9 * p3)
    ctx.fill()
    text(ctx, 'a nature documentary', 540, 776, 44, FONT_BUBBLE, WHITE, None, shadow=False, bold=True, a=p3)
    parrot(ctx, 470, 1650, 1.45, T, mouth=0, acc=('shades',), flap=0.2 * abs(math.sin(T * 4)))
    ctx.restore()
    flash(ctx, T, t0, 0.15)


def jungle_bg(ctx, T):
    vgrad(ctx, hexc('#1f8f5f'), hexc('#0b3b2c'))
    r = np.random.default_rng(5)
    posts = ['source??', "it's just autocomplete", 'AI is a fad', 'ratio', 'first', 'cope', 'bubble!!',
             'it cant even count Rs', 'nothing ever happens', 'wall incoming']
    for i, p in enumerate(posts):
        x = r.uniform(60, 700)
        y = (r.uniform(0, H) + T * r.uniform(20, 45)) % (H + 200) - 100
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(r.uniform(-0.12, 0.12))
        set_font(ctx, FONT_BUBBLE, 34, True)
        w = text_w(ctx, p) + 110
        rrect(ctx, 0, 0, w, 70, 18)
        rgb(ctx, WHITE, 0.16)
        ctx.fill()
        circle(ctx, 38, 35, 20)
        rgb(ctx, WHITE, 0.25)
        ctx.fill()
        text(ctx, p, 70, 37, 34, FONT_BUBBLE, WHITE, None, shadow=False, bold=True, align='left', a=0.35)
        ctx.restore()


def leaves(ctx, T):
    for (x, y, ang, s) in [(-40, 150, 0.6, 1.3), (1100, 120, 2.5, 1.2), (-60, 1150, -0.2, 1.1), (1120, 1000, 3.4, 1.0)]:
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(ang + math.sin(T * 1.3 + x) * 0.04)
        ctx.scale(max(s, 1e-4), max(s, 1e-4))
        ctx.move_to(0, 0)
        ctx.curve_to(120, -120, 380, -90, 470, 0)
        ctx.curve_to(380, 90, 120, 120, 0, 0)
        fill_stroke(ctx, hexc('#2ecc71'), INK, 8)
        ctx.move_to(0, 0)
        ctx.line_to(450, 0)
        rgb(ctx, INK)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()


def draw_doc(ctx, S, T):
    t = T - S.start
    jungle_bg(ctx, T)
    # parrot on branch (enters before its line)
    pl = S.lines_of('parrot')[0]
    enter = pl.start - 0.7
    if T >= enter:
        pe = ease_back(prog(T, enter, 0.45))
        bxo = lerp(-500, 0, pe)
        ctx.move_to(-20 + bxo, 1085)
        ctx.curve_to(200 + bxo, 1070, 380 + bxo, 1100, 470 + bxo, 1080)
        rgb(ctx, INK)
        ctx.set_line_width(46)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke_preserve()
        rgb(ctx, hexc('#8b5a2b'))
        ctx.set_line_width(32)
        ctx.stroke()
        parrot(ctx, 230 + bxo, 1080, 0.82, T, mouth=S.talking('parrot', T), blink=blinkf(T), mood='angry',
               flap=0.3 * abs(math.sin(T * 12)) if T < pl.start else 0)
    leaves(ctx, T)
    kl = S.lines_of('kevin')[0]
    kevin(ctx, 690, 1620, 1.0, T, mouth=S.talking('kevin', T), blink=blinkf(T, 1.1),
          mood='smug' if T < pl.start - 0.7 else 'shock', typing=(kl.start - 1.2 < T < kl.start),
          look=(-0.8, 0) if T > pl.start - 0.7 else (0, 0.4))
    # lower third
    n1 = S.lines[0]
    p = ease_out(prog(T, n1.start + 2.0, 0.4)) * (1 - ease_in(prog(T, kl.start - 0.3, 0.3)))
    if p > 0:
        x = lerp(-700, 60, p)
        rrect(ctx, x, 640, 700, 150, 10)
        rgb(ctx, WHITE, 0.95)
        ctx.fill()
        rrect(ctx, x, 640, 18, 150, 0)
        rgb(ctx, YELLOW)
        ctx.fill()
        text(ctx, 'THE COMMON SKEPTIC', x + 50, 690, 56, FONT_COND, INK, None, shadow=False, align='left')
        text(ctx, 'Homo goalpostus', x + 52, 752, 42, FONT_BUBBLE, GRAY, None, shadow=False, align='left', bold=True)
    char_bubble(ctx, S, 'kevin', T, 600, 1000, 700, (760, 1200), 50)
    char_bubble(ctx, S, 'parrot', T, 520, 560, 640, (420, 800), 50)
    # binocular intro
    if t < 2.2:
        k = ease_io(clamp((t - 1.2) / 1.0))
        r = lerp(330, 1500, k)
        ctx.push_group()
        rgb(ctx, (0, 0, 0))
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        circle(ctx, 540 - r * 0.62, 1100, r)
        ctx.fill()
        circle(ctx, 540 + r * 0.62, 1100, r)
        ctx.fill()
        ctx.pop_group_to_source()
        ctx.paint()
    caption(ctx, S.line('narrator', T, 0), T, 300)


CARD_ICON = {}


def icon(ctx, kind, x, y, s, T):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    circle(ctx, 0, 0, 80)
    fill_stroke(ctx, CREAM, INK, 8)
    if kind == 'medal':
        ctx.move_to(-35, -70)
        ctx.line_to(0, -5)
        ctx.line_to(35, -70)
        rgb(ctx, RED)
        ctx.set_line_width(18)
        ctx.stroke()
        circle(ctx, 0, 20, 40)
        fill_stroke(ctx, YELLOW, INK, 7)
        star(ctx, 0, 20, 22, 10)
        rgb(ctx, ORANGE)
        ctx.fill()
    elif kind == 'code':
        text(ctx, '</>', 0, 4, 80, FONT_MONO, BLUE, INK, lw=8, shadow=False, bold=True)
    elif kind == 'agents':
        for i in range(4):
            for j in range(4):
                circle(ctx, -39 + i * 26, -39 + j * 26, 10)
                rgb(ctx, GREEN if (i + j + int(T * 6)) % 3 else YELLOW)
                ctx.fill()
    elif kind == 'dots':
        pts = [(-40, -20), (0, -45), (40, -20), (25, 30), (-25, 30), (0, 0)]
        rgb(ctx, PURPLE)
        ctx.set_line_width(5)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                ctx.move_to(*pts[i])
                ctx.line_to(*pts[j])
        ctx.stroke()
        for p in pts:
            circle(ctx, p[0], p[1], 10)
            fill_stroke(ctx, WHITE, INK, 5)
    elif kind == 'fluid':
        rgb(ctx, BLUE)
        ctx.set_line_width(9)
        for k in range(3):
            ctx.new_path()
            for i in range(60):
                a = i / 60 * TAU * 1.6 + T * 3 + k * 2.1
                r = 8 + i * 1.05
                if i == 0:
                    ctx.move_to(r * math.cos(a), r * math.sin(a))
                else:
                    ctx.line_to(r * math.cos(a), r * math.sin(a))
            ctx.stroke()
    elif kind == 'flask':
        poly(ctx, [(-18, -60), (18, -60), (18, -15), (50, 50), (-50, 50), (-18, -15)])
        fill_stroke(ctx, WHITE, INK, 7)
        poly(ctx, [(-34, 18), (34, 18), (50, 50), (-50, 50)])
        rgb(ctx, GREEN)
        ctx.fill()
        for i in range(3):
            yy = 10 - ((T * 60 + i * 25) % 60)
            circle(ctx, -10 + i * 12, yy, 6)
            rgb(ctx, GREEN, 0.8)
            ctx.fill()
    ctx.restore()


def draw_round(ctx, S, T):
    c = S.cfg
    n = c['n']
    col1, col2 = hexc(c['colors'][0]), hexc(c['colors'][1])
    sunburst(ctx, 540, 820, T, col1, col2)
    halftone(ctx, WHITE, 0.06)
    move_t = S.m('move')
    # header
    ph = ease_back(prog(T, S.start, 0.35))
    text(ctx, c['label'], 540, 270, 120, FONT_TITLE, WHITE, INK, scale=ph, rot=-0.03, tracking=4)
    goal_counter(ctx, T, n if T >= move_t + 0.35 else n - 1, move_t + 0.35)
    # card
    ct = S.m('card')
    pc = prog(T, ct, 0.35)
    if pc > 0:
        s = lerp(1.8, 1.0, ease_out(pc))
        ctx.save()
        ctx.translate(540, 800)
        ctx.rotate(lerp(-0.25, -0.02, ease_out(pc)))
        ctx.scale(max(s, 1e-4), max(s, 1e-4))
        a = clamp(pc * 3)
        rrect(ctx, -470 + 14, -340 + 18, 940, 680, 40)
        rgb(ctx, INK, 0.9 * a)
        ctx.fill()
        rrect(ctx, -470, -340, 940, 680, 40)
        fill_stroke(ctx, WHITE, INK, 10, a=a)
        icon(ctx, c['icon'], -330, -215, 0.95, T)
        head_w = 600
        text_block(ctx, c['head'], 90, -215, 46, head_w, FONT_BUBBLE, INK, None, 1.0, shadow=False, bold=True)
        # big stamp text
        pb = ease_back(prog(T, ct + 0.3, 0.3), 2.6)
        if pb > 0:
            big = c['big']
            size = 140 if len(big) <= 9 else (110 if len(big) <= 13 else 92)
            text(ctx, big, 0, -40, size, FONT_TITLE, col1, INK, lw=14, scale=lerp(2.2, 1, pb), rot=-0.04,
                 a=clamp(pb * 2), tracking=3)
        for i, ln in enumerate(c['lines']):
            pl = ease_out(prog(T, ct + 0.6 + i * 0.25, 0.3))
            if pl > 0:
                circle(ctx, -400, 90 + i * 70, 10)
                rgb(ctx, col1, pl)
                ctx.fill()
                fs = fit_size(ctx, ln, 36, 800, FONT_BUBBLE, True)
                text(ctx, ln, -375 + (1 - pl) * 40, 92 + i * 70, fs, FONT_BUBBLE, INK, None, shadow=False,
                     align='left', bold=True, a=pl)
        pf = prog(T, ct + 1.4, 0.4)
        text(ctx, c['foot'], 0, 295, fit_size(ctx, c['foot'], 27, 860, FONT_BUBBLE, True), FONT_BUBBLE, (0.4, 0.4, 0.45), None, shadow=False, bold=True, a=pf)
        ctx.restore()
    # characters
    acc = []
    if n >= 1:
        acc.append('medal')
    if n >= 3:
        acc.append('gradcap')
    if n >= 4:
        acc.append('glasses')
    if n >= 6:
        acc.append('labcoat')
    pm = 'smug' if T > move_t + 0.3 else 'normal'
    if 'q' in S.marks and T > S.m('q'):
        pm = 'smug'
    parrot(ctx, 215, 1800, 0.72, T, mouth=S.talking('parrot', T), blink=blinkf(T), mood=pm, acc=tuple(acc))
    kmood = 'smug' if n < 4 else 'nervous'
    sweat = clamp((n - 3) / 3)
    frozen = 'crickets' in S.marks and T > S.m('crickets')
    if frozen:
        kmood = 'shock'
    if S.line('narrator', T, 0) is not None:
        kmood = 'angry'
    kevin(ctx, 820, 1905, 0.72, T, mouth=S.talking('kevin', T), blink=blinkf(T, 0.7) and not frozen, mood=kmood,
          desk=False, sweat=sweat, look=(-0.8, -0.3))
    # goalposts leaving
    if T >= move_t:
        k = prog(T, move_t + 0.3, 0.9)
        if k < 1:
            gx = lerp(980, 1300, ease_in(k))
            gy = lerp(1500, 300, ease_in(k))
            ctx.save()
            ctx.translate(gx, gy)
            ctx.rotate(k * 2)
            goalpost(ctx, 0, 100, 0.6)
            ctx.restore()
            if k > 0:
                text(ctx, 'WHOOSH', 850, 1420, 70, FONT_TITLE, YELLOW, INK, rot=-0.2, a=1 - k,
                     scale=ease_back(clamp(k * 4)))
    if not ('crickets' in S.marks and T > S.m('crickets') + 0.3):
        char_bubble(ctx, S, 'parrot', T, 470, 1335, 840, (330, 1560), 46)
    char_bubble(ctx, S, 'kevin', T, 610, 1310, 760, (840, 1560), 50)
    caption(ctx, S.line('narrator', T, 0), T, 1300)
    if 'crickets' in S.marks and T > S.m('crickets'):
        k = prog(T, S.m('crickets'), 0.3)
        text(ctx, '*crickets*', 780, 1470, 80, FONT_TITLE, WHITE, INK, a=k, rot=0.05 * math.sin(T * 6))


def earth(ctx, T):
    g = cairo.RadialGradient(540, 2750, 1000, 540, 2750, 1350)
    g.add_color_stop_rgba(0, 0.3, 0.7, 1, 0.6)
    g.add_color_stop_rgba(1, 0.3, 0.7, 1, 0)
    ctx.set_source(g)
    ctx.paint()
    circle(ctx, 540, 2750, 1120)
    fill_stroke(ctx, hexc('#2d6cdf'), INK, 10)
    ctx.save()
    circle(ctx, 540, 2750, 1115)
    ctx.clip()
    r = np.random.default_rng(2)
    for i in range(9):
        x = (r.uniform(-400, 1500) + T * 25) % 1900 - 400
        y = r.uniform(1650, 1950)
        ellipse(ctx, x, y, r.uniform(90, 200), r.uniform(40, 80))
        rgb(ctx, hexc('#3ec46d'))
        ctx.fill()
    ctx.restore()


def draw_space(ctx, S, T):
    t = T - S.start
    rgb(ctx, hexc('#070a1c'))
    ctx.paint()
    stars_bg(ctx, T)
    earth(ctx, T)
    # six goalposts in orbit
    for i in range(6):
        ph = t * 0.22 + i * 0.16
        x = lerp(-250, 1330, (ph % 1.3) / 1.3)
        y = 1250 - math.sin((ph % 1.3) / 1.3 * math.pi) * 380 + i * 30
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(0.3 + math.sin(t + i) * 0.2)
        rocket_trail(ctx, 0, -40, math.pi, T + i, 160)
        goalpost(ctx, 0, 60, 0.5)
        ctx.restore()
    text(ctx, 'LOW EARTH ORBIT', 540, 270, 90, FONT_TITLE, WHITE, INK, tracking=4,
         scale=ease_back(prog(T, S.start + 0.3, 0.35)))
    goal_counter(ctx, T, 6, None, 395)
    # satellite dish w/ Kevin-ish antenna label
    caption(ctx, S.line('narrator', T, 0), T, 620, col=WHITE)


CHART = dict(x0=150, x1=990, y0=1300, y1=560)  # y0 bottom, y1 top
CHART_PTS = [(2019.1, 2), (2020.4, 9), (2022.2, 36), (2023.2, 300), (2024.5, 1800), (2025.6, 2 * 3600 + 17 * 60),
             (2026.4, 16 * 3600)]
CHART_LABELS = {0: '2 sec', 3: '5 min', 5: '2 hr 17 min', 6: '16+ hours'}
WALL_YEARS = [2022.0, 2023.0, 2024.0, 2025.0, 2026.0]
DRAW_DUR = 4.6


def chart_xy(year, secs):
    c = CHART
    x = lerp(c['x0'], c['x1'], (year - 2019) / (2026.6 - 2019))
    ly = math.log10(secs)
    y = lerp(c['y0'], c['y1'], (ly - 0) / (math.log10(86400 * 1.3) - 0))
    return x, y


def chart_wall_times(S):
    d0 = S.m('draw') + 1.4
    xs = [p[0] for p in CHART_PTS]
    return [d0 + (wy - xs[0]) / (xs[-1] - xs[0]) * DRAW_DUR for wy in WALL_YEARS]


def draw_chart(ctx, S, T):
    ch = S.m('chart')
    rgb(ctx, CREAM)
    ctx.paint()
    rgb(ctx, hexc('#9fc5e8'), 0.35)
    ctx.set_line_width(2)
    for x in range(0, W, 54):
        ctx.move_to(x, 0)
        ctx.line_to(x, H)
    for y in range(0, H, 54):
        ctx.move_to(0, y)
        ctx.line_to(W, y)
    ctx.stroke()
    if T < ch + 0.4:
        # Kevin big, center
        k = ease_in(prog(T, ch, 0.4))
        kevin(ctx, lerp(540, 900, k), lerp(1500, 1950, k), lerp(1.15, 0.6, k), T, mouth=S.talking('kevin', T),
              blink=blinkf(T), mood='smug', desk=True)
        char_bubble(ctx, S, 'kevin', T, 540, 760, 760, (700, 1000), 58)
        return
    pin = ease_back(prog(T, ch, 0.4))
    ctx.save()
    ctx.translate(540, 900)
    ctx.scale(max(pin, 1e-4), max(pin, 1e-4))
    ctx.translate(-540, -900)
    text_block(ctx, 'How long a task can AI agents finish on their own?', 540, 285, 62, 950, FONT_TITLE, INK,
               None, 1.0, shadow=False)
    text(ctx, 'Human-expert time, 50% success rate (approx., METR)', 540, 400, 30, FONT_BUBBLE, GRAY, None,
         shadow=False, bold=True)
    c = CHART
    ctx.move_to(c['x0'], c['y1'] - 30)
    ctx.line_to(c['x0'], c['y0'])
    ctx.line_to(c['x1'] + 30, c['y0'])
    rgb(ctx, INK)
    ctx.set_line_width(7)
    ctx.stroke()
    for lab, secs in (('1 sec', 1), ('1 min', 60), ('1 hr', 3600), ('1 day', 86400)):
        _, y = chart_xy(2019, secs)
        text(ctx, lab, c['x0'] - 18, y, 30, FONT_BUBBLE, INK, None, shadow=False, bold=True, align='right')
        ctx.move_to(c['x0'], y)
        ctx.line_to(c['x1'], y)
        rgb(ctx, GRAY, 0.35)
        ctx.set_line_width(2)
        ctx.set_dash([10, 10])
        ctx.stroke()
        ctx.set_dash([])
    for yr in range(2019, 2027):
        x, _ = chart_xy(yr + 0.5, 1)
        text(ctx, "'%02d" % (yr % 100), x, c['y0'] + 40, 32, FONT_BUBBLE, INK, None, shadow=False, bold=True)
    # progress
    d0 = S.m('draw') + 1.4
    pr = clamp((T - d0) / DRAW_DUR)
    xs = [p[0] for p in CHART_PTS]
    cur_year = lerp(xs[0], xs[-1], pr)
    # walls
    wts = chart_wall_times(S)
    for i, (wy, wt) in enumerate(zip(WALL_YEARS, wts)):
        appear = wt - 0.9
        if T < appear:
            continue
        x, _ = chart_xy(wy, 1)
        # wall height: tall column
        top = c['y1'] + 40
        amt = clamp((T - wt) / 0.9) if T >= wt else 0
        if amt >= 1:
            continue
        pa = ease_back(prog(T, appear, 0.3))
        ctx.save()
        ctx.rectangle(0, 0, W, c['y0'])
        ctx.clip()
        hh = (c['y0'] - top) * pa
        # bricks column
        for r in range(int(hh / 32) + 1):
            bx = x - 21
            by = c['y0'] - (r + 1) * 32
            fy = amt * amt * 900 * (0.5 + ((r * 7) % 5) / 5)
            fx = amt * 300 * ((r % 3) - 1)
            ctx.save()
            ctx.translate(bx + 21 + fx, by + 16 + fy)
            ctx.rotate(amt * (r % 4 - 1.5))
            rrect(ctx, -21, -15, 42, 30, 4)
            fill_stroke(ctx, (0.8, 0.3, 0.2), INK, 3)
            ctx.restore()
        ctx.restore()
        if amt == 0:
            text(ctx, 'WALL', x, top - 30, 34, FONT_TITLE, RED, INK, lw=5, shadow=False, rot=-0.1)
        else:
            text(ctx, 'NOPE', x, top - 30 - amt * 60, 40, FONT_TITLE, YELLOW, INK, a=1 - amt, scale=1 + amt)
    # the line
    if pr > 0:
        pts = []
        for i in range(len(CHART_PTS) - 1):
            (ya, sa), (yb, sb) = CHART_PTS[i], CHART_PTS[i + 1]
            if ya > cur_year:
                break
            pts.append(chart_xy(ya, sa))
            if yb > cur_year:
                f = (cur_year - ya) / (yb - ya)
                pts.append(chart_xy(cur_year, 10 ** lerp(math.log10(sa), math.log10(sb), f)))
        else:
            pass
        if pr >= 1:
            pts = [chart_xy(*p) for p in CHART_PTS]
        if len(pts) >= 2:
            poly(ctx, pts, close=False)
            rgb(ctx, INK)
            ctx.set_line_width(22)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
            rgb(ctx, GREEN)
            ctx.set_line_width(12)
            ctx.stroke()
            hx, hy = pts[-1]
            # parrot head marker
            burst(ctx, hx, hy, 34, 10, YELLOW, T * 4, 5)
        for i, (yr, secs) in enumerate(CHART_PTS):
            if yr <= cur_year + 1e-6:
                x, y = chart_xy(yr, secs)
                circle(ctx, x, y, 13)
                fill_stroke(ctx, WHITE, INK, 6)
                if i in CHART_LABELS:
                    pl = ease_back(prog(T, d0 + (yr - xs[0]) / (xs[-1] - xs[0]) * DRAW_DUR, 0.3))
                    lab = CHART_LABELS[i]
                    left = i >= 5
                    text(ctx, lab, x + (-24 if left else 24), y - 42, 40 if i == 6 else 34, FONT_TITLE,
                         RED if i == 6 else INK, WHITE if i != 6 else INK, lw=6, align='right' if left else 'left',
                         shadow=False, scale=pl)
    ctx.restore()
    caption(ctx, S.line('narrator', T, 0), T, 1480)
    pl = S.lines_of('parrot')[0]
    parrot(ctx, 230, 1880, 0.62, T, mouth=S.talking('parrot', T), blink=blinkf(T), mood='smug',
           acc=('medal', 'gradcap', 'glasses'))
    kevin(ctx, 900, 1950, 0.6, T, blink=blinkf(T, 0.4), mood='nervous', desk=True, sweat=0.6)
    char_bubble(ctx, S, 'parrot', T, 560, 1470, 720, (330, 1690), 52)


def tungsten(ctx, x, y, s):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    poly(ctx, [(0, -60), (60, -30), (0, 0), (-60, -30)])
    fill_stroke(ctx, (0.78, 0.8, 0.84), INK, 5)
    poly(ctx, [(-60, -30), (0, 0), (0, 60), (-60, 30)])
    fill_stroke(ctx, (0.55, 0.57, 0.62), INK, 5)
    poly(ctx, [(60, -30), (0, 0), (0, 60), (60, 30)])
    fill_stroke(ctx, (0.42, 0.44, 0.5), INK, 5)
    ctx.restore()


def draw_shop(ctx, S, T):
    vgrad(ctx, hexc('#ffe3b3'), hexc('#ffc680'))
    # shelves behind
    for row in range(3):
        y = 700 + row * 190
        rrect(ctx, 80, y, 920, 22, 6)
        fill_stroke(ctx, hexc('#a0692f'), INK, 5)
        for i in range(8):
            cols = [RED, BLUE, YELLOW, GREEN, PINK, PURPLE, ORANGE, CYAN]
            rrect(ctx, 110 + i * 110, y - 110 + (i % 2) * 15, 80, 110 - (i % 2) * 15, 10)
            fill_stroke(ctx, cols[(i + row * 3) % 8], INK, 5)
    # awning
    for i in range(10):
        poly(ctx, [(i * 108, 360), ((i + 1) * 108, 360), ((i + 1) * 108, 480), (i * 108 + 54, 530), (i * 108, 480)])
        fill_stroke(ctx, RED if i % 2 == 0 else WHITE, INK, 5)
    rrect(ctx, 140, 205, 800, 140, 20)
    fill_stroke(ctx, hexc('#2d3436'), INK, 8)
    text(ctx, "POLLY'S SNACK SHOP", 540, 278, 78, FONT_TITLE, YELLOW, None, shadow=False, tracking=3)
    # parrot behind counter
    pl = S.lines_of('parrot')[0]
    parrot(ctx, 470, 1420, 1.05, T, mouth=S.talking('parrot', T), blink=blinkf(T),
           mood='smug' if T >= pl.start else 'normal', look=(0.6, 0.4))
    # counter
    rrect(ctx, 40, 1380, 1000, 520, 20)
    fill_stroke(ctx, hexc('#c98b4f'), INK, 9)
    rrect(ctx, 20, 1350, 1040, 60, 14)
    fill_stroke(ctx, hexc('#e0a868'), INK, 9)
    # tungsten cubes pile
    ct = S.m('cubes')
    pos = [(130, 1320), (250, 1320), (190, 1270), (840, 1320), (960, 1320), (900, 1270), (190, 1215), (900, 1215),
           (70, 1350), (1010, 1360)]
    for i, (x, y) in enumerate(pos):
        dt = T - (ct + i * 0.12)
        if dt < 0:
            continue
        yy = lerp(-200, y, bounce(clamp(dt / 0.5)))
        tungsten(ctx, x, yy - 30, 0.9)
    if T >= ct:
        ptag = ease_back(prog(T, ct + 1.0, 0.3))
        ctx.save()
        ctx.translate(230, 1060)
        ctx.rotate(-0.12)
        ctx.scale(max(ptag, 1e-4), max(ptag, 1e-4))
        rrect(ctx, -170, -60, 340, 120, 16)
        fill_stroke(ctx, YELLOW, INK, 7)
        text(ctx, 'TUNGSTEN!', 0, -12, 54, FONT_TITLE, INK, None, shadow=False)
        text(ctx, 'sold at a loss', 0, 32, 30, FONT_BUBBLE, RED, None, shadow=False, bold=True)
        ctx.restore()
    # profit chart going down
    p = prog(T, S.start + 0.8, 3.0)
    ctx.save()
    ctx.translate(90, 1500)
    rrect(ctx, 0, 0, 400, 300, 20)
    fill_stroke(ctx, WHITE, INK, 7)
    text(ctx, 'PROFIT', 200, 45, 48, FONT_TITLE, INK, None, shadow=False)
    pts = [(40 + i * 40, 110 + i * 16 + 18 * math.sin(i * 1.7)) for i in range(int(1 + 8 * p))]
    if len(pts) >= 2:
        poly(ctx, pts, close=False)
        rgb(ctx, RED)
        ctx.set_line_width(10)
        ctx.stroke()
    ctx.restore()
    rrect(ctx, 560, 1520, 440, 300, 20)
    fill_stroke(ctx, WHITE, INK, 7)
    text_block(ctx, 'Real experiment! (Anthropic Project Vend, 2025)', 780, 1670, 44, 380, FONT_BUBBLE, INK, None, 1.0,
               shadow=False, bold=True)
    caption(ctx, S.line('narrator', T, 0), T, 560)
    char_bubble(ctx, S, 'parrot', T, 700, 760, 560, (720, 960), 54)


def draw_finale(ctx, S, T):
    end_t = S.m('endcard')
    sh = S.m('shades')
    sunburst(ctx, 540, 1000, T, hexc('#7d5fff'), hexc('#6c4ee8'))
    halftone(ctx, WHITE, 0.06)
    if T < end_t:
        # pedestal
        rrect(ctx, 60, 1280, 380, 700, 16)
        fill_stroke(ctx, WHITE, INK, 9)
        text(ctx, 'NOT A', 250, 1400, 60, FONT_TITLE, INK, None, shadow=False)
        text(ctx, 'PARROT', 250, 1470, 60, FONT_TITLE, INK, None, shadow=False)
        acc = ['medal', 'gradcap']
        shades_on = T >= sh + 0.35
        if shades_on:
            acc.append('shades')
        parrot(ctx, 220, 1285, 1.0, T, mouth=S.talking('parrot', T), blink=blinkf(T), mood='smug', acc=tuple(acc))
        if sh <= T < sh + 0.35:  # shades falling
            k = ease_in(prog(T, sh, 0.35))
            ctx.save()
            ctx.translate(0, lerp(-900, 0, k))
            ctx.save()
            ctx.translate(220, 1285)
            ctx.translate(55, -320 + 4 * math.sin(T * 5.2))
            poly(ctx, [(-70, -25), (60, -25), (60, 10), (-10, 20), (-70, 10)])
            fill_stroke(ctx, INK, INK, 6)
            ctx.restore()
            ctx.restore()
        kevin(ctx, 800, 1700, 0.95, T, mouth=S.talking('kevin', T), blink=blinkf(T, 0.3),
              mood='nervous' if T < sh else 'shock', desk=True, sweat=1.0,
              typing=(S.lines_of('kevin')[0].start - 1.2 < T < S.lines_of('kevin')[0].start))
        caption(ctx, S.line('narrator', T, 0), T, 420, col=WHITE)
        char_bubble(ctx, S, 'kevin', T, 700, 880, 560, (860, 1100), 52)
        char_bubble(ctx, S, 'parrot', T, 500, 700, 760, (360, 960), 56, shout=True)
        return
    # END CARD
    t = T - end_t
    sunburst(ctx, 540, 900, T, hexc('#ffcf3f'), hexc('#ffb020'))
    halftone(ctx, ORANGE, 0.12)
    p1 = ease_back(prog(T, end_t, 0.3), 2.5)
    text(ctx, 'JUST A', 540, 330, 150, FONT_TITLE, WHITE, INK, scale=lerp(3, 1, p1) if p1 > 0 else 0, rot=-0.06)
    text(ctx, 'PARROT™', 540, 490, 220, FONT_TITLE, GREEN, INK, lw=26, scale=lerp(3, 1, p1) if p1 > 0 else 0,
         rot=-0.06)
    parrot(ctx, 470, 1420, 1.2, T, acc=('shades', 'medal', 'gradcap'), flap=0.3 * abs(math.sin(T * 5)))
    p2 = ease_back(prog(T, end_t + 0.6, 0.35))
    ctx.save()
    ctx.translate(540, 1530)
    ctx.rotate(-0.03)
    ctx.scale(max(p2, 1e-4), max(p2, 1e-4))
    rrect(ctx, -380, -70, 760, 140, 70)
    fill_stroke(ctx, INK, WHITE, 6)
    text(ctx, 'TAG YOUR KEVIN', 0, 4, 90, FONT_TITLE, YELLOW, None, shadow=False, tracking=3)
    ctx.restore()
    p3 = prog(T, end_t + 1.1, 0.5)
    text_block(ctx, 'Facts as of Sept 2026. Claims marked * are still under expert review. Sources in caption.',
               540, 1670, 32, 860, FONT_BUBBLE, INK, None, 1.05, a=p3, shadow=False, bold=True)
    confetti(ctx, T, end_t)
    flash(ctx, T, end_t, 0.15)


DRAW = {'news': draw_news, 'doc': draw_doc, 'round': draw_round, 'space': draw_space, 'chart': draw_chart,
        'shop': draw_shop, 'finale': draw_finale}

# ============================================================== render
TL = None


def scene_at(scenes, T):
    for i, S in enumerate(scenes):
        if S.start <= T < S.end:
            return i
    return len(scenes) - 1


def render_frame(ctx, scenes, T):
    i = scene_at(scenes, T)
    S = scenes[i]
    ctx.save()
    DRAW[S.kind](ctx, S, T)
    ctx.restore()
    # iris transition from previous scene
    tr = 0.32
    if i > 0 and T - S.start < tr:
        k = ease_io((T - S.start) / tr)
        # draw previous scene outside a growing circle
        ctx.save()
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.rectangle(0, 0, W, H)
        circle(ctx, 540, 960, lerp(0, 1150, k))
        ctx.clip()
        P = scenes[i - 1]
        DRAW[P.kind](ctx, P, P.end - 0.001)
        ctx.restore()
        circle(ctx, 540, 960, lerp(0, 1150, k))
        rgb(ctx, INK)
        ctx.set_line_width(24)
        ctx.stroke()


def worker(args):
    wid, f0, f1, path = args
    scenes = pickle.load(open(os.path.join(OUT, 'timeline.pkl'), 'rb'))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
           path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        T = f / FPS
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        rgb(ctx, (0, 0, 0))
        ctx.paint()
        ctx.restore()
        render_frame(ctx, scenes, T)
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close()
    p.wait()
    return path


def main():
    from multiprocessing import Pool
    scenes, sfx_events, voice_clips, total = build_timeline()
    for S in scenes:
        print('%-7s %6.2f - %6.2f  marks=%s' % (S.kind, S.start, S.end, {k: round(v, 2) for k, v in S.marks.items()}))
    print('TOTAL %.2fs' % total)
    pickle.dump(scenes, open(os.path.join(OUT, 'timeline.pkl'), 'wb'))
    if '--stills' in sys.argv:
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(surf)
        times = [float(x) for x in sys.argv[sys.argv.index('--stills') + 1].split(',')]
        for T in times:
            ctx.save()
            rgb(ctx, (0, 0, 0))
            ctx.paint()
            ctx.restore()
            render_frame(ctx, scenes, T)
            surf.write_to_png(os.path.join(OUT, 'still_%06.2f.png' % T))
        return
    wav = mix_audio(scenes, sfx_events, voice_clips, total)
    nframes = int(total * FPS)
    nw = os.cpu_count() or 4
    chunk = math.ceil(nframes / nw)
    jobs = [(i, i * chunk, min(nframes, (i + 1) * chunk), os.path.join(OUT, 'part%02d.mp4' % i)) for i in range(nw)]
    with Pool(nw) as pool:
        parts = pool.map(worker, jobs)
    lst = os.path.join(OUT, 'parts.txt')
    open(lst, 'w').write(''.join("file '%s'\n" % p for p in parts))
    final = os.path.join(OUT, 'just_a_parrot.mp4')
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav,
                           '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                           final])
    print('wrote', final)


if __name__ == '__main__':
    main()
