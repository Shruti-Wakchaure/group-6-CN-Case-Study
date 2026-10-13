"""Predefined simulation scenarios and cross-scenario comparison engine for CloudScale."""

from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd

from core.validation import SimulationConfig
from core.simulator import generate_traffic_series
from core.autoscaling import run_fixed_simulation, run_autoscaling_simulation
from core.metrics import evaluate_simulation_results, SimulationComparison


@dataclass
class ScenarioPreset:
    """Predefined scenario definition with narrative context and parameters."""
    id: str
    name: str
    description: str
    expected_outcome: str
    tradeoffs_and_lessons: str
    recommended_tuning: str
    config: SimulationConfig


PREDEFINED_SCENARIOS: Dict[str, ScenarioPreset] = {
    "normal_day": ScenarioPreset(
        id="normal_day",
        name="1. Normal Business Day",
        description="Standard diurnal business cycle with moderate morning and evening traffic oscillations.",
        expected_outcome="Auto-scaling dynamically tracks diurnal demand, maintaining 100% request success while delivering significant cost savings (~30-45%) compared to an overprovisioned fixed baseline.",
        tradeoffs_and_lessons="Demonstrates ideal auto-scaling behavior under predictable, smoothly oscillating demand.",
        recommended_tuning="Maintain generous cooldowns to avoid unnecessary micro-scaling during transient ripples.",
        config=SimulationConfig(
            initial_users=300,
            peak_users=1400,
            requests_per_user_min=5.0,
            duration_steps=60,
            step_unit_minutes=1.0,
            traffic_pattern="Periodic / Daily",
            fixed_servers=8,
            as_initial_servers=2,
            as_min_servers=2,
            as_max_servers=10,
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=70.0,
            cpu_scale_in_threshold=30.0,
            scale_out_cooldown=3,
            scale_in_cooldown=4,
            startup_delay=1,
            scale_out_step_size=2,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=42
        )
    ),
    "gradual_growth": ScenarioPreset(
        id="gradual_growth",
        name="2. Gradual Traffic Growth",
        description="Consistent upward traffic growth over time, testing incremental step-by-step capacity expansion.",
        expected_outcome="Auto-scaling smoothly provisions additional servers step-by-step as demand increases, avoiding latency spikes and keeping CPU within healthy bounds.",
        tradeoffs_and_lessons="No requests dropped; costs scale proportionally with actual business growth rather than paying peak cost upfront.",
        recommended_tuning="Tuning scale_out_step_size to 2 servers ensures timely capacity addition before reaching 85% CPU.",
        config=SimulationConfig(
            initial_users=200,
            peak_users=2200,
            requests_per_user_min=6.0,
            duration_steps=60,
            step_unit_minutes=1.0,
            traffic_pattern="Gradual Growth",
            fixed_servers=9,
            as_initial_servers=2,
            as_min_servers=2,
            as_max_servers=16,
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=70.0,
            cpu_scale_in_threshold=30.0,
            scale_out_cooldown=3,
            scale_in_cooldown=3,
            startup_delay=1,
            scale_out_step_size=2,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=101
        )
    ),
    "festival_sale": ScenarioPreset(
        id="festival_sale",
        name="3. Festival Sale Traffic Spike",
        description="E-commerce promotional event with sharp flash-sale surge (6x jump in demand), plateau, and cool-down.",
        expected_outcome="Fixed infrastructure is completely overwhelmed (severe request drops, high latency). Auto-scaling rapidly adds servers, keeping request success high and fulfilling customer purchases.",
        tradeoffs_and_lessons="Auto-scaling cost may be comparable or higher than an under-provisioned fixed system, but saves business revenue by actually fulfilling transactions instead of dropping customer orders.",
        recommended_tuning="Ensure max_servers is high enough to accommodate peak promotional volume and scale_out_step_size is at least 3.",
        config=SimulationConfig(
            initial_users=400,
            peak_users=3200,
            requests_per_user_min=6.0,
            duration_steps=60,
            step_unit_minutes=1.0,
            traffic_pattern="Festival Sale",
            fixed_servers=8,
            as_initial_servers=3,
            as_min_servers=2,
            as_max_servers=22,
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=70.0,
            cpu_scale_in_threshold=30.0,
            scale_out_cooldown=2,
            scale_in_cooldown=4,
            startup_delay=2,
            scale_out_step_size=3,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=777
        )
    ),
    "sudden_surge": ScenarioPreset(
        id="sudden_surge",
        name="4. Sudden Traffic Surge",
        description="Instantaneous traffic leap with startup delay enabled, demonstrating startup lag and latency transient behavior.",
        expected_outcome="During server startup delay (warmup period), temporary queueing and elevated response times occur before newly provisioned servers become active and normalize throughput.",
        tradeoffs_and_lessons="Highlights the physical reality of cloud VM provisioning delays (e.g. EC2 launch time). Auto-scaling cannot react instantly without predictive or pre-warmed buffers.",
        recommended_tuning="Use pre-warming (provisioned concurrency), reduce VM image startup overhead, or lower scale-out trigger to 60%.",
        config=SimulationConfig(
            initial_users=300,
            peak_users=2400,
            requests_per_user_min=6.0,
            duration_steps=50,
            step_unit_minutes=1.0,
            traffic_pattern="Sudden Spike",
            fixed_servers=10,
            as_initial_servers=2,
            as_min_servers=2,
            as_max_servers=18,
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=70.0,
            cpu_scale_in_threshold=30.0,
            scale_out_cooldown=2,
            scale_in_cooldown=3,
            startup_delay=3,
            scale_out_step_size=3,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=88
        )
    ),
    "low_traffic": ScenarioPreset(
        id="low_traffic",
        name="5. Low Traffic & Cost Optimization",
        description="Off-peak night-time traffic scenario showcasing maximum financial savings from aggressive scale-in.",
        expected_outcome="Auto-scaling contracts down to minimum servers (2 nodes), cutting infrastructure spending by over 60-70% compared to a constant fixed fleet running idle.",
        tradeoffs_and_lessons="Proves the fundamental economic value of cloud elasticity during slow hours without sacrificing response times.",
        recommended_tuning="Verify that minimum server count still maintains N+1 redundancy across availability zones.",
        config=SimulationConfig(
            initial_users=150,
            peak_users=250,
            requests_per_user_min=4.0,
            duration_steps=60,
            step_unit_minutes=1.0,
            traffic_pattern="Constant",
            fixed_servers=10,
            as_initial_servers=3,
            as_min_servers=2,
            as_max_servers=10,
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=75.0,
            cpu_scale_in_threshold=35.0,
            scale_out_cooldown=3,
            scale_in_cooldown=3,
            startup_delay=1,
            scale_out_step_size=1,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=12
        )
    ),
    "extreme_overload": ScenarioPreset(
        id="extreme_overload",
        name="6. Extreme Overload (Capacity Capped)",
        description="Traffic demands that purposely exceed the configured maximum server count, testing ceiling limits.",
        expected_outcome="Both fixed and auto-scaling systems experience overload and request drops once max_servers is saturated. Explicit warnings and unmet demand metrics are clearly quantified.",
        tradeoffs_and_lessons="Illustrates that auto-scaling cannot protect service quality if arbitrary organizational quota limits or budget ceilings cap server count below true demand.",
        recommended_tuning="Review cloud account vCPU service quotas and implement graceful degradation or waiting-room queues.",
        config=SimulationConfig(
            initial_users=600,
            peak_users=4500,
            requests_per_user_min=6.0,
            duration_steps=60,
            step_unit_minutes=1.0,
            traffic_pattern="Festival Sale",
            fixed_servers=10,
            as_initial_servers=3,
            as_min_servers=2,
            as_max_servers=14,  # Artificially capped below peak need (needs ~27 servers)
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=70.0,
            cpu_scale_in_threshold=30.0,
            scale_out_cooldown=2,
            scale_in_cooldown=3,
            startup_delay=1,
            scale_out_step_size=2,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=999
        )
    ),
    "stress_test": ScenarioPreset(
        id="stress_test",
        name="7. Maximum Capacity Stress Test",
        description="Highly fluctuating randomized traffic testing stability, rapid scale-out/scale-in, and cooldown robustness.",
        expected_outcome="Tests rapid alternating traffic shifts. Verifies that cooldown timers and anti-flapping logic prevent server oscillation/thrashing.",
        tradeoffs_and_lessons="Demonstrates how hysteresis and cooldown prevent excessive billing churn and VM instability.",
        recommended_tuning="Set scale-in cooldown at least 1.5x higher than scale-out cooldown to create a stabilizing buffer.",
        config=SimulationConfig(
            initial_users=500,
            peak_users=2800,
            requests_per_user_min=6.0,
            duration_steps=60,
            step_unit_minutes=1.0,
            traffic_pattern="Randomized",
            fixed_servers=12,
            as_initial_servers=4,
            as_min_servers=3,
            as_max_servers=20,
            server_capacity_rpm=1000.0,
            cpu_scale_out_threshold=70.0,
            cpu_scale_in_threshold=30.0,
            scale_out_cooldown=2,
            scale_in_cooldown=4,
            startup_delay=1,
            scale_out_step_size=3,
            scale_in_step_size=1,
            cost_per_server_hour=0.10,
            sla_target_response_time_ms=200.0,
            random_seed=555
        )
    )
}


