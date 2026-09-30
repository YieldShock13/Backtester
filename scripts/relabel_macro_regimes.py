from pathlib import Path
p=Path('app.py')
s=p.read_text()
repls={
"st.caption('Historical conditional regimes within the configured backtest window. σ thresholds are estimated from factor changes over that same configured window; these are conditional historical observations, not hypothetical repricing shocks.')":"st.caption('Historical conditional regimes within the configured backtest window — not hypothetical repricing shocks. JSE ≥10% refers to the market being at least 10% below its prior running peak; reported JSE return is the average period return while in that drawdown regime. σ thresholds are estimated from factor changes over the same configured window.')",
"st.toggle('JSE drawdown ≥10%'":"st.toggle('JSE drawdown regime (≥10% below prior peak)'",
"'JSE Drawdown ≥10%','JSE benchmark drawdown from running peak ≤ -10%'":"'JSE Drawdown Regime (≥10% below prior peak)','Historical observations where JSE level is ≥10% below prior running peak; this is NOT a -10% one-period shock'",
"{'Scenario':'JSE Drawdown ≥10%','Factor':BENCHMARK_TICKER,'Transformation':'drawdown from running peak','Threshold':'≤ -10%'":"{'Scenario':'JSE Drawdown Regime (≥10% below prior peak)','Factor':BENCHMARK_TICKER,'Transformation':'drawdown state versus prior running peak (not one-period return)','Threshold':'drawdown ≤ -10%'",
"'Avg JSE Return'":"'Avg JSE Period Return During Regime'"
}
for old,new in repls.items():
 if old not in s: raise SystemExit('Missing target: '+old)
 s=s.replace(old,new)
p.write_text(s)
