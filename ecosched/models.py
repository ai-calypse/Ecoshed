"""Engine state and immutable, non-clairvoyant scheduling interfaces."""
from dataclasses import dataclass
import math


def positive(value, label):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be positive and finite")


@dataclass(frozen=True)
class HostSpec:
    host_id: str
    cpu: float
    memory: float

    def __post_init__(self):
        positive(self.cpu, "Host CPU")
        positive(self.memory, "Host memory")


@dataclass(frozen=True)
class Request:
    instance_id: str
    task_group_id: str
    cpu: float
    memory: float
    arrival: float


@dataclass(frozen=True)
class HostView:
    host_id: str
    cpu_capacity: float
    memory_capacity: float
    cpu_used: float
    memory_used: float
    state: str

    def fits(self, request):
        return (self.cpu_used + request.cpu <= self.cpu_capacity + 1e-9
                and self.memory_used + request.memory <= self.memory_capacity + 1e-12)


@dataclass(frozen=True)
class RunningView:
    request: Request
    host_id: str
    started_at: float
    state: str


@dataclass(frozen=True)
class Migration:
    instance_id: str
    destination: str


@dataclass
class Host:
    spec: HostSpec
    cpu: float = 0.0
    memory: float = 0.0
    state: str = "sleep"
    ready_at: float = 0.0
    idle_since: float | None = None
    energy_j: float = 0.0
    reservations: int = 0

    def view(self):
        return HostView(self.spec.host_id, self.spec.cpu, self.spec.memory,
                        self.cpu, self.memory, self.state)


@dataclass
class Allocation:
    request: Request
    host_id: str
    start: float
    finish: float
    generation: int = 0
    state: str = "running"
    destination: str | None = None
