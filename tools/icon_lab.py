"""Generates AppIcon.icon for the 'teleport' mark: origin ring -> arc -> pin.

usage: icon_lab.py OUT_DIR [--flat]
Writes OUT_DIR/AppIcon.icon (SVG layers + icon.json) and, with --flat,
rough flat previews OUT_DIR/flat-light.png and flat-dark.png.
All geometry is on Apple's 1024 icon canvas.
"""
import json
import math
import os
import sys

# ---------------------------------------------------------------- design
DX, DY = -18, -44                     # optical centring of the whole mark
ORIGIN = (300 + DX, 748 + DY)
RING_OUT, RING_IN = 86, 44
PIN_C = (706 + DX, 486 + DY)
PIN_R = 172
PIN_TIP = (706 + DX, 782 + DY)
HOLE_R = 64
# an even hop from the top of the ring, peaking between the two, landing in the pin's head
ARC = ((318 + DX, 670 + DY), (470 + DX, 170 + DY), (640 + DX, 628 + DY))   # start, control, end
ARC_W = (36, 72)                      # width at start, width at end: it grows as it travels
STYLE = "hop"                         # "hop": one solid arc; "dots": a trail of growing dots
DOTS = 5                              # dots in the trail, all in the open between ring and pin

C = {  # display-p3 colours
    "bg_top": (0.965, 0.978, 1.000), "bg_bottom": (0.835, 0.895, 0.985),
    "bg_top_dark": (0.070, 0.110, 0.200), "bg_bottom_dark": (0.020, 0.035, 0.070),
    "pin": (0.040, 0.400, 0.960), "pin_dark": (0.250, 0.560, 1.000),
    "ring": (0.200, 0.740, 0.980), "ring_dark": (0.300, 0.800, 1.000),
    "arc": (0.420, 0.690, 1.000), "arc_dark": (0.450, 0.700, 1.000),
}

# group settings, front to back: (shadow opacity, translucency)
GLASS = {"pin": (0.50, 0.10), "ring": (0.40, 0.25), "arc": (0.30, 0.40)}


# ---------------------------------------------------------------- geometry
def quad(p0, p1, p2, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])


def quad_d(p0, p1, p2, t):
    return (2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0]),
            2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1]))


def arc_polygon(steps=96):
    """The arc as a filled band whose width grows from ARC_W[0] to ARC_W[1], round-capped."""
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        x, y = quad(*ARC, t)
        dx, dy = quad_d(*ARC, t)
        n = math.hypot(dx, dy)
        nx, ny = -dy / n, dx / n
        w = (ARC_W[0] + (ARC_W[1] - ARC_W[0]) * t) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))

    def cap(center, w, a_from, a_to, steps=16):
        return [(center[0] + w * math.cos(a_from + (a_to - a_from) * i / steps),
                 center[1] + w * math.sin(a_from + (a_to - a_from) * i / steps)) for i in range(1, steps)]

    end = quad(*ARC, 1)
    a_end = math.atan2(*reversed(quad_d(*ARC, 1)))
    start = quad(*ARC, 0)
    a_start = math.atan2(*reversed(quad_d(*ARC, 0)))
    # left side runs along +normal (angle + pi/2); caps sweep around the far side
    end_cap = cap(end, ARC_W[1] / 2, a_end + math.pi / 2, a_end - math.pi / 2)
    start_cap = cap(start, ARC_W[0] / 2, a_start - math.pi / 2, a_start - 3 * math.pi / 2)
    return left + end_cap + right[::-1] + start_cap


def pin_tangents():
    cx, cy = PIN_C
    d = PIN_TIP[1] - cy
    a = math.acos(PIN_R / d)
    return ((cx - PIN_R * math.sin(a), cy + PIN_R * math.cos(a)),
            (cx + PIN_R * math.sin(a), cy + PIN_R * math.cos(a)))


def pin_outline(steps=180):
    (cx, cy), r = PIN_C, PIN_R
    (lx, ly), (rx, ry) = pin_tangents()
    a0 = math.atan2(ly - cy, lx - cx)
    a1 = math.atan2(ry - cy, rx - cx)
    span = 2 * math.pi - (a0 - a1)          # the long way round, over the top
    return [PIN_TIP] + [(cx + r * math.cos(a0 + span * i / steps), cy + r * math.sin(a0 + span * i / steps))
                        for i in range(steps + 1)]


# ---------------------------------------------------------------- SVG
def svg(body):
    return f'<svg width="1024" height="1024" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">\n{body}\n</svg>\n'


