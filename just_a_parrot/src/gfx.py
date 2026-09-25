"""Cairo drawing helpers + cartoon characters."""
import math
import cairo

W, H = 1080, 1920
TAU = math.tau

# ---------------------------------------------------------------- palette
INK = (0.08, 0.07, 0.12)
WHITE = (1, 1, 1)
CREAM = (1.0, 0.97, 0.9)
YELLOW = (1.0, 0.84, 0.18)
ORANGE = (1.0, 0.55, 0.12)
RED = (0.93, 0.2, 0.25)
PINK = (1.0, 0.45, 0.62)
GREEN = (0.22, 0.78, 0.36)
DGREEN = (0.1, 0.52, 0.25)
LGREEN = (0.62, 0.92, 0.45)
BLUE = (0.2, 0.5, 0.98)
DBLUE = (0.08, 0.14, 0.38)
CYAN = (0.3, 0.9, 0.95)
PURPLE = (0.55, 0.3, 0.95)
SKIN = (1.0, 0.8, 0.64)
SKIN_D = (0.9, 0.62, 0.48)
GRAY = (0.55, 0.57, 0.62)


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in(t):
    return t ** 3


def ease_io(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_back(t, s=1.9):
    t = t - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_elastic(t):
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * TAU / 3) + 1


def bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


# ---------------------------------------------------------------- primitives
def rgb(ctx, c, a=1.0):
    if len(c) == 4:
        ctx.set_source_rgba(*c)
    else:
        ctx.set_source_rgba(c[0], c[1], c[2], a)


def fill_stroke(ctx, fill, stroke=INK, lw=8, a=1.0):
    if fill is not None:
        rgb(ctx, fill, a)
        if stroke is not None:
            ctx.fill_preserve()
        else:
            ctx.fill()
    if stroke is not None:
        rgb(ctx, stroke, a)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()


def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -TAU / 4, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, TAU / 4)
    ctx.arc(x + r, y + h - r, r, TAU / 4, TAU / 2)
    ctx.arc(x + r, y + r, r, TAU / 2, 3 * TAU / 4)
    ctx.close_path()


def ellipse(ctx, cx, cy, rx, ry):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()


def circle(ctx, cx, cy, r):
    ctx.new_sub_path()
    ctx.arc(cx, cy, max(r, 0.01), 0, TAU)


def poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def bg_fill(ctx, c):
    rgb(ctx, c)
    ctx.paint()


def vgrad(ctx, c1, c2, x0=0, y0=0, x1=0, y1=H):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    g.add_color_stop_rgb(0, *c1)
    g.add_color_stop_rgb(1, *c2)
    ctx.set_source(g)
    ctx.paint()


def sunburst(ctx, cx, cy, t, c1, c2, n=18, speed=0.15):
    rgb(ctx, c1)
    ctx.paint()
    rgb(ctx, c2)
    R = 2600
    for i in range(n):
        a0 = TAU * i / n + t * speed
        a1 = a0 + TAU / n / 2
        ctx.move_to(cx, cy)
        ctx.line_to(cx + R * math.cos(a0), cy + R * math.sin(a0))
        ctx.line_to(cx + R * math.cos(a1), cy + R * math.sin(a1))
        ctx.close_path()
    ctx.fill()


