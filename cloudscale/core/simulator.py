"""Traffic generator and time-step simulation framework for CloudScale."""

import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from core.validation import SimulationConfig


@dataclass
class TimeStepMetrics:
    """Metrics recorded at a single simulation time step."""
    step: int
    time_minutes: float
    users: int
    incoming_requests: float
    active_servers: int
    provisioning_servers: int
    total_servers: int
    capacity_rpm: float
    processed_requests: float
    dropped_requests: float
    cpu_utilization_pct: float
    raw_utilization_pct: float
    requests_per_active_server: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    step_cost_usd: float
    cumulative_cost_usd: float
    scaling_action: str
    is_overloaded: bool
    sla_breached: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_traffic_series(config: SimulationConfig) -> List[int]:
    """
    Generate deterministic time-series of active users based on the selected traffic pattern.
    Uses numpy's default_rng with the configured random_seed for reproducibility.
    """
    steps = config.duration_steps
    initial = max(0, config.initial_users)
    peak = max(0, config.peak_users)
    rng = np.random.default_rng(config.random_seed)

    user_counts: List[int] = []

    pattern = config.traffic_pattern

    if pattern == "Constant":
        user_counts = [initial] * steps

    elif pattern == "Gradual Growth":
        # Linear ramp from initial to peak
        for t in range(steps):
            fraction = t / max(1, steps - 1)
            val = initial + (peak - initial) * fraction
            user_counts.append(int(round(val)))

    elif pattern == "Sudden Spike":
        # Flat baseline, sudden sharp surge in the middle third, then drops back
        spike_start = int(steps * 0.35)
        spike_end = int(steps * 0.65)
        for t in range(steps):
            if spike_start <= t <= spike_end:
                val = peak
            else:
                val = initial
            user_counts.append(int(round(val)))

    elif pattern == "Periodic / Daily":
        # Sinusoidal diurnal wave
        for t in range(steps):
            wave = 0.5 * (1.0 - math.cos(2.0 * math.pi * t / max(1, steps)))
            val = initial + (peak - initial) * wave
            user_counts.append(int(round(val)))

    elif pattern == "Festival Sale":
        # Phased flash sale:
        # Phase 1: 0% - 20% warmup
        # Phase 2: 20% - 35% steep surge
        # Phase 3: 35% - 65% peak flash sale plateau with micro-bursts
        # Phase 4: 65% - 100% gradual cool-down
        for t in range(steps):
            progress = t / max(1, steps)
            if progress < 0.20:
                ramp = progress / 0.20
                val = initial + (initial * 0.2) * ramp
            elif progress < 0.35:
                sub_prog = (progress - 0.20) / 0.15
                # Exponential climb
                val = initial * 1.2 + (peak - initial * 1.2) * (sub_prog ** 1.8)
            elif progress < 0.65:
                # Sustained peak with slight deterministic wave
                sub_prog = (progress - 0.35) / 0.30
                micro_wave = math.sin(sub_prog * 4.0 * math.pi) * 0.05 * (peak - initial)
                val = peak + micro_wave
            else:
                sub_prog = (progress - 0.65) / 0.35
                decay = math.exp(-2.5 * sub_prog)
                val = initial + (peak - initial) * decay
            user_counts.append(max(0, int(round(val))))

    elif pattern == "Randomized":
        # Random walk / bounded noise between min and max bounds
        low = min(initial, peak)
        high = max(initial, peak)
        curr = float(initial)
        for _ in range(steps):
            delta = rng.normal(loc=0.0, scale=(high - low + 1) * 0.08)
            curr = np.clip(curr + delta, low, high)
            user_counts.append(int(round(curr)))

    else:
        user_counts = [initial] * steps

    # If both initial and peak are zero, return strictly zero traffic
    if initial == 0 and peak == 0:
        return [0] * steps

    # Add subtle deterministic jitter to continuous patterns for realism (seeded)
    if pattern in ["Gradual Growth", "Periodic / Daily", "Festival Sale"] and steps > 0 and (initial > 0 or peak > 0):
        jitter = rng.normal(0, max(0.5, 0.015 * peak), size=steps)
        for i in range(steps):
            user_counts[i] = max(0, int(round(user_counts[i] + jitter[i])))

    return user_counts


def estimate_latency_ms(
    incoming_requests: float,
    capacity_rpm: float,
    sla_target_ms: float
) -> tuple[float, float]:
    """
    Estimate average and p95 latency using a queuing theory approximation model.
    
    Model formulation:
    - Base server processing latency L0 = 35 ms.
    - Let rho = incoming_requests / capacity_rpm (utilization).
    - When capacity == 0: saturation timeout is returned.
    - When rho < 0.85: M/M/1-style queueing delay L0 / (1 - min(0.9, rho)^1.4).
    - When 0.85 <= rho < 1.0: latency ramps up noticeably as queues build.
    - When rho >= 1.0 (overload): queuing delay escalates up to timeout (2500 ms).
    - P95 latency is modeled as 1.35x to 1.85x of average latency based on queue variance.
    
    Returns:
        (avg_response_time_ms, p95_response_time_ms)
    """
    base_latency = 35.0
    timeout_latency = max(2500.0, sla_target_ms * 5.0)

    if capacity_rpm <= 0:
        return timeout_latency, timeout_latency * 1.2

    if incoming_requests <= 0:
        return base_latency, base_latency * 1.25

    rho = incoming_requests / capacity_rpm

    if rho < 0.85:
        # Healthy load: slight queueing
        factor = 1.0 / max(0.05, (1.0 - (rho ** 1.35)))
        avg_rt = base_latency + (base_latency * 0.45 * (factor - 1.0))
        avg_rt = min(avg_rt, 250.0)
    elif rho < 1.0:
        # High load: queue builds up towards SLA boundary
        excess = (rho - 0.85) / 0.15
        avg_rt = 250.0 + excess * (sla_target_ms * 1.5 - 250.0)
    else:
        # Overload: requests waiting or dropping
        overload_ratio = rho - 1.0
        avg_rt = sla_target_ms * 1.5 + (overload_ratio * 1200.0)
        avg_rt = min(timeout_latency, avg_rt)

    # Estimate 95th percentile
    variance_factor = 1.35 + 0.45 * min(1.0, rho)
    p95_rt = min(timeout_latency * 1.2, avg_rt * variance_factor)

    return round(avg_rt, 2), round(p95_rt, 2)
