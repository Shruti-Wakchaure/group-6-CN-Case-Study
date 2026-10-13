"""Automated tests for auto-scaling and fixed infrastructure logic in CloudScale."""

import pytest
import pandas as pd
from core.validation import SimulationConfig
from core.autoscaling import run_fixed_simulation, run_autoscaling_simulation


def test_fixed_infrastructure_invariance():
    """Verify that fixed infrastructure maintains constant server count throughout simulation."""
    cfg = SimulationConfig(fixed_servers=7, duration_steps=30, server_capacity_rpm=1000.0)
    traffic = [100 + i * 20 for i in range(30)]

    df = run_fixed_simulation(cfg, traffic)
    assert len(df) == 30
    assert (df["active_servers"] == 7).all()
    assert (df["total_servers"] == 7).all()
    assert (df["capacity_rpm"] == 7000.0).all()


def test_autoscaling_scale_out_trigger():
    """Verify that auto-scaling expands capacity when CPU exceeds scale-out threshold."""
    # Capacity per server = 1000 RPM. Initial servers = 2 (Capacity = 2000 RPM).
    # 500 users * 6 = 3000 requests/min -> Raw utilization = 150% (triggers scale-out).
    cfg = SimulationConfig(
        as_initial_servers=2,
        as_min_servers=2,
        as_max_servers=8,
        server_capacity_rpm=1000.0,
        requests_per_user_min=6.0,
        cpu_scale_out_threshold=70.0,
        scale_out_cooldown=1,
        startup_delay=0,
        scale_out_step_size=2
    )
    # Step 0: low traffic (100 users = 600 req -> 30% util)
    # Step 1: surge (500 users = 3000 req -> > 70% util)
    # Step 2: high traffic continues
    traffic = [100, 500, 500, 500]

    df = run_autoscaling_simulation(cfg, traffic)
    assert df["active_servers"].iloc[0] == 2
    # At step 1, scale-out was triggered with 0 startup delay
    assert df["active_servers"].iloc[1] == 4
    assert "SCALE_OUT" in df["scaling_action"].iloc[1]


def test_autoscaling_scale_in_trigger():
    """Verify that auto-scaling contracts capacity when CPU falls below scale-in threshold."""
    # Start with 5 servers. High traffic initially, then drops to near zero.
    cfg = SimulationConfig(
        as_initial_servers=5,
        as_min_servers=2,
        as_max_servers=10,
        server_capacity_rpm=1000.0,
        requests_per_user_min=5.0,
        cpu_scale_in_threshold=30.0,
        scale_in_cooldown=1,
        startup_delay=0,
        scale_in_step_size=1
    )
    # Step 0: 400 users (2000 req / 5000 cap = 40% util)
    # Step 1: 50 users (250 req / 5000 cap = 5% util -> triggers scale in)
    # Step 2: 50 users (250 req / 4000 cap = 6.25% util -> in cooldown)
    # Step 3: 50 users (250 req / 4000 cap = 6.25% util -> triggers scale in)
    traffic = [400, 50, 50, 50, 50]

    df = run_autoscaling_simulation(cfg, traffic)
    assert df["active_servers"].iloc[0] == 5
    assert df["active_servers"].iloc[1] == 4
    assert "SCALE_IN (-1)" in df["scaling_action"].iloc[1]


def test_min_and_max_server_limits_respected():
    """Verify that server count never breaches configured min or max limits."""
    cfg = SimulationConfig(
        as_initial_servers=2,
        as_min_servers=2,
        as_max_servers=4,
        server_capacity_rpm=500.0,
        requests_per_user_min=10.0,
        cpu_scale_out_threshold=50.0,
        cpu_scale_in_threshold=20.0,
        scale_out_cooldown=0,
        startup_delay=0,
        scale_out_step_size=3
    )
    # Extreme traffic: 2000 users = 20,000 req/min
    traffic = [2000] * 5

    df = run_autoscaling_simulation(cfg, traffic)
    # Initial is 2. Step 0 scale out (+2 to reach max 4). Cannot exceed 4.
    assert (df["total_servers"] <= 4).all()
    assert (df["active_servers"] <= 4).all()
    assert (df["active_servers"] >= 2).all()
    assert any("MAX_CAPACITY_REACHED" in str(act) for act in df["scaling_action"])


def test_cooldown_enforcement():
    """Verify that cooldown prevents consecutive scaling actions in subsequent steps."""
    cfg = SimulationConfig(
        as_initial_servers=2,
        as_min_servers=2,
        as_max_servers=10,
        server_capacity_rpm=1000.0,
        requests_per_user_min=6.0,
        cpu_scale_out_threshold=70.0,
        scale_out_cooldown=3,  # Cooldown of 3 steps
        startup_delay=0,
        scale_out_step_size=1
    )
    # Heavy traffic on all steps
    traffic = [500] * 6

    df = run_autoscaling_simulation(cfg, traffic)
    # Step 0: Scale out (+1) -> active becomes 3. last_scale_out = 0.
    # Step 1: Cooldown active (1 - 0 <= 3) -> SCALE_OUT_COOLDOWN
    # Step 2: Cooldown active (2 - 0 <= 3) -> SCALE_OUT_COOLDOWN
    # Step 3: Cooldown active (3 - 0 <= 3) -> SCALE_OUT_COOLDOWN
    # Step 4: Cooldown expired (4 - 0 > 3) -> Scale out (+1) -> active becomes 4
    assert "SCALE_OUT" in df["scaling_action"].iloc[0]
    assert df["scaling_action"].iloc[1] == "SCALE_OUT_COOLDOWN"
    assert df["scaling_action"].iloc[2] == "SCALE_OUT_COOLDOWN"
    assert df["scaling_action"].iloc[3] == "SCALE_OUT_COOLDOWN"
    assert "SCALE_OUT" in df["scaling_action"].iloc[4]


def test_startup_delay_behavior():
    """Verify that servers warming up during startup delay do not process traffic until ready."""
    cfg = SimulationConfig(
        as_initial_servers=2,
        as_min_servers=2,
        as_max_servers=10,
        server_capacity_rpm=1000.0,
        requests_per_user_min=6.0,
        cpu_scale_out_threshold=70.0,
        scale_out_cooldown=5,
        startup_delay=2,  # 2 steps warmup
        scale_out_step_size=2
    )
    # Step 0 triggers scale-out. Servers ready at step 2.
    traffic = [500, 500, 500, 500]

    df = run_autoscaling_simulation(cfg, traffic)
    # Step 0: active = 2, total = 4 (2 provisioning)
    assert df["active_servers"].iloc[0] == 2
    assert df["provisioning_servers"].iloc[0] == 2
    assert df["total_servers"].iloc[0] == 4

    # Step 1: still in startup delay
    assert df["active_servers"].iloc[1] == 2
    assert df["provisioning_servers"].iloc[1] == 2

    # Step 2: warmup complete -> active becomes 4
    assert df["active_servers"].iloc[2] == 4
    assert df["provisioning_servers"].iloc[2] == 0
