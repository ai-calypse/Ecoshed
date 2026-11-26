"""Build the beginner's guide PDF from the code, the data and the experiment results.

    python -m RUSHI_Task.guide.build --profile <an empty scratch folder>

Every number in the guide is computed here from the real power curves, Rohan's scoring
code, the LR forecast, the team's committed results and the same-job runs
(RUSHI_Task/same_job), so the text cannot drift from the facts. Output: guide.html and
the PDF in this folder. Printing needs Microsoft Edge (headless).
"""
from collections import Counter
from datetime import date
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import unittest

import jinja2
import markdown

from ecosched import HostView, Request, SimulationConfig, load_curve
from ROHAN_Task.policies import LRMMT, local_linear_predict
from RUSHI_Task import charts as C
from RUSHI_Task.accounting import pair_gap
from RUSHI_Task.same_job import analyze as S
from RUSHI_Task.same_job.policy import SameJobLRMMT

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHARTS = HERE / "charts"
PDF = HERE / "EcoSched_Same_Job_Rule_Guide.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
SIM = SimulationConfig(memory_unit_bytes=1e9)
TASK = Request("typical", "g", 0.5, 0.0117, 0)   # half a core of 64; 1.17% of memory
# The plan was first committed, before any run, on Rushi's local working branch; that
# branch's history is not part of the pull request (see RUSHI_Task/same_job/DESIGN.md).
FIRST_DESIGN_COMMIT = "742d058"


def view(key, cpu_share, memory_share, state="active"):
    return HostView(key, 64.0, 1.0, 64.0 * cpu_share, memory_share, state)


def num(value, digits=1):
    return f"{value:,.{digits}f}"


def table(header, rows, align=None):
    align = align or ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


# ---------- background values (Parts A-B) ----------

