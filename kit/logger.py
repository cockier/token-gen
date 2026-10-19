from __future__ import annotations

import sys
import os
import json
import time
import difflib
import traceback as _tb
import datetime
import threading
import shutil
from typing import Any, Optional

from .colors import Color, Gradient
from .styles import Style, BorderStyle, render_panel, render_table, strip_ansi


class Level:
    DEBUG    = 0
    INFO     = 1
    SUCCESS  = 2
    WARNING  = 3
    ERROR    = 4
    CRITICAL = 5


_META = {
    Level.DEBUG:    ("·", Color.rgb(100, 100, 140)),
    Level.INFO:     ("›", Color.rgb(80,  160, 255)),
    Level.SUCCESS:  ("✓", Color.rgb(50,  220, 100)),
    Level.WARNING:  ("!", Color.rgb(255, 180, 0)),
    Level.ERROR:    ("✗", Color.rgb(255, 60,  60)),
    Level.CRITICAL: ("☠", Color.rgb(255, 0,   80)),
}

_SPARK  = "▁▂▃▄▅▆▇█"
_CALLOUT = {
    "note":   (Color.rgb(80,  160, 255), "ℹ", "NOTE"),
    "tip":    (Color.rgb(50,  220, 100), "✦", "TIP"),
    "warn":   (Color.rgb(255, 180, 0),   "⚠", "WARN"),
    "danger": (Color.rgb(255, 60,  60),  "✗", "DANGER"),
    "info":   (Color.rgb(160, 100, 255), "◈", "INFO"),
}


class _History:
    def __init__(self, maxlen=500):
        self._buf  = []
        self._lock = threading.Lock()
        self.maxlen = maxlen

    def push(self, level, msg, ts):
        with self._lock:
            self._buf.append({"level": level, "msg": msg, "ts": ts})
            if len(self._buf) > self.maxlen:
                self._buf.pop(0)

    def all(self):
        with self._lock:
            return list(self._buf)

    def clear(self):
        with self._lock:
            self._buf.clear()


