"""
Value Investor's Workbench
==========================
Senior-level stock analysis app with AI-powered qualitative analysis.
Stack: Streamlit · yfinance · pandas · plotly · Anthropic Claude API

Install:
    pip install streamlit yfinance pandas plotly anthropic

Run:
    streamlit run app.py

Streamlit Cloud: add ANTHROPIC_API_KEY to Secrets.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import anthropic
from datetime import datetime, timedelta
import math
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Value Investor's Workbench",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_CSS = """
<style>
:root {
    --bg: #0e1117;
    --card: #1a1d27;
    --accent: #00c4b4;
    --text: #e0e0e0;
    --sub: #888;
    --green: #00c853;
    --red: #ff1744;
    --yellow: #ffd600;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] { background: #12151e; }
.metric-card {
    background: var(--card);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    border-left: 3px solid var(--accent);
}
.metric-label { color: var(--sub); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { font-size: 22px; font-weight: 700; color: var(--text); }
.tag-green  { color: var(--green); font-weight: 700; }
.tag-red    { color: var(--red);   font-weight: 700; }
.tag-yellow { color: var(--yellow);font-weight: 700; }
.section-header {
    font-size: 20px; font-weight: 700;
    border-bottom: 1px solid #2a2d3a;
    padding-bottom: 6px; margin-top: 24px; margin-bottom: 14px;
    color: var(--accent);
}
.ai-box {
    background: var(--card);
    border-radius: 12px;
    padding: 24px 28px;
    border: 1px solid #2a2d3a;
    line-height: 1.75;
}
stTabs [data-baseweb="tab"] { color: var(--sub); }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def fmt_large(n):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "N/A"
    if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"

def fmt_pct(n):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "N/A"
    return f"{n*100:.2f}%"

def safe(info, key, default="N/A"):
    v = info.get(key, default)
    if v is None: return default
    return v

def color_tag(val, good_above=None, bad_above=None):
    try:
        v = float(val)
        if good_above is not None and v >= good_above:
            return f'<span class="tag-green">{val}</span>'
        if bad_above is not None and v >= bad_above:
            return f'<span class="tag-red">{val}</span>'
        return f'<span class="tag-yellow">{val}</span>'
    except:
        return val

@st.cache_data(ttl=3600, show_spinner=False)
def load_ticker(ticker: str):
    try:
        # yfinance automaticky použije curl_cffi (pokud je nainstalována),
        # čímž obejde rate-limiting Yahoo Finance bez ruční správy session.
        t = yf.Ticker(ticker.upper())
        info = t.info
        if not info:
            st.error("Nepodařilo se získat data pro tento ticker.")
            return None, None, None, None, None, None, None
        hist   = t.history(period="1y", interval="1d")
        hist5y = t.history(period="5y", interval="3mo")
        inc    = t.financials
        bal    = t.balance_sheet
        cf     = t.cashflow
        shares = t.get_shares_full(start="2018-01-01")
        return info, hist, hist5y, inc, bal, cf, shares
    except Exception as e:
        st.error(f"Chyba při stahování dat: {e}")
        return None, None, None, None, None, None, None

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Value Investor's Workbench")
    st.markdown("---")
    ticker_input = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper()
    st.markdown("---")
    st.markdown("### ⚙️ DCF Parameters")
    discount_rate = st.slider("Discount Rate (%)", 6.0, 20.0, 10.0, 0.5) / 100
    growth_rate   = st.number_input("Growth Rate – yr 1–5 (%)", value=10.0, step=0.5) / 100
    terminal_gr   = st.number_input("Terminal Growth Rate (%)", value=3.0, step=0.5) / 100
    mos_required  = st.number_input("Margin of Safety (%)", value=20.0, step=5.0) / 100
    st.markdown("---")
    api_key_input = st.text_input("Anthropic API Key", type="password",
                                  help="Or set ANTHROPIC_API_KEY in Streamlit Secrets.")

# ──────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────
with st.spinner(f"Loading data for **{ticker_input}**…"):
    try:
        info, hist, hist5y, inc, bal, cf, shares_full = load_ticker(ticker_input)
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.stop()

if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
    st.error("Ticker not found or no data available. Check the symbol and try again.")
    st.stop()

curr_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

# ──────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Dashboard", "📊 360° Metrics", "💰 DCF Model", "📋 Financial Statements"
])

