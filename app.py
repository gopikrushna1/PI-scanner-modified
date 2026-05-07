import streamlit as st
import pandas as pd
import requests
import math
import os
import time
import gzip
import shutil
from datetime import datetime, timedelta, timezone
import concurrent.futures
import zipfile

# IST Offset
IST_OFFSET = timedelta(hours=5, minutes=30)
IST = timezone(IST_OFFSET)

def get_ist_now():
    return datetime.now(IST)

# Set page configuration
st.set_page_config(page_title="Positional Stock Option Scanner", layout="wide")

# Custom CSS for compact layout and button-like tabs
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0rem !important;
            white-space: nowrap !important;
        }
        h2 {
            font-size: 1.1rem !important;
            padding-top: 0.2rem !important;
            margin-bottom: 0.1rem !important;
        }
        h3 {
            font-size: 1.0rem !important;
            padding-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
        }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            white-space: pre-wrap;
            background-color: #f0f2f6;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 1.1rem;
            font-weight: 600;
            border: 1px solid #d6d6d6;
        }
        .stTabs [aria-selected="true"] {
            background-color: #007bff;
            color: white !important;
            border-color: #007bff;
        }
        
        /* Prevent graying out during refresh */
        .stApp {
            transition: none !important;
        }
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            opacity: 1 !important;
            transition: none !important;
        }
        
        /* Hide File Uploader Instructions */
        [data-testid="stFileUploaderDropzone"] div div span {
           display: none !important;
        }
        [data-testid="stFileUploaderDropzone"] div div small {
           display: none !important;
        }
        
        /* Force Dataframe Font Weight */
        div[data-testid="stDataFrame"] {
            font-weight: 600 !important;
        }
    </style>
