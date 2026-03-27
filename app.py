"""
Value Investor's Workbench
==========================
Stack: Streamlit · yfinance · pandas · plotly
Bez závislosti na Anthropic API – analytická sekce je strukturovaný manuální průvodce.

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
    --bg: #0e1117; --card: #1a1d27; --accent: #00c4b4;
    --text: #e0e0e0; --sub: #888;
    --green: #00c853; --red: #ff1744; --yellow: #ffd600;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] { background: #12151e; }
.metric-card {
    background: var(--card); border-radius: 10px;
    padding: 16px 20px; margin-bottom: 10px;
    border-left: 3px solid var(--accent);
}
.metric-label { color: var(--sub); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { font-size: 22px; font-weight: 700; color: var(--text); }
.section-header {
    font-size: 20px; font-weight: 700;
    border-bottom: 1px solid #2a2d3a;
    padding-bottom: 6px; margin-top: 24px; margin-bottom: 14px;
    color: var(--accent);
}
.analysis-box {
    background: var(--card); border-radius: 12px;
    padding: 24px 28px; border: 1px solid #2a2d3a; line-height: 1.8;
}
.pillar {
    background: #12151e; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 10px;
    border-left: 3px solid #ffd600;
}
.pillar-title { font-weight: 700; color: var(--yellow); margin-bottom: 6px; }
.pillar-body  { color: #bbb; font-size: 14px; line-height: 1.7; }
.tag-green  { color: var(--green); font-weight: 700; }
.tag-red    { color: var(--red);   font-weight: 700; }
.tag-yellow { color: var(--yellow);font-weight: 700; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def fmt_large(n):
    if n is None or (isinstance(n, float) and math.isnan(n)): return "N/A"
    if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"

def fmt_pct(n):
    if n is None or (isinstance(n, float) and math.isnan(n)): return "N/A"
    return f"{n*100:.2f}%"

def safe(info, key, default="N/A"):
    v = info.get(key, default)
    return default if v is None else v

def mcard(col, label, val):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{val}</div>'
        f'</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_ticker(ticker: str):
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info
        if not info:
            st.error("Nepodařilo se získat data pro tento ticker.")
            return None, None, None, None, None, None, None
        hist   = t.history(period="1y",  interval="1d")
        hist5y = t.history(period="5y",  interval="3mo")
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
    st.markdown("### ⚙️ DCF Parametry")
    discount_rate = st.slider("Discount Rate / WACC (%)", 6.0, 20.0, 10.0, 0.5) / 100
    growth_rate   = st.number_input("Growth Rate – rok 1–5 (%)", value=10.0, step=0.5) / 100
    terminal_gr   = st.number_input("Terminal Growth Rate (%)",  value=3.0,  step=0.5) / 100
    mos_required  = st.number_input("Margin of Safety (%)",      value=20.0, step=5.0) / 100

# ──────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────
with st.spinner(f"Načítám data pro **{ticker_input}**…"):
    info, hist, hist5y, inc, bal, cf, shares_full = load_ticker(ticker_input)

if info is None:
    st.stop()

curr_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

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
    name     = safe(info, "longName", ticker_input)
    sector   = safe(info, "sector")
    industry = safe(info, "industry")
    mktcap   = fmt_large(info.get("marketCap"))
    employees = f"{info.get('fullTimeEmployees', 'N/A'):,}" if info.get("fullTimeEmployees") else "N/A"
    website  = safe(info, "website")
    prev_close = info.get("previousClose", 0) or 0
    chg = ((curr_price - prev_close) / prev_close * 100) if prev_close else 0
    chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"

    st.markdown(f"## {name} &nbsp; `{ticker_input}`")

    c1, c2, c3, c4, c5 = st.columns(5)
    mcard(c1, "Aktuální cena",  f"${curr_price:.2f}")
    mcard(c2, "1D změna",       chg_str)
    mcard(c3, "Market Cap",     mktcap)
    mcard(c4, "Sektor",         sector)
    mcard(c5, "Zaměstnanci",    employees)
    st.markdown(f"**Industrie:** {industry} &nbsp;|&nbsp; **Web:** [{website}]({website})")

    # Candlestick
    st.markdown('<div class="section-header">📉 Graf ceny (1 rok)</div>', unsafe_allow_html=True)
    if hist is not None and not hist.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.75, 0.25], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"],
            increasing_line_color="#00c853", decreasing_line_color="#ff1744",
            name="Cena"), row=1, col=1)
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"],
            marker_color=["#00c853" if c >= o else "#ff1744"
                          for c, o in zip(hist["Close"], hist["Open"])],
            name="Objem"), row=2, col=1)
        fig.update_layout(
            paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
            font_color="#e0e0e0", xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=10, b=0), height=460, showlegend=False,
            xaxis=dict(gridcolor="#2a2d3a"), yaxis=dict(gridcolor="#2a2d3a"),
            xaxis2=dict(gridcolor="#2a2d3a"), yaxis2=dict(gridcolor="#2a2d3a"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── ANALYTICKÝ PRŮVODCE ───────────────────
    st.markdown('<div class="section-header">🔍 Analytický průvodce – Vyhodnocení společnosti</div>',
                unsafe_allow_html=True)

    biz_summary = safe(info, "longBusinessSummary", "Popis není k dispozici.")

    st.markdown(f'<div class="analysis-box">', unsafe_allow_html=True)
    st.markdown(f"## Vyhodnocení společnosti {ticker_input} – Zisková mašina?")
    st.markdown("---")

    # Laické představení – z yfinance
    st.markdown("### 🏢 Laické představení společnosti")
    st.info(f"📄 **Popis z yfinance:** {biz_summary[:800]}{'…' if len(biz_summary) > 800 else ''}")
    st.markdown(
        "_👉 Doplň vlastními slovy: Co firma dělá? Komu prodává? Jak vydělává? "
        "Jsou výnosy opakující se (SaaS, předplatné) nebo jednorázové?_"
    )

    pillars = [
        ("1️⃣ PILÍŘ 1 – Monopol nebo silné postavení na trhu",
         "Má firma **ekonomický příkop (moat)**? Ovládá ekosystém, síťový efekt nebo silnou značku? "
         "Je těžké ji nahradit?\n\n"
         "👉 Zjisti: tržní podíl, bariéry vstupu, sílu značky (Interbrand, Forbes). "
         "Odpověz: **Moat: ANO / NE / SPORNÉ**"),
        ("2️⃣ Klíčové metriky (přehled)",
         f"Data z yfinance (viz záložka **360° Metriky**):\n"
         f"- Tržby: **{fmt_large(info.get('totalRevenue'))}**\n"
         f"- FCF: **{fmt_large(info.get('freeCashflow'))}**\n"
         f"- Provozní marže: **{fmt_pct(info.get('operatingMargins'))}**\n"
         f"- Debt/Equity: **{safe(info, 'debtToEquity')}**\n"
         f"- Hotovost: **{fmt_large(info.get('totalCash'))}**\n\n"
         "👉 Jsou marže rostoucí nebo klesající? Je firma schopna splácet dluhy z provozního CF?"),
        ("3️⃣ Investiční teze – pohled do budoucna",
         "👉 Vypiš 3 **růstové motory** (nové trhy, produkty, geografie) a 3 **rizika** "
         "(konkurence, regulace, zadlužení, odchod zákazníků).\n\n"
         "Zdroje: investor relations, výroční zpráva (10-K/Annual Report), earnings call transkripty."),
        ("4️⃣ Přátelský vztah k akcionářům",
         f"- Dividend Yield: **{fmt_pct(info.get('dividendYield'))}** | "
         f"Payout Ratio: **{fmt_pct(info.get('payoutRatio'))}**\n"
         f"- Buybacky: viz záložka **360° Metriky → Buyback Yield**\n\n"
         "👉 Zjisti: Jak velký % zisku jde zpět akcionářům? "
         "Má CEO skin in the game (vlastní akcie)? Odpověz: **Alokace kapitálu: ANO / NE / SPORNÉ**"),
        ("5️⃣ Srovnání s nejbližšími konkurenty",
         "👉 Sestav tabulku (Firma | Tržby | Marže | P/E | Komentář) pro 3–4 přímé konkurenty. "
         "Zdroje: Macrotrends, Wisesheets, Finviz Screener.\n\n"
         "Otázka: Roste firma rychleji než sektor? Má lepší marže než konkurence?"),
        ("6️⃣ Insider transakce + analytický konsenzus",
         f"- Analyst Rating: **{safe(info, 'recommendationKey', 'N/A').upper()}** | "
         f"Cílová cena: **${safe(info, 'targetMeanPrice')}** "
         f"(rozsah ${safe(info, 'targetLowPrice')} – ${safe(info, 'targetHighPrice')})\n"
         f"- Počet analytiků: **{safe(info, 'numberOfAnalystOpinions')}**\n\n"
         "👉 Insider transakce: ověř na [OpenInsider](https://openinsider.com) nebo SEC Form 4. "
         "Kupují nebo prodávají insideři? Proč?"),
        ("7️⃣ Vyhodnocení kritérií 1–6",
         "Po vyplnění předchozích sekcí zaznamenej výsledky:\n\n"
         "| Kritérium | Hodnocení |\n|---|---|\n"
         "| Monopolní postavení | ✅ / ❌ / ⚠️ |\n"
         "| Finanční síla | ✅ / ❌ / ⚠️ |\n"
         "| Růstový potenciál | ✅ / ❌ / ⚠️ |\n"
         "| Přátelský vztah k akcionářům | ✅ / ❌ / ⚠️ |\n"
         "| Management a kapitálová alokace | ✅ / ❌ / ⚠️ |\n"
         "| Celková stabilita a výkonnost | ✅ / ❌ / ⚠️ |"),
        ("8️⃣ Závěr",
         "👉 Napiš jednu větu tučně: **Je [TICKER] zisková mašina a proč ANO/NE?**"),
        ("9️⃣ Celkové shrnutí pro investora",
         "👉 Souvislý odstavec pro laika: Hlavní argumenty pro a proti investici. "
         "Jak velké je riziko vs. potenciál? Co by muselo nastat, aby se teze zhroutila?"),
    ]

    for title, body in pillars:
        st.markdown(
            f'<div class="pillar">'
            f'<div class="pillar-title">{title}</div>'
            f'<div class="pillar-body">', unsafe_allow_html=True)
        st.markdown(body)
        st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        f"*Datum analýzy: {datetime.today().strftime('%d. %m. %Y')} &nbsp;|&nbsp; "
        "Zdroje: yfinance, SEC filings, investor relations.*\n\n"
        "⚠️ *Není investiční poradenství. Investujte na vlastní riziko.*"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 2 – 360° METRIKY
# ══════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">📊 Valuace</div>', unsafe_allow_html=True)

    earnings_date = "N/A"
    if info.get("earningsTimestamps"):
        try:
            earnings_date = datetime.fromtimestamp(info["earningsTimestamps"][0]).strftime("%d.%m.%Y")
        except: pass

    val_df = pd.DataFrame({
        "Metrika": ["P/E (TTM)", "Forward P/E", "P/S", "P/B", "EV/EBITDA", "Nejbližší Earnings"],
        "Hodnota": [
            safe(info, "trailingPE"), safe(info, "forwardPE"),
            safe(info, "priceToSalesTrailing12Months"),
            safe(info, "priceToBook"), safe(info, "enterpriseToEbitda"),
            earnings_date,
        ]
    })
    st.dataframe(val_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">💹 Rentabilita & Zdraví</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({
            "Metrika": ["ROE", "ROA", "Gross Margin", "Operating Margin", "Profit Margin"],
            "Hodnota": [fmt_pct(info.get(k)) for k in
                        ["returnOnEquity","returnOnAssets","grossMargins",
                         "operatingMargins","profitMargins"]]
        }), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({
            "Metrika": ["Debt/Equity", "Current Ratio", "Total Debt", "Cash & Equivalents"],
            "Hodnota": [safe(info,"debtToEquity"), safe(info,"currentRatio"),
                        fmt_large(info.get("totalDebt")), fmt_large(info.get("totalCash"))]
        }), use_container_width=True, hide_index=True)

    # Dividendy & Buybacky
    st.markdown('<div class="section-header">💵 Dividendy & Buybacky</div>', unsafe_allow_html=True)

    div_yield    = info.get("dividendYield", 0) or 0
    payout       = info.get("payoutRatio", 0) or 0
    buyback_yield = 0.0
    bb_vol_1y    = "N/A"

    if shares_full is not None and not shares_full.empty:
        s = shares_full.sort_index()
        if len(s) >= 2:
            s_now  = s.iloc[-1]
            s_1y   = s[s.index <= s.index[-1] - timedelta(days=365)]
            if not s_1y.empty:
                s_1y_val = s_1y.iloc[-1]
                buyback_yield = max((s_1y_val - s_now) / s_1y_val, 0)
                bb_vol_1y = fmt_large(max(s_1y_val - s_now, 0) * curr_price)

    total_sh_yield = div_yield + buyback_yield

    c1, c2, c3, c4 = st.columns(4)
    mcard(c1, "Dividend Yield",          fmt_pct(div_yield))
    mcard(c2, "Buyback Yield (1Y)",      fmt_pct(buyback_yield))
    mcard(c3, "Total Shareholder Yield", fmt_pct(total_sh_yield))
    mcard(c4, "Buyback objem (1Y)",      bb_vol_1y)
    st.markdown(f"**Payout Ratio:** {fmt_pct(payout)}")

    # Share Count Trend
    st.markdown('<div class="section-header">📉 Share Count Trend (5 let)</div>', unsafe_allow_html=True)
    if shares_full is not None and not shares_full.empty:
        sh = shares_full.sort_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=sh.index, y=sh.values / 1e9,
            mode="lines+markers",
            line=dict(color="#00c4b4", width=2),
            fill="tozeroy", fillcolor="rgba(0,196,180,0.08)",
            name="Akcie (mld.)"
        ))
        fig2.update_layout(
            paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
            font_color="#e0e0e0", height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="Akcie (mld.)", gridcolor="#2a2d3a"),
            xaxis=dict(gridcolor="#2a2d3a"),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Data o počtu akcií nejsou k dispozici.")

# ══════════════════════════════════════════════
# TAB 3 – DCF MODEL
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">💰 Discounted Cash Flow Model</div>', unsafe_allow_html=True)

    fcf = info.get("freeCashflow")
    if fcf is None and cf is not None and not cf.empty:
        for lbl in ["Free Cash Flow", "freeCashFlow"]:
            if lbl in cf.index:
                fcf = cf.loc[lbl].iloc[0]; break
    fcf = fcf or 0.0

    shares_out = info.get("sharesOutstanding") or 1
    st.info(f"**FCF:** {fmt_large(fcf)}  |  **Shares:** {shares_out/1e9:.2f}B  |  **Cena:** ${curr_price:.2f}")

    def dcf_model(fcf, gr, tgr, dr, years=10):
        if dr <= tgr: return None
        pv, cf_t = 0.0, fcf
        for t in range(1, years + 1):
            cf_t *= (1 + (gr if t <= 5 else tgr))
            pv   += cf_t / (1 + dr) ** t
        terminal = cf_t * (1 + tgr) / (dr - tgr)
        return pv + terminal / (1 + dr) ** years

    if fcf and fcf > 0:
        total_pv   = dcf_model(fcf, growth_rate, terminal_gr, discount_rate)
        fair_value = (total_pv / shares_out) if total_pv else None
        mos_price  = fair_value * (1 - mos_required) if fair_value else None

        if fair_value:
            updown   = (fair_value - curr_price) / curr_price * 100
            is_cheap = curr_price <= mos_price

            c1, c2, c3, c4 = st.columns(4)
            mcard(c1, "Fair Value (DCF)",            f"${fair_value:.2f}")
            mcard(c2, f"MoS cena ({mos_required*100:.0f}%)", f"${mos_price:.2f}")
            mcard(c3, "Aktuální cena",               f"${curr_price:.2f}")
            mcard(c4, "Upside / Downside",           f"{'▲' if updown>=0 else '▼'} {abs(updown):.1f}%")

            if is_cheap:
                st.success(f"✅ **{ticker_input}** se obchoduje POD MoS cenou (${mos_price:.2f}) → potenciálně **PODHODNOCENÁ**.")
            else:
                st.error(f"❌ **{ticker_input}** je o ${curr_price-mos_price:.2f} NAD MoS cenou → dle DCF **NADHODNOCENÁ**.")

            # Sensitivity
            st.markdown('<div class="section-header">📐 Sensitivity tabulka (Fair Value / akcii)</div>',
                        unsafe_allow_html=True)
            g_range = [growth_rate + d for d in (-0.04, -0.02, 0, 0.02, 0.04)]
            d_range = [discount_rate + d for d in (-0.02, -0.01, 0, 0.01, 0.02)]
            sens = {}
            for dr in d_range:
                row = {}
                for gr in g_range:
                    if dr > terminal_gr and gr >= 0:
                        pv = dcf_model(fcf, gr, terminal_gr, dr)
                        row[f"G={gr*100:.1f}%"] = f"${pv/shares_out:.2f}" if pv else "N/A"
                    else:
                        row[f"G={gr*100:.1f}%"] = "N/A"
                sens[f"D={dr*100:.1f}%"] = row
            st.dataframe(pd.DataFrame(sens).T, use_container_width=True)

            # Waterfall
            st.markdown('<div class="section-header">📊 DCF Waterfall (PV / akcii)</div>',
                        unsafe_allow_html=True)
            labels, pvs, cf_t = [], [], fcf
            for t in range(1, 11):
                cf_t *= (1 + (growth_rate if t <= 5 else terminal_gr))
                pvs.append(round(cf_t / (1 + discount_rate)**t / shares_out, 2))
                labels.append(f"Yr {t}")
            tv = (cf_t * (1 + terminal_gr) / (discount_rate - terminal_gr)) / (1+discount_rate)**10 / shares_out
            labels.append("Terminální"); pvs.append(round(tv, 2))

            fig3 = go.Figure(go.Bar(
                x=labels, y=pvs,
                marker_color=["#00c4b4"]*10 + ["#ffd600"],
                text=[f"${v:.2f}" for v in pvs], textposition="outside",
            ))
            fig3.update_layout(
                paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
                font_color="#e0e0e0", height=340,
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis=dict(title="PV / akcii ($)", gridcolor="#2a2d3a"),
                xaxis=dict(gridcolor="#2a2d3a"),
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.error("DCF výpočet selhal – zkontroluj Discount Rate vs Terminal Growth Rate.")
    else:
        st.warning(f"FCF pro {ticker_input} není k dispozici nebo je záporný. DCF nelze spočítat.")

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

    s1, s2, s3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
    with s1: show_statement(inc, "Income Statement")
    with s2: show_statement(bal, "Balance Sheet")
    with s3: show_statement(cf,  "Cash Flow Statement")

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<small style='color:#555'>⚠️ Pouze pro informační účely. Není investiční poradenství. "
    "Data: yfinance / Yahoo Finance. Investujte na vlastní riziko.</small>",
    unsafe_allow_html=True
)
