"""Automated tests for configuration validation in CloudScale."""

import pytest
from core.validation import SimulationConfig, validate_config, load_default_config


def test_default_config_is_valid():
    """Verify that default configuration passes all validation checks."""
    cfg = load_default_config()
    result = validate_config(cfg)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_invalid_server_boundaries():
    """Verify minimum and maximum server count rules."""
    # Min servers < 1
    cfg = SimulationConfig(as_min_servers=0)
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any("Auto-scaling minimum server count must be at least 1" in e for e in result.errors)

    # Max servers < min servers
    cfg2 = SimulationConfig(as_min_servers=5, as_max_servers=3)
    result2 = validate_config(cfg2)
    assert result2.is_valid is False
    assert any("cannot be less than minimum servers" in e for e in result2.errors)

    # Initial servers out of bounds
    cfg3 = SimulationConfig(as_min_servers=3, as_max_servers=10, as_initial_servers=1)
    result3 = validate_config(cfg3)
    assert result3.is_valid is False
    assert any("cannot be less than minimum servers" in e for e in result3.errors)

    cfg4 = SimulationConfig(as_min_servers=3, as_max_servers=10, as_initial_servers=15)
    result4 = validate_config(cfg4)
    assert result4.is_valid is False
    assert any("cannot exceed maximum servers" in e for e in result4.errors)


def test_threshold_ordering_validation():
    """Scale-in threshold must be strictly lower than scale-out threshold."""
    # Scale in higher than scale out
    cfg = SimulationConfig(cpu_scale_out_threshold=60.0, cpu_scale_in_threshold=70.0)
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any("must be strictly lower than scale-out threshold" in e for e in result.errors)

    # Thresholds equal
    cfg2 = SimulationConfig(cpu_scale_out_threshold=60.0, cpu_scale_in_threshold=60.0)
    result2 = validate_config(cfg2)
    assert result2.is_valid is False
    assert any("must be strictly lower than scale-out threshold" in e for e in result2.errors)

    # Out of 0-100 range
    cfg3 = SimulationConfig(cpu_scale_out_threshold=105.0)
    result3 = validate_config(cfg3)
    assert result3.is_valid is False
    assert any("between 0% (exclusive) and 100% (inclusive)" in e for e in result3.errors)


def test_negative_values_rejected():
    """Ensure negative traffic, durations, and costs are rejected."""
    cfg = SimulationConfig(initial_users=-10)
    assert validate_config(cfg).is_valid is False

    cfg2 = SimulationConfig(duration_steps=2)  # < 5 steps
    assert validate_config(cfg2).is_valid is False

    cfg3 = SimulationConfig(cost_per_server_hour=-0.05)
    assert validate_config(cfg3).is_valid is False

    cfg4 = SimulationConfig(fixed_servers=0)
    assert validate_config(cfg4).is_valid is False


def test_dict_conversion_and_casting():
    """Verify dictionary parsing and type safety."""
    raw = {
        "initial_users": "250",
        "peak_users": "1500",
        "requests_per_user_min": "4.5",
        "duration_steps": "30",
        "fixed_servers": "5",
        "as_min_servers": "2",
        "as_max_servers": "10",
        "as_initial_servers": "3",
    }
    cfg = SimulationConfig.from_dict(raw)
    assert cfg.initial_users == 250
    assert cfg.peak_users == 1500
    assert cfg.requests_per_user_min == 4.5
    assert cfg.duration_steps == 30
    assert cfg.fixed_servers == 5
