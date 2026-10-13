"""CloudScale: Cloud Network Infrastructure Case Study
Interactive Streamlit Dashboard for Cost Optimization and Scalability Simulation.
"""

import sys
from pathlib import Path

# Add project root to path for local imports
project_dir = Path(__file__).resolve().parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from core.validation import (
    SimulationConfig,
    validate_config,
    load_default_config,
    VALID_TRAFFIC_PATTERNS
)
from core.simulator import generate_traffic_series
from core.autoscaling import run_fixed_simulation, run_autoscaling_simulation
from core.metrics import evaluate_simulation_results
from core.scenarios import PREDEFINED_SCENARIOS, run_all_scenarios_comparison
from core.reports import (
    generate_merged_simulation_csv,
    generate_markdown_report,
    generate_html_report
)

# Page configuration
st.set_page_config(
    page_title="CloudScale | Cloud Infrastructure Simulation",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Dark Theme CSS
CUSTOM_CSS = """
<style>
    /* Dark navy theme overrides */
    .stApp {
        background-color: #0b132b;
        color: #e2e8f0;
    }
    
    /* Header & typography */
    h1, h2, h3, h4 {
        color: #f8fafc !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1c2541;
        border-right: 1px solid #3a506b;
    }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1c2541;
        border: 1px solid #3a506b;
        border-radius: 8px;
        padding: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetricValue"] {
        color: #64dfdf !important;
        font-weight: 700;
        font-size: 24px;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 13px;
        font-weight: 500;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1c2541;
        padding: 8px;
        border-radius: 8px;
        border: 1px solid #3a506b;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3a506b !important;
        color: #64dfdf !important;
    }
    
    /* Alert badges */
    .badge-info {
        background: #1e3a8a;
        color: #93c5fd;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        display: inline-block;
    }
    
    /* Architecture Diagram Box */
    .arch-box {
        background: #1c2541;
        border: 1px solid #3a506b;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Initialize Session State
if "config" not in st.session_state:
    st.session_state.config = load_default_config()

if "selected_preset_key" not in st.session_state:
    st.session_state.selected_preset_key = "festival_sale"


# Sidebar: Preset and Configuration Controls
with st.sidebar:
    st.markdown("### ☁️ CloudScale Control Panel")
    st.caption("Case Study Simulation Parameters")

    # Scenario Presets
    preset_names = {k: v.name for k, v in PREDEFINED_SCENARIOS.items()}
    preset_names["custom"] = "⚙️ Custom Configuration"

    selected_preset = st.selectbox(
        "Select Scenario Preset",
        options=list(preset_names.keys()),
        format_func=lambda x: preset_names[x],
        index=list(preset_names.keys()).index(st.session_state.selected_preset_key)
        if st.session_state.selected_preset_key in preset_names else 2
    )

    if selected_preset != "custom" and selected_preset != st.session_state.selected_preset_key:
        st.session_state.selected_preset_key = selected_preset
        preset_cfg = PREDEFINED_SCENARIOS[selected_preset].config
        st.session_state.config = SimulationConfig.from_dict(preset_cfg.to_dict())
        st.rerun()

    cfg = st.session_state.config

    # Configuration Sections
    with st.expander("📊 Workload & Traffic", expanded=True):
        pattern_idx = VALID_TRAFFIC_PATTERNS.index(cfg.traffic_pattern) if cfg.traffic_pattern in VALID_TRAFFIC_PATTERNS else 4
        traffic_pattern = st.selectbox("Traffic Pattern", options=VALID_TRAFFIC_PATTERNS, index=pattern_idx)
        initial_users = st.number_input("Initial Users", min_value=0, max_value=50000, value=int(cfg.initial_users), step=50)
        peak_users = st.number_input("Peak Users", min_value=0, max_value=100000, value=int(cfg.peak_users), step=100)
        req_per_user = st.number_input("Requests / User / Min", min_value=0.1, max_value=60.0, value=float(cfg.requests_per_user_min), step=0.5)
        duration_steps = st.number_input("Simulation Steps (min)", min_value=10, max_value=360, value=int(cfg.duration_steps), step=10)
        random_seed = st.number_input("Random Seed", min_value=0, max_value=999999, value=int(cfg.random_seed), step=1)

    with st.expander("🖥️ Server Capacity & Fixed Fleet", expanded=True):
        fixed_servers = st.number_input("Fixed Baseline Servers", min_value=1, max_value=100, value=int(cfg.fixed_servers), step=1)
        server_capacity = st.number_input("Server Capacity (req/min)", min_value=100.0, max_value=10000.0, value=float(cfg.server_capacity_rpm), step=200.0)

    with st.expander("⚡ Auto-Scaling Policy", expanded=False):
        as_min_servers = st.number_input("Min Servers", min_value=1, max_value=50, value=int(cfg.as_min_servers), step=1)
        as_max_servers = st.number_input("Max Servers", min_value=as_min_servers, max_value=100, value=int(cfg.as_max_servers), step=1)
        as_initial_servers = st.number_input("Initial AS Servers", min_value=as_min_servers, max_value=as_max_servers, value=int(min(max(cfg.as_initial_servers, as_min_servers), as_max_servers)), step=1)
        scale_out_threshold = st.slider("Scale-Out CPU Threshold (%)", min_value=40.0, max_value=95.0, value=float(cfg.cpu_scale_out_threshold), step=5.0)
        scale_in_threshold = st.slider("Scale-In CPU Threshold (%)", min_value=10.0, max_value=scale_out_threshold - 5.0, value=float(min(cfg.cpu_scale_in_threshold, scale_out_threshold - 5.0)), step=5.0)
        scale_out_cooldown = st.number_input("Scale-Out Cooldown (steps)", min_value=0, max_value=20, value=int(cfg.scale_out_cooldown), step=1)
        scale_in_cooldown = st.number_input("Scale-In Cooldown (steps)", min_value=0, max_value=20, value=int(cfg.scale_in_cooldown), step=1)
        startup_delay = st.number_input("Server Startup Delay (steps)", min_value=0, max_value=10, value=int(cfg.startup_delay), step=1)
        scale_out_step = st.number_input("Scale-Out Step Size", min_value=1, max_value=10, value=int(cfg.scale_out_step_size), step=1)
        scale_in_step = st.number_input("Scale-In Step Size", min_value=1, max_value=10, value=int(cfg.scale_in_step_size), step=1)

    with st.expander("💰 Financial & SLA Targets", expanded=False):
        cost_per_hour = st.number_input("Cost / Server / Hour ($)", min_value=0.01, max_value=10.0, value=float(cfg.cost_per_server_hour), step=0.05)
        sla_target_ms = st.number_input("Target SLA Latency (ms)", min_value=50.0, max_value=2000.0, value=float(cfg.sla_target_response_time_ms), step=25.0)

    # Build updated config object
    updated_config = SimulationConfig(
        initial_users=initial_users,
        peak_users=peak_users,
        requests_per_user_min=req_per_user,
        duration_steps=duration_steps,
        step_unit_minutes=1.0,
        traffic_pattern=traffic_pattern,
        fixed_servers=fixed_servers,
        as_initial_servers=as_initial_servers,
        as_min_servers=as_min_servers,
        as_max_servers=as_max_servers,
        server_capacity_rpm=server_capacity,
        cpu_scale_out_threshold=scale_out_threshold,
        cpu_scale_in_threshold=scale_in_threshold,
        scale_out_cooldown=scale_out_cooldown,
        scale_in_cooldown=scale_in_cooldown,
        startup_delay=startup_delay,
        scale_out_step_size=scale_out_step,
        scale_in_step_size=scale_in_step,
        cost_per_server_hour=cost_per_hour,
        sla_target_response_time_ms=sla_target_ms,
        random_seed=random_seed
    )

    validation = validate_config(updated_config)
    st.session_state.config = updated_config

    if not validation.is_valid:
        st.error("⚠️ Invalid Configuration:")
        for err in validation.errors:
            st.write(f"- {err}")
    elif validation.warnings:
        for warn in validation.warnings:
            st.warning(f"Note: {warn}")
    else:
        st.success("✅ Configuration Validated")


# Main Dashboard Header
st.title("☁️ CloudScale: Cloud Network Infrastructure")
st.markdown(
    "**A Case Study on Cost Optimization and Scalability** &bull; "
    "*Simulating Dynamic Horizontal Scaling vs. Static Capacity Under Real-World E-Commerce Traffic*"
)

# Problem statement context card
with st.container():
    st.markdown(
        """
        <div style="background: rgba(58, 80, 107, 0.35); border-left: 4px solid #48bfe3; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
            <strong style="color: #64dfdf;">Problem Statement:</strong>
            An e-commerce website experiences volatile user traffic throughout the day. Static provisioning wastes budget during lulls and risks crashes during surges.
            This case study simulates and measures cost, utilization, latency, and availability when comparing fixed infrastructure with dynamic threshold-based auto-scaling.
        </div>
        """,
        unsafe_allow_html=True
    )

# Execution of Simulation Engine
if not validation.is_valid:
    st.error("Please resolve configuration errors in the sidebar before running simulation.")
    st.stop()

current_config = st.session_state.config

# 1. Deterministic Traffic Generation
traffic_series = generate_traffic_series(current_config)

# 2. Infrastructure Simulations (Identical Traffic Inputs)
fixed_df = run_fixed_simulation(current_config, traffic_series)
as_df = run_autoscaling_simulation(current_config, traffic_series)

# 3. Comparative Evaluation & Metrics
comparison = evaluate_simulation_results(fixed_df, as_df, current_config)
fixed_perf = comparison.fixed_metrics
as_perf = comparison.as_metrics
cost_comp = comparison.cost_comparison


# Plotly Dark Theme Helper
def apply_plotly_theme(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(color="#f1f5f9", size=16)),
        template="plotly_dark",
        paper_bgcolor="#1c2541",
        plot_bgcolor="#0b132b",
        font=dict(color="#cbd5e1", size=12),
        margin=dict(l=40, r=40, t=50, b=40),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11)
        ),
        hovermode="x unified"
    )
    fig.update_xaxes(gridcolor="#3a506b", zerolinecolor="#3a506b")
    fig.update_yaxes(gridcolor="#3a506b", zerolinecolor="#3a506b")
    return fig


# Dashboard Tabs
tabs = st.tabs([
    "📊 Overview",
    "⏱️ Live Simulation",
    "🏗️ Architecture",
    "📈 Scalability Analysis",
    "💰 Cost Optimization",
    "🎯 Performance & SLA",
    "🔄 Scenario Comparison",
    "📋 Recommendations & Reports",
    "📐 Methodology"
])


# -------------------------------------------------------------
# TAB 1: OVERVIEW
# -------------------------------------------------------------
with tabs[0]:
    st.subheader("Executive Comparison Summary")

    # High-level Alert Banner if Overload Occurred
    if as_perf.total_dropped_requests > 0:
        st.warning(
            f"⚠️ **Capacity Ceiling Warning:** Auto-scaling dropped {as_perf.total_dropped_requests:,.0f} requests "
            f"due to max server limits ({current_config.as_max_servers} nodes) or startup delays."
        )
    elif fixed_perf.total_dropped_requests > 0:
        st.info(
            f"💡 **Elasticity Advantage:** Fixed infrastructure dropped {fixed_perf.total_dropped_requests:,.0f} requests, "
            f"while Auto-Scaling sustained 100.0% availability by adding dynamic capacity."
        )

    # KPI Metrics Grid
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Fixed Baseline Cost",
            f"${cost_comp.fixed.total_cost_usd:.2f}",
            f"{fixed_perf.peak_servers} servers static"
        )
    with c2:
        st.metric(
            "Auto-Scaling Cost",
            f"${cost_comp.autoscaling.total_cost_usd:.2f}",
            f"Peak: {as_perf.peak_servers} servers"
        )
    with c3:
        delta_color = "normal" if cost_comp.is_cost_saving else "inverse"
        st.metric(
            "Net Cost Savings",
            cost_comp.savings_percent_display,
            f"${cost_comp.absolute_savings_usd:+.2f}",
            delta_color=delta_color
        )
    with c4:
        st.metric(
            "AS Success Rate",
            f"{as_perf.request_success_rate_pct:.2f}%",
            f"vs Fixed {fixed_perf.request_success_rate_pct:.2f}%"
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("Total Simulated Requests", f"{as_perf.total_incoming_requests:,.0f}")
    with c6:
        st.metric("AS Scaling Events", f"{as_perf.scaling_events_count}", f"{as_perf.scale_out_count} out, {as_perf.scale_in_count} in")
    with c7:
        st.metric("AS SLA Compliance", f"{as_perf.sla_compliance_rate_pct:.1f}%", f"Target < {current_config.sla_target_response_time_ms:.0f}ms")
    with c8:
        st.metric("AS Overload Duration", f"{as_perf.overload_duration_steps} steps", f"vs Fixed {fixed_perf.overload_duration_steps} steps")

    st.markdown("---")

    # High-level Comparative Visual
    col_left, col_right = st.columns(2)
    with col_left:
        # Cost Comparison Bar Chart
        cost_fig = go.Figure()
        cost_fig.add_trace(go.Bar(
            name="Fixed Baseline",
            x=["Infrastructure Cost"],
            y=[cost_comp.fixed.total_cost_usd],
            marker_color="#94a3b8",
            text=[f"${cost_comp.fixed.total_cost_usd:.2f}"],
            textposition="auto"
        ))
        cost_fig.add_trace(go.Bar(
            name="Auto-Scaling",
            x=["Infrastructure Cost"],
            y=[cost_comp.autoscaling.total_cost_usd],
            marker_color="#38bdf8",
            text=[f"${cost_comp.autoscaling.total_cost_usd:.2f}"],
            textposition="auto"
        ))
        apply_plotly_theme(cost_fig, "Total Infrastructure Spending ($)", height=320)
        st.plotly_chart(cost_fig, use_container_width=True)

    with col_right:
        # Request Fulfillment Donut / Stacked Bar
        req_fig = go.Figure()
        req_fig.add_trace(go.Bar(
            name="Processed Requests",
            x=["Fixed Baseline", "Auto-Scaling"],
            y=[fixed_perf.total_processed_requests, as_perf.total_processed_requests],
            marker_color="#34d399"
        ))
        req_fig.add_trace(go.Bar(
            name="Dropped Requests",
            x=["Fixed Baseline", "Auto-Scaling"],
            y=[fixed_perf.total_dropped_requests, as_perf.total_dropped_requests],
            marker_color="#f43f5e"
        ))
        req_fig.update_layout(barmode="stack")
        apply_plotly_theme(req_fig, "Request Fulfillment (Processed vs Dropped)", height=320)
        st.plotly_chart(req_fig, use_container_width=True)


# -------------------------------------------------------------
# TAB 2: LIVE-STYLE SIMULATION
# -------------------------------------------------------------
with tabs[1]:
    st.subheader("Step-by-Step Simulation Scrubber")
    st.caption("Inspect instantaneous load balancer distribution and cluster states at any point in time.")

    step_idx = st.slider(
        "Simulation Time Step (Minute)",
        min_value=0,
        max_value=len(as_df) - 1,
        value=min(int(len(as_df) * 0.45), len(as_df) - 1),
        step=1
    )

    f_row = fixed_df.iloc[step_idx]
    as_row = as_df.iloc[step_idx]

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        st.metric("Step Active Users", f"{int(as_row['users']):,}")
    with sc2:
        st.metric("Incoming Traffic", f"{as_row['incoming_requests']:,.0f} req/min")
    with sc3:
        st.metric("AS Active Servers", f"{int(as_row['active_servers'])}", f"+{int(as_row['provisioning_servers'])} starting")
    with sc4:
        st.metric("AS CPU Utilization", f"{as_row['cpu_utilization_pct']:.1f}%")
    with sc5:
        st.metric("Scaling Action", str(as_row['scaling_action']))

    st.markdown("### 🖥️ Virtual Server Farm State")
    num_active = int(as_row["active_servers"])
    num_prov = int(as_row["provisioning_servers"])
    req_per_srv = as_row["requests_per_active_server"]
    srv_util = as_row["cpu_utilization_pct"]

    # Display simulated cluster nodes
    node_cols = st.columns(min(max(num_active + num_prov, 1), 8))
    for i in range(num_active):
        col_target = node_cols[i % len(node_cols)]
        status_color = "#34d399" if srv_util < current_config.cpu_scale_out_threshold else "#fbbf24"
        if srv_util >= 95.0:
            status_color = "#f43f5e"

        with col_target:
            st.markdown(
                f"""
                <div style="background:#1c2541; border: 2px solid {status_color}; border-radius: 8px; padding: 10px; margin-bottom: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #94a3b8;">NODE-0{i+1}</div>
                    <div style="font-size: 13px; font-weight: 700; color: #f1f5f9;">ONLINE</div>
                    <div style="font-size: 11px; color: #38bdf8;">{req_per_srv:.0f} RPM</div>
                    <div style="font-size: 11px; color: {status_color}; font-weight: 600;">{srv_util:.0f}% CPU</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    for j in range(num_prov):
        col_target = node_cols[(num_active + j) % len(node_cols)]
        with col_target:
            st.markdown(
                f"""
                <div style="background:#1c2541; border: 2px dashed #fbbf24; border-radius: 8px; padding: 10px; margin-bottom: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #94a3b8;">NODE-W{j+1}</div>
                    <div style="font-size: 13px; font-weight: 700; color: #fbbf24;">WARMING UP</div>
                    <div style="font-size: 11px; color: #94a3b8;">Delay active</div>
                    <div style="font-size: 11px; color: #fbbf24;">0 RPM</div>
                </div>
                """,
                unsafe_allow_html=True
            )


# -------------------------------------------------------------
# TAB 3: INFRASTRUCTURE ARCHITECTURE
# -------------------------------------------------------------
with tabs[2]:
    st.subheader("System Architecture & Cloud Mapping")
    st.markdown("Detailed breakdown of simulated infrastructure components and their enterprise cloud equivalents.")

    # Visual Architecture ASCII Flow
    st.markdown(
        """
        ```
        [ Simulated Users / Traffic Generator ]
                        │
                        ▼ (HTTP Requests)
             [ Load Balancer (Equal Distr.) ]
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      [ VM-01 ]     [ VM-02 ]     [ VM-0N ]  (Active Application Server Fleet)
          │             │             │
          └─────────────┬─────────────┘
                        ▼
         [ Aggregate Processing & SLA Engine ]
                        │
                        ▼ (CPU Utilization & Queue Lengths)
        [ CloudWatch-Style Metrics Monitor ]
                        │
                        ▼ (Threshold & Cooldown Rules)
       [ Auto-Scaling Policy Decision Engine ]
                        │
                        ▼ (Spin up / Terminate Nodes)
            [ Cluster Orchestrator ]
        ```
        """
    )

    st.markdown("### Simulated Components vs. Production Cloud Architecture")
    mapping_data = [
        {"Component": "Traffic Generator", "Simulation Logic": "Time-step user count generator with reproducible seed", "Production Equivalent": "Real customer traffic + Load Testing (e.g. k6, Locust)"},
        {"Component": "Load Balancer", "Simulation Logic": "Equal distribution of incoming requests across active nodes", "Production Equivalent": "AWS Application Load Balancer (ALB) / NGINX"},
        {"Component": "Application Servers", "Simulation Logic": "Homogeneous compute nodes with capacity = 1,000 req/min", "Production Equivalent": "Amazon EC2 instances (e.g. t3.medium) or ECS / EKS Pods"},
        {"Component": "Auto-Scaling Policy", "Simulation Logic": "Threshold evaluation (>70% out, <30% in) + Cooldown & Startup Delays", "Production Equivalent": "AWS EC2 Auto Scaling Target Tracking / Step Scaling"},
        {"Component": "Cost Calculation", "Simulation Logic": "Discrete server-hour accrual = (servers × minutes / 60) × hourly rate", "Production Equivalent": "AWS Cost Explorer / FinOps Billing Engine"},
        {"Component": "Telemetry & SLA", "Simulation Logic": "M/M/1 queuing approximation latency modeling + SLA target check", "Production Equivalent": "Amazon CloudWatch, Datadog, Prometheus & OpenTelemetry"},
    ]
    st.table(pd.DataFrame(mapping_data))


# -------------------------------------------------------------
# TAB 4: SCALABILITY ANALYSIS
# -------------------------------------------------------------
with tabs[3]:
    st.subheader("Scalability & Workload Tracking")

    # Chart 1: Traffic vs Active Servers
    fig_scale = go.Figure()
    fig_scale.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["incoming_requests"],
        name="Incoming Requests (RPM)",
        line=dict(color="#64dfdf", width=2),
        yaxis="y1"
    ))
    fig_scale.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["active_servers"],
        name="Auto-Scaling Active Servers",
        line=dict(color="#f59e0b", width=3, shape="hv"),
        yaxis="y2"
    ))
    fig_scale.add_trace(go.Scatter(
        x=fixed_df["time_minutes"],
        y=fixed_df["active_servers"],
        name="Fixed Baseline Servers",
        line=dict(color="#94a3b8", width=2, dash="dash"),
        yaxis="y2"
    ))
    fig_scale.update_layout(
        yaxis=dict(title="Incoming Requests (RPM)", title_font=dict(color="#64dfdf")),
        yaxis2=dict(title="Server Count", title_font=dict(color="#f59e0b"), overlaying="y", side="right")
    )
    apply_plotly_theme(fig_scale, "Traffic Demand vs. Server Count Over Time")
    st.plotly_chart(fig_scale, use_container_width=True)

    # Chart 2: CPU Utilization with Thresholds
    fig_cpu = go.Figure()
    fig_cpu.add_trace(go.Scatter(
        x=fixed_df["time_minutes"],
        y=fixed_df["cpu_utilization_pct"],
        name="Fixed Baseline CPU %",
        line=dict(color="#94a3b8", width=1.5, dash="dot")
    ))
    fig_cpu.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["cpu_utilization_pct"],
        name="Auto-Scaling CPU %",
        line=dict(color="#38bdf8", width=2.5)
    ))
    # Add horizontal threshold lines
    fig_cpu.add_hline(
        y=current_config.cpu_scale_out_threshold,
        line_dash="dash",
        line_color="#f43f5e",
        annotation_text=f"Scale-Out ({current_config.cpu_scale_out_threshold}%)",
        annotation_position="bottom right"
    )
    fig_cpu.add_hline(
        y=current_config.cpu_scale_in_threshold,
        line_dash="dash",
        line_color="#10b981",
        annotation_text=f"Scale-In ({current_config.cpu_scale_in_threshold}%)",
        annotation_position="top right"
    )
    apply_plotly_theme(fig_cpu, "CPU Utilization (%) and Auto-Scaling Thresholds")
    st.plotly_chart(fig_cpu, use_container_width=True)

    # Chart 3: Demand vs Processing Capacity
    fig_cap = go.Figure()
    fig_cap.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["incoming_requests"],
        name="Demand (RPM)",
        fill="tozeroy",
        fillcolor="rgba(100, 223, 223, 0.15)",
        line=dict(color="#64dfdf", width=1.5)
    ))
    fig_cap.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["capacity_rpm"],
        name="Auto-Scaling Capacity (RPM)",
        line=dict(color="#38bdf8", width=2.5)
    ))
    fig_cap.add_trace(go.Scatter(
        x=fixed_df["time_minutes"],
        y=fixed_df["capacity_rpm"],
        name="Fixed Baseline Capacity (RPM)",
        line=dict(color="#94a3b8", width=2, dash="dash")
    ))
    apply_plotly_theme(fig_cap, "Demand vs. Aggregate Processing Capacity (RPM)")
    st.plotly_chart(fig_cap, use_container_width=True)


