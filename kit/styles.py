import re
import shutil
from .colors import Color


class Style:
    BOLD      = "\033[1m"
    DIM       = "\033[2m"
    ITALIC    = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK     = "\033[5m"
    REVERSE   = "\033[7m"
    STRIKE    = "\033[9m"
    RESET     = "\033[0m"


class BorderStyle:
    SINGLE = {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h":  "─", "v":  "│", "mt": "┬", "mb": "┴",
        "ml": "├", "mr": "┤", "c":  "┼",
    }
    DOUBLE = {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h":  "═", "v":  "║", "mt": "╦", "mb": "╩",
        "ml": "╠", "mr": "╣", "c":  "╬",
    }
    ROUNDED = {
        "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
        "h":  "─", "v":  "│", "mt": "┬", "mb": "┴",
        "ml": "├", "mr": "┤", "c":  "┼",
    }
    BOLD = {
        "tl": "┏", "tr": "┓", "bl": "┗", "br": "┛",
        "h":  "━", "v":  "┃", "mt": "┳", "mb": "┻",
        "ml": "┣", "mr": "┫", "c":  "╋",
    }
    ASCII = {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h":  "-", "v":  "|", "mt": "+", "mb": "+",
        "ml": "+", "mr": "+", "c":  "+",
    }
    DOTTED = {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h":  "┄", "v":  "┆", "mt": "┬", "mb": "┴",
        "ml": "├", "mr": "┤", "c":  "┼",
    }
    OUTER_HEAVY = {
        "tl": "┏", "tr": "┓", "bl": "┗", "br": "┛",
        "h":  "━", "v":  "┃", "mt": "┯", "mb": "┷",
        "ml": "┠", "mr": "┨", "c":  "┼",
    }
    MINIMAL = {
        "tl": " ", "tr": " ", "bl": " ", "br": " ",
        "h":  "─", "v":  " ", "mt": "─", "mb": "─",
        "ml": " ", "mr": " ", "c":  "─",
    }


def strip_ansi(s):
    return re.sub(r"\033\[[0-9;]*m", "", s)


def term_width():
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def render_panel(
    content_lines,
    title=None,
    border=None,
    border_color=None,
    title_color=None,
    padding=1,
    width=None,
):
    b  = border or BorderStyle.ROUNDED
    bc = border_color or ""
    tc = title_color or (border_color or Color.BRIGHT_WHITE)
    R  = Color.RESET
    pad = " " * padding

    raw_lines = [strip_ansi(l) for l in content_lines]
    content_w = max((len(l) for l in raw_lines), default=0)
    if title:
        content_w = max(content_w, len(strip_ansi(title)) + 4)
    inner_w = content_w + padding * 2
    if width is not None:
        inner_w = max(width - 2, inner_w)

    lines = []
    if title:
        raw_title = len(strip_ansi(title)) + 2
        lh = b["h"] * 2
        rh = b["h"] * max(0, inner_w - 2 - raw_title)
        lines.append(f"{bc}{b['tl']}{lh} {tc}{title}{R}{bc} {rh}{b['tr']}{R}")
    else:
        lines.append(f"{bc}{b['tl']}{b['h'] * inner_w}{b['tr']}{R}")

    for line in content_lines:
        spaces = max(0, inner_w - padding * 2 - len(strip_ansi(line)))
        lines.append(f"{bc}{b['v']}{R}{pad}{line}{' ' * spaces}{pad}{bc}{b['v']}{R}")

    lines.append(f"{bc}{b['bl']}{b['h'] * inner_w}{b['br']}{R}")
    return "\n".join(lines)