def background():
    hpe = load_curve("hpe_dl360_gen9")
    w = hpe.watts
    v, t = {}, {}
    v.update(sleep_w=num(SIM.sleep_watts, 0), full_w=num(w[-1], 0), idle_w=num(w[0], 0),
             wake_s=num(SIM.wake_latency_s, 0), idle_timeout=num(SIM.idle_timeout_s, 0),
             on_premium=num(w[0] - SIM.sleep_watts, 0), scale=num(w[-1] - w[0], 0),
             first_slice=num(w[1] - w[0]), cheapest_slice=num(min(w[i + 1] - w[i] for i in range(10)), 0))
    efficiency = {i: w[i] / (i / 10) for i in range(1, 11)}
    best = min(efficiency, key=efficiency.get)
    v.update(eff_10=num(efficiency[1], 0), eff_best=num(efficiency[best], 0), eff_best_load=f"{10 * best}%")
    rows = []
    for i in range(11):
        rows.append([f"{10 * i}%", num(w[i]), num(w[i + 1] - w[i]) if i < 10 else "",
                     num(efficiency[i], 0) if i else ""])
    t["power_table"] = table(["CPU load", "Watts", "Cost of the next 10%", "Watts per unit of work"], rows,
                             ["---", "---:", "---:", "---:"])
    p10, p20 = hpe.power(0.1), hpe.power(0.2)
    pack, spread = p20 + SIM.sleep_watts, 2 * p10
    v.update(p10=num(p10), p20=num(p20, 0), pack_total=num(pack, 0), spread_total=num(spread),
             spread_extra=num(spread - pack), spread_pct=f"{100 * (spread - pack) / pack:.0f}%",
             spread_dynamic=num(spread - pack - (w[0] - SIM.sleep_watts)))
    # LR trend-line example, with the real forecast function and safety factor.
    safety = LRMMT(SIM).config.safety_factor
    ok = [0.62 + 0.02 * i for i in range(10)]
    over = [0.66 + 0.02 * i for i in range(10)]
    v.update(lr_ok_first=f"{100 * ok[0]:.0f}%", lr_ok_last=f"{100 * ok[-1]:.0f}%",
             lr_ok_pred=f"{100 * local_linear_predict(ok):.0f}%",
             lr_ok_press=f"{100 * safety * local_linear_predict(ok):.0f}%",
             lr_over_last=f"{100 * over[-1]:.0f}%", lr_over_pred=f"{100 * local_linear_predict(over):.0f}%",
             lr_over_press=f"{100 * safety * local_linear_predict(over):.0f}%")
    # Placement scores for one typical task, from Rohan's own _score.
    cpu = LRMMT(SIM, hpe)
    servers = [("Busy server, 45% CPU", view("busy", 0.45, 0.5)),
               ("Empty server, on, no work", view("empty", 0, 0)),
               ("Sleeping server", view("asleep", 0, 0, "sleep"))]
    rows, extra = [], {}
    for label, host in servers:
        score = cpu._score(TASK, host)[0]
        extra[host.host_id] = score * (w[-1] - w[0])
        rows.append([label, num(extra[host.host_id], 2) + " W", f"{score:.4f}"])
    t["score_table"] = table(["Server", "Extra watts for this task", "Score (lower wins)"], rows,
                             ["---", "---:", "---:"])
    v["wake_vs_busy"] = num(extra["asleep"] / extra["busy"], 0)
    v.update(task_cpu_pct=f"{100 * TASK.cpu / 64:.2f}%", task_mem_pct=f"{100 * TASK.memory:.2f}%")
    # Why the memory-aware score spreads tasks: busy memory-heavy server versus an empty one.
    memory = LRMMT(SIM, hpe, memory_aware=True)
    busy, empty = view("busy", 0.30, 0.57), view("empty", 0, 0)
    parts = {}
    for host in (busy, empty):
        power = cpu._score(TASK, host)[0]
        total = memory._score(TASK, host)[0]
        parts[host.host_id] = (power * (w[-1] - w[0]), power, total - power, total)
    picked = min(parts, key=lambda k: parts[k][3])
    rows = [["Extra watts for this task"] + [num(parts[k][0], 2) + " W" for k in ("busy", "empty")],
            ["Power score (watts ÷ " + v["scale"] + ")"] + [f"{parts[k][1]:.4f}" for k in ("busy", "empty")],
            ["Balance term (0.25 × imbalance after)"] + [f"{parts[k][2]:.4f}" for k in ("busy", "empty")],
            ["**Memory-aware total**"] + [f"**{parts[k][3]:.4f}**" + (" ← picked" if k == picked else "")
                                          for k in ("busy", "empty")]]
    t["flaw1_table"] = table(["", "Busy: 30% CPU, 57% memory", "Empty: on, no work"], rows, ["---", "---:", "---:"])
    v.update(flaw_balance_gap=f"{parts['busy'][2] - parts['empty'][2]:.4f}",
             flaw_power_gap=f"{parts['empty'][1] - parts['busy'][1]:.4f}",
             flaw_ratio=num((parts["busy"][2] - parts["empty"][2]) / (parts["empty"][1] - parts["busy"][1]), 1),
             task_skew=f"{abs(TASK.cpu / 64 - TASK.memory):.4f}", empty_extra_w=num(parts["empty"][0], 1),
             flaw_picked=picked)
    return v, t


