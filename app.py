import io
import re
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Portfolio Backtester", layout="wide")

START = "2012-02-01"
RF = 0.07
INITIAL = 1_202_000
ALLOC = {
    "ALSI": 400_000,
    "SP500": 200_000,
    "SA_BONDS": 200_000,
    "EUROPE": 125_000,
    "NEWGOLD": 45_000,
    "EXXARO": 50_000,
    "BERKSHIRE": 56_000,
    "MSCI_EM": 65_000,
    "AGG": 61_000,
}
TICKERS = {
    "ALSI": "^J203.JO",
    "SP500": "^GSPC",
    "EUROPE": "^STOXX",
    "NEWGOLD": "GLD.JO",
    "EXXARO": "EXX.JO",
    "BERKSHIRE": "BRK-B",
    "MSCI_EM": "EEM",
    "AGG": "AGG",
    "USDZAR": "ZAR=X",
    "EURZAR": "EURZAR=X",
}


def _quarter_candidates():
    now = pd.Timestamp.today()
    quarter_months = [(3, "March"), (6, "June"), (9, "September"), (12, "December")]
    out = []
    for year in range(now.year, 2025, -1):
        for month, name in reversed(quarter_months):
            if year == now.year and month > now.month:
                continue
            bases = [
                f"02Kbp2%20Capital%20Market%20{name}%20{year}.zip",
                f"02Kbp2%20Capital%20Markets%20{name}%20{year}.zip",
                f"02Kbp2%20Capital%20Markets%20and%20Flow%20of%20Funds%20{name}%20{year}.zip",
            ]
            for b in bases:
                out.append(f"https://www.resbank.co.za/content/dam/sarb/publications/quarterly-bulletins/download-information-from-zipped-data-files/{year}/{b}")
    # Known-good validated source from the original reconstruction.
    out.append("https://www.resbank.co.za/content/dam/sarb/publications/quarterly-bulletins/download-information-from-zipped-data-files/2026/02Kbp2%20Capital%20Market%20March%202026.zip")
    return list(dict.fromkeys(out))


def _parse_govi_dat(text):
    lines = text.splitlines()
    header_i = None
    for i, line in enumerate(lines):
        if line.startswith("1KBP2013MM"):
            header_i = i
            break
    if header_i is None:
        raise ValueError("KBP2013M GOVI series not found")

    rows = []
    for line in lines[header_i + 1:]:
        if line.startswith("1"):
            break
        if not line.startswith("4"):
            continue
        m = re.match(r"^4(\d{4}/\d{2})\s+([+-]\d+)F", line)
        if m:
            rows.append((pd.to_datetime(m.group(1), format="%Y/%m"), float(m.group(2))))
    if not rows:
        raise ValueError("No GOVI monthly observations parsed")
    s = pd.Series(dict(rows), name="SA_BONDS").sort_index()
    s.index = s.index + pd.offsets.MonthEnd(0)
    return s


@st.cache_data(ttl=21600, show_spinner=False)
def load_govi():
    last_error = None
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in _quarter_candidates():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200 or not resp.content.startswith(b"PK"):
                continue
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                dats = [n for n in z.namelist() if n.lower().endswith(".dat")]
                if not dats:
                    continue
                text = z.read(dats[0]).decode("latin-1", errors="ignore")
            s = _parse_govi_dat(text)
            return s, url
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Could not load SARB GOVI: {last_error}")


