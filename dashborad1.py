import time
import random
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# Configuration & styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Shipment Atmosphere Monitor",
    page_icon="📦",
    layout="wide",
)

# Inject a simple professional theme
CUSTOM_CSS = """
<style>
    .main {
        background-color: #0f172a; /* dark slate */
        color: #e5e7eb;           /* light gray */
        font-family: "Segoe UI", Roboto, sans-serif;
    }
    .stMetric {
        background-color: #111827;
        border-radius: 0.5rem;
        padding: 0.75rem;
        box-shadow: 0 0 10px rgba(15,23,42,0.7);
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
# Initialization of session state
# ---------------------------------------------------------
if "running" not in st.session_state:
    st.session_state.running = False

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=[
            "timestamp",
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
    # VOC ranges can be tuned as you like
    "VOC": {
        "unit": "ppm",
        "bot_min": 0,
        "bot_max": 800,
        "warn_low": None,
        "warn_high": 500,  # example warning threshold
    },
}

# Probability per second that we inject a warning event.
# Roughly yields one warning every ~20 seconds on average,
# but spacing is random.
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

    # If no warning rule, just return the current in-range value
    if warn_low is None and warn_high is None:
        return current_value

    # Decide randomly whether to go low or high if both exist
    if warn_low is not None and warn_high is not None:
        direction = random.choice(["low", "high"])
    elif warn_low is not None:
        direction = "low"
    else:
        direction = "high"

    if direction == "low":
        # Push below lower warning threshold but within bot_min
        new_val = random.uniform(bot_min, warn_low - 0.5)
    else:
        # Push above upper warning threshold but within bot_max
        new_val = random.uniform(warn_high + 0.5, bot_max)

    return new_val


def evaluate_warnings(o2, co2, rh, voc):
    """Return booleans and messages for active warnings."""
    msgs = []

    o2_warn = (o2 < PARAMETERS["O2"]["warn_low"]) or (o2 > PARAMETERS["O2"]["warn_high"])
    if o2_warn:
        msgs.append(f"O₂ outside safe range: {o2:.2f} {PARAMETERS['O2']['unit']}")

    co2_warn = co2 > PARAMETERS["CO2"]["warn_high"]
    if co2_warn:
        msgs.append(f"CO₂ high: {co2:.0f} {PARAMETERS['CO2']['unit']}")

    rh_warn = rh > PARAMETERS["RH"]["warn_high"]
    if rh_warn:
        msgs.append(f"RH high: {rh:.1f} {PARAMETERS['RH']['unit']}")

    voc_warn = voc > PARAMETERS["VOC"]["warn_high"]
    if voc_warn:
        msgs.append(f"VOC high: {voc:.0f} {PARAMETERS['VOC']['unit']}")

    any_warn = o2_warn or co2_warn or rh_warn or voc_warn
    return any_warn, o2_warn, co2_warn, rh_warn, voc_warn, msgs


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
    start_btn = st.button("▶ Start Detector", type="primary")
    stop_btn = st.button("⏹ Stop Tracking")

    if start_btn:
        st.session_state.running = True
    if stop_btn:
        st.session_state.running = False
        st.session_state.warning_active = False
        st.session_state.warning_messages = []

    st.write("Status:", "🟢 RUNNING" if st.session_state.running else "⚪️ IDLE")

with status_col:
    st.markdown('<div class="section-header">Shipment Context</div>', unsafe_allow_html=True)
    st.write("• Mode: Simulation (bot-generated data)")
    st.write("• Use case: Atmosphere monitoring for nut/food shipments")
    st.write("• Sampling interval: 1 second")

# ---------------------------------------------------------
# Data generation loop (single tick per rerun)
# ---------------------------------------------------------
if st.session_state.running:
    # Generate base (normal) readings
    o2 = generate_normal_value("O2")
    n2 = generate_normal_value("N2")
    co2 = generate_normal_value("CO2")
    rh = generate_normal_value("RH")
    voc = generate_normal_value("VOC")

    # Decide whether to inject a warning event for this tick
    if should_inject_warning():
        # Randomly choose 1–2 parameters to disturb
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

    any_warn, o2_warn, co2_warn, rh_warn, voc_warn, msgs = evaluate_warnings(
        o2, co2, rh, voc
    )

    ts = pd.Timestamp.now()

    new_row = {
        "timestamp": ts,
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

    st.session_state.data = pd.concat(
        [st.session_state.data, pd.DataFrame([new_row])],
        ignore_index=True,
    )

    st.session_state.warning_active = any_warn
    st.session_state.warning_messages = msgs
    if any_warn:
        st.session_state.last_warning_ts = ts

    # Sleep a bit so the user sees the refresh; in production you might
    # use streamlit-autorefresh or another pattern.
    time.sleep(1)

# ---------------------------------------------------------
# Warning banner
# ---------------------------------------------------------
if st.session_state.warning_active and st.session_state.warning_messages:
    st.markdown(
        '<div class="warning-banner">⚠ ATMOSPHERE ALERT – Operator Intervention Recommended</div>',
        unsafe_allow_html=True,
    )
    for m in st.session_state.warning_messages:
        st.write("•", m)

# ---------------------------------------------------------
# KPIs row
# ---------------------------------------------------------
if not st.session_state.data.empty:
    latest = st.session_state.data.iloc[-1]

    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    with kpi_col1:
        st.metric(
            label="Oxygen (O₂)",
            value=f"{latest['O2_vol_pct']:.2f} {PARAMETERS['O2']['unit']}",
            delta="WARNING" if latest["O2_warning"] else "",
        )
    with kpi_col2:
        st.metric(
            label="Nitrogen (N₂)",
            value=f"{latest['N2_vol_pct']:.2f} {PARAMETERS['N2']['unit']}",
        )
    with kpi_col3:
        st.metric(
            label="Carbon dioxide (CO₂)",
            value=f"{latest['CO2_ppm']:.0f} {PARAMETERS['CO2']['unit']}",
            delta="HIGH" if latest["CO2_warning"] else "",
        )
    with kpi_col4:
        st.metric(
            label="Relative humidity (RH)",
            value=f"{latest['RH_pct']:.1f} {PARAMETERS['RH']['unit']}",
            delta="HIGH" if latest["RH_warning"] else "",
        )
    with kpi_col5:
        st.metric(
            label="VOC",
            value=f"{latest['VOC_ppm']:.0f} {PARAMETERS['VOC']['unit']}",
            delta="HIGH" if latest["VOC_warning"] else "",
        )

# ---------------------------------------------------------
# Time series charts
# ---------------------------------------------------------
st.markdown('<div class="section-header">Live Trends</div>', unsafe_allow_html=True)

if not st.session_state.data.empty:
    df_plot = st.session_state.data.set_index("timestamp")

    gas_col1, gas_col2 = st.columns(2)

    with gas_col1:
        st.subheader("O₂ and N₂ (vol%)")
        st.line_chart(df_plot[["O2_vol_pct", "N2_vol_pct"]])

    with gas_col2:
        st.subheader("CO₂ & VOC (ppm)")
        st.line_chart(df_plot[["CO2_ppm", "VOC_ppm"]])

    rh_col1, rh_col2 = st.columns([2, 1])

    with rh_col1:
        st.subheader("Relative Humidity (%RH)")
        st.line_chart(df_plot[["RH_pct"]])

    with rh_col2:
        st.subheader("Latest Samples")
        st.dataframe(
            st.session_state.data.tail(20).set_index("timestamp"),
            use_container_width=True,
            height=320,
        )
else:
    st.info("Detector is idle. Click 'Start Detector' to begin simulation.")