def toy_example(v, t, tasks=12):
    """Part C3: job J7's tasks placed one by one by Rohan's real code, with and without the rule."""
    hpe = load_curve("hpe_dl360_gen9")
    start = [view("Busy-A", 0.30, 0.57), view("Busy-B", 0.45, 0.50),
             view("Empty-1", 0, 0), view("Empty-2", 0, 0), view("Empty-3", 0, 0)]
    empty = {h.host_id for h in start if h.cpu_used == 0}
    rows, used = [], {}
    for memory_aware in (True, False):
        for rule in (False, True):
            policy = SameJobLRMMT(SIM, hpe, memory_aware=memory_aware, same_job=rule)
            hosts = {h.host_id: h for h in start}
            counts = Counter()
            for i in range(tasks):
                request = Request(f"j7_{i}", "J7", TASK.cpu, TASK.memory, 0)
                choice = policy.select_host(request, list(hosts.values()), 0)
                hosts[choice] = policy._add(hosts[choice], request)
                counts[choice] += 1
            key = ("mem" if memory_aware else "lr") + ("_rule" if rule else "")
            used[key] = counts
            name = ("Memory-aware LR-MMT" if memory_aware else "LR-MMT") + (" **+ rule**" if rule else "")
            rows.append([name, ", ".join(f'<span style="white-space:nowrap">{h} × {n}</span>'
                                         for h, n in sorted(counts.items())), len(counts),
                         sum(h in empty for h in counts)])
    t["toy_table"] = table(["Algorithm", "Where J7's tasks went", "Servers holding J7",
                            "Empty servers kept on by J7"], rows, ["---", "---", "---:", "---:"])
    v["toy"] = {"tasks": tasks, "mem_servers": len(used["mem"]), "mem_rule_servers": len(used["mem_rule"]),
                "mem_empty": sum(h in empty for h in used["mem"]),
                "mem_saved": len(empty) - sum(h in empty for h in used["mem_rule"]),
                "lr_servers": len(used["lr"]), "lr_rule_servers": len(used["lr_rule"]),
                "lr_empty": sum(h in empty for h in used["lr"])}
    if not (v["toy"]["mem_rule_servers"] == v["toy"]["lr_rule_servers"] == 1 and v["toy"]["mem_servers"] > 1):
        raise ValueError(f"The worked example no longer shows what the text says: {used}")


def team_values(v):
    rows = json.loads(S.COMMITTED.read_text(encoding="utf-8"))
    index = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in rows}
    changes = [S.pct(index[(4000, c, "lr_mmt_memory")]["energy_kwh"], index[(4000, c, "lr_mmt")]["energy_kwh"])
               for c in S.CURVES]
    v["team_mem_range"] = f"{min(changes):.2f}–{max(changes):.2f}%"
    originals = ("first_fit", "best_fit", "lr_mmt", "lr_mmt_memory")
    v["team_ff_wins"] = sum(min(originals, key=lambda p: index[(s, c, p)]["energy_kwh"]) == "first_fit"
                            for s, c in S.CASES)
    v["team_tasks_4000"] = f"{index[(4000, 'hpe_dl360_gen9', 'lr_mmt')]['completed_instances']:,}"
    v["team_tasks"] = {s: f"{index[(s, 'hpe_dl360_gen9', 'lr_mmt')]['completed_instances']:,}" for s in S.SIZES}
    # D5's exact split: share of the memory-aware version's extra energy that is servers on while running work.
    shares = []
    for c in S.CURVES:
        gap = pair_gap(index[(4000, c, "lr_mmt")], index[(4000, c, "lr_mmt_memory")], load_curve(c))
        shares.append(gap["on_running_work_j"] / gap["total_j"])
    v["d5_running_share"] = f"{100 * statistics.fmean(shares):.0f}%"
    v["first_design_commit"] = FIRST_DESIGN_COMMIT


# ---------- guide-only figures ----------