# -------------------------------------------------------------
# TAB 5: COST OPTIMIZATION
# -------------------------------------------------------------
with tabs[4]:
    st.subheader("Financial & Cost Analytics")

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.metric("Fixed Total Cost", f"${cost_comp.fixed.total_cost_usd:.2f}")
        st.caption(f"Cost per 1k processed: ${cost_comp.fixed.cost_per_1k_processed_requests:.4f}")
    with f_col2:
        st.metric("Auto-Scaling Total Cost", f"${cost_comp.autoscaling.total_cost_usd:.2f}")
        st.caption(f"Cost per 1k processed: ${cost_comp.autoscaling.cost_per_1k_processed_requests:.4f}")
    with f_col3:
        st.metric("Net Financial Savings", cost_comp.savings_percent_display, f"${cost_comp.absolute_savings_usd:.2f}")
        st.caption(cost_comp.summary_verdict)

    # Cumulative Cost Chart
    fig_cum_cost = go.Figure()
    fig_cum_cost.add_trace(go.Scatter(
        x=fixed_df["time_minutes"],
        y=fixed_df["cumulative_cost_usd"],
        name="Fixed Baseline Cumulative Cost ($)",
        line=dict(color="#94a3b8", width=2.5)
    ))
    fig_cum_cost.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["cumulative_cost_usd"],
        name="Auto-Scaling Cumulative Cost ($)",
        line=dict(color="#38bdf8", width=2.5)
    ))
    apply_plotly_theme(fig_cum_cost, "Cumulative Infrastructure Expenditure Over Time ($)")
    st.plotly_chart(fig_cum_cost, use_container_width=True)

    # Step-by-Step Server-Hour Cost
    fig_step_cost = go.Figure()
    fig_step_cost.add_trace(go.Bar(
        x=fixed_df["time_minutes"],
        y=fixed_df["step_cost_usd"],
        name="Fixed Step Cost ($)",
        marker_color="rgba(148, 163, 184, 0.6)"
    ))
    fig_step_cost.add_trace(go.Bar(
        x=as_df["time_minutes"],
        y=as_df["step_cost_usd"],
        name="Auto-Scaling Step Cost ($)",
        marker_color="rgba(56, 189, 248, 0.8)"
    ))
    apply_plotly_theme(fig_step_cost, "Discrete Step-by-Step Expenditure ($)")
    st.plotly_chart(fig_step_cost, use_container_width=True)