# ══════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════
with tab1:
    # Header
    name = safe(info, "longName", ticker_input)
    sector   = safe(info, "sector")
    industry = safe(info, "industry")
    mktcap   = fmt_large(info.get("marketCap"))
    employees = f"{info.get('fullTimeEmployees', 'N/A'):,}" if info.get("fullTimeEmployees") else "N/A"
    website  = safe(info, "website")
    prev_close = info.get("previousClose", 0)
    chg = ((curr_price - prev_close) / prev_close * 100) if prev_close else 0
    chg_str = f"{'▲' if chg>=0 else '▼'} {abs(chg):.2f}%"

    st.markdown(f"## {name} &nbsp; `{ticker_input}`")

    c1, c2, c3, c4, c5 = st.columns(5)
    def mcard(col, label, val):
        col.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

    mcard(c1, "Current Price", f"${curr_price:.2f}")
    mcard(c2, "1D Change", chg_str)
    mcard(c3, "Market Cap", mktcap)
    mcard(c4, "Sector", sector)
    mcard(c5, "Employees", employees)

    st.markdown(f"**Industry:** {industry} &nbsp;|&nbsp; **Web:** [{website}]({website})", unsafe_allow_html=True)

    # Candlestick
    st.markdown('<div class="section-header">📉 Price Chart (1 Year)</div>', unsafe_allow_html=True)
    if not hist.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.75, 0.25], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"],  close=hist["Close"],
            increasing_line_color="#00c853", decreasing_line_color="#ff1744",
            name="Price"), row=1, col=1)
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"],
            marker_color=["#00c853" if c >= o else "#ff1744"
                          for c, o in zip(hist["Close"], hist["Open"])],
            name="Volume"), row=2, col=1)
        fig.update_layout(
            paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
            font_color="#e0e0e0", xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=10, b=0), height=460,
            showlegend=False,
            xaxis=dict(gridcolor="#2a2d3a"),
            yaxis=dict(gridcolor="#2a2d3a"),
            xaxis2=dict(gridcolor="#2a2d3a"),
            yaxis2=dict(gridcolor="#2a2d3a"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── AI ANALYSIS ────────────────────────────
    st.markdown('<div class="section-header">🤖 AI-Powered Deep Analysis</div>', unsafe_allow_html=True)

    # Resolve API key
    resolved_key = api_key_input
    if not resolved_key:
        try:
            resolved_key = st.secrets["ANTHROPIC_API_KEY"]
        except:
            resolved_key = None

    today_str = datetime.today().strftime("%d. %m. %Y")

    # Gather snapshot for AI
    summary_data = f"""
Ticker: {ticker_input}
Company: {name}
Sector: {sector} / {industry}
Current Price: ${curr_price:.2f}
Market Cap: {mktcap}
P/E: {safe(info,'trailingPE')}
Forward P/E: {safe(info,'forwardPE')}
P/B: {safe(info,'priceToBook')}
P/S: {safe(info,'priceToSalesTrailing12Months')}
EV/EBITDA: {safe(info,'enterpriseToEbitda')}
ROE: {fmt_pct(info.get('returnOnEquity'))}
ROA: {fmt_pct(info.get('returnOnAssets'))}
Gross Margin: {fmt_pct(info.get('grossMargins'))}
Operating Margin: {fmt_pct(info.get('operatingMargins'))}
Profit Margin: {fmt_pct(info.get('profitMargins'))}
Revenue: {fmt_large(info.get('totalRevenue'))}
Free Cash Flow: {fmt_large(info.get('freeCashflow'))}
Debt/Equity: {safe(info,'debtToEquity')}
Current Ratio: {safe(info,'currentRatio')}
Dividend Yield: {fmt_pct(info.get('dividendYield'))}
52W High: {safe(info,'fiftyTwoWeekHigh')}
52W Low: {safe(info,'fiftyTwoWeekLow')}
Business Summary: {safe(info,'longBusinessSummary','N/A')[:600]}
"""

    PROMPT = f"""Jsi seniorní finanční analytik a hodnotoví investor. Na základě níže uvedených dat o společnosti vytvoř hloubkovou analýzu PŘESNĚ podle šablony.
Piš plynule, analyticky, v češtině. Každou sekci naplň konkrétními informacemi na základě dat.
Dnešní datum: {today_str}

DATA:
{summary_data}

ŠABLONA (vyplň ji přesně, zachovej emoji a strukturu):

# Vyhodnocení společnosti {ticker_input} – Zisková mašina?

## Laické představení společnosti
[Souvislý text, lidskou řečí. Co firma dělá, hlavní produkty/služby, komu prodává, jak vydělává peníze, opakovanost výnosů, ekonomika jednotky, hlavní tahouny růstu a rizika.]

### 1️⃣ PILÍŘ 1 – Monopol nebo silné postavení na trhu
[Má firma moat? Ekosystém, síťový efekt, bariéry vstupu? Konkrétní důkazy.]
=> **Zhodnocení Moatu:** [ANO/NE/SPORNÉ]

### 2️⃣ Přehled klíčových údajů a metrik
[Tabulka markdown: Metrika | Hodnota | Komentář – Tržby, EPS, FCF, Provozní marže, Debt/Equity, Hotovost]
*Krátký komentář co čísla znamenají pro sílu a stabilitu.*

### 3️⃣ Investiční teze – pohled do budoucna
**Růstové motory:**
- [bod 1]
- [bod 2]
- [bod 3]

**Rizika a varovné signály:**
- [bod 1]
- [bod 2]
- [bod 3]

[Shrnutí v odstavci.]

### 4️⃣ Přátelský vztah k akcionářům
[Dividendy, buybacky, management, skin in the game, historické příklady.]
=> **Alokace kapitálu:** [ANO/NE/SPORNÉ]

### 5️⃣ Srovnání s nejbližšími konkurenty
| Firma | Business Model | Tržby/Ziskovost | Zadlužení | Komentář |
|-------|---------------|-----------------|-----------|----------|
[3-4 řádky]
[Shrnutí pozice firmy.]

### 6️⃣ Insider transakce + analytický konsenzus
- **Insideři:** [shrnutí]
- **Analytický rating:** [buy/hold/sell a průměrný cílový kurz]
- **Kontext:** [vysvětlení]

### 7️⃣ Vyhodnocení kritérií 1–6
| Kritérium | Hodnocení |
|-----------|-----------|
| Monopolní postavení | [ANO/NE/SPORNÉ] |
| Finanční síla | [ANO/NE/SPORNÉ] |
| Růstový potenciál | [ANO/NE/SPORNÉ] |
| Přátelský vztah k akcionářům | [ANO/NE/SPORNÉ] |
| Management a kapitálová alokace | [ANO/NE/SPORNÉ] |
| Celková stabilita a výkonnost | [ANO/NE/SPORNÉ] |

### 8️⃣ Závěr
**[Jedna věta tučně: je to zisková mašina a proč.]**

### 9️⃣ Celkové shrnutí pro investora
[Souvislý text pro laika. Hlavní argumenty pro a proti. Jasný pohled ANO/NE.]

---
*Autor: AI Chatbot | Datum: {today_str}*
*⚠️ Není investiční poradenství. Zdroje: yfinance, veřejné informace. Rizika: konkurence, regulace, tržní podmínky.*
"""

    if resolved_key:
        gen_btn = st.button("🚀 Generovat AI analýzu", type="primary")
        ai_placeholder = st.empty()

        if gen_btn:
            with st.spinner("Generuji hloubkovou analýzu…"):
                try:
                    client = anthropic.Anthropic(api_key=resolved_key)
                    ai_text = ""
                    with client.messages.stream(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4000,
                        messages=[{"role": "user", "content": PROMPT}],
                    ) as stream:
                        for text in stream.text_stream:
                            ai_text += text
                            ai_placeholder.markdown(
                                f'<div class="ai-box">{ai_text}▌</div>',
                                unsafe_allow_html=True)
                    ai_placeholder.markdown(
                        f'<div class="ai-box">{ai_text}</div>',
                        unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"AI chyba: {e}")
        else:
            ai_placeholder.info("Klikni na **Generovat AI analýzu** pro spuštění hloubkové analýzy.")
    else:
        st.warning("Pro AI analýzu zadej Anthropic API klíč v postranním panelu nebo nastav `ANTHROPIC_API_KEY` v Streamlit Secrets.")

# ══════════════════════════════════════════════
# TAB 2 — 360° METRICS
# ══════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">📊 Valuace</div>', unsafe_allow_html=True)

    valuation_data = {
        "Metrika": ["P/E (TTM)", "Forward P/E", "P/S", "P/B", "EV/EBITDA", "Nejbližší Earnings"],
        "Hodnota": [
            safe(info, "trailingPE"),
            safe(info, "forwardPE"),
            safe(info, "priceToSalesTrailing12Months"),
            safe(info, "priceToBook"),
            safe(info, "enterpriseToEbitda"),
            safe(info, "earningsDate") if info.get("earningsDate") else
                (datetime.fromtimestamp(info["earningsTimestamps"][0]).strftime("%d.%m.%Y")
                 if info.get("earningsTimestamps") else "N/A"),
        ]
    }
    st.dataframe(pd.DataFrame(valuation_data), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">💹 Rentabilita & Zdraví</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        prof_data = {
            "Metrika": ["ROE", "ROA", "Gross Margin", "Operating Margin", "Profit Margin"],
            "Hodnota": [
                fmt_pct(info.get("returnOnEquity")),
                fmt_pct(info.get("returnOnAssets")),
                fmt_pct(info.get("grossMargins")),
                fmt_pct(info.get("operatingMargins")),
                fmt_pct(info.get("profitMargins")),
            ]
        }
        st.dataframe(pd.DataFrame(prof_data), use_container_width=True, hide_index=True)
    with c2:
        health_data = {
            "Metrika": ["Debt/Equity", "Current Ratio", "Total Debt", "Cash & Equivalents"],
            "Hodnota": [
                safe(info, "debtToEquity"),
                safe(info, "currentRatio"),
                fmt_large(info.get("totalDebt")),
                fmt_large(info.get("totalCash")),
            ]
        }
        st.dataframe(pd.DataFrame(health_data), use_container_width=True, hide_index=True)

    # ── DIVIDENDS & BUYBACKS ──────────────────
    st.markdown('<div class="section-header">💵 Dividendy & Buybacky</div>', unsafe_allow_html=True)

    div_yield = info.get("dividendYield", 0) or 0
    payout    = info.get("payoutRatio", 0) or 0

    # Buyback yield: use shares outstanding change
    buyback_yield = 0.0
    bb_vol_1y = "N/A"
    if shares_full is not None and not shares_full.empty:
        shares_series = shares_full.sort_index()
        if len(shares_series) >= 2:
            s_now  = shares_series.iloc[-1]
            s_1y   = shares_series[shares_series.index <= shares_series.index[-1] - timedelta(days=365)]
            if not s_1y.empty:
                s_1y_val = s_1y.iloc[-1]
                buyback_yield = max((s_1y_val - s_now) / s_1y_val, 0)
                bb_vol_1y = fmt_large(max(s_1y_val - s_now, 0) * curr_price)

    total_sh_yield = div_yield + buyback_yield

    c1, c2, c3, c4 = st.columns(4)
    mcard(c1, "Dividend Yield",      fmt_pct(div_yield))
    mcard(c2, "Buyback Yield (1Y)",  fmt_pct(buyback_yield))
    mcard(c3, "Total Shareholder Yield", fmt_pct(total_sh_yield))
    mcard(c4, "Buyback Vol (1Y $)",  bb_vol_1y)

    st.markdown(f"**Payout Ratio:** {fmt_pct(payout)}")

    # Share Count Trend Chart
    st.markdown('<div class="section-header">📉 Share Count Trend (5 let)</div>', unsafe_allow_html=True)
    if shares_full is not None and not shares_full.empty:
        sh = shares_full.sort_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=sh.index, y=sh.values / 1e9,
            mode="lines+markers",
            line=dict(color="#00c4b4", width=2),
            fill="tozeroy", fillcolor="rgba(0,196,180,0.08)",
            name="Shares (B)"
        ))
        fig2.update_layout(
            paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
            font_color="#e0e0e0", height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="Shares (B)", gridcolor="#2a2d3a"),
            xaxis=dict(gridcolor="#2a2d3a"),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Data o počtu akcií nejsou k dispozici.")