@st.cache_data(ttl=3600, show_spinner=False)
def load_yahoo():
    raw = yf.download(
        list(TICKERS.values()), start=START, end=None,
        auto_adjust=False, actions=False, progress=False, group_by="column"
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no data")
    adj = raw["Adj Close"].copy()
    reverse = {v: k for k, v in TICKERS.items()}
    adj = adj.rename(columns=reverse)
    # JSE securities are quoted in cents; J203 is an index level.
    for c in ["NEWGOLD", "EXXARO"]:
        adj[c] = adj[c] / 100.0
    adj["USDZAR"] = adj["USDZAR"].ffill()
    adj["EURZAR"] = adj["EURZAR"].ffill()
    zar = pd.DataFrame(index=adj.index)
    for c in ["ALSI", "NEWGOLD", "EXXARO"]:
        zar[c] = adj[c]
    for c in ["SP500", "BERKSHIRE", "MSCI_EM", "AGG"]:
        zar[c] = adj[c] * adj["USDZAR"]
    zar["EUROPE"] = adj["EUROPE"] * adj["EURZAR"]
    return zar


def build_monthly_master():
    zar = load_yahoo()
    govi, source = load_govi()
    monthly = zar.resample("ME").last()
    # GOVI is monthly. Extend its most recently published level through the current month;
    # Yahoo sleeves continue updating as fresh prices arrive.
    idx = monthly.index.union(govi.index).sort_values()
    bond = govi.reindex(idx).ffill().reindex(monthly.index)
    master = monthly.join(bond, how="left")
    assets = list(ALLOC)
    master = master[assets].loc["2012-02-01":].dropna()
    return master, source


def buy_hold(master):
    vals = master.div(master.iloc[0]).mul(pd.Series(ALLOC), axis=1)
    vals["PORTFOLIO"] = vals.sum(axis=1)
    return vals


def annual_rebalanced(master):
    assets = list(ALLOC)
    target = pd.Series(ALLOC, dtype=float) / INITIAL
    returns = master[assets].pct_change(fill_method=None).fillna(0.0)
    values = pd.DataFrame(index=master.index, columns=assets, dtype=float)
    values.iloc[0] = pd.Series(ALLOC)
    for i in range(1, len(master)):
        prev = values.iloc[i - 1].astype(float)
        # Rebalance at the start of each calendar year (before that month's return).
        if master.index[i].year != master.index[i - 1].year:
            prev = target * prev.sum()
        values.iloc[i] = prev * (1.0 + returns.iloc[i])
    values["PORTFOLIO"] = values.sum(axis=1)
    return values


def metrics(values):
    p = values["PORTFOLIO"].dropna()
    r = p.pct_change(fill_method=None).dropna()
    years = (p.index[-1] - p.index[0]).days / 365.25
    cagr = (p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1
    vol = r.std() * np.sqrt(12)
    mrf = (1 + RF) ** (1 / 12) - 1
    excess = r - mrf
    sharpe = excess.mean() / excess.std() * np.sqrt(12)
    downside = excess[excess < 0]
    downside_vol = np.sqrt(np.mean(downside ** 2)) * np.sqrt(12)
    sortino = (excess.mean() * 12) / downside_vol
    dd = p / p.cummax() - 1
    mdd = dd.min()
    var95 = r.quantile(0.05)
    cvar95 = r[r <= var95].mean()
    return {
        "Initial Value": p.iloc[0], "Ending Value": p.iloc[-1],
        "Total Return": p.iloc[-1] / p.iloc[0] - 1, "CAGR": cagr,
        "Annualised Volatility": vol, "Sharpe Ratio (RF 7%)": sharpe,
        "Downside Volatility": downside_vol, "Sortino Ratio": sortino,
        "Maximum Drawdown": mdd, "Calmar Ratio": cagr / abs(mdd),
        "Monthly VaR 95%": var95, "Monthly CVaR 95%": cvar95,
        "Best Month": r.max(), "Worst Month": r.min(),
        "Positive Months": (r > 0).mean(), "Max DD Date": dd.idxmin(),
    }


def annual_returns(values):
    r = values["PORTFOLIO"].pct_change(fill_method=None).dropna()
    a = (1 + r).groupby(r.index.year).prod() - 1
    out = pd.DataFrame({"Year": a.index.astype(int), "Annual Return": a.values})
    out["Period"] = "Full Year"
    if values.index[0].month != 1:
        out.loc[out["Year"] == values.index[0].year, "Period"] = "Partial Year"
    if values.index[-1].month != 12:
        out.loc[out["Year"] == values.index[-1].year, "Period"] = "Partial Year"
    return out


def line_chart(series_map, title, ytitle):
    fig = go.Figure()
    for name, s in series_map.items():
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=name))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title=ytitle,
                      hovermode="x unified", legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def metric_table(m):
    pct = {"Total Return", "CAGR", "Annualised Volatility", "Downside Volatility",
           "Maximum Drawdown", "Monthly VaR 95%", "Monthly CVaR 95%", "Best Month",
           "Worst Month", "Positive Months"}
    rows = []
    for k, v in m.items():
        if k == "Max DD Date":
            value = pd.Timestamp(v).strftime("%Y-%m")
        elif k in ["Initial Value", "Ending Value"]:
            value = f"R{v:,.0f}"
        elif k in pct:
            value = f"{v:.2%}"
        else:
            value = f"{v:.3f}"
        rows.append((k, value))
    return pd.DataFrame(rows, columns=["Metric", "Value"])


st.title("Portfolio Backtester")
st.caption("Live Yahoo Finance market data + SARB GOVI | Starting capital R1,202,000 | Risk-free rate 7%")

try:
    with st.spinner("Updating market data…"):
        master, govi_source = build_monthly_master()
        bh = buy_hold(master)
        rb = annual_rebalanced(master)
except Exception as e:
    st.error(f"Data update failed: {e}")
    st.stop()

