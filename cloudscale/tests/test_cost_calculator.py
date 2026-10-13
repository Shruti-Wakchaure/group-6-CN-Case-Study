"""Automated tests for cost calculation and financial metrics in CloudScale."""

import pytest
import pandas as pd
from core.validation import SimulationConfig
from core.cost_calculator import (
    calculate_cost_savings_pct,
    compute_system_cost_metrics,
    compare_infrastructure_costs
)


def test_calculate_cost_savings_pct_standard():
    """Verify standard positive savings percentage calculation."""
    fixed = 100.0
    as_cost = 60.0
    # ((100 - 60) / 100) * 100 = 40.0%
    assert calculate_cost_savings_pct(fixed, as_cost) == 40.0


def test_calculate_cost_savings_pct_zero_baseline():
    """Verify zero baseline fixed cost returns None safely without division by zero."""
    assert calculate_cost_savings_pct(0.0, 50.0) is None
    assert calculate_cost_savings_pct(-10.0, 50.0) is None


def test_calculate_cost_savings_pct_negative_savings():
    """Verify negative savings are returned truthfully when auto-scaling costs more."""
    fixed = 50.0
    as_cost = 75.0
    # ((50 - 75) / 50) * 100 = -50.0%
    assert calculate_cost_savings_pct(fixed, as_cost) == -50.0


def test_cost_accrual_math():
    """Verify server-hours and cost calculation formulas."""
    cfg = SimulationConfig(
        step_unit_minutes=1.0,
        cost_per_server_hour=0.12
    )

    # 60 time steps of 10 servers = 600 server-minutes = 10 server-hours
    # Cost = 10 * 0.12 = $1.20
    df = pd.DataFrame({
        "step": list(range(60)),
        "total_servers": [10] * 60,
        "active_servers": [10] * 60,
        "cumulative_cost_usd": [round((i + 1) * (1.0 / 60.0) * 10 * 0.12, 4) for i in range(60)],
        "incoming_requests": [1000.0] * 60,
        "processed_requests": [1000.0] * 60,
    })

    metrics = compute_system_cost_metrics(df, cfg)
    assert abs(metrics.total_server_hours - 10.0) < 1e-4
    assert abs(metrics.total_cost_usd - 1.20) < 1e-2

    # Total requests = 60,000
    # Cost per 1k = 1.20 / 60 = 0.02
    assert abs(metrics.cost_per_1k_incoming_requests - 0.02) < 1e-3
    assert abs(metrics.cost_per_1k_processed_requests - 0.02) < 1e-3


def test_empty_dataframe_cost_handling():
    """Verify empty dataframe returns zero metrics without exceptions."""
    cfg = SimulationConfig()
    metrics = compute_system_cost_metrics(pd.DataFrame(), cfg)
    assert metrics.total_cost_usd == 0.0
    assert metrics.total_server_hours == 0.0
    assert metrics.cost_per_1k_incoming_requests == 0.0
