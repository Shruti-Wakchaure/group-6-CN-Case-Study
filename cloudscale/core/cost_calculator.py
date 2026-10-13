"""Cost calculation and financial comparative analytics for CloudScale."""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import pandas as pd

from core.validation import SimulationConfig


@dataclass
class CostMetrics:
    """Cost metrics for a single infrastructure system."""
    total_cost_usd: float
    total_server_hours: float
    cost_per_1k_incoming_requests: float
    cost_per_1k_processed_requests: float
    peak_active_servers: int
    avg_active_servers: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostComparisonResult:
    """Comparative financial analysis between Fixed and Auto-Scaling infrastructure."""
    fixed: CostMetrics
    autoscaling: CostMetrics
    absolute_savings_usd: float
    savings_percent: Optional[float]
    savings_percent_display: str
    is_cost_saving: bool
    summary_verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fixed": self.fixed.to_dict(),
            "autoscaling": self.autoscaling.to_dict(),
            "absolute_savings_usd": self.absolute_savings_usd,
            "savings_percent": self.savings_percent,
            "savings_percent_display": self.savings_percent_display,
            "is_cost_saving": self.is_cost_saving,
            "summary_verdict": self.summary_verdict,
        }


def calculate_cost_savings_pct(fixed_cost: float, as_cost: float) -> Optional[float]:
    """
    Calculate cost savings percentage:
        ((Fixed Cost - Auto-Scaling Cost) / Fixed Cost) * 100
    Returns None if Fixed Cost is 0 or negative.
    Negative savings percentages are returned truthfully if Auto-Scaling costs more.
    """
    if fixed_cost <= 0.0:
        return None
    return ((fixed_cost - as_cost) / fixed_cost) * 100.0


def compute_system_cost_metrics(df: pd.DataFrame, config: SimulationConfig) -> CostMetrics:
    """Compute comprehensive cost metrics from time-series DataFrame."""
    if df.empty:
        return CostMetrics(
            total_cost_usd=0.0,
            total_server_hours=0.0,
            cost_per_1k_incoming_requests=0.0,
            cost_per_1k_processed_requests=0.0,
            peak_active_servers=0,
            avg_active_servers=0.0,
        )

    step_hours = config.step_unit_minutes / 60.0
    # Billable servers = total_servers (active + provisioning)
    total_server_hours = float((df["total_servers"] * step_hours).sum())
    total_cost = float(df["cumulative_cost_usd"].iloc[-1])

    total_incoming = float(df["incoming_requests"].sum())
    total_processed = float(df["processed_requests"].sum())

    cost_per_1k_incoming = (
        (total_cost / total_incoming * 1000.0) if total_incoming > 0 else 0.0
    )
    cost_per_1k_processed = (
        (total_cost / total_processed * 1000.0) if total_processed > 0 else 0.0
    )

    peak_servers = int(df["active_servers"].max())
    avg_servers = float(df["active_servers"].mean())

    return CostMetrics(
        total_cost_usd=round(total_cost, 4),
        total_server_hours=round(total_server_hours, 2),
        cost_per_1k_incoming_requests=round(cost_per_1k_incoming, 4),
        cost_per_1k_processed_requests=round(cost_per_1k_processed, 4),
        peak_active_servers=peak_servers,
        avg_active_servers=round(avg_servers, 2),
    )


def compare_infrastructure_costs(
    fixed_df: pd.DataFrame,
    as_df: pd.DataFrame,
    config: SimulationConfig
) -> CostComparisonResult:
    """
    Generate side-by-side cost optimization comparison between Fixed and Auto-Scaling infrastructure.
    """
    fixed_metrics = compute_system_cost_metrics(fixed_df, config)
    as_metrics = compute_system_cost_metrics(as_df, config)

    diff = fixed_metrics.total_cost_usd - as_metrics.total_cost_usd
    savings_pct = calculate_cost_savings_pct(
        fixed_metrics.total_cost_usd,
        as_metrics.total_cost_usd
    )

    if savings_pct is None:
        savings_display = "N/A"
        verdict = "Baseline fixed cost is zero; percentage savings cannot be evaluated."
        is_saving = False
    elif savings_pct > 0.0:
        savings_display = f"{savings_pct:+.2f}%"
        is_saving = True
        verdict = f"Auto-scaling reduced infrastructure spending by {savings_display} (${diff:.2f})."
    elif savings_pct < 0.0:
        savings_display = f"{savings_pct:+.2f}%"
        is_saving = False
        verdict = f"Auto-scaling cost is higher by {abs(savings_pct):.2f}% (${abs(diff):.2f}) due to dynamic scaling capacity matching a sustained peak beyond baseline."
    else:
        savings_display = "0.00%"
        is_saving = False
        verdict = "Both architectures incurred identical infrastructure costs."

    return CostComparisonResult(
        fixed=fixed_metrics,
        autoscaling=as_metrics,
        absolute_savings_usd=round(diff, 4),
        savings_percent=round(savings_pct, 2) if savings_pct is not None else None,
        savings_percent_display=savings_display,
        is_cost_saving=is_saving,
        summary_verdict=verdict
    )
