"""Academic case study report generation and export utilities for CloudScale."""

from typing import Dict, Any, List
import pandas as pd
from datetime import datetime

from core.validation import SimulationConfig
from core.metrics import SimulationComparison


def generate_merged_simulation_csv(fixed_df: pd.DataFrame, as_df: pd.DataFrame) -> str:
    """
    Merge Fixed and Auto-Scaling simulation data into a single comprehensive CSV
    with clean, descriptive column headers suitable for data analysis.
    """
    merged = pd.DataFrame()
    merged["Time_Step"] = fixed_df["step"]
    merged["Time_Elapsed_Minutes"] = fixed_df["time_minutes"]
    merged["Active_Users"] = fixed_df["users"]
    merged["Incoming_Requests_RPM"] = fixed_df["incoming_requests"]

    # Fixed Infrastructure Metrics
    merged["Fixed_Active_Servers"] = fixed_df["active_servers"]
    merged["Fixed_Capacity_RPM"] = fixed_df["capacity_rpm"]
    merged["Fixed_Processed_Requests"] = fixed_df["processed_requests"]
    merged["Fixed_Dropped_Requests"] = fixed_df["dropped_requests"]
    merged["Fixed_CPU_Util_Pct"] = fixed_df["cpu_utilization_pct"]
    merged["Fixed_Avg_Latency_MS"] = fixed_df["avg_response_time_ms"]
    merged["Fixed_P95_Latency_MS"] = fixed_df["p95_response_time_ms"]
    merged["Fixed_Cumulative_Cost_USD"] = fixed_df["cumulative_cost_usd"]

    # Auto-Scaling Metrics
    merged["AS_Active_Servers"] = as_df["active_servers"]
    merged["AS_Provisioning_Servers"] = as_df["provisioning_servers"]
    merged["AS_Total_Servers"] = as_df["total_servers"]
    merged["AS_Capacity_RPM"] = as_df["capacity_rpm"]
    merged["AS_Processed_Requests"] = as_df["processed_requests"]
    merged["AS_Dropped_Requests"] = as_df["dropped_requests"]
    merged["AS_CPU_Util_Pct"] = as_df["cpu_utilization_pct"]
    merged["AS_Avg_Latency_MS"] = as_df["avg_response_time_ms"]
    merged["AS_P95_Latency_MS"] = as_df["p95_response_time_ms"]
    merged["AS_Cumulative_Cost_USD"] = as_df["cumulative_cost_usd"]
    merged["AS_Scaling_Action"] = as_df["scaling_action"]

    return merged.to_csv(index=False)