def halftone(ctx, c, a=0.08, step=36, r=6):
    rgb(ctx, c, a)
    for yy in range(0, H + step, step):
        for xx in range(0, W + step, step):
            ox = step / 2 if (yy // step) % 2 else 0
            circle(ctx, xx + ox, yy, r)
    ctx.fill()


# ---------------------------------------------------------------- text
FONT_TITLE = 'Bangers'
FONT_BUBBLE = 'Baloo 2'
FONT_HEAVY = 'Luckiest Guy'
FONT_MONO = 'Space Mono'
FONT_COND = 'Anton'


def set_font(ctx, family, size, bold=False):
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def text_w(ctx, s):
    return ctx.text_extents(s).x_advance


def wrap(ctx, text, maxw):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if text_w(ctx, test) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text(ctx, s, x, y, size, family=FONT_TITLE, fill=WHITE, stroke=INK, lw=None, align='center',
         shadow=True, bold=False, a=1.0, scale=1.0, rot=0.0, tracking=0):
    """Draw outlined meme-style text. (x, y) is the anchor at the text's vertical middle."""
    if a <= 0 or scale <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(scale, scale)
    set_font(ctx, family, size, bold)
    ext = ctx.text_extents(s)
    fe = ctx.font_extents()
    w = ext.x_advance + tracking * max(0, len(s) - 1)
    ox = {'center': -w / 2, 'left': 0, 'right': -w}[align]
    oy = (fe[0] - fe[1]) / 2
    lw = size * 0.16 if lw is None else lw

    def path():
        ctx.new_path()
        if tracking:
            cx_ = ox
            for ch in s:
                ctx.move_to(cx_, oy)
                ctx.text_path(ch)
                cx_ += ctx.text_extents(ch).x_advance + tracking
        else:
            ctx.move_to(ox, oy)
            ctx.text_path(s)

    if shadow and stroke is not None:
        ctx.save()
        ctx.translate(size * 0.06, size * 0.08)
        path()
        rgb(ctx, INK, 0.9 * a)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
        ctx.fill()
        ctx.restore()
    path()
    if stroke is not None:
        rgb(ctx, stroke, a)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    rgb(ctx, fill, a)
    ctx.fill()
    ctx.restore()
    return w


def text_block(ctx, s, x, y, size, maxw, family=FONT_TITLE, fill=WHITE, stroke=INK, line_h=1.1,
               align='center', a=1.0, lw=None, shadow=True, bold=False, words_visible=None, hl=None):
    """Wrapped multi-line text, centered vertically at y. words_visible: reveal count."""
    set_font(ctx, family, size, bold)
    lines = wrap(ctx, s, maxw)
    total = len(lines) * size * line_h
    y0 = y - total / 2 + size * line_h / 2
    shown = 0
    for i, ln in enumerate(lines):
        ws = ln.split()
        if words_visible is not None:
            k = max(0, min(len(ws), words_visible - shown))
            shown += len(ws)
            if k == 0:
                continue
            # draw full-line layout but only first k words: keep positions stable
            set_font(ctx, family, size, bold)
            full_w = text_w(ctx, ln)
            part = ' '.join(ws[:k])
            if align == 'center':
                xx = x - full_w / 2
            elif align == 'left':
                xx = x
            else:
                xx = x - full_w
            text(ctx, part, xx, y0 + i * size * line_h, size, family, fill, stroke, lw, 'left', shadow, bold, a)
        else:
            text(ctx, ln, x, y0 + i * size * line_h, size, family, fill, stroke, lw, align, shadow, bold, a)
    return total, lines


def measure_block(ctx, s, size, maxw, family=FONT_TITLE, line_h=1.1, bold=False):
    set_font(ctx, family, size, bold)
    lines = wrap(ctx, s, maxw)
    return max(text_w(ctx, l) for l in lines), len(lines) * size * line_h, lines


def bubble(ctx, s, x, y, w, size, tail=(0, 0), fill=WHITE, tcol=INK, family=FONT_BUBBLE, words_visible=None,
           pop=1.0, bold=True, shout=False, border=INK):
    """Speech bubble centered at (x, y), tail pointing to absolute point `tail`."""
    if pop <= 0:
        return
    tw, th, lines = measure_block(ctx, s, size, w - 70, family, 1.05, bold)
    bw, bh = max(tw + 80, 260), th + 60
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(pop, 1e-4), max(pop, 1e-4))
    tx, ty = tail[0] - x, tail[1] - y
    # tail
    ang = math.atan2(ty, tx)
    base = 40
    px, py = -math.sin(ang) * base, math.cos(ang) * base
    poly(ctx, [(px * 0.9 + tx * 0.25, py * 0.9 + ty * 0.25), (tx / pop, ty / pop), (-px * 0.9 + tx * 0.25, -py * 0.9 + ty * 0.25)])
    fill_stroke(ctx, fill, border, 9)
    if shout:
        n = 22
        pts = []
        for i in range(n * 2):
            a = TAU * i / (n * 2)
            rr = 1.0 if i % 2 == 0 else 0.86
            pts.append((math.cos(a) * bw * 0.62 * rr, math.sin(a) * bh * 0.72 * rr))
        poly(ctx, pts)
    else:
        rrect(ctx, -bw / 2, -bh / 2, bw, bh, 44)
    fill_stroke(ctx, fill, border, 9)
    # cover tail seam
    poly(ctx, [(px * 0.8 + tx * 0.2, py * 0.8 + ty * 0.2), (tx * 0.35, ty * 0.35), (-px * 0.8 + tx * 0.2, -py * 0.8 + ty * 0.2)])
    rgb(ctx, fill)
    ctx.fill()
    text_block(ctx, s, 0, 4, size, w - 70, family, tcol, None, 1.05, 'center', 1.0, shadow=False, bold=bold,
               words_visible=words_visible)
    ctx.restore()


