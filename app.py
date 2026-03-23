"""
Value Investor's Workbench
==========================
Spuštění: streamlit run app.py
Závislosti: streamlit, yfinance, pandas, plotly, anthropic, requests
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import anthropic
from datetime import datetime, date
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Value Investor's Workbench",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DARK MODE CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg: #0e1117; --card: #1a1d27; --accent: #4f8ef7;
    --green: #22c55e; --red: #ef4444; --text: #e2e8f0; --muted: #94a3b8;
}
.stApp { background-color: var(--bg); color: var(--text); }
.metric-card {
    background: var(--card); border-radius: 12px; padding: 16px 20px;
    border: 1px solid #2d3148; margin-bottom: 8px;
}
.metric-card h4 { color: var(--muted); font-size: 0.78rem; margin: 0 0 4px; text-transform: uppercase; letter-spacing: .05em; }
.metric-card p  { color: var(--text); font-size: 1.4rem; font-weight: 700; margin: 0; }
.section-header {
    font-size: 1.15rem; font-weight: 700; color: var(--accent);
    border-left: 4px solid var(--accent); padding-left: 10px; margin: 24px 0 12px;
}
.badge-green { background:#14532d; color:#86efac; border-radius:6px; padding:2px 10px; font-size:.8rem; font-weight:600; }
.badge-red   { background:#450a0a; color:#fca5a5; border-radius:6px; padding:2px 10px; font-size:.8rem; font-weight:600; }
.badge-yellow{ background:#451a03; color:#fde68a; border-radius:6px; padding:2px 10px; font-size:.8rem; font-weight:600; }
div[data-testid="stTabs"] button { color: var(--muted) !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ─────────────────────────────────────────────────────────────────────
def fmt_num(v, decimals=2, suffix=""):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    if abs(v) >= 1e12: return f"{v/1e12:.{decimals}f}T{suffix}"
    if abs(v) >= 1e9:  return f"{v/1e9:.{decimals}f}B{suffix}"
    if abs(v) >= 1e6:  return f"{v/1e6:.{decimals}f}M{suffix}"
    return f"{v:.{decimals}f}{suffix}"

def pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
    return f"{v*100:.2f}%"

def safe(d, key, default=None):
    try:
        v = d.get(key, default)
        return v if v not in (None, "N/A", {}) else default
    except Exception:
        return default

def plotly_dark_layout():
    return dict(
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e2e8f0"), xaxis=dict(gridcolor="#2d3148", zerolinecolor="#2d3148"),
        yaxis=dict(gridcolor="#2d3148", zerolinecolor="#2d3148"),
        margin=dict(l=0, r=0, t=32, b=0),
    )

# ── DATA LOADER ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def load_ticker(ticker: str):
    t = yf.Ticker(ticker)
    info = t.info or {}
    hist_1y  = t.history(period="1y",  interval="1d")
    hist_5y  = t.history(period="5y",  interval="1mo")
    fin_a    = t.financials          # annual income statement (columns = dates)
    bal_a    = t.balance_sheet
    cf_a     = t.cashflow
    fin_q    = t.quarterly_financials
    bal_q    = t.quarterly_balance_sheet
    shares_q = t.get_shares_full(start="2019-01-01")
    return dict(info=info, hist_1y=hist_1y, hist_5y=hist_5y,
                fin_a=fin_a, bal_a=bal_a, cf_a=cf_a,
                fin_q=fin_q, bal_q=bal_q, shares_q=shares_q)

# ── AI ANALYSIS ──────────────────────────────────────────────────────────────────
def generate_ai_analysis(ticker: str, info: dict) -> str:
    today = date.today().strftime("%d. %m. %Y")
    name  = info.get("longName", ticker)
    sector = info.get("sector", "N/A")
    mcap  = fmt_num(info.get("marketCap"))
    rev   = fmt_num(info.get("totalRevenue"))
    eps   = info.get("trailingEps", "N/A")
    pm    = pct(info.get("profitMargins"))
    om    = pct(info.get("operatingMargins"))
    fcf   = fmt_num(info.get("freeCashflow"))
    de    = info.get("debtToEquity", "N/A")
    cash  = fmt_num(info.get("totalCash"))
    div   = pct(info.get("dividendYield"))
    roe   = pct(info.get("returnOnEquity"))
    roa   = pct(info.get("returnOnAssets"))
    pe    = info.get("trailingPE", "N/A")
    pb    = info.get("priceToBook", "N/A")
    summary = info.get("longBusinessSummary", "")[:1200]
    recKey  = info.get("recommendationKey", "N/A")
    tgtMean = info.get("targetMeanPrice", "N/A")

    prompt = f"""Jsi špičkový kvantitativní finanční analytik a hodnotový investor (value investing). 