def generate_markdown_report(
    config: SimulationConfig,
    comparison: SimulationComparison,
    scenario_name: str = "Custom Simulation"
) -> str:
    """
    Generate an academic case study report in Markdown format.
    """
    fixed = comparison.fixed_metrics
    autoscaling = comparison.as_metrics
    cost = comparison.cost_comparison
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    savings_str = cost.savings_percent_display

    rec_md = ""
    for r in comparison.recommendations:
        rec_md += f"- **[{r['severity']}] {r['category']}**: {r['finding']}\n  *Actionable Recommendation*: {r['recommendation']}\n\n"

    report = f"""# CloudScale: Cloud Network Infrastructure Case Study
## Cost Optimization and Scalability Analysis Report

**Date of Evaluation:** {now}  
**Scenario Title:** {scenario_name}  
**Methodology:** Deterministic Discrete Time-Step Simulation with Queuing Delay Approximation  

---

### 1. Executive Summary

This case study investigates horizontal elastic scaling versus static capacity allocation for an e-commerce cloud network workload. Under simulated demand varying from **{config.initial_users:,}** to **{config.peak_users:,}** concurrent users, our objective was to evaluate cost reduction, server utilization efficiency, and request availability.

**Key Findings:**
- **Baseline Fixed Spending:** ${cost.fixed.total_cost_usd:.2f} ({cost.fixed.total_server_hours:.2f} server-hours)
- **Auto-Scaling Spending:** ${cost.autoscaling.total_cost_usd:.2f} ({cost.autoscaling.total_server_hours:.2f} server-hours)
- **Net Financial Impact:** ${cost.absolute_savings_usd:.2f} ({savings_str})
- **Request Availability:** Fixed = **{fixed.request_success_rate_pct:.2f}%** | Auto-Scaling = **{autoscaling.request_success_rate_pct:.2f}%**
- **SLA Compliance Target (<={config.sla_target_response_time_ms} ms):** Fixed = **{fixed.sla_compliance_rate_pct:.1f}%** | Auto-Scaling = **{autoscaling.sla_compliance_rate_pct:.1f}%**
- **Dynamic Scaling Actions:** {autoscaling.scaling_events_count} total events ({autoscaling.scale_out_count} scale-outs, {autoscaling.scale_in_count} scale-ins)

---

### 2. Experimental Configuration & Assumptions

| Parameter | Value | Description / Unit |
|---|---|---|
| Simulation Duration | {config.duration_steps} steps | Total evaluation intervals (1 step = {config.step_unit_minutes} min) |
| Traffic Pattern | {config.traffic_pattern} | Workload generation model |
| Initial / Peak Users | {config.initial_users:,} / {config.peak_users:,} | Concurrent customer load |
| User Request Rate | {config.requests_per_user_min} req/min | Workload generated per active user |
| Fixed Server Fleet | {config.fixed_servers} instances | Baseline static capacity ({config.fixed_servers * config.server_capacity_rpm:,.0f} req/min total) |
| Auto-Scaling Range | {config.as_min_servers} min - {config.as_max_servers} max | Dynamic boundaries (Initial: {config.as_initial_servers}) |
| Server Capacity | {config.server_capacity_rpm:,.0f} req/min | Peak sustainable throughput per virtual machine |
| Scale-Out Trigger | > {config.cpu_scale_out_threshold}% CPU | Horizontal elasticity expansion threshold |
| Scale-In Trigger | < {config.cpu_scale_in_threshold}% CPU | Elastic contraction threshold with anti-flap dampening |
| Cooldown Periods | Out: {config.scale_out_cooldown} steps / In: {config.scale_in_cooldown} steps | Prevents rapid oscillation / thrashing |
| VM Startup Delay | {config.startup_delay} steps | Warmup/provisioning latency before taking traffic |
| Unit Pricing | ${config.cost_per_server_hour:.2f} / server-hour | Standard hourly cloud compute rate assumption |
| Target SLA Latency | {config.sla_target_response_time_ms} ms | Maximum acceptable customer response time |
| Deterministic Seed | {config.random_seed} | Ensures 100% reproducible scenario execution |

---

### 3. Detailed Comparative Performance Metrics

| Performance Dimension | Fixed Infrastructure Baseline | Auto-Scaling Infrastructure | Delta / Variance |
|---|---|---|---|
| **Total Incurred Cost** | **${cost.fixed.total_cost_usd:.2f}** | **${cost.autoscaling.total_cost_usd:.2f}** | **${cost.absolute_savings_usd:.2f} ({savings_str})** |
| Total Server-Hours Billed | {cost.fixed.total_server_hours:.2f} hrs | {cost.autoscaling.total_server_hours:.2f} hrs | {cost.fixed.total_server_hours - cost.autoscaling.total_server_hours:.2f} hrs |
| Cost per 1,000 Incoming Req | ${cost.fixed.cost_per_1k_incoming_requests:.4f} | ${cost.autoscaling.cost_per_1k_incoming_requests:.4f} | ${cost.fixed.cost_per_1k_incoming_requests - cost.autoscaling.cost_per_1k_incoming_requests:.4f} |
| Cost per 1,000 Processed Req | ${cost.fixed.cost_per_1k_processed_requests:.4f} | ${cost.autoscaling.cost_per_1k_processed_requests:.4f} | ${cost.fixed.cost_per_1k_processed_requests - cost.autoscaling.cost_per_1k_processed_requests:.4f} |
| **Total Incoming Requests** | {fixed.total_incoming_requests:,.0f} | {autoscaling.total_incoming_requests:,.0f} | 0 |
| **Successfully Processed** | {fixed.total_processed_requests:,.0f} | {autoscaling.total_processed_requests:,.0f} | +{autoscaling.total_processed_requests - fixed.total_processed_requests:,.0f} |
| **Dropped / Unserved Requests** | {fixed.total_dropped_requests:,.0f} | {autoscaling.total_dropped_requests:,.0f} | -{fixed.total_dropped_requests - autoscaling.total_dropped_requests:,.0f} |
| **Request Success Rate** | **{fixed.request_success_rate_pct:.2f}%** | **{autoscaling.request_success_rate_pct:.2f}%** | **+{autoscaling.request_success_rate_pct - fixed.request_success_rate_pct:.2f}%** |
| Average CPU Utilization | {fixed.avg_cpu_utilization_pct:.1f}% | {autoscaling.avg_cpu_utilization_pct:.1f}% | {autoscaling.avg_cpu_utilization_pct - fixed.avg_cpu_utilization_pct:.1f}% |
| Peak CPU Utilization | {fixed.peak_cpu_utilization_pct:.1f}% | {autoscaling.peak_cpu_utilization_pct:.1f}% | {autoscaling.peak_cpu_utilization_pct - fixed.peak_cpu_utilization_pct:.1f}% |
| Average Response Time | {fixed.avg_response_time_ms:.1f} ms | {autoscaling.avg_response_time_ms:.1f} ms | {autoscaling.avg_response_time_ms - fixed.avg_response_time_ms:.1f} ms |
| Estimated P95 Latency | {fixed.p95_response_time_ms:.1f} ms | {autoscaling.p95_response_time_ms:.1f} ms | {autoscaling.p95_response_time_ms - fixed.p95_response_time_ms:.1f} ms |
| SLA Compliance Rate | {fixed.sla_compliance_rate_pct:.1f}% | {autoscaling.sla_compliance_rate_pct:.1f}% | +{autoscaling.sla_compliance_rate_pct - fixed.sla_compliance_rate_pct:.1f}% |
| Overload Duration | {fixed.overload_duration_steps} steps ({fixed.overload_duration_minutes} min) | {autoscaling.overload_duration_steps} steps ({autoscaling.overload_duration_minutes} min) | -{fixed.overload_duration_steps - autoscaling.overload_duration_steps} steps |
| Server Range Utilized | Fixed: {fixed.peak_servers} nodes | Active: {config.as_min_servers} - {autoscaling.peak_servers} nodes | Dynamic Range |

---

### 4. Mathematical Model & Formulation

1. **Processing Capacity:**  
   $$\\text{{Capacity}}(t) = N_{{\\text{{active}}}}(t) \\times C_{{\\text{{server}}}}$$

2. **Load Balancer Request Assignment:**  
   $$R_{{\\text{{server}}}}(t) = \\frac{{R_{{\\text{{incoming}}}}(t)}}{{N_{{\\text{{active}}}}(t)}}$$

3. **CPU Utilization:**  
   $$\\rho(t) = \\min\\left(100\\%, \\frac{{R_{{\\text{{incoming}}}}(t)}}{{\\text{{Capacity}}(t)}} \\times 100\\%\\right)$$

4. **Latency Estimation (Queuing Approximation):**  
   $$RT(t) = L_0 + \\Delta L\\left(\\rho(t)\\right)$$
   Where $L_0 = 35\\text{{ ms}}$ base latency, escalating with server utilization up to timeout saturation.

5. **Infrastructure Expenditure:**  
   $$\\text{{Cost}} = \\sum_{{t=0}}^{{T-1}} N_{{\\text{{billable}}}}(t) \\times \\left(\\frac{{\\Delta t}}{{60}}\\right) \\times \\text{{Rate}}_{{\\text{{hour}}}}$$

6. **Relative Cost Savings:**  
   $$\\text{{Savings}} = \\frac{{\\text{{Cost}}_{{\\text{{fixed}}}} - \\text{{Cost}}_{{\\text{{AS}}}}}}{{\\text{{Cost}}_{{\\text{{fixed}}}}}} \\times 100\\%$$

---

### 5. Automated Evidence-Based Recommendations

{rec_md}

---

### 6. Limitations & Cloud Model Disclosures

1. **Local Mathematical Simulation:** This analysis runs locally on synthetic discrete time steps and does not connect to live AWS/GCP/Azure infrastructure or produce binding invoices.
2. **Simplified Network Latency:** Network transport jitters, DNS routing variations, and distributed database lock contention are abstracted through standard queuing approximations.
3. **Instance Homogeneity:** All virtual machines are treated as identical uniform compute units.

---
*Report generated automatically by CloudScale: Cloud Network Infrastructure Case Study Tool.*
"""
    return report


