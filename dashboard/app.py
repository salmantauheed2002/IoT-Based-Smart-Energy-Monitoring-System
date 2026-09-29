#!/usr/bin/env python3
"""
Streamlit Dashboard for Smart Extension Monitor.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.firebase_client import get_client
from src.config import MOCK_MODE


st.set_page_config(
    page_title="Smart Extension Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=15)
def load_data(n: int = 100):
    client = get_client()
    rows = client.get_latest_n(n)
    records = []

    for item in reversed(rows):  # oldest → newest for charts
        key = item["key"]
        data = item["data"]
        try:
            ts = datetime.strptime(key, "%Y%m%d%H%M%S")
        except ValueError:
            continue

        env = data.get("Environment", data.get("Enviornment", {}))  # tolerate typo

        row = {
            "timestamp": ts,
            "key": key,
            "temp": env.get("Temperature"),
            "humidity": env.get("Humidity"),
        }

        for i in range(1, 4):
            s = data.get(f"Sensor{i}", {})
            row[f"s{i}_voltage"] = s.get("Voltage")
            row[f"s{i}_current"] = s.get("Current")
            row[f"s{i}_power"] = s.get("Power")
            row[f"s{i}_energy"] = s.get("Energy")
            row[f"s{i}_pf"] = s.get("PowerFactor")
            row[f"s{i}_freq"] = s.get("Frequency")

        records.append(row)

    return pd.DataFrame(records)


def metric_card(label: str, value, unit: str = "", delta=None):
    st.metric(label=label, value=f"{value}{unit}" if value is not None else "—", delta=delta)


def main():
    st.title("⚡ Smart Extension Monitor")
    st.caption("Multi-channel energy & environment dashboard")

    # Sidebar
    with st.sidebar:
        st.header("Controls")
        n_points = st.slider("History points", 10, 300, 80)
        auto_refresh = st.checkbox("Auto-refresh (15s)", value=True)
        st.markdown("---")
        mode = "🟢 MOCK / LOCAL" if MOCK_MODE else "🔵 LIVE FIREBASE"
        st.info(f"**Mode:** {mode}")
        st.markdown(
            """
            **How to use**
            1. Run the simulator:  
               `python -m simulator.sensor_simulator`
            2. Open this dashboard
            3. Watch live data appear
            """
        )
        if st.button("🔄 Force refresh"):
            st.cache_data.clear()

    df = load_data(n_points)

    if df.empty:
        st.warning(
            "No data yet. Start the simulator in another terminal:\n\n"
            "```bash\npython -m simulator.sensor_simulator\n```"
        )
        st.stop()

    latest = df.iloc[-1]

    # ---------- KPI Row ----------
    st.subheader("Current Readings")
    cols = st.columns(4)

    with cols[0]:
        st.markdown("**Sensor 1**")
        metric_card("Power", f"{latest['s1_power']:.1f}" if pd.notna(latest['s1_power']) else None, " W")
        metric_card("Energy", f"{latest['s1_energy']:.2f}" if pd.notna(latest['s1_energy']) else None, " kWh")

    with cols[1]:
        st.markdown("**Sensor 2**")
        metric_card("Power", f"{latest['s2_power']:.1f}" if pd.notna(latest['s2_power']) else None, " W")
        metric_card("Energy", f"{latest['s2_energy']:.2f}" if pd.notna(latest['s2_energy']) else None, " kWh")

    with cols[2]:
        st.markdown("**Sensor 3**")
        metric_card("Power", f"{latest['s3_power']:.1f}" if pd.notna(latest['s3_power']) else None, " W")
        metric_card("Energy", f"{latest['s3_energy']:.2f}" if pd.notna(latest['s3_energy']) else None, " kWh")

    with cols[3]:
        st.markdown("**Environment**")
        metric_card("Temperature", f"{latest['temp']:.1f}" if pd.notna(latest['temp']) else None, " °C")
        metric_card("Humidity", f"{latest['humidity']:.1f}" if pd.notna(latest['humidity']) else None, " %")

    st.markdown("---")

    # ---------- Power Chart ----------
    st.subheader("Power over Time")
    fig_power = go.Figure()
    for i, color in zip(range(1, 4), ["#636EFA", "#EF553B", "#00CC96"]):
        fig_power.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df[f"s{i}_power"],
                name=f"Sensor {i}",
                mode="lines",
                line=dict(color=color, width=2),
            )
        )
    fig_power.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="Power (W)",
        xaxis_title=None,
    )
    st.plotly_chart(fig_power, use_container_width=True)

    # ---------- Two-column charts ----------
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Voltage")
        fig_v = go.Figure()
        for i in range(1, 4):
            fig_v.add_trace(
                go.Scatter(x=df["timestamp"], y=df[f"s{i}_voltage"], name=f"S{i}", mode="lines")
            )
        fig_v.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="V")
        st.plotly_chart(fig_v, use_container_width=True)

    with c2:
        st.subheader("Environment")
        fig_env = make_subplots(specs=[[{"secondary_y": True}]])
        fig_env.add_trace(
            go.Scatter(x=df["timestamp"], y=df["temp"], name="Temp (°C)", line=dict(color="#FFA15A")),
            secondary_y=False,
        )
        fig_env.add_trace(
            go.Scatter(x=df["timestamp"], y=df["humidity"], name="Humidity (%)", line=dict(color="#19D3F3")),
            secondary_y=True,
        )
        fig_env.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10))
        fig_env.update_yaxes(title_text="°C", secondary_y=False)
        fig_env.update_yaxes(title_text="%", secondary_y=True)
        st.plotly_chart(fig_env, use_container_width=True)

    # ---------- Energy bar ----------
    st.subheader("Cumulative Energy (kWh)")
    energy_vals = [
        latest[f"s{i}_energy"] if pd.notna(latest[f"s{i}_energy"]) else 0
        for i in range(1, 4)
    ]
    fig_e = px.bar(
        x=["Sensor 1", "Sensor 2", "Sensor 3"],
        y=energy_vals,
        labels={"x": "", "y": "kWh"},
        color=["Sensor 1", "Sensor 2", "Sensor 3"],
        color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96"],
    )
    fig_e.update_layout(height=280, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_e, use_container_width=True)

    # ---------- Raw table ----------
    with st.expander("Raw data (latest 20 rows)"):
        st.dataframe(
            df.tail(20).sort_values("timestamp", ascending=False),
            use_container_width=True,
        )

    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(15)
        st.rerun()


if __name__ == "__main__":
    main()