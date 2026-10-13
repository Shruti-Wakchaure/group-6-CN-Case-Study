"""Performance, availability, SLA metrics, and recommendation engine for CloudScale."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import pandas as pd

from core.validation import SimulationConfig
from core.cost_calculator import compare_infrastructure_costs, CostComparisonResult


@dataclass
class SystemPerformanceMetrics:
    """Comprehensive performance and availability metrics for an infrastructure system."""
    system_name: str
    total_incoming_requests: float
    total_processed_requests: float
    total_dropped_requests: float
    request_success_rate_pct: float
    avg_cpu_utilization_pct: float
    peak_cpu_utilization_pct: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    sla_compliance_rate_pct: float
    overload_duration_steps: int
    overload_duration_minutes: float
    scaling_events_count: int
    scale_out_count: int
    scale_in_count: int
    peak_servers: int
    avg_servers: float
    total_server_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationComparison:
    """Full comparative evaluation of Fixed vs Auto-Scaling models."""
    fixed_metrics: SystemPerformanceMetrics
    as_metrics: SystemPerformanceMetrics
    cost_comparison: CostComparisonResult
    recommendations: List[Dict[str, str]]
    summary_highlights: Dict[str, Any]


def compute_performance_metrics(
    df: pd.DataFrame,
    system_name: str,
    config: SimulationConfig
) -> SystemPerformanceMetrics:
    """Compute detailed performance, availability, and SLA metrics from time-series DataFrame."""
    if df.empty:
        return SystemPerformanceMetrics(
            system_name=system_name,
            total_incoming_requests=0.0,
            total_processed_requests=0.0,
            total_dropped_requests=0.0,
            request_success_rate_pct=100.0,
            avg_cpu_utilization_pct=0.0,
            peak_cpu_utilization_pct=0.0,
            avg_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            sla_compliance_rate_pct=100.0,
            overload_duration_steps=0,
            overload_duration_minutes=0.0,
            scaling_events_count=0,
            scale_out_count=0,
            scale_in_count=0,
            peak_servers=0,
            avg_servers=0.0,
            total_server_hours=0.0,
        )

    incoming = float(df["incoming_requests"].sum())
    processed = float(df["processed_requests"].sum())
    dropped = float(df["dropped_requests"].sum())

    success_rate = (processed / incoming * 100.0) if incoming > 0 else 100.0
    avg_cpu = float(df["cpu_utilization_pct"].mean())
    peak_cpu = float(df["cpu_utilization_pct"].max())

    avg_rt = float(df["avg_response_time_ms"].mean())
    p95_rt = float(df["p95_response_time_ms"].quantile(0.95))

    sla_compliant_steps = int((df["avg_response_time_ms"] <= config.sla_target_response_time_ms).sum())
    sla_compliance_pct = (sla_compliant_steps / len(df) * 100.0) if len(df) > 0 else 100.0

    overload_steps = int(df["is_overloaded"].sum())
    overload_minutes = overload_steps * config.step_unit_minutes

    scale_out_count = int(df["scaling_action"].str.startswith("SCALE_OUT (+").sum())
    scale_in_count = int(df["scaling_action"].str.startswith("SCALE_IN (-").sum())
    total_scaling = scale_out_count + scale_in_count

    peak_servers = int(df["active_servers"].max())
    avg_servers = float(df["active_servers"].mean())
    step_hours = config.step_unit_minutes / 60.0
    total_server_hours = float((df["total_servers"] * step_hours).sum())

    return SystemPerformanceMetrics(
        system_name=system_name,
        total_incoming_requests=round(incoming, 1),
        total_processed_requests=round(processed, 1),
        total_dropped_requests=round(dropped, 1),
        request_success_rate_pct=round(success_rate, 2),
        avg_cpu_utilization_pct=round(avg_cpu, 2),
        peak_cpu_utilization_pct=round(peak_cpu, 2),
        avg_response_time_ms=round(avg_rt, 2),
        p95_response_time_ms=round(p95_rt, 2),
        sla_compliance_rate_pct=round(sla_compliance_pct, 2),
        overload_duration_steps=overload_steps,
        overload_duration_minutes=round(overload_minutes, 1),
        scaling_events_count=total_scaling,
        scale_out_count=scale_out_count,
        scale_in_count=scale_in_count,
        peak_servers=peak_servers,
        avg_servers=round(avg_servers, 2),
        total_server_hours=round(total_server_hours, 2),
    )


def generate_automated_recommendations(
    fixed_perf: SystemPerformanceMetrics,
    as_perf: SystemPerformanceMetrics,
    cost_comp: CostComparisonResult,
    as_df: pd.DataFrame,
    config: SimulationConfig
) -> List[Dict[str, str]]:
    """
    Generate evidence-based architectural recommendations derived directly from calculated simulation values.
    """
    recommendations: List[Dict[str, str]] = []

    # 1. Capacity & Overload Analysis
    if as_perf.total_dropped_requests > 0:
        max_reached_steps = int((as_df["scaling_action"] == "MAX_CAPACITY_REACHED").sum())
        startup_delays_active = int((as_df["provisioning_servers"] > 0).sum())

        if max_reached_steps > 0:
            recommendations.append({
                "category": "Capacity Limit",
                "severity": "CRITICAL",
                "finding": f"Auto-scaling reached its configured ceiling of {config.as_max_servers} servers across {max_reached_steps} steps, dropping {as_perf.total_dropped_requests:,.0f} requests.",
                "recommendation": f"Increase 'as_max_servers' beyond {config.as_max_servers} or implement rate limiting/queueing to absorb peak surges without dropping connections."
            })
        elif config.startup_delay > 0 and startup_delays_active > 0:
            recommendations.append({
                "category": "Startup Latency Lag",
                "severity": "WARNING",
                "finding": f"Requests dropped ({as_perf.total_dropped_requests:,.0f}) primarily during server startup warmup delays ({config.startup_delay} steps).",
                "recommendation": "Configure predictive scaling or pre-warmed instance pools to initiate scaling ahead of anticipated promotional spikes, or lower 'cpu_scale_out_threshold' to scale out sooner."
            })
        else:
            recommendations.append({
                "category": "Overload Mitigation",
                "severity": "WARNING",
                "finding": f"Unmet demand of {as_perf.total_dropped_requests:,.0f} requests was recorded.",
                "recommendation": "Adjust scale-out step size or inspect server request-handling throughput assumptions."
            })
    else:
        recommendations.append({
            "category": "Reliability & Availability",
            "severity": "INFO",
            "finding": f"Auto-scaling achieved 100.0% request success rate with zero dropped requests across {as_perf.total_incoming_requests:,.0f} total incoming requests.",
            "recommendation": "Maintain current capacity headroom; the auto-scaling configuration successfully sustained traffic demands."
        })

    # 2. Cost Analysis
    if cost_comp.savings_percent is not None:
        if cost_comp.savings_percent > 0:
            recommendations.append({
                "category": "Cost Efficiency",
                "severity": "POSITIVE",
                "finding": f"Auto-scaling saved {cost_comp.savings_percent_display} (${cost_comp.absolute_savings_usd:.2f}) compared to fixed infrastructure.",
                "recommendation": "The dynamic elasticity model provides significant operational savings by scaling down servers during low-traffic intervals."
            })
        elif cost_comp.savings_percent < 0:
            recommendations.append({
                "category": "Cost Trade-off",
                "severity": "WARNING",
                "finding": f"Auto-scaling cost was {abs(cost_comp.savings_percent):.2f}% higher than the fixed baseline.",
                "recommendation": f"The fixed baseline was underprovisioned ({config.fixed_servers} servers, dropping {fixed_perf.total_dropped_requests:,.0f} requests). Auto-scaling scaled up to {as_perf.peak_servers} servers to maintain availability. Cost is higher because actual required work was delivered."
            })
        else:
            recommendations.append({
                "category": "Cost Parity",
                "severity": "INFO",
                "finding": "Both configurations incurred equal infrastructure expenditure.",
                "recommendation": "Assess whether traffic variance warrants dynamic scaling overhead or if fixed provisioning is adequate."
            })

    # 3. Utilization & Overprovisioning
    if as_perf.avg_cpu_utilization_pct < 35.0:
        recommendations.append({
            "category": "Resource Utilization",
            "severity": "WARNING",
            "finding": f"Average auto-scaling CPU utilization was relatively low ({as_perf.avg_cpu_utilization_pct:.1f}%).",
            "recommendation": f"Consider lowering minimum servers from {config.as_min_servers} to 1 during off-peak periods, or rightsizing individual server capacity."
        })
    elif as_perf.avg_cpu_utilization_pct > 75.0:
        recommendations.append({
            "category": "Workload Stress",
            "severity": "WARNING",
            "finding": f"Average CPU utilization remained high ({as_perf.avg_cpu_utilization_pct:.1f}%), leaving limited buffer for sudden spikes.",
            "recommendation": "Consider lowering the scale-out threshold to 60-65% or increasing scale-out step size to maintain healthy headroom."
        })

    # 4. Latency & SLA
    if as_perf.sla_compliance_rate_pct < 95.0:
        recommendations.append({
            "category": "Service Level Agreement (SLA)",
            "severity": "CRITICAL",
            "finding": f"SLA compliance fell to {as_perf.sla_compliance_rate_pct:.1f}% below the {config.sla_target_response_time_ms}ms target.",
            "recommendation": "Target latency degraded under load. Decrease scale-out cooldown and increase step size to rapidly alleviate server queue buildup."
        })
    else:
        recommendations.append({
            "category": "Latency Performance",
            "severity": "INFO",
            "finding": f"SLA compliance target of {config.sla_target_response_time_ms}ms was met for {as_perf.sla_compliance_rate_pct:.1f}% of simulation steps (Average: {as_perf.avg_response_time_ms:.1f}ms).",
            "recommendation": "Response times remained well within acceptable customer experience bounds."
        })

    # 5. Cooldown & Flapping
    cooldown_blocks = int(as_df["scaling_action"].str.contains("COOLDOWN").sum())
    dampened_events = int(as_df["scaling_action"].str.contains("DAMPENED").sum())
    if cooldown_blocks > 5:
        recommendations.append({
            "category": "Cooldown Tuning",
            "severity": "INFO",
            "finding": f"Scaling actions were held back by cooldown timers in {cooldown_blocks} steps.",
            "recommendation": "Ensure cooldown values allow adequate reaction time without creating persistent backlogs during rapid traffic shifts."
        })
    if dampened_events > 0:
        recommendations.append({
            "category": "Anti-Flapping Protection",
            "severity": "INFO",
            "finding": f"Anti-flapping logic prevented premature scale-in on {dampened_events} occasions, averting server thrashing.",
            "recommendation": "The safety hysteresis between scale-in and scale-out thresholds successfully stabilized server cluster count."
        })

    return recommendations


def evaluate_simulation_results(
    fixed_df: pd.DataFrame,
    as_df: pd.DataFrame,
    config: SimulationConfig
) -> SimulationComparison:
    """Run full comparative analysis, metrics generation, cost analytics, and recommendations."""
    fixed_perf = compute_performance_metrics(fixed_df, "Fixed Infrastructure", config)
    as_perf = compute_performance_metrics(as_df, "Auto-Scaling Infrastructure", config)
    cost_comp = compare_infrastructure_costs(fixed_df, as_df, config)
    recommendations = generate_automated_recommendations(fixed_perf, as_perf, cost_comp, as_df, config)

    highlights = {
        "cost_savings_pct": cost_comp.savings_percent,
        "cost_savings_display": cost_comp.savings_percent_display,
        "absolute_savings_usd": cost_comp.absolute_savings_usd,
        "fixed_cost_usd": cost_comp.fixed.total_cost_usd,
        "as_cost_usd": cost_comp.autoscaling.total_cost_usd,
        "fixed_success_rate": fixed_perf.request_success_rate_pct,
        "as_success_rate": as_perf.request_success_rate_pct,
        "fixed_dropped_requests": fixed_perf.total_dropped_requests,
        "as_dropped_requests": as_perf.total_dropped_requests,
        "as_scaling_events": as_perf.scaling_events_count,
        "fixed_overload_steps": fixed_perf.overload_duration_steps,
        "as_overload_steps": as_perf.overload_duration_steps,
    }

    return SimulationComparison(
        fixed_metrics=fixed_perf,
        as_metrics=as_perf,
        cost_comparison=cost_comp,
        recommendations=recommendations,
        summary_highlights=highlights
    )