def generate_html_report(
    config: SimulationConfig,
    comparison: SimulationComparison,
    scenario_name: str = "Custom Simulation"
) -> str:
    """
    Generate a standalone, beautifully styled HTML case study report.
    """
    fixed = comparison.fixed_metrics
    autoscaling = comparison.as_metrics
    cost = comparison.cost_comparison
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rec_items_html = ""
    for r in comparison.recommendations:
        badge_color = "#38bdf8"
        if r["severity"] == "CRITICAL":
            badge_color = "#f43f5e"
        elif r["severity"] == "WARNING":
            badge_color = "#fbbf24"
        elif r["severity"] == "POSITIVE":
            badge_color = "#34d399"

        rec_items_html += f"""
        <div style="background: rgba(255,255,255,0.03); border-left: 4px solid {badge_color}; padding: 14px 18px; margin-bottom: 12px; border-radius: 4px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="background: {badge_color}; color: #0b132b; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">{r['severity']}</span>
                <strong style="color: #f1f5f9; font-size: 14px;">{r['category']}</strong>
            </div>
            <div style="color: #cbd5e1; font-size: 13px; margin-bottom: 4px;">{r['finding']}</div>
            <div style="color: #94a3b8; font-size: 12px; font-style: italic;"><strong>Action:</strong> {r['recommendation']}</div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CloudScale Case Study Report — {scenario_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0b132b;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 30px;
            margin: 0;
        }}
        .container {{
            max-width: 1080px;
            margin: 0 auto;
            background: #1c2541;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        h1 {{
            color: #64dfdf;
            margin-top: 0;
            font-size: 28px;
            border-bottom: 2px solid #3a506b;
            padding-bottom: 12px;
        }}
        h2 {{
            color: #48bfe3;
            font-size: 20px;
            margin-top: 32px;
            border-bottom: 1px solid #3a506b;
            padding-bottom: 6px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }}
        .kpi-card {{
            background: #0b132b;
            padding: 18px;
            border-radius: 8px;
            border: 1px solid #3a506b;
            text-align: center;
        }}
        .kpi-title {{
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .kpi-value {{
            font-size: 26px;
            font-weight: 700;
            color: #64dfdf;
            margin-top: 6px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        th, td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid #3a506b;
        }}
        th {{
            background: #0b132b;
            color: #48bfe3;
            font-weight: 600;
        }}
        tr:hover td {{
            background: rgba(255,255,255,0.02);
        }}
        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .tag-success {{ background: #065f46; color: #a7f3d0; }}
        .tag-warning {{ background: #78350f; color: #fde68a; }}
        .tag-danger {{ background: #881337; color: #fecdd3; }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
            border-top: 1px solid #3a506b;
            padding-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CloudScale: Cloud Network Infrastructure Case Study</h1>
        <p style="color: #94a3b8; margin-top: -8px;">
            Cost Optimization and Scalability Analysis &bull; Scenario: <strong>{scenario_name}</strong> &bull; Generated: {now}
        </p>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Fixed Baseline Cost</div>
                <div class="kpi-value" style="color: #94a3b8;">${cost.fixed.total_cost_usd:.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Auto-Scaling Cost</div>
                <div class="kpi-value" style="color: #38bdf8;">${cost.autoscaling.total_cost_usd:.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Net Savings</div>
                <div class="kpi-value" style="color: #34d399;">{cost.savings_percent_display}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">AS Request Success Rate</div>
                <div class="kpi-value" style="color: #64dfdf;">{autoscaling.request_success_rate_pct:.1f}%</div>
            </div>
        </div>

        <h2>Comparative Evaluation Matrix</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Fixed Baseline</th>
                    <th>Auto-Scaling</th>
                    <th>Variance / Impact</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Total Incurred Cost</td>
                    <td><strong>${cost.fixed.total_cost_usd:.2f}</strong></td>
                    <td><strong>${cost.autoscaling.total_cost_usd:.2f}</strong></td>
                    <td><strong style="color: #34d399;">${cost.absolute_savings_usd:.2f} ({cost.savings_percent_display})</strong></td>
                </tr>
                <tr>
                    <td>Server-Hours Billed</td>
                    <td>{cost.fixed.total_server_hours:.2f} hrs</td>
                    <td>{cost.autoscaling.total_server_hours:.2f} hrs</td>
                    <td>{cost.fixed.total_server_hours - cost.autoscaling.total_server_hours:.2f} hrs</td>
                </tr>
                <tr>
                    <td>Total Incoming Requests</td>
                    <td>{fixed.total_incoming_requests:,.0f}</td>
                    <td>{autoscaling.total_incoming_requests:,.0f}</td>
                    <td>Identical Workload</td>
                </tr>
                <tr>
                    <td>Processed Requests</td>
                    <td>{fixed.total_processed_requests:,.0f}</td>
                    <td>{autoscaling.total_processed_requests:,.0f}</td>
                    <td>+{autoscaling.total_processed_requests - fixed.total_processed_requests:,.0f}</td>
                </tr>
                <tr>
                    <td>Dropped Requests</td>
                    <td><span class="tag {('tag-danger' if fixed.total_dropped_requests > 0 else 'tag-success')}">{fixed.total_dropped_requests:,.0f}</span></td>
                    <td><span class="tag {('tag-danger' if autoscaling.total_dropped_requests > 0 else 'tag-success')}">{autoscaling.total_dropped_requests:,.0f}</span></td>
                    <td>Reduced by {fixed.total_dropped_requests - autoscaling.total_dropped_requests:,.0f}</td>
                </tr>
                <tr>
                    <td>Request Success Rate</td>
                    <td>{fixed.request_success_rate_pct:.2f}%</td>
                    <td>{autoscaling.request_success_rate_pct:.2f}%</td>
                    <td>+{autoscaling.request_success_rate_pct - fixed.request_success_rate_pct:.2f}%</td>
                </tr>
                <tr>
                    <td>Average CPU Utilization</td>
                    <td>{fixed.avg_cpu_utilization_pct:.1f}%</td>
                    <td>{autoscaling.avg_cpu_utilization_pct:.1f}%</td>
                    <td>Balanced Headroom</td>
                </tr>
                <tr>
                    <td>Average Response Time</td>
                    <td>{fixed.avg_response_time_ms:.1f} ms</td>
                    <td>{autoscaling.avg_response_time_ms:.1f} ms</td>
                    <td>{autoscaling.avg_response_time_ms - fixed.avg_response_time_ms:+.1f} ms</td>
                </tr>
                <tr>
                    <td>SLA Compliance (&le; {config.sla_target_response_time_ms} ms)</td>
                    <td>{fixed.sla_compliance_rate_pct:.1f}%</td>
                    <td>{autoscaling.sla_compliance_rate_pct:.1f}%</td>
                    <td>+{autoscaling.sla_compliance_rate_pct - fixed.sla_compliance_rate_pct:.1f}%</td>
                </tr>
                <tr>
                    <td>Overload Duration</td>
                    <td>{fixed.overload_duration_steps} steps</td>
                    <td>{autoscaling.overload_duration_steps} steps</td>
                    <td>-{fixed.overload_duration_steps - autoscaling.overload_duration_steps} steps</td>
                </tr>
                <tr>
                    <td>Active Server Range</td>
                    <td>Fixed: {fixed.peak_servers}</td>
                    <td>Dynamic: {config.as_min_servers} to {autoscaling.peak_servers}</td>
                    <td>Elastic Adjustment</td>
                </tr>
            </tbody>
        </table>

        <h2>Actionable System Recommendations</h2>
        {rec_items_html}

        <h2>Configuration Parameters</h2>
        <table>
            <tbody>
                <tr><td>Traffic Pattern</td><td>{config.traffic_pattern}</td><td>Initial / Peak Users</td><td>{config.initial_users:,} / {config.peak_users:,}</td></tr>
                <tr><td>Requests / User / Min</td><td>{config.requests_per_user_min}</td><td>Duration Steps</td><td>{config.duration_steps} ({config.duration_steps * config.step_unit_minutes} min)</td></tr>
                <tr><td>Fixed Server Count</td><td>{config.fixed_servers} nodes</td><td>Server Capacity</td><td>{config.server_capacity_rpm:,.0f} req/min</td></tr>
                <tr><td>AS Min / Max Servers</td><td>{config.as_min_servers} / {config.as_max_servers} nodes</td><td>Scale-Out / In Triggers</td><td>> {config.cpu_scale_out_threshold}% / < {config.cpu_scale_in_threshold}%</td></tr>
                <tr><td>Cooldowns (Out / In)</td><td>{config.scale_out_cooldown} / {config.scale_in_cooldown} steps</td><td>Startup Delay</td><td>{config.startup_delay} steps</td></tr>
                <tr><td>Hourly Server Cost</td><td>${config.cost_per_server_hour:.2f}</td><td>SLA Response Target</td><td>{config.sla_target_response_time_ms} ms</td></tr>
            </tbody>
        </table>

        <div class="footer">
            CloudScale Simulation Engine &bull; Academic Case Study &bull; Deterministic Seed: {config.random_seed}
        </div>
    </div>
</body>
</html>
"""
    return html
