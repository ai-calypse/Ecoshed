"""The same-job (finish-together) rule on Rohan's two LR-MMT policies (DESIGN.md here).

A server can only sleep when its last task leaves. Tasks of the same job (task
group) are created together and tend to finish together, so placing a task next
to tasks of its own job lets a server empty in one go.

The rule, added in front of Rohan's unchanged score (ROHAN_Task/policies.py):
    use a server that
      1. is running work right now,
      2. already has tasks of this job (by the policy's own records), and
      3. stays under the controller's overload line after this task
         (Rohan's own _pressure test: memory 90%, CPU forecast x 1.2);
    if several servers qualify, Rohan's score picks among them. If none qualifies,
    Rohan's original policy decides exactly as before.

Conditions 1 and 3 keep the rule from waking or refilling a server, and from
overcrowding one (which would make the controller move the job's tasks apart).
No new numbers are introduced.

The LR-MMT controller (LR forecast, MMT, 30% underload rule, cooldowns) is
inherited unchanged and uses the same order for migration destinations. The
policy sees only what the engine gives every policy: each request's job id, host
snapshots, and every 5 minutes the running tasks. It never sees durations. It is
not told when a task finishes, so between controller ticks it remembers its own
placements, and at each tick it rebuilds its records from the running list.
"""
from collections import Counter, defaultdict

from ROHAN_Task.policies import LRMMT


class SameJobLRMMT(LRMMT):
    """Rohan's LR-MMT (CPU-only or memory-aware) plus the same-job rule.

    With same_job=False it is Rohan's policy exactly (unit test), so every
    difference in the results comes from the rule.
    """

    def __init__(self, simulation_config, curve=None, config=None, memory_aware=False, same_job=True, name=None):
        super().__init__(simulation_config, curve, config, memory_aware=memory_aware)
        self.same_job = same_job
        if name:
            self.name = name
        elif same_job:
            self.name = self.name + "_same_job"
        self.jobs_on = defaultdict(Counter)   # host -> {task_group_id: tasks placed there}

    def next_to_job(self, request, host):
        """True if the rule applies to this server for this task (conditions 1-3)."""
        return (host.cpu_used > 0
                and self.jobs_on[host.host_id][request.task_group_id] > 0
                and self._pressure(self._add(host, request)) < 1)

    def _score(self, request, host):
        original = super()._score(request, host)           # (Rohan's score, host id)
        if not self.same_job:
            return original
        return (0 if self.next_to_job(request, host) else 1, *original)

    def select_host(self, request, hosts, now):
        choice = super().select_host(request, hosts, now)
        if choice is not None:
            self.jobs_on[choice][request.task_group_id] += 1
        return choice

    def on_tick(self, now, hosts, running):
        # Rebuild the records from the engine's list of running tasks (exact at a tick).
        self.jobs_on = defaultdict(Counter)
        where = {}
        for task in running:
            self.jobs_on[task.host_id][task.request.task_group_id] += 1
            where[task.request.instance_id] = task
        plans = super().on_tick(now, hosts, running)
        for plan in plans:  # planned moves: count the task at its destination from now on
            task = where[plan.instance_id]
            self.jobs_on[task.host_id][task.request.task_group_id] -= 1
            self.jobs_on[plan.destination][task.request.task_group_id] += 1
        return plans


POLICIES = {
    # name: memory_aware
    "lr_mmt_same_job": False,
    "lr_mmt_memory_same_job": True,
}


def make_policy(name, simulation_config, curve):
    return SameJobLRMMT(simulation_config, curve, memory_aware=POLICIES[name], name=name)
