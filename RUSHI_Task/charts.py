"""Small standard-library SVG charts for the D5 report (no plotting packages).

Colours were checked with a colour-blind-safety validator against the white
surface: blue/orange identify the two policies everywhere; red/violet mean
"adds energy"/"saves energy". Text always uses ink colours, never series
colours. Every mark carries a <title> so hovering the opened SVG shows its value.
"""
import html
import math

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
SURFACE, INK, INK2, MUTED = "#ffffff", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
CPU, MEMORY = "#2a78d6", "#eb6834"
ADDS, SAVES, NET = "#e34948", "#6250d6", "#52514e"
POLICY_COLOURS = {"lr_mmt": CPU, "lr_mmt_memory": MEMORY}
POLICY_NAMES = {"lr_mmt": "CPU-oriented LR-MMT", "lr_mmt_memory": "LR-MMT + CPU/memory-aware (proposed)"}


def esc(value):
    return html.escape(str(value), quote=True)


def text(x, y, value, size=13, fill=INK2, anchor="start", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{esc(value)}</text>')


def document(width, height, title, desc, parts):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title>', f'<desc id="desc">{esc(desc)}</desc>',
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
        f'<g font-family="{esc(FONT)}">', *parts, "</g>", "</svg>", ""])


def nice_ticks(low, high, count=6):
    span = high - low or 1.0
    raw = span / count
    step = 10 ** math.floor(math.log10(raw))
    step *= next(m for m in (1, 2, 2.5, 5, 10) if raw <= m * step)
    start = math.floor(low / step) * step
    ticks, value = [], start
    while value <= high + step * 1e-9:
        ticks.append(round(value, 10))
        value += step
    return ticks


def legend(x, y, items):
    """items: [(label, colour)] drawn as swatch + ink text, left to right."""
    parts = []
    for label, colour in items:
        parts.append(f'<rect x="{x:.1f}" y="{y - 10:.1f}" width="12" height="12" rx="2" fill="{colour}"/>')
        parts.append(text(x + 18, y, label, 13, INK2))
        x += 18 + 7.2 * len(label) + 26
    return parts


def hbar(x_zero, x_end, y, height, fill, tip):
    """Horizontal bar from the zero line, 4px-rounded only at its data end."""
    left, right = sorted((x_zero, x_end))
    width = right - left
    if width < 1:
        return f'<rect x="{x_zero - 0.5:.1f}" y="{y:.1f}" width="1" height="{height}" fill="{fill}"><title>{esc(tip)}</title></rect>'
    r = min(4.0, width, height / 2)
    if x_end >= x_zero:
        d = (f"M{left:.1f},{y:.1f} H{right - r:.1f} Q{right:.1f},{y:.1f} {right:.1f},{y + r:.1f} "
             f"V{y + height - r:.1f} Q{right:.1f},{y + height:.1f} {right - r:.1f},{y + height:.1f} H{left:.1f} Z")
    else:
        d = (f"M{right:.1f},{y:.1f} H{left + r:.1f} Q{left:.1f},{y:.1f} {left:.1f},{y + r:.1f} "
             f"V{y + height - r:.1f} Q{left:.1f},{y + height:.1f} {left + r:.1f},{y + height:.1f} H{right:.1f} Z")
    return f'<path d="{d}" fill="{fill}"><title>{esc(tip)}</title></path>'


def vbar(x, y_base, y_top, width, fill, tip):
    """Column grown from the baseline, 4px-rounded at the top only."""
    height = y_base - y_top
    if height < 1:
        return f'<rect x="{x:.1f}" y="{y_base - 1:.1f}" width="{width}" height="1" fill="{fill}"><title>{esc(tip)}</title></rect>'
    r = min(4.0, height, width / 2)
    d = (f"M{x:.1f},{y_base:.1f} V{y_top + r:.1f} Q{x:.1f},{y_top:.1f} {x + r:.1f},{y_top:.1f} "
         f"H{x + width - r:.1f} Q{x + width:.1f},{y_top:.1f} {x + width:.1f},{y_top + r:.1f} V{y_base:.1f} Z")
    return f'<path d="{d}" fill="{fill}"><title>{esc(tip)}</title></path>'