# ══════════════════════════════════════════════
# TAB 3 — DCF MODEL
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">💰 Discounted Cash Flow Model</div>', unsafe_allow_html=True)

    # Get FCF
    fcf = info.get("freeCashflow")
    if fcf is None and cf is not None and not cf.empty:
        for label in ["Free Cash Flow", "freeCashFlow"]:
            if label in cf.index:
                fcf = cf.loc[label].iloc[0]
                break
    if fcf is None:
        fcf = 0.0

    shares_out = info.get("sharesOutstanding") or 1

    st.info(f"**Poslední Free Cash Flow:** {fmt_large(fcf)}  |  **Shares Outstanding:** {shares_out/1e9:.2f}B  |  **Aktuální cena:** ${curr_price:.2f}")

    # ── DCF CALCULATION ───────────────────────
    def dcf_model(fcf, growth_r, terminal_gr, disc_r, years=10):
        if disc_r <= terminal_gr:
            return None
        pv = 0.0
        cf_t = fcf
        for t in range(1, years + 1):
            g = growth_r if t <= 5 else terminal_gr
            cf_t *= (1 + g)
            pv += cf_t / (1 + disc_r) ** t
        terminal = cf_t * (1 + terminal_gr) / (disc_r - terminal_gr)
        pv += terminal / (1 + disc_r) ** years
        return pv

    if fcf and fcf > 0:
        total_pv    = dcf_model(fcf, growth_rate, terminal_gr, discount_rate)
        fair_value  = (total_pv / shares_out) if total_pv else None
        mos_price   = fair_value * (1 - mos_required) if fair_value else None

        if fair_value:
            updown = (fair_value - curr_price) / curr_price * 100
            is_cheap = curr_price <= mos_price

            c1, c2, c3, c4 = st.columns(4)
            mcard(c1, "Fair Value (DCF)", f"${fair_value:.2f}")
            mcard(c2, f"MoS Price ({mos_required*100:.0f}%)", f"${mos_price:.2f}")
            mcard(c3, "Aktuální Cena", f"${curr_price:.2f}")
            mcard(c4, "Upside / Downside", f"{'▲' if updown>=0 else '▼'} {abs(updown):.1f}%")

            if is_cheap:
                st.success(f"✅ Akcie **{ticker_input}** se obchoduje POD MoS cenou (${mos_price:.2f}). Potenciálně **PODHODNOCENÁ** dle DCF.")
            else:
                diff = curr_price - mos_price
                st.error(f"❌ Akcie **{ticker_input}** je o ${diff:.2f} NAD MoS cenou. Dle DCF **NADHODNOCENÁ** nebo bez dostatečného bezpečnostního polštáře.")

            # Sensitivity table
            st.markdown('<div class="section-header">📐 Sensitivity tabulka (Fair Value)</div>', unsafe_allow_html=True)
            growth_range   = [growth_rate - 0.04, growth_rate - 0.02, growth_rate, growth_rate + 0.02, growth_rate + 0.04]
            discount_range = [discount_rate - 0.02, discount_rate - 0.01, discount_rate, discount_rate + 0.01, discount_rate + 0.02]
            sens = {}
            for dr in discount_range:
                row = {}
                for gr in growth_range:
                    if dr > terminal_gr and gr >= 0:
                        pv = dcf_model(fcf, gr, terminal_gr, dr)
                        row[f"G={gr*100:.1f}%"] = f"${pv/shares_out:.2f}" if pv else "N/A"
                    else:
                        row[f"G={gr*100:.1f}%"] = "N/A"
                sens[f"D={dr*100:.1f}%"] = row
            st.dataframe(pd.DataFrame(sens).T, use_container_width=True)

            # Waterfall chart
            st.markdown('<div class="section-header">📊 DCF Waterfall</div>', unsafe_allow_html=True)
            yr_labels, yr_pvs = [], []
            cf_t = fcf
            for t in range(1, 11):
                g = growth_rate if t <= 5 else terminal_gr
                cf_t *= (1 + g)
                pv_t = cf_t / (1 + discount_rate) ** t / shares_out
                yr_labels.append(f"Yr {t}")
                yr_pvs.append(round(pv_t, 2))
            tv = (cf_t * (1 + terminal_gr) / (discount_rate - terminal_gr)) / (1 + discount_rate) ** 10 / shares_out
            yr_labels.append("Terminal")
            yr_pvs.append(round(tv, 2))

            fig3 = go.Figure(go.Bar(
                x=yr_labels, y=yr_pvs,
                marker_color=["#00c4b4"] * 10 + ["#ffd600"],
                text=[f"${v:.2f}" for v in yr_pvs],
                textposition="outside",
            ))
            fig3.update_layout(
                paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
                font_color="#e0e0e0", height=340,
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis=dict(title="PV per share ($)", gridcolor="#2a2d3a"),
                xaxis=dict(gridcolor="#2a2d3a"),
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.error("DCF výpočet selhal – zkontroluj discount rate vs terminal growth rate.")
    else:
        st.warning(f"Free Cash Flow pro {ticker_input} není k dispozici nebo je záporný. DCF nelze spočítat.")

# ══════════════════════════════════════════════
# TAB 4 — FINANCIAL STATEMENTS
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">📋 Finanční výkazy (poslední 4 roky)</div>', unsafe_allow_html=True)

    def show_statement(df, title):
        if df is None or df.empty:
            st.warning(f"{title}: data nejsou k dispozici.")
            return
        df = df.copy()
        df.columns = [str(c)[:10] for c in df.columns]
        # Format large numbers
        df = df.apply(pd.to_numeric, errors="coerce")
        df = df.map(lambda x: fmt_large(x) if pd.notna(x) else "N/A")
        st.markdown(f"**{title}**")
        st.dataframe(df, use_container_width=True)

    s1, s2, s3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
    with s1: show_statement(inc,  "Income Statement")
    with s2: show_statement(bal,  "Balance Sheet")
    with s3: show_statement(cf,   "Cash Flow Statement")

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<small style='color:#555'>⚠️ Tato aplikace slouží pouze k informačním účelům a nepředstavuje investiční poradenství. "
    "Veškerá data pochází z veřejných zdrojů (yfinance). Investujte na vlastní riziko.</small>",
    unsafe_allow_html=True
)
