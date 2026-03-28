"""
Gonnomi | Verze 3.0
===================
Stack: Streamlit · yfinance · pandas · plotly · curl_cffi · deep_translator

Install:
    pip install streamlit yfinance pandas plotly curl_cffi deep_translator

Run:
    streamlit run app.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math, warnings
warnings.filterwarnings("ignore")

# deep_translator je volitelný – bez něj se popis zobrazí v angličtině
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_OK = True
except ImportError:
    TRANSLATOR_OK = False

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────
SMOOTH_LIMIT = 500

# Rozšířený slovník pro našeptávač (ticker → název)
TICKER_MAP = {
    "AAPL":"Apple Inc.","MSFT":"Microsoft Corp.","GOOGL":"Alphabet Inc.",
    "AMZN":"Amazon.com Inc.","META":"Meta Platforms","TSLA":"Tesla Inc.",
    "NVDA":"NVIDIA Corp.","BRK-B":"Berkshire Hathaway B","JPM":"JPMorgan Chase",
    "V":"Visa Inc.","MA":"Mastercard","UNH":"UnitedHealth Group",
    "JNJ":"Johnson & Johnson","XOM":"Exxon Mobil","PG":"Procter & Gamble",
    "HD":"Home Depot","BAC":"Bank of America","ABBV":"AbbVie Inc.",
    "MRK":"Merck & Co.","CVX":"Chevron Corp.","LLY":"Eli Lilly",
    "AVGO":"Broadcom Inc.","PEP":"PepsiCo","KO":"Coca-Cola",
    "COST":"Costco","TMO":"Thermo Fisher","MCD":"McDonald's",
    "CSCO":"Cisco Systems","WMT":"Walmart","CRM":"Salesforce",
    "NEE":"NextEra Energy","ACN":"Accenture","AMD":"AMD","INTC":"Intel",
    "NFLX":"Netflix","DIS":"Walt Disney","PYPL":"PayPal",
    "^GSPC":"S&P 500","^DJI":"Dow Jones","^IXIC":"NASDAQ Composite",
    "^RUT":"Russell 2000","^FTSE":"FTSE 100","^DAX":"DAX",
    "^N225":"Nikkei 225","^HSI":"Hang Seng",
    "GC=F":"Gold Futures","SI=F":"Silver Futures","CL=F":"Crude Oil WTI",
    "BZ=F":"Brent Crude","NG=F":"Natural Gas","ZW=F":"Wheat Futures",
    "BTC-USD":"Bitcoin","ETH-USD":"Ethereum","BNB-USD":"BNB",
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY",
}
# Invertovaný map: název → ticker
NAME_MAP = {v.lower(): k for k, v in TICKER_MAP.items()}

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Gonnomi | Verze 3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# SIDEBAR – navigace + theme
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Gonnomi")
    st.caption("Verze 3.0")
    st.markdown("---")
    page  = st.radio("Navigace", ["🏠 Overview", "📊 Markets"], label_visibility="collapsed")
    theme = st.radio("🎨 Režim", ["Dark", "Light"], horizontal=True)
    st.markdown("---")

# ──────────────────────────────────────────────
# THEME TOKENS
# ──────────────────────────────────────────────
if theme == "Dark":
    BG=       "#0e1117"; CARD=   "#1a1d27"; CARD2=  "#12151e"
    TEXT=     "#ffffff"; SUB=    "#aaaaaa"; BORDER= "#2a2d3a"
    ACCENT=   "#00c4b4"; PLOT_BG="#0e1117"
    BTN_BG=   "#1a1d27"; BTN_TXT="#ffffff"; BTN_BRD="#2a2d3a"
    BTN_ABGD= "#00c4b4"; BTN_ATXT="#0e1117"; BTN_ABRD="#00c4b4"
    TBL_HDR=  "#1a1d27"; TBL_ROW="#0e1117"; TBL_ALT="#12151e"
else:
    BG=       "#f5f7fa"; CARD=   "#ffffff"; CARD2=  "#eef1f5"
    TEXT=     "#111111"; SUB=    "#555555"; BORDER= "#d0d5dd"
    ACCENT=   "#0077b6"; PLOT_BG="#ffffff"
    BTN_BG=   "#ffffff"; BTN_TXT="#333333"; BTN_BRD="#d0d5dd"
    BTN_ABGD= "#0077b6"; BTN_ATXT="#ffffff"; BTN_ABRD="#0077b6"
    TBL_HDR=  "#e8ecf0"; TBL_ROW="#ffffff"; TBL_ALT="#f5f7fa"

GREEN="#00c853"; RED="#ff1744"; YELLOW="#ffd600"

# ──────────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
html,body,[data-testid="stAppViewContainer"]{{background:{BG}!important;color:{TEXT}!important;}}
[data-testid="stSidebar"]{{background:{CARD2}!important;}}
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] div{{color:{TEXT}!important;}}
h1,h2,h3,h4,h5,h6{{color:{TEXT}!important;}}

/* Tabulky – plná adaptace na dark/light */
[data-testid="stDataFrame"] table{{background:{TBL_ROW}!important;color:{TEXT}!important;border-collapse:collapse;}}
[data-testid="stDataFrame"] th{{background:{TBL_HDR}!important;color:{TEXT}!important;border:1px solid {BORDER};padding:6px 12px;}}
[data-testid="stDataFrame"] td{{background:{TBL_ROW}!important;color:{TEXT}!important;border:1px solid {BORDER};padding:6px 12px;}}
[data-testid="stDataFrame"] tr:nth-child(even) td{{background:{TBL_ALT}!important;}}

/* Tlačítka období – kontrastní v obou režimech */
div[data-testid="column"] button[kind="secondary"]{{
    background:{BTN_BG}!important;color:{BTN_TXT}!important;
    border:1px solid {BTN_BRD}!important;font-weight:600;
}}
div[data-testid="column"] button[kind="primary"]{{
    background:{BTN_ABGD}!important;color:{BTN_ATXT}!important;
    border:1px solid {BTN_ABRD}!important;font-weight:700;
}}
div[data-testid="column"] button:hover{{border-color:{ACCENT}!important;color:{ACCENT}!important;}}

/* Komponenty */
.metric-card{{background:{CARD};border-radius:10px;padding:16px 20px;
              margin-bottom:10px;border-left:3px solid {ACCENT};}}
.metric-label{{color:{SUB};font-size:12px;text-transform:uppercase;letter-spacing:1px;}}
.metric-value{{font-size:22px;font-weight:700;color:{TEXT};}}
.section-header{{font-size:20px;font-weight:700;border-bottom:1px solid {BORDER};
                 padding-bottom:6px;margin-top:24px;margin-bottom:14px;color:{ACCENT};}}
.ticker-badge{{display:inline-block;background:{CARD2};color:{ACCENT};
               border:1px solid {BORDER};border-radius:6px;
               padding:2px 10px;font-size:14px;font-weight:700;margin-left:10px;}}
.status-open{{color:{GREEN};font-weight:700;}}
.status-pre{{color:{YELLOW};font-weight:700;}}
.status-after{{color:#ff9800;font-weight:700;}}
.status-closed{{color:{RED};font-weight:700;}}
.analysis-box{{background:{CARD};border-radius:12px;padding:24px 28px;
               border:1px solid {BORDER};line-height:1.8;color:{TEXT};}}
.pillar{{background:{CARD2};border-radius:8px;padding:14px 18px;
         margin-bottom:10px;border-left:3px solid {YELLOW};}}
.pillar-title{{font-weight:700;color:{YELLOW};margin-bottom:6px;}}
.pillar-body{{color:{TEXT};font-size:14px;line-height:1.7;}}
.search-hint{{color:{SUB};font-size:13px;margin-top:4px;}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def fmt_large(n):
    if n is None or (isinstance(n,float) and math.isnan(n)): return "N/A"
    try:
        n=float(n)
        if abs(n)>=1e12: return f"${n/1e12:.2f}T"
        if abs(n)>=1e9:  return f"${n/1e9:.2f}B"
        if abs(n)>=1e6:  return f"${n/1e6:.2f}M"
        return f"${n:,.0f}"
    except: return "N/A"

def fmt_pct(n):
    if n is None or (isinstance(n,float) and math.isnan(n)): return "N/A"
    try: return f"{float(n)*100:.2f} %"
    except: return "N/A"

def safe(info,key,default="N/A"):
    v=info.get(key,default); return default if v is None else v

def mcard(col,label,val):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{val}</div>'
        f'</div>',unsafe_allow_html=True)

def safe_yield(raw,div_paid,mktcap):
    try:
        v=float(raw)
        if 0<=v<=0.20: return v,False
    except: pass
    try:
        m=abs(float(div_paid))/float(mktcap)
        if 0<=m<=0.20: return m,True
    except: pass
    return 0.0,True

def calc_buyback_yield(shares_full,curr_price):
    if shares_full is None or shares_full.empty: return 0.0,"N/A",False
    s=shares_full.sort_index()
    if len(s)<2: return 0.0,"N/A",False
    s_now=float(s.iloc[-1])
    s_1y=s[s.index<=s.index[-1]-timedelta(days=365)]
    if s_1y.empty: return 0.0,"N/A",False
    s1v=float(s_1y.iloc[-1])
    if s1v<=0: return 0.0,"N/A",False
    by=max((s1v-s_now)/s1v,0.0)
    return by,fmt_large(max(s1v-s_now,0)*curr_price),True

def market_status(info):
    """Vrátí HTML badge se stavem trhu."""
    state=info.get("marketState","")
    if state=="REGULAR":   return '<span class="status-open">● Trh otevřen</span>'
    if state=="PRE":       return '<span class="status-pre">◐ Pre-market</span>'
    if state in ("POST","POSTPOST"): return '<span class="status-after">◑ After-hours</span>'
    return '<span class="status-closed">○ Trh zavřen</span>'

# ──────────────────────────────────────────────
# OMNI-SEARCH (Autocomplete)
# ──────────────────────────────────────────────
def resolve_ticker(query: str) -> str:
    """Převede název / partial match na ticker symbol."""
    q = query.strip()
    if not q: return ""
    # Přímý ticker match
    if q.upper() in TICKER_MAP: return q.upper()
    # Přesný název match
    if q.lower() in NAME_MAP: return NAME_MAP[q.lower()]
    # Partial match v názvech
    for name, tkr in NAME_MAP.items():
        if q.lower() in name: return tkr
    # Zkusíme raw jako ticker
    return q.upper()

def autocomplete_options(query: str) -> list[str]:
    """Vrátí seznam návrhů pro našeptávač."""
    if len(query) < 1: return []
    q = query.lower()
    results = []
    for tkr, name in TICKER_MAP.items():
        if q in tkr.lower() or q in name.lower():
            results.append(f"{tkr} — {name}")
    return results[:10]

# ──────────────────────────────────────────────
# CACHED LOADERS
# ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_ticker(ticker: str):
    try:
        t      = yf.Ticker(ticker.upper())
        info   = dict(t.info)
        inc    = t.financials
        bal    = t.balance_sheet
        cf     = t.cashflow
        shares = t.get_shares_full(start="2018-01-01")
        if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
            return None,None,None,None,None
        return info,inc,bal,cf,shares
    except Exception as e:
        st.error(f"Chyba: {e}"); return None,None,None,None,None

@st.cache_data(ttl=300, show_spinner=False)
def load_hist(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        t  = yf.Ticker(ticker.upper())
        df = t.history(period=period, interval=interval)
        if df.empty: return pd.DataFrame()
        df = df[["Close"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except: return pd.DataFrame()

@st.cache_data(show_spinner=False)
def aggregate(df: pd.DataFrame, max_pts: int) -> pd.DataFrame:
    n=len(df)
    if n<=max_pts: return df
    bs=max(1,n//max_pts)
    agg=df.groupby(df.index//bs).agg({"Close":"mean"})
    step=(df.index[-1]-df.index[0])/max(len(agg)-1,1)
    agg.index=pd.date_range(start=df.index[0],periods=len(agg),freq=step)
    agg.index.name="Datum"
    return agg

@st.cache_data(ttl=86400, show_spinner=False)
def translate_text(text: str) -> str:
    """Přeloží text EN→CS pomocí deep_translator (cachováno 24h)."""
    if not TRANSLATOR_OK or not text: return text
    try:
        # Translator zvládne max ~5000 znaků naráz
        chunks=[text[i:i+4500] for i in range(0,len(text),4500)]
        return " ".join(GoogleTranslator(source="en",target="cs").translate(c) for c in chunks)
    except:
        return text

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────
if "ticker" not in st.session_state:     st.session_state.ticker    = "AAPL"
if "tr_selected" not in st.session_state: st.session_state.tr_selected = "1Y"
if "search_query" not in st.session_state: st.session_state.search_query = ""

# ══════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════
if page == "🏠 Overview":

    st.markdown(f"# 📈 Gonnomi <span style='font-size:16px;color:{SUB}'>v3.0</span>",
                unsafe_allow_html=True)
    st.markdown(f"<p style='color:{SUB}'>Profesionální investiční platforma · Value Investing · DCF · Analýza trhu</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    # ── OMNI-SEARCH ──────────────────────────
    st.markdown(f"### 🔍 Vyhledat akcii, index, komoditu nebo kryptoměnu")

    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        raw_query = st.text_input(
            "Vyhledávání",
            value=st.session_state.search_query,
            placeholder="Zadej ticker (AAPL) nebo název (Apple)…",
            label_visibility="collapsed",
        )
    with col_btn:
        go_btn = st.button("🔎 Hledat", use_container_width=True, type="primary")

    # Našeptávač
    if raw_query and len(raw_query) >= 1:
        suggestions = autocomplete_options(raw_query)
        if suggestions:
            chosen = st.selectbox(
                "Návrhy",
                options=["— vyber nebo pokračuj psaním —"] + suggestions,
                label_visibility="collapsed",
            )
            if chosen != "— vyber nebo pokračuj psaním —":
                raw_query = chosen.split(" — ")[0]

    st.markdown(
        f'<div class="search-hint">💡 Příklady: AAPL · Apple · S&P 500 · Bitcoin · Gold Futures · EUR/USD</div>',
        unsafe_allow_html=True,
    )

    if go_btn and raw_query:
        resolved = resolve_ticker(raw_query.split(" — ")[0])
        st.session_state.ticker       = resolved
        st.session_state.search_query = raw_query

    ticker_input = st.session_state.ticker

    # ── LOAD & DISPLAY OVERVIEW ───────────────
    with st.spinner(f"Načítám **{ticker_input}**…"):
        info,_,_,_,_ = load_ticker(ticker_input)

    if info is None:
        st.error("Ticker nenalezen. Zkus jiný symbol nebo název.")
    else:
        curr_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
        prev_close = float(info.get("previousClose") or curr_price)
        chg        = ((curr_price-prev_close)/prev_close*100) if prev_close else 0
        name       = safe(info,"longName",ticker_input)
        sector     = safe(info,"sector")
        industry   = safe(info,"industry")
        website    = safe(info,"website")
        mktcap     = fmt_large(info.get("marketCap"))
        employees  = f"{info['fullTimeEmployees']:,}" if info.get("fullTimeEmployees") else "N/A"
        status_html= market_status(info)

        # Header
        col_h1, col_h2 = st.columns([3,1])
        with col_h1:
            st.markdown(
                f"## {name} "
                f'<span class="ticker-badge">{ticker_input}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(status_html, unsafe_allow_html=True)
        with col_h2:
            chg_color = GREEN if chg>=0 else RED
            st.markdown(
                f"<div style='text-align:right'>"
                f"<div style='font-size:32px;font-weight:800;color:{TEXT}'>${curr_price:.2f}</div>"
                f"<div style='font-size:18px;color:{chg_color};font-weight:700'>"
                f"{'▲' if chg>=0 else '▼'} {abs(chg):.2f} %</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Metriky
        c1,c2,c3,c4,c5 = st.columns(5)
        mcard(c1,"Market Cap",   mktcap)
        mcard(c2,"Sektor",       sector)
        mcard(c3,"Industrie",    industry)
        mcard(c4,"Zaměstnanci",  employees)
        mcard(c5,"Web",         f"[{website}]({website})")

        # Popis – přeložený do češtiny
        st.markdown('<div class="section-header">🏢 O společnosti</div>', unsafe_allow_html=True)
        biz_en = safe(info,"longBusinessSummary","")
        if biz_en:
            with st.spinner("Překládám popis do češtiny…"):
                biz_cs = translate_text(biz_en)
            st.markdown(
                f'<div class="analysis-box">{biz_cs}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Popis společnosti není k dispozici.")

        st.markdown(
            f"<br><small style='color:{SUB}'>Analytický průvodce a hloubková analýza jsou dostupné v sekci "
            f"<b>📊 Markets</b>.</small>",
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════
# PAGE: MARKETS
# ══════════════════════════════════════════════
elif page == "📊 Markets":

    ticker_input = st.session_state.ticker

    # Quick search v Markets
    col_qs, col_qb = st.columns([5,1])
    with col_qs:
        qs = st.text_input("Ticker / Název", value=ticker_input,
                           placeholder="AAPL, Microsoft, Gold…",
                           label_visibility="collapsed")
    with col_qb:
        if st.button("🔎", use_container_width=True):
            st.session_state.ticker = resolve_ticker(qs.split(" — ")[0])
            st.rerun()

    # DCF params v expander (čistý sidebar)
    with st.sidebar:
        with st.expander("⚙️ DCF Parametry", expanded=False):
            with st.form("dcf_form"):
                discount_rate = st.slider("WACC (%)",6.0,20.0,10.0,0.5)/100
                growth_rate   = st.number_input("Growth Rate 1–5y (%)",value=10.0,step=0.5)/100
                terminal_gr   = st.number_input("Terminal Growth (%)",value=3.0,step=0.5)/100
                mos_required  = st.number_input("Margin of Safety (%)",value=20.0,step=5.0)/100
                smoothing     = st.slider("Spline tension",0.0,1.3,0.8,0.05)
                show_ma       = st.checkbox("Klouzavý průměr (MA)",value=True)
                ma_window     = st.slider("Okno MA",5,200,20,5,disabled=not show_ma)
                st.form_submit_button("Použít", type="primary", use_container_width=True)

    # Defaults při prvním renderu (před odesláním formuláře)
    if "discount_rate" not in dir(): discount_rate=0.10
    if "growth_rate"   not in dir(): growth_rate=0.10
    if "terminal_gr"   not in dir(): terminal_gr=0.03
    if "mos_required"  not in dir(): mos_required=0.20
    if "smoothing"     not in dir(): smoothing=0.8
    if "show_ma"       not in dir(): show_ma=True
    if "ma_window"     not in dir(): ma_window=20

    # LOAD DATA
    with st.spinner(f"Načítám {ticker_input}…"):
        info,inc,bal,cf,shares_full = load_ticker(ticker_input)

    if info is None:
        st.error("Ticker nenalezen."); st.stop()

    curr_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
    market_cap = float(info.get("marketCap") or 0)
    shares_out = float(info.get("sharesOutstanding") or 1)
    name       = safe(info,"longName",ticker_input)
    prev_close = float(info.get("previousClose") or curr_price)
    chg        = ((curr_price-prev_close)/prev_close*100) if prev_close else 0

    # Header
    col_h,col_p = st.columns([3,1])
    with col_h:
        st.markdown(
            f"## {name} "
            f'<span class="ticker-badge">{ticker_input}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(market_status(info), unsafe_allow_html=True)
    with col_p:
        chg_color = GREEN if chg>=0 else RED
        st.markdown(
            f"<div style='text-align:right'>"
            f"<div style='font-size:28px;font-weight:800;color:{TEXT}'>${curr_price:.2f}</div>"
            f"<div style='font-size:16px;color:{chg_color};font-weight:700'>"
            f"{'▲' if chg>=0 else '▼'} {abs(chg):.2f} %</div>"
            f"</div>",unsafe_allow_html=True)

    # TABS
    tab1,tab2,tab3,tab4 = st.tabs(["📉 Graf & Metriky","📊 360° Analýza","💰 DCF Model","📋 Výkazy"])

    # ──────────────────────────────────────────
    # TAB 1 – GRAF & METRIKY
    # ──────────────────────────────────────────
    with tab1:
        RANGES = {
            "1D":("1d","5m"),"1W":("5d","30m"),"1M":("1mo","1d"),
            "3M":("3mo","1d"),"6M":("6mo","1d"),"YTD":("ytd","1d"),
            "1Y":("1y","1d"),"5Y":("5y","1wk"),"ALL":("max","1mo"),
        }
        # Intervaly kde se nezobrazuje čas (jen datum)
        DATE_ONLY_RANGES = {"1M","3M","6M","YTD","1Y","5Y","ALL"}

        btn_cols = st.columns(len(RANGES))
        for i,label in enumerate(RANGES):
            is_active = label==st.session_state.tr_selected
            if btn_cols[i].button(label, key=f"tr_{label}",
                                  use_container_width=True,
                                  type="primary" if is_active else "secondary"):
                st.session_state.tr_selected=label; st.rerun()

        period,interval = RANGES[st.session_state.tr_selected]
        hist_raw = load_hist(ticker_input,period,interval)

        if hist_raw is not None and not hist_raw.empty:
            n_raw = len(hist_raw)
            hist  = aggregate(hist_raw,SMOOTH_LIMIT)
            n_agg = len(hist)
            was_agg = n_raw>SMOOTH_LIMIT

            # Klouzavý průměr
            if show_ma and len(hist)>=ma_window:
                hist=hist.copy()
                hist["MA"]=hist["Close"].rolling(window=ma_window,min_periods=1).mean()

            close      = hist["Close"]
            prev_vals  = close.shift(1)
            abs_chg    = close - prev_vals
            pct_chg    = abs_chg / prev_vals * 100
            first_p    = float(close.iloc[0])
            last_p     = float(close.iloc[-1])
            is_up      = last_p>=first_p
            lc         = GREEN if is_up else RED
            y_min      = float(close.min())*0.99
            y_max      = float(close.max())*1.01

            # Formát data v hoveru
            date_only  = st.session_state.tr_selected in DATE_ONLY_RANGES
            x_fmt      = "%d.%m.%Y" if date_only else "%d.%m.%Y %H:%M"

            # Tooltip s abs. a % změnou
            hover_texts = []
            for i_h in range(len(close)):
                d   = close.index[i_h]
                p   = close.iloc[i_h]
                d_str = d.strftime(x_fmt)
                if i_h==0:
                    hover_texts.append(f"<b>{d_str}</b><br>Cena: <b>${p:.2f}</b>")
                else:
                    ac = abs_chg.iloc[i_h]
                    pc = pct_chg.iloc[i_h]
                    sign = "+" if ac>=0 else ""
                    hover_texts.append(
                        f"<b>{d_str}</b><br>"
                        f"Cena: <b>${p:.2f}</b><br>"
                        f"Změna: <b>{sign}{ac:.2f} USD ({sign}{pc:.2f} %)</b>"
                    )

            fig=go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["Close"],
                mode="lines",
                name="Cena",
                line=dict(color=lc,width=2.5,shape="spline",smoothing=smoothing),
                fill="tozeroy",
                fillgradient=dict(
                    type="vertical",
                    colorscale=[
                        [0.0,"rgba(0,200,83,0.0)"  if is_up else "rgba(255,23,68,0.0)"],
                        [1.0,"rgba(0,200,83,0.15)" if is_up else "rgba(255,23,68,0.15)"],
                    ],
                ),
                text=hover_texts,
                hovertemplate="%{text}<extra></extra>",
                hoverlabel=dict(bgcolor=CARD,font_color=TEXT,bordercolor=BORDER),
            ))

            if show_ma and "MA" in hist.columns and hist["MA"].notna().any():
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist["MA"],
                    mode="lines", name=f"MA {ma_window}",
                    line=dict(color=YELLOW,width=1.5,dash="dot",shape="spline",smoothing=0.5),
                    hovertemplate=f"MA{ma_window}: <b>$%{{y:.2f}}</b><extra></extra>",
                ))

            fig.update_layout(
                paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                font_color=TEXT, height=420,
                margin=dict(l=0,r=0,t=10,b=0),
                showlegend=show_ma,
                legend=dict(orientation="h",yanchor="bottom",y=1.01,
                            xanchor="left",x=0,font=dict(color=TEXT)),
                dragmode=False, hovermode="x unified",
                xaxis=dict(showgrid=False,zeroline=False,showline=False,
                           tickfont=dict(color=SUB,size=11),fixedrange=True),
                yaxis=dict(showgrid=False,zeroline=False,showline=False,
                           tickprefix="$",tickfont=dict(color=SUB,size=11),
                           range=[y_min,y_max],fixedrange=True),
            )
            st.plotly_chart(fig,use_container_width=True,
                            config={"displayModeBar":False,"scrollZoom":False,"staticPlot":False})

            # Mini stats
            period_chg = (last_p-first_p)/first_p*100 if first_p else 0
            ca,cb,cc,cd = st.columns(4)
            ca.metric("Začátek období", f"${first_p:.2f}")
            cb.metric("Konec období",   f"${last_p:.2f}")
            cc.metric("Změna období",   f"{'+' if period_chg>=0 else ''}{period_chg:.2f} %")
            cd.metric("Bodů v grafu",   f"{n_agg:,}",
                      help=f"Agregováno z {n_raw:,}" if was_agg else "Bez agregace")
            if was_agg:
                st.caption(f"ℹ️ Data agregována z {n_raw:,} → {n_agg:,} bodů (bucket avg).")
        else:
            st.warning("Graf není k dispozici.")

        # KLÍČOVÉ METRIKY
        st.markdown('<div class="section-header">📊 Klíčové metriky</div>',unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        mcard(c1,"P/E (TTM)",   safe(info,"trailingPE"))
        mcard(c2,"Forward P/E", safe(info,"forwardPE"))
        mcard(c3,"P/B",         safe(info,"priceToBook"))
        mcard(c4,"EV/EBITDA",   safe(info,"enterpriseToEbitda"))
        c1,c2,c3,c4 = st.columns(4)
        mcard(c1,"ROE",             fmt_pct(info.get("returnOnEquity")))
        mcard(c2,"Operating Margin",fmt_pct(info.get("operatingMargins")))
        mcard(c3,"Debt/Equity",     safe(info,"debtToEquity"))
        mcard(c4,"FCF",             fmt_large(info.get("freeCashflow")))

    # ──────────────────────────────────────────
    # TAB 2 – 360° ANALÝZA
    # ──────────────────────────────────────────
    with tab2:
        # Valuace
        st.markdown('<div class="section-header">📊 Valuace</div>',unsafe_allow_html=True)
        earnings_date="N/A"
        if info.get("earningsTimestamps"):
            try: earnings_date=datetime.fromtimestamp(info["earningsTimestamps"][0]).strftime("%d.%m.%Y")
            except: pass
        st.dataframe(pd.DataFrame({
            "Metrika":["P/E (TTM)","Forward P/E","P/S","P/B","EV/EBITDA","Nejbližší Earnings"],
            "Hodnota":[safe(info,"trailingPE"),safe(info,"forwardPE"),
                       safe(info,"priceToSalesTrailing12Months"),
                       safe(info,"priceToBook"),safe(info,"enterpriseToEbitda"),earnings_date]
        }),use_container_width=True,hide_index=True)

        # Rentabilita
        st.markdown('<div class="section-header">💹 Rentabilita & Zdraví</div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.dataframe(pd.DataFrame({
                "Metrika":["ROE","ROA","Gross Margin","Operating Margin","Profit Margin"],
                "Hodnota":[fmt_pct(info.get(k)) for k in
                           ["returnOnEquity","returnOnAssets","grossMargins",
                            "operatingMargins","profitMargins"]]
            }),use_container_width=True,hide_index=True)
        with c2:
            st.dataframe(pd.DataFrame({
                "Metrika":["Debt/Equity","Current Ratio","Total Debt","Cash"],
                "Hodnota":[safe(info,"debtToEquity"),safe(info,"currentRatio"),
                           fmt_large(info.get("totalDebt")),fmt_large(info.get("totalCash"))]
            }),use_container_width=True,hide_index=True)

        # Buybacky
        st.markdown('<div class="section-header">💵 Dividendy & Buybacky</div>',unsafe_allow_html=True)
        div_yield_raw,div_est=safe_yield(
            info.get("dividendYield"),
            info.get("lastDividendValue",0)*shares_out*4 if info.get("lastDividendValue") else None,
            market_cap)
        bb_yield,bb_vol,bb_avail=calc_buyback_yield(shares_full,curr_price)
        total_sh=fmt_pct(div_yield_raw+bb_yield) if bb_avail else "N/A"
        c1,c2,c3,c4=st.columns(4)
        mcard(c1,f"Dividend Yield{' *' if div_est else ''}",fmt_pct(div_yield_raw))
        mcard(c2,"Buyback Yield (1Y)",fmt_pct(bb_yield) if bb_avail else "N/A")
        mcard(c3,"Total Shareholder Yield",total_sh)
        mcard(c4,"Buyback objem (1Y)",bb_vol)
        st.markdown(f"**Payout Ratio:** {fmt_pct(info.get('payoutRatio'))}")

        # Share Count – spline
        st.markdown('<div class="section-header">📉 Share Count Trend (5 let)</div>',unsafe_allow_html=True)
        if shares_full is not None and not shares_full.empty:
            sh=shares_full.sort_index()
            fig2=go.Figure()
            fig2.add_trace(go.Scatter(
                x=sh.index, y=sh.values/1e9,
                mode="lines",
                line=dict(color=ACCENT,width=2,shape="spline",smoothing=0.8),
                fill="tozeroy",fillcolor="rgba(0,196,180,0.08)",
                name="Akcie (mld.)"
            ))
            fig2.update_layout(
                paper_bgcolor=PLOT_BG,plot_bgcolor=PLOT_BG,
                font_color=TEXT,height=260,margin=dict(l=0,r=0,t=10,b=0),
                yaxis=dict(title="Akcie (mld.)",showgrid=False,zeroline=False,
                           tickfont=dict(color=TEXT)),
                xaxis=dict(showgrid=False,zeroline=False,tickfont=dict(color=TEXT)),
                hovermode="x unified",
            )
            st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
        else:
            st.info("Data o počtu akcií nejsou k dispozici.")

        # Analytický průvodce
        st.markdown('<div class="section-header">🔍 Analytický průvodce</div>',unsafe_allow_html=True)
        pillars=[
            ("1️⃣ Monopol / Moat",
             f"Market Cap: **{fmt_large(market_cap)}** | Sektor: **{safe(info,'sector')}**\n\n"
             "👉 Tržní podíl, ekosystém, síťový efekt, bariéry vstupu.\n\n"
             "✏️ **ANO / NE / SPORNÉ**"),
            ("2️⃣ Klíčové metriky",
             f"| Metrika | Hodnota |\n|---|---|\n"
             f"| Tržby | {fmt_large(info.get('totalRevenue'))} |\n"
             f"| EPS | {safe(info,'trailingEps')} |\n"
             f"| FCF | {fmt_large(info.get('freeCashflow'))} |\n"
             f"| Op. marže | {fmt_pct(info.get('operatingMargins'))} |\n"
             f"| D/E | {safe(info,'debtToEquity')} |"),
            ("3️⃣ Investiční teze","👉 3 růstové motory a 3 rizika. Zdroj: 10-K, earnings call."),
            ("4️⃣ Alokace kapitálu",
             f"Dividenda: {fmt_pct(div_yield_raw)} | Buyback: {fmt_pct(bb_yield) if bb_avail else 'N/A'}\n\n"
             "✏️ **ANO / NE / SPORNÉ**"),
            ("5️⃣ Konkurence","| Firma | Tržby | Marže | P/E |\n|---|---|---|---|\n| … |"),
            ("6️⃣ Insideři & Analytici",
             f"Rating: `{safe(info,'recommendationKey','N/A').upper()}` | "
             f"Cíl: ${safe(info,'targetMeanPrice')} (${safe(info,'targetLowPrice')}–${safe(info,'targetHighPrice')})\n\n"
             "[OpenInsider.com](https://openinsider.com)"),
            ("7️⃣ Scorecard",
             "| Kritérium | ✅/❌/⚠️ |\n|---|---|\n"
             "| Moat | |\n| Finanční síla | |\n| Růst | |\n"
             "| Akcionáři | |\n| Management | |\n| Stabilita | |"),
            ("8️⃣ Závěr",f"✏️ **Je {ticker_input} zisková mašina? ANO / NE – proč?**"),
            ("9️⃣ Shrnutí pro investora","👉 Argumenty pro/proti, riziko vs. potenciál."),
        ]
        st.markdown('<div class="analysis-box">',unsafe_allow_html=True)
        for title,body in pillars:
            st.markdown(
                f'<div class="pillar"><div class="pillar-title">{title}</div>'
                f'<div class="pillar-body">',unsafe_allow_html=True)
            st.markdown(body)
            st.markdown('</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

    # ──────────────────────────────────────────
    # TAB 3 – DCF MODEL
    # ──────────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-header">💰 Discounted Cash Flow (10Y)</div>',
                    unsafe_allow_html=True)
        fcf=info.get("freeCashflow")
        if fcf is None and cf is not None and not cf.empty:
            for lbl in ["Free Cash Flow","freeCashFlow"]:
                if lbl in cf.index: fcf=float(cf.loc[lbl].iloc[0]); break
        fcf=float(fcf) if fcf else 0.0

        st.info(f"FCF: {fmt_large(fcf)} | Shares: {shares_out/1e9:.2f}B | WACC: {discount_rate*100:.1f} % | Cena: ${curr_price:.2f}")

        def dcf_model(f,gr,tgr,dr,y=10):
            if dr<=tgr: return None
            pv,ct=0.0,f
            for t in range(1,y+1):
                ct*=(1+(gr if t<=5 else tgr)); pv+=ct/(1+dr)**t
            return pv+ct*(1+tgr)/(dr-tgr)/(1+dr)**y

        if fcf>0:
            tv=dcf_model(fcf,growth_rate,terminal_gr,discount_rate)
            fv=(tv/shares_out) if tv else None
            mp=fv*(1-mos_required) if fv else None
            if fv:
                ud=(fv-curr_price)/curr_price*100
                cheap=curr_price<=mp
                c1,c2,c3,c4=st.columns(4)
                mcard(c1,"Fair Value",f"${fv:.2f}")
                mcard(c2,f"MoS ({mos_required*100:.0f} %)",f"${mp:.2f}")
                mcard(c3,"Aktuální cena",f"${curr_price:.2f}")
                mcard(c4,"Upside/Down",f"{'▲' if ud>=0 else '▼'} {abs(ud):.1f} %")
                if cheap:
                    st.success(f"✅ {ticker_input} pod MoS cenou → potenciálně PODHODNOCENÁ.")
                else:
                    st.error(f"❌ {ticker_input} nad MoS cenou → dle DCF NADHODNOCENÁ.")

                # Sensitivity
                st.markdown('<div class="section-header">📐 Sensitivity tabulka</div>',unsafe_allow_html=True)
                gr_r=[growth_rate+d for d in (-0.04,-0.02,0,0.02,0.04)]
                dr_r=[discount_rate+d for d in (-0.02,-0.01,0,0.01,0.02)]
                sens={}
                for dr in dr_r:
                    row={}
                    for gr in gr_r:
                        p=dcf_model(fcf,gr,terminal_gr,dr) if dr>terminal_gr and gr>=0 else None
                        row[f"G={gr*100:.1f}%"]=f"${p/shares_out:.2f}" if p else "N/A"
                    sens[f"D={dr*100:.1f}%"]=row
                st.dataframe(pd.DataFrame(sens).T,use_container_width=True)

                # Waterfall
                st.markdown('<div class="section-header">📊 DCF Waterfall</div>',unsafe_allow_html=True)
                labels,pvs,ct=[],[],fcf
                for t in range(1,11):
                    ct*=(1+(growth_rate if t<=5 else terminal_gr))
                    pvs.append(round(ct/(1+discount_rate)**t/shares_out,2))
                    labels.append(f"Yr {t}")
                if discount_rate>terminal_gr:
                    tv2=(ct*(1+terminal_gr)/(discount_rate-terminal_gr))/(1+discount_rate)**10/shares_out
                    labels.append("Terminální"); pvs.append(round(tv2,2))
                GRID="#2a2d3a" if theme=="Dark" else "#e0e0e0"
                fig3=go.Figure(go.Bar(
                    x=labels,y=pvs,marker_color=[ACCENT]*10+[YELLOW],
                    text=[f"${v:.2f}" for v in pvs],textposition="outside",
                    textfont=dict(color=TEXT),
                ))
                fig3.update_layout(
                    paper_bgcolor=PLOT_BG,plot_bgcolor=PLOT_BG,font_color=TEXT,height=340,
                    margin=dict(l=0,r=0,t=20,b=0),
                    yaxis=dict(title="PV/akcii ($)",gridcolor=GRID,tickfont=dict(color=TEXT)),
                    xaxis=dict(gridcolor=GRID,tickfont=dict(color=TEXT)),
                )
                st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
        else:
            st.warning("FCF není dostupný nebo záporný – DCF nelze spočítat.")

    # ──────────────────────────────────────────
    # TAB 4 – VÝKAZY
    # ──────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-header">📋 Finanční výkazy (4 roky)</div>',unsafe_allow_html=True)
        def show_stmt(df,title):
            if df is None or df.empty: st.warning(f"{title}: N/A"); return
            d=df.copy()
            d.columns=[str(c)[:10] for c in d.columns]
            d=d.apply(pd.to_numeric,errors="coerce")
            d=d.map(lambda x: fmt_large(x) if pd.notna(x) else "N/A")
            st.markdown(f"**{title}**")
            st.dataframe(d,use_container_width=True)
        s1,s2,s3=st.tabs(["Income Statement","Balance Sheet","Cash Flow"])
        with s1: show_stmt(inc,"Income Statement")
        with s2: show_stmt(bal,"Balance Sheet")
        with s3: show_stmt(cf,"Cash Flow")

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<small style='color:{SUB}'>Gonnomi v3.0 · Pouze pro informační účely · "
    "Není investiční poradenství · Data: yfinance/Yahoo Finance</small>",
    unsafe_allow_html=True)
