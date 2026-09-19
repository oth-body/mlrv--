#!/usr/bin/env python3
"""Minimal .pd file builder: symbolic object references, auto-indexed
connections. Exists specifically to make CLAUDE.md gotcha #7 (manual
#X connect index-counting errors) structurally impossible instead of
merely documented against."""


class Patch:
    def __init__(self, w=1200, h=900):
        self.objs = []  # list of raw #X lines (obj/msg/text/table), in order
        self.conns = []  # (src_idx, src_outlet, dst_idx, dst_inlet)
        self.w, self.h = w, h

    def obj(self, x, y, text):
        self.objs.append(f"#X obj {x} {y} {text};")
        return len(self.objs) - 1

    def msg(self, x, y, text):
        self.objs.append(f"#X msg {x} {y} {text};")
        return len(self.objs) - 1

    def floatatom(self, x, y, w=5):
        self.objs.append(f"#X floatatom {x} {y} {w} 0 0 0 - - - 0;")
        return len(self.objs) - 1

    def text(self, x, y, text):
        self.objs.append(f"#X text {x} {y} {text};")
        return len(self.objs) - 1

    def connect(self, src, sout, dst, din):
        self.conns.append((src, sout, dst, din))

    def timeline(self, x0, y0, events):
        """events: list of (delay_ms, msg_text_or_None, target_idx, target_inlet).
        Builds loadbang -> [t b b ...] -> per-event [delay N] -> [msg ...] -> target,
        auto-wiring the whole fan-out. If msg_text is None, the delay's bang goes
        straight to the target (useful for bang-triggered targets like tabwrite~).
        Returns the loadbang index (rarely needed)."""
        lb = self.obj(x0, y0, "loadbang")
        n = len(events)
        t = self.obj(x0, y0 + 30, "t " + " ".join(["b"] * n))
        self.connect(lb, 0, t, 0)
        for i, (delay_ms, msg_text, target, inlet) in enumerate(events):
            col_x = x0 + 90 * i
            d = self.obj(col_x, y0 + 70, f"delay {delay_ms}")
            self.connect(t, i, d, 0)
            if msg_text is None:
                self.connect(d, 0, target, inlet)
            else:
                m = self.msg(col_x, y0 + 110, msg_text)
                self.connect(d, 0, m, 0)
                self.connect(m, 0, target, inlet)
        return lb

    def render(self):
        lines = [f"#N canvas 0 0 {self.w} {self.h} 10;"]
        lines += self.objs
        for s, so, d, di in self.conns:
            lines.append(f"#X connect {s} {so} {d} {di};")
        return "\n".join(lines) + "\n"

    def write(self, path):
        with open(path, "w") as f:
            f.write(self.render())