def run_all_scenarios_comparison() -> pd.DataFrame:
    """
    Execute all 7 predefined scenarios through both Fixed and Auto-Scaling models.
    Produces a standardized comparison DataFrame for academic analysis and export.
    """
    rows: List[Dict[str, Any]] = []

    for preset_id, preset in PREDEFINED_SCENARIOS.items():
        cfg = preset.config
        traffic = generate_traffic_series(cfg)
        fixed_df = run_fixed_simulation(cfg, traffic)
        as_df = run_autoscaling_simulation(cfg, traffic)
        comp = evaluate_simulation_results(fixed_df, as_df, cfg)

        savings_str = (
            f"{comp.cost_comparison.savings_percent:+.1f}%"
            if comp.cost_comparison.savings_percent is not None
            else "N/A"
        )

        rows.append({
            "Scenario Preset": preset.name,
            "Pattern": cfg.traffic_pattern,
            "Total Requests": f"{comp.fixed_metrics.total_incoming_requests:,.0f}",
            "Fixed Servers": cfg.fixed_servers,
            "Fixed Cost ($)": f"${comp.cost_comparison.fixed.total_cost_usd:.2f}",
            "Fixed Success Rate (%)": f"{comp.fixed_metrics.request_success_rate_pct:.1f}%",
            "Fixed Overload (steps)": comp.fixed_metrics.overload_duration_steps,
            "AS Min-Max Servers": f"{cfg.as_min_servers} - {cfg.as_max_servers}",
            "AS Peak Servers": comp.as_metrics.peak_servers,
            "AS Cost ($)": f"${comp.cost_comparison.autoscaling.total_cost_usd:.2f}",
            "AS Success Rate (%)": f"{comp.as_metrics.request_success_rate_pct:.1f}%",
            "AS Overload (steps)": comp.as_metrics.overload_duration_steps,
            "Cost Savings (%)": savings_str,
            "Net Savings ($)": f"${comp.cost_comparison.absolute_savings_usd:.2f}",
            "Scaling Events": comp.as_metrics.scaling_events_count
        })

    return pd.DataFrame(rows)
