# Portfolio Backtester

Streamlit dashboard for the ZAR portfolio backtest beginning February 2012.

## Portfolio

Starting capital: **R1,202,000**

- FTSE/JSE All Share (`^J203.JO`): R400,000
- S&P 500 (`^GSPC`): R200,000
- South African government bonds (SARB `KBP2013M` GOVI): R200,000
- STOXX Europe (`^STOXX`): R125,000
- NewGold (`GLD.JO`): R45,000
- Exxaro (`EXX.JO`): R50,000
- Berkshire Hathaway B (`BRK-B`): R56,000
- MSCI Emerging Markets (`EEM`): R65,000
- US Aggregate Bond ETF (`AGG`): R61,000

Foreign assets are translated to ZAR. Risk-free rate for Sharpe/Sortino analytics is 7% p.a.

## Backtests

The dashboard shows both:

1. **Buy & Hold** — original capital is invested once and weights drift.
2. **Annual Rebalanced** — portfolio is reset to original target weights at the start of each calendar year.

It includes portfolio value, growth of R100, drawdown, monthly returns, rolling 12-month return, rolling volatility, rolling 36-month Sharpe, sleeve values, annual returns, weight drift, VaR/CVaR, Sortino and Calmar.

## Live updates

Yahoo Finance data are fetched by the app and cached for one hour. SARB GOVI is monthly; the app checks SARB quarterly data releases and carries the latest published GOVI level forward until a new observation is published. This allows fresh market prices to update the portfolio without fabricating daily government-bond-index returns.

## Streamlit

Main file: `app.py`