def bar_groups(path, title, subtitle, groups, legend_items, unit, value_format, note="", width=980):
    """Horizontal bars in labelled groups around a shared zero line.

    groups: [{"label": str, "bars": [{"label", "value", "colour", "tip"}]}]
    """
    bar_h, gap, group_gap, header = 16, 6, 18, 24
    label_w, left, right_pad = 250, 264, 90
    top = 118
    rows = sum(len(g["bars"]) for g in groups)
    height = top + rows * (bar_h + gap) + len(groups) * (group_gap + header) + 64 + (22 if note else 0)
    values = [b["value"] for g in groups for b in g["bars"]]
    low, high = min(0.0, min(values)), max(0.0, max(values))
    ticks = nice_ticks(low, high)
    low, high = min(low, ticks[0]), max(high, ticks[-1])
    plot_w = width - left - right_pad
    sx = lambda v: left + (v - low) / (high - low) * plot_w
    parts = [text(24, 34, title, 20, INK, weight="bold"), text(24, 58, subtitle, 13, INK2)]
    parts += legend(24, 88, legend_items)
    bottom = height - 52 - (22 if note else 0)
    for t in ticks:
        x = sx(t)
        parts.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{bottom}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(text(x, bottom + 18, value_format(t, tick=True), 12, MUTED, "middle"))
    parts.append(text(left + plot_w / 2, bottom + 38, unit, 12, MUTED, "middle"))
    zero = sx(0.0)
    y = top
    for group in groups:
        parts.append(text(24, y + 13, group["label"], 13, INK, weight="bold"))
        y += header
        for bar in group["bars"]:
            parts.append(text(label_w, y + bar_h - 3, bar["label"], 12, INK2, "end"))
            x_end = sx(bar["value"])
            parts.append(hbar(zero, x_end, y, bar_h, bar["colour"], bar["tip"]))
            label = value_format(bar["value"])
            if bar["value"] >= 0:
                parts.append(text(x_end + 6, y + bar_h - 3, label, 12, INK2))
            else:
                parts.append(text(x_end - 6, y + bar_h - 3, label, 12, INK2, "end"))
            y += bar_h + gap
        y += group_gap
    parts.append(f'<line x1="{zero:.1f}" y1="{top - 8}" x2="{zero:.1f}" y2="{bottom}" stroke="{AXIS}" stroke-width="1"/>')
    if note:
        parts.append(text(24, height - 16, note, 12, MUTED))
    desc = subtitle + " " + "; ".join(f'{g["label"]}: ' + ", ".join(f'{b["label"]} {value_format(b["value"])}' for b in g["bars"]) for g in groups)
    path.write_text(document(width, height, title, desc, parts), encoding="utf-8", newline="\n")


