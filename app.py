import streamlit as st

st.set_page_config(
    page_title="Chartink Scanner Builder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background: #0d1117 !important; }
    .block-container { padding-top: 1.2rem !important; max-width: 100% !important; }

    [data-testid="stHeader"] { background: #0d1117 !important; }
    [data-testid="stSidebar"] {
        background: #161b22 !important;
        border-right: 1px solid #30363d !important;
    }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #58a6ff !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="stSidebar"] hr { border-color: #30363d !important; margin: 0.8rem 0 !important; }

    h1 { font-size: 1.7rem !important; font-weight: 800 !important; color: #f0f6fc !important; }
    h2 { font-size: 1.05rem !important; font-weight: 700 !important; color: #c9d1d9 !important;
         border-bottom: 1px solid #21262d; padding-bottom: 0.3rem; }
    h3 { font-size: 0.95rem !important; font-weight: 600 !important; color: #8b949e !important; }
    p, .stMarkdown p { color: #8b949e !important; font-size: 0.85rem !important; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: #161b22; padding: 6px 8px;
        border-radius: 10px; border: 1px solid #30363d; margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px; background: transparent; border-radius: 7px;
        padding: 6px 20px; font-size: 0.9rem; font-weight: 600;
        color: #8b949e !important; border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: #1f6feb !important; color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(31,111,235,0.4);
    }

    .stButton button {
        background: #1f6feb !important; color: white !important;
        border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; font-size: 0.85rem !important;
        padding: 6px 16px !important;
    }
    .stButton button:hover {
        background: #388bfd !important;
        box-shadow: 0 4px 12px rgba(31,111,235,0.4) !important;
    }

    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background: #21262d !important; border: 1px solid #30363d !important;
        border-radius: 8px !important; color: #c9d1d9 !important; font-size: 0.88rem !important;
    }
    .stCheckbox label { color: #c9d1d9 !important; font-size: 0.88rem !important; }
    .stSlider [data-baseweb="slider"] { margin-top: 0.2rem; }

    [data-testid="stMetric"] {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 12px 16px;
    }
    [data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.85rem !important; }

    /* Scanner output box */
    .scanner-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px 20px;
        font-family: 'Courier New', monospace;
        font-size: 0.82rem;
        color: #58a6ff;
        line-height: 1.7;
        white-space: pre-wrap;
        word-break: break-all;
    }
    .condition-badge {
        display: inline-block;
        background: #1f6feb22;
        border: 1px solid #1f6feb55;
        border-radius: 5px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        color: #58a6ff;
        margin: 2px;
    }
    .section-card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 1rem;
    }
    hr { border-color: #21262d !important; margin: 0.8rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:1rem;">
    <div style="font-size:1.8rem; font-weight:900; color:#f0f6fc; letter-spacing:-0.03em;">
        🔍 Scanner <span style="color:#1f6feb;">Builder</span>
    </div>
    <div style="background:#3fb95022; border:1px solid #3fb95055; border-radius:6px;
                padding:2px 10px; font-size:0.75rem; font-weight:700; color:#3fb950;">
        CHARTINK
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar: Scanner Selection ──
with st.sidebar:
    st.markdown("### 🧩 Scanner Mode")
    scanner_mode = st.radio(
        "Select Scanner",
        ["Trend Scanner", "Breakout Scanner", "Combined Scanner (Recommended)"],
        index=2
    )

    st.markdown("---")
    st.markdown("### ⚙️ Universe")
    universe = st.selectbox("Stock Universe", ["{33489} - All NSE Stocks", "{34} - F&O Stocks", "{35} - Nifty 500"], index=0)
    universe_code = universe.split(" ")[0]

    st.markdown("---")
    st.markdown("### 🛠️ Trend Filter Settings")

    min_price = st.slider("Min Close Price (₹)", 10, 500, 150, 10)
    min_volume = st.number_input("Min Volume", value=100000, step=10000)
    adx_threshold = st.slider("ADX Threshold", 10, 40, 20, 5)
    rsi_threshold = st.slider("RSI Threshold", 40, 70, 50, 5)

    st.markdown("---")
    st.markdown("### 📈 Breakout Settings")
    breakout_lookback = st.slider("Breakout Lookback (days)", 60, 250, 120, 10)
    breakout_buffer = st.slider("Breakout Buffer (%)", 1.0, 10.0, 5.0, 0.5)

    st.markdown("---")
    st.markdown("### 📅 Consecutive Up Days")
    up_days = st.slider("Consecutive Up Days Filter", 1, 3, 2, 1)

# ── Main Tabs ──
tab1, tab2, tab3 = st.tabs(["📊 Scanner Output", "📖 Conditions Explained", "💡 Usage Guide"])

# ── Helper to build scanners ──
def build_trend_scanner(universe_code, min_price, min_volume, adx_threshold, rsi_threshold, up_days):
    conditions = [
        "daily ema ( close,5 ) >  daily sma ( close,20 )",
        "daily wma ( close,10 ) >  daily sma ( close,20 )",
        f"daily adx di positive ( 14 ) >  {adx_threshold}",
        f"daily adx ( 14 ) >  {adx_threshold}",
        f"daily volume >  {int(min_volume)}",
        "daily macd line ( 26,12,9 ) >  0",
        "daily close >  1 day ago close",
        "daily close >  daily sma ( close,50 )",
        f"daily close >  {min_price}",
        "daily adx di positive ( 14 ) >  daily adx di negative ( 14 )",
        f"daily rsi ( 14 ) >  {rsi_threshold}",
        "daily macd line ( 26,12,9 ) >  daily macd signal ( 26,12,9 )",
        "daily sma ( close,20 ) >  daily sma ( close,40 )",
    ]
    if up_days >= 2:
        conditions.append("daily close >  2 days ago close")
    if up_days >= 3:
        conditions.append("daily close >  3 days ago close")
    return conditions

def build_breakout_scanner(universe_code, breakout_lookback, breakout_buffer, min_volume):
    buf = 1 + breakout_buffer / 100
    conditions = [
        f"daily max ( 5 ,  daily close ) >  6 days ago max ( {breakout_lookback} ,  daily close ) *  {buf}",
        "daily volume >  daily sma ( volume,5 )",
        "daily close >  1 day ago close",
    ]
    return conditions

def format_scanner(universe_code, conditions):
    joined = "\nand  ".join(conditions)
    return f"( {universe_code} (\n  {joined}\n) )"

# ── Build based on mode ──
trend_conditions    = build_trend_scanner(universe_code, min_price, min_volume, adx_threshold, rsi_threshold, up_days)
breakout_conditions = build_breakout_scanner(universe_code, breakout_lookback, breakout_buffer, min_volume)

if scanner_mode == "Trend Scanner":
    final_conditions = trend_conditions
    title = "Trend Confirmation Scanner"
    color = "#58a6ff"
elif scanner_mode == "Breakout Scanner":
    final_conditions = breakout_conditions
    title = "Breakout Detection Scanner"
    color = "#3fb950"
else:
    final_conditions = trend_conditions + breakout_conditions[:-1]  # avoid duplicate close>1d
    title = "Combined Trend + Breakout Scanner"
    color = "#f0883e"

scanner_output = format_scanner(universe_code, final_conditions)

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 Total Conditions", len(final_conditions))
    with col2:
        st.metric("🎯 Scanner Type", scanner_mode.split(" ")[0])
    with col3:
        st.metric("📦 Universe", universe_code)

    st.markdown(f"""
    <div style="margin: 0.5rem 0 0.8rem;">
        <span style="font-size:1rem; font-weight:700; color:{color};">{title}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="scanner-box">{scanner_output}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👆 Copy the above code and paste it directly into Chartink Scanner → Formula box.")

    with st.expander("📋 Individual Conditions List"):
        for i, cond in enumerate(final_conditions, 1):
            st.markdown(f"**{i}.** `{cond}`")

with tab2:
    if scanner_mode in ["Trend Scanner", "Combined Scanner (Recommended)"]:
        st.markdown("## 📈 Trend Filter Conditions")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        trend_explanations = {
            "EMA(5) > SMA(20)": "Short-term average ऊपर है medium-term से — bullish momentum active hai",
            "WMA(10) > SMA(20)": "Weighted average bhi confirm kar raha hai upward pressure",
            f"ADX > {adx_threshold}": "Trend strong hai, sideways/choppy nahi — minimum strength confirm",
            f"ADX +DI > {adx_threshold}": "Bullish directional movement significant level pe hai",
            "ADX +DI > ADX -DI": "Bulls bears se zyada strong hain is waqt",
            f"RSI(14) > {rsi_threshold}": "Momentum positive zone mein hai (neutral midpoint ke upar)",
            "MACD Line > 0": "Overall bullish territory mein hai stock",
            "MACD Line > Signal": "MACD bullish crossover — fresh momentum signal",
            "Close > SMA(50)": "Price medium-term average ke upar — trend intact",
            "SMA(20) > SMA(40)": "Medium-term trend rising — healthy uptrend structure",
            f"Close > ₹{min_price}": "Penny stocks filter out — only quality stocks",
            f"Volume > {int(min_volume):,}": "Enough liquidity confirm — thinly traded stocks out",
            "Close > 1 day ago": "Kal bhi stock badha tha — momentum fresh hai",
        }
        if up_days >= 2:
            trend_explanations["Close > 2 days ago"] = "2 consecutive up days — sustained buying pressure"
        if up_days >= 3:
            trend_explanations["Close > 3 days ago"] = "3 consecutive up days — very strong momentum"

        for cond, exp in trend_explanations.items():
            st.markdown(f"""
            <div style="padding: 6px 0; border-bottom: 1px solid #21262d;">
                <span class="condition-badge">{cond}</span>
                <span style="color:#8b949e; font-size:0.83rem; margin-left:8px;">{exp}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if scanner_mode in ["Breakout Scanner", "Combined Scanner (Recommended)"]:
        st.markdown("## 🚀 Breakout Filter Conditions")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        breakout_explanations = {
            f"5-day high > {breakout_lookback}-day high × {1 + breakout_buffer/100:.2f}":
                f"Stock ne apni {breakout_lookback}-din ki high ko {breakout_buffer}% se tod diya — genuine breakout!",
            "Volume > 5-day Avg Volume":
                "Breakout ke saath volume bhi badha — institutional participation confirm",
            "Close > 1 day ago close":
                "Aaj ka close positive — momentum continue hai",
        }
        for cond, exp in breakout_explanations.items():
            st.markdown(f"""
            <div style="padding: 6px 0; border-bottom: 1px solid #21262d;">
                <span class="condition-badge">{cond}</span>
                <span style="color:#8b949e; font-size:0.83rem; margin-left:8px;">{exp}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("## ⏰ Kab Run Karein?")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        steps = [
            ("3:30 PM ke baad", "Market close hone ke baad run karo — fully formed candles"),
            ("Results review karo", "5-10 stocks shortlist karo jo scan mein aaye"),
            ("Chart manually check karo", "Volume, pattern, support confirm karo"),
            ("Entry set karo", "Stop-loss aur target next day ke liye ready rakho"),
            ("9:15 AM execute", "Agle din flat/slight gap-up pe hi enter karo"),
        ]
        for i, (step, desc) in enumerate(steps, 1):
            st.markdown(f"""
            <div style="display:flex; gap:12px; padding:8px 0; border-bottom:1px solid #21262d;">
                <div style="min-width:24px; height:24px; background:#1f6feb; border-radius:50%;
                            display:flex; align-items:center; justify-content:center;
                            font-size:0.75rem; font-weight:700; color:white;">{i}</div>
                <div>
                    <div style="color:#c9d1d9; font-weight:600; font-size:0.85rem;">{step}</div>
                    <div style="color:#6e7681; font-size:0.78rem;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown("## ⚠️ Kab Ignore Karein?")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        warnings = [
            ("Market hours mein", "❌", "Incomplete candles = false signals"),
            ("Expiry day (Thu)", "⚠️", "F&O volatility distort karta hai signals"),
            ("Budget / Big news day", "⚠️", "Fundamentals override karte hain technicals"),
            ("Gap-up open pe entry", "❌", "Risk-reward kharab ho jaata hai"),
            ("Sideways market mein", "⚠️", "Trend scanners weak market mein false signals dete hain"),
        ]
        for situation, icon, reason in warnings:
            color = "#f85149" if icon == "❌" else "#d29922"
            st.markdown(f"""
            <div style="display:flex; gap:10px; padding:8px 0; border-bottom:1px solid #21262d; align-items:start;">
                <div style="font-size:1rem;">{icon}</div>
                <div>
                    <div style="color:{color}; font-weight:600; font-size:0.85rem;">{situation}</div>
                    <div style="color:#6e7681; font-size:0.78rem;">{reason}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("## 💡 Pro Tips")
    tips = [
        ("Combined scanner use karo", "Dono scanners ke results mein jo common stocks hain — wo highest conviction trades hain"),
        ("Gap-up avoid karo", "Agar stock bahut zyada gap-up kare to wait karo — risk-reward bigad jaata hai"),
        ("Thursday caution", "F&O expiry pe signals reliable nahi hote — better to sit out"),
        ("Volume confirm karo", "Scanner results ke baad manually dekho ki volume breakout ke saath aya ya nahi"),
    ]
    cols = st.columns(2)
    for i, (tip_title, tip_desc) in enumerate(tips):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="section-card" style="margin-bottom:0.5rem;">
                <div style="color:#f0883e; font-weight:700; font-size:0.88rem; margin-bottom:4px;">💡 {tip_title}</div>
                <div style="color:#8b949e; font-size:0.82rem;">{tip_desc}</div>
            </div>
            """, unsafe_allow_html=True)
