"""Energy is the first objective; resource complementarity breaks power ties."""
from ROHAN_Task.policies import LRMMT


class EnergyFirst(LRMMT):
    def __init__(self, simulation_config, curve, memory_aware=False, controller=True):
        super().__init__(simulation_config, curve, memory_aware=memory_aware)
        self.name = "energy_first_memory" if memory_aware else "energy_first_cpu"
        self.controller = controller

    def _score(self, request, host):
        cpu = min(1.0, (host.cpu_used + request.cpu) / host.cpu_capacity)
        memory = (host.memory_used + request.memory) / host.memory_capacity
        before = (self.simulation.sleep_watts if host.state == "sleep"
                  else self.curve.power(min(1.0, max(0.0, host.cpu_used / host.cpu_capacity))))
        delta_watts = self.curve.power(cpu) - before
        # A nanowatt tolerance suppresses only floating-point roundoff. No
        # weighted balance term can override a materially cheaper destination.
        secondary = abs(cpu - memory) if self.memory_aware else -cpu
        return round(delta_watts, 9), secondary, -cpu, host.host_id

    def on_tick(self, now, hosts, running):
        if self.controller:
            return super().on_tick(now, hosts, running)
        return []