def power_curve_chart(path):
    w = load_curve("hpe_dl360_gen9").watts
    width, height, top = 980, 400, 96
    parts = [C.text(24, 34, "HPE DL360 Gen9: watts at each CPU load", 20, C.INK, weight="bold"),
             C.text(24, 58, "SPECpower measurements used by the simulator. The first 10% slice costs the most.", 13, C.INK2)]
    # Left panel: watts versus load.
    lx0, lx1, y0, y1 = 80, 450, top + 10, height - 64
    sy = lambda v: y1 - v / 300 * (y1 - y0)
    sx = lambda u: lx0 + u * (lx1 - lx0)
    for tick in (0, 100, 200, 300):
        parts.append(f'<line x1="{lx0}" y1="{sy(tick):.1f}" x2="{lx1}" y2="{sy(tick):.1f}" stroke="{C.GRID}"/>')
        parts.append(C.text(lx0 - 8, sy(tick) + 4, f"{tick} W", 12, C.MUTED, "end"))
    for i in range(0, 11, 2):
        parts.append(C.text(sx(i / 10), y1 + 18, f"{10 * i}%", 12, C.MUTED, "middle"))
    points = " ".join(f"{sx(i / 10):.1f},{sy(w[i]):.1f}" for i in range(11))
    parts.append(f'<polyline points="{points}" fill="none" stroke="{C.INK2}" stroke-width="2"/>')
    for i in range(11):
        parts.append(f'<circle cx="{sx(i / 10):.1f}" cy="{sy(w[i]):.1f}" r="4" fill="{C.INK2}" stroke="#ffffff" '
                     f'stroke-width="2"><title>{10 * i}% CPU: {w[i]:.1f} W</title></circle>')
    parts.append(C.text(sx(0) + 8, sy(w[0]) + 18, f"idle {w[0]:.0f} W", 12, C.INK2))
    parts.append(C.text(sx(1) - 8, sy(w[-1]) - 9, f"full {w[-1]:.0f} W", 12, C.INK2, "end"))
    parts.append(f'<line x1="{lx0}" y1="{y1}" x2="{lx1}" y2="{y1}" stroke="{C.AXIS}"/>')
    parts.append(C.text((lx0 + lx1) / 2, height - 22, "CPU load", 12, C.MUTED, "middle"))
    # Right panel: watts added by each slice.
    rx0, rx1 = 560, 950
    slices = [w[i + 1] - w[i] for i in range(10)]
    sy2 = lambda v: y1 - v / 45 * (y1 - y0)
    for tick in (0, 10, 20, 30, 40):
        parts.append(f'<line x1="{rx0}" y1="{sy2(tick):.1f}" x2="{rx1}" y2="{sy2(tick):.1f}" stroke="{C.GRID}"/>')
        parts.append(C.text(rx0 - 8, sy2(tick) + 4, f"{tick} W", 12, C.MUTED, "end"))
    band = (rx1 - rx0) / 10
    for i, s in enumerate(slices):
        x = rx0 + i * band + band * 0.18
        colour = C.ADDS if i == 0 else C.INK2
        parts.append(C.vbar(x, y1, sy2(s), band * 0.64, colour, f"{10 * i}-{10 * i + 10}%: +{s:.1f} W"))
        parts.append(C.text(x + band * 0.32, sy2(s) - 6, f"{s:.0f}", 12, C.INK2, "middle"))
        parts.append(C.text(x + band * 0.32, y1 + 18, f"{10 * i}", 11, C.MUTED, "middle"))
    parts.append(f'<line x1="{rx0}" y1="{y1}" x2="{rx1}" y2="{y1}" stroke="{C.AXIS}"/>')
    parts.append(C.text((rx0 + rx1) / 2, height - 22, "watts added by each 10% slice (slice start, %)", 12, C.MUTED, "middle"))
    parts.append(C.text(lx0, top - 6, "Watts", 13, C.INK, weight="bold"))
    parts.append(C.text(rx0, top - 6, "Cost of each 10% slice", 13, C.INK, weight="bold"))
    desc = "Watts at 0-100% load: " + ", ".join(f"{x:.1f}" for x in w)
    path.write_text(C.document(width, height, "HPE DL360 Gen9 power curve", desc, parts), encoding="utf-8", newline="\n")