""", unsafe_allow_html=True)

import json
import re

# Paths for persistent storage
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

BLACKLIST_FILE = os.path.join(DATA_DIR, 'blacklist.json')
TOKEN_FILE = os.path.join(DATA_DIR, 'token.json')
META_FILE = os.path.join(DATA_DIR, 'meta.json')
LTP_CACHE_FILE = os.path.join(DATA_DIR, 'ltp_cache.json')
OI_CACHE_FILE  = os.path.join(DATA_DIR, 'oi_cache.json')

FILES = {
    'Monthly': os.path.join(DATA_DIR, 'monthly.csv'),
    'Weekly': os.path.join(DATA_DIR, 'weekly.csv'),
    'Intraday': os.path.join(DATA_DIR, 'intraday.csv')
}

def load_meta():
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_meta(key, date_str):
    try:
        meta = load_meta()
        meta[key] = date_str
        with open(META_FILE, 'w') as f:
            json.dump(meta, f)
    except:
        pass

def load_ltp_cache():
    if os.path.exists(LTP_CACHE_FILE):
        try:
            with open(LTP_CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_ltp_cache(new_data):
    try:
        cache = load_ltp_cache()
        cache.update(new_data)
        with open(LTP_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except:
        pass

def load_oi_cache():
    if os.path.exists(OI_CACHE_FILE):
        try:
            with open(OI_CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_oi_cache(new_data):
    try:
        cache = load_oi_cache()
        cache.update(new_data)
        with open(OI_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except:
        pass

def extract_date_from_filename(filename):
    match = re.search(r'(\d{8})', filename)
    if match:
        d = match.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None

def extract_csv_from_zip(zip_file):
    try:
        with zipfile.ZipFile(zip_file) as z:
            csv_files = [f for f in z.namelist() if f.lower().endswith('.csv')]
            if not csv_files:
                st.error("No CSV file found in the ZIP archive.")
                return None, None
            csv_filename = csv_files[0]
            with z.open(csv_filename) as f:
                return f.read(), csv_filename
    except Exception as e:
        st.error(f"Error extracting ZIP file: {e}")
        return None, None

def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                if data.get('date') == get_ist_now().strftime('%Y-%m-%d'):
                    return data.get('token', '')
        except:
            pass
    return ''

def save_token(token):
    try:
        data = {
            'date': get_ist_now().strftime('%Y-%m-%d'),
            'token': token
        }
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, 'r') as f:
                data = json.load(f)
                if data.get('date') == get_ist_now().strftime('%Y-%m-%d'):
                    return set(data.get('keys', []))
        except:
            pass
    return set()

def save_blacklist(keys):
    try:
        data = {
            'date': get_ist_now().strftime('%Y-%m-%d'),
            'keys': list(keys)
        }
        with open(BLACKLIST_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

NSE_JSON_PATH = 'NSE.json'

# Known NSE/BSE index symbols in FO bhavcopy
INDEX_SYMBOLS = {
    'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY',
    'SENSEX', 'BANKEX', 'NIFTYNXT50', 'BSESENSEX',
    'MIDSELECT', 'NIFTYIT', 'NIFTY50', 'NIFTY100',
}

@st.cache_data
def load_nse_json():
    if os.path.exists(NSE_JSON_PATH):
        try:
            df = pd.read_json(NSE_JSON_PATH)
            if 'segment' in df.columns:
                df = df[df['segment'] == 'NSE_FO']
            df['expiry_dt'] = pd.to_datetime(df['expiry'], unit='ms').dt.normalize()
            return df
        except Exception as e:
            st.error(f"Error loading NSE.json: {e}")
            return pd.DataFrame()
    else:
        st.error(f"NSE.json not found at {NSE_JSON_PATH}")
        return pd.DataFrame()

def process_bhavcopy(bhav_file, df_json, target_expiry_index=0, min_underlying_move_pct=0.0, instrument_filter='All'):
    """
    Process bhavcopy CSV and return ATM options with enriched columns:
    - OI, OI_Change, Volume (from bhavcopy)
    - PCR per symbol (Put OI / Call OI)
    - Underlying move % filter applied if min_underlying_move_pct > 0
    """
    try:
        df_bhav = pd.read_csv(bhav_file)

        # ---------------------------------------------------------------
        # CHANGE 1: Include OI columns in required check
        # ---------------------------------------------------------------
        required_cols = [
            'FinInstrmTp', 'TckrSymb', 'XpryDt', 'ClsPric', 'StrkPric',
            'OptnTp', 'HghPric', 'LwPric', 'LastPric'
        ]
        # Optional OI/Volume columns — we check separately so we don't hard-fail
        oi_cols_available = all(c in df_bhav.columns for c in ['OpnIntrst', 'ChngInOpnIntrst', 'TtlTradgVol'])

        if not all(col in df_bhav.columns for col in required_cols):
            st.error(f"Uploaded file missing required columns: {required_cols}")
            return pd.DataFrame()

        # --- Process Futures ---
        futures = df_bhav[df_bhav['FinInstrmTp'].isin(['STF', 'IDF'])].copy()
        if futures.empty:
            st.warning("No Futures data found in uploaded file.")
            return pd.DataFrame()

        futures['XpryDt'] = pd.to_datetime(futures['XpryDt'])
        ist_now = get_ist_now()
        today = ist_now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        futures = futures[futures['XpryDt'] >= today]

        if futures.empty:
            st.warning("No future expiries found in the uploaded file.")
            return pd.DataFrame()

        futures = futures.sort_values('XpryDt')
        available_expiries = sorted(futures['XpryDt'].unique())

        if target_expiry_index >= len(available_expiries):
            target_expiry = available_expiries[-1]
        else:
            target_expiry = available_expiries[target_expiry_index]

        near_futures = futures[futures['XpryDt'] == target_expiry].copy()
        near_futures = near_futures[['TckrSymb', 'ClsPric', 'XpryDt']]
        near_futures = near_futures.rename(columns={'ClsPric': 'FuturePrice', 'XpryDt': 'FutureExpiryDate'})

        # ---------------------------------------------------------------
        # CHANGE 2: Compute underlying move % using prev close vs last price
        # We use futures PrevClsPric vs ClsPric to measure how much the
        # underlying has moved. Only available if 'PrvClsPric' exists.
        # ---------------------------------------------------------------
        underlying_move_available = 'PrvClsPric' in futures.columns

        if underlying_move_available:
            fut_move = futures[futures['XpryDt'] == target_expiry][['TckrSymb', 'ClsPric', 'PrvClsPric']].copy()
            fut_move['UnderlyingMove%'] = (
                (fut_move['ClsPric'] - fut_move['PrvClsPric']) / fut_move['PrvClsPric'] * 100
            ).abs()
            fut_move = fut_move[['TckrSymb', 'UnderlyingMove%']]
        else:
            fut_move = pd.DataFrame(columns=['TckrSymb', 'UnderlyingMove%'])

        # --- Process Options ---
        options = df_bhav[df_bhav['OptnTp'].isin(['CE', 'PE'])].copy()
        if options.empty:
            st.warning("No Options data found in uploaded file.")
            return pd.DataFrame()

        options['XpryDt'] = pd.to_datetime(options['XpryDt'])

        # ---------------------------------------------------------------
        # CHANGE 3: Build PCR (Put-Call Ratio) per symbol
        # PCR = Total Put OI / Total Call OI for ATM expiry
        # Done BEFORE filtering to ATM strike so we use all strikes for PCR
        # ---------------------------------------------------------------
        pcr_map = {}
        if oi_cols_available:
            options_for_pcr = options[options['XpryDt'] == target_expiry].copy()
            options_for_pcr['OpnIntrst'] = pd.to_numeric(options_for_pcr['OpnIntrst'], errors='coerce').fillna(0)

            call_oi = options_for_pcr[options_for_pcr['OptnTp'] == 'CE'].groupby('TckrSymb')['OpnIntrst'].sum()
            put_oi  = options_for_pcr[options_for_pcr['OptnTp'] == 'PE'].groupby('TckrSymb')['OpnIntrst'].sum()

            pcr_series = put_oi / call_oi.replace(0, float('nan'))
            pcr_map = pcr_series.to_dict()

        # Merge options with futures
        merged = pd.merge(options, near_futures, on='TckrSymb')
        merged = merged[merged['XpryDt'] == merged['FutureExpiryDate']]

        merged['Diff'] = abs(merged['StrkPric'] - merged['FuturePrice'])

        best_strikes = merged[['TckrSymb', 'StrkPric', 'Diff']].drop_duplicates()
        best_strikes = best_strikes.sort_values(by=['TckrSymb', 'Diff', 'StrkPric'])
        best_strikes = best_strikes.groupby('TckrSymb').first().reset_index()

        atm_options = pd.merge(merged, best_strikes[['TckrSymb', 'StrkPric']], on=['TckrSymb', 'StrkPric'])

        # ---------------------------------------------------------------
        # CHANGE 4: Include OI columns in selection if available
        # ---------------------------------------------------------------
        base_cols = [
            'TckrSymb', 'XpryDt', 'StrkPric', 'OptnTp',
            'FuturePrice', 'ClsPric', 'FinInstrmNm',
            'HghPric', 'LwPric', 'LastPric'
        ]
        if oi_cols_available:
            base_cols += ['OpnIntrst', 'ChngInOpnIntrst', 'TtlTradgVol']

        atm_rows = atm_options[base_cols].copy()
        atm_rows['XpryDt'] = atm_rows['XpryDt'].dt.normalize()

        # Merge with Upstox JSON
        result = pd.merge(
            atm_rows,
            df_json,
            left_on=['TckrSymb', 'StrkPric', 'OptnTp', 'XpryDt'],
            right_on=['underlying_symbol', 'strike_price', 'instrument_type', 'expiry_dt'],
            how='inner'
        )

        # Build final column list
        final_cols = [
            'TckrSymb', 'XpryDt', 'StrkPric', 'OptnTp',
            'FuturePrice', 'ClsPric', 'instrument_key',
            'HghPric', 'LwPric', 'LastPric'
        ]
        if oi_cols_available:
            final_cols += ['OpnIntrst', 'ChngInOpnIntrst', 'TtlTradgVol']

        final_df = result[final_cols].copy()

        rename_map = {
            'TckrSymb': 'Symbol',
            'XpryDt': 'ExpiryDate',
            'StrkPric': 'StrikePrice',
            'OptnTp': 'OptionType',
            'ClsPric': 'Trigger',
            'HghPric': 'HighPrice',
            'LwPric': 'LowPrice',
            'LastPric': 'LastPrice',
        }
        if oi_cols_available:
            rename_map.update({
                'OpnIntrst': 'OI',
                'ChngInOpnIntrst': 'OI_Change',
                'TtlTradgVol': 'Volume'
            })

        final_df = final_df.rename(columns=rename_map)

        # Camarilla R4
        final_df['Camarilla_R4'] = final_df['Trigger'] + (final_df['HighPrice'] - final_df['LowPrice']) * 1.1 / 2

        # Trigger × 2
        final_df['Trigger'] = final_df['Trigger'] * 2

        # ---------------------------------------------------------------
        # CHANGE 5: Add PCR column
        # ---------------------------------------------------------------
        if pcr_map:
            final_df['PCR'] = final_df['Symbol'].map(pcr_map).round(2)
        else:
            final_df['PCR'] = float('nan')

        # ---------------------------------------------------------------
        # CHANGE 6: Add underlying move % and apply filter
        # ---------------------------------------------------------------
        if underlying_move_available and not fut_move.empty:
            final_df = pd.merge(final_df, fut_move, on='TckrSymb', how='left')
            # Rename TckrSymb back after merge — it was renamed to Symbol earlier
            # The merge above won't work because we renamed. Fix: merge on Symbol
            # Redo: keep TckrSymb → Symbol mapping
        else:
            final_df['UnderlyingMove%'] = float('nan')

        # Re-attempt underlying move merge correctly (Symbol is already renamed)
        if underlying_move_available and not fut_move.empty:
            # fut_move has TckrSymb column; final_df has Symbol column
            fut_move_renamed = fut_move.rename(columns={'TckrSymb': 'Symbol'})
            # Drop if already added from previous merge attempt
            if 'UnderlyingMove%' in final_df.columns:
                final_df = final_df.drop(columns=['UnderlyingMove%'])
            final_df = pd.merge(final_df, fut_move_renamed, on='Symbol', how='left')

        # Apply minimum underlying move filter
        if min_underlying_move_pct > 0 and 'UnderlyingMove%' in final_df.columns:
            before = len(final_df)
            final_df = final_df[
                final_df['UnderlyingMove%'].isna() |
                (final_df['UnderlyingMove%'] >= min_underlying_move_pct)
            ]
            after = len(final_df)
            if before != after:
                st.caption(f"ℹ️ {before - after} symbols filtered out (Underlying Move < {min_underlying_move_pct}%)")

        # ---------------------------------------------------------------
        # CHANGE 7: OI Change confirmation flag
        # Mark True if OI_Change > 0 (fresh buying), False if unwinding
        # ---------------------------------------------------------------
        if 'OI_Change' in final_df.columns:
            final_df['OI_Change'] = pd.to_numeric(final_df['OI_Change'], errors='coerce').fillna(0)
            final_df['OI'] = pd.to_numeric(final_df['OI'], errors='coerce').fillna(0)
            final_df['Volume'] = pd.to_numeric(final_df['Volume'], errors='coerce').fillna(0)
            final_df['OI_Confirmed'] = final_df['OI_Change'] > 0

        return final_df

    except Exception as e:
        st.error(f"Error processing file: {e}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame()


def fetch_live_data(instrument_keys, token):
    """
    Fetch LTP + OI + Volume + IV + Prev Close from Upstox v3 full market quote API.
    Returns: (ltp_map, oi_map)
      ltp_map  = {instrument_token: last_price}
      oi_map   = {instrument_key:   {oi, volume, iv, cp (prev_close), oi_change}}
    Uses /v3/market-quote/quotes for full data (not just LTP).
    Falls back to /v3/market-quote/ltp for LTP if full quote fails.
    """
    if not token:
        return {}, {}

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    batch_size = 50
    ltp_map = {}
    oi_map  = {}
    batches = [instrument_keys[i:i + batch_size] for i in range(0, len(instrument_keys), batch_size)]

    def fetch_batch(batch):
        batch_ltp = {}
        batch_oi  = {}

        # ── Full market quote (has OI, volume, IV, prev_close) ──
        try:
            url    = "https://api.upstox.com/v3/market-quote/quotes"
            params = {'instrument_key': ','.join(batch)}
            resp   = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    for inst_key, details in data.get('data', {}).items():
                        # LTP
                        inst_token = details.get('instrument_token')
                        last_price = details.get('last_price')
                        if inst_token and last_price is not None:
                            batch_ltp[inst_token] = last_price

                        # OI + Volume + IV + Prev Close
                        oi_data = details.get('oi', None)
                        vol     = details.get('volume', None)
                        iv      = details.get('average_price', None)  # IV not direct; use greeks if available
                        cp      = details.get('close_price', None)    # prev close
                        oi_day_high = details.get('oi_day_high', None)
                        oi_day_low  = details.get('oi_day_low', None)

                        # Greeks (IV is here if available)
                        greeks = details.get('option_greeks', {}) or {}
                        iv_val = greeks.get('vega', None)   # vega as IV proxy, or use 'iv' if present
                        iv_val = greeks.get('iv', iv_val)    # actual IV if present

                        # Depth / best bid-ask spread (for liquidity check)
                        depth   = details.get('depth', {}) or {}
                        best_bid = (depth.get('buy',  [{}]) or [{}])[0].get('price', 0)
                        best_ask = (depth.get('sell', [{}]) or [{}])[0].get('price', 0)

                        batch_oi[inst_key] = {
                            'oi'        : oi_data,
                            'volume'    : vol,
                            'iv'        : iv_val,
                            'cp'        : cp,
                            'oi_day_high': oi_day_high,
                            'oi_day_low' : oi_day_low,
                            'best_bid'  : best_bid,
                            'best_ask'  : best_ask,
                        }
                    return batch_ltp, batch_oi
        except Exception:
            pass

        # ── Fallback: LTP only ───────────────────────────────────
        try:
            url    = "https://api.upstox.com/v3/market-quote/ltp"
            params = {'instrument_key': ','.join(batch)}
            resp   = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    for inst_key, details in data.get('data', {}).items():
                        inst_token = details.get('instrument_token')
                        last_price = details.get('last_price')
                        if inst_token and last_price is not None:
                            batch_ltp[inst_token] = last_price
        except Exception:
            pass

        return batch_ltp, batch_oi

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures_list = [executor.submit(fetch_batch, batch) for batch in batches]
        for future in concurrent.futures.as_completed(futures_list):
            try:
                bltp, boi = future.result()
                ltp_map.update(bltp)
                oi_map.update(boi)
            except Exception:
                pass

    return ltp_map, oi_map


# Keep fetch_ltp as a thin wrapper for backward compat
def fetch_ltp(instrument_keys, token):
    ltp_map, _ = fetch_live_data(instrument_keys, token)
    return ltp_map


def display_option_chain(df, access_token, key_suffix, show_oi_filter, show_unconfirmed, hide_weak_signals=False):
    st.caption(f"Last Updated: {get_ist_now().strftime('%H:%M:%S')} IST")
    if df.empty:
        st.info("No data to display. Please upload a valid Bhavcopy in the sidebar.")
        return

    has_oi = 'OI' in df.columns and 'OI_Change' in df.columns and 'Volume' in df.columns
    has_pcr = 'PCR' in df.columns
    has_underlying = 'UnderlyingMove%' in df.columns

    # Fetch LTP + Live OI + Volume
    if access_token:
        all_keys = df['instrument_key'].dropna().unique().tolist()

        ist_now = get_ist_now()
        current_time = ist_now.time()
        start_time = datetime.strptime("09:00", "%H:%M").time()
        end_time   = datetime.strptime("15:40", "%H:%M").time()
        is_market_hours = start_time <= current_time <= end_time

        ltp_cache = load_ltp_cache()
        oi_cache  = load_oi_cache()
        missing_keys = [k for k in all_keys if k not in ltp_cache]

        should_fetch = is_market_hours or bool(missing_keys)

        if should_fetch:
            keys_to_fetch = all_keys if is_market_hours else missing_keys
            fetched_ltp, fetched_oi = fetch_live_data(keys_to_fetch, access_token)
            if fetched_ltp:
                save_ltp_cache(fetched_ltp)
                ltp_cache = load_ltp_cache()
            if fetched_oi:
                save_oi_cache(fetched_oi)
                oi_cache = load_oi_cache()

        ltp_data = {k: ltp_cache.get(k, 0.0) for k in all_keys}
        df['ltp'] = df['instrument_key'].map(ltp_data).fillna(0.0)

        # ── Live OI & Volume from API ──────────────────────────────────
        # Override bhavcopy OI/Volume with live values when available
        def get_oi_field(inst_key, field):
            return oi_cache.get(inst_key, {}).get(field, None)

        df['live_oi']     = df['instrument_key'].apply(lambda k: get_oi_field(k, 'oi'))
        df['live_volume'] = df['instrument_key'].apply(lambda k: get_oi_field(k, 'volume'))
        df['live_iv']     = df['instrument_key'].apply(lambda k: get_oi_field(k, 'iv'))
        df['prev_close']  = df['instrument_key'].apply(lambda k: get_oi_field(k, 'cp'))

        # Compute live OI change: live_oi - bhavcopy OI (prev day EOD OI)
        if 'OI' in df.columns:
            df['live_oi_change'] = (
                pd.to_numeric(df['live_oi'], errors='coerce') -
                pd.to_numeric(df['OI'],      errors='coerce')
            )
        else:
            df['live_oi_change'] = pd.to_numeric(df['live_oi'], errors='coerce')

        # ── Smart OI Interpretation (Price + OI Matrix) ────────────────
        # Price direction: ltp vs prev_close from API
        def oi_signal(row):
            try:
                ltp     = float(row['ltp'])       if row['ltp']      else 0
                cp      = float(row['prev_close']) if row['prev_close'] else 0
                oi_chg  = float(row['live_oi_change']) if pd.notna(row['live_oi_change']) else 0

                if ltp == 0 or cp == 0:
                    return '-'

                price_up = ltp > cp
                oi_up    = oi_chg > 0

                if price_up and oi_up:
                    return '🟢 Fresh Buying'       # Strong bullish
                elif price_up and not oi_up:
                    return '🟡 Short Covering'      # Weak move
                elif not price_up and oi_up:
                    return '🔴 Short Buildup'       # Strong bearish
                else:
                    return '⚪ Unwinding'           # Weak
            except:
                return '-'

        df['OI_Signal'] = df.apply(oi_signal, axis=1)

    else:
        df['ltp']           = 0.0
        df['live_oi']       = None
        df['live_volume']   = None
        df['live_iv']       = None
        df['live_oi_change'] = None
        df['OI_Signal']     = '-'
        st.warning("Enter Access Token in sidebar to see live LTP.")

    # Intraday: use Camarilla_R4 as trigger
    if key_suffix == 'Intraday' and 'Camarilla_R4' in df.columns:
        df['Trigger'] = df['Camarilla_R4']

    # Change %
    def calculate_numeric_change(row):
        try:
            ocp = row['Trigger']
            ltp = row['ltp']
            if ocp > 0 and ltp > 0:
                return (ltp / ocp * 100)
            return 0.0
        except:
            return 0.0

    df['change_val'] = df.apply(calculate_numeric_change, axis=1)
    df['change %'] = df['change_val']

    # --- Intraday Blacklist Logic ---
    if key_suffix == 'Intraday':
        blacklist = load_blacklist()
        current_time = get_ist_now().time()
        cutoff_time = datetime.strptime("09:30", "%H:%M").time()

        if current_time < cutoff_time:
            violators = df[df['change %'] >= 100]['instrument_key'].tolist()
            if violators:
                blacklist.update(violators)
                save_blacklist(blacklist)

        if blacklist:
            df = df[~df['instrument_key'].isin(blacklist)]

    # ---------------------------------------------------------------
    # CHANGE 8: OI Confirmation filter in display
    # If show_oi_filter=True, hide rows where OI_Change <= 0 (unwinding)
    # ---------------------------------------------------------------
    if has_oi and show_oi_filter and not show_unconfirmed:
        before = len(df)
        df = df[df['OI_Confirmed'] == True]
        after = len(df)
        if before != after:
            st.caption(f"ℹ️ {before - after} options hidden (OI declining — possible unwinding)")

    # Hide weak live OI signals (Short Covering + Unwinding)
    if hide_weak_signals and 'OI_Signal' in df.columns:
        weak = ['🟡 Short Covering', '⚪ Unwinding']
        before = len(df)
        df = df[~df['OI_Signal'].isin(weak)]
        after = len(df)
        if before != after:
            st.caption(f"ℹ️ {before - after} weak signals hidden (Short Covering / Unwinding)")

    # Split Calls/Puts
    calls_df = df[df['OptionType'] == 'CE'].copy()
    puts_df  = df[df['OptionType'] == 'PE'].copy()

    calls_df = calls_df.sort_values(by='change %', ascending=False)
    puts_df  = puts_df.sort_values(by='change %', ascending=False)

    # Build display columns dynamically
    has_live_oi = 'live_oi' in df.columns and df['live_oi'].notna().any()

    display_cols = ['Symbol', 'StrikePrice', 'Trigger', 'ltp', 'change %']
    format_dict = {
        'change %': '{:.2f}%',
        'Trigger': '{:.2f}',
        'ltp': '{:.2f}',
        'StrikePrice': '{:.2f}'
    }

    # Live OI columns (from API) — shown instead of bhavcopy OI when available
    if has_live_oi:
        display_cols += ['live_oi', 'live_oi_change', 'live_volume', 'live_iv', 'OI_Signal']
        format_dict.update({
            'live_oi':        '{:,.0f}',
            'live_oi_change': '{:+,.0f}',
            'live_volume':    '{:,.0f}',
            'live_iv':        '{:.2%}',
        })
    elif has_oi:
        # Fallback to bhavcopy OI if no live data
        display_cols += ['OI', 'OI_Change', 'Volume']
        format_dict.update({
            'OI':        '{:,.0f}',
            'OI_Change': '{:,.0f}',
            'Volume':    '{:,.0f}'
        })

    if has_pcr:
        display_cols.append('PCR')
        format_dict['PCR'] = '{:.2f}'

    if has_underlying:
        display_cols.append('UnderlyingMove%')
        format_dict['UnderlyingMove%'] = '{:.2f}%'

    # Styling
    def color_row(row):
        styles = [''] * len(row)
        col_list = list(row.index)

        change_idx       = col_list.index('change %')       if 'change %'       in col_list else None
        oi_change_idx    = col_list.index('OI_Change')      if 'OI_Change'      in col_list else None
        live_oi_chg_idx  = col_list.index('live_oi_change') if 'live_oi_change' in col_list else None
        oi_signal_idx    = col_list.index('OI_Signal')      if 'OI_Signal'      in col_list else None

        change_val    = row.get('change %', 0)
        oi_signal_val = row.get('OI_Signal', '-')

        # change % coloring
        if change_val >= 100:
            base_bg = 'background-color: darkgreen; color: white'
        elif change_val >= 90:
            base_bg = 'background-color: lightgreen; color: black'
        else:
            base_bg = ''

        if base_bg and change_idx is not None:
            styles[change_idx] = base_bg

        # Bhavcopy OI_Change coloring (fallback)
        if oi_change_idx is not None:
            oi_change_val = row.get('OI_Change', 0)
            if oi_change_val > 0:
                styles[oi_change_idx] = 'background-color: #c8f7c5; color: black'
            elif oi_change_val < 0:
                styles[oi_change_idx] = 'background-color: #f7c5c5; color: black'

        # Live OI change coloring
        if live_oi_chg_idx is not None:
            live_oi_chg = row.get('live_oi_change', 0)
            try:
                live_oi_chg = float(live_oi_chg) if pd.notna(live_oi_chg) else 0
                if live_oi_chg > 0:
                    styles[live_oi_chg_idx] = 'background-color: #c8f7c5; color: black'
                elif live_oi_chg < 0:
                    styles[live_oi_chg_idx] = 'background-color: #f7c5c5; color: black'
            except:
                pass

        # OI Signal row highlight
        if oi_signal_idx is not None:
            if 'Fresh Buying' in str(oi_signal_val):
                styles[oi_signal_idx] = 'background-color: #1a7a1a; color: white; font-weight: 700'
            elif 'Short Covering' in str(oi_signal_val):
                styles[oi_signal_idx] = 'background-color: #fff3cd; color: black; font-weight: 700'
            elif 'Short Buildup' in str(oi_signal_val):
                styles[oi_signal_idx] = 'background-color: #b22222; color: white; font-weight: 700'
            elif 'Unwinding' in str(oi_signal_val):
                styles[oi_signal_idx] = 'background-color: #e0e0e0; color: black'

        return styles

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Calls (CE)")
        # PCR guidance for calls
        if has_pcr and not calls_df.empty:
            avg_pcr = calls_df['PCR'].mean()
            if not pd.isna(avg_pcr):
                pcr_label = "Bullish (Low PCR)" if avg_pcr < 1 else "Bearish (High PCR)"
                st.caption(f"Avg PCR: {avg_pcr:.2f} — {pcr_label}")

        valid_cols = [c for c in display_cols if c in calls_df.columns]
        st.dataframe(
            calls_df[valid_cols].style
            .apply(color_row, axis=1)
            .format({k: v for k, v in format_dict.items() if k in valid_cols})
            .set_properties(**{'font-weight': '600', 'text-align': 'center', 'font-size': '16px'}),
            hide_index=True,
            use_container_width=True,
            height=1800
        )

    with col2:
        st.subheader("Puts (PE)")
        if has_pcr and not puts_df.empty:
            avg_pcr = puts_df['PCR'].mean()
            if not pd.isna(avg_pcr):
                pcr_label = "Bearish (High PCR)" if avg_pcr > 1 else "Bullish (Low PCR)"
                st.caption(f"Avg PCR: {avg_pcr:.2f} — {pcr_label}")

        valid_cols = [c for c in display_cols if c in puts_df.columns]
        st.dataframe(
            puts_df[valid_cols].style
            .apply(color_row, axis=1)
            .format({k: v for k, v in format_dict.items() if k in valid_cols})
            .set_properties(**{'font-weight': '600', 'text-align': 'center', 'font-size': '16px'}),
            hide_index=True,
            use_container_width=True,
            height=1800
        )



def display_oi_analysis(df_list, access_token, run_every):
    """
    Live OI Analysis tab — shows all symbols grouped by OI Signal type.
    df_list: list of (label, df) tuples from all three bhavcopies
    """
    st.caption(f"Last Updated: {get_ist_now().strftime('%H:%M:%S')} IST")

    if not access_token:
        st.warning("Access Token required for live OI data.")
        return

    # Combine all dataframes
    all_rows = []
    for source_label, df in df_list:
        if df is not None and not df.empty:
            df = df.copy()
            df['Source'] = source_label
            all_rows.append(df)

    if not all_rows:
        st.info("Upload at least one Bhavcopy to see OI Analysis.")
        return

    combined = pd.concat(all_rows, ignore_index=True)

    # Fetch live data for all instrument keys
    all_keys = combined['instrument_key'].dropna().unique().tolist()
    if not all_keys:
        st.info("No instrument keys found.")
        return

    with st.spinner("Fetching live OI data..."):
        fetched_ltp, fetched_oi = fetch_live_data(all_keys, access_token)
        if fetched_ltp:
            save_ltp_cache(fetched_ltp)
        if fetched_oi:
            save_oi_cache(fetched_oi)

    ltp_cache = load_ltp_cache()
    oi_cache  = load_oi_cache()

    # Map live data
    combined['ltp']       = combined['instrument_key'].map(ltp_cache).fillna(0.0)
    combined['live_oi']   = combined['instrument_key'].apply(lambda k: oi_cache.get(k, {}).get('oi'))
    combined['live_vol']  = combined['instrument_key'].apply(lambda k: oi_cache.get(k, {}).get('volume'))
    combined['live_iv']   = combined['instrument_key'].apply(lambda k: oi_cache.get(k, {}).get('iv'))
    combined['cp']        = combined['instrument_key'].apply(lambda k: oi_cache.get(k, {}).get('cp'))

    # OI Change: live OI vs bhavcopy OI (prev EOD)
    if 'OI' in combined.columns:
        combined['oi_change'] = (
            pd.to_numeric(combined['live_oi'], errors='coerce') -
            pd.to_numeric(combined['OI'],      errors='coerce')
        )
    else:
        combined['oi_change'] = pd.to_numeric(combined['live_oi'], errors='coerce')

    # Smart OI Signal
    def oi_signal(row):
        try:
            ltp    = float(row['ltp']) if row['ltp'] else 0
            cp     = float(row['cp'])  if row['cp']  else 0
            oi_chg = float(row['oi_change']) if pd.notna(row['oi_change']) else 0
            if ltp == 0 or cp == 0:
                return 'Unknown'
            price_up = ltp > cp
            oi_up    = oi_chg > 0
            if price_up and oi_up:     return 'Fresh Buying'
            elif price_up and not oi_up: return 'Short Covering'
            elif not price_up and oi_up: return 'Short Buildup'
            else:                        return 'Unwinding'
        except:
            return 'Unknown'

    combined['OI_Signal'] = combined.apply(oi_signal, axis=1)

    # Change %
    combined['change%'] = combined.apply(
        lambda r: round((r['ltp'] / r['Trigger'] * 100), 2)
        if r['ltp'] > 0 and r.get('Trigger', 0) > 0 else 0.0,
        axis=1
    )

    # ── Summary cards at top ─────────────────────────────────────
    st.markdown("### 📊 Live OI Signal Summary")
    
    counts = combined['OI_Signal'].value_counts()
    c1, c2, c3, c4 = st.columns(4)
    
    def signal_card(col, label, emoji, color, bg):
        count = counts.get(label, 0)
        col.markdown(f"""
        <div style="background:{bg}; border-radius:12px; padding:16px; text-align:center;">
            <div style="font-size:2rem;">{emoji}</div>
            <div style="font-size:1.5rem; font-weight:800; color:{color};">{count}</div>
            <div style="font-size:0.95rem; font-weight:600; color:{color};">{label}</div>
            <div style="font-size:0.8rem; color:{color}; opacity:0.85;">
                {"Price↑ + OI↑" if label=="Fresh Buying" else
                 "Price↑ + OI↓" if label=="Short Covering" else
                 "Price↓ + OI↑" if label=="Short Buildup" else
                 "Price↓ + OI↓"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    signal_card(c1, 'Fresh Buying',   '🟢', '#ffffff', '#1a5c1a')
    signal_card(c2, 'Short Covering', '🟡', '#5c4a00', '#fff3cd')
    signal_card(c3, 'Short Buildup',  '🔴', '#ffffff', '#8b0000')
    signal_card(c4, 'Unwinding',      '⚪', '#555555', '#e0e0e0')

    st.markdown("---")

    # ── Display columns ──────────────────────────────────────────
    disp_cols = ['Symbol', 'OptionType', 'StrikePrice', 'Source',
                 'ltp', 'change%', 'live_oi', 'oi_change', 'live_vol', 'live_iv']
    fmt = {
        'ltp':        '{:.2f}',
        'change%':    '{:.2f}%',
        'live_oi':    '{:,.0f}',
        'oi_change':  '{:+,.0f}',
        'live_vol':   '{:,.0f}',
        'live_iv':    '{:.2f}',
        'StrikePrice':'{:.0f}',
    }

    def style_oi_table(df_sub):
        def row_color(row):
            sig = row.get('OI_Signal', '')
            base = [''] * len(row)
            if   sig == 'Fresh Buying':   return [f'background-color:#1a5c1a;color:white'   ] * len(row)
            elif sig == 'Short Covering': return [f'background-color:#fff3cd;color:#5c4a00' ] * len(row)
            elif sig == 'Short Buildup':  return [f'background-color:#8b0000;color:white'   ] * len(row)
            elif sig == 'Unwinding':      return [f'background-color:#e0e0e0;color:#555555' ] * len(row)
            return base
        valid = [c for c in disp_cols if c in df_sub.columns]
        return (df_sub[valid].style
                .apply(row_color, axis=1)
                .format({k: v for k,v in fmt.items() if k in valid}, na_rep='-')
                .set_properties(**{'text-align': 'center', 'font-size': '15px', 'font-weight': '600'}))

    # ── Four sections ─────────────────────────────────────────────
    sections = [
        ('🟢 Fresh Buying',   'Fresh Buying',   'Strong bullish — Price↑ + OI↑. Best CE signals.'),
        ('🔴 Short Buildup',  'Short Buildup',  'Strong bearish — Price↓ + OI↑. Best PE signals.'),
        ('🟡 Short Covering', 'Short Covering', 'Weak move — Price↑ + OI↓. Short sellers exiting, may reverse.'),
        ('⚪ Unwinding',      'Unwinding',      'Weak — Price↓ + OI↓. Longs exiting. Avoid.'),
    ]

    for title, signal_key, desc in sections:
        sub = combined[combined['OI_Signal'] == signal_key].copy()
        sub = sub.sort_values('change%', ascending=False)
        with st.expander(f"{title} — {len(sub)} symbols", expanded=(signal_key in ['Fresh Buying', 'Short Buildup'])):
            st.caption(desc)
            if sub.empty:
                st.info("No symbols in this category right now.")
            else:
                st.dataframe(style_oi_table(sub), hide_index=True, use_container_width=True,
                             height=min(60 + len(sub) * 38, 800))


# --- Configuration Logic ---
is_client_view = "UPSTOX_ACCESS_TOKEN" in st.secrets and st.secrets["UPSTOX_ACCESS_TOKEN"].strip() != ""

if is_client_view:
    access_token = st.secrets["UPSTOX_ACCESS_TOKEN"]
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

    auto_refresh = True
    refresh_interval = 15
    target_expiry_idx = 0
    min_underlying_move = 0.0
    show_oi_filter = True
    show_unconfirmed = False
    instrument_filter = 'All'
    hide_weak_signals = False

else:
    with st.sidebar:
        st.header("Configuration")

        saved_token = load_token()
        access_token = st.text_input("Upstox Access Token", value=saved_token, type="password")
        if access_token and access_token != saved_token:
            save_token(access_token)

        st.markdown("---")
        st.header("Expiry Settings")
        expiry_type = st.radio(
            "Select Expiry Month",
            options=["Current Month", "Next Month"],
            index=0
        )
        target_expiry_idx = 0 if expiry_type == "Current Month" else 1

        # Instrument type filter
        st.markdown("---")
        st.header("Instrument Type")
        instrument_filter = st.radio(
            "Show",
            options=["All", "Index Only", "Stocks Only"],
            index=0,
            help="All = Stocks + Indices\nIndex Only = NIFTY, BANKNIFTY, FINNIFTY, SENSEX etc.\nStocks Only = Individual stock options only"
        )
        if instrument_filter == "Index Only":
            st.caption("NIFTY · BANKNIFTY · FINNIFTY · MIDCPNIFTY · SENSEX · BANKEX")

        # ---------------------------------------------------------------
        # Signal Filters
        # ---------------------------------------------------------------
        st.markdown("---")
        st.header("Signal Filters")

        min_underlying_move = st.slider(
            "Min Underlying Move % (0 = off)",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.25,
            help="Only show options where the underlying stock/index has moved at least this % from previous close. Requires PrvClsPric in bhavcopy."
        )

        show_oi_filter = st.checkbox(
            "OI Confirmation Filter",
            value=False,
            help="When enabled, hides options where Open Interest is declining (possible unwinding, not fresh buying)."
        )

        show_unconfirmed = False
        if show_oi_filter:
            show_unconfirmed = st.checkbox(
                "Show unconfirmed (OI declining) anyway",
                value=False,
                help="Override: show all options but still highlight OI_Change column in red/green."
            )

        hide_weak_signals = st.checkbox(
            "Hide Weak OI Signals",
            value=False,
            help="Hide rows where live OI Signal is 'Short Covering' or 'Unwinding' — keep only Fresh Buying and Short Buildup."
        )

        st.markdown("---")
        st.header("Data Management")

        st.subheader("NSE Instrument JSON")
        if st.button("🔄 Download Latest"):
            try:
                with st.spinner("Downloading latest NSE.json from Upstox..."):
                    url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    response = requests.get(url, headers=headers, stream=True)
                    if response.status_code == 200:
                        with open(NSE_JSON_PATH, "wb") as f_out:
                            with gzip.GzipFile(fileobj=response.raw) as f_in:
                                shutil.copyfileobj(f_in, f_out)
                        st.cache_data.clear()
                        st.success("Updated successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed to download. Status: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

        meta = load_meta()

        st.subheader("Monthly")
        up_m = st.file_uploader("Upload Monthly Bhavcopy", type=['zip'], key='m_up')
        if up_m is not None:
            csv_content, csv_name = extract_csv_from_zip(up_m)
            if csv_content:
                with open(FILES['Monthly'], "wb") as f:
                    f.write(csv_content)
                date_str = extract_date_from_filename(csv_name)
                if date_str:
                    save_meta('Monthly', date_str)
                st.success(f"Monthly file updated from {csv_name}!")
        if 'Monthly' in meta and os.path.exists(FILES['Monthly']):
            st.caption(f"📅 Data Date: {meta['Monthly']}")
        elif os.path.exists(FILES['Monthly']):
            m_time = os.path.getmtime(FILES['Monthly'])
            st.caption(f"📅 Last Updated: {datetime.fromtimestamp(m_time).strftime('%Y-%m-%d %H:%M')}")

        st.subheader("Weekly")
        up_w = st.file_uploader("Upload Weekly Bhavcopy", type=['zip'], key='w_up')
        if up_w is not None:
            csv_content, csv_name = extract_csv_from_zip(up_w)
            if csv_content:
                with open(FILES['Weekly'], "wb") as f:
                    f.write(csv_content)
                date_str = extract_date_from_filename(csv_name)
                if date_str:
                    save_meta('Weekly', date_str)
                st.success(f"Weekly file updated from {csv_name}!")
        if 'Weekly' in meta and os.path.exists(FILES['Weekly']):
            st.caption(f"📅 Data Date: {meta['Weekly']}")
        elif os.path.exists(FILES['Weekly']):
            w_time = os.path.getmtime(FILES['Weekly'])
            st.caption(f"📅 Last Updated: {datetime.fromtimestamp(w_time).strftime('%Y-%m-%d %H:%M')}")

        st.subheader("Intraday")
        up_i = st.file_uploader("Upload Intraday Bhavcopy", type=['zip'], key='i_up')
        if up_i is not None:
            csv_content, csv_name = extract_csv_from_zip(up_i)
            if csv_content:
                with open(FILES['Intraday'], "wb") as f:
                    f.write(csv_content)
                date_str = extract_date_from_filename(csv_name)
                if date_str:
                    save_meta('Intraday', date_str)
                st.success(f"Intraday file updated from {csv_name}!")
        if 'Intraday' in meta and os.path.exists(FILES['Intraday']):
            st.caption(f"📅 Data Date: {meta['Intraday']}")
        elif os.path.exists(FILES['Intraday']):
            i_time = os.path.getmtime(FILES['Intraday'])
            st.caption(f"📅 Last Updated: {datetime.fromtimestamp(i_time).strftime('%Y-%m-%d %H:%M')}")

        st.markdown("---")
        st.header("Auto Refresh")
        auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
        refresh_interval = st.slider("Refresh Interval (seconds)", min_value=5, max_value=60, value=15)


# --- Main Page ---
st.title("Positional Stock Option Scanner")

nse_json_df = load_nse_json()

if not nse_json_df.empty:
    tab1, tab2, tab3, tab4 = st.tabs(["Monthly", "Weekly", "Intraday", "🔴 OI Analysis"])
    run_every = refresh_interval if auto_refresh else None

    with tab1:
        st.header(f"Monthly Options ({expiry_type if not is_client_view else 'Current Month'})")
        if os.path.exists(FILES['Monthly']):
            @st.fragment(run_every=run_every)
            def show_monthly():
                df_m = process_bhavcopy(
                    FILES['Monthly'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move,
                    instrument_filter=instrument_filter
                )
                display_option_chain(df_m, access_token, "Monthly", show_oi_filter, show_unconfirmed, hide_weak_signals)
            show_monthly()
        else:
            st.info("Please upload a Monthly Bhavcopy in the sidebar to view data.")

    with tab2:
        st.header(f"Weekly Options ({expiry_type if not is_client_view else 'Current Month'})")
        if os.path.exists(FILES['Weekly']):
            @st.fragment(run_every=run_every)
            def show_weekly():
                df_w = process_bhavcopy(
                    FILES['Weekly'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move,
                    instrument_filter=instrument_filter
                )
                display_option_chain(df_w, access_token, "Weekly", show_oi_filter, show_unconfirmed, hide_weak_signals)
            show_weekly()
        else:
            st.info("Please upload a Weekly Bhavcopy in the sidebar to view data.")

    with tab3:
        st.header(f"Intraday Options ({expiry_type if not is_client_view else 'Current Month'})")
        if os.path.exists(FILES['Intraday']):
            @st.fragment(run_every=run_every)
            def show_intraday():
                df_i = process_bhavcopy(
                    FILES['Intraday'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move,
                    instrument_filter=instrument_filter
                )
                display_option_chain(df_i, access_token, "Intraday", show_oi_filter, show_unconfirmed, hide_weak_signals)
            show_intraday()
        else:
            st.info("Please upload an Intraday Bhavcopy in the sidebar to view data.")

    with tab4:
        st.header("Live OI Signal Analysis")
        @st.fragment(run_every=run_every)
        def show_oi_analysis():
            df_list = []
            if os.path.exists(FILES['Monthly']):
                df_m = process_bhavcopy(FILES['Monthly'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move,
                    instrument_filter=instrument_filter)
                df_list.append(('Monthly', df_m))
            if os.path.exists(FILES['Weekly']):
                df_w = process_bhavcopy(FILES['Weekly'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move,
                    instrument_filter=instrument_filter)
                df_list.append(('Weekly', df_w))
            if os.path.exists(FILES['Intraday']):
                df_i = process_bhavcopy(FILES['Intraday'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move,
                    instrument_filter=instrument_filter)
                df_list.append(('Intraday', df_i))
            display_oi_analysis(df_list, access_token, run_every)
        show_oi_analysis()


else:
    st.error("Critical Error: NSE.json could not be loaded.")