def render_table(
    headers,
    rows,
    border=None,
    header_color=None,
    border_color=None,
    col_colors=None,
    zebra=False,
    zebra_color=None,
    align=None,
):
    b  = border or BorderStyle.SINGLE
    hc = header_color or (Style.BOLD + Color.BRIGHT_CYAN)
    bc = border_color or Color.BRIGHT_BLACK
    zc = zebra_color or Color.rgb(20, 20, 30)
    R  = Color.RESET

    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    _align = align or ["left"] * len(headers)

    def _cell(text, width, a):
        s = str(text)
        if a == "right":  return s.rjust(width)
        if a == "center": return s.center(width)
        return s.ljust(width)

    def h_line(left, mid, right, fill):
        segs = [fill * (w + 2) for w in col_widths]
        return f"{bc}{left}{mid.join(segs)}{right}{R}"

    def data_row(cells, color="", bg=""):
        parts = []
        for i, cell in enumerate(cells):
            c = (col_colors[i] if col_colors and i < len(col_colors) else "") or color
            w = col_widths[i] if i < len(col_widths) else 0
            a = _align[i] if i < len(_align) else "left"
            parts.append(f" {bg}{c}{_cell(cell, w, a)}{R} ")
        sep = f"{bc}{b['v']}{R}"
        return f"{bc}{b['v']}{R}" + sep.join(parts) + f"{bc}{b['v']}{R}"

    lines = [
        h_line(b["tl"], b["mt"], b["tr"], b["h"]),
        data_row([str(h) for h in headers], hc),
        h_line(b["ml"], b["c"], b["mr"], b["h"]),
    ]
    for ri, row in enumerate(rows):
        bg = f"{zc}" if zebra and ri % 2 == 1 else ""
        lines.append(data_row([str(c) for c in row], bg=bg))
    lines.append(h_line(b["bl"], b["mb"], b["br"], b["h"]))
    return "\n".join(lines)


def render_two_col(
    left_lines,
    right_lines,
    gap=4,
    left_width=None,
    right_width=None,
    left_border=None,
    right_border=None,
    left_border_color=None,
    right_border_color=None,
    left_title=None,
    right_title=None,
):
    tw = term_width()
    lw = left_width or (tw // 2 - gap)
    rw = right_width or (tw - lw - gap)

    lp = render_panel(
        left_lines,
        title=left_title,
        border=left_border or BorderStyle.ROUNDED,
        border_color=left_border_color or Color.BRIGHT_BLACK,
        width=lw,
    )
    rp = render_panel(
        right_lines,
        title=right_title,
        border=right_border or BorderStyle.ROUNDED,
        border_color=right_border_color or Color.BRIGHT_BLACK,
        width=rw,
    )

    l_rows = lp.splitlines()
    r_rows = rp.splitlines()
    pad_to = max(len(l_rows), len(r_rows))
    l_raw_w = max((len(strip_ansi(ln)) for ln in l_rows), default=0)

    out = []
    for i in range(pad_to):
        l = l_rows[i] if i < len(l_rows) else ""
        r = r_rows[i] if i < len(r_rows) else ""
        l_pad = l_raw_w - len(strip_ansi(l))
        out.append(f"{l}{' ' * (l_pad + gap)}{r}")
    return "\n".join(out)


def render_header(
    title,
    subtitle=None,
    gradient=None,
    border_color=None,
    width=None,
    border=None,
):
    from .colors import Gradient
    w   = width or term_width()
    bc  = border_color or Color.rgb(88, 101, 242)
    b   = border or BorderStyle.DOUBLE
    R   = Color.RESET
    grad = gradient or Gradient.NEON

    styled = Color.multi_gradient(title, *grad)
    lines  = [styled]
    if subtitle:
        lines.append("")
        lines.append(f"{Color.BRIGHT_BLACK}{subtitle}{R}")

    return render_panel(lines, border=b, border_color=bc, padding=2, width=w)


def render_badge(text, color=None, border=False):
    c = color or Color.rgb(88, 101, 242)
    R = Color.RESET
    if border:
        return f"{c}[{R} {c}{text}{R} {c}]{R}"
    return f"{c}[ {text} ]{R}"
