import time
import random

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Shipment Atmosphere Monitor · Purdue Food Science",
    page_icon="📦",
    layout="wide",
)

# ---------------------------------------------------------
# Purdue brand-inspired styling
# ---------------------------------------------------------
# Primary: Boilermaker Gold #CFB991, Black #000000
# Supporting grays from brand guidelines.
BRAND_GOLD = "#CFB991"
BRAND_BLACK = "#000000"
BRAND_DARK_GRAY = "#373A36"
BRAND_GRAY = "#9D9795"
BRAND_STEEL = "#555960"

CUSTOM_CSS = f"""
<style>
    /* Overall background and typography */
    .main {{
        background-color: #f5f5f5;
        color: {BRAND_DARK_GRAY};
        font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    /* Branded header bar */
    .app-header {{
        border-radius: 0.75rem;
        padding: 1.25rem 1.5rem;
        background: linear-gradient(120deg, {BRAND_BLACK}, #1f2933);
        color: #ffffff;
        border: 2px solid {BRAND_GOLD};
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        gap: 1.5rem;
    }}

    .app-header-left {{
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }}

    .app-eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-size: 0.65rem;
        color: {BRAND_GOLD};
    }}

    .app-title {{
        font-size: 1.4rem;
        font-weight: 600;
        margin: 0;
    }}

    .app-subtitle {{
        font-size: 0.9rem;
        color: #e5e7eb;
        margin: 0;
    }}

    .app-header-right {{
        text-align: right;
        font-size: 0.8rem;
        color: #e5e7eb;
    }}

    .app-header-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        background-color: rgba(207, 185, 145, 0.1);
        border: 1px solid {BRAND_GOLD};
        font-size: 0.7rem;
        color: {BRAND_GOLD};
        margin-bottom: 0.3rem;
    }}

    /* Section labels */
    .section-header {{
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: {BRAND_GRAY};
        margin: 1.25rem 0 0.5rem 0;
    }}

    /* Neat cards for controls, context, KPIs */
    .card {{
        background-color: #ffffff;
        border-radius: 0.75rem;
        padding: 0.9rem 1rem;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }}

    .card-heading {{
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
        color: {BRAND_DARK_GRAY};
    }}

    .card-label {{
        font-size: 0.8rem;
        color: {BRAND_GRAY};
    }}

    /* KPI metric cards */
    .stMetric {{
        background-color: #ffffff;
        color: {BRAND_DARK_GRAY};
        border-radius: 0.75rem;
        padding: 0.75rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03);
    }}

    /* Warning banner */
    .warning-banner {{
        padding: 0.75rem 1rem;
        border-radius: 0.75rem;
        background: linear-gradient(90deg, #7f1d1d, #b91c1c);
        color: #fef2f2;
        font-weight: 500;
        border: 1px solid #fecaca;
        margin-top: 1rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    .warning-icon {{
        font-size: 1.2rem;
    }}

    /* Latest samples table wrapper */
    .table-card {{
        background-color: #ffffff;
        border-radius: 0.75rem;
        padding: 0.75rem 0.75rem 0.25rem 0.75rem;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);
    }}

    /* Make Streamlit's native divider subtle */
    hr {{
        border: none;
        border-top: 1px solid #e0e0e0;
        margin: 1.5rem 0 0.75rem 0;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# Multi-detector configuration
# ---------------------------------------------------------
NUM_DETECTORS = 3
DETECTOR_IDS = [f"Detector {i}" for i in range(1, NUM_DETECTORS + 1)]

# ---------------------------------------------------------
# Initialization of session state
# ---------------------------------------------------------
if "detector_running" not in st.session_state:
    st.session_state.detector_running = {
        det_id: False for det_id in DETECTOR_IDS
    }

if "data" not in st.session_state:
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

# Reference start time for relative seconds.
if "t0" not in st.session_state:
    st.session_state.t0 = None

# ---------------------------------------------------------
# Parameter ranges and warning rules
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
    "VOC": {
        "unit": "ppm",
        "bot_min": 0,
        "bot_max": 800,
        "warn_low": None,
        "warn_high": 500,
    },
}

WARNING_PROB_PER_SECOND = 1.0 / 20.0  # Approximately one event every 20 seconds.


def should_inject_warning():
    """Randomly decide whether to inject an abnormal sensor condition."""
    return random.random() < WARNING_PROB_PER_SECOND


def generate_normal_value(param_key):
    """Generate a simulated reading within the configured range."""
    cfg = PARAMETERS[param_key]
    return random.uniform(cfg["bot_min"], cfg["bot_max"])


def generate_warning_value(param_key, current_value):
    """Generate a value that crosses the configured warning threshold."""
    cfg = PARAMETERS[param_key]
    warn_low = cfg["warn_low"]
    warn_high = cfg["warn_high"]
    bot_min = cfg["bot_min"]
    bot_max = cfg["bot_max"]

    if warn_low is None and warn_high is None:
        return current_value

    if warn_low is not None and warn_high is not None:
        direction = random.choice(["low", "high"])
    elif warn_low is not None:
        direction = "low"
    else:
        direction = "high"

    if direction == "low":
        return random.uniform(bot_min, warn_low - 0.5)

    return random.uniform(warn_high + 0.5, bot_max)


def evaluate_warnings(o2, co2, rh, voc):
    """Evaluate readings against alert thresholds and return warning details."""
    msgs = []

    o2_warn = (
        o2 < PARAMETERS["O2"]["warn_low"]
        or o2 > PARAMETERS["O2"]["warn_high"]
    )
    if o2_warn:
        msgs.append(
            f"O₂ outside safe range: {o2:.2f} {PARAMETERS['O2']['unit']} "
            f"(safe {PARAMETERS['O2']['warn_low']:.1f}–"
            f"{PARAMETERS['O2']['warn_high']:.1f} {PARAMETERS['O2']['unit']})"
        )

    co2_warn = co2 > PARAMETERS["CO2"]["warn_high"]
    if co2_warn:
        msgs.append(
            f"CO₂ high: {co2:.0f} {PARAMETERS['CO2']['unit']} "
            f"(warning > {PARAMETERS['CO2']['warn_high']:.0f} "
            f"{PARAMETERS['CO2']['unit']})"
        )

    rh_warn = rh > PARAMETERS["RH"]["warn_high"]
    if rh_warn:
        msgs.append(
            f"RH high: {rh:.1f} {PARAMETERS['RH']['unit']} "
            f"(warning > {PARAMETERS['RH']['warn_high']:.0f} "
            f"{PARAMETERS['RH']['unit']})"
        )

    voc_warn = voc > PARAMETERS["VOC"]["warn_high"]
    if voc_warn:
        msgs.append(
            f"VOC high: {voc:.0f} {PARAMETERS['VOC']['unit']} "
            f"(warning > {PARAMETERS['VOC']['warn_high']:.0f} "
            f"{PARAMETERS['VOC']['unit']})"
        )

    any_warn = o2_warn or co2_warn or rh_warn or voc_warn

    return any_warn, o2_warn, co2_warn, rh_warn, voc_warn, msgs


def multi_series_chart(df, field, title, y_title, palette):
    """
    Create a shared-axis, multi-detector line chart.

    The x-axis is elapsed time in seconds. Each detector is represented
    by a separate colored series.
    """
    return (
        alt.Chart(df)
        .mark_line(point=False)
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
                alt.Tooltip(
                    "seconds_since_start:Q",
                    title="Time (s)",
                    format=".0f",
                ),
                alt.Tooltip("detector_id:N", title="Detector"),
                alt.Tooltip(f"{field}:Q", title=y_title),
            ],
        )
        .properties(title=title, height=260)
    )


# ---------------------------------------------------------
# Branded header
# ---------------------------------------------------------
st.markdown(
    f"""