class LogKit:
    def __init__(
        self,
        name="LOG",
        min_level=Level.DEBUG,
        show_time=True,
        show_name=True,
        name_gradient=None,
        time_color=None,
        file=None,
        thread_safe=False,
        history=False,
        history_maxlen=500,
    ):
        self.name           = name
        self.min_level      = min_level
        self.show_time      = show_time
        self.show_name      = show_name
        self.name_gradient  = name_gradient or Gradient.DISCORD
        self.time_color     = time_color or Color.BRIGHT_BLACK
        self.file           = file or sys.stdout
        self._lock          = threading.Lock() if thread_safe else None
        self._hist          = _History(history_maxlen) if history else None
        self._name_str      = Color.multi_gradient(name, *self.name_gradient)
        self._status_active = False
        self._time_fmt      = None

    def _ts(self):
        if self._time_fmt:
            return datetime.datetime.now().strftime(self._time_fmt)
        return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _prefix(self, level):
        sym, color = _META[level]
        _dim = Color.rgb(50, 50, 70)
        parts = []
        if self.show_time:
            parts.append(f"{self.time_color}{self._ts()}{Color.RESET}")
        if self.show_name:
            parts.append(f"{_dim}·{Color.RESET} {self._name_str} {_dim}·{Color.RESET}")
        parts.append(f"{color}{sym}{Color.RESET}")
        return "  ".join(parts)

    def _emit(self, level, msg, color=None):
        if level < self.min_level:
            return
        _, lc = _META[level]
        mc = color or lc
        self._write(f"{self._prefix(level)} {mc}{msg}{Color.RESET}")
        if self._hist:
            self._hist.push(level, msg, self._ts())

    def _write(self, text, end="\n"):
        if self._status_active and end == "\n":
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            self._status_active = False
        if self._lock:
            with self._lock:
                print(text, end=end, file=self.file, flush=True)
        else:
            print(text, end=end, file=self.file, flush=True)

    def _tw(self):
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def debug   (self, msg, color=None): self._emit(Level.DEBUG,    msg, color)
    def info    (self, msg, color=None): self._emit(Level.INFO,     msg, color)
    def success (self, msg, color=None): self._emit(Level.SUCCESS,  msg, color)
    def warning (self, msg, color=None): self._emit(Level.WARNING,  msg, color)
    def error   (self, msg, color=None): self._emit(Level.ERROR,    msg, color)
    def critical(self, msg, color=None): self._emit(Level.CRITICAL, msg, color)

    def banner(self, text, gradient=None, border=None, border_color=None, padding=2):
        grad = gradient or Gradient.NEON
        bc   = border_color or Color.rgb(88, 101, 242)
        b    = border or BorderStyle.DOUBLE
        self._write(render_panel(
            [Color.multi_gradient(text, *grad)],
            border=b, border_color=bc, padding=padding,
        ))

    def rule(self, text=None, char="─", color=None, width=None, gradient=None):
        w = width or self._tw()
        c = color or Color.BRIGHT_BLACK
        R = Color.RESET
        if text:
            raw  = len(strip_ansi(text))
            pad  = max(0, w - raw - 2)
            l, r = char * (pad // 2), char * (pad - pad // 2)
            if gradient:
                l = Color.multi_gradient(l, *gradient)
                r = Color.multi_gradient(r, *gradient)
            else:
                l, r = f"{c}{l}{R}", f"{c}{r}{R}"
            self._write(f"{l} {text} {r}")
        else:
            line = char * w
            self._write(Color.multi_gradient(line, *gradient) if gradient else f"{c}{line}{R}")

    def panel(self, lines, title=None, border=None, border_color=None,
              title_color=None, padding=1, width=None):
        self._write(render_panel(
            lines, title=title,
            border=border or BorderStyle.ROUNDED,
            border_color=border_color or Color.rgb(88, 101, 242),
            title_color=title_color or Color.BRIGHT_WHITE,
            padding=padding, width=width,
        ))

    def table(self, headers, rows, border=None, header_color=None,
              border_color=None, col_colors=None, zebra=False, align=None):
        self._write(render_table(
            headers, rows,
            border=border or BorderStyle.SINGLE,
            header_color=header_color or (Style.BOLD + Color.rgb(88, 101, 242)),
            border_color=border_color or Color.BRIGHT_BLACK,
            col_colors=col_colors, zebra=zebra, align=align,
        ))

    def kv(self, pairs, key_color=None, sep="  →  ", val_color=None, indent=2):
        kc  = key_color or Color.rgb(88, 101, 242)
        vc  = val_color or Color.BRIGHT_WHITE
        R   = Color.RESET
        pad = " " * indent
        mk  = max((len(str(k)) for k, _ in pairs), default=0)
        for k, v in pairs:
            self._write(f"{pad}{kc}{str(k).ljust(mk)}{R}{sep}{vc}{v}{R}")

    def gradient(self, text, *stops):
        return Color.multi_gradient(text, *stops)

    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.file)

    def divider(self):
        self._write("")

    def section(self, title, gradient=None, char="─", color=None, width=None):
        w    = width or self._tw()
        grad = gradient or Gradient.NEON
        c    = color or Color.BRIGHT_BLACK
        R    = Color.RESET
        line = f"{c}{char * w}{R}"
        self._write(line)
        self._write(Color.multi_gradient(f"  {title}  ", *grad))
        self._write(line)

    def keyval(self, key, val, key_color=None, val_color=None, sep="  →  ", indent=2):
        kc = key_color or Color.rgb(88, 101, 242)
        vc = val_color or Color.BRIGHT_WHITE
        R  = Color.RESET
        self._write(f"{' ' * indent}{kc}{key}{R}{sep}{vc}{val}{R}")

    def counter(self, label, current, total, color=None, bar=True, bar_width=20):
        c   = color or Color.rgb(88, 101, 242)
        R   = Color.RESET
        dim = Color.BRIGHT_BLACK
        pct = current / total if total else 0.0

        if bar:
            f   = int(pct * bar_width)
            e   = bar_width - f
            bar_s = (
                f"{Color.rgb(88, 101, 242)}{'█' * f}"
                f"{Color.BRIGHT_BLACK}{'░' * e}{R}"
            )
            line = (
                f"\r{c}{label}{R}  {bar_s}  "
                f"{c}{current}{R}{dim}/{R}{c}{total}{R}  "
                f"{dim}{pct * 100:5.1f}%{R}"
            )
        else:
            line = (
                f"\r{c}{label}{R}  "
                f"{c}{current}{R}{dim}/{R}{c}{total}{R}  "
                f"{dim}{pct * 100:5.1f}%{R}"
            )

        def _out(s, nl=False):
            if self._lock:
                with self._lock:
                    sys.stdout.write(s + ("\n" if nl else ""))
                    sys.stdout.flush()
            else:
                sys.stdout.write(s + ("\n" if nl else ""))
                sys.stdout.flush()

        if current >= total:
            _out(line, nl=True)
            self._status_active = False
        else:
            _out(line)
            self._status_active = True

    def status(self, msg, color=None):
        c   = color or Color.BRIGHT_BLACK
        R   = Color.RESET
        w   = self._tw()
        pad = max(0, w - len(strip_ansi(msg)) - 1)
        line = f"\r{c}{msg}{R}{' ' * pad}"
        if self._lock:
            with self._lock:
                sys.stdout.write(line)
                sys.stdout.flush()
        else:
            sys.stdout.write(line)
            sys.stdout.flush()
        self._status_active = True

    def status_clear(self):
        sys.stdout.write("\r\033[2K")
        sys.stdout.flush()
        self._status_active = False

    def multiline(self, lines, level=Level.INFO, color=None):
        if not lines:
            return
        _, lc = _META[level]
        c   = color or lc
        R   = Color.RESET
        pfx = self._prefix(level)
        cont = " " * len(strip_ansi(pfx))
        self._write(f"{pfx} {c}{lines[0]}{R}")
        for line in lines[1:]:
            self._write(f"{cont} {c}{line}{R}")

    def tree(self, data, _pfx="", key_color=None, val_color=None, gradient=None):
        kc = key_color or Color.rgb(88, 101, 242)
        vc = val_color or Color.BRIGHT_WHITE
        R  = Color.RESET

        def _key(k):
            if gradient:
                return Color.multi_gradient(str(k), *gradient)
            return f"{kc}{k}{R}"

        def _walk(node, pfx):
            if isinstance(node, dict):
                items = list(node.items())
                for i, (k, v) in enumerate(items):
                    last = i == len(items) - 1
                    conn = "└─ " if last else "├─ "
                    cpfx = pfx + ("   " if last else "│  ")
                    if isinstance(v, (dict, list)) and v:
                        self._write(f"{Color.BRIGHT_BLACK}{pfx}{conn}{R}{_key(k)}")
                        _walk(v, cpfx)
                    else:
                        self._write(f"{Color.BRIGHT_BLACK}{pfx}{conn}{R}{_key(k)}{Color.BRIGHT_BLACK} : {R}{vc}{v}{R}")
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    last = i == len(node) - 1
                    conn = "└─ " if last else "├─ "
                    cpfx = pfx + ("   " if last else "│  ")
                    if isinstance(v, (dict, list)) and v:
                        self._write(f"{Color.BRIGHT_BLACK}{pfx}{conn}{R}{kc}[{i}]{R}")
                        _walk(v, cpfx)
                    else:
                        self._write(f"{Color.BRIGHT_BLACK}{pfx}{conn}{R}{vc}{v}{R}")
            else:
                self._write(f"{pfx}{vc}{node}{R}")

        _walk(data, _pfx)

    def json(self, data, indent=2, key_color=None, str_color=None,
             num_color=None, bool_color=None, null_color=None):
        import re
        kc  = key_color  or Color.rgb(88,  101, 242)
        sc  = str_color  or Color.rgb(80,  200, 120)
        nc  = num_color  or Color.rgb(255, 180, 0)
        bc  = bool_color or Color.rgb(255, 100, 60)
        nlc = null_color or Color.BRIGHT_BLACK
        R   = Color.RESET

        raw  = json.dumps(data, indent=indent, ensure_ascii=False, default=str)
        _key = re.compile(r'^(\s*)"((?:[^"\\]|\\.)*)"(\s*:\s*)')
        _str = re.compile(r'^(\s*)"((?:[^"\\]|\\.)*)"(\s*,?)$')
        _num = re.compile(r'^(\s*)(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(\s*,?)$')
        _boo = re.compile(r'^(\s*)(true|false)(\s*,?)$')
        _nul = re.compile(r'^(\s*)(null)(\s*,?)$')
        out  = []

        for line in raw.splitlines():
            m = _key.match(line)
            if m:
                ck   = f'{m.group(1)}{kc}"{m.group(2)}"{R}{m.group(3)}'
                rest = line[m.end():].rstrip()
                com  = ""
                if rest.endswith(","):
                    com, rest = ",", rest[:-1].rstrip()
                if rest in ("true", "false"):   out.append(f"{ck}{bc}{rest}{R}{com}")
                elif rest == "null":            out.append(f"{ck}{nlc}{rest}{R}{com}")
                elif rest.startswith('"'):      out.append(f'{ck}{sc}{rest}{R}{com}')
                elif rest in ("{", "[", "}", "]", "", "{}", "[]"):
                                                out.append(f"{ck}{Color.BRIGHT_BLACK}{rest}{R}{com}")
                else:                           out.append(f"{ck}{nc}{rest}{R}{com}")
                continue
            if m := _boo.match(line): out.append(f"{m.group(1)}{bc}{m.group(2)}{R}{m.group(3)}"); continue
            if m := _nul.match(line): out.append(f"{m.group(1)}{nlc}{m.group(2)}{R}{m.group(3)}"); continue
            if m := _num.match(line): out.append(f"{m.group(1)}{nc}{m.group(2)}{R}{m.group(3)}"); continue
            if m := _str.match(line): out.append(f'{m.group(1)}{sc}"{m.group(2)}"{R}{m.group(3)}'); continue
            out.append(f"{Color.BRIGHT_BLACK}{line}{R}")

        self._write("\n".join(out))

    def hex_dump(self, data, width=16, offset_color=None, hex_color=None,
                 ascii_color=None, highlight=None, highlight_color=None):
        oc  = offset_color    or Color.rgb(88,  101, 242)
        hc  = hex_color       or Color.BRIGHT_WHITE
        ac  = ascii_color     or Color.rgb(80,  200, 120)
        hlc = highlight_color or Color.rgb(255, 180, 0)
        R   = Color.RESET
        dim = Color.BRIGHT_BLACK
        hl  = set(highlight) if highlight else set()

        for row in range(0, len(data), width):
            chunk  = data[row:row + width]
            offset = f"{oc}{row:08x}{R}"
            parts  = []
            for i, b in enumerate(chunk):
                if i == width // 2:
                    parts.append(f"{dim} {R}")
                col = hlc if b in hl else hc
                parts.append(f"{col}{b:02x}{R}")
            missing = width - len(chunk)
            for i in range(missing):
                if (len(chunk) + i) == width // 2:
                    parts.append("  ")
                parts.append("   ")
            hex_s  = " ".join(parts)
            asc_s  = "".join(
                f"{hlc if b in hl else ac}{chr(b) if 0x20 <= b < 0x7f else '.'}{R}"
                for b in chunk
            )
            self._write(f"  {offset}  {dim}│{R} {hex_s}  {dim}│{R} {asc_s}")

    def diff(self, a, b, label_a="a", label_b="b", context=3,
             add_color=None, rem_color=None, meta_color=None):
        ac = add_color  or Color.rgb(50,  220, 100)
        rc = rem_color  or Color.rgb(255, 60,  60)
        mc = meta_color or Color.BRIGHT_BLACK
        R  = Color.RESET

        ud = list(difflib.unified_diff(
            a.splitlines(keepends=True), b.splitlines(keepends=True),
            fromfile=label_a, tofile=label_b, n=context,
        ))
        if not ud:
            self._write(f"{mc}(no diff){R}")
            return
        for line in ud:
            line = line.rstrip("\n")
            if line.startswith(("+++", "---")): self._write(f"{Style.BOLD}{mc}{line}{R}")
            elif line.startswith("@@"):         self._write(f"{mc}{line}{R}")
            elif line.startswith("+"):          self._write(f"{ac}{line}{R}")
            elif line.startswith("-"):          self._write(f"{rc}{line}{R}")
            else:                               self._write(f"{Color.BRIGHT_BLACK}{line}{R}")

    def sparkline(self, values, label="", color=None, gradient=None,
                  min_val=None, max_val=None):
        if not values:
            return ""
        lo   = min_val if min_val is not None else min(values)
        hi   = max_val if max_val is not None else max(values)
        span = hi - lo or 1
        chars = "".join(
            _SPARK[max(0, min(int(((v - lo) / span) * (len(_SPARK) - 1)), len(_SPARK) - 1))]
            for v in values
        )
        R = Color.RESET
        if gradient:
            colored = Color.multi_gradient(chars, *gradient)
        elif color:
            colored = f"{color}{chars}{R}"
        else:
            colored = Color.multi_gradient(chars, *Gradient.OCEAN)
        prefix = f"{Color.BRIGHT_BLACK}{label} {R}" if label else ""
        self._write(f"{prefix}{colored}")
        return chars

    def rate(self, label, count, elapsed, unit="/s", color=None):
        c   = color or Color.rgb(88, 101, 242)
        R   = Color.RESET
        dim = Color.BRIGHT_BLACK
        r   = count / elapsed if elapsed > 0 else 0.0
        self._write(f"  {c}{label}{R}{dim}:{R}  {c}{r:.2f}{R}{dim}{unit}{R}")

    def elapsed(self, start, label="elapsed", color=None):
        c     = color or Color.rgb(88, 101, 242)
        R     = Color.RESET
        dim   = Color.BRIGHT_BLACK
        delta = time.time() - start
        if delta < 60:       s = f"{delta:.3f}s"
        elif delta < 3600:
            m, sec = divmod(delta, 60)
            s = f"{int(m)}m {sec:.1f}s"
        else:
            h, rem = divmod(delta, 3600)
            m, sec = divmod(rem, 60)
            s = f"{int(h)}h {int(m)}m {sec:.0f}s"
        self._write(f"  {c}{label}{R}{dim}:{R}  {c}{s}{R}")

    def badge(self, text, color=None, bg=False, bg_color=None):
        c = color or Color.rgb(88, 101, 242)
        R = Color.RESET
        pill = f"{bg_color} {text} {R}" if (bg and bg_color) else f"{c}[ {text} ]{R}"
        self._write(pill)
        return strip_ansi(pill)

    def callout(self, text, style="note", width=None, border=None):
        w    = width or min(self._tw(), 72)
        b    = border or BorderStyle.ROUNDED
        c, icon, label = _CALLOUT.get(style, _CALLOUT["note"])
        R    = Color.RESET
        self._write(render_panel(
            [f"{c}{Style.BOLD}{icon}  {label}{R}", "", f"{Color.BRIGHT_WHITE}{text}{R}"],
            border=b, border_color=c, padding=1, width=w,
        ))

    def columns(self, items, ncols=3, color=None, header_color=None,
                headers=None, gutter=3):
        c    = color        or Color.BRIGHT_WHITE
        hc   = header_color or (Style.BOLD + Color.rgb(88, 101, 242))
        R    = Color.RESET
        tw   = self._tw()
        colw = max(1, (tw - gutter * (ncols - 1)) // ncols)
        rpc  = (len(items) + ncols - 1) // ncols
        cols = [items[i * rpc:(i + 1) * rpc] for i in range(ncols)]
        mrow = max(len(col) for col in cols) if cols else 0

        if headers:
            row = []
            for i in range(ncols):
                h   = headers[i] if i < len(headers) else ""
                pad = max(0, colw - len(strip_ansi(h)))
                row.append(f"{hc}{h}{R}{' ' * pad}")
            self._write((" " * gutter).join(row))
            self._write((" " * gutter).join([f"{Color.BRIGHT_BLACK}{'─' * colw}{R}"] * ncols))

        for ri in range(mrow):
            row = []
            for ci in range(ncols):
                val = str(cols[ci][ri]) if ri < len(cols[ci]) else ""
                pad = max(0, colw - len(strip_ansi(val)))
                row.append(f"{c}{val}{R}{' ' * pad}")
            self._write((" " * gutter).join(row))

    def traceback(self, exc=None, header="Traceback", show_locals=False):
        R    = Color.RESET
        dim  = Color.BRIGHT_BLACK
        red  = Color.rgb(255, 60, 60)
        yel  = Color.rgb(255, 180, 0)
        blu  = Color.rgb(80,  160, 255)
        bold = Style.BOLD

        if exc is None:
            etype, exc, tb = sys.exc_info()
        else:
            etype, tb = type(exc), exc.__traceback__

        if exc is None:
            self._write(f"{dim}(no active exception){R}")
            return

        self._write(f"{red}{bold}{'─' * 4} {header} {'─' * 40}{R}")
        for frame in _tb.extract_tb(tb):
            self._write(
                f"  {dim}File{R} {blu}\"{frame.filename}\"{R}"
                f"{dim}, line {R}{yel}{frame.lineno}{R}"
                f"{dim}, in {R}{bold}{frame.name}{R}"
            )
            if frame.line:
                self._write(f"    {dim}│{R}  {frame.line.strip()}")
            if show_locals:
                for lk, lv in (getattr(frame, "locals", None) or {}).items():
                    self._write(f"      {dim}{lk} = {repr(lv)}{R}")
        self._write(f"\n  {red}{bold}{etype.__name__}: {exc}{R}")
        self._write(f"{red}{bold}{'─' * 46}{R}")

    def progress_bar(self, current, total, label="", width=40,
                     fill_char="█", empty_char="░", fill_gradient=None,
                     show_eta=False, start_time=None):
        R   = Color.RESET
        dim = Color.BRIGHT_BLACK
        pct = current / total if total else 0.0
        f   = int(pct * width)
        e   = width - f
        fs  = Color.multi_gradient("█" * f, *fill_gradient) if (fill_gradient and f) else f"{Color.rgb(88, 101, 242)}{'█' * f}{R}"
        es  = f"{dim}{empty_char * e}{R}"
        pct_s = f"{pct * 100:5.1f}%"
        eta_s = ""
        if show_eta and start_time and current > 0:
            elapsed = time.time() - start_time
            remain  = (total - current) / (current / elapsed)
            eta_s   = f"  {dim}eta {remain:.0f}s{R}"
        lbl = f"{Color.BRIGHT_WHITE}{label} {R}" if label else ""
        line = (
            f"\r{lbl}{fs}{es}  "
            f"{Color.rgb(88, 101, 242)}{pct_s}{R}"
            f"  {dim}{current}/{total}{R}{eta_s}"
        )
        if current >= total:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            self._status_active = False
        else:
            sys.stdout.write(line)
            sys.stdout.flush()
            self._status_active = True

    def inspect(self, obj, name=None, show_private=False, show_methods=False):
        R    = Color.RESET
        dim  = Color.BRIGHT_BLACK
        bc   = Color.rgb(88, 101, 242)
        vc   = Color.BRIGHT_WHITE
        mc   = Color.rgb(120, 120, 170)
        bold = Style.BOLD
        lbl  = name or obj.__class__.__name__
        self._write(f"{bc}{bold}◈ {lbl}{R}  {dim}<{type(obj).__name__}>{R}")
        self._write(f"  {dim}repr:{R} {vc}{repr(obj)[:120]}{R}")
        self._write("")
        for k in dir(obj):
            if not show_private and k.startswith("_"):
                continue
            try:
                v = getattr(obj, k)
            except Exception:
                continue
            if callable(v):
                if show_methods:
                    self._write(f"  {mc}{k}(){R}")
            else:
                vr = repr(v)
                if len(vr) > 80:
                    vr = vr[:77] + "..."
                self._write(f"  {bc}{k}{R}{dim} = {R}{vc}{vr}{R}")

    def countdown(self, seconds, label="starting in", color=None, done_msg="go"):
        c = color or Color.rgb(255, 180, 0)
        R = Color.RESET
        for i in range(seconds, 0, -1):
            sys.stdout.write(f"\r{c}{label} {i}s...{R}  ")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write(f"\r{Color.rgb(50, 220, 100)}{done_msg}{R}        \n")
        sys.stdout.flush()

    def get_history(self):
        return self._hist.all() if self._hist else []

    def replay(self, min_level=Level.DEBUG):
        for e in self.get_history():
            if e["level"] >= min_level:
                _, lc = _META[e["level"]]
                print(f"{Color.BRIGHT_BLACK}{e['ts']}{Color.RESET}  {lc}{e['msg']}{Color.RESET}")

    def clear_history(self):
        if self._hist:
            self._hist.clear()

    def set_time_format(self, fmt):
        self._time_fmt = fmt

    def syntax(self, code: str, lang: str = "python", line_numbers: bool = True,
               title: str = None, border=None):
        from .syntax import highlight
        from .styles import BorderStyle
        highlighted = highlight(code, lang, line_numbers=line_numbers)
        b = border or BorderStyle.ROUNDED
        lbl = title or lang
        self._write(render_panel(
            highlighted.splitlines(),
            title=lbl, border=b,
            border_color=Color.rgb(70, 70, 90),
            padding=1,
        ))

    def markdown(self, text: str):
        from .markdown import render as md_render
        self._write(md_render(text))

    def markup(self, text: str):
        from .markup import render as mk_render
        self._write(mk_render(text))

    def file_tree(self, path: str = ".", max_depth: int = 4,
                  show_hidden: bool = False, show_size: bool = False):
        from .filetree import render_file_tree
        self._write(render_file_tree(path, max_depth=max_depth,
                                     show_hidden=show_hidden, show_size=show_size))

    def theme(self, name: str):
        from .themes import apply as _apply
        _apply(name)
        t_c = Color.rgb(100, 200, 255)
        self._write(f"  {t_c}theme → {name}{Color.RESET}")