# -------------------------------------------------------------
# TAB 6: PERFORMANCE & SLA
# -------------------------------------------------------------
with tabs[5]:
    st.subheader("Performance, Latency & Availability Metrics")

    # Latency Chart
    fig_rt = go.Figure()
    fig_rt.add_trace(go.Scatter(
        x=fixed_df["time_minutes"],
        y=fixed_df["avg_response_time_ms"],
        name="Fixed Avg Latency (ms)",
        line=dict(color="#94a3b8", width=1.5, dash="dot")
    ))
    fig_rt.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["avg_response_time_ms"],
        name="Auto-Scaling Avg Latency (ms)",
        line=dict(color="#64dfdf", width=2.5)
    ))
    fig_rt.add_trace(go.Scatter(
        x=as_df["time_minutes"],
        y=as_df["p95_response_time_ms"],
        name="Auto-Scaling P95 Latency (ms)",
        line=dict(color="#f43f5e", width=1.5, dash="dash")
    ))
    fig_rt.add_hline(
        y=current_config.sla_target_response_time_ms,
        line_dash="dash",
        line_color="#fbbf24",
        annotation_text=f"SLA Target ({current_config.sla_target_response_time_ms} ms)",
        annotation_position="top left"
    )
    apply_plotly_theme(fig_rt, "Estimated Response Times vs. SLA Target (ms)")
    st.plotly_chart(fig_rt, use_container_width=True)

    # Dropped Requests Comparison
    fig_drop = go.Figure()
    fig_drop.add_trace(go.Bar(
        x=fixed_df["time_minutes"],
        y=fixed_df["dropped_requests"],
        name="Fixed Dropped Requests",
        marker_color="#f43f5e"
    ))
    fig_drop.add_trace(go.Bar(
        x=as_df["time_minutes"],
        y=as_df["dropped_requests"],
        name="Auto-Scaling Dropped Requests",
        marker_color="#fbbf24"
    ))
    apply_plotly_theme(fig_drop, "Unserved / Dropped Requests Per Step")
    st.plotly_chart(fig_drop, use_container_width=True)


