"""Print styling and deterministic vector/raster serialization."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ARNAV_Task.dashboard.constants import POLICY_COLORS, SKEW_COLORS

LABELS = {"first_fit": "First Fit", "best_fit": "Best Fit", "lr_mmt": "CPU LR-MMT",
          "lr_mmt_memory": "CPU/memory LR-MMT"}
CURVE_LABELS = {"hpe_dl360_gen9": "HPE DL360 Gen9", "huawei_rh2288h_v3": "Huawei RH2288H V3",
                "quanta_d51b_2u": "QuantaGrid D51B-2U"}


def configure(config):
    matplotlib.rcParams.update({"font.family": [config["font_family"], "sans-serif"], "font.size": 9,
        "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#56616b", "text.color": "#17212b",
        "axes.labelcolor": "#17212b", "figure.facecolor": "white", "axes.facecolor": "white",
        "grid.alpha": .22, "grid.linewidth": .5, "svg.fonttype": "none",
        "svg.hashsalt": config["svg_hashsalt"], "pdf.fonttype": 42, "ps.fonttype": 42})


def save_figure(fig, directory, identifier, config):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for extension in config["formats"]:
        path = directory / f"{identifier}.{extension}"
        metadata = ({"Date": None, "Creator": "EcoSched D6"} if extension == "svg" else
                    {"CreationDate": None, "ModDate": None, "Creator": "EcoSched D6"} if extension == "pdf" else
                    {"Software": "EcoSched D6"})
        fig.savefig(path, dpi=config["dpi"], bbox_inches="tight", pad_inches=.16, metadata=metadata)
        paths.append(path)
    plt.close(fig)
    return paths


def json_write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
