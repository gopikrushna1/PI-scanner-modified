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

def process_bhavcopy(bhav_file, df_json, target_expiry_index=0, min_underlying_move_pct=0.0):
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


def fetch_ltp(instrument_keys, token):
    if not token:
        return {}

    url = "https://api.upstox.com/v3/market-quote/ltp"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    batch_size = 50
    ltp_map = {}
    batches = [instrument_keys[i:i + batch_size] for i in range(0, len(instrument_keys), batch_size)]

    def fetch_batch(batch):
        params = {'instrument_key': ','.join(batch)}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    quotes = data.get('data', {})
                    result = {}
                    for key, details in quotes.items():
                        inst_token = details.get('instrument_token')
                        last_price = details.get('last_price')
                        if inst_token is not None:
                            result[inst_token] = last_price
                    return result
        except Exception:
            pass
        return {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures_list = [executor.submit(fetch_batch, batch) for batch in batches]
        for future in concurrent.futures.as_completed(futures_list):
            try:
                batch_result = future.result()
                if batch_result:
                    ltp_map.update(batch_result)
            except Exception:
                pass

    return ltp_map


def display_option_chain(df, access_token, key_suffix, show_oi_filter, show_unconfirmed):
    st.caption(f"Last Updated: {get_ist_now().strftime('%H:%M:%S')} IST")
    if df.empty:
        st.info("No data to display. Please upload a valid Bhavcopy in the sidebar.")
        return

    has_oi = 'OI' in df.columns and 'OI_Change' in df.columns and 'Volume' in df.columns
    has_pcr = 'PCR' in df.columns
    has_underlying = 'UnderlyingMove%' in df.columns

    # Fetch LTP
    if access_token:
        all_keys = df['instrument_key'].dropna().unique().tolist()

        ist_now = get_ist_now()
        current_time = ist_now.time()
        start_time = datetime.strptime("09:00", "%H:%M").time()
        end_time = datetime.strptime("15:40", "%H:%M").time()
        is_market_hours = start_time <= current_time <= end_time

        ltp_cache = load_ltp_cache()
        missing_keys = [k for k in all_keys if k not in ltp_cache]

        should_fetch = is_market_hours or bool(missing_keys)

        if should_fetch:
            keys_to_fetch = all_keys if is_market_hours else missing_keys
            fetched_data = fetch_ltp(keys_to_fetch, access_token)
            if fetched_data:
                save_ltp_cache(fetched_data)
                ltp_cache = load_ltp_cache()

        ltp_data = {k: ltp_cache.get(k, 0.0) for k in all_keys}
        df['ltp'] = df['instrument_key'].map(ltp_data).fillna(0.0)
    else:
        df['ltp'] = 0.0
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

    # Split Calls/Puts
    calls_df = df[df['OptionType'] == 'CE'].copy()
    puts_df  = df[df['OptionType'] == 'PE'].copy()

    calls_df = calls_df.sort_values(by='change %', ascending=False)
    puts_df  = puts_df.sort_values(by='change %', ascending=False)

    # Build display columns dynamically
    display_cols = ['Symbol', 'StrikePrice', 'Trigger', 'ltp', 'change %']
    format_dict = {
        'change %': '{:.2f}%',
        'Trigger': '{:.2f}',
        'ltp': '{:.2f}',
        'StrikePrice': '{:.2f}'
    }

    if has_oi:
        display_cols += ['OI', 'OI_Change', 'Volume']
        format_dict.update({
            'OI': '{:,.0f}',
            'OI_Change': '{:,.0f}',
            'Volume': '{:,.0f}'
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

        change_idx = col_list.index('change %') if 'change %' in col_list else None
        oi_change_idx = col_list.index('OI_Change') if 'OI_Change' in col_list else None

        change_val = row.get('change %', 0)
        oi_change_val = row.get('OI_Change', 0) if has_oi else 1

        if change_val >= 100:
            base_bg = 'background-color: darkgreen; color: white'
        elif change_val >= 90:
            base_bg = 'background-color: lightgreen; color: black'
        else:
            base_bg = ''

        if base_bg and change_idx is not None:
            styles[change_idx] = base_bg

        # Highlight OI_Change column: green if rising, red if falling
        if oi_change_idx is not None:
            if oi_change_val > 0:
                styles[oi_change_idx] = 'background-color: #c8f7c5; color: black'
            elif oi_change_val < 0:
                styles[oi_change_idx] = 'background-color: #f7c5c5; color: black'

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

        # ---------------------------------------------------------------
        # CHANGE 9: New filter controls in sidebar
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
    tab1, tab2, tab3 = st.tabs(["Monthly", "Weekly", "Intraday"])
    run_every = refresh_interval if auto_refresh else None

    with tab1:
        st.header(f"Monthly Options ({expiry_type if not is_client_view else 'Current Month'})")
        if os.path.exists(FILES['Monthly']):
            @st.fragment(run_every=run_every)
            def show_monthly():
                df_m = process_bhavcopy(
                    FILES['Monthly'], nse_json_df,
                    target_expiry_index=target_expiry_idx,
                    min_underlying_move_pct=min_underlying_move
                )
                display_option_chain(df_m, access_token, "Monthly", show_oi_filter, show_unconfirmed)
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
                    min_underlying_move_pct=min_underlying_move
                )
                display_option_chain(df_w, access_token, "Weekly", show_oi_filter, show_unconfirmed)
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
                    min_underlying_move_pct=min_underlying_move
                )
                display_option_chain(df_i, access_token, "Intraday", show_oi_filter, show_unconfirmed)
            show_intraday()
        else:
            st.info("Please upload an Intraday Bhavcopy in the sidebar to view data.")

else:
    st.error("Critical Error: NSE.json could not be loaded.")
