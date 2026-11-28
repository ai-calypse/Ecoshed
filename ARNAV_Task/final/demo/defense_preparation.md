# EcoSched defense preparation

Answers reflect active artifacts, not unimplemented plans. Presenter allocation remains provisional.

**What is the research novelty?** An isolated, explainable placement ablation: change CPU-oriented incremental-power scoring to CPU/memory balance-aware scoring while retaining the same LR/MMT controller, simulator, data and power assumptions. The contribution includes a defensible negative result, not a universal new scheduler.

**Why can memory-aware placement consume more energy?** It can prefer emptier already-powered hosts because the balance penalty outweighs the incremental-power advantage of busy hosts. Work spreads across more hosts that empty less readily. D5’s per-curve largest-workload on/work shares are 87.09%, 88.25% and 88.60% of each curve’s net gap; fewer wakes offset some cost. The earlier “about 88%” pooled ratio is not one physical measurement.

**Why Alibaba data?** It supplies actual task requests, multiplicity, timestamps, machine capacities and eligible observed attempts. We preserve those relationships rather than generating favorable workloads. Completed/window filters and request-based modeling still limit production representativeness.

**Why SPECpower?** It provides measured whole-server load-to-watts points. We interpolate them as a surrogate sensitivity model. They are not calibrated Alibaba hardware, and modeled kWh is not an observed electricity bill.

**What makes comparisons fair?** Primary pairs match workload size, curve, fixed 64-host pool, seed 2026, controller, admission, runtime, migration/sleep model and stopping rule. Both scores enforce memory feasibility. Additional baselines have no consolidation controller, so their comparison has broader differences.

**Why 36 rather than 54 experiments?** Four approved active policies × three sizes × three power curves. Historical additional policies are excluded from active conclusions, though their original code/results remain preserved.

**How is efficiency calculated?** Wh per completed individual instance = 1000 × modeled kWh / completed instances. A task group can contain many instances and is not the denominator.

**Why is pressure not an observed SLA?** It measures host-time above requested CPU/memory reservation thresholds. The model does not observe application deadlines or actual service failures.

**Why Kafka?** It demonstrates ordered, authentic workload transport and a separately verifiable monitoring pipeline for D6. It is not the core scheduling novelty and does not improve scheduler energy by itself.

**What happens to duplicates?** SQLite uniqueness and payload consistency checks count exact redelivery without inflating distinct instances. Conflicting identity/sequence payloads are errors that prevent successful verification. The established semantics are at least once with idempotent persistence.

**How does restart preserve counts?** Events/aggregates commit to SQLite before manual Kafka offset commits. Re-delivery after interruption is safe because persistence is idempotent. Full source-facing event verification, not counts alone, establishes completion.

**Is the live replay running the scheduler?** No. It transports arrivals and monitors offered requests, throughput, lag and integrity. Energy, active hosts, migrations and waiting on research pages come from earlier offline simulations.

**Can the original results be fully reproduced?** Exact active archive/member/prepared-output identities and independent raw-row validation are established; numerical results reconcile. Three historical metadata references remain unresolved and D6 did not rerun the complete scheduler matrix. Full historical lineage or fresh simulation replication is not claimed.

**What remains limited?** One selected window/pool, overlapping samples, complete-attempt filtering, no statistical replications, request-based utilization, surrogate power, assumed migration/sleep behavior, missing background/DAG dynamics, limited category observations and a single-broker laptop transport setup.

**What did each person implement?** Yaksh: historical D1 data/sampling handoff. Brave: event simulator, power and active raw/experiment integration. Rohan: documented D3 scheduling/controller modules, imported in Brave’s integration commit. Rushi: D5 accounting, observer, placement/skew analysis. Arnav: D6 artifact validation, dashboard, recovered-input verification, Kafka workers/controller/state, live monitoring, publication exports and final report/deck/runbook. Git authorship and implementation credit are explicitly separated.

**What was Arnav’s individual technical contribution?** A common numerically reconciled artifact layer; honest provenance diagnostics and exact input recovery; a professional eight-page offline/live dashboard; real ordered Kafka replay with durable idempotent SQLite state and event-level verification; reproducible publication assets; and this editable academic/demo package. Existing scheduling and preparation algorithms were reused rather than reimplemented. D6 work remains uncommitted.

**Did the proposed approach work?** It saved energy in 4/9 primary cases, with 10.96–14.56% penalties at the largest workload. Some performance metrics improved. The result identifies an energy/performance trade-off and a placement-scoring mechanism, not consistent energy savings or statistical significance.