<div class="app-header">
  <div class="app-header-left">
    <div class="app-eyebrow">Purdue University · Department of Food Science</div>
    <h1 class="app-title">Shipment Atmosphere Monitor</h1>
    <p class="app-subtitle">
      Real-time simulation of O₂, N₂, CO₂, RH, and VOC conditions during food and nut shipments.
    </p>
  </div>

  <div class="app-header-right">
    <div class="app-header-pill">
      <span>●</span><span>Prototype dashboard</span>
    </div>
    <div>Sampling interval: 1 second (simulated)</div>
    <div>Detectors: 3 virtual sensors</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Controls and detector placement
# ---------------------------------------------------------
st.markdown(
    '<div class="section-header">Configuration</div>',
    unsafe_allow_html=True,
)

controls_col, image_col = st.columns([1.2, 1])

with controls_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-heading">Detector control</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="card-label">Start or stop each simulated detector independently.</div>',
        unsafe_allow_html=True,
    )

    for det_id in DETECTOR_IDS:
        start_key = f"start_{det_id}"
        stop_key = f"stop_{det_id}"

        c1, c2, c3 = st.columns([1, 1, 1.2])

        with c1:
            if st.button(
                f"▶ Start {det_id}",
                key=start_key,
                type="primary",
            ):
                st.session_state.detector_running[det_id] = True

                if st.session_state.t0 is None:
                    st.session_state.t0 = pd.Timestamp.now()

        with c2:
            if st.button(f"⏹ Stop {det_id}", key=stop_key):
                st.session_state.detector_running[det_id] = False

        with c3:
            status = (
                "🟢 RUNNING"
                if st.session_state.detector_running[det_id]
                else "⚪️ Idle"
            )
            st.write(f"{det_id}: {status}")

    st.markdown("</div>", unsafe_allow_html=True)