def line_panels(path, title, subtitle, panels, legend_items, x_label, width=980):
    """Stacked panels sharing one time axis; each panel has its own y-axis.

    panels: [{"title", "y_max", "y_format", "series": [{"name", "colour", "x", "y"}]}]
    """
    panel_h, panel_gap, left, right_pad, top = 190, 58, 70, 150, 112
    height = top + len(panels) * (panel_h + panel_gap) + 40
    xs = [x for p in panels for s in p["series"] for x in s["x"]]
    x_max = max(xs)
    x_ticks = [t for t in range(0, int(math.ceil(x_max)) + 1, 2)]
    x_end = max(float(x_ticks[-1]), x_max)
    plot_w = width - left - right_pad
    sx = lambda v: left + v / x_end * plot_w
    parts = [text(24, 34, title, 20, INK, weight="bold"), text(24, 58, subtitle, 13, INK2)]
    parts += legend(24, 88, legend_items)
    for index, panel in enumerate(panels):
        y0 = top + index * (panel_h + panel_gap) + 22
        y1 = y0 + panel_h
        sy = lambda v, y0=y0, y1=y1, m=panel["y_max"]: y1 - v / m * (y1 - y0)
        parts.append(text(left, y0 - 12, panel["title"], 14, INK, weight="bold"))
        for t in nice_ticks(0, panel["y_max"], 4):
            if t > panel["y_max"] + 1e-9:
                continue
            parts.append(f'<line x1="{left}" y1="{sy(t):.1f}" x2="{left + plot_w}" y2="{sy(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
            parts.append(text(left - 8, sy(t) + 4, panel["y_format"](t), 12, MUTED, "end"))
        for t in x_ticks:
            parts.append(text(sx(t), y1 + 18, f"{t} h", 12, MUTED, "middle"))
        parts.append(f'<line x1="{left}" y1="{y1}" x2="{left + plot_w}" y2="{y1}" stroke="{AXIS}" stroke-width="1"/>')
        ends = []
        for series in panel["series"]:
            points = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(series["x"], series["y"]))
            mean = series.get("average", sum(series["y"]) / len(series["y"]))
            parts.append(f'<polyline points="{points}" fill="none" stroke="{series["colour"]}" stroke-width="2" '
                         f'stroke-linejoin="round" stroke-linecap="round"><title>{esc(series["name"])}: '
                         f'average {esc(panel["y_format"](mean))}</title></polyline>')
            ends.append((sy(mean), series))
        # Average markers at the right edge; labels only when they do not collide
        # (otherwise the legend and the hover titles carry identity).
        ends.sort(key=lambda e: e[0])
        labelled = len(ends) < 2 or all(b[0] - a[0] >= 16 for a, b in zip(ends, ends[1:]))
        for y, series in ends:
            parts.append(f'<line x1="{left + plot_w + 4:.1f}" y1="{y:.1f}" x2="{left + plot_w + 14:.1f}" y2="{y:.1f}" '
                         f'stroke="{series["colour"]}" stroke-width="2" stroke-linecap="round"/>')
            if labelled:
                average = panel["y_format"](series.get("average", sum(series["y"]) / len(series["y"])))
                parts.append(text(left + plot_w + 18, y + 4, f'{series["short"]} avg {average}', 12, INK2))
    parts.append(text(left + plot_w / 2, height - 14, x_label, 12, MUTED, "middle"))
    desc = subtitle + " " + "; ".join(
        f'{p["title"]}: ' + ", ".join(f'{s["name"]} average {p["y_format"](s.get("average", sum(s["y"]) / len(s["y"])))}'
                                      for s in p["series"])
        for p in panels)
    path.write_text(document(width, height, title, desc, parts), encoding="utf-8", newline="\n")


def grouped_columns(path, title, subtitle, categories, series, y_label, y_format, note="", width=980):
    """Columns per category, one per series (<=24px wide, 2px gap between neighbours).

    series: [{"name", "colour", "values": [...]}] aligned with categories.
    """
    left, right_pad, top, plot_h = 70, 30, 112, 280
    height = top + plot_h + 90 + (18 if note else 0)
    y_max = max(v for s in series for v in s["values"])
    ticks = nice_ticks(0, y_max, 5)
    y_top = ticks[-1]
    plot_w = width - left - right_pad
    band = plot_w / len(categories)
    bar_w = min(24.0, (band * 0.6 - 2 * (len(series) - 1)) / len(series))
    y_base = top + plot_h
    sy = lambda v: y_base - v / y_top * plot_h
    parts = [text(24, 34, title, 20, INK, weight="bold"), text(24, 58, subtitle, 13, INK2)]
    parts += legend(24, 88, [(s["name"], s["colour"]) for s in series])
    for t in ticks:
        parts.append(f'<line x1="{left}" y1="{sy(t):.1f}" x2="{left + plot_w}" y2="{sy(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(text(left - 8, sy(t) + 4, y_format(t), 12, MUTED, "end"))
    group_w = len(series) * bar_w + 2 * (len(series) - 1)
    for i, category in enumerate(categories):
        cx = left + band * i + band / 2
        x = cx - group_w / 2
        for s in series:
            value = s["values"][i]
            parts.append(vbar(x, y_base, sy(value), bar_w, s["colour"], f'{s["name"]}, {category}: {y_format(value)}'))
            parts.append(text(x + bar_w / 2, sy(value) - 6, y_format(value), 12, INK2, "middle"))
            x += bar_w + 2
        parts.append(text(cx, y_base + 18, category, 12, INK2, "middle"))
    parts.append(f'<line x1="{left}" y1="{y_base}" x2="{left + plot_w}" y2="{y_base}" stroke="{AXIS}" stroke-width="1"/>')
    parts.append(text(left + plot_w / 2, y_base + 40, y_label, 12, MUTED, "middle"))
    if note:
        parts.append(text(24, height - 16, note, 12, MUTED))
    desc = subtitle + " " + "; ".join(
        f'{c}: ' + ", ".join(f'{s["name"]} {y_format(s["values"][i])}' for s in series) for i, c in enumerate(categories))
    path.write_text(document(width, height, title, desc, parts), encoding="utf-8", newline="\n")
