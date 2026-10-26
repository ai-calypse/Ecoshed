# EcoSched

EcoSched is an AMS 560 project studying whether CPU-and-memory-aware placement can reduce modeled data-center energy use without unacceptable overload or migration costs.

The planned experiment compares **LR-MMT** with **LR-MMT + CPU/Memory-Aware Placement** using the same Alibaba workload, hosts, simulator, and SPECpower energy model. Results will describe the simulation, not Alibaba's actual electricity consumption.

## Current status

**Data preparation is complete. Simulator and scheduling experiments are next.**

| Deliverable | Status |
|---|---|
| D1: Reproducible workload package | Complete — [Yaksh's task and handoff](YAKSH_Task/README.md) |
| D2: Simulator and power model | Next |
| D3: Scheduling policies | Pending simulator integration |
| D4–D6: Experiments, analysis, demo and final report | Pending |

## Start here

1. Read [YAKSH_Task/README.md](YAKSH_Task/README.md) for what is ready and what the next teammate should do.
2. Run the data checks below. Python 3.10+ is sufficient; no packages need installing.
3. Use the [simulator handoff](YAKSH_Task/docs/SIMULATOR_HANDOFF.md) to integrate the prepared inputs.

```sh
python3 -m unittest discover -s YAKSH_Task/scripts -p 'test_*.py'
python3 YAKSH_Task/scripts/validate_data.py
```

Both commands are read-only and preserve the recorded full-source verification report.

The prepared files are already in the repository. **You do not need to download or process the raw trace to start the simulator.**

## Repository guide

| Location | Contents |
|---|---|
| [YAKSH_Task/](YAKSH_Task/) | Yaksh's completed data preparation, inputs, code, checks and handoff |
| [YAKSH_Task/REPORT.md](YAKSH_Task/REPORT.md) | Detailed data quality and sampling report |
| [docs/EcoSched_Proposal.pdf](docs/EcoSched_Proposal.pdf) | Original project proposal, preserved as submitted |
| [Latest handoff release](https://github.com/ai-calypse/Ecoshed/releases/tag/data-v1.1.0) | Updated portable handoff ZIP |
| [Original input downloads](https://github.com/ai-calypse/Ecoshed/releases/tag/data-v1.0.0) | Unmodified raw-data archive and proposal video |

Large original inputs are release assets to keep clones small. See [raw-data instructions](docs/RAW_DATA.md) only if you need to rebuild the inputs.

## Experiment inputs

Every policy must use the same fixed 64-host pool and the same workload files. Prepared workloads contain 250, 1,000 and 4,000 **task groups**. Each group represents its original `instance_num` independently schedulable instances.

Start with 250 groups for integration, then 1,000 for comparison. The 4,000-group input is a heavy burst stress case. Runtime estimates, missing measurements and resource units are documented with the data. Every sample now passes explicit instance/CPU/memory arrival-profile and resource-mix limits; see [sampling quality](YAKSH_Task/docs/SAMPLING_QUALITY.md).

## Sources

- [Alibaba Cluster Trace Program, v2017](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017)
- [SPECpower results](https://www.spec.org/power_ssj2008/results/) — planned source for the simulator's power model

The original proposal records the initial team allocation. The current handoff credits the completed data-preparation work to **Yaksh Gandhi**.
