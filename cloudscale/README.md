# CloudScale: Cloud Network Infrastructure
## A Case Study on Cost Optimization and Scalability

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Streamlit-red.svg)](https://streamlit.io/)
[![Testing](https://img.shields.io/badge/tests-pytest-green.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## 1. Project Overview

**CloudScale** is a presentation-ready cloud infrastructure simulation and analytical case study dashboard. It models and contrasts two common infrastructure paradigms under dynamic e-commerce workloads:
1. **Traditional Fixed Infrastructure (Baseline):** A statically provisioned server fleet sized upfront.
2. **Dynamic Auto-Scaling Infrastructure:** An elastic, threshold-based horizontal scaling cluster that expands and contracts capacity in response to real-time workload fluctuations.

The project runs **100% locally on Windows** without requiring a paid AWS, GCP, or Azure subscription. It provides concrete numerical evidence, interactive visualizations, and downloadable academic reports for presentations, laboratory assignments, and viva defense.

---

## 2. Problem Statement

Modern online shopping platforms experience dramatic workload volatility throughout the day:
- **Off-Peak Hours (Night / Early Morning):** User traffic is minimal. A fixed cluster provisioned for peak load wastes significant capital paying for idle, underutilized compute resources.
- **Festival Sales / Flash Events:** User traffic surges exponentially (5x–10x baseline). If the fleet cannot scale out dynamically, CPU utilization saturates at 100%, request queues back up, latencies skyrocket beyond acceptable SLA thresholds, and customer transactions fail due to dropped connections.

**Core Objective:** Simulate, benchmark, and visualize the trade-offs between static overprovisioning/underprovisioning and dynamic cloud elasticity across **cost**, **utilization**, **latency**, and **availability**.

---

## 3. Key Features

- **Discrete-Time Simulation Engine:** Deterministic, reproducible time-step simulator modeling traffic generation, capacity bounds, queuing delays, and server lifecycle states.
- **Configurable Workload Patterns:**
  - *Constant Traffic*
  - *Gradual Linear Growth*
  - *Sudden Traffic Spike*
  - *Periodic / Daily Diurnal Wave*
  - *Festival Flash Sale (Phased surge and cooldown)*
  - *Randomized Stochastic Traffic*
- **Equal-Distribution Load Balancer:** Models traffic distribution across all active, healthy compute instances.
- **Horizontal Auto-Scaling Engine:**
  - Dual threshold scaling policy (Scale-Out $> 70\%$, Scale-In $< 30\%$).
  - Configurable cooldown periods preventing rapid oscillation (flapping).
  - Anti-flapping dampening logic preventing premature de-provisioning.
  - Virtual machine startup warmup delays (warmup state before accepting live traffic).
- **Queuing Latency Approximation Model:** Non-linear M/M/1 queuing approximation calculating average response time and 95th-percentile (p95) latency.
- **Transparent FinOps Cost Modeling:** Discrete server-hour billing calculating exact costs, savings percentages, and cost per 1,000 processed transactions.
- **Interactive Multi-Tab Dashboard:** Built with Streamlit and Plotly in a high-contrast dark navy aesthetic (`#0b132b`).
- **One-Click Predefined Scenarios:** 7 academic benchmarks covering business cycles, flash sales, off-peak savings, and ceiling overloads.
- **Automated Evidence-Based Recommendations:** Generates contextual cloud architecture recommendations derived strictly from calculated simulation results.
- **Exportable Academic Artifacts:** Downloadable CSV raw time-step telemetry, scenario benchmark CSVs, Markdown case study reports, and standalone HTML reports.

---

## 4. Architecture & Component Mapping

```
[ Simulated Users / Traffic Generator ]
                │
                ▼ (Incoming Requests RPM)
     [ Simulated Load Balancer ]
                │ (Equal Distribution)
  ┌─────────────┼─────────────┐
  ▼             ▼             ▼
[ VM-01 ]   [ VM-02 ]     [ VM-0N ]   (Active Application Server Cluster)
  │             │             │
  └─────────────┬─────────────┘
                ▼
  [ Processing & Queuing Engine ]
                │
                ▼ (CPU Utilization & Queues)
    [ Telemetry Metrics Monitor ]
                │
                ▼ (Scale-Out / Scale-In Thresholds)
   [ Auto-Scaling Policy Engine ]
                │
                ▼ (Spin Up / Terminate Instances)
      [ Cluster Orchestrator ]
                │
                ▼
  [ Cost Calculator & Dashboard ]
```

### Simulated vs. Production Cloud Architecture
| Component | CloudScale Simulation | Real Production Cloud Equivalent |
|---|---|---|
| **Traffic Generator** | Deterministic user generator with reproducible seed | Real user HTTP traffic / Load testing (k6, Locust) |
| **Load Balancer** | Equal distribution across active nodes | AWS Application Load Balancer (ALB) / NGINX |
| **Compute Nodes** | Homogeneous virtual servers (1,000 RPM capacity) | AWS EC2 (t3.medium / c5.large) or AWS ECS / EKS |
| **Scaling Engine** | Dual-threshold evaluation with cooldowns & startup lag | AWS Auto Scaling Groups (ASG) / Kubernetes HPA |
| **Cost Engine** | Server-hour discrete billing model | AWS Cost Explorer / FinOps billing exports |
| **Telemetry & SLA** | Queuing delay approximation model | Amazon CloudWatch / Datadog / OpenTelemetry |

---

## 5. Project Directory Structure

```
cloudscale/
│
├── app.py                          # Streamlit interactive web dashboard
├── requirements.txt                # Python package dependencies
├── README.md                       # Comprehensive documentation & presentation guide
├── .gitignore                      # Git exclusion rules
│
├── config/
│   └── default_config.json         # Default simulation parameters
│
├── core/
│   ├── __init__.py                 # Core package initializer
│   ├── validation.py               # Input constraints and validation
│   ├── simulator.py                # Traffic generation & queuing latency model
│   ├── autoscaling.py              # Fixed baseline & dynamic auto-scaler engines
│   ├── cost_calculator.py          # Financial analytics & savings formulas
│   ├── metrics.py                  # SLA, availability & automated recommendation engine
│   ├── scenarios.py                # 7 Predefined benchmark scenarios
│   └── reports.py                  # CSV, Markdown & HTML case study generators
│
├── tests/
│   ├── test_validation.py          # Validation & error handling unit tests
│   ├── test_simulator.py           # Traffic & integration tests
│   ├── test_autoscaling.py         # Scaling policies, cooldowns & delay tests
│   └── test_cost_calculator.py     # FinOps cost calculations & zero-baseline tests
│
└── reports/
    └── .gitkeep                    # Directory for generated reports
```

---

## 6. Installation & Execution (Windows PowerShell)

### Prerequisites
- Python 3.11 or higher installed on Windows.
- Windows PowerShell.

### Step 1: Navigate to Project Directory
```powershell
cd c:\Users\sudhi\OneDrive\Desktop\CN\cloudscale
```

### Step 2: (Optional but Recommended) Create & Activate Virtual Environment
```powershell
python -m venv .venv
```

If PowerShell displays an execution policy restriction (`script execution is disabled on this system`), run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then activate the environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 4: Run the Interactive Dashboard
```powershell
python -m streamlit run app.py
```
Streamlit will launch locally in your default web browser at:
**`http://localhost:8501`**

---

## 7. Running Automated Test Suite

To verify simulation logic, cooldown enforcement, cost calculations, and export generators:
```powershell
python -m pytest -v
```

Expected result:
```
tests/test_autoscaling.py::test_fixed_infrastructure_invariance PASSED
tests/test_autoscaling.py::test_autoscaling_scale_out_trigger PASSED
tests/test_autoscaling.py::test_autoscaling_scale_in_trigger PASSED
tests/test_autoscaling.py::test_min_and_max_server_limits_respected PASSED
tests/test_autoscaling.py::test_cooldown_enforcement PASSED
tests/test_autoscaling.py::test_startup_delay_behavior PASSED
tests/test_cost_calculator.py::test_calculate_cost_savings_pct_standard PASSED
tests/test_cost_calculator.py::test_calculate_cost_savings_pct_zero_baseline PASSED
tests/test_cost_calculator.py::test_calculate_cost_savings_pct_negative_savings PASSED
tests/test_cost_calculator.py::test_cost_accrual_math PASSED
tests/test_cost_calculator.py::test_empty_dataframe_cost_handling PASSED
tests/test_simulator.py::test_deterministic_random_seed PASSED
tests/test_simulator.py::test_zero_traffic_handling PASSED
tests/test_simulator.py::test_latency_model_behavior PASSED
tests/test_simulator.py::test_full_scenario_integration_and_exports PASSED
tests/test_validation.py::test_default_config_is_valid PASSED
tests/test_validation.py::test_invalid_server_boundaries PASSED
tests/test_validation.py::test_threshold_ordering_validation PASSED
tests/test_validation.py::test_negative_values_rejected PASSED
tests/test_validation.py::test_dict_conversion_and_casting PASSED
============================= 20 passed in 0.95s ==============================
```

---

## 8. Mathematical Formulations & Assumptions

### 1. Cluster Throughput Capacity
$$\text{Capacity}(t) = N_{\text{active}}(t) \times C_{\text{server}}$$
- $N_{\text{active}}(t)$: Number of active virtual servers online at time step $t$.
- $C_{\text{server}}$: Processing throughput per server (default: 1,000 requests/minute).

### 2. Workload CPU Utilization
$$\rho(t) = \frac{R_{\text{incoming}}(t)}{\text{Capacity}(t)}$$
$$\text{CPU Utilization}(t) = \min(100\%, \rho(t) \times 100\%)$$

### 3. Horizontal Scaling Hysteresis
- **Scale-Out Trigger:** Initiated when $\text{CPU}(t) > 70\%$ and cooldown has elapsed:
  $$N_{\text{new}} = \min(N_{\text{active}} + S_{\text{out}}, N_{\text{max}})$$
- **Scale-In Trigger:** Initiated when $\text{CPU}(t) < 30\%$, cooldown has elapsed, and anti-flap check confirms that removing nodes will not immediately breach the scale-out threshold:
  $$N_{\text{new}} = \max(N_{\text{active}} - S_{\text{in}}, N_{\text{min}})$$

### 4. Non-Linear Queuing Latency Model
$$\text{RT}(t) = L_0 + \Delta L(\rho)$$
- Base server latency $L_0 = 35\text{ ms}$.
- Healthy utilization ($\rho < 0.85$): Latency remains stable ($35\text{ ms} - 120\text{ ms}$).
- Elevated utilization ($0.85 \le \rho < 1.0$): Queue buffers increase latency ($120\text{ ms} - 350\text{ ms}$).
- Overload ($\rho \ge 1.0$): Server queue saturation and dropped requests ramp latency toward timeout ($2,500\text{ ms}$).
- $P95\text{ Latency} \approx \text{RT}(t) \times (1.35 + 0.45 \times \min(1.0, \rho))$.

### 5. Infrastructure Financial Model
$$\text{Cost} = \sum_{t=0}^{T-1} N_{\text{billable}}(t) \times \left(\frac{\Delta t}{60}\right) \times \text{Rate}_{\text{hour}}$$
- $N_{\text{billable}}(t) = N_{\text{active}}(t) + N_{\text{provisioning}}(t)$ (Warmup instances are billable).
- $\text{Cost Savings (\%)} = \left(\frac{\text{Fixed Cost} - \text{Auto-Scaling Cost}}{\text{Fixed Cost}}\right) \times 100\%$

---

## 9. Predefined Benchmark Scenarios

1. **Normal Business Day:** Diurnal traffic wave. Demonstrates steady 35%–45% cost savings with zero dropped requests.
2. **Gradual Traffic Growth:** Incremental ramp testing step-by-step capacity expansion without latency surges.
3. **Festival Sale Traffic Spike:** 6x flash-sale surge. Overwhelms fixed baseline while auto-scaling sustains transaction processing.
4. **Sudden Traffic Surge:** Tests physical reality of server startup delays (warmup lag) and transient latency queues.
5. **Low Traffic & Cost Optimization:** Night-time lull demonstrating dramatic 60%–70% budget reduction by scaling down to minimum nodes.
6. **Extreme Overload (Capacity Capped):** Workload exceeding max server ceilings to demonstrate system behavior during resource exhaustion.
7. **Maximum Capacity Stress Test:** Randomized fluctuating traffic testing cooldown stability and anti-flapping protection.

---

## 10. Five-Minute Presentation Demonstration Sequence

When presenting this project for an evaluation or viva examination:

1. **Minute 1 — Problem Statement & Fixed Architecture Flaws:**
   - Open the **Overview Tab**.
   - Explain why statically provisioning 10 servers creates an expensive dilemma: paying for idle servers at night, but risking crashes during Diwali / Black Friday flash sales.
2. **Minute 2 — Festival Sale Live Simulation:**
   - Select the **Festival Sale Traffic Spike** preset in the sidebar.
   - Point out the KPI comparison: Auto-scaling achieves **100% Request Success Rate** while the fixed baseline drops customer orders.
3. **Minute 3 — Live Server Cluster Inspection:**
   - Switch to the **Live Simulation Tab**.
   - Move the step scrubber to minute 25. Show how virtual nodes transition from `WARMING UP` (startup delay) to `ONLINE`, and how traffic is distributed across the cluster.
4. **Minute 4 — Scalability & Cost Curves:**
   - Switch to **Scalability Analysis** and **Cost Optimization Tabs**.
   - Highlight the dynamic server count matching incoming request curves, and explain the cumulative cost curves.
5. **Minute 5 — Recommendations & Academic Reports:**
   - Switch to **Recommendations & Reports Tab**.
   - Show the automated evidence-based recommendations generated from calculated data.
   - Demonstrate downloading the **Case Study Report (HTML / Markdown)** and **Simulation Data (CSV)**.

---

## 11. Limitations & Assumptions Disclosure

1. **Local Mathematical Simulation:** All metrics are generated using deterministic queuing and elasticity models; this tool does not connect to AWS or generate cloud invoices.
2. **Homogeneous Virtual Machines:** All compute instances are modeled as uniform units with identical capacity.
3. **Simplified Network Latency:** Network backbone jitter and database lock contention are abstracted through standard queuing formulations.

---

## 12. Troubleshooting

- **PowerShell Script Execution Error:**  
  Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell terminal.
- **Port 8501 Already in Use:**  
  Run `python -m streamlit run app.py --server.port 8502`.
- **ModuleNotFoundError:**  
  Ensure you have run `python -m pip install -r requirements.txt`.

---
*Created for CloudScale: Cloud Network Infrastructure Case Study.*