# ---------------------------------------------------------------- characters
def parrot(ctx, x, y, s, t, mouth=0.0, blink=False, look=(0, 0), mood='normal', flap=0.0, acc=(), tilt=0.0):
    """Cartoon parrot 'Polly' facing right. (x, y) = feet position. s = scale (1 ~ 520px tall)."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    ctx.rotate(tilt)
    bob = math.sin(t * 5.2) * 4
    ctx.translate(0, bob)
    lw = 9
    # tail feathers
    for i, (col, ang) in enumerate([(BLUE, 0.35), (RED, 0.2), (YELLOW, 0.05)]):
        ctx.save()
        ctx.translate(-60, -120)
        ctx.rotate(ang + math.sin(t * 3 + i) * 0.04)
        ctx.move_to(-20, 0)
        ctx.curve_to(-60, 120, -70, 200, -45, 260)
        ctx.curve_to(-20, 210, 10, 120, 25, 0)
        ctx.close_path()
        fill_stroke(ctx, col, INK, lw)
        ctx.restore()
    # feet
    for fx in (-25, 30):
        for k in (-1, 0, 1):
            ctx.move_to(fx, -10)
            ctx.line_to(fx + k * 18, 8)
        rgb(ctx, GRAY)
        ctx.set_line_width(14)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    # body
    ellipse(ctx, 0, -150, 115, 150)
    fill_stroke(ctx, GREEN, INK, lw)
    ellipse(ctx, 22, -115, 62, 100)
    rgb(ctx, LGREEN)
    ctx.fill()
    # lab coat accessory (behind wing)
    if 'labcoat' in acc:
        ctx.move_to(-100, -220)
        ctx.curve_to(-120, -120, -110, -40, -80, -20)
        ctx.line_to(80, -20)
        ctx.curve_to(110, -60, 115, -150, 90, -230)
        ctx.line_to(40, -250)
        ctx.line_to(10, -120)
        ctx.line_to(-30, -250)
        ctx.close_path()
        fill_stroke(ctx, WHITE, INK, lw)
        ctx.move_to(10, -120)
        ctx.line_to(10, -25)
        rgb(ctx, INK)
        ctx.set_line_width(5)
        ctx.stroke()
        rrect(ctx, 30, -150, 40, 30, 6)
        fill_stroke(ctx, (0.85, 0.9, 1), INK, 5)
    # wing
    ctx.save()
    ctx.translate(-30, -210)
    ctx.rotate(-0.15 - flap * 1.1)
    ctx.move_to(0, 0)
    ctx.curve_to(-90, 20, -95, 140, -40, 190)
    ctx.curve_to(10, 150, 40, 60, 0, 0)
    ctx.close_path()
    fill_stroke(ctx, DGREEN, INK, lw)
    for i, c in enumerate((BLUE, RED)):
        ctx.move_to(-45 + i * 12, 120 + i * 20)
        ctx.curve_to(-60, 160, -50, 185, -40, 190)
        ctx.curve_to(-20 + i * 8, 170, -15, 140, -45 + i * 12, 120 + i * 20)
        rgb(ctx, c)
        ctx.fill()
    ctx.restore()
    # head
    hx, hy = 25, -305
    circle(ctx, hx, hy, 98)
    fill_stroke(ctx, GREEN, INK, lw)
    # crest
    for i in range(3):
        ctx.save()
        ctx.translate(hx - 30 + i * 22, hy - 88)
        ctx.rotate(-0.7 + i * 0.3 + math.sin(t * 4 + i) * 0.08)
        ctx.move_to(-12, 10)
        ctx.curve_to(-18, -40, -5, -70, 0, -80)
        ctx.curve_to(10, -60, 18, -30, 12, 10)
        ctx.close_path()
        fill_stroke(ctx, RED, INK, 7)
        ctx.restore()
    circle(ctx, hx, hy, 98)
    rgb(ctx, GREEN)
    ctx.fill()
    # forehead red patch
    ctx.save()
    circle(ctx, hx, hy, 94)
    ctx.clip()
    ellipse(ctx, hx + 35, hy - 80, 70, 40)
    rgb(ctx, RED)
    ctx.fill()
    ellipse(ctx, hx + 10, hy + 40, 50, 40)
    rgb(ctx, YELLOW)
    ctx.fill()
    ctx.restore()
    circle(ctx, hx, hy, 98)
    rgb(ctx, INK)
    ctx.set_line_width(lw)
    ctx.stroke()
    # eye
    ex, ey = hx + 30, hy - 15
    ellipse(ctx, ex, ey, 42, 44)
    fill_stroke(ctx, WHITE, INK, 7)
    if blink:
        ctx.move_to(ex - 30, ey)
        ctx.line_to(ex + 30, ey)
        rgb(ctx, INK)
        ctx.set_line_width(8)
        ctx.stroke()
    else:
        px, py = ex + 8 + look[0] * 12, ey + 2 + look[1] * 12
        r = 16 if mood != 'shock' else 9
        circle(ctx, px, py, r)
        rgb(ctx, INK)
        ctx.fill()
        circle(ctx, px + 5, py - 6, 5)
        rgb(ctx, WHITE)
        ctx.fill()
    # brow for moods
    if mood in ('angry', 'smug', 'sad'):
        ctx.save()
        d = {'angry': 0.35, 'smug': -0.15, 'sad': -0.35}[mood]
        ctx.translate(ex, ey - 55 + (8 if mood == 'angry' else 0))
        ctx.rotate(d)
        ctx.move_to(-40, 0)
        ctx.line_to(40, 0)
        rgb(ctx, INK)
        ctx.set_line_width(12)
        ctx.stroke()
        ctx.restore()
        if mood == 'smug':
            ellipse(ctx, ex, ey - 20, 44, 22)
            rgb(ctx, GREEN)
            ctx.fill()
            ctx.move_to(ex - 42, ey - 4)
            ctx.line_to(ex + 42, ey - 4)
            rgb(ctx, INK)
            ctx.set_line_width(7)
            ctx.stroke()
    # beak
    bx, by = hx + 72, hy + 5
    m = clamp(mouth)
    # lower beak
    ctx.save()
    ctx.translate(bx, by + 18)
    ctx.rotate(m * 0.55)
    ctx.move_to(-10, 0)
    ctx.curve_to(20, 5, 45, 12, 55, 18)
    ctx.curve_to(40, 45, 0, 50, -15, 35)
    ctx.close_path()
    fill_stroke(ctx, (0.3, 0.3, 0.35), INK, 7)
    if m > 0.1:
        ellipse(ctx, 15, 20, 18 * m, 10 * m)
        rgb(ctx, PINK)
        ctx.fill()
    ctx.restore()
    # upper beak (hooked)
    ctx.move_to(bx - 15, by - 40)
    ctx.curve_to(bx + 60, by - 55, bx + 105, by - 10, bx + 80, by + 55)
    ctx.curve_to(bx + 70, by + 30, bx + 40, by + 18, bx - 12, by + 22)
    ctx.close_path()
    fill_stroke(ctx, (0.45, 0.45, 0.52), INK, 7)
    ctx.move_to(bx + 5, by - 30)
    ctx.curve_to(bx + 40, by - 34, bx + 60, by - 20, bx + 68, by)
    rgb(ctx, (1, 1, 1), 0.35)
    ctx.set_line_width(6)
    ctx.stroke()
    # accessories
    if 'glasses' in acc:
        for gx in (ex - 5,):
            circle(ctx, gx, ey, 50)
            rgb(ctx, INK)
            ctx.set_line_width(9)
            ctx.stroke()
        ctx.move_to(ex - 55, ey - 5)
        ctx.line_to(hx - 90, ey - 15)
        ctx.stroke()
    if 'shades' in acc:
        ctx.move_to(ex - 70, ey - 25)
        ctx.line_to(ex + 60, ey - 25)
        ctx.curve_to(ex + 60, ey + 25, ex + 10, ey + 40, ex - 10, ey + 10)
        ctx.curve_to(ex - 30, ey + 40, ex - 70, ey + 20, ex - 70, ey - 25)
        fill_stroke(ctx, INK, INK, 6)
        ctx.move_to(ex + 25, ey - 12)
        ctx.line_to(ex + 45, ey - 12)
        rgb(ctx, WHITE, 0.7)
        ctx.set_line_width(6)
        ctx.stroke()
    if 'gradcap' in acc:
        ctx.save()
        ctx.translate(hx - 5, hy - 95)
        ctx.rotate(-0.12)
        poly(ctx, [(-110, 0), (0, -40), (110, 0), (0, 40)])
        fill_stroke(ctx, INK, INK, 4)
        rrect(ctx, -55, 5, 110, 40, 8)
        fill_stroke(ctx, INK, INK, 4)
        ctx.move_to(0, 0)
        ctx.line_to(80, 20)
        ctx.line_to(85, 80 + math.sin(t * 4) * 6)
        rgb(ctx, YELLOW)
        ctx.set_line_width(6)
        ctx.stroke()
        circle(ctx, 85, 85 + math.sin(t * 4) * 6, 10)
        rgb(ctx, YELLOW)
        ctx.fill()
        ctx.restore()
    if 'medal' in acc:
        ctx.move_to(-40, -250)
        ctx.line_to(20, -140)
        ctx.line_to(80, -255)
        rgb(ctx, RED)
        ctx.set_line_width(18)
        ctx.stroke()
        circle(ctx, 20, -120, 42)
        fill_stroke(ctx, YELLOW, INK, 7)
        circle(ctx, 20, -120, 28)
        rgb(ctx, ORANGE)
        ctx.set_line_width(5)
        ctx.stroke()
        text(ctx, '1', 20, -118, 40, FONT_HEAVY, WHITE, INK, 6, shadow=False)
    ctx.restore()


def kevin(ctx, x, y, s, t, mouth=0.0, blink=False, mood='smug', typing=False, sweat=0.0, look=(0, 0),
          desk=True, sign=None, shake=0.0):
    """The Skeptic, 'Kevin'. Facing left. (x, y) = desk-top center."""
    ctx.save()
    ctx.translate(x + math.sin(t * 60) * shake * 10, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    lw = 9
    bob = math.sin(t * 4) * 3
    # body / hoodie
    ctx.move_to(-190, 40)
    ctx.curve_to(-180, -160, 180, -160, 190, 40)
    ctx.close_path()
    fill_stroke(ctx, hexc('#6c5ce7'), INK, lw)
    # hoodie strings
    for sx in (-30, 30):
        ctx.move_to(sx, -120)
        ctx.line_to(sx - 5, -40)
        rgb(ctx, WHITE)
        ctx.set_line_width(7)
        ctx.stroke()
    ctx.translate(0, bob)
    # neck
    rrect(ctx, -35, -175, 70, 50, 12)
    fill_stroke(ctx, SKIN_D, INK, lw)
    # head
    hx, hy = 0, -290
    ellipse(ctx, hx, hy, 125, 140)
    fill_stroke(ctx, SKIN, INK, lw)
    # ears
    for sx in (-1, 1):
        ellipse(ctx, hx + sx * 125, hy + 10, 22, 32)
        fill_stroke(ctx, SKIN, INK, 7)
    ellipse(ctx, hx, hy, 125, 140)
    rgb(ctx, SKIN)
    ctx.fill()
    # hair: messy tufts
    ctx.move_to(-130, -300)
    tufts = [(-120, -400), (-80, -350), (-60, -440), (-20, -375), (10, -455), (40, -380), (80, -440), (95, -370),
             (130, -400), (128, -300)]
    for px, py in tufts:
        ctx.line_to(px, py + (math.sin(t * 7 + px) * 4 if mood == 'shock' else 0))
    ctx.curve_to(100, -370, -100, -370, -130, -300)
    ctx.close_path()
    fill_stroke(ctx, hexc('#4a2c1a'), INK, lw)
    # backwards cap
    ctx.move_to(-120, -345)
    ctx.curve_to(-110, -450, 110, -450, 120, -345)
    ctx.close_path()
    fill_stroke(ctx, RED, INK, lw)
    rrect(ctx, 95, -360, 70, 26, 12)
    fill_stroke(ctx, RED, INK, 7)
    # eyes + glasses
    eyes = [(-50, -290), (50, -290)]
    for ex, ey in eyes:
        if blink:
            ctx.move_to(ex - 18, ey)
            ctx.line_to(ex + 18, ey)
            rgb(ctx, INK)
            ctx.set_line_width(7)
            ctx.stroke()
        else:
            r = 12 if mood != 'shock' else 7
            if mood == 'shock':
                circle(ctx, ex, ey, 22)
                fill_stroke(ctx, WHITE, INK, 4)
            circle(ctx, ex - 6 + look[0] * 8, ey + look[1] * 8, r)
            rgb(ctx, INK)
            ctx.fill()
        rrect(ctx, ex - 42, ey - 32, 84, 64, 18)
        rgb(ctx, (0.6, 0.85, 1.0), 0.25)
        ctx.fill_preserve()
        rgb(ctx, INK)
        ctx.set_line_width(8)
        ctx.stroke()
    ctx.move_to(-8, -292)
    ctx.line_to(8, -292)
    ctx.set_line_width(8)
    ctx.stroke()
    # brows
    brow = {'smug': (0.25, -0.1, -8), 'angry': (0.35, -0.35, 6), 'shock': (-0.3, 0.3, -22), 'sad': (-0.3, 0.3, -6),
            'normal': (0, 0, 0), 'nervous': (-0.25, 0.25, -10)}[mood]
    for i, (ex, ey) in enumerate(eyes):
        ctx.save()
        ctx.translate(ex, ey - 50 + brow[2] + (-10 if (mood == 'smug' and i == 1) else 0))
        ctx.rotate(brow[i])
        ctx.move_to(-28, 0)
        ctx.line_to(28, 0)
        rgb(ctx, hexc('#4a2c1a'))
        ctx.set_line_width(13)
        ctx.stroke()
        ctx.restore()
    # nose
    ctx.move_to(-10, -265)
    ctx.curve_to(-25, -225, 0, -215, 15, -228)
    rgb(ctx, INK)
    ctx.set_line_width(6)
    ctx.stroke()
    # mouth
    mx, my = 0, -195
    m = clamp(mouth)
    if m > 0.08:
        ellipse(ctx, mx, my, 38 + 6 * m, 8 + 32 * m)
        fill_stroke(ctx, hexc('#5a1020'), INK, 7)
        ctx.save()
        ellipse(ctx, mx, my, 38 + 6 * m, 8 + 32 * m)
        ctx.clip()
        ellipse(ctx, mx, my + 22 * m, 22, 12 * m)
        rgb(ctx, PINK)
        ctx.fill()
        ctx.restore()
    else:
        if mood == 'smug':
            ctx.move_to(mx - 35, my + 2)
            ctx.curve_to(mx - 5, my + 10, mx + 25, my + 5, mx + 42, my - 14)
        elif mood in ('sad', 'nervous'):
            ctx.move_to(mx - 32, my + 8)
            for k in range(4):
                ctx.line_to(mx - 32 + (k + 1) * 16, my + (0 if k % 2 == 0 else 8))
        elif mood == 'shock':
            ellipse(ctx, mx, my, 22, 30)
        else:
            ctx.move_to(mx - 30, my)
            ctx.curve_to(mx - 10, my + 12, mx + 10, my + 12, mx + 30, my)
        rgb(ctx, INK)
        ctx.set_line_width(8)
        ctx.stroke()
    # sweat
    if sweat > 0:
        for k, (sx, sy) in enumerate([(115, -350), (-120, -330)]):
            yy = sy + ((t * 90 + k * 40) % 80) * sweat
            ctx.move_to(sx, yy - 30)
            ctx.curve_to(sx + 18, yy, sx + 14, yy + 18, sx, yy + 18)
            ctx.curve_to(sx - 14, yy + 18, sx - 18, yy, sx, yy - 30)
            fill_stroke(ctx, (0.55, 0.85, 1.0), INK, 5, a=clamp(sweat))
    ctx.translate(0, -bob)
    # desk + laptop
    if desk:
        # hands
        for sx in (-1, 1):
            hxx = sx * 110 + (math.sin(t * 30 + sx) * 8 if typing else 0)
            hyy = 30 + (abs(math.sin(t * 25 + sx * 2)) * -10 if typing else 0)
            ellipse(ctx, hxx, hyy, 40, 28)
            fill_stroke(ctx, SKIN, INK, 7)
        # laptop back (we see the lid from the front-ish: facing Kevin)
        ctx.move_to(-170, 60)
        ctx.line_to(-140, -60)
        ctx.line_to(140, -60)
        ctx.line_to(170, 60)
        ctx.close_path()
        fill_stroke(ctx, (0.78, 0.8, 0.85), INK, lw)
        text(ctx, 'NO AI', 0, 0, 44, FONT_HEAVY, RED, INK, 6, shadow=False, rot=-0.08)
        ctx.move_to(-80, 25)
        ctx.line_to(80, -30)
        rgb(ctx, RED)
        ctx.set_line_width(8)
        ctx.stroke()
        # desk
        rrect(ctx, -330, 55, 660, 60, 12)
        fill_stroke(ctx, hexc('#c98b4f'), INK, lw)
    if sign:
        ctx.save()
        ctx.translate(-10, -40)
        ctx.rotate(-0.05 + math.sin(t * 3) * 0.03)
        rrect(ctx, -12, -40, 24, 260, 6)
        fill_stroke(ctx, hexc('#c98b4f'), INK, 7)
        rrect(ctx, -230, -250, 460, 220, 14)
        fill_stroke(ctx, CREAM, INK, 9)
        text_block(ctx, sign, 0, -140, 58, 420, FONT_HEAVY, INK, None, 1.0, shadow=False)
        ctx.restore()
    ctx.restore()


def goalpost(ctx, x, y, s, col=YELLOW, a=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    ctx.move_to(0, 0)
    ctx.line_to(0, -120)
    ctx.move_to(-80, -120)
    ctx.line_to(80, -120)
    ctx.move_to(-80, -120)
    ctx.line_to(-80, -300)
    ctx.move_to(80, -120)
    ctx.line_to(80, -300)
    rgb(ctx, INK, a)
    ctx.set_line_width(26)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke_preserve()
    rgb(ctx, col, a)
    ctx.set_line_width(14)
    ctx.stroke()
    ctx.restore()


def brick_wall(ctx, x0, y0, w, h, t=0, broken=None, label=True, bw=150, bh=64):
    """Brick wall. broken: (cx, cy, r, amount) hole."""
    ctx.save()
    rows = int(h / bh) + 1
    for r in range(rows):
        off = (bw / 2) if r % 2 else 0
        for c in range(-1, int(w / bw) + 2):
            bx = x0 + c * bw - off
            by = y0 + r * bh
            if bx + bw < x0 or bx > x0 + w:
                continue
            ccx, ccy = bx + bw / 2, by + bh / 2
            dx, dy, fl = 0, 0, 0
            if broken:
                hx, hy, hr, amt = broken
                d = math.hypot(ccx - hx, ccy - hy)
                if d < hr:
                    if amt >= 1:
                        continue
                    k = (hr - d) / hr
                    ang = math.atan2(ccy - hy, ccx - hx) + (c * 1.7 + r) % 0.7
                    dist = amt * 1400 * (0.4 + k)
                    dx = math.cos(ang) * dist
                    dy = math.sin(ang) * dist + 2200 * amt * amt
                    fl = amt * (c * 3 + r * 2 % 5 - 3) * 2
            ctx.save()
            ctx.translate(ccx + dx, ccy + dy)
            ctx.rotate(fl)
            shade = 0.72 + ((c * 7 + r * 13) % 5) * 0.035
            rrect(ctx, -bw / 2 + 3, -bh / 2 + 3, bw - 6, bh - 6, 6)
            fill_stroke(ctx, (shade, 0.3 * shade + 0.05, 0.22 * shade), INK, 5)
            ctx.restore()
    ctx.restore()


def rocket_trail(ctx, x, y, ang, t, length=500):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    for i in range(14):
        k = i / 14
        r = 50 * (1 - k) + 12 + 6 * math.sin(t * 40 + i)
        circle(ctx, -60 - k * length, math.sin(t * 30 + i * 1.3) * 12 * k, r)
        c = (1, 0.9 - 0.6 * k, 0.2 * (1 - k))
        rgb(ctx, c, 0.9 * (1 - k))
        ctx.fill()
    ctx.restore()


def star(ctx, x, y, r1, r2, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = rot + math.pi * i / n
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    poly(ctx, pts)


def burst(ctx, x, y, r, n=14, col=YELLOW, rot=0.0, lw=9):
    star(ctx, x, y, r, r * 0.72, n, rot)
    fill_stroke(ctx, col, INK, lw)


def check_stamp(ctx, x, y, s, a=1.0, rot=-0.2, label='SOLVED', col=GREEN):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    rrect(ctx, -220, -75, 440, 150, 22)
    rgb(ctx, col, a)
    ctx.set_line_width(14)
    ctx.stroke()
    rrect(ctx, -200, -57, 400, 114, 14)
    ctx.set_line_width(5)
    ctx.stroke()
    text(ctx, label, 0, 4, 100, FONT_TITLE, col, None, shadow=False, a=a)
    ctx.restore()


def fit_size(ctx, s, size, maxw, family, bold=False):
    set_font(ctx, family, size, bold)
    w = text_w(ctx, s)
    return size if w <= maxw else size * maxw / w


def anchor(ctx, x, y, s, t, mouth=0.0, blink=False, mood='normal'):
    """TV news anchor. (x, y) = desk-top center."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    lw = 9
    # suit
    ctx.move_to(-230, 60)
    ctx.curve_to(-220, -170, 220, -170, 230, 60)
    ctx.close_path()
    fill_stroke(ctx, hexc('#2d3a5a'), INK, lw)
    poly(ctx, [(-60, -135), (0, -20), (60, -135)])
    fill_stroke(ctx, WHITE, INK, 6)
    poly(ctx, [(-14, -120), (14, -120), (22, -40), (0, -10), (-22, -40)])
    fill_stroke(ctx, RED, INK, 6)
    for sx in (-1, 1):
        poly(ctx, [(sx * 60, -135), (sx * 20, -40), (sx * 110, -100)])
        fill_stroke(ctx, hexc('#24304d'), INK, 6)
    # head
    hx, hy = 0, -290
    rrect(ctx, -32, -190, 64, 60, 12)
    fill_stroke(ctx, SKIN_D, INK, lw)
    for sx in (-1, 1):
        ellipse(ctx, hx + sx * 118, hy + 10, 20, 30)
        fill_stroke(ctx, SKIN, INK, 7)
    ellipse(ctx, hx, hy, 118, 135)
    fill_stroke(ctx, SKIN, INK, lw)
    # slick helmet hair
    ctx.move_to(-122, -290)
    ctx.curve_to(-140, -420, 60, -470, 125, -330)
    ctx.curve_to(125, -300, 110, -290, 118, -280)
    ctx.curve_to(60, -370, -40, -360, -122, -290)
    ctx.close_path()
    fill_stroke(ctx, hexc('#2b2b2b'), INK, lw)
    ctx.move_to(-60, -390)
    ctx.curve_to(0, -420, 60, -400, 90, -360)
    rgb(ctx, WHITE, 0.5)
    ctx.set_line_width(8)
    ctx.stroke()
    for ex in (-45, 45):
        ey = -290
        if blink:
            ctx.move_to(ex - 16, ey)
            ctx.line_to(ex + 16, ey)
            rgb(ctx, INK)
            ctx.set_line_width(7)
            ctx.stroke()
        else:
            circle(ctx, ex, ey, 11)
            rgb(ctx, INK)
            ctx.fill()
        ctx.move_to(ex - 26, ey - 40 - (8 if mood == 'serious' else 0))
        ctx.line_to(ex + 26, ey - 44 + (6 if mood == 'serious' and ex < 0 else 0))
        rgb(ctx, hexc('#2b2b2b'))
        ctx.set_line_width(11)
        ctx.stroke()
    ctx.move_to(-5, -265)
    ctx.curve_to(-20, -230, 5, -222, 15, -232)
    rgb(ctx, INK)
    ctx.set_line_width(6)
    ctx.stroke()
    m = clamp(mouth)
    if m > 0.08:
        rrect(ctx, -46, -205 - 4, 92, 12 + 34 * m, 14)
        fill_stroke(ctx, hexc('#5a1020'), INK, 7)
        rrect(ctx, -38, -205 - 2, 76, 12, 5)
        rgb(ctx, WHITE)
        ctx.fill()
    else:
        ctx.move_to(-50, -205)
        ctx.curve_to(-20, -180, 20, -180, 50, -205)
        ctx.close_path()
        fill_stroke(ctx, WHITE, INK, 7)
    # desk
    poly(ctx, [(-420, 40), (420, 40), (380, 320), (-380, 320)])
    fill_stroke(ctx, hexc('#c0392b'), INK, lw)
    ctx.restore()
