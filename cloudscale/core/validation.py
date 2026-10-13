"""Validation module for CloudScale simulation configurations."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import json
from pathlib import Path


VALID_TRAFFIC_PATTERNS = [
    "Constant",
    "Gradual Growth",
    "Sudden Spike",
    "Periodic / Daily",
    "Festival Sale",
    "Randomized",
]


@dataclass
class SimulationConfig:
    """Configuration parameters for the CloudScale simulation."""
    initial_users: int = 500
    peak_users: int = 3000
    requests_per_user_min: float = 6.0
    duration_steps: int = 60
    step_unit_minutes: float = 1.0
    traffic_pattern: str = "Festival Sale"
    fixed_servers: int = 10
    as_initial_servers: int = 3
    as_min_servers: int = 2
    as_max_servers: int = 15
    server_capacity_rpm: float = 1000.0
    cpu_scale_out_threshold: float = 70.0
    cpu_scale_in_threshold: float = 30.0
    scale_out_cooldown: int = 3
    scale_in_cooldown: int = 3
    startup_delay: int = 2
    scale_out_step_size: int = 2
    scale_in_step_size: int = 1
    cost_per_server_hour: float = 0.10
    sla_target_response_time_ms: float = 200.0
    random_seed: int = 42

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        """Instantiate configuration from dictionary, casting types safely."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        
        # Cast fields safely
        try:
            if "initial_users" in filtered:
                filtered["initial_users"] = int(filtered["initial_users"])
            if "peak_users" in filtered:
                filtered["peak_users"] = int(filtered["peak_users"])
            if "requests_per_user_min" in filtered:
                filtered["requests_per_user_min"] = float(filtered["requests_per_user_min"])
            if "duration_steps" in filtered:
                filtered["duration_steps"] = int(filtered["duration_steps"])
            if "step_unit_minutes" in filtered:
                filtered["step_unit_minutes"] = float(filtered["step_unit_minutes"])
            if "traffic_pattern" in filtered:
                filtered["traffic_pattern"] = str(filtered["traffic_pattern"])
            if "fixed_servers" in filtered:
                filtered["fixed_servers"] = int(filtered["fixed_servers"])
            if "as_initial_servers" in filtered:
                filtered["as_initial_servers"] = int(filtered["as_initial_servers"])
            if "as_min_servers" in filtered:
                filtered["as_min_servers"] = int(filtered["as_min_servers"])
            if "as_max_servers" in filtered:
                filtered["as_max_servers"] = int(filtered["as_max_servers"])
            if "server_capacity_rpm" in filtered:
                filtered["server_capacity_rpm"] = float(filtered["server_capacity_rpm"])
            if "cpu_scale_out_threshold" in filtered:
                filtered["cpu_scale_out_threshold"] = float(filtered["cpu_scale_out_threshold"])
            if "cpu_scale_in_threshold" in filtered:
                filtered["cpu_scale_in_threshold"] = float(filtered["cpu_scale_in_threshold"])
            if "scale_out_cooldown" in filtered:
                filtered["scale_out_cooldown"] = int(filtered["scale_out_cooldown"])
            if "scale_in_cooldown" in filtered:
                filtered["scale_in_cooldown"] = int(filtered["scale_in_cooldown"])
            if "startup_delay" in filtered:
                filtered["startup_delay"] = int(filtered["startup_delay"])
            if "scale_out_step_size" in filtered:
                filtered["scale_out_step_size"] = int(filtered["scale_out_step_size"])
            if "scale_in_step_size" in filtered:
                filtered["scale_in_step_size"] = int(filtered["scale_in_step_size"])
            if "cost_per_server_hour" in filtered:
                filtered["cost_per_server_hour"] = float(filtered["cost_per_server_hour"])
            if "sla_target_response_time_ms" in filtered:
                filtered["sla_target_response_time_ms"] = float(filtered["sla_target_response_time_ms"])
            if "random_seed" in filtered:
                filtered["random_seed"] = int(filtered["random_seed"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Failed to cast configuration parameters: {exc}")

        return cls(**filtered)


@dataclass
class ValidationResult:
    """Outcome of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


def validate_config(config: Any) -> ValidationResult:
    """
    Validate simulation parameters according to engineering and business constraints.
    Returns ValidationResult with explicit errors and actionable warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if isinstance(config, dict):
        try:
            cfg = SimulationConfig.from_dict(config)
        except Exception as exc:
            return ValidationResult(is_valid=False, errors=[f"Configuration formatting error: {exc}"], warnings=[])
    elif isinstance(config, SimulationConfig):
        cfg = config
    else:
        return ValidationResult(is_valid=False, errors=["Config must be a SimulationConfig or dict."], warnings=[])

    # Traffic & Duration checks
    if cfg.initial_users < 0:
        errors.append("Initial user traffic must be non-negative (>= 0).")
    if cfg.peak_users < 0:
        errors.append("Peak user traffic must be non-negative (>= 0).")
    if cfg.duration_steps < 5:
        errors.append("Simulation duration must be at least 5 time steps.")
    if cfg.duration_steps > 1440:
        warnings.append("Simulation duration exceeds 1440 steps (24 hours). Processing may take slightly longer.")
    if cfg.requests_per_user_min < 0:
        errors.append("Requests per user per minute must be non-negative.")
    if cfg.step_unit_minutes <= 0:
        errors.append("Time-step duration must be strictly positive (> 0 minutes).")

    if cfg.traffic_pattern not in VALID_TRAFFIC_PATTERNS:
        errors.append(f"Traffic pattern '{cfg.traffic_pattern}' is unsupported. Choose from: {', '.join(VALID_TRAFFIC_PATTERNS)}.")

    # Server Capacity & Fixed Infrastructure
    if cfg.fixed_servers < 1:
        errors.append("Fixed infrastructure server count must be at least 1.")
    if cfg.server_capacity_rpm <= 0:
        errors.append("Server processing capacity must be strictly positive (> 0 requests/min).")

    # Auto-scaling limits
    if cfg.as_min_servers < 1:
        errors.append("Auto-scaling minimum server count must be at least 1.")
    if cfg.as_max_servers < cfg.as_min_servers:
        errors.append(f"Auto-scaling maximum servers ({cfg.as_max_servers}) cannot be less than minimum servers ({cfg.as_min_servers}).")
    if cfg.as_initial_servers < cfg.as_min_servers:
        errors.append(f"Initial auto-scaling servers ({cfg.as_initial_servers}) cannot be less than minimum servers ({cfg.as_min_servers}).")
    if cfg.as_initial_servers > cfg.as_max_servers:
        errors.append(f"Initial auto-scaling servers ({cfg.as_initial_servers}) cannot exceed maximum servers ({cfg.as_max_servers}).")

    # Step sizing
    if cfg.scale_out_step_size < 1:
        errors.append("Scale-out step size must be at least 1 server.")
    if cfg.scale_in_step_size < 1:
        errors.append("Scale-in step size must be at least 1 server.")

    # Thresholds
    if cfg.cpu_scale_out_threshold <= 0 or cfg.cpu_scale_out_threshold > 100:
        errors.append("CPU scale-out threshold must be between 0% (exclusive) and 100% (inclusive).")
    if cfg.cpu_scale_in_threshold < 0 or cfg.cpu_scale_in_threshold >= 100:
        errors.append("CPU scale-in threshold must be between 0% (inclusive) and 100% (exclusive).")
    if cfg.cpu_scale_in_threshold >= cfg.cpu_scale_out_threshold:
        errors.append(
            f"CPU scale-in threshold ({cfg.cpu_scale_in_threshold}%) must be strictly lower than "
            f"scale-out threshold ({cfg.cpu_scale_out_threshold}%)."
        )
    elif (cfg.cpu_scale_out_threshold - cfg.cpu_scale_in_threshold) < 15.0:
        warnings.append(
            f"Narrow gap between scale-in ({cfg.cpu_scale_in_threshold}%) and scale-out ({cfg.cpu_scale_out_threshold}%) "
            f"thresholds may induce flapping/oscillation if cooldown is short."
        )

    # Cooldown & Delays
    if cfg.scale_out_cooldown < 0:
        errors.append("Scale-out cooldown must be non-negative (>= 0).")
    if cfg.scale_in_cooldown < 0:
        errors.append("Scale-in cooldown must be non-negative (>= 0).")
    if cfg.startup_delay < 0:
        errors.append("Server startup delay must be non-negative (>= 0).")

    # Cost & SLA
    if cfg.cost_per_server_hour < 0:
        errors.append("Server cost per hour must be non-negative (>= 0).")
    if cfg.sla_target_response_time_ms <= 0:
        errors.append("Target SLA response time must be strictly positive (> 0 ms).")

    # Architectural Warnings
    max_as_capacity = cfg.as_max_servers * cfg.server_capacity_rpm
    peak_demand = cfg.peak_users * cfg.requests_per_user_min
    if peak_demand > max_as_capacity:
        warnings.append(
            f"Expected peak demand ({peak_demand:,.0f} req/min) exceeds maximum auto-scaling capacity "
            f"({max_as_capacity:,.0f} req/min across {cfg.as_max_servers} servers). Request drops will occur during peak."
        )

    fixed_capacity = cfg.fixed_servers * cfg.server_capacity_rpm
    if peak_demand > fixed_capacity:
        warnings.append(
            f"Expected peak demand exceeds fixed baseline capacity ({fixed_capacity:,.0f} req/min). "
            f"Fixed infrastructure will experience overload."
        )

    return ValidationResult(
        is_valid=(len(errors) == 0),
        errors=errors,
        warnings=warnings
    )


def load_default_config(filepath: Optional[str] = None) -> SimulationConfig:
    """Load default configuration from JSON file or fall back to dataclass defaults."""
    if filepath is None:
        base_dir = Path(__file__).resolve().parent.parent
        filepath = str(base_dir / "config" / "default_config.json")

    path = Path(filepath)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SimulationConfig.from_dict(data)
        except Exception:
            return SimulationConfig()
    return SimulationConfig()
