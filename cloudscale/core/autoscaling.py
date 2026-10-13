"""Auto-scaling engine and baseline infrastructure simulator for CloudScale."""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
import pandas as pd

from core.validation import SimulationConfig
from core.simulator import TimeStepMetrics, estimate_latency_ms


@dataclass
class AutoScalerState:
    """Internal state of the Auto-Scaling engine across simulation steps."""
    active_servers: int
    provisioning_queue: List[Tuple[int, int]] = field(default_factory=list)  # (activation_step, server_count)
    last_scale_out_step: int = -9999
    last_scale_in_step: int = -9999
    scale_out_events: int = 0
    scale_in_events: int = 0


def run_fixed_simulation(config: SimulationConfig, traffic_series: List[int]) -> pd.DataFrame:
    """
    Run baseline simulation using a fixed number of servers.
    The baseline system uses the exact same traffic, request rate, capacity, and cost rate.
    """
    records: List[Dict[str, Any]] = []
    cumulative_cost = 0.0
    step_duration_hours = config.step_unit_minutes / 60.0
    fixed_servers = config.fixed_servers
    capacity_rpm = fixed_servers * config.server_capacity_rpm

    for t, users in enumerate(traffic_series):
        incoming_requests = users * config.requests_per_user_min
        
        # Load balancer & processing capacity
        processed_requests = min(incoming_requests, capacity_rpm)
        dropped_requests = max(0.0, incoming_requests - capacity_rpm)
        
        # Utilization
        if capacity_rpm > 0:
            raw_util = (incoming_requests / capacity_rpm) * 100.0
            cpu_util = min(100.0, raw_util)
        else:
            raw_util = 100.0
            cpu_util = 100.0

        req_per_server = (incoming_requests / fixed_servers) if fixed_servers > 0 else 0.0

        # Latency
        avg_rt, p95_rt = estimate_latency_ms(
            incoming_requests=incoming_requests,
            capacity_rpm=capacity_rpm,
            sla_target_ms=config.sla_target_response_time_ms
        )

        # Cost: Fixed active servers running for step_duration_hours
        step_cost = fixed_servers * step_duration_hours * config.cost_per_server_hour
        cumulative_cost += step_cost

        is_overloaded = (raw_util > 100.0) or (dropped_requests > 0.0)
        sla_breached = avg_rt > config.sla_target_response_time_ms

        metric = TimeStepMetrics(
            step=t,
            time_minutes=t * config.step_unit_minutes,
            users=users,
            incoming_requests=round(incoming_requests, 2),
            active_servers=fixed_servers,
            provisioning_servers=0,
            total_servers=fixed_servers,
            capacity_rpm=round(capacity_rpm, 2),
            processed_requests=round(processed_requests, 2),
            dropped_requests=round(dropped_requests, 2),
            cpu_utilization_pct=round(cpu_util, 2),
            raw_utilization_pct=round(raw_util, 2),
            requests_per_active_server=round(req_per_server, 2),
            avg_response_time_ms=avg_rt,
            p95_response_time_ms=p95_rt,
            step_cost_usd=round(step_cost, 6),
            cumulative_cost_usd=round(cumulative_cost, 4),
            scaling_action="FIXED_CAPACITY",
            is_overloaded=is_overloaded,
            sla_breached=sla_breached
        )
        records.append(metric.to_dict())

    return pd.DataFrame(records)