# -------------------------------------------------------------
# TAB 7: SCENARIO COMPARISON
# -------------------------------------------------------------
with tabs[6]:
    st.subheader("Academic Cross-Scenario Benchmarking")
    st.caption("Side-by-side comparison across all 7 predefined workloads evaluated under identical economic models.")

    if st.button("🚀 Re-calculate All 7 Presets Matrix", key="run_matrix_btn"):
        with st.spinner("Simulating all presets..."):
            all_scenarios_df = run_all_scenarios_comparison()
            st.session_state.all_scenarios_df = all_scenarios_df
    else:
        if "all_scenarios_df" not in st.session_state:
            st.session_state.all_scenarios_df = run_all_scenarios_comparison()

    matrix_df = st.session_state.all_scenarios_df
    st.dataframe(matrix_df, use_container_width=True)

    # Download Scenario Comparison CSV
    csv_matrix = matrix_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Scenario Comparison Matrix (CSV)",
        data=csv_matrix,
        file_name="cloudscale_scenario_benchmarks.csv",
        mime="text/csv"
    )

    # Narrative Analysis of Scenarios
    st.markdown("### Scenario Insights & Architectural Trade-offs")
    for key, p in PREDEFINED_SCENARIOS.items():
        with st.expander(f"📌 {p.name}"):
            st.write(f"**Context:** {p.description}")
            st.write(f"**Outcome:** {p.expected_outcome}")
            st.write(f"**Key Trade-offs:** {p.tradeoffs_and_lessons}")
            st.write(f"**Tuning Guidance:** {p.recommended_tuning}")


