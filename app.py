import streamlit as st
import pandas as pd
import requests
import numpy as np
import json
import os
import time
from datetime import datetime, timedelta, timezone

# ── IST ──
IST = timezone(timedelta(hours=5, minutes=30))
def get_ist_now():
    return datetime.now(IST)

st.set_page_config(
    page_title="Stock Scanner Pro",
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
    [data-testid="stSidebar"] { background: #161b22 !important; border-right: 1px solid #30363d !important; }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #58a6ff !important; font-size: 0.85rem !important;
        text-transform: uppercase; letter-spacing: 0.08em;
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
        font-weight: 600 !important; font-size: 0.85rem !important; padding: 6px 16px !important;
    }
    .stButton button:hover { background: #388bfd !important; box-shadow: 0 4px 12px rgba(31,111,235,0.4) !important; }
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background: #21262d !important; border: 1px solid #30363d !important;
        border-radius: 8px !important; color: #c9d1d9 !important; font-size: 0.88rem !important;
    }
    .stCheckbox label { color: #c9d1d9 !important; font-size: 0.88rem !important; }
    [data-testid="stMetric"] {
        background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 12px 16px;
    }
    [data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.85rem !important; }
    div[data-testid="stDataFrame"] { border-radius: 10px !important; border: 1px solid #21262d !important; overflow: hidden; }
    hr { border-color: #21262d !important; margin: 0.8rem 0 !important; }
    .stSpinner > div { border-top-color: #1f6feb !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──
DATA_DIR = "data"
TOKEN_FILE = os.path.join(DATA_DIR, "token.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ── F&O Stock List ──
STOCK_LIST = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN","BAJFINANCE",
    "BHARTIARTL","KOTAKBANK","LT","HCLTECH","AXISBANK","ASIANPAINT","MARUTI",
    "SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","POWERGRID","NTPC","TECHM","ONGC",
    "JSWSTEEL","TATAMOTORS","ADANIENT","ADANIPORTS","COALINDIA","BAJAJFINSV",
    "DRREDDY","CIPLA","DIVISLAB","EICHERMOT","HEROMOTOCO","HINDALCO","INDUSINDBK",
    "ITC","M&M","SBILIFE","TATACONSUM","TATASTEEL","UPL","VEDL","BPCL","IOC",
    "GAIL","BRITANNIA","HAVELLS","PIDILITIND","BERGEPAINT","MUTHOOTFIN","CHOLAFIN",
    "NAUKRI","DMART","ZOMATO","ABBOTINDIA","ACC","AFFLE","ALKEM","APLLTD",
    "APOLLOHOSP","APOLLOTYRE","AUROPHARMA","BANDHANBNK","BANKBARODA","BEL","BHEL",
    "BIOCON","BOSCHLTD","CANBK","CANFINHOME","COFORGE","CONCOR","CUMMINSIND",
    "DABUR","DEEPAKNTR","DLF","ESCORTS","FEDERALBNK","GLENMARK","GMRINFRA",
    "GODREJCP","GODREJPROP","GRANULES","GUJGASLTD","HAL","HINDCOPPER","HINDPETRO",
    "ICICIGI","ICICIPRULI","IDFCFIRSTB","IEX","IGL","INDUSTOWER","IRCTC",
    "JINDALSTEL","JUBLFOOD","KAJARIACER","KPITTECH","LTIM","LTTS","LUPIN",
    "MARICO","MCX","MANAPPURAM","MOTHERSON","MRF","NATIONALUM","NAVINFLUOR",
    "NMDC","OBEROIRLTY","OFSS","PAGEIND","PERSISTENT","PETRONET","PFC","PNB",
    "POLYCAB","RBLBANK","RECLTD","SAIL","SHREECEM","SIEMENS","SRF","SUNTV",
    "SUPREMEIND","SYNGENE","TATACHEM","TATACOMM","TATAELXSI","TRENT","TVSMOTOR",
    "UBL","VOLTAS","ZEEL","ZYDUSLIFE","LICI","HAL","NHPC","SJVN","RVNL",
    "RAILVIKAS","IRFC","HUDCO","MAZAGON","COCHINSHIP","GRSE"
]

# ── Token helpers ──
def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                d = json.load(f)
            if d.get("date") == get_ist_now().strftime("%Y-%m-%d"):
                return d.get("token", "")
        except:
            pass
    return ""

def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"date": get_ist_now().strftime("%Y-%m-%d"), "token": token}, f)

# ── Upstox Historical Data ──
def get_historical(token, symbol, days=200):
    end   = get_ist_now().strftime("%Y-%m-%d")
    start = (get_ist_now() - timedelta(days=days)).strftime("%Y-%m-%d")
    inst_key = f"NSE_EQ|{symbol}"
    url = f"https://api.upstox.com/v2/historical-candle/{requests.utils.quote(inst_key, safe='')}/day/{end}/{start}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            candles = r.json().get("data", {}).get("candles", [])
            if not candles:
                return pd.DataFrame()
            df = pd.DataFrame(candles, columns=["date","open","high","low","close","volume","oi"])
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# ── Technical Indicators ──
def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_sma(series, period):
    return series.rolling(window=period).mean()

def calc_wma(series, period):
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def calc_rsi(series, period=14):
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    macd_line   = calc_ema(series, fast) - calc_ema(series, slow)
    signal_line = calc_ema(macd_line, signal)
    return macd_line, signal_line

def calc_adx(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm]   = 0
    minus_dm[minus_dm < plus_dm]  = 0
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr      = tr.ewm(span=period, adjust=False).mean()
    plus_di  = 100 * plus_dm.ewm(span=period, adjust=False).mean()  / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    dx       = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_val  = dx.ewm(span=period, adjust=False).mean()
    return adx_val, plus_di, minus_di

# ── Scanner Logic ──
def scan_stock(df, params):
    if len(df) < 130:
        return None, None

    c = df["close"]
    v = df["volume"]

    ema5      = calc_ema(c, 5)
    sma20     = calc_sma(c, 20)
    sma40     = calc_sma(c, 40)
    sma50     = calc_sma(c, 50)
    wma10     = calc_wma(c, 10)
    rsi14     = calc_rsi(c, 14)
    macd_l, macd_s = calc_macd(c)
    adx14, plus_di, minus_di = calc_adx(df, 14)
    vol_sma5  = calc_sma(v, 5)
    high120   = c.rolling(120).max()

    adx_thr = params["adx_threshold"]
    rsi_thr = params["rsi_threshold"]
    buf     = 1 + params["breakout_buffer"] / 100

    conds = {
        "EMA5>SMA20":        bool(ema5.iloc[-1]    > sma20.iloc[-1]),
        "WMA10>SMA20":       bool(wma10.iloc[-1]   > sma20.iloc[-1]),
        f"+DI>{adx_thr}":    bool(plus_di.iloc[-1] > adx_thr),
        f"ADX>{adx_thr}":    bool(adx14.iloc[-1]   > adx_thr),
        "Vol>Min":           bool(v.iloc[-1]        > params["min_volume"]),
        "MACD>0":            bool(macd_l.iloc[-1]   > 0),
        "Close>1dAgo":       bool(c.iloc[-1]        > c.iloc[-2]),
        "Close>SMA50":       bool(c.iloc[-1]        > sma50.iloc[-1]),
        "Close>MinPrice":    bool(c.iloc[-1]        > params["min_price"]),
        "+DI>-DI":           bool(plus_di.iloc[-1]  > minus_di.iloc[-1]),
        f"RSI>{rsi_thr}":    bool(rsi14.iloc[-1]   > rsi_thr),
        "MACD>Signal":       bool(macd_l.iloc[-1]   > macd_s.iloc[-1]),
        "Close>2dAgo":       bool(c.iloc[-1]        > c.iloc[-3]),
        "SMA20>SMA40":       bool(sma20.iloc[-1]    > sma40.iloc[-1]),
        "Breakout5d>120d":   bool(c.rolling(5).max().iloc[-1] > high120.iloc[-7] * buf),
        "Vol>VolSMA5":       bool(v.iloc[-1]        > vol_sma5.iloc[-1]),
    }

    info = {
        "Close":  round(c.iloc[-1], 2),
        "Chg%":   round((c.iloc[-1] / c.iloc[-2] - 1) * 100, 2),
        "RSI":    round(rsi14.iloc[-1], 1),
        "ADX":    round(adx14.iloc[-1], 1),
        "+DI":    round(plus_di.iloc[-1], 1),
        "-DI":    round(minus_di.iloc[-1], 1),
        "MACD":   round(macd_l.iloc[-1], 3),
        "Volume": int(v.iloc[-1]),
    }
    return conds, info

def passes(conds, mode):
    trend_keys    = [k for k in conds if k not in ("Breakout5d>120d", "Vol>VolSMA5")]
    breakout_keys = ["Breakout5d>120d", "Vol>VolSMA5", "Close>1dAgo"]
    if mode == "Trend":
        return all(conds[k] for k in trend_keys)
    elif mode == "Breakout":
        return all(conds[k] for k in breakout_keys)
    else:
        return all(conds[k] for k in trend_keys) and all(conds[k] for k in breakout_keys)

# ── Sidebar ──
with st.sidebar:
    st.markdown("### 🔑 Upstox Access Token")
    saved_token  = load_token()
    token_input  = st.text_input("Access Token", value=saved_token, type="password",
                                  placeholder="Paste your daily token here")
    if token_input and token_input != saved_token:
        save_token(token_input)
        st.success("✅ Token saved!")
    access_token = token_input or saved_token

    st.markdown("---")
    st.markdown("### 🧩 Scanner Mode")
    scanner_mode = st.radio("Mode", ["Trend", "Breakout", "Combined"], index=2)

    st.markdown("---")
    st.markdown("### ⚙️ Filter Settings")
    min_price     = st.slider("Min Price (₹)", 10, 500, 150, 10)
    min_volume    = st.number_input("Min Volume", value=100000, step=10000)
    adx_threshold = st.slider("ADX Threshold", 10, 40, 20, 5)
    rsi_threshold = st.slider("RSI Threshold", 40, 70, 50, 5)
    breakout_buf  = st.slider("Breakout Buffer (%)", 1.0, 10.0, 5.0, 0.5)

    st.markdown("---")
    st.info(f"📦 **{len(STOCK_LIST)}** F&O stocks ready to scan")

params = {
    "min_price":       min_price,
    "min_volume":      min_volume,
    "adx_threshold":   adx_threshold,
    "rsi_threshold":   rsi_threshold,
    "breakout_buffer": breakout_buf,
}

# ── Header ──
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:1rem;">
    <div style="font-size:1.8rem; font-weight:900; color:#f0f6fc; letter-spacing:-0.03em;">
        🔍 Stock Scanner <span style="color:#1f6feb;">Pro</span>
    </div>
    <div style="background:#1f6feb22; border:1px solid #1f6feb55; border-radius:6px;
                padding:2px 10px; font-size:0.75rem; font-weight:700; color:#58a6ff;">
        UPSTOX LIVE
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 Scanner", "📋 Setup Guide"])

with tab1:
    if not access_token:
        st.warning("⚠️ Pehle sidebar mein Upstox Access Token daalo!")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("📦 Total Stocks", len(STOCK_LIST))
    with col2: st.metric("🧩 Mode", scanner_mode)
    with col3: st.metric("📉 Min Price", f"₹{min_price}")
    with col4: st.metric("📊 ADX Min", adx_threshold)

    st.markdown("---")
    run_btn = st.button("🚀 Run Scanner", use_container_width=True)

    if run_btn:
        results_list = []
        errors       = []
        progress_bar = st.progress(0)
        status_text  = st.empty()
        total        = len(STOCK_LIST)

        for i, symbol in enumerate(STOCK_LIST):
            status_text.markdown(
                f"<p style='color:#8b949e;font-size:0.85rem;'>🔍 Scanning <b style='color:#58a6ff'>{symbol}</b>... ({i+1}/{total})</p>",
                unsafe_allow_html=True
            )
            progress_bar.progress((i + 1) / total)

            df_hist = get_historical(access_token, symbol, days=210)
            if df_hist.empty or len(df_hist) < 130:
                errors.append(symbol)
                time.sleep(0.1)
                continue

            try:
                conds, info = scan_stock(df_hist, params)
                if conds is None:
                    errors.append(symbol)
                    continue

                if passes(conds, scanner_mode):
                    score     = sum(conds.values())
                    total_c   = len(conds)
                    tv_link   = f"https://www.tradingview.com/chart/?symbol=NSE:{symbol}"
                    results_list.append({
                        "Symbol":   symbol,
                        "Close ₹":  info["Close"],
                        "Chg%":     info["Chg%"],
                        "RSI":      info["RSI"],
                        "ADX":      info["ADX"],
                        "+DI":      info["+DI"],
                        "-DI":      info["-DI"],
                        "MACD":     info["MACD"],
                        "Volume":   f"{info['Volume']:,}",
                        "Score":    f"{score}/{total_c}",
                        "Chart":    tv_link,
                    })
            except Exception as e:
                errors.append(symbol)

            time.sleep(0.15)

        progress_bar.empty()
        status_text.empty()

        st.session_state["scan_results"] = results_list
        st.session_state["scan_errors"]  = errors
        st.session_state["scan_time"]    = get_ist_now().strftime("%d %b %Y, %I:%M %p IST")
        st.session_state["scan_mode"]    = scanner_mode

    # ── Display Results ──
    if "scan_results" in st.session_state:
        results_list = st.session_state["scan_results"]
        errors       = st.session_state.get("scan_errors", [])
        scan_time    = st.session_state.get("scan_time", "")
        mode_used    = st.session_state.get("scan_mode", "")

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("✅ Passed", len(results_list))
        with c2: st.metric("⚠️ Skipped", len(errors))
        with c3: st.metric("🕐 Scanned At", scan_time)

        if results_list:
            df_res = pd.DataFrame(results_list)
            st.markdown(
                f"<div style='color:#3fb950;font-weight:700;font-size:1rem;margin-bottom:0.5rem;'>"
                f"✅ {len(results_list)} stocks passed <b>{mode_used}</b> Scanner</div>",
                unsafe_allow_html=True
            )
            st.dataframe(
                df_res,
                use_container_width=True,
                column_config={
                    "Chart":    st.column_config.LinkColumn("Chart 📈", display_text="📈 Open"),
                    "Chg%":     st.column_config.NumberColumn("Chg%",    format="%.2f%%"),
                    "Close ₹":  st.column_config.NumberColumn("Close ₹", format="₹%.2f"),
                },
                hide_index=True
            )
            csv = df_res.drop(columns=["Chart"]).to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name=f"scanner_{mode_used}_{get_ist_now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("🔍 Koi stock pass nahi hua. Filters thoda loosen karo ya market close ke baad run karo.")

        if errors:
            with st.expander(f"⚠️ {len(errors)} symbols skip/error"):
                st.write(", ".join(errors))

with tab2:
    st.markdown("## 🚀 Setup & Usage Guide")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 🔑 Step 1: Access Token Kaise Milega?")
        st.markdown("""
- [developer.upstox.com](https://developer.upstox.com) pe jaao
- App create karo → API Key & Secret milega
- Upstox login karo → Access Token generate hoga
- **Token daily expire hota hai** — roz generate karna padega
- Sidebar mein paste karo → auto-save ho jaata hai
        """)

        st.markdown("### ⏰ Kab Run Karein?")
        st.success("**3:30 PM ke baad** — Market close, fully formed candles")
        st.warning("**Market hours mein mat run karo** — false signals aate hain")

    with col_b:
        st.markdown("### 🧩 Scanner Modes")
        st.markdown("""
| Mode | Kya karta hai |
|------|--------------|
| **Trend** | Pehle se strong uptrend mein stocks |
| **Breakout** | 6-month high tod rahe stocks |
| **Combined** | Dono conditions ek saath — highest quality |
        """)

        st.markdown("### 💡 Pro Tips")
        st.markdown("""
- **Combined mode** sabse reliable hai
- Results mein **Score** dekho — jitna zyada utna better
- **TradingView link** se chart manually verify karo
- **Gap-up stocks avoid karo** — risk-reward kharab hota hai
- CSV download karke watchlist banao
        """)
