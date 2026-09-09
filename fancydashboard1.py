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
# Purdue + techno styling
# ---------------------------------------------------------
BRAND_GOLD = "#CFB991"
BRAND_BLACK = "#050816"      # deep dark background
BRAND_DARK_GRAY = "#E5E7EB"  # light text on dark
BRAND_GRAY = "#9D9795"
BRAND_STEEL = "#6B7280"

CUSTOM_CSS = f"""
<style>
    /* Global app background + typography */
    html, body, .main {{
        background: radial-gradient(circle at top, #0f172a 0%, #020617 45%, #000000 100%);
        color: {BRAND_DARK_GRAY};
        font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Subtle techno grid overlay */
    .main::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background-image: 
            linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
        background-size: 24px 24px;
        mix-blend-mode: soft-light;
        z-index: -1;
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    /* Techno header bar */
    .app-header {{
        border-radius: 1rem;
        padding: 1.25rem 1.5rem;
        background: linear-gradient(135deg, #020617 0%, #0f172a 40%, #1e293b 100%);
        color: #f9fafb;
        border: 1px solid rgba(148, 163, 184, 0.45);
        box-shadow:
            0 0 0 1px rgba(15, 23, 42, 0.9),
            0 25px 60px rgba(15, 23, 42, 0.9);
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        gap: 1.5rem;
        position: relative;
        overflow: hidden;
    }}

    /* Diagonal light sweep */
    .app-header::after {{
        content: "";
        position: absolute;
        inset: -40%;
        background: radial-gradient(circle at 0% 0%, rgba(34, 211, 238, 0.18), transparent 60%);
        mix-blend-mode: screen;
        pointer-events: none;
        animation: headerSweep 12s linear infinite;
    }}

    @keyframes headerSweep {{
        0% {{ transform: translateX(-20%) translateY(-10%) rotate(15deg); }}
        50% {{ transform: translateX(40%) translateY(20%) rotate(15deg); }}
        100% {{ transform: translateX(110%) translateY(-10%) rotate(15deg); }}
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
        opacity: 0.9;
    }}

    .app-title {{
        font-size: 1.6rem;
        font-weight: 650;
        margin: 0;
        letter-spacing: 0.03em;
    }}

    .app-subtitle {{
        font-size: 0.88rem;
        color: #cbd5f5;
        margin: 0;
        max-width: 36rem;
    }}

    .app-header-right {{
        text-align: right;
        font-size: 0.8rem;
        color: #cbd5f5;
    }}

    .app-header-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.4rem 0.8rem;
        border-radius: 999px;
        background: radial-gradient(circle at 0% 0%, rgba(34, 211, 238, 0.25), transparent 60%);
        border: 1px solid rgba(34, 211, 238, 0.6);
        font-size: 0.72rem;
        color: #e0f2fe;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }}

    .app-header-pill span:first-child {{
        display: inline-block;
        width: 0.55rem;
        height: 0.55rem;
        border-radius: 999px;
        background: radial-gradient(circle at 30% 30%, #22c55e 0%, #16a34a 40%, #0f766e 100%);
        box-shadow: 0 0 12px rgba(34, 197, 94, 0.85);
        animation: pulseDot 1.8s ease-in-out infinite;
    }}

    @keyframes pulseDot {{
        0%, 100% {{ transform: scale(1); opacity: 1; }}
        50% {{ transform: scale(1.3); opacity: 0.75; }}
    }}

    /* Section labels */
    .section-header {{
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #9ca3af;
        margin: 1.4rem 0 0.75rem 0;
        position: relative;
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
    }}

    .section-header::before {{
        content: "";
        width: 16px;
        height: 2px;
        background: linear-gradient(90deg, #22d3ee, #a855f7, #facc15);
        border-radius: 999px;
    }}

    /* Cards: glassy, glowing edges */
    .card, .table-card {{
        background: radial-gradient(circle at top left, rgba(15, 23, 42, 0.9), rgba(3, 7, 18, 0.95));
        border-radius: 0.9rem;
        padding: 0.9rem 1rem;
        border: 1px solid rgba(148, 163, 184, 0.55);
        box-shadow:
            0 0 0 1px rgba(15, 23, 42, 0.8),
            0 20px 45px rgba(15, 23, 42, 0.9);
        backdrop-filter: blur(20px);
    }}

    .table-card {{
        padding: 0.85rem 0.85rem 0.3rem 0.85rem;
    }}

    .card-heading {{
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
        color: #e5e7eb;
    }}

    .card-label {{
        font-size: 0.8rem;
        color: #9ca3af;
    }}

    /* Metric tiles (st.metric wrapper) */
    .stMetric {{
        background: radial-gradient(circle at top, rgba(15, 23, 42, 0.95), rgba(2, 6, 23, 0.98));
        color: #e5e7eb;
        border-radius: 0.85rem;
        padding: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.65);
        box-shadow:
            0 0 0 1px rgba(15, 23, 42, 0.7),
            0 18px 40px rgba(15, 23, 42, 0.9);
    }}

    /* Some Streamlit text classes (may change across versions) */
    .st-emotion-cache-12w0qpk, .st-emotion-cache-1wivap2 {{
        color: #e5e7eb !important;
    }}

    /* Button styling: more techno */
    .stButton > button {{
        background: linear-gradient(120deg, #22d3ee, #a855f7);
        color: #0b1120;
        border-radius: 999px;
        border: 1px solid rgba(148, 163, 184, 0.6);
        padding: 0.35rem 0.9rem;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        box-shadow: 0 10px 25px rgba(56, 189, 248, 0.45);
        transition: transform 0.08s ease-out, box-shadow 0.08s ease-out, filter 0.08s ease-out;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        filter: brightness(1.08);
        box-shadow: 0 16px 32px rgba(129, 140, 248, 0.65);
    }}

    .stButton > button:active {{
        transform: translateY(0px) scale(0.98);
        box-shadow: 0 10px 24px rgba(56, 189, 248, 0.5);
    }}

    /* Warning banner: animated alert strip */
    .warning-banner {{
        padding: 0.75rem 1rem;
        border-radius: 0.85rem;
        background: linear-gradient(90deg, #7f1d1d, #b91c1c, #7f1d1d);
        background-size: 200% 200%;
        color: #fee2e2;
        font-weight: 500;
        border: 1px solid #fecaca;
        margin-top: 1rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        box-shadow:
            0 0 0 1px rgba(127, 29, 29, 0.7),
            0 16px 36px rgba(127, 29, 29, 0.75);
        animation: warningShift 6s linear infinite;
    }}

    @keyframes warningShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    .warning-icon {{
        font-size: 1.25rem;
        filter: drop-shadow(0 0 8px rgba(248, 113, 113, 0.9));
    }}

    /* Divider styling */
    hr {{
        border: none;
        border-top: 1px solid rgba(148, 163, 184, 0.45);
        margin: 1.5rem 0 0.8rem 0;
    }}

    /* Dataframe tweaks for dark theme */
    .table-card .stDataFrame, .table-card [data-testid="stTable"] {{
        color: #e5e7eb;
    }}

    .table-card thead tr th, .table-card tbody tr td {{
        background-color: rgba(15, 23, 42, 0.9) !important;
        border-color: rgba(55, 65, 81, 0.6) !important;
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
# Sidebar controls
# ---------------------------------------------------------
with st.sidebar:
    st.title("Simulation controls")
    st.markdown("Adjust atmosphere simulation parameters and view filters.")

    events_per_minute = st.slider(
        "Warning events per minute (approx.)",
        min_value=1,
        max_value=6,
        value=3,
        help="Controls how often abnormal sensor conditions are injected."
    )

    sampling_interval_ms = st.slider(
        "Sampling interval (ms)",
        min_value=500,
        max_value=3000,
        value=1000,
        step=250,
        help="Controls how often new readings are simulated."
    )

    selected_detectors = st.multiselect(
        "Detectors to display",
        options=DETECTOR_IDS,
        default=DETECTOR_IDS,
    )

    st.markdown("---")
    start_all = st.button("▶ Start all detectors")
    stop_all = st.button("⏹ Stop all detectors")

# ---------------------------------------------------------
# Altair techno theme
# ---------------------------------------------------------
def shipment_techno_theme():
    return {
        "config": {
            "background": "rgba(10, 16, 28, 0.0)",
            "view": {"strokeWidth": 0},
            "axis": {
                "labelColor": "#e5e7eb",
                "titleColor": "#9ca3af",
                "gridColor": "rgba(148, 163, 184, 0.25)",
                "domainColor": "rgba(148, 163, 184, 0.5)",
            },
            "legend": {
                "labelColor": "#e5e7eb",
                "titleColor": "#9ca3af",
            },
            "title": {
                "color": "#e5e7eb",
                "fontSize": 12,
            },
            "line": {"strokeWidth": 2},
        }
    }

alt.themes.register("shipment_techno", shipment_techno_theme)
alt.themes.enable("shipment_techno")

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

# Honor sidebar global controls
if start_all:
    for det_id in DETECTOR_IDS:
        st.session_state.detector_running[det_id] = True
    if st.session_state.t0 is None:
        st.session_state.t0 = pd.Timestamp.now()

if stop_all:
    for det_id in DETECTOR_IDS:
        st.session_state.detector_running[det_id] = False

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

# Use sidebar slider to control warning frequency
WARNING_PROB_PER_SECOND = events_per_minute / 60.0


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
        .mark_line(point=False, strokeWidth=2)
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
        .properties(title=title, height=280)
    )

# ---------------------------------------------------------
# Branded header + status
# ---------------------------------------------------------
any_running = any(st.session_state.detector_running.values())

system_state = "ALERT" if st.session_state.warning_active else (
    "ACTIVE" if any_running else "STANDBY"
)

system_state_icon = "⚠" if system_state == "ALERT" else (
    "🟢" if system_state == "ACTIVE" else "⚪️"
)

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
      <span></span><span>Real-time prototype</span>
    </div>
    <div>{system_state_icon} System state: <strong>{system_state}</strong></div>
    <div>Sampling interval: {sampling_interval_ms} ms · virtual stream</div>
    <div>Detectors online: {sum(st.session_state.detector_running.values())} / {NUM_DETECTORS}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Controls (per-detector) and detector image
# ---------------------------------------------------------
st.markdown(
    '<div class="section-header">Configuration</div>',
    unsafe_allow_html=True,
)

controls_col, image_col = st.columns([1.4, 1])

with controls_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-heading">Per-detector control</div>',
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
            ):
                st.session_state.detector_running[det_id] = True
                if st.session_state.t0 is None:
                    st.session_state.t0 = pd.Timestamp.now()

        with c2:
            if st.button(f"⏹ Stop {det_id}", key=stop_key):
                st.session_state.detector_running[det_id] = False

        with c3:
            status = (
                "🟢 ACTIVE"
                if st.session_state.detector_running[det_id]
                else "⚪️ STANDBY"
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
        use_container_width=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Auto-refresh (uses sidebar sampling interval)
# ---------------------------------------------------------
any_running = any(st.session_state.detector_running.values())

if any_running:
    st_autorefresh(
        interval=sampling_interval_ms,
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
# Current readings (top band KPIs)
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

    # Filter by selected detectors from sidebar
    latest_all = latest_all[
        latest_all["detector_id"].isin(selected_detectors)
    ]

    det_cols = st.columns(max(len(selected_detectors), 1))

    for det_col, det_id in zip(det_cols, selected_detectors):
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
    st.info("All detectors are in STANDBY. Start any detector to begin the simulation.")

# ---------------------------------------------------------
# Live trends (middle band)
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

    # Filter by selected detectors
    df_plot = df_plot[df_plot["detector_id"].isin(selected_detectors)]

    # Neon palettes per detector
    base_palette = ["#22d3ee", "#a855f7", "#facc15"]
    # map detectors to colors deterministically
    color_map = {
        det_id: base_palette[i % len(base_palette)]
        for i, det_id in enumerate(selected_detectors)
    }
    palette = [color_map[det] for det in selected_detectors]

    o2_colors = palette
    n2_colors = palette
    co2_colors = palette
    voc_colors = palette
    rh_colors = palette

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
        st.altair_chart(chart_o2, use_container_width=True, theme=None)

    with row1_col2:
        chart_n2 = multi_series_chart(
            df_plot,
            "N2_vol_pct",
            "Nitrogen (N₂)",
            "Concentration (vol%)",
            n2_colors,
        )
        st.altair_chart(chart_n2, use_container_width=True, theme=None)

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
        st.altair_chart(chart_co2, use_container_width=True, theme=None)

    with row2_col2:
        chart_voc = multi_series_chart(
            df_plot,
            "VOC_ppm",
            "VOC",
            "Concentration (ppm)",
            voc_colors,
        )
        st.altair_chart(chart_voc, use_container_width=True, theme=None)

    # Row 3: RH trend and data log (bottom band)
    row3_col1, row3_col2 = st.columns([2, 1])

    with row3_col1:
        chart_rh = multi_series_chart(
            df_plot,
            "RH_pct",
            "Relative humidity (RH)",
            "Relative humidity (%RH)",
            rh_colors,
        )
        st.altair_chart(chart_rh, use_container_width=True, theme=None)

    with row3_col2:
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown("**Data Log**")

        # Filter log by selected detectors
        log_df = st.session_state.data[
            st.session_state.data["detector_id"].isin(selected_detectors)
        ]

        st.dataframe(
            log_df.tail(30).set_index(
                ["timestamp", "detector_id"]
            ),
            use_container_width=True,
            height=320,
        )

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("Waiting for data. Start any detector to populate the trend charts.")