# -------------------------------------------------------------
# TAB 8: RECOMMENDATIONS & REPORTS
# -------------------------------------------------------------
with tabs[7]:
    st.subheader("Data-Driven Recommendations & Report Exports")

    st.markdown("### 🔍 Automated Engineering Recommendations")
    for r in comparison.recommendations:
        badge_color = "#38bdf8"
        if r["severity"] == "CRITICAL":
            badge_color = "#f43f5e"
        elif r["severity"] == "WARNING":
            badge_color = "#fbbf24"
        elif r["severity"] == "POSITIVE":
            badge_color = "#34d399"

        st.markdown(
            f"""
            <div style="background:#1c2541; border-left: 4px solid {badge_color}; padding: 12px 16px; margin-bottom: 10px; border-radius: 4px;">
                <span style="background:{badge_color}; color:#0b132b; font-size:11px; font-weight:700; padding:2px 6px; border-radius:4px;">{r['severity']}</span>
                <strong style="color:#f1f5f9; margin-left:8px;">{r['category']}</strong>
                <div style="color:#cbd5e1; font-size:13px; margin-top:4px;">{r['finding']}</div>
                <div style="color:#94a3b8; font-size:12px; font-style:italic; margin-top:2px;"><strong>Actionable Recommendation:</strong> {r['recommendation']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.subheader("📥 Export Case Study Artifacts")

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    # 1. Merged Simulation Data CSV
    merged_csv_str = generate_merged_simulation_csv(fixed_df, as_df)
    with exp_col1:
        st.download_button(
            label="📄 Download Time-Step Data (CSV)",
            data=merged_csv_str.encode('utf-8'),
            file_name="cloudscale_simulation_timestep_data.csv",
            mime="text/csv",
            help="Download time-step by time-step raw telemetry and server calculations."
        )

    # 2. Markdown Academic Report
    md_report = generate_markdown_report(current_config, comparison, scenario_name=preset_names.get(st.session_state.selected_preset_key, "Custom"))
    with exp_col2:
        st.download_button(
            label="📑 Download Case Study Report (Markdown)",
            data=md_report.encode('utf-8'),
            file_name="cloudscale_case_study_report.md",
            mime="text/markdown",
            help="Complete case study write-up with executive summary, tables, and findings."
        )

    # 3. HTML Standalone Report
    html_report = generate_html_report(current_config, comparison, scenario_name=preset_names.get(st.session_state.selected_preset_key, "Custom"))
    with exp_col3:
        st.download_button(
            label="🌐 Download Case Study Report (HTML)",
            data=html_report.encode('utf-8'),
            file_name="cloudscale_case_study_report.html",
            mime="text/html",
            help="Presentation-ready styled HTML report suitable for direct submission or printing."
        )


# -------------------------------------------------------------
# TAB 9: METHODOLOGY & ASSUMPTIONS
# -------------------------------------------------------------
with tabs[8]:
    st.subheader("Methodology, Mathematical Formulas & Disclosures")

    st.markdown(
        r"""
        ### 1. Mathematical Formulas

        **A. Discrete Server Capacity:**  
        $$\text{Capacity}(t) = N_{\text{active}}(t) \times C_{\text{server}}$$
        Where $N_{\text{active}}(t)$ represents active online virtual machines and $C_{\text{server}}$ is throughput capacity (default: 1,000 requests/minute).

        **B. Server Workload Utilization:**  
        $$\rho(t) = \frac{R_{\text{incoming}}(t)}{\text{Capacity}(t)}$$
        CPU utilization displayed is bounded: $\text{CPU}(t) = \min(100\%, \rho(t) \times 100\%)$.

        **C. Horizontal Scaling Hysteresis:**  
        - Scale-Out is triggered if $\text{CPU}(t) > \text{Threshold}_{\text{out}}$ and $(t - t_{\text{last\_out}}) > \text{Cooldown}_{\text{out}}$.  
        - Scale-In is triggered if $\text{CPU}(t) < \text{Threshold}_{\text{in}}$, $(t - t_{\text{last\_in}}) > \text{Cooldown}_{\text{in}}$, and removing nodes does not immediately re-trigger scale-out (anti-flapping dampening).

        **D. Queuing Delay Latency Approximation:**  
        $$\text{RT}(t) = L_0 + \Delta L(\rho)$$
        Base server response latency $L_0 = 35\text{ ms}$. As $\rho \to 1.0$, queues form, and latency climbs. For $\rho \ge 1.0$ (overload), latency rapidly climbs up to timeout (2,500 ms).

        **E. Transparent Cloud Cost Formulation:**  
        $$\text{Cost} = \sum_{t=0}^{T-1} N_{\text{billable}}(t) \times \left(\frac{\Delta t}{60}\right) \times \text{Rate}_{\text{hour}}$$
        Where $N_{\text{billable}}(t) = N_{\text{active}}(t) + N_{\text{provisioning}}(t)$.

        **F. Percentage Cost Savings:**  
        $$\text{Savings (\%)} = \frac{\text{Cost}_{\text{fixed}} - \text{Cost}_{\text{AS}}}{\text{Cost}_{\text{fixed}}} \times 100\%$$
        *(Handles zero baseline cost cleanly; negative savings are reported honestly without distortion).*

        ---

        ### 2. Educational Scope & Limitations
        1. **Simulated Environment:** All figures are computed locally using mathematical discrete-time models. They are not direct measurements from AWS, Google Cloud, or Microsoft Azure.
        2. **Homogeneous Compute Units:** Instances are modeled as identical virtual servers. Real production systems often utilize heterogeneous architectures, spot instances, and container autoscaling (KEDA/HPA).
        3. **Deterministic Reproducibility:** Every simulation is deterministic and reproducible via the configured random seed.
        """
    )