def run_autoscaling_simulation(config: SimulationConfig, traffic_series: List[int]) -> pd.DataFrame:
    """
    Run auto-scaling simulation with threshold-based horizontal scaling, cooldowns, and startup delay.
    
    Order of operations at each time step t:
    1. Check provisioning queue: Any servers scheduled for step t become active.
    2. Process incoming requests using active servers.
    3. Calculate utilization and latency.
    4. Calculate infrastructure cost (billable instances = active + provisioning).
    5. Evaluate scaling policy (cooldowns, thresholds, anti-flapping dampening) for subsequent time steps.
    6. Record metrics.
    """
    records: List[Dict[str, Any]] = []
    cumulative_cost = 0.0
    step_duration_hours = config.step_unit_minutes / 60.0

    state = AutoScalerState(
        active_servers=config.as_initial_servers,
        provisioning_queue=[],
        last_scale_out_step=-9999,
        last_scale_in_step=-9999
    )

    for t, users in enumerate(traffic_series):
        # 1. Update provisioning queue: servers that finished startup delay
        ready_servers = 0
        remaining_queue: List[Tuple[int, int]] = []
        for ready_step, count in state.provisioning_queue:
            if ready_step <= t:
                ready_servers += count
            else:
                remaining_queue.append((ready_step, count))
        state.active_servers += ready_servers
        state.provisioning_queue = remaining_queue

        # Provisioning servers currently warming up
        provisioning_count = sum(c for _, c in state.provisioning_queue)
        total_servers = state.active_servers + provisioning_count

        # 2. Capacity & Processing (only active servers handle traffic)
        capacity_rpm = state.active_servers * config.server_capacity_rpm
        incoming_requests = users * config.requests_per_user_min
        processed_requests = min(incoming_requests, capacity_rpm)
        dropped_requests = max(0.0, incoming_requests - capacity_rpm)

        # 3. Utilization & Latency
        if capacity_rpm > 0:
            raw_util = (incoming_requests / capacity_rpm) * 100.0
            cpu_util = min(100.0, raw_util)
        else:
            raw_util = 100.0
            cpu_util = 100.0

        req_per_server = (incoming_requests / state.active_servers) if state.active_servers > 0 else 0.0

        avg_rt, p95_rt = estimate_latency_ms(
            incoming_requests=incoming_requests,
            capacity_rpm=capacity_rpm,
            sla_target_ms=config.sla_target_response_time_ms
        )

        # 4. Evaluate Scaling Policy
        scaling_action = "NONE"

        # Check scale-out condition
        if cpu_util > config.cpu_scale_out_threshold:
            # Check cooldown
            if (t - state.last_scale_out_step) <= config.scale_out_cooldown:
                scaling_action = "SCALE_OUT_COOLDOWN"
            elif total_servers >= config.as_max_servers:
                scaling_action = "MAX_CAPACITY_REACHED"
            else:
                # Can scale out
                room = config.as_max_servers - total_servers
                to_add = min(config.scale_out_step_size, room)
                if to_add > 0:
                    if config.startup_delay > 0:
                        activation_step = t + config.startup_delay
                        state.provisioning_queue.append((activation_step, to_add))
                        scaling_action = f"SCALE_OUT (+{to_add} starting, ready step {activation_step})"
                    else:
                        state.active_servers += to_add
                        scaling_action = f"SCALE_OUT (+{to_add} active)"
                    state.last_scale_out_step = t
                    state.scale_out_events += 1

        # Check scale-in condition
        elif cpu_util < config.cpu_scale_in_threshold:
            if provisioning_count > 0:
                # Do not scale in while servers are actively provisioning
                scaling_action = "SCALE_IN_BLOCKED_PROVISIONING"
            elif (t - state.last_scale_in_step) <= config.scale_in_cooldown:
                scaling_action = "SCALE_IN_COOLDOWN"
            elif total_servers <= config.as_min_servers:
                scaling_action = "MIN_CAPACITY_REACHED"
            else:
                # Anti-flapping dampening check:
                # If we remove servers, what would the new CPU utilization become?
                room_to_remove = min(config.scale_in_step_size, state.active_servers - config.as_min_servers)
                if room_to_remove > 0:
                    hypothetical_active = state.active_servers - room_to_remove
                    hypothetical_capacity = hypothetical_active * config.server_capacity_rpm
                    hypothetical_util = (incoming_requests / hypothetical_capacity) * 100.0 if hypothetical_capacity > 0 else 100.0

                    if hypothetical_util >= config.cpu_scale_out_threshold:
                        scaling_action = "SCALE_IN_DAMPENED (Anti-Flap)"
                    else:
                        state.active_servers -= room_to_remove
                        state.last_scale_in_step = t
                        state.scale_in_events += 1
                        scaling_action = f"SCALE_IN (-{room_to_remove})"

        # Recalculate cluster count after scaling action for telemetry
        provisioning_count = sum(c for _, c in state.provisioning_queue)
        total_servers = state.active_servers + provisioning_count

        # In cloud computing, total instances provisioned (active + starting) are billable
        step_cost = total_servers * step_duration_hours * config.cost_per_server_hour
        cumulative_cost += step_cost

        is_overloaded = (raw_util > 100.0) or (dropped_requests > 0.0)
        sla_breached = avg_rt > config.sla_target_response_time_ms

        # Record metrics
        metric = TimeStepMetrics(
            step=t,
            time_minutes=t * config.step_unit_minutes,
            users=users,
            incoming_requests=round(incoming_requests, 2),
            active_servers=state.active_servers,
            provisioning_servers=provisioning_count,
            total_servers=total_servers,
            capacity_rpm=round(capacity_rpm, 2),
            processed_requests=round(processed_requests, 2),
            dropped_requests=round(dropped_requests, 2),
            cpu_utilization_pct=round(cpu_util, 2),
            raw_utilization_pct=round(raw_util, 2),
            requests_per_active_server=round(req_per_server, 2),
            avg_response_time_ms=avg_rt,
            p95_response_time_ms=p95_rt,
            step_cost_usd=round(step_cost, 6),
            cumulative_cost_usd=round(cumulative_cost, 4),
            scaling_action=scaling_action,
            is_overloaded=is_overloaded,
            sla_breached=sla_breached
        )
        records.append(metric.to_dict())

    return pd.DataFrame(records)