with image_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-heading">Detector placement inside shipment</div>',
        unsafe_allow_html=True,
    )

    st.image(
        "https://raw.githubusercontent.com/akashpatil8888/PurdueShipment/main/image.jpg",
    caption="Approximate placement of the shipment atmosphere detectors.",
    width="stretch",
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------
any_running = any(st.session_state.detector_running.values())

if any_running:
    st_autorefresh(
        interval=1000,
        limit=10**9,
        key="atmosphere_refresh",
    )

# ---------------------------------------------------------
# Data generation
# ---------------------------------------------------------
if any_running:
    ts = pd.Timestamp.now()

    if st.session_state.t0 is None:
        st.session_state.t0 = ts

    new_rows = []
    any_warn_global = False
    msgs_global = []

    for det_id in DETECTOR_IDS:
        if not st.session_state.detector_running[det_id]:
            continue

        o2 = generate_normal_value("O2")
        n2 = generate_normal_value("N2")
        co2 = generate_normal_value("CO2")
        rh = generate_normal_value("RH")
        voc = generate_normal_value("VOC")

        if should_inject_warning():
            params_to_disturb = random.sample(
                ["O2", "CO2", "RH", "VOC"],
                k=random.choice([1, 2]),
            )

            for parameter in params_to_disturb:
                if parameter == "O2":
                    o2 = generate_warning_value("O2", o2)
                elif parameter == "CO2":
                    co2 = generate_warning_value("CO2", co2)
                elif parameter == "RH":
                    rh = generate_warning_value("RH", rh)
                elif parameter == "VOC":
                    voc = generate_warning_value("VOC", voc)

        (
            any_warn,
            o2_warn,
            co2_warn,
            rh_warn,
            voc_warn,
            msgs,
        ) = evaluate_warnings(o2, co2, rh, voc)

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
            msgs_global.extend([f"{det_id}: {message}" for message in msgs])

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
# Warning banner
# ---------------------------------------------------------
if st.session_state.warning_active and st.session_state.warning_messages:
    specific_text = "; ".join(st.session_state.warning_messages)

    st.markdown(
        f"""
<div class="warning-banner">
  <div class="warning-icon">⚠</div>
  <div><strong>Atmosphere alert</strong> – {specific_text}</div>
</div>
""",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Current readings
# ---------------------------------------------------------
st.markdown(
    '<div class="section-header">Current readings</div>',
    unsafe_allow_html=True,
)

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
                value=(
                    f"{latest['O2_vol_pct']:.2f} "
                    f"{PARAMETERS['O2']['unit']}"
                ),
                delta="WARNING" if latest["O2_warning"] else "",
            )

            st.metric(
                label="Nitrogen (N₂)",
                value=(
                    f"{latest['N2_vol_pct']:.2f} "
                    f"{PARAMETERS['N2']['unit']}"
                ),
            )

            st.metric(
                label="Carbon dioxide (CO₂)",
                value=(
                    f"{latest['CO2_ppm']:.0f} "
                    f"{PARAMETERS['CO2']['unit']}"
                ),
                delta="HIGH" if latest["CO2_warning"] else "",
            )

            st.metric(
                label="Relative humidity (RH)",
                value=(
                    f"{latest['RH_pct']:.1f} "
                    f"{PARAMETERS['RH']['unit']}"
                ),
                delta="HIGH" if latest["RH_warning"] else "",
            )

            st.metric(
                label="VOC",
                value=(
                    f"{latest['VOC_ppm']:.0f} "
                    f"{PARAMETERS['VOC']['unit']}"
                ),
                delta="HIGH" if latest["VOC_warning"] else "",
            )
else:
    st.info("All detectors are idle. Start any detector to begin the simulation.")

# ---------------------------------------------------------
# Live trends
# ---------------------------------------------------------
st.markdown(
    '<div class="section-header">Live trends</div>',
    unsafe_allow_html=True,
)

if not st.session_state.data.empty and st.session_state.t0 is not None:
    df_plot = st.session_state.data.copy()
    df_plot["timestamp"] = pd.to_datetime(df_plot["timestamp"])

    df_plot["seconds_since_start"] = (
        df_plot["timestamp"] - st.session_state.t0
    ).dt.total_seconds()

    # Purdue gold, gray, and black provide one color per detector.
    o2_colors = [BRAND_GOLD, BRAND_STEEL, BRAND_BLACK]
    n2_colors = [BRAND_GOLD, BRAND_STEEL, BRAND_BLACK]
    co2_colors = [BRAND_GOLD, BRAND_STEEL, BRAND_BLACK]
    voc_colors = [BRAND_GOLD, BRAND_STEEL, BRAND_BLACK]
    rh_colors = [BRAND_GOLD, BRAND_STEEL, BRAND_BLACK]

    # Row 1: O₂ and N₂
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

    # Row 2: CO₂ and VOC
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

    # Row 3: RH trend and data log
    row3_col1, row3_col2 = st.columns([2, 1])

    with row3_col1:
        chart_rh = multi_series_chart(
            df_plot,
            "RH_pct",
            "Relative humidity (RH)",
            "Relative humidity (%RH)",
            rh_colors,
        )
        st.altair_chart(chart_rh, use_container_width=True)

    with row3_col2:
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown("**Data Log**")

        st.dataframe(
            st.session_state.data.tail(30).set_index(
                ["timestamp", "detector_id"]
            ),
            use_container_width=True,
            height=320,
        )

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("Waiting for data. Start any detector to populate the trend charts.")
