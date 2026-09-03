import time
import random
import pandas as pd
import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# Configuration & styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Shipment Atmosphere Monitor",
    page_icon="📦",
    layout="wide",
)

CUSTOM_CSS = """
<style>
    .main {
        background-color: #0f172a; /* dark slate background */
        color: #e5e7eb;           /* light text for general content */
        font-family: "Segoe UI", Roboto, sans-serif;
    }
    /* KPI metric cards: grey background, black text */
    .stMetric {
        background-color: #e5e7eb;  /* light grey card background */
        color: #111827;             /* dark text inside the card */
        border-radius: 0.5rem;
        padding: 0.75rem;
        box-shadow: 0 0 10px rgba(15,23,42,0.3);
    }
    .warning-banner {
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        background: linear-gradient(90deg, #b91c1c, #f97316);
        color: #f9fafb;
        font-weight: 600;
        border: 1px solid #fecaca;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(248,113,113,0.7); }
        70% { box-shadow: 0 0 0 12px rgba(248,113,113,0); }
        100% { box-shadow: 0 0 0 0 rgba(248,113,113,0); }
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# Multi-detector config
# ---------------------------------------------------------
NUM_DETECTORS = 3
DETECTOR_IDS = [f"Detector {i}" for i in range(1, NUM_DETECTORS + 1)]

# ---------------------------------------------------------
# Initialization of session state
# ---------------------------------------------------------
if "detector_running" not in st.session_state:
    # one running flag per detector
    st.session_state.detector_running = {det_id: False for det_id in DETECTOR_IDS}

if "data" not in st.session_state:
    # one row per detector per timestamp
    st.session_state.data = pd.DataFrame(
        columns=[
            "timestamp",
            "detector_id",
            "O2_vol_pct",
            "N2_vol_pct",
            "CO2_ppm",
            "RH_pct",
            "VOC_ppm",
            "O2_warning",
            "CO2_warning",
            "RH_warning",
            "VOC_warning",
        ]
    )

if "last_warning_ts" not in st.session_state:
    st.session_state.last_warning_ts = None

if "warning_active" not in st.session_state:
    st.session_state.warning_active = False

if "warning_messages" not in st.session_state:
    st.session_state.warning_messages = []

# store the reference start time for relative seconds
if "t0" not in st.session_state:
    st.session_state.t0 = None

# ---------------------------------------------------------
# Parameter ranges & warning rules
# ---------------------------------------------------------
PARAMETERS = {
    "O2": {
        "unit": "vol%",
        "bot_min": 15.0,
        "bot_max": 25.0,
        "warn_low": 19.5,
        "warn_high": 22.0,
    },
    "N2": {
        "unit": "vol%",
        "bot_min": 78.0,
        "bot_max": 79.5,
        "warn_low": None,
        "warn_high": None,
    },
    "CO2": {
        "unit": "ppm",
        "bot_min": 400,
        "bot_max": 7000,
        "warn_low": None,
        "warn_high": 5000,
    },
    "RH": {
        "unit": "%RH",
        "bot_min": 30,
        "bot_max": 90,
        "warn_low": None,
        "warn_high": 70,
    },
    # VOC ranges can be tuned as needed
    "VOC": {
        "unit": "ppm",
        "bot_min": 0,
        "bot_max": 800,
        "warn_low": None,
        "warn_high": 500,  # example warning threshold
    },
}

# Warning probability: ~1 event per 20 seconds, random spacing
WARNING_PROB_PER_SECOND = 1.0 / 20.0


def should_inject_warning():
    """Randomly decide whether to inject a warning event this tick."""
    return random.random() < WARNING_PROB_PER_SECOND


def generate_normal_value(param_key):
    """Generate a normal in-range value for a parameter."""
    cfg = PARAMETERS[param_key]
    return random.uniform(cfg["bot_min"], cfg["bot_max"])


def generate_warning_value(param_key, current_value):
    """
    Generate an out-of-range value for a parameter
    that will trigger the warning logic.
    """
    cfg = PARAMETERS[param_key]
    warn_low = cfg["warn_low"]
    warn_high = cfg["warn_high"]
    bot_min = cfg["bot_min"]
    bot_max = cfg["bot_max"]

    if warn_low is None and warn_high is None:
        # No warning rule defined; keep value
        return current_value

    if warn_low is not None and warn_high is not None:
        direction = random.choice(["low", "high"])
    elif warn_low is not None:
        direction = "low"
    else:
        direction = "high"

    if direction == "low":
        new_val = random.uniform(bot_min, warn_low - 0.5)
    else:
        new_val = random.uniform(warn_high + 0.5, bot_max)

    return new_val


def evaluate_warnings(o2, co2, rh, voc):
    """Return booleans and messages for active warnings."""
    msgs = []

    o2_warn = (o2 < PARAMETERS["O2"]["warn_low"]) or (o2 > PARAMETERS["O2"]["warn_high"])
    if o2_warn:
        msgs.append(
            f"O₂ outside safe range: {o2:.2f} {PARAMETERS['O2']['unit']} "
            f"(safe {PARAMETERS['O2']['warn_low']:.1f}–{PARAMETERS['O2']['warn_high']:.1f} {PARAMETERS['O2']['unit']})"
        )

    co2_warn = co2 > PARAMETERS["CO2"]["warn_high"]
    if co2_warn:
        msgs.append(
            f"CO₂ high: {co2:.0f} {PARAMETERS['CO2']['unit']} "
            f"(warning > {PARAMETERS['CO2']['warn_high']:.0f} {PARAMETERS['CO2']['unit']})"
        )

    rh_warn = rh > PARAMETERS["RH"]["warn_high"]
    if rh_warn:
        msgs.append(
            f"RH high: {rh:.1f} {PARAMETERS['RH']['unit']} "
            f"(warning > {PARAMETERS['RH']['warn_high']:.0f} {PARAMETERS['RH']['unit']})"
        )

    voc_warn = voc > PARAMETERS["VOC"]["warn_high"]
    if voc_warn:
        msgs.append(
            f"VOC high: {voc:.0f} {PARAMETERS['VOC']['unit']} "
            f"(warning > {PARAMETERS['VOC']['warn_high']:.0f} {PARAMETERS['VOC']['unit']})"
        )

    any_warn = o2_warn or co2_warn or rh_warn or voc_warn
    return any_warn, o2_warn, co2_warn, rh_warn, voc_warn, msgs


def multi_series_chart(df, field, title, y_title, palette):
    """
    Multi-detector line chart on shared axes (color = detector_id),
    x-axis is seconds since start (numeric).
    """
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X(
                "seconds_since_start:Q",
                title="Time since start (s)",
                axis=alt.Axis(format=".0f"),
            ),
            y=alt.Y(f"{field}:Q", title=y_title),
            color=alt.Color(
                "detector_id:N",
                title="Detector",
                scale=alt.Scale(range=palette),
            ),
            tooltip=[
                "seconds_since_start:Q",
                "detector_id:N",
                f"{field}:Q",
            ],
        )
        .properties(title=title, height=250)
    )

# ---------------------------------------------------------
# Layout: header & controls
# ---------------------------------------------------------
st.title("Shipment Atmosphere Monitor")
st.caption(
    "Real-time simulation of detector readings for O₂, N₂, CO₂, RH, and VOC "
    "during food/nut shipment."
)

controls_col, status_col = st.columns([1, 2])

with controls_col:
    st.markdown('<div class="section-header">Detector Control</div>', unsafe_allow_html=True)

    # One row of buttons per detector
    for det_id in DETECTOR_IDS:
        start_key = f"start_{det_id}"
        stop_key = f"stop_{det_id}"

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button(f"▶ Start {det_id}", key=start_key, type="primary"):
                st.session_state.detector_running[det_id] = True
                # set t0 on first start if not set
                if st.session_state.t0 is None:
                    st.session_state.t0 = pd.Timestamp.now()
        with c2:
            if st.button(f"⏹ Stop {det_id}", key=stop_key):
                st.session_state.detector_running[det_id] = False
        with c3:
            status = "🟢 RUNNING" if st.session_state.detector_running[det_id] else "⚪️ IDLE"
            st.write(status)

with status_col:
    st.markdown('<div class="section-header">Shipment Context</div>', unsafe_allow_html=True)
    st.write("• Mode: Simulation (bot-generated data)")
    st.write("• Use case: Atmosphere monitoring for nut/food shipments")
    st.write("• Sampling interval: 1 second (bot tick)")

# ---------------------------------------------------------
# Auto-refresh: keep app rerunning every 1s while any detector is running
# ---------------------------------------------------------
any_running = any(st.session_state.detector_running.values())
if any_running:
    st_autorefresh(interval=1000, limit=10**9, key="atmosphere_refresh")

# ---------------------------------------------------------
# Data generation tick – for all running detectors
# Detector keeps tracking even during warnings
# ---------------------------------------------------------
if any_running:
    ts = pd.Timestamp.now()
    # ensure t0 is set if user started detectors before this tick
    if st.session_state.t0 is None:
        st.session_state.t0 = ts

    new_rows = []
    any_warn_global = False
    msgs_global = []

    for det_id in DETECTOR_IDS:
        if not st.session_state.detector_running[det_id]:
            continue  # this detector is stopped

        # Generate base (normal) readings
        o2 = generate_normal_value("O2")
        n2 = generate_normal_value("N2")
        co2 = generate_normal_value("CO2")
        rh = generate_normal_value("RH")
        voc = generate_normal_value("VOC")

        # Randomly inject a warning event (1–2 parameters disturbed)
        if should_inject_warning():
            params_to_disturb = random.sample(
                ["O2", "CO2", "RH", "VOC"],
                k=random.choice([1, 2]),
            )
            for p in params_to_disturb:
                if p == "O2":
                    o2 = generate_warning_value("O2", o2)
                elif p == "CO2":
                    co2 = generate_warning_value("CO2", co2)
                elif p == "RH":
                    rh = generate_warning_value("RH", rh)
                elif p == "VOC":
                    voc = generate_warning_value("VOC", voc)

        # Evaluate warnings – detector continues tracking regardless
        any_warn, o2_warn, co2_warn, rh_warn, voc_warn, msgs = evaluate_warnings(
            o2, co2, rh, voc
        )

        new_rows.append(
            {
                "timestamp": ts,
                "detector_id": det_id,
                "O2_vol_pct": o2,
                "N2_vol_pct": n2,
                "CO2_ppm": co2,
                "RH_pct": rh,
                "VOC_ppm": voc,
                "O2_warning": o2_warn,
                "CO2_warning": co2_warn,
                "RH_warning": rh_warn,
                "VOC_warning": voc_warn,
            }
        )

        if any_warn:
            any_warn_global = True
            msgs_global.extend([f"{det_id}: {m}" for m in msgs])

    if new_rows:
        st.session_state.data = pd.concat(
            [st.session_state.data, pd.DataFrame(new_rows)],
            ignore_index=True,
        )

    st.session_state.warning_active = any_warn_global
    st.session_state.warning_messages = msgs_global
    if any_warn_global:
        st.session_state.last_warning_ts = ts

# ---------------------------------------------------------
# Warning banner – specific gas failures (does NOT stop data)
# ---------------------------------------------------------
if st.session_state.warning_active and st.session_state.warning_messages:
    specific_text = "; ".join(st.session_state.warning_messages)
    st.markdown(
        f'<div class="warning-banner">⚠ ATMOSPHERE ALERT – {specific_text}</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# KPIs row – per detector (grey cards, black text via CSS)
# ---------------------------------------------------------
if not st.session_state.data.empty:
    latest_ts = st.session_state.data["timestamp"].max()
    latest_all = st.session_state.data[
        st.session_state.data["timestamp"] == latest_ts
    ]

    det_cols = st.columns(NUM_DETECTORS)

    for det_col, det_id in zip(det_cols, DETECTOR_IDS):
        det_latest = latest_all[latest_all["detector_id"] == det_id]
        if det_latest.empty:
            continue
        latest = det_latest.iloc[-1]

        with det_col:
            st.markdown(f"**{det_id}**")
            st.metric(
                label="Oxygen (O₂)",
                value=f"{latest['O2_vol_pct']:.2f} {PARAMETERS['O2']['unit']}",
                delta="WARNING" if latest["O2_warning"] else "",
            )
            st.metric(
                label="Nitrogen (N₂)",
                value=f"{latest['N2_vol_pct']:.2f} {PARAMETERS['N2']['unit']}",
            )
            st.metric(
                label="Carbon dioxide (CO₂)",
                value=f"{latest['CO2_ppm']:.0f} {PARAMETERS['CO2']['unit']}",
                delta="HIGH" if latest["CO2_warning"] else "",
            )
            st.metric(
                label="Relative humidity (RH)",
                value=f"{latest['RH_pct']:.1f} {PARAMETERS['RH']['unit']}",
                delta="HIGH" if latest["RH_warning"] else "",
            )
            st.metric(
                label="VOC",
                value=f"{latest['VOC_ppm']:.0f} {PARAMETERS['VOC']['unit']}",
                delta="HIGH" if latest["VOC_warning"] else "",
            )

# ---------------------------------------------------------
# Time series charts – separate graphs per parameter,
# multiple detectors overlaid per graph (x = seconds since start)
# ---------------------------------------------------------
st.markdown('<div class="section-header">Live Trends</div>', unsafe_allow_html=True)

if not st.session_state.data.empty and st.session_state.t0 is not None:
    df_plot = st.session_state.data.copy()
    df_plot["timestamp"] = pd.to_datetime(df_plot["timestamp"])

    # compute seconds since start as a float column
    df_plot["seconds_since_start"] = (
        (df_plot["timestamp"] - st.session_state.t0).dt.total_seconds()
    )

    # Color palettes per parameter (3 detectors)
    o2_colors = ["#22c55e", "#4ade80", "#16a34a"]
    n2_colors = ["#3b82f6", "#60a5fa", "#1d4ed8"]
    co2_colors = ["#f97316", "#fdba74", "#c2410c"]
    voc_colors = ["#a855f7", "#c4b5fd", "#7c3aed"]
    rh_colors = ["#38bdf8", "#7dd3fc", "#0ea5e9"]

    # Row 1: O2, N2
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        chart_o2 = multi_series_chart(
            df_plot,
            "O2_vol_pct",
            "Oxygen (O₂)",
            "Concentration (vol%)",
            o2_colors,
        )
        st.altair_chart(chart_o2, use_container_width=True)

    with row1_col2:
        chart_n2 = multi_series_chart(
            df_plot,
            "N2_vol_pct",
            "Nitrogen (N₂)",
            "Concentration (vol%)",
            n2_colors,
        )
        st.altair_chart(chart_n2, use_container_width=True)

    # Row 2: CO2, VOC
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        chart_co2 = multi_series_chart(
            df_plot,
            "CO2_ppm",
            "Carbon dioxide (CO₂)",
            "Concentration (ppm)",
            co2_colors,
        )
        st.altair_chart(chart_co2, use_container_width=True)

    with row2_col2:
        chart_voc = multi_series_chart(
            df_plot,
            "VOC_ppm",
            "VOC",
            "Concentration (ppm)",
            voc_colors,
        )
        st.altair_chart(chart_voc, use_container_width=True)

    # Row 3: RH + recent samples
    row3_col1, row3_col2 = st.columns([2, 1])
    with row3_col1:
        chart_rh = multi_series_chart(
            df_plot,
            "RH_pct",
            "Relative humidity (RH)",
            "Relative Humidity (%RH)",
            rh_colors,
        )
        st.altair_chart(chart_rh, use_container_width=True)

    with row3_col2:
        st.subheader("Latest Samples")
        st.dataframe(
            st.session_state.data.tail(30).set_index(["timestamp", "detector_id"]),
            use_container_width=True,
            height=320,
        )
else:
    st.info("All detectors are idle. Click the start button for any detector to begin simulation.")
