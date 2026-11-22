"""Piecewise linear SPECpower target-load curves; watts integrate to joules."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

CURVE_FILE = Path(__file__).with_name("power_curves.json")


@dataclass(frozen=True)
class PowerCurve:
    name: str
    watts: tuple[float, ...]
    source: str = ""

    def __post_init__(self):
        if len(self.watts) != 11 or any(not math.isfinite(w) or w < 0 for w in self.watts):
            raise ValueError("Power curve needs 11 finite nonnegative watts at 0,10,...,100%")

    def power(self, utilization: float) -> float:
        if not math.isfinite(utilization) or not 0 <= utilization <= 1:
            raise ValueError("CPU utilization must be finite and within [0, 1]")
        x = utilization * 10
        i = min(int(x), 9)
        return self.watts[i] + (self.watts[i + 1] - self.watts[i]) * (x - i)


def load_curve(name="hpe_dl360_gen9") -> PowerCurve:
    data = json.loads(CURVE_FILE.read_text(encoding="utf-8"))
    row = data["curves"][name]
    return PowerCurve(name, tuple(row["watts"]), row["source"])
