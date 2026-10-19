import re
import math


class Color:
    RESET = "\033[0m"

    BLACK          = "\033[30m"
    RED            = "\033[31m"
    GREEN          = "\033[32m"
    YELLOW         = "\033[33m"
    BLUE           = "\033[34m"
    MAGENTA        = "\033[35m"
    CYAN           = "\033[36m"
    WHITE          = "\033[37m"

    BRIGHT_BLACK   = "\033[90m"
    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"

    BG_BLACK   = "\033[40m"
    BG_RED     = "\033[41m"
    BG_GREEN   = "\033[42m"
    BG_YELLOW  = "\033[43m"
    BG_BLUE    = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN    = "\033[46m"
    BG_WHITE   = "\033[47m"

    @staticmethod
    def rgb(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg_rgb(r, g, b):
        return f"\033[48;2;{r};{g};{b}m"

    @staticmethod
    def color256(n):
        return f"\033[38;5;{n}m"

    @staticmethod
    def bg_color256(n):
        return f"\033[48;5;{n}m"

    @staticmethod
    def gradient_text(text, start_rgb, end_rgb):
        if len(text) <= 1:
            r, g, b = start_rgb
            return f"{Color.rgb(r, g, b)}{text}{Color.RESET}"
        result = ""
        n = len(text)
        for i, ch in enumerate(text):
            t = i / (n - 1)
            r = int(start_rgb[0] + t * (end_rgb[0] - start_rgb[0]))
            g = int(start_rgb[1] + t * (end_rgb[1] - start_rgb[1]))
            b = int(start_rgb[2] + t * (end_rgb[2] - start_rgb[2]))
            result += f"{Color.rgb(r, g, b)}{ch}"
        return result + Color.RESET

    @staticmethod
    def multi_gradient(text, *stops):
        if not stops:
            return text
        if len(stops) == 1:
            r, g, b = stops[0]
            return f"{Color.rgb(r, g, b)}{text}{Color.RESET}"
        n = len(text)
        segs = len(stops) - 1
        result = ""
        for i, ch in enumerate(text):
            pos = (i / max(n - 1, 1)) * segs
            seg = min(int(pos), segs - 1)
            lt = pos - seg
            sr, sg, sb = stops[seg]
            er, eg, eb = stops[seg + 1]
            r = int(sr + lt * (er - sr))
            g = int(sg + lt * (eg - sg))
            b = int(sb + lt * (eb - sb))
            result += f"{Color.rgb(r, g, b)}{ch}"
        return result + Color.RESET

    @staticmethod
    def rainbow(text):
        """full HSV hue rotation across text — red→yellow→green→cyan→blue→magenta→red"""
        result = ""
        n = max(len(text), 1)
        for i, ch in enumerate(text):
            h = (i / n) * 360
            r, g, b = Color._hsv_to_rgb(h, 1.0, 1.0)
            result += f"{Color.rgb(r, g, b)}{ch}"
        return result + Color.RESET

    @staticmethod
    def _hsv_to_rgb(h, s, v):
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        if   h < 60:  r, g, b = c, x, 0
        elif h < 120: r, g, b = x, c, 0
        elif h < 180: r, g, b = 0, c, x
        elif h < 240: r, g, b = 0, x, c
        elif h < 300: r, g, b = x, 0, c
        else:         r, g, b = c, 0, x
        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

    @staticmethod
    def pulse(rgb_tuple, t):
        """sinusoidal brightness — t in [0, 1], returns rgb string at that brightness"""
        brightness = 0.4 + 0.6 * math.sin(t * math.pi)
        r = int(rgb_tuple[0] * brightness)
        g = int(rgb_tuple[1] * brightness)
        b = int(rgb_tuple[2] * brightness)
        return Color.rgb(r, g, b)

    @staticmethod
    def blend(c1, c2, t):
        """lerp between two rgb tuples — returns tuple, not escape code"""
        t = max(0.0, min(1.0, t))
        return (
            int(c1[0] + t * (c2[0] - c1[0])),
            int(c1[1] + t * (c2[1] - c1[1])),
            int(c1[2] + t * (c2[2] - c1[2])),
        )

    @staticmethod
    def dim_rgb(rgb_tuple, factor=0.5):
        """multiply brightness of an rgb tuple"""
        r, g, b = rgb_tuple
        return Color.rgb(int(r * factor), int(g * factor), int(b * factor))

    @staticmethod
    def from_hex(hex_str):
        """'#ff6600' or 'ff6600' → Color.rgb(...)"""
        h = hex_str.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return Color.rgb(r, g, b)

    @staticmethod
    def strip(s):
        return re.sub(r"\033\[[0-9;]*m", "", s)

    @staticmethod
    def bold(s):
        return f"\033[1m{s}\033[0m"

    @staticmethod
    def italic(s):
        return f"\033[3m{s}\033[0m"

    @staticmethod
    def underline(s):
        return f"\033[4m{s}\033[0m"

    @staticmethod
    def strike(s):
        return f"\033[9m{s}\033[0m"

    @staticmethod
    def dim_text(s):
        return f"\033[2m{s}\033[0m"


class Gradient:
    FIRE    = [(255, 50,  0),   (255, 150, 0),  (255, 255, 0)]
    OCEAN   = [(0,   30,  80),  (0,   100, 200), (0,   200, 255)]
    NEON    = [(255, 0,   128), (128, 0,   255), (0,   200, 255)]
    MATRIX  = [(0,   20,  0),   (0,   200, 50)]
    GOLD    = [(200, 150, 0),   (255, 220, 50),  (200, 150, 0)]
    BLOOD   = [(80,  0,   0),   (200, 0,   0),   (255, 50,  50)]
    CYBER   = [(0,   255, 200), (0,   100, 255), (200, 0,   255)]
    DISCORD = [(88,  101, 242), (155, 89,  182), (88,  101, 242)]
    CANDY   = [(255, 100, 150), (255, 200, 100), (100, 200, 255)]
    TOXIC   = [(50,  255, 0),   (200, 255, 0),   (0,   200, 100)]
    VOID    = [(20,  0,   40),  (80,  0,   160), (180, 0,   255)]
    LAVA    = [(255, 0,   0),   (255, 80,  0),   (255, 200, 0)]
    SUNSET  = [(255, 80,  0),   (220, 20,  80),  (100, 0,   180)]
    ARCTIC  = [(100, 200, 255), (200, 240, 255),  (80, 160, 220)]
    RUST    = [(100, 30,  0),   (180, 70,  10),  (220, 140, 60)]
    ACID    = [(100, 255, 0),   (200, 255, 50),  (50,  200, 0)]
    GHOST   = [(60,  60,  80),  (140, 140, 180), (60,  60,  80)]
    INFRA   = [(0,   0,   60),  (100, 0,   100), (255, 0,   80),  (255, 200, 0)]
    ROYAL   = [(80,  0,   180), (160, 80,  255), (80,  0,   180)]

    @staticmethod
    def from_hex(h1, h2, *rest):
        """build a gradient stop list from hex strings"""
        def _parse(h):
            h = h.lstrip("#")
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        return [_parse(h) for h in (h1, h2, *rest)]

    @staticmethod
    def interpolate(stops, n):
        """expand a stop list to n evenly-spaced rgb tuples"""
        if n <= 1:
            return [stops[0]]
        out = []
        segs = len(stops) - 1
        for i in range(n):
            t = (i / (n - 1)) * segs
            s = min(int(t), segs - 1)
            lt = t - s
            c = Color.blend(stops[s], stops[s + 1], lt)
            out.append(c)
        return out