def path_d(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"


def circle_d(c, r):
    x, y = c
    return f"M{x} {y - r} A{r} {r} 0 1 1 {x} {y + r} A{r} {r} 0 1 1 {x} {y - r} Z"


def pin_svg():
    return svg(f'  <path fill="#FFFFFF" fill-rule="evenodd" d="{path_d(pin_outline())} {circle_d(PIN_C, HOLE_R)}"/>')


def ring_svg():
    return svg(f'  <path fill="#FFFFFF" fill-rule="evenodd" d="{circle_d(ORIGIN, RING_OUT)} {circle_d(ORIGIN, RING_IN)}"/>')


def dot_trail():
    """(centre, radius) along the arc, growing towards the pin."""
    # Space the dots evenly by distance along the curve, not by curve parameter,
    # or they bunch up at the top of the hop.
    samples = [quad(*ARC, i / 400) for i in range(401)]
    lengths = [0.0]
    for a, b in zip(samples, samples[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    out = []
    for i in range(DOTS):
        f = i / (DOTS - 1)
        target = lengths[-1] * (0.10 + 0.66 * f)
        j = next(k for k, v in enumerate(lengths) if v >= target)
        out.append((samples[j], ARC_W[0] / 2 + (ARC_W[1] - ARC_W[0]) / 2 * f + 2))
    return out


def arc_svg():
    if STYLE == "dots":
        dots = [f'  <path fill="#FFFFFF" d="{circle_d((round(c[0], 1), round(c[1], 1)), round(r, 1))}"/>'
                for c, r in dot_trail()]
        return svg("\n".join(dots))
    return svg(f'  <path fill="#FFFFFF" d="{path_d(arc_polygon())}"/>')


# ---------------------------------------------------------------- icon.json
def p3(c, a=1.0):
    return "display-p3:" + ",".join(f"{v:.5f}" for v in (*c, a))


def layer(name, image, key):
    return {
        "name": name, "image-name": image, "glass": True,
        "fill-specializations": [
            {"value": {"solid": p3(C[key])}},
            {"appearance": "dark", "value": {"solid": p3(C[key + "_dark"])}},
        ],
    }


def group(lyr, key):
    shadow, translucency = GLASS[key]
    return {"layers": [lyr], "specular": True,
            "shadow": {"kind": "layer-color", "opacity": shadow},
            "translucency": {"enabled": True, "value": translucency}}


def icon_json():
    return {
        "fill-specializations": [
            {"value": {"linear-gradient": [p3(C["bg_top"]), p3(C["bg_bottom"])]}},
            {"appearance": "dark", "value": {"linear-gradient": [p3(C["bg_top_dark"]), p3(C["bg_bottom_dark"])]}},
        ],
        # the first group is the frontmost
        "groups": [
            group(layer("Pin", "Pin.svg", "pin"), "pin"),
            group(layer("Origin", "Origin.svg", "ring"), "ring"),
            group(layer("Arc", "Arc.svg", "arc"), "arc"),
        ],
        "supported-platforms": {"circles": ["watchOS"], "squares": "shared"},
    }


def write_bundle(out):
    bundle = os.path.join(out, "AppIcon.icon")
    assets = os.path.join(bundle, "Assets")
    os.makedirs(assets, exist_ok=True)
    for f in os.listdir(assets):
        os.remove(os.path.join(assets, f))
    for name, body in (("Pin.svg", pin_svg()), ("Origin.svg", ring_svg()), ("Arc.svg", arc_svg())):
        with open(os.path.join(assets, name), "w", newline="\n") as f:
            f.write(body)
    with open(os.path.join(bundle, "icon.json"), "w", newline="\n") as f:
        json.dump(icon_json(), f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- flat preview
def flat(out, dark=False):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    S = 3
    N = 1024 * S

    def rgb(k):
        return tuple(int(v * 255) for v in C[k + ("_dark" if dark else "")])

    top, bot = (C["bg_top_dark"], C["bg_bottom_dark"]) if dark else (C["bg_top"], C["bg_bottom"])
    img = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        img.putpixel((0, y), tuple(int(255 * (top[i] + (bot[i] - top[i]) * t)) for i in range(3)))
    img = img.resize((N, N), Image.BICUBIC)

    def sc(pts):
        return [(x * S, y * S) for x, y in pts]

    def ell(d, c, r, fill):
        d.ellipse([(c[0] - r) * S, (c[1] - r) * S, (c[0] + r) * S, (c[1] + r) * S], fill=fill)

    arc_m = Image.new("L", (N, N), 0)
    if STYLE == "dots":
        d = ImageDraw.Draw(arc_m)
        for c, r in dot_trail():
            ell(d, c, r, 255)
    else:
        ImageDraw.Draw(arc_m).polygon(sc(arc_polygon()), fill=255)
    ring_m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(ring_m)
    ell(d, ORIGIN, RING_OUT, 255)
    ell(d, ORIGIN, RING_IN, 0)
    pin_m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(pin_m)
    d.polygon(sc(pin_outline()), fill=255)
    ell(d, PIN_C, HOLE_R, 0)

    for m, key, alpha in ((arc_m, "arc", 0.62), (ring_m, "ring", 0.82), (pin_m, "pin", 0.92)):
        sh = ImageChops.offset(m.filter(ImageFilter.GaussianBlur(16 * S)), 0, 12 * S).point(lambda v: int(v * 0.28))
        img = Image.composite(Image.new("RGB", (N, N), tuple(int(c * 0.55) for c in rgb(key))), img, sh)
        img = Image.composite(Image.new("RGB", (N, N), rgb(key)), img, m.point(lambda v, a=alpha: int(v * a)))
        rim = ImageChops.subtract(m, ImageChops.offset(m, 4 * S, 7 * S)).filter(ImageFilter.GaussianBlur(2 * S))
        img = Image.composite(Image.new("RGB", (N, N), (255, 255, 255)), img, rim.point(lambda v: int(v * 0.75)))
    img = img.resize((1024, 1024), Image.LANCZOS)
    img.save(os.path.join(out, "flat-dark.png" if dark else "flat-light.png"))


if __name__ == "__main__":
    out_dir = sys.argv[1]
    for arg in sys.argv[2:]:
        if arg.startswith("--style="):
            STYLE = arg.split("=", 1)[1]
        elif arg.startswith("--pin="):        # --pin=r,g,b  (display-p3, 0..1)
            C["pin"] = tuple(float(v) for v in arg.split("=", 1)[1].split(","))
        elif arg.startswith("--pin-dark="):
            C["pin_dark"] = tuple(float(v) for v in arg.split("=", 1)[1].split(","))
        elif arg.startswith("--pin-glass="):  # translucency of the pin group
            GLASS["pin"] = (GLASS["pin"][0], float(arg.split("=", 1)[1]))
    os.makedirs(out_dir, exist_ok=True)
    write_bundle(out_dir)
    if "--flat" in sys.argv:
        flat(out_dir)
        flat(out_dir, dark=True)
