"""
Gonnomi | Verze 2.5
===================
Stack: Streamlit · yfinance · pandas · plotly · curl_cffi

Install:
    pip install streamlit yfinance pandas plotly curl_cffi

Run:
    streamlit run app.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import math
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Gonnomi | Verze 2.5",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Gonnomi")
    st.caption("Verze 2.5")
    st.markdown("---")
    ticker_input = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper()
    theme = st.radio("🎨 Režim zobrazení", ["Dark", "Light"], horizontal=True)
    st.markdown("---")
    st.markdown("### ⚙️ DCF Parametry")
    discount_rate = st.slider("Discount Rate / WACC (%)", 6.0, 20.0, 10.0, 0.5) / 100
    growth_rate   = st.number_input("Growth Rate – rok 1–5 (%)", value=10.0, step=0.5) / 100
    terminal_gr   = st.number_input("Terminal Growth Rate (%)",  value=3.0,  step=0.5) / 100
    mos_required  = st.number_input("Margin of Safety (%)",      value=20.0, step=5.0) / 100

# ──────────────────────────────────────────────
# THEME
# ──────────────────────────────────────────────
if theme == "Dark":
    BG       = "#0e1117"
    CARD     = "#1a1d27"
    CARD2    = "#12151e"
    TEXT     = "#ffffff"
    SUB      = "#aaaaaa"
    BORDER   = "#2a2d3a"
    ACCENT   = "#00c4b4"
    PLOT_BG  = "#1a1d27"
    GRID_CLR = "#2a2d3a"
    TABLE_HDR= "#1a1d27"
    TABLE_ROW= "#0e1117"
    TABLE_ALT= "#12151e"
    BTN_BG   = "#1a1d27"
    BTN_ACT  = "#00c4b4"
    BTN_TXT  = "#ffffff"
    BTN_ATXT = "#0e1117"
else:
    BG       = "#f5f7fa"
    CARD     = "#ffffff"
    CARD2    = "#eef1f5"
    TEXT     = "#000000"
    SUB      = "#555555"
    BORDER   = "#d0d5dd"
    ACCENT   = "#0077b6"
    PLOT_BG  = "#ffffff"
    GRID_CLR = "#e0e0e0"
    TABLE_HDR= "#e8ecf0"
    TABLE_ROW= "#ffffff"
    TABLE_ALT= "#f5f7fa"
    BTN_BG   = "#ffffff"
    BTN_ACT  = "#0077b6"
    BTN_TXT  = "#333333"
    BTN_ATXT = "#ffffff"

GREEN = "#00c853"
RED   = "#ff1744"
YELLOW= "#ffd600"

st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    background-color: {BG} !important;
    color: {TEXT} !important;
}}
[data-testid="stSidebar"] {{ background-color: {CARD2} !important; }}
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] div {{ color: {TEXT} !important; }}
h1,h2,h3,h4,h5,h6 {{ color: {TEXT} !important; }}
[data-testid="stDataFrame"] table {{ background:{TABLE_ROW} !important; color:{TEXT} !important; border-collapse:collapse; }}
[data-testid="stDataFrame"] th {{ background:{TABLE_HDR} !important; color:{TEXT} !important; border:1px solid {BORDER}; padding:6px 12px; }}
[data-testid="stDataFrame"] td {{ background:{TABLE_ROW} !important; color:{TEXT} !important; border:1px solid {BORDER}; padding:6px 12px; }}
[data-testid="stDataFrame"] tr:nth-child(even) td {{ background:{TABLE_ALT} !important; }}
.metric-card {{ background:{CARD}; border-radius:10px; padding:16px 20px; margin-bottom:10px; border-left:3px solid {ACCENT}; }}
.metric-label {{ color:{SUB}; font-size:12px; text-transform:uppercase; letter-spacing:1px; }}
.metric-value {{ font-size:22px; font-weight:700; color:{TEXT}; }}
.section-header {{ font-size:20px; font-weight:700; border-bottom:1px solid {BORDER}; padding-bottom:6px; margin-top:24px; margin-bottom:14px; color:{ACCENT}; }}
.analysis-box {{ background:{CARD}; border-radius:12px; padding:24px 28px; border:1px solid {BORDER}; line-height:1.8; color:{TEXT}; }}
.pillar {{ background:{CARD2}; border-radius:8px; padding:14px 18px; margin-bottom:10px; border-left:3px solid {YELLOW}; color:{TEXT}; }}
.pillar-title {{ font-weight:700; color:{YELLOW}; margin-bottom:6px; }}
.pillar-body  {{ color:{TEXT}; font-size:14px; line-height:1.7; }}

/* Time Range Button Bar */
.tr-bar {{
    display: flex; gap: 6px; flex-wrap: wrap;
    margin-bottom: 8px;
}}
.tr-btn {{
    background: {BTN_BG}; color: {BTN_TXT};
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 4px 12px; font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all .15s;
}}
.tr-btn:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
.tr-btn.active {{
    background: {BTN_ACT}; color: {BTN_ATXT};
    border-color: {BTN_ACT};
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def fmt_large(n):
    if n is None or (isinstance(n, float) and math.isnan(n)): return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
        if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
        if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
        return f"${n:,.0f}"
    except: return "N/A"

def fmt_pct(n):
    if n is None or (isinstance(n, float) and math.isnan(n)): return "N/A"
    try: return f"{float(n)*100:.2f}%"
    except: return "N/A"

def safe(info, key, default="N/A"):
    v = info.get(key, default)
    return default if v is None else v

def mcard(col, label, val):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{val}</div>'
        f'</div>', unsafe_allow_html=True)

def safe_yield(raw_val, dividends_paid, market_cap):
    try:
        v = float(raw_val)
        if 0.0 <= v <= 0.20: return v, False
    except (TypeError, ValueError): pass
    try:
        manual = abs(float(dividends_paid)) / float(market_cap)
        if 0.0 <= manual <= 0.20: return manual, True
    except (TypeError, ValueError, ZeroDivisionError): pass
    return 0.0, True

def calc_buyback_yield(shares_full, curr_price):
    if shares_full is None or shares_full.empty: return 0.0, "N/A", False
    s = shares_full.sort_index()
    if len(s) < 2: return 0.0, "N/A", False
    s_now  = float(s.iloc[-1])
    cutoff = s.index[-1] - timedelta(days=365)
    s_1y   = s[s.index <= cutoff]
    if s_1y.empty: return 0.0, "N/A", False
    s_1y_val = float(s_1y.iloc[-1])
    if s_1y_val <= 0: return 0.0, "N/A", False
    bb_yield = max((s_1y_val - s_now) / s_1y_val, 0.0)
    bb_vol   = fmt_large(max(s_1y_val - s_now, 0) * curr_price)
    return bb_yield, bb_vol, True

# ──────────────────────────────────────────────
# TIME RANGE CONFIG
# ──────────────────────────────────────────────
RANGES = {
    "1D":  ("1d",  "5m"),
    "1W":  ("5d",  "30m"),
    "1M":  ("1mo", "1d"),
    "3M":  ("3mo", "1d"),
    "6M":  ("6mo", "1d"),
    "YTD": ("ytd", "1d"),
    "1Y":  ("1y",  "1d"),
    "5Y":  ("5y",  "1wk"),
    "ALL": ("max", "1mo"),
}

if "tr_selected" not in st.session_state:
    st.session_state.tr_selected = "1Y"

# ──────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_ticker(ticker: str):
    """
    Vrací POUZE serializovatelná data (dict, DataFrame, Series).
    Objekt yf.Ticker() se vytvoří lokálně, data se vytáhnou a objekt se zahodí.
    """
    try:
        t = yf.Ticker(ticker.upper())          # lokální objekt – NIKDY se nevrací
        info = t.info
        if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
            return None, None, None, None, None
        inc    = t.financials                  # DataFrame
        bal    = t.balance_sheet               # DataFrame
        cf     = t.cashflow                    # DataFrame
        shares = t.get_shares_full(start="2018-01-01")  # Series / DataFrame
        # t je zde zahozeno – garbage collector ho uvolní
        return info, inc, bal, cf, shares
    except Exception as e:
        st.error(f"Chyba při stahování dat: {e}")
        return None, None, None, None, None

@st.cache_data(ttl=300, show_spinner=False)
def load_hist(ticker: str, period: str, interval: str):
    try:
        t = yf.Ticker(ticker.upper())
        return t.history(period=period, interval=interval)
    except:
        return pd.DataFrame()

with st.spinner(f"Načítám data pro **{ticker_input}**…"):
    info, inc, bal, cf, shares_full = load_ticker(ticker_input)

if info is None:
    st.error("Ticker nenalezen nebo data nejsou k dispozici.")
    st.stop()

curr_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
market_cap = float(info.get("marketCap") or 0)
shares_out = float(info.get("sharesOutstanding") or 1)

# ──────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Dashboard", "📊 360° Metriky", "💰 DCF Model", "📋 Finanční výkazy"
])

# ══════════════════════════════════════════════
# TAB 1 – DASHBOARD
# ══════════════════════════════════════════════
with tab1:
    name      = safe(info, "longName", ticker_input)
    sector    = safe(info, "sector")
    industry  = safe(info, "industry")
    website   = safe(info, "website")
    employees = f"{info['fullTimeEmployees']:,}" if info.get("fullTimeEmployees") else "N/A"
    prev_close = float(info.get("previousClose") or curr_price)
    chg = ((curr_price - prev_close) / prev_close * 100) if prev_close else 0
    chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"

    st.markdown(f"## {name} &nbsp; `{ticker_input}`")

    c1, c2, c3, c4, c5 = st.columns(5)
    mcard(c1, "Aktuální cena", f"${curr_price:.2f}")
    mcard(c2, "1D změna",      chg_str)
    mcard(c3, "Market Cap",    fmt_large(market_cap))
    mcard(c4, "Sektor",        sector)
    mcard(c5, "Zaměstnanci",   employees)
    st.markdown(f"**Industrie:** {industry} &nbsp;|&nbsp; **Web:** [{website}]({website})")

    # ── TIME RANGE SELECTOR ───────────────────
    st.markdown('<div class="section-header">📉 Graf ceny</div>', unsafe_allow_html=True)

    # Render tlačítek jako Streamlit columns (čisté, bez JS)
    btn_cols = st.columns(len(RANGES))
    for i, (label, _) in enumerate(RANGES.items()):
        is_active = (label == st.session_state.tr_selected)
        btn_style = (
            f"background-color:{BTN_ACT};color:{BTN_ATXT};border:1px solid {BTN_ACT};"
            if is_active else
            f"background-color:{BTN_BG};color:{BTN_TXT};border:1px solid {BORDER};"
        )
        if btn_cols[i].button(
            label,
            key=f"tr_{label}",
            use_container_width=True,
        ):
            st.session_state.tr_selected = label
            st.rerun()

    # Načti historii pro vybrané období
    period, interval = RANGES[st.session_state.tr_selected]
    hist = load_hist(ticker_input, period, interval)

    # ── AREA CHART ────────────────────────────
    if hist is not None and not hist.empty:
        close = hist["Close"]
        first_price = float(close.iloc[0])
        last_price  = float(close.iloc[-1])
        is_up = last_price >= first_price

        line_color = GREEN if is_up else RED
        # RGBA pro gradient výplň
        fill_color_top    = f"rgba(0,200,83,0.25)"  if is_up else f"rgba(255,23,68,0.25)"
        fill_color_bottom = f"rgba(0,200,83,0.0)"   if is_up else f"rgba(255,23,68,0.0)"

        fig = go.Figure()

        # Gradient výplň: dvě vrstvy (upper fill + lower transparent)
        fig.add_trace(go.Scatter(
            x=close.index, y=close.values,
            mode="lines",
            line=dict(color=line_color, width=2.5),
            fill="tozeroy",
            fillgradient=dict(
                type="vertical",
                colorscale=[
                    [0.0, fill_color_bottom],
                    [1.0, fill_color_top],
                ],
            ),
            hovertemplate="<b>%{x|%d.%m.%Y %H:%M}</b><br>Cena: <b>$%{y:.2f}</b><extra></extra>",
            name="Cena",
        ))

        fig.update_layout(
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font_color=TEXT,
            height=420,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            # Statický graf – zákaz zoomu i panu
            dragmode=False,
            xaxis=dict(
                gridcolor=GRID_CLR,
                showgrid=True,
                tickfont=dict(color=TEXT),
                linecolor=BORDER,
                fixedrange=True,        # zakáže zoom/pan na ose X
            ),
            yaxis=dict(
                gridcolor=GRID_CLR,
                showgrid=True,
                tickfont=dict(color=TEXT),
                tickprefix="$",
                linecolor=BORDER,
                fixedrange=True,        # zakáže zoom/pan na ose Y
            ),
            # Hover: svislá ryska + unified popisek
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=CARD,
                font_color=TEXT,
                bordercolor=BORDER,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,   # skrytí lišty nástrojů
                "scrollZoom": False,       # zákaz zoom scrollem
                "doubleClick": False,      # zákaz reset double-clickem
                "staticPlot": False,       # hover zůstane funkční
            },
        )

        # Mini info pod grafem
        period_chg = ((last_price - first_price) / first_price * 100) if first_price else 0
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Začátek období", f"${first_price:.2f}")
        col_b.metric("Konec období",   f"${last_price:.2f}")
        col_c.metric("Změna období",   f"{period_chg:+.2f}%")
    else:
        st.warning("Graf není k dispozici pro vybrané období.")

    # ── ANALYTICKÝ PRŮVODCE ───────────────────
    st.markdown('<div class="section-header">🔍 Analytický průvodce – Vyhodnocení společnosti</div>',
                unsafe_allow_html=True)

    biz_summary = safe(info, "longBusinessSummary", "Popis není k dispozici.")
    div_yield_raw, div_est = safe_yield(
        info.get("dividendYield"),
        info.get("lastDividendValue", 0) * shares_out * 4 if info.get("lastDividendValue") else None,
        market_cap,
    )
    bb_yield, bb_vol, bb_avail = calc_buyback_yield(shares_full, curr_price)

    analyst_rating = safe(info, "recommendationKey", "N/A").upper()
    target_mean    = safe(info, "targetMeanPrice")
    target_low     = safe(info, "targetLowPrice")
    target_high    = safe(info, "targetHighPrice")
    num_analysts   = safe(info, "numberOfAnalystOpinions")

    st.markdown(f'<div class="analysis-box">', unsafe_allow_html=True)
    st.markdown(f"## Vyhodnocení společnosti {ticker_input} – Zisková mašina?")
    st.markdown(f"*Datum: {datetime.today().strftime('%d. %m. %Y')} | Zdroj: yfinance / Yahoo Finance*")
    st.markdown("---")

    st.markdown("### 🏢 Laické představení společnosti")
    st.markdown(
        f"**Sektor:** {sector} &nbsp;|&nbsp; **Industrie:** {industry}\n\n"
        f"**Popis činnosti (EN):**\n\n> {biz_summary[:900]}{'…' if len(biz_summary)>900 else ''}\n\n"
        f"👉 *Doplň vlastními slovy v češtině: Co firma dělá? Komu prodává? "
        f"Jsou výnosy opakující se (předplatné/SaaS) nebo jednorázové?*"
    )

    pillars = [
        (
            "1️⃣ PILÍŘ 1 – Monopol nebo silné postavení na trhu",
            f"Tržní kapitalizace: **{fmt_large(market_cap)}** | Sektor: **{sector}**\n\n"
            "👉 Zjisti: tržní podíl, ekosystém (lock-in), síťový efekt, bariéry vstupu.\n\n"
            "✏️ **Tvé zhodnocení Moatu: ANO / NE / SPORNÉ**"
        ),
        (
            "2️⃣ Přehled klíčových údajů a metrik (z yfinance)",
            f"| Metrika | Hodnota |\n|---|---|\n"
            f"| Tržby | {fmt_large(info.get('totalRevenue'))} |\n"
            f"| EPS (TTM) | {safe(info,'trailingEps')} |\n"
            f"| Free Cash Flow | {fmt_large(info.get('freeCashflow'))} |\n"
            f"| Provozní marže | {fmt_pct(info.get('operatingMargins'))} |\n"
            f"| Debt/Equity | {safe(info,'debtToEquity')} |\n"
            f"| Hotovost | {fmt_large(info.get('totalCash'))} |\n\n"
            "👉 *Jsou marže stabilní nebo rostoucí? Zvládne firma splácet dluhy z provozního CF?*"
        ),
        (
            "3️⃣ Investiční teze – pohled do budoucna",
            "👉 Vypiš **3 růstové motory** a **3 rizika**.\n\n"
            "Zdroje: výroční zpráva (10-K), earnings call transkripty, investor relations."
        ),
        (
            "4️⃣ Přátelský vztah k akcionářům",
            f"- **Dividend Yield:** {fmt_pct(div_yield_raw)}"
            f"{' *(ručně dopočítáno)*' if div_est else ''}\n"
            f"- **Payout Ratio:** {fmt_pct(info.get('payoutRatio'))}\n"
            f"- **Buyback Yield (1Y):** {fmt_pct(bb_yield) if bb_avail else 'N/A'}\n"
            f"- **Total Shareholder Yield:** "
            f"{fmt_pct(div_yield_raw + bb_yield) if bb_avail else 'N/A'}\n\n"
            "✏️ **Alokace kapitálu: ANO / NE / SPORNÉ**"
        ),
        (
            "5️⃣ Srovnání s nejbližšími konkurenty",
            "| Firma | Tržby | Marže | P/E | Komentář |\n|---|---|---|---|---|\n| ... |\n\n"
            "Zdroje: Finviz, Macrotrends, Wisesheets."
        ),
        (
            "6️⃣ Insider transakce + analytický konsenzus",
            f"- **Analytický rating:** `{analyst_rating}` | Cílová cena: **${target_mean}** "
            f"(rozsah ${target_low} – ${target_high})\n"
            f"- **Počet analytiků:** {num_analysts}\n"
            f"- **Insider transakce:** [OpenInsider.com](https://openinsider.com) | SEC Form 4"
        ),
        (
            "7️⃣ Vyhodnocení kritérií 1–6",
            "| Kritérium | Hodnocení |\n|---|---|\n"
            "| Monopolní postavení | ✅ / ❌ / ⚠️ |\n"
            "| Finanční síla | ✅ / ❌ / ⚠️ |\n"
            "| Růstový potenciál | ✅ / ❌ / ⚠️ |\n"
            "| Přátelský vztah k akcionářům | ✅ / ❌ / ⚠️ |\n"
            "| Management a kapitálová alokace | ✅ / ❌ / ⚠️ |\n"
            "| Celková stabilita a výkonnost | ✅ / ❌ / ⚠️ |"
        ),
        (
            "8️⃣ Závěr",
            f"✏️ **Jedna věta: Je {ticker_input} zisková mašina – ANO nebo NE a proč?**"
        ),
        (
            "9️⃣ Celkové shrnutí pro investora",
            "👉 Hlavní argumenty pro a proti. Jak velké je riziko vs. potenciál? "
            "Co by muselo nastat, aby se teze zhroutila?"
        ),
    ]

    for title, body in pillars:
        st.markdown(
            f'<div class="pillar"><div class="pillar-title">{title}</div>'
            f'<div class="pillar-body">', unsafe_allow_html=True)
        st.markdown(body)
        st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("*⚠️ Není investiční poradenství. Data: yfinance. Investujte na vlastní riziko.*")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 2 – 360° METRIKY
# ══════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">📊 Valuace</div>', unsafe_allow_html=True)

    earnings_date = "N/A"
    if info.get("earningsTimestamps"):
        try: earnings_date = datetime.fromtimestamp(info["earningsTimestamps"][0]).strftime("%d.%m.%Y")
        except: pass

    st.dataframe(pd.DataFrame({
        "Metrika": ["P/E (TTM)", "Forward P/E", "P/S", "P/B", "EV/EBITDA", "Nejbližší Earnings"],
        "Hodnota": [
            safe(info,"trailingPE"), safe(info,"forwardPE"),
            safe(info,"priceToSalesTrailing12Months"),
            safe(info,"priceToBook"), safe(info,"enterpriseToEbitda"),
            earnings_date,
        ]
    }), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">💹 Rentabilita & Zdraví</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({
            "Metrika": ["ROE","ROA","Gross Margin","Operating Margin","Profit Margin"],
            "Hodnota": [fmt_pct(info.get(k)) for k in
                        ["returnOnEquity","returnOnAssets","grossMargins",
                         "operatingMargins","profitMargins"]]
        }), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({
            "Metrika": ["Debt/Equity","Current Ratio","Total Debt","Cash & Equivalents"],
            "Hodnota": [safe(info,"debtToEquity"), safe(info,"currentRatio"),
                        fmt_large(info.get("totalDebt")), fmt_large(info.get("totalCash"))]
        }), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">💵 Dividendy & Buybacky</div>', unsafe_allow_html=True)

    div_yield_raw, div_est = safe_yield(
        info.get("dividendYield"),
        info.get("lastDividendValue", 0) * shares_out * 4 if info.get("lastDividendValue") else None,
        market_cap,
    )
    bb_yield, bb_vol, bb_avail = calc_buyback_yield(shares_full, curr_price)
    total_sh_str = fmt_pct(div_yield_raw + bb_yield) if bb_avail else "N/A"
    payout = info.get("payoutRatio") or 0

    c1, c2, c3, c4 = st.columns(4)
    mcard(c1, f"Dividend Yield{' *' if div_est else ''}", fmt_pct(div_yield_raw))
    mcard(c2, "Buyback Yield (1Y)", fmt_pct(bb_yield) if bb_avail else "N/A")
    mcard(c3, "Total Shareholder Yield", total_sh_str)
    mcard(c4, "Buyback objem (1Y)", bb_vol)
    st.markdown(f"**Payout Ratio:** {fmt_pct(payout)}")
    if div_est:
        st.caption("\\* Dividend Yield ručně dopočítán z lastDividendValue / Market Cap.")

    st.markdown('<div class="section-header">📉 Share Count Trend (5 let)</div>', unsafe_allow_html=True)
    if shares_full is not None and not shares_full.empty:
        sh = shares_full.sort_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=sh.index, y=sh.values / 1e9,
            mode="lines+markers",
            line=dict(color=ACCENT, width=2),
            fill="tozeroy", fillcolor="rgba(0,196,180,0.08)",
            name="Akcie (mld.)"
        ))
        fig2.update_layout(
            paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
            font_color=TEXT, height=280,
            margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(title="Akcie (mld.)", gridcolor=GRID_CLR, tickfont=dict(color=TEXT)),
            xaxis=dict(gridcolor=GRID_CLR, tickfont=dict(color=TEXT)),
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Data o počtu akcií nejsou k dispozici.")

# ══════════════════════════════════════════════
# TAB 3 – DCF MODEL
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">💰 Discounted Cash Flow Model (10Y)</div>',
                unsafe_allow_html=True)

    fcf = info.get("freeCashflow")
    if fcf is None and cf is not None and not cf.empty:
        for lbl in ["Free Cash Flow","freeCashFlow"]:
            if lbl in cf.index:
                fcf = float(cf.loc[lbl].iloc[0]); break
    fcf = float(fcf) if fcf else 0.0

    st.info(
        f"**FCF (TTM):** {fmt_large(fcf)} &nbsp;|&nbsp; "
        f"**Shares:** {shares_out/1e9:.2f}B &nbsp;|&nbsp; "
        f"**WACC:** {discount_rate*100:.1f}% &nbsp;|&nbsp; "
        f"**Aktuální cena:** ${curr_price:.2f}"
    )

    def dcf_model(fcf, gr, tgr, dr, years=10):
        if dr <= tgr: return None
        pv, cf_t = 0.0, fcf
        for t in range(1, years+1):
            cf_t *= (1 + (gr if t <= 5 else tgr))
            pv   += cf_t / (1+dr)**t
        tv = cf_t * (1+tgr) / (dr-tgr)
        return pv + tv / (1+dr)**years

    if fcf > 0:
        total_pv   = dcf_model(fcf, growth_rate, terminal_gr, discount_rate)
        fair_value = (total_pv / shares_out) if total_pv else None
        mos_price  = fair_value * (1 - mos_required) if fair_value else None

        if fair_value:
            updown   = (fair_value - curr_price) / curr_price * 100
            is_cheap = curr_price <= mos_price

            c1,c2,c3,c4 = st.columns(4)
            mcard(c1, "Fair Value (DCF)",                    f"${fair_value:.2f}")
            mcard(c2, f"MoS cena ({mos_required*100:.0f}%)", f"${mos_price:.2f}")
            mcard(c3, "Aktuální cena",                       f"${curr_price:.2f}")
            mcard(c4, "Upside / Downside",
                  f"{'▲' if updown>=0 else '▼'} {abs(updown):.1f}%")

            if is_cheap:
                st.success(f"✅ **{ticker_input}** (${curr_price:.2f}) pod MoS cenou (${mos_price:.2f}) → potenciálně **PODHODNOCENÁ**.")
            else:
                st.error(f"❌ **{ticker_input}** (${curr_price:.2f}) je o ${curr_price-mos_price:.2f} nad MoS cenou → dle DCF **NADHODNOCENÁ**.")

            st.markdown('<div class="section-header">📐 Sensitivity (Fair Value / akcii)</div>',
                        unsafe_allow_html=True)
            g_range = [growth_rate + d for d in (-0.04,-0.02,0,0.02,0.04)]
            d_range = [discount_rate + d for d in (-0.02,-0.01,0,0.01,0.02)]
            sens = {}
            for dr in d_range:
                row = {}
                for gr in g_range:
                    pv = dcf_model(fcf,gr,terminal_gr,dr) if dr>terminal_gr and gr>=0 else None
                    row[f"G={gr*100:.1f}%"] = f"${pv/shares_out:.2f}" if pv else "N/A"
                sens[f"D={dr*100:.1f}%"] = row
            st.dataframe(pd.DataFrame(sens).T, use_container_width=True)

            st.markdown('<div class="section-header">📊 DCF Waterfall (PV / akcii)</div>',
                        unsafe_allow_html=True)
            labels, pvs, cf_t = [], [], fcf
            for t in range(1,11):
                cf_t *= (1+(growth_rate if t<=5 else terminal_gr))
                pvs.append(round(cf_t/(1+discount_rate)**t/shares_out, 2))
                labels.append(f"Yr {t}")
            if discount_rate > terminal_gr:
                tv = (cf_t*(1+terminal_gr)/(discount_rate-terminal_gr))/(1+discount_rate)**10/shares_out
                labels.append("Terminální"); pvs.append(round(tv,2))

            fig3 = go.Figure(go.Bar(
                x=labels, y=pvs,
                marker_color=[ACCENT]*10+[YELLOW],
                text=[f"${v:.2f}" for v in pvs], textposition="outside",
                textfont=dict(color=TEXT),
            ))
            fig3.update_layout(
                paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                font_color=TEXT, height=340,
                margin=dict(l=0,r=0,t=20,b=0),
                yaxis=dict(title="PV / akcii ($)", gridcolor=GRID_CLR, tickfont=dict(color=TEXT)),
                xaxis=dict(gridcolor=GRID_CLR, tickfont=dict(color=TEXT)),
            )
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        else:
            st.error("DCF selhalo – zkontroluj Discount Rate vs Terminal Growth Rate.")
    else:
        st.warning(f"FCF pro **{ticker_input}** není dostupný nebo je záporný. DCF nelze spočítat.")

# ══════════════════════════════════════════════
# TAB 4 – FINANČNÍ VÝKAZY
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">📋 Finanční výkazy (poslední 4 roky)</div>',
                unsafe_allow_html=True)

    def show_statement(df, title):
        if df is None or df.empty:
            st.warning(f"{title}: data nejsou k dispozici.")
            return
        d = df.copy()
        d.columns = [str(c)[:10] for c in d.columns]
        d = d.apply(pd.to_numeric, errors="coerce")
        d = d.map(lambda x: fmt_large(x) if pd.notna(x) else "N/A")
        st.markdown(f"**{title}**")
        st.dataframe(d, use_container_width=True)

    s1,s2,s3 = st.tabs(["Income Statement","Balance Sheet","Cash Flow"])
    with s1: show_statement(inc, "Income Statement")
    with s2: show_statement(bal, "Balance Sheet")
    with s3: show_statement(cf,  "Cash Flow Statement")

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<small style='color:{SUB}'>Gonnomi v2.5 &nbsp;|&nbsp; "
    "⚠️ Pouze pro informační účely. Není investiční poradenství. "
    "Data: yfinance / Yahoo Finance. Investujte na vlastní riziko.</small>",
    unsafe_allow_html=True
)