bhm, rbm = metrics(bh), metrics(rb)
last = master.index[-1]
st.caption(f"Data through {last:%d %b %Y}. Yahoo data refreshes hourly; GOVI updates when a newer SARB release is available.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Buy & Hold Value", f"R{bhm['Ending Value']:,.0f}")
c2.metric("Buy & Hold CAGR", f"{bhm['CAGR']:.2%}")
c3.metric("Sharpe (7% RF)", f"{bhm['Sharpe Ratio (RF 7%)']:.3f}")
c4.metric("Max Drawdown", f"{bhm['Maximum Drawdown']:.2%}")

st.subheader("Buy & Hold vs Annual Rebalancing")
line_chart({"Buy & Hold": bh["PORTFOLIO"], "Annual Rebalanced": rb["PORTFOLIO"]},
           "Portfolio Value", "ZAR")

comparison = pd.DataFrame({
    "Buy & Hold": metric_table(bhm).set_index("Metric")["Value"],
    "Annual Rebalanced": metric_table(rbm).set_index("Metric")["Value"],
})
st.dataframe(comparison, use_container_width=True)

tab_bh, tab_rb = st.tabs(["Buy & Hold", "Annual Rebalanced"])
for tab, name, vals, met in [(tab_bh, "Buy & Hold", bh, bhm), (tab_rb, "Annual Rebalanced", rb, rbm)]:
    with tab:
        st.subheader(f"{name} Analytics")
        st.dataframe(metric_table(met), hide_index=True, use_container_width=True)
        p = vals["PORTFOLIO"]
        r = p.pct_change(fill_method=None).dropna()
        growth = p / p.iloc[0] * 100
        dd = (p / p.cummax() - 1) * 100
        roll_ret = ((1 + r).rolling(12).apply(np.prod, raw=True) - 1) * 100
        roll_vol = r.rolling(12).std() * np.sqrt(12) * 100
        mrf = (1 + RF) ** (1 / 12) - 1
        ex = r - mrf
        roll_sr = ex.rolling(36).mean() / ex.rolling(36).std() * np.sqrt(12)

        line_chart({name: p}, "Portfolio Value", "ZAR")
        line_chart({name: growth}, "Growth of R100", "Value")
        line_chart({"Drawdown": dd}, "Portfolio Drawdown", "%")

        bar = go.Figure(go.Bar(x=r.index, y=r.values * 100, name="Monthly Return"))
        bar.update_layout(title="Monthly Portfolio Returns", xaxis_title="Date", yaxis_title="Return (%)")
        st.plotly_chart(bar, use_container_width=True)

        line_chart({"12M Return": roll_ret}, "Rolling 12-Month Return", "%")
        line_chart({"12M Volatility": roll_vol}, "Rolling 12-Month Annualised Volatility", "%")
        line_chart({"36M Sharpe": roll_sr}, "Rolling 36-Month Sharpe Ratio — RF 7%", "Sharpe")

        sleeve_cols = list(ALLOC)
        line_chart({c: vals[c] for c in sleeve_cols}, "Portfolio Sleeve Values", "ZAR")

        st.subheader("Annual Returns")
        ar = annual_returns(vals).copy()
        ar["Annual Return"] = ar["Annual Return"].map(lambda x: f"{x:.2%}")
        st.dataframe(ar, hide_index=True, use_container_width=True)

        weights = vals[list(ALLOC)].div(vals["PORTFOLIO"], axis=0)
        wt = pd.DataFrame({
            "Asset": list(ALLOC),
            "Initial Weight": [ALLOC[a] / INITIAL for a in ALLOC],
            "Ending Weight": weights.iloc[-1].values,
        })
        wt["Initial Weight"] = wt["Initial Weight"].map(lambda x: f"{x:.2%}")
        wt["Ending Weight"] = wt["Ending Weight"].map(lambda x: f"{x:.2%}")
        st.subheader("Portfolio Weights")
        st.dataframe(wt, hide_index=True, use_container_width=True)

with st.expander("Methodology & data"):
    st.write("The Buy & Hold portfolio invests the original allocations once and permits weights to drift. The Annual Rebalanced portfolio resets to the original target weights at the start of each calendar year. Foreign sleeves are translated into ZAR. The R400k South African equity sleeve uses the FTSE/JSE All Share (^J203.JO). The R200k South African bond sleeve uses SARB KBP2013M GOVI.")
    st.write("Yahoo market data are refreshed hourly by the app. GOVI is a monthly SARB series; its latest published level is carried forward until SARB publishes a new observation. This permits the dashboard to update with fresh market prices without inventing daily GOVI returns.")
    st.write(f"SARB source loaded: {govi_source}")