def life_chart(path):
    width, height = 980, 330
    box_fill, box_line = "#f5f4f0", "#c3c2b7"

    def box(x, y, w, h, title, sub="", fill=box_fill):
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{box_line}"/>',
               C.text(x + w / 2, y + (h / 2 - 2 if sub else h / 2 + 5), title, 13, C.INK, "middle", "bold")]
        if sub:
            out.append(C.text(x + w / 2, y + h / 2 + 15, sub, 11.5, C.INK2, "middle"))
        return out

    def arrow(x1, y1, x2, y2, label="", above=True):
        out = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C.INK2}" stroke-width="1.6" '
               f'marker-end="url(#arrow)"/>']
        if label:
            out.append(C.text((x1 + x2) / 2, (y1 + y2) / 2 + (-8 if above else 16), label, 11.5, C.INK2, "middle"))
        return out

    parts = ['<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
             f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{C.INK2}"/></marker></defs>',
             C.text(24, 30, "The life of a task", 15, C.INK, weight="bold")]
    xs = [24, 214, 404, 594, 784]
    labels = [("Task arrives", "asks for CPU + memory"), ("Queue", "first in, first out"),
              ("Placement", "picks a server"), ("Runs", "may be migrated"), ("Finishes", "frees its space")]
    for x, (title, sub) in zip(xs, labels):
        parts += box(x, 44, 172, 56, title, sub, "#eef4fc" if title == "Placement" else box_fill)
    for a, b in zip(xs, xs[1:]):
        parts += arrow(a + 172, 72, b - 4, 72)
    parts.append(C.text(24, 150, "The life of a server", 15, C.INK, weight="bold"))
    parts += box(24, 166, 200, 56, "Asleep", "5 W")
    parts += box(390, 166, 200, 56, "Waking up", "full power for 10 s")
    parts += box(756, 166, 200, 56, "On", "45 W and up (HPE)")
    parts += arrow(224, 186, 386, 186, "a task is placed on it")
    parts += arrow(590, 186, 752, 186, "10 s later")
    parts.append(f'<path d="M856,222 C856,290 124,290 124,226" fill="none" stroke="{C.INK2}" stroke-width="1.6" '
                 f'marker-end="url(#arrow)"/>')
    parts.append(C.text(490, 300, "no work for 60 s: falls asleep", 11.5, C.INK2, "middle"))
    parts.append(C.text(24, 322, "Every 5 minutes the controller checks all servers: it moves tasks off overloaded ones "
                        "and empties servers under 30% so they can sleep.", 12, C.MUTED))
    path.write_text(C.document(width, height, "Life of a task and a server",
                               "Task: arrives, queues, is placed, runs, finishes. Server: asleep, waking, on, asleep again.",
                               parts), encoding="utf-8", newline="\n")


# ---------- assembly ----------

def render(context):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(HERE), undefined=jinja2.StrictUndefined,
                             autoescape=False, keep_trailing_newline=True)
    text = env.get_template("guide.md.j2").render(**context)
    body = markdown.markdown(text, extensions=["tables", "md_in_html", "attr_list", "sane_lists", "fenced_code"])
    css = (HERE / "style.css").read_text(encoding="utf-8")
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<title>Keeping each job together</title><style>{css}</style></head>'
            f'<body>{body}</body></html>')
    out = HERE / "guide.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


def print_pdf(html_path, profile):
    PDF.unlink(missing_ok=True)
    subprocess.run([str(EDGE), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={profile}", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=20000", f"--print-to-pdf={PDF}", html_path.as_uri()],
                   check=True, capture_output=True, timeout=180)
    if not PDF.exists():
        raise RuntimeError("Edge did not write the PDF")
    return PDF


def build(profile):
    CHARTS.mkdir(exist_ok=True)
    v, t = background()
    toy_example(v, t)
    team_values(v)
    v["test_count"] = unittest.defaultTestLoader.discover(str(ROOT / "RUSHI_Task" / "tests")).countTestCases()
    power_curve_chart(CHARTS / "power_curve.svg")
    life_chart(CHARTS / "life_of_a_task.svg")
    from RUSHI_Task.guide import results as R   # Parts C4 and E-F values
    r = R.values(S.build())
    v.update(r["v"])
    t.update(r["t"])
    for name in r["charts"]:
        shutil.copyfile(S.REPORTS / name, CHARTS / name)
    v["date"] = date.today().strftime("%B %d, %Y").replace(" 0", " ")
    return print_pdf(render({"v": v, "t": t}), profile)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True, help="throwaway Edge profile folder")
    args = parser.parse_args()
    print(build(args.profile))
