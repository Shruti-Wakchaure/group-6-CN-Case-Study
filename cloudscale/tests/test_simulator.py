"""Integration and simulator engine tests for CloudScale."""

import pytest
import pandas as pd
from core.validation import SimulationConfig
from core.simulator import generate_traffic_series, estimate_latency_ms
from core.autoscaling import run_fixed_simulation, run_autoscaling_simulation
from core.metrics import evaluate_simulation_results
from core.reports import (
    generate_merged_simulation_csv,
    generate_markdown_report,
    generate_html_report
)


def test_deterministic_random_seed():
    """Verify that identical random seeds produce 100% identical traffic series."""
    cfg1 = SimulationConfig(traffic_pattern="Randomized", random_seed=42, duration_steps=50)
    cfg2 = SimulationConfig(traffic_pattern="Randomized", random_seed=42, duration_steps=50)
    cfg3 = SimulationConfig(traffic_pattern="Randomized", random_seed=999, duration_steps=50)

    t1 = generate_traffic_series(cfg1)
    t2 = generate_traffic_series(cfg2)
    t3 = generate_traffic_series(cfg3)

    assert t1 == t2
    assert t1 != t3


def test_zero_traffic_handling():
    """Verify system operates cleanly under zero traffic without NaN or ZeroDivisionError."""
    cfg = SimulationConfig(initial_users=0, peak_users=0, duration_steps=10)
    traffic = generate_traffic_series(cfg)
    assert traffic == [0] * 10

    fixed_df = run_fixed_simulation(cfg, traffic)
    as_df = run_autoscaling_simulation(cfg, traffic)

    assert fixed_df["dropped_requests"].sum() == 0.0
    assert as_df["dropped_requests"].sum() == 0.0
    assert (fixed_df["cpu_utilization_pct"] == 0.0).all()

    comparison = evaluate_simulation_results(fixed_df, as_df, cfg)
    assert comparison.fixed_metrics.request_success_rate_pct == 100.0
    assert comparison.as_metrics.request_success_rate_pct == 100.0


def test_latency_model_behavior():
    """Verify queuing latency calculation across idle, normal, and overloaded states."""
    sla_target = 200.0
    cap = 1000.0

    # Idle (0 requests)
    rt_idle, _ = estimate_latency_ms(0.0, cap, sla_target)
    assert rt_idle == 35.0

    # Normal load (500 requests / 1000 cap = 50% util)
    rt_normal, _ = estimate_latency_ms(500.0, cap, sla_target)
    assert 35.0 < rt_normal < 150.0

    # Overloaded (2000 requests / 1000 cap = 200% util)
    rt_overload, p95_overload = estimate_latency_ms(2000.0, cap, sla_target)
    assert rt_overload > sla_target
    assert p95_overload > rt_overload


def test_full_scenario_integration_and_exports():
    """
    End-to-end integration test:
    Run complete simulation scenario, compute metrics, compare costs, and generate all export formats.
    """
    cfg = SimulationConfig(
        initial_users=300,
        peak_users=1800,
        requests_per_user_min=5.0,
        duration_steps=30,
        traffic_pattern="Festival Sale",
        fixed_servers=10,
        as_initial_servers=3,
        as_min_servers=2,
        as_max_servers=15,
        server_capacity_rpm=1000.0,
        random_seed=123
    )

    traffic = generate_traffic_series(cfg)
    fixed_df = run_fixed_simulation(cfg, traffic)
    as_df = run_autoscaling_simulation(cfg, traffic)

    assert len(fixed_df) == 30
    assert len(as_df) == 30

    comparison = evaluate_simulation_results(fixed_df, as_df, cfg)

    # Cost comparison checks
    assert comparison.cost_comparison.fixed.total_cost_usd > 0
    assert comparison.cost_comparison.autoscaling.total_cost_usd > 0
    assert comparison.cost_comparison.savings_percent is not None

    # Recommendations generated
    assert len(comparison.recommendations) > 0

    # Export generation
    merged_csv = generate_merged_simulation_csv(fixed_df, as_df)
    assert "Time_Step" in merged_csv
    assert "Fixed_Cumulative_Cost_USD" in merged_csv
    assert "AS_Cumulative_Cost_USD" in merged_csv

    md_report = generate_markdown_report(cfg, comparison, "Integration Test")
    assert "# CloudScale: Cloud Network Infrastructure Case Study" in md_report
    assert "Executive Summary" in md_report

    html_report = generate_html_report(cfg, comparison, "Integration Test")
    assert "<!DOCTYPE html>" in html_report
    assert "CloudScale" in html_report