Dnes je {today}. Analyzuj společnost {name} (ticker: {ticker}, sektor: {sector}).

Dostupná data:
- Tržní kapitalizace: {mcap}
- Tržby: {rev}
- EPS (TTM): {eps}
- Free Cash Flow: {fcf}
- Provozní marže: {om}
- Zisková marže: {pm}
- ROE: {roe} | ROA: {roa}
- Debt/Equity: {de}
- Hotovost: {cash}
- Dividendový výnos: {div}
- P/E: {pe} | P/B: {pb}
- Analytický konsenzus: {recKey}, cíl: {tgtMean}
- Popis: {summary}

Vygeneruj kompletní analýzu přesně v tomto formátu (Markdown, česky):

# Vyhodnocení společnosti {ticker} – Zisková mašina?

## Laické představení společnosti
[Souvislý text, lidskou řečí, bez žargonu. Co firma dělá, komu prodává, jak vydělává, ekonomika jednotky, tahouny růstu a rizika.]

### 1️⃣ PILÍŘ 1 – Monopol nebo silné postavení na trhu
[Má firma moat? Ekosystém, síťový efekt, bariéry vstupu? Důkazy s fakty.]
=> **Zhodnocení Moatu:** [ANO/NE/SPORNÉ]

### 2️⃣ Přehled klíčových údajů a metrik
| Metrika | Hodnota |
|---|---|
| Tržby | {rev} |
| EPS | {eps} |
| FCF | {fcf} |
| Provozní marže | {om} |
| Debt/Equity | {de} |
| Hotovost | {cash} |
*[Krátký komentář – co čísla říkají o síle a stabilitě.]*

### 3️⃣ Investiční teze – pohled do budoucna
- **Růstové motory:** [odrážky]
- **Rizika a varovné signály:** [odrážky]
[Shrnutí příležitostí a hrozeb v jednom odstavci.]

### 4️⃣ Přátelský vztah k akcionářům
[Dividendy, buybacky, kapitálová alokace, chování managementu, skin in the game.]
=> **Alokace kapitálu:** [ANO/NE/SPORNÉ]

### 5️⃣ Srovnání s nejbližšími konkurenty
| Firma | Business Model | Tržby/Ziskovost | Zadlužení | Komentář |
|---|---|---|---|---|
[Vyplň 3-4 konkurenty]
[Stručné shrnutí pozice firmy v konkurenci.]

### 6️⃣ Insider transakce + analytický konsenzus
- Insider aktivity: [shrnutí]
- Analytický rating: {recKey}, průměrný cíl: {tgtMean}
- [Kontext a vysvětlení]

### 7️⃣ Vyhodnocení kritérií 1–6
| Kritérium | Hodnocení |
|---|---|
| Monopolní postavení | [ANO/NE/SPORNÉ] |
| Finanční síla | [ANO/NE/SPORNÉ] |
| Růstový potenciál | [ANO/NE/SPORNÉ] |
| Přátelský vztah k akcionářům | [ANO/NE/SPORNÉ] |
| Management a kapitálová alokace | [ANO/NE/SPORNÉ] |
| Celková stabilita a výkonnost | [ANO/NE/SPORNÉ] |

### 8️⃣ Závěr
**[Jedna věta tučně: je to „zisková mašina" a proč.]**

### 9️⃣ Celkové shrnutí pro investora
[Souvislý text pro laika. Hlavní argumenty, síla vs rizika, jasný pohled ANO/NE.]

---
*Autor: AI Chatbot | Datum: {today}*
*⚠️ Není investiční poradenství. Zdroje: yfinance, veřejná data. Rizika: konkurence, regulace, makroekonomika.*"""

    client = anthropic.Anthropic()
    with st.spinner("🤖 AI generuje hloubkovou analýzu…"):
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
    return msg.content[0].text

# ══════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📊 Value Investor's Workbench")
    st.markdown("---")
    ticker_input = st.text_input("Ticker symbol", value="AAPL").upper().strip()
    run_btn = st.button("🔍 Analyzovat", use_container_width=True, type="primary")
    st.markdown("---")
    st.markdown("### ⚙️ DCF parametry")
    discount_rate  = st.slider("Discount Rate (%)", 6.0, 20.0, 10.0, 0.5) / 100
    growth_rate    = st.number_input("Růst FCF – roky 1–5 (%)", value=10.0, step=0.5) / 100
    terminal_rate  = st.number_input("Terminální růst (%)", value=3.0, step=0.5) / 100
    mos_pct        = st.number_input("Požadovaná Margin of Safety (%)", value=20.0, step=5.0) / 100
    st.markdown("---")
    st.caption("Data: yfinance · AI: Claude Sonnet")

# ══════════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════════
if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"
if "data" not in st.session_state:
    st.session_state.data = None
if "ai_text" not in st.session_state:
    st.session_state.ai_text = {}

if run_btn or st.session_state.data is None:
    st.session_state.ticker = ticker_input
    with st.spinner(f"Stahuji data pro {ticker_input}…"):
        st.session_state.data = load_ticker(ticker_input)

data   = st.session_state.data
ticker = st.session_state.ticker
info   = data["info"]

# ── TABS ─────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🏠 Dashboard", "📐 Metriky 360°", "💰 DCF Model", "📋 Výkazy"])

# ══════════════════════════════════════════════════════════════════════════════════
# TAB 1 – DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════════
with tab1:
    name = info.get("longName", ticker)
    st.markdown(f"## {name} &nbsp; <span style='color:#94a3b8;font-size:1rem'>({ticker})</span>", unsafe_allow_html=True)

    # KPI row
    price      = safe(info, "currentPrice") or safe(info, "regularMarketPrice", 0)
    prev_close = safe(info, "previousClose", price)
    chg        = (price - prev_close) / prev_close * 100 if prev_close else 0
    chg_color  = "badge-green" if chg >= 0 else "badge-red"
    chg_sign   = "+" if chg >= 0 else ""

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val in [
        (c1, "Cena", f"${price:.2f}"),
        (c2, "Změna", f'{chg_sign}{chg:.2f}%'),
        (c3, "Tržní kap.", fmt_num(safe(info,"marketCap"), suffix=" USD")),
        (c4, "Sektor", info.get("sector","N/A")),
        (c5, "Zaměstnanci", fmt_num(safe(info,"fullTimeEmployees"), 0)),
    ]:
        col.markdown(f'<div class="metric-card"><h4>{label}</h4><p>{val}</p></div>', unsafe_allow_html=True)

    # Company info row
    st.markdown(f"""
    <div class="metric-card" style="margin-top:8px">
    <b>Průmysl:</b> {info.get('industry','N/A')} &nbsp;|&nbsp;
    <b>Burza:</b> {info.get('exchange','N/A')} &nbsp;|&nbsp;
    <b>Web:</b> <a href="{info.get('website','#')}" target="_blank">{info.get('website','N/A')}</a>
    </div>""", unsafe_allow_html=True)

    # Candlestick chart
    st.markdown('<div class="section-header">📈 Vývoj ceny – 1 rok (OHLC)</div>', unsafe_allow_html=True)
    hist = data["hist_1y"]
    if not hist.empty:
        fig = make_subplots(rows=2, cols=1, row_heights=[0.75, 0.25], shared_xaxes=True, vertical_spacing=0.02)
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"],
            increasing_line_color="#22c55e", decreasing_line_color="#ef4444", name="OHLC"
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"], name="Objem",
            marker_color=["#22c55e" if c >= o else "#ef4444" for c, o in zip(hist["Close"], hist["Open"])]
        ), row=2, col=1)
        fig.update_layout(**plotly_dark_layout(), height=480, showlegend=False)
        fig.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # AI Analysis
    st.markdown('<div class="section-header">🤖 Hloubková AI analýza</div>', unsafe_allow_html=True)
    if ticker not in st.session_state.ai_text:
        if st.button("▶ Generovat AI analýzu", type="primary"):
            st.session_state.ai_text[ticker] = generate_ai_analysis(ticker, info)
            st.rerun()
    else:
        if st.button("🔄 Obnovit analýzu"):
            del st.session_state.ai_text[ticker]
            st.rerun()
        st.markdown(st.session_state.ai_text[ticker])

# ══════════════════════════════════════════════════════════════════════════════════
# TAB 2 – METRICS 360°
# ══════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">📐 Valuace & Rentabilita</div>', unsafe_allow_html=True)

    metrics = {
        "P/E (TTM)":           safe(info, "trailingPE"),
        "Forward P/E":         safe(info, "forwardPE"),
        "P/S":                 safe(info, "priceToSalesTrailing12Months"),
        "P/B":                 safe(info, "priceToBook"),
        "EV/EBITDA":           safe(info, "enterpriseToEbitda"),
        "Příští Earnings":     safe(info, "earningsTimestampStart"),
        "ROE":                 safe(info, "returnOnEquity"),
        "ROA":                 safe(info, "returnOnAssets"),
        "Gross Margin":        safe(info, "grossMargins"),
        "Operating Margin":    safe(info, "operatingMargins"),
        "Profit Margin":       safe(info, "profitMargins"),
        "Debt/Equity":         safe(info, "debtToEquity"),
        "Current Ratio":       safe(info, "currentRatio"),
        "Dividend Yield":      safe(info, "dividendYield"),
        "Payout Ratio":        safe(info, "payoutRatio"),
    }

    def fmt_metric(k, v):
        if v is None: return "N/A"
        if "Margin" in k or "ROE" in k or "ROA" in k or "Yield" in k or "Ratio" in k and "Current" not in k and "Debt" not in k:
            return pct(v)
        if "Earnings" in k:
            try: return datetime.fromtimestamp(v).strftime("%d.%m.%Y")
            except: return str(v)
        return f"{v:.2f}"

    rows = [(k, fmt_metric(k, v)) for k, v in metrics.items()]
    half = len(rows) // 2
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame(rows[:half], columns=["Metrika","Hodnota"]).set_index("Metrika"),
                     use_container_width=True)
    with c2:
        st.dataframe(pd.DataFrame(rows[half:], columns=["Metrika","Hodnota"]).set_index("Metrika"),
                     use_container_width=True)

    # ── BUYBACKS ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔄 Analýza Buybacků & Share Count</div>', unsafe_allow_html=True)

    shares_series = data["shares_q"]
    if shares_series is not None and len(shares_series) > 2:
        shares_df = pd.DataFrame(shares_series, columns=["Shares"])
        shares_df.index = pd.to_datetime(shares_df.index)
        shares_df = shares_df.sort_index()

        # Resample to quarterly
        shares_q = shares_df.resample("Q").last().dropna()

        # Buyback yield (1Y)
        if len(shares_q) >= 4:
            s_now  = shares_q["Shares"].iloc[-1]
            s_1y   = shares_q["Shares"].iloc[-5] if len(shares_q) >= 5 else shares_q["Shares"].iloc[0]
            bb_yield = (s_1y - s_now) / s_1y if s_1y else 0
        else:
            bb_yield = 0

        div_yield_v = safe(info, "dividendYield") or 0
        total_sh_yield = div_yield_v + bb_yield

        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="metric-card"><h4>Buyback Yield (1Y)</h4><p>{bb_yield*100:.2f}%</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><h4>Dividend Yield</h4><p>{div_yield_v*100:.2f}%</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><h4>Total Shareholder Yield</h4><p>{total_sh_yield*100:.2f}%</p></div>', unsafe_allow_html=True)

        # Buyback volumes
        avg_price = safe(info, "currentPrice") or 100
        periods = {"YTD": shares_q.last("1Q"), "6M": shares_q.last("2Q"),
                   "1Y": shares_q.last("4Q"), "2Y": shares_q.last("8Q"),
                   "5Y": shares_q}
        vol_rows = []
        for label, subset in periods.items():
            if len(subset) >= 2:
                red = subset["Shares"].iloc[0] - subset["Shares"].iloc[-1]
                vol = red * avg_price
                vol_rows.append({"Období": label, "Redukce akcií": fmt_num(red, 0), "Objem buybacků (est.)": fmt_num(vol)})
        if vol_rows:
            st.dataframe(pd.DataFrame(vol_rows).set_index("Období"), use_container_width=True)

        # Share Count Trend Chart
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=shares_q.index, y=shares_q["Shares"]/1e9,
            mode="lines+markers", line=dict(color="#4f8ef7", width=2),
            fill="tozeroy", fillcolor="rgba(79,142,247,0.1)", name="Shares (mld)"
        ))
        fig2.update_layout(**plotly_dark_layout(), height=280,
                           title="Share Count Trend", yaxis_title="Mld. akcií")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Data o počtu akcií nejsou k dispozici.")

# ══════════════════════════════════════════════════════════════════════════════════
# TAB 3 – DCF MODEL
# ══════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">💰 Discounted Cash Flow – Fair Value</div>', unsafe_allow_html=True)

    # Get latest FCF
    cf = data["cf_a"]
    fcf_val = None
    if cf is not None and not cf.empty:
        for row_name in ["Free Cash Flow", "FreeCashFlow"]:
            if row_name in cf.index:
                fcf_series = cf.loc[row_name].dropna()
                if not fcf_series.empty:
                    fcf_val = float(fcf_series.iloc[0])
                    break
    if fcf_val is None:
        fcf_val = safe(info, "freeCashflow")

    shares_out = safe(info, "sharesOutstanding") or safe(info, "impliedSharesOutstanding") or 1e9
    cur_price  = safe(info, "currentPrice") or safe(info, "regularMarketPrice", 100)

    col_l, col_r = st.columns([1, 1])
    with col_l:
        if fcf_val:
            st.metric("Poslední Free Cash Flow (TTM)", fmt_num(fcf_val))
            fcf_input = st.number_input("Upravit FCF (USD)", value=float(fcf_val), step=1e8, format="%.0f")
        else:
            st.warning("FCF nenalezeno, zadejte ručně.")
            fcf_input = st.number_input("FCF (USD)", value=1e9, step=1e8, format="%.0f")

        st.metric("Aktuální cena", f"${cur_price:.2f}")
        st.metric("Akcií v oběhu", fmt_num(shares_out, 0))

    # DCF Calculation
    if fcf_input and shares_out and discount_rate > terminal_rate:
        # Phase 1: 5 years explicit
        dcf_values = []
        fcf_t = fcf_input
        for t in range(1, 6):
            fcf_t = fcf_t * (1 + growth_rate)
            pv = fcf_t / (1 + discount_rate) ** t
            dcf_values.append({"Rok": f"Rok {t}", "FCF (proj.)": fmt_num(fcf_t), "PV": fmt_num(pv)})

        # Phase 2: Terminal value
        terminal_fcf = fcf_t * (1 + terminal_rate)
        terminal_val = terminal_fcf / (discount_rate - terminal_rate)
        pv_terminal  = terminal_val / (1 + discount_rate) ** 5

        sum_pv  = sum(fcf_input * (1+growth_rate)**t / (1+discount_rate)**t for t in range(1, 6))
        intrinsic_total = sum_pv + pv_terminal
        fair_value  = intrinsic_total / shares_out
        mos_price   = fair_value * (1 - mos_pct)
        upside      = (fair_value - cur_price) / cur_price * 100
        mos_upside  = (mos_price - cur_price) / cur_price * 100

        with col_r:
            st.metric("Fair Value (DCF)", f"${fair_value:.2f}", f"{upside:+.1f}% vs. tržní cena")
            st.metric(f"MoS Cena ({mos_pct*100:.0f}% MoS)", f"${mos_price:.2f}", f"{mos_upside:+.1f}% vs. tržní cena")
            st.metric("Terminální hodnota (PV)", fmt_num(pv_terminal))

            if cur_price <= mos_price:
                st.markdown('<span class="badge-green">✅ PODHODNOCENÁ – splňuje MoS</span>', unsafe_allow_html=True)
                verdict = f"Akcie **{ticker}** se obchoduje pod MoS cenou ${mos_price:.2f}, což naznačuje atraktivní vstupní bod pro hodnotového investora."
            elif cur_price <= fair_value:
                st.markdown('<span class="badge-yellow">⚠️ SPRAVEDLIVÁ CENA – bez MoS polštáře</span>', unsafe_allow_html=True)
                verdict = f"Akcie **{ticker}** je blízko fair value (${fair_value:.2f}), ale nenabízí požadovaný bezpečnostní polštář {mos_pct*100:.0f}%."
            else:
                st.markdown('<span class="badge-red">❌ NADHODNOCENÁ – nesplňuje MoS</span>', unsafe_allow_html=True)
                verdict = f"Akcie **{ticker}** se obchoduje nad fair value ${fair_value:.2f}. Při požadované MoS {mos_pct*100:.0f}% je vstupní cena příliš vysoká."
            st.info(verdict)

        # DCF table + waterfall chart
        st.markdown("#### Projekce Cash Flow")
        dcf_df = pd.DataFrame(dcf_values)
        st.dataframe(dcf_df.set_index("Rok"), use_container_width=True)

        # Waterfall chart – value composition
        fig3 = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative"] * 5 + ["relative", "total"],
            x=[f"Rok {i}" for i in range(1, 6)] + ["Terminální PV", "Celkem"],
            y=[
                *[fcf_input*(1+growth_rate)**t/(1+discount_rate)**t for t in range(1,6)],
                pv_terminal, 0
            ],
            connector={"line": {"color": "#2d3148"}},
            increasing={"marker": {"color": "#4f8ef7"}},
            decreasing={"marker": {"color": "#ef4444"}},
            totals={"marker": {"color": "#22c55e"}},
        ))
        fig3.update_layout(**plotly_dark_layout(), height=320, title="Složení DCF hodnoty (PV)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.error("Nelze vypočítat DCF: zkontrolujte vstupy (discount rate musí být > terminal rate).")

# ══════════════════════════════════════════════════════════════════════════════════
# TAB 4 – FINANCIAL STATEMENTS
# ══════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">📋 Finanční výkazy (4 roky)</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

    def show_statement(df, name):
        if df is None or df.empty:
            st.warning(f"{name} není k dispozici.")
            return
        cols = df.columns[:4]
        display = df[cols].copy()
        display.columns = [str(c)[:10] for c in display.columns]
        display = display.map(lambda x: fmt_num(x, 1) if isinstance(x, (int, float)) and not np.isnan(x) else x)
        st.dataframe(display, use_container_width=True)

    with s1: show_statement(data["fin_a"], "Income Statement")
    with s2: show_statement(data["bal_a"], "Balance Sheet")
    with s3: show_statement(data["cf_a"],  "Cash Flow")

# ── FOOTER ────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ Tato aplikace neposkytuje investiční poradenství. Data: yfinance. AI: Claude (Anthropic). Vždy provádějte vlastní due diligence.")
